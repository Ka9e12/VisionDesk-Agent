from __future__ import annotations

import ctypes
import os
import platform
import shutil
import subprocess
import time
from pathlib import Path
from ctypes import wintypes
from typing import Any

from desktop_agent.schema import Action, ActionResult, ScreenImage


WINDOWS_APP_ALIASES = {
    "edge": "msedge",
    "microsoft edge": "msedge",
    "chrome": "chrome",
    "google chrome": "chrome",
    "wechat": "Weixin.exe",
    "weixin": "Weixin.exe",
    "微信": "Weixin.exe",
    "企业微信": "WXWork.exe",
    "wecom": "WXWork.exe",
    "wxwork": "WXWork.exe",
    "notepad": "notepad",
    "记事本": "notepad",
    "explorer": "explorer",
    "file explorer": "explorer",
    "文件资源管理器": "explorer",
    "cmd": "cmd",
    "command prompt": "cmd",
    "powershell": "powershell",
}

WINDOWS_APP_SEARCH_TERMS = {
    "wechat": {"wechat", "weixin", "微信"},
    "weixin": {"wechat", "weixin", "微信"},
    "微信": {"wechat", "weixin", "微信"},
    "企业微信": {"企业微信", "wxwork", "wecom"},
    "wecom": {"企业微信", "wxwork", "wecom"},
    "wxwork": {"企业微信", "wxwork", "wecom"},
    "edge": {"edge", "microsoft edge", "msedge"},
    "microsoft edge": {"edge", "microsoft edge", "msedge"},
    "chrome": {"chrome", "google chrome"},
    "google chrome": {"chrome", "google chrome"},
}

WINDOWS_KNOWN_APP_PATHS = {
    "wechat": [
        ("ProgramFiles", "Tencent", "Weixin", "Weixin.exe"),
        ("ProgramFiles(x86)", "Tencent", "Weixin", "Weixin.exe"),
    ],
    "weixin": [
        ("ProgramFiles", "Tencent", "Weixin", "Weixin.exe"),
        ("ProgramFiles(x86)", "Tencent", "Weixin", "Weixin.exe"),
    ],
    "微信": [
        ("ProgramFiles", "Tencent", "Weixin", "Weixin.exe"),
        ("ProgramFiles(x86)", "Tencent", "Weixin", "Weixin.exe"),
    ],
    "企业微信": [
        ("ProgramFiles", "WXWork", "WXWork.exe"),
        ("ProgramFiles(x86)", "WXWork", "WXWork.exe"),
        ("ProgramFiles", "Tencent", "WXWork", "WXWork.exe"),
        ("ProgramFiles(x86)", "Tencent", "WXWork", "WXWork.exe"),
    ],
    "wecom": [
        ("ProgramFiles", "WXWork", "WXWork.exe"),
        ("ProgramFiles(x86)", "WXWork", "WXWork.exe"),
    ],
    "wxwork": [
        ("ProgramFiles", "WXWork", "WXWork.exe"),
        ("ProgramFiles(x86)", "WXWork", "WXWork.exe"),
    ],
}


def _enable_windows_dpi_awareness() -> None:
    if platform.system().lower() != "windows":
        return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
        return
    except Exception:
        pass
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


