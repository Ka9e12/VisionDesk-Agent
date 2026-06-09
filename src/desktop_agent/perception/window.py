from __future__ import annotations

import ctypes
import platform
import subprocess
from ctypes import wintypes

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


def _parse_osascript_pair(value: str | None) -> tuple[int, int] | None:
    if not value:
        return None
    try:
        parts = [part.strip() for part in value.split(",")]
        if len(parts) < 2:
            return None
        return int(float(parts[0])), int(float(parts[1]))
    except Exception:
        return None


def _macos_window_state() -> WindowState:
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
    bounds = None
    if app:
        position = _parse_osascript_pair(
            _run_osascript(
                f'''
                tell application "System Events"
                  tell application process "{app}"
                    if exists window 1 then
                      return position of window 1
                    else
                      return ""
                    end if
                  end tell
                end tell
                '''
            )
        )
        size = _parse_osascript_pair(
            _run_osascript(
                f'''
                tell application "System Events"
                  tell application process "{app}"
                    if exists window 1 then
                      return size of window 1
                    else
                      return ""
                    end if
                  end tell
                end tell
                '''
            )
        )
        if position and size and size[0] > 0 and size[1] > 0:
            bounds = {
                "left": position[0],
                "top": position[1],
                "width": size[0],
                "height": size[1],
            }
    return WindowState(
        active_app=app or None,
        active_window_title=title or None,
        mouse_position=_mouse_position(),
        active_window_bounds=bounds,
    )


def _windows_window_state() -> WindowState:
    try:
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        hwnd = user32.GetForegroundWindow()
        title = _windows_window_title(user32, hwnd)
        app = _windows_process_name(user32, kernel32, hwnd)
        bounds = _windows_window_bounds(user32, hwnd)
        return WindowState(
            active_app=app,
            active_window_title=title,
            mouse_position=_mouse_position(),
            active_window_bounds=bounds,
        )
    except Exception:
        return WindowState(mouse_position=_mouse_position())


def _windows_window_title(user32, hwnd: int) -> str | None:
    length = user32.GetWindowTextLengthW(hwnd)
    if length <= 0:
        return None
    buffer = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buffer, length + 1)
    return buffer.value or None


def _windows_window_bounds(user32, hwnd: int) -> dict[str, int] | None:
    rect = wintypes.RECT()
    if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        return None
    width = int(rect.right - rect.left)
    height = int(rect.bottom - rect.top)
    if width <= 0 or height <= 0:
        return None
    return {
        "left": int(rect.left),
        "top": int(rect.top),
        "width": width,
        "height": height,
    }


def _windows_process_name(user32, kernel32, hwnd: int) -> str | None:
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    if not pid.value:
        return None

    process_query_limited_information = 0x1000
    handle = kernel32.OpenProcess(
        process_query_limited_information, False, pid.value
    )
    if not handle:
        return None

    try:
        size = wintypes.DWORD(260)
        buffer = ctypes.create_unicode_buffer(size.value)
        ok = kernel32.QueryFullProcessImageNameW(
            handle, 0, buffer, ctypes.byref(size)
        )
        if not ok:
            return f"pid:{pid.value}"
        return buffer.value.rsplit("\\", 1)[-1] or f"pid:{pid.value}"
    finally:
        kernel32.CloseHandle(handle)


class WindowProvider:
    def snapshot(self) -> WindowState:
        system = platform.system().lower()
        if system == "darwin":
            return _macos_window_state()
        if system == "windows":
            return _windows_window_state()
        return WindowState(mouse_position=_mouse_position())
