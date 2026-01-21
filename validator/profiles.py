from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Set


@dataclass(frozen=True)
class Profile:
    name: str
    require_orm: bool
    allow_separate_rma: bool
    allow_exr: bool


PROFILES = [
    Profile(name="Unreal", require_orm=True, allow_separate_rma=False, allow_exr=False),
    Profile(name="Unity", require_orm=False, allow_separate_rma=True, allow_exr=False),
    Profile(name="VFX", require_orm=False, allow_separate_rma=True, allow_exr=True),
]


def get_profile(name: str) -> Profile:
    for p in PROFILES:
        if p.name.lower() == name.lower():
            return p
    return PROFILES[0]
