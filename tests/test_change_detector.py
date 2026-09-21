import numpy as np

from ocr_keju.capture.change_detector import frame_difference, frame_signature


def test_frame_difference_ignores_identical_frames_and_detects_change() -> None:
    first = np.zeros((200, 400, 3), dtype=np.uint8)
    second = first.copy()
    second[40:160, 80:320] = 255

    first_signature = frame_signature(first)
    same_signature = frame_signature(first.copy())
    changed_signature = frame_signature(second)

    assert frame_difference(first_signature, same_signature) == 0.0
    assert frame_difference(first_signature, changed_signature) > 0.1
