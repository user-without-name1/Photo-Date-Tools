import os
import sys
from pathlib import Path
from PIL import Image
from PIL.ExifTags import TAGS
from datetime import datetime
import platform

if platform.system() == "Windows":
    import ctypes
    from ctypes import wintypes

    def set_creation_time(path, dt):
        FILE_WRITE_ATTRIBUTES = 0x100
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        CreateFile = kernel32.CreateFileW
        SetFileTime = kernel32.SetFileTime
        CloseHandle = kernel32.CloseHandle

        handle = CreateFile(str(path), FILE_WRITE_ATTRIBUTES, 0, None, 3, 0, None)
        if handle == -1:
            print(f"Unable to open file {path} to change the creation time.")
            return

        wintime = int((dt - datetime(1601, 1, 1)).total_seconds() * 10**7)
        ctime = wintypes.FILETIME(wintime & 0xFFFFFFFF, wintime >> 32)
        SetFileTime(handle, ctypes.byref(ctime), None, None)
        CloseHandle(handle)


def update_exif_date(file_path, new_date):
    """
    Writes the new date into EXIF tags. Returns True on success, False otherwise.
    JPEG is re-saved with its original quality to avoid silent re-compression loss.
    PNG/WEBP EXIF support in Pillow is partial — failures here are expected and
    do not stop the file's filesystem date from being updated by the caller.
    """
    try:
        img = Image.open(file_path)
        exif = img.getexif()
        exif_date_str = new_date.strftime("%Y:%m:%d %H:%M:%S")
        date_tags = ["DateTime", "DateTimeOriginal", "DateTimeDigitized"]

        for tag_id, tag_name in TAGS.items():
            if tag_name in date_tags:
                exif[tag_id] = exif_date_str

        save_kwargs = {"exif": exif}
        if img.format == "JPEG":
            # Preserve original quality — Pillow defaults to quality=75 on re-save,
            # which silently degrades the image every time this script runs.
            save_kwargs["quality"] = "keep"

        img.save(file_path, **save_kwargs)
        return True
    except Exception as e:
        print(f"[EXIF] Failed to update EXIF for {file_path}: {e}")
        return False


def set_file_dates(file_path, new_date):
    """
    Changes the file system and EXIF date.
    new_date - datetime object
    """
    update_exif_date(file_path, new_date)

    mod_time = new_date.timestamp()
    os.utime(file_path, (mod_time, mod_time))

    if platform.system() == "Windows":
        try:
            set_creation_time(file_path, new_date)
        except Exception as e:
            print(f"[Creation] Failed to change Creation time for {file_path}: {e}")

    print(f"[OK] {file_path} -> {new_date.strftime('%d/%m/%Y')}")


def prompt_date(message):
    """
    Keeps asking until a valid dd/mm/yyyy date is entered.
    Prevents one bad input from crashing the whole batch.
    """
    while True:
        raw = input(message).strip()
        try:
            return datetime.strptime(raw, "%d/%m/%Y")
        except ValueError:
            print("Invalid date format. Expected dd/mm/yyyy, e.g. 24/12/2023.")


def process_photos(path, mode="single"):
    path = Path(path)
    files = []

    if path.is_file():
        files = [path]
    elif path.is_dir():
        files = [
            f
            for f in path.glob("*")
            if f.suffix.lower() in [".jpg", ".jpeg", ".png", ".webp"]
        ]
    else:
        print(f"Path not found: {path}")
        return

    if not files:
        print("No photos found.")
        return

    if mode == "all":
        new_date = prompt_date("Enter a new date for all files (dd/mm/yyyy): ")
        for f in files:
            set_file_dates(f, new_date)
    else:
        for f in files:
            try:
                img = Image.open(f)
                exif = img.getexif()
                current_date = None
                for tag_id, value in exif.items():
                    tag = TAGS.get(tag_id, tag_id)
                    if tag in ["DateTime", "DateTimeOriginal", "DateTimeDigitized"]:
                        current_date = value
                        break
            except Exception:
                current_date = None

            print(f"\nFile: {f.name}")
            print(f"Current date EXIF: {current_date}")
            new_date = prompt_date("Enter a new date (dd/mm/yyyy): ")
            set_file_dates(f, new_date)


if __name__ == "__main__":
    path = input("Enter the path to the file or folder with photos: ").strip()
    mode = (
        input("Select mode: “single” - per file, “all” - bulk, one date for all: ")
        .strip()
        .lower()
    )
    if mode not in ["single", "all"]:
        print("Incorrect mode. Used  'single'.")
        mode = "single"
    process_photos(path, mode)
