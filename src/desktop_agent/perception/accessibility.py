from __future__ import annotations

import platform
from typing import Any


class AccessibilityProvider:
    """Small, safe accessibility probe.

    Full tree traversal is intentionally optional because it requires system
    permissions and platform-specific libraries. The multimodal screenshot
    remains the primary signal.
    """

    def snapshot(self) -> dict[str, Any] | None:
        system = platform.system().lower()
        if system == "windows":
            return self._windows_snapshot()
        if system != "darwin":
            return {"available": False, "reason": f"unsupported platform: {system}"}

        try:
            import ApplicationServices as AS
        except Exception:
            return {
                "available": False,
                "reason": "pyobjc-framework-ApplicationServices is not installed",
            }

        try:
            system = AS.AXUIElementCreateSystemWide()
            err, focused_app = AS.AXUIElementCopyAttributeValue(
                system, "AXFocusedApplication", None
            )
            if err != 0:
                return {"available": False, "reason": f"AX error {err}"}

            result: dict[str, Any] = {"available": True}
            for attr, key in [
                ("AXTitle", "title"),
                ("AXRole", "role"),
                ("AXDescription", "description"),
            ]:
                try:
                    attr_err, value = AS.AXUIElementCopyAttributeValue(
                        focused_app, attr, None
                    )
                    if attr_err == 0 and value:
                        result[key] = str(value)
                except Exception:
                    pass
            return result
        except Exception as exc:
            return {"available": False, "reason": str(exc)}

    def _windows_snapshot(self) -> dict[str, Any] | None:
        try:
            from pywinauto import Desktop
        except Exception:
            return {"available": False, "reason": "pywinauto is not installed"}

        try:
            window = Desktop(backend="uia").active()
            rect = window.rectangle()
            return {
                "available": True,
                "title": window.window_text() or None,
                "role": window.friendly_class_name() or None,
                "rect": {
                    "left": rect.left,
                    "top": rect.top,
                    "right": rect.right,
                    "bottom": rect.bottom,
                },
            }
        except Exception as exc:
            return {"available": False, "reason": str(exc)}
