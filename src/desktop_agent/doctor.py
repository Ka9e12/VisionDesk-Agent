from __future__ import annotations

import importlib.util
import platform
from pathlib import Path

from desktop_agent.config import AgentConfig
from desktop_agent.perception.screenshot import ScreenshotProvider


def _has_module(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def doctor(config: AgentConfig) -> list[tuple[str, bool, str]]:
    checks: list[tuple[str, bool, str]] = []
    system = platform.system().lower()
    checks.append(("python", True, platform.python_version()))
    checks.append(("platform", True, platform.platform()))
    checks.append(("AGENT_MODEL", bool(config.model), config.model or "missing"))
    checks.append(("AGENT_API_KEY", bool(config.api_key), "set" if config.api_key else "missing"))
    checks.append(("pyautogui", _has_module("pyautogui"), "keyboard/mouse control"))
    checks.append(("mss", _has_module("mss"), "fast screenshot"))
    checks.append(("PIL", _has_module("PIL"), "image sizing/resizing"))
    checks.append(("pytesseract", _has_module("pytesseract"), "optional OCR"))
    checks.append(("playwright", _has_module("playwright"), "optional browser DOM"))
    if system == "darwin":
        checks.append(
            (
                "ApplicationServices",
                _has_module("ApplicationServices"),
                "optional macOS accessibility",
            )
        )
    elif system == "windows":
        checks.append(("pywinauto", _has_module("pywinauto"), "optional Windows UI Automation"))

    try:
        path = Path.cwd() / ".doctor-screenshot.png"
        screen = ScreenshotProvider(max_width=800).capture(path)
        path.unlink(missing_ok=True)
        screen.path.unlink(missing_ok=True)
        checks.append(("screenshot", True, "ok"))
    except Exception as exc:
        checks.append(("screenshot", False, str(exc)))
    return checks
