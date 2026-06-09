from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from desktop_agent.schema import ActionResult


@dataclass
class TaskMemory:
    task: str
    notes: list[str] = field(default_factory=list)
    action_results: list[dict[str, Any]] = field(default_factory=list)
    user_messages: list[str] = field(default_factory=list)

    def add_result(self, result: ActionResult) -> None:
        self.action_results.append(result.to_dict())

    def add_note(self, note: str) -> None:
        self.notes.append(note)

    def add_user_message(self, message: str) -> None:
        self.user_messages.append(message)

    def recent_actions(self, limit: int = 8) -> list[dict[str, Any]]:
        return self.action_results[-limit:]

    def to_prompt_dict(self) -> dict[str, Any]:
        return {
            "task": self.task,
            "notes": self.notes[-12:],
            "recent_action_results": self.recent_actions(),
            "user_messages": self.user_messages[-6:],
        }
