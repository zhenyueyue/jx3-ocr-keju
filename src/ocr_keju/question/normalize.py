from __future__ import annotations

import re
import unicodedata


_PREFIX_RE = re.compile(
    r"^\s*(?:\[?\s*)?(?:单选题|多选题|选择题|判断题|题目)(?:\s*\]?)\s*[:：、.．-]*\s*",
    re.IGNORECASE,
)
_WHITESPACE_RE = re.compile(r"\s+")
_PUNCTUATION_RE = re.compile(r"[，。！？；：、,.!?;:'\"“”‘’（）()【】\[\]《》<>·…—_\-]+")


def normalize_question(text: str) -> str:
    """Normalize OCR/API question text for deterministic lookup.

    This intentionally keeps letters, digits and CJK characters while removing
    presentation-only differences such as whitespace, punctuation and common
    question-type prefixes.
    """

    value = unicodedata.normalize("NFKC", text or "")
    value = _PREFIX_RE.sub("", value)
    value = _WHITESPACE_RE.sub("", value)
    value = _PUNCTUATION_RE.sub("", value)
    return value.casefold().strip()
