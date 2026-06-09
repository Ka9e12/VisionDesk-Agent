from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


def _parse_bool(value: Any, field_name: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "y", "on"}:
            return True
        if normalized in {"0", "false", "no", "n", "off", ""}:
            return False
    if isinstance(value, int) and value in {0, 1}:
        return bool(value)
    raise ValueError(f"Planner field '{field_name}' must be a boolean")


@dataclass
class ScreenImage:
    path: Path
    width: int
    height: int
    base64_png: str
    mime_type: str = "image/png"
    original_width: int | None = None
    original_height: int | None = None
    desktop_width: int | None = None
    desktop_height: int | None = None
    origin_x: int = 0
    origin_y: int = 0
    capture_source: str = ""
    capture_scope: str = "screen"

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "path": str(self.path),
            "width": self.width,
            "height": self.height,
            "mime_type": self.mime_type,
            "coordinate_space": "screenshot_image_pixels",
            "capture_scope": self.capture_scope,
            "encoded_bytes": len(self.base64_png),
            "has_image": bool(self.base64_png),
        }

    def to_diagnostic_dict(self) -> dict[str, Any]:
        original_width = self.original_width or self.width
        original_height = self.original_height or self.height
        desktop_width = self.desktop_width or original_width
        desktop_height = self.desktop_height or original_height
        return {
            **self.to_public_dict(),
            "original_width": original_width,
            "original_height": original_height,
            "desktop_width": desktop_width,
            "desktop_height": desktop_height,
            "origin_x": self.origin_x,
            "origin_y": self.origin_y,
            "scale_x": desktop_width / self.width if self.width else 1.0,
            "scale_y": desktop_height / self.height if self.height else 1.0,
            "capture_source": self.capture_source,
            "capture_scope": self.capture_scope,
        }

    def to_desktop_point(self, x: int, y: int) -> tuple[int, int]:
        image_width = self.width or self.original_width or 0
        image_height = self.height or self.original_height or 0
        original_width = self.original_width or image_width
        original_height = self.original_height or image_height
        desktop_width = self.desktop_width or original_width
        desktop_height = self.desktop_height or original_height

        if image_width > 0:
            x = max(0, min(int(x), image_width - 1))
        if image_height > 0:
            y = max(0, min(int(y), image_height - 1))

        if image_width > 0 and desktop_width > 0:
            desktop_x = round(x * desktop_width / image_width)
            desktop_x = max(0, min(desktop_x, desktop_width - 1))
        else:
            desktop_x = int(x)

        if image_height > 0 and desktop_height > 0:
            desktop_y = round(y * desktop_height / image_height)
            desktop_y = max(0, min(desktop_y, desktop_height - 1))
        else:
            desktop_y = int(y)

        return self.origin_x + desktop_x, self.origin_y + desktop_y


@dataclass
class WindowState:
    active_app: str | None = None
    active_window_title: str | None = None
    mouse_position: tuple[int, int] | None = None
    active_window_bounds: dict[str, int] | None = None


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
            done=_parse_bool(raw.get("done", False), "done"),
            final_answer=str(raw.get("final_answer", "")),
            needs_user=_parse_bool(raw.get("needs_user", False), "needs_user"),
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
