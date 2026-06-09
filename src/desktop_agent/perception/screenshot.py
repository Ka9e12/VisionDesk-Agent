from __future__ import annotations

import base64
import subprocess
from pathlib import Path

from desktop_agent.schema import ScreenImage


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

    def capture(self, path: Path) -> ScreenImage:
        path.parent.mkdir(parents=True, exist_ok=True)
        if not self._capture_with_mss(path):
            if not self._capture_with_pyautogui(path):
                self._capture_with_macos_screencapture(path)

        if not path.exists():
            raise RuntimeError(
                "Screenshot command completed but did not create an image. Check screen recording permission or run in a graphical desktop session."
            )

        final_path, width, height, mime_type = _normalize_image(
            path,
            max_width=self.max_width,
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
        )

    def _capture_with_mss(self, path: Path) -> bool:
        try:
            import mss
            import mss.tools
        except Exception:
            return False

        try:
            with mss.mss() as sct:
                monitor = sct.monitors[0]
                shot = sct.grab(monitor)
                mss.tools.to_png(shot.rgb, shot.size, output=str(path))
            return True
        except Exception:
            return False

    def _capture_with_pyautogui(self, path: Path) -> bool:
        try:
            import pyautogui
        except Exception:
            return False

        try:
            image = pyautogui.screenshot()
            image.save(path)
            return True
        except Exception:
            return False

    def _capture_with_macos_screencapture(self, path: Path) -> None:
        try:
            subprocess.run(
                ["screencapture", "-x", str(path)],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception as exc:
            raise RuntimeError(
                "Unable to capture screenshot. Install mss/pyautogui or grant screen recording permission."
            ) from exc
