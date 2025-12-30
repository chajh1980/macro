import easyocr
import numpy as np
from typing import List, Tuple, Optional
import logging
from PIL import ImageGrab

logger = logging.getLogger("app.core.ocr")

# Initialize reader globally to avoid reloading model
# Note: This might be heavy on startup.
# We can lazy load it if needed.
reader = None

def get_reader():
    global reader
    if reader is None:
        logger.info("Initializing EasyOCR reader...")
        reader = easyocr.Reader(['ko', 'en'], gpu=False) # Force CPU for compatibility if GPU not available
        logger.info("EasyOCR reader initialized.")
    return reader

def find_text_on_screen(
    target_text: str,
    region: Optional[Tuple[int, int, int, int]] = None
) -> Optional[Tuple[int, int, int, int]]:
    """
    Checks if the target text exists in the specified region (or full screen).
    Returns True if found, False otherwise.
    """
    try:
        r = get_reader()
        
        # Capture screen
        if region:
            bbox = (region[0], region[1], region[0] + region[2], region[1] + region[3])
            screenshot = ImageGrab.grab(bbox=bbox)
        else:
            screenshot = ImageGrab.grab()
            
        # Convert to numpy array for EasyOCR
        image_np = np.array(screenshot)
        
        # Read text
        results = r.readtext(image_np)
        
        # Check for target text
        # results format: ([[x,y], [x,y]...], 'text', confidence)
        # results format: ([[x,y], [x,y]...], 'text', confidence)
        for (bbox, text, prob) in results:
            if target_text in text:
                # bbox is list of 4 points [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
                # We need x, y, w, h
                # Usually bbox[0] is top-left, bbox[2] is bottom-right
                tl = bbox[0]
                br = bbox[2]
                
                x = int(tl[0])
                y = int(tl[1])
                w = int(br[0] - tl[0])
                h = int(br[1] - tl[1])
                
                # Correct for region offset if needed
                if region:
                     x += region[0]
                     y += region[1]
                
                return (x, y, w, h)
                
        return None
        
    except Exception as e:
        logger.error(f"Error finding text '{target_text}': {e}")
        return None
