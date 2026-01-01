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
        
        # --- Top: Name ---
        grp_gen = QGroupBox("General")
        layout_gen = QFormLayout()
        grp_gen.setLayout(layout_gen)
        self.name_edit = QLineEdit()
        self.name_edit.textChanged.connect(self._sync_data)
        layout_gen.addRow("Step Name:", self.name_edit)
        self.layout.addWidget(grp_gen)
        
        # =========================================================================
        # 1. Flow Control Section
        # =========================================================================
        grp_flow = QGroupBox("1. Flow Control")
        layout_flow = QVBoxLayout()
        grp_flow.setLayout(layout_flow)
        
        self.combo_flow = QComboBox()
        self.combo_flow.addItems(["Basic Step", "If Condition", "Until Loop", "Await"])
        self.combo_flow.currentIndexChanged.connect(self._on_flow_changed)
        layout_flow.addWidget(self.combo_flow)
        
        self.stack_flow = PyQt6.QtWidgets.QStackedWidget()
        layout_flow.addWidget(self.stack_flow)
        
        # 0: Basic (Empty)
        self.page_flow_basic = QWidget()
        self.stack_flow.addWidget(self.page_flow_basic)
        
        # 1: If (Empty for now)
        self.page_flow_if = QWidget()
        self.stack_flow.addWidget(self.page_flow_if)
        
        # 2: Until (Maybe loop limit?)
        self.page_flow_until = QWidget()
        self.stack_flow.addWidget(self.page_flow_until)
        
        # 3: Await (Timeout/Interval)
        self.page_flow_await = QWidget()
        pfa_layout = QFormLayout()
        self.page_flow_await.setLayout(pfa_layout)
        self.await_timeout = QDoubleSpinBox()
        self.await_timeout.setRange(0, 3600); self.await_timeout.setValue(10.0)
        self.await_interval = QSpinBox()
        self.await_interval.setRange(10, 10000); self.await_interval.setValue(500)
        self.await_interval.setSuffix(" ms")
        self.await_timeout.valueChanged.connect(self._sync_data)
        self.await_interval.valueChanged.connect(self._sync_data)
        pfa_layout.addRow("Timeout (s):", self.await_timeout)
        pfa_layout.addRow("Check Interval:", self.await_interval)
        self.stack_flow.addWidget(self.page_flow_await)
        
        self.layout.addWidget(grp_flow)
        
        # =========================================================================
        # 2. Condition Section
        # =========================================================================
        grp_cond = QGroupBox("2. Condition")
        layout_cond = QVBoxLayout()
        grp_cond.setLayout(layout_cond)
        
        self.combo_cond = QComboBox()
        self.combo_cond.addItems(["None / Time", "Find Image", "Find Color", "Find Text"]) # Text placeholder
        self.combo_cond.currentIndexChanged.connect(self._on_cond_changed)
        layout_cond.addWidget(self.combo_cond)
        
        self.stack_cond = PyQt6.QtWidgets.QStackedWidget()
        layout_cond.addWidget(self.stack_cond)
        
        # 0: None / Time
        self.page_cond_time = QWidget()
        pct_layout = QFormLayout()
        self.page_cond_time.setLayout(pct_layout)
        self.wait_time = QDoubleSpinBox()
        self.wait_time.setRange(0, 3600)
        self.wait_time.valueChanged.connect(self._sync_data)
        pct_layout.addRow("Wait Time (s):", self.wait_time)
        self.stack_cond.addWidget(self.page_cond_time)
        
        # 1: Image
        self.page_cond_img = QWidget()
        pci_layout = QFormLayout()
        self.page_cond_img.setLayout(pci_layout)
        
        self.img_path = QLineEdit()
        self.btn_capture_img = QPushButton("Capture")
        row_img = QHBoxLayout(); row_img.addWidget(self.img_path); row_img.addWidget(self.btn_capture_img)
        self.img_preview = QLabel("No Image")
        self.img_preview.setFixedSize(200, 80); self.img_preview.setStyleSheet("border: 1px dashed gray;")
        self.img_conf = QDoubleSpinBox(); self.img_conf.setRange(0.1, 1.0); self.img_conf.setValue(0.9); self.img_conf.setSingleStep(0.05)
        self.img_fullscreen = QCheckBox("Full Screen"); self.img_fullscreen.setChecked(True)
        self.img_area = QLineEdit(); self.img_area.setEnabled(False)
        self.btn_set_area_img = QPushButton("Set Area"); self.btn_set_area_img.setEnabled(False)
        row_area_img = QHBoxLayout(); row_area_img.addWidget(self.img_fullscreen); row_area_img.addWidget(self.img_area); row_area_img.addWidget(self.btn_set_area_img)
        
        # Connections
        self.img_path.textChanged.connect(self._sync_data)
        self.img_conf.valueChanged.connect(self._sync_data)
        self.img_fullscreen.toggled.connect(self._on_img_fullscreen_toggled)
        self.img_area.textChanged.connect(self._sync_data)
        
        pci_layout.addRow("Image:", row_img)
        pci_layout.addRow("Preview:", self.img_preview)
        pci_layout.addRow("Confidence:", self.img_conf)
        pci_layout.addRow("Search Area:", row_area_img)
        self.stack_cond.addWidget(self.page_cond_img)
        
        # 2: Color
        self.page_cond_color = QWidget()
        pcc_layout = QFormLayout()
        self.page_cond_color.setLayout(pcc_layout)
        
        self.color_val = QLineEdit("#FFFFFF")
        self.btn_pick_color = QPushButton("Pick")
        self.color_preview = QLabel(); self.color_preview.setFixedSize(20, 20); self.color_preview.setStyleSheet("border: 1px solid black; background: #FFF;")
        row_col = QHBoxLayout(); row_col.addWidget(self.color_preview); row_col.addWidget(self.color_val); row_col.addWidget(self.btn_pick_color)
        
        self.color_tol = QSpinBox(); self.color_tol.setRange(0, 100); self.color_tol.setValue(10)
        self.color_match_idx = QSpinBox(); self.color_match_idx.setRange(0, 99)
        self.color_fullscreen = QCheckBox("Full Screen"); self.color_fullscreen.setChecked(True)
        self.color_area = QLineEdit(); self.color_area.setEnabled(False)
        self.btn_set_area_color = QPushButton("Set Area"); self.btn_set_area_color.setEnabled(False)
        row_area_col = QHBoxLayout(); row_area_col.addWidget(self.color_fullscreen); row_area_col.addWidget(self.color_area); row_area_col.addWidget(self.btn_set_area_color)
        
        # Connections
        self.color_val.textChanged.connect(self._sync_data)
        self.color_val.textChanged.connect(self._update_color_preview_ui)
        self.color_tol.valueChanged.connect(self._sync_data)
        self.color_match_idx.valueChanged.connect(self._sync_data)
        self.color_fullscreen.toggled.connect(self._on_color_fullscreen_toggled)
        self.color_area.textChanged.connect(self._sync_data)
        
        pcc_layout.addRow("Target Color:", row_col)
        pcc_layout.addRow("Tolerance:", self.color_tol)
        pcc_layout.addRow("Match Index:", self.color_match_idx)
        pcc_layout.addRow("Search Area:", row_area_col)
        self.stack_cond.addWidget(self.page_cond_color)
        
        # 3: Text placeholder
        self.page_cond_text = QWidget()
        self.stack_cond.addWidget(self.page_cond_text)
        
        self.layout.addWidget(grp_cond)
        
        # =========================================================================
        # 3. Action Section
        # =========================================================================
        grp_act = QGroupBox("3. Action")
        layout_act = QVBoxLayout()
        grp_act.setLayout(layout_act)
        
        self.combo_act = QComboBox()
        self.combo_act.addItems(["None", "Move Mouse", "Click Mouse", "Goto Step"])
        self.combo_act.currentIndexChanged.connect(self._on_act_changed)
        layout_act.addWidget(self.combo_act)
        
        self.stack_act = PyQt6.QtWidgets.QStackedWidget()
        layout_act.addWidget(self.stack_act)
        
        # 0: None
        self.stack_act.addWidget(QWidget())
        
        # 1: Move
        self.page_act_move = QWidget()
        pam_layout = QFormLayout()
        self.page_act_move.setLayout(pam_layout)
        self.move_x = QSpinBox(); self.move_x.setRange(-9999, 9999) # Allow neg for offsets
        self.move_y = QSpinBox(); self.move_y.setRange(-9999, 9999)
        self.btn_pick_pos = QPushButton("Pick Pos") # Only valid for absolute move
        row_move = QHBoxLayout(); row_move.addWidget(QLabel("X:")); row_move.addWidget(self.move_x); row_move.addWidget(QLabel("Y:")); row_move.addWidget(self.move_y)
        
        # Connections
        self.move_x.valueChanged.connect(self._sync_data)
        self.move_y.valueChanged.connect(self._sync_data)
        
        pam_layout.addRow(QLabel("Target / Offset:"), row_move)
        pam_layout.addRow("", self.btn_pick_pos)
        self.stack_act.addWidget(self.page_act_move)
        
        # 2: Click (Re-use Move params?) 
        # Click usually implies Move then Click. Or Click at current.
        # Let's verify Action model. It has target_x/y.
        # We can reuse the same UI logic or duplicate fields. Let's reuse Logic but separate UI widgets for clarity if needed.
        # For simplicity, Click page will have same X/Y fields.
        self.page_act_click = QWidget()
        pac_layout = QFormLayout()
        self.page_act_click.setLayout(pac_layout)
        self.click_x = QSpinBox(); self.click_x.setRange(-9999, 9999)
        self.click_y = QSpinBox(); self.click_y.setRange(-9999, 9999)
        row_click = QHBoxLayout(); row_click.addWidget(QLabel("X:")); row_click.addWidget(self.click_x); row_click.addWidget(QLabel("Y:")); row_click.addWidget(self.click_y)
        self.click_x.valueChanged.connect(self._sync_data)
        self.click_y.valueChanged.connect(self._sync_data)
        pac_layout.addRow(QLabel("Target / Offset (0=Current):"), row_click)
        self.stack_act.addWidget(self.page_act_click)
        
        # 3: Goto
        self.page_act_goto = QWidget()
        pag_layout = QFormLayout()
        self.page_act_goto.setLayout(pag_layout)
        self.goto_idx = QSpinBox(); self.goto_idx.setRange(1, 9999)
        self.goto_idx.valueChanged.connect(self._sync_data)
        pag_layout.addRow("Jump to Step #:", self.goto_idx)
        self.stack_act.addWidget(self.page_act_goto)
        
        self.layout.addWidget(grp_act)
        
        # --- Bottom ---
        self.layout.addStretch()
        self.test_btn = QPushButton("Test This Step")
        self.layout.addWidget(self.test_btn)

    # --- UI Logic Handlers ---
    
    def _on_flow_changed(self, idx):
        self.stack_flow.setCurrentIndex(idx)
        self._sync_data()
        
    def _on_cond_changed(self, idx):
        self.stack_cond.setCurrentIndex(idx)
        self._sync_data()
        
    def _on_act_changed(self, idx):
        self.stack_act.setCurrentIndex(idx)
        self._sync_data()
        
    def _on_img_fullscreen_toggled(self, checked):
        self.img_area.setEnabled(not checked)
        self.btn_set_area_img.setEnabled(not checked)
        if checked: self.img_area.clear()
        self._sync_data()

    def _on_color_fullscreen_toggled(self, checked):
        self.color_area.setEnabled(not checked)
        self.btn_set_area_color.setEnabled(not checked)
        if checked: self.color_area.clear()
        self._sync_data()
        
    def _update_color_preview_ui(self, text):
        try: self.color_preview.setStyleSheet(f"background: {text}; border: 1px solid black;")
        except: pass

    # --- Load & Sync ---

    def load_step(self, step: Step):
        self.current_step = step
        self.blockSignals(True)
        
        self.name_edit.setText(step.name)
        
        # 1. Flow
        if step.type == StepType.IF: flow_idx = 1
        elif step.type == StepType.UNTIL: flow_idx = 2
        elif step.type == StepType.AWAIT: flow_idx = 3
        else: flow_idx = 0 # General/Basic
        self.combo_flow.setCurrentIndex(flow_idx)
        self.stack_flow.setCurrentIndex(flow_idx)
        
        # Await Params
        if step.type == StepType.AWAIT:
            self.await_timeout.setValue(step.condition.retry_timeout_s or 10.0)
            self.await_interval.setValue(step.condition.retry_interval_ms or 500)
            
        # 2. Condition
        if step.condition.type == ConditionType.IMAGE: cond_idx = 1
        elif step.condition.type == ConditionType.COLOR: cond_idx = 2
        elif step.condition.type == ConditionType.TEXT: cond_idx = 3
        else: cond_idx = 0 # Time/None
        self.combo_cond.setCurrentIndex(cond_idx)
        self.stack_cond.setCurrentIndex(cond_idx)
        
        # Cond Params
        self.wait_time.setValue(step.condition.wait_time_s)
        
        # Image
        self.img_path.setText(step.condition.target_image_path or "")
        self.img_conf.setValue(step.condition.confidence or 0.9)
        if step.condition.watch_area and step.condition.type == ConditionType.IMAGE:
             self.img_fullscreen.setChecked(False)
             self.img_area.setText(str(step.condition.watch_area))
        else:
             self.img_fullscreen.setChecked(True)
        self._update_preview(step.condition.target_image_path)
             
        # Color
        self.color_val.setText(step.condition.target_color or "#FFFFFF")
        self._update_color_preview_ui(step.condition.target_color or "#FFFFFF")
        self.color_tol.setValue(step.condition.color_tolerance)
        self.color_match_idx.setValue(step.condition.match_index)
        if step.condition.watch_area and step.condition.type == ConditionType.COLOR:
             self.color_fullscreen.setChecked(False)
             self.color_area.setText(str(step.condition.watch_area))
        else:
             self.color_fullscreen.setChecked(True)
             
        # 3. Action
        if step.action.type == ActionType.MOVE: act_idx = 1
        elif step.action.type == ActionType.CLICK: act_idx = 2
        elif step.action.type == ActionType.GOTO: act_idx = 3
        else: act_idx = 0
        self.combo_act.setCurrentIndex(act_idx)
        self.stack_act.setCurrentIndex(act_idx)
        
        # Act Params
        tx = step.action.target_x or 0
        ty = step.action.target_y or 0
        self.move_x.setValue(tx); self.move_y.setValue(ty)
        self.click_x.setValue(tx); self.click_y.setValue(ty)
        self.goto_idx.setValue(step.action.goto_step_index or 1)
        
        self.blockSignals(False)

    def _sync_data(self):
        if not self.current_step or self.signalsBlocked(): return
        
        self.current_step.name = self.name_edit.text()
        
        # 1. Flow
        f_idx = self.combo_flow.currentIndex()
        if f_idx == 1: self.current_step.type = StepType.IF
        elif f_idx == 2: self.current_step.type = StepType.UNTIL
        elif f_idx == 3: 
            self.current_step.type = StepType.AWAIT
            self.current_step.condition.retry_timeout_s = self.await_timeout.value()
            self.current_step.condition.retry_interval_ms = self.await_interval.value()
        else: self.current_step.type = StepType.GENERAL
        
        # 2. Condition
        c_idx = self.combo_cond.currentIndex()
        if c_idx == 1: # Image
            self.current_step.condition.type = ConditionType.IMAGE
            self.current_step.condition.target_image_path = self.img_path.text()
            self.current_step.condition.confidence = self.img_conf.value()
            try:
                t = self.img_area.text()
                self.current_step.condition.watch_area = eval(t) if t else None
            except: pass
        elif c_idx == 2: # Color
            self.current_step.condition.type = ConditionType.COLOR
            self.current_step.condition.target_color = self.color_val.text()
            self.current_step.condition.color_tolerance = self.color_tol.value()
            self.current_step.condition.match_index = self.color_match_idx.value()
            try:
                t = self.color_area.text()
                self.current_step.condition.watch_area = eval(t) if t else None
            except: pass
        else: # Time / None
            self.current_step.condition.type = ConditionType.TIME
            self.current_step.condition.wait_time_s = self.wait_time.value()
            
        # 3. Action
        a_idx = self.combo_act.currentIndex()
        if a_idx == 1: # Move
            self.current_step.action.type = ActionType.MOVE
            self.current_step.action.target_x = self.move_x.value()
            self.current_step.action.target_y = self.move_y.value()
        elif a_idx == 2: # Click
            self.current_step.action.type = ActionType.CLICK
            self.current_step.action.target_x = self.click_x.value()
            self.current_step.action.target_y = self.click_y.value()
        elif a_idx == 3: # Goto
            self.current_step.action.type = ActionType.GOTO
            self.current_step.action.goto_step_index = self.goto_idx.value()
        else:
            self.current_step.action.type = ActionType.NONE
            
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
