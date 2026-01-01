from typing import List, Tuple, Optional
import logging

logger = logging.getLogger("app.core.image_proc")

def find_image_on_screen(
    target_image_path: str,
    confidence: float = 0.8,
    region: Optional[Tuple[int, int, int, int]] = None,
    grayscale: bool = False
) -> List[Tuple[int, int, int, int]]:
    import pyautogui
    import cv2
    import numpy as np
    """
    Finds all occurrences of the target image on the screen.
    Returns a list of (left, top, width, height) tuples.
    """
    matches = []
    
    # 1. Try Standard Search
    try:
        matches = list(pyautogui.locateAllOnScreen(
            target_image_path,
            confidence=confidence,
            region=region,
            grayscale=grayscale
        ))
    except (pyautogui.ImageNotFoundException, Exception):
        pass
        
    if matches:
        # Convert to list of tuples
        results = [(box.left, box.top, box.width, box.height) for box in matches]
        return results

    # Load image once to check dimensions
    template = cv2.imread(target_image_path)
    if template is None:
        return []
        
    h, w = template.shape[:2]

    # 3. Try Downscaling (Retina Fix: 2x capture -> 1x effective search?)
    # Only if image is large enough (> 40px). Downscaling small icons destroys them.
    if w > 40 and h > 40:
        logger.info(f"Grayscale search failed. Retrying with 50% scaled template (Retina fix)...")
        try:
            new_width = int(w * 0.5)
            new_height = int(h * 0.5)
            resized_template = cv2.resize(template, (new_width, new_height), interpolation=cv2.INTER_AREA)
            
            import tempfile, os
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                cv2.imwrite(tmp.name, resized_template)
                tmp_path = tmp.name
                
            try:
                matches = list(pyautogui.locateAllOnScreen(
                    tmp_path,
                    confidence=confidence,
                    region=region,
                    grayscale=grayscale
                ))
            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
                    
            if matches:
                logger.info("Found matches with 50% scale fallback.")
                results = [(box.left, box.top, box.width, box.height) for box in matches]
                return results

        except Exception as e:
            logger.error(f"Error during fallback search: {e}")
            
            
    # 4. Low Confidence Fallback removed per user feedback.
    # It causes false positives on state-sensitive icons (different colors).
    
    return []

def sort_matches(matches: List[Tuple[int, int, int, int]]) -> List[Tuple[int, int, int, int]]:
    """
    Sorts matches by top-left coordinate (y first, then x).
    """
    # Sort by y (top), then x (left)
    return sorted(matches, key=lambda box: (box[1], box[0]))

def deduplicate_matches(
    matches: List[Tuple[int, int, int, int]],
    radius_px: int
) -> List[Tuple[int, int, int, int]]:
    """
    Removes matches that are within radius_px of each other.
    Assumes matches are already sorted by priority if that matters.
    """
    if not matches:
        return []
        
    unique_matches = []
    
    for match in matches:
        mx, my, mw, mh = match
        m_center_x = mx + mw // 2
        m_center_y = my + mh // 2
        
        is_duplicate = False
        for unique in unique_matches:
            ux, uy, uw, uh = unique
            u_center_x = ux + uw // 2
            u_center_y = uy + uh // 2
            
            dist = ((m_center_x - u_center_x) ** 2 + (m_center_y - u_center_y) ** 2) ** 0.5
            if dist < radius_px:
                is_duplicate = True
                break
        
        if not is_duplicate:
            unique_matches.append(match)
            
    return unique_matches

