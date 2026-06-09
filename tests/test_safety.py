import unittest

from desktop_agent.safety.policy import RiskPolicy
from desktop_agent.schema import Action


class SafetyTests(unittest.TestCase):
    def test_delete_text_is_high_risk(self):
        policy = RiskPolicy(require_confirmation=True)
        assessment = policy.assess(
            "删除桌面文件",
            Action(type="click", params={"x": 1, "y": 1}, reason="确认删除"),
        )
        self.assertEqual(assessment.level, "high")
        self.assertTrue(assessment.requires_confirmation)

    def test_wait_is_low_risk(self):
        policy = RiskPolicy(require_confirmation=True)
        assessment = policy.assess(
            "等待页面加载",
            Action(type="wait", params={"seconds": 1}),
        )
        self.assertEqual(assessment.level, "low")
        self.assertFalse(assessment.requires_confirmation)


if __name__ == "__main__":
    unittest.main()
