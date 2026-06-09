import unittest
from pathlib import Path

from desktop_agent.schema import Action, PlanDecision, ScreenImage


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

    def test_plan_decision_parses_string_booleans(self):
        decision = PlanDecision.from_dict(
            {
                "thought": "go",
                "done": "false",
                "needs_user": "true",
                "actions": [],
            }
        )
        self.assertFalse(decision.done)
        self.assertTrue(decision.needs_user)

    def test_plan_decision_rejects_invalid_boolean_string(self):
        with self.assertRaisesRegex(ValueError, "done"):
            PlanDecision.from_dict(
                {
                    "thought": "go",
                    "done": "not really",
                    "actions": [],
                }
            )

    def test_screen_image_maps_scaled_point_to_desktop_point(self):
        screen = ScreenImage(
            path=Path("shot.jpg"),
            width=1100,
            height=618,
            base64_png="",
            original_width=2560,
            original_height=1440,
        )
        self.assertEqual(screen.to_desktop_point(550, 309), (1280, 720))

    def test_screen_image_maps_point_with_origin_offset(self):
        screen = ScreenImage(
            path=Path("shot.jpg"),
            width=100,
            height=50,
            base64_png="",
            original_width=200,
            original_height=100,
            origin_x=-200,
            origin_y=50,
        )
        self.assertEqual(screen.to_desktop_point(50, 25), (-100, 100))

    def test_screen_image_maps_window_capture_point_with_origin(self):
        screen = ScreenImage(
            path=Path("shot.jpg"),
            width=1280,
            height=820,
            base64_png="",
            original_width=1280,
            original_height=820,
            desktop_width=1280,
            desktop_height=820,
            origin_x=305,
            origin_y=348,
            capture_scope="window",
        )
        self.assertEqual(screen.to_desktop_point(100, 200), (405, 548))

    def test_screen_image_maps_downscaled_window_capture_point(self):
        screen = ScreenImage(
            path=Path("shot.jpg"),
            width=1000,
            height=500,
            base64_png="",
            original_width=2000,
            original_height=1000,
            desktop_width=2000,
            desktop_height=1000,
            origin_x=300,
            origin_y=400,
            capture_scope="window",
        )
        self.assertEqual(screen.to_desktop_point(500, 250), (1300, 900))

    def test_screen_image_maps_high_dpi_window_capture_point(self):
        screen = ScreenImage(
            path=Path("shot.jpg"),
            width=2400,
            height=1600,
            base64_png="",
            original_width=2400,
            original_height=1600,
            desktop_width=1200,
            desktop_height=800,
            origin_x=100,
            origin_y=50,
            capture_scope="window",
        )
        self.assertEqual(screen.to_desktop_point(1200, 800), (700, 450))

    def test_screen_image_maps_negative_origin_window_capture_point(self):
        screen = ScreenImage(
            path=Path("shot.jpg"),
            width=800,
            height=600,
            base64_png="",
            original_width=800,
            original_height=600,
            desktop_width=800,
            desktop_height=600,
            origin_x=-900,
            origin_y=100,
            capture_scope="window",
        )
        self.assertEqual(screen.to_desktop_point(400, 300), (-500, 400))

    def test_screen_image_maps_to_desktop_coordinate_space_when_it_differs(self):
        screen = ScreenImage(
            path=Path("shot.jpg"),
            width=1100,
            height=618,
            base64_png="",
            original_width=2200,
            original_height=1236,
            desktop_width=1100,
            desktop_height=618,
        )
        self.assertEqual(screen.to_desktop_point(550, 309), (550, 309))


if __name__ == "__main__":
    unittest.main()
