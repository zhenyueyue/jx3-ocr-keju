from ocr_keju.database import QuestionRepository
from ocr_keju.models import ExamQuestion


def test_repository_upserts_and_finds_exact(tmp_path) -> None:
    repository = QuestionRepository(tmp_path / "questions.db")
    question = ExamQuestion(
        remote_id=123,
        title="题目？",
        normalized_title="题目",
        options=("A", "B"),
        answer_indices=(1,),
        answer_text=("B",),
        is_right=True,
    )

    assert repository.upsert_many([question]) == 1
    assert repository.count() == 1
    loaded = repository.find_exact("题目")

    assert loaded == question
