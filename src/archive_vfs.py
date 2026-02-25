"""
Archive Virtual File System – browse ZIP/TAR/GZ/7Z/RAR archives as directories.
Provides ArchiveVFS class that returns lists of FileInfo objects
compatible with the existing FileModel.
"""
import os
import zipfile
import tarfile
import time
import logging
from fs_worker import FileInfo

try:
    import py7zr
except ImportError:
    py7zr = None

try:
    import rarfile
except ImportError:
    rarfile = None

ARCHIVE_EXTENSIONS = {
    ".zip", ".tar", ".tar.gz", ".tgz", ".tar.bz2", ".tbz2", ".tar.xz", ".txz",
    ".gz", ".bz2", ".xz", ".7z", ".rar",
}

# Extensions we can actually open
SUPPORTED_EXTENSIONS = {".zip", ".tar", ".tar.gz", ".tgz", ".tar.bz2", ".tbz2", ".tar.xz", ".txz", ".7z", ".rar"}


def is_archive(path: str) -> bool:
    """Check if a file path looks like an archive we can open."""
    lower = path.lower()
    for ext in SUPPORTED_EXTENSIONS:
        if lower.endswith(ext):
            return True
    return False


def _format_size(size: int) -> str:
    if size < 0: return "0 B"
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.0f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


