import os
import time
import math
from PySide6.QtCore import QThread, Signal, QObject

class FileInfo:
    def __init__(self, name, ext, size, date, is_dir, full_path, size_bytes=0, mtime=0):
        self.name = name
        self.ext = ext
        self.size = size
        self.date = date
        self.is_dir = is_dir
        self.full_path = full_path
        # Raw values for numeric sorting
        self._size_bytes = size_bytes
        self._mtime = mtime

class ScanWorker(QObject):
    finished = Signal(list)
    error = Signal(str)

    def __init__(self, path):
        super().__init__()
        self.path = path

    def run(self):
        try:
            files = []
            # Add [..] entry if not at root
            parent = os.path.dirname(self.path)
            if parent != self.path:
                files.append(FileInfo("..", "", "<DIR>", "", True, parent, 0, 0))

            with os.scandir(self.path) as it:
                for entry in it:
                    try:
                        stats = entry.stat()
                        is_dir = entry.is_dir()
                        name = entry.name
                        mtime = stats.st_mtime
                        
                        if is_dir:
                            ext = ""
                            size_str = "<DIR>"
                            size_bytes = 0
                        else:
                            name_parts = os.path.splitext(name)
                            ext = name_parts[1].lstrip('.')
                            size_bytes = stats.st_size
                            size_str = self.format_size(size_bytes)

                        date_str = time.strftime('%d.%m.%Y %H:%M', time.localtime(mtime))
                        
                        files.append(FileInfo(
                            name, ext, size_str, date_str, is_dir, entry.path,
                            size_bytes, mtime
                        ))
                    except (PermissionError, OSError):
                        continue  # Skip files we can't access
            
            # Initial sort: Directories first, then by name
            files.sort(key=lambda x: (x.name != "..", not x.is_dir, x.name.lower()))
            self.finished.emit(files)
            
        except Exception as e:
            self.error.emit(str(e))

    @staticmethod
    def format_size(size_bytes):
        if size_bytes == 0: return "0 B"
        size_name = ("B", "KB", "MB", "GB", "TB")
        i = int(math.floor(math.log(size_bytes, 1024)))
        p = math.pow(1024, i)
        s = round(size_bytes / p, 2)
        return f"{s} {size_name[i]}"

class VfsWorker(QObject):
    finished = Signal(list)
    error = Signal(str)

    def __init__(self, vfs, inner_path):
        super().__init__()
        self.vfs = vfs
        self.inner_path = inner_path

    def run(self):
        try:
            files = self.vfs.list_dir(self.inner_path)
            # Sorting is usually handled by the VFS or the Model, 
            # but we can ensure consistent baseline here.
            files.sort(key=lambda x: (not x.is_dir, x.name.lower()))
            self.finished.emit(files)
        except Exception as e:
            self.error.emit(str(e))

class VfsThread(QThread):
    def __init__(self, vfs, inner_path):
        super().__init__()
        self.worker = VfsWorker(vfs, inner_path)
        self.worker.moveToThread(self)
        self.started.connect(self.worker.run)
        self.worker.finished.connect(self.quit)
        self.worker.error.connect(self.quit)

class ScanThread(QThread):
    def __init__(self, path):
        super().__init__()
        self.worker = ScanWorker(path)
        self.worker.moveToThread(self)
        self.started.connect(self.worker.run)
        self.worker.finished.connect(self.quit)
        self.worker.error.connect(self.quit)