class ActionExecutor:
    def __init__(self, *, dry_run: bool = False) -> None:
        self.dry_run = dry_run
        self._pyautogui = None

    def execute(self, action: Action, screen: ScreenImage | None = None) -> ActionResult:
        method = getattr(self, f"_do_{action.type}", None)
        if method is None:
            return ActionResult(action, False, f"Unknown action type: {action.type}")
        if self.dry_run and action.type not in {"wait", "finish", "ask_user"}:
            return ActionResult(action, True, "dry-run: action skipped")
        try:
            data = method(action.params, screen)
            return ActionResult(action, True, "ok", data or {})
        except Exception as exc:
            return ActionResult(action, False, str(exc))

    def supported_actions(self) -> list[str]:
        return sorted(
            name.removeprefix("_do_")
            for name in dir(self)
            if name.startswith("_do_")
        )

    def _pg(self) -> Any:
        if self._pyautogui is None:
            _enable_windows_dpi_awareness()
            try:
                import pyautogui
            except Exception as exc:
                raise RuntimeError(
                    "pyautogui is required for mouse and keyboard actions. Install with: pip install -e '.[control]'"
                ) from exc
            pyautogui.FAILSAFE = True
            pyautogui.PAUSE = 0.05
            self._pyautogui = pyautogui
        return self._pyautogui

    def _point(self, params: dict[str, Any], screen: ScreenImage | None) -> tuple[int, int]:
        x = int(params["x"])
        y = int(params["y"])
        if screen:
            return screen.to_desktop_point(x, y)
        return x, y

    def _do_move_mouse(
        self, params: dict[str, Any], screen: ScreenImage | None
    ) -> dict[str, Any]:
        x, y = self._point(params, screen)
        duration = float(params.get("duration", 0.2))
        self._pg().moveTo(x, y, duration=duration)
        return {"x": x, "y": y}

    def _do_click(
        self, params: dict[str, Any], screen: ScreenImage | None
    ) -> dict[str, Any]:
        x, y = self._point(params, screen)
        button = str(params.get("button", "left"))
        clicks = int(params.get("clicks", 1))
        interval = float(params.get("interval", 0.05))
        self._pg().click(x=x, y=y, clicks=clicks, interval=interval, button=button)
        return {"x": x, "y": y, "button": button, "clicks": clicks}

    def _do_double_click(
        self, params: dict[str, Any], screen: ScreenImage | None
    ) -> dict[str, Any]:
        params = {**params, "clicks": 2}
        return self._do_click(params, screen)

    def _do_right_click(
        self, params: dict[str, Any], screen: ScreenImage | None
    ) -> dict[str, Any]:
        params = {**params, "button": "right"}
        return self._do_click(params, screen)

    def _do_drag_to(
        self, params: dict[str, Any], screen: ScreenImage | None
    ) -> dict[str, Any]:
        x, y = self._point(params, screen)
        duration = float(params.get("duration", 0.4))
        button = str(params.get("button", "left"))
        self._pg().dragTo(x, y, duration=duration, button=button)
        return {"x": x, "y": y, "button": button}

    def _do_scroll(
        self, params: dict[str, Any], screen: ScreenImage | None
    ) -> dict[str, Any]:
        clicks = int(params.get("clicks", params.get("amount", 0)))
        if clicks == 0:
            direction = str(params.get("direction", "down"))
            clicks = -5 if direction == "down" else 5
        self._pg().scroll(clicks)
        return {"clicks": clicks}

    def _do_type_text(
        self, params: dict[str, Any], screen: ScreenImage | None
    ) -> dict[str, Any]:
        text = str(params.get("text", ""))
        paste = bool(params.get("paste", True))
        if paste:
            self._paste_text(text)
        else:
            interval = float(params.get("interval", 0.01))
            self._pg().write(text, interval=interval)
        return {"chars": len(text), "paste": paste}

    def _paste_text(self, text: str) -> None:
        system = platform.system().lower()
        if system == "darwin":
            subprocess.run(["pbcopy"], input=text, text=True, check=True)
            self._pg().hotkey("command", "v")
            return
        try:
            import pyperclip
        except Exception as exc:
            raise RuntimeError(
                "Non-macOS paste requires pyperclip or paste=false ASCII typing"
            ) from exc
        pyperclip.copy(text)
        self._pg().hotkey("ctrl", "v")

    def _do_press(
        self, params: dict[str, Any], screen: ScreenImage | None
    ) -> dict[str, Any]:
        key = str(params["key"])
        presses = int(params.get("presses", 1))
        interval = float(params.get("interval", 0.05))
        self._pg().press(key, presses=presses, interval=interval)
        return {"key": key, "presses": presses}

    def _do_hotkey(
        self, params: dict[str, Any], screen: ScreenImage | None
    ) -> dict[str, Any]:
        keys = params.get("keys", [])
        if not isinstance(keys, list) or not keys:
            raise ValueError("hotkey action requires non-empty keys list")
        self._pg().hotkey(*[str(key) for key in keys])
        return {"keys": keys}

    def _do_key_down(
        self, params: dict[str, Any], screen: ScreenImage | None
    ) -> dict[str, Any]:
        key = str(params["key"])
        self._pg().keyDown(key)
        return {"key": key}

    def _do_key_up(
        self, params: dict[str, Any], screen: ScreenImage | None
    ) -> dict[str, Any]:
        key = str(params["key"])
        self._pg().keyUp(key)
        return {"key": key}

    def _do_wait(
        self, params: dict[str, Any], screen: ScreenImage | None
    ) -> dict[str, Any]:
        seconds = float(params.get("seconds", 1.0))
        seconds = max(0.0, min(seconds, 60.0))
        time.sleep(seconds)
        return {"seconds": seconds}

    def _focus_snapshot(self):
        from desktop_agent.perception.window import WindowProvider

        return WindowProvider().snapshot()

    def _normalize_app_name(self, value: str) -> str:
        name = str(value).strip().lower().replace("\\", "/").rsplit("/", 1)[-1]
        for suffix in {".exe", ".lnk", ".app"}:
            if name.endswith(suffix):
                name = name[: -len(suffix)]
        return name

    def _expected_app_names(self, app: str, launched: str) -> set[str]:
        candidates = {app, launched}
        normalized_app = self._normalize_app_name(app)
        if normalized_app in WINDOWS_APP_ALIASES:
            candidates.add(WINDOWS_APP_ALIASES[normalized_app])

        normalized = set()
        for candidate in candidates:
            name = self._normalize_app_name(str(candidate))
            if name:
                normalized.add(name)
        return normalized

    def _window_matches_app(self, active_app: str | None, expected: set[str]) -> bool:
        if not active_app:
            return False
        active = self._normalize_app_name(active_app)
        return active in expected

    def _windows_search_terms(self, app: str) -> set[str]:
        normalized = self._normalize_app_name(app)
        terms = {normalized}
        alias = WINDOWS_APP_ALIASES.get(normalized)
        if alias:
            terms.add(self._normalize_app_name(alias))
        terms.update(WINDOWS_APP_SEARCH_TERMS.get(normalized, set()))
        return {term for term in terms if term}

    def _windows_start_menu_roots(self) -> list[Path]:
        roots = []
        for env_name in {"APPDATA", "ProgramData"}:
            root = os.environ.get(env_name)
            if root:
                roots.append(Path(root) / "Microsoft" / "Windows" / "Start Menu" / "Programs")
        return roots

    def _windows_find_start_menu_shortcut(
        self, terms: set[str], roots: list[Path] | None = None
    ) -> Path | None:
        roots = roots or self._windows_start_menu_roots()
        normalized_terms = {self._normalize_app_name(term) for term in terms}
        parent_matches: list[Path] = []
        for root in roots:
            if not root.exists():
                continue
            try:
                shortcuts = root.rglob("*.lnk")
                for shortcut in shortcuts:
                    stem = self._normalize_app_name(shortcut.stem)
                    if "卸载" in stem or "uninstall" in stem:
                        continue
                    if stem in normalized_terms:
                        return shortcut
                    parent = self._normalize_app_name(shortcut.parent.name)
                    if parent in normalized_terms:
                        parent_matches.append(shortcut)
            except Exception:
                continue
        return parent_matches[0] if parent_matches else None

    def _windows_known_paths(self, terms: set[str]) -> list[Path]:
        paths: list[Path] = []
        for term in terms:
            for parts in WINDOWS_KNOWN_APP_PATHS.get(term, []):
                root = os.environ.get(parts[0])
                if not root:
                    continue
                paths.append(Path(root).joinpath(*parts[1:]))
        return paths

    def _windows_resolve_app(self, app: str) -> dict[str, str]:
        terms = self._windows_search_terms(app)

        shortcut = self._windows_find_start_menu_shortcut(terms)
        if shortcut:
            return {
                "method": "start_menu_shortcut",
                "target": str(shortcut),
                "launched": WINDOWS_APP_ALIASES.get(
                    self._normalize_app_name(app), shortcut.stem
                ),
            }

        for path in self._windows_known_paths(terms):
            if path.exists():
                return {
                    "method": "known_path",
                    "target": str(path),
                    "launched": path.name,
                }

        commands = []
        normalized = self._normalize_app_name(app)
        alias = WINDOWS_APP_ALIASES.get(normalized)
        if alias:
            commands.append(alias)
        commands.append(app)

        for command in commands:
            found = shutil.which(command)
            if found:
                return {
                    "method": "path_lookup",
                    "target": found,
                    "launched": Path(found).name,
                }

        command = commands[0]
        return {"method": "shell_start", "target": command, "launched": command}

    def _windows_window_process_name(self, hwnd: int) -> str | None:
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
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
                return None
            return buffer.value
        finally:
            kernel32.CloseHandle(handle)

    def _windows_focus_existing_app(self, expected: set[str]) -> dict[str, Any] | None:
        if platform.system().lower() != "windows":
            return None

        user32 = ctypes.windll.user32
        hwnd_match: list[int] = []

        def visit(hwnd: int, _lparam: int) -> bool:
            if not user32.IsWindowVisible(hwnd):
                return True
            process_name = self._windows_window_process_name(hwnd)
            if self._window_matches_app(process_name, expected):
                hwnd_match.append(hwnd)
                return False
            return True

        enum_proc = ctypes.WINFUNCTYPE(
            ctypes.c_bool, wintypes.HWND, wintypes.LPARAM
        )(visit)
        user32.EnumWindows(enum_proc, 0)
        if not hwnd_match:
            return None

        hwnd = hwnd_match[0]
        sw_restore = 9
        user32.ShowWindow(hwnd, sw_restore)
        user32.SetForegroundWindow(hwnd)
        time.sleep(0.25)
        snapshot = self._focus_snapshot()
        return {
            "focused": self._window_matches_app(snapshot.active_app, expected),
            "active_app": snapshot.active_app,
            "active_window_title": snapshot.active_window_title,
        }

    def _wait_for_app_focus(
        self, app: str, launched: str, timeout: float
    ) -> dict[str, Any]:
        expected = self._expected_app_names(app, launched)
        deadline = time.perf_counter() + max(0.0, timeout)
        snapshot = None

        while True:
            snapshot = self._focus_snapshot()
            if self._window_matches_app(snapshot.active_app, expected):
                return {
                    "focused": True,
                    "active_app": snapshot.active_app,
                    "active_window_title": snapshot.active_window_title,
                }
            if time.perf_counter() >= deadline:
                return {
                    "focused": False,
                    "active_app": snapshot.active_app if snapshot else None,
                    "active_window_title": snapshot.active_window_title
                    if snapshot
                    else None,
                }
            time.sleep(0.25)

    def _do_open_app(
        self, params: dict[str, Any], screen: ScreenImage | None
    ) -> dict[str, Any]:
        app = str(params["name"])
        system = platform.system().lower()
        launched = app
        if system == "darwin":
            subprocess.run(["open", "-a", app], check=True)
        elif system == "windows":
            resolved = self._windows_resolve_app(app)
            launched = resolved["launched"]
            expected = self._expected_app_names(app, launched)
            focus_result = self._windows_focus_existing_app(expected)
            if focus_result and focus_result.get("focused"):
                return {
                    "name": app,
                    "platform": system,
                    "launched": launched,
                    "method": "focus_existing",
                    "target": resolved["target"],
                    **focus_result,
                }

            target = resolved["target"]
            suffix = Path(target).suffix.lower()
            if resolved["method"] == "start_menu_shortcut":
                os.startfile(target)  # type: ignore[attr-defined]
            elif resolved["method"] == "shell_start":
                subprocess.run(["cmd", "/c", "start", "", target], check=True)
            elif suffix == ".exe":
                subprocess.Popen([target])
            else:
                subprocess.run(["cmd", "/c", "start", "", target], check=True)
        else:
            subprocess.Popen([app])
        data = {"name": app, "platform": system, "launched": launched}
        if system == "windows":
            data.update({"method": resolved["method"], "target": resolved["target"]})
        if system in {"darwin", "windows"}:
            timeout = float(params.get("focus_timeout", 5.0))
            data.update(self._wait_for_app_focus(app, launched, timeout))
        return data

    def _do_open_url(
        self, params: dict[str, Any], screen: ScreenImage | None
    ) -> dict[str, Any]:
        url = str(params["url"])
        system = platform.system().lower()
        if system == "darwin":
            subprocess.run(["open", url], check=True)
        elif system == "windows":
            subprocess.run(["cmd", "/c", "start", "", url], check=True)
        else:
            subprocess.run(["xdg-open", url], check=True)
        return {"url": url}

    def _do_finish(
        self, params: dict[str, Any], screen: ScreenImage | None
    ) -> dict[str, Any]:
        return {"message": str(params.get("message", ""))}

    def _do_ask_user(
        self, params: dict[str, Any], screen: ScreenImage | None
    ) -> dict[str, Any]:
        question = str(params.get("question", "需要你确认下一步。"))
        answer = input(f"{question}\n> ")
        return {"question": question, "answer": answer}
