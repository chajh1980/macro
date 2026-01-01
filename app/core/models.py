from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class StepType(str, Enum):
    GENERAL = "GENERAL"
    CONDITION = "CONDITION"
    LOOP = "LOOP"

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

class Action(BaseModel):
    type: ActionType
    # Click specific
    target_x: Optional[int] = None
    target_y: Optional[int] = None
    
    # Goto specific
    goto_step_index: Optional[int] = None # 1-based index as per PRD, but we might convert to 0-based internally

class Step(BaseModel):
    id: str = Field(..., description="Unique identifier for the step")
    name: str = "New Step"
    type: StepType = StepType.GENERAL
    condition: Condition
    action: Action
    next_step_index: Optional[int] = None # Implicitly next, but can be explicit
    step_interval_ms: int = 5

class Workflow(BaseModel):
    name: str
    steps: List[Step] = []
    created_at: str
    updated_at: str
