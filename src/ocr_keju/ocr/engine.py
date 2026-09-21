from __future__ import annotations

from dataclasses import dataclass
from threading import Lock
from time import perf_counter
from typing import Any

import numpy as np


@dataclass(frozen=True, slots=True)
class OcrLine:
    text: str
    score: float
    box: tuple[tuple[float, float], ...]


@dataclass(frozen=True, slots=True)
class OcrResult:
    text: str
    lines: tuple[OcrLine, ...]
    mean_score: float
    elapsed_seconds: float


class RapidOcrEngine:
    """Lazy RapidOCR wrapper so the models load only when OCR is first used."""

    def __init__(self) -> None:
        self._engine: Any | None = None
        self._engine_lock = Lock()

    def _get_engine(self) -> Any:
        if self._engine is not None:
            return self._engine
        with self._engine_lock:
            if self._engine is None:
                from rapidocr import RapidOCR

                # RapidOCR 默认会把较小截图的短边强制放大到 736，
                # 对清晰的游戏 UI 区域会制造大量无意义像素。这里只限制超大截图，
                # 普通科举区域保持原尺寸，显著降低文字检测延迟。
                self._engine = RapidOCR(
                    params={
                        "Det.limit_type": "max",
                        "Det.limit_side_len": 960,
                        "Global.log_level": "error",
                    }
                )
        return self._engine

    def warmup(self) -> None:
        self._get_engine()

    def recognize(self, image: np.ndarray) -> OcrResult:
        started = perf_counter()
        result = self._get_engine()(image, use_cls=False)
        elapsed = perf_counter() - started
        return self._convert_result(result, elapsed)

    @staticmethod
    def _convert_result(result: Any, elapsed_seconds: float) -> OcrResult:
        txts = tuple(getattr(result, "txts", None) or ())
        scores = tuple(float(v) for v in (getattr(result, "scores", None) or ()))
        boxes_raw = getattr(result, "boxes", None)

        if not txts:
            return OcrResult(text="", lines=(), mean_score=0.0, elapsed_seconds=elapsed_seconds)

        if boxes_raw is None:
            boxes = [() for _ in txts]
        else:
            boxes = [
                tuple((float(point[0]), float(point[1])) for point in box)
                for box in boxes_raw
            ]

        if len(scores) < len(txts):
            scores = scores + (0.0,) * (len(txts) - len(scores))
        if len(boxes) < len(txts):
            boxes.extend([()] * (len(txts) - len(boxes)))

        indices = list(range(len(txts)))
        if any(boxes):
            indices.sort(
                key=lambda index: (
                    min((point[1] for point in boxes[index]), default=float(index)),
                    min((point[0] for point in boxes[index]), default=0.0),
                )
            )

        lines = tuple(
            OcrLine(text=str(txts[index]).strip(), score=scores[index], box=boxes[index])
            for index in indices
            if str(txts[index]).strip()
        )
        text = "\n".join(line.text for line in lines)
        mean_score = (
            sum(line.score for line in lines) / len(lines)
            if lines
            else 0.0
        )
        return OcrResult(
            text=text,
            lines=lines,
            mean_score=mean_score,
            elapsed_seconds=elapsed_seconds,
        )
