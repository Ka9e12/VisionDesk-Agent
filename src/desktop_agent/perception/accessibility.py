from __future__ import annotations

from typing import Any


class AccessibilityProvider:
    """Small, safe macOS Accessibility probe.

    Full AX tree traversal is intentionally optional because it requires system
    permissions and pyobjc. The multimodal screenshot remains the primary signal.
    """

    def snapshot(self) -> dict[str, Any] | None:
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
