from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


QuestionSource = Literal["local", "jx3box"]


@dataclass(frozen=True, slots=True)
class ExamQuestion:
    remote_id: int | None
    title: str
    normalized_title: str
    options: tuple[str, ...]
    answer_indices: tuple[int, ...]
    answer_text: tuple[str, ...]
    is_right: bool | None = None


@dataclass(frozen=True, slots=True)
class SearchResult:
    question: ExamQuestion
    source: QuestionSource
    confidence: float
