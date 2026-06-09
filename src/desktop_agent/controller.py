from __future__ import annotations

import re
import time
from dataclasses import dataclass

from desktop_agent.actions.executor import ActionExecutor
from desktop_agent.config import AgentConfig
from desktop_agent.memory.task_memory import TaskMemory
from desktop_agent.perception.collector import PerceptionCollector
from desktop_agent.planner.openai_compatible import OpenAICompatiblePlanner, PlannerError
from desktop_agent.runtime.logger import RunLogger
from desktop_agent.safety.confirmation import Confirmation
from desktop_agent.safety.policy import RiskPolicy
from desktop_agent.schema import Action


@dataclass
class RunResult:
    success: bool
    message: str
    log_dir: str


class AgentController:
    def __init__(self, config: AgentConfig) -> None:
        self.config = config
        self.logger = RunLogger(config.log_dir)
        self.memory = None
        self.perception = PerceptionCollector(config, self.logger)
        self.planner = OpenAICompatiblePlanner(config)
        self.executor = ActionExecutor(dry_run=config.dry_run)
        self.policy = RiskPolicy(require_confirmation=config.require_confirmation)
        self.confirmation = Confirmation(assume_yes=config.assume_yes)

    def run(self, task: str) -> RunResult:
        self.memory = TaskMemory(task)
        self.logger.log("run_started", {"task": task, "dry_run": self.config.dry_run})

        for step in range(1, self.config.max_steps + 1):
            step_started = time.perf_counter()
            print(f"\n[step {step}] observe")
            observe_started = time.perf_counter()
            observation = self.perception.collect(
                task=task,
                step=step,
                recent_actions=self.memory.recent_actions() if self.memory else [],
            )
            observe_seconds = time.perf_counter() - observe_started
            print(f"[step {step}] observe done {observe_seconds:.2f}s")
            self.logger.log("observation", observation.to_prompt_dict())

            print("[step {step}] think".format(step=step))
            think_started = time.perf_counter()
            try:
                decision = self.planner.decide(task, observation, self.memory)
            except PlannerError as exc:
                self.logger.log("planner_error", {"message": str(exc)})
                return RunResult(False, str(exc), str(self.logger.run_dir))
            think_seconds = time.perf_counter() - think_started
            print(f"[step {step}] think done {think_seconds:.2f}s")

            self.logger.log("decision", decision.to_dict())
            if decision.thought:
                print(f"thought: {decision.thought}")

            if decision.needs_user:
                question = decision.user_question or "需要你提供更多信息。"
                answer = input(f"{question}\n> ")
                self.memory.add_user_message(answer)
                self.logger.log("user_response", {"question": question, "answer": answer})
                continue

            if decision.done:
                message = decision.final_answer or "任务已完成。"
                self.logger.log("run_finished", {"success": True, "message": message})
                return RunResult(True, message, str(self.logger.run_dir))

            if not decision.actions:
                self.memory.add_note("Planner returned no actions; waiting before retry.")
                decision.actions.append(
                    self._wait_action("planner returned no actions; observe again")
                )

            guard_message = self._wechat_send_guard_message(
                task, decision.actions, decision.thought
            )
            if guard_message:
                self.memory.add_note(guard_message)
                self.logger.log(
                    "guardrail_blocked",
                    {"reason": guard_message, "decision": decision.to_dict()},
                )
                decision.actions = [
                    self._wait_action(
                        "wechat send blocked until target result selection and strict target confirmation are present"
                    )
                ]

            for action in decision.actions:
                if self.config.require_confirmation:
                    assessment = self.policy.assess(task, action)
                    self.logger.log(
                        "risk_assessment",
                        {
                            "action": action.to_dict(),
                            "level": assessment.level,
                            "reason": assessment.reason,
                            "requires_confirmation": assessment.requires_confirmation,
                        },
                    )

                    if assessment.requires_confirmation:
                        approved = self.confirmation.approve(action, assessment.reason)
                        if not approved:
                            message = "用户取消了高风险动作，任务停止。"
                            self.logger.log(
                                "run_finished", {"success": False, "message": message}
                            )
                            return RunResult(False, message, str(self.logger.run_dir))
                else:
                    self.logger.log(
                        "risk_control_disabled",
                        {"action": action.to_dict()},
                    )

                print(f"act: {action.type} {action.params}")
                act_started = time.perf_counter()
                result = self.executor.execute(action, observation.screen)
                act_seconds = time.perf_counter() - act_started
                self.memory.add_result(result)
                self.logger.log("action_result", result.to_dict())
                self.logger.log(
                    "action_timing",
                    {
                        "action": action.to_dict(),
                        "seconds": round(act_seconds, 3),
                    },
                )

                if not result.success:
                    print(f"action failed: {result.message}")
                    self.memory.add_note(
                        f"Action {action.type} failed: {result.message}"
                    )
                    break

                if action.type == "finish":
                    message = str(action.params.get("message", "任务已完成。"))
                    self.logger.log("run_finished", {"success": True, "message": message})
                    return RunResult(True, message, str(self.logger.run_dir))

            self.logger.log(
                "step_timing",
                {
                    "step": step,
                    "observe_seconds": round(observe_seconds, 3),
                    "think_seconds": round(think_seconds, 3),
                    "total_seconds": round(time.perf_counter() - step_started, 3),
                    "screen": observation.screen.to_public_dict(),
                },
            )

        message = f"达到最大步骤数 {self.config.max_steps}，任务未确认完成。"
        self.logger.log("run_finished", {"success": False, "message": message})
        return RunResult(False, message, str(self.logger.run_dir))

    def _wait_action(self, reason: str):
        return Action(type="wait", params={"seconds": 1}, reason=reason)

    def _wechat_send_guard_message(
        self, task: str, actions: list[Action], thought: str = ""
    ) -> str | None:
        if not self._is_wechat_message_task(task):
            return None
        if not self._contains_enter_send(actions):
            return None

        target = self._wechat_target_from_task(task)
        if not target:
            return (
                "已阻止微信发送：无法从任务中可靠识别目标联系人或群聊。"
                "请重新观察或询问用户后再发送。"
            )
        if self._has_selected_wechat_target(target):
            if self._has_strict_wechat_target_confirmation(target, thought, actions):
                return None
            return (
                f"已阻止微信发送：虽然本轮任务已经点击过“{target}”的搜索结果，"
                "但发送前的判断没有明确写出已严格确认当前会话标题/对象就是该目标。"
                "请重新观察并确认后再发送。"
            )

        return (
            f"已阻止微信发送：按 Enter 发送前，本轮任务必须先搜索并点击"
            f"与“{target}”匹配的搜索结果，然后重新观察并严格确认当前会话目标。"
        )

    def _is_wechat_message_task(self, task: str) -> bool:
        return (
            ("微信" in task or "WeChat" in task or "weixin" in task.lower())
            and any(word in task for word in ["发送", "发消息", "说", "发给"])
        )

    def _contains_enter_send(self, actions: list[Action]) -> bool:
        for action in actions:
            if action.type != "press":
                continue
            key = str(action.params.get("key", "")).strip().lower()
            if key in {"enter", "return"}:
                return True
        return False

    def _wechat_target_from_task(self, task: str) -> str | None:
        patterns = [
            r"(?:微信|WeChat|weixin).*?(?:给|向)\s*(?:联系人|好友|群聊|群)?\s*[“\"']?(.+?)[”\"']?\s*(?:发送|发消息|说|发给|发|[:：，,。]|$)",
            r"(?:微信|WeChat|weixin).*?(?:群聊|群)\s*[“\"']?(.+?)[”\"']?\s*(?:发送|发消息|说|发给|发|[:：，,。]|$)",
            r"(?:微信|WeChat|weixin).*?(?:发送消息|发消息|发送)\s*(?:给|到|至)\s*(?:联系人|好友|群聊|群)?\s*[“\"']?(.+?)[”\"']?\s*(?:发送|发消息|说|发给|发|[:：，,。]|$)",
            r"(?:微信|WeChat|weixin).*?发给\s*(?:联系人|好友|群聊|群)?\s*[“\"']?(.+?)[”\"']?\s*(?:发送|发消息|说|发给|发|[:：，,。]|$)",
            r"(?:给|向)\s*(?:联系人|好友|群聊|群)?\s*[“\"']?(.+?)[”\"']?\s*(?:发送|发消息|说|发给|发|[:：，,。]|$)",
        ]
        for pattern in patterns:
            match = re.search(pattern, task, flags=re.IGNORECASE)
            if match:
                target = match.group(1).strip(" ：:，,。.！!？?“”\"'《》")
                target = re.sub(r"^(?:联系人|好友|群聊|群)\s*", "", target)
                if target:
                    return target
        return None

    def _has_strict_wechat_target_confirmation(
        self, target: str, thought: str, actions: list[Action]
    ) -> bool:
        text = "\n".join([thought, *[action.reason for action in actions]])
        if target not in text:
            return False
        unsafe_terms = [
            "看起来",
            "可能",
            "似乎",
            "像是",
            "不确定",
            "未确认",
            "无法确认",
            "不能确认",
            "不清楚",
        ]
        if any(term in text for term in unsafe_terms):
            return False
        confirmation_terms = [
            "严格确认",
            "确认当前会话",
            "确认当前对话",
            "确认当前对话框",
            "确认目标联系人正确",
            "确认目标群聊正确",
            "会话标题",
            "聊天对象",
            "群聊名称",
            "标题显示",
            "标题可见",
            "当前会话对象",
            "当前对话框就是",
        ]
        return any(term in text for term in confirmation_terms)

    def _has_selected_wechat_target(self, target: str | None) -> bool:
        if not self.memory:
            return False
        target = (target or "").strip()
        for result in self.memory.action_results:
            action = result.get("action", {})
            if not result.get("success"):
                continue
            if action.get("type") not in {"click", "double_click"}:
                continue
            text = (
                f"{action.get('reason', '')}\n"
                f"{action.get('params', {})}\n"
                f"{result.get('message', '')}\n"
                f"{result.get('data', {})}"
            )
            if "搜索结果" not in text and "匹配" not in text:
                continue
            if target and target not in text:
                continue
            return True
        return False
