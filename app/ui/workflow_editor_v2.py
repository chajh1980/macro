import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from PyQt6.QtWidgets import (
    QMainWindow,
    QCheckBox,
    QHBoxLayout,
    QAbstractItemView,
    QPushButton,
    QSplitter,
    QTreeWidget,
    QTreeWidgetItem,
    QTreeWidgetItemIterator,
    QVBoxLayout,
    QWidget,
    QMessageBox,
    QLabel,
    QFrame,
    QSizePolicy,
    QApplication,
)
from PyQt6.QtCore import Qt, pyqtSignal, QMimeData, QRect
from PyQt6.QtGui import QDrag, QMouseEvent, QGuiApplication
from app.ui.inspector import PropertyInspectorWidget
from app.ui.overlay import Overlay
from app.core.models import (
    Workflow,
    Step,
    ConditionType,
    ActionType,
    Condition,
    Action,
    StepType,
    LoopMode,
)
from app.utils.common import get_workflows_dir
from app.utils.screen_utils import set_window_size_percentage
import json
import uuid
import datetime
from typing import Optional


class PaletteButton(QPushButton):
    def __init__(self, title: str, description: str, category: str, type_code: str):
        super().__init__(f"{title}\n{description}")
        self.category = category
        self.type_code = type_code
        self._drag_start_pos = None
        self.setObjectName("paletteBtn")

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_pos = event.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._drag_start_pos is None:
            return super().mouseMoveEvent(event)
        if event.buttons() != Qt.MouseButton.LeftButton:
            return super().mouseMoveEvent(event)

        from PyQt6.QtWidgets import QApplication
        if (event.pos() - self._drag_start_pos).manhattanLength() <= QApplication.startDragDistance():
            return super().mouseMoveEvent(event)

        drag = QDrag(self)
        mime = QMimeData()
        payload = f"{self.category}:{self.type_code}"
        mime.setText(payload)
        mime.setData("application/vnd.antigravity.step-type", payload.encode())
        drag.setMimeData(mime)
        drag.exec(Qt.DropAction.CopyAction)
        self._drag_start_pos = None


