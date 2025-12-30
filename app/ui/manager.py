import os
import json
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QPushButton, QMessageBox, QLabel, QCheckBox
)
from app.utils.common import get_workflows_dir
from app.core.models import Workflow

class WorkflowManager(QWidget):
    def __init__(self, on_edit_workflow, on_run_workflow):
        super().__init__()
        self.on_edit_workflow = on_edit_workflow
        self.on_run_workflow = on_run_workflow
        
        self.setWindowTitle("Visual Macro Manager")
        self.resize(400, 300)
        
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        
        # Top Bar
        top_layout = QHBoxLayout()
        self.label = QLabel("Available Workflows:")
        self.always_on_top_cb = QCheckBox("Always on Top")
        self.always_on_top_cb.stateChanged.connect(self._toggle_always_on_top)
        
        top_layout.addWidget(self.label)
        top_layout.addStretch()
        top_layout.addWidget(self.always_on_top_cb)
        self.layout.addLayout(top_layout)
        
        self.list_widget = QListWidget()
        self.layout.addWidget(self.list_widget)
        
        btn_layout = QHBoxLayout()
        self.new_btn = QPushButton("New")
        self.edit_btn = QPushButton("Edit")
        self.run_btn = QPushButton("Run")
        self.del_btn = QPushButton("Delete")
        
        btn_layout.addWidget(self.new_btn)
        btn_layout.addWidget(self.edit_btn)
        btn_layout.addWidget(self.run_btn)
        btn_layout.addWidget(self.del_btn)
        self.layout.addLayout(btn_layout)
        
        # Connect
        self.new_btn.clicked.connect(self._new_workflow)
        self.edit_btn.clicked.connect(self._edit_workflow)
        self.run_btn.clicked.connect(self._run_workflow)
        self.del_btn.clicked.connect(self._delete_workflow)
        
        self.refresh_list()

    def _toggle_always_on_top(self, state):
        from PyQt6.QtCore import Qt
        if state == 2: # Checked
            self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowStaysOnTopHint)
        self.show()

    def refresh_list(self):
        self.list_widget.clear()
        workflows_dir = get_workflows_dir()
        if not os.path.exists(workflows_dir):
            os.makedirs(workflows_dir)
            
        for name in os.listdir(workflows_dir):
            if os.path.isdir(os.path.join(workflows_dir, name)):
                self.list_widget.addItem(name)

    def _new_workflow(self):
        # For now just create a default one
        # In real app, ask for name
        import datetime
        name = f"workflow_{int(datetime.datetime.now().timestamp())}"
        path = os.path.join(get_workflows_dir(), name)
        os.makedirs(path)
        
        # Create empty flow.json
        workflow = Workflow(
            name=name,
            created_at=str(datetime.datetime.now()),
            updated_at=str(datetime.datetime.now())
        )
        
        with open(os.path.join(path, "flow.json"), "w") as f:
            f.write(workflow.json())
            
        self.refresh_list()

    def _edit_workflow(self):
        item = self.list_widget.currentItem()
        if item:
            self.on_edit_workflow(item.text())

    def _run_workflow(self):
        item = self.list_widget.currentItem()
        if item:
            self.on_run_workflow(item.text())

    def _delete_workflow(self):
        item = self.list_widget.currentItem()
        if item:
            name = item.text()
            confirm = QMessageBox.question(
                self, "Confirm Delete",
                f"Are you sure you want to delete workflow '{name}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if confirm == QMessageBox.StandardButton.Yes:
                import shutil
                path = os.path.join(get_workflows_dir(), name)
                if os.path.exists(path):
                    try:
                        shutil.rmtree(path)
                        self.refresh_list()
                    except Exception as e:
                        QMessageBox.critical(self, "Error", f"Failed to delete workflow: {e}")
