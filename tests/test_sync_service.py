from ocr_keju.database import QuestionRepository
from ocr_keju.models import ExamQuestion
from ocr_keju.sync import QuestionBankSyncService


class FakeApiClient:
    def search(self, query: str) -> list[ExamQuestion]:
        assert query == "单选题"
        return [
            ExamQuestion(
                remote_id=1,
                title="单选题：第一题？",
                normalized_title="第一题",
                options=("A",),
                answer_indices=(0,),
                answer_text=("A",),
                is_right=True,
            ),
            ExamQuestion(
                remote_id=2,
                title="单选题：第二题？",
                normalized_title="第二题",
                options=("B",),
                answer_indices=(0,),
                answer_text=("B",),
                is_right=True,
            ),
        ]


def test_sync_service_populates_repository(tmp_path) -> None:
    repository = QuestionRepository(tmp_path / "questions.db")
    report = QuestionBankSyncService(repository, FakeApiClient()).sync()  # type: ignore[arg-type]

    assert report.fetched == 2
    assert report.stored == 2
    assert report.local_total == 2
    assert repository.count() == 2
