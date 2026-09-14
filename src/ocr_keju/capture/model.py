from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class CaptureRegion:
    left: int
    top: int
    width: int
    height: int
    screen_name: str = ""

    @property
    def is_valid(self) -> bool:
        return self.width >= 20 and self.height >= 20

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any] | None) -> "CaptureRegion | None":
        if not value:
            return None
        try:
            region = cls(
                left=int(value["left"]),
                top=int(value["top"]),
                width=int(value["width"]),
                height=int(value["height"]),
                screen_name=str(value.get("screen_name", "")),
            )
        except (KeyError, TypeError, ValueError):
            return None
        return region if region.is_valid else None
