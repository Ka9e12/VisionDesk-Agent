from __future__ import annotations

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
        from desktop_agent.schema import Action

        return Action(type="wait", params={"seconds": 1}, reason=reason)