class BlockPaletteV2(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("v2Palette")
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(10)
        self.setLayout(layout)

        def section(title: str, items):
            block = QWidget()
            block.setObjectName("paletteSection")
            v = QVBoxLayout()
            v.setContentsMargins(0, 0, 0, 0)
            v.setSpacing(8)
            block.setLayout(v)

            label = QLabel(title)
            label.setStyleSheet("font-weight: 700; color: #2f4765;")
            v.addWidget(label)

            row = QVBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(6)
            for item in items:
                title_text, desc, category, tcode = item
                btn = PaletteButton(title_text, desc, category, tcode)
                row.addWidget(btn)
            v.addLayout(row)
            v.addStretch(1)
            return block

        cols = [
            ("조건 찾기", [
                ("🖼️ 이미지", "화면 이미지 탐색", "Condition", "image"),
                ("🎨 색상", "색상 영역 탐색", "Condition", "color"),
                ("⏱️ 대기", "time delay", "Condition", "wait"),
            ]),
            ("동작", [
                ("🖱️ 클릭", "현재/지정 위치 클릭", "Action", "click"),
                ("↔️ 이동", "마우스 이동", "Action", "move"),
                ("⌨️ 키 입력", "단축키/문자", "Action", "key"),
                ("↩️ Goto", "Step 점프", "Action", "goto"),
            ]),
            ("흐름 제어", [
                ("⚙️ If", "조건부 실행", "Control", "if"),
                ("🔁 Loop(while1)", "무한 반복", "Control", "loop_forever"),
                ("⏩ Loop until", "조건 충족 시 종료", "Control", "loop_until"),
                ("🔁 Loop while", "조건 충족 시 계속 실행", "Control", "loop_while"),
                ("⌛ Await", "조건 대기 후 실행", "Control", "await"),
                ("🧩 Input", "사용자 입력", "Control", "input"),
                ("✂️ Break", "최근 루프 종료", "Control", "break"),
            ]),
        ]

        for title, items in cols:
            sec = section(title, items)
            layout.addWidget(sec)
        layout.addStretch(1)

        self.setStyleSheet(
            """
            #v2Palette {
                border: 1px solid #bfd3f8;
                border-radius: 10px;
                background: qlineargradient(x1:0 y1:0, x2:1 y2:1, stop:0 #f5f9ff, stop:1 #eef3ff);
            }
            #paletteSection QLabel {
                padding-left: 4px;
            }
            #paletteBtn {
                text-align: left;
                padding: 8px 12px;
                border: 1px solid #cdd9ef;
                border-radius: 8px;
                background: #f3f7ff;
                color: #13233f;
                min-width: 180px;
                font-size: 11px;
            }
            #paletteBtn:hover {
                border-color: #6e95de;
                background: #e6eeff;
            }
            #paletteBtn:pressed {
                background: #d6e4ff;
            }
            """
        )


class BlockStepCardWidget(QWidget):
    step_selected = pyqtSignal(Step)
    condition_step_requested = pyqtSignal(Step)
    condition_clear_requested = pyqtSignal(Step)

    def __init__(self, step: Step, index_str: str):
        super().__init__()
        self.step = step
        self._drag_start_pos = None

        self.setObjectName("blockCard")
        if self.step.type == StepType.IF:
            self.setProperty("flowKind", "if")
        elif self.step.type == StepType.LOOP:
            self.setProperty("flowKind", "loop")
        elif self.step.type == StepType.AWAIT:
            self.setProperty("flowKind", "await")
        elif self.step.type == StepType.BREAK:
            self.setProperty("flowKind", "break")
        elif self.step.type == StepType.INPUT:
            self.setProperty("flowKind", "input")
        else:
            self.setProperty("flowKind", "normal")
        layout = QVBoxLayout()
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)
        self.setLayout(layout)

        header = QHBoxLayout()
        header.setSpacing(8)

        idx = QLabel(f"#{index_str}")
        idx.setStyleSheet("color:#475569; font-size:13px; font-weight:700;")
        header.addWidget(idx)

        title = QLabel(self._title_text())
        title.setStyleSheet("font-size:16px; font-weight:700;")
        header.addWidget(title)

        if self.step.type == StepType.IF:
            tag = "IF"
        elif self.step.type == StepType.LOOP:
            if self.step.condition.loop_infinite:
                tag = "WHILE(1)"
            else:
                tag = "LOOP"
        elif self.step.type == StepType.AWAIT:
            tag = "AWAIT"
        elif self.step.type == StepType.BREAK:
            tag = "BREAK"
        else:
            tag = self._type_text()
        tag_label = QLabel(tag)
        tag_label.setStyleSheet("font-size:14px; color:#1d4ed8; font-weight:700;")
        header.addWidget(tag_label)

        header.addStretch()

        typ = QLabel(self._type_text())
        typ.setStyleSheet("color:#475569; font-size:12px;")
        header.addWidget(typ, 0, Qt.AlignmentFlag.AlignRight)

        frame = QFrame()
        frame.setLayout(header)
        layout.addWidget(frame)

        summary = self._build_summary_row()
        layout.addWidget(summary)

        if self._needs_condition_slot():
            has_inline_condition = self._has_inline_condition()
            has_condition_child = self._has_condition_child()
            has_condition = has_condition_child or has_inline_condition
            condition_layout = QHBoxLayout()
            if has_condition:
                condition_btn = QPushButton("조건 편집")
                condition_btn.setMinimumHeight(24)
                condition_btn.setStyleSheet(
                    """
                    QPushButton {
                        font-size: 11px;
                        font-weight: 700;
                        color: #0f172a;
                        border: 1px solid #93c5fd;
                        border-radius: 8px;
                        padding: 4px 10px;
                        background: #eff6ff;
                    }
                    QPushButton:hover { background: #dbeafe; }
                    QPushButton:pressed { background: #bfdbfe; }
                    """
                )
                condition_btn.clicked.connect(self._emit_condition_edit)
            else:
                condition_btn = QPushButton("조건 추가")
                condition_btn.setMinimumHeight(24)
                condition_btn.setStyleSheet(
                    """
                    QPushButton {
                        font-size: 11px;
                        font-weight: 700;
                        color: #0f172a;
                        border: 1px solid #93c5fd;
                        border-radius: 8px;
                        padding: 4px 10px;
                        background: #eff6ff;
                    }
                    QPushButton:hover { background: #dbeafe; }
                    QPushButton:pressed { background: #bfdbfe; }
                    """
                )
                # The card itself is passed when condition is empty, so editor can auto-create
                # a default condition step (이미지 탐색) in the first slot.
                condition_btn.clicked.connect(lambda: self.condition_step_requested.emit(self.step))
            condition_layout.addStretch(1)
            condition_layout.addWidget(condition_btn)

            if has_condition:
                clear_btn = QPushButton("조건 비우기")
                clear_btn.setMinimumHeight(24)
                clear_btn.setStyleSheet(
                    """
                    QPushButton {
                        font-size: 11px;
                        font-weight: 700;
                        color: #0f172a;
                        border: 1px solid #fda4af;
                        border-radius: 8px;
                        padding: 4px 10px;
                        background: #fee2e2;
                    }
                    QPushButton:hover { background: #fecaca; }
                    QPushButton:pressed { background: #fca5a5; }
                    """
                )
                clear_btn.clicked.connect(self._emit_condition_clear)
                condition_layout.addWidget(clear_btn)
            layout.addLayout(condition_layout)
        self.setStyleSheet(
            """
            #blockCard {
                background-color: #f5f7fb;
                border: 1px solid #d8e2ff;
                border-left: 5px solid #3b82c4;
                border-radius: 10px;
            }
            #blockCard:hover {
                border-color: #8fb4f3;
                background: #eef2ff;
            }
            #blockCard[flowKind=\"if\"] {
                border-left: 5px solid #3b82c4;
            }
            #blockCard[flowKind=\"loop\"] {
                border-left: 5px solid #8b5cf6;
            }
            #blockCard[flowKind=\"await\"] {
                border-left: 5px solid #0ea5a4;
            }
            #blockCard[flowKind=\"break\"] {
                border-left: 5px solid #f43f5e;
            }
            #blockCard[flowKind=\"input\"] {
                border-left: 5px solid #f59e0b;
            }
            """
        )

    def _needs_condition_slot(self) -> bool:
        t = self.step.type
        if isinstance(t, str):
            t = t.strip().upper()
            if t.startswith("STEPTYPE."):
                t = t.split(".", 1)[1]
        elif isinstance(t, StepType):
            t = t.value
        else:
            t = str(t).upper()
            if t.startswith("STEPTYPE."):
                t = t.split(".", 1)[1]

        if t == StepType.LOOP.value:
            loop_infinite = self._to_bool(self.step.condition.loop_infinite)
            return not loop_infinite
        return t in {StepType.IF.value, StepType.AWAIT.value, StepType.UNTIL.value}

    @staticmethod
    def _to_bool(value) -> bool:
        if isinstance(value, bool):
            return value
        if value is None:
            return False
        if isinstance(value, (int, float)):
            return bool(value)
        return str(value).lower() in {"1", "true", "yes", "y"}

    def _has_inline_condition(self) -> bool:
        c = self.step.condition
        if c.type == ConditionType.IMAGE:
            return bool(c.target_image_path)
        if c.type == ConditionType.COLOR:
            return bool(c.target_color)
        if c.type == ConditionType.TEXT:
            return bool(c.target_text)
        return False

    @staticmethod
    def _is_condition_like_step(step: Step) -> bool:
        if not step:
            return False
        if step.type == StepType.CONDITION:
            return True
        if step.condition.type in (ConditionType.IMAGE, ConditionType.COLOR, ConditionType.TEXT):
            return True
        return False

    def _has_condition_child(self) -> bool:
        return bool(self.step.children) and self._is_condition_like_step(self.step.children[0])

    def _has_active_condition(self) -> bool:
        return self._has_condition_child() or self._has_inline_condition()

    def _condition_target(self):
        if self._has_condition_child():
            return self.step.children[0]
        return self.step

    def _emit_condition_edit(self):
        self.condition_step_requested.emit(self._condition_target())

    def _emit_condition_clear(self):
        self.condition_clear_requested.emit(self.step)

    def _build_summary_row(self):
        segments = self._summary_segments()
        if not segments:
            label = QLabel(self._summary_text())
            label.setStyleSheet("color:#1f2937; font-size:12px;")
            label.setWordWrap(True)
            return label

        container = QWidget()
        summary_layout = QHBoxLayout()
        summary_layout.setContentsMargins(0, 0, 0, 0)
        summary_layout.setSpacing(6)
        container.setLayout(summary_layout)

        def summary_button(text, handler):
            btn = QPushButton(text)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFlat(True)
            btn.setStyleSheet(
                """
                QPushButton {
                    color: #1d4ed8;
                    font-size: 12px;
                    border: 0;
                    padding: 0;
                    text-decoration: underline;
                    background: transparent;
                }
                QPushButton:hover {
                    color: #1e40af;
                }
                """
            )
            if handler is not None:
                btn.clicked.connect(handler)
            return btn

        for idx, (text, clickable) in enumerate(segments):
            if idx > 0:
                summary_layout.addWidget(QLabel("|"))
                last = summary_layout.itemAt(summary_layout.count() - 1).widget()
                if last:
                    last.setStyleSheet("color:#94a3b8;")
            if clickable:
                summary_layout.addWidget(summary_button(text, self._emit_condition_edit))
            else:
                label = QLabel(text)
                label.setStyleSheet("color:#334155; font-size:12px;")
                summary_layout.addWidget(label)

        summary_layout.addStretch(1)
        return container

    def _summary_segments(self):
        segments = []
        if self.step.type in [StepType.IF, StepType.AWAIT]:
            if self._has_condition_child():
                cond_name = self.step.children[0].name or "Condition"
                body_count = max(0, len(self.step.children) - 1)
                segments.extend(
                    [
                        ("조건", True),
                        (f"적용 조건: {cond_name}", True),
                        (f"본문: {body_count}개", False),
                    ]
                )
            elif self._has_inline_condition():
                segments.extend(
                    [
                        ("조건", True),
                        (f"적용 조건: {self._inline_condition_text()} (인라인)", True),
                        (f"본문: {len(self.step.children)}개", False),
                    ]
                )
            else:
                segments.extend(
                    [
                        ("조건", True),
                        ("적용 조건: 미설정", False),
                        (f"본문: {len(self.step.children)}개", False),
                    ]
                )
            return segments

        if self.step.type == StepType.LOOP:
            if self.step.condition.loop_infinite:
                segments.extend(
                    [
                        ("반복 모드: while(1)", False),
                        (f"본문: {len(self.step.children)}개", False),
                    ]
                )
                return segments

            if self._has_condition_child():
                cond_name = self.step.children[0].name or "Condition"
                mode = self.step.condition.loop_mode.value if self.step.condition else "UNTIL_FOUND"
                mode_kr = "while(조건 충족 시)" if mode == LoopMode.WHILE_FOUND.value else "until(조건 미충족 시)"
                body_count = max(0, len(self.step.children) - 1)
                limit = (
                    f" / 최대 {self.step.condition.loop_max_count}회"
                    if self.step.condition.loop_max_count is not None
                    else ""
                )
                segments.extend(
                    [
                        (f"반복 모드: {mode_kr}{limit}", False),
                        ("적용 조건", True),
                        (cond_name, True),
                        (f"본문: {body_count}개", False),
                    ]
                )
            elif self._has_inline_condition():
                mode = "while" if self.step.condition.loop_mode == LoopMode.WHILE_FOUND else "until"
                limit = (
                    f" / 최대 {self.step.condition.loop_max_count}회"
                    if self.step.condition.loop_max_count is not None
                    else ""
                )
                segments.extend(
                    [
                        (f"반복 모드: {mode}{limit}", False),
                        ("적용 조건", True),
                        (f"{self._inline_condition_text()} (인라인)", True),
                    ]
                )
            else:
                mode = "while" if self.step.condition.loop_mode == LoopMode.WHILE_FOUND else "until"
                limit = (
                    f" / 최대 {self.step.condition.loop_max_count}회"
                    if self.step.condition.loop_max_count is not None
                    else ""
                )
                segments.extend(
                    [
                        (f"반복 모드: {mode}{limit}", False),
                        ("적용 조건", True),
                        ("미설정", False),
                        (f"본문: {len(self.step.children)}개", False),
                    ]
                )
            return segments

        return []
    def _summary_text(self):
        if self.step.children:
            if self.step.type in [StepType.IF, StepType.AWAIT, StepType.LOOP]:
                target = self.step.children[0]
                cond_name = target.name or "Condition"
                if self.step.type == StepType.LOOP:
                    if self.step.condition.loop_infinite:
                        body_count = len(self.step.children)
                        return f"반복 모드: while(1) | 본문: {body_count}개 | 적용 조건: {cond_name}"
                    mode = self.step.condition.loop_mode.value if self.step.condition else "UNTIL_FOUND"
                    mode_kr = "while(조건 충족 시)" if mode == LoopMode.WHILE_FOUND.value else "until(조건 미충족 시)"
                    body_count = max(0, len(self.step.children) - 1)
                    return (
                        f"반복 모드: {mode_kr}"
                        f" | 적용 조건: {cond_name}"
                        f" | 본문: {body_count}개"
                    )
                body_count = max(0, len(self.step.children) - 1)
                return f"조건: 적용됨 | 적용 조건: {cond_name} | 본문: {body_count}개"
        else:
            if self.step.type in [StepType.IF, StepType.AWAIT]:
                condition_summary = self._inline_condition_text()
                return f"조건: 미적용 | 적용 조건: {condition_summary} (인라인)"
            if self.step.type == StepType.LOOP:
                if self.step.condition.loop_infinite:
                    body_count = len(self.step.children)
                    return f"반복 모드: while(1) | 본문: {body_count}개"
                mode = "while" if self.step.condition.loop_mode == LoopMode.WHILE_FOUND else "until"
                limit = f" / 최대 {self.step.condition.loop_max_count}회" if self.step.condition.loop_max_count is not None else ""
                return f"반복 모드: {mode}{limit} | 적용 조건: {self._inline_condition_text()}"

        if self.step.type == StepType.LOOP:
            if self.step.condition.loop_infinite:
                return "반복 모드: while(1)"
            return "반복 모드: 설정 대기"
        if self.step.type == StepType.BREAK:
            return "현재 루프 즉시 종료"
        if self.step.type == StepType.INPUT:
            var_name = self.step.action.input_variable_name or "count"
            return f"Input Variable: {var_name}"

        if self.step.condition.type == ConditionType.TIME and self.step.action.type == ActionType.NONE:
            return f"Wait {self.step.condition.wait_time_s:.1f}s"
        if self.step.action.type == ActionType.GOTO:
            return f"Goto Step #{self.step.action.goto_step_index or 1}"
        return ""

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_pos = event.pos()
        self.step_selected.emit(self.step)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._drag_start_pos is None:
            return super().mouseMoveEvent(event)
        from PyQt6.QtWidgets import QApplication

        if (event.pos() - self._drag_start_pos).manhattanLength() <= QApplication.startDragDistance():
            return super().mouseMoveEvent(event)

        drag = QDrag(self)
        mime = QMimeData()
        mime.setText(f"move:{self.step.id}")
        mime.setData("application/vnd.antigravity.step-type", f"move:{self.step.id}".encode())
        drag.setMimeData(mime)
        drag.exec(Qt.DropAction.MoveAction)
        self._drag_start_pos = None

    def mouseReleaseEvent(self, event):
        self._drag_start_pos = None
        super().mouseReleaseEvent(event)

    def _title_text(self):
        if self.step.type == StepType.IF:
            return f"{self.step.name}"
        if self.step.type == StepType.LOOP:
            if self.step.condition.loop_infinite:
                return "Loop (while 1)"
            return self.step.name
        if self.step.type == StepType.AWAIT:
            return self.step.name
        return self.step.name

    def _type_text(self):
        if self.step.type == StepType.IF:
            return "IF"
        if self.step.type == StepType.LOOP:
            if self.step.condition.loop_infinite:
                return "LOOP(while1)"
            return "LOOP"
        if self.step.type == StepType.BREAK:
            return "Break"
        if self.step.type == StepType.AWAIT:
            return "AWAIT"
        if self.step.type == StepType.INPUT:
            return "Input"
        if self.step.condition.type == ConditionType.IMAGE:
            return "Image"
        if self.step.condition.type == ConditionType.COLOR:
            return "Color"
        if self.step.condition.type == ConditionType.TEXT:
            return "Text"
        if self.step.condition.type == ConditionType.TIME and self.step.action.type == ActionType.NONE:
            return "Wait"
        if self.step.action.type == ActionType.MOVE:
            return "Move"
        if self.step.action.type == ActionType.CLICK:
            return "Click"
        if self.step.action.type == ActionType.GOTO:
            return "Goto"
        if self.step.action.type == ActionType.KEY:
            return "Key"
        return str(self.step.type)

    def _inline_condition_text(self) -> str:
        c = self.step.condition
        if c.type == ConditionType.IMAGE:
            return "이미지 탐색"
        if c.type == ConditionType.COLOR:
            return "색상 탐색"
        if c.type == ConditionType.TEXT:
            return "텍스트 탐색"
        if c.type == ConditionType.TIME:
            return "시간 대기"
        return "미설정"


