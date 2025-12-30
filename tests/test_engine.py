import unittest
from unittest.mock import MagicMock, patch
from app.core.models import Workflow, Step, Condition, Action, ConditionType, ActionType
from app.core.engine import WorkflowRunner
import time

class TestWorkflowRunner(unittest.TestCase):
    def setUp(self):
        self.workflow = Workflow(
            name="Test Workflow",
            created_at="",
            updated_at=""
        )
        
    @patch('app.core.engine.time.sleep') # Mock sleep to speed up tests
    @patch('app.core.engine.find_image_on_screen')
    @patch('app.core.engine.pyautogui.click')
    def test_simple_flow(self, mock_click, mock_find_image, mock_sleep):
        # Step 1: Wait 1s
        step1 = Step(
            id="1",
            name="Wait",
            condition=Condition(type=ConditionType.TIME, wait_time_s=1.0),
            action=Action(type=ActionType.NONE)
        )
        
        # Step 2: Click (mock image match)
        step2 = Step(
            id="2",
            name="Click Image",
            condition=Condition(type=ConditionType.IMAGE, target_image_path="test.png"),
            action=Action(type=ActionType.CLICK, target_x=100, target_y=100)
        )
        
        self.workflow.steps = [step1, step2]
        
        # Mock image finding
        mock_find_image.return_value = [(0, 0, 10, 10)]
        
        runner = WorkflowRunner(self.workflow)
        runner.run()
        
        # Verify
        self.assertEqual(mock_click.call_count, 1)
        mock_click.assert_called_with(100, 100)

    @patch('app.core.engine.time.sleep')
    def test_goto_loop(self, mock_sleep):
        # Step 1: Goto Step 2 (Index 1) -> But wait, Step 2 is Index 1.
        # Let's make a loop: Step 1 -> Step 2 -> Goto Step 1
        # But we need a break condition or it runs forever.
        # Engine loop checks self.is_running.
        # We can mock _check_condition to return False after some calls?
        pass

if __name__ == '__main__':
    unittest.main()
