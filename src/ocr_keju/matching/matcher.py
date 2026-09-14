from __future__ import annotations

from dataclasses import dataclass

from rapidfuzz import fuzz, process

from ocr_keju.models import ExamQuestion


@dataclass(frozen=True, slots=True)
class MatchCandidate:
    question: ExamQuestion
    confidence: float


class LocalQuestionMatcher:
    """Fast in-memory fuzzy matcher for the small local question bank."""

    def __init__(self, questions: list[ExamQuestion]) -> None:
        self.questions = questions
        self._choices = {
            index: question.normalized_title
            for index, question in enumerate(questions)
            if question.normalized_title
        }

    def best(self, normalized_query: str) -> MatchCandidate | None:
        if not normalized_query or not self._choices:
            return None
        match = process.extractOne(
            normalized_query,
            self._choices,
            scorer=fuzz.ratio,
            score_cutoff=0,
        )
        if match is None:
            return None
        _, score, index = match
        return MatchCandidate(
            question=self.questions[int(index)],
            confidence=float(score) / 100.0,
        )
