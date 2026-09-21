from __future__ import annotations

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget

from ocr_keju.capture import CaptureRegion
from ocr_keju.pipeline import AnswerBox, RecognitionOutcome


class AnswerOverlay(QWidget):
    """Transparent click-through overlay that outlines the correct option in-place."""

    def __init__(self) -> None:
        super().__init__(None)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowTransparentForInput
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._rects: list[QRect] = []
        self._status_text = ""

    def show_outcome(self, outcome: RecognitionOutcome, region: CaptureRegion) -> None:
        if outcome.match is None or not outcome.answer_boxes:
            self.hide()
            return
        self.show_boxes(outcome.answer_boxes, region)

    def show_box(self, box: AnswerBox, region: CaptureRegion) -> None:
        self.show_boxes((box,), region)

    def show_boxes(self, boxes: tuple[AnswerBox, ...], region: CaptureRegion) -> None:
        if not boxes:
            self.hide()
            return

        global_rects = [
            QRect(
                region.left + box.left,
                region.top + box.top,
                box.width,
                box.height,
            )
            for box in boxes
        ]
        bounds = global_rects[0]
        for rect in global_rects[1:]:
            bounds = bounds.united(rect)
        bounds = bounds.adjusted(-8, -8, 8, 8)

        self._status_text = ""
        self._rects = [rect.translated(-bounds.left(), -bounds.top()) for rect in global_rects]
        self.setGeometry(bounds)
        self.show()
        self.raise_()
        self.update()

    def show_detecting(self, region: CaptureRegion) -> None:
        self._rects.clear()
        self._status_text = "检测到新题 · 识别中…"
        width = 190
        height = 34
        top = region.top - height - 8
        if top < 0:
            top = region.top + region.height + 8
        self.setGeometry(region.left, top, width, height)
        self.show()
        self.raise_()
        self.update()

    def show_message(self, region: CaptureRegion, text: str) -> None:
        self._rects.clear()
        self._status_text = text
        width = 220
        height = 34
        top = region.top - height - 8
        if top < 0:
            top = region.top + region.height + 8
        self.setGeometry(region.left, top, width, height)
        self.show()
        self.raise_()
        self.update()

    def clear(self) -> None:
        self._rects.clear()
        self._status_text = ""
        self.hide()

    def paintEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        if not self._rects and not self._status_text:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        if self._status_text:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(20, 23, 30, 230))
            painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 8, 8)
            painter.setPen(QColor(255, 199, 72, 255))
            font = QFont("Microsoft YaHei UI", 10)
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(
                self.rect().adjusted(12, 0, -8, 0),
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                self._status_text,
            )
            return

        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QColor(55, 230, 125, 245), 4))
        for rect in self._rects:
            painter.drawRoundedRect(rect, 7, 7)
