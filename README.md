# Photo Date Tools

Two scripts to change photo EXIF dates and filesystem timestamps (created/modified) for JPG/PNG/WEBP files.

- **`date_modife.py`** — set a fully custom date (day/month/year) per file or for a whole batch.
- **`date_modife_only_year.py`** — change only the year, keeping month/day/time as-is.

## Requirements

- Python 3.9+
- Pillow

```bash
pip install Pillow
```

Windows-only feature: both scripts also rewrite the file's **Creation Time** (not just Modified) via the `kernel32` API. On Linux/macOS this part is skipped automatically — only EXIF and Modified/Accessed timestamps are changed.

## What changed from the original version

Both scripts had two issues that are now fixed:

1. **JPEG quality loss on every run.** Re-saving a JPEG without specifying `quality` makes Pillow re-compress it at its default (75), silently degrading the image — and this stacked with every re-run. Both scripts now use `quality="keep"`, which re-saves JPEG without re-compression.
2. **One bad input crashed the whole batch.** A typo in the date/year prompt (`datetime.strptime`/`int()`) used to raise an exception and stop the script with a traceback, even mid-batch. Both scripts now re-prompt on invalid input instead of crashing.

Script-specific fixes:

- **`date_modife_only_year.py`**: moving a photo taken on **Feb 29** to a non-leap year used to crash with `ValueError`. It now falls back to Feb 28 for that file and continues with the rest of the batch (with an OK/Failed count printed at the end).
- **`date_modife_only_year.py`**: in `"all"` mode, if a `<folder>_copy` already exists in Downloads, it used to be deleted silently. It now asks for confirmation before deleting.

## Known limitation (not fixed, by design)

PNG/WEBP EXIF support in Pillow is partial and inconsistent across files. If EXIF writing fails for a PNG/WEBP, the script prints `[EXIF] Failed for ...` but still updates the filesystem timestamps (Modified/Created) — so the file's date in Explorer changes even if the EXIF tag inside the file doesn't. This is a Pillow limitation, not something fixable in the script.

## Usage

### date_modife.py

```bash
python date_modife.py
```

Prompts:
1. `Enter the path to the file or folder with photos:` — a single file or a folder
2. `Select mode: "single" - per file, "all" - bulk, one date for all:`
   - `single` — asks for a date (`dd/mm/yyyy`) separately for each file, shows current EXIF date for reference
   - `all` — asks once, applies the same date to every file in the folder

### date_modife_only_year.py

```bash
python date_modife_only_year.py
```

Prompts:
1. `Enter path to file or folder:`
2. `Mode: 'single' or 'all':`
   - `single` — changes the year of files in place
   - `all` (folder only) — **copies the entire folder** to `~/Downloads/<foldername>_copy` first, and works on the copy; the original folder is untouched
3. `Enter new year (YYYY):` — applies to all matched files, keeping month/day/time unchanged (except Feb 29 → Feb 28 fallback as noted above)

## Supported formats

`.jpg`, `.jpeg`, `.png`, `.webp`

## Notes

- `date_modife.py` and `date_modife_only_year.py` in `single` mode edit files **in place** — back up originals first if unsure.
- `date_modife_only_year.py` in `all` mode is the safer option since it always works on a copy in Downloads.
