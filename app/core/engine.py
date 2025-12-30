import time
import logging
import pyautogui
from typing import Optional
from PyQt6.QtCore import QObject, pyqtSignal
from app.core.models import Workflow, Step, ConditionType, ActionType, ImageMatchMode
from app.core.image_proc import find_image_on_screen, sort_matches, deduplicate_matches
# from app.core.ocr import find_text_on_screen # Lazy loaded
from app.utils.screen_utils import physical_to_logical

logger = logging.getLogger("app.core.engine")

class WorkflowRunner(QObject):
    progress_signal = pyqtSignal(int, str) # Step Index, Step Name
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()
    
    def __init__(self, workflow: Workflow, workflow_dir: str = ""):
        super().__init__()
        self.workflow = workflow
        self.workflow_dir = workflow_dir
        self.is_running = False
        self.current_step_index = 0
        self.visited_matches = [] # For sequential image matching

    def stop(self):
        self.is_running = False
        self.log_signal.emit("Stopping workflow...")

    def _interruptible_sleep(self, duration_s: float) -> bool:
        """Sleeps for duration_s but checks is_running every 0.1s. Returns False if stopped."""
        end_time = time.time() + duration_s
        while time.time() < end_time:
            if not self.is_running:
                return False
            time.sleep(min(0.1, end_time - time.time()))
        return True

    def run_step(self, step: Step):
        """Executes a single step for testing purposes."""
        self.is_running = True
        self.log_signal.emit(f"Testing step: {step.name}")
        
        try:
            # 1. Check Condition
            if not self._check_condition(step):
                self.log_signal.emit(f"Condition failed for step {step.name}.")
            else:
                self.log_signal.emit(f"Condition met for step {step.name}.")
                # 2. Execute Action
                if self.is_running:
                    self._execute_action(step)
                    self.log_signal.emit(f"Action executed for step {step.name}.")
        except Exception as e:
            self.log_signal.emit(f"Error testing step: {e}")
        finally:
            self.is_running = False
            self.finished_signal.emit()

    def run(self):
        self.is_running = True
        self.current_step_index = 0
        self.visited_matches = []
        self.last_match_region = None # (x, y, w, h)
        
        self.log_signal.emit(f"Starting workflow: {self.workflow.name}")
        
        try:
            while self.is_running and 0 <= self.current_step_index < len(self.workflow.steps):
                step = self.workflow.steps[self.current_step_index]
                self.progress_signal.emit(self.current_step_index, step.name)
                self.log_signal.emit(f"Executing step {self.current_step_index + 1}: {step.name}")
                
                # Reset match region for this step
                self.last_match_region = None
                
                # 1. Check Condition
                if not self._check_condition(step):
                    self.log_signal.emit(f"Condition failed for step {step.name}. Proceeding...")
                    pass

                # 2. Execute Action
                if self.is_running: 
                    self._execute_action(step)
                
                # 3. Move to next step (unless Goto changed it)
                if step.action.type != ActionType.GOTO:
                    self.current_step_index += 1
                    
                # Step interval
                if not self._interruptible_sleep(step.step_interval_ms / 1000.0):
                    break
                
            self.log_signal.emit("Workflow finished.")
        except Exception as e:
            logger.exception("Error running workflow")
            self.log_signal.emit(f"Critical Error: {e}")
        finally:
            self.is_running = False
            self.finished_signal.emit()

    def _check_condition(self, step: Step) -> bool:
        condition = step.condition
        start_time = time.time()
        
        if condition.type == ConditionType.TIME:
            return self._interruptible_sleep(condition.wait_time_s)
            
        elif condition.type == ConditionType.IMAGE:
            while self.is_running:
                # Infinite retry as requested by user
                # if time.time() - start_time > condition.timeout_s:
                #    logger.warning("Image condition timeout.")
                #    return False
                
                image_path = condition.target_image_path
                if self.workflow_dir and image_path:
                    import os
                    image_path = os.path.join(self.workflow_dir, image_path)
                
                # logger.debug(f"Resolving image path: {condition.target_image_path} -> {image_path}")
                    
                matches = find_image_on_screen(
                    image_path,
                    confidence=condition.confidence
                )
                
                if matches:
                    # Store the first match for Action usage
                    # matches is list of (x, y, w, h) in PHYSICAL pixels
                    self.last_match_region = matches[0]
                    return True
                
                # Retry every 200ms (tuned per user request)
                if not self._interruptible_sleep(0.2):
                    return False
                
        elif condition.type == ConditionType.TEXT:
            try:
                from app.core.ocr import find_text_on_screen
            except ImportError:
                 logger.error("OCR module not available.")
                 return False

            while self.is_running:
                if time.time() - start_time > condition.timeout_s:
                    logger.warning("Text condition timeout.")
                    return False
                
                region = tuple(condition.watch_area) if condition.watch_area else None
                
                found_region = find_text_on_screen(condition.target_text, region=region)
                if found_region:
                    self.last_match_region = found_region # (x, y, w, h)
                    return True
                    
                if not self._interruptible_sleep(condition.scan_interval_ms / 1000.0):
                    return False
                
        return False

    def _execute_action(self, step: Step):
        action = step.action
        
        if action.type == ActionType.NONE:
            return
            
        elif action.type == ActionType.GOTO:
            if action.goto_step_index is not None:
                target_index = action.goto_step_index - 1
                if 0 <= target_index < len(self.workflow.steps):
                    self.current_step_index = target_index
                else:
                    logger.error(f"Invalid Goto index: {action.goto_step_index}")

        elif action.type == ActionType.MOVE:
             # Logic split: 
             # 1. If Condition is IMAGE, target_x/y are OFFSETS from match center.
             # 2. If Condition is TIME/GENERAL, target_x/y are ABSOLUTE coordinates.
             
             move_x = None
             move_y = None
             
             if step.condition.type == ConditionType.IMAGE and self.last_match_region:
                 # Calculate center of last matched region
                 rx, ry, rw, rh = self.last_match_region
                 l_rx, l_ry, l_rw, l_rh = physical_to_logical((rx, ry, rw, rh))
                 center_x = l_rx + l_rw // 2
                 center_y = l_ry + l_rh // 2
                 
                 # Apply offsets (defaults to 0 if None)
                 off_x = action.target_x or 0
                 off_y = action.target_y or 0
                 
                 move_x = center_x + off_x
                 move_y = center_y + off_y
                 logger.info(f"Moving to match center ({center_x}, {center_y}) + offset ({off_x}, {off_y}) = ({move_x}, {move_y})")
                 
             else:
                 # Absolute Move
                 move_x = action.target_x
                 move_y = action.target_y
                 logger.info(f"Moving to absolute: ({move_x}, {move_y})")
             
             if move_x is not None and move_y is not None:
                 pyautogui.moveTo(move_x, move_y)
             else:
                 logger.warning("Move action requested but no target set (or no match found).")
             
        elif action.type == ActionType.CLICK:
             # Click specific coords OR current position
             if action.target_x is not None and action.target_y is not None and (action.target_x != 0 or action.target_y != 0):
                 pyautogui.moveTo(action.target_x, action.target_y)
             
             # If no coords set, it clicks at CURRENT position (which might be where Move Step left it)
             pyautogui.click()
             logger.info("Clicked mouse.")

    def _handle_sequential_click(self, step: Step):
        image_path = step.condition.target_image_path
        if self.workflow_dir and image_path:
            import os
            image_path = os.path.join(self.workflow_dir, image_path)
            
        matches = find_image_on_screen(
            image_path,
            confidence=step.condition.confidence
        )
        
        matches = sort_matches(matches)
        
        valid_match = None
        for match in matches:
            mx, my, mw, mh = match
            # PHYSICAL pixels here
            
            # Convert to Logical for visited check? 
            # Or keep visited in physical?
            # Let's keep visited in physical for consistency with matches, then convert ONLY for click.
            
            center_x = mx + mw // 2
            center_y = my + mh // 2
            
            is_visited = False
            for vx, vy in self.visited_matches:
                dist = ((center_x - vx)**2 + (center_y - vy)**2)**0.5
                if dist < step.condition.deduplicate_radius_px:
                    is_visited = True
                    break
            
            if not is_visited:
                valid_match = (center_x, center_y)
                break
        
        if valid_match:
            cx, cy = valid_match
            # cx, cy are PHYSICAL. Convert to LOGICAL for PyAutoGUI.
            l_cx, l_cy = physical_to_logical((cx, cy))
            
            pyautogui.moveTo(l_cx, l_cy)
            pyautogui.click()
            self.visited_matches.append((cx, cy))
        else:
            logger.info("No new matches found for sequential click.")
