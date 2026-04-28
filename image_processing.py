import cv2
import numpy as np
import threading
from pathlib import Path

from config import (
    DEBUG_MATCH_SCORES,
    FACE_COMBINED_THRESHOLD,
    FACE_HISTOGRAM_THRESHOLD,
    FACE_ORB_THRESHOLD,
    FACE_STRUCTURAL_THRESHOLD,
    MIN_CROP_DETAIL_STDDEV,
    MIN_FACE_SIZE_RATIO,
    REQUIRE_FACE_FOR_MATCH,
    SFACE_COSINE_THRESHOLD,
    SFACE_REQUIRED_FOR_MATCH,
    SFACE_RECOGNITION_MODEL,
    YUNET_FACE_DETECTION_MODEL,
    YUNET_SCORE_THRESHOLD,
)


SUPPORTED_IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png")
_yunet_detector = None
_yunet_input_size = None
_yunet_lock = threading.Lock()
_sface_recognizer = None


def _model_exists(path):
    return path is not None and Path(path).exists()


def detect_faces_yunet(image):
    if image is None or not _model_exists(YUNET_FACE_DETECTION_MODEL):
        return []

    height, width = image.shape[:2]
    global _yunet_detector, _yunet_input_size

    with _yunet_lock:
        if _yunet_detector is None or _yunet_input_size != (width, height):
            _yunet_detector = cv2.FaceDetectorYN.create(
                str(YUNET_FACE_DETECTION_MODEL),
                "",
                (width, height),
                score_threshold=YUNET_SCORE_THRESHOLD,
                nms_threshold=0.3,
                top_k=5000,
            )
            _yunet_input_size = (width, height)

        _, faces = _yunet_detector.detect(image)

    if faces is None:
        return []
    return [face for face in faces]


def largest_yunet_face(image):
    faces = detect_faces_yunet(image)
    if not faces:
        return None
    return max(faces, key=lambda face: face[2] * face[3])


def get_sface_recognizer():
    global _sface_recognizer
    if _sface_recognizer is not None:
        return _sface_recognizer
    if not _model_exists(SFACE_RECOGNITION_MODEL):
        return None
    _sface_recognizer = cv2.FaceRecognizerSF.create(str(SFACE_RECOGNITION_MODEL), "")
    return _sface_recognizer


def sface_feature(image, face):
    recognizer = get_sface_recognizer()
    if recognizer is None or face is None:
        return None
    try:
        aligned = recognizer.alignCrop(image, face)
        return recognizer.feature(aligned)
    except Exception as exc:
        if DEBUG_MATCH_SCORES:
            print(f"[match] SFace feature failed: {exc}")
        return None


def compare_sface(live_image, stored_image):
    live_face = largest_yunet_face(live_image)
    stored_face = largest_yunet_face(stored_image)
    if live_face is None:
        if DEBUG_MATCH_SCORES:
            print("[match] rejected: YuNet found no live face")
        return None
    if stored_face is None:
        if DEBUG_MATCH_SCORES:
            print("[match] SFace skipped: YuNet found no stored face")
        return None

    live_feature = sface_feature(live_image, live_face)
    stored_feature = sface_feature(stored_image, stored_face)
    recognizer = get_sface_recognizer()
    if recognizer is None or live_feature is None or stored_feature is None:
        return None

    cosine_score = float(recognizer.match(live_feature, stored_feature, cv2.FaceRecognizerSF_FR_COSINE))
    match = cosine_score >= SFACE_COSINE_THRESHOLD
    if DEBUG_MATCH_SCORES:
        print(f"[match] sface_cosine={cosine_score:.3f} threshold={SFACE_COSINE_THRESHOLD:.3f} match={match}")
    return match, cosine_score


