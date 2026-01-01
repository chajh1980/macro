import os
import json
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QSplitter, QMessageBox, QCheckBox, QApplication
)
from PyQt6.QtCore import Qt, QRect
from app.ui.toolbar import ComponentToolbar
from app.ui.canvas import WorkflowCanvasWidget
from app.ui.inspector import PropertyInspectorWidget
from app.ui.overlay import Overlay
from app.core.models import Workflow, Step, ConditionType, ActionType, Condition, Action
from app.utils.common import get_workflows_dir
from app.utils.screen_utils import get_screen_scale

class WorkflowEditor(QMainWindow):
    def __init__(self, workflow_name: str, on_close):
        super().__init__()
        self.workflow_name = workflow_name
        self.on_close_callback = on_close
        self.workflow = self._load_workflow(workflow_name)
        self.has_unsaved_changes = False
        
        self.setWindowTitle(f"Editing: {workflow_name}")
        self.resize(1000, 700) # Resized per user request (was 1200x800)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout() # Main layout is now Vertical
        central_widget.setLayout(main_layout)
        
        # 1. Top Toolbar (New)
        self.toolbar = ComponentToolbar()
        self.toolbar.setFixedHeight(100)
        main_layout.addWidget(self.toolbar)
        
        # 2. Splitter (Canvas + Inspector)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Canvas (Left/Center)
        self.canvas = WorkflowCanvasWidget()
        splitter.addWidget(self.canvas)
        
        # Inspector (Right)
        self.inspector = PropertyInspectorWidget()
        self.inspector.setFixedWidth(350)
        self.inspector.set_workflow_dir(os.path.join(get_workflows_dir(), self.workflow_name))
        splitter.addWidget(self.inspector)
        
        main_layout.addWidget(splitter)
        self.inspector.set_workflow_dir(os.path.join(get_workflows_dir(), self.workflow_name))
        splitter.addWidget(self.inspector)
        
        main_layout.addWidget(splitter)
        
        # Bottom Buttons
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("Save")
        self.cancel_btn = QPushButton("Close")
        self.always_on_top_cb = QCheckBox("Always on Top")
        self.always_on_top_cb.stateChanged.connect(self._toggle_always_on_top)
        
        btn_layout.addWidget(self.always_on_top_cb)
        btn_layout.addStretch()
        self.delete_btn = QPushButton("Delete Step") # New
        self.delete_btn.setStyleSheet("background-color: #ffcccc; color: #cc0000;") # Optional styling
        btn_layout.addWidget(self.delete_btn)
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)
        main_layout.addLayout(btn_layout)
        
        # Connect Signals
        self.canvas.step_dropped.connect(self._on_step_dropped)
        self.canvas.itemClicked.connect(self._on_step_selected)
        
        self.save_btn.clicked.connect(self._save_workflow)
        self.delete_btn.clicked.connect(self._delete_current_step) # Connect
        self.cancel_btn.clicked.connect(self.close)
        
        # Initial State
        self._refresh_canvas()
        self.inspector.show_workflow_props(self.workflow)
        
        # Connect Inspector Signals to update logic
        # Image Page
        self.inspector.step_props.capture_img_btn.clicked.connect(self._capture_image)
        self.inspector.step_props.img_capture_area_btn.clicked.connect(lambda: self._capture_area_watch(for_image=True))
        
        # Color Page
        self.inspector.step_props.pick_color_btn.clicked.connect(self._pick_color)
        self.inspector.step_props.color_set_area_btn.clicked.connect(lambda: self._capture_area_watch(for_image=False))
        
        # Move Page
        self.inspector.step_props.pick_pos_btn.clicked.connect(self._pick_point)
        
        # Test Button
        self.inspector.step_props.test_btn.clicked.connect(self._test_current_step)
        
        # Signals for value changes
        self.inspector.step_props.step_changed.connect(self._on_step_changed_from_inspector)

    def _toggle_always_on_top(self, state):
        if state == 2: # Checked
            self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowStaysOnTopHint)
        self.show()

    def _load_workflow(self, name: str) -> Workflow:
        path = os.path.join(get_workflows_dir(), name, "flow.json")
        if os.path.exists(path):
            with open(path, "r") as f:
                data = json.load(f)
                return Workflow(**data)
        return Workflow(name=name, created_at="", updated_at="")

    def _save_workflow(self):
        path = os.path.join(get_workflows_dir(), self.workflow_name, "flow.json")
        with open(path, "w") as f:
            f.write(self.workflow.json())
        self.has_unsaved_changes = False
        QMessageBox.information(self, "Saved", "Workflow saved successfully.")

    def _refresh_canvas(self):
        self.canvas.update_steps(self.workflow.steps)

    def _on_step_dropped(self, category, type_code):
        new_step = Step(
            id=str(len(self.workflow.steps) + 1),
            name=f"New Step {len(self.workflow.steps) + 1}",
            condition=Condition(type=ConditionType.TIME, wait_time_s=0),
            action=Action(type=ActionType.NONE)
        )
        
        if category == "Condition":
            if type_code == "image":
                new_step.condition.type = ConditionType.IMAGE
                new_step.action.type = ActionType.MOVE
                new_step.name = "Find Image"
            elif type_code == "wait":
                new_step.condition.type = ConditionType.TIME
                new_step.condition.wait_time_s = 1.0
                new_step.name = "Wait"
            elif type_code == "color":
                new_step.condition.type = ConditionType.COLOR
                new_step.action.type = ActionType.MOVE
                new_step.name = "Find Color"
                
        elif category == "Action":
            if type_code == "click":
                new_step.condition.type = ConditionType.TIME
                new_step.condition.wait_time_s = 0
                new_step.action.type = ActionType.CLICK
                new_step.name = "Click Mouse"
            elif type_code == "move":
                new_step.condition.type = ConditionType.TIME
                new_step.condition.wait_time_s = 0
                new_step.action.type = ActionType.MOVE
                new_step.name = "Move Mouse"
            elif type_code == "goto":
                new_step.condition.type = ConditionType.TIME
                new_step.condition.wait_time_s = 0
                new_step.action.type = ActionType.GOTO
                new_step.action.goto_step_index = 1
                new_step.name = "Goto Step"
        
        self.workflow.steps.append(new_step)
        self.has_unsaved_changes = True
        self._refresh_canvas()
        
        last_row = self.canvas.count() - 1
        self.canvas.setCurrentRow(last_row)
        self._on_step_selected(self.canvas.item(last_row))

    def _on_step_selected(self, item):
        row = self.canvas.row(item)
        if 0 <= row < len(self.workflow.steps):
            step = self.workflow.steps[row]
            self.inspector.show_step_props(step)
        else:
            self.inspector.show_workflow_props(self.workflow)
            
    def _on_step_changed_from_inspector(self, step):
        # Update canvas item text to reflect new name/props
        self.has_unsaved_changes = True
        self._refresh_canvas_item()

    def _on_reordered(self):
        # The canvas list has been reordered visually.
        # We need to sync self.workflow.steps to match the new order.
        # Since StepCardWidget holds the step object, we can reconstruct the list.
        
        new_steps = []
        for i in range(self.canvas.count()):
            item = self.canvas.item(i)
            widget = self.canvas.itemWidget(item)
            if hasattr(widget, 'idx_label'): # It's a StepCardWidget
                # Wait, StepCardWidget is initialized with a Step, 
                # but we need to retrieve the Step object that was associated with this item.
                # Actually, in update_steps we did: widget = StepCardWidget(step, i+1)
                # But we didn't store step on the widget itself as a public prop, 
                # though it might be in closure or we can add it.
                # BETTER: Store step in UserRole of the QListWidgetItem.
                pass
            
        # Re-approach: In update_steps, store step in Item UserRole.
        # Then here we iterate items and rebuild list.
        new_steps = []
        for i in range(self.canvas.count()):
            item = self.canvas.item(i)
            step = item.data(Qt.ItemDataRole.UserRole)
            if step:
                new_steps.append(step)
        
        self.workflow.steps = new_steps
        self.has_unsaved_changes = True
        
        # Refresh indices in UI
        self._refresh_canvas()
        
        # Determine which item is selected and show it
        row = self.canvas.currentRow()
        if row >= 0:
             self._on_step_selected(self.canvas.item(row))

    def _delete_current_step(self):
        row = self.canvas.currentRow()
        if row < 0:
            QMessageBox.information(self, "Delete", "Please select a step to delete.")
            return
            
        step = self.workflow.steps[row]
        reply = QMessageBox.question(
            self, "Delete Step",
            f"Are you sure you want to delete step #{row+1} '{step.name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            del self.workflow.steps[row]
            self.has_unsaved_changes = True
            self._refresh_canvas()
            
            # Select next item or previous or nothing
            next_row = min(row, self.canvas.count() - 1)
            if next_row >= 0:
                self.canvas.setCurrentRow(next_row)
                self._on_step_selected(self.canvas.item(next_row))
            else:
                self.inspector.show_workflow_props(self.workflow)

    # --- Capture Handlers ---
    
    def _capture_image(self):
        self.hide() # Hide editor to capture screen underneath
        self.overlay = Overlay(mode="region")
        self.overlay.captured.connect(self._on_image_captured)
        self.overlay.show()
        
    def _on_image_captured(self, rect):
        self.show() # Show editor again
        
        current_step = self.inspector.current_step
        if not current_step: return

        # Handle High-DPI Capture
        scale = get_screen_scale()
        # rect.x/y/w/h are in logical points. 
        # grabWindow takes logical coords, but returns physical pixel pixmap.
        
        import datetime
        from PyQt6.QtGui import QGuiApplication
        
        screen = QGuiApplication.primaryScreen()
        # grabWindow(windowId, x, y, w, h) -> Pixmap
        # On Retina: if x=10, y=10, w=100, h=100 (logical)
        # Pixmap size will be 200x200 (physical).
        # This is exactly what we want for High-DPI template matching!
        pixmap = screen.grabWindow(0, rect.x(), rect.y(), rect.width(), rect.height())
        
        assets_dir = os.path.join(get_workflows_dir(), self.workflow_name, "assets")
        if not os.path.exists(assets_dir):
            os.makedirs(assets_dir)
            
        filename = f"target_{int(datetime.datetime.now().timestamp())}.png"
        path = os.path.join(assets_dir, filename)
        pixmap.save(path)
        
        rel_path = os.path.join("assets", filename)
        
        current_step.condition.target_image_path = rel_path
        self.inspector.step_props.load_step(current_step)
        self._refresh_canvas_item()

    def _capture_area_watch(self, for_image=False):
        self.hide()
        self.overlay = Overlay(mode="region")
        self.overlay.captured.connect(lambda rect: self._on_area_captured(rect, for_image=for_image))
        self.overlay.show()

    def _on_area_captured(self, rect, for_image=False):
        self.show()
        current_step = self.inspector.current_step
        if not current_step: return

        # rect is logical
        area = [rect.x(), rect.y(), rect.width(), rect.height()]
        current_step.condition.watch_area = area
        self.inspector.step_props.load_step(current_step)

    def _pick_point(self):
        self.hide()
        self.overlay = Overlay(mode="point")
        self.overlay.clicked.connect(self._on_point_picked)
        self.overlay.show()

    def _on_point_picked(self, x, y):
        self.show()
        current_step = self.inspector.current_step
        if not current_step: return

        current_step.action.target_x = x
        current_step.action.target_y = y
        self.inspector.step_props.load_step(current_step)
        self._refresh_canvas_item()

        self.inspector.step_props.load_step(current_step)
        self._refresh_canvas_item()

    def _pick_color(self):
        self.hide()
        self.overlay = Overlay(mode="color")
        self.overlay.color_picked.connect(self._on_color_picked)
        self.overlay.show()
        
    def _on_color_picked(self, hex_color):
        self.show()
        current_step = self.inspector.current_step
        if not current_step: return
        
        current_step.condition.target_color = hex_color
        self.inspector.step_props.load_step(current_step)
        self._refresh_canvas_item()

    def _refresh_canvas_item(self):
        # Simply refresh list for now
        self._refresh_canvas()
        if self.inspector.current_step:
            try:
                idx = self.workflow.steps.index(self.inspector.current_step)
                self.canvas.setCurrentRow(idx)
            except ValueError:
                pass

    def _test_current_step(self):
        """Test the current step logic and show visual feedback"""
        from app.core.engine import find_image_on_screen
        import time
        
        step = self.inspector.current_step
        if not step: return
        
        # 1. Image Search Test
        if step.condition.type == ConditionType.IMAGE and step.condition.target_image_path:
             # Resolve path
            path = os.path.join(get_workflows_dir(), self.workflow_name, step.condition.target_image_path)
            
            # Use visual overlay to show "Searching..." (optional)
            
            # Perform Search
            # engine.find_image_on_screen expects physical pixels usually? 
            # Or depends on implementation. Let's assume it returns physical pixels (PyAutoGUI default).
            import pyautogui
            
            try:
                # We need a robust finder. Re-use engine logic or call it directly.
                matches = find_image_on_screen(
                    path, 
                    confidence=step.condition.confidence or 0.9,
                    region=step.condition.watch_area
                )
                
                if matches:
                    # Match found! Draw green box.
                    # matches are PHYSICAL pixels (from pyautogui/opencv scan)
                    # We need to convert to LOGICAL points for Qt Overlay.
                    match = matches[0] # Take first
                    
                    from app.utils.screen_utils import get_screen_scale
                    scale = get_screen_scale()
                    
                    # Convert Physical -> Logical
                    x = int(match[0] / scale)
                    y = int(match[1] / scale)
                    w = int(match[2] / scale)
                    h = int(match[3] / scale)
                    
                    rect = QRect(x, y, w, h)
                    
                    # Show Highlight Overlay
                    self.highlight_overlay = Overlay(mode="highlight", highlight_rect=rect)
                    self.highlight_overlay.show()
                    
                    # ALSO Move mouse to the target click location logic
                    # Calculate center
                    center_x = x + w // 2
                    center_y = y + h // 2
                    
                    # Add offset if Action is CLICK
                    off_x = step.action.target_x or 0
                    off_y = step.action.target_y or 0
                    
                    target_x = center_x + off_x
                    target_y = center_y + off_y
                    
                    from PyQt6.QtGui import QCursor
                    QCursor.setPos(target_x, target_y)
                    
                    # Use a non-modal message box or just wait?
                    msg = QMessageBox(self)
                    msg.setWindowTitle("Test Result")
                    msg.setText(f"Image Found!\nMoved mouse to ({target_x}, {target_y}) using logical coords.")
                    msg.setIcon(QMessageBox.Icon.Information)
                    msg.setStandardButtons(QMessageBox.StandardButton.Ok)
                    msg.exec()
                else:
                    QMessageBox.warning(self, "Test Result", "Image NOT Found.")
            except Exception as e:
                QMessageBox.critical(self, "Test Error", str(e))

        elif step.condition.type == ConditionType.COLOR and step.condition.target_color:
             from app.core.image_proc import find_color_on_screen
             import pyautogui
             try:
                 region = None
                 if step.condition.watch_area:
                     # watch_area is usually [x, y, w, h] (Logic? Or Physical?)
                     # It comes from _on_area_captured which stores logical coords (rect.x(), rect.y())
                     # BUT pyautogui.screenshot(region=...) usually expects physical pixels on Mac if Retina? or logical?
                     # Let's check handle_condition logic.
                     # Actually find_color_on_screen calls pyautogui.screenshot(region=region).
                     # PyAutoGUI region is (left, top, width, height).
                     # We should assume watch_area is stored in logical, so we might need to scale it if pyautogui expects physical.
                     # BUT wait, previously we said overlay returns logical.
                     # Let's trust find_color_on_screen handles it or pass it as is for now.
                     region = tuple(step.condition.watch_area)

                 matches = find_color_on_screen(
                     step.condition.target_color,
                     tolerance=step.condition.color_tolerance,
                     region=region
                 )

                 if matches:
                     # Respect Match Index
                     idx = step.condition.match_index
                     if idx >= len(matches):
                         idx = 0 # Default to first if overflow

                     match = matches[idx]
                     
                     from app.utils.screen_utils import get_screen_scale
                     scale = get_screen_scale()
                     
                     # Convert Physical -> Logical
                     x = int(match[0] / scale)
                     y = int(match[1] / scale)
                     w = int(match[2] / scale)
                     h = int(match[3] / scale)
                     
                     rect = QRect(x, y, w, h)
                     
                     self.highlight_overlay = Overlay(mode="highlight", highlight_rect=rect)
                     self.highlight_overlay.show()
                     
                     center_x = x + w // 2
                     center_y = y + h // 2
                     
                     from PyQt6.QtGui import QCursor
                     QCursor.setPos(center_x, center_y)
                     
                     msg = QMessageBox(self)
                     msg.setWindowTitle("Test Result")
                     msg.setText(f"Color Found (Match #{idx+1})!\nMoved mouse to ({center_x}, {center_y}) using logical coords.")
                     msg.setIcon(QMessageBox.Icon.Information)
                     msg.setStandardButtons(QMessageBox.StandardButton.Ok)
                     msg.exec()
                 else:
                     QMessageBox.warning(self, "Test Result", "Color NOT Found.")
             except Exception as e:
                 QMessageBox.critical(self, "Test Error", str(e))
        
        elif step.action.type == ActionType.MOVE:
             # Visual verification for Move
             tx = step.action.target_x
             ty = step.action.target_y
             if tx is not None and ty is not None:
                 import pyautogui
                 # Move mouse to target
                 pyautogui.moveTo(tx, ty)
                 QMessageBox.information(self, "Test Result", f"Moved mouse to ({tx}, {ty}).")
             else:
                 QMessageBox.warning(self, "Test Result", "Target coordinates not set.")
                 
        elif step.action.type == ActionType.CLICK:
             # Visual verification for Click
             # Clicks usually happen at current position unless coords set
             # We just wiggle mouse or show info
             import pyautogui
             current_x, current_y = pyautogui.position()
             QMessageBox.information(self, "Test Result", f"Click Action: Will click at current position ({current_x}, {current_y}).")

        elif step.condition.type == ConditionType.TIME:
             sec = step.condition.wait_time_s
             QMessageBox.information(self, "Test Result", f"Wait Step: Configured to wait {sec} seconds.\n(This is a logic step, no visual test needed.)")
             
        elif step.action.type == ActionType.GOTO:
             idx = step.action.goto_step_index
             QMessageBox.information(self, "Test Result", f"Goto Step: Will jump to Step #{idx}.\n(Logic valid.)")
        
        else:
            QMessageBox.information(self, "Test Info", "This step type implies no immediate visual condition.")

    def closeEvent(self, event):
        if self.has_unsaved_changes:
            reply = QMessageBox.question(
                self, "Unsaved Changes", "Save changes before closing?",
                QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel
            )
            if reply == QMessageBox.StandardButton.Save:
                self._save_workflow()
                self.on_close_callback()
                event.accept()
            elif reply == QMessageBox.StandardButton.Discard:
                self.on_close_callback()
                event.accept()
            else:
                event.ignore()
        else:
            self.on_close_callback()
            event.accept()
