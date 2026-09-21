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


def test_frame_difference_detects_small_text_like_change() -> None:
    first = np.zeros((140, 800, 3), dtype=np.uint8)
    second = first.copy()
    # 模拟题干一小段文字发生变化，而不是整块 UI 变化。
    second[35:55, 80:360] = 255

    score = frame_difference(frame_signature(first), frame_signature(second))

    assert score > 0.012