class WorkflowCanvasV2(QTreeWidget):
    step_dropped = pyqtSignal(str, str, object, str)
    step_clicked = pyqtSignal(Step)
    condition_step_selected = pyqtSignal(Step)
    condition_clear_requested = pyqtSignal(Step)
    reordered = pyqtSignal()

    DROP_CONDITION = "condition"
    DROP_BODY = "body"
    DROP_ABOVE = "above"
    DROP_BELOW = "below"

    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setSelectionMode(QTreeWidget.SelectionMode.SingleSelection)
        self.setAlternatingRowColors(True)
        self.setHeaderHidden(True)
        self.setIndentation(16)
        self.setUniformRowHeights(False)
        self.setStyleSheet(
            """
            QTreeWidget {
                border: 1px solid #c6d2eb;
                border-radius: 8px;
                background: #f5f8ff;
                color: #111827;
                show-decoration-selected: 1;
            }
            QTreeWidget::item:selected {
                background: #dbe7ff;
            }
            QTreeWidget::item:hover {
                background: #e2ebff;
            }
            """
        )

    def mimeTypes(self):
        types = super().mimeTypes()
        types.append("application/vnd.antigravity.step-type")
        return types

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat("application/vnd.antigravity.step-type"):
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat("application/vnd.antigravity.step-type"):
            event.acceptProposedAction()
            return
        super().dragMoveEvent(event)

    def _is_container(self, step: Step):
        return step.type in [StepType.IF, StepType.LOOP, StepType.AWAIT, StepType.UNTIL]

    def _requires_condition_slot(self, step: Step) -> bool:
        t = step.type
        if isinstance(t, str):
            t = t.strip().upper()
            if t.startswith("STEPTYPE."):
                t = t.split(".", 1)[1]
        elif isinstance(t, StepType):
            t = t.value
        else:
            t = str(t).upper()
            if t.startswith("STEPTYPE."):
                t = t.split(".", 1)[1]

        if t == StepType.LOOP.value:
            loop_infinite = self._to_bool(step.condition.loop_infinite)
            return not loop_infinite
        return t in {StepType.IF.value, StepType.AWAIT.value, StepType.UNTIL.value}

    @staticmethod
    def _to_bool(value) -> bool:
        if isinstance(value, bool):
            return value
        if value is None:
            return False
        if isinstance(value, (int, float)):
            return bool(value)
        return str(value).lower() in {"1", "true", "yes", "y"}

    def dropEvent(self, event):
        if event.mimeData().hasFormat("application/vnd.antigravity.step-type"):
            data = event.mimeData().text()
            category, type_code = data.split(":")
            target_item = self.itemAt(event.position().toPoint())
            slot = self.DROP_BELOW

            if target_item:
                step = target_item.data(0, Qt.ItemDataRole.UserRole)
                indicator = self.dropIndicatorPosition()

                if indicator == QTreeWidget.DropIndicatorPosition.AboveItem:
                    slot = self.DROP_ABOVE
                elif indicator == QTreeWidget.DropIndicatorPosition.BelowItem:
                    slot = self.DROP_BELOW
                elif indicator == QTreeWidget.DropIndicatorPosition.OnItem:
                    if step and self._is_container(step):
                        if self._requires_condition_slot(step):
                            rect = self.visualItemRect(target_item)
                            y = event.position().y() - rect.top()
                            slot = self.DROP_CONDITION if y < rect.height() * 0.45 else self.DROP_BODY
                        else:
                            slot = self.DROP_BODY
                    else:
                        slot = self.DROP_BELOW

            self.step_dropped.emit(category, type_code, target_item, slot)
            event.setDropAction(Qt.DropAction.CopyAction)
            event.accept()
            return

        super().dropEvent(event)
        self.reordered.emit()

    def update_steps(self, steps):
        self.clear()
        if not steps:
            hint_item = QTreeWidgetItem(self)
            hint_widget = QLabel("블록을 끌어다 놓아 첫 단계를 추가하세요")
            hint_widget.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
            hint_widget.setWordWrap(True)
            hint_widget.setStyleSheet("padding:30px; color:#334155; font-size: 14px;")
            hint_widget.setMinimumHeight(140)
            self.setItemWidget(hint_item, 0, hint_widget)
            hint_item.setSizeHint(0, hint_widget.sizeHint())
            return

        def add_items(items, parent_item=None, prefix="", hide_first_child=False):
            visible_index = 1
            for i, step in enumerate(items):
                if hide_first_child and i == 0:
                    idx = f"{prefix}0"
                else:
                    idx = f"{prefix}{visible_index}"
                    visible_index += 1

                item = QTreeWidgetItem(parent_item or self)
                item.setData(0, Qt.ItemDataRole.UserRole, step)
                widget = BlockStepCardWidget(step, idx)
                widget.step_selected.connect(self.step_clicked.emit)
                widget.condition_step_requested.connect(self.condition_step_selected.emit)
                widget.condition_clear_requested.connect(self.condition_clear_requested.emit)
                self.setItemWidget(item, 0, widget)
                item.setSizeHint(0, widget.sizeHint())
                if hide_first_child and i == 0:
                    item.setHidden(True)

                if self._is_container(step):
                    item.setFlags(item.flags() | Qt.ItemFlag.ItemIsDropEnabled)
                else:
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsDropEnabled)

                if step.children:
                    child_hide_first = False
                    add_items(step.children, item, f"{idx}.", hide_first_child=child_hide_first)
                else:
                    item.setExpanded(True)

        add_items(steps)


