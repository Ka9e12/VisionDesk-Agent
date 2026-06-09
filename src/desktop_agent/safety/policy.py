from __future__ import annotations

import re
from dataclasses import dataclass

from desktop_agent.schema import Action


HIGH_RISK_PATTERNS = [
    r"\bdelete\b",
    r"\bremove\b",
    r"\berase\b",
    r"\bsubmit\b",
    r"\bsend\b",
    r"\bpurchase\b",
    r"\bbuy\b",
    r"\bpay\b",
    r"\btransfer\b",
    r"\brm\s+-",
    r"删除",
    r"移除",
    r"清空",
    r"发送",
    r"提交",
    r"支付",
    r"购买",
    r"转账",
    r"下单",
    r"注销",
]

MEDIUM_RISK_ACTIONS = {"type_text", "hotkey", "press", "drag_to"}
LOW_RISK_ACTIONS = {
    "move_mouse",
    "click",
    "double_click",
    "right_click",
    "scroll",
    "wait",
    "open_app",
    "open_url",
    "finish",
    "ask_user",
    "key_down",
    "key_up",
}


@dataclass(frozen=True)
class RiskAssessment:
    level: str
    reason: str
    requires_confirmation: bool


class RiskPolicy:
    def __init__(self, *, require_confirmation: bool = True) -> None:
        self.require_confirmation = require_confirmation

    def assess(self, task: str, action: Action) -> RiskAssessment:
        declared = action.risk.lower().strip()
        action_text = f"{task}\n{action.reason}\n{action.type}\n{action.params}"
        if declared in {"high", "dangerous"}:
            return self._result("high", "planner marked action as high risk")

        for pattern in HIGH_RISK_PATTERNS:
            if re.search(pattern, action_text, flags=re.IGNORECASE):
                return self._result("high", f"matched high-risk pattern: {pattern}")

        if action.type not in LOW_RISK_ACTIONS and action.type not in MEDIUM_RISK_ACTIONS:
            return self._result("high", f"unknown action type: {action.type}")

        if action.type in MEDIUM_RISK_ACTIONS or declared == "medium":
            return self._result("medium", f"{action.type} can change application state")

        return self._result("low", "low-risk action")

    def _result(self, level: str, reason: str) -> RiskAssessment:
        should_confirm = self.require_confirmation and level in {"high"}
        return RiskAssessment(level, reason, should_confirm)
