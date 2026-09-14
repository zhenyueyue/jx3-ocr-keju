from __future__ import annotations

import json
from collections.abc import Iterable
from typing import Any

import httpx

from ocr_keju.api.errors import JX3BoxApiError, JX3BoxProtocolError
from ocr_keju.models import ExamQuestion
from ocr_keju.question import normalize_question


class JX3BoxExamClient:
    def __init__(
        self,
        base_url: str = "https://pull-gplugin.jx3box.com",
        timeout_seconds: float = 8.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            timeout=timeout_seconds,
            transport=transport,
            headers={
                "Accept": "application/json, text/plain, */*",
                "User-Agent": "ocr-keju/0.1 (+https://jx3box.com)",
                "Referer": "https://www.jx3box.com/",
            },
            follow_redirects=True,
        )

    def __enter__(self) -> "JX3BoxExamClient":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def close(self) -> None:
        self._client.close()

    def search(self, query: str) -> list[ExamQuestion]:
        query = query.strip()
        if not query:
            return []

        try:
            response = self._client.get("/api/exam", params={"search": query})
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise JX3BoxApiError(f"JX3BOX request failed: {exc}") from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise JX3BoxProtocolError("JX3BOX returned non-JSON content") from exc

        if not isinstance(payload, dict):
            raise JX3BoxProtocolError("JX3BOX response root is not an object")
        if payload.get("code") != 0:
            raise JX3BoxProtocolError(
                f"JX3BOX returned code={payload.get('code')!r}, msg={payload.get('msg')!r}"
            )

        data = payload.get("data")
        if data is None:
            return []
        if not isinstance(data, list):
            raise JX3BoxProtocolError("JX3BOX data field is not a list")

        return [self._parse_item(item) for item in data]

    @staticmethod
    def _parse_json_list(value: Any, field_name: str) -> list[Any]:
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except json.JSONDecodeError as exc:
                raise JX3BoxProtocolError(f"Invalid JSON in {field_name}") from exc
        if not isinstance(value, list):
            raise JX3BoxProtocolError(f"{field_name} is not a list")
        return value

    @classmethod
    def _parse_item(cls, item: Any) -> ExamQuestion:
        if not isinstance(item, dict):
            raise JX3BoxProtocolError("Question item is not an object")

        try:
            remote_id = int(item["id"])
            title = str(item["title"]).strip()
        except (KeyError, TypeError, ValueError) as exc:
            raise JX3BoxProtocolError("Question item misses a valid id/title") from exc

        options_raw = cls._parse_json_list(item.get("options"), "options")
        answers_raw = cls._parse_json_list(item.get("answer"), "answer")
        options = tuple(str(option).strip() for option in options_raw)

        answer_indices_list: list[int] = []
        for value in answers_raw:
            try:
                index = int(value)
            except (TypeError, ValueError) as exc:
                raise JX3BoxProtocolError(f"Invalid answer index: {value!r}") from exc
            if index < 0 or index >= len(options):
                raise JX3BoxProtocolError(
                    f"Answer index {index} out of range for {len(options)} options"
                )
            answer_indices_list.append(index)

        answer_indices = tuple(answer_indices_list)
        answer_text = tuple(options[index] for index in answer_indices)
        is_right_raw = item.get("isRight")
        is_right = is_right_raw if isinstance(is_right_raw, bool) else None

        return ExamQuestion(
            remote_id=remote_id,
            title=title,
            normalized_title=normalize_question(title),
            options=options,
            answer_indices=answer_indices,
            answer_text=answer_text,
            is_right=is_right,
        )
