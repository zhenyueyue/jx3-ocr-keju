from pathlib import Path

import numpy as np

from ocr_keju.config import Settings
from ocr_keju.database import QuestionRepository
from ocr_keju.models import ExamQuestion
from ocr_keju.ocr import OcrLine, OcrResult
from ocr_keju.pipeline import RecognitionPipeline


class FakeOcrEngine:
    def recognize(self, image: np.ndarray) -> OcrResult:
        return OcrResult(
            text="稻香村的村长是谁？\nA. 刘洋\nB. 王遗风",
            lines=(
                OcrLine("稻香村的村长是谁？", 0.98, ((20, 20), (240, 20), (240, 50), (20, 50))),
                OcrLine("A. 刘洋", 0.97, ((30, 90), (150, 90), (150, 120), (30, 120))),
                OcrLine("B. 王遗风", 0.97, ((30, 140), (180, 140), (180, 170), (30, 170))),
            ),
            mean_score=0.97,
            elapsed_seconds=0.1,
        )


def test_pipeline_locates_correct_answer_box_from_full_region(tmp_path, monkeypatch) -> None:
    repository = QuestionRepository(tmp_path / "questions.db")
    repository.upsert_many(
        [
            ExamQuestion(
                remote_id=10,
                title="单选题：稻香村的村长是谁？",
                normalized_title="稻香村的村长是谁",
                options=("刘洋", "王遗风"),
                answer_indices=(0,),
                answer_text=("刘洋",),
                is_right=True,
            )
        ]
    )
    settings = Settings(data_dir=Path(tmp_path), database_path=tmp_path / "questions.db")
    pipeline = RecognitionPipeline(settings, repository, FakeOcrEngine())  # type: ignore[arg-type]
    image = np.zeros((300, 500, 3), dtype=np.uint8)

    outcome = pipeline.recognize(image)

    assert outcome.match is not None
    assert outcome.answer_boxes
    box = outcome.answer_boxes[0]
    assert box.text == "A. 刘洋"
    assert box.top < 100
    assert box.confidence >= 0.9
