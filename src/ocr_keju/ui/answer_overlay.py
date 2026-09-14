from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout

from ocr_keju.pipeline import RecognitionOutcome


class AnswerOverlay(QFrame):
    def __init__(self) -> None:
        super().__init__(None)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setObjectName("answerOverlay")
        self.setStyleSheet(
            """
            QFrame#answerOverlay {
                background: rgba(20, 23, 30, 235);
                border: 1px solid rgba(255, 255, 255, 35);
                border-radius: 12px;
            }
            QLabel { color: #f5f7fb; }
            QLabel#overlayAnswer { font-size: 24px; font-weight: 700; }
            QLabel#overlayMeta { color: #a9b0be; font-size: 12px; }
            """
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(6)
        self.answer_label = QLabel("-")
        self.answer_label.setObjectName("overlayAnswer")
        self.answer_label.setWordWrap(True)
        self.meta_label = QLabel("")
        self.meta_label.setObjectName("overlayMeta")
        layout.addWidget(self.answer_label)
        layout.addWidget(self.meta_label)
        self.setMinimumWidth(320)
        self.setMaximumWidth(560)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.hide)

    def show_outcome(self, outcome: RecognitionOutcome, timeout_ms: int) -> None:
        if outcome.match is None:
            return
        result = outcome.match
        answer = " / ".join(result.question.answer_text) or "未解析到答案"
        self.answer_label.setText(answer)
        self.meta_label.setText(
            f"{result.source} · 匹配 {result.confidence:.0%} · OCR {outcome.ocr.mean_score:.0%}"
        )
        self.adjustSize()
        screen = QGuiApplication.screenAt(QGuiApplication.primaryScreen().geometry().center())
        if screen is None:
            screen = QGuiApplication.primaryScreen()
        if screen is not None:
            area = screen.availableGeometry()
            self.move(
                area.right() - self.width() - 24,
                area.top() + 24,
            )
        self.show()
        self.raise_()
        self._timer.start(max(1000, timeout_ms))
