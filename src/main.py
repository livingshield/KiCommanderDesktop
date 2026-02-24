import sys
import os
import subprocess
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTableView, QHeaderView, QMenuBar, 
                             QLabel, QPushButton, QStatusBar, QLineEdit, QMessageBox,
                             QInputDialog)
from PySide6.QtCore import Qt, QSettings, QPoint, QSize, QEvent
import qtawesome as qta

from file_model import FileModel
from fs_worker import ScanThread
from file_ops import FileOpThread
from navigation_utils import get_drives, get_quick_links

class FilePanel(QWidget):
    def __init__(self, panel_id, initial_path):
        super().__init__()
        self.panel_id = panel_id
        self.current_path = initial_path
        self.settings = QSettings("KiCommander", "Desktop")
        
        last_path = self.settings.value(f"panels/{self.panel_id}/path")
        if last_path and os.path.exists(last_path):
            self.current_path = last_path

        self.setup_ui()
        self.refresh_path(self.current_path)

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
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
        self.table.installEventFilter(self)
        
        body_layout.addWidget(self.table, 1)
        main_layout.addLayout(body_layout, 1)

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
                    # Just move down after selection
                    self.table.selectionModel().select(index, self.table.selectionModel().Toggle | self.table.selectionModel().Rows)
                    self.table.setCurrentIndex(self.model.index(index.row() + 1, 0))
                    return True
        return super().eventFilter(source, event)

    def refresh_path(self, path):
        self.current_path = os.path.abspath(path)
        self.path_label.setText(self.current_path)
        self.settings.setValue(f"panels/{self.panel_id}/path", self.current_path)
        
        self.thread = ScanThread(self.current_path)
        self.thread.worker.finished.connect(self.on_scan_finished)
        self.thread.start()

    def on_scan_finished(self, files):
        self.model.update_files(files)
        self.table.selectRow(0)
        self.table.setFocus()

    def on_double_click(self, index):
        file_info = self.model.get_file(index.row())
        if file_info:
            if file_info.is_dir:
                self.refresh_path(file_info.full_path)
            else:
                # Open with default OS app
                os.startfile(file_info.full_path)

    def get_selected_paths(self):
        indices = self.table.selectionModel().selectedRows()
        paths = []
        for idx in indices:
            f = self.model.get_file(idx.row())
            if f and f.name != "..":
                paths.append(f.full_path)
        return paths

class KiCommander(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("KiCommander Desktop")
        self.settings = QSettings("KiCommander", "Desktop")
        
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

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        panels_layout = QHBoxLayout()
        self.left_panel = FilePanel("left", os.path.expanduser("~"))
        self.right_panel = FilePanel("right", "C:\\")
        
        panels_layout.addWidget(self.left_panel)
        panels_layout.addWidget(self.right_panel)
        main_layout.addLayout(panels_layout, 1)

        # Command Line
        cmd_layout = QHBoxLayout()
        cmd_label = QLabel("Command:")
        cmd_label.setToolTip("Enter system commands to execute in the current path")
        cmd_layout.addWidget(cmd_label)
        self.cmd_input = QLineEdit()
        self.cmd_input.setToolTip("Type command and press Enter (e.g., notepad, cmd, or python script)")
        self.cmd_input.returnPressed.connect(self.execute_command)
        cmd_layout.addWidget(self.cmd_input)
        main_layout.addLayout(cmd_layout)

        # Bottom Buttons
        btn_layout = QHBoxLayout()
        self.btn_configs = [
            ("F3 View", "eye", self.op_not_implemented, "View file content"),
            ("F4 Edit", "edit", self.op_not_implemented, "Edit selected file"),
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
        
        main_layout.addLayout(btn_layout)

        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("Ready")

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

    def op_not_implemented(self):
        QMessageBox.information(self, "Info", "Functionality coming soon!")

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
        # Override for F-keys
        key = event.key()
        if key == Qt.Key_F3: self.op_not_implemented()
        elif key == Qt.Key_F4: self.op_not_implemented()
        elif key == Qt.Key_F5: self.op_copy()
        elif key == Qt.Key_F6: self.op_move()
        elif key == Qt.Key_F7: self.op_mkdir()
        elif key == Qt.Key_F8: self.op_delete()
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
    app = QApplication(sys.argv)
    
    # Load stylesheet relative to this script (handling PyInstaller bundle)
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller bundled path
        style_path = os.path.join(sys._MEIPASS, "style.qss")
    else:
        # Normal Python execution path
        script_dir = os.path.dirname(os.path.abspath(__file__))
        style_path = os.path.join(script_dir, "style.qss")
    
    if os.path.exists(style_path):
        with open(style_path, "r") as f:
            app.setStyleSheet(f.read())
    else:
        app.setStyle("Fusion")
    
    window = KiCommander()
    window.show()
    sys.exit(app.exec())