def detect_faces(image):
    if image is None:
        return []

    yunet_faces = detect_faces_yunet(image)
    if yunet_faces:
        return [(int(face[0]), int(face[1]), int(face[2]), int(face[3])) for face in yunet_faces]

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.equalizeHist(gray)

    min_side = max(24, int(min(gray.shape[:2]) * MIN_FACE_SIZE_RATIO))
    cascade_names = [
        "haarcascade_frontalface_default.xml",
        "haarcascade_frontalface_alt2.xml",
        "haarcascade_frontalface_alt.xml",
        "haarcascade_profileface.xml",
    ]

    detected = []
    for cascade_name in cascade_names:
        cascade_path = cv2.data.haarcascades + cascade_name
        face_cascade = cv2.CascadeClassifier(cascade_path)
        if face_cascade.empty():
            continue

        for min_neighbors in (4, 3, 2):
            faces = face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.05,
                minNeighbors=min_neighbors,
                minSize=(min_side, min_side),
            )
            detected.extend(list(faces))
            if detected:
                return detected

        if cascade_name == "haarcascade_profileface.xml":
            flipped = cv2.flip(gray, 1)
            faces = face_cascade.detectMultiScale(
                flipped,
                scaleFactor=1.05,
                minNeighbors=3,
                minSize=(min_side, min_side),
            )
            width = gray.shape[1]
            for x, y, w, h in faces:
                detected.append((width - x - w, y, w, h))
            if detected:
                return detected

    return detected


def has_detectable_face(image):
    return len(detect_faces(image)) > 0


def largest_face(image):
    faces = detect_faces(image)
    if not faces:
        return None
    return max(faces, key=lambda face: face[2] * face[3])


def crop_face(image, padding_ratio: float = 0.28):
    face = largest_face(image)
    if face is None:
        return None

    x, y, w, h = face
    pad_x = int(w * padding_ratio)
    pad_y = int(h * padding_ratio)
    x1 = max(0, x - pad_x)
    y1 = max(0, y - pad_y)
    x2 = min(image.shape[1], x + w + pad_x)
    y2 = min(image.shape[0], y + h + pad_y)
    if x2 <= x1 or y2 <= y1:
        return None
    return image[y1:y2, x1:x2]


