import sys
import os
import subprocess
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTableView, QHeaderView, QMenuBar, 
                             QLabel, QPushButton, QStatusBar, QLineEdit, QMessageBox,
                             QInputDialog, QMenu)
from PySide6.QtCore import Qt, QSettings, QPoint, QSize, QEvent, QSortFilterProxyModel, QFileSystemWatcher, QTimer
from PySide6.QtGui import QAction, QIcon, QPixmap
import qtawesome as qta
import ctypes

def get_assets_dir():
    """Return the assets directory regardless of whether we're running as a
    plain Python script or a PyInstaller bundle."""
    if getattr(sys, '_MEIPASS', None):
        # PyInstaller extracts everything to sys._MEIPASS at runtime
        return os.path.join(sys._MEIPASS, 'assets')
    else:
        # Running as a normal .py script from  src/
        src_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.abspath(os.path.join(src_dir, '..', 'assets'))

ASSETS_DIR = get_assets_dir()

from file_model import FileModel
from fs_worker import ScanThread
from file_ops import FileOpThread
from navigation_utils import get_drives, get_quick_links
from search_dialog import SearchDialog
from preview_dialog import PreviewDialog
from properties_dialog import PropertiesDialog

class FilePanel(QWidget):
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
        self._debounce.setInterval(300)  # 300ms debounce
        self._debounce.timeout.connect(self._do_auto_refresh)

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

        # Path label
        self.path_label = QLabel(self.current_path)
        self.path_label.setObjectName("PathLabel")
        self.path_label.setToolTip("Current directory path (Double-click or Enter to browse)")
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
        
        self.table.doubleClicked.connect(self.on_double_click)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        self.table.installEventFilter(self)
        
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

    def show_context_menu(self, pos):
        index = self.table.indexAt(pos)
        menu = QMenu(self)
        
        if index.isValid():
            row = index.row()
            if self.filter_visible:
                row = self.proxy.mapToSource(index).row()
            file_info = self.model.get_file(row)
            if file_info and file_info.name != "..":
                menu.addAction(qta.icon("fa5s.folder-open", color="#89b4fa"), "Open", lambda: self.on_double_click(index))
                menu.addSeparator()
                menu.addAction(qta.icon("fa5s.eye", color="#a6e3a1"), "Preview (F3)", lambda: self.preview_file(file_info.full_path))
                menu.addAction(qta.icon("fa5s.edit", color="#f9e2af"), "Rename (F2)", lambda: self.rename_file(file_info))
                menu.addSeparator()
                menu.addAction(qta.icon("fa5s.copy", color="#cdd6f4"), "Copy (F5)", lambda: None)
                menu.addAction(qta.icon("fa5s.external-link-alt", color="#cdd6f4"), "Move (F6)", lambda: None)
                menu.addAction(qta.icon("fa5s.trash-alt", color="#f38ba8"), "Delete (F8)", lambda: None)
                menu.addSeparator()
                menu.addAction(qta.icon("fa5s.info-circle", color="#cba6f7"), "Properties", lambda: self.show_properties(file_info.full_path))
        
        menu.addSeparator()
        menu.addAction(qta.icon("fa5s.sync", color="#89b4fa"), "Refresh", lambda: self.refresh_path(self.current_path))
        menu.addAction(qta.icon("fa5s.folder-plus", color="#a6e3a1"), "New Folder (F7)", lambda: None)
        menu.exec(self.table.viewport().mapToGlobal(pos))

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
        if event.type() == QEvent.KeyPress and source is self.table:
            # Enter to open
            if event.key() in (Qt.Key_Return, Qt.Key_Enter):
                index = self.table.currentIndex()
                if index.isValid():
                    self.on_double_click(index)
                    return True
            # Space to toggle selection (Total Commander style)
            elif event.key() == Qt.Key_Space:
                index = self.table.currentIndex()
                if index.isValid():
                    self.table.selectionModel().select(index, self.table.selectionModel().Toggle | self.table.selectionModel().Rows)
                    self.table.setCurrentIndex(self.model.index(index.row() + 1, 0))
                    return True
            # F2 to rename
            elif event.key() == Qt.Key_F2:
                index = self.table.currentIndex()
                if index.isValid():
                    file_info = self.model.get_file(index.row())
                    if file_info and file_info.name != "..":
                        self.rename_file(file_info)
                        return True
            # Escape to close filter
            elif event.key() == Qt.Key_Escape and self.filter_visible:
                self.toggle_filter()
                return True
        return super().eventFilter(source, event)

    def refresh_path(self, path):
        self.current_path = os.path.abspath(path)
        self.path_label.setText(self.current_path)
        self.settings.setValue(f"panels/{self.panel_id}/path", self.current_path)
        
        # Update watcher to new directory
        watched = self._watcher.directories()
        if watched:
            self._watcher.removePaths(watched)
        if os.path.isdir(self.current_path):
            self._watcher.addPath(self.current_path)
        
        self.thread = ScanThread(self.current_path)
        self.thread.worker.finished.connect(self.on_scan_finished)
        self.thread.start()

    def on_scan_finished(self, files):
        # Preserve current selection if this is an auto-refresh
        selected_name = None
        idx = self.table.currentIndex()
        if idx.isValid():
            fi = self.model.get_file(idx.row())
            if fi:
                selected_name = fi.name
        
        self.model.update_files(files)
        self.table.horizontalHeader().viewport().update()
        
        # Restore selection by name
        if selected_name:
            for row in range(self.model.rowCount()):
                fi = self.model.get_file(row)
                if fi and fi.name == selected_name:
                    self.table.selectRow(row)
                    return
        self.table.selectRow(0)

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

    def on_double_click(self, index):
        row = index.row()
        if self.filter_visible:
            row = self.proxy.mapToSource(index).row()
        file_info = self.model.get_file(row)
        if file_info:
            if file_info.is_dir:
                if self.filter_visible:
                    self.toggle_filter()
                self.refresh_path(file_info.full_path)
            else:
                os.startfile(file_info.full_path)

    def get_selected_paths(self):
        indices = self.table.selectionModel().selectedRows()
        paths = []
        for idx in indices:
            f = self.model.get_file(idx.row())
            if f and f.name != "..":
                paths.append(f.full_path)
        return paths

class CustomTitleBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setFixedHeight(35)
        self.setObjectName("TitleBar")
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 0, 0)
        layout.setSpacing(0)
        
        # Icon and title
        self.icon_label = QLabel()
        icon_path = os.path.join(ASSETS_DIR, "icon.png")
        if os.path.exists(icon_path):
            self.icon_label.setPixmap(QPixmap(icon_path).scaled(22, 22, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            self.icon_label.setPixmap(qta.icon("fa5s.rocket", color="#89b4fa").pixmap(22, 22))
        layout.addWidget(self.icon_label)
        
        self.title_label = QLabel("KiCommander Desktop")
        self.title_label.setObjectName("TitleLabel")
        layout.addWidget(self.title_label)
        
        layout.addStretch()
        
        # Window buttons
        btn_style = "QPushButton { border: none; padding: 5px; background: transparent; } QPushButton:hover { background-color: #313244; }"
        
        self.min_btn = QPushButton()
        self.min_btn.setIcon(qta.icon("fa5s.minus", color="#cdd6f4"))
        self.min_btn.setStyleSheet(btn_style)
        self.min_btn.clicked.connect(self.parent.showMinimized)
        layout.addWidget(self.min_btn)
        
        self.max_btn = QPushButton()
        self.max_btn.setIcon(qta.icon("fa5s.expand", color="#cdd6f4"))
        self.max_btn.setStyleSheet(btn_style)
        self.max_btn.clicked.connect(self.toggle_maximize)
        layout.addWidget(self.max_btn)
        
        self.close_btn = QPushButton()
        self.close_btn.setIcon(qta.icon("fa5s.times", color="#cdd6f4"))
        self.close_btn.setStyleSheet("QPushButton { border: none; padding: 5px; background: transparent; } QPushButton:hover { background-color: #f38ba8; }")
        self.close_btn.clicked.connect(self.parent.close)
        layout.addWidget(self.close_btn)
        
        self.drag_pos = None

    def toggle_maximize(self):
        if self.parent.isMaximized():
            self.parent.showNormal()
            self.max_btn.setIcon(qta.icon("fa5s.expand", color="#cdd6f4"))
        else:
            self.parent.showMaximized()
            self.max_btn.setIcon(qta.icon("fa5s.compress", color="#cdd6f4"))

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_pos = event.globalPos() - self.parent.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self.drag_pos:
            self.parent.move(event.globalPos() - self.drag_pos)
            event.accept()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.toggle_maximize()

class KiCommander(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        self.setWindowTitle("KiCommander Desktop")
        icon_path = os.path.join(ASSETS_DIR, "icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        else:
            icon_path = os.path.join(ASSETS_DIR, "icon.png")
            if os.path.exists(icon_path):
                self.setWindowIcon(QIcon(icon_path))
            else:
                self.setWindowIcon(qta.icon("fa5s.rocket", color="#89b4fa"))
        self.settings = QSettings("KiCommander", "Desktop")
        self.drag_pos = None
        self._dragging = False
        
        self.restoreGeometry(self.settings.value("window/geometry", b""))
        self.restoreState(self.settings.value("window/state", b""))
        if not self.geometry().isValid():
            self.resize(1200, 800)

        self.setup_ui()

    def setup_ui(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu("&Files")
        file_menu.addAction("Exit", self.close, "Alt+F4")
        
        cmd_menu = menubar.addMenu("&Commands")
        cmd_menu.addAction("Refresh", self.refresh_all, "Ctrl+R")
        cmd_menu.addAction("Search (Alt+F7)", self.op_search, "Alt+F7")
        cmd_menu.addAction("Filter (Ctrl+F)", self.op_filter, "Ctrl+F")
        
        # Enable dragging through the menubar
        menubar.installEventFilter(self)

        central_widget = QWidget()
        central_widget.setObjectName("CentralWidget")
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Title Bar
        self.title_bar = CustomTitleBar(self)
        main_layout.addWidget(self.title_bar)

        # Content Widget
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.addWidget(content_widget, 1)

        panels_layout = QHBoxLayout()
        self.left_panel = FilePanel("left", os.path.expanduser("~"))
        self.right_panel = FilePanel("right", "C:\\")
        
        panels_layout.addWidget(self.left_panel)
        panels_layout.addWidget(self.right_panel)
        content_layout.addLayout(panels_layout, 1)

        # Command Line
        cmd_layout = QHBoxLayout()
        cmd_label = QLabel("Command:")
        cmd_label.setToolTip("Enter system commands to execute in the current path")
        cmd_layout.addWidget(cmd_label)
        self.cmd_input = QLineEdit()
        self.cmd_input.setToolTip("Type command and press Enter (e.g., notepad, cmd, or python script)")
        self.cmd_input.returnPressed.connect(self.execute_command)
        cmd_layout.addWidget(self.cmd_input)
        content_layout.addLayout(cmd_layout)

        # Bottom Buttons
        btn_layout = QHBoxLayout()
        self.btn_configs = [
            ("F3 View", "eye", self.op_view, "Preview file content (text, image, hex)"),
            ("F4 Edit", "edit", self.op_edit, "Open file in default editor"),
            ("F5 Copy", "copy", self.op_copy, "Copy selected files to target panel"),
            ("F6 Move", "external-link-alt", self.op_move, "Move selected files to target panel"),
            ("F7 NewFolder", "folder-plus", self.op_mkdir, "Create a new directory"),
            ("F8 Delete", "trash-alt", self.op_delete, "Delete selected files permanently"),
            ("Alt+F4 Exit", "times-circle", self.close, "Close application")
        ]
        
        for text, icon_name, callback, tooltip in self.btn_configs:
            btn = QPushButton(text)
            btn.setIcon(qta.icon(f"fa5s.{icon_name}", color="#cdd6f4"))
            btn.setToolTip(tooltip)
            btn.clicked.connect(callback)
            btn_layout.addWidget(btn)
        
        content_layout.addLayout(btn_layout)

        # Status Bar
        self.sb = QStatusBar()
        content_layout.addWidget(self.sb)
        self.sb.showMessage("Ready")

    def get_active_panel(self):
        return self.left_panel if self.left_panel.table.hasFocus() else self.right_panel

    def get_target_panel(self):
        return self.right_panel if self.left_panel.table.hasFocus() else self.left_panel

    def execute_command(self):
        cmd = self.cmd_input.text()
        if not cmd: return
        active_path = self.get_active_panel().current_path
        try:
            subprocess.Popen(cmd, shell=True, cwd=active_path)
            self.cmd_input.clear()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to run command: {e}")

    def refresh_all(self):
        self.left_panel.refresh_path(self.left_panel.current_path)
        self.right_panel.refresh_path(self.right_panel.current_path)

    def eventFilter(self, source, event):
        if source is self.menuBar():
            if event.type() == QEvent.MouseButtonPress:
                if event.button() == Qt.LeftButton:
                    # Record anchor but DON'T consume event – menu items must still work
                    self.drag_pos = event.globalPos() - self.frameGeometry().topLeft()
                    self._dragging = False
                    return False  # pass through so menu opens normally
            elif event.type() == QEvent.MouseMove:
                if event.buttons() == Qt.LeftButton and self.drag_pos:
                    delta = event.globalPos() - (self.drag_pos + self.frameGeometry().topLeft())
                    if not self._dragging and delta.manhattanLength() > 5:
                        self._dragging = True
                    if self._dragging:
                        self.move(event.globalPos() - self.drag_pos)
                        return True
            elif event.type() == QEvent.MouseButtonRelease:
                self.drag_pos = None
                self._dragging = False
        return super().eventFilter(source, event)

    def op_view(self):
        active = self.get_active_panel()
        indices = active.table.selectionModel().selectedRows()
        if indices:
            row = indices[0].row()
            f = active.model.get_file(row)
            if f and not f.is_dir:
                active.preview_file(f.full_path)

    def op_edit(self):
        active = self.get_active_panel()
        indices = active.table.selectionModel().selectedRows()
        if indices:
            row = indices[0].row()
            f = active.model.get_file(row)
            if f and not f.is_dir:
                os.startfile(f.full_path)

    def op_search(self):
        active = self.get_active_panel()
        dlg = SearchDialog(active.current_path, self)
        dlg.navigate_to.connect(active.refresh_path)
        dlg.exec()

    def op_filter(self):
        active = self.get_active_panel()
        active.toggle_filter()

    def op_mkdir(self):
        active = self.get_active_panel()
        name, ok = QInputDialog.getText(self, "New Folder", "Name:")
        if ok and name:
            path = os.path.join(active.current_path, name)
            self.run_op('mkdir', [path])

    def op_delete(self):
        paths = self.get_active_panel().get_selected_paths()
        if not paths: return
        
        reply = QMessageBox.question(self, "Confirm Delete", 
                                   f"Are you sure you want to delete {len(paths)} items?",
                                   QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.run_op('delete', paths)

    def op_copy(self):
        self.file_op_dialog('copy')

    def op_move(self):
        self.file_op_dialog('move')

    def file_op_dialog(self, op_type):
        active = self.get_active_panel()
        target = self.get_target_panel()
        paths = active.get_selected_paths()
        if not paths: return
        
        self.run_op(op_type, paths, target.current_path)

    def run_op(self, op_type, sources, target=None):
        self.statusBar().showMessage(f"Running {op_type}...")
        self.op_thread = FileOpThread(op_type, sources, target)
        self.op_thread.worker.finished.connect(self.on_op_finished)
        self.op_thread.start()

    def on_op_finished(self, success, message):
        self.statusBar().showMessage(message)
        if not success:
            QMessageBox.warning(self, "Operation Failed", message)
        self.refresh_all()

    def keyPressEvent(self, event):
        key = event.key()
        mods = event.modifiers()
        if key == Qt.Key_F3: self.op_view()
        elif key == Qt.Key_F4: self.op_edit()
        elif key == Qt.Key_F5: self.op_copy()
        elif key == Qt.Key_F6: self.op_move()
        elif key == Qt.Key_F7: self.op_mkdir()
        elif key == Qt.Key_F8: self.op_delete()
        elif key == Qt.Key_F7 and mods & Qt.AltModifier: self.op_search()
        elif key == Qt.Key_F and mods & Qt.ControlModifier: self.op_filter()
        elif key == Qt.Key_Tab:
            if self.left_panel.table.hasFocus(): self.right_panel.table.setFocus()
            else: self.left_panel.table.setFocus()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event):
        self.settings.setValue("window/geometry", self.saveGeometry())
        self.settings.setValue("window/state", self.saveState())
        super().closeEvent(event)

if __name__ == "__main__":
    # Force Taskbar Icon on Windows
    try:
        myappid = 'KiCommander.Desktop.v1'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except Exception:
        pass

    app = QApplication(sys.argv)
    
    # Load stylesheet
    style_path = os.path.join(ASSETS_DIR, "style.qss")
    if os.path.exists(style_path):
        with open(style_path, "r") as f:
            app.setStyleSheet(f.read())
    else:
        app.setStyle("Fusion")
    
    window = KiCommander()
    
    # Set App Icon
    icon_path = os.path.join(ASSETS_DIR, "icon.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    else:
        icon_path = os.path.join(ASSETS_DIR, "icon.png")
        if os.path.exists(icon_path):
            app.setWindowIcon(QIcon(icon_path))
        else:
            app.setWindowIcon(qta.icon("fa5s.rocket", color="#89b4fa"))
    
    window.show()
    sys.exit(app.exec())
