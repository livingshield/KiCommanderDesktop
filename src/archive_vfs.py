"""
Archive Virtual File System – browse ZIP/TAR/GZ archives as directories.
Provides ArchiveVFS class that returns lists of FileInfo objects
compatible with the existing FileModel.
"""
import os
import zipfile
import tarfile
import time
from fs_worker import FileInfo


ARCHIVE_EXTENSIONS = {
    ".zip", ".tar", ".tar.gz", ".tgz", ".tar.bz2", ".tbz2", ".tar.xz", ".txz",
    ".gz", ".bz2", ".xz", ".7z", ".rar",  # 7z/rar listed for detection only
}

# Extensions we can actually open
SUPPORTED_EXTENSIONS = {".zip", ".tar", ".tar.gz", ".tgz", ".tar.bz2", ".tbz2", ".tar.xz", ".txz"}


def is_archive(path: str) -> bool:
    """Check if a file path looks like an archive we can open."""
    lower = path.lower()
    for ext in SUPPORTED_EXTENSIONS:
        if lower.endswith(ext):
            return True
    return False


def _format_size(size: int) -> str:
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

    def list_dir(self, inner_path: str = "") -> list:
        """
        List contents of a directory inside the archive.
        inner_path: relative path inside the archive (e.g. "src/utils/")
        Returns list of FileInfo objects.
        """
        if self._is_zip:
            return self._list_zip(inner_path)
        elif self._is_tar:
            return self._list_tar(inner_path)
        return []

    def _list_zip(self, inner_path: str) -> list:
        """List directory contents of a ZIP archive."""
        inner_path = inner_path.strip("/")
        prefix = inner_path + "/" if inner_path else ""
        depth = prefix.count("/")

        entries = {}  # name -> FileInfo
        try:
            with zipfile.ZipFile(self.archive_path, "r") as zf:
                for info in zf.infolist():
                    name = info.filename.replace("\\", "/")
                    # Skip entries not under current prefix
                    if prefix and not name.startswith(prefix):
                        continue
                    # Get relative name after prefix
                    rel = name[len(prefix):]
                    if not rel or rel == "/":
                        continue

                    # Determine if this is a direct child or deeper
                    parts = rel.strip("/").split("/")
                    child_name = parts[0]

                    if child_name in entries:
                        continue

                    is_dir = info.is_dir() or len(parts) > 1
                    if is_dir:
                        fi = FileInfo(
                            name=child_name,
                            ext="<DIR>",
                            size="<DIR>",
                            date="",
                            is_dir=True,
                            full_path=prefix + child_name + "/",
                        )
                        fi._size_bytes = 0
                        fi._mtime = 0
                    else:
                        dt = info.date_time
                        try:
                            mtime = time.mktime(dt + (0, 0, -1))
                            date_str = time.strftime("%d.%m.%Y %H:%M", time.localtime(mtime))
                        except (ValueError, OverflowError):
                            mtime = 0
                            date_str = ""
                        fi = FileInfo(
                            name=child_name,
                            ext=os.path.splitext(child_name)[1],
                            size=_format_size(info.file_size),
                            date=date_str,
                            is_dir=False,
                            full_path=prefix + child_name,
                        )
                        fi._size_bytes = info.file_size
                        fi._mtime = mtime
                    entries[child_name] = fi
        except (zipfile.BadZipFile, OSError):
            pass
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
                    if prefix and not name.startswith(prefix):
                        continue
                    rel = name[len(prefix):]
                    if not rel or rel == "/":
                        continue

                    parts = rel.strip("/").split("/")
                    child_name = parts[0]

                    if child_name in entries:
                        continue

                    is_dir = member.isdir() or len(parts) > 1
                    if is_dir:
                        fi = FileInfo(
                            name=child_name,
                            ext="<DIR>",
                            size="<DIR>",
                            date="",
                            is_dir=True,
                            full_path=prefix + child_name + "/",
                        )
                        fi._size_bytes = 0
                        fi._mtime = 0
                    else:
                        mtime = member.mtime
                        date_str = time.strftime("%d.%m.%Y %H:%M", time.localtime(mtime))
                        fi = FileInfo(
                            name=child_name,
                            ext=os.path.splitext(child_name)[1],
                            size=_format_size(member.size),
                            date=date_str,
                            is_dir=False,
                            full_path=prefix + child_name,
                        )
                        fi._size_bytes = member.size
                        fi._mtime = mtime
                    entries[child_name] = fi
        except (tarfile.TarError, OSError):
            pass
        return list(entries.values())

    def extract_file(self, inner_path: str, dest_dir: str) -> str | None:
        """Extract a single file from the archive to dest_dir. Returns extracted path."""
        inner_path = inner_path.strip("/")
        try:
            if self._is_zip:
                with zipfile.ZipFile(self.archive_path, "r") as zf:
                    zf.extract(inner_path, dest_dir)
                    return os.path.join(dest_dir, inner_path.replace("/", os.sep))
            elif self._is_tar:
                with tarfile.open(self.archive_path, "r:*") as tf:
                    tf.extract(inner_path, dest_dir, filter='data')
                    return os.path.join(dest_dir, inner_path.replace("/", os.sep))
        except (zipfile.BadZipFile, tarfile.TarError, OSError, KeyError):
            pass
        return None

    def extract_all(self, dest_dir: str) -> bool:
        """Extract entire archive to dest_dir."""
        try:
            if self._is_zip:
                with zipfile.ZipFile(self.archive_path, "r") as zf:
                    zf.extractall(dest_dir)
                return True
            elif self._is_tar:
                with tarfile.open(self.archive_path, "r:*") as tf:
                    tf.extractall(dest_dir, filter='data')
                return True
        except (zipfile.BadZipFile, tarfile.TarError, OSError):
            pass
        return False
