from __future__ import annotations

from dataclasses import dataclass
from threading import Lock

import numpy as np
from rapidfuzz import fuzz

from ocr_keju.api import JX3BoxApiError, JX3BoxExamClient
from ocr_keju.config import Settings
from ocr_keju.database import QuestionRepository
from ocr_keju.image import preprocess_question_image
from ocr_keju.matching import LocalQuestionMatcher
from ocr_keju.models import SearchResult
from ocr_keju.ocr import OcrResult, RapidOcrEngine
from ocr_keju.question import normalize_question
from ocr_keju.services import QuestionService


@dataclass(frozen=True, slots=True)
class AnswerBox:
    left: int
    top: int
    width: int
    height: int
    text: str
    confidence: float


@dataclass(frozen=True, slots=True)
class RecognitionOutcome:
    ocr: OcrResult
    match: SearchResult | None
    warning: str = ""
    answer_boxes: tuple[AnswerBox, ...] = ()
    detected_question: str = ""
    question_watch_height: int = 0


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
        self._local_matcher: LocalQuestionMatcher | None = None
        self._matcher_lock = Lock()

    def warmup(self) -> None:
        self.ocr_engine.warmup()
        self.refresh_local_index()

    def invalidate_local_index(self) -> None:
        with self._matcher_lock:
            self._local_matcher = None

    def refresh_local_index(self) -> None:
        matcher = LocalQuestionMatcher(self.repository.list_all())
        with self._matcher_lock:
            self._local_matcher = matcher

    def _get_local_matcher(self) -> LocalQuestionMatcher:
        with self._matcher_lock:
            matcher = self._local_matcher
        if matcher is not None:
            return matcher
        self.refresh_local_index()
        with self._matcher_lock:
            assert self._local_matcher is not None
            return self._local_matcher

    def recognize(
        self,
        image: np.ndarray,
        local_match_threshold: float = 0.78,
    ) -> RecognitionOutcome:
        original_height, original_width = image.shape[:2]
        prepared = preprocess_question_image(image)
        prepared_height, prepared_width = prepared.shape[:2]
        ocr = self.ocr_engine.recognize(prepared)
        if not ocr.text.strip():
            return RecognitionOutcome(ocr=ocr, match=None, warning="OCR 未识别到文字")

        scale_x = prepared_width / max(original_width, 1)
        scale_y = prepared_height / max(original_height, 1)

        matcher = self._get_local_matcher()
        local_service = QuestionService(
            self.repository,
            None,
            local_match_threshold=local_match_threshold,
            local_matcher=matcher,
        )
        resolution = local_service.resolve_ocr_lines(tuple(line.text for line in ocr.lines))
        match = resolution.result
        question_watch_height = self._question_watch_height(
            ocr,
            resolution.question_line_count,
            scale_y,
            original_height,
        )

        if match is None and resolution.raw_question:
            try:
                with JX3BoxExamClient(
                    base_url=self.settings.api_base_url,
                    timeout_seconds=self.settings.api_timeout_seconds,
                ) as client:
                    remote_service = QuestionService(
                        self.repository,
                        client,
                        local_match_threshold=local_match_threshold,
                        local_matcher=matcher,
                    )
                    match = remote_service.resolve(resolution.raw_question)
                    if match is not None and match.source == "jx3box":
                        with self._matcher_lock:
                            self._local_matcher = remote_service.local_matcher
            except JX3BoxApiError as exc:
                return RecognitionOutcome(
                    ocr=ocr,
                    match=None,
                    warning=f"本地未达到匹配阈值，远端查询失败：{exc}",
                    detected_question=resolution.raw_question,
                    question_watch_height=question_watch_height,
                )

        if match is None:
            return RecognitionOutcome(
                ocr=ocr,
                match=None,
                warning="未找到匹配题目",
                detected_question=resolution.raw_question,
                question_watch_height=question_watch_height,
            )

        answer_boxes = self._find_answer_boxes(
            ocr,
            match,
            resolution.question_line_count,
            scale_x,
            scale_y,
            original_width,
            original_height,
        )
        warning = "" if answer_boxes else "已找到答案，但没有在选项区域定位到答案文字，请重新框选题目和全部选项"
        return RecognitionOutcome(
            ocr=ocr,
            match=match,
            warning=warning,
            answer_boxes=answer_boxes,
            detected_question=resolution.raw_question,
            question_watch_height=question_watch_height,
        )

    @staticmethod
    def _question_watch_height(
        ocr: OcrResult,
        question_line_count: int,
        scale_y: float,
        original_height: int,
    ) -> int:
        question_lines = [
            line
            for line in ocr.lines[: max(0, question_line_count)]
            if line.box
        ]
        if not question_lines:
            return max(40, min(original_height, int(original_height * 0.35)))

        bottom = max(max(point[1] for point in line.box) for line in question_lines)
        mapped_bottom = int(bottom / max(scale_y, 1e-6))
        return max(40, min(original_height, mapped_bottom + 24))

    @staticmethod
    def _find_answer_boxes(
        ocr: OcrResult,
        match: SearchResult,
        question_line_count: int,
        scale_x: float,
        scale_y: float,
        original_width: int,
        original_height: int,
    ) -> tuple[AnswerBox, ...]:
        option_lines = list(ocr.lines[max(0, question_line_count):])
        if not option_lines:
            return ()

        boxes: list[AnswerBox] = []
        used_indices: set[int] = set()
        for answer in match.question.answer_text:
            answer_normalized = normalize_question(answer)
            if not answer_normalized:
                continue

            best_index = -1
            best_score = 0.0
            for index, line in enumerate(option_lines):
                if index in used_indices or not line.box:
                    continue
                line_normalized = normalize_question(line.text)
                if not line_normalized:
                    continue
                score = max(
                    fuzz.ratio(answer_normalized, line_normalized),
                    fuzz.partial_ratio(answer_normalized, line_normalized),
                ) / 100.0
                if score > best_score:
                    best_score = score
                    best_index = index

            if best_index < 0 or best_score < 0.62:
                continue

            used_indices.add(best_index)
            line = option_lines[best_index]
            xs = [point[0] / max(scale_x, 1e-6) for point in line.box]
            ys = [point[1] / max(scale_y, 1e-6) for point in line.box]
            left = max(0, int(min(xs)) - 10)
            top = max(0, int(min(ys)) - 7)
            right = min(original_width, int(max(xs)) + 10)
            bottom = min(original_height, int(max(ys)) + 7)
            boxes.append(
                AnswerBox(
                    left=left,
                    top=top,
                    width=max(1, right - left),
                    height=max(1, bottom - top),
                    text=line.text,
                    confidence=best_score,
                )
            )

        return tuple(boxes)
