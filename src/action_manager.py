import os
import sys
import json
import subprocess
import tempfile
from PySide6.QtWidgets import QMessageBox, QInputDialog, QDialog, QMenu, QApplication
from PySide6.QtCore import Qt, QUrl, QMimeData, QByteArray
from PySide6.QtGui import QCursor
import qtawesome as qta

from ftp_vfs import FTPVFS
from sftp_vfs import SFTPVFS
from smb_vfs import SMBVFS
from archive_vfs import ArchiveVFS, is_archive
from fs_worker import FileInfo
from archiver import ArchiveThread
from vfs_ops import VfsOpThread
from queue_manager import QueueManager
from settings_dialog import SettingsDialog
from search_dialog import SearchDialog
from duplicate_view import DuplicateDialog
from diff_viewer import DiffDialog
from connection_manager import ConnectionManagerDialog
from operation_dialogs import CopyMoveDialog
from multi_rename_dialog import MultiRenameDialog
from sync_dialog import SyncDialog
from dialogs.network_connect_dialogs import SFTPConnectDialog, SMBConnectDialog

class ActionManager:
    def __init__(self, main_window):
        self.mw = main_window # KiCommander instance
        
        # Connect Queue Manager overwrite signals
        self.queue = QueueManager.instance()
        self.queue.query_overwrite.connect(self.on_queue_overwrite)
        self.queue.queue_updated.connect(self._show_transfer_mgr_if_needed)

    def _show_transfer_mgr_if_needed(self):
        """Automatically show the transfer manager if there are active or waiting items."""
        active_items = [i for i in self.queue.items if i.status in ("Running", "Waiting")]
        if active_items and not self.mw.transfer_widget.isVisible():
            self.mw.transfer_widget.show()

    def op_view(self):
        active = self.mw.get_active_panel()
        items = active.get_selected_items()
        if items:
            f = items[0]
            if not f.is_dir:
                active.preview_file(f.full_path)

    def op_edit(self):
        active = self.mw.get_active_panel()
        items = active.get_selected_items()
        if items:
            f = items[0]
            if f.is_dir: return
            
            target_path = f.full_path
            if active._vfs:
                # VFS: Download to temp and edit
                import tempfile
                tmp_dir = tempfile.gettempdir()
                target_path = active._vfs.extract_file(f.full_path, tmp_dir)
            
            if not target_path: return

            editor_path = self.mw.settings.value("editor/path", "")
            if editor_path and os.path.exists(editor_path):
                try:
                    subprocess.Popen([editor_path, target_path])
                except Exception as e:
                    QMessageBox.warning(self.mw, "Editor Error", f"Failed to launch editor:\n{e}")
            else:
                # Fallback to system default
                if sys.platform == "win32":
                    os.startfile(target_path)
                elif sys.platform == "darwin":
                    subprocess.Popen(["open", target_path])
                else:
                    subprocess.Popen(["xdg-open", target_path])

    def op_settings(self):
        """Open settings dialog."""
        dlg = SettingsDialog(self.mw)
        if dlg.exec() == QDialog.Accepted:
            # Refresh anything if needed
            pass

    def op_search(self):
        active = self.mw.get_active_panel()
        root_path = active.current_path if not active._vfs else active._vfs_inner
        dlg = SearchDialog(root_path, self.mw, vfs=active._vfs)
        dlg.navigate_to.connect(active.refresh_path)
        dlg.exec()

    def op_filter(self):
        active = self.mw.get_active_panel()
        active.toggle_filter()

    def run_plugin(self, plugin):
        """Execute a plugin with the selected files from the active panel."""
        active = self.mw.get_active_panel()
        selected = active.get_selected_paths()
        try:
            plugin.action(selected, active)
        except Exception as e:
            QMessageBox.warning(self.mw, "Plugin Error", f"{plugin.name} failed:\n{e}")

    def op_connect_ftp(self):
        """Connect to the test FTP server using credentials from secrets.json."""
        try:
            # Resolve secrets.json path relative to the executable/script
            if getattr(sys, 'frozen', False):
                base_dir = os.path.dirname(sys.executable)
            else:
                base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            
            secrets_path = os.path.join(base_dir, "secrets.json")
            
            with open(secrets_path, "r") as f:
                config = json.load(f)
            ftp_conf = config.get("ftp")
            if not ftp_conf:
                QMessageBox.critical(self.mw, "Config Error", "FTP credentials not found in secrets.json")
                return
            
            vfs = FTPVFS(ftp_conf["host"], ftp_conf["user"], ftp_conf["pass"])
            # The actual connection will happen in the VfsThread during refresh
            active = self.mw.get_active_panel()
            active._enter_vfs(vfs, "ftp", "/")
        except Exception as e:
            QMessageBox.critical(self.mw, "Error", f"Failed to load FTP config: {e}")

    def op_connect_sftp(self):
        """Prompt user for SFTP credentials and open session in active panel."""
        dlg = SFTPConnectDialog(self.mw)
        if dlg.exec() != QDialog.Accepted:
            return

        data = dlg.get_data()
        if not data["host"] or not data["user"]:
            QMessageBox.warning(self.mw, "Input Error", "Host and username are required.")
            return

        vfs = SFTPVFS(data["host"], data["user"], data["pass"], port=data["port"])
        active = self.mw.get_active_panel()
        active._enter_vfs(vfs, "sftp", "/")

    def op_connect_smb(self):
        """Prompt user for SMB credentials and open share in active panel."""
        dlg = SMBConnectDialog(self.mw)
        if dlg.exec() != QDialog.Accepted:
            return

        data = dlg.get_data()
        if not data["host"] or not data["share"]:
            QMessageBox.warning(self.mw, "Input Error", "Host and share name are required.")
            return

        vfs = SMBVFS(data["host"], data["share"], data["user"], data["pass"], 
                     port=data["port"], domain=data["domain"])
        active = self.mw.get_active_panel()
        active._enter_vfs(vfs, "smb", "/")

    def op_connection_manager(self):
        """Open the Connection Manager and connect to the selected server."""
        dlg = ConnectionManagerDialog(self.mw)
        if dlg.exec() != ConnectionManagerDialog.Accepted:
            return
        c = dlg.get_selected_connection()
        if not c:
            return
        ptype = c.get("type", "FTP")
        host = c.get("host", "")
        user = c.get("user", "")
        passwd = c.get("pass", "")
        port = c.get("port", 21)
        active = self.mw.get_active_panel()
        if ptype == "FTP":
            from ftp_vfs import FTPVFS
            vfs = FTPVFS(host, user, passwd)
            active._enter_vfs(vfs, "ftp", "/")
        elif ptype == "SFTP":
            vfs = SFTPVFS(host, user, passwd, port=port)
            active._enter_vfs(vfs, "sftp", "/")
        elif ptype == "SMB":
            share = c.get("share", "")
            domain = c.get("domain", "")
            vfs = SMBVFS(host, share, user, passwd, port=port, domain=domain)
            active._enter_vfs(vfs, "smb", "/")

    def op_mkdir(self):
        active = self.mw.get_active_panel()
        name, ok = QInputDialog.getText(self.mw, "New Folder", "Name:")
        if ok and name:
            if active._vfs:
                path = os.path.join(active._vfs_inner, name).replace("\\", "/")
            else:
                path = os.path.join(active.current_path, name)
            self.run_op('mkdir', [path])

    def op_archive(self):
        """Vytvoří archiv z vybraných položek (Alt+F5)."""
        active = self.mw.get_active_panel()
        target_panel = self.mw.get_target_panel()
        
        # Podporujeme archivaci pouze lokálních souborů v této verzi
        if active._vfs:
            QMessageBox.warning(self.mw, "Archive", "Archiving from VFS is not supported yet.")
            return

        sources = active.get_selected_paths()
        if not sources: return

        # Návrh názvu archivu
        default_name = "archive.zip"
        if len(sources) == 1:
            default_name = os.path.basename(sources[0]) + ".zip"

        name, ok = QInputDialog.getText(self.mw, "Pack Files", 
                                       "Enter archive name (use .zip or .7z extension):", 
                                       text=default_name)
        if not (ok and name): return

        # Určení typu a cílové cesty
        target_dir = target_panel.current_path if (target_panel and not target_panel._vfs) else active.current_path
        target_path = os.path.join(target_dir, name)
        
        ext = os.path.splitext(name)[1].lower()
        if ext == ".rar":
            QMessageBox.warning(self.mw, "Archive Error", "RAR format is supported for extraction only (Read-Only). Please use .zip or .7z.")
            return
            
        archive_type = "zip"
        if ext == ".7z": archive_type = "7z"
        elif ext != ".zip":
            # Default na zip pokud uživatel zadal divnou nebo žádnou příponu
            target_path += ".zip"

        self.mw.statusBar().showMessage(f"Creating {archive_type} archive...")
        self.mw.archive_thread = ArchiveThread(sources, target_path, archive_type)
        self.mw.archive_thread.worker.progress.connect(lambda p, m: self.mw.statusBar().showMessage(f"{m} ({p}%)"))
        self.mw.archive_thread.worker.finished.connect(self.on_op_finished)
        self.mw.archive_thread.start()

    def op_compare(self):
        """Porovná vybraný soubor v levém panelu s vybraným souborem v pravém panelu."""
        left_sel = self.mw.left_tabs.currentWidget().get_selected_items() if self.mw.left_tabs.currentWidget()._vfs else self.mw.left_tabs.currentWidget().get_selected_paths()
        right_sel = self.mw.right_tabs.currentWidget().get_selected_items() if self.mw.right_tabs.currentWidget()._vfs else self.mw.right_tabs.currentWidget().get_selected_paths()

        if len(left_sel) != 1 or len(right_sel) != 1:
            QMessageBox.information(self.mw, "Compare", "Select exactly one file in each panel to compare.")
            return

        def get_content(panel, sel):
            path = sel[0]
            if panel._vfs:
                # Pro VFS musíme stáhnout do tempu pro přečtení contentu
                import tempfile
                with tempfile.TemporaryDirectory() as tmp:
                    local_tmp = panel._vfs.extract_file(path.full_path if hasattr(path, 'full_path') else path, tmp)
                    if local_tmp:
                        with open(local_tmp, "r", encoding="utf-8", errors="replace") as f:
                            return path.full_path if hasattr(path, 'full_path') else path, f.read()
            else:
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    return path, f.read()
            return None, None

        try:
            p1, c1 = get_content(self.mw.left_tabs.currentWidget(), left_sel)
            p2, c2 = get_content(self.mw.right_tabs.currentWidget(), right_sel)
            
            if c1 is not None and c2 is not None:
                dlg = DiffDialog(p1, c1, p2, c2, self.mw)
                dlg.exec()
        except Exception as e:
            QMessageBox.critical(self.mw, "Compare Error", f"Could not read files:\n{e}")

    def op_find_duplicates(self):
        """Otevře okno pro hledání duplicit v aktuálních složkách obou panelů."""
        folders = []
        left = self.mw.left_tabs.currentWidget()
        right = self.mw.right_tabs.currentWidget()
        if not left._vfs: folders.append(left.current_path)
        if not right._vfs: folders.append(right.current_path)
        
        if not folders:
            QMessageBox.warning(self.mw, "Duplicates", "Duplicate search only works for local folders.")
            return

        dlg = DuplicateDialog(folders, self.mw)
        dlg.exec()

    def op_delete(self):
        active = self.mw.get_active_panel()
        # For VFS we need items (FileInfo) to know if it's a dir
        sources = active.get_selected_items() if active._vfs else active.get_selected_paths()
        if not sources: return
        
        confirm = self.mw.settings.value("behavior/confirm_delete", "true") == "true"
        if confirm:
            reply = QMessageBox.question(self.mw, "Confirm Delete", 
                                       f"Are you sure you want to delete {len(sources)} items?",
                                       QMessageBox.Yes | QMessageBox.No)
            if reply != QMessageBox.Yes:
                return
        
        self.run_op('delete', sources)

    def op_copy(self):
        self.file_op_dialog('copy')

    def op_move(self):
        self.file_op_dialog('move')

    def op_clipboard_copy(self, is_cut=False):
        """Kopíruje vybrané lokální soubory do systémové schránky."""
        active = self.mw.get_active_panel()
        if active._vfs and active._vfs_type not in ["smb"]:
            # OS nerozumí sftp:// nebo archive paths
            return

        paths = active.get_selected_paths()
        if not paths: return

        urls = []
        for p in paths:
            urls.append(QUrl.fromLocalFile(p))

        mime_data = QMimeData()
        mime_data.setUrls(urls)

        if is_cut:
            # Tell OS it's a Cut operation
            # 2 = Cut, 5 = Copy
            if sys.platform == "win32":
                mime_data.setData("application/x-qt-windows-mime;value=\"Preferred DropEffect\"", QByteArray.fromRawData(bytes([2, 0, 0, 0])))
            else:
                # Portable way (some managers use this)
                paths_str = '\n'.join(p for p in paths)
                mime_data.setData("gnome/copy-files", QByteArray.fromRawData(f"cut\n{paths_str}".encode('utf-8')))

        QApplication.clipboard().setMimeData(mime_data)
        self.mw.statusBar().showMessage(f"{'Cut' if is_cut else 'Copied'} {len(urls)} items to clipboard.")

    def op_clipboard_paste(self):
        """Vloží soubory ze systémové schránky do aktuálního panelu."""
        mime_data = QApplication.clipboard().mimeData()
        if not mime_data.hasUrls():
            return

        urls = mime_data.urls()
        sources = [u.toLocalFile() for u in urls if u.isLocalFile()]
        if not sources: return

        active = self.mw.get_active_panel()
        target_path = active.current_path
        if active._vfs:
            target_path = active._vfs_inner

        # Check for Move effect
        op_type = 'copy'
        if sys.platform == "win32" and mime_data.hasFormat("application/x-qt-windows-mime;value=\"Preferred DropEffect\""):
            data = mime_data.data("application/x-qt-windows-mime;value=\"Preferred DropEffect\"")
            if len(data) > 0 and data[0] == 2:
                op_type = 'move'
        elif mime_data.hasFormat("gnome/copy-files"):
            data = bytes(mime_data.data("gnome/copy-files")).decode('utf-8')
            if data.startswith("cut"):
                op_type = 'move'

        self.run_op(op_type, sources, target_path)

    def file_op_dialog(self, op_type):
        active = self.mw.get_active_panel()
        target_panel = self.mw.get_target_panel()
        
        vfs_involved = active._vfs or (target_panel and target_panel._vfs)
        items = active.get_selected_items() if vfs_involved else active.get_selected_paths()
        if not items: return
        
        source_names = [i.name if hasattr(i, 'name') else os.path.basename(i) for i in items]
        
        target_path = target_panel.current_path
        if target_panel._vfs:
            target_path = target_panel._vfs_inner
            
        dlg = CopyMoveDialog(op_type, source_names, target_path, self.mw)
        if dlg.exec() != QDialog.Accepted:
            return
            
        final_target = dlg.get_target_path()
        if dlg.result_mode == "queue":
            self.mw.statusBar().showMessage(f"Added {op_type} to queue.")
            QueueManager.instance().add_to_queue(
                op_type, items, final_target, 
                active._vfs, target_panel._vfs if target_panel else None
            )
        else:
            self.run_op(op_type, items, final_target)

    def run_op(self, op_type, sources, target=None):
        self.mw.statusBar().showMessage(f"Running {op_type}...")
        
        active = self.mw.get_active_panel()
        target_panel = self.mw.get_target_panel()
        
        source_vfs = active._vfs
        target_vfs = target_panel._vfs if target_panel else None
        
        # We use VfsOpThread for both VFS and local to get overwrite support
        self.mw.op_thread = VfsOpThread(op_type, sources, source_vfs, target_vfs, target)
        self.mw.op_thread.worker.query_overwrite.connect(self.on_query_overwrite, Qt.QueuedConnection)
        self.mw.op_thread.worker.finished.connect(self.on_op_finished)
        self.mw.op_thread.start()

    def on_queue_overwrite(self, item_id, src, target_info):
        """Useless if background, handles conflict in the queue."""
        src_name = src.name if hasattr(src, 'name') else str(src)
        src_size = src.size if hasattr(src, 'size') else "?"
        src_date = src.date if hasattr(src, 'date') else "?"
        
        msg = (f"<b>FRONTÁ - KONFLIKT:</b><br>Soubor již existuje: <b>{src_name}</b><br><br>"
               f"<b>Zdroj:</b> {src_size}, {src_date}<br>"
               f"<b>Cíl:</b> {target_info.size if target_info.size else '??'}, {target_info.date}<br><br>"
               "Chcete soubor přepsat?")
        
        box = QMessageBox(self.mw)
        box.setWindowTitle("Fronta: Potvrdit přepsání")
        box.setText(msg)
        box.setIcon(QMessageBox.Question)
        btn_overwrite = box.addButton("Přepsat", QMessageBox.AcceptRole)
        btn_skip = box.addButton("Přeskočit", QMessageBox.RejectRole)
        btn_cancel = box.addButton("Zrušit frontu", QMessageBox.DestructiveRole)
        box.exec()
        
        result = 'skip'
        if box.clickedButton() == btn_overwrite: result = 'overwrite'
        elif box.clickedButton() == btn_cancel: result = 'cancel'
        
        QueueManager.instance().set_overwrite_result(item_id, result)

    def on_query_overwrite(self, src, target_info):
        # src can be FileInfo or name string
        src_name = src.name if hasattr(src, 'name') else str(src)
        src_size = src.size if hasattr(src, 'size') else "?"
        src_date = src.date if hasattr(src, 'date') else "?"
        
        msg = (f"File already exists: <b>{src_name}</b><br><br>"
               f"<b>Source:</b> {src_size}, {src_date}<br>"
               f"<b>Target:</b> {target_info.size if target_info.size else '??'}, {target_info.date}<br><br>"
               "Do you want to overwrite it?")
        
        box = QMessageBox(self.mw)
        box.setWindowTitle("Confirm Overwrite")
        box.setText(msg)
        box.setIcon(QMessageBox.Question)
        btn_overwrite = box.addButton("Overwrite", QMessageBox.AcceptRole)
        btn_skip = box.addButton("Skip", QMessageBox.RejectRole)
        btn_cancel = box.addButton("Cancel", QMessageBox.DestructiveRole)
        box.exec()
        
        result = 'skip'
        if box.clickedButton() == btn_overwrite: result = 'overwrite'
        elif box.clickedButton() == btn_cancel: result = 'cancel'
        
        self.mw.op_thread.worker.set_overwrite_result(result)

    def on_op_finished(self, success, message):
        self.mw.statusBar().showMessage(message)
        if not success:
            QMessageBox.warning(self.mw, "Operation Failed", message)
        self.mw.refresh_all()

    def op_favorites(self):
        """Management oblíbených složek (Hotlist)."""
        active = self.mw.get_active_panel()
        favs = self.mw.settings.value("favorites/list", [])
        if not favs: favs = []
        if isinstance(favs, str): favs = [favs]
        
        menu = QMenu(self.mw)
        menu.setStyleSheet("QMenu { background-color: #1e1e2e; color: #cdd6f4; border: 1px solid #45475a; }")
        
        # Přidat aktuální
        curr = active.current_path if not active._vfs else f"[{active._vfs_type.upper()}] {active._vfs_inner}"
        add_action = menu.addAction(qta.icon("fa5s.plus-circle", color="#a6e3a1"), f"Přidat aktuální: {curr[:30]}...")
        
        def add_fav():
            if curr not in favs:
                favs.append(curr)
                self.mw.settings.setValue("favorites/list", favs)
        add_action.triggered.connect(add_fav)
        
        menu.addSeparator()
        
        for p in favs:
            action = menu.addAction(p)
            def navigate(target=p):
                if target.startswith("["):
                    tag_end = target.find("]")
                    if tag_end != -1:
                        self.mw.statusBar().showMessage(f"Switching VFS path to {target}")
                        active._vfs_inner = target[tag_end+2:]
                        active._refresh_vfs()
                else:
                    active.refresh_path(target)
            action.triggered.connect(navigate)
            
        if favs:
            menu.addSeparator()
            clear_action = menu.addAction(qta.icon("fa5s.eraser", color="#f38ba8"), "Vymazat vše")
            clear_action.triggered.connect(lambda: self.mw.settings.setValue("favorites/list", []))

        menu.exec(QCursor.pos())

    def op_multi_rename(self):
        """Hromadné přejmenování vybraných souborů."""
        active = self.mw.get_active_panel()
        items = active.get_selected_items() if active._vfs else active.get_selected_paths()
        if not items:
            self.mw.statusBar().showMessage("Žádné soubory vybrány.")
            return

        # If localized paths, convert to simple objects with name/full_path for the dialog
        if not active._vfs:
            from fs_worker import FileInfo
            files_to_pass = []
            for p in items:
                name = os.path.basename(p)
                files_to_pass.append(FileInfo(name, "", "", "", os.path.isdir(p), p, 0, 0))
        else:
            files_to_pass = items

        dlg = MultiRenameDialog(files_to_pass, vfs=active._vfs, parent=self.mw)
        if dlg.exec() == QDialog.Accepted:
            rename_map = dlg.get_rename_map() # List of (path, new_name)
            if rename_map:
                QueueManager.instance().add_to_queue(
                    'rename', rename_map, None,
                    source_vfs=active._vfs
                )
                self.mw.statusBar().showMessage(f"Přejmenování {len(rename_map)} souborů přidáno do fronty.")

    def op_sync(self):
        """Otevře dialog pro synchronizaci aktuálních složek v obou panelech."""
        left = self.mw.left_tabs.currentWidget()
        right = self.mw.right_tabs.currentWidget()
        
        if left._vfs or right._vfs:
            QMessageBox.warning(self.mw, "Sync", "Synchronizace zatím nepodporuje VFS. Použijte lokální složky.")
            return
            
        dlg = SyncDialog(left.current_path, right.current_path, self.mw)
        dlg.exec()

    def execute_shell_command(self, cmd, active_panel):
        """Spustí příkaz v aktivním panelu (lokálně nebo přes SSH)."""
        if active_panel._vfs_type == "sftp" and hasattr(active_panel._vfs, 'exec_command'):
            # Remote command via SSH
            try:
                output = active_panel._vfs.exec_command(cmd, active_panel._vfs_inner)
                QMessageBox.information(self.mw, "Vzdálený výstup", output)
            except Exception as e:
                QMessageBox.critical(self.mw, "Chyba SSH", f"Příkaz selhal:\n{e}")
            return

        # Lokální spuštění
        active_path = active_panel.current_path
        try:
            subprocess.Popen(cmd, shell=True, cwd=active_path)
        except Exception as e:
            QMessageBox.critical(self.mw, "Chyba", f"Nepodařilo se spustit příkaz:\n{e}")
