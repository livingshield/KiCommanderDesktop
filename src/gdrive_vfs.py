import os
import io
import time
from typing import List, Dict, Tuple
from fs_worker import FileInfo
from logger import log

try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
    GDRIVE_AVAILABLE = True
except ImportError:
    GDRIVE_AVAILABLE = False


SCOPES = ['https://www.googleapis.com/auth/drive']

class GDriveVFS:
    def __init__(self, credentials_path: str = "credentials.json", token_path: str = "token.json"):
        if not GDRIVE_AVAILABLE:
            raise ImportError("Google API client libraries are not installed.")
        
        self.creds = None
        self.credentials_path = credentials_path
        self.token_path = token_path
        
        # We need absolute paths if the executable is frozen
        import sys
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            
        self.credentials_path = os.path.join(base_dir, credentials_path)
        self.token_path = os.path.join(base_dir, token_path)

        # In-memory cache to avoid repeated Drive API calls for path resolution
        # Maps string path (e.g. "MyFolder/MySubfolder") to Drive Folder ID
        self._path_cache = {"": "root", "/": "root"}

    def connect(self):
        """Authenticates and builds the Drive API service."""
        if not os.path.exists(self.credentials_path):
            if os.path.exists(self.token_path):
                # Perhaps token works anyway? Let's check below.
                pass
            else:
                raise FileNotFoundError(f"Missing Google Drive {self.credentials_path}. Please download it from Google Cloud Console.")

        if os.path.exists(self.token_path):
            self.creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)
            
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                if not os.path.exists(self.credentials_path):
                    raise FileNotFoundError(f"Need {self.credentials_path} for initial authentication.")
                flow = InstalledAppFlow.from_client_secrets_file(self.credentials_path, SCOPES)
                self.creds = flow.run_local_server(port=0)
            
            with open(self.token_path, 'w') as token:
                token.write(self.creds.to_json())

        self.service = build('drive', 'v3', credentials=self.creds)

    def _resolve_path_to_id(self, path: str) -> str:
        """Helper to find the Google Drive ID for a given / slash delimited path."""
        path = path.strip("/")
        if not path:
            return "root"
            
        if path in self._path_cache:
            return self._path_cache[path]
            
        parts = path.split("/")
        current_id = "root"
        current_built_path = ""
        
        for part in parts:
            if current_built_path:
                current_built_path = f"{current_built_path}/{part}"
            else:
                current_built_path = part
                
            if current_built_path in self._path_cache:
                current_id = self._path_cache[current_built_path]
                continue
                
            # Query for part inside current_id
            query = f"'{current_id}' in parents and name='{part}' and trashed=false"
            results = self.service.files().list(q=query, fields="files(id, mimeType)", pageSize=1).execute()
            items = results.get('files', [])
            
            if not items:
                raise FileNotFoundError(f"Path '{path}' not found on Google Drive.")
                
            current_id = items[0]['id']
            self._path_cache[current_built_path] = current_id
            
        return current_id

    def list_dir(self, inner_path: str = "") -> list:
        folder_id = self._resolve_path_to_id(inner_path)
        
        query = f"'{folder_id}' in parents and trashed=false"
        # We fetch id, name, mimeType, size, modifiedTime
        results = self.service.files().list(
            q=query, 
            fields="files(id, name, mimeType, size, modifiedTime, owners)",
            pageSize=1000
        ).execute()
        
        items = results.get('files', [])
        
        files = []
        
        for item in items:
            name = item['name']
            is_dir = (item['mimeType'] == 'application/vnd.google-apps.folder')
            size_bytes = int(item.get('size', 0)) if not is_dir else 0
            
            if is_dir:
                ext = ""
                size_str = "<DIR>"
            else:
                ext = os.path.splitext(name)[1].removeprefix('.')
                if size_bytes == 0 and not 'size' in item:
                    # Google Docs/Sheets don't have size natively exported
                    size_str = "<DOC>"
                else:
                    size_str = self._format_size(size_bytes)
                    
            mtime_str = item.get('modifiedTime', "")
            mtime = 0.0
            date_str = ""
            try:
                import datetime
                # Just a rough parse for string "2023-11-20T08:00:00.000Z"
                dt = datetime.datetime.strptime(mtime_str[:19], "%Y-%m-%dT%H:%M:%S")
                mtime = dt.timestamp()
                date_str = dt.strftime('%d.%m.%Y %H:%M')
            except Exception:
                pass
                
            owner = ""
            if item.get('owners'):
                owner = item['owners'][0].get('displayName', "")
                
            full_path = f"{inner_path.strip('/')}/{name}" if inner_path.strip('/') else name
            
            fi = FileInfo(
                name=name, ext=ext, size=size_str, date=date_str, 
                is_dir=is_dir, full_path=full_path, 
                size_bytes=size_bytes, mtime=mtime, 
                owner=owner, group="gdrive", permissions=""
            )
            # Store ID in FileInfo implicitly via hack (or lookup later)
            # but simplest is just mapping it in cache so download knows
            self._path_cache[full_path] = item['id']
            files.append(fi)
            
        return files

    def ensure_local(self, inner_path: str) -> str:
        """Download to temp and return local path for viewing/execution."""
        import tempfile
        tmp = tempfile.mkdtemp(prefix="gdrive_")
        return self.extract_file(inner_path, tmp)

    def extract_file(self, inner_path: str, dest_dir: str) -> str:
        file_id = self._resolve_path_to_id(inner_path)
        name = os.path.basename(inner_path)
        dest_path = os.path.join(dest_dir, name)
        
        request = self.service.files().get_media(fileId=file_id)
        
        with open(dest_path, 'wb') as fh:
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while done is False:
                status, done = downloader.next_chunk()
        return dest_path

    def upload_file(self, local_path: str, dest_dir: str = ""):
        parent_id = self._resolve_path_to_id(dest_dir)
        name = os.path.basename(local_path)
        
        file_metadata = {
            'name': name,
            'parents': [parent_id]
        }
        media = MediaFileUpload(local_path, resumable=True)
        self.service.files().create(body=file_metadata, media_body=media, fields='id').execute()

    def mkdir(self, dir_path: str):
        parent_dir = os.path.dirname(dir_path)
        parent_id = self._resolve_path_to_id(parent_dir)
        new_name = os.path.basename(dir_path)
        
        file_metadata = {
            'name': new_name,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [parent_id]
        }
        self.service.files().create(body=file_metadata, fields='id').execute()

    def remove(self, path: str):
        file_id = self._resolve_path_to_id(path)
        self.service.files().delete(fileId=file_id).execute()
        if path in self._path_cache:
            del self._path_cache[path]

    def rmdir(self, path: str):
        self.remove(path)

    def is_dir(self, path: str) -> bool:
        if not path or path == "/": return True
        try:
            _ = self._resolve_path_to_id(path)
            # if we get here, it exists, but is it a dir?
            # actually we don't know without a get() call for mimeType
            return True # Just guessing for now
        except:
            return False

    def disconnect(self):
        pass

    def _format_size(self, size: float) -> str:
        if size < 0: return "0 B"
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.0f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"
