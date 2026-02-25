import os
import sys
from collections import deque
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableView, 
                             QHeaderView, QLabel, QPushButton, QLineEdit, 
                             QMenu, QTabWidget, QInputDialog, QMessageBox, QApplication)
from PySide6.QtCore import Qt, QSettings, QTimer, QFileSystemWatcher, QSortFilterProxyModel, QEvent, Signal, QItemSelectionModel
from PySide6.QtGui import QDrag, QPixmap

import qtawesome as qta

from file_model import FileModel
from fs_worker import ScanThread, FileInfo, VfsThread
from navigation_utils import get_drives, get_quick_links, BreadcrumbsWidget
from preview_dialog import PreviewDialog
from properties_dialog import PropertiesDialog
from archive_vfs import ArchiveVFS, is_archive

from ui.panels.interaction_handler import InteractionHandler
from ui.panels.context_menu import ContextMenuBuilder

class FilePanel(QWidget):
    got_focus = Signal(object) # emits self
    folder_changed = Signal(str) # emits current path
    
    def __init__(self, panel_id, initial_path):
        super().__init__()
        self.panel_id = panel_id
        self.current_path = initial_path
        self.settings = QSettings("KiCommander", "Desktop")
        
        last_path = self.settings.value(f"panels/{self.panel_id}/path")
        if last_path and os.path.exists(last_path):
            self.current_path = last_path

        # File system watcher for auto-refresh
        self._watcher = QFileSystemWatcher(self)
        self._watcher.directoryChanged.connect(self._on_dir_changed)
        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(300)
        self._debounce.timeout.connect(self._do_auto_refresh)

        # VFS state (unified for archives and network protocols)
        self._vfs = None           # Any VFS instance supporting list_dir/extract_file
        self._vfs_inner = ""       # Current path inside VFS
        self._vfs_type = None      # "archive", "ftp", etc.
        self._locked = False

        self.history = deque(maxlen=20)

        # Components
        self.interaction_handler = InteractionHandler(self)
        self.menu_builder = ContextMenuBuilder(self)

        self.setup_ui()
        self.refresh_path(self.current_path)

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        self.filter_visible = False
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(2)

        # Drive Selector Bar
        self.drive_bar = QHBoxLayout()
        self.drive_bar.setSpacing(2)
        self.update_drive_bar()
        main_layout.addLayout(self.drive_bar)

        # Breadcrumbs
        self.breadcrumbs = BreadcrumbsWidget(self)
        self.breadcrumbs.path_clicked.connect(self.on_breadcrumb_clicked)
        main_layout.addWidget(self.breadcrumbs)

        # Path label (kept for compact info)
        self.path_label = QLabel(self.current_path)
        self.path_label.setObjectName("PathLabel")
        self.path_label.setStyleSheet("font-size: 10px; color: #585b70; padding-left: 4px;")
        main_layout.addWidget(self.path_label)

        # Body with Sidebar and Table
        body_layout = QHBoxLayout()
        body_layout.setSpacing(2)

        # Sidebar (Quick Links)
        self.sidebar = QVBoxLayout()
        self.sidebar.setSpacing(5)
        self.sidebar.setAlignment(Qt.AlignTop)
        self.update_sidebar()
        body_layout.addLayout(self.sidebar)

        # Table
        self.table = QTableView()
        self.model = FileModel()
        self.table.setModel(self.model)
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setSelectionMode(QTableView.ExtendedSelection)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)
        # Default column widths: Name wider, others compact
        self.table.setColumnWidth(0, 280)  # Name
        self.table.setColumnWidth(1, 60)   # Ext
        self.table.setColumnWidth(2, 90)   # Size
        
        # --- Drag and Drop ---
        self.table.setDragEnabled(True)
        self.table.setAcceptDrops(True)
        self.table.setDropIndicatorShown(True)
        self.table.setDragDropMode(QTableView.DragDrop)
        self.table.setDefaultDropAction(Qt.CopyAction)
        
        self.table.doubleClicked.connect(self.on_double_click)
        # Context menu is strictly manual via timer
        self.table.setContextMenuPolicy(Qt.NoContextMenu) 
        self.table.installEventFilter(self)
        self.table.viewport().installEventFilter(self)
        
        # --- Sorting via header clicks ---
        header = self.table.horizontalHeader()
        header.setSectionsClickable(True)
        header.sectionClicked.connect(self._on_header_clicked)
        header.setCursor(Qt.PointingHandCursor)
        
        body_layout.addWidget(self.table, 1)
        main_layout.addLayout(body_layout, 1)

        # Inline filter bar (hidden by default)
        self.filter_bar = QLineEdit()
        self.filter_bar.setPlaceholderText("Type to filter files... (Escape to close)")
        self.filter_bar.setObjectName("FilterBar")
        self.filter_bar.textChanged.connect(self.on_filter_changed)
        self.filter_bar.setVisible(False)
        main_layout.addWidget(self.filter_bar)

        # Proxy model for filtering
        self.proxy = QSortFilterProxyModel()
        self.proxy.setSourceModel(self.model)
        self.proxy.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.proxy.setFilterKeyColumn(0)

    def update_drive_bar(self):
        # Clear existing
        while self.drive_bar.count():
            item = self.drive_bar.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        for drive in get_drives():
            btn = QPushButton(drive.replace("\\", ""))
            btn.setFixedWidth(40)
            btn.setStyleSheet("padding: 2px; font-size: 9pt;")
            btn.setToolTip(f"Open drive {drive}")
            btn.clicked.connect(lambda checked, d=drive: self.refresh_path(d))
            self.drive_bar.addWidget(btn)
        self.drive_bar.addStretch()

    def update_sidebar(self):
        # Clear existing
        while self.sidebar.count():
            item = self.sidebar.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        for link in get_quick_links():
            btn = QPushButton()
            btn.setIcon(qta.icon(link["icon"], color="#cdd6f4"))
            btn.setFixedSize(32, 32)
            btn.setToolTip(link["name"])
            btn.clicked.connect(lambda checked, p=link["path"]: self.refresh_path(p))
            self.sidebar.addWidget(btn)

    def get_selected_paths(self):
        indices = self.table.selectionModel().selectedRows()
        if not indices:
            # Fallback to current index
            curr = self.table.currentIndex()
            if curr.isValid():
                indices = [curr]
                
        paths = []
        for index in indices:
            row = index.row()
            if self.filter_visible:
                row = self.proxy.mapToSource(index).row()
            file_info = self.model.get_file(row)
            if file_info and file_info.name != " .. ":
                paths.append(file_info.full_path)
        return paths


    def _enter_vfs(self, vfs, vfs_type, inner=""):
        """Enter VFS mode (archive, ftp, etc.)."""
        self._vfs = vfs
        self._vfs_type = vfs_type
        self._vfs_inner = inner
        self._refresh_vfs()

    def _vfs_preview(self, file_info):
        """Extract file from VFS to temp and preview."""
        import tempfile
        dest = tempfile.mkdtemp(prefix="kicmd_")
        extracted = self._vfs.extract_file(file_info.full_path, dest)
        if extracted and os.path.exists(extracted):
            self.preview_file(extracted)

    def _extract_here(self, file_info):
        """Extract selected item to current real directory."""
        self._vfs.extract_file(file_info.full_path, self.current_path)

    def _extract_all(self):
        """Extract entire VFS content to a chosen directory."""
        from PySide6.QtWidgets import QFileDialog
        dest = QFileDialog.getExistingDirectory(self, "Extract to...", self.current_path)
        if dest:
            self._vfs.extract_all(dest)

    def preview_file(self, path):
        if os.path.isfile(path):
            dlg = PreviewDialog(path, self)
            dlg.exec()

    def show_properties(self, path):
        dlg = PropertiesDialog(path, self)
        dlg.exec()

    def rename_file(self, file_info):
        new_name, ok = QInputDialog.getText(self, "Rename", "New name:", text=file_info.name)
        if ok and new_name and new_name != file_info.name:
            old = file_info.full_path
            new = os.path.join(os.path.dirname(old), new_name)
            try:
                os.rename(old, new)
                self.refresh_path(self.current_path)
            except OSError as e:
                QMessageBox.warning(self, "Rename Failed", str(e))

    def toggle_filter(self):
        self.filter_visible = not self.filter_visible
        self.filter_bar.setVisible(self.filter_visible)
        if self.filter_visible:
            self.table.setModel(self.proxy)
            self.filter_bar.setFocus()
        else:
            self.filter_bar.clear()
            self.table.setModel(self.model)
            self.table.setFocus()

    def on_filter_changed(self, text):
        self.proxy.setFilterFixedString(text)

    def eventFilter(self, source, event):
        if self.interaction_handler.eventFilter(source, event):
            return True
        return super().eventFilter(source, event)

    def refresh(self):
        """Standard refresh: works for both real filesystem and VFS."""
        if self._vfs:
            self._refresh_vfs()
        else:
            self.refresh_path(self.current_path)

    def refresh_path(self, path):
        # Exit VFS mode if entering a real path
        self._vfs = None
        self._vfs_inner = ""
        self._vfs_type = None

        new_abs = os.path.abspath(path)
        if self._locked and hasattr(self, 'current_path') and new_abs != self.current_path:
            # If locked, open in new tab instead
            tw = self.parent()
            while tw and not isinstance(tw, QTabWidget): tw = tw.parent()
            if tw:
                self.window().add_tab(tw, new_abs)
                return

        self.current_path = new_abs
        self.path_label.setText(self.current_path)
        self.breadcrumbs.set_path(self.current_path)
        self.folder_changed.emit(os.path.basename(self.current_path) or self.current_path)
        
        # Update history
        if not self.history or self.history[-1] != self.current_path:
            self.history.append(self.current_path)

        self.settings.setValue(f"panels/{self.panel_id}/path", self.current_path)
        
        # Update watcher to new directory
        watched = self._watcher.directories()
        if watched:
            self._watcher.removePaths(watched)
        if os.path.isdir(self.current_path):
            self._watcher.addPath(self.current_path)
        
        self.model.clear_for_scan()
        self.thread = ScanThread(self.current_path)
        self.thread.worker.chunk_filled.connect(self.model.add_files)
        self.thread.worker.finished.connect(self.on_scan_finished)
        self.thread.start()

    def _start_manual_drag(self):
        """Starts a manual QDrag for the selected items."""
        selected_indexes = self.table.selectionModel().selectedRows()
        if not selected_indexes:
            return

        drag = QDrag(self.table)
        mime_data = self.model.mimeData(selected_indexes)
        drag.setMimeData(mime_data)

        # Create a simple icon as drag pixmap
        pixmap = qta.icon("fa5s.clone", color="#89b4fa").pixmap(32, 32)
        drag.setPixmap(pixmap)
        drag.setHotSpot(pixmap.rect().center())

        # Force CopyAction so files are NEVER moved when dragging to desktop
        drag.exec(Qt.CopyAction)

    def _refresh_vfs(self):
        """List contents of the current VFS + inner path."""
        if not self._vfs: return
        
        display_path = self._vfs_inner if self._vfs_inner else "/"
        self.path_label.setText(f"[{self._vfs_type.upper()}] {display_path}")
        self.breadcrumbs.set_path(display_path, vfs_type=self._vfs_type)
        self.folder_changed.emit(f"[{self._vfs_type.upper()}] {os.path.basename(display_path) or '/'}")
        
        # Update history with VFS type tag
        vfs_tag = f"[{self._vfs_type.upper()}] {display_path}"
        if not self.history or self.history[-1] != vfs_tag:
            self.history.append(vfs_tag)
        
        self.model.clear_for_scan()
        # Use VfsThread for asynchronous listing
        self.thread = VfsThread(self._vfs, self._vfs_inner)
        self.thread.worker.chunk_filled.connect(self.model.add_files)
        self.thread.worker.finished.connect(self._on_vfs_scan_finished)
        self.thread.start()

    def _on_vfs_scan_finished(self, files):
        # Capture current selection
        prev_name = None
        prev_row = self.table.currentIndex().row() if self.table.currentIndex().isValid() else 0
        idx = self.table.currentIndex()
        if idx.isValid():
            fi = self.model.get_file(idx.row())
            if fi: prev_name = fi.name

        # Add '..' entry to go back
        up = FileInfo(name=" .. ", ext="", size="", date="", is_dir=True,
                      full_path="..")
        up._size_bytes = 0
        up._mtime = 0
        self.model.update_files([up] + files)
        
        self._restore_selection(prev_name, prev_row)

    def _restore_selection(self, prev_name, prev_row):
        """Restore selection and cursor based on filename or row index fallback."""
        row_to_select = 0
        
        # 1. Try to find by name
        if prev_name:
            for r in range(self.model.rowCount()):
                fi = self.model.get_file(r)
                if fi and fi.name == prev_name:
                    row_to_select = r
                    break
            else:
                # 2. Fallback to same index if name not found (e.g. after delete)
                row_to_select = min(prev_row, self.model.rowCount() - 1) if self.model.rowCount() > 0 else 0
        else:
            row_to_select = min(prev_row, self.model.rowCount() - 1) if self.model.rowCount() > 0 else 0

        new_idx = self.model.index(row_to_select, 0)
        self.table.selectionModel().clearSelection()
        self.table.selectRow(row_to_select)
        self.table.setCurrentIndex(new_idx)
        self.table.scrollTo(new_idx)

    def on_scan_finished(self, files):
        # Capture current selection
        prev_name = None
        prev_row = self.table.currentIndex().row() if self.table.currentIndex().isValid() else 0
        idx = self.table.currentIndex()
        if idx.isValid():
            fi = self.model.get_file(idx.row())
            if fi: prev_name = fi.name
        
        self.model.update_files(files)
        self.table.horizontalHeader().viewport().update()
        
        self._restore_selection(prev_name, prev_row)

    def _on_dir_changed(self, path):
        """Called by QFileSystemWatcher when directory contents change."""
        self._debounce.start()  # restart 300ms timer

    def _do_auto_refresh(self):
        """Debounced auto-refresh – re-scan current directory."""
        if os.path.isdir(self.current_path):
            self.thread = ScanThread(self.current_path)
            self.thread.worker.finished.connect(self.on_scan_finished)
            self.thread.start()

    def _on_header_clicked(self, col: int):
        """Toggle asc/desc on same column, switch to asc on new column."""
        if self.model._sort_col == col:
            order = Qt.DescendingOrder if self.model._sort_asc else Qt.AscendingOrder
        else:
            order = Qt.AscendingOrder
        self.model.sort(col, order)
        self.table.horizontalHeader().viewport().update()

    def on_breadcrumb_clicked(self, path):
        if self._vfs:
            self._vfs_inner = path
            self._refresh_vfs()
        else:
            self.refresh_path(path)

    def show_history(self):
        """Shows a popup menu with directory history."""
        if not self.history: return
        from PySide6.QtGui import QCursor
        menu = QMenu(self)
        menu.setStyleSheet("QMenu { background-color: #1e1e2e; color: #cdd6f4; border: 1px solid #45475a; }")
        
        # Show in reverse order (newest first)
        for p in list(reversed(self.history)):
            action = menu.addAction(p)
            # Capture p in lambda
            def navigate(target=p):
                if target.startswith("["):
                    tag_end = target.find("]")
                    if tag_end != -1:
                        self._vfs_inner = target[tag_end+2:]
                        self._refresh_vfs()
                else:
                    self.refresh_path(target)
            
            action.triggered.connect(navigate)
        
        # Position menu below breadcrumbs
        menu.exec(QCursor.pos())

    def on_double_click(self, index):
        row = index.row()
        if self.filter_visible:
            row = self.proxy.mapToSource(index).row()
        file_info = self.model.get_file(row)
        if not file_info:
            return

        # --- Inside VFS (archive, ftp, etc.) ---
        if self._vfs:
            if file_info.name == " .. ":
                if self._vfs_inner and self._vfs_inner not in ["/", ""]:
                    # Go up inside VFS
                    parts = self._vfs_inner.strip("/").rsplit("/", 1)
                    self._vfs_inner = "/" + parts[0] if len(parts) > 1 else "/"
                    if len(parts) == 1:
                        self._vfs_inner = "/"
                    self._refresh_vfs()
                else:
                    # Exit VFS back to real filesystem
                    self._vfs = None
                    self._vfs_inner = ""
                    self._vfs_type = None
                    self.refresh_path(self.current_path)
            elif file_info.is_dir:
                self._vfs_inner = file_info.full_path
                self._refresh_vfs()
            else:
                self._vfs_preview(file_info)
            return

        # --- Real filesystem ---
        if file_info.is_dir:
            if self.filter_visible:
                self.toggle_filter()
            self.refresh_path(file_info.full_path)
        elif is_archive(file_info.full_path):
            self._enter_vfs(ArchiveVFS(file_info.full_path), "archive")
        else:
            os.startfile(file_info.full_path)

    def get_selected_items(self):
        """Returns list of FileInfo objects for selected rows."""
        rows = set(index.row() for index in self.table.selectionModel().selectedRows())
        if self.filter_visible:
            rows = set(self.proxy.mapToSource(self.table.model().index(r, 0)).row() for r in rows)
        
        if not rows:
            # Fallback to current index if nothing selected
            curr = self.table.currentIndex()
            if curr.isValid():
                r = curr.row()
                if self.filter_visible: r = self.proxy.mapToSource(curr).row()
                rows = {r}

        items = []
        for r in sorted(rows):
            fi = self.model.get_file(r)
            if fi and fi.name != " .. ":
                items.append(fi)
        return items
