from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

from validator.core.grouping import AssetGroup, TextureRecord, build_groups
from validator.core.image_metadata import validate_image_metadata
from validator.core.orm_validation import validate_orm_maps
from validator.core.required_maps import ValidationResult, count_levels, validate_required_maps
from validator.profiles import Profile
from validator.config import SUPPORTED_EXTS


def iter_texture_files(root: Path):
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if p.suffix.lower() not in SUPPORTED_EXTS:
            continue
        yield p


@dataclass
class FolderScanResult:
    folder: str
    assets_found: int
    textures_scanned: int
    naming_issues: int
    errors: int
    warnings: int
    infos: int


def scan_folder(folder: Path, profile: Profile) -> tuple[Dict[str, AssetGroup], List[TextureRecord], Dict[str, List[ValidationResult]], FolderScanResult]:
    files = list(iter_texture_files(folder))
    groups, unparsed = build_groups(files, folder)

    results_by_asset: Dict[str, List[ValidationResult]] = {}
    total_e = total_w = total_i = 0

    for name, group in groups.items():
        res: List[ValidationResult] = []
        res.extend(validate_required_maps(group, profile))
        res.extend(validate_image_metadata(group, profile))
        res.extend(validate_orm_maps(group))
        results_by_asset[name] = res

        e, w, i = count_levels(res)
        total_e += e
        total_w += w
        total_i += i

    summary = FolderScanResult(
        folder=str(folder),
        assets_found=len(groups),
        textures_scanned=len(files),
        naming_issues=len(unparsed),
        errors=total_e,
        warnings=total_w,
        infos=total_i,
    )

    return groups, unparsed, results_by_asset, summary
