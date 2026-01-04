from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class StepType(str, Enum):
    GENERAL = "GENERAL"
    CONDITION = "CONDITION"
    LOOP = "LOOP" # Replaces UNTIL conceptually
    IF = "IF"
    UNTIL = "UNTIL" # Legacy, keep for now or deprecate
    AWAIT = "AWAIT"
    INPUT = "INPUT"
    INPUT = "INPUT"

class ConditionType(str, Enum):
    IMAGE = "IMAGE"
    TEXT = "TEXT"
    COLOR = "COLOR"
    TIME = "TIME"

class ActionType(str, Enum):
    CLICK = "CLICK"
    MOVE = "MOVE"
    GOTO = "GOTO"
    NONE = "NONE"
    
class ImageMatchMode(str, Enum):
    SINGLE = "SINGLE"
    SEQUENTIAL = "SEQUENTIAL"

class LoopMode(str, Enum):
    WHILE_FOUND = "WHILE_FOUND" # Run while condition is met
    UNTIL_FOUND = "UNTIL_FOUND" # Run until condition is met

class Condition(BaseModel):
    type: ConditionType
    # Image specific
    target_image_path: Optional[str] = None
    match_mode: ImageMatchMode = ImageMatchMode.SINGLE
    confidence: float = 0.8
    scan_interval_ms: int = 500
    timeout_s: float = 10.0
    deduplicate_radius_px: int = 10
    
    # Text specific
    target_text: Optional[str] = None
    watch_area: Optional[List[int]] = None # [x, y, w, h]
    
    # Color specific
    target_color: Optional[str] = None # Hex "#RRGGBB"
    color_tolerance: int = 0
    match_index: int = 0 # 0=First match, 1=Second...
    
    # Time specific
    wait_time_s: float = 0.0
    
    # Await / Retry Policy (for If/Until/Wait)
    retry_timeout_s: float = 5.0 # Total max time to retry
    retry_interval_ms: int = 500   # Interval between checks
    
    # Smart Loop Configuration
    loop_mode: LoopMode = LoopMode.UNTIL_FOUND
    loop_max_count: int = 100 # Safety limit
    loop_count_variable: Optional[str] = None # New: Use variable for loop count

class Action(BaseModel):
    type: ActionType
    # Click specific
    target_x: Optional[int] = None
    target_y: Optional[int] = None
    
    # Goto specific
    goto_step_index: Optional[int] = None # 1-based index as per PRD, but we might convert to 0-based internally
    input_variable_name: Optional[str] = "count" # New: Variable name to store input
    input_prompt: str = "값을 입력하세요" # New: Text to show user

class Step(BaseModel):
    id: str = Field(..., description="Unique identifier for the step")
    name: str = "New Step"
    type: StepType = StepType.GENERAL
    condition: Condition
    action: Action
    children: List['Step'] = Field(default_factory=list) # Nested steps for If/Until
    next_step_index: Optional[int] = None # Implicitly next, but can be explicit
    step_interval_ms: int = 5

class Workflow(BaseModel):
    name: str
    steps: List[Step] = []
    created_at: str
    updated_at: str
