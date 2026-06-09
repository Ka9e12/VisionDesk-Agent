import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from desktop_agent.perception.screenshot import CaptureResult, ScreenshotProvider


class FallbackScreenshotProvider(ScreenshotProvider):
    def __init__(self):
        super().__init__()
        self.regions = []

    def _capture_with_mss(self, path, failures, region=None):
        self.regions.append(region)
        if region is not None:
            failures.append("forced region failure")
            return None
        path.write_bytes(b"fallback")
        return CaptureResult(
            path=path,
            width=100,
            height=50,
            desktop_width=100,
            desktop_height=50,
            source="test",
            scope="screen",
        )

    def _capture_with_pyautogui(self, path, failures, region=None):
        failures.append("forced pyautogui failure")
        return None

    def _capture_with_pillow_imagegrab(self, path, failures, region=None):
        failures.append("forced imagegrab failure")
        return None


class ScreenshotProviderTests(unittest.TestCase):
    def test_window_region_capture_falls_back_to_full_screen(self):
        provider = FallbackScreenshotProvider()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "shot.png"
            with patch(
                "desktop_agent.perception.screenshot._normalize_image",
                return_value=(path, 100, 50, "image/png"),
            ):
                screen = provider.capture(
                    path,
                    region={"left": 10, "top": 20, "width": 300, "height": 200},
                )

        self.assertEqual(screen.capture_scope, "screen")
        self.assertEqual(screen.origin_x, 0)
        self.assertIn({"left": 10, "top": 20, "width": 300, "height": 200}, provider.regions)
        self.assertIn(None, provider.regions)


if __name__ == "__main__":
    unittest.main()
