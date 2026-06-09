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
        import pyautogui

        size = pyautogui.size()
        checks.append(("display_size", True, f"{int(size.width)}x{int(size.height)}"))
    except Exception as exc:
        checks.append(("display_size", False, str(exc)))

    path = Path.cwd() / ".doctor-screenshot.png"
    screen = None
    try:
        screen = ScreenshotProvider(max_width=800).capture(path)
        detail = screen.to_diagnostic_dict()
        checks.append(
            (
                "screenshot",
                True,
                (
                    f"{detail['width']}x{detail['height']} from "
                    f"{detail['original_width']}x{detail['original_height']}; "
                    f"desktop={detail['desktop_width']}x{detail['desktop_height']}; "
                    f"origin=({detail['origin_x']},{detail['origin_y']}); "
                    f"scale=({detail['scale_x']:.3f},{detail['scale_y']:.3f}); "
                    f"source={detail['capture_source'] or 'unknown'}"
                ),
            )
        )
    except Exception as exc:
        checks.append(("screenshot", False, str(exc)))
    finally:
        path.unlink(missing_ok=True)
        if screen is not None:
            screen.path.unlink(missing_ok=True)
    return checks
