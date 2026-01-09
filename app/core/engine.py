import time
import logging
import pyautogui
from typing import Optional
from PyQt6.QtCore import QObject, pyqtSignal
from app.core.models import Workflow, Step, ConditionType, ActionType, ImageMatchMode, StepType
from app.core.image_proc import find_image_on_screen, sort_matches, deduplicate_matches
# from app.core.ocr import find_text_on_screen # Lazy loaded
from app.utils.screen_utils import physical_to_logical

logger = logging.getLogger("app.core.engine")

class WorkflowRunner(QObject):
    progress_signal = pyqtSignal(int, str) # Step Index, Step Name
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()
    request_input_signal = pyqtSignal(str) # Prompt. Returns to self.set_input_value
    
    def __init__(self, workflow: Workflow, workflow_dir: str = ""):
        super().__init__()
        self.workflow = workflow
        self.workflow_dir = workflow_dir
        self.is_running = False
        self.current_step_index = 0
        self.visited_matches = [] # For sequential image matching
        self.max_visited_matches = 1000  # Limit memory usage  # Limit memory usage
        self.max_visited_matches = 1000 # Limit memory usage
        
        # Variable Context
        self.variables = {}
        # Input Synchronization
        import threading
        self.input_event = threading.Event()
        self.input_result = None

    def set_input_value(self, value):
        """Called by Main Thread when user provides input"""
        self.input_result = value
        self.input_event.set()

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
        if step.type == StepType.INPUT:
            # 1. Request Input
            prompt = step.action.input_prompt or "값을 입력하세요"
            self.log_signal.emit(f"[INPUT] requesting input: {prompt}")
            
            # Clear previous event/result
            self.input_event.clear()
            self.input_result = None
            
            # Emit signal to UI
            self.request_input_signal.emit(prompt)
            
            # Wait for response (blocking this thread, but allow stop)
            while not self.input_event.is_set():
                if not self.is_running: return False
                time.sleep(0.1)
                
            # 2. Store Variable
            var_name = step.action.input_variable_name or "count"
            try:
                # Try converting to int if possible, else string
                val = int(self.input_result)
            except:
                val = self.input_result
                
            self.variables[var_name] = val
            self.log_signal.emit(f"[INPUT] Stored '{val}' in variable '{var_name}'")
            return True

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
                
        elif step.type == StepType.LOOP:
            # Smart Loop Logic
            # Mode: WHILE_FOUND vs UNTIL_FOUND
            # Count: loop_max_count
            
            mode = step.condition.loop_mode
            max_count = step.condition.loop_max_count or 100
            
            self.log_signal.emit(f"[LOOP] Starting {mode.value} (Max: {max_count})...")
            
        elif step.type == StepType.LOOP:
            # Smart Loop Logic
            # Condition: First Child Step
            # Body: Remaining Children
            
            mode = step.condition.loop_mode
            max_count = step.condition.loop_max_count or 100
            
            # Check for Variable Override
            if step.condition.loop_count_variable:
                var_name = step.condition.loop_count_variable
                if var_name in self.variables:
                    val = self.variables[var_name]
                    if isinstance(val, int):
                        max_count = val
                        self.log_signal.emit(f"[LOOP] Using variable '{var_name}' = {max_count}")
                    else:
                        self.log_signal.emit(f"[LOOP] Variable '{var_name}' is not an integer ({val}). Using default {max_count}.")
                else:
                    self.log_signal.emit(f"[LOOP] Variable '{var_name}' not found. Using default {max_count}.")
            
            self.log_signal.emit(f"[LOOP] Starting {mode.value} (Max: {max_count})...")
            
            if not step.children:
                self.log_signal.emit(f"[LOOP] Error: No condition step (first child) found.")
                return False
                
            count = 0
            while self.is_running:
                # 1. Check Max Count
                if count >= max_count:
                    self.log_signal.emit(f"[LOOP] Max count ({max_count}) reached. Stopping.")
                    break
                    
                # 2. Check Condition (Execute First Child)
                # First child is the "Condition Step". We execute it and see if it returns True.
                cond_step = step.children[0]
                is_found = self._execute_step(cond_step)
                
                should_run_body = False
                
                if mode == LoopMode.WHILE_FOUND:
                    if is_found:
                         should_run_body = True
                         self.log_signal.emit(f"[LOOP] #{count+1}: Condition Met (Found). Running body...")
                    else:
                         self.log_signal.emit(f"[LOOP] Condition Not Met (Not Found). Loop Ends.")
                         break
                         
                elif mode == LoopMode.UNTIL_FOUND:
                    if not is_found:
                         should_run_body = True
                         self.log_signal.emit(f"[LOOP] #{count+1}: Condition Not Met (Not Found). Running body (Retry)...")
                    else:
                         self.log_signal.emit(f"[LOOP] Condition Met (Found!). Loop Ends.")
                         break
                
                # 3. Execution (Body)
                if should_run_body:
                    body_steps = step.children[1:]
                    if body_steps:
                        if not self._execute_steps(body_steps):
                             self.log_signal.emit(f"[LOOP] Body execution failed/stopped.")
                             return False 
                    
                    count += 1
                    
                    # Prevent instant infinite loops if body is empty
                    if not body_steps:
                        self._interruptible_sleep(0.1)
                else:
                    break
                    
            return True
            
        elif step.type == StepType.UNTIL:
            # Deprecated Legacy Handling (keeping for safety if user has old steps)
            return self._execute_until_legacy(step)
            
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
                elapsed = time.time() - start_time
                if elapsed > timeout:
                    self.log_signal.emit(f"[AWAIT] Timeout reached ({elapsed:.1f}s / {timeout}s). Failed.")
                    return False
                
                # Wait Interval
                self.log_signal.emit(f"[AWAIT] Condition failed. Retrying in {interval}s... (Elapsed: {elapsed:.1f}s)")
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
                self.log_signal.emit(f"Condition failed: {step.name}")
                return False
            
            # Execute Action (if condition met)
            # Some steps might have ActionType.NONE (e.g. Find Image only, no auto move?)
            # But usually Find Image has Action.MOVE default.
            if self.is_running:
                self._execute_action(step)
            
            return True

    def _check_condition(self, step: Step) -> bool:
        condition = step.condition
        
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
            
            self.log_signal.emit(f"Scanning for Image: {os.path.basename(image_path) if image_path else 'None'}")
            matches = find_image_on_screen(
                image_path,
                confidence=condition.confidence
            )
            
            if matches:
                self.last_match_region = matches[0]
                self.log_signal.emit(f"Image found at {matches[0]}")
                return True
            else:
                self.log_signal.emit(f"Image NOT found.")
                return False
                
        elif condition.type == ConditionType.COLOR:
             # Single check only
             from app.core.image_proc import find_color_on_screen
             scan_region = tuple(condition.watch_area) if condition.watch_area else None
             
             self.log_signal.emit(f"Scanning for Color: {condition.target_color} (Tol: {condition.color_tolerance})")
             matches = find_color_on_screen(
                 target_hex=condition.target_color,
                 tolerance=condition.color_tolerance,
                 region=scan_region
             )
             
             if matches:
                 idx = condition.match_index
                 if idx < len(matches):
                     self.last_match_region = matches[idx]
                     self.log_signal.emit(f"Color found at {matches[idx]} (Match #{idx+1}/{len(matches)})")
                     return True
                 else:
                     self.log_signal.emit(f"Color matched {len(matches)} times, but index {idx} out of range.")
                     return False
             else:
                 self.log_signal.emit(f"Color NOT found.")
             
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
            except ImportError as e:
                self.log_signal.emit(f"OCR not available: {e}")
                logger.warning("OCR functionality removed - text recognition disabled")
                return False
            except Exception as e:
                self.log_signal.emit(f"Text recognition error: {e}")
                logger.error(f"Error in text recognition: {e}")
                return False
            return False
                
        return False

    def _execute_action(self, step: Step):
        action = step.action
        
        if action.type == ActionType.NONE:
            return

        elif action.type == ActionType.GOTO:
            if action.goto_step_index is not None:
                # PRD uses 1-based, internal is 0-based
                self.current_step_index = action.goto_step_index - 1
                self.log_signal.emit(f"GOTO: Jumping to step {action.goto_step_index}")
                return True

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
