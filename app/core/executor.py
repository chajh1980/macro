import time
import math
import os
from typing import List, Optional, Tuple

import pyautogui as pag
import easyocr
import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal

from app.models.workflow import Workflow, Step, Condition, Action


class Executor(QThread):
    progress = pyqtSignal(str)
    finished = pyqtSignal()
    stopped = pyqtSignal()

    def __init__(self, workflow: Workflow):
        super().__init__()
        self._workflow = workflow
        self._stop_flag = False
        self._visited_points: List[Tuple[int, int]] = []
        self._reader = None  # Lazy load EasyOCR
        # macOS에서 상단 모서리 FailSafe로 조기 중단되는 것을 방지
        try:
            pag.FAILSAFE = False
            pag.PAUSE = 0
        except Exception:
            pass

    def stop(self) -> None:
        self._stop_flag = True

    def run(self) -> None:
        try:
            index = 0
            while 0 <= index < len(self._workflow.steps) and not self._stop_flag:
                step = self._workflow.steps[index]
                print(f"[DEBUG] Executing Step {index + 1}: {step.step_type}, Condition: {step.condition.type}, Action: {step.action.type}")
                self.progress.emit(f"Step {index + 1}: {step.step_type}")
                
                target_point = self._wait_for_condition(step.condition)
                print(f"[DEBUG] Condition Result: {target_point}")
                
                if target_point is None and self._stop_flag:
                    print("[DEBUG] Stopped during condition wait")
                    break
                
                self._perform_action(step.action, target_point)
                print(f"[DEBUG] Action Performed")
                
                # 스텝별 기본 실행 간격
                try:
                    interval_ms = getattr(step, "interval_ms", 5)
                    if interval_ms and interval_ms > 0:
                        time.sleep(min(0.5, interval_ms / 1000.0))
                except Exception:
                    pass

                # Handle goto logic
                if step.action.type == "goto" and step.action.goto:
                    # UI uses 1-based index, convert to 0-based
                    target_idx = step.action.goto.step_index - 1
                    if 0 <= target_idx < len(self._workflow.steps):
                        index = target_idx
                    else:
                        print(f"Invalid goto index: {step.action.goto.step_index}")
                        index += 1
                else:
                    index += 1
        except Exception as e:
            print(f"Execution error: {e}")
        finally:
            self.finished.emit()

    # --- internal helpers ---

    def _get_reader(self):
        if self._reader is None:
            # Load Korean and English
            self._reader = easyocr.Reader(['ko', 'en'], gpu=False) 
        return self._reader

    def _wait_for_condition(self, condition: Condition) -> Optional[Tuple[int, int]]:
        if condition.type == "wait" and condition.wait:
            # interruptible sleep
            total = max(0.0, float(condition.wait.seconds))
            end = time.time() + total
            while not self._stop_flag and time.time() < end:
                time.sleep(min(0.05, end - time.time()))
            return None

        if condition.type == "image" and condition.image:
            return self._wait_for_image_condition(condition)

        if condition.type == "text" and condition.text:
            return self._wait_for_text_condition(condition)

        return None

    def _perform_action(self, action: Action, target_point: Optional[Tuple[int, int]]) -> None:
        if action.type in ("move", "move_click") and action.move:
            self._human_move(action.move.position, duration_s=0.5)
            if action.type == "move_click":
                pag.click()
        elif action.type == "click" and action.click:
            if action.click.use_condition_target and target_point is not None:
                pag.click(target_point)
            elif action.click.position is not None:
                pag.click(action.click.position)
        elif action.type == "keypress" and action.keypress:
            pag.typewrite(action.keypress.text)
        # goto/none: 처리 상 run 루프에서 결정됨

    # image matching util
    @staticmethod
    def _distance(a: Tuple[int, int], b: Tuple[int, int]) -> float:
        return math.hypot(a[0] - b[0], a[1] - b[1])

    @staticmethod
    def _center_of(box) -> Tuple[int, int]:
        return (box.left + box.width // 2, box.top + box.height // 2)

    # smooth human-like mouse move using bezier curve
    def _human_move(self, dest: Tuple[int, int], duration_s: float = 0.5) -> None:
        try:
            start_x, start_y = pag.position()
        except Exception:
            # 일부 환경에서 position()이 실패하면 현재 위치를 (0,0)으로 간주
            start_x, start_y = 0, 0
        end_x, end_y = dest
        # control points: simple quadratic bezier with small curvature
        ctrl_x = (start_x + end_x) / 2.0
        ctrl_y = (start_y + end_y) / 2.0
        # add slight offset based on distance to create curve
        dx = end_x - start_x
        dy = end_y - start_y
        ctrl_x += -dy * 0.1
        ctrl_y += dx * 0.1

        steps = max(10, int(duration_s * 120))
        for i in range(steps + 1):
            t = i / steps
            # quadratic bezier interpolation
            x = (1 - t) * (1 - t) * start_x + 2 * (1 - t) * t * ctrl_x + t * t * end_x
            y = (1 - t) * (1 - t) * start_y + 2 * (1 - t) * t * ctrl_y + t * t * end_y
            try:
                pag.moveTo(int(x), int(y))
            except Exception:
                # 일시적 권한/포커스 문제 시 작은 대기 후 재시도
                time.sleep(0.005)
            time.sleep(max(0.0, duration_s / steps))

    def _wait_for_image_condition(self, condition: Condition) -> Optional[Tuple[int, int]]:
        assert condition.image is not None
        cfg = condition.image

        start = time.time()
        while not self._stop_flag:
            # 템플릿 파일 검증
            if not cfg.template_path or not os.path.exists(cfg.template_path):
                # 템플릿이 설정되지 않았거나 파일이 없으면 폴링 대기
                if cfg.timeout_s is not None and time.time() - start > cfg.timeout_s:
                    return None
                time.sleep(cfg.poll_interval_ms / 1000.0)
                continue

            try:
                boxes = list(
                    pag.locateAllOnScreen(
                        cfg.template_path,
                        region=cfg.watch_area,
                        confidence=cfg.confidence,
                    )
                )
            except Exception:
                # 이미지 읽기 실패(OpenCV 로딩 오류 등) 시에도 폴링 대기
                if cfg.timeout_s is not None and time.time() - start > cfg.timeout_s:
                    return None
                time.sleep(cfg.poll_interval_ms / 1000.0)
                continue

            if not boxes:
                if cfg.timeout_s is not None and time.time() - start > cfg.timeout_s:
                    return None
                time.sleep(cfg.poll_interval_ms / 1000.0)
                continue

            centers: List[Tuple[int, int]] = [self._center_of(b) for b in boxes]
            centers.sort(key=lambda p: (p[1], p[0]))  # top-left first

            if cfg.multi_mode == "single":
                return centers[0]

            # sequential mode: pick next unvisited and click within this wait
            for c in centers:
                if all(self._distance(c, v) >= cfg.min_dedup_distance_px for v in self._visited_points):
                    self._visited_points.append(c)
                    return c

            # all centers are already visited; treat as done for this pass
            return None

        return None

    def _wait_for_text_condition(self, condition: Condition) -> Optional[Tuple[int, int]]:
        assert condition.text is not None
        cfg = condition.text
        reader = self._get_reader()

        start = time.time()
        while not self._stop_flag:
            # Capture screen region
            region = cfg.watch_area
            if region:
                screenshot = pag.screenshot(region=region)
                # Adjust coordinates offset later
                offset_x, offset_y = region[0], region[1]
            else:
                screenshot = pag.screenshot()
                offset_x, offset_y = 0, 0

            # Convert to numpy for EasyOCR
            img_np = np.array(screenshot)
            
            try:
                # Read text
                results = reader.readtext(img_np)
                # results format: ([[x,y],[x,y]...], text, confidence)
                
                for (bbox, text, prob) in results:
                    if cfg.target_text in text:
                        # Found it! Return center
                        (tl, tr, br, bl) = bbox
                        center_x = int((tl[0] + br[0]) / 2) + offset_x
                        center_y = int((tl[1] + br[1]) / 2) + offset_y
                        return (center_x, center_y)
                        
            except Exception as e:
                print(f"OCR Error: {e}")

            if cfg.timeout_s is not None and time.time() - start > cfg.timeout_s:
                return None
            
            time.sleep(0.5) # Poll interval for OCR (slower than image)

        return None
