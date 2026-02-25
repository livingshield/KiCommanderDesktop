import os
import qtawesome as qta
from PySide6.QtWidgets import QMenu
from PySide6.QtCore import Qt
from archive_vfs import ArchiveVFS, is_archive

class ContextMenuBuilder:
    def __init__(self, panel):
        self.p = panel # FilePanel instance

    def build_and_show(self, pos):
        index = self.p.table.indexAt(pos)
        menu = QMenu(self.p)
        menu.setStyleSheet("QMenu { background-color: #1e1e2e; color: #cdd6f4; border: 1px solid #45475a; }")
        
        actions = self.p.window().actions

        if index.isValid():
            row = index.row()
            if self.p.filter_visible:
                row = self.p.proxy.mapToSource(index).row()
            file_info = self.p.model.get_file(row)
            
            if file_info and file_info.name != "..":
                # Header with file name (non-interactive)
                header = menu.addAction(qta.icon("fa5s.file", color="#cdd6f4"), file_info.name)
                header.setEnabled(False)
                menu.addSeparator()

                # Basic Ops
                menu.addAction(qta.icon("fa5s.eye", color="#a6e3a1"), "View (F3)", lambda: actions.op_view())
                menu.addAction(qta.icon("fa5s.edit", color="#f9e2af"), "Edit (F4)", lambda: actions.op_edit())
                
                if not self.p._vfs and is_archive(file_info.full_path):
                    menu.addAction(qta.icon("fa5s.file-archive", color="#cba6f7"), "Browse Archive",
                                   lambda: self.p._enter_vfs(ArchiveVFS(file_info.full_path), "archive"))
                
                menu.addSeparator()
                
                # File Operations
                menu.addAction(qta.icon("fa5s.copy", color="#89b4fa"), "Copy (F5)", lambda: actions.op_copy())
                menu.addAction(qta.icon("fa5s.external-link-alt", color="#fab387"), "Move (F6)", lambda: actions.op_move())
                menu.addAction(qta.icon("fa5s.file-archive", color="#cba6f7"), "Pack files (Alt+F5)", lambda: actions.op_archive())
                
                menu.addSeparator()
                
                # Clipboard
                menu.addAction(qta.icon("fa5s.cut", color="#cdd6f4"), "Cut (Ctrl+X)", lambda: actions.op_clipboard_copy(True))
                menu.addAction(qta.icon("fa5s.clone", color="#cdd6f4"), "Copy (Ctrl+C)", lambda: actions.op_clipboard_copy(False))
                menu.addAction(qta.icon("fa5s.paste", color="#cdd6f4"), "Paste (Ctrl+V)", lambda: actions.op_clipboard_paste())
                
                menu.addSeparator()
                
                # Management
                menu.addAction(qta.icon("fa5s.i-cursor", color="#f9e2af"), "Rename (F2)", lambda: self.p.rename_file(file_info))
                menu.addAction(qta.icon("fa5s.trash-alt", color="#f38ba8"), "Delete (F8)", lambda: actions.op_delete())
                
                menu.addSeparator()
                menu.addAction(qta.icon("fa5s.info-circle", color="#89b4fa"), "Properties (Alt+Enter)", lambda: self.p.show_properties(file_info.full_path))
            else:
                # Click on [..] or empty area
                menu.addAction(qta.icon("fa5s.folder-plus", color="#a6e3a1"), "New Folder (F7)", lambda: actions.op_mkdir())
                menu.addAction(qta.icon("fa5s.paste", color="#cdd6f4"), "Paste (Ctrl+V)", lambda: actions.op_clipboard_paste())
        else:
            # Click on empty area
            menu.addAction(qta.icon("fa5s.folder-plus", color="#a6e3a1"), "New Folder (F7)", lambda: actions.op_mkdir())
            menu.addAction(qta.icon("fa5s.paste", color="#cdd6f4"), "Paste (Ctrl+V)", lambda: actions.op_clipboard_paste())
            menu.addSeparator()
            menu.addAction(qta.icon("fa5s.sync", color="#89b4fa"), "Refresh (Ctrl+R)", lambda: self.p.window().refresh_all())

        menu.exec(self.p.table.viewport().mapToGlobal(pos))
