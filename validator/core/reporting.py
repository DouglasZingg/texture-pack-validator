from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from validator.core.grouping import AssetGroup, TextureRecord
from validator.core.required_maps import ValidationResult


def iso_now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def ensure_reports_dir(root: Path) -> Path:
    out = root / "reports"
    out.mkdir(parents=True, exist_ok=True)
    return out


def group_maps_list(group: AssetGroup) -> List[str]:
    return sorted({r.parsed.map_type for r in group.textures if r.parsed})


def serialize_results(results: List[ValidationResult]) -> List[dict]:
    return [{"level": r.level, "message": r.message} for r in results]


def serialize_unparsed(unparsed: List[TextureRecord]) -> List[dict]:
    out: List[dict] = []
    for r in unparsed:
        out.append(
            {
                "file": r.rel_path,
                "error": r.parse_error or "Unknown parse error",
            }
        )
    return out


def build_report_dict(
    tool_version: str,
    profile: str,
    groups: Dict[str, AssetGroup],
    results_by_asset: Dict[str, List[ValidationResult]],
    unparsed: List[TextureRecord],
    autofix_log: Optional[List[str]] = None,
) -> dict:
    assets = []
    for name in sorted(groups.keys(), key=lambda s: s.lower()):
        g = groups[name]
        assets.append(
            {
                "name": name,
                "maps": group_maps_list(g),
                "results": serialize_results(results_by_asset.get(name, [])),
            }
        )

    report = {
        "tool": "Texture Pack Validator",
        "version": tool_version,
        "timestamp": iso_now(),
        "profile": profile,
        "assets": assets,
        "naming_issues": serialize_unparsed(unparsed),
        "autofix_log": autofix_log or [],
    }
    return report


def write_json_report(report: dict, output_path: Path) -> None:
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")


def write_html_report(report: dict, output_path: Path) -> None:
    """
    Simple no-deps HTML report (jinja2 comes later if you want).
    """
    def esc(s: str) -> str:
        return (
            s.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )

    title = f"{report.get('tool')} - Report"
    ts = esc(str(report.get("timestamp", "")))
    profile = esc(str(report.get("profile", "")))

    rows = []
    for asset in report.get("assets", []):
        name = esc(asset.get("name", ""))
        maps = ", ".join(asset.get("maps", []))
        maps = esc(maps)

        res_lines = []
        for r in asset.get("results", []):
            lvl = esc(r.get("level", ""))
            msg = esc(r.get("message", ""))
            res_lines.append(f"<div><b>{lvl}</b>: {msg}</div>")
        res_html = "".join(res_lines) if res_lines else "<div><i>No results</i></div>"

        rows.append(
            f"""
            <tr>
              <td style="vertical-align:top; padding:8px; border-bottom:1px solid #ddd;"><b>{name}</b></td>
              <td style="vertical-align:top; padding:8px; border-bottom:1px solid #ddd;">{maps}</td>
              <td style="vertical-align:top; padding:8px; border-bottom:1px solid #ddd;">{res_html}</td>
            </tr>
            """
        )

    naming_rows = []
    for ni in report.get("naming_issues", []):
        f = esc(ni.get("file", ""))
        e = esc(ni.get("error", ""))
        naming_rows.append(f"<div><b>{f}</b>: {e}</div>")
    naming_html = "".join(naming_rows) if naming_rows else "<div><i>None</i></div>"

    autofix_lines = []
    for line in report.get("autofix_log", []):
        autofix_lines.append(f"<div>{esc(line)}</div>")
    autofix_html = "".join(autofix_lines) if autofix_lines else "<div><i>None</i></div>"

    html = f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>{esc(title)}</title>
</head>
<body style="font-family: Arial, sans-serif; margin: 24px;">
  <h1 style="margin-bottom:4px;">{esc(title)}</h1>
  <div style="color:#444;">Timestamp: {ts}</div>
  <div style="color:#444; margin-bottom:16px;">Profile: {profile}</div>

  <h2>Assets</h2>
  <table style="border-collapse:collapse; width:100%;">
    <thead>
      <tr>
        <th style="text-align:left; padding:8px; border-bottom:2px solid #333;">Asset</th>
        <th style="text-align:left; padding:8px; border-bottom:2px solid #333;">Maps</th>
        <th style="text-align:left; padding:8px; border-bottom:2px solid #333;">Results</th>
      </tr>
    </thead>
    <tbody>
      {''.join(rows)}
    </tbody>
  </table>

  <h2 style="margin-top:24px;">Naming Issues</h2>
  {naming_html}

  <h2 style="margin-top:24px;">Auto-fix Log</h2>
  {autofix_html}
</body>
</html>
"""
    output_path.write_text(html, encoding="utf-8")

def write_batch_json_report(batch_report: dict, output_path: Path) -> None:
    output_path.write_text(json.dumps(batch_report, indent=2), encoding="utf-8")


def build_batch_report_dict(
    tool_version: str,
    profile: str,
    folder_summaries: list[dict],
) -> dict:
    return {
        "tool": "Texture Pack Validator",
        "version": tool_version,
        "timestamp": iso_now(),
        "profile": profile,
        "folders": folder_summaries,
    }