def find_color_on_screen(
    target_hex: str,
    tolerance: int = 10,
    region: Optional[Tuple[int, int, int, int]] = None
) -> List[Tuple[int, int, int, int]]:
    """
    Finds regions matching the target color.
    Returns list of (x, y, w, h) bounding boxes of matching connected components.
    """
    import pyautogui
    import cv2
    import numpy as np
    try:
        # 1. Parse Hex to BGR
        if target_hex.startswith('#'):
            target_hex = target_hex[1:]
        
        r = int(target_hex[0:2], 16)
        g = int(target_hex[2:4], 16)
        b = int(target_hex[4:6], 16)
        
        
        logger.debug(f"DEBUG_COLOR: TargetHex={target_hex}, RGB=({r},{g},{b}), BGR=({b},{g},{r})")
        
        # 2. Capture Screen
        screenshot = pyautogui.screenshot(region=region)
        img = np.array(screenshot)
        logger.debug(f"DEBUG_COLOR: Captured Image Shape={img.shape}")
        
        # DEBUG: Save screenshot to verify what we are searching (User requested)
        import os
        from app.utils.common import get_app_dir
        debug_path = os.path.join(get_app_dir(), "debug_color_search.png")
        logger.debug(f"DEBUG_COLOR: Saving debug image to {debug_path}")
        cv2.imwrite(debug_path, cv2.cvtColor(img, cv2.COLOR_RGB2BGR)) # Save original capture
        
        # Handle RGBA (Mac) -> RGB
        if img.shape[2] == 4:
            img = img[:, :, :3]
            
        # RGB to BGR
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        
        # 3. Create Mask
        lower = np.array([max(0, b - tolerance), max(0, g - tolerance), max(0, r - tolerance)])
        upper = np.array([min(255, b + tolerance), min(255, g + tolerance), min(255, r + tolerance)])
        
        mask = cv2.inRange(img, lower, upper)
        
        # DEBUG: Save mask
        mask_path = os.path.join(get_app_dir(), "debug_color_mask.png")
        cv2.imwrite(mask_path, mask)
        
        # 4. Find Contours (Connected Components)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        logger.debug(f"DEBUG_COLOR: Found {len(contours)} contours")
        
        # DEBUG: Log region and scale
        if region:
            from app.utils.screen_utils import get_screen_scale
            scale = get_screen_scale()
            logger.debug(f"DEBUG_COLOR: Region provided={region}, Scale={scale}")
            
            # Check if capture is 1x (Logical) or 2x (Physical)
            # Img shape is (H, W, C)
            h_img, w_img = img.shape[:2]
            w_region = region[2]
            
            capture_scale = 1.0
            if abs(w_img - w_region * scale) < 5:
                capture_scale = scale # Captured at 2x
                logger.debug("DEBUG_COLOR: Capture is Physical (High-Res)")
            elif abs(w_img - w_region) < 5:
                capture_scale = 1.0 # Captured at 1x
                logger.debug("DEBUG_COLOR: Capture is Logical (Low-Res)")
            else:
                 logger.warning(f"DEBUG_COLOR: Capture size mismatch? Img={w_img}, Region={w_region}")
        else:
            scale = 1.0 # Fallback
            capture_scale = 1.0
            logger.debug("DEBUG_COLOR: No region provided (Full Screen)")
            from app.utils.screen_utils import get_screen_scale
            scale = get_screen_scale()

        matches = []
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            # Filter tiny noise (Require at least 2px dimensions)
            if w >= 2 and h >= 2:
                
                # Normalize to Physical Coordinates (2x)
                if capture_scale == 1.0 and scale > 1.0:
                    # Captured in 1x, need to upscale to Physical
                    x = int(x * scale)
                    y = int(y * scale)
                    w = int(w * scale)
                    h = int(h * scale)
                
                # Add region offset (Region is Logical, so multiply by scale for Physical)
                if region:
                    local_x, local_y = x, y
                    x += int(region[0] * scale)
                    y += int(region[1] * scale)
                    # logger.debug(f"DEBUG_COLOR: Offset calc: LocalScaled({local_x},{local_y}) + RegionScaled({int(region[0]*scale)},{int(region[1]*scale)}) -> Global({x},{y})")
                    
                matches.append((x, y, w, h))
        
        # DEBUG: Draw matches on a result image
        result_img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR).copy()
        for (mx, my, mw, mh) in matches:
            # Note: matches are in GLOBAL coordinates if region is used.
            # But we want to draw on the LOCAL captured image 'img'.
            # We need to reverse the offset for drawing.
            
            draw_x, draw_y = mx, my
            if region:
                 from app.utils.screen_utils import get_screen_scale
                 scale = get_screen_scale()
                 draw_x -= int(region[0] * scale)
                 draw_y -= int(region[1] * scale)
             
            # Scale back to local image coords if image was 1x but matches are 2x
            if capture_scale == 1.0 and scale > 1.0:
                 draw_x = int(draw_x / scale)
                 draw_y = int(draw_y / scale)
                 draw_w = int(mw / scale)
                 draw_h = int(mh / scale)
            else:
                 draw_w = mw
                 draw_h = mh
            
            cv2.rectangle(result_img, (draw_x, draw_y), (draw_x + draw_w, draw_y + draw_h), (0, 255, 0), 2)

        result_path = os.path.join(get_app_dir(), "debug_color_result.png")
        cv2.imwrite(result_path, result_img)
                
        # Sort by visual order (top-left)
        matches = sort_matches(matches)
        return matches
        
    except Exception as e:
        logger.error(f"Error in find_color_on_screen: {e}")
        return []
