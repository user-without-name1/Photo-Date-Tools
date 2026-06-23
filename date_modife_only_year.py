import os
import shutil
import platform
from pathlib import Path
from PIL import Image
from PIL.ExifTags import TAGS
from datetime import datetime

if platform.system() == "Windows":
    import ctypes
    from ctypes import wintypes

    def set_creation_time(path, dt):
        FILE_WRITE_ATTRIBUTES = 0x100
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

        handle = kernel32.CreateFileW(
            str(path),
            FILE_WRITE_ATTRIBUTES,
            0,
            None,
            3,
            0,
            None,
        )

        if handle == -1:
            return

        wintime = int((dt - datetime(1601, 1, 1)).total_seconds() * 10**7)
        ctime = wintypes.FILETIME(wintime & 0xFFFFFFFF, wintime >> 32)

        kernel32.SetFileTime(handle, ctypes.byref(ctime), None, None)
        kernel32.CloseHandle(handle)


def get_photo_datetime(file_path):
    try:
        img = Image.open(file_path)
        exif = img.getexif()

        for tag_id, value in exif.items():
            tag = TAGS.get(tag_id, tag_id)
            if tag in ["DateTimeOriginal", "DateTime", "DateTimeDigitized"]:
                return datetime.strptime(value, "%Y:%m:%d %H:%M:%S")
    except Exception:
        pass

    # fallback — дата файла
    ts = file_path.stat().st_mtime
    return datetime.fromtimestamp(ts)


def safe_replace_year(dt, new_year):
    """
    dt.replace(year=...) raises ValueError for Feb 29 moved to a non-leap year.
    Fall back to Feb 28 in that case instead of crashing the whole batch.
    """
    try:
        return dt.replace(year=new_year)
    except ValueError:
        return dt.replace(year=new_year, month=2, day=28)


def update_year_keep_rest(file_path, new_year):
    original_dt = get_photo_datetime(file_path)

    new_dt = safe_replace_year(original_dt, new_year)

    # --- EXIF ---
    try:
        img = Image.open(file_path)
        exif = img.getexif()
        exif_date_str = new_dt.strftime("%Y:%m:%d %H:%M:%S")

        for tag_id, tag_name in TAGS.items():
            if tag_name in ["DateTime", "DateTimeOriginal", "DateTimeDigitized"]:
                exif[tag_id] = exif_date_str

        save_kwargs = {"exif": exif}
        if img.format == "JPEG":
            # Preserve original quality — without this, every run silently
            # re-compresses the JPEG at Pillow's default quality (75).
            save_kwargs["quality"] = "keep"

        img.save(file_path, **save_kwargs)
    except Exception as e:
        print(f"[EXIF] Failed for {file_path.name}: {e}")

    # --- File system dates ---
    mod_time = new_dt.timestamp()
    os.utime(file_path, (mod_time, mod_time))

    if platform.system() == "Windows":
        try:
            set_creation_time(file_path, new_dt)
        except Exception:
            pass

    print(f"[OK] {file_path.name}: {original_dt} -> {new_dt}")


def copy_folder_to_downloads(folder_path):
    downloads = Path.home() / "Downloads"
    new_folder = downloads / f"{folder_path.name}_copy"

    if new_folder.exists():
        confirm = input(
            f"'{new_folder}' already exists and will be deleted. Continue? (y/n): "
        ).strip().lower()
        if confirm != "y":
            print("Aborted.")
            sys.exit(0)
        shutil.rmtree(new_folder)

    shutil.copytree(folder_path, new_folder)
    return new_folder


def prompt_year(message):
    """Keeps asking until a plausible 4-digit year is entered."""
    while True:
        raw = input(message).strip()
        if raw.isdigit() and 1900 <= int(raw) <= 2100:
            return int(raw)
        print("Invalid year. Enter a 4-digit year between 1900 and 2100.")


def process(path, mode):
    path = Path(path)

    if path.is_file():
        files = [path]
    elif path.is_dir():
        files = [f for f in path.glob("*")
                 if f.suffix.lower() in [".jpg", ".jpeg", ".png", ".webp"]]
    else:
        print("Invalid path.")
        return

    if not files:
        print("No photos found.")
        return

    if mode == "all" and path.is_dir():
        path = copy_folder_to_downloads(path)
        files = [f for f in path.glob("*")
                 if f.suffix.lower() in [".jpg", ".jpeg", ".png", ".webp"]]
        print(f"Working with copy: {path}")

    new_year = prompt_year("Enter new year (YYYY): ")

    ok_count = 0
    fail_count = 0
    for f in files:
        try:
            update_year_keep_rest(f, new_year)
            ok_count += 1
        except Exception as e:
            print(f"[FAIL] {f.name}: {e}")
            fail_count += 1

    print(f"\nDone. OK: {ok_count}, Failed: {fail_count}")


if __name__ == "__main__":
    import sys

    path = input("Enter path to file or folder: ").strip()
    mode = input("Mode: 'single' or 'all': ").strip().lower()

    if mode not in ["single", "all"]:
        mode = "single"

    process(path, mode)
