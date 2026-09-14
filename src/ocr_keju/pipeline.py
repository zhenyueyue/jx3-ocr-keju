from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ocr_keju.api import JX3BoxApiError, JX3BoxExamClient
from ocr_keju.config import Settings
from ocr_keju.database import QuestionRepository
from ocr_keju.image import preprocess_question_image
from ocr_keju.models import SearchResult
from ocr_keju.ocr import OcrResult, RapidOcrEngine
from ocr_keju.services import QuestionService


@dataclass(frozen=True, slots=True)
class RecognitionOutcome:
    ocr: OcrResult
    match: SearchResult | None
    warning: str = ""


class RecognitionPipeline:
    def __init__(
        self,
        settings: Settings,
        repository: QuestionRepository,
        ocr_engine: RapidOcrEngine | None = None,
    ) -> None:
        self.settings = settings
        self.repository = repository
        self.ocr_engine = ocr_engine or RapidOcrEngine()

    def recognize(
        self,
        image: np.ndarray,
        local_match_threshold: float = 0.78,
    ) -> RecognitionOutcome:
        prepared = preprocess_question_image(image)
        ocr = self.ocr_engine.recognize(prepared)
        if not ocr.text.strip():
            return RecognitionOutcome(ocr=ocr, match=None, warning="OCR 未识别到文字")

        try:
            with JX3BoxExamClient(
                base_url=self.settings.api_base_url,
                timeout_seconds=self.settings.api_timeout_seconds,
            ) as client:
                service = QuestionService(
                    self.repository,
                    client,
                    local_match_threshold=local_match_threshold,
                )
                match = service.resolve(ocr.text)
        except JX3BoxApiError as exc:
            return RecognitionOutcome(
                ocr=ocr,
                match=None,
                warning=f"本地未达到匹配阈值，远端查询失败：{exc}",
            )

        warning = "" if match is not None else "未找到匹配题目"
        return RecognitionOutcome(ocr=ocr, match=match, warning=warning)
