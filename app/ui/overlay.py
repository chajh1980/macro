from PyQt6.QtWidgets import QWidget, QRubberBand, QApplication
from PyQt6.QtCore import Qt, QRect, pyqtSignal, QTimer
from PyQt6.QtGui import QPainter, QColor, QPen
from app.utils.screen_utils import get_screen_scale

class Overlay(QWidget):
    captured = pyqtSignal(QRect) # For region selection
    clicked = pyqtSignal(int, int) # For coordinate selection
    
    def __init__(self, mode="region", highlight_rect: QRect = None): 
        # mode: "region", "point", "highlight"
        super().__init__()
        print(f"DEBUG: Overlay initialized with mode={mode}")
        self.mode = mode
        self.highlight_rect = highlight_rect
        
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint | 
            Qt.WindowType.Tool  # Tool sometimes helps with focus behavior
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet("background-color: transparent;")
        
        # Cover specific screen or all screens?
        # For now, primary screen is safest for coordinates.
        screen = QApplication.primaryScreen()
        self.setGeometry(screen.geometry())
        
        if self.mode == "highlight":
            self.setCursor(Qt.CursorShape.ArrowCursor)
            # Auto close after some time?
            QTimer.singleShot(2000, self.close) # Show for 2 seconds
        elif self.mode == "running":
            self.setWindowFlags(
                Qt.WindowType.FramelessWindowHint | 
                Qt.WindowType.WindowStaysOnTopHint |
                Qt.WindowType.Tool |
                Qt.WindowType.WindowTransparentForInput | # Clicks pass through
                Qt.WindowType.WindowDoesNotAcceptFocus # No focus
            )
            self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
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
                self.captured.emit(rect)
            elif self.mode == "point":
                self.clicked.emit(event.pos().x(), event.pos().y())
            self.close()
            
    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close()
