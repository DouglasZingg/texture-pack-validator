from __future__ import annotations

from validator.profiles import get_profile


def test_profiles_exist():
    assert get_profile("Unreal").name == "Unreal"
    assert get_profile("Unity").name == "Unity"
    assert get_profile("VFX").name == "VFX"
