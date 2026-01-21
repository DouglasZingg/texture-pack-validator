from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional, Tuple

# Canonical map types we support (Day 2)
CANON_MAPS = {
    "BaseColor",
    "Normal",
    "Roughness",
    "Metallic",
    "AmbientOcclusion",
    "ORM",
    "Emissive",
    "Opacity",
    "Height",
}

# Aliases -> canonical
ALIASES = {
    # BaseColor
    "albedo": "BaseColor",
    "basecolor": "BaseColor",
    "diffuse": "BaseColor",
    "color": "BaseColor",
    "col": "BaseColor",
    # Normal
    "normal": "Normal",
    "nrm": "Normal",
    "nor": "Normal",
    # Roughness
    "roughness": "Roughness",
    "rough": "Roughness",
    "rgh": "Roughness",
    # Metallic
    "metallic": "Metallic",
    "metal": "Metallic",
    "met": "Metallic",
    # AO
    "ao": "AmbientOcclusion",
    "ambientocclusion": "AmbientOcclusion",
    "occlusion": "AmbientOcclusion",
    "occ": "AmbientOcclusion",
    # Packed
    "orm": "ORM",
    "rma": "ORM",
    # Optional
    "emissive": "Emissive",
    "emis": "Emissive",
    "opacity": "Opacity",
    "alpha": "Opacity",
    "height": "Height",
    "disp": "Height",
    "displacement": "Height",
}

_VERSION_RE = re.compile(r"^(?P<base>.+)_(?:v|V)(?P<ver>\d{3,})$", re.IGNORECASE)


@dataclass(frozen=True)
class ParsedName:
    asset: str
    map_type: str
    version: Optional[int]
    raw_map_token: str


def canonicalize_map_token(token: str) -> Optional[str]:
    t = token.strip().lower()
    if not t:
        return None
    canon = ALIASES.get(t)
    if canon:
        return canon
    # If user already uses canonical spelling
    # (case-insensitive)
    for m in CANON_MAPS:
        if t == m.lower():
            return m
    return None


def parse_texture_filename(stem: str) -> Tuple[Optional[ParsedName], Optional[str]]:
    """
    Parse filenames like:
      Asset_MapType
      Asset_MapType_v###     (version optional)

    Returns: (ParsedName | None, error_message | None)
    """
    parts = stem.split("_")
    if len(parts) < 2:
        return None, "No '_' separator found (expected Asset_MapType[_v###])."

    version: Optional[int] = None

    # Case: ..._MapType_v###
    last = parts[-1]
    if last.lower().startswith("v") and last[1:].isdigit() and len(last) >= 4:
        # Need at least Asset, MapType, v###
        if len(parts) < 3:
            return None, "Version suffix present but missing map type (expected Asset_MapType_v###)."

        try:
            version = int(last[1:])
        except ValueError:
            return None, "Version suffix could not be parsed."

        map_token = parts[-2]
        asset = "_".join(parts[:-2]).strip()
    else:
        # Case: ..._MapType
        map_token = parts[-1]
        asset = "_".join(parts[:-1]).strip()

    if not asset:
        return None, "Asset name was empty."

    canon = canonicalize_map_token(map_token)
    if not canon:
        return None, f"Unknown map type token '{map_token}'."

    return ParsedName(asset=asset, map_type=canon, version=version, raw_map_token=map_token), None

