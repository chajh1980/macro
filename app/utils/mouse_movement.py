import time
import random
import math
import pyautogui

def get_current_position():
    return pyautogui.position()

def bezier_curve(t, p0, p1, p2, p3):
    """Cubic Bezier curve formula"""
    return (1-t)**3 * p0 + 3 * (1-t)**2 * t * p1 + 3 * (1-t) * t**2 * p2 + t**3 * p3

def human_move_to(target_x, target_y, duration=0.2):
    """
    Moves mouse to (target_x, target_y) using a cubic Bezier curve 
    to simulate human-like movement.
    """
    start_x, start_y = pyautogui.position()
    
    # If distance is very small, just move directly
    dist = math.hypot(target_x - start_x, target_y - start_y)
    if dist < 5:
        pyautogui.moveTo(target_x, target_y)
        return

    # Create control points for a more natural curve
    # Use smaller random offset to keep curve closer to direct path
    offset_factor = min(0.1, 20.0 / dist)  # Smaller offset for longer distances
    
    # Control point 1: 1/3 of the way with slight perpendicular offset
    cp1_x = start_x + (target_x - start_x) * 0.33
    cp1_y = start_y + (target_y - start_y) * 0.33
    
    # Add small perpendicular deviation
    dx = target_x - start_x
    dy = target_y - start_y
    perp_x = -dy * offset_factor * random.uniform(-1, 1)
    perp_y = dx * offset_factor * random.uniform(-1, 1)
    
    cp1_x += perp_x
    cp1_y += perp_y
    
    # Control point 2: 2/3 of the way with slight perpendicular offset
    cp2_x = start_x + (target_x - start_x) * 0.67
    cp2_y = start_y + (target_y - start_y) * 0.67
    cp2_x += perp_x * 0.5
    cp2_y += perp_y * 0.5
    
    # Steps based on duration
    steps = max(int(duration * 100), 10)  # More steps for smoother movement
    
    for i in range(steps + 1):
        t = i / steps
        # Simple smoothstep easing
        t_eased = t * t * (3 - 2 * t)
        
        x = bezier_curve(t_eased, start_x, cp1_x, cp2_x, target_x)
        y = bezier_curve(t_eased, start_y, cp1_y, cp2_y, target_y)
        
        pyautogui.moveTo(int(x), int(y))
        
        # Sleep to match duration
        time.sleep(duration / steps)
        
    # Ensure final position
    pyautogui.moveTo(target_x, target_y)
