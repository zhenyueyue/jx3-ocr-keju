from __future__ import annotations

from difflib import SequenceMatcher

from ocr_keju.api.client import JX3BoxExamClient
from ocr_keju.database.repository import QuestionRepository
from ocr_keju.matching import LocalQuestionMatcher
from ocr_keju.models import ExamQuestion, SearchResult
from ocr_keju.question import normalize_question


class QuestionService:
    def __init__(
        self,
        repository: QuestionRepository,
        api_client: JX3BoxExamClient,
        local_match_threshold: float = 0.78,
    ) -> None:
        self.repository = repository
        self.api_client = api_client
        self.local_match_threshold = local_match_threshold

    def resolve(self, raw_question: str) -> SearchResult | None:
        normalized = normalize_question(raw_question)
        if not normalized:
            return None

        local = self.repository.find_exact(normalized)
        if local is not None:
            return SearchResult(question=local, source="local", confidence=1.0)

        fuzzy = LocalQuestionMatcher(self.repository.list_all()).best(normalized)
        if fuzzy is not None and fuzzy.confidence >= self.local_match_threshold:
            self.repository.increment_hit(fuzzy.question.remote_id)
            return SearchResult(
                question=fuzzy.question,
                source="local",
                confidence=fuzzy.confidence,
            )

        remote_questions: list[ExamQuestion] = []
        for query in self._remote_queries(raw_question, normalized):
            remote_questions = self.api_client.search(query)
            if remote_questions:
                break
        if not remote_questions:
            return None

        self.repository.upsert_many(remote_questions)
        best, confidence = self._select_best(normalized, remote_questions)
        return SearchResult(question=best, source="jx3box", confidence=confidence)

    @staticmethod
    def _remote_queries(raw_question: str, normalized: str) -> list[str]:
        candidates: list[str] = []

        def add(value: str) -> None:
            value = value.strip()
            if len(value) >= 2 and value not in candidates:
                candidates.append(value)

        add(raw_question)
        lines = sorted(
            (line.strip() for line in raw_question.splitlines() if line.strip()),
            key=len,
            reverse=True,
        )
        for line in lines[:3]:
            add(line)
        if len(normalized) > 14:
            add(normalized[:14])
            add(normalized[-14:])
        else:
            add(normalized)
        return candidates

    @staticmethod
    def _select_best(
        normalized_query: str, questions: list[ExamQuestion]
    ) -> tuple[ExamQuestion, float]:
        scored = [
            (
                SequenceMatcher(None, normalized_query, question.normalized_title).ratio(),
                question,
            )
            for question in questions
        ]
        score, question = max(scored, key=lambda item: item[0])
        return question, score
