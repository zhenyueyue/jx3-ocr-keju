import json

import httpx

from ocr_keju.api import JX3BoxExamClient


def test_client_parses_exam_payload() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["search"] == "测试题目"
        return httpx.Response(
            200,
            json={
                "code": 0,
                "msg": "ok",
                "data": [
                    {
                        "id": 100,
                        "title": "单选题：测试题目？",
                        "options": json.dumps(["错误", "正确"], ensure_ascii=False),
                        "answer": "[1]",
                        "isRight": False,
                    }
                ],
            },
        )

    transport = httpx.MockTransport(handler)
    with JX3BoxExamClient(transport=transport) as client:
        questions = client.search("测试题目")

    assert len(questions) == 1
    question = questions[0]
    assert question.remote_id == 100
    assert question.normalized_title == "测试题目"
    assert question.answer_indices == (1,)
    assert question.answer_text == ("正确",)
