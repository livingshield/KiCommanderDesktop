import uuid
from PySide6.QtCore import QObject, Signal, QThread
from vfs_ops import VfsOperationWorker

class QueueItem:
    def __init__(self, op_type, sources, target_path, source_vfs=None, target_vfs=None):
        self.id = str(uuid.uuid4())
        self.op_type = op_type
        self.sources = sources
        self.target_path = target_path
        self.source_vfs = source_vfs
        self.target_vfs = target_vfs
        self.status = "Waiting" # Waiting, Running, Completed, Error, Paused
        self.progress = 0
        self.current_file = ""
        self.error_msg = ""

class QueueManager(QObject):
    queue_updated = Signal()
    item_finished = Signal(str, bool, str) # id, success, message
    query_overwrite = Signal(str, object, object) # item_id, src_info, target_info

    _instance = None

    def __init__(self):
        super().__init__()
        self.items = []
        self.current_worker = None
        self.current_thread = None
        self.paused = False

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = QueueManager()
        return cls._instance

    def add_to_queue(self, op_type, sources, target_path, source_vfs=None, target_vfs=None):
        item = QueueItem(op_type, sources, target_path, source_vfs, target_vfs)
        self.items.append(item)
        self.queue_updated.emit()
        self._check_next()
        return item.id

    def _check_next(self):
        if self.current_worker or self.paused:
            return

        for item in self.items:
            if item.status == "Waiting":
                self._start_item(item)
                break

    def _start_item(self, item):
        item.status = "Running"
        self.queue_updated.emit()

        self.current_thread = QThread()
        self.current_worker = VfsOperationWorker(
            item.op_type, item.sources, 
            item.source_vfs, item.target_vfs, item.target_path
        )
        self.current_worker.moveToThread(self.current_thread)
        
        self.current_thread.started.connect(self.current_worker.run)
        self.current_worker.progress.connect(lambda p, f: self._on_progress(item.id, p, f))
        self.current_worker.finished.connect(lambda s, m: self._on_finished(item.id, s, m))
        
        # Forward overwrite queries to the manager, which can then notify UI
        self.current_worker.query_overwrite.connect(
            lambda src, tgt: self.query_overwrite.emit(item.id, src, tgt)
        )
        
        self.current_thread.start()

    def set_overwrite_result(self, item_id, result):
        """Called from UI to resolve a conflict in the queue."""
        if self.current_worker and self.items and any(i.id == item_id for i in self.items if i.status == "Running"):
            self.current_worker.set_overwrite_result(result)

    def _on_progress(self, item_id, progress, current_file):
        for item in self.items:
            if item.id == item_id:
                item.progress = progress
                item.current_file = current_file
                self.queue_updated.emit()
                break

    def _on_finished(self, item_id, success, message):
        for item in self.items:
            if item.id == item_id:
                item.status = "Completed" if success else "Error"
                item.error_msg = "" if success else message
                item.progress = 100
                break
        
        # Clean up thread
        if self.current_thread:
            self.current_thread.quit()
            self.current_thread.wait()
        
        self.current_worker = None
        self.current_thread = None
        
        self.item_finished.emit(item_id, success, message)
        self.queue_updated.emit()
        self._check_next()

    def remove_item(self, item_id):
        # If it's the current one, we'd need to stop the worker first
        # For now, just remove if not running
        self.items = [i for i in self.items if i.id != item_id or i.status == "Running"]
        self.queue_updated.emit()

    def pause_queue(self, paused):
        self.paused = paused
        if not self.paused:
            self._check_next()
        self.queue_updated.emit()
