from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit, QProgressBar, QCheckBox, QApplication
)
from PyQt6.QtCore import Qt, pyqtSlot, QTimer
from app.core.engine import WorkflowRunner

class RunnerWindow(QWidget):
    def __init__(self, runner: WorkflowRunner):
        super().__init__()
        self.runner = runner
        self.setWindowTitle("Workflow Runner")
        self.resize(400, 300)
        
        # Focus Management: Don't steal focus on show
        # Qt.Tool prevents minimization on macOS, so we remove it.
        # WA_ShowWithoutActivating helps, but minimization is the primary method now.
        # self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        
        # Overlay
        self.overlay = None
        self.listener = None
        
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        
        # Status Label
        self.status_label = QLabel("Initializing...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.layout.addWidget(self.status_label)
        
        # Progress Bar (Indeterminate or Step based)
        self.progress_bar = QProgressBar()
        self.layout.addWidget(self.progress_bar)
        
        # Log Area
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.layout.addWidget(self.log_area)
        
        # Stop Button
        self.stop_btn = QPushButton("STOP (Option+C)")
        self.stop_btn.setStyleSheet("background-color: red; color: white; font-weight: bold; padding: 10px;")
        self.stop_btn.clicked.connect(self._stop_workflow)
        self.layout.addWidget(self.stop_btn)
        
        # Connect Signals
        self.runner.progress_signal.connect(self._on_progress)
        self.runner.log_signal.connect(self._on_log)
        self.runner.finished_signal.connect(self._on_finished)
        
        # Always on Top
        self.always_on_top_cb = QCheckBox("Always on Top")
        self.always_on_top_cb.stateChanged.connect(self._toggle_always_on_top)
        self.layout.addWidget(self.always_on_top_cb)
        
    def _toggle_always_on_top(self, state):
        if state == 2: # Checked
            self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowStaysOnTopHint)
        self.show()
        
    @pyqtSlot(int, str)
    def _on_progress(self, index, name):
        self.status_label.setText(f"Step {index + 1}: {name}")
        
    @pyqtSlot(str)
    def _on_log(self, message):
        self.log_area.append(message)
        
    @pyqtSlot()
    def _on_finished(self):
        self.status_label.setText("Finished")
        self.stop_btn.setText("Close Window")
        self.stop_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 10px;")
        try:
            self.stop_btn.clicked.disconnect()
        except: pass
        self.stop_btn.clicked.connect(self.close)
        
        # Close Overlay
        if self.overlay:
            self.overlay.close()
            self.overlay = None
            
        # Restore Window
        self.showNormal()
        self.activateWindow()
        self.raise_()
        
    def _stop_workflow(self):
        self.runner.stop()
        self.log_area.append("Stop requested...")
        if self.overlay:
            self.overlay.close()
            self.overlay = None
            
        # Restore just in case stop button was clicked from minimized tray? 
        # (Though button is on window, so window must be open to click it. 
        # But if Ctrl+C triggered it, we want to restore.)
        # Ideally Ctrl+C calls stop -> finishes workflow -> _on_finished restores.
        # But let's ensure immediate feedback if needed.
        self.showNormal()
        self.activateWindow()

    def showEvent(self, event):
        super().showEvent(event)
        print("DEBUG: RunnerWindow showEvent triggered")
        
        # Hotkey Listener disabled due to 'trace trap' crash on macOS
        # self._start_hotkey_listener()
        
        # Show Overlay FIRST
        try:
            from app.ui.overlay import Overlay
            if not self.overlay:
                print("DEBUG: Creating Running Overlay")
                self.overlay = Overlay(mode="running")
                self.overlay.show()
                # Force overlay to paint? 
                QApplication.processEvents()
        except Exception as e:
            print(f"DEBUG: Error creating overlay: {e}")
            self.log_area.append(f"Error showing overlay: {e}")
            
        # Minimize removed per user request (logic: "cannot close it")
        # Start normal but try not to steal focus via WA_ShowWithoutActivating
        
    def closeEvent(self, event):
        self._stop_hotkey_listener()
        if self.overlay:
            self.overlay.close()
        super().closeEvent(event)
        
    def _start_hotkey_listener(self):
        try:
             from pynput import keyboard
             self.listener = keyboard.GlobalHotKeys({
                 '<alt>+c': self._on_hotkey_stop
             })
             self.listener.start()
             self.log_area.append("Global Hotkey Option+C enabled.")
        except ImportError:
             self.log_area.append("pynput not found. Hotkeys disabled.")
        except Exception as e:
             self.log_area.append(f"Error starting hotkeys: {e}")
        
    def _stop_hotkey_listener(self):
        if hasattr(self, 'listener') and self.listener:
            try:
                self.listener.stop()
            except: pass
            self.listener = None
            
    def _on_hotkey_stop(self):
        # Called from non-GUI thread
        # runner.stop() is thread-safe flag setting
        self.runner.stop()
