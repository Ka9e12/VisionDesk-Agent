from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _as_bool(value: str | bool | None, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _as_int(value: str | None, default: int) -> int:
    if value is None or value == "":
        return default
    return int(value)


def _as_float(value: str | None, default: float) -> float:
    if value is None or value == "":
        return default
    return float(value)


def load_env_file(path: str | Path = ".env") -> None:
    env_path = Path(path)
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


@dataclass(frozen=True)
class AgentConfig:
    api_key: str
    api_base: str
    model: str
    max_steps: int = 30
    dry_run: bool = False
    require_confirmation: bool = True
    assume_yes: bool = False
    temperature: float = 0.1
    request_timeout: int = 120
    log_dir: Path = Path("logs")
    screenshot_max_width: int = 1100
    window_screenshot_max_width: int = 1600
    capture_active_window: bool = True
    screenshot_format: str = "jpeg"
    jpeg_quality: int = 70
    include_ocr: bool = False
    include_browser_dom: bool = False
    include_accessibility: bool = False
    browser_cdp_endpoint: str | None = None
    use_json_response_format: bool = False

    @classmethod
    def from_env(cls) -> "AgentConfig":
        return cls(
            api_key=os.getenv("AGENT_API_KEY", ""),
            api_base=os.getenv("AGENT_API_BASE", "https://api.openai.com/v1"),
            model=os.getenv("AGENT_MODEL", ""),
            max_steps=_as_int(os.getenv("AGENT_MAX_STEPS"), 30),
            dry_run=_as_bool(os.getenv("AGENT_DRY_RUN"), False),
            require_confirmation=_as_bool(os.getenv("AGENT_REQUIRE_CONFIRMATION"), True),
            assume_yes=_as_bool(os.getenv("AGENT_ASSUME_YES"), False),
            temperature=_as_float(os.getenv("AGENT_TEMPERATURE"), 0.1),
            request_timeout=_as_int(os.getenv("AGENT_REQUEST_TIMEOUT"), 120),
            log_dir=Path(os.getenv("AGENT_LOG_DIR", "logs")),
            screenshot_max_width=_as_int(os.getenv("AGENT_SCREENSHOT_MAX_WIDTH"), 1100),
            window_screenshot_max_width=_as_int(
                os.getenv("AGENT_WINDOW_SCREENSHOT_MAX_WIDTH"), 1600
            ),
            capture_active_window=_as_bool(
                os.getenv("AGENT_CAPTURE_ACTIVE_WINDOW"), True
            ),
            screenshot_format=os.getenv("AGENT_SCREENSHOT_FORMAT", "jpeg"),
            jpeg_quality=_as_int(os.getenv("AGENT_JPEG_QUALITY"), 70),
            include_ocr=_as_bool(os.getenv("AGENT_INCLUDE_OCR"), False),
            include_browser_dom=_as_bool(os.getenv("AGENT_INCLUDE_BROWSER_DOM"), False),
            include_accessibility=_as_bool(os.getenv("AGENT_INCLUDE_ACCESSIBILITY"), False),
            browser_cdp_endpoint=os.getenv("AGENT_BROWSER_CDP_ENDPOINT") or None,
            use_json_response_format=_as_bool(os.getenv("AGENT_USE_JSON_RESPONSE_FORMAT"), False),
        )

    def with_overrides(
        self,
        *,
        max_steps: int | None = None,
        dry_run: bool | None = None,
        assume_yes: bool | None = None,
        screenshot_max_width: int | None = None,
        include_ocr: bool | None = None,
        include_browser_dom: bool | None = None,
        include_accessibility: bool | None = None,
    ) -> "AgentConfig":
        return AgentConfig(
            api_key=self.api_key,
            api_base=self.api_base,
            model=self.model,
            max_steps=max_steps if max_steps is not None else self.max_steps,
            dry_run=dry_run if dry_run is not None else self.dry_run,
            require_confirmation=self.require_confirmation,
            assume_yes=assume_yes if assume_yes is not None else self.assume_yes,
            temperature=self.temperature,
            request_timeout=self.request_timeout,
            log_dir=self.log_dir,
            screenshot_max_width=screenshot_max_width
            if screenshot_max_width is not None
            else self.screenshot_max_width,
            window_screenshot_max_width=self.window_screenshot_max_width,
            capture_active_window=self.capture_active_window,
            screenshot_format=self.screenshot_format,
            jpeg_quality=self.jpeg_quality,
            include_ocr=include_ocr if include_ocr is not None else self.include_ocr,
            include_browser_dom=include_browser_dom
            if include_browser_dom is not None
            else self.include_browser_dom,
            include_accessibility=include_accessibility
            if include_accessibility is not None
            else self.include_accessibility,
            browser_cdp_endpoint=self.browser_cdp_endpoint,
            use_json_response_format=self.use_json_response_format,
        )