class ArchiveVFS:
    """Virtual file system layer for browsing archive contents."""

    def __init__(self, archive_path: str):
        self.archive_path = archive_path
        self._is_zip = zipfile.is_zipfile(archive_path)
        self._is_tar = tarfile.is_tarfile(archive_path) if not self._is_zip else False
        self._is_7z = False
        self._is_rar = False

        if not self._is_zip and not self._is_tar:
            if py7zr and py7zr.is_7zfile(archive_path):
                self._is_7z = True
            elif rarfile and rarfile.is_rarfile(archive_path):
                self._is_rar = True

    def list_dir(self, inner_path: str = "") -> list:
        """List contents of a directory inside the archive."""
        if self._is_zip:
            return self._list_zip(inner_path)
        elif self._is_tar:
            return self._list_tar(inner_path)
        elif self._is_7z:
            return self._list_7z(inner_path)
        elif self._is_rar:
            return self._list_rar(inner_path)
        return []

    def _list_zip(self, inner_path: str) -> list:
        """List directory contents of a ZIP archive."""
        inner_path = inner_path.strip("/")
        prefix = inner_path + "/" if inner_path else ""
        entries = {}
        try:
            with zipfile.ZipFile(self.archive_path, "r") as zf:
                for info in zf.infolist():
                    name = info.filename.replace("\\", "/")
                    if prefix and not name.startswith(prefix): continue
                    rel = name[len(prefix):]
                    if not rel or rel == "/": continue
                    parts = rel.strip("/").split("/")
                    child_name = parts[0]
                    if child_name in entries: continue

                    is_dir = info.is_dir() or len(parts) > 1
                    if is_dir:
                        fi = FileInfo(child_name, "<DIR>", "<DIR>", "", True, prefix + child_name + "/", 0, 0)
                    else:
                        dt = info.date_time
                        try:
                            mtime = time.mktime(dt + (0, 0, -1))
                            date_str = time.strftime("%d.%m.%Y %H:%M", time.localtime(mtime))
                        except: mtime, date_str = 0, ""
                        fi = FileInfo(child_name, os.path.splitext(child_name)[1].lstrip('.'), 
                                     _format_size(info.file_size), date_str, False, 
                                     prefix + child_name, info.file_size, mtime)
                    entries[child_name] = fi
        except: pass
        return list(entries.values())

    def _list_tar(self, inner_path: str) -> list:
        """List directory contents of a TAR archive."""
        inner_path = inner_path.strip("/")
        prefix = inner_path + "/" if inner_path else ""
        entries = {}
        try:
            with tarfile.open(self.archive_path, "r:*") as tf:
                for member in tf.getmembers():
                    name = member.name.replace("\\", "/")
                    if prefix and not name.startswith(prefix): continue
                    rel = name[len(prefix):]
                    if not rel or rel == "/": continue
                    parts = rel.strip("/").split("/")
                    child_name = parts[0]
                    if child_name in entries: continue

                    is_dir = member.isdir() or len(parts) > 1
                    if is_dir:
                        fi = FileInfo(child_name, "<DIR>", "<DIR>", "", True, prefix + child_name + "/", 0, 0)
                    else:
                        mtime = member.mtime
                        date_str = time.strftime("%d.%m.%Y %H:%M", time.localtime(mtime))
                        fi = FileInfo(child_name, os.path.splitext(child_name)[1].lstrip('.'), 
                                     _format_size(member.size), date_str, False, 
                                     prefix + child_name, member.size, mtime)
                    entries[child_name] = fi
        except: pass
        return list(entries.values())

    def _list_7z(self, inner_path: str) -> list:
        """List contents of a 7z archive."""
        inner_path = inner_path.strip("/")
        prefix = inner_path + "/" if inner_path else ""
        entries = {}
        try:
            with py7zr.SevenZipFile(self.archive_path, mode='r') as archive:
                for info in archive.list():
                    name = info.filename.replace("\\", "/")
                    if prefix and not name.startswith(prefix): continue
                    rel = name[len(prefix):]
                    if not rel or rel == "/": continue
                    parts = rel.strip("/").split("/")
                    child_name = parts[0]
                    if child_name in entries: continue

                    is_dir = info.is_directory or len(parts) > 1
                    if is_dir:
                        fi = FileInfo(child_name, "<DIR>", "<DIR>", "", True, prefix + child_name + "/", 0, 0)
                    else:
                        mtime = info.modified.timestamp() if info.modified else 0
                        date_str = time.strftime("%d.%m.%Y %H:%M", time.localtime(mtime)) if mtime else ""
                        fi = FileInfo(child_name, os.path.splitext(child_name)[1].lstrip('.'), 
                                     _format_size(info.uncompressed), date_str, False, 
                                     prefix + child_name, info.uncompressed, mtime)
                    entries[child_name] = fi
        except: pass
        return list(entries.values())

    def _list_rar(self, inner_path: str) -> list:
        """List contents of a RAR archive."""
        inner_path = inner_path.strip("/")
        prefix = inner_path + "/" if inner_path else ""
        entries = {}
        try:
            with rarfile.RarFile(self.archive_path) as rf:
                for info in rf.infolist():
                    name = info.filename.replace("\\", "/")
                    if prefix and not name.startswith(prefix): continue
                    rel = name[len(prefix):]
                    if not rel or rel == "/": continue
                    parts = rel.strip("/").split("/")
                    child_name = parts[0]
                    if child_name in entries: continue

                    is_dir = info.isdir() or len(parts) > 1
                    if is_dir:
                        fi = FileInfo(child_name, "<DIR>", "<DIR>", "", True, prefix + child_name + "/", 0, 0)
                    else:
                        dt = info.date_time
                        mtime = time.mktime(dt + (0, 0, -1))
                        date_str = time.strftime("%d.%m.%Y %H:%M", time.localtime(mtime))
                        fi = FileInfo(child_name, os.path.splitext(child_name)[1].lstrip('.'), 
                                     _format_size(info.file_size), date_str, False, 
                                     prefix + child_name, info.file_size, mtime)
                    entries[child_name] = fi
        except: pass
        return list(entries.values())

    def extract_file(self, inner_path: str, dest_dir: str) -> str | None:
        """Extract a single file from the archive to dest_dir."""
        inner_path = inner_path.strip("/")
        try:
            if self._is_zip:
                with zipfile.ZipFile(self.archive_path, "r") as zf:
                    zf.extract(inner_path, dest_dir)
            elif self._is_tar:
                with tarfile.open(self.archive_path, "r:*") as tf:
                    tf.extract(inner_path, dest_dir, filter='data')
            elif self._is_7z:
                with py7zr.SevenZipFile(self.archive_path, mode='r') as archive:
                    archive.extract(targets=[inner_path], path=dest_dir)
            elif self._is_rar:
                with rarfile.RarFile(self.archive_path) as rf:
                    rf.extract(inner_path, dest_dir)
            
            return os.path.join(dest_dir, inner_path.replace("/", os.sep))
        except: return None

    def extract_all(self, dest_dir: str) -> bool:
        """Extract entire archive to dest_dir."""
        try:
            if self._is_zip:
                with zipfile.ZipFile(self.archive_path, "r") as zf: zf.extractall(dest_dir)
            elif self._is_tar:
                with tarfile.open(self.archive_path, "r:*") as tf: tf.extractall(dest_dir, filter='data')
            elif self._is_7z:
                with py7zr.SevenZipFile(self.archive_path, mode='r') as archive: archive.extractall(path=dest_dir)
            elif self._is_rar:
                with rarfile.RarFile(self.archive_path) as rf: rf.extractall(path=dest_dir)
            return True
        except: return False

    def upload_file(self, local_source: str, remote_dest_path: str) -> bool:
        return False

    def delete_item(self, remote_path: str, is_dir: bool) -> bool:
        return False

    def mkdir(self, remote_path: str) -> bool:
        return False
