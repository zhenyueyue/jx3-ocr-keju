import numpy as np
import pytest

from ocr_keju.ocr import RapidOcrEngine


class FakeResult:
    txts = ("第二行", "第一行")
    scores = (0.8, 0.9)
    boxes = np.array(
        [
            [[0, 50], [100, 50], [100, 70], [0, 70]],
            [[0, 10], [100, 10], [100, 30], [0, 30]],
        ],
        dtype=np.float32,
    )


def test_ocr_result_is_sorted_top_to_bottom() -> None:
    result = RapidOcrEngine._convert_result(FakeResult(), 0.12)

    assert result.text == "第一行\n第二行"
    assert result.mean_score == pytest.approx(0.85)
    assert result.elapsed_seconds == 0.12
