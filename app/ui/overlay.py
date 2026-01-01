from PyQt6.QtWidgets import QWidget, QRubberBand, QApplication
from PyQt6.QtCore import Qt, QRect, pyqtSignal, QTimer
from PyQt6.QtGui import QPainter, QColor, QPen, QPixmap, QImage
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
        import pyautogui
        self.screen_grab = pyautogui.screenshot() # Returns PIL Image
        
        # Convert to QPixmap for painting
        im = self.screen_grab.convert("RGBA")
        data = im.tobytes("raw", "RGBA")
        qim = QImage(data, im.size[0], im.size[1], QImage.Format.Format_RGBA8888)
        self.full_pixmap = QPixmap.fromImage(qim)
         
        
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
        
        # Enable Mouse Tracking for Magnifier
        self.setMouseTracking(True)
        
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
            
        elif self.mode == "color":
             # 1. Dim Background
             painter.setBrush(QColor(0, 0, 0, 50))
             painter.setPen(Qt.PenStyle.NoPen)
             painter.drawRect(self.rect())
             
             # 2. Magnifier Logic
             if hasattr(self, 'mouse_pos') and self.mouse_pos:
                 mx, my = self.mouse_pos.x(), self.mouse_pos.y()
                 
                 # Config
                 zoom_factor = 4 # 4x Zoom
                 capture_radius = 10 # Capture 10px radius (20x20 area)
                 # Total Capture Size = 20x20
                 # Total Display Size = 20 * Zoom = 80x80
                 
                 # Prepare Source Rect (Physical Coords for High-DPI)
                 scale = 1.0
                 if self.full_pixmap.width() > self.width():
                     scale = self.full_pixmap.width() / self.width()
                     
                 # Center of capture in Physical Coords
                 phys_cx = int(mx * scale)
                 phys_cy = int(my * scale)
                 phys_radius = int(capture_radius * scale)
                 
                 # Crop Rect
                 crop_rect = QRect(
                     phys_cx - phys_radius, 
                     phys_cy - phys_radius, 
                     phys_radius * 2, 
                     phys_radius * 2
                 )
                 
                 # Capture from cached pixmap
                 cropped = self.full_pixmap.copy(crop_rect)
                 
                 # Scale up for Zoom (Nearest Neighbor for crisp pixels)
                 display_size = (capture_radius * 2) * zoom_factor
                 zoomed = cropped.scaled(
                     display_size, display_size, 
                     Qt.AspectRatioMode.KeepAspectRatio, 
                     Qt.TransformationMode.FastTransformation
                 )
                 
                 # Draw Magnifier Box (Offset from cursor)
                 offset_x = 20
                 offset_y = 20
                 
                 # Check boundaries to flip side if near edge
                 draw_x = mx + offset_x
                 draw_y = my + offset_y
                 if draw_x + display_size > self.width(): draw_x = mx - offset_x - display_size
                 if draw_y + display_size > self.height(): draw_y = my - offset_y - display_size
                 
                 # Draw White Border/Background for Magnifier
                 mag_rect = QRect(draw_x, draw_y, display_size, display_size)
                 painter.setBrush(Qt.GlobalColor.white)
                 painter.setPen(QPen(Qt.GlobalColor.black, 1))
                 painter.drawRect(mag_rect.adjusted(-1, -1, 1, 1)) # Border
                 
                 painter.drawPixmap(mag_rect, zoomed)
                 
                 # Draw Central Crosshair (Highlighting the center pixel)
                 # Center pixel is at (radius * zoom, radius * zoom) in local coords
                 center_local = capture_radius * zoom_factor
                 pixel_size = zoom_factor # 1 logical pixel * zoom? No, 1 captured pixel * zoom.
                 # Actually 1 physical pixel * zoom?
                 # If scale=2 (Retina), 1 logical px = 2 physical px.
                 # We captured physical pixels.
                 # If we want to highlight ONE LOGICAL PIXEL (which user is picking),
                 # that is 'scale' physical pixels.
                 # So standard pixel size on magnifier = zoom_factor * scale? No.
                 # zoomed is physically scaled.
                 
                 # Let's simplify: Highlight the CENTER of the magnifier.
                 # We want to outline the center block.
                 # Block size = zoom_factor (if 1 src pixel -> zoom_factor pixels)
                 # Wait, if Retina (scale=2), we captured 40x40 for 20x20 logical area.
                 # We display 40x40 * zoom? No.
                 # capture_radius=10 -> 20px logical width.
                 # Physical width = 20 * 2 = 40px.
                 # We crop 40x40 physical pixels.
                 # We want to display this as ??
                 # If we duplicate each physical pixel by zoom_factor...
                 # But valid color picking is on PHYSICAL pixel usually (or logical?).
                 # Our color picker code (lines 212) picks PHYSICAL pixel: self.screen_grab.getpixel((px, py))
                 # So we are picking ONE PHYSICAL PIXEL.
                 # So we should highlight ONE PHYSICAL PIXEL.
                 # In 'zoomed' pixmap (scaled from physical source), 1 physical pixel = 'zoom_factor' pixels wide/high.
                 # Correct.
                 
                 # So highlight box size = zoom_factor.
                 # Position = Center.
                 # Center of mag_rect is (draw_x + display_size/2, ...).
                 # We want to draw a box of size `zoom_factor` centered there.
                 # TopLeft = Center - zoom_factor/2
                 
                 cx = draw_x + (display_size // 2)
                 cy = draw_y + (display_size // 2)
                 
                 # Adjust for box alignment
                 # If even size, center is between pixels. 
                 # 20 radius -> 40 pixels. Center is between 20 and 21.
                 # We want pixel 20 (0-indexed? 0..39. Center? 19 or 20?)
                 # phys_cx is center. radius is 10. Range [cx-10, cx+10). Length 20.
                 # Center pixel is relative index 10.
                 # So 10 * zoom_factor is the offset.
                 # Yes.
                 
                 box_size = zoom_factor
                 # Offset from top-left of mag_rect
                 box_x = draw_x + (capture_radius * scale * zoom_factor) # Wait, logic tricky with scale
                 # Simplification: Draw crosshair over the whole widget
                 
                 painter.setPen(QPen(Qt.GlobalColor.red, 1))
                 painter.setBrush(Qt.BrushStyle.NoBrush)
                 
                 # Box around center pixel?
                 # Center of 'zoomed' corresponds to the mouse position.
                 # Mouse pos is 'phys_cx'.
                 # In crop, 'phys_cx' is at index 'phys_radius' (if crop is cx-r to cx+r).
                 # So relative position is `phys_radius`.
                 # Scaled position = `phys_radius * zoom_src_to_dst_ratio`?
                 # zoomed size = display_size.
                 # cropped size = phys_radius * 2.
                 # Ratio = display_size / (phys_radius * 2) = zoom_factor.
                 # So relative pixel x = phys_radius * zoom_factor.
                 
                 # Draw red box
                 center_box_x = draw_x + (phys_radius * zoom_factor)
                 center_box_y = draw_y + (phys_radius * zoom_factor)
                 
                 # But we might need to adjust if zoom_factor is small.
                 # Just draw a crosshair for now.
                 
                 # Crosshair
                 painter.drawLine(draw_x + (display_size // 2), draw_y, draw_x + (display_size // 2), draw_y + display_size)
                 painter.drawLine(draw_x, draw_y + (display_size // 2), draw_x + display_size, draw_y + (display_size // 2))
                 
                 # Outline Center Pixel
                 painter.drawRect(center_box_x, center_box_y, zoom_factor, zoom_factor)
                 
                 
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

        if self.mode == "color":
             # Trigger Pick
             # Already handled in mouseRelease typically? 
             # Or mouseRelease calls 'hide' then emit.
             # Let's keep consistency.
             # Just store clicked?
             # Standard behavior: Press -> (Drag) -> Release -> Action.
             pass

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
        elif self.mode == "color":
            self.mouse_pos = event.pos()
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
