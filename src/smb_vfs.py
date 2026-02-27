"""
SMB Virtual File System – browse Windows network shares.
Implements the VFS interface using pysmb.
"""
import os
import io
import time
import math
import socket
from smb.SMBConnection import SMBConnection
from fs_worker import FileInfo
from logger import log


class SMBVFS:
    def __init__(self, host, share, user, passwd, port=445, domain=""):
        self.host = host
        self.share = share  # Share name, e.g. "public" in \\server\public
        self.user = user
        self.passwd = passwd
        self.port = port
        self.domain = domain
        self._conn: SMBConnection | None = None
        # Derive a client name from hostname (SMB requires a local name)
        self._client_name = socket.gethostname()

    # ------------------------------------------------------------------ #
    #  Connection
    # ------------------------------------------------------------------ #

    def connect(self) -> bool:
        """Establish / reuse SMB connection."""
        if self._conn:
            try:
                # lightweight keepalive — list root share entries
                self._conn.listPath(self.share, "/", timeout=5)
                return True
            except Exception:
                self._conn = None

        try:
            conn = SMBConnection(
                self.user,
                self.passwd,
                self._client_name,
                self.host,
                domain=self.domain,
                use_ntlm_v2=True,
                is_direct_tcp=(self.port == 445),
            )
            connected = conn.connect(self.host, self.port, timeout=30)
            if not connected:
                return False
            self._conn = conn
            return True
        except Exception as e:
            log.error(f"[SMBVFS] Connection failed: {e}")
            self._conn = None
            return False

    # ------------------------------------------------------------------ #
    #  Directory listing
    # ------------------------------------------------------------------ #

    def list_dir(self, path: str = "/") -> list:
        """Return list of FileInfo for the given remote path on the share."""
        if not self.connect():
            raise Exception(f"SMB connection to \\\\{self.host}\\{self.share} failed")
        assert self._conn is not None

        path = path or "/"
        files = []
        try:
            for entry in self._conn.listPath(self.share, path):
                name = entry.filename
                if name in (".", ".."):
                    continue

                is_dir = entry.isDirectory
                size_bytes = entry.file_size
                # SMB returns create_time / last_write_time as Unix timestamps
                mtime = entry.last_write_time or 0
                date_str = time.strftime("%d.%m.%Y %H:%M", time.localtime(mtime)) if mtime else ""

                fi = FileInfo(
                    name=name,
                    ext="" if is_dir else os.path.splitext(name)[1].lstrip("."),
                    size="<DIR>" if is_dir else self.format_size(size_bytes),
                    date=date_str,
                    is_dir=is_dir,
                    full_path=f"{path.rstrip('/')}/{name}",
                    size_bytes=size_bytes,
                    mtime=mtime,
                )
                files.append(fi)
        except Exception as e:
            log.error(f"[SMBVFS] list_dir failed for '{path}': {e}")
        return files

    # ------------------------------------------------------------------ #
    #  File transfer
    # ------------------------------------------------------------------ #

    def extract_file(self, remote_path: str, local_dest_dir: str) -> str | None:
        """Download a file from the SMB share to a local directory."""
        if not self.connect():
            raise Exception("SMB not connected")
        assert self._conn is not None

        local_name = os.path.basename(remote_path)
        local_path = os.path.join(local_dest_dir, local_name)
        with open(local_path, "wb") as f:
            self._conn.retrieveFile(self.share, remote_path, f)
        return local_path

    def upload_file(self, local_source: str, remote_dest_path: str) -> bool:
        """Upload a local file to the SMB share."""
        if not self.connect():
            raise Exception("SMB not connected")
        assert self._conn is not None

        with open(local_source, "rb") as f:
            self._conn.storeFile(self.share, remote_dest_path, f)
        return True

    # ------------------------------------------------------------------ #
    #  Deletion & creation
    # ------------------------------------------------------------------ #

    def delete_item(self, remote_path: str, is_dir: bool) -> bool:
        """Delete a file or directory on the SMB share."""
        if not self.connect():
            raise Exception("SMB not connected")
        assert self._conn is not None

        if is_dir:
            self._rmdir_recursive(remote_path)
        else:
            self._conn.deleteFiles(self.share, remote_path)
        return True

    def _rmdir_recursive(self, path: str):
        """Recursively remove a remote directory."""
        assert self._conn is not None
        for entry in self._conn.listPath(self.share, path):
            if entry.filename in (".", ".."):
                continue
            item_path = f"{path.rstrip('/')}/{entry.filename}"
            if entry.isDirectory:
                self._rmdir_recursive(item_path)
            else:
                self._conn.deleteFiles(self.share, item_path)
        self._conn.deleteDirectory(self.share, path)

    def mkdir(self, remote_path: str) -> bool:
        """Create a directory on the SMB share."""
        if not self.connect():
            raise Exception("SMB not connected")
        assert self._conn is not None

        self._conn.createDirectory(self.share, remote_path)
        return True

    # ------------------------------------------------------------------ #
    #  Cleanup
    # ------------------------------------------------------------------ #

    def close(self):
        if self._conn:
            try:
                self._conn.close()
            except Exception:
                pass
            self._conn = None

    # ------------------------------------------------------------------ #
    #  Helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def format_size(size_bytes: int) -> str:
        if size_bytes == 0:
            return "0 B"
        size_name = ("B", "KB", "MB", "GB", "TB")
        i = int(math.floor(math.log(size_bytes, 1024)))
        p = math.pow(1024, i)
        s = round(size_bytes / p, 2)
        return f"{s} {size_name[i]}"
