from __future__ import annotations

import dataclasses
import json
import shutil
from pathlib import Path
from typing import List, Optional

from app.models.workflow import (
    Workflow,
    Step,
    Condition,
    ImageCondition,
    WaitCondition,
    Action,
    ClickAction,
    KeypressAction,
    GotoAction,
)


def get_workflows_root() -> Path:
    root = Path(__file__).resolve().parents[2] / "workflows"
    root.mkdir(parents=True, exist_ok=True)
    return root


aSYNC_EXTS = {".png", ".jpg", ".jpeg", ".bmp"}


def list_workflows() -> List[str]:
    root = get_workflows_root()
    names: List[str] = []
    for child in sorted(root.iterdir()):
        if child.is_dir() and (child / "flow.json").exists():
            names.append(child.name)
    return names


def _serialize_workflow(wf: Workflow) -> dict:
    def to_dict(obj):
        if dataclasses.is_dataclass(obj):
            return {k: to_dict(v) for k, v in dataclasses.asdict(obj).items()}
        if isinstance(obj, list):
            return [to_dict(x) for x in obj]
        return obj

    return to_dict(wf)


def _deserialize_workflow(data: dict) -> Workflow:
    steps: List[Step] = []
    for s in data.get("steps", []):
        ctype = s["condition"]["type"]
        if ctype == "image":
            img = s["condition"].get("image", {})
            cond = Condition(
                type="image",
                image=ImageCondition(
                    template_path=img.get("template_path", ""),
                    watch_area=tuple(img.get("watch_area")) if img.get("watch_area") else None,
                    confidence=img.get("confidence", 0.9),
                    multi_mode=img.get("multi_mode", "single"),
                    min_dedup_distance_px=img.get("min_dedup_distance_px", 10),
                    poll_interval_ms=img.get("poll_interval_ms", 150),
                    timeout_s=img.get("timeout_s"),
                ),
            )
        elif ctype == "wait":
            cond = Condition(type="wait", wait=WaitCondition(seconds=s["condition"]["wait"]["seconds"]))
        else:
            cond = Condition(type=ctype)

        atype = s["action"]["type"]
        if atype == "click":
            click = s["action"].get("click", {})
            act = Action(
                type="click",
                click=ClickAction(
                    use_condition_target=click.get("use_condition_target", True),
                    position=tuple(click.get("position")) if click.get("position") else None,
                ),
            )
        elif atype == "keypress":
            kp = s["action"].get("keypress", {})
            act = Action(type="keypress", keypress=KeypressAction(text=kp.get("text", "")))
        elif atype == "goto":
            g = s["action"].get("goto", {})
            act = Action(type="goto", goto=GotoAction(step_index=int(g.get("step_index", 0))))
        else:
            act = Action(type="none")

        steps.append(Step(condition=cond, action=act))
    return Workflow(steps=steps)


def load_workflow(name: str) -> Workflow:
    wf_dir = get_workflows_root() / name
    with open(wf_dir / "flow.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    workflow = _deserialize_workflow(data)

    # convert relative asset paths to absolute
    for step in workflow.steps:
        if step.condition.type == "image" and step.condition.image:
            p = step.condition.image.template_path
            if p and not Path(p).is_absolute():
                step.condition.image.template_path = str((wf_dir / p).resolve())
    return workflow


def save_workflow(name: str, workflow: Workflow) -> None:
    wf_root = get_workflows_root()
    wf_dir = wf_root / name
    assets_dir = wf_dir / "assets"
    wf_dir.mkdir(parents=True, exist_ok=True)
    assets_dir.mkdir(parents=True, exist_ok=True)

    # copy image assets and rewrite paths to relative
    used_files = set()
    for step in workflow.steps:
        if step.condition.type == "image" and step.condition.image:
            src = step.condition.image.template_path
            if not src:
                continue
            src_path = Path(src)
            if not src_path.exists():
                # leave as-is if missing
                continue
            ext = src_path.suffix.lower() or ".png"
            if ext not in aSYNC_EXTS:
                ext = ".png"
            # avoid name collision; keep basename if unique
            dest_name = src_path.name if src_path.name not in used_files else f"{src_path.stem}_copy{ext}"
            dest_path = assets_dir / dest_name
            counter = 1
            while dest_path.exists():
                dest_name = f"{src_path.stem}_{counter}{ext}"
                dest_path = assets_dir / dest_name
                counter += 1
            shutil.copy2(src_path, dest_path)
            used_files.add(dest_name)
            # set relative path in model
            step.condition.image.template_path = str(Path("assets") / dest_name)

    # write flow.json with relative paths
    with open(wf_dir / "flow.json", "w", encoding="utf-8") as f:
        json.dump(_serialize_workflow(workflow), f, ensure_ascii=False, indent=2)


def delete_workflow(name: str) -> None:
    wf_dir = get_workflows_root() / name
    if wf_dir.exists():
        shutil.rmtree(wf_dir)
