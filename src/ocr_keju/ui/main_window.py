from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QEvent, Property, QPropertyAnimation, Qt, Signal
from PySide6.QtGui import QColor, QCloseEvent, QFont, QMouseEvent, QPainter
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSizeGrip,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ocr_keju.capture import CaptureRegion
from ocr_keju.pipeline import PendingQuestion, RecognitionOutcome


class WindowControlButton(QPushButton):
    def __init__(self, symbol: str, role: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._role = role
        self._hover_progress = 0.0
        self._animation = QPropertyAnimation(self, b"hoverProgress", self)
        self._animation.setDuration(140)
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.setText(symbol)
        self.setFixedSize(40, 30)
        self.setFlat(True)
        self.setProperty("windowControl", True)
        self.setCursor(Qt.CursorShape.ArrowCursor)
        font = QFont("Segoe UI Symbol", 10)
        if role == "close":
            font.setPointSize(13)
        self.setFont(font)

    def _get_hover_progress(self) -> float:
        return self._hover_progress

    def _set_hover_progress(self, value: float) -> None:
        self._hover_progress = value
        self.update()

    hoverProgress = Property(float, _get_hover_progress, _set_hover_progress)

    def _animate_to(self, value: float) -> None:
        self._animation.stop()
        self._animation.setStartValue(self._hover_progress)
        self._animation.setEndValue(value)
        self._animation.start()

    def enterEvent(self, event: QEvent) -> None:
        self._animate_to(1.0)
        super().enterEvent(event)

    def leaveEvent(self, event: QEvent) -> None:
        self._animate_to(0.0)
        super().leaveEvent(event)

    def paintEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        progress = self._hover_progress
        if self.isDown():
            progress = 1.0

        if self._role == "close":
            hover = QColor(196, 48, 58)
            pressed = QColor(173, 38, 48)
        else:
            hover = QColor(40, 48, 61)
            pressed = QColor(48, 58, 73)

        target = pressed if self.isDown() else hover
        background = QColor(
            target.red(),
            target.green(),
            target.blue(),
            int(255 * progress),
        )
        if progress > 0:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(background)
            painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 5, 5)

        color = QColor(223, 229, 237)
        if self._role == "close" and progress > 0.35:
            color = QColor(255, 255, 255)
        painter.setPen(color)
        painter.setFont(self.font())
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self.text())


class TitleBar(QWidget):
    def __init__(self, window: "MainWindow") -> None:
        super().__init__(window)
        self._window = window
        self._drag_global = None
        self._window_origin = None
        self.setObjectName("titleBar")
        self.setFixedHeight(52)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 8, 10, 8)
        layout.setSpacing(9)

        app_mark = QLabel("科")
        app_mark.setObjectName("appMark")
        app_mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        app_mark.setFixedSize(28, 28)

        title_block = QVBoxLayout()
        title_block.setSpacing(0)
        title = QLabel("科举助手")
        title.setObjectName("windowTitle")
        subtitle = QLabel("JX3 OCR")
        subtitle.setObjectName("windowSubtitle")
        title_block.addWidget(title)
        title_block.addWidget(subtitle)

        self.state_label = QLabel("实时检测")
        self.state_label.setObjectName("stateBadge")
        self.state_label.setProperty("state", "idle")
        self.state_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.minimize_button = WindowControlButton("—", "minimize", self)
        self.maximize_button = WindowControlButton("▢", "maximize", self)
        self.close_button = WindowControlButton("×", "close", self)

        self.minimize_button.setToolTip("最小化")
        self.maximize_button.setToolTip("最大化")
        self.close_button.setToolTip("关闭")

        self.minimize_button.clicked.connect(window.showMinimized)
        self.maximize_button.clicked.connect(window.toggle_maximized)
        self.close_button.clicked.connect(window.close)

        layout.addWidget(app_mark)
        layout.addLayout(title_block)
        layout.addStretch(1)
        layout.addWidget(self.state_label)
        layout.addSpacing(4)
        layout.addWidget(self.minimize_button)
        layout.addWidget(self.maximize_button)
        layout.addWidget(self.close_button)

    def set_maximized(self, maximized: bool) -> None:
        self.maximize_button.setText("❐" if maximized else "▢")
        self.maximize_button.setToolTip("还原" if maximized else "最大化")

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_global = event.globalPosition().toPoint()
            self._window_origin = self._window.frameGeometry().topLeft()
            handle = self._window.windowHandle()
            if handle is not None and handle.startSystemMove():
                self._drag_global = None
                self._window_origin = None
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if (
            self._drag_global is not None
            and self._window_origin is not None
            and event.buttons() & Qt.MouseButton.LeftButton
            and not self._window.isMaximized()
        ):
            delta = event.globalPosition().toPoint() - self._drag_global
            self._window.move(self._window_origin + delta)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._drag_global = None
        self._window_origin = None
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._window.toggle_maximized()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)


