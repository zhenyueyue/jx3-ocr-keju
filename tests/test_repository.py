from ocr_keju.database import QuestionRepository
from ocr_keju.matching import LocalQuestionMatcher
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


def test_user_question_overrides_remote_question_and_updates_in_place(tmp_path) -> None:
    repository = QuestionRepository(tmp_path / "questions.db")
    remote = ExamQuestion(
        remote_id=321,
        title="单选题：同一道题？",
        normalized_title="同一道题",
        options=("远端A", "远端B"),
        answer_indices=(0,),
        answer_text=("远端A",),
        is_right=True,
    )
    user = ExamQuestion(
        remote_id=None,
        title="同一道题？",
        normalized_title="同一道题",
        options=("用户A", "用户B"),
        answer_indices=(1,),
        answer_text=("用户B",),
        is_right=True,
    )
    repository.upsert_many([remote])
    repository.upsert_user_question(user)

    matcher = LocalQuestionMatcher(repository.list_all())
    assert matcher.exact("同一道题") == user

    corrected = ExamQuestion(
        remote_id=None,
        title="同一道题？",
        normalized_title="同一道题",
        options=("用户A", "用户B"),
        answer_indices=(0,),
        answer_text=("用户A",),
        is_right=True,
    )
    repository.upsert_user_question(corrected)

    assert repository.count() == 2
    assert LocalQuestionMatcher(repository.list_all()).exact("同一道题") == corrected
