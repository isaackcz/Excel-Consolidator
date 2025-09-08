## Excel Consolidator

### Overview
Excel Consolidator is a modern, offline desktop application that merges and summarizes data from many Excel workbooks into a single, formatted output based on your chosen template. It preserves your template’s styles (colors, borders, fonts, column widths, row heights) while summing numeric values across source files. It also adds cell-level audit comments so you can hover in Excel to see which files contributed to each total.

Built with Python and PyQt5, it runs as a GUI app and can be packaged into a standalone Windows executable.

### Key Features
- **Template‑driven output**: Uses your selected workbook as the style/structure template.
- **Automatic summation**: Sums numeric values across all `.xlsx` files in a folder.
- **Formatting preserved**: Keeps borders, fills, fonts, merged cells, column widths, and row heights from the template.
- **Interactive verification**: Writes Excel comments on consolidated cells showing per‑file contributions and applies a subtle orange border to indicate consolidated values.
- **Contribution index**: Adds a `Contributions` sheet with a filterable table of cell → file → contribution and hyperlinks from consolidated cells back to their detailed rows.
- **Progress feedback**: Non‑blocking background worker with progress bar and processed file list.
- **Advanced settings (dialog)**: Fine‑tune data processing, file handling, validation, and performance preferences.

### How It Works
1. You select a formatted Excel template (any standard `.xlsx`).
2. You select a folder with source workbooks. The app loads each workbook (skipping temp files like `~$...`).
3. Numeric cells are summed by address (e.g., `C12`) across files.
4. The combined result is written into the template’s corresponding cells.
5. Each consolidated cell gets an audit comment listing file contributions; consolidated cells get an orange border.
6. The result is saved as a date‑stamped file like `Consolidated - Jan 01 2025.xlsx` in your chosen folder. If your template is `.xlsm`, the output preserves macros (`.xlsm`). A `Contributions` sheet provides a filterable breakdown.

### Quick Start (Windows EXE)
1. Download the latest `Excel Consolidate.exe` from the `dist/` folder or your release channel.
2. Double‑click to run (no installation required).
3. Follow the on‑screen steps:
   - Step 1: Select the template Excel file.
   - Step 2: Select the folder containing the `.xlsx` files to consolidate.
   - Step 3: Select the save location.
   - Optional: Open “Advanced Settings” to configure behavior.
4. Click “Run Consolidation”. When finished, open the consolidated file directly from the success dialog.

### Running From Source
- **Prerequisites**:
  - Python 3.9+ (Windows recommended; works cross‑platform when running from source)
  - Microsoft Excel (optional, for viewing the result)

- **Install dependencies**:
  ```bash
  python -m venv .venv
  .venv\\Scripts\\activate
  pip install --upgrade pip
  pip install pyqt5 openpyxl pandas "xlrd<2.0" pyinstaller
  ```

- **Start the app**:
  ```bash
  python main.py
  ```

### Packaging a Standalone EXE (PyInstaller)
This repository includes `Excel Consolidate.spec` configured to bundle the app icon and logo.

- Build with the spec (recommended):
  ```bash
  pyinstaller "Excel Consolidate.spec"
  ```

- Or build directly from the script:
  ```bash
  pyinstaller --noconfirm \
    --noconsole \
    --name "Excel Consolidate" \
    --icon resources/app.ico \
    --add-data "resources/app.ico;resources" \
    --add-data "resources/logo.png;resources" \
    main.py
  ```

Artifacts will appear under `build/` and `dist/`. The portable app is `dist/Excel Consolidate.exe`.

### Advanced Settings (Summary)
Open “Advanced Settings” before running to customize behavior. Tabs include:
- **Data Processing**
  - Auto‑convert text that looks like numbers to numeric (e.g., `'1,234' → 1234`).
  - Convert percentages (e.g., `'50%' → 0.5`).
- **File Handling**
  - Formats: `.xlsx` (always). Optional `.xls` when enabled.
  - Note: `.csv` support is currently disabled in this build.
  - Duplicate/temporary file safeguards (skips `~$` temp files).
- **Validation**
  - Options to validate structure, data types, and value ranges (when enabled).
- **Performance & Safety**
  - Optional backup creation in the save directory.

Note: Some analysis/report‑generation features are preview‑only in this build; the dialog will indicate if a function is disabled.

### Output
- **File name**: `Consolidated - <Mon DD YYYY>.xlsx` (or `.xlsm` if the template was `.xlsm`).
- **Sheet**: Your template’s active sheet is used for writing totals.
- **Comments**: Hover on consolidated cells to see a per‑file breakdown.
- **Visual cues**: Orange border on consolidated cells.
- **Contributions sheet**: `Contributions` with filterable columns `Cell`, `File Name`, `Contribution`. Consolidated cells include hyperlinks back to their first detailed row.

### Supported Input
- `.xlsx` workbooks (primary)
- Optional `.xls` (requires `xlrd<2.0`, enable in Advanced Settings)
- `.csv` is not supported in this build.

The app skips temporary Excel lock files (e.g., `~$Workbook.xlsx`).

### Tips & Best Practices
- Use a clean, fully formatted template. The app preserves template formatting.
- Keep source files structurally consistent so cell addresses align meaningfully.
- Avoid placing totals in the source files where the app scans for values; overall totals are best left to the consolidated output.

### Troubleshooting
- **Nothing happens when I click Run**: Ensure all three steps are completed (template, source folder, save folder).
- **No files found**: Only `.xlsx` files are included by default. Enable `.xls` in Advanced Settings if needed.
- **Cell comments not visible**: In Excel, enable “Show/Hide Comments/Notes”. This app writes classic comments/notes.
- **Antivirus flags the EXE**: Build locally from source with PyInstaller as shown above; code‑sign in enterprise environments.
- **Unsupported or corrupted files**: Ensure each workbook opens in Excel and isn’t password‑protected or corrupted.

### Development Notes
- GUI: PyQt5 (`QWidget` app with modern stylesheet) and a background `QThread` worker for consolidation.
- Excel I/O: `openpyxl` for `.xlsx` read/write, `xlrd<2.0` for legacy `.xls`.
- Packaging: PyInstaller using `Excel Consolidate.spec` with embedded resources in `resources/`.

### Folder Structure
```text
resources/           # Icons and images used by the GUI
build/               # PyInstaller intermediate build artifacts
dist/                # Packaged executable output
main.py              # Application code (GUI + worker)
Excel Consolidate.spec  # PyInstaller spec
```

### License
© 2025 Izak. All rights reserved.

If you need an open‑source license, please add one explicitly (e.g., MIT) and update this section.

### Changelog
- 2025‑Q2: Modernized UI, added contribution comments and optional `Contributions` sheet, improved Advanced Settings.

### Support
For issues or feature requests, please open a ticket with:
- Steps to reproduce
- Template file description (do not upload sensitive data)
- Sample file names and counts
- Expected vs actual behavior

### Acknowledgements
Built with Python, PyQt5, openpyxl, pandas, and PyInstaller.