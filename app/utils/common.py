import logging
import os
import sys

def setup_logging(name: str = "app"):
    logger = logging.getLogger(name)
    log_level = logging.DEBUG if is_debug_mode() else logging.INFO
    logger.setLevel(log_level)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)

    if not logger.handlers:
        logger.addHandler(handler)

    return logger

def get_project_root() -> str:
    if getattr(sys, 'frozen', False):
         # Running as compiled executable
         # Return directory of executable
         return os.path.dirname(sys.executable)
    else:
        # Running as script
        # Assuming this file is in app/utils/common.py
        return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def get_workflows_dir() -> str:
    return os.path.join(get_project_root(), "workflows")

def get_app_dir() -> str:
    return get_project_root()

def is_debug_mode() -> bool:
    return os.getenv("AUTOMACRO_DEBUG", "0") == "1"
