from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from desktop_agent.config import AgentConfig
from desktop_agent.memory.task_memory import TaskMemory
from desktop_agent.planner.prompts import SYSTEM_PROMPT, build_user_text
from desktop_agent.schema import Observation, PlanDecision


class PlannerError(RuntimeError):
    pass


class OpenAICompatiblePlanner:
    def __init__(self, config: AgentConfig) -> None:
        self.config = config

    def decide(self, task: str, observation: Observation, memory: TaskMemory) -> PlanDecision:
        if not self.config.model:
            raise PlannerError("AGENT_MODEL is not set")
        if not self.config.api_key:
            raise PlannerError("AGENT_API_KEY is not set")

        payload = self._build_payload(task, observation, memory)
        response = self._post_json(self._chat_completions_url(), payload)
        content = self._extract_content(response)
        parsed = self._parse_json_object(content)
        return PlanDecision.from_dict(parsed)

    def _build_payload(
        self, task: str, observation: Observation, memory: TaskMemory
    ) -> dict[str, Any]:
        user_text = build_user_text(
            task,
            observation.to_prompt_dict(),
            memory.to_prompt_dict(),
        )
        payload: dict[str, Any] = {
            "model": self.config.model,
            "temperature": self.config.temperature,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_text},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{observation.screen.mime_type};base64,{observation.screen.base64_png}"
                            },
                        },
                    ],
                },
            ],
        }
        if self.config.use_json_response_format:
            payload["response_format"] = {"type": "json_object"}
        return payload

    def _chat_completions_url(self) -> str:
        base = self.config.api_base.rstrip("/")
        if base.endswith("/chat/completions"):
            return base
        if base.endswith("/v1"):
            return base + "/chat/completions"
        return base + "/v1/chat/completions"

    def _post_json(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=data,
            headers={
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(
                request, timeout=self.config.request_timeout
            ) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise PlannerError(f"Model request failed: HTTP {exc.code}: {body}") from exc
        except Exception as exc:
            raise PlannerError(f"Model request failed: {exc}") from exc

    def _extract_content(self, response: dict[str, Any]) -> str:
        try:
            content = response["choices"][0]["message"]["content"]
        except Exception as exc:
            raise PlannerError(f"Unexpected model response shape: {response}") from exc

        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    parts.append(str(item.get("text", "")))
            return "\n".join(parts)
        raise PlannerError(f"Unsupported message content: {content!r}")

    def _parse_json_object(self, text: str) -> dict[str, Any]:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            lines = cleaned.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            cleaned = "\n".join(lines).strip()

        try:
            value = json.loads(cleaned)
        except json.JSONDecodeError:
            start = cleaned.find("{")
            end = cleaned.rfind("}")
            if start == -1 or end == -1 or end <= start:
                raise PlannerError(f"Planner did not return JSON: {text}")
            value = json.loads(cleaned[start : end + 1])

        if not isinstance(value, dict):
            raise PlannerError("Planner JSON root must be an object")
        return value
