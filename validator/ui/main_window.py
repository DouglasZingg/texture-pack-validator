from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPushButton,
    QSplitter,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from validator.core.grouping import AssetGroup, TextureRecord, build_groups
from validator.core.required_maps import ValidationResult, count_levels, validate_required_maps

SUPPORTED_EXTS = {".png", ".tif", ".tiff", ".jpg", ".jpeg", ".exr"}


@dataclass(frozen=True)
class ScanItem:
    filename: str
    rel_path: str
    ext: str


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
        self.resize(1100, 700)

        self._root: Optional[Path] = None
        self._groups: dict[str, AssetGroup] = {}
        self._unparsed: list[TextureRecord] = []
        self._results_by_asset: dict[str, list[ValidationResult]] = {}

        # --- Top controls
        self.folder_label = QLabel("Texture Export Folder:")
        self.folder_edit = QLineEdit()
        self.folder_edit.setPlaceholderText("Select an export folder...")
        self.folder_edit.setReadOnly(True)

        self.pick_btn = QPushButton("Browse...")
        self.scan_btn = QPushButton("Scan")
        self.scan_btn.setEnabled(False)

        self.summary_label = QLabel("No folder selected.")
        self.summary_label.setTextInteractionFlags(Qt.TextSelectableByMouse)

        # --- Left: asset list
        self.asset_list = QListWidget()
        self.asset_list.setSelectionMode(QAbstractItemView.SingleSelection)

        # --- Right: details for selected asset + parse issues + results
        self.asset_header = QLabel("Select an asset to see its maps.")
        self.asset_header.setTextInteractionFlags(Qt.TextSelectableByMouse)

        self.map_list = QListWidget()
        self.map_list.setSelectionMode(QAbstractItemView.NoSelection)

        self.results_header = QLabel("Validation results:")
        self.results_header.setTextInteractionFlags(Qt.TextSelectableByMouse)

        self.results_list = QListWidget()
        self.results_list.setSelectionMode(QAbstractItemView.NoSelection)

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
        self.asset_header.setText("Select an asset to see its maps.")

        files = list(iter_texture_files(self._root))

        self._groups, self._unparsed = build_groups(files, self._root)

        # Build validation results per asset (Day 3)
        self._results_by_asset = {}
        for name, group in self._groups.items():
            self._results_by_asset[name] = validate_required_maps(group)

        # Populate asset list with counts
        asset_names = sorted(self._groups.keys(), key=lambda s: s.lower())
        total_errors = total_warnings = 0

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

        # Populate unparsed list
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

        # Auto-select first asset if any
        if self.asset_list.count() > 0:
            self.asset_list.setCurrentRow(0)

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

        # Show validation results (Day 3)
        results = self._results_by_asset.get(asset_name, [])
        for r in results:
            self.results_list.addItem(QListWidgetItem(f"{r.level}: {r.message}"))
