from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from validator.util.naming import ParsedName, parse_texture_filename


@dataclass(frozen=True)
class TextureRecord:
    path: Path
    rel_path: str
    ext: str
    parsed: Optional[ParsedName]
    parse_error: Optional[str]


@dataclass
class AssetGroup:
    name: str
    textures: List[TextureRecord]

    def map_types(self) -> List[str]:
        types = sorted({t.parsed.map_type for t in self.textures if t.parsed})
        return types


def build_groups(files: List[Path], root: Path) -> tuple[Dict[str, AssetGroup], List[TextureRecord]]:
    """
    Returns:
      groups: asset_name -> AssetGroup
      unparsed: list of TextureRecord that failed parsing
    """
    groups: Dict[str, AssetGroup] = {}
    unparsed: List[TextureRecord] = []

    for p in files:
        rel = p.relative_to(root).as_posix()
        parsed, err = parse_texture_filename(p.stem)

        rec = TextureRecord(
            path=p,
            rel_path=rel,
            ext=p.suffix.lower(),
            parsed=parsed,
            parse_error=err,
        )

        if not parsed:
            unparsed.append(rec)
            continue

        grp = groups.get(parsed.asset)
        if not grp:
            grp = AssetGroup(name=parsed.asset, textures=[])
            groups[parsed.asset] = grp
        grp.textures.append(rec)

    # Stable ordering inside groups
    for g in groups.values():
        g.textures.sort(key=lambda r: r.rel_path.lower())

    unparsed.sort(key=lambda r: r.rel_path.lower())
    return groups, unparsed
