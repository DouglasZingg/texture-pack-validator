from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Set

from validator.core.grouping import AssetGroup


@dataclass(frozen=True)
class ValidationResult:
    level: str  # "INFO" | "WARNING" | "ERROR"
    message: str


def _present_map_types(group: AssetGroup) -> Set[str]:
    return {rec.parsed.map_type for rec in group.textures if rec.parsed}


def validate_required_maps(group: AssetGroup) -> List[ValidationResult]:
    """
    Day 3 rules (v1):
      - BaseColor required
      - Normal required
      - Roughness/Metallic/AO required OR ORM present (packed)
    """
    results: List[ValidationResult] = []
    present = _present_map_types(group)

    # Base requirements
    if "BaseColor" not in present:
        results.append(ValidationResult("ERROR", "Missing required map: BaseColor"))
    if "Normal" not in present:
        results.append(ValidationResult("ERROR", "Missing required map: Normal"))

    # Packed workflow
    if "ORM" in present:
        results.append(ValidationResult("INFO", "ORM present (AO/Roughness/Metallic packed)"))
    else:
        # Separate workflow requirements
        missing = []
        if "AmbientOcclusion" not in present:
            missing.append("AmbientOcclusion")
        if "Roughness" not in present:
            missing.append("Roughness")
        if "Metallic" not in present:
            missing.append("Metallic")

        if missing:
            results.append(
                ValidationResult(
                    "ERROR",
                    "Missing required map(s): " + ", ".join(missing) + " (or provide ORM)",
                )
            )

    if not results:
        results.append(ValidationResult("INFO", "All required maps present."))

    return results


def count_levels(results: Iterable[ValidationResult]) -> tuple[int, int, int]:
    """Returns (errors, warnings, infos)."""
    e = w = i = 0
    for r in results:
        if r.level == "ERROR":
            e += 1
        elif r.level == "WARNING":
            w += 1
        else:
            i += 1
    return e, w, i
