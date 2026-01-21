from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from PIL import Image, UnidentifiedImageError


@dataclass(frozen=True)
class ImageInfo:
    width: int
    height: int
    mode: str          # e.g. "RGB", "RGBA", "L"
    format: str        # e.g. "PNG", "TIFF", "JPEG"
    has_alpha: bool
    channels: int


def read_image_info(path: Path) -> tuple[Optional[ImageInfo], Optional[str]]:
    """
    Reads lightweight metadata with Pillow.
    Returns (ImageInfo|None, error_message|None).
    """
    try:
        with Image.open(path) as img:
            w, h = img.size
            mode = img.mode or ""
            fmt = (img.format or "").upper()

            # Determine channels/alpha from mode
            # Common: L(1), RGB(3), RGBA(4)
            ch = 0
            has_alpha = False
            if mode == "L":
                ch = 1
            elif mode == "LA":
                ch = 2
                has_alpha = True
            elif mode == "RGB":
                ch = 3
            elif mode == "RGBA":
                ch = 4
                has_alpha = True
            else:
                # Best-effort: count bands
                try:
                    ch = len(img.getbands())
                    has_alpha = "A" in img.getbands()
                except Exception:
                    ch = 0

            return ImageInfo(
                width=w,
                height=h,
                mode=mode,
                format=fmt,
                has_alpha=has_alpha,
                channels=ch,
            ), None

    except UnidentifiedImageError:
        return None, "Unsupported image format (Pillow could not identify file)."
    except Exception as e:
        return None, f"Failed to read image metadata: {e}"
