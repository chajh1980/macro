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
        self.command_combo.addItems(["Find Image", "Find Color", "Move Mouse", "Click Mouse", "Wait", "Loop/Goto", "Await"])
        self.command_combo.setEnabled(False) # Prevent changing type
        
        top_layout.addRow("Step Name:", self.name_edit)
        top_layout.addRow("Step Type:", self.command_combo)
        self.layout.addWidget(top_group)
        
        # --- Stacked Pages ---
        self.stack = PyQt6.QtWidgets.QStackedWidget()
        self.layout.addWidget(self.stack)
        
        # 0. Find Image
        self.page_image = QWidget()
        layout_img = QFormLayout()
        self.page_image.setLayout(layout_img)
        
        self.img_path_edit = QLineEdit()
        self.capture_img_btn = QPushButton("Capture Image")
        row_img = QHBoxLayout(); row_img.addWidget(self.img_path_edit); row_img.addWidget(self.capture_img_btn)
        
        self.img_preview = QLabel("No Image")
        self.img_preview.setFixedSize(200, 100); self.img_preview.setStyleSheet("border: 1px dashed gray;")
        
        self.img_confidence = QDoubleSpinBox(); self.img_confidence.setRange(0.1, 1.0); self.img_confidence.setValue(0.9); self.img_confidence.setSingleStep(0.05)
        self.img_full_window_cb = QCheckBox("Full Screen"); self.img_full_window_cb.setChecked(True)
        self.img_watch_area_edit = QLineEdit(); self.img_watch_area_edit.setEnabled(False)
        self.img_capture_area_btn = QPushButton("Set Area"); self.img_capture_area_btn.setEnabled(False)
        row_area = QHBoxLayout(); row_area.addWidget(self.img_full_window_cb); row_area.addWidget(self.img_watch_area_edit); row_area.addWidget(self.img_capture_area_btn)
        
        self.img_offset_x = QSpinBox(); self.img_offset_x.setRange(-9999, 9999)
        self.img_offset_y = QSpinBox(); self.img_offset_y.setRange(-9999, 9999)
        row_offset = QHBoxLayout(); row_offset.addWidget(QLabel("X:")); row_offset.addWidget(self.img_offset_x); row_offset.addWidget(QLabel("Y:")); row_offset.addWidget(self.img_offset_y)
        
        layout_img.addRow("Image Path:", row_img)
        layout_img.addRow("Preview:", self.img_preview)
        layout_img.addRow("Confidence:", self.img_confidence)
        layout_img.addRow("Search Area:", row_area)
        layout_img.addRow("Action Move Offset:", row_offset)
        self.stack.addWidget(self.page_image)
        
        # 1. Find Color
        self.page_color = QWidget()
        layout_col = QFormLayout()
        self.page_color.setLayout(layout_col)
        
        self.color_val_edit = QLineEdit("#FFFFFF")
        self.pick_color_btn = QPushButton("Pick Color")
        self.color_preview = QLabel(); self.color_preview.setFixedSize(24, 24); self.color_preview.setStyleSheet("background: #FFF; border: 1px solid black;")
        row_col = QHBoxLayout(); row_col.addWidget(self.color_preview); row_col.addWidget(self.color_val_edit); row_col.addWidget(self.pick_color_btn)
        
        self.color_tolerance = QSpinBox(); self.color_tolerance.setRange(0, 100); self.color_tolerance.setValue(10)
        self.color_match_index = QSpinBox(); self.color_match_index.setRange(0, 99)
        self.color_full_window_cb = QCheckBox("Full Screen"); self.color_full_window_cb.setChecked(True)
        self.color_watch_area_edit = QLineEdit(); self.color_watch_area_edit.setEnabled(False)
        self.color_set_area_btn = QPushButton("Set Area"); self.color_set_area_btn.setEnabled(False)
        row_area_col = QHBoxLayout(); row_area_col.addWidget(self.color_full_window_cb); row_area_col.addWidget(self.color_watch_area_edit); row_area_col.addWidget(self.color_set_area_btn)
        
        layout_col.addRow("Target Color:", row_col)
        layout_col.addRow("Tolerance:", self.color_tolerance)
        layout_col.addRow("Match Index:", self.color_match_index)
        layout_col.addRow("Search Area:", row_area_col)
        self.stack.addWidget(self.page_color)
        
        # 2. Move Mouse
        self.page_move = QWidget()
        layout_move = QFormLayout()
        self.page_move.setLayout(layout_move)
        
        self.move_x = QSpinBox(); self.move_x.setRange(0, 9999)
        self.move_y = QSpinBox(); self.move_y.setRange(0, 9999)
        self.pick_pos_btn = QPushButton("Pick Position")
        layout_move.addRow("Target X:", self.move_x)
        layout_move.addRow("Target Y:", self.move_y)
        layout_move.addRow("", self.pick_pos_btn)
        self.stack.addWidget(self.page_move)
        
        # 3. Click Mouse
        self.page_click = QWidget()
        layout_click = QFormLayout()
        self.page_click.setLayout(layout_click)
        self.click_desc = QLabel("Clicks the current mouse position (or previous Move target).")
        self.click_desc.setStyleSheet("color: gray;")
        layout_click.addRow(self.click_desc)
        self.stack.addWidget(self.page_click)
        
        # 4. Wait
        self.page_wait = QWidget()
        layout_wait = QFormLayout()
        self.page_wait.setLayout(layout_wait)
        self.wait_spin = QDoubleSpinBox(); self.wait_spin.setRange(0, 3600)
        layout_wait.addRow("Duration (s):", self.wait_spin)
        self.stack.addWidget(self.page_wait)
        
        # 5. Loop/Goto
        self.page_goto = QWidget()
        layout_goto = QFormLayout()
        self.page_goto.setLayout(layout_goto)
        self.goto_spin = QSpinBox(); self.goto_spin.setRange(1, 9999)
        layout_goto.addRow("Jump to Step #:", self.goto_spin)
        self.stack.addWidget(self.page_goto)
        
        # 6. Await
        self.page_await = QWidget()
        layout_await = QFormLayout()
        self.page_await.setLayout(layout_await)
        self.await_timeout = QDoubleSpinBox(); self.await_timeout.setRange(0, 3600); self.await_timeout.setValue(10.0)
        self.await_interval = QSpinBox(); self.await_interval.setRange(10, 10000); self.await_interval.setValue(500); self.await_interval.setSuffix(" ms")
        layout_await.addRow(QLabel("Waits for child steps to succeed."))
        layout_await.addRow("Max Duration (Limit) (s):", self.await_timeout)
        layout_await.addRow("Retry Delay (Interval):", self.await_interval)
        self.stack.addWidget(self.page_await)
        
        # --- Bottom ---
        self.layout.addStretch()
        self.test_btn = QPushButton("Test This Step")
        self.layout.addWidget(self.test_btn)
        
        # --- Connections ---
        self.command_combo.currentIndexChanged.connect(self._on_combo_changed)
        
        self.name_edit.textChanged.connect(self._sync_data)
        
        # Image
        self.img_path_edit.textChanged.connect(self._sync_data)
        self.img_confidence.valueChanged.connect(self._sync_data)
        self.img_full_window_cb.toggled.connect(self._on_img_fullscreen_toggled)
        self.img_watch_area_edit.textChanged.connect(self._sync_data)
        self.img_offset_x.valueChanged.connect(self._sync_data)
        self.img_offset_y.valueChanged.connect(self._sync_data)
        
        # Color
        self.color_val_edit.textChanged.connect(self._sync_data)
        self.color_val_edit.textChanged.connect(self._update_color_preview)
        self.color_tolerance.valueChanged.connect(self._sync_data)
        self.color_match_index.valueChanged.connect(self._sync_data)
        self.color_full_window_cb.toggled.connect(self._on_color_fullscreen_toggled)
        self.color_watch_area_edit.textChanged.connect(self._sync_data)
        
        # Move
        self.move_x.valueChanged.connect(self._sync_data)
        self.move_y.valueChanged.connect(self._sync_data)
        
        # Wait
        self.wait_spin.valueChanged.connect(self._sync_data)
        
        # Goto
        self.goto_spin.valueChanged.connect(self._sync_data)
        
        # Await
        self.await_timeout.valueChanged.connect(self._sync_data)
        self.await_interval.valueChanged.connect(self._sync_data)
        
    def _on_combo_changed(self, idx):
        self.stack.setCurrentIndex(idx)
        self._sync_data()
        
    def _on_img_fullscreen_toggled(self, checked):
        self.img_watch_area_edit.setEnabled(not checked)
        self.img_capture_area_btn.setEnabled(not checked)
        if checked: self.img_watch_area_edit.clear()
        self._sync_data()
        
    def _on_color_fullscreen_toggled(self, checked):
        self.color_watch_area_edit.setEnabled(not checked)
        self.color_set_area_btn.setEnabled(not checked)
        if checked: self.color_watch_area_edit.clear()
        self._sync_data()
        
    def _update_color_preview(self, text):
        try: self.color_preview.setStyleSheet(f"background: {text}; border: 1px solid black;")
        except: pass
        
    def load_step(self, step: Step):
        self.current_step = step
        self.blockSignals(True)
        
        self.name_edit.setText(step.name)
        
        # Determine Index
        idx = 0
        if step.type == StepType.AWAIT: idx = 6
        elif step.type == StepType.IF: idx = 6 
        elif step.type == StepType.UNTIL: idx = 6
        elif step.condition.type == ConditionType.IMAGE: idx = 0
        elif step.condition.type == ConditionType.COLOR: idx = 1
        elif step.action.type == ActionType.MOVE and step.condition.type == ConditionType.TIME: idx = 2
        elif step.action.type == ActionType.CLICK and step.condition.type == ConditionType.TIME: idx = 3
        elif step.action.type == ActionType.NONE and step.condition.type == ConditionType.TIME: idx = 4 # Wait
        elif step.action.type == ActionType.GOTO: idx = 5
        
        self.command_combo.setCurrentIndex(idx)
        self.stack.setCurrentIndex(idx)
        
        # Populate
        self.img_path_edit.setText(step.condition.target_image_path or "")
        self.img_confidence.setValue(step.condition.confidence or 0.9)
        if step.condition.watch_area and step.condition.type == ConditionType.IMAGE:
             self.img_full_window_cb.setChecked(False)
             self.img_watch_area_edit.setText(str(step.condition.watch_area))
        else:
             self.img_full_window_cb.setChecked(True)
        
        tx = step.action.target_x or 0
        ty = step.action.target_y or 0
        self.img_offset_x.setValue(tx); self.img_offset_y.setValue(ty)
        self.move_x.setValue(tx); self.move_y.setValue(ty)
        
        self.color_val_edit.setText(step.condition.target_color or "#FFFFFF")
        self._update_color_preview(step.condition.target_color)
        self.color_tolerance.setValue(step.condition.color_tolerance)
        self.color_match_index.setValue(step.condition.match_index)
        if step.condition.watch_area and step.condition.type == ConditionType.COLOR:
             self.color_full_window_cb.setChecked(False)
             self.color_watch_area_edit.setText(str(step.condition.watch_area))
        else:
             self.color_full_window_cb.setChecked(True)
             
        self.wait_spin.setValue(step.condition.wait_time_s)
        self.goto_spin.setValue(step.action.goto_step_index or 1)
        
        self.await_timeout.setValue(step.condition.retry_timeout_s or 10.0)
        self.await_interval.setValue(step.condition.retry_interval_ms or 500)
        
        # Preview
        if idx == 0: self._update_preview(step.condition.target_image_path)
        
        self.blockSignals(False)
        
    def _sync_data(self):
        if not self.current_step or self.signalsBlocked(): return
        
        idx = self.command_combo.currentIndex()
        self.current_step.name = self.name_edit.text()
        
        # 0. Image
        if idx == 0:
            self.current_step.condition.type = ConditionType.IMAGE
            self.current_step.action.type = ActionType.MOVE
            self.current_step.condition.target_image_path = self.img_path_edit.text()
            self.current_step.condition.confidence = self.img_confidence.value()
            self.current_step.action.target_x = self.img_offset_x.value()
            self.current_step.action.target_y = self.img_offset_y.value()
            try:
                t = self.img_watch_area_edit.text()
                self.current_step.condition.watch_area = eval(t) if t else None
            except: pass
            
        # 1. Color
        elif idx == 1:
            self.current_step.condition.type = ConditionType.COLOR
            self.current_step.action.type = ActionType.MOVE
            self.current_step.condition.target_color = self.color_val_edit.text()
            self.current_step.condition.color_tolerance = self.color_tolerance.value()
            self.current_step.condition.match_index = self.color_match_index.value()
            try:
                t = self.color_watch_area_edit.text()
                self.current_step.condition.watch_area = eval(t) if t else None
            except: pass
            
        # 2. Move
        elif idx == 2:
            self.current_step.condition.type = ConditionType.TIME
            self.current_step.condition.wait_time_s = 0
            self.current_step.action.type = ActionType.MOVE
            self.current_step.action.target_x = self.move_x.value()
            self.current_step.action.target_y = self.move_y.value()
            
        # 3. Click
        elif idx == 3:
            self.current_step.condition.type = ConditionType.TIME
            self.current_step.condition.wait_time_s = 0
            self.current_step.action.type = ActionType.CLICK
            
        # 4. Wait
        elif idx == 4:
            self.current_step.condition.type = ConditionType.TIME
            self.current_step.action.type = ActionType.NONE
            self.current_step.condition.wait_time_s = self.wait_spin.value()
            
        # 5. Goto
        elif idx == 5:
            self.current_step.action.type = ActionType.GOTO
            self.current_step.action.goto_step_index = self.goto_spin.value()
            
        # 6. Await
        elif idx == 6:
            self.current_step.type = StepType.AWAIT
            self.current_step.condition.type = ConditionType.TIME # Placeholder
            self.current_step.condition.retry_timeout_s = self.await_timeout.value()
            self.current_step.condition.retry_interval_ms = self.await_interval.value()
            
        self.step_changed.emit(self.current_step)

    def set_workflow_dir(self, path):
         self.workflow_dir = path
         
    def _update_preview(self, path):
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
