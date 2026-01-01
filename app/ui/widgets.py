import os
import PyQt6.QtWidgets 
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox, QSpinBox, 
    QDoubleSpinBox, QLineEdit, QGroupBox, QFormLayout, QCheckBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from app.core.models import Step, StepType, ConditionType, ActionType

class StepPropertiesWidget(QWidget):
    step_changed = pyqtSignal(Step)
    
class StepPropertiesWidget(QWidget):
    step_changed = pyqtSignal(Step)
    
    def __init__(self):
        super().__init__()
        self.current_step = None
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        
        # --- Top: Common Fields ---
        top_group = QGroupBox("General")
        top_layout = QFormLayout()
        top_group.setLayout(top_layout)
        
        self.name_edit = QLineEdit()
        self.command_combo = QComboBox()
        self.command_combo.addItems(["Find Image", "Find Color", "Move Mouse", "Click Mouse", "Wait", "Loop/Goto"])
        self.command_combo.setEnabled(False) # Prevent changing type after creation (User Request)
        
        top_layout.addRow("Step Name:", self.name_edit)
        top_layout.addRow("Action Type:", self.command_combo)
        self.layout.addWidget(top_group)
        
        # --- Middle: Stacked Type Settings ---
        self.stack = PyQt6.QtWidgets.QStackedWidget()
        self.layout.addWidget(self.stack)
        
        # 0. Image Page (Find Image -> Move to it)
        self.page_image = QWidget()
        p_img_layout = QFormLayout()
        self.page_image.setLayout(p_img_layout)
        
        self.img_path_edit = QLineEdit()
        self.capture_img_btn = QPushButton("Capture Image")
        row_img = QHBoxLayout()
        row_img.addWidget(self.img_path_edit)
        row_img.addWidget(self.capture_img_btn)
        
        self.img_preview = QLabel("No Image")
        self.img_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.img_preview.setFixedSize(200, 100)
        self.img_preview.setStyleSheet("border: 1px dashed gray;")
        
        self.img_confidence = QDoubleSpinBox()
        self.img_confidence.setRange(0.1, 1.0)
        self.img_confidence.setSingleStep(0.05)
        self.img_confidence.setValue(0.9)
        
        self.img_full_window_cb = QCheckBox("Full Screen")
        self.img_full_window_cb.setChecked(True)
        self.img_watch_area_edit = QLineEdit()
        self.img_watch_area_edit.setEnabled(False)
        self.img_capture_area_btn = QPushButton("Set Area")
        self.img_capture_area_btn.setEnabled(False)
        row_img_area = QHBoxLayout()
        row_img_area.addWidget(self.img_full_window_cb)
        row_img_area.addWidget(self.img_watch_area_edit)
        row_img_area.addWidget(self.img_capture_area_btn)
        
        # Image Offset (Moves mouse to center + offset)
        self.img_offset_x = QSpinBox()
        self.img_offset_x.setRange(-9999, 9999)
        self.img_offset_y = QSpinBox()
        self.img_offset_y.setRange(-9999, 9999)
        row_img_offset = QHBoxLayout()
        row_img_offset.addWidget(QLabel("X:"))
        row_img_offset.addWidget(self.img_offset_x)
        row_img_offset.addWidget(QLabel("Y:"))
        row_img_offset.addWidget(self.img_offset_y)
        
        # Retry Policy (Await) for Image
        grp_retry = QGroupBox("Retry Policy (Await)")
        layout_retry = QFormLayout()
        grp_retry.setLayout(layout_retry)
        
        self.retry_timeout = QDoubleSpinBox()
        self.retry_timeout.setRange(0, 3600)
        self.retry_timeout.setValue(5.0)
        self.retry_interval = QSpinBox()
        self.retry_interval.setRange(10, 10000)
        self.retry_interval.setValue(500)
        self.retry_interval.setSuffix(" ms")
        
        layout_retry.addRow("Timeout (s):", self.retry_timeout)
        layout_retry.addRow("Check Interval:", self.retry_interval)
        
        p_img_layout.addRow("Image Path:", row_img)
        p_img_layout.addRow("Preview:", self.img_preview)
        p_img_layout.addRow("Confidence:", self.img_confidence)
        p_img_layout.addRow("Search Area:", row_img_area)
        p_img_layout.addRow("Move Offset:", row_img_offset)
        p_img_layout.addRow(grp_retry) # Add Retry Group
        
        self.stack.addWidget(self.page_image)
        
        # 1. Color Page (New)
        self.page_color = QWidget()
        p_color_layout = QFormLayout()
        self.page_color.setLayout(p_color_layout)
        
        # Target Color
        self.color_val_edit = QLineEdit("#FFFFFF")
        self.pick_color_btn = QPushButton("Pick Color")
        self.color_preview = QLabel()
        self.color_preview.setFixedSize(24, 24)
        self.color_preview.setStyleSheet("background-color: #FFFFFF; border: 1px solid black;")
        
        row_color_target = QHBoxLayout()
        row_color_target.addWidget(self.color_preview)
        row_color_target.addWidget(self.color_val_edit)
        row_color_target.addWidget(self.pick_color_btn)
        
        # Tolerance
        self.color_tolerance = QSpinBox()
        self.color_tolerance.setRange(0, 100)
        self.color_tolerance.setValue(10)
        
        # Match Index (Which blob to pick)
        self.color_match_index = QSpinBox()
        self.color_match_index.setRange(0, 99)
        
        # Search Area (Re-use logic similar to Image)
        self.color_full_window_cb = QCheckBox("Full Screen")
        self.color_full_window_cb.setChecked(True)
        self.color_watch_area_edit = QLineEdit()
        self.color_watch_area_edit.setEnabled(False)
        self.color_set_area_btn = QPushButton("Set Area")
        self.color_set_area_btn.setEnabled(False)
        row_color_area = QHBoxLayout()
        row_color_area.addWidget(self.color_full_window_cb)
        row_color_area.addWidget(self.color_watch_area_edit)
        row_color_area.addWidget(self.color_set_area_btn)
        
        # Retry Policy (Await) for Color - Shared Widgets? No, separate for safety/simplicity
        grp_retry_color = QGroupBox("Retry Policy (Await)")
        layout_retry_color = QFormLayout()
        grp_retry_color.setLayout(layout_retry_color)
        
        self.retry_timeout_color = QDoubleSpinBox()
        self.retry_timeout_color.setRange(0, 3600)
        self.retry_timeout_color.setValue(5.0)
        self.retry_interval_color = QSpinBox()
        self.retry_interval_color.setRange(10, 10000)
        self.retry_interval_color.setValue(500)
        self.retry_interval_color.setSuffix(" ms")
        
        layout_retry_color.addRow("Timeout (s):", self.retry_timeout_color)
        layout_retry_color.addRow("Check Interval:", self.retry_interval_color)
        
        p_color_layout.addRow("Target Color:", row_color_target)
        p_color_layout.addRow("Tolerance:", self.color_tolerance)
        p_color_layout.addRow("Match Index:", self.color_match_index)
        p_color_layout.addRow("Search Area:", row_color_area)
        p_color_layout.addRow(grp_retry_color) # Add Retry Group
        
        self.stack.addWidget(self.page_color)
        
        # 2. Move Page (Re-indexed from 1 -> 2)
        # Note: Command Combo list: ["Find Image", "Find Color", "Move Mouse", "Click Mouse", "Wait", "Loop/Goto"]
        # Index 0: Image
        # Index 1: Color
        # Index 2: Move
        # Index 3: Click
        # Index 4: Wait
        # Index 5: Goto

        
        # 1. Move Page
        self.page_move = QWidget()
        p_move_layout = QFormLayout()
        self.page_move.setLayout(p_move_layout)
        
        self.move_x = QSpinBox()
        self.move_x.setRange(0, 9999)
        self.move_y = QSpinBox()
        self.move_y.setRange(0, 9999)
        self.pick_pos_btn = QPushButton("Pick Position")
        
        p_move_layout.addRow("Target X:", self.move_x)
        p_move_layout.addRow("Target Y:", self.move_y)
        p_move_layout.addRow("", self.pick_pos_btn)
        
        self.stack.addWidget(self.page_move)
        
        # 2. Click Page (New)
        self.page_click = QWidget()
        p_click_layout = QFormLayout()
        self.page_click.setLayout(p_click_layout)
        
        self.click_desc = QLabel("Clicks the current mouse position.")
        self.click_desc.setStyleSheet("color: gray;")
        p_click_layout.addRow(self.click_desc)
        
        self.stack.addWidget(self.page_click)
        
        # 3. Wait Page
        self.page_wait = QWidget()
        p_wait_layout = QFormLayout()
        self.page_wait.setLayout(p_wait_layout)
        
        self.wait_spin = QDoubleSpinBox()
        self.wait_spin.setRange(0, 3600)
        p_wait_layout.addRow("Duration (sec):", self.wait_spin)
        
        self.stack.addWidget(self.page_wait)
        
        # 4. Goto Page
        self.page_goto = QWidget()
        p_goto_layout = QFormLayout()
        self.page_goto.setLayout(p_goto_layout)
        
        self.goto_spin = QSpinBox()
        self.goto_spin.setRange(1, 9999)
        p_goto_layout.addRow("Jump to Step #:", self.goto_spin)
        
        self.stack.addWidget(self.page_goto)
        
        # --- Bottom: Tools ---
        self.layout.addStretch()
        self.test_btn = QPushButton("Test This Step")
        self.layout.addWidget(self.test_btn)
        
        # --- Logic & Connections ---
        # Mapping: Combo Index -> Stack Index
        # ["Find Image", "Move Mouse", "Click Mouse", "Wait", "Loop/Goto"]
        # Indices: 0, 1, 2, 3, 4
        
        self.command_combo.currentIndexChanged.connect(self._on_combo_changed)
        
        # Connect change signals
        # Name
        self.name_edit.textChanged.connect(self._sync_data)
        
        # Image
        self.img_path_edit.textChanged.connect(self._sync_data)
        self.img_confidence.valueChanged.connect(self._sync_data)
        self.img_full_window_cb.toggled.connect(self._on_img_full_window_toggled)
        self.img_watch_area_edit.textChanged.connect(self._sync_data)
        self.img_offset_x.valueChanged.connect(self._sync_data)
        self.img_offset_y.valueChanged.connect(self._sync_data)
        
        # Color
        self.color_val_edit.textChanged.connect(self._sync_data)
        self.color_val_edit.textChanged.connect(self._update_color_preview) # Preview update
        self.color_tolerance.valueChanged.connect(self._sync_data)
        self.color_match_index.valueChanged.connect(self._sync_data)
        self.color_full_window_cb.toggled.connect(self._on_color_full_window_toggled)
        self.color_watch_area_edit.textChanged.connect(self._sync_data)
        
        # Move
        self.move_x.valueChanged.connect(self._sync_data)
        self.move_y.valueChanged.connect(self._sync_data)
        
        # Wait
        self.wait_spin.valueChanged.connect(self._sync_data)
        
        # Goto
        self.goto_spin.valueChanged.connect(self._sync_data)
        
        # Retry Policy Signals
        self.retry_timeout.valueChanged.connect(self._sync_data)
        self.retry_interval.valueChanged.connect(self._sync_data)
        self.retry_timeout_color.valueChanged.connect(self._sync_data)
        self.retry_interval_color.valueChanged.connect(self._sync_data)

    def _on_combo_changed(self, index):
        self.stack.setCurrentIndex(index)
        self._sync_data()
        
    def _on_img_full_window_toggled(self, checked):
        self.img_watch_area_edit.setEnabled(not checked)
        self.img_capture_area_btn.setEnabled(not checked)
        if checked: self.img_watch_area_edit.clear()
        self._sync_data()

    def _on_color_full_window_toggled(self, checked):
        self.color_watch_area_edit.setEnabled(not checked)
        self.color_set_area_btn.setEnabled(not checked)
        if checked: self.color_watch_area_edit.clear()
        self._sync_data()
        
    def _update_color_preview(self, text):
        try:
             self.color_preview.setStyleSheet(f"background-color: {text}; border: 1px solid black;")
        except: pass
        
    def load_step(self, step: Step):
        self.current_step = step
        self.blockSignals(True) # Prevent sync back while loading
        
        self.name_edit.setText(step.name)
        
        # Determine Mode
        mode_idx = 0 # Default Image
        if step.action.type == ActionType.GOTO:
            mode_idx = 5
        elif step.condition.type == ConditionType.TIME:
            if step.action.type == ActionType.NONE:
                mode_idx = 4 # Wait
            else:
                 # Move or Click
                 if step.action.type == ActionType.CLICK:
                     mode_idx = 3 # Click
                 elif step.action.type == ActionType.MOVE:
                     mode_idx = 2 # Move Logic check
        elif step.condition.type == ConditionType.COLOR:
            mode_idx = 1
        elif step.condition.type == ConditionType.IMAGE:
            mode_idx = 0
            
        self.command_combo.setCurrentIndex(mode_idx)
        self.stack.setCurrentIndex(mode_idx)

        # Populate Fields
        # 0. Image
        self.img_path_edit.setText(step.condition.target_image_path or "")
        self.img_confidence.setValue(step.condition.confidence or 0.9)
        if step.condition.watch_area:
             self.img_full_window_cb.setChecked(False)
             self.img_watch_area_edit.setText(str(step.condition.watch_area))
        else:
             self.img_full_window_cb.setChecked(True)
        # Retry Image
        self.retry_timeout.setValue(step.condition.retry_timeout_s if step.condition.retry_timeout_s is not None else 5.0)
        self.retry_interval.setValue(step.condition.retry_interval_ms if step.condition.retry_interval_ms is not None else 500)
             
        # 1. Color
        self.color_val_edit.setText(step.condition.target_color or "#FFFFFF")
        self.color_tolerance.setValue(step.condition.color_tolerance)
        self.color_match_index.setValue(step.condition.match_index)
        if step.condition.watch_area and step.condition.type == ConditionType.COLOR:
             self.color_full_window_cb.setChecked(False)
             self.color_watch_area_edit.setText(str(step.condition.watch_area))
        else:
             self.color_full_window_cb.setChecked(True)
        self._update_color_preview(step.condition.target_color or "#FFFFFF")
        # Retry Color
        self.retry_timeout_color.setValue(step.condition.retry_timeout_s if step.condition.retry_timeout_s is not None else 5.0)
        self.retry_interval_color.setValue(step.condition.retry_interval_ms if step.condition.retry_interval_ms is not None else 500)
        
        # 2. Offsets (Image action uses Move params too)
        # ... existing ...
        tx = step.action.target_x or 0
        ty = step.action.target_y or 0
        
        self.img_offset_x.setValue(tx)
        self.img_offset_y.setValue(ty)
        
        self.move_x.setValue(tx)
        self.move_y.setValue(ty)
        
        # 4. Wait
        self.wait_spin.setValue(step.condition.wait_time_s)
        
        # 5. Goto
        self.goto_spin.setValue(step.action.goto_step_index or 1)
        
        # Preview
        if mode_idx == 0:
            self._update_preview(step.condition.target_image_path)
        
        self.blockSignals(False)
        
    def _sync_data(self):
        if not self.current_step or self.signalsBlocked(): return
        
        idx = self.command_combo.currentIndex()
        self.current_step.name = self.name_edit.text()
        
        if idx == 0: # Find Image
            self.current_step.condition.type = ConditionType.IMAGE
            self.current_step.action.type = ActionType.MOVE
            self.current_step.condition.target_image_path = self.img_path_edit.text()
            self.current_step.condition.confidence = self.img_confidence.value()
            self.current_step.action.target_x = self.img_offset_x.value()
            self.current_step.action.target_y = self.img_offset_y.value()
            # Retry
            self.current_step.condition.retry_timeout_s = self.retry_timeout.value()
            self.current_step.condition.retry_interval_ms = self.retry_interval.value()
            
            try:
                txt = self.img_watch_area_edit.text()
                self.current_step.condition.watch_area = eval(txt) if txt else None
            except: pass
            
        elif idx == 1: # Find Color
            self.current_step.condition.type = ConditionType.COLOR
            self.current_step.action.type = ActionType.MOVE
            self.current_step.condition.target_color = self.color_val_edit.text()
            self.current_step.condition.color_tolerance = self.color_tolerance.value()
            self.current_step.condition.match_index = self.color_match_index.value()
            # Retry
            self.current_step.condition.retry_timeout_s = self.retry_timeout_color.value()
            self.current_step.condition.retry_interval_ms = self.retry_interval_color.value()
            
            try:
                txt = self.color_watch_area_edit.text()
                self.current_step.condition.watch_area = eval(txt) if txt else None
            except: pass
            
        elif idx == 2: # Move Mouse
            self.current_step.condition.type = ConditionType.TIME
            self.current_step.condition.wait_time_s = 0
            self.current_step.action.type = ActionType.MOVE
            self.current_step.action.target_x = self.move_x.value()
            self.current_step.action.target_y = self.move_y.value()
            
        elif idx == 3: # Click Mouse
            self.current_step.condition.type = ConditionType.TIME
            self.current_step.condition.wait_time_s = 0
            self.current_step.action.type = ActionType.CLICK
            
        elif idx == 4: # Wait
            self.current_step.condition.type = ConditionType.TIME
            self.current_step.action.type = ActionType.NONE
            self.current_step.condition.wait_time_s = self.wait_spin.value()
            
        elif idx == 5: # Goto
            self.current_step.condition.type = ConditionType.TIME
            self.current_step.condition.wait_time_s = 0
            self.current_step.action.type = ActionType.GOTO
            self.current_step.action.goto_step_index = self.goto_spin.value()
            
        self.step_changed.emit(self.current_step)

    def set_workflow_dir(self, path):
         self.workflow_dir = path
         
    def _update_preview(self, path):
        # ... logic as before ...
        if path and hasattr(self, 'workflow_dir') and not os.path.isabs(path):
             path = os.path.join(self.workflow_dir, path)
        if path and os.path.exists(path):
            from PyQt6.QtGui import QPixmap
            pm = QPixmap(path)
            if not pm.isNull():
                self.img_preview.setPixmap(pm.scaled(200, 100, Qt.AspectRatioMode.KeepAspectRatio))
                self.img_preview.setText("")
                return
        self.img_preview.setText("No Image")
