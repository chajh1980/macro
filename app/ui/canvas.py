from PyQt6.QtWidgets import QListWidget, QListWidgetItem, QAbstractItemView, QWidget, QLabel, QVBoxLayout, QHBoxLayout, QPushButton
from PyQt6.QtCore import Qt, pyqtSignal, QMimeData, QSize
from PyQt6.QtGui import QIcon, QAction
from app.core.models import Step, Condition, Action, StepType, ConditionType, ActionType

class StepCardWidget(QWidget):
    def __init__(self, step: Step, index: int):
        super().__init__()
        layout = QHBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        self.setLayout(layout)
        
        # 1. Index
        self.idx_label = QLabel(f"#{index}")
        self.idx_label.setStyleSheet("font-weight: bold; color: #888; margin-right: 5px;")
        layout.addWidget(self.idx_label)
        
        # 2. Name
        self.name_label = QLabel(step.name)
        self.name_label.setStyleSheet("font-weight: bold; font-size: 14px; margin-right: 10px;")
        layout.addWidget(self.name_label)
        
        # 3. Detail (Middle, Variable)
        detail_text = self._get_detail(step)
        self.detail_label = QLabel(detail_text)
        self.detail_label.setStyleSheet("color: #444;")
        layout.addWidget(self.detail_label)
        
        # Spacer
        layout.addStretch()
        
        # 4. Type (Right)
        type_str = self._get_type_str(step)
        self.type_label = QLabel(type_str)
        self.type_label.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(self.type_label)
        
    def _get_type_str(self, step: Step) -> str:
        if step.condition.type == ConditionType.IMAGE:
            return "Image"
        elif step.condition.type == ConditionType.COLOR:
            return "Color"
        elif step.condition.type == ConditionType.TEXT:
            return "Text"
        elif step.condition.type == ConditionType.TIME and step.condition.wait_time_s > 0:
            return "Wait"
        elif step.action.type != ActionType.NONE:
            return step.action.type.value # Click, Move, etc.
        return ""

    def _get_detail(self, step: Step) -> str:
        # User requested specifics:
        # Wait: "Wait: 2.0s"
        # Find Color: "Target: #RRGGBB"
        # Goto: "Goto #3"
        
        # 1. Wait (Time Condition)
        if step.condition.type == ConditionType.TIME:
             if step.action.type == ActionType.NONE:
                 return f"Wait: {step.condition.wait_time_s}s"
        
        # 2. Find Color
        if step.condition.type == ConditionType.COLOR:
             return f"Target: {step.condition.target_color}"
             
        # 3. Goto
        if step.action.type == ActionType.GOTO:
             return f"Goto #{step.action.goto_step_index or '?'}"
             
        # Other Defaults
        if step.condition.type == ConditionType.IMAGE:
             import os
             name = os.path.basename(step.condition.target_image_path) if step.condition.target_image_path else "Not set"
             return f"File: {name}"
             
        if step.condition.type == ConditionType.TEXT:
             return f"Text: '{step.condition.target_text}'"
             
        if step.action.type == ActionType.CLICK:
             return "Click"
             
        if step.action.type == ActionType.MOVE:
             return "Move"
             
        return ""

class WorkflowCanvasWidget(QListWidget):
    step_dropped = pyqtSignal(str, str)  # category, type
    delete_requested = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setAlternatingRowColors(True)
        self.setSpacing(5)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Delete or event.key() == Qt.Key.Key_Backspace:
            self.delete_requested.emit()
        else:
            super().keyPressEvent(event)

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.count() == 0:
            from PyQt6.QtGui import QPainter, QColor
            painter = QPainter(self.viewport())
            painter.setPen(QColor(150, 150, 150))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Drag steps here or double-click from Library")

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat("application/vnd.antigravity.step-type"):
            event.accept()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat("application/vnd.antigravity.step-type"):
            event.accept()
        else:
            super().dragMoveEvent(event)

    reordered = pyqtSignal()
    
    def dropEvent(self, event):
        if event.mimeData().hasFormat("application/vnd.antigravity.step-type"):
             # New step dropped from Library
            data = event.mimeData().text()
            category, type_code = data.split(":")
            self.step_dropped.emit(category, type_code)
            event.accept()
        else:
             # Internal Reorder
            super().dropEvent(event)
            self.reordered.emit()

    def update_steps(self, steps):
        self.clear()
        for i, step in enumerate(steps):
            item = QListWidgetItem(self)
            item.setData(Qt.ItemDataRole.UserRole, step) # Store step object
            widget = StepCardWidget(step, i + 1)
            item.setSizeHint(widget.sizeHint())
            self.addItem(item)
            self.setItemWidget(item, widget)
