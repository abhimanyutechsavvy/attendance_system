import cv2
import numpy as np


def compare_images(live_image, stored_image, threshold: float = 0.25):
    if live_image is None or stored_image is None:
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
