from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np


def load_image(path: Path | str) -> np.ndarray:
    data = np.fromfile(str(path), dtype=np.uint8)
    image = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"无法读取图片: {path}")
    return image


def preprocess_question_image(image: np.ndarray) -> np.ndarray:
    """Enhance a small game-UI text crop without destroying character edges."""

    if image.ndim == 2:
        bgr = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    elif image.shape[2] == 4:
        bgr = cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
    else:
        bgr = image.copy()

    height, width = bgr.shape[:2]
    if height < 260:
        scale = min(2.0, max(1.25, 260.0 / max(height, 1)))
        bgr = cv2.resize(
            bgr,
            (int(width * scale), int(height * scale)),
            interpolation=cv2.INTER_CUBIC,
        )

    lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB)
    lightness, a_channel, b_channel = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    lightness = clahe.apply(lightness)
    enhanced = cv2.merge((lightness, a_channel, b_channel))
    return cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)
