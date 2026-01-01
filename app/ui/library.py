from PyQt6.QtWidgets import QListWidget, QListWidgetItem, QAbstractItemView
from PyQt6.QtCore import Qt, QMimeData
from PyQt6.QtGui import QDrag, QIcon
from app.core.models import StepType, ConditionType, ActionType

class ComponentLibraryWidget(QListWidget):
    def __init__(self):
        super().__init__()
        self.setDragEnabled(True)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setAlternatingRowColors(True)
        
        # Populate library
        self._add_item("Image Match", "Condition", "image")
        self._add_item("Find Color", "Condition", "color")
        # Text Match removed as per user request (too slow)
        self._add_item("Wait", "Condition", "wait")
        self._add_item("Click", "Action", "click")
        self._add_item("Move", "Action", "move")
        self._add_item("Goto", "Action", "goto")

    def _add_item(self, name, category, type_code):
        item = QListWidgetItem(f"{category}: {name}")
        item.setData(Qt.ItemDataRole.UserRole, type_code)
        item.setData(Qt.ItemDataRole.UserRole + 1, category)
        self.addItem(item)
    
    def mouseDoubleClickEvent(self, event):
        item = self.itemAt(event.pos())
        if item:
            type_code = item.data(Qt.ItemDataRole.UserRole)
            category = item.data(Qt.ItemDataRole.UserRole + 1)
            # We can't easily emit a custom signal without defining it on class level.
            # But QListWidget already has itemDoubleClicked signal.
            # Let's rely on the parent connecting to itemDoubleClicked.
            super().mouseDoubleClickEvent(event)
        else:
            super().mouseDoubleClickEvent(event)

    def startDrag(self, supportedActions):
        item = self.currentItem()
        if not item:
            return
            
        type_code = item.data(Qt.ItemDataRole.UserRole)
        category = item.data(Qt.ItemDataRole.UserRole + 1)
        
        mime_data = QMimeData()
        mime_data.setText(f"{category}:{type_code}")
        mime_data.setData("application/vnd.antigravity.step-type", f"{category}:{type_code}".encode())
        
        drag = QDrag(self)
        drag.setMimeData(mime_data)
        drag.exec(Qt.DropAction.CopyAction)
