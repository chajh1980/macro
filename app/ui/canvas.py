from PyQt6.QtWidgets import QTreeWidget, QTreeWidgetItem, QAbstractItemView, QWidget, QLabel, QVBoxLayout, QHBoxLayout, QPushButton, QFrame
from PyQt6.QtCore import Qt, pyqtSignal, QMimeData, QSize
from PyQt6.QtGui import QIcon, QAction, QDrag, QMouseEvent
from app.core.models import Step, Condition, Action, StepType, ConditionType, ActionType

class ClickableFrame(QFrame):
    clicked = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        else:
            super().mousePressEvent(event)

class StepCardWidget(QWidget):
    step_selected = pyqtSignal(Step) # Signal to notify canvas/editor of specific selection
    
    def __init__(self, step: Step, index_str: str):
        super().__init__()
        self.step = step
        self.layout = QHBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        self.setLayout(self.layout)
        
        # Check if AWAIT with child -> "Two Slot" Mode
        self.child_step = None
        if step.type == StepType.AWAIT and step.children:
            self.child_step = step.children[0]
            
        if self.child_step:
            self._init_composite_ui(index_str)
        else:
            self._init_standard_ui(index_str)

    def _init_standard_ui(self, index_str):
        self.layout.setContentsMargins(5, 5, 5, 5)
        self.layout.setSpacing(10)
        
        # 1. Index
        self.idx_label = QLabel(f"#{index_str}")
        self.idx_label.setStyleSheet("font-weight: bold; color: #888;")
        self.layout.addWidget(self.idx_label)
        
        # 2. Name
        name_text = self.step.name
        self.name_label = QLabel(name_text)
        self.name_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        self.layout.addWidget(self.name_label)
        
        # 3. Detail
        detail_text = self._get_detail(self.step)
        self.detail_label = QLabel(detail_text)
        self.detail_label.setStyleSheet("color: #444;")
        self.layout.addWidget(self.detail_label)
        
        self.layout.addStretch()
        
        # 4. Type
        type_str = self._get_type_str(self.step)
        self.type_label = QLabel(type_str)
        self.type_label.setStyleSheet("color: #888; font-size: 11px;")
        self.layout.addWidget(self.type_label)

    def _init_composite_ui(self, index_str):
        # Frame 1: Parent (Await)
        frame_parent = ClickableFrame()
        frame_parent.setStyleSheet("QFrame { background-color: #f0f0f0; border-radius: 4px; border: 1px solid #ccc; } QFrame:hover { background-color: #e0e0e0; }")
        frame_parent.clicked.connect(lambda: self.step_selected.emit(self.step))
        
        layout_p = QHBoxLayout()
        frame_parent.setLayout(layout_p)
        layout_p.setContentsMargins(5, 2, 5, 2)
        
        lbl_idx = QLabel(f"#{index_str}")
        lbl_idx.setStyleSheet("font-weight: bold; color: #555;")
        lbl_name = QLabel("Await")
        lbl_name.setStyleSheet("font-weight: bold; color: #000;")
        lbl_info = QLabel(f"{self.step.condition.retry_timeout_s}s")
        lbl_info.setStyleSheet("color: #666; font-size: 11px;")
        
        layout_p.addWidget(lbl_idx)
        layout_p.addWidget(lbl_name)
        layout_p.addWidget(lbl_info)
        
        # Frame 2: Child (e.g. Find Image)
        frame_child = ClickableFrame()
        frame_child.setStyleSheet("QFrame { background-color: #e6f3ff; border-radius: 4px; border: 1px solid #0066cc; } QFrame:hover { background-color: #d0e8ff; }")
        frame_child.clicked.connect(lambda: self.step_selected.emit(self.child_step))
        
        layout_c = QHBoxLayout()
        frame_child.setLayout(layout_c)
        layout_c.setContentsMargins(5, 2, 5, 2)
        
        child_type = self._get_type_str(self.child_step)
        child_name = self.child_step.name
        child_detail = self._get_detail(self.child_step)
        
        lbl_c_icon = QLabel("↳") # Arrow icon
        lbl_c_name = QLabel(child_name)
        lbl_c_name.setStyleSheet("font-weight: bold; color: #004488;")
        lbl_c_detail = QLabel(child_detail)
        lbl_c_detail.setStyleSheet("color: #004488; font-size: 11px;")
        
        layout_c.addWidget(lbl_c_icon)
        layout_c.addWidget(lbl_c_name)
        layout_c.addWidget(lbl_c_detail)
        layout_c.addStretch()
        
        # Add to main layout
        self.layout.addWidget(frame_parent, 1) # Stretch 1
        self.layout.addSpacing(5)
        self.layout.addWidget(frame_child, 3) # Stretch 3 (Child gets more space)
        
    def _get_type_str(self, step: Step) -> str:
        if step.type == StepType.IF:
            return "IF"
        elif step.type == StepType.UNTIL:
            return "UNTIL"
        elif step.type == StepType.AWAIT:
            return "AWAIT"
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
        
        # 3. Find Image
        if step.condition.type == ConditionType.IMAGE:
             path = step.condition.target_image_path
             if path:
                 import os
                 return f"...{os.path.basename(path)}"
             return "No Image"
             
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
    step_clicked = pyqtSignal(Step) # New signal for internal clicks

    
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
        
                # Create Widget
                widget = StepCardWidget(step, idx_str)
                widget.step_selected.connect(self.step_clicked.emit) # Forward signal
                self.setItemWidget(item, 0, widget)
                
                # Recursion for children
                if step.children:
                    # SPECIAL CASE: For AWAIT with 1 child, we visualised it inline in the parent widget.
                    # Technically, we should still traverse to keep the tree structure valid for drag/drop?
                    # BUT, if we show the child node, it will be duplicated visually.
                    # So, if AWAIT has children, and we used Inline mode, we should NOT create a tree item for the first child?
                    # Or create it but HIDDEN? Creating it hidden is safer for logic involving indices/traversal.
                    
                    hide_first_child = (step.type == StepType.AWAIT and len(step.children) >= 1)
                    
                    # Pass a custom flag or handle logic?
                    # Let's just pass logic to child_builder
                    build_tree(step.children, item, f"{idx_str}.", hide_first_child=hide_first_child)
                else:
                    item.setExpanded(True)

        # Recursive function with index tracking
        def build_tree(current_steps, parent_item=None, prefix="", hide_first_child=False):
            for i, step in enumerate(current_steps):
                idx_str = f"{prefix}{i+1}"
                
                if parent_item:
                    item = QTreeWidgetItem(parent_item)
                else:
                    item = QTreeWidgetItem(self)
                
                item.setData(0, Qt.ItemDataRole.UserRole, step)
                
                # Check if this item is the one we should hide?
                if i == 0 and hide_first_child:
                    # HIDDEN ITEM
                    item.setHidden(True)
                    # We still need the widget? No, visual is improved in parent.
                    # But we might need widget for selection callbacks?
                    # The parent's "Right Slot" click will select this step object.
                    # Inspector just needs the object.
                    # BUT, if we want `setCurrentItem` to work (for delete/highlight), the item must exist.
                    # Hidden items can be selected programmatically? Yes.
                    pass
                
                # Create Widget
                widget = StepCardWidget(step, idx_str)
                widget.step_selected.connect(self.step_clicked.emit)
                self.setItemWidget(item, 0, widget)
                
                # Detect inline mode for THIS step
                is_await_inline = (step.type == StepType.AWAIT and len(step.children) >= 1)
                
                if step.children:
                    build_tree(step.children, item, f"{idx_str}.", hide_first_child=is_await_inline)
                
                item.setExpanded(True) # Default expand

        build_tree(steps)
