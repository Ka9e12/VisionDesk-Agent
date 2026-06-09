from __future__ import annotations

from typing import Any


class BrowserDomProvider:
    def __init__(self, cdp_endpoint: str | None = None) -> None:
        self.cdp_endpoint = cdp_endpoint

    def snapshot(self) -> dict[str, Any] | None:
        if not self.cdp_endpoint:
            return {
                "available": False,
                "reason": "AGENT_BROWSER_CDP_ENDPOINT is not set",
            }

        try:
            from playwright.sync_api import sync_playwright
        except Exception:
            return {"available": False, "reason": "playwright is not installed"}

        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.connect_over_cdp(self.cdp_endpoint)
                pages = []
                for context in browser.contexts:
                    for page in context.pages:
                        if page.is_closed():
                            continue
                        pages.append(self._page_snapshot(page))
                browser.close()
                return {"available": True, "pages": pages[:5]}
        except Exception as exc:
            return {"available": False, "reason": str(exc)}

    def _page_snapshot(self, page: Any) -> dict[str, Any]:
        elements = page.evaluate(
            """
            () => Array.from(document.querySelectorAll(
              'a,button,input,textarea,select,[role="button"],[contenteditable="true"]'
            )).slice(0, 120).map((el, index) => {
              const rect = el.getBoundingClientRect();
              const style = window.getComputedStyle(el);
              return {
                index,
                tag: el.tagName.toLowerCase(),
                role: el.getAttribute('role'),
                type: el.getAttribute('type'),
                text: (el.innerText || el.value || el.getAttribute('aria-label') || el.placeholder || '').slice(0, 120),
                href: el.href || null,
                visible: rect.width > 0 && rect.height > 0 && style.visibility !== 'hidden' && style.display !== 'none',
                rect: { x: rect.x, y: rect.y, width: rect.width, height: rect.height }
              }
            })
            """
        )
        return {
            "title": page.title(),
            "url": page.url,
            "elements": elements,
        }
