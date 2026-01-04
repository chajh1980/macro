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


# Debug Logging for Segfault Diagnosis
import logging
import sys
import os

def setup_debug_logging():
    try:
        log_path = os.path.join(os.path.expanduser("~"), "Desktop", "automacro_debug.log")
        logging.basicConfig(
            filename=log_path,
            level=logging.DEBUG,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        return logging.getLogger("startup")
    except Exception:
        return logging.getLogger("startup_fallback")

logger = setup_debug_logging()
logger.info("AutoMacro starting up...")
logger.info(f"Python: {sys.version}")
logger.info(f"Platform: {sys.platform}")

from app.utils.common import setup_logging as app_setup_logging
# We can continue using the file logger or switch/add the app one.
# For now let's rely on the global file config we just set.


def main():
    app = QApplication(sys.argv)
    
    # Global references to keep windows alive
    windows = {}
    
    def on_edit_workflow(name):
        try:
            editor = WorkflowEditor(name, lambda: windows.pop("editor", None))
            windows["editor"] = editor
            editor.show()
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            # Show error logic even if we don't have a parent window easily accessible, 
            # we can use the active window or None (if app exists)
            logger.error(f"Failed to open editor: {e}")
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Icon.Critical)
            msg.setText(f"Error opening editor for '{name}':\n{e}")
            msg.exec()
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
        
        # Connect Input Signal
        def on_input_requested(prompt):
            from PyQt6.QtWidgets import QInputDialog
            items = ["1", "2", "3", "4", "5"]
            val, ok = QInputDialog.getItem(runner_window, "입력 요청", prompt, items, 0, False)
            if ok and val:
                runner.set_input_value(val)
            else:
                runner.set_input_value("1") # Default fallback
                
        runner.request_input_signal.connect(on_input_requested)
        
        t = threading.Thread(target=runner.run)
        t.start()
        
    manager = WorkflowManager(on_edit_workflow, on_run_workflow)
    windows["manager"] = manager
    manager.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
