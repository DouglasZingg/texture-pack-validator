from __future__ import annotations

from pathlib import Path
from typing import Iterable, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from validator.config import SUPPORTED_EXTS
from validator.core.autofix import apply_renames, plan_renames
from validator.core.grouping import AssetGroup, TextureRecord, build_groups
from validator.core.image_metadata import validate_image_metadata
from validator.core.orm_validation import validate_orm_maps
from validator.core.reporting import (
    build_report_dict,
    ensure_reports_dir,
    write_html_report,
    write_json_report,
)
from validator.core.required_maps import ValidationResult, count_levels, validate_required_maps


def iter_texture_files(root: Path) -> Iterable[Path]:
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if p.suffix.lower() not in SUPPORTED_EXTS:
            continue
        yield p


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Texture Pack Validator")
        self.resize(1200, 720)

        self._root: Optional[Path] = None
        self._groups: dict[str, AssetGroup] = {}
        self._unparsed: list[TextureRecord] = []
        self._results_by_asset: dict[str, list[ValidationResult]] = []

        # Reporting / metadata
        self._autofix_log_lines: list[str] = []
        self._profile_name: str = "Default"
        self._tool_version: str = "1.0.0"

        # --- Top controls
        self.folder_label = QLabel("Texture Export Folder:")
        self.folder_edit = QLineEdit()
        self.folder_edit.setPlaceholderText("Select an export folder...")
        self.folder_edit.setReadOnly(True)

        self.pick_btn = QPushButton("Browse...")
        self.scan_btn = QPushButton("Scan")
        self.scan_btn.setEnabled(False)

        self.autofix_checkbox = QCheckBox("Auto-fix naming")
        self.autofix_checkbox.setChecked(False)

        self.export_json_btn = QPushButton("Export JSON")
        self.export_html_btn = QPushButton("Export HTML")
        self.export_json_btn.setEnabled(False)
        self.export_html_btn.setEnabled(False)

        self.summary_label = QLabel("No folder selected.")
        self.summary_label.setTextInteractionFlags(Qt.TextSelectableByMouse)

        # --- Left: asset list
        self.asset_list = QListWidget()
        self.asset_list.setSelectionMode(QAbstractItemView.SingleSelection)

        # --- Right: details
        self.asset_header = QLabel("Select an asset to see its maps.")
        self.asset_header.setTextInteractionFlags(Qt.TextSelectableByMouse)

        self.map_list = QListWidget()
        self.map_list.setSelectionMode(QAbstractItemView.NoSelection)

        self.results_header = QLabel("Validation results:")
        self.results_header.setTextInteractionFlags(Qt.TextSelectableByMouse)

        self.results_list = QListWidget()
        self.results_list.setSelectionMode(QAbstractItemView.NoSelection)

        self.fix_header = QLabel("Auto-fix log:")
        self.fix_header.setTextInteractionFlags(Qt.TextSelectableByMouse)

        self.fix_log_list = QListWidget()
        self.fix_log_list.setSelectionMode(QAbstractItemView.NoSelection)

        self.parse_header = QLabel("Unparsed / naming issues:")
        self.parse_header.setTextInteractionFlags(Qt.TextSelectableByMouse)

        self.unparsed_list = QListWidget()
        self.unparsed_list.setSelectionMode(QAbstractItemView.NoSelection)

        # --- Splitter layout
        right_panel = QWidget()
        right_layout = QVBoxLayout()
        right_layout.addWidget(self.asset_header)

        right_layout.addWidget(QLabel("Maps (by type):"))
        right_layout.addWidget(self.map_list, 2)

        right_layout.addWidget(self.results_header)
        right_layout.addWidget(self.results_list, 2)

        right_layout.addWidget(self.fix_header)
        right_layout.addWidget(self.fix_log_list, 1)

        right_layout.addWidget(self.parse_header)
        right_layout.addWidget(self.unparsed_list, 1)

        right_panel.setLayout(right_layout)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self.asset_list)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)

        # --- Main layout
        top_row = QHBoxLayout()
        top_row.addWidget(self.folder_label)
        top_row.addWidget(self.folder_edit, 1)
        top_row.addWidget(self.pick_btn)
        top_row.addWidget(self.scan_btn)
        top_row.addWidget(self.autofix_checkbox)
        top_row.addWidget(self.export_json_btn)
        top_row.addWidget(self.export_html_btn)

        main_layout = QVBoxLayout()
        main_layout.addLayout(top_row)
        main_layout.addWidget(self.summary_label)
        main_layout.addWidget(splitter, 1)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

        self.setStatusBar(QStatusBar())

        # --- Signals
        self.pick_btn.clicked.connect(self.on_pick_folder)
        self.scan_btn.clicked.connect(self.on_scan)
        self.asset_list.currentItemChanged.connect(self.on_asset_selected)
        self.export_json_btn.clicked.connect(self.on_export_json)
        self.export_html_btn.clicked.connect(self.on_export_html)

    # ----------------------------
    # UI Actions
    # ----------------------------
    def on_pick_folder(self) -> None:
        start_dir = str(self._root) if self._root else str(Path.home())
        folder = QFileDialog.getExistingDirectory(self, "Select Texture Export Folder", start_dir)
        if not folder:
            return

        self._root = Path(folder)
        self.folder_edit.setText(str(self._root))
        self.scan_btn.setEnabled(True)

        self.summary_label.setText("Folder selected. Click Scan.")
        self.statusBar().showMessage("Folder set.", 3000)

    def on_scan(self) -> None:
        if not self._root or not self._root.exists():
            self.statusBar().showMessage("Invalid folder.", 4000)
            return

        self.asset_list.clear()
        self.map_list.clear()
        self.results_list.clear()
        self.unparsed_list.clear()
        self.fix_log_list.clear()
        self._autofix_log_lines.clear()
        self.asset_header.setText("Select an asset to see its maps.")

        # Initial scan + grouping
        files = list(iter_texture_files(self._root))
        self._groups, self._unparsed = build_groups(files, self._root)

        # Day 6: optional auto-fix rename, then rebuild groups
        if self.autofix_checkbox.isChecked():
            all_actions = []
            for g in self._groups.values():
                all_actions.extend(plan_renames(g))

            applied, errors = apply_renames(all_actions)

            if not applied and not errors:
                line = "Auto-fix enabled: nothing to rename."
                self.fix_log_list.addItem(QListWidgetItem(line))
                self._autofix_log_lines.append(line)

            for a in applied:
                line = f"Renamed: {a.src.name} -> {a.dst.name} ({a.note})"
                self.fix_log_list.addItem(QListWidgetItem(line))
                self._autofix_log_lines.append(line)

            for err in errors:
                line = f"ERROR: {err}"
                self.fix_log_list.addItem(QListWidgetItem(line))
                self._autofix_log_lines.append(line)

            # Re-scan after renames so everything reflects final names
            files = list(iter_texture_files(self._root))
            self._groups, self._unparsed = build_groups(files, self._root)
        else:
            line = "Auto-fix disabled."
            self.fix_log_list.addItem(QListWidgetItem(line))
            self._autofix_log_lines.append(line)

        # Build validation results per asset (Days 3-5)
        self._results_by_asset = {}
        for name, group in self._groups.items():
            results: list[ValidationResult] = []
            results.extend(validate_required_maps(group))     # Day 3
            results.extend(validate_image_metadata(group))    # Day 4
            results.extend(validate_orm_maps(group))          # Day 5
            self._results_by_asset[name] = results

        # Populate asset list with counts
        asset_names = sorted(self._groups.keys(), key=lambda s: s.lower())
        total_errors = 0
        total_warnings = 0

        for name in asset_names:
            g = self._groups[name]
            maps = ", ".join(g.map_types()) if g.map_types() else "No parsed maps"

            res = self._results_by_asset.get(name, [])
            e, w, _ = count_levels(res)
            total_errors += e
            total_warnings += w

            item = QListWidgetItem(f"{name}    [{maps}]    (E:{e} W:{w})")
            item.setData(Qt.UserRole, name)
            self.asset_list.addItem(item)

        # Populate naming issues list
        for rec in self._unparsed:
            msg = rec.parse_error or "Unknown parse error"
            self.unparsed_list.addItem(QListWidgetItem(f"{rec.rel_path} - {msg}"))

        self.summary_label.setText(
            f"Assets found: {len(self._groups)} | "
            f"Textures scanned: {len(files)} | "
            f"Naming issues: {len(self._unparsed)} | "
            f"Errors: {total_errors} | Warnings: {total_warnings}"
        )

        self.statusBar().showMessage(
            f"Scan complete: {len(self._groups)} assets, {total_errors} errors.",
            5000,
        )

        # Enable exports after a scan
        self.export_json_btn.setEnabled(True)
        self.export_html_btn.setEnabled(True)

        # Auto-select first asset if any
        if self.asset_list.count() > 0:
            self.asset_list.setCurrentRow(0)
        else:
            self.map_list.clear()
            self.results_list.clear()
            self.asset_header.setText("No assets found.")

    def on_asset_selected(self, current: Optional[QListWidgetItem], previous: Optional[QListWidgetItem]) -> None:
        self.map_list.clear()
        self.results_list.clear()

        if not current:
            self.asset_header.setText("Select an asset to see its maps.")
            return

        asset_name = current.data(Qt.UserRole)
        group = self._groups.get(asset_name)
        if not group:
            self.asset_header.setText("Select an asset to see its maps.")
            return

        # Build map-type -> list of files display
        by_type: dict[str, list[str]] = {}
        for rec in group.textures:
            if not rec.parsed:
                continue
            by_type.setdefault(rec.parsed.map_type, []).append(rec.rel_path)

        self.asset_header.setText(f"Asset: {group.name} | Parsed textures: {len(group.textures)}")

        for map_type in sorted(by_type.keys(), key=lambda s: s.lower()):
            self.map_list.addItem(QListWidgetItem(f"{map_type} ({len(by_type[map_type])})"))
            for rel in by_type[map_type]:
                child = QListWidgetItem(f"  - {rel}")
                child.setFlags(child.flags() & ~Qt.ItemIsSelectable)
                self.map_list.addItem(child)

        # Show validation results (Days 3-5)
        results = self._results_by_asset.get(asset_name, [])
        if not results:
            self.results_list.addItem(QListWidgetItem("INFO: No results."))
        else:
            for r in results:
                self.results_list.addItem(QListWidgetItem(f"{r.level}: {r.message}"))

    # ----------------------------
    # Reporting (Day 7)
    # ----------------------------
    def _build_report(self) -> dict:
        if not self._root:
            raise RuntimeError("No folder selected.")

        return build_report_dict(
            tool_version=self._tool_version,
            profile=self._profile_name,
            groups=self._groups,
            results_by_asset=self._results_by_asset,
            unparsed=self._unparsed,
            autofix_log=self._autofix_log_lines,
        )

    def on_export_json(self) -> None:
        if not self._root:
            return

        try:
            reports_dir = ensure_reports_dir(self._root)
            out_path = reports_dir / "report.json"

            report = self._build_report()
            write_json_report(report, out_path)

            QMessageBox.information(self, "Export JSON", f"Saved:\n{out_path}")
        except Exception as e:
            QMessageBox.critical(self, "Export JSON", f"Failed:\n{e}")

    def on_export_html(self) -> None:
        if not self._root:
            return

        try:
            reports_dir = ensure_reports_dir(self._root)
            out_path = reports_dir / "report.html"

            report = self._build_report()
            write_html_report(report, out_path)

            QMessageBox.information(self, "Export HTML", f"Saved:\n{out_path}")
        except Exception as e:
            QMessageBox.critical(self, "Export HTML", f"Failed:\n{e}")
