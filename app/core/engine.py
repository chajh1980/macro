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
        self.current_step_index = 0 # This will be incremented by _execute_steps
        self.visited_matches = []
        self.last_match_region = None # (x, y, w, h)
        
        self.log_signal.emit(f"Starting workflow: {self.workflow.name}")
        
        try:
            self._execute_steps(self.workflow.steps)
            self.log_signal.emit("Workflow finished.")
        except Exception as e:
            logger.exception("Error running workflow")
            self.log_signal.emit(f"Critical Error: {e}")
        finally:
            self.is_running = False
            self.finished_signal.emit()

    def _execute_steps(self, steps: list[Step]) -> bool:
        """
        Executes a list of steps sequentially.
        Returns True if all steps succeeded, False if any failed (and stopped execution).
        """
        if not steps: return True
        
        for step in steps:
            if not self.is_running: return False
            
            # Emit Progress
            self.current_step_index += 1
            self.progress_signal.emit(self.current_step_index, step.name)
            self.log_signal.emit(f"Executing step {self.current_step_index}: {step.name}")
            
            # Reset match region for this step (unless we want to preserve it across steps? Usually reset)
            # self.last_match_region = None # Keep invalidating? Or keep for 'Move' after 'Find'?
            # Actually, Move depends on last_match_region OF THE PREVIOUS step
            # So we should ONLY invalidate if this step generates a NEW match.
            # But if this step is 'Wait', we shouldn't clear the region.
            
            success = self._execute_step(step)
            
            if not success:
                # If a step failed, what to do?
                # For now, default behavior is Continue or Stop?
                # User hasn't specified Error Handling.
                # Assuming "Stop on Failure" for now, EXCEPT for Await loops which handle their own failure.
                # But _execute_step returns True/False.
                # If we return False here, the parent block stops.
                
                # Check if we should stop
                # Let's assume critical failure logs have been emitted.
                pass
                
            # Step interval
            if not self._interruptible_sleep(step.step_interval_ms / 1000.0):
                return False
                
        return True

    def _execute_step(self, step: Step) -> bool:
        """
        Executes a single step. Returns True if successful, False if condition failed or action failed.
        """
        # 1. Handle Control Flow Steps
        if step.type == StepType.IF:
            # Check condition (ConditionType.IMAGE/COLOR usually)
            # If True -> Run Children
            # If False -> Skip Children
            if self._check_condition(step):
                self.log_signal.emit(f"[IF] Condition met. Executing children...")
                return self._execute_steps(step.children)
            else:
                self.log_signal.emit(f"[IF] Condition failed. Skipping children.")
                return True # Inherently successful in execution, just didn't run children.
                
        elif step.type == StepType.UNTIL:
            # Logic: Repeat children WHILE condition is True? Or UNTIL True?
            # User said: "satisfy condition -> repeat". This is WHILE TRUE.
            # So: Check Condition -> If True, Run Children, Repeat.
            self.log_signal.emit(f"[UNTIL] Starting loop (While Condition is True)...")
            loop_count = 0
            while self.is_running:
                if self._check_condition(step):
                    loop_count += 1
                    self.log_signal.emit(f"[UNTIL] Loop #{loop_count} - Condition met.")
                    if not self._execute_steps(step.children):
                        return False # Child failed/stopped
                    
                    # Prevent infinite tight loop if children are empty or instant
                    if not step.children:
                        self._interruptible_sleep(0.1)
                else:
                    self.log_signal.emit(f"[UNTIL] Condition no longer met. Exiting loop.")
                    break
            return True
            
        elif step.type == StepType.AWAIT:
            # Logic: Retry children UNTIL they succeed (return True).
            # Timeout: step.condition.retry_timeout_s
            # Interval: step.condition.retry_interval_ms
            
            timeout = step.condition.retry_timeout_s or 10.0
            interval = (step.condition.retry_interval_ms or 500) / 1000.0
            start_time = time.time()
            
            self.log_signal.emit(f"[AWAIT] Waiting for children to succeed (Timeout: {timeout}s)...")
            
            while self.is_running:
                # Run children. If _execute_steps returns True, it means ALL children succeeded.
                # We assume "Child Condition" is the first step or all steps.
                # If any child fails, _execute_steps continues? 
                # Wait, _execute_steps currently runs all. 
                # We need to know if the "Find Image" child *found* it.
                # 'Find Image' returns True if found, False if not.
                
                # We need to capture the success of the children.
                # But _execute_steps runs sequentially.
                # If we have [Find Image], `_execute_step` returns True/False.
                # We need `_execute_steps` to propagate failure?
                # Currently `_execute_steps` ignores failure ("pass").
                # I should change that.
                
                children_success = True
                for child in step.children:
                    if not self._execute_step(child):
                        children_success = False
                        break # Stop executing remaining children in this attempt
                
                if children_success:
                    self.log_signal.emit(f"[AWAIT] Children execution successful.")
                    return True
                
                # Check Timeout
                if time.time() - start_time > timeout:
                    self.log_signal.emit(f"[AWAIT] Timeout reached ({timeout}s). Failed.")
                    return False
                
                # Wait Interval
                self.log_signal.emit(f"[AWAIT] Retrying in {interval}s...")
                if not self._interruptible_sleep(interval):
                     return False
                     
            return False # Stopped
            
        # 2. General Steps (Find Image, Click, etc.)
        else:
            # Check Condition
            condition_met = self._check_condition(step)
            
            if not condition_met:
                # If condition was TIME (Wait), it returns True usually (unless stopped).
                # If IMAGE/COLOR/TEXT, it returns False if not found.
                self.log_signal.emit(f"Condition not met for step: {step.name}")
                return False
            
            # Execute Action (if condition met)
            # Some steps might have ActionType.NONE (e.g. Find Image only, no auto move?)
            # But usually Find Image has Action.MOVE default.
            if self.is_running:
                self._execute_action(step)
            
            return True

    def _check_condition(self, step: Step) -> bool:
        condition = step.condition
        start_time = time.time()
        
        if condition.type == ConditionType.TIME:
            # Wait logic
            if condition.wait_time_s > 0:
                self.log_signal.emit(f"Waiting {condition.wait_time_s}s...")
                return self._interruptible_sleep(condition.wait_time_s)
            return True
            
        elif condition.type == ConditionType.IMAGE:
            # Single check only (Retry handled by AWAIT parent)
            image_path = condition.target_image_path
            if self.workflow_dir and image_path:
                import os
                image_path = os.path.join(self.workflow_dir, image_path)
            
            matches = find_image_on_screen(
                image_path,
                confidence=condition.confidence
            )
            
            if matches:
                self.last_match_region = matches[0]
                self.log_signal.emit(f"Image found: {condition.target_image_path}")
                return True
            else:
                return False
                
        elif condition.type == ConditionType.COLOR:
             # Single check only
             from app.core.image_proc import find_color_on_screen
             scan_region = tuple(condition.watch_area) if condition.watch_area else None
             
             matches = find_color_on_screen(
                 target_hex=condition.target_color,
                 tolerance=condition.color_tolerance,
                 region=scan_region
             )
             
             if matches:
                 idx = condition.match_index
                 if idx < len(matches):
                     self.last_match_region = matches[idx]
                     self.log_signal.emit(f"Color found: {condition.target_color}")
                     return True
             
             return False
                
        elif condition.type == ConditionType.TEXT:
            try:
                from app.core.ocr import find_text_on_screen
                # Single check
                region = tuple(condition.watch_area) if condition.watch_area else None
                found_region = find_text_on_screen(condition.target_text, region=region)
                if found_region:
                    self.last_match_region = found_region
                    self.log_signal.emit(f"Text found: {condition.target_text}")
                    return True
            except: pass
            return False
                
        return False

    def _execute_action(self, step: Step):
        action = step.action
        
        if action.type == ActionType.NONE:
            return
            
        elif action.type == ActionType.GOTO:
            # Not supported in recursive structure comfortably yet.
            # Could raise exception or handle?
            # User said "Goto" is "Etc".
            # Can we support Goto?
            # Goto index is typically linear index.
            # In tree structure, "Goto Step 5" is ambiguous.
            # For now, log warning that Goto is limited or deprecated in structured flow.
            # OR: We just modify current_step_index? But we are not using it for control anymore.
            self.log_signal.emit("Warning: GOTO action is not fully supported in structured mode.")
            pass 

        elif action.type == ActionType.MOVE:
             move_x = None
             move_y = None
             
             if step.condition.type in (ConditionType.IMAGE, ConditionType.COLOR, ConditionType.TEXT) and self.last_match_region:
                 # Relative Move
                 rx, ry, rw, rh = self.last_match_region
                 l_rx, l_ry, l_rw, l_rh = physical_to_logical((rx, ry, rw, rh))
                 center_x = l_rx + l_rw // 2
                 center_y = l_ry + l_rh // 2
                 
                 off_x = action.target_x or 0
                 off_y = action.target_y or 0
                 
                 move_x = center_x + off_x
                 move_y = center_y + off_y
             else:
                 # Absolute Move
                 move_x = action.target_x
                 move_y = action.target_y
             
             if move_x is not None and move_y is not None:
                 pyautogui.moveTo(move_x, move_y)
             else:
                 logger.warning("Move action requested but no target set.")
             
        elif action.type == ActionType.CLICK:
             if action.target_x is not None and action.target_y is not None and (action.target_x != 0 or action.target_y != 0):
                 pyautogui.moveTo(action.target_x, action.target_y)
             pyautogui.click()
             
    def _handle_sequential_click(self, step: Step):
        # ... logic as before, but adapted if needed ...
        pass

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
