# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QFileSystemWatcher, QTimer
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
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

from validator.core.autofix import apply_renames, plan_renames
from validator.core.batch import scan_folder
from validator.core.grouping import AssetGroup, TextureRecord
from validator.core.reporting import (
    build_batch_report_dict,
    build_report_dict,
    ensure_reports_dir,
    write_batch_json_report,
    write_html_report,
    write_json_report,
)
from validator.core.required_maps import ValidationResult, count_levels
from validator.profiles import PROFILES, Profile


def profile_summary_text(p: Profile) -> str:
    lines = [
        f"Profile: {p.name}",
        "",
        "Rules:",
        "- BaseColor + Normal required",
    ]
    if p.require_orm:
        lines.append("- ORM required (packed AO/Roughness/Metallic)")
        lines.append("- Separate AO/Roughness/Metallic do NOT satisfy by themselves")
    else:
        lines.append("- AO/Roughness/Metallic required OR ORM present")
    if p.allow_exr:
        lines.append("- EXR allowed in metadata checks")
    else:
        lines.append("- EXR not expected (warnings/errors may appear)")
    return "\n".join(lines)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Texture Pack Validator")
        self.resize(1320, 780)

        # Current single-folder state (still supported)
        self._root: Optional[Path] = None
        self._groups: dict[str, AssetGroup] = {}
        self._unparsed: list[TextureRecord] = []
        self._results_by_asset: dict[str, list[ValidationResult]] = {}

        # Batch state
        self._batch_folders: list[Path] = []
        self._last_batch_report: Optional[dict] = None

        # Reporting / metadata
        self._autofix_log_lines: list[str] = []
        self._tool_version: str = "1.0.0"

        # Profiles
        self._profile: Profile = PROFILES[0]

        # Watcher (optional)
        self._watcher = QFileSystemWatcher(self)
        self._watch_enabled = False
        self._debounce_timer = QTimer(self)
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.setInterval(600)  # ms
        self._debounce_timer.timeout.connect(self._on_watch_debounced)
        self._pending_watch_rescan = False

        # --- Top controls (single folder)
        self.folder_label = QLabel("Texture Export Folder:")
        self.folder_edit = QLineEdit()
        self.folder_edit.setPlaceholderText("Select an export folder...")
        self.folder_edit.setReadOnly(True)

        self.pick_btn = QPushButton("Browse...")
        self.scan_btn = QPushButton("Scan Selected")
        self.scan_btn.setEnabled(False)

        self.autofix_checkbox = QCheckBox("Auto-fix naming")
        self.autofix_checkbox.setChecked(False)

        self.batch_rename_checkbox = QCheckBox("Batch can rename")
        self.batch_rename_checkbox.setChecked(False)

        self.profile_combo = QComboBox()
        self.profile_combo.addItems([p.name for p in PROFILES])
        self.profile_combo.setCurrentIndex(0)

        self.watch_checkbox = QCheckBox("Watch folders")
        self.watch_checkbox.setChecked(False)

        # Export (single)
        self.export_json_btn = QPushButton("Export JSON")
        self.export_html_btn = QPushButton("Export HTML")
        self.export_json_btn.setEnabled(False)
        self.export_html_btn.setEnabled(False)

        # Batch controls
        self.add_folder_btn = QPushButton("Add Folder")
        self.remove_folder_btn = QPushButton("Remove Folder")
        self.scan_all_btn = QPushButton("Scan All")
        self.export_batch_btn = QPushButton("Export Batch JSON")
        self.export_batch_btn.setEnabled(False)

        self.summary_label = QLabel("No folder selected.")
        self.summary_label.setTextInteractionFlags(Qt.TextSelectableByMouse)

        # --- Left column: batch folder list + asset list
        self.batch_list = QListWidget()
        self.batch_list.setSelectionMode(QAbstractItemView.ExtendedSelection)

        self.asset_list = QListWidget()
        self.asset_list.setSelectionMode(QAbstractItemView.SingleSelection)

        # --- Right: details
        self.asset_header = QLabel("Select an asset to see its maps.")
        self.asset_header.setTextInteractionFlags(Qt.TextSelectableByMouse)

        self.profile_header = QLabel("Profile rules:")
        self.profile_rules = QLabel(profile_summary_text(self._profile))
        self.profile_rules.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.profile_rules.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.profile_rules.setStyleSheet("QLabel { padding: 6px; border: 1px solid #aaa; }")

        self.map_list = QListWidget()
        self.map_list.setSelectionMode(QAbstractItemView.NoSelection)

        self.results_header = QLabel("Validation results:")
        self.results_list = QListWidget()
        self.results_list.setSelectionMode(QAbstractItemView.NoSelection)

        self.fix_header = QLabel("Auto-fix log:")
        self.fix_log_list = QListWidget()
        self.fix_log_list.setSelectionMode(QAbstractItemView.NoSelection)

        self.parse_header = QLabel("Unparsed / naming issues:")
        self.unparsed_list = QListWidget()
        self.unparsed_list.setSelectionMode(QAbstractItemView.NoSelection)

        self.batch_summary_header = QLabel("Batch summary:")
        self.batch_summary_list = QListWidget()
        self.batch_summary_list.setSelectionMode(QAbstractItemView.NoSelection)

        # --- Layout: left side has batch list + asset list
        left_panel = QWidget()
        left_layout = QVBoxLayout()
        left_layout.addWidget(QLabel("Batch folders:"))
        left_layout.addWidget(self.batch_list, 2)

        batch_btn_row = QHBoxLayout()
        batch_btn_row.addWidget(self.add_folder_btn)
        batch_btn_row.addWidget(self.remove_folder_btn)
        batch_btn_row.addWidget(self.scan_all_btn)
        batch_btn_row.addWidget(self.export_batch_btn)
        left_layout.addLayout(batch_btn_row)

        left_layout.addWidget(QLabel("Assets in selected folder:"))
        left_layout.addWidget(self.asset_list, 2)

        left_panel.setLayout(left_layout)

        # --- Right panel layout
        right_panel = QWidget()
        right_layout = QVBoxLayout()
        right_layout.addWidget(self.asset_header)

        right_layout.addWidget(self.profile_header)
        right_layout.addWidget(self.profile_rules)

        right_layout.addWidget(QLabel("Maps (by type):"))
        right_layout.addWidget(self.map_list, 2)

        right_layout.addWidget(self.results_header)
        right_layout.addWidget(self.results_list, 2)

        right_layout.addWidget(self.fix_header)
        right_layout.addWidget(self.fix_log_list, 1)

        right_layout.addWidget(self.parse_header)
        right_layout.addWidget(self.unparsed_list, 1)

        right_layout.addWidget(self.batch_summary_header)
        right_layout.addWidget(self.batch_summary_list, 1)

        right_panel.setLayout(right_layout)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)

        # --- Top row layout
        top_row = QHBoxLayout()
        top_row.addWidget(self.folder_label)
        top_row.addWidget(self.folder_edit, 1)
        top_row.addWidget(self.pick_btn)
        top_row.addWidget(self.scan_btn)
        top_row.addWidget(self.autofix_checkbox)
        top_row.addWidget(self.batch_rename_checkbox)
        top_row.addWidget(QLabel("Profile:"))
        top_row.addWidget(self.profile_combo)
        top_row.addWidget(self.watch_checkbox)
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
        self.scan_btn.clicked.connect(self.on_scan_selected)
        self.asset_list.currentItemChanged.connect(self.on_asset_selected)

        self.export_json_btn.clicked.connect(self.on_export_json)
        self.export_html_btn.clicked.connect(self.on_export_html)

        self.profile_combo.currentIndexChanged.connect(self.on_profile_changed)

        self.add_folder_btn.clicked.connect(self.on_add_folder)
        self.remove_folder_btn.clicked.connect(self.on_remove_folders)
        self.scan_all_btn.clicked.connect(self.on_scan_all)
        self.export_batch_btn.clicked.connect(self.on_export_batch)

        self.batch_list.currentItemChanged.connect(self.on_batch_selection_changed)

        self.watch_checkbox.toggled.connect(self.on_watch_toggled)
        self._watcher.directoryChanged.connect(self.on_watch_event)
        self._watcher.fileChanged.connect(self.on_watch_event)

    # ----------------------------
    # Profile
    # ----------------------------
    def on_profile_changed(self, idx: int) -> None:
        idx = max(0, min(idx, len(PROFILES) - 1))
        self._profile = PROFILES[idx]
        self.profile_rules.setText(profile_summary_text(self._profile))
        self.statusBar().showMessage(f"Profile set: {self._profile.name}", 2500)

        # If we have current groups loaded, re-run selected scan validations quickly by re-scanning folder
        if self._root and self._root.exists():
            self.on_scan_selected()

    # ----------------------------
    # Single folder selection
    # ----------------------------
    def on_pick_folder(self) -> None:
        start_dir = str(self._root) if self._root else str(Path.home())
        folder = QFileDialog.getExistingDirectory(self, "Select Texture Export Folder", start_dir)
        if not folder:
            return
        self._root = Path(folder)
        self.folder_edit.setText(str(self._root))
        self.scan_btn.setEnabled(True)

        # Also add to batch list if not already present
        if self._root not in self._batch_folders:
            self._batch_folders.append(self._root)
            self._refresh_batch_list(select=self._root)

        self.summary_label.setText("Folder selected. Click Scan Selected or Scan All.")
        self.statusBar().showMessage("Folder set.", 3000)

        # Update watcher paths if enabled
        if self._watch_enabled:
            self._reset_watches()

    def on_batch_selection_changed(self, current: Optional[QListWidgetItem], previous: Optional[QListWidgetItem]) -> None:
        if not current:
            return
        folder_str = current.data(Qt.UserRole)
        if not folder_str:
            return
        p = Path(folder_str)
        if p.exists():
            self._root = p
            self.folder_edit.setText(str(self._root))
            self.scan_btn.setEnabled(True)
            self.statusBar().showMessage("Selected batch folder.", 2000)

    # ----------------------------
    # Batch folder list
    # ----------------------------
    def _refresh_batch_list(self, select: Optional[Path] = None) -> None:
        self.batch_list.clear()
        for p in self._batch_folders:
            it = QListWidgetItem(str(p))
            it.setData(Qt.UserRole, str(p))
            self.batch_list.addItem(it)

        if select:
            for i in range(self.batch_list.count()):
                it = self.batch_list.item(i)
                if Path(it.data(Qt.UserRole)) == select:
                    self.batch_list.setCurrentRow(i)
                    break

    def on_add_folder(self) -> None:
        start_dir = str(Path.home())
        folder = QFileDialog.getExistingDirectory(self, "Add Export Folder to Batch", start_dir)
        if not folder:
            return
        p = Path(folder)
        if p not in self._batch_folders:
            self._batch_folders.append(p)
        self._refresh_batch_list(select=p)

        if self._watch_enabled:
            self._reset_watches()

    def on_remove_folders(self) -> None:
        selected = self.batch_list.selectedItems()
        if not selected:
            return
        remove_set = {Path(it.data(Qt.UserRole)) for it in selected}
        self._batch_folders = [p for p in self._batch_folders if p not in remove_set]
        self._refresh_batch_list()

        if self._watch_enabled:
            self._reset_watches()

    # ----------------------------
    # Watch folders (optional)
    # ----------------------------
    def on_watch_toggled(self, checked: bool) -> None:
        self._watch_enabled = checked
        if checked:
            self._reset_watches()
            self.statusBar().showMessage("Watching folders for changes.", 2500)
        else:
            self._watcher.removePaths(self._watcher.directories())
            self._watcher.removePaths(self._watcher.files())
            self.statusBar().showMessage("Watch disabled.", 2500)

    def _reset_watches(self) -> None:
        # Clear existing
        if self._watcher.directories():
            self._watcher.removePaths(self._watcher.directories())
        if self._watcher.files():
            self._watcher.removePaths(self._watcher.files())

        # Add directory watches (top-level folders only; good enough for v1)
        dirs = [str(p) for p in self._batch_folders if p.exists()]
        if dirs:
            self._watcher.addPaths(dirs)

    def on_watch_event(self, _path: str) -> None:
        if not self._watch_enabled:
            return
        # Debounce so we don't rescan 20 times during a copy/export
        self._pending_watch_rescan = True
        self._debounce_timer.start()

    def _on_watch_debounced(self) -> None:
        if not self._pending_watch_rescan:
            return
        self._pending_watch_rescan = False
        # Auto scan-all
        self.on_scan_all()

    # ----------------------------
    # Scans
    # ----------------------------
    def _clear_right_panels(self) -> None:
        self.asset_list.clear()
        self.map_list.clear()
        self.results_list.clear()
        self.unparsed_list.clear()
        self.fix_log_list.clear()

    def on_scan_selected(self) -> None:
        if not self._root or not self._root.exists():
            self.statusBar().showMessage("Invalid folder.", 4000)
            return

        self._clear_right_panels()
        self.batch_summary_list.clear()
        self._autofix_log_lines.clear()
        self._last_batch_report = None
        self.export_batch_btn.setEnabled(False)

        # Scan folder (build groups, results)
        # Optional auto-fix naming is applied only for selected scan (keeps batch safe)
        # If you want it in batch too later, we can add that.
        groups, unparsed, results_by_asset, summary = scan_folder(self._root, self._profile)

        if self.autofix_checkbox.isChecked():
            # Plan/apply renames for parsed textures, then rescan
            all_actions = []
            for g in groups.values():
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

            # Rescan after rename
            groups, unparsed, results_by_asset, summary = scan_folder(self._root, self._profile)

        else:
            line = "Auto-fix disabled."
            self.fix_log_list.addItem(QListWidgetItem(line))
            self._autofix_log_lines.append(line)

        self._groups = groups
        self._unparsed = unparsed
        self._results_by_asset = results_by_asset

        # Populate asset list with counts
        asset_names = sorted(self._groups.keys(), key=lambda s: s.lower())
        for name in asset_names:
            g = self._groups[name]
            maps = ", ".join(g.map_types()) if g.map_types() else "No parsed maps"
            res = self._results_by_asset.get(name, [])
            e, w, _ = count_levels(res)
            item = QListWidgetItem(f"{name}    [{maps}]    (E:{e} W:{w})")
            item.setData(Qt.UserRole, name)
            self.asset_list.addItem(item)

        # Naming issues
        for rec in self._unparsed:
            msg = rec.parse_error or "Unknown parse error"
            self.unparsed_list.addItem(QListWidgetItem(f"{rec.rel_path} - {msg}"))

        self.summary_label.setText(
            f"Profile: {self._profile.name} | "
            f"Folder: {self._root} | "
            f"Assets: {summary.assets_found} | "
            f"Textures: {summary.textures_scanned} | "
            f"Naming issues: {summary.naming_issues} | "
            f"Errors: {summary.errors} | Warnings: {summary.warnings}"
        )

        self.export_json_btn.setEnabled(True)
        self.export_html_btn.setEnabled(True)

        if self.asset_list.count() > 0:
            self.asset_list.setCurrentRow(0)
        else:
            self.asset_header.setText("No assets found.")

        self.statusBar().showMessage("Scan Selected complete.", 2500)

    def on_scan_all(self) -> None:
        if not self._batch_folders:
            self.statusBar().showMessage("No batch folders to scan.", 3000)
            return

        self.batch_summary_list.clear()
        summaries: list[dict] = []

        total_assets = total_textures = total_issues = total_e = total_w = 0

        for folder in self._batch_folders:
            if not folder.exists():
                summaries.append(
                    {
                        "folder": str(folder),
                        "status": "missing",
                        "assets_found": 0,
                        "textures_scanned": 0,
                        "naming_issues": 0,
                        "errors": 0,
                        "warnings": 0,
                        "infos": 0,
                    }
                )
                self.batch_summary_list.addItem(QListWidgetItem(f"{folder}  - MISSING"))
                continue

                # --- Optional batch rename (explicit + safe)
            rename_applied = 0
            rename_errors = 0

            if self.autofix_checkbox.isChecked() and self.batch_rename_checkbox.isChecked():
                # First pass groups for planning renames
                groups0, unparsed0, results0, summary0 = scan_folder(folder, self._profile)

                all_actions = []
                for g in groups0.values():
                    all_actions.extend(plan_renames(g))

                applied, errors = apply_renames(all_actions)
                rename_applied = len(applied)
                rename_errors = len(errors)

                # Optional: log in batch summary list (keeps it visible)
                if rename_applied:
                    self.batch_summary_list.addItem(QListWidgetItem(f"Renamed in {folder}: {rename_applied} file(s)"))
                for err in errors:
                    self.batch_summary_list.addItem(QListWidgetItem(f"ERROR rename in {folder}: {err}"))

            # Final scan (always) after optional renames
            groups, unparsed, results_by_asset, summary = scan_folder(folder, self._profile)

            summaries.append(
                {
                    "folder": summary.folder,
                    "status": "ok",
                    "assets_found": summary.assets_found,
                    "textures_scanned": summary.textures_scanned,
                    "naming_issues": summary.naming_issues,
                    "errors": summary.errors,
                    "warnings": summary.warnings,
                    "infos": summary.infos,
                    "renames_applied": rename_applied,
                    "rename_errors": rename_errors,
                }
            )

            total_assets += summary.assets_found
            total_textures += summary.textures_scanned
            total_issues += summary.naming_issues
            total_e += summary.errors
            total_w += summary.warnings

            self.batch_summary_list.addItem(
                QListWidgetItem(
                    f"{folder}  | Assets:{summary.assets_found}  Tex:{summary.textures_scanned}  "
                    f"Issues:{summary.naming_issues}  E:{summary.errors} W:{summary.warnings}  "
                    f"Renamed:{rename_applied} ErrRen:{rename_errors}"
                )
            )

        batch_report = build_batch_report_dict(
            tool_version=self._tool_version,
            profile=self._profile.name,
            folder_summaries=summaries,
        )
        self._last_batch_report = batch_report
        self.export_batch_btn.setEnabled(True)

        self.summary_label.setText(
            f"Batch ({self._profile.name}) | "
            f"Folders: {len(self._batch_folders)} | Assets: {total_assets} | Textures: {total_textures} | "
            f"Naming issues: {total_issues} | Errors: {total_e} | Warnings: {total_w}"
        )
        self.statusBar().showMessage("Scan All complete.", 2500)

    # ----------------------------
    # Asset selection
    # ----------------------------
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

        results = self._results_by_asset.get(asset_name, [])
        if not results:
            self.results_list.addItem(QListWidgetItem("INFO: No results."))
        else:
            for r in results:
                self.results_list.addItem(QListWidgetItem(f"{r.level}: {r.message}"))

    # ----------------------------
    # Reporting
    # ----------------------------
    def _build_report(self) -> dict:
        if not self._root:
            raise RuntimeError("No folder selected.")
        return build_report_dict(
            tool_version=self._tool_version,
            profile=self._profile.name,
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

    def on_export_batch(self) -> None:
        if not self._last_batch_report:
            return
        try:
            # Write batch report to the currently selected folder if set; otherwise, home
            base = self._root if self._root else Path.home()
            reports_dir = ensure_reports_dir(base)
            out_path = reports_dir / "batch_report.json"
            write_batch_json_report(self._last_batch_report, out_path)
            QMessageBox.information(self, "Export Batch JSON", f"Saved:\n{out_path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Batch JSON", f"Failed:\n{e}")
