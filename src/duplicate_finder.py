import os
import hashlib
import json
from PySide6.QtCore import QObject, Signal, QThread

class DuplicateFinderWorker(QObject):
    finished = Signal(dict)  # groups of duplicates: {hash: [path, path, ...]}
    progress = Signal(str)
    error = Signal(str)

    def __init__(self, folders):
        super().__init__()
        self.folders = folders
        self._is_running = True

    def stop(self):
        self._is_running = False

    def run(self):
        try:
            # Fáze 1: Sběr souborů podle velikosti
            self.progress.emit("Fáze 1: Skenování souborů a velikostí...")
            size_groups = {}
            for folder in self.folders:
                for root, _, files in os.walk(folder):
                    if not self._is_running: return
                    for name in files:
                        path = os.path.join(root, name)
                        try:
                            size = os.path.getsize(path)
                            if size == 0: continue # Skip empty files
                            if size not in size_groups:
                                size_groups[size] = []
                            size_groups[size].append(path)
                        except: continue

            # Necháme si jen velikosti, které mají víc než 1 soubor
            potential_dupes = [paths for size, paths in size_groups.items() if len(paths) > 1]
            
            # Fáze 2: Částečný hash (4KB)
            self.progress.emit("Fáze 2: Kontrola částečných hashů...")
            partial_groups = {}
            for paths in potential_dupes:
                if not self._is_running: return
                for path in paths:
                    h = self._get_hash(path, partial=True)
                    if h:
                        if h not in partial_groups: partial_groups[h] = []
                        partial_groups[h].append(path)

            potential_dupes = [paths for h, paths in partial_groups.items() if len(paths) > 1]

            # Fáze 3: Plný hash
            self.progress.emit("Fáze 3: Výpočet plných hashů...")
            final_groups = {}
            total_potential = sum(len(p) for p in potential_dupes)
            processed = 0

            for paths in potential_dupes:
                for path in paths:
                    if not self._is_running: return
                    h = self._get_hash(path, partial=False)
                    if h:
                        if h not in final_groups: final_groups[h] = []
                        final_groups[h].append(path)
                    
                    processed += 1
                    if processed % 10 == 0:
                        self.progress.emit(f"Fáze 3: Zpracování {processed}/{total_potential}...")

            # Finální filtrování
            result = {h: paths for h, paths in final_groups.items() if len(paths) > 1}
            
            # Mezistav do JSON
            data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
            os.makedirs(data_dir, exist_ok=True)
            with open(os.path.join(data_dir, "duplicates_scan.json"), "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2)

            self.finished.emit(result)

        except Exception as e:
            self.error.emit(str(e))

    def _get_hash(self, path, partial=False):
        try:
            hasher = hashlib.blake2b()
            with open(path, "rb") as f:
                if partial:
                    chunk = f.read(4096)
                    hasher.update(chunk)
                else:
                    while True:
                        chunk = f.read(65536)
                        if not chunk: break
                        hasher.update(chunk)
            return hasher.hexdigest()
        except:
            return None

class DuplicateFinderThread(QThread):
    def __init__(self, folders):
        super().__init__()
        self.worker = DuplicateFinderWorker(folders)
        self.worker.moveToThread(self)
        self.started.connect(self.worker.run)
        self.worker.finished.connect(self.quit)
