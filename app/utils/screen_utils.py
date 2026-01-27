import platform
from PyQt6.QtGui import QGuiApplication

def get_screen_scale():
    """Returns the Device Pixel Ratio (DPR) of the primary screen."""
    app = QGuiApplication.instance()
    if not app:
        # Fallback if no app instance (e.g. running just backend tests)
        # But usually we run within GUI context or have a dummy app
        # For simple headless, assume 1.0 or use platform check
        if platform.system() == "Darwin":
            return 2.0  # Common default for Retina, but dangerous assumption.
            # Better to require GUI app for accurate scale.
            return 1.0
        return 1.0

    screen = app.primaryScreen()
    return screen.devicePixelRatio()

def get_screen_geometry():
    """Returns screen dimensions (width, height) in logical pixels."""
    app = QGuiApplication.instance()
    if not app:
        # Fallback
        return (1920, 1080)  # Default 1080p

    screen = app.primaryScreen()
    geometry = screen.geometry()
    return (geometry.width(), geometry.height())

def set_window_size_percentage(widget, width_pct=0.3, height_pct=0.3):
    """
    Set window size as percentage of screen size.
    width_pct: 0.0-1.0 (30% = 0.3)
    height_pct: 0.0-1.0
    """
    screen_w, screen_h = get_screen_geometry()

    target_w = int(screen_w * width_pct)
    target_h = int(screen_h * height_pct)

    widget.resize(target_w, target_h)

def set_window_size_fixed(widget, width=1000, height=700):
    """
    Set fixed window size (for backward compatibility).
    """
    widget.resize(width, height)

def logical_to_physical(rect_or_point):
    """Converts logical coordinates (PyQt/OS points) to physical pixels (Screenshot)."""
    scale = get_screen_scale()
    if isinstance(rect_or_point, (list, tuple)) and len(rect_or_point) == 4:
        # x, y, w, h
        return [int(v * scale) for v in rect_or_point]
    elif isinstance(rect_or_point, (list, tuple)) and len(rect_or_point) == 2:
        # x, y
        return [int(v * scale) for v in rect_or_point]
    return rect_or_point

def physical_to_logical(rect_or_point):
    """Converts physical pixels (Image Search results) to logical coordinates (Click)."""
    scale = get_screen_scale()
    if scale == 0: return rect_or_point
    
    if isinstance(rect_or_point, (list, tuple)) and len(rect_or_point) == 4:
        return [int(v / scale) for v in rect_or_point]
    elif isinstance(rect_or_point, (list, tuple)) and len(rect_or_point) == 2:
        return [int(v / scale) for v in rect_or_point]
    return rect_or_point
