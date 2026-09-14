from __future__ import annotations

from dataclasses import dataclass

from ocr_keju.api.client import JX3BoxExamClient
from ocr_keju.database.repository import QuestionRepository


DEFAULT_SYNC_QUERIES = ("单选题",)


@dataclass(frozen=True, slots=True)
class SyncReport:
    fetched: int
    stored: int
    local_total: int


class QuestionBankSyncService:
    """Populate the local bank through stable broad searches on the pull API."""

    def __init__(self, repository: QuestionRepository, api_client: JX3BoxExamClient) -> None:
        self.repository = repository
        self.api_client = api_client

    def sync(self, queries: tuple[str, ...] = DEFAULT_SYNC_QUERIES) -> SyncReport:
        by_remote_id = {}
        for query in queries:
            for question in self.api_client.search(query):
                if question.remote_id is not None:
                    by_remote_id[question.remote_id] = question

        questions = list(by_remote_id.values())
        stored = self.repository.upsert_many(questions)
        return SyncReport(
            fetched=len(questions),
            stored=stored,
            local_total=self.repository.count(),
        )
