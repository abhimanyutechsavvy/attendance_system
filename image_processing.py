import cv2
import numpy as np
from pathlib import Path

from config import MIN_FACE_SIZE_RATIO, REQUIRE_FACE_FOR_MATCH


SUPPORTED_IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png")


def detect_faces(image):
    if image is None:
        return []

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    face_cascade = cv2.CascadeClassifier(cascade_path)
    if face_cascade.empty():
        return []

    min_side = max(24, int(min(gray.shape[:2]) * MIN_FACE_SIZE_RATIO))
    faces = face_cascade.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(min_side, min_side),
    )
    return list(faces)


def has_detectable_face(image):
    return len(detect_faces(image)) > 0


def compare_images(live_image, stored_image, threshold: float = 0.25):
    if live_image is None or stored_image is None:
        return False, 0.0

    if REQUIRE_FACE_FOR_MATCH and not has_detectable_face(live_image):
        return False, 0.0

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
