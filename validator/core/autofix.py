from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from validator.core.grouping import AssetGroup, TextureRecord


@dataclass(frozen=True)
class RenameAction:
    src: Path
    dst: Path
    note: str


def _unique_path(dst: Path) -> Path:
    """
    If dst exists, add suffix _fixedN before extension.
    """
    if not dst.exists():
        return dst

    stem = dst.stem
    ext = dst.suffix
    parent = dst.parent

    i = 1
    while True:
        candidate = parent / f"{stem}_fixed{i}{ext}"
        if not candidate.exists():
            return candidate
        i += 1


def plan_renames(group: AssetGroup) -> List[RenameAction]:
    """
    Plan renames for all parsed textures in a group.
    Target naming: Asset_MapType.ext (drops version tokens).
    """
    actions: List[RenameAction] = []

    for rec in group.textures:
        if not rec.parsed:
            continue

        asset = rec.parsed.asset
        map_type = rec.parsed.map_type
        ext = rec.path.suffix  # keep original ext exactly

        desired_name = f"{asset}_{map_type}{ext}"
        desired_path = rec.path.with_name(desired_name)

        # Skip if already matches desired
        if rec.path.name == desired_name:
            continue

        # Ensure we don't overwrite; make unique if needed
        final_dst = _unique_path(desired_path)

        note = "rename"
        if final_dst != desired_path:
            note = "rename (collision -> suffixed)"

        actions.append(RenameAction(src=rec.path, dst=final_dst, note=note))

    return actions


def apply_renames(actions: List[RenameAction]) -> Tuple[List[RenameAction], List[str]]:
    """
    Execute renames. Returns (applied_actions, errors).
    """
    applied: List[RenameAction] = []
    errors: List[str] = []

    for a in actions:
        try:
            # Re-check collision at time of rename
            dst = _unique_path(a.dst)
            a2 = RenameAction(src=a.src, dst=dst, note=a.note)
            a2.src.rename(a2.dst)
            applied.append(a2)
        except Exception as e:
            errors.append(f"Failed to rename '{a.src.name}' -> '{a.dst.name}': {e}")

    return applied, errors
