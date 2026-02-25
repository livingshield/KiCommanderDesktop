import os
import platform
import string
from PySide6.QtCore import QStandardPaths, Qt, Signal
from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QLabel

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

class BreadcrumbsWidget(QWidget):
    path_clicked = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        self.layout.setAlignment(Qt.AlignLeft)

    def set_path(self, path, vfs_type=None):
        # Clear layout
        while self.layout.count():
            item = self.layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not path: return

        # Split path logic
        parts = []
        if not vfs_type:
            path = os.path.normpath(path)
            drive, rest = os.path.splitdrive(path)
            if drive:
                parts.append((drive + "\\", drive + "\\"))
            folders = [f for f in rest.split(os.sep) if f]
            accum = drive + "\\" if drive else ""
            for f in folders:
                accum = os.path.join(accum, f)
                parts.append((f, accum))
        else:
            # VFS path (usually / separated)
            folders = [f for f in path.split("/") if f]
            parts.append(("/", "/"))
            accum = ""
            for f in folders:
                accum += "/" + f
                parts.append((f, accum))

        for i, (name, p) in enumerate(parts):
            btn = QPushButton(name.rstrip("\\/"))
            if not name.strip() or name in ("/", "\\"): 
                btn.setText("/")
            
            btn.setFlat(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton { color: #89b4fa; padding: 2px 4px; border-radius: 4px; border: none; font-size: 11px; }
                QPushButton:hover { background-color: #313244; color: #f5e0dc; }
            """)
            btn.clicked.connect(lambda checked, target=p: self.path_clicked.emit(target))
            self.layout.addWidget(btn)

            if i < len(parts) - 1:
                sep = QLabel("›")
                sep.setStyleSheet("color: #585b70; font-weight: bold;")
                self.layout.addWidget(sep)
        
        self.layout.addStretch()
