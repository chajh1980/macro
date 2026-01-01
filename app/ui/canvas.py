from PyQt6.QtWidgets import QTreeWidget, QTreeWidgetItem, QAbstractItemView, QWidget, QLabel, QVBoxLayout, QHBoxLayout, QPushButton
from PyQt6.QtCore import Qt, pyqtSignal, QMimeData, QSize
from PyQt6.QtGui import QIcon, QAction, QDrag
from app.core.models import Step, Condition, Action, StepType, ConditionType, ActionType

class StepCardWidget(QWidget):
    def __init__(self, step: Step, index_str: str):
        super().__init__()
        layout = QHBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        self.setLayout(layout)
        
        # 1. Index (e.g. "1.1", "2")
        self.idx_label = QLabel(f"#{index_str}")
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
        if step.type == StepType.IF:
            return "IF"
        elif step.type == StepType.UNTIL:
            return "UNTIL"
        elif step.condition.type == ConditionType.IMAGE:
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
             
        # 4. If/Until (No special details for now, maybe condition summary later)
        if step.type in [StepType.IF, StepType.UNTIL]:
             return "(Container)"

        # Other Defaults -> Empty per user request
        return ""

class WorkflowCanvasWidget(QTreeWidget):
    step_dropped = pyqtSignal(str, str, object)  # category, type, parent_item (can be None)
    delete_requested = pyqtSignal()
    reordered = pyqtSignal() # Needs complex handling for tree reorder, simplification: just sync model
    
    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setAlternatingRowColors(True)
        self.setHeaderHidden(True)
        self.setIndentation(20) # Indent for children
        
        # IMPORTANT: To support dropping ON items (nesting), we need DropIndicator
        # But QTreeWidget default behavior is mostly sufficient if handled in dropEvent
        
    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Delete or event.key() == Qt.Key.Key_Backspace:
            self.delete_requested.emit()
        else:
            super().keyPressEvent(event)

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.topLevelItemCount() == 0:
            from PyQt6.QtGui import QPainter, QColor
            painter = QPainter(self.viewport())
            painter.setPen(QColor(150, 150, 150))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Drag steps here (If/Until supported)")

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
            
    def dropEvent(self, event):
        if event.mimeData().hasFormat("application/vnd.antigravity.step-type"):
             # New step dropped from Library
            data = event.mimeData().text()
            category, type_code = data.split(":")
            
            # Identify drop target (parent)
            target_item = self.itemAt(event.position().toPoint())
            
            self.step_dropped.emit(category, type_code, target_item)
            event.accept()
        else:
             # Internal Reorder (Nesting support handled by QTreeWidget, but we need to signal model update)
             # QTreeWidget handles the UI move automatically if super().dropEvent is called.
             # We just need to signal the controller to re-read the tree and update the model.
            super().dropEvent(event)
            self.reordered.emit()

    def update_steps(self, steps):
        self.clear()
        
        def add_items(step_list, parent_widget=None):
            for i, step in enumerate(step_list):
                item = QTreeWidgetItem(parent_widget) if parent_widget else QTreeWidgetItem(self)
                item.setData(0, Qt.ItemDataRole.UserRole, step)
                
                # Index generation: e.g. "1", "1.1", "1.1.2" (Not easy to compute statelessly without passing index prefix)
                # For now just use simple indices? Or traverse to calculate?
                # Simpler: Just rely on flat index or simple count for UI?
                # Let's pass 'index_str'
                
                # Actually, recursive index like "1.1" is good.
                # But widget creation happens after item is added.
                pass
        
        # Recursive function with index tracking
        def build_tree(current_steps, parent_item=None, prefix=""):
            for i, step in enumerate(current_steps):
                idx_str = f"{prefix}{i+1}"
                
                if parent_item:
                    item = QTreeWidgetItem(parent_item)
                else:
                    item = QTreeWidgetItem(self)
                
                item.setData(0, Qt.ItemDataRole.UserRole, step)
                
                # Create Widget
                widget = StepCardWidget(step, idx_str)
                self.setItemWidget(item, 0, widget)
                
                # Recursion for children
                if step.children:
                    build_tree(step.children, item, f"{idx_str}.")
                
                item.setExpanded(True) # Default expand

        build_tree(steps)
