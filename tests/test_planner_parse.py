import unittest

from desktop_agent.config import AgentConfig
from desktop_agent.planner.openai_compatible import OpenAICompatiblePlanner


class PlannerParseTests(unittest.TestCase):
    def test_parse_json_from_code_fence(self):
        planner = OpenAICompatiblePlanner(
            AgentConfig(api_key="key", api_base="http://example.test/v1", model="model")
        )
        parsed = planner._parse_json_object(
            '```json\n{"thought":"ok","actions":[],"done":true}\n```'
        )
        self.assertTrue(parsed["done"])

    def test_chat_completions_url_accepts_bare_base_url(self):
        planner = OpenAICompatiblePlanner(
            AgentConfig(api_key="key", api_base="http://example.test:9999", model="model")
        )
        self.assertEqual(
            planner._chat_completions_url(),
            "http://example.test:9999/v1/chat/completions",
        )

    def test_chat_completions_url_accepts_v1_base_url(self):
        planner = OpenAICompatiblePlanner(
            AgentConfig(api_key="key", api_base="http://example.test:9999/v1", model="model")
        )
        self.assertEqual(
            planner._chat_completions_url(),
            "http://example.test:9999/v1/chat/completions",
        )

    def test_chat_completions_url_accepts_full_endpoint(self):
        planner = OpenAICompatiblePlanner(
            AgentConfig(
                api_key="key",
                api_base="http://example.test:9999/v1/chat/completions",
                model="model",
            )
        )
        self.assertEqual(
            planner._chat_completions_url(),
            "http://example.test:9999/v1/chat/completions",
        )


if __name__ == "__main__":
    unittest.main()
