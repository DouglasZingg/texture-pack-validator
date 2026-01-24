# Texture Pack Validator (Project 7)

Standalone Python + PySide6 utility that validates Substance Painter / game-ready texture exports and produces severity-based QA reports.

**Targets:** Pipeline Developer / Tools / Technical Artist  
**Use cases:** Unreal/Unity texture delivery, VFX asset lookdev handoff, texture library QA

---

## Quick Start (Windows CMD)

1) Download / clone the repo  
2) Run the setup script:

```bat
setup.bat
```

3) Launch the app:

```bat
python main.py
```

---

## Quick Start (macOS/Linux)

```bash
chmod +x setup.sh
./setup.sh
python main.py
```

---

## What this tool checks

### Required maps (profile-aware)
- **All profiles:** BaseColor + Normal required
- **Unreal:** packed **ORM** required (AO/Roughness/Metallic)
- **Unity/VFX:** requires **AO + Roughness + Metallic** OR **ORM**

### Image metadata (Pillow)
- resolution + power-of-two warnings
- max texture size warnings/errors
- channel sanity checks
- extension expectations (VFX allows EXR more broadly)

### ORM packed validation
- must be RGB (3 channels)
- warns on alpha
- warns if channels look flat/identical

---

## Usage

### Single folder scan
1. **Browse…** select an export folder (demo\make_demo_textures.py will make sample textures)
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

Batch scan export:
```
<selected_folder or home>/reports/
  batch_report.json
```

---

## Tests

Install dev requirements and run:

```bash
pip install -r requirements-dev.txt
pytest -q
```

(Or choose "Yes" when `setup.bat` asks to install dev deps + run tests.)

---

## Troubleshooting

**Pillow “Unsupported image format” on PNG/TIF**
- The file may be empty/corrupt or not actually an image (wrong extension).
- Re-export from Substance Painter.

**ORM exists but tool says AO/Roughness/Metallic missing**
- Ensure filename parses as ORM: `Asset_ORM.png` (or `Asset_ORM_v###.png`)
- Confirm it appears under “Maps (by type)” and not “Naming issues”

---

## License
MIT
