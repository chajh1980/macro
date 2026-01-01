from PyQt6.QtWidgets import QWidget, QRubberBand, QApplication
from PyQt6.QtCore import Qt, QRect, pyqtSignal, QTimer
from PyQt6.QtGui import QPainter, QColor, QPen
import pyautogui
from app.utils.screen_utils import get_screen_scale

class Overlay(QWidget):
    captured = pyqtSignal(QRect) # For region selection
    clicked = pyqtSignal(int, int) # For coordinate selection
    color_picked = pyqtSignal(str) # Hex string
    
    def __init__(self, mode="region", highlight_rect: QRect = None): 
        # mode: "region", "point", "highlight", "color"
        super().__init__()
        # print(f"DEBUG: Overlay initialized with mode={mode}")
        self.mode = mode
        self.highlight_rect = highlight_rect
        
        # 1. Capture Screen State BEFORE showing overlay (Fixes Dimming Bug)
        self.screen_grab = pyautogui.screenshot() # Returns PIL Image
        
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint | 
            Qt.WindowType.Tool  
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet("background-color: transparent;")
        
        # Cover primary screen
        screen = QApplication.primaryScreen()
        self.setGeometry(screen.geometry())
        
        if self.mode == "highlight":
            self.setCursor(Qt.CursorShape.ArrowCursor)
            QTimer.singleShot(2000, self.close) 
        elif self.mode == "running":
            self.setWindowFlags(
                Qt.WindowType.FramelessWindowHint | 
                Qt.WindowType.WindowStaysOnTopHint |
                Qt.WindowType.Tool |
                Qt.WindowType.WindowTransparentForInput | 
                Qt.WindowType.WindowDoesNotAcceptFocus 
            )
            self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        elif self.mode == "color":
             self.setCursor(Qt.CursorShape.CrossCursor)
        else:
            self.setCursor(Qt.CursorShape.CrossCursor)
        
        self.start_point = None
        self.end_point = None
        self.rubber_band = QRubberBand(QRubberBand.Shape.Rectangle, self)
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        if self.mode == "highlight" and self.highlight_rect:
            # Draw Green Box
            pen = QPen(Qt.GlobalColor.green, 4)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(self.highlight_rect)
            
            # Draw Label "MATCH"
            painter.setPen(Qt.GlobalColor.white)
            painter.setBackground(Qt.GlobalColor.green)
            painter.setBackgroundMode(Qt.BGMode.OpaqueMode)
            painter.drawText(self.highlight_rect.topLeft(), " MATCH ")
            
        elif self.mode == "running":
            # print("DEBUG: Overlay painting running border")
            # Draw Red Border (5px)
            pen = QPen(Qt.GlobalColor.red, 10) # 10px stroke, but half works if on edge?
            # Actually if we draw on rect(), half the stroke is clipped.
            # Let's use 5px and inset slightly or just draw thick.
            pen.setWidth(10)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            
            # Draw rect slightly inside to ensure visibility
            r = self.rect()
            painter.drawRect(r)
            
            # Draw Label "RUNNING (Mouse to Corner to Stop)"
            painter.setPen(Qt.GlobalColor.white)
            font = painter.font()
            font.setBold(True)
            font.setPointSize(16)
            painter.setFont(font)
            
            label_text = " RUNNING (Mouse to Corner to Stop) "
            fm = painter.fontMetrics()
            w = fm.horizontalAdvance(label_text)
            h = fm.height()
            
            # Top Right Position
            label_rect = QRect(r.width() - w - 20, 20, w, h)
            
            painter.fillRect(label_rect, Qt.GlobalColor.red)
            painter.drawText(label_rect, Qt.AlignmentFlag.AlignCenter, label_text)
            
        else:
            # Standard Capture Overlay
            painter.setBrush(QColor(0, 0, 0, 50))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRect(self.rect())
            
            if self.mode == "region" and self.start_point and self.end_point:
                rect = QRect(self.start_point, self.end_point).normalized()
                painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
                painter.fillRect(rect, Qt.GlobalColor.transparent)
                
                painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
                pen = QPen(Qt.GlobalColor.red, 2)
                painter.setPen(pen)
                painter.drawRect(rect)

    def mousePressEvent(self, event):
        if self.mode == "highlight":
            self.close() # Click to dismiss early
            return

        if event.button() == Qt.MouseButton.LeftButton:
            self.start_point = event.pos()
            if self.mode == "region":
                self.rubber_band.setGeometry(QRect(self.start_point, self.start_point))
                self.rubber_band.show()
    
    def mouseMoveEvent(self, event):
        if self.mode == "region" and self.start_point:
            self.end_point = event.pos()
            self.rubber_band.setGeometry(QRect(self.start_point, self.end_point).normalized())
            self.update()
            
    def mouseReleaseEvent(self, event):
        if self.mode == "highlight":
            return

        if event.button() == Qt.MouseButton.LeftButton:
            self.hide()
            QApplication.processEvents()
            
            # Emit Logical Coordinates (Qt coordinates)
            # The receiver (editor.py) will handle any scaling if needed for screenshotting
            # but usually grabWindow takes logical coords.
            # However, for consistency, let's keep emitting logical keys.
            
            if self.mode == "region":
                self.end_point = event.pos()
                rect = QRect(self.start_point, self.end_point).normalized()
                
                # CROP from CACHED CLEAN SCREENSHOT to avoid dimming (Fixes bug)
                # PIL Image crop: (left, top, right, bottom)
                # Need to handle Retina scaling?
                # pyautogui.screenshot returns physical pixels on Windows? And scaled on Mac?
                # On Mac with Retina, pyautogui.screenshot returns high-res image (e.g. 2x size of point coords).
                # But our QWidget geometry is logical coordinates (1x).
                # We need to map logical rect to physical image coordinates.
                
                scale = 1.0
                if self.screen_grab.width > self.width():
                     scale = self.screen_grab.width / self.width()
                
                left = int(rect.x() * scale)
                top = int(rect.y() * scale)
                right = int((rect.x() + rect.width()) * scale)
                bottom = int((rect.y() + rect.height()) * scale)
                
                cropped_img = self.screen_grab.crop((left, top, right, bottom))
                
                # Save to specific temp path or emit object?
                # Existing Editor expects to verify signal... wait Editor logic needs update too.
                # Let's emit the rect for now, AND save the image to a known location?
                # Or change signal to emit path?
                # Let's change signal to emit (QRect, str) -> Rect and file path.
                
                import tempfile
                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
                    cropped_img.save(f.name)
                    temp_path = f.name
                
                self.captured.emit(rect) # Keep signature for now? No, need to pass data.
                # Signal is defined as pyqtSignal(QRect). I can't change it easily without changing receiver.
                # BUT I can store the last capture in a public variable or singleton?
                # Better: Emit a custom signal or change definition.
                # I will change signal definition to pyqtSignal(object) in next step.
                self.last_capture_path = temp_path
                
            elif self.mode == "point":
                self.clicked.emit(event.pos().x(), event.pos().y())
                
            elif self.mode == "color":
                 # Get color at pos
                 x = event.pos().x()
                 y = event.pos().y()
                 
                 # Handle scaling
                 scale = 1.0
                 if self.screen_grab.width > self.width():
                      scale = self.screen_grab.width / self.width()
                      
                 px = int(x * scale)
                 py = int(y * scale)
                 
                 # Boundary check
                 if 0 <= px < self.screen_grab.width and 0 <= py < self.screen_grab.height:
                     # Force RGBA -> RGB handling
                     pixel = self.screen_grab.getpixel((px, py))
                     r, g, b = pixel[:3]
                     hex_color = f"#{r:02x}{g:02x}{b:02x}"
                     self.color_picked.emit(hex_color)
                 
            self.close()
            
    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close()