def center_face_candidate(image):
    """Fallback for webcams where Haar misses faces due to lighting/angle."""
    if image is None:
        return None

    height, width = image.shape[:2]
    crop_w = int(width * 0.52)
    crop_h = int(height * 0.68)
    x1 = max(0, (width - crop_w) // 2)
    y1 = max(0, int(height * 0.12))
    x2 = min(width, x1 + crop_w)
    y2 = min(height, y1 + crop_h)
    if x2 <= x1 or y2 <= y1:
        return None
    return image[y1:y2, x1:x2]


def best_face_crop(image, allow_center_fallback: bool = False):
    face = crop_face(image)
    if face is not None:
        return face, "detected"
    if allow_center_fallback:
        return center_face_candidate(image), "center"
    return None, "missing"


def has_enough_detail(face):
    if face is None:
        return False
    gray = cv2.cvtColor(face, cv2.COLOR_BGR2GRAY)
    return float(gray.std()) >= MIN_CROP_DETAIL_STDDEV


def normalize_face(face):
    gray = cv2.cvtColor(face, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, (160, 160), interpolation=cv2.INTER_AREA)
    gray = cv2.equalizeHist(gray)
    return gray


def structural_similarity_score(face_a, face_b):
    a = normalize_face(face_a).astype(np.float32)
    b = normalize_face(face_b).astype(np.float32)

    # Lightweight SSIM-style score without adding extra dependencies.
    c1 = 6.5025
    c2 = 58.5225
    mu_a = cv2.GaussianBlur(a, (11, 11), 1.5)
    mu_b = cv2.GaussianBlur(b, (11, 11), 1.5)
    sigma_a = cv2.GaussianBlur(a * a, (11, 11), 1.5) - mu_a * mu_a
    sigma_b = cv2.GaussianBlur(b * b, (11, 11), 1.5) - mu_b * mu_b
    sigma_ab = cv2.GaussianBlur(a * b, (11, 11), 1.5) - mu_a * mu_b

    numerator = (2 * mu_a * mu_b + c1) * (2 * sigma_ab + c2)
    denominator = (mu_a * mu_a + mu_b * mu_b + c1) * (sigma_a + sigma_b + c2)
    score_map = numerator / np.maximum(denominator, 1e-6)
    return float(np.clip(score_map.mean(), 0.0, 1.0))


def histogram_similarity_score(face_a, face_b):
    a = normalize_face(face_a)
    b = normalize_face(face_b)
    hist_a = cv2.calcHist([a], [0], None, [64], [0, 256])
    hist_b = cv2.calcHist([b], [0], None, [64], [0, 256])
    cv2.normalize(hist_a, hist_a)
    cv2.normalize(hist_b, hist_b)
    return float(np.clip(cv2.compareHist(hist_a, hist_b, cv2.HISTCMP_CORREL), 0.0, 1.0))


def orb_face_score(face_a, face_b):
    a = normalize_face(face_a)
    b = normalize_face(face_b)
    orb = cv2.ORB_create(800)
    kp1, des1 = orb.detectAndCompute(a, None)
    kp2, des2 = orb.detectAndCompute(b, None)

    if des1 is None or des2 is None or len(kp1) < 12 or len(kp2) < 12:
        return 0.0

    matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
    matches = matcher.knnMatch(des1, des2, k=2)
    good_matches = []
    for pair in matches:
        if len(pair) != 2:
            continue
        m, n = pair
        if m.distance < 0.72 * n.distance:
            good_matches.append(m)

    return float(len(good_matches) / max(1, min(len(kp1), len(kp2))))


def compare_face_regions(live_image, stored_image):
    sface_result = compare_sface(live_image, stored_image)
    if sface_result is not None:
        return sface_result
    if SFACE_REQUIRED_FOR_MATCH:
        if DEBUG_MATCH_SCORES:
            print("[match] rejected: SFace match is required but no SFace comparison was available")
        return False, 0.0

    live_face, live_source = best_face_crop(live_image, allow_center_fallback=False)
    stored_face, stored_source = best_face_crop(stored_image, allow_center_fallback=True)
    if live_face is None:
        if DEBUG_MATCH_SCORES:
            print("[match] rejected: no live face detected")
        return False, 0.0

    if not has_enough_detail(live_face) or not has_enough_detail(stored_face):
        if DEBUG_MATCH_SCORES:
            print("[match] rejected: not enough detail in live/stored crop")
        return False, 0.0

    structural_score = structural_similarity_score(live_face, stored_face)
    histogram_score = histogram_similarity_score(live_face, stored_face)
    orb_score = orb_face_score(live_face, stored_face)
    combined_score = (
        structural_score * 0.50
        + histogram_score * 0.30
        + min(orb_score / 0.25, 1.0) * 0.20
    )

    # ORB can be weak on smooth/low-light face crops, so use it as a bonus
    # signal instead of a hard requirement unless the threshold is raised.
    orb_passes = FACE_ORB_THRESHOLD <= 0 or orb_score >= FACE_ORB_THRESHOLD
    match = (
        structural_score >= FACE_STRUCTURAL_THRESHOLD
        and histogram_score >= FACE_HISTOGRAM_THRESHOLD
        and orb_passes
        and combined_score >= FACE_COMBINED_THRESHOLD
    )
    if DEBUG_MATCH_SCORES:
        print(
            "[match] "
            f"live={live_source} stored={stored_source} "
            f"structural={structural_score:.3f} "
            f"hist={histogram_score:.3f} "
            f"orb={orb_score:.3f} "
            f"combined={combined_score:.3f} "
            f"match={match}"
        )
    return match, float(combined_score)


def compare_images(live_image, stored_image, threshold: float = 0.25):
    if live_image is None or stored_image is None:
        return False, 0.0

    if REQUIRE_FACE_FOR_MATCH:
        return compare_face_regions(live_image, stored_image)

    live_gray = cv2.cvtColor(live_image, cv2.COLOR_BGR2GRAY)
    stored_gray = cv2.cvtColor(stored_image, cv2.COLOR_BGR2GRAY)

    orb = cv2.ORB_create(500)
    kp1, des1 = orb.detectAndCompute(live_gray, None)
    kp2, des2 = orb.detectAndCompute(stored_gray, None)

    if des1 is None or des2 is None or len(kp1) == 0 or len(kp2) == 0:
        return False, 0.0

    matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
    matches = matcher.knnMatch(des1, des2, k=2)
    good_matches = [m for m, n in matches if m.distance < 0.75 * n.distance]

    score = len(good_matches) / max(1, min(len(kp1), len(kp2)))
    return score >= threshold, float(score)


def encode_image_data_url(image):
    ok, buffer = cv2.imencode(".jpg", image)
    if not ok:
        return ""
    import base64
    return "data:image/jpeg;base64," + base64.b64encode(buffer).decode("utf-8")


def annotate_face(image, name: str = "", match: bool = False):
    annotated = image.copy()
    face = largest_face(annotated)
    if face is None:
        label = "NO FACE DETECTED"
        color = (0, 0, 255)
        cv2.rectangle(annotated, (12, 12), (330, 58), color, cv2.FILLED)
        cv2.putText(annotated, label, (22, 44), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2, cv2.LINE_AA)
        return annotated

    x, y, w, h = [int(v) for v in face]
    x = max(0, x)
    y = max(0, y)
    color = (0, 255, 0) if match else (0, 165, 255)
    label = name.strip() if match and name else "NOT MATCHED"
    cv2.rectangle(annotated, (x, y), (x + w, y + h), color, 3)

    label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)
    label_w = max(label_size[0] + 18, 90)
    label_y1 = max(0, y - 36)
    cv2.rectangle(annotated, (x, label_y1), (x + label_w, label_y1 + 34), color, cv2.FILLED)
    cv2.putText(annotated, label, (x + 8, label_y1 + 24), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2, cv2.LINE_AA)
    return annotated


