from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ocr_keju.capture import CaptureRegion
from ocr_keju.pipeline import RecognitionOutcome


class MainWindow(QMainWindow):
    select_region_requested = Signal()
    recognize_requested = Signal()
    monitor_toggle_requested = Signal()
    sync_requested = Signal()
    closing = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("OCR 科举助手")
        self.resize(760, 590)
        self.setMinimumSize(680, 520)
        self._build_ui()
        self._apply_style()

    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(14)

        title = QLabel("OCR 科举助手")
        title.setObjectName("title")
        subtitle = QLabel("实时 OCR · 自动检测新题目 · 正确选项原位描边")
        subtitle.setObjectName("muted")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        status_card = QFrame()
        status_card.setObjectName("card")
        status_layout = QHBoxLayout(status_card)
        status_layout.setContentsMargins(16, 12, 16, 12)
        self.bank_label = QLabel("本地题库：-")
        self.region_label = QLabel("检测区域：未设置")
        self.monitor_label = QLabel("实时检测：等待框选")
        status_layout.addWidget(self.bank_label)
        status_layout.addStretch(1)
        status_layout.addWidget(self.region_label)
        status_layout.addStretch(1)
        status_layout.addWidget(self.monitor_label)
        layout.addWidget(status_card)

        buttons = QHBoxLayout()
        self.select_button = QPushButton("框选题目 + 选项区域")
        self.monitor_button = QPushButton("暂停实时检测")
        self.monitor_button.setObjectName("primaryButton")
        self.recognize_button = QPushButton("立即检测")
        self.sync_button = QPushButton("同步题库")
        buttons.addWidget(self.select_button)
        buttons.addWidget(self.monitor_button)
        buttons.addWidget(self.recognize_button)
        buttons.addWidget(self.sync_button)
        buttons.addStretch(1)
        layout.addLayout(buttons)

        self.status_label = QLabel("就绪")
        self.status_label.setObjectName("muted")
        layout.addWidget(self.status_label)

        answer_card = QFrame()
        answer_card.setObjectName("card")
        answer_layout = QVBoxLayout(answer_card)
        answer_layout.setContentsMargins(18, 16, 18, 16)
        answer_caption = QLabel("答案")
        answer_caption.setObjectName("muted")
        self.answer_label = QLabel("等待识别")
        self.answer_label.setObjectName("answer")
        self.answer_label.setWordWrap(True)
        self.match_label = QLabel("")
        self.match_label.setWordWrap(True)
        self.meta_label = QLabel("")
        self.meta_label.setObjectName("muted")
        answer_layout.addWidget(answer_caption)
        answer_layout.addWidget(self.answer_label)
        answer_layout.addWidget(self.match_label)
        answer_layout.addWidget(self.meta_label)
        layout.addWidget(answer_card)

        ocr_caption = QLabel("OCR 原文")
        ocr_caption.setObjectName("muted")
        self.ocr_text = QTextEdit()
        self.ocr_text.setReadOnly(True)
        self.ocr_text.setPlaceholderText("识别后的题目文字会显示在这里")
        self.ocr_text.setMinimumHeight(150)
        layout.addWidget(ocr_caption)
        layout.addWidget(self.ocr_text, 1)

        self.select_button.clicked.connect(self.select_region_requested.emit)
        self.monitor_button.clicked.connect(self.monitor_toggle_requested.emit)
        self.recognize_button.clicked.connect(self.recognize_requested.emit)
        self.sync_button.clicked.connect(self.sync_requested.emit)

    def _apply_style(self) -> None:
        self.setStyleSheet(
            """
            QMainWindow, QWidget {
                background: #11151d;
                color: #eef2f8;
                font-family: "Microsoft YaHei UI", "Segoe UI";
                font-size: 13px;
            }
            QLabel#title { font-size: 28px; font-weight: 700; }
            QLabel#muted { color: #98a2b3; }
            QLabel#answer { font-size: 28px; font-weight: 700; color: #ffffff; }
            QFrame#card {
                background: #181e28;
                border: 1px solid #252d3a;
                border-radius: 12px;
            }
            QPushButton {
                background: #202735;
                border: 1px solid #313b4d;
                border-radius: 8px;
                padding: 9px 15px;
            }
            QPushButton:hover { background: #283244; }
            QPushButton:disabled { color: #667085; background: #181e28; }
            QPushButton#primaryButton {
                background: #2f6fed;
                border-color: #2f6fed;
                font-weight: 600;
            }
            QPushButton#primaryButton:hover { background: #3d7af0; }
            QTextEdit {
                background: #0d1118;
                border: 1px solid #252d3a;
                border-radius: 10px;
                padding: 10px;
                selection-background-color: #2f6fed;
            }
            """
        )

    def set_bank_count(self, count: int) -> None:
        self.bank_label.setText(f"本地题库：{count}")

    def set_monitoring(self, enabled: bool, configured: bool) -> None:
        if not configured:
            self.monitor_label.setText("实时检测：等待框选")
            self.monitor_button.setText("开启实时检测")
            self.monitor_button.setDisabled(True)
            return
        self.monitor_button.setDisabled(False)
        if enabled:
            self.monitor_label.setText("实时检测：已开启")
            self.monitor_button.setText("暂停实时检测")
        else:
            self.monitor_label.setText("实时检测：已暂停")
            self.monitor_button.setText("开启实时检测")

    def set_region(self, region: CaptureRegion | None) -> None:
        if region is None:
            self.region_label.setText("检测区域：未设置")
            return
        self.region_label.setText(f"检测区域：{region.width}×{region.height}")

    def set_busy(self, busy: bool, message: str = "") -> None:
        self.recognize_button.setDisabled(busy)
        self.monitor_button.setDisabled(busy)
        self.sync_button.setDisabled(busy)
        self.select_button.setDisabled(busy)
        if message:
            self.status_label.setText(message)

    def show_status(self, message: str) -> None:
        self.status_label.setText(message)

    def show_outcome(self, outcome: RecognitionOutcome) -> None:
        self.ocr_text.setPlainText(outcome.ocr.text)
        if outcome.match is None:
            self.answer_label.setText("未找到答案")
            self.match_label.setText(outcome.warning)
            self.meta_label.setText(
                f"OCR 置信度 {outcome.ocr.mean_score:.0%} · {outcome.ocr.elapsed_seconds * 1000:.0f} ms"
            )
            return

        result = outcome.match
        self.answer_label.setText(" / ".join(result.question.answer_text) or "未解析到答案")
        self.match_label.setText(result.question.title)
        self.meta_label.setText(
            f"来源 {result.source} · 匹配 {result.confidence:.0%} · "
            f"OCR {outcome.ocr.mean_score:.0%} · {outcome.ocr.elapsed_seconds * 1000:.0f} ms"
        )

    def closeEvent(self, event: QCloseEvent) -> None:
        self.closing.emit()
        super().closeEvent(event)
