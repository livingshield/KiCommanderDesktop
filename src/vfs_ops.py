import os
import shutil
import tempfile
import time
from PySide6.QtCore import QObject, Signal, QThread

class VfsOperationWorker(QObject):
    finished = Signal(bool, str)
    progress = Signal(int, str)
    # Signal to ask main thread for overwrite: (src_info, target_info) -> returns string ('overwrite', 'skip', 'cancel')
    query_overwrite = Signal(object, object) 

    def __init__(self, op_type, sources, source_vfs=None, target_vfs=None, target_path=None):
        super().__init__()
        self.op_type = op_type # 'copy', 'move', 'delete'
        self.sources = sources # List of FileInfo or full paths
        self.source_vfs = source_vfs
        self.target_vfs = target_vfs
        self.target_path = target_path # Base path for target
        self._overwrite_result = None # Internal storage for query result

    def set_overwrite_result(self, result):
        self._overwrite_result = result

    def get_target_info(self, name):
        """Helper to get FileInfo for an existing file at target location."""
        try:
            if self.target_vfs:
                # Need to list target dir to find the file
                files = self.target_vfs.list_dir(self.target_path)
                for f in files:
                    if f.name == name: return f
                return None
            else:
                target_full = os.path.join(self.target_path, name)
                if os.path.exists(target_full):
                    import time
                    stats = os.stat(target_full)
                    is_dir = os.path.isdir(target_full)
                    mtime = stats.st_mtime
                    date_str = time.strftime('%d.%m.%Y %H:%M', time.localtime(mtime))
                    size_bytes = stats.st_size
                    # Generic format_size if needed, but we'll use raw for compare
                    from fs_worker import FileInfo
                    return FileInfo(name, "", "", date_str, is_dir, target_full, size_bytes, mtime)
                return None
        except:
            return None

    def run(self):
        try:
            if self.op_type == 'mkdir':
                target_vfs = self.target_vfs if self.target_vfs else self.source_vfs
                if target_vfs:
                    target_vfs.mkdir(self.sources[0])
                else:
                    os.makedirs(self.sources[0], exist_ok=True)
                self.finished.emit(True, f"Folder created: {os.path.basename(self.sources[0])}")
                return

            if self.op_type == 'rename':
                # For rename, sources is a list of (FileInfo/Path, NewName)
                total = len(self.sources)
                for i, (src_info, new_name) in enumerate(self.sources):
                    if hasattr(src_info, 'full_path'):
                        src_path = src_info.full_path
                        is_dir = src_info.is_dir
                        old_dir = os.path.dirname(src_path)
                    else:
                        src_path = src_info
                        is_dir = os.path.isdir(src_path)
                        old_dir = os.path.dirname(src_path)
                    
                    self.progress.emit(int(i / total * 100), os.path.basename(src_path))
                    
                    if self.source_vfs:
                        # VFS rename: usually it's move from old_path to new_full_path
                        new_full = os.path.join(old_dir, new_name).replace("\\", "/")
                        # Check if provider has rename, otherwise use move
                        if hasattr(self.source_vfs, 'rename'):
                            self.source_vfs.rename(src_path, new_full)
                        else:
                            self.source_vfs.move(src_path, new_full)
                    else:
                        # Local rename
                        new_full = os.path.join(old_dir, new_name)
                        os.rename(src_path, new_full)
                
                self.finished.emit(True, f"Multi-Rename completed for {total} files.")
                return

            total = len(self.sources)
            for i, src_info in enumerate(self.sources):
                # source path might be FileInfo or string
                if hasattr(src_info, 'full_path'):
                    src_path = src_info.full_path
                    name = src_info.name
                    is_dir = src_info.is_dir
                else:
                    src_path = src_info
                    name = os.path.basename(src_path)
                    is_dir = os.path.isdir(src_path)

                if self.op_type == 'delete':
                    if self.source_vfs:
                        self.source_vfs.delete_item(src_path, is_dir)
                    else:
                        if is_dir: shutil.rmtree(src_path)
                        else: os.remove(src_path)
                
                elif self.op_type in ['copy', 'move']:
                    # Check for existing target
                    target_info = self.get_target_info(name)
                    if target_info:
                        # Ask UI (blocking-ish via signal/slot or internal loop)
                        self._overwrite_result = None
                        
                        # Ensure we pass something with .size and .date if possible
                        from fs_worker import FileInfo
                        if not hasattr(src_info, 'size'):
                            # It's likely a local path string
                            stats = os.stat(src_path)
                            mtime = stats.st_mtime
                            d_str = time.strftime('%d.%m.%Y %H:%M', time.localtime(mtime))
                            from fs_worker import ScanWorker
                            s_str = ScanWorker.format_size(stats.st_size)
                            src_meta = FileInfo(name, "", s_str, d_str, is_dir, src_path, stats.st_size, mtime)
                        else:
                            src_meta = src_info

                        self.query_overwrite.emit(src_meta, target_info)
                        
                        # Wait for UI response
                        start_wait = time.time()
                        while self._overwrite_result is None:
                            time.sleep(0.05)
                            if time.time() - start_wait > 300: # 5 min timeout
                                raise Exception("Overwrite query timed out")

                        if self._overwrite_result == 'skip':
                            continue
                        elif self._overwrite_result == 'cancel':
                            self.finished.emit(True, "Operation cancelled by user.")
                            return

                    # Determine source and target type
                    # Case 1: VFS -> Local
                    if self.source_vfs and not self.target_vfs:
                        # Extract/Download
                        self.source_vfs.extract_file(src_path, self.target_path)
                    
                    # Case 2: Local -> VFS
                    elif not self.source_vfs and self.target_vfs:
                        # Upload
                        remote_dest = os.path.join(self.target_path, name).replace("\\", "/")
                        self.target_vfs.upload_file(src_path, remote_dest)
                    
                    # Case 3: VFS -> VFS
                    elif self.source_vfs and self.target_vfs:
                        # Download to temp then upload
                        with tempfile.TemporaryDirectory() as tmp:
                            local_tmp = self.source_vfs.extract_file(src_path, tmp)
                            if local_tmp:
                                remote_dest = os.path.join(self.target_path, name).replace("\\", "/")
                                self.target_vfs.upload_file(local_tmp, remote_dest)
                    
                    # Case 4: Local -> Local (handled by FileOpThread, but we can support here too)
                    else:
                        dst = os.path.join(self.target_path, name)
                        if self.op_type == 'copy':
                            if is_dir: 
                                if os.path.exists(dst): shutil.rmtree(dst)
                                shutil.copytree(src_path, dst)
                            else: shutil.copy2(src_path, dst)
                        else: # move
                            if os.path.exists(dst):
                                if os.path.isdir(dst): shutil.rmtree(dst)
                                else: os.remove(dst)
                            shutil.move(src_path, dst)

                    # For 'move' from VFS, we delete the source after copy
                    if self.op_type == 'move' and self.source_vfs:
                        self.source_vfs.delete_item(src_path, is_dir)

                self.progress.emit(int((i + 1) / total * 100), name)

            self.finished.emit(True, f"VFS Operation {self.op_type} completed.")
        except Exception as e:
            self.finished.emit(False, str(e))

class VfsOpThread(QThread):
    def __init__(self, op_type, sources, source_vfs=None, target_vfs=None, target_path=None):
        super().__init__()
        self.worker = VfsOperationWorker(op_type, sources, source_vfs, target_vfs, target_path)
        self.worker.moveToThread(self)
        self.started.connect(self.worker.run)
        self.worker.finished.connect(self.quit)
