import os
import string
import platform
from PySide6.QtCore import QStandardPaths

def get_drives():
    drives = []
    if platform.system() == "Windows":
        # Check for drives A-Z
        for letter in string.ascii_uppercase:
            drive = f"{letter}:\\"
            if os.path.exists(drive):
                drives.append(drive)
    else:
        # For Linux/Mac, just root for now, could expand to /media or /Volumes
        drives.append("/")
    return drives

def get_quick_links():
    links = [
        {"name": "Desktop", "path": QStandardPaths.writableLocation(QStandardPaths.DesktopLocation), "icon": "fa5s.desktop"},
        {"name": "Downloads", "path": QStandardPaths.writableLocation(QStandardPaths.DownloadLocation), "icon": "fa5s.download"},
        {"name": "Documents", "path": QStandardPaths.writableLocation(QStandardPaths.DocumentsLocation), "icon": "fa5s.file-alt"},
        {"name": "Pictures", "path": QStandardPaths.writableLocation(QStandardPaths.PicturesLocation), "icon": "fa5s.image"},
        {"name": "Music", "path": QStandardPaths.writableLocation(QStandardPaths.MusicLocation), "icon": "fa5s.music"},
        {"name": "Videos", "path": QStandardPaths.writableLocation(QStandardPaths.MoviesLocation), "icon": "fa5s.video"},
    ]
    # Filter out empty paths or non-existent ones
    return [l for l in links if l["path"] and os.path.exists(l["path"])]
