import unittest

from desktop_agent.schema import Action, PlanDecision


class SchemaTests(unittest.TestCase):
    def test_action_accepts_flat_params(self):
        action = Action.from_dict(
            {"type": "click", "x": 10, "y": 20, "reason": "test"}
        )
        self.assertEqual(action.type, "click")
        self.assertEqual(action.params, {"x": 10, "y": 20})
        self.assertEqual(action.reason, "test")

    def test_plan_decision_parses_actions(self):
        decision = PlanDecision.from_dict(
            {
                "thought": "go",
                "actions": [{"type": "wait", "params": {"seconds": 1}}],
            }
        )
        self.assertFalse(decision.done)
        self.assertEqual(decision.actions[0].type, "wait")


if __name__ == "__main__":
    unittest.main()
