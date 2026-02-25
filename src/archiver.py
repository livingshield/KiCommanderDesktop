import os
import zipfile
import threading
from PySide6.QtCore import QObject, Signal, QThread

try:
    import py7zr
except ImportError:
    py7zr = None

class ArchiveWorker(QObject):
    progress = Signal(int, str)
    finished = Signal(bool, str)

    def __init__(self, sources, target_archive, archive_type):
        super().__init__()
        self.sources = sources
        self.target_archive = target_archive
        self.archive_type = archive_type.lower()
        self._is_running = True

    def run(self):
        try:
            if self.archive_type == 'zip':
                self._create_zip()
            elif self.archive_type == '7z':
                if not py7zr:
                    self.finished.emit(False, "py7zr library is not installed.")
                    return
                self._create_7z()
            else:
                self.finished.emit(False, f"Unsupported archive type for creation: {self.archive_type}")
        except Exception as e:
            self.finished.emit(False, str(e))

    def _create_zip(self):
        with zipfile.ZipFile(self.target_archive, 'w', zipfile.ZIP_DEFLATED) as zf:
            total_files = self._count_files(self.sources)
            current_count = 0
            
            for source in self.sources:
                if not self._is_running: break
                
                if os.path.isdir(source):
                    for root, dirs, files in os.walk(source):
                        for file in files:
                            if not self._is_running: break
                            full_path = os.path.join(root, file)
                            rel_path = os.path.relpath(full_path, os.path.dirname(source))
                            zf.write(full_path, rel_path)
                            current_count += 1
                            self.progress.emit(int((current_count / total_files) * 100), f"Archiving {file}...")
                else:
                    zf.write(source, os.path.basename(source))
                    current_count += 1
                    self.progress.emit(int((current_count / total_files) * 100), f"Archiving {os.path.basename(source)}...")
            
        self.finished.emit(True, f"Archive created: {os.path.basename(self.target_archive)}")

    def _create_7z(self):
        with py7zr.SevenZipFile(self.target_archive, 'w') as sz:
            total_files = self._count_files(self.sources)
            current_count = 0
            
            for source in self.sources:
                if not self._is_running: break
                
                if os.path.isdir(source):
                    # py7zr write_all handles recursion, but we do it manually for progress
                    for root, dirs, files in os.walk(source):
                        for file in files:
                            if not self._is_running: break
                            full_path = os.path.join(root, file)
                            rel_path = os.path.relpath(full_path, os.path.dirname(source))
                            sz.write(full_path, rel_path)
                            current_count += 1
                            self.progress.emit(int((current_count / total_files) * 100), f"Archiving {file}...")
                else:
                    sz.write(source, os.path.basename(source))
                    current_count += 1
                    self.progress.emit(int((current_count / total_files) * 100), f"Archiving {os.path.basename(source)}...")

        self.finished.emit(True, f"Archive created: {os.path.basename(self.target_archive)}")

    def _count_files(self, sources):
        count = 0
        for s in sources:
            if os.path.isdir(s):
                for _, _, files in os.walk(s):
                    count += len(files)
            else:
                count += 1
        return max(1, count)

    def stop(self):
        self._is_running = False

class ArchiveThread(QThread):
    def __init__(self, sources, target_archive, archive_type):
        super().__init__()
        self.worker = ArchiveWorker(sources, target_archive, archive_type)
        self.worker.moveToThread(self)
        self.started.connect(self.worker.run)

    def stop(self):
        self.worker.stop()
        self.wait()
