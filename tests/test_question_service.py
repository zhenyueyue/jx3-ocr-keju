from ocr_keju.database import QuestionRepository
from ocr_keju.models import ExamQuestion
from ocr_keju.services import QuestionService


class FakeApiClient:
    def __init__(self, questions: list[ExamQuestion]) -> None:
        self.questions = questions
        self.calls: list[str] = []

    def search(self, query: str) -> list[ExamQuestion]:
        self.calls.append(query)
        return self.questions


def test_service_caches_remote_result_and_uses_local_next_time(tmp_path) -> None:
    repository = QuestionRepository(tmp_path / "questions.db")
    remote_question = ExamQuestion(
        remote_id=7,
        title="单选题：稻香村的村长是谁？",
        normalized_title="稻香村的村长是谁",
        options=("刘洋", "王遗风"),
        answer_indices=(0,),
        answer_text=("刘洋",),
        is_right=True,
    )
    api = FakeApiClient([remote_question])
    service = QuestionService(repository, api)  # type: ignore[arg-type]

    first = service.resolve("稻香村的村长是谁？")
    second = service.resolve("单选题：稻香村的村长是谁")

    assert first is not None and first.source == "jx3box"
    assert second is not None and second.source == "local"
    assert api.calls == ["稻香村的村长是谁？"]
    assert repository.count() == 1


def test_service_uses_fuzzy_local_match_for_small_ocr_error(tmp_path) -> None:
    repository = QuestionRepository(tmp_path / "questions.db")
    repository.upsert_many(
        [
            ExamQuestion(
                remote_id=8,
                title="单选题：稻香村的村长是谁？",
                normalized_title="稻香村的村长是谁",
                options=("刘洋",),
                answer_indices=(0,),
                answer_text=("刘洋",),
                is_right=True,
            )
        ]
    )
    api = FakeApiClient([])
    service = QuestionService(repository, api)  # type: ignore[arg-type]

    result = service.resolve("稻香衬的村长是谁")

    assert result is not None
    assert result.source == "local"
    assert result.confidence >= 0.78
    assert api.calls == []


def test_service_extracts_question_from_ocr_lines_with_options(tmp_path) -> None:
    repository = QuestionRepository(tmp_path / "questions.db")
    repository.upsert_many(
        [
            ExamQuestion(
                remote_id=9,
                title="单选题：稻香村的村长是谁？",
                normalized_title="稻香村的村长是谁",
                options=("刘洋", "王遗风", "李复"),
                answer_indices=(0,),
                answer_text=("刘洋",),
                is_right=True,
            )
        ]
    )
    api = FakeApiClient([])
    service = QuestionService(repository, api)  # type: ignore[arg-type]

    resolution = service.resolve_ocr_lines(("稻香衬的村长是谁?", "A. 刘洋", "B. 王遗风", "C. 李复"))

    assert resolution.result is not None
    assert resolution.result.question.remote_id == 9
    assert resolution.question_line_count == 1
    assert api.calls == []


def test_remote_queries_include_long_ocr_line() -> None:
    queries = QuestionService._remote_queries(
        "以下哪个江湖势力曾派人到稻香村\n《空冥诀》的消息？",
        "以下哪个江湖势力曾派人到稻香村空冥诀的消息",
    )

    assert "以下哪个江湖势力曾派人到稻香村" in queries
    assert queries[0].count("\n") == 1
