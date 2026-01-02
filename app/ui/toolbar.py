from PyQt6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QVBoxLayout, QLabel, QGroupBox
from PyQt6.QtCore import Qt, QMimeData
from PyQt6.QtGui import QDrag, QAction

class DraggableButton(QPushButton):
    def __init__(self, name, category, type_code):
        super().__init__(name)
        self.category = category
        self.type_code = type_code
        self.setFixedWidth(100)
        self.setFixedHeight(40)
        
    def mouseMoveEvent(self, event):
        if event.buttons() != Qt.MouseButton.LeftButton:
            return

        drag = QDrag(self)
        mime = QMimeData()
        
        # Consistent mime type with canvas expectations
        mime.setText(f"{self.category}:{self.type_code}")
        mime.setData("application/vnd.antigravity.step-type", f"{self.category}:{self.type_code}".encode())
        
        drag.setMimeData(mime)
        drag.exec(Qt.DropAction.CopyAction)

class ComponentToolbar(QWidget):
    def __init__(self):
        super().__init__()
        layout = QHBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(20)
        self.setLayout(layout)
        
        # Style
        self.setStyleSheet("""
            QGroupBox {
                border: 1px solid #ddd;
                border-radius: 5px;
                margin-top: 10px;
                font-weight: bold;
                color: #555;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px 0 3px;
            }
            QPushButton {
                background-color: #fce4ec; /* Light pinkish match */
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                color: #333;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #f8bbd0;
            }
            QPushButton:pressed {
                background-color: #f48fb1;
            }
        """)
        
        # 1. Condition Group
        grp_cond = QGroupBox("Condition")
        layout_cond = QHBoxLayout()
        grp_cond.setLayout(layout_cond)
        
        layout_cond.addWidget(DraggableButton("Find Image", "Condition", "image"))
        layout_cond.addWidget(DraggableButton("Find Color", "Condition", "color"))
        
        layout.addWidget(grp_cond)
        
        # 2. Action Group
        grp_act = QGroupBox("Action")
        layout_act = QHBoxLayout()
        grp_act.setLayout(layout_act)
        
        layout_act.addWidget(DraggableButton("Wait", "Condition", "wait")) # Wait technically is condition
        layout_act.addWidget(DraggableButton("Click", "Action", "click"))
        layout_act.addWidget(DraggableButton("Move", "Action", "move"))
        
        layout.addWidget(grp_act)
        
        # 3. Logic/Etc Group
        grp_etc = QGroupBox("Flow Control")
        layout_etc = QHBoxLayout()
        grp_etc.setLayout(layout_etc)
        
        layout_etc.addWidget(DraggableButton("Goto", "Action", "goto"))
        layout_etc.addWidget(DraggableButton("If", "Control", "if"))
        layout_etc.addWidget(DraggableButton("Until", "Control", "until"))
        layout_etc.addWidget(DraggableButton("Await", "Control", "await"))
        
        layout.addWidget(grp_etc)
        
        layout.addStretch()
