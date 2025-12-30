from PyQt6.QtWidgets import QListWidget, QListWidgetItem, QAbstractItemView, QWidget, QLabel, QVBoxLayout, QHBoxLayout, QPushButton
from PyQt6.QtCore import Qt, pyqtSignal, QMimeData, QSize
from PyQt6.QtGui import QIcon, QAction
from app.core.models import Step, Condition, Action, StepType, ConditionType, ActionType

class StepCardWidget(QWidget):
    def __init__(self, step: Step, index: int):
        super().__init__()
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        self.setLayout(layout)
        
        # Header: Index + Name + Type
        header_layout = QHBoxLayout()
        self.idx_label = QLabel(f"#{index}")
        self.idx_label.setStyleSheet("font-weight: bold; color: #888;")
        
        self.name_label = QLabel(step.name)
        self.name_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        
        type_str = "Unknown"
        if step.condition.type == ConditionType.IMAGE:
            type_str = "Condition: Image"
        elif step.condition.type == ConditionType.TEXT:
            type_str = "Condition: Text"
        elif step.condition.type == ConditionType.TIME and step.condition.wait_time_s > 0:
            type_str = "Condition: Wait"
        elif step.action.type != ActionType.NONE:
            type_str = f"Action: {step.action.type.value}"
            
        self.type_label = QLabel(type_str)
        self.type_label.setStyleSheet("color: #666; font-size: 11px;")
        
        header_layout.addWidget(self.idx_label)
        header_layout.addWidget(self.name_label)
        header_layout.addStretch()
        header_layout.addWidget(self.type_label)
        layout.addLayout(header_layout)
        
        # Body: Summary
        self.summary_label = QLabel(self._get_summary(step))
        self.summary_label.setWordWrap(True)
        self.summary_label.setStyleSheet("color: #444; margin-top: 5px;")
        layout.addWidget(self.summary_label)

    def _get_summary(self, step: Step) -> str:
        if step.condition.type == ConditionType.IMAGE:
            return f"Find Image: {step.condition.target_image_path or 'Not set'}"
        elif step.condition.type == ConditionType.TEXT:
            return f"Find Text: '{step.condition.target_text}'"
            
        # Check Action First for Time-based steps
        if step.action.type == ActionType.CLICK:
             # It's a click. 
             # Technically it has a TIME condition (Wait), but user sees it as Action.
             pos_str = "Last Match"
             if step.action.target_x is not None and step.action.target_y is not None:
                 pos_str = f"({step.action.target_x}, {step.action.target_y})"
             return f"Click: {pos_str}"
             
        elif step.action.type == ActionType.MOVE:
             pos_str = "Last Match" # Default for move might be last match if 0,0?
             if step.action.target_x is not None and step.action.target_y is not None:
                 pos_str = f"({step.action.target_x}, {step.action.target_y})"
             return f"Move: {pos_str}"
             
        elif step.action.type == ActionType.GOTO:
             return f"Goto Step: #{step.action.goto_step_index or '?'}"
             
        # If Action is NONE and Condition is TIME, then it's a pure Wait
        if step.condition.type == ConditionType.TIME:
            return f"Wait: {step.condition.wait_time_s}s"
            
        return "No details"

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
