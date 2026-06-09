from __future__ import annotations

import subprocess

from desktop_agent.schema import WindowState


def _run_osascript(script: str) -> str | None:
    try:
        return subprocess.check_output(
            ["osascript", "-e", script],
            text=True,
            stderr=subprocess.DEVNULL,
            timeout=5,
        ).strip()
    except Exception:
        return None


def _mouse_position() -> tuple[int, int] | None:
    try:
        import pyautogui
    except Exception:
        return None

    try:
        pos = pyautogui.position()
        return int(pos.x), int(pos.y)
    except Exception:
        return None


class WindowProvider:
    def snapshot(self) -> WindowState:
        app = _run_osascript(
            'tell application "System Events" to get name of first application process whose frontmost is true'
        )
        title = None
        if app:
            title = _run_osascript(
                f'''
                tell application "System Events"
                  tell application process "{app}"
                    if exists window 1 then
                      return name of window 1
                    else
                      return ""
                    end if
                  end tell
                end tell
                '''
            )
        return WindowState(
            active_app=app or None,
            active_window_title=title or None,
            mouse_position=_mouse_position(),
        )
