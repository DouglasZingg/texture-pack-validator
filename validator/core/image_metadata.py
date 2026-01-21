from __future__ import annotations

from typing import List

from validator.config import ALLOWED_EXT_BY_MAP, MAX_SIZE_ERROR, MAX_SIZE_WARN
from validator.core.grouping import AssetGroup, TextureRecord
from validator.core.required_maps import ValidationResult
from validator.util.image_info import read_image_info
from validator.profiles import Profile

def _is_power_of_two(n: int) -> bool:
    return n > 0 and (n & (n - 1)) == 0


def _severity_for_size(w: int, h: int) -> str | None:
    m = max(w, h)
    if m >= MAX_SIZE_ERROR:
        return "ERROR"
    if m >= MAX_SIZE_WARN:
        return "WARNING"
    return None


def validate_image_metadata(group: AssetGroup, profile: Profile) -> List[ValidationResult]:
    """
    Day 4 checks (Pillow):
      - readable image
      - resolution power-of-two (warning)
      - max size thresholds (warning/error)
      - channel sanity (basic)
      - extension expectation by map type (warning)
    """
    results: List[ValidationResult] = []

    for rec in group.textures:
        if not rec.parsed:
            continue

        map_type = rec.parsed.map_type
        ext = rec.ext.lower()

        # File extension expectations (studio-dependent => warning)
        allowed = set(ALLOWED_EXT_BY_MAP.get(map_type, set()))
        if profile.allow_exr:
            allowed.add(".exr")

        if allowed and ext not in allowed:
            results.append(
                ValidationResult(
                    "WARNING",
                    f"{map_type}: unexpected file extension '{ext}' (expected one of {sorted(allowed)})",
                )
            )


        info, err = read_image_info(rec.path)
        if err:
            # EXR often isn't supported by default Pillow builds.
            level = "WARNING" if ext == ".exr" else "ERROR"
            results.append(ValidationResult(level, f"{map_type}: {rec.rel_path} - {err}"))
            continue

        w, h = info.width, info.height

        # Size thresholds
        sev = _severity_for_size(w, h)
        if sev:
            results.append(
                ValidationResult(sev, f"{map_type}: very large resolution ({w}x{h})")
            )

        # Power-of-two warning (common game rule, not always required)
        if not (_is_power_of_two(w) and _is_power_of_two(h)):
            results.append(
                ValidationResult("WARNING", f"{map_type}: not power-of-two ({w}x{h})")
            )

        # Channel sanity checks (lightweight)
        if map_type in {"Normal", "ORM"}:
            # Expect RGB, warn on alpha
            if info.channels < 3:
                results.append(ValidationResult("WARNING", f"{map_type}: suspicious channel count ({info.mode})"))
            if info.has_alpha:
                results.append(ValidationResult("WARNING", f"{map_type}: has alpha channel (unexpected)"))
        elif map_type == "BaseColor":
            # BaseColor can be RGB/RGBA, but grayscale is suspicious
            if info.channels == 1:
                results.append(ValidationResult("WARNING", f"{map_type}: appears grayscale ({info.mode})"))

    return results
