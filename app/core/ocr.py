
# import easyocr # REMOVED to save space
import logging
from typing import List, Tuple, Optional

logger = logging.getLogger("app.core.ocr")

def find_text_on_screen(
    target_text: str,
    region: Optional[Tuple[int, int, int, int]] = None
) -> Optional[Tuple[int, int, int, int]]:
    """
    Dummy implementation. OCR has been removed to reduce build size.
    """
    logger.error("OCR functionality has been removed from this build.")
    return None
