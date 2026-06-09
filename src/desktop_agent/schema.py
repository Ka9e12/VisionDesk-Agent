from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ScreenImage:
    path: Path
    width: int
    height: int
    base64_png: str
    mime_type: str = "image/png"

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "path": str(self.path),
            "width": self.width,
            "height": self.height,
            "mime_type": self.mime_type,
            "encoded_bytes": len(self.base64_png),
            "has_image": bool(self.base64_png),
        }


@dataclass
class WindowState:
    active_app: str | None = None
    active_window_title: str | None = None
    mouse_position: tuple[int, int] | None = None


@dataclass
class Observation:
    task: str
    step: int
    screen: ScreenImage
    window: WindowState = field(default_factory=WindowState)
    ocr_text: str | None = None
    browser_dom: dict[str, Any] | None = None
    accessibility_tree: dict[str, Any] | None = None
    recent_actions: list[dict[str, Any]] = field(default_factory=list)

    def to_prompt_dict(self) -> dict[str, Any]:
        return {
            "task": self.task,
            "step": self.step,
            "screen": self.screen.to_public_dict(),
            "window": asdict(self.window),
            "ocr_text": self.ocr_text,
            "browser_dom": self.browser_dom,
            "accessibility_tree": self.accessibility_tree,
            "recent_actions": self.recent_actions[-8:],
        }


@dataclass
class Action:
    type: str
    params: dict[str, Any] = field(default_factory=dict)
    reason: str = ""
    risk: str = "low"

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "Action":
        if "type" not in raw:
            raise ValueError("Action is missing required field: type")
        params = raw.get("params")
        if params is None:
            params = {
                key: value
                for key, value in raw.items()
                if key not in {"type", "reason", "risk"}
            }
        if not isinstance(params, dict):
            raise ValueError("Action params must be an object")
        return cls(
            type=str(raw["type"]),
            params=params,
            reason=str(raw.get("reason", "")),
            risk=str(raw.get("risk", "low")),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "params": self.params,
            "reason": self.reason,
            "risk": self.risk,
        }


@dataclass
class ActionResult:
    action: Action
    success: bool
    message: str
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action.to_dict(),
            "success": self.success,
            "message": self.message,
            "data": self.data,
        }


@dataclass
class PlanDecision:
    thought: str
    actions: list[Action] = field(default_factory=list)
    done: bool = False
    final_answer: str = ""
    needs_user: bool = False
    user_question: str = ""

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "PlanDecision":
        actions_raw = raw.get("actions", [])
        if actions_raw is None:
            actions_raw = []
        if not isinstance(actions_raw, list):
            raise ValueError("Planner field 'actions' must be a list")
        return cls(
            thought=str(raw.get("thought", "")),
            actions=[Action.from_dict(item) for item in actions_raw],
            done=bool(raw.get("done", False)),
            final_answer=str(raw.get("final_answer", "")),
            needs_user=bool(raw.get("needs_user", False)),
            user_question=str(raw.get("user_question", "")),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "thought": self.thought,
            "actions": [action.to_dict() for action in self.actions],
            "done": self.done,
            "final_answer": self.final_answer,
            "needs_user": self.needs_user,
            "user_question": self.user_question,
        }
