from __future__ import annotations

import cv2
import numpy as np


def frame_signature(image: np.ndarray) -> np.ndarray:
    """Return a tiny grayscale representation suitable for cheap change checks."""
    if image.ndim == 2:
        gray = image
    else:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    small = cv2.resize(gray, (96, 54), interpolation=cv2.INTER_AREA)
    return cv2.GaussianBlur(small, (3, 3), 0)


def frame_difference(previous: np.ndarray, current: np.ndarray) -> float:
    """Return the ratio of visibly changed pixels in two tiny frame signatures.

    Text changes occupy only a small portion of the selected game UI. Using the
    whole-image mean hid many real question changes, while a changed-pixel ratio
    keeps strong character-edge changes visible without making OCR run every tick.
    """
    if previous.shape != current.shape:
        return 1.0
    delta = cv2.absdiff(previous, current)
    strong_ratio = float(np.count_nonzero(delta >= 12)) / float(delta.size)
    medium_ratio = float(np.count_nonzero(delta >= 6)) / float(delta.size)
    return max(strong_ratio, medium_ratio * 0.55)
