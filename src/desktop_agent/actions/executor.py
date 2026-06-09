from __future__ import annotations

import platform
import subprocess
import time
from typing import Any

from desktop_agent.schema import Action, ActionResult, ScreenImage


WINDOWS_APP_ALIASES = {
    "edge": "msedge",
    "microsoft edge": "msedge",
    "chrome": "chrome",
    "google chrome": "chrome",
    "notepad": "notepad",
    "记事本": "notepad",
    "explorer": "explorer",
    "file explorer": "explorer",
    "文件资源管理器": "explorer",
    "cmd": "cmd",
    "command prompt": "cmd",
    "powershell": "powershell",
}


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
        if screen and screen.width and screen.height:
            x = max(0, min(x, screen.width - 1))
            y = max(0, min(y, screen.height - 1))
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

    def _do_open_app(
        self, params: dict[str, Any], screen: ScreenImage | None
    ) -> dict[str, Any]:
        app = str(params["name"])
        system = platform.system().lower()
        if system == "darwin":
            subprocess.run(["open", "-a", app], check=True)
        elif system == "windows":
            command = WINDOWS_APP_ALIASES.get(app.strip().lower(), app)
            subprocess.run(["cmd", "/c", "start", "", command], check=True)
        else:
            subprocess.Popen([app])
        return {"name": app}

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
