import unittest

from desktop_agent.config import AgentConfig


class ConfigTests(unittest.TestCase):
    def test_with_overrides_accepts_screenshot_max_width(self):
        config = AgentConfig(api_key="key", api_base="http://example.test", model="m")

        updated = config.with_overrides(screenshot_max_width=0)

        self.assertEqual(updated.screenshot_max_width, 0)
        self.assertEqual(config.screenshot_max_width, 1100)


if __name__ == "__main__":
    unittest.main()
