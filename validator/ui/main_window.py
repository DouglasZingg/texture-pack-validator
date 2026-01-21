from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPushButton,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)


SUPPORTED_EXTS = {".png", ".tif", ".tiff", ".jpg", ".jpeg", ".exr"}


@dataclass(frozen=True)
class ScanItem:
    filename: str
    rel_path: str
    ext: str


def iter_texture_files(root: Path) -> Iterable[Path]:
    # Recursive scan; ignores hidden/system-ish noise reasonably well.
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if p.suffix.lower() not in SUPPORTED_EXTS:
            continue
        yield p


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Texture Pack Validator (Day 1)")
        self.resize(920, 600)

        self._root: Path | None = None

        # --- Widgets
        self.folder_label = QLabel("Texture Export Folder:")
        self.folder_edit = QLineEdit()
        self.folder_edit.setPlaceholderText("Select an export folder...")
        self.folder_edit.setReadOnly(True)

        self.pick_btn = QPushButton("Browse...")
        self.scan_btn = QPushButton("Scan")
        self.scan_btn.setEnabled(False)

        self.summary_label = QLabel("No folder selected.")
        self.summary_label.setTextInteractionFlags(Qt.TextSelectableByMouse)

        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QAbstractItemView.ExtendedSelection)

        # --- Layout
        top_row = QHBoxLayout()
        top_row.addWidget(self.folder_label)
        top_row.addWidget(self.folder_edit, 1)
        top_row.addWidget(self.pick_btn)
        top_row.addWidget(self.scan_btn)

        main_layout = QVBoxLayout()
        main_layout.addLayout(top_row)
        main_layout.addWidget(self.summary_label)
        main_layout.addWidget(self.list_widget, 1)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

        self.setStatusBar(QStatusBar())

        # --- Signals
        self.pick_btn.clicked.connect(self.on_pick_folder)
        self.scan_btn.clicked.connect(self.on_scan)

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

        self.list_widget.clear()

        files = list(iter_texture_files(self._root))
        items = self._to_scan_items(files, self._root)

        # Sort for stable UI
        items.sort(key=lambda x: (x.rel_path.lower(), x.filename.lower()))

        for it in items:
            text = f"{it.rel_path}  ({it.ext.upper().lstrip('.')})"
            row = QListWidgetItem(text)
            row.setData(Qt.UserRole, it)  # store the structured item for future days
            self.list_widget.addItem(row)

        self.summary_label.setText(
            f"Found {len(items)} texture files "
            f"({', '.join(sorted(e.upper().lstrip('.') for e in SUPPORTED_EXTS))})."
        )
        self.statusBar().showMessage(f"Scan complete: {len(items)} files.", 4000)

    @staticmethod
    def _to_scan_items(files: List[Path], root: Path) -> List[ScanItem]:
        out: List[ScanItem] = []
        for p in files:
            rel = p.relative_to(root).as_posix()
            out.append(
                ScanItem(
                    filename=p.name,
                    rel_path=rel,
                    ext=p.suffix.lower(),
                )
            )
        return out
