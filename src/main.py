import sys
import os
from collections import deque
import subprocess
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QMenuBar, QLabel, QStatusBar, QLineEdit, 
                             QMessageBox, QMenu, QTabWidget, QPushButton)
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
from theme_manager import ThemeManager

from ui.title_bar import CustomTitleBar
from ui.panels.file_panel import FilePanel
from action_manager import ActionManager
from logger import setup_logger, log
from event_bus import bus

class KiCommander(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        self.setWindowTitle("KiCommander Desktop")
        self.settings = QSettings("KiCommander", "Desktop")

        icon_name = self.settings.value("appearance/app_icon", "icon.png")
        icon_path_assets = os.path.join(ASSETS_DIR, icon_name)
        icon_path_icons = os.path.join(ASSETS_DIR, "icons", icon_name)
        
        if os.path.exists(icon_path_icons):
            self.setWindowIcon(QIcon(icon_path_icons))
        elif os.path.exists(icon_path_assets):
            self.setWindowIcon(QIcon(icon_path_assets))
        else:
            self.setWindowIcon(qta.icon("fa5s.rocket", color="#89b4fa"))


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
        file_menu.addAction(qta.icon("fa5s.cog", color="#94e2d5"), "Settings", lambda: bus.action_requested.emit("settings"))
        file_menu.addSeparator()
        file_menu.addAction("Exit", self.close, "Alt+F4")
        
        cmd_menu = menubar.addMenu("Commands")
        cmd_menu.addAction("Refresh", self.refresh_all, "Ctrl+R")
        cmd_menu.addAction("Search", lambda: bus.action_requested.emit("search"), "Alt+F7")
        cmd_menu.addAction("Filter", lambda: bus.action_requested.emit("filter"), "Ctrl+F")
        cmd_menu.addAction(qta.icon("fa5s.globe", color="#f9e2af"), "Connect to FTP", lambda: bus.action_requested.emit("connect_ftp"), "Ctrl+K")
        cmd_menu.addAction(qta.icon("fa5s.lock", color="#a6e3a1"), "Connect to SFTP/SSH", lambda: bus.action_requested.emit("connect_sftp"), "Ctrl+Shift+K")
        cmd_menu.addAction(qta.icon("fa5s.server", color="#cba6f7"), "Connect to SMB/Windows Share", lambda: bus.action_requested.emit("connect_smb"), "Ctrl+M")
        cmd_menu.addAction(qta.icon("fa5.google", color="#89b4fa"), "Connect to Google Drive", lambda: bus.action_requested.emit("connect_gdrive"))
        cmd_menu.addSeparator()
        cmd_menu.addAction(qta.icon("fa5s.bookmark", color="#fab387"), "Saved Connections…", lambda: bus.action_requested.emit("connection_manager"), "Ctrl+L")
        cmd_menu.addSeparator()
        cmd_menu.addAction(qta.icon("fa5s.star", color="#f9e2af"), "Favorites (Hotlist)", lambda: bus.action_requested.emit("favorites"), "Ctrl+D")
        cmd_menu.addAction(qta.icon("fa5s.columns", color="#89dceb"), "Compare Files (Side-by-side)", lambda: bus.action_requested.emit("compare"), "Ctrl+Alt+D")
        cmd_menu.addAction(qta.icon("fa5s.copy", color="#f5c2e7"), "Find Duplicate Files", lambda: bus.action_requested.emit("duplicates"), "Ctrl+Shift+D")
        cmd_menu.addAction(qta.icon("fa5s.edit", color="#89b4fa"), "Multi-Rename Tool", lambda: bus.action_requested.emit("multi_rename"), "F11")
        cmd_menu.addAction(qta.icon("fa5s.sync", color="#89b4fa"), "Synchronize Directories", lambda: bus.action_requested.emit("sync"), "Alt+Y")

        # Operations shortcuts (F3-F10)
        for text, key, route in [
            ("View", "F3", "view"),
            ("Edit", "F4", "edit"),
            ("Copy", "F5", "copy"),
            ("Move", "F6", "move"),
            ("New Folder", "F7", "mkdir"),
            ("Delete", "F8", "delete"),
            ("Rename", "Shift+F6", "rename"),
            ("Properties", "Alt+Return", "properties")
        ]:
            action = QAction(text, self)
            action.setShortcut(key)
            action.setShortcutContext(Qt.ApplicationShortcut)
            # Use default argument binding so lambda captures the current `route`
            action.triggered.connect(lambda checked=False, r=route: bus.action_requested.emit(r))
            self.addAction(action)
            
        exit_action = QAction("Exit", self)
        exit_action.setShortcut("F10")
        exit_action.setShortcutContext(Qt.ApplicationShortcut)
        exit_action.triggered.connect(self.close)
        self.addAction(exit_action)
        
        quickview_action = QAction("Toggle Quick View", self)
        quickview_action.setShortcut("Ctrl+Q")
        quickview_action.setShortcutContext(Qt.ApplicationShortcut)
        quickview_action.triggered.connect(lambda: bus.toggle_quick_view.emit())
        self.addAction(quickview_action)

        terminal_action_f9 = QAction("Toggle Terminal", self)
        terminal_action_f9.setShortcut("F9")
        terminal_action_f9.setShortcutContext(Qt.ApplicationShortcut)
        terminal_action_f9.triggered.connect(lambda: bus.toggle_terminal.emit())
        self.addAction(terminal_action_f9)
        
        terminal_action_tilde = QAction("Toggle Terminal (Alt)", self)
        terminal_action_tilde.setShortcut("Ctrl+`")
        terminal_action_tilde.setShortcutContext(Qt.ApplicationShortcut)
        terminal_action_tilde.triggered.connect(lambda: bus.toggle_terminal.emit())
        self.addAction(terminal_action_tilde)

        tree_action = QAction("Toggle Directory Tree", self)
        tree_action.setShortcut("Alt+F10")
        tree_action.setShortcutContext(Qt.ApplicationShortcut)
        tree_action.triggered.connect(lambda: bus.toggle_tree.emit())
        self.addAction(tree_action)


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

        # Použití QSplitter pro nastavitelnou šířku všech 3 panelů
        from PySide6.QtWidgets import QSplitter, QTabWidget, QTabBar
        self.main_splitter = QSplitter(Qt.Horizontal)
        
        # Left Tabs
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
        
        # Directory Tree Panel
        from directory_tree import DirectoryTreeWidget
        self.tree_widget = DirectoryTreeWidget(self)
        self.tree_widget.hide() # Hidden by default
        
        self.main_splitter.addWidget(self.tree_widget)
        self.main_splitter.addWidget(self.left_tabs)
        self.main_splitter.addWidget(self.right_tabs)
        
        # Quick View Panel
        from quick_view_widget import QuickViewWidget
        self.quick_view = QuickViewWidget(self)
        self.quick_view.hide() # Hidden by default
        self.main_splitter.addWidget(self.quick_view)
        
        # Nastavení výchozích proporcí (tree 0, levý a pravý maj víc místa, quick_view 0 - skrytý)
        self.main_splitter.setSizes([0, 450, 450, 0])
        
        self.vertical_splitter = QSplitter(Qt.Vertical)
        self.vertical_splitter.addWidget(self.main_splitter)
        
        # Terminal Widget
        from terminal_widget import TerminalWidget
        self.terminal_widget = TerminalWidget(self)
        self.terminal_widget.hide() # Hidden by default
        self.vertical_splitter.addWidget(self.terminal_widget)
        self.vertical_splitter.setSizes([800, 0])
        self.vertical_splitter.setChildrenCollapsible(False)
        
        content_layout.addWidget(self.vertical_splitter, 1)

        # Initialize with saved or default tabs
        self.init_tabs()

        # Signal handling for focus tracking
        # (This will be done during add_tab)

        # Command Line
        cmd_layout = QHBoxLayout()
        cmd_layout.setContentsMargins(5, 0, 5, 0)
        cmd_label = QLabel("Command:")
        cmd_label.setObjectName("CommandLabel")
        cmd_label.setToolTip("Enter system commands to execute in the current path")
        cmd_layout.addWidget(cmd_label)
        self.cmd_input = QLineEdit()
        self.cmd_input.setToolTip("Type command and press Enter (e.g., notepad, cmd, or python script)")
        self.cmd_input.returnPressed.connect(self.execute_command)
        cmd_layout.addWidget(self.cmd_input)
        content_layout.addLayout(cmd_layout)

        # Bottom Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(2)
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
            btn.setMinimumHeight(35)
            btn_layout.addWidget(btn)
        
        content_layout.addLayout(btn_layout)

        # Status Bar
        self.sb = QStatusBar()
        self.sb.setObjectName("MainStatusBar")
        self.sb.setFixedHeight(25)
        content_layout.addWidget(self.sb)
        self.sb.showMessage("Ready")

        # --- Transfer Manager (Integrated) ---
        self.transfer_widget = TransferManagerWidget(self)
        self.transfer_widget.setVisible(False) # Hidden by default
        content_layout.addWidget(self.transfer_widget)
        
        # The QueueManager signal is now handled by ActionManager
        # self.actions.on_queue_overwrite is already connected in ActionManager.__init__
        
        # --- Event Bus Subscription ---
        bus.selection_changed.connect(self._on_selection_changed)
        bus.toggle_quick_view.connect(self.toggle_quick_view_panel)
        bus.toggle_terminal.connect(self.toggle_terminal_panel)
        bus.toggle_tree.connect(self.toggle_tree_panel)
        bus.app_icon_changed.connect(self.update_app_icon)
        bus.app_theme_changed.connect(self.update_app_theme)

    def _on_selection_changed(self, file_info):
        """Reaguje na EventBus, když uživatel změní kurzor v aktivní tabulce."""
        if not self.quick_view.isVisible():
            return
            
        if file_info:
            self.quick_view.load_file(file_info.full_path)
        else:
            self.quick_view.load_file(None)

    def update_app_icon(self, icon_name):
        """Dynamically updates the window icon."""
        icon_path_assets = os.path.join(ASSETS_DIR, icon_name)
        icon_path_icons = os.path.join(ASSETS_DIR, "icons", icon_name)
        
        icon = None
        if os.path.exists(icon_path_icons):
            icon = QIcon(icon_path_icons)
        elif os.path.exists(icon_path_assets):
            icon = QIcon(icon_path_assets)
        else:
            icon = qta.icon("fa5s.rocket", color="#89b4fa")
            
        if icon:
            self.setWindowIcon(icon)
            # We also need to update the title bar icon label if it exists
            if hasattr(self, 'title_bar'):
                self.title_bar.update_icon(icon_name)

    def update_app_theme(self, theme_name):
        """Dynamically updates the application theme."""
        style_path = os.path.join(ASSETS_DIR, "style.qss")
        app = QApplication.instance()
        if app and os.path.exists(style_path):
            ThemeManager.apply_theme(app, style_path, theme_name)

    def toggle_quick_view_panel(self):
        """Skryje/Odhalí náhledový panel s plynulou úpravou proporcí."""
        if self.quick_view.isVisible():
            self.quick_view.hide()
            self.main_splitter.setSizes([450, 450, 0])
        else:
            self.quick_view.show()
            # Sebereme prostor napůl
            w = self.main_splitter.width()
            pW = int(w * 0.4)
            qW = w - 2 * pW
            self.main_splitter.setSizes([pW, pW, qW])
            
            # Nasimulujeme update pro naběhnutí souboru
            active = self.get_active_panel()
            if active and hasattr(active, "get_selected_paths"):
                 paths = active.get_selected_paths()
                 if paths:
                     # Hack: Simulovat ztrátu a nabytí focusu nebo prostě reload u view
                     self.quick_view.load_file(paths[0])
                     
    def toggle_terminal_panel(self):
        """Skryje/Odhalí vestavěný terminál na spodu obrazovky."""
        if self.terminal_widget.isVisible():
            self.terminal_widget.hide()
            self.terminal_widget.stop()
            self.vertical_splitter.setSizes([self.height(), 0])
        else:
            self.terminal_widget.show()
            h = self.vertical_splitter.height()
            self.vertical_splitter.setSizes([int(h * 0.7), int(h * 0.3)])
            self.terminal_widget.term.setFocus()
            
            # Start proper session
            panel = self.get_active_panel()
            if panel and getattr(panel, "_vfs", None):
                if type(panel._vfs).__name__ == "SFTPVFS":
                    self.terminal_widget.start_ssh(panel._vfs)
                else:
                    self.terminal_widget.start_local() # Fallback
            else:
                path = panel.current_path if panel else None
                self.terminal_widget.start_local(working_dir=path)

    def toggle_tree_panel(self):
        """Skryje/Odhalí globální stromovou navigaci na levé straně."""
        if self.tree_widget.isVisible():
            self.tree_widget.hide()
            sizes = self.main_splitter.sizes()
            sizes[0] = 0
            self.main_splitter.setSizes(sizes)
        else:
            self.tree_widget.show()
            w = self.main_splitter.width()
            tree_w = int(w * 0.2)
            sizes = self.main_splitter.sizes()
            rest = max(0, w - tree_w - sizes[3])
            half_rest = int(rest / 2)
            self.main_splitter.setSizes([tree_w, half_rest, half_rest, sizes[3]])
            
            # Synchronizovat strom hned po zobrazení
            active = self.get_active_panel()
            if active and hasattr(active, "current_path"):
                from event_bus import bus
                bus.directory_selected.emit(active.current_path)

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

    def eventFilter(self, source, event):
        # Allow dragging window by menubar
        if source is self.menuBar():
            if event.type() == QEvent.MouseButtonPress:
                if event.button() == Qt.LeftButton:
                    self.drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                    self._dragging = False
                    return False
            elif event.type() == QEvent.MouseMove:
                if event.buttons() == Qt.LeftButton and self.drag_pos:
                    delta = event.globalPosition().toPoint() - (self.drag_pos + self.frameGeometry().topLeft())
                    if not self._dragging and delta.manhattanLength() > 5:
                        self._dragging = True
                    if self._dragging:
                        self.move(event.globalPosition().toPoint() - self.drag_pos)
                        return True
            elif event.type() == QEvent.MouseButtonRelease:
                self.drag_pos = None
                self._dragging = False
        
        # Track focus for panels (Dynamické zjišťování přes Tabs)
        if event.type() == QEvent.FocusIn:
            left_active = self.left_tabs.currentWidget()
            right_active = self.right_tabs.currentWidget()
            
            if left_active and hasattr(left_active, 'table') and source is left_active.table:
                self._last_active_panel = left_active
            elif right_active and hasattr(right_active, 'table') and source is right_active.table:
                self._last_active_panel = right_active

        return super().eventFilter(source, event)

    def keyPressEvent(self, event):
        key = event.key()
        
        # Obsluha přepínání panelů pomocí klávesy Tab
        if key == Qt.Key_Tab:
            active = self.get_active_panel()
            left_active = self.left_tabs.currentWidget()
            right_active = self.right_tabs.currentWidget()
            
            if active == left_active and right_active:
                right_active.table.setFocus()
                self._last_active_panel = right_active
            elif active == right_active and left_active:
                left_active.table.setFocus()
                self._last_active_panel = left_active
            event.accept()
        else:
            super().keyPressEvent(event)

    def execute_command(self):
        cmd = self.cmd_input.text()
        if not cmd: return
        
        active = self.get_active_panel()
        # Delegování spuštění na ActionManager
        self.actions.execute_shell_command(cmd, active)
        self.cmd_input.clear()

    def refresh_all(self):
        if self.left_tabs.currentWidget(): self.left_tabs.currentWidget().refresh()
        if self.right_tabs.currentWidget(): self.right_tabs.currentWidget().refresh()

    def init_tabs(self):
        # Default fallback
        left_path = self.settings.value("panels/left/path", os.path.expanduser("~") if hasattr(os, 'expanduser') else os.path.expanduser("~"))
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
        from PySide6.QtGui import QCursor
        menu.exec(QCursor.pos())

    def closeEvent(self, event):
        self.settings.setValue("window/geometry", self.saveGeometry())
        self.settings.setValue("window/state", self.saveState())
        if hasattr(self, 'terminal_widget'):
            self.terminal_widget.stop()
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

    # Start Background Logger
    log_listener = setup_logger()
    log.info("Starting KiCommander Desktop v1.9")
    
    app = QApplication(sys.argv)
    
    # Load stylesheet
    style_path = os.path.join(ASSETS_DIR, "style.qss")
    
    window = KiCommander()
    theme_name = window.settings.value("appearance/theme", "Mocha")
    
    if os.path.exists(style_path):
        ThemeManager.apply_theme(app, style_path, theme_name)
    else:
        app.setStyle("Fusion")
    
    # Set App Icon
    icon_name = window.settings.value("appearance/app_icon", "icon.png")
    icon_path_assets = os.path.join(ASSETS_DIR, icon_name)
    icon_path_icons = os.path.join(ASSETS_DIR, "icons", icon_name)

    if os.path.exists(icon_path_icons):
        app.setWindowIcon(QIcon(icon_path_icons))
    elif os.path.exists(icon_path_assets):
        app.setWindowIcon(QIcon(icon_path_assets))
    else:
        app.setWindowIcon(qta.icon("fa5s.rocket", color="#89b4fa"))
    
    window.show()
    ret_val = app.exec()
    # Cleanup Logging Thread Safely
    log_listener.stop()
    sys.exit(ret_val)
