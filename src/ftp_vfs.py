"""
FTP Virtual File System – browse remote FTP servers.
Implements the VFS interface to return FileInfo objects.
"""
import os
import ftplib
import time
from fs_worker import FileInfo
from logger import log


class FTPVFS:
    def __init__(self, host, user, passwd, timeout=30):
        self.host = host
        self.user = user
        self.passwd = passwd
        self.timeout = timeout
        self._ftp = None
        self.current_inner = "/"

    def connect(self):
        """Establish connection or return existing one."""
        if self._ftp:
            try:
                self._ftp.voidcmd("NOOP")
                return True
            except:
                self._ftp = None

        try:
            self._ftp = ftplib.FTP(self.host, timeout=self.timeout)
            self._ftp.login(self.user, self.passwd)
            # Use binary mode by default
            self._ftp.voidcmd("TYPE I")
            return True
        except Exception as e:
            log.error(f"[FTPVFS] Connection failed: {e}")
            self._ftp = None
            return False

    def list_dir(self, path="/") -> list:
        """
        List directory contents via MLSD or LIST.
        Returns list of FileInfo objects.
        """
        if not self.connect():
            return []

        path = path or "/"
        files = []
        try:
            # Try MLSD first (modern, reliable parsing)
            try:
                for name, facts in self._ftp.mlsd(path):
                    if name in [".", ".."]:
                        continue
                    
                    is_dir = facts.get("type") in ["dir", "pdir", "cdir"]
                    size_bytes = int(facts.get("size", 0)) if not is_dir else 0
                    
                    # Parse modification time (YYYYMMDDHHMMSS)
                    mtime_str = facts.get("modify")
                    mtime: float = 0.0
                    date_str = ""
                    if mtime_str:
                        try:
                            # We only care about YYYYMMDDHHMMSS
                            ts = time.strptime(mtime_str[:14], "%Y%m%d%H%M%S")
                            mtime = time.mktime(ts)
                            date_str = time.strftime("%d.%m.%Y %H:%M", time.localtime(mtime))
                        except:
                            pass

                    fi = FileInfo(
                        name=name,
                        ext="" if is_dir else os.path.splitext(name)[1].lstrip("."),
                        size="<DIR>" if is_dir else self.format_size(size_bytes),
                        date=date_str,
                        is_dir=is_dir,
                        full_path=os.path.join(path, name).replace("\\", "/"),
                        size_bytes=size_bytes,
                        mtime=mtime
                    )
                    files.append(fi)
                return files
            except (ftplib.error_perm, AttributeError):
                # Fallback to LIST
                lines: list[str] = []
                self._ftp.retrlines(f"LIST {path}", lines.append)
                # Note: Parsing LIST output is notoriously fragile. 
                # For this MVP we prioritize MLSD.
                # In a real app we'd use a robust parser like 'ftpparser'.
                return [] 
        except Exception as e:
            log.error(f"[FTPVFS] list_dir failed: {e}")
            return []

    def extract_file(self, remote_path: str, local_dest_dir: str) -> str | None:
        """Download file from FTP to local directory."""
        if not self.connect():
            raise Exception("FTP not connected")
        
        local_name = os.path.basename(remote_path)
        local_path = os.path.join(local_dest_dir, local_name)
        
        with open(local_path, "wb") as f:
            self._ftp.retrbinary(f"RETR {remote_path}", f.write)
        return local_path

    def upload_file(self, local_source: str, remote_dest_path: str) -> bool:
        """Upload file from local directory to FTP."""
        if not self.connect():
            raise Exception("FTP not connected")
            
        with open(local_source, "rb") as f:
            self._ftp.storbinary(f"STOR {remote_dest_path}", f)
        return True

    def delete_item(self, remote_path: str, is_dir: bool) -> bool:
        """Delete file or directory from FTP."""
        if not self.connect():
            raise Exception("FTP not connected")
            
        if is_dir:
            self._ftp.rmd(remote_path)
        else:
            self._ftp.delete(remote_path)
        return True

    def mkdir(self, remote_path: str) -> bool:
        """Create a directory on FTP."""
        if not self.connect():
            raise Exception("FTP not connected")
        self._ftp.mkd(remote_path)
        return True

    def extract_all(self, local_dest_dir: str) -> bool:
        """Download entire current directory (shallow for now)."""
        # Note: True recursive mirror is complex for an MVP.
        # We start by downloading files in the current folder.
        files = self.list_dir(self.current_inner)
        success = True
        for f in files:
            if not f.is_dir:
                if not self.extract_file(f.full_path, local_dest_dir):
                    success = False
        return success

    def close(self):
        if self._ftp:
            try:
                self._ftp.quit()
            except:
                pass
            self._ftp = None

    @staticmethod
    def format_size(size_bytes):
        if size_bytes == 0: return "0 B"
        import math
        size_name = ("B", "KB", "MB", "GB", "TB")
        i = int(math.floor(math.log(size_bytes, 1024)))
        p = math.pow(1024, i)
        s = round(size_bytes / p, 2)
        return f"{s} {size_name[i]}"
