import os
from fs_worker import FileInfo

class SearchVFS:
    """Virtual File System representing a flat list of search results.
    May wrap another VFS if the search was performed inside one."""
    def __init__(self, search_results: list[FileInfo], title: str = "Search Results", source_vfs=None):
        self.files = search_results
        self.title = title
        self.source_vfs = source_vfs

    def list_dir(self, inner_path: str = "") -> list:
        # We ignore inner_path, search results are flat
        return self.files

    def is_dir(self, inner_path: str) -> bool:
        # Only the root is a dir, everything else is whatever its FileInfo says it is
        if not inner_path:
            return True
        for f in self.files:
            if f.name == inner_path:
                return f.is_dir
        return False

    def ensure_local(self, inner_path: str) -> str:
        # Finding the local path for external opening.
        # Since these files exist on the actual disk or inside another VFS:
        # If it's pure disk search results, full_path IS the local path.
        # But wait, search results could be from another VFS!
        # SearchDialog already handles this because it passes the correct path.
        for f in self.files:
            if f.name == inner_path or f.full_path.endswith(inner_path):
                return f.full_path # Search results keep their real path in full_path
        return inner_path
        
    def extract_file(self, inner_path: str, dest_dir: str) -> str:
        """Extract a file to the destination directory. Handles mixed sources."""
        import shutil
        for f in self.files:
            if f.name == inner_path or f.full_path == inner_path or inner_path.endswith(f.name):
                # Is it from a VFS?
                if self.source_vfs:
                    # In VFS search, the full_path usually corresponds to the internal VFS path
                    return self.source_vfs.extract_file(f.full_path, dest_dir)
                else:
                    # Standard local file system search
                    if os.path.exists(f.full_path) and not f.is_dir:
                        dest_path = os.path.join(dest_dir, f.name)
                        shutil.copy2(f.full_path, dest_path)
                        return dest_path
        return ""

    def extract_all(self, dest_dir: str):
        for f in self.files:
            if not f.is_dir:
                self.extract_file(f.full_path, dest_dir)

    # Mock other methods just in case things try to call them
    def mkdir(self, inner_path: str):
        raise NotImplementedError("Cannot create directories in search results")

    def rmdir(self, inner_path: str):
        raise NotImplementedError("Cannot remove directories directly from search results")

    def remove(self, inner_path: str):
        raise NotImplementedError("Cannot remove files directly from search results")

    def disconnect(self):
        pass
