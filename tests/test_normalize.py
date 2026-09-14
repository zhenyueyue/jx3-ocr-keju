from ocr_keju.question import normalize_question


def test_normalize_removes_question_prefix_whitespace_and_punctuation() -> None:
    assert normalize_question(" 单选题： 稻香村 的村长是谁？ ") == "稻香村的村长是谁"


def test_normalize_applies_nfkc() -> None:
    assert normalize_question("ＡＢＣ １２３") == "abc123"
