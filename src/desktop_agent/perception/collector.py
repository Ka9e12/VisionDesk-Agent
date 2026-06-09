from __future__ import annotations

from desktop_agent.config import AgentConfig
from desktop_agent.perception.accessibility import AccessibilityProvider
from desktop_agent.perception.browser_dom import BrowserDomProvider
from desktop_agent.perception.ocr import OcrProvider
from desktop_agent.perception.screenshot import ScreenshotProvider
from desktop_agent.perception.window import WindowProvider
from desktop_agent.runtime.logger import RunLogger
from desktop_agent.schema import Observation


def _usable_window_region(bounds: dict[str, int] | None) -> dict[str, int] | None:
    if not bounds:
        return None
    try:
        region = {
            "left": int(bounds["left"]),
            "top": int(bounds["top"]),
            "width": int(bounds["width"]),
            "height": int(bounds["height"]),
        }
    except Exception:
        return None
    if region["width"] < 160 or region["height"] < 120:
        return None
    return region


def _should_capture_window(window_title: str | None, region: dict[str, int] | None) -> bool:
    if not region:
        return False
    if (window_title or "").strip().lower() == "program manager":
        return False
    return True


class PerceptionCollector:
    def __init__(self, config: AgentConfig, logger: RunLogger) -> None:
        self.config = config
        self.logger = logger
        self.screenshots = ScreenshotProvider(
            max_width=config.screenshot_max_width,
            image_format=config.screenshot_format,
            jpeg_quality=config.jpeg_quality,
        )
        self.window = WindowProvider()
        self.ocr = OcrProvider()
        self.browser = BrowserDomProvider(config.browser_cdp_endpoint)
        self.accessibility = AccessibilityProvider()

    def collect(
        self, *, task: str, step: int, recent_actions: list[dict]
    ) -> Observation:
        window = self.window.snapshot()
        region = (
            _usable_window_region(window.active_window_bounds)
            if self.config.capture_active_window
            else None
        )
        if not _should_capture_window(window.active_window_title, region):
            region = None
        screen = self.screenshots.capture(
            self.logger.screenshot_path(step),
            region=region,
            max_width=self.config.window_screenshot_max_width
            if region
            else self.config.screenshot_max_width,
        )
        ocr_text = self.ocr.extract_text(screen.path) if self.config.include_ocr else None
        browser_dom = (
            self.browser.snapshot() if self.config.include_browser_dom else None
        )
        accessibility_tree = (
            self.accessibility.snapshot()
            if self.config.include_accessibility
            else None
        )
        return Observation(
            task=task,
            step=step,
            screen=screen,
            window=window,
            ocr_text=ocr_text,
            browser_dom=browser_dom,
            accessibility_tree=accessibility_tree,
            recent_actions=recent_actions,
        )