class MainWindow(QMainWindow):
    select_region_requested = Signal()
    recognize_requested = Signal()
    monitor_toggle_requested = Signal()
    sync_requested = Signal()
    pending_answer_selected = Signal(int)
    closing = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("OCR 科举助手")
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.resize(980, 650)
        self.setMinimumSize(860, 570)
        self._ocr_expanded = False
        self._monitor_configured = False
        self._build_ui()
        self._apply_style()
        self._sync_window_state()

    def _build_ui(self) -> None:
        root = QWidget()
        root.setObjectName("windowFrame")
        root.setProperty("maximized", False)
        self._window_frame = root
        self.setCentralWidget(root)

        shell = QVBoxLayout(root)
        shell.setContentsMargins(1, 1, 1, 1)
        shell.setSpacing(0)

        self.title_bar = TitleBar(self)
        self.header_state = self.title_bar.state_label
        shell.addWidget(self.title_bar)

        content_root = QWidget()
        content_root.setObjectName("contentRoot")
        shell.addWidget(content_root, 1)

        page = QVBoxLayout(content_root)
        page.setContentsMargins(22, 14, 22, 18)
        page.setSpacing(14)

        body = QHBoxLayout()
        body.setSpacing(14)

        # Left: controls and compact system state.
        left_panel = QFrame()
        left_panel.setObjectName("sidePanel")
        left_panel.setFixedWidth(292)
        left = QVBoxLayout(left_panel)
        left.setContentsMargins(16, 16, 16, 16)
        left.setSpacing(12)

        control_title = QLabel("实时检测")
        control_title.setObjectName("sectionTitle")
        control_hint = QLabel("框选一次题目与选项区域，之后自动跟随换题。")
        control_hint.setObjectName("hint")
        control_hint.setWordWrap(True)
        left.addWidget(control_title)
        left.addWidget(control_hint)

        self.monitor_button = QPushButton("暂停实时检测")
        self.monitor_button.setObjectName("primaryButton")
        self.monitor_button.setMinimumHeight(42)
        left.addWidget(self.monitor_button)

        self.select_button = QPushButton("重新框选识别区域")
        self.select_button.setObjectName("secondaryButton")
        self.select_button.setMinimumHeight(38)
        left.addWidget(self.select_button)

        actions = QHBoxLayout()
        actions.setSpacing(8)
        self.recognize_button = QPushButton("立即检测")
        self.recognize_button.setObjectName("quietButton")
        self.sync_button = QPushButton("同步题库")
        self.sync_button.setObjectName("quietButton")
        actions.addWidget(self.recognize_button)
        actions.addWidget(self.sync_button)
        left.addLayout(actions)

        divider = QFrame()
        divider.setObjectName("divider")
        divider.setFixedHeight(1)
        left.addWidget(divider)

        info_title = QLabel("运行状态")
        info_title.setObjectName("sectionTitle")
        left.addWidget(info_title)

        self.monitor_state_label = self._make_status_row(
            left,
            "检测",
            "等待框选",
            "monitorStateValue",
        )
        self.bank_value = self._make_status_row(
            left,
            "题库",
            "—",
            "statusValue",
        )
        self.region_value = self._make_status_row(
            left,
            "区域",
            "未设置",
            "statusValue",
        )

        left.addStretch(1)

        side_note = QLabel("提示：框选范围越紧凑，OCR 越快。")
        side_note.setObjectName("footnote")
        side_note.setWordWrap(True)
        left.addWidget(side_note)

        body.addWidget(left_panel)

        # Right: current answer first, details second.
        content = QVBoxLayout()
        content.setSpacing(12)

        answer_card = QFrame()
        answer_card.setObjectName("answerCard")
        answer_layout = QVBoxLayout(answer_card)
        answer_layout.setContentsMargins(20, 18, 20, 18)
        answer_layout.setSpacing(8)

        answer_top = QHBoxLayout()
        answer_caption = QLabel("当前答案")
        answer_caption.setObjectName("eyebrow")
        self.answer_status = QLabel("等待题目")
        self.answer_status.setObjectName("miniBadge")
        answer_top.addWidget(answer_caption)
        answer_top.addStretch(1)
        answer_top.addWidget(self.answer_status)

        self.answer_label = QLabel("等待识别")
        self.answer_label.setObjectName("answer")
        self.answer_label.setWordWrap(True)

        self.match_label = QLabel("打开科举界面后，程序会自动识别。")
        self.match_label.setObjectName("questionText")
        self.match_label.setWordWrap(True)

        self.meta_label = QLabel("")
        self.meta_label.setObjectName("meta")
        self.meta_label.setWordWrap(True)

        answer_layout.addLayout(answer_top)
        answer_layout.addWidget(self.answer_label)
        answer_layout.addWidget(self.match_label)
        answer_layout.addWidget(self.meta_label)
        content.addWidget(answer_card)

        self.pending_card = QFrame()
        self.pending_card.setObjectName("pendingCard")
        pending_layout = QVBoxLayout(self.pending_card)
        pending_layout.setContentsMargins(18, 16, 18, 16)
        pending_layout.setSpacing(9)

        pending_header = QHBoxLayout()
        pending_title = QLabel("题库未收录")
        pending_title.setObjectName("pendingTitle")
        pending_tip = QLabel("点正确答案即可保存")
        pending_tip.setObjectName("pendingTip")
        pending_header.addWidget(pending_title)
        pending_header.addStretch(1)
        pending_header.addWidget(pending_tip)

        self.pending_question_label = QLabel("")
        self.pending_question_label.setObjectName("pendingQuestion")
        self.pending_question_label.setWordWrap(True)

        self.pending_options_layout = QVBoxLayout()
        self.pending_options_layout.setSpacing(7)

        pending_layout.addLayout(pending_header)
        pending_layout.addWidget(self.pending_question_label)
        pending_layout.addLayout(self.pending_options_layout)
        self.pending_card.hide()
        content.addWidget(self.pending_card)

        detail_card = QFrame()
        detail_card.setObjectName("detailCard")
        detail_layout = QVBoxLayout(detail_card)
        detail_layout.setContentsMargins(16, 13, 16, 13)
        detail_layout.setSpacing(9)

        detail_header = QHBoxLayout()
        detail_title = QLabel("识别详情")
        detail_title.setObjectName("sectionTitle")
        self.ocr_toggle_button = QPushButton("查看 OCR 原文")
        self.ocr_toggle_button.setObjectName("linkButton")
        detail_header.addWidget(detail_title)
        detail_header.addStretch(1)
        detail_header.addWidget(self.ocr_toggle_button)

        self.ocr_text = QTextEdit()
        self.ocr_text.setObjectName("ocrText")
        self.ocr_text.setReadOnly(True)
        self.ocr_text.setPlaceholderText("识别后的原始文字会显示在这里")
        self.ocr_text.setMinimumHeight(118)
        self.ocr_text.setMaximumHeight(160)
        self.ocr_text.hide()

        detail_layout.addLayout(detail_header)
        detail_layout.addWidget(self.ocr_text)
        content.addWidget(detail_card)
        content.addStretch(1)

        body.addLayout(content, 1)
        page.addLayout(body, 1)

        status_bar = QFrame()
        status_bar.setObjectName("statusBar")
        status_layout = QHBoxLayout(status_bar)
        status_layout.setContentsMargins(12, 8, 12, 8)
        status_layout.setSpacing(8)
        self.status_dot = QLabel("●")
        self.status_dot.setObjectName("statusDot")
        self.status_label = QLabel("就绪")
        self.status_label.setObjectName("statusText")
        status_layout.addWidget(self.status_dot)
        status_layout.addWidget(self.status_label)
        status_layout.addStretch(1)
        self.size_grip = QSizeGrip(status_bar)
        self.size_grip.setObjectName("sizeGrip")
        self.size_grip.setFixedSize(14, 14)
        status_layout.addWidget(self.size_grip)
        page.addWidget(status_bar)

        self.select_button.clicked.connect(self.select_region_requested.emit)
        self.monitor_button.clicked.connect(self.monitor_toggle_requested.emit)
        self.recognize_button.clicked.connect(self.recognize_requested.emit)
        self.sync_button.clicked.connect(self.sync_requested.emit)
        self.ocr_toggle_button.clicked.connect(self._toggle_ocr_details)

    def _make_status_row(
        self,
        parent_layout: QVBoxLayout,
        label: str,
        value: str,
        object_name: str,
    ) -> QLabel:
        row = QFrame()
        row.setObjectName("statusRow")
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(11, 9, 11, 9)
        row_layout.setSpacing(8)

        name = QLabel(label)
        name.setObjectName("statusName")
        value_label = QLabel(value)
        value_label.setObjectName(object_name)
        value_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )

        row_layout.addWidget(name)
        row_layout.addStretch(1)
        row_layout.addWidget(value_label)
        parent_layout.addWidget(row)
        return value_label

    def _toggle_ocr_details(self) -> None:
        self._ocr_expanded = not self._ocr_expanded
        self.ocr_text.setVisible(self._ocr_expanded)
        self.ocr_toggle_button.setText(
            "收起 OCR 原文" if self._ocr_expanded else "查看 OCR 原文"
        )

    def _refresh_dynamic_style(self, widget: QWidget) -> None:
        style = widget.style()
        style.unpolish(widget)
        style.polish(widget)
        widget.update()

    def _apply_style(self) -> None:
        self.setStyleSheet(
            """
            QMainWindow {
                background: transparent;
            }
            QWidget#windowFrame {
                background: #0c0f14;
                color: #e9edf3;
                border: 1px solid #222b37;
                border-radius: 9px;
                font-family: "Microsoft YaHei UI", "Segoe UI";
                font-size: 13px;
            }
            QWidget#windowFrame[maximized="true"] {
                border: none;
                border-radius: 0px;
            }
            QWidget#contentRoot {
                background: transparent;
                border: none;
            }
            QWidget#titleBar {
                background: #0f141b;
                border: none;
                border-bottom: 1px solid #1b232e;
                border-top-left-radius: 9px;
                border-top-right-radius: 9px;
            }
            QWidget#windowFrame[maximized="true"] QWidget#titleBar {
                border-top-left-radius: 0px;
                border-top-right-radius: 0px;
            }
            QLabel#appMark {
                color: #ffffff;
                background: #315fbd;
                border: 1px solid #4272d2;
                border-radius: 6px;
                font-size: 14px;
                font-weight: 700;
            }
            QLabel#windowTitle {
                color: #edf1f7;
                font-size: 13px;
                font-weight: 650;
            }
            QLabel#windowSubtitle {
                color: #667284;
                font-size: 9px;
                letter-spacing: 1px;
            }
            QLabel#sectionTitle {
                color: #dce2ea;
                font-size: 13px;
                font-weight: 600;
            }
            QLabel#hint, QLabel#footnote, QLabel#meta {
                color: #778294;
                font-size: 12px;
            }
            QLabel#eyebrow {
                color: #8a95a6;
                font-size: 12px;
                font-weight: 600;
            }

            QFrame#sidePanel,
            QFrame#detailCard {
                background: #11161e;
                border: 1px solid #1c2430;
                border-radius: 8px;
            }

            QFrame#answerCard {
                background: #121821;
                border: 1px solid #253246;
                border-radius: 8px;
            }

            QLabel#answer {
                color: #ffffff;
                font-size: 32px;
                font-weight: 700;
                padding-top: 3px;
                padding-bottom: 3px;
            }
            QLabel#questionText {
                color: #c5ced9;
                font-size: 14px;
                line-height: 1.4;
            }

            QLabel#stateBadge {
                min-width: 76px;
                padding: 6px 10px;
                border-radius: 6px;
                font-size: 12px;
                font-weight: 600;
            }
            QLabel#stateBadge[state="on"] {
                color: #7ee2a8;
                background: #10231a;
                border: 1px solid #1f5637;
            }
            QLabel#stateBadge[state="off"] {
                color: #c8ced8;
                background: #181d25;
                border: 1px solid #2a3340;
            }
            QLabel#stateBadge[state="idle"] {
                color: #d6b56f;
                background: #211c12;
                border: 1px solid #55431d;
            }

            QLabel#miniBadge {
                color: #8fa0b7;
                background: #171e28;
                border: 1px solid #283344;
                border-radius: 5px;
                padding: 4px 8px;
                font-size: 11px;
            }
            QLabel#miniBadge[state="ok"] {
                color: #7ee2a8;
                background: #10231a;
                border-color: #1f5637;
            }
            QLabel#miniBadge[state="warn"] {
                color: #e8c273;
                background: #211c12;
                border-color: #55431d;
            }
            QLabel#miniBadge[state="error"] {
                color: #ef8d8d;
                background: #261416;
                border-color: #5b282d;
            }

            QFrame#statusRow {
                background: #0e131a;
                border: 1px solid #1b232e;
                border-radius: 6px;
            }
            QLabel#statusName {
                color: #707b8b;
                font-size: 12px;
            }
            QLabel#statusValue,
            QLabel#monitorStateValue {
                color: #cfd6df;
                font-size: 12px;
                font-weight: 600;
            }
            QLabel#monitorStateValue[state="on"] { color: #72d99e; }
            QLabel#monitorStateValue[state="off"] { color: #d2af68; }
            QLabel#monitorStateValue[state="idle"] { color: #7b8695; }

            QFrame#divider {
                background: #202733;
                border: none;
            }

            QPushButton {
                min-height: 34px;
                border-radius: 6px;
                padding: 0 12px;
                font-weight: 500;
            }
            QPushButton[windowControl="true"] {
                min-width: 40px;
                max-width: 40px;
                min-height: 30px;
                max-height: 30px;
                padding: 0px;
                margin: 0px;
                background: transparent;
                border: none;
            }
            QPushButton#primaryButton {
                background: #3169e6;
                color: #ffffff;
                border: 1px solid #3b73f0;
                font-weight: 600;
            }
            QPushButton#primaryButton:hover {
                background: #3a73ee;
                border-color: #4b82f4;
            }
            QPushButton#primaryButton:pressed {
                background: #2c61d5;
            }

            QPushButton#secondaryButton {
                background: #171d26;
                color: #d6dde6;
                border: 1px solid #2b3543;
            }
            QPushButton#secondaryButton:hover {
                background: #1d2530;
                border-color: #394658;
            }

            QPushButton#quietButton {
                background: #10151c;
                color: #9da8b7;
                border: 1px solid #252e3a;
            }
            QPushButton#quietButton:hover {
                color: #e0e5ec;
                background: #171d26;
                border-color: #344052;
            }

            QPushButton#linkButton {
                min-height: 26px;
                padding: 0 4px;
                background: transparent;
                border: none;
                color: #739df7;
                font-size: 12px;
            }
            QPushButton#linkButton:hover {
                color: #9bb8fa;
            }

            QPushButton:disabled {
                color: #545d6a;
                background: #11161d;
                border-color: #1d2530;
            }

            QFrame#pendingCard {
                background: #1b1710;
                border: 1px solid #574421;
                border-radius: 8px;
            }
            QLabel#pendingTitle {
                color: #f0c66a;
                font-size: 13px;
                font-weight: 700;
            }
            QLabel#pendingTip {
                color: #9c8450;
                font-size: 11px;
            }
            QLabel#pendingQuestion {
                color: #e8e0cf;
                font-size: 13px;
            }
            QPushButton#pendingOption {
                min-height: 36px;
                text-align: left;
                padding-left: 12px;
                color: #e6ddca;
                background: #221d14;
                border: 1px solid #46391f;
            }
            QPushButton#pendingOption:hover {
                color: #fff1cc;
                background: #2b2417;
                border-color: #755d2c;
            }

            QTextEdit#ocrText {
                background: #0b0f14;
                color: #aeb8c5;
                border: 1px solid #202936;
                border-radius: 6px;
                padding: 9px;
                font-family: "Cascadia Mono", "Consolas", "Microsoft YaHei UI";
                font-size: 12px;
                selection-background-color: #315fbd;
            }

            QFrame#statusBar {
                background: #0f141b;
                border: 1px solid #1b232e;
                border-radius: 6px;
            }
            QLabel#statusDot {
                color: #58c98b;
                font-size: 10px;
            }
            QLabel#statusDot[state="busy"] { color: #6f9df5; }
            QLabel#statusDot[state="warn"] { color: #d7ad58; }
            QLabel#statusDot[state="error"] { color: #e06b73; }
            QLabel#statusDot[state="ok"] { color: #58c98b; }
            QLabel#statusText {
                color: #8e99a8;
                font-size: 12px;
            }
            QSizeGrip#sizeGrip {
                background: transparent;
            }
            """
        )

    def toggle_maximized(self) -> None:
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()
        self._sync_window_state()

    def _sync_window_state(self) -> None:
        maximized = self.isMaximized()
        self._window_frame.setProperty("maximized", maximized)
        self._refresh_dynamic_style(self._window_frame)
        self.title_bar.set_maximized(maximized)
        self.size_grip.setVisible(not maximized)

    def changeEvent(self, event: QEvent) -> None:
        super().changeEvent(event)
        if event.type() == QEvent.Type.WindowStateChange:
            self._sync_window_state()

    def set_bank_count(self, count: int) -> None:
        self.bank_value.setText(f"{count} 题")

    def set_monitoring(self, enabled: bool, configured: bool) -> None:
        self._monitor_configured = configured
        if not configured:
            self.monitor_state_label.setText("等待框选")
            self.monitor_state_label.setProperty("state", "idle")
            self._refresh_dynamic_style(self.monitor_state_label)
            self.monitor_button.setText("开启实时检测")
            self.monitor_button.setDisabled(True)
            self.header_state.setText("未配置")
            self.header_state.setProperty("state", "idle")
            self._refresh_dynamic_style(self.header_state)
            return

        self.monitor_button.setDisabled(False)
        if enabled:
            self.monitor_state_label.setText("运行中")
            self.monitor_state_label.setProperty("state", "on")
            self.monitor_button.setText("暂停实时检测")
            self.header_state.setText("实时检测中")
            self.header_state.setProperty("state", "on")
        else:
            self.monitor_state_label.setText("已暂停")
            self.monitor_state_label.setProperty("state", "off")
            self.monitor_button.setText("开启实时检测")
            self.header_state.setText("已暂停")
            self.header_state.setProperty("state", "off")
        self._refresh_dynamic_style(self.monitor_state_label)
        self._refresh_dynamic_style(self.header_state)

    def set_region(self, region: CaptureRegion | None) -> None:
        if region is None:
            self.region_value.setText("未设置")
            return
        self.region_value.setText(f"{region.width} × {region.height}")

    def set_busy(self, busy: bool, message: str = "") -> None:
        self.recognize_button.setDisabled(busy)
        self.monitor_button.setDisabled(busy or not self._monitor_configured)
        self.sync_button.setDisabled(busy)
        self.select_button.setDisabled(busy)
        if message:
            self.show_status(message)

    def show_status(self, message: str) -> None:
        self.status_label.setText(message)
        if any(word in message for word in ("失败", "错误")):
            state = "error"
        elif any(word in message for word in ("未收录", "未找到", "未定位", "等待")):
            state = "warn"
        elif any(word in message for word in ("正在", "识别中", "读取")):
            state = "busy"
        else:
            state = "ok"
        self.status_dot.setProperty("state", state)
        self._refresh_dynamic_style(self.status_dot)

    def show_pending_question(self, pending: PendingQuestion) -> None:
        self.clear_pending_question()
        self.pending_question_label.setText(pending.question)
        for index, option in enumerate(pending.options):
            button = QPushButton(option.display_text)
            button.setObjectName("pendingOption")
            button.clicked.connect(
                lambda _checked=False, answer_index=index: self.pending_answer_selected.emit(
                    answer_index
                )
            )
            self.pending_options_layout.addWidget(button)
        self.pending_card.show()
        self.answer_status.setText("待补录")
        self.answer_status.setProperty("state", "warn")
        self._refresh_dynamic_style(self.answer_status)

    def clear_pending_question(self) -> None:
        while self.pending_options_layout.count():
            item = self.pending_options_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self.pending_question_label.clear()
        self.pending_card.hide()

    def show_user_answer_saved(self, question: str, answer: str) -> None:
        self.answer_label.setText(answer)
        self.match_label.setText(question)
        self.meta_label.setText("用户补录 · 已保存到本地题库")
        self.answer_status.setText("已补录")
        self.answer_status.setProperty("state", "ok")
        self._refresh_dynamic_style(self.answer_status)

    def show_outcome(self, outcome: RecognitionOutcome) -> None:
        self.ocr_text.setPlainText(outcome.ocr.text)
        if outcome.match is None:
            if outcome.pending_question is not None:
                self.answer_label.setText("题库未收录")
                self.answer_status.setText("需要补录")
                self.answer_status.setProperty("state", "warn")
            else:
                self.answer_label.setText("未找到答案")
                self.answer_status.setText("未命中")
                self.answer_status.setProperty("state", "error")
            self._refresh_dynamic_style(self.answer_status)
            self.match_label.setText(
                outcome.detected_question or outcome.warning or "未解析到有效题目"
            )
            self.meta_label.setText(
                f"OCR {outcome.ocr.mean_score:.0%} · "
                f"{outcome.ocr.elapsed_seconds * 1000:.0f} ms"
            )
            return

        result = outcome.match
        self.answer_label.setText(
            " / ".join(result.question.answer_text) or "未解析到答案"
        )
        self.match_label.setText(result.question.title)
        source = "本地题库" if result.source == "local" else "JX3BOX"
        self.meta_label.setText(
            f"{source} · 匹配 {result.confidence:.0%} · "
            f"OCR {outcome.ocr.mean_score:.0%} · "
            f"{outcome.ocr.elapsed_seconds * 1000:.0f} ms"
        )
        self.answer_status.setText("已命中")
        self.answer_status.setProperty("state", "ok")
        self._refresh_dynamic_style(self.answer_status)

    def closeEvent(self, event: QCloseEvent) -> None:
        self.closing.emit()
        super().closeEvent(event)
