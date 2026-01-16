from PyQt6.QtWidgets import QWidget, QVBoxLayout, QStackedWidget, QLabel, QLineEdit, QFormLayout
from PyQt6.QtCore import pyqtSignal
from app.ui.widgets import StepPropertiesWidget
from app.core.models import Step, Workflow

class WorkflowPropertiesWidget(QWidget):
    workflow_changed = pyqtSignal()

    def __init__(self):
        super().__init__()
        layout = QFormLayout()
        self.name_edit = QLineEdit()
        self.desc_edit = QLineEdit()
        layout.addRow("Name:", self.name_edit)
        layout.addRow("Description:", self.desc_edit)
        self.setLayout(layout)
        
        self.workflow = None
        self.name_edit.textChanged.connect(self._on_name_changed)
        
    def load_workflow(self, workflow: Workflow):
        self.workflow = workflow
        self.name_edit.setText(workflow.name)
        # self.desc_edit.setText(workflow.description) # Assuming description exists
        
    def _on_name_changed(self, text):
        if self.workflow:
            self.workflow.name = text
            self.workflow_changed.emit()

class PropertyInspectorWidget(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)
        
        # Header
        self.header_label = QLabel("Properties")
        self.header_label.setStyleSheet("font-weight: bold; padding: 10px; background-color: #f0f0f0;")
        layout.addWidget(self.header_label)
        
        # Stack
        self.stack = QStackedWidget()
        layout.addWidget(self.stack)
        
        # Pages
        self.workflow_props = WorkflowPropertiesWidget()
        self.step_props = StepPropertiesWidget()
        
        self.stack.addWidget(self.workflow_props) # Index 0
        self.stack.addWidget(self.step_props)     # Index 1
        
        self.current_step = None

    def set_workflow_dir(self, directory: str):
        self.step_props.set_workflow_dir(directory)

    def show_workflow_props(self, workflow: Workflow):
        self.header_label.setText("Workflow Properties")
        self.workflow_props.load_workflow(workflow)
        self.stack.setCurrentIndex(0)
        self.current_step = None

    def show_step_props(self, step: Step):
        self.header_label.setText(f"Step Properties: {step.name}")
        self.step_props.load_step(step)
        self.stack.setCurrentIndex(1)
        self.current_step = step
