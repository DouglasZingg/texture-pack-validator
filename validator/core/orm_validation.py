from __future__ import annotations

from typing import List

from PIL import Image

from validator.core.grouping import AssetGroup
from validator.core.required_maps import ValidationResult
from validator.util.image_info import read_image_info


def _channel_extrema(img: Image.Image) -> tuple[tuple[int, int], tuple[int, int], tuple[int, int]] | None:
    """
    Returns (R_minmax, G_minmax, B_minmax) for RGB image using getextrema().
    """
    try:
        extrema = img.getextrema()
        # For RGB, extrema is: ((rmin,rmax),(gmin,gmax),(bmin,bmax))
        if isinstance(extrema, tuple) and len(extrema) >= 3 and isinstance(extrema[0], tuple):
            return extrema[0], extrema[1], extrema[2]
    except Exception:
        return None
    return None


def validate_orm_maps(group: AssetGroup) -> List[ValidationResult]:
    """
    Day 5 ORM checks :
      - must be readable
      - must have >= 3 channels (RGB)
      - warn if alpha present
      - warn if channels look identical (grayscale-ish)
      - warn if any channel is flat (min == max)
    """
    results: List[ValidationResult] = []

    # Find ORM textures
    orm_recs = [r for r in group.textures if r.parsed and r.parsed.map_type == "ORM"]
    if not orm_recs:
        return results

    for rec in orm_recs:
        info, err = read_image_info(rec.path)
        if err:
            # Let Day 4 handle metadata read errors; keep this as a soft warning
            results.append(ValidationResult("WARNING", f"ORM: {rec.rel_path} - cannot analyze channels ({err})"))
            continue

        # Channel count check
        if info.channels < 3:
            results.append(ValidationResult("ERROR", f"ORM: {rec.rel_path} - needs RGB (3 channels), got {info.mode}"))
            continue

        if info.has_alpha:
            results.append(ValidationResult("WARNING", f"ORM: {rec.rel_path} - has alpha channel (unexpected)"))

        # Analyze content quickly
        try:
            with Image.open(rec.path) as img:
                # Convert to RGB for consistent extrema
                rgb = img.convert("RGB")
                ex = _channel_extrema(rgb)
                if not ex:
                    results.append(ValidationResult("WARNING", f"ORM: {rec.rel_path} - could not compute channel extrema"))
                    continue

                (rmin, rmax), (gmin, gmax), (bmin, bmax) = ex

                # Flat channel warnings (common packing mistake)
                if rmin == rmax:
                    results.append(ValidationResult("WARNING", f"ORM: {rec.rel_path} - R channel is flat (AO may be missing)"))
                if gmin == gmax:
                    results.append(ValidationResult("WARNING", f"ORM: {rec.rel_path} - G channel is flat (Roughness may be missing)"))
                if bmin == bmax:
                    results.append(ValidationResult("WARNING", f"ORM: {rec.rel_path} - B channel is flat (Metallic may be missing)"))

                # Grayscale-ish: all channels share same extrema
                if (rmin, rmax) == (gmin, gmax) == (bmin, bmax):
                    results.append(ValidationResult("WARNING", f"ORM: {rec.rel_path} - channels look identical (may be grayscale, not packed)"))

        except Exception as e:
            results.append(ValidationResult("WARNING", f"ORM: {rec.rel_path} - channel analysis failed ({e})"))

    return results
