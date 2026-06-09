from __future__ import annotations

from pathlib import Path


class OcrProvider:
    def extract_text(self, image_path: Path) -> str | None:
        try:
            import pytesseract
            from PIL import Image
        except Exception:
            return None

        try:
            with Image.open(image_path) as image:
                return pytesseract.image_to_string(image).strip() or None
        except Exception:
            return None
