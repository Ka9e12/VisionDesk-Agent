from __future__ import annotations

import base64
import ctypes
import platform
import subprocess
from dataclasses import dataclass
from pathlib import Path

from desktop_agent.schema import ScreenImage


@dataclass(frozen=True)
class CaptureResult:
    path: Path
    width: int
    height: int
    desktop_width: int | None = None
    desktop_height: int | None = None
    origin_x: int = 0
    origin_y: int = 0
    source: str = ""
    scope: str = "screen"


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


def _image_size_with_pillow(path: Path) -> tuple[int, int] | None:
    try:
        from PIL import Image
    except Exception:
        return None

    with Image.open(path) as image:
        return image.size


def _image_size_with_sips(path: Path) -> tuple[int, int] | None:
    try:
        output = subprocess.check_output(
            ["sips", "-g", "pixelWidth", "-g", "pixelHeight", str(path)],
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        return None

    width = 0
    height = 0
    for line in output.splitlines():
        if "pixelWidth:" in line:
            width = int(line.rsplit(":", 1)[1].strip())
        if "pixelHeight:" in line:
            height = int(line.rsplit(":", 1)[1].strip())
    return (width, height) if width and height else None


def _desktop_size_for_capture(
    width: int, height: int, origin_x: int = 0, origin_y: int = 0
) -> tuple[int, int] | None:
    if origin_x != 0 or origin_y != 0 or width <= 0 or height <= 0:
        return None
    try:
        import pyautogui
    except Exception:
        return None

    try:
        size = pyautogui.size()
        desktop_width = int(size.width)
        desktop_height = int(size.height)
    except Exception:
        return None

    if desktop_width <= 0 or desktop_height <= 0:
        return None

    capture_ratio = width / height
    desktop_ratio = desktop_width / desktop_height
    if abs(capture_ratio - desktop_ratio) / capture_ratio > 0.02:
        return None
    return desktop_width, desktop_height


def _valid_region(region: dict[str, int] | None) -> dict[str, int] | None:
    if not region:
        return None
    try:
        left = int(region["left"])
        top = int(region["top"])
        width = int(region["width"])
        height = int(region["height"])
    except Exception:
        return None
    if width < 80 or height < 80:
        return None
    return {"left": left, "top": top, "width": width, "height": height}


def _normalize_image(
    path: Path, *, max_width: int, image_format: str, jpeg_quality: int
) -> tuple[Path, int, int, str]:
    try:
        from PIL import Image
    except Exception:
        size = _image_size_with_sips(path) or (0, 0)
        return path, size[0], size[1], "image/png"

    with Image.open(path) as image:
        output = image
        width, height = output.size
        if max_width > 0 and width > max_width:
            ratio = max_width / width
            output = output.resize((max_width, int(height * ratio)))

        normalized_format = image_format.strip().lower()
        if normalized_format in {"jpg", "jpeg"}:
            output_path = path.with_suffix(".jpg")
            output.convert("RGB").save(
                output_path,
                format="JPEG",
                quality=max(25, min(jpeg_quality, 95)),
                optimize=True,
            )
            if output_path != path:
                path.unlink(missing_ok=True)
            width, height = output.size
            return output_path, width, height, "image/jpeg"

        output.save(path, format="PNG", optimize=True)
        width, height = output.size
        return path, width, height, "image/png"


class ScreenshotProvider:
    def __init__(
        self,
        max_width: int = 1100,
        image_format: str = "jpeg",
        jpeg_quality: int = 70,
    ) -> None:
        self.max_width = max_width
        self.image_format = image_format
        self.jpeg_quality = jpeg_quality

    def capture(
        self,
        path: Path,
        region: dict[str, int] | None = None,
        max_width: int | None = None,
    ) -> ScreenImage:
        _enable_windows_dpi_awareness()
        path.parent.mkdir(parents=True, exist_ok=True)
        failures: list[str] = []
        capture_region = _valid_region(region)
        capture = (
            self._capture_with_mss(path, failures, capture_region)
            or self._capture_with_pyautogui(path, failures, capture_region)
            or self._capture_with_pillow_imagegrab(path, failures, capture_region)
        )
        if capture is None and platform.system().lower() == "darwin":
            capture = self._capture_with_macos_screencapture(
                path, failures, capture_region
            )
        if capture is None and capture_region is not None:
            failures.append("window-region capture failed; retrying full-screen capture")
            capture = (
                self._capture_with_mss(path, failures, None)
                or self._capture_with_pyautogui(path, failures, None)
                or self._capture_with_pillow_imagegrab(path, failures, None)
            )
            if capture is None and platform.system().lower() == "darwin":
                capture = self._capture_with_macos_screencapture(path, failures, None)
        if capture is None:
            details = "; ".join(failures) if failures else "no capture backend available"
            raise RuntimeError(f"Unable to capture screenshot. Attempts: {details}")

        if not path.exists():
            raise RuntimeError(
                "Screenshot command completed but did not create an image. Check screen recording permission or run in a graphical desktop session."
            )

        final_path, width, height, mime_type = _normalize_image(
            path,
            max_width=self.max_width if max_width is None else max_width,
            image_format=self.image_format,
            jpeg_quality=self.jpeg_quality,
        )
        encoded = base64.b64encode(final_path.read_bytes()).decode("ascii")
        return ScreenImage(
            path=final_path,
            width=width,
            height=height,
            base64_png=encoded,
            mime_type=mime_type,
            original_width=capture.width,
            original_height=capture.height,
            desktop_width=capture.desktop_width,
            desktop_height=capture.desktop_height,
            origin_x=capture.origin_x,
            origin_y=capture.origin_y,
            capture_source=capture.source,
            capture_scope=capture.scope,
        )

    def _capture_with_mss(
        self,
        path: Path,
        failures: list[str],
        region: dict[str, int] | None = None,
    ) -> CaptureResult | None:
        try:
            import mss
            import mss.tools
        except Exception as exc:
            failures.append(f"mss import failed: {exc}")
            return None

        try:
            mss_factory = getattr(mss, "MSS", None) or getattr(mss, "mss")
            with mss_factory() as sct:
                monitor = region or sct.monitors[0]
                shot = sct.grab(monitor)
                mss.tools.to_png(shot.rgb, shot.size, output=str(path))
            width = int(monitor.get("width", shot.size.width))
            height = int(monitor.get("height", shot.size.height))
            origin_x = int(monitor.get("left", 0))
            origin_y = int(monitor.get("top", 0))
            if region:
                desktop_size = (region["width"], region["height"])
            else:
                desktop_size = _desktop_size_for_capture(
                    width, height, origin_x, origin_y
                )
            return CaptureResult(
                path=path,
                width=width,
                height=height,
                desktop_width=desktop_size[0] if desktop_size else None,
                desktop_height=desktop_size[1] if desktop_size else None,
                origin_x=origin_x,
                origin_y=origin_y,
                source="mss",
                scope="window" if region else "screen",
            )
        except Exception as exc:
            failures.append(f"mss failed: {exc}")
            return None

    def _capture_with_pyautogui(
        self,
        path: Path,
        failures: list[str],
        region: dict[str, int] | None = None,
    ) -> CaptureResult | None:
        try:
            import pyautogui
        except Exception as exc:
            failures.append(f"pyautogui import failed: {exc}")
            return None

        try:
            if region:
                image = pyautogui.screenshot(
                    region=(
                        region["left"],
                        region["top"],
                        region["width"],
                        region["height"],
                    )
                )
            else:
                image = pyautogui.screenshot()
            image.save(path)
            width = int(image.size[0])
            height = int(image.size[1])
            desktop_size = (
                (region["width"], region["height"])
                if region
                else _desktop_size_for_capture(width, height)
            )
            return CaptureResult(
                path=path,
                width=width,
                height=height,
                desktop_width=desktop_size[0] if desktop_size else None,
                desktop_height=desktop_size[1] if desktop_size else None,
                origin_x=region["left"] if region else 0,
                origin_y=region["top"] if region else 0,
                source="pyautogui",
                scope="window" if region else "screen",
            )
        except Exception as exc:
            failures.append(f"pyautogui failed: {exc}")
            return None

    def _capture_with_pillow_imagegrab(
        self,
        path: Path,
        failures: list[str],
        region: dict[str, int] | None = None,
    ) -> CaptureResult | None:
        try:
            from PIL import ImageGrab
        except Exception as exc:
            failures.append(f"PIL.ImageGrab import failed: {exc}")
            return None

        try:
            if region:
                image = ImageGrab.grab(
                    bbox=(
                        region["left"],
                        region["top"],
                        region["left"] + region["width"],
                        region["top"] + region["height"],
                    )
                )
            else:
                image = ImageGrab.grab(all_screens=True)
            image.save(path)
            width = int(image.size[0])
            height = int(image.size[1])
            desktop_size = (
                (region["width"], region["height"])
                if region
                else _desktop_size_for_capture(width, height)
            )
            return CaptureResult(
                path=path,
                width=width,
                height=height,
                desktop_width=desktop_size[0] if desktop_size else None,
                desktop_height=desktop_size[1] if desktop_size else None,
                origin_x=region["left"] if region else 0,
                origin_y=region["top"] if region else 0,
                source="PIL.ImageGrab",
                scope="window" if region else "screen",
            )
        except Exception as exc:
            failures.append(f"PIL.ImageGrab failed: {exc}")
            return None

    def _capture_with_macos_screencapture(
        self,
        path: Path,
        failures: list[str],
        region: dict[str, int] | None = None,
    ) -> CaptureResult | None:
        try:
            command = ["screencapture", "-x"]
            if region:
                command.extend(
                    [
                        "-R",
                        f"{region['left']},{region['top']},{region['width']},{region['height']}",
                    ]
                )
            command.append(str(path))
            subprocess.run(
                command,
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            size = _image_size_with_pillow(path) or _image_size_with_sips(path) or (0, 0)
            desktop_size = (
                (region["width"], region["height"])
                if region
                else _desktop_size_for_capture(size[0], size[1])
            )
            return CaptureResult(
                path=path,
                width=size[0],
                height=size[1],
                desktop_width=desktop_size[0] if desktop_size else None,
                desktop_height=desktop_size[1] if desktop_size else None,
                origin_x=region["left"] if region else 0,
                origin_y=region["top"] if region else 0,
                source="screencapture",
                scope="window" if region else "screen",
            )
        except Exception as exc:
            failures.append(f"screencapture failed: {exc}")
            return None
