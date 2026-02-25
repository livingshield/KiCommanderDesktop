"""
SFTP Virtual File System – browse remote SSH/SFTP servers.
Implements the VFS interface to return FileInfo objects, using paramiko.
"""
import os
import stat
import time
import paramiko
from fs_worker import FileInfo


class SFTPVFS:
    def __init__(self, host, user, passwd, port=22, timeout=30):
        self.host = host
        self.user = user
        self.passwd = passwd
        self.port = port
        self.timeout = timeout
        self._ssh: paramiko.SSHClient | None = None
        self._sftp: paramiko.SFTPClient | None = None

    # ------------------------------------------------------------------ #
    #  Connection
    # ------------------------------------------------------------------ #

    def connect(self) -> bool:
        """Establish / reuse SSH + SFTP connection."""
        if self._sftp:
            try:
                self._sftp.stat(".")   # lightweight keepalive
                return True
            except Exception:
                self._sftp = None
                self._ssh = None

        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(
                self.host,
                port=self.port,
                username=self.user,
                password=self.passwd,
                timeout=self.timeout,
                allow_agent=False,
                look_for_keys=False,
            )
            self._ssh = ssh
            self._sftp = ssh.open_sftp()
            return True
        except Exception as e:
            print(f"[SFTPVFS] Connection failed: {e}")
            self._ssh = None
            self._sftp = None
            return False

    # ------------------------------------------------------------------ #
    #  Directory listing
    # ------------------------------------------------------------------ #

    def list_dir(self, path: str = "/") -> list:
        """Return list of FileInfo for the given remote path."""
        if not self.connect():
            raise Exception(f"SFTP connection to {self.host} failed")

        path = path or "/"
        files = []
        try:
            for attr in self._sftp.listdir_attr(path):
                name = attr.filename
                is_dir = stat.S_ISDIR(attr.st_mode) if attr.st_mode else False
                size_bytes = attr.st_size or 0
                mtime = attr.st_mtime or 0
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
            print(f"[SFTPVFS] list_dir failed for '{path}': {e}")
        return files

    # ------------------------------------------------------------------ #
    #  File transfer
    # ------------------------------------------------------------------ #

    def extract_file(self, remote_path: str, local_dest_dir: str) -> str | None:
        """Download a file from the SFTP server."""
        if not self.connect():
            raise Exception("SFTP not connected")

        local_name = os.path.basename(remote_path)
        local_path = os.path.join(local_dest_dir, local_name)
        self._sftp.get(remote_path, local_path)
        return local_path

    def upload_file(self, local_source: str, remote_dest_path: str) -> bool:
        """Upload a local file to the SFTP server."""
        if not self.connect():
            raise Exception("SFTP not connected")

        self._sftp.put(local_source, remote_dest_path)
        return True

    # ------------------------------------------------------------------ #
    #  Deletion & creation
    # ------------------------------------------------------------------ #

    def delete_item(self, remote_path: str, is_dir: bool) -> bool:
        """Delete a file or directory on the SFTP server."""
        if not self.connect():
            raise Exception("SFTP not connected")

        if is_dir:
            self._rmdir_recursive(remote_path)
        else:
            self._sftp.remove(remote_path)
        return True

    def _rmdir_recursive(self, path: str):
        """Recursively remove a remote directory."""
        for attr in self._sftp.listdir_attr(path):
            item_path = f"{path}/{attr.filename}"
            if stat.S_ISDIR(attr.st_mode):
                self._rmdir_recursive(item_path)
            else:
                self._sftp.remove(item_path)
        self._sftp.rmdir(path)

    def mkdir(self, remote_path: str) -> bool:
        """Create a directory on the SFTP server."""
        if not self.connect():
            raise Exception("SFTP not connected")

        self._sftp.mkdir(remote_path)
        return True

    def exec_command(self, cmd: str, workdir: str = "/") -> str:
        """Execute a shell command on the remote server via SSH."""
        if not self.connect():
            raise Exception("SFTP connection to host failed")
        
        full_cmd = f"cd '{workdir}' && {cmd}"
        stdin, stdout, stderr = self._ssh.exec_command(full_cmd)
        return stdout.read().decode('utf-8', errors='replace') + stderr.read().decode('utf-8', errors='replace')

    # ------------------------------------------------------------------ #
    #  Cleanup
    # ------------------------------------------------------------------ #

    def close(self):
        if self._sftp:
            try: self._sftp.close()
            except: pass
            self._sftp = None
        if self._ssh:
            try: self._ssh.close()
            except: pass
            self._ssh = None

    # ------------------------------------------------------------------ #
    #  Helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def format_size(size_bytes: int) -> str:
        if size_bytes == 0:
            return "0 B"
        import math
        size_name = ("B", "KB", "MB", "GB", "TB")
        i = int(math.floor(math.log(size_bytes, 1024)))
        p = math.pow(1024, i)
        s = round(size_bytes / p, 2)
        return f"{s} {size_name[i]}"