class WorkflowEditorV2(QMainWindow):
    def __init__(self, workflow_name: str, on_close):
        super().__init__()
        self.workflow_name = workflow_name
        self.on_close_callback = on_close
        self.workflow = self._load_workflow(workflow_name)
        self.has_unsaved_changes = False

        self.setWindowTitle(f"Editing (V2): {workflow_name}")
        self.setStyleSheet(
            """
            QWidget {
                font-family: "Apple SD Gothic Neo", "Malgun Gothic", "Noto Sans KR", "SF Pro Text", Arial, sans-serif;
                color: #1f2937;
                font-size: 13px;
            }
            QMainWindow {
                background: qlineargradient(x1:0 y1:0, x2:1 y2:1, stop:0 #e8edff, stop:1 #f4f7ff);
            }
            QPushButton {
                font-size: 12px;
            }
            QLabel {
                color: #0f172a;
            }
            QLineEdit {
                background-color: #ffffff;
                color: #0f172a;
                border: 1px solid #93c5fd;
                border-radius: 8px;
                padding: 6px 8px;
                selection-background-color: #dbeafe;
                selection-color: #0f172a;
            }
            QLineEdit:disabled {
                background-color: #f8fafc;
                color: #94a3b8;
            }
            QAbstractSpinBox {
                background-color: #ffffff;
                color: #0f172a;
                border: 1px solid #93c5fd;
                border-radius: 8px;
                padding: 4px 8px;
                min-height: 22px;
                selection-background-color: #dbeafe;
                selection-color: #0f172a;
            }
            QAbstractSpinBox:hover {
                border-color: #60a5fa;
            }
            QComboBox {
                background-color: #ffffff;
                color: #0f172a;
                font-size: 13px;
                padding: 6px 28px 6px 10px;
                border: 1px solid #93c5fd;
                border-radius: 8px;
                min-height: 28px;
                selection-background-color: #dbeafe;
                selection-color: #0f172a;
            }
            QComboBox:hover {
                border-color: #60a5fa;
            }
            QComboBox::drop-down {
                width: 24px;
                border-left: 1px solid #93c5fd;
                subcontrol-origin: padding;
                subcontrol-position: right;
                border-top-right-radius: 8px;
                border-bottom-right-radius: 8px;
            }
            QComboBox QAbstractItemView {
                background: #ffffff;
                color: #0f172a;
                selection-background-color: #dbeafe;
                selection-color: #0f172a;
                border: 1px solid #93c5fd;
            }
            QMessageBox {
                background-color: #ffffff;
                color: #0f172a;
                font-size: 14px;
            }
            QMessageBox QLabel {
                color: #0f172a;
                font-size: 14px;
            }
            QMessageBox QPushButton {
                min-width: 88px;
                min-height: 28px;
                padding: 6px 14px;
                font-size: 14px;
                font-weight: 600;
                color: #1e3a8a;
                border: 1px solid #93c5fd;
                border-radius: 8px;
            }
            QMessageBox QPushButton:hover {
                background: #dbeafe;
                border-color: #60a5fa;
            }
            QMessageBox QPushButton:default {
                background: #2563eb;
                color: #ffffff;
                border-color: #1d4ed8;
            }
            """
        )
        set_window_size_percentage(self, width_pct=0.7, height_pct=0.6)

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(8)
        central.setLayout(main_layout)

        badge = QLabel("V2 블록 플로우 에디터")
        badge.setStyleSheet(
            "QLabel {"
            "font-weight: 700;"
            "font-size: 18px;"
            "padding: 4px 10px;"
            "color: #0f274f;"
            "background: qlineargradient(x1:0 y1:0, x2:1 y2:0, stop:0 #d6e2ff, stop:1 #ebf1ff);"
            "border: 1px solid #a9c1f5;"
            "border-radius: 8px;"
            "}"
        )
        badge.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        main_layout.addWidget(badge)

        self.toolbar = BlockPaletteV2()
        self.toolbar.setFixedWidth(300)
        self.toolbar.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        self.toolbar.setContentsMargins(0, 0, 0, 0)

        workspace = QSplitter(Qt.Orientation.Horizontal)
        workspace.addWidget(self.toolbar)

        left_panel = QWidget()
        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)
        left_panel.setLayout(left_layout)
        self.canvas = WorkflowCanvasV2()
        left_layout.addWidget(self.canvas, 1)
        workspace.addWidget(left_panel)

        self.inspector = PropertyInspectorWidget()
        self.inspector.setFixedWidth(350)
        self.inspector.set_workflow_dir(os.path.join(get_workflows_dir(), self.workflow_name))
        workspace.addWidget(self.inspector)
        workspace.setStretchFactor(0, 2)
        workspace.setStretchFactor(1, 4)
        workspace.setStretchFactor(2, 3)
        main_layout.addWidget(workspace)

        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("Save")
        self.cancel_btn = QPushButton("Close")
        self.delete_btn = QPushButton("Delete Step")
        self.delete_btn.setStyleSheet("background-color:#ffcccc; color:#cc0000;")
        self.always_on_top_cb = QCheckBox("Always on Top")
        self.always_on_top_cb.stateChanged.connect(self._toggle_always_on_top)
        btn_layout.addWidget(self.always_on_top_cb)
        btn_layout.addStretch()
        btn_layout.addWidget(self.delete_btn)
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)
        main_layout.addLayout(btn_layout)

        # Signals
        self.canvas.step_dropped.connect(self._on_step_dropped)
        self.canvas.itemClicked.connect(self._on_step_selected)
        self.canvas.step_clicked.connect(self._on_step_selected_from_widget)
        self.canvas.condition_step_selected.connect(self._on_condition_step_selected)
        self.canvas.condition_clear_requested.connect(self._on_condition_clear_requested)
        self.canvas.reordered.connect(self._on_reordered)
        self.save_btn.clicked.connect(self._save_workflow)
        self.delete_btn.clicked.connect(self._delete_current_step)
        self.cancel_btn.clicked.connect(self.close)
        self.inspector.step_props.step_changed.connect(self._on_step_changed_from_inspector)
        self.inspector.workflow_props.workflow_changed.connect(self._on_workflow_props_changed)
        self.inspector.step_props.capture_img_btn.setEnabled(True)
        self.inspector.step_props.capture_img_btn.clicked.connect(self._capture_image)
        self.inspector.step_props.img_capture_area_btn.clicked.connect(lambda: self._capture_area_watch(for_image=True))
        self.inspector.step_props.pick_color_btn.clicked.connect(self._pick_color)
        self.inspector.step_props.color_set_area_btn.clicked.connect(lambda: self._capture_area_watch(for_image=False))
        self.inspector.step_props.pick_pos_btn.clicked.connect(self._pick_point)
        self.inspector.step_props.test_btn.clicked.connect(self._test_current_step)

        self._refresh_canvas()
        self.inspector.show_workflow_props(self.workflow)

    def _on_workflow_props_changed(self):
        self.has_unsaved_changes = True
        self.setWindowTitle(f"Editing (V2): {self.workflow_name} *")

    def _can_capture(self):
        return self.inspector is not None and self.inspector.step_props is not None

    def _is_overlay_active(self):
        return hasattr(self, "overlay") and self.overlay is not None and self.overlay.isVisible()

    def _show_capture_error(self, context: str, err):
        self.show()
        QMessageBox.warning(self, "Capture Error", f"{context}: {err}")

    def _capture_image(self):
        if not self._can_capture():
            return
        if self._is_overlay_active():
            return
        self.hide()
        try:
            self.overlay = Overlay(mode="region")
            self.overlay.captured.connect(self._on_image_captured)
            self.overlay.canceled.connect(self.show)
            self.overlay.show()
            QApplication.processEvents()
        except Exception as e:
            self._show_capture_error("capture image 시작 실패", e)

    def _on_image_captured(self, rect):
        self.show()
        self.overlay = None

        current_step = self.inspector.current_step
        if not current_step:
            return

        screen = QGuiApplication.primaryScreen()
        pixmap = screen.grabWindow(0, rect.x(), rect.y(), rect.width(), rect.height())

        assets_dir = os.path.join(get_workflows_dir(), self.workflow_name, "assets")
        if not os.path.exists(assets_dir):
            os.makedirs(assets_dir)

        filename = f"target_{int(datetime.datetime.now().timestamp())}.png"
        path = os.path.join(assets_dir, filename)
        pixmap.save(path)

        rel_path = os.path.join("assets", filename)
        current_step.condition.target_image_path = rel_path
        self.inspector.step_props.load_step(current_step)
        self._refresh_canvas_item()

    def _capture_area_watch(self, for_image=False):
        if not self._can_capture():
            return
        if self._is_overlay_active():
            return
        self.hide()
        try:
            self.overlay = Overlay(mode="region")
            self.overlay.captured.connect(lambda rect: self._on_area_captured(rect, for_image=for_image))
            self.overlay.canceled.connect(self.show)
            self.overlay.show()
            QApplication.processEvents()
        except Exception as e:
            self._show_capture_error("capture area 시작 실패", e)

    def _on_area_captured(self, rect, for_image=False):
        self.show()
        self.overlay = None

        _ = for_image

        current_step = self.inspector.current_step
        if not current_step:
            return

        area = [rect.x(), rect.y(), rect.width(), rect.height()]
        current_step.condition.watch_area = area
        self.inspector.step_props.load_step(current_step)

    def _pick_point(self):
        if not self._can_capture():
            return
        if self._is_overlay_active():
            return
        self.hide()
        try:
            self.overlay = Overlay(mode="point")
            self.overlay.clicked.connect(self._on_point_picked)
            self.overlay.canceled.connect(self.show)
            self.overlay.show()
            QApplication.processEvents()
        except Exception as e:
            self._show_capture_error("좌표 선택 시작 실패", e)

    def _on_point_picked(self, x, y):
        self.show()
        self.overlay = None

        current_step = self.inspector.current_step
        if not current_step:
            return

        current_step.action.target_x = x
        current_step.action.target_y = y
        self.inspector.step_props.load_step(current_step)
        self._refresh_canvas_item()

    def _pick_color(self):
        if not self._can_capture():
            return
        if self._is_overlay_active():
            return
        self.hide()
        try:
            self.overlay = Overlay(mode="color")
            self.overlay.color_picked.connect(self._on_color_picked)
            self.overlay.canceled.connect(self.show)
            self.overlay.show()
            QApplication.processEvents()
        except Exception as e:
            self._show_capture_error("색상 선택 시작 실패", e)

    def _on_color_picked(self, hex_color):
        self.show()
        self.overlay = None

        current_step = self.inspector.current_step
        if not current_step:
            return

        current_step.condition.target_color = hex_color
        self.inspector.step_props.load_step(current_step)
        self._refresh_canvas_item()

    def _test_current_step(self):
        step = self.inspector.current_step
        if not step:
            QMessageBox.information(self, "Test Step", "테스트할 스텝이 선택되지 않았습니다.")
            return

        # 1) Image
        if step.condition.type == ConditionType.IMAGE and step.condition.target_image_path:
            try:
                from app.core.engine import find_image_on_screen
                img_path = os.path.join(get_workflows_dir(), self.workflow_name, step.condition.target_image_path)
                matches = find_image_on_screen(
                    img_path,
                    confidence=step.condition.confidence or 0.9,
                    region=step.condition.watch_area,
                )
                if matches:
                    match = matches[0]
                    from app.utils.screen_utils import get_screen_scale
                    scale = get_screen_scale()
                    rect = QRect(int(match[0] / scale), int(match[1] / scale), int(match[2] / scale), int(match[3] / scale))
                    self.highlight_overlay = Overlay(mode="highlight", highlight_rect=rect)
                    self.highlight_overlay.show()

                    center_x = rect.x() + rect.width() // 2 + (step.action.target_x or 0)
                    center_y = rect.y() + rect.height() // 2 + (step.action.target_y or 0)
                    try:
                        from PyQt6.QtGui import QCursor
                        QCursor.setPos(center_x, center_y)
                    except Exception:
                        pass
                    QMessageBox.information(self, "Test Result", f"이미지 찾음: ({center_x}, {center_y})")
                else:
                    QMessageBox.warning(self, "Test Result", "이미지를 찾지 못했습니다.")
            except Exception as e:
                QMessageBox.critical(self, "Test Error", f"이미지 테스트 실패: {e}")
            return

        # 2) Color
        if step.condition.type == ConditionType.COLOR and step.condition.target_color:
            try:
                from app.core.image_proc import find_color_on_screen
                region = tuple(step.condition.watch_area) if step.condition.watch_area else None
                matches = find_color_on_screen(
                    step.condition.target_color,
                    tolerance=step.condition.color_tolerance,
                    region=region,
                )
                if matches:
                    idx = step.condition.match_index or 0
                    if idx >= len(matches):
                        idx = 0
                    match = matches[idx]
                    from app.utils.screen_utils import get_screen_scale
                    scale = get_screen_scale()
                    rect = QRect(int(match[0] / scale), int(match[1] / scale), int(match[2] / scale), int(match[3] / scale))
                    self.highlight_overlay = Overlay(mode="highlight", highlight_rect=rect)
                    self.highlight_overlay.show()
                    QMessageBox.information(self, "Test Result", f"색상 찾음: index={idx+1}")
                else:
                    QMessageBox.warning(self, "Test Result", "색상을 찾지 못했습니다.")
            except Exception as e:
                QMessageBox.critical(self, "Test Error", f"색상 테스트 실패: {e}")
            return

        # 3) Move
        if step.action.type == ActionType.MOVE:
            if step.action.target_x is None or step.action.target_y is None:
                QMessageBox.warning(self, "Test Result", "Move 좌표가 없습니다.")
                return
            try:
                import pyautogui
                pyautogui.moveTo(step.action.target_x, step.action.target_y)
                QMessageBox.information(self, "Test Result", f"마우스를 ({step.action.target_x}, {step.action.target_y})로 이동했습니다.")
            except Exception as e:
                QMessageBox.critical(self, "Test Error", f"Move 테스트 실패: {e}")
            return

        # 4) Click
        if step.action.type == ActionType.CLICK:
            try:
                import pyautogui
                x = step.action.target_x if step.action.target_x is not None else None
                y = step.action.target_y if step.action.target_y is not None else None
                pyautogui.click(x=x, y=y)
                QMessageBox.information(self, "Test Result", "클릭 테스트를 실행했습니다.")
            except Exception as e:
                QMessageBox.critical(self, "Test Error", f"Click 테스트 실패: {e}")
            return

        # 5) Goto / Time / 기타
        if step.action.type == ActionType.GOTO:
            QMessageBox.information(self, "Test Result", f"Goto Step 테스트: {step.action.goto_step_index or 1}")
            return

        if step.condition.type == ConditionType.TIME:
            QMessageBox.information(self, "Test Result", f"Wait 테스트: {step.condition.wait_time_s}s")
            return

        QMessageBox.information(self, "Test Result", "해당 타입은 즉시 실행 가능한 테스트가 없습니다.")

    def _toggle_always_on_top(self, state):
        if state == 2:
            self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowStaysOnTopHint)
        self.show()

    def _load_workflow(self, name: str) -> Workflow:
        path = os.path.join(get_workflows_dir(), name, "flow.json")
        workflow = None
        if os.path.exists(path):
            with open(path, "r") as f:
                data = None
                try:
                    data = json.load(f)
                    workflow = Workflow(**data)
                except Exception:
                    workflow = self._load_legacy_workflow(data, name)

        if workflow is None and os.path.exists(path):
            try:
                with open(path, "r") as f:
                    data = json.load(f)
            except Exception:
                data = None
            workflow = self._load_legacy_workflow(data, name)

        if not workflow:
            workflow = Workflow(name=name, created_at="", updated_at="")

        def update_ids_recursive(steps):
            for step in steps:
                step.id = str(uuid.uuid4())
                if step.children:
                    update_ids_recursive(step.children)

        update_ids_recursive(workflow.steps)
        return workflow

    def _load_legacy_workflow(self, data, workflow_name: str) -> Optional[Workflow]:
        if not isinstance(data, dict):
            if isinstance(data, list):
                data = {"name": workflow_name, "steps": data, "created_at": "", "updated_at": ""}
            else:
                return None

        raw_steps = data.get("steps")
        if not isinstance(raw_steps, list):
            return None

        if not data.get("name"):
            data["name"] = workflow_name

        from app.core.models import KeyInputMode

        def normalize_condition_type(raw_type):
            t = str(raw_type or "time").strip().lower()
            if t == "image":
                return ConditionType.IMAGE
            if t == "color":
                return ConditionType.COLOR
            if t == "text":
                return ConditionType.TEXT
            return ConditionType.TIME

        def normalize_action_type(raw_type):
            t = str(raw_type or "none").strip().lower()
            if t == "move":
                return ActionType.MOVE
            if t == "click":
                return ActionType.CLICK
            if t in ("keypress", "key", "key_press"):
                return ActionType.KEY
            if t == "goto":
                return ActionType.GOTO
            return ActionType.NONE

        def normalize_step_type(raw_type):
            t = str(raw_type or "general").strip().lower()
            if t in ("if", "condition_if"):
                return StepType.IF
            if t in ("until", "loop"):
                return StepType.LOOP
            if t == "await":
                return StepType.AWAIT
            if t == "input":
                return StepType.INPUT
            if t == "break":
                return StepType.BREAK
            return StepType.GENERAL

        def to_list(value):
            if isinstance(value, tuple):
                return list(value)
            if isinstance(value, list):
                return value
            return None

        def parse_legacy_step(raw_step):
            if not isinstance(raw_step, dict):
                return None

            condition_raw = raw_step.get("condition", {})
            action_raw = raw_step.get("action", {})
            condition_type = normalize_condition_type(condition_raw.get("type"))

            condition_kwargs = {
                "type": condition_type,
                "target_text": None,
                "target_color": None,
                "watch_area": None,
                "target_image_path": None,
                "match_mode": getattr(condition_raw, "match_mode", "SINGLE"),
                "confidence": 0.8,
                "scan_interval_ms": 500,
                "timeout_s": 10.0,
                "deduplicate_radius_px": 10,
                "wait_time_s": 0.0,
                "retry_timeout_s": 5.0,
                "retry_interval_ms": 500,
                "loop_mode": LoopMode.UNTIL_FOUND,
                "loop_max_count": 100,
                "loop_count_variable": None,
                "loop_infinite": False,
                "color_tolerance": 0,
                "match_index": 0,
            }

            if condition_type == ConditionType.IMAGE:
                image_raw = condition_raw.get("image") if isinstance(condition_raw.get("image"), dict) else {}
                condition_kwargs["target_image_path"] = image_raw.get("template_path")
                condition_kwargs["confidence"] = image_raw.get("confidence", condition_raw.get("confidence", 0.8))
                condition_kwargs["scan_interval_ms"] = image_raw.get("poll_interval_ms", condition_raw.get("scan_interval_ms", 500))
                condition_kwargs["timeout_s"] = image_raw.get("timeout_s", condition_raw.get("timeout_s", 10.0))
                condition_kwargs["deduplicate_radius_px"] = image_raw.get("min_dedup_distance_px", condition_raw.get("deduplicate_radius_px", 10))
                area = image_raw.get("watch_area") if isinstance(image_raw, dict) else None
                condition_kwargs["watch_area"] = to_list(area)
            elif condition_type == ConditionType.COLOR:
                color_raw = condition_raw.get("color") if isinstance(condition_raw.get("color"), dict) else {}
                condition_kwargs["target_color"] = color_raw.get("target_color", condition_raw.get("target_color"))
                condition_kwargs["color_tolerance"] = color_raw.get("tolerance", condition_raw.get("color_tolerance", 0))
                condition_kwargs["match_index"] = color_raw.get("match_index", condition_raw.get("match_index", 0))
                area = color_raw.get("watch_area") if isinstance(color_raw, dict) else None
                condition_kwargs["watch_area"] = to_list(area)
            elif condition_type == ConditionType.TEXT:
                text_raw = condition_raw.get("text")
                if isinstance(text_raw, dict):
                    condition_kwargs["target_text"] = text_raw.get("value")
                else:
                    condition_kwargs["target_text"] = condition_raw.get("target_text")
            else:
                wait_raw = condition_raw.get("wait")
                if isinstance(wait_raw, dict):
                    condition_kwargs["wait_time_s"] = float(wait_raw.get("seconds", condition_raw.get("wait_time_s", 0.0)))
                else:
                    condition_kwargs["wait_time_s"] = float(condition_raw.get("wait_time_s", 0.0))

            action_type = normalize_action_type(action_raw.get("type"))
            action_kwargs = {
                "type": action_type,
                "target_x": None,
                "target_y": None,
                "goto_step_index": None,
                "input_variable_name": action_raw.get("input_variable_name", "count"),
                "input_prompt": action_raw.get("input_prompt", "값을 입력하세요"),
                "key_sequence": None,
                "key_mode": KeyInputMode.PRESS,
            }

            if action_type in (ActionType.MOVE, ActionType.CLICK):
                position = action_raw.get("move", {}).get("position") if isinstance(action_raw.get("move"), dict) else None
                if position is None and action_type == ActionType.CLICK:
                    position = action_raw.get("click", {}).get("position") if isinstance(action_raw.get("click"), dict) else None
                if position is None:
                    position = action_raw.get("position")
                if isinstance(position, (list, tuple)) and len(position) == 2:
                    action_kwargs["target_x"] = int(position[0])
                    action_kwargs["target_y"] = int(position[1])
            elif action_type == ActionType.GOTO:
                goto_raw = action_raw.get("goto", {}) if isinstance(action_raw.get("goto"), dict) else {}
                action_kwargs["goto_step_index"] = int(goto_raw.get("step_index", action_raw.get("goto_step_index", 1) or 1))
            elif action_type == ActionType.KEY:
                key_raw = action_raw.get("keypress", {}) if isinstance(action_raw.get("keypress"), dict) else {}
                if key_raw is None or not isinstance(key_raw, dict):
                    key_raw = {}
                action_kwargs["key_sequence"] = key_raw.get("text", action_raw.get("key_sequence", ""))
                key_mode = str(key_raw.get("mode", "press")).lower()
                action_kwargs["key_mode"] = KeyInputMode.PRESS if key_mode in ("press", "hotkey", "combo") else KeyInputMode.TYPE

            step_type = normalize_step_type(raw_step.get("step_type") or raw_step.get("type"))
            step = Step(
                id=str(raw_step.get("id") or uuid.uuid4()),
                name=str(raw_step.get("name") or raw_step.get("label") or "Step"),
                type=step_type,
                condition=Condition(**condition_kwargs),
                action=Action(**action_kwargs),
            )

            loop_mode = raw_step.get("loop_mode")
            if loop_mode:
                step.condition.loop_mode = LoopMode.WHILE_FOUND if str(loop_mode).lower().startswith("while") else LoopMode.UNTIL_FOUND
            step.condition.loop_infinite = bool(raw_step.get("loop_infinite", step.condition.loop_infinite))
            step.condition.loop_count_variable = raw_step.get("loop_count_variable")
            if raw_step.get("loop_max_count") is not None:
                try:
                    step.condition.loop_max_count = int(raw_step.get("loop_max_count"))
                except Exception:
                    pass

            step.step_interval_ms = raw_step.get("step_interval_ms", raw_step.get("interval_ms", step.step_interval_ms))
            child_list = raw_step.get("children") or raw_step.get("steps") or []
            if not isinstance(child_list, list):
                child_list = []
            for child_raw in child_list:
                child_step = parse_legacy_step(child_raw)
                if child_step:
                    step.children.append(child_step)

            return step

        steps = []
        for raw_step in raw_steps:
            parsed = parse_legacy_step(raw_step)
            if parsed:
                steps.append(parsed)

        return Workflow(
            name=data.get("name", workflow_name),
            steps=steps,
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
        )

    def _save_workflow(self):
        path = os.path.join(get_workflows_dir(), self.workflow_name, "flow.json")
        with open(path, "w") as f:
            f.write(self.workflow.json())
        self.has_unsaved_changes = False
        self.setWindowTitle(f"Editing (V2): {self.workflow_name}")
        QMessageBox.information(self, "Saved", "Workflow saved successfully.")

    def _refresh_canvas(self):
        self.canvas.update_steps(self.workflow.steps)

    def _find_step_by_id(self, step_id):
        def traverse(steps, parent=None):
            for s in steps:
                if s.id == step_id:
                    return s, parent
                if s.children:
                    res, p = traverse(s.children, s)
                    if res:
                        return res, p
            return None, None

        return traverse(self.workflow.steps)

    def _is_descendant_of(self, root_step, target_step):
        if root_step is target_step:
            return True
        for child in root_step.children:
            if self._is_descendant_of(child, target_step):
                return True
        return False

    def _configure_new_step(self, step, category, type_code):
        if category == "Condition":
            if type_code == "image":
                step.condition.type = ConditionType.IMAGE
                step.action.type = ActionType.MOVE
                step.name = "Find Image"
            elif type_code == "wait":
                step.condition.type = ConditionType.TIME
                step.condition.wait_time_s = 1.0
                step.name = "Wait"
            elif type_code == "color":
                step.condition.type = ConditionType.COLOR
                step.action.type = ActionType.MOVE
                step.name = "Find Color"
        elif category == "Action":
            if type_code == "click":
                step.condition.type = ConditionType.TIME
                step.condition.wait_time_s = 0
                step.action.type = ActionType.CLICK
                step.name = "Click Mouse"
            elif type_code == "move":
                step.condition.type = ConditionType.TIME
                step.condition.wait_time_s = 0
                step.action.type = ActionType.MOVE
                step.name = "Move Mouse"
            elif type_code == "key":
                step.condition.type = ConditionType.TIME
                step.condition.wait_time_s = 0
                step.action.type = ActionType.KEY
                step.action.key_sequence = ""
                step.name = "Key Input"
            elif type_code == "goto":
                step.condition.type = ConditionType.TIME
                step.condition.wait_time_s = 0
                step.action.type = ActionType.GOTO
                step.action.goto_step_index = 1
                step.name = "Goto Step"
        elif category == "Control":
            if type_code == "if":
                step.type = StepType.IF
                step.name = "If Condition"
                step.condition.type = ConditionType.IMAGE
            elif type_code in ["until", "loop", "loop_until"]:
                step.type = StepType.LOOP
                step.name = "Loop (until)"
                step.condition.type = ConditionType.IMAGE
                step.condition.loop_mode = LoopMode.UNTIL_FOUND
                step.condition.loop_max_count = 100
                step.condition.loop_infinite = False
            elif type_code == "loop_while":
                step.type = StepType.LOOP
                step.name = "Loop (while)"
                step.condition.type = ConditionType.IMAGE
                step.condition.loop_mode = LoopMode.WHILE_FOUND
                step.condition.loop_max_count = 100
                step.condition.loop_infinite = False
            elif type_code == "loop_forever":
                step.type = StepType.LOOP
                step.name = "Loop (while 1)"
                step.condition.type = ConditionType.IMAGE
                step.condition.loop_mode = LoopMode.UNTIL_FOUND
                step.condition.loop_infinite = True
            elif type_code == "await":
                step.type = StepType.AWAIT
                step.name = "Await"
                step.condition.type = ConditionType.TIME
            elif type_code == "input":
                step.type = StepType.INPUT
                step.name = "User Input"
                step.action.type = ActionType.NONE
            elif type_code == "break":
                step.type = StepType.BREAK
                step.name = "Break"
                step.condition.type = ConditionType.TIME
                step.action.type = ActionType.NONE
                step.action.goto_step_index = None

    def _on_step_dropped(self, category, type_code, target_item=None, slot=WorkflowCanvasV2.DROP_BELOW):
        new_step = None
        source_list = None

        if category == "move":
            step_id = type_code
            found_step, found_parent = self._find_step_by_id(step_id)
            if not found_step:
                return
            new_step = found_step
            source_list = found_parent.children if found_parent else self.workflow.steps
        else:
            new_step = Step(
                id=str(uuid.uuid4()),
                name="Step",
                condition=Condition(type=ConditionType.TIME, wait_time_s=0),
                action=Action(type=ActionType.NONE),
            )
            self._configure_new_step(new_step, category, type_code)

        if not new_step:
            return

        if category == "move" and target_item:
            target_step = target_item.data(0, Qt.ItemDataRole.UserRole)
            if target_step is new_step or self._is_descendant_of(new_step, target_step):
                return
            try:
                source_list.remove(new_step)
            except ValueError:
                return
        elif category == "move" and source_list is not None:
            try:
                source_list.remove(new_step)
            except ValueError:
                return

        inserted = False
        if target_item:
            target_step = target_item.data(0, Qt.ItemDataRole.UserRole)
            parent_item = target_item.parent()
            parent_step = parent_item.data(0, Qt.ItemDataRole.UserRole) if parent_item else None
            target_list = parent_step.children if parent_step else self.workflow.steps

            try:
                target_idx = target_list.index(target_step)
            except ValueError:
                target_idx = len(target_list)

            is_container = target_step and self.canvas._is_container(target_step)
            requires_condition_slot = (
                target_step is not None and self.canvas._requires_condition_slot(target_step)
            )
            if slot == WorkflowCanvasV2.DROP_CONDITION and is_container and new_step.type == StepType.BREAK:
                slot = WorkflowCanvasV2.DROP_BODY
            if slot == WorkflowCanvasV2.DROP_CONDITION and is_container:
                if not requires_condition_slot:
                    slot = WorkflowCanvasV2.DROP_BODY
                else:
                    target_step.children.insert(0, new_step)
                    inserted = True
            elif slot == WorkflowCanvasV2.DROP_BODY and is_container:
                target_step.children.append(new_step)
                inserted = True
            elif slot == WorkflowCanvasV2.DROP_ABOVE:
                target_list.insert(target_idx, new_step)
                inserted = True
            elif slot == WorkflowCanvasV2.DROP_BELOW:
                target_list.insert(target_idx + 1, new_step)
                inserted = True

        if not inserted:
            self.workflow.steps.append(new_step)

        self.has_unsaved_changes = True
        self._refresh_canvas()
        self.canvas.expandAll()

    def _on_step_selected(self, item, _col=0):
        if not item:
            self.inspector.show_workflow_props(self.workflow)
            return

        step = item.data(0, Qt.ItemDataRole.UserRole)
        if step:
            self.inspector.show_step_props(step)
        else:
            self.inspector.show_workflow_props(self.workflow)

    def _on_step_selected_from_widget(self, step):
        if step:
            self.inspector.show_step_props(step)

    def _on_step_changed_from_inspector(self, _step):
        self.has_unsaved_changes = True
        self._refresh_canvas_item()

    def _condition_slot_needs_step(self, step: Step) -> bool:
        return self.canvas._requires_condition_slot(step)

    def _ensure_condition_step_from_inline(self, parent_step: Step):
        if parent_step.condition.type == ConditionType.TIME and not (
            parent_step.condition.target_image_path
            or parent_step.condition.target_color
            or parent_step.condition.target_text
        ):
            return None

        if parent_step.condition.type == ConditionType.IMAGE:
            default_name = "Find Image"
            action_type = ActionType.MOVE
        elif parent_step.condition.type == ConditionType.COLOR:
            default_name = "Find Color"
            action_type = ActionType.MOVE
        elif parent_step.condition.type == ConditionType.TEXT:
            default_name = "Find Text"
            action_type = ActionType.NONE
        else:
            return None

        condition_step = Step(
            id=str(uuid.uuid4()),
            name=default_name,
            condition=Condition(
                type=parent_step.condition.type,
                target_image_path=parent_step.condition.target_image_path,
                target_color=parent_step.condition.target_color,
                target_text=parent_step.condition.target_text,
                confidence=parent_step.condition.confidence,
                watch_area=parent_step.condition.watch_area,
                color_tolerance=parent_step.condition.color_tolerance,
                match_index=parent_step.condition.match_index,
                timeout_s=parent_step.condition.timeout_s,
                scan_interval_ms=parent_step.condition.scan_interval_ms,
                deduplicate_radius_px=parent_step.condition.deduplicate_radius_px,
                loop_mode=parent_step.condition.loop_mode,
                loop_max_count=parent_step.condition.loop_max_count,
                loop_count_variable=parent_step.condition.loop_count_variable,
                loop_infinite=parent_step.condition.loop_infinite,
                wait_time_s=0.0,
            ),
            action=Action(type=action_type),
            children=[],
        )

        # Keep legacy fields only for recovery of old workflows and avoid duplicate condition sources.
        parent_step.condition.target_image_path = None
        parent_step.condition.target_color = None
        parent_step.condition.target_text = None
        parent_step.condition.watch_area = None
        parent_step.condition.type = ConditionType.TIME
        parent_step.condition.wait_time_s = 0.0
        return condition_step

    def _find_condition_parent(self, condition_step: Step):
        def walk(steps):
            for step in steps:
                if step.children and step.children[0] is condition_step and self._condition_slot_needs_step(step):
                    return step
                parent = walk(step.children)
                if parent:
                    return parent
            return None

        return walk(self.workflow.steps)

    @staticmethod
    def _looks_like_condition_step(step: Step) -> bool:
        if not step:
            return False
        if step.type == StepType.CONDITION:
            return True
        return step.condition.type in (ConditionType.IMAGE, ConditionType.COLOR, ConditionType.TEXT)

    def _clear_condition_inline(self, step: Step):
        loop_state = None
        if step.type == StepType.LOOP:
            loop_state = (
                step.condition.loop_mode,
                step.condition.loop_infinite,
                step.condition.loop_max_count,
                step.condition.loop_count_variable,
            )
        step.condition.target_image_path = None
        step.condition.target_color = None
        step.condition.target_text = None
        step.condition.watch_area = None
        step.condition.confidence = 0.8
        step.condition.scan_interval_ms = 500
        step.condition.timeout_s = 10.0
        step.condition.color_tolerance = 0
        step.condition.match_index = 0
        step.condition.type = ConditionType.IMAGE
        step.condition.wait_time_s = 0.0
        if loop_state is not None:
            step.condition.loop_mode, step.condition.loop_infinite, step.condition.loop_max_count, step.condition.loop_count_variable = loop_state

    def _on_condition_clear_requested(self, step):
        if not step or not self._condition_slot_needs_step(step):
            return

        if step.children and self._looks_like_condition_step(step.children[0]):
            step.children.pop(0)
            self.has_unsaved_changes = True
            self._refresh_canvas()
            self.inspector.show_step_props(step)
            self.canvas.expandAll()
            return

        self._clear_condition_inline(step)
        self.has_unsaved_changes = True
        self._refresh_canvas()
        self.inspector.show_step_props(step)
        self.canvas.expandAll()

    def _on_condition_step_selected(self, step):
        # 'step' can be either the condition child step itself, or a container step
        # when its condition slot is empty and user pressed "조건 추가".
        if step is None:
            return

        if self._find_condition_parent(step):
            self.inspector.show_step_props(step)
            return

        if self._condition_slot_needs_step(step) and not step.children:
            inline_condition = self._ensure_condition_step_from_inline(step)
            if inline_condition:
                step.children.insert(0, inline_condition)
                self.has_unsaved_changes = True
                self._refresh_canvas()
                self.inspector.show_step_props(inline_condition)
                self.canvas.expandAll()
                return

            # Create default condition step (Find Image) and place it as first child.
            condition_step = Step(
                id=str(uuid.uuid4()),
                name="Find Image",
                condition=Condition(type=ConditionType.IMAGE),
                action=Action(type=ActionType.NONE),
            )
            self._configure_new_step(condition_step, "Condition", "image")
            step.children.insert(0, condition_step)
            self.has_unsaved_changes = True
            self._refresh_canvas()
            self.inspector.show_step_props(condition_step)
            self.canvas.expandAll()
            return

        self.inspector.show_step_props(step)

    def _on_reordered(self):
        def safe_get_step(item):
            return item.data(0, Qt.ItemDataRole.UserRole)

        def traverse_item(item):
            step = safe_get_step(item)
            if not step:
                return None
            new_children = []
            for i in range(item.childCount()):
                child_item = item.child(i)
                child_step = traverse_item(child_item)
                if child_step:
                    new_children.append(child_step)
            step.children = new_children
            return step

        new_root_steps = []
        for i in range(self.canvas.topLevelItemCount()):
            item = self.canvas.topLevelItem(i)
            step = traverse_item(item)
            if not step:
                continue
            if step.children and step.type not in [StepType.IF, StepType.UNTIL, StepType.AWAIT, StepType.LOOP]:
                orphans = step.children
                step.children = []
                new_root_steps.append(step)
                new_root_steps.extend(orphans)
            else:
                new_root_steps.append(step)

        self.workflow.steps = new_root_steps
        self.has_unsaved_changes = True
        self._refresh_canvas()

    def _delete_current_step(self):
        item = self.canvas.currentItem()
        if not item:
            QMessageBox.information(self, "Delete", "Please select a step to delete.")
            return

        target = item.data(0, Qt.ItemDataRole.UserRole)
        reply = QMessageBox.question(
            self,
            "Delete Step",
            f"Are you sure you want to delete '{target.name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        def remove_step(target_step, steps):
            for i, step in enumerate(steps):
                if step is target_step:
                    steps.pop(i)
                    return True
                if remove_step(target_step, step.children):
                    return True
            return False

        if remove_step(target, self.workflow.steps):
            parent = item.parent()
            if parent:
                parent.removeChild(item)
            else:
                self.canvas.invisibleRootItem().removeChild(item)
            self.has_unsaved_changes = True
            self._refresh_canvas()
        else:
            QMessageBox.warning(self, "Error", "Could not find target step in workflow.")

    def _refresh_canvas_item(self):
        current_step = self.inspector.current_step
        self._refresh_canvas()
        if current_step:
            iterator = QTreeWidgetItemIterator(self.canvas)
            while iterator.value():
                item = iterator.value()
                if item.data(0, Qt.ItemDataRole.UserRole) == current_step:
                    self.canvas.setCurrentItem(item)
                    break
                iterator += 1

    def closeEvent(self, event):
        if not self.has_unsaved_changes:
            self.on_close_callback()
            event.accept()
            return

        reply = QMessageBox.question(
            self,
            "Unsaved Changes",
            "Save changes before close?",
            QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Save,
        )
        if reply == QMessageBox.StandardButton.Save:
            self._save_workflow()
            self.on_close_callback()
            event.accept()
        elif reply == QMessageBox.StandardButton.Discard:
            self.on_close_callback()
            event.accept()
        else:
            event.ignore()


def launch_v2_editor(workflow_name: str, on_close):
    return WorkflowEditorV2(workflow_name, on_close)


if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    win = WorkflowEditorV2("sample", lambda: None)
    win.show()
    sys.exit(app.exec())
