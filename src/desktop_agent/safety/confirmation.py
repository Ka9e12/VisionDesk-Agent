from __future__ import annotations

from desktop_agent.schema import Action


class Confirmation:
    def __init__(self, *, assume_yes: bool = False) -> None:
        self.assume_yes = assume_yes

    def approve(self, action: Action, reason: str) -> bool:
        if self.assume_yes:
            return True
        print("\n需要确认高风险动作：")
        print(f"- action: {action.type}")
        print(f"- params: {action.params}")
        print(f"- reason: {reason}")
        answer = input("允许执行？输入 yes 继续，其它任意输入取消：").strip().lower()
        return answer in {"yes", "y"}