def annotate_viewfinder(image, name: str = ""):
    annotated = image.copy()
    face = largest_face(annotated)
    if face is None:
        return annotated

    x, y, w, h = [int(v) for v in face]
    x = max(0, x)
    y = max(0, y)
    color = (0, 255, 0)
    label = "FACE IN FRAME"

    cv2.rectangle(annotated, (x, y), (x + w, y + h), color, 3)
    label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)
    label_w = max(label_size[0] + 18, 120)
    label_y1 = max(0, y - 36)
    cv2.rectangle(annotated, (x, label_y1), (x + label_w, label_y1 + 34), color, cv2.FILLED)
    cv2.putText(annotated, label, (x + 8, label_y1 + 24), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2, cv2.LINE_AA)
    return annotated


def get_student_image_paths(student, base_dir: Path):
    main_image_path = base_dir / student["stored_image"]
    student_id = student["student_id"]
    paths = []

    if main_image_path.exists():
        paths.append(main_image_path)

    for extension in SUPPORTED_IMAGE_EXTENSIONS:
        paths.extend(sorted(base_dir.glob(f"{student_id}_*{extension}")))

    unique_paths = []
    seen = set()
    for path in paths:
        resolved = path.resolve()
        if resolved not in seen:
            seen.add(resolved)
            unique_paths.append(path)

    return unique_paths


def compare_with_student_images(live_image, student, base_dir: Path, threshold: float = 0.25):
    image_paths = get_student_image_paths(student, base_dir)
    best_match = False
    best_score = 0.0
    best_image = None
    best_path = None

    for image_path in image_paths:
        stored_image = cv2.imread(str(image_path))
        if stored_image is None:
            continue

        match, score = compare_images(live_image, stored_image, threshold=threshold)
        if score > best_score or best_image is None:
            best_match = match
            best_score = score
            best_image = stored_image
            best_path = image_path

    return best_match, best_score, best_image, best_path, len(image_paths)


def draw_side_by_side(image_a, image_b, window_name: str, status_text: str = None, score: float = None):
    height = max(image_a.shape[0], image_b.shape[0], 540)
    width = image_a.shape[1] + image_b.shape[1]
    canvas = np.zeros((height, width, 3), dtype=np.uint8)
    canvas[: image_a.shape[0], : image_a.shape[1]] = image_a
    canvas[: image_b.shape[0], image_a.shape[1] : image_a.shape[1] + image_b.shape[1]] = image_b

    label_color = (0, 255, 0) if status_text == "MATCH" else (0, 165, 255)
    cv2.rectangle(canvas, (0, 0), (width, 80), (40, 40, 40), cv2.FILLED)
    if status_text:
        cv2.putText(canvas, status_text, (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.4, label_color, 3, cv2.LINE_AA)
    if score is not None:
        cv2.putText(canvas, f"Score: {score:.3f}", (300, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2, cv2.LINE_AA)
    cv2.putText(canvas, "Green = Confirm   Red = Retry", (20, height - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2, cv2.LINE_AA)

    cv2.imshow(window_name, canvas)
    cv2.waitKey(1)
