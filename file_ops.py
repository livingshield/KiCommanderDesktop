import os
import shutil
from PySide6.QtCore import QObject, Signal, QThread

class FileOperationWorker(QObject):
    finished = Signal(bool, str) # Success, Message
    progress = Signal(int, str) # Progress %, Current file

    def __init__(self, op_type, sources, target=None):
        super().__init__()
        self.op_type = op_type # 'copy', 'move', 'delete', 'mkdir'
        self.sources = sources # List of paths
        self.target = target # Target directory

    def run(self):
        try:
            if self.op_type == 'mkdir':
                os.makedirs(self.sources[0], exist_ok=False)
                self.finished.emit(True, f"Folder created: {os.path.basename(self.sources[0])}")
                return

            total = len(self.sources)
            for i, src in enumerate(self.sources):
                name = os.path.basename(src)
                if self.op_type == 'copy':
                    dst = os.path.join(self.target, name)
                    if os.path.isdir(src):
                        shutil.copytree(src, dst)
                    else:
                        shutil.copy2(src, dst)
                
                elif self.op_type == 'move':
                    dst = os.path.join(self.target, name)
                    shutil.move(src, dst)
                
                elif self.op_type == 'delete':
                    if os.path.isdir(src):
                        shutil.rmtree(src)
                    else:
                        os.remove(src)
                
                self.progress.emit(int((i + 1) / total * 100), name)

            self.finished.emit(True, f"Operation {self.op_type} completed successfully.")
        except Exception as e:
            self.finished.emit(False, str(e))

class FileOpThread(QThread):
    def __init__(self, op_type, sources, target=None):
        super().__init__()
        self.worker = FileOperationWorker(op_type, sources, target)
        self.worker.moveToThread(self)
        self.started.connect(self.worker.run)
        self.worker.finished.connect(self.quit)
