from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable
from pathlib import Path

from ocr_keju.database.schema import SCHEMA_SQL
from ocr_keju.models import ExamQuestion


class QuestionRepository:
    def __init__(self, database_path: Path | str) -> None:
        self.database_path = Path(database_path)

    def initialize(self) -> None:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(SCHEMA_SQL)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def upsert_many(self, questions: Iterable[ExamQuestion]) -> int:
        rows = list(questions)
        if not rows:
            return 0
        self.initialize()
        with self._connect() as connection:
            connection.executemany(
                """
                INSERT INTO questions (
                    remote_id, title, normalized_title, options_json,
                    answer_indices_json, answer_text_json, is_right, source
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'jx3box')
                ON CONFLICT(remote_id) DO UPDATE SET
                    title = excluded.title,
                    normalized_title = excluded.normalized_title,
                    options_json = excluded.options_json,
                    answer_indices_json = excluded.answer_indices_json,
                    answer_text_json = excluded.answer_text_json,
                    is_right = excluded.is_right,
                    source = excluded.source,
                    updated_at = CURRENT_TIMESTAMP
                """,
                [
                    (
                        question.remote_id,
                        question.title,
                        question.normalized_title,
                        json.dumps(question.options, ensure_ascii=False),
                        json.dumps(question.answer_indices),
                        json.dumps(question.answer_text, ensure_ascii=False),
                        None if question.is_right is None else int(question.is_right),
                    )
                    for question in rows
                ],
            )
        return len(rows)

    def upsert_user_question(self, question: ExamQuestion) -> None:
        if not question.normalized_title:
            raise ValueError("用户题目不能为空")
        self.initialize()
        with self._connect() as connection:
            existing = connection.execute(
                """
                SELECT id FROM questions
                WHERE source = 'user' AND normalized_title = ?
                LIMIT 1
                """,
                (question.normalized_title,),
            ).fetchone()
            values = (
                question.title,
                question.normalized_title,
                json.dumps(question.options, ensure_ascii=False),
                json.dumps(question.answer_indices),
                json.dumps(question.answer_text, ensure_ascii=False),
                None if question.is_right is None else int(question.is_right),
            )
            if existing is None:
                connection.execute(
                    """
                    INSERT INTO questions (
                        remote_id, title, normalized_title, options_json,
                        answer_indices_json, answer_text_json, is_right, source
                    ) VALUES (NULL, ?, ?, ?, ?, ?, ?, 'user')
                    """,
                    values,
                )
            else:
                connection.execute(
                    """
                    UPDATE questions SET
                        title = ?, normalized_title = ?, options_json = ?,
                        answer_indices_json = ?, answer_text_json = ?, is_right = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (*values, existing["id"]),
                )

    def find_exact(self, normalized_title: str) -> ExamQuestion | None:
        self.initialize()
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM questions
                WHERE normalized_title = ?
                ORDER BY CASE WHEN source = 'user' THEN 0 ELSE 1 END,
                         updated_at DESC, id DESC
                LIMIT 1
                """,
                (normalized_title,),
            ).fetchone()
            if row is None:
                return None
            connection.execute(
                "UPDATE questions SET hit_count = hit_count + 1 WHERE id = ?",
                (row["id"],),
            )
        return self._row_to_question(row)

    def list_all(self) -> list[ExamQuestion]:
        self.initialize()
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM questions
                ORDER BY CASE WHEN source = 'user' THEN 0 ELSE 1 END, id ASC
                """
            ).fetchall()
        return [self._row_to_question(row) for row in rows]

    def increment_hit(self, remote_id: int | None) -> None:
        if remote_id is None:
            return
        with self._connect() as connection:
            connection.execute(
                "UPDATE questions SET hit_count = hit_count + 1 WHERE remote_id = ?",
                (remote_id,),
            )

    def count(self) -> int:
        self.initialize()
        with self._connect() as connection:
            row = connection.execute("SELECT COUNT(*) AS total FROM questions").fetchone()
        return int(row["total"])

    @staticmethod
    def _row_to_question(row: sqlite3.Row) -> ExamQuestion:
        is_right_value = row["is_right"]
        return ExamQuestion(
            remote_id=row["remote_id"],
            title=row["title"],
            normalized_title=row["normalized_title"],
            options=tuple(json.loads(row["options_json"])),
            answer_indices=tuple(int(value) for value in json.loads(row["answer_indices_json"])),
            answer_text=tuple(json.loads(row["answer_text_json"])),
            is_right=None if is_right_value is None else bool(is_right_value),
        )
