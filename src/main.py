import sys
import os
from collections import deque
import subprocess
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QMenuBar, QLabel, QStatusBar, QLineEdit, 
                             QMessageBox, QMenu, QTabWidget)
from PySide6.QtCore import Qt, QSettings, QEvent
from PySide6.QtGui import QAction, QIcon
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

from queue_manager import QueueManager
from transfer_manager_view import TransferManagerWidget
from plugin_manager import discover_plugins

from ui.title_bar import CustomTitleBar
from ui.panels.file_panel import FilePanel
from action_manager import ActionManager

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
        self._last_active_panel = None
        
        # Initialize Action Manager
        self.actions = ActionManager(self)
        
        self.restoreGeometry(self.settings.value("window/geometry", b""))
        self.restoreState(self.settings.value("window/state", b""))
        if not self.geometry().isValid():
            self.resize(1200, 800)

        self.setup_ui()

    def setup_ui(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu("Files")
        file_menu.addAction(qta.icon("fa5s.cog", color="#94e2d5"), "Settings", self.actions.op_settings)
        file_menu.addSeparator()
        file_menu.addAction("Exit", self.close, "Alt+F4")
        
        cmd_menu = menubar.addMenu("Commands")
        cmd_menu.addAction("Refresh", self.refresh_all, "Ctrl+R")
        cmd_menu.addAction("Search", self.actions.op_search, "Alt+F7")
        cmd_menu.addAction("Filter", self.actions.op_filter, "Ctrl+F")
        cmd_menu.addAction(qta.icon("fa5s.globe", color="#f9e2af"), "Connect to FTP", self.actions.op_connect_ftp, "Ctrl+K")
        cmd_menu.addAction(qta.icon("fa5s.lock", color="#a6e3a1"), "Connect to SFTP/SSH", self.actions.op_connect_sftp, "Ctrl+Shift+K")
        cmd_menu.addAction(qta.icon("fa5s.server", color="#cba6f7"), "Connect to SMB/Windows Share", self.actions.op_connect_smb, "Ctrl+M")
        cmd_menu.addSeparator()
        cmd_menu.addAction(qta.icon("fa5s.bookmark", color="#fab387"), "Saved Connections…", self.actions.op_connection_manager, "Ctrl+L")
        cmd_menu.addSeparator()
        cmd_menu.addAction(qta.icon("fa5s.star", color="#f9e2af"), "Favorites (Hotlist)", self.actions.op_favorites, "Ctrl+D")
        cmd_menu.addAction(qta.icon("fa5s.columns", color="#89dceb"), "Compare Files (Side-by-side)", self.actions.op_compare, "Ctrl+Alt+D")
        cmd_menu.addAction(qta.icon("fa5s.copy", color="#f5c2e7"), "Find Duplicate Files", self.actions.op_find_duplicates, "Ctrl+Shift+D")
        cmd_menu.addAction(qta.icon("fa5s.edit", color="#89b4fa"), "Multi-Rename Tool", self.actions.op_multi_rename, "F11")
        cmd_menu.addAction(qta.icon("fa5s.sync", color="#89b4fa"), "Synchronize Directories", self.actions.op_sync, "Alt+Y")

        # Load plugins
        if getattr(sys, '_MEIPASS', None):
            plugins_dir = os.path.join(sys._MEIPASS, "plugins")
        else:
            plugins_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "plugins")
        self._plugins = discover_plugins(plugins_dir)
        if self._plugins:
            cmd_menu.addSeparator()
            for plugin in self._plugins:
                cmd_menu.addAction(
                    qta.icon("fa5s.puzzle-piece", color="#cba6f7"),
                    plugin.menu_text,
                    lambda p=plugin: self.actions.run_plugin(p)
                )

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
        panels_layout.setSpacing(5)
        
        # Left Tabs
        from PySide6.QtWidgets import QTabWidget, QTabBar
        self.left_tabs = QTabWidget()
        self.left_tabs.setTabsClosable(True)
        self.left_tabs.tabCloseRequested.connect(lambda i: self.close_tab(self.left_tabs, i))
        
        # Right Tabs
        self.right_tabs = QTabWidget()
        self.right_tabs.setTabsClosable(True)
        self.right_tabs.tabCloseRequested.connect(lambda i: self.close_tab(self.right_tabs, i))
        self.right_tabs.setContextMenuPolicy(Qt.CustomContextMenu)
        self.right_tabs.customContextMenuRequested.connect(lambda p: self._tab_context_menu(self.right_tabs, p))
        
        self.left_tabs.setContextMenuPolicy(Qt.CustomContextMenu)
        self.left_tabs.customContextMenuRequested.connect(lambda p: self._tab_context_menu(self.left_tabs, p))
        
        panels_layout.addWidget(self.left_tabs)
        panels_layout.addWidget(self.right_tabs)
        content_layout.addLayout(panels_layout, 1)

        # Initialize with saved or default tabs
        self.init_tabs()

        # Signal handling for focus tracking
        # (This will be done during add_tab)

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
            ("F3 View", "eye", self.actions.op_view, "Preview file content (text, image, hex)"),
            ("F4 Edit", "edit", self.actions.op_edit, "Open file in default editor"),
            ("F5 Copy", "copy", self.actions.op_copy, "Copy selected files to target panel"),
            ("F6 Move", "external-link-alt", self.actions.op_move, "Move selected files to target panel"),
            ("F7 NewFolder", "folder-plus", self.actions.op_mkdir, "Create a new directory"),
            ("F8 Delete", "trash-alt", self.actions.op_delete, "Delete selected files permanently"),
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

        # --- Transfer Manager Dock ---
        from PySide6.QtWidgets import QDockWidget
        self.transfer_dock = QDockWidget("Transfer Manager", self)
        self.transfer_widget = TransferManagerWidget(self)
        self.transfer_dock.setWidget(self.transfer_widget)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.transfer_dock)
        
        # The QueueManager signal is now handled by ActionManager
        # self.actions.on_queue_overwrite is already connected in ActionManager.__init__

    def get_active_panel(self):
        if self._last_active_panel:
            return self._last_active_panel
        return self.left_tabs.currentWidget()

    def get_target_panel(self):
        active = self.get_active_panel()
        if active in [self.left_tabs.widget(i) for i in range(self.left_tabs.count())]:
            return self.right_tabs.currentWidget()
        else:
            return self.left_tabs.currentWidget()

    def execute_command(self):
        cmd = self.cmd_input.text()
        if not cmd: return
        
        active = self.get_active_panel()
        if active._vfs_type == "sftp" and hasattr(active._vfs, 'exec_command'):
            # Remote command via SSH
            try:
                output = active._vfs.exec_command(cmd, active._vfs_inner)
                QMessageBox.information(self, "Remote Command Output", output)
                self.cmd_input.clear()
            except Exception as e:
                QMessageBox.critical(self, "Remote Error", f"Command failed: {e}")
            return

        active_path = active.current_path
        try:
            subprocess.Popen(cmd, shell=True, cwd=active_path)
            self.cmd_input.clear()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to run command: {e}")

    def refresh_all(self):
        if self.left_tabs.currentWidget(): self.left_tabs.currentWidget().refresh()
        if self.right_tabs.currentWidget(): self.right_tabs.currentWidget().refresh()

    def init_tabs(self):
        # Default fallback
        left_path = self.settings.value("panels/left/path", os.expanduser("~") if hasattr(os, 'expanduser') else os.path.expanduser("~"))
        right_path = self.settings.value("panels/right/path", "C:\\")
        
        self.add_tab(self.left_tabs, left_path)
        self.add_tab(self.right_tabs, right_path)
        
        self._last_active_panel = self.left_tabs.currentWidget()

    def add_tab(self, tab_widget, path):
        panel_id = "left" if tab_widget == self.left_tabs else "right"
        panel = FilePanel(panel_id, path)
        panel.got_focus.connect(self._on_panel_focus)
        panel.folder_changed.connect(lambda p, t=tab_widget, w=panel: self._update_tab_title(t, w, p))
        
        idx = tab_widget.addTab(panel, os.path.basename(path) or path)
        tab_widget.setCurrentIndex(idx)
        return panel

    def close_tab(self, tab_widget, index):
        if tab_widget.count() > 1:
            w = tab_widget.widget(index)
            tab_widget.removeTab(index)
            w.deleteLater()

    def _on_panel_focus(self, panel):
        self._last_active_panel = panel

    def _update_tab_title(self, tab_widget, panel, title):
        idx = tab_widget.indexOf(panel)
        if idx != -1:
            lock_icon = " 🔒" if panel._locked else ""
            tab_widget.setTabText(idx, title + lock_icon)

    def _tab_context_menu(self, tab_widget, pos):
        idx = tab_widget.tabBar().tabAt(pos)
        if idx == -1: return
        
        panel = tab_widget.widget(idx)
        menu = QMenu(self)
        menu.setStyleSheet("QMenu { background-color: #1e1e2e; color: #cdd6f4; border: 1px solid #45475a; }")
        
        lock_act = menu.addAction("Lock Tab" if not panel._locked else "Unlock Tab")
        def toggle_lock():
            panel._locked = not panel._locked
            self._update_tab_title(tab_widget, panel, tab_widget.tabText(idx).replace(" 🔒", ""))
        lock_act.triggered.connect(toggle_lock)
        
        menu.addAction("Close Tab", lambda: self.close_tab(tab_widget, idx))
        menu.exec(QCursor.pos())

    def eventFilter(self, source, event):
        if source is self.menuBar():
            if event.type() == QEvent.MouseButtonPress:
                if event.button() == Qt.LeftButton:
                    self.drag_pos = event.globalPos() - self.frameGeometry().topLeft()
                    self._dragging = False
                    return False
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
        
        # Track focus for panels
        if event.type() == QEvent.FocusIn:
            if source is self.left_panel.table:
                self._last_active_panel = self.left_panel
            elif source is self.right_panel.table:
                self._last_active_panel = self.right_panel

        return super().eventFilter(source, event)








    def keyPressEvent(self, event):
        key = event.key()
        mods = event.modifiers()
        if key == Qt.Key_F3: self.actions.op_view()
        elif key == Qt.Key_F4: self.actions.op_edit()
        elif key == Qt.Key_F5: self.actions.op_copy()
        elif key == Qt.Key_F6: self.actions.op_move()
        elif key == Qt.Key_F7: self.actions.op_mkdir()
        elif key == Qt.Key_F8: self.actions.op_delete()
        elif key == Qt.Key_F11: self.actions.op_multi_rename()
        elif key == Qt.Key_D and mods & Qt.ControlModifier: self.actions.op_favorites()
        elif key == Qt.Key_D and (mods & Qt.ControlModifier) and (mods & Qt.AltModifier): self.actions.op_compare()
        elif key == Qt.Key_F5 and mods & Qt.AltModifier: self.actions.op_archive()
        elif key == Qt.Key_F7 and mods & Qt.AltModifier: self.actions.op_search()
        elif key == Qt.Key_F and mods & Qt.ControlModifier: self.actions.op_filter()
        elif key == Qt.Key_C and mods & Qt.ControlModifier: self.actions.op_clipboard_copy(False)
        elif key == Qt.Key_X and mods & Qt.ControlModifier: self.actions.op_clipboard_copy(True)
        elif key == Qt.Key_V and mods & Qt.ControlModifier: self.actions.op_clipboard_paste()
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
    if sys.platform == "win32":
        try:
            import ctypes
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
