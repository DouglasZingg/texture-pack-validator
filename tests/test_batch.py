from __future__ import annotations

from pathlib import Path

from PIL import Image

from validator.core.batch import scan_folder
from validator.core.autofix import plan_renames, apply_renames
from validator.profiles import get_profile


def write_png(path: Path, size=(4, 4), mode="RGB") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new(mode, size).save(path)


def test_batch_scan_summary_counts(tmp_path: Path) -> None:
    export_dir = tmp_path / "exports"
    export_dir.mkdir()

    # CrateA: BaseColor + Normal + ORM
    write_png(export_dir / "CrateA_BaseColor.png")
    write_png(export_dir / "CrateA_Normal.png")
    write_png(export_dir / "CrateA_ORM.png")

    # CrateB: incomplete
    write_png(export_dir / "CrateB_BaseColor.png")

    profile = get_profile("Unity")
    groups, unparsed, results_by_asset, summary = scan_folder(export_dir, profile)

    assert summary.assets_found == 2
    assert summary.textures_scanned == 4
    assert summary.naming_issues == 0
    assert summary.errors >= 1
    assert "CrateA" in groups
    assert "CrateB" in groups


def test_unreal_requires_orm(tmp_path: Path) -> None:
    export_dir = tmp_path / "exports"
    export_dir.mkdir()

    # Separate maps present, but Unreal requires ORM
    write_png(export_dir / "CrateA_BaseColor.png")
    write_png(export_dir / "CrateA_Normal.png")
    write_png(export_dir / "CrateA_Roughness.png")
    write_png(export_dir / "CrateA_Metallic.png")
    write_png(export_dir / "CrateA_AmbientOcclusion.png")

    profile = get_profile("Unreal")
    groups, unparsed, results_by_asset, summary = scan_folder(export_dir, profile)

    crate_res = results_by_asset["CrateA"]
    assert any(r.level == "ERROR" and "ORM" in r.message for r in crate_res)


def test_autofix_never_overwrites(tmp_path: Path) -> None:
    export_dir = tmp_path / "exports"
    export_dir.mkdir()

    # Collision-ish scenario
    write_png(export_dir / "CrateA_BaseColor.png")
    write_png(export_dir / "CrateA_basecolor.png")

    profile = get_profile("Unity")
    groups0, unparsed0, results0, summary0 = scan_folder(export_dir, profile)

    actions = []
    for g in groups0.values():
        actions.extend(plan_renames(g))

    applied, errors = apply_renames(actions)

    assert len(errors) == 0
