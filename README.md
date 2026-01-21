# Texture Pack Validator (Project 7)

Standalone Python + PySide6 utility that validates Substance Painter / game-ready texture exports and produces severity-based QA reports.

**Targets:** Pipeline Developer / Tools / Technical Artist  
**Use cases:** Unreal/Unity texture delivery, VFX asset lookdev handoff, texture library QA

---

## Features

### Scan + Grouping
- Scans a folder (or batch of folders) for texture exports (`.png`, `.tif/.tiff`, `.jpg/.jpeg`, `.exr`)
- Parses filenames into **Asset + MapType (+ optional version)**
- Groups textures per asset/material set

### Validation (Severity-based)
- **Required maps** (profile aware):
  - BaseColor + Normal required
  - Unreal profile: **ORM required**
  - Unity/VFX profiles: requires **AO + Roughness + Metallic OR ORM**
- **Image metadata** (Pillow):
  - resolution checks (power-of-two warnings)
  - max texture size warnings/errors
  - channel sanity (alpha on ORM/Normal, grayscale BaseColor)
  - extension expectations (VFX profile allows EXR more broadly)
- **ORM packed checks**:
  - must be RGB (3 channels)
  - warns on alpha
  - warns if channels appear identical / flat (likely not packed correctly)

### Auto-fix (Optional)
- Rename to studio-friendly format: `Asset_MapType.ext`
- Collision-safe: never overwrites, uses `_fixedN` suffix
- Batch rename is explicitly opt-in

### Reporting
- Export `report.json`
- Export `report.html` (no-deps HTML)
- Batch scan produces a `batch_report.json`

### Profiles
- **Unreal**: packed ORM required  
- **Unity**: separate maps or ORM allowed  
- **VFX**: more permissive (EXR allowed)  

---

## Naming Conventions

Supported patterns:
- `Asset_MapType.ext`
- `Asset_MapType_v###.ext` (version optional)

Examples:
- `CrateA_BaseColor.png`
- `CrateA_Normal.png`
- `CrateA_ORM_v003.tif`

Packed ORM convention:
- **R** = Ambient Occlusion  
- **G** = Roughness  
- **B** = Metallic  

---

## Installation

### Requirements
- Python 3.10+ recommended
- PySide6, Pillow, pytest (dev)

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
# source .venv/bin/activate
pip install -r requirements.txt
```

---

## Run

```bash
python main.py
```

---

## Usage

### Single folder scan
1. **Browse…** select an export folder
2. Choose **Profile** (Unreal / Unity / VFX)
3. Click **Scan Selected**
4. Review results per asset
5. Export JSON/HTML reports

### Batch scan
1. Add folders using **Add Folder**
2. Click **Scan All**
3. Optionally enable:
   - **Auto-fix naming** (renames files)
   - **Batch can rename** (allows renaming during Scan All)
4. Export batch summary JSON

### Watch mode (optional)
Enable **Watch folders** to auto-rescan on changes (best-effort, debounced).

---

## Output

For each scanned folder:
```
<export_folder>/
  reports/
    report.json
    report.html
```

For batch scan export:
```
<selected_folder or home>/reports/
  batch_report.json
```

---

## Demo Data (optional)

Generate valid tiny textures so metadata checks always work:

```bash
python demo/make_demo_textures.py
```

---

## Troubleshooting

**Pillow “Unsupported image format” on PNG/TIF**
- The file may be empty/corrupt or not actually an image (wrong extension).
- Try opening it in an image viewer or re-export from Substance Painter.

**ORM exists but tool says AO/Roughness/Metallic missing**
- Ensure filename parses as ORM: `Asset_ORM.png` (or `Asset_ORM_v###.png`)
- Confirm it appears under “Maps (by type)” and not “Naming issues”

**Watch mode doesn’t detect changes**
- File system watching behavior varies by OS.
- Use **Scan All** manually if needed.

---

## Tests

```bash
pytest -q
```

---

## License
MIT
