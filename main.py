import sys
import os
import logging
from PyQt6.QtWidgets import QApplication
from app.ui.manager import WorkflowManager
from app.ui.editor import WorkflowEditor
from app.core.engine import WorkflowRunner
from app.ui.runner import RunnerWindow
from app.core.models import Workflow
from app.utils.common import setup_logging, get_workflows_dir
import json
import threading

logger = setup_logging()

def main():
    app = QApplication(sys.argv)
    
    # Global references to keep windows alive
    windows = {}
    
    def on_edit_workflow(name):
        editor = WorkflowEditor(name, lambda: windows.pop("editor", None))
        windows["editor"] = editor
        editor.show()
        # We might want to hide manager or keep it open?
        # PRD 3.0: "Workflow Manager... Select -> Edit".
        # Usually Manager stays or hides. Let's keep it open for now.

    def on_run_workflow(name):
        # Load workflow
        path = os.path.join(get_workflows_dir(), name, "flow.json")
        if not os.path.exists(path):
            logger.error(f"Workflow not found: {path}")
            return
            
        with open(path, "r") as f:
            data = json.load(f)
            workflow = Workflow(**data)
            
        # Run in separate thread to not freeze UI
        workflow_dir = os.path.join(get_workflows_dir(), name)
        runner = WorkflowRunner(workflow, workflow_dir=workflow_dir)
        runner_window = RunnerWindow(runner)
        windows["runner"] = runner_window
        runner_window.show()
        
        t = threading.Thread(target=runner.run)
        t.start()
        
    manager = WorkflowManager(on_edit_workflow, on_run_workflow)
    windows["manager"] = manager
    manager.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
