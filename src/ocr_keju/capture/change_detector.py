from __future__ import annotations

import cv2
import numpy as np


def frame_signature(image: np.ndarray) -> np.ndarray:
    """Return a tiny grayscale representation suitable for cheap change checks."""
    if image.ndim == 2:
        gray = image
    else:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    small = cv2.resize(gray, (64, 36), interpolation=cv2.INTER_AREA)
    return cv2.GaussianBlur(small, (3, 3), 0)


def frame_difference(previous: np.ndarray, current: np.ndarray) -> float:
    if previous.shape != current.shape:
        return 1.0
    delta = cv2.absdiff(previous, current)
    return float(delta.mean()) / 255.0
