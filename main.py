import sys
import os
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTableView, QHeaderView, QMenuBar, 
                             QLabel, QPushButton, QStatusBar)
from PySide6.QtCore import Qt, QSettings, QPoint, QSize, QEvent
import qtawesome as qta

from file_model import FileModel
from fs_worker import ScanThread

class FilePanel(QWidget):
    def __init__(self, panel_id, initial_path):
        super().__init__()
        self.panel_id = panel_id
        self.current_path = initial_path
        self.settings = QSettings("KiCommander", "Desktop")
        
        # Restore last path if available
        last_path = self.settings.value(f"panels/{self.panel_id}/path")
        if last_path and os.path.exists(last_path):
            self.current_path = last_path

        self.setup_ui()
        self.refresh_path(self.current_path)

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Path label
        self.path_label = QLabel(self.current_path)
        self.path_label.setStyleSheet("font-weight: bold; padding: 5px; background: #333; color: white;")
        layout.addWidget(self.path_label)

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
        
        # Navigation
        self.table.doubleClicked.connect(self.on_double_click)
        self.table.installEventFilter(self) # For Enter key implementation
        
        layout.addWidget(self.table)

    def eventFilter(self, source, event):
        if event.type() == QEvent.KeyPress and source is self.table:
            if event.key() in (Qt.Key_Return, Qt.Key_Enter):
                index = self.table.currentIndex()
                if index.isValid():
                    self.on_double_click(index)
                    return True
        return super().eventFilter(source, event)

    def refresh_path(self, path):
        self.current_path = os.path.abspath(path)
        self.path_label.setText(self.current_path)
        
        # Save to settings
        self.settings.setValue(f"panels/{self.panel_id}/path", self.current_path)
        
        self.thread = ScanThread(self.current_path)
        self.thread.worker.finished.connect(self.on_scan_finished)
        self.thread.start()

    def on_scan_finished(self, files):
        self.model.update_files(files)
        # Restore focused row if possible, or select first
        self.table.selectRow(0)
        self.table.setFocus()

    def on_double_click(self, index):
        file_info = self.model.get_file(index.row())
        if file_info and file_info.is_dir:
            self.refresh_path(file_info.full_path)

class KiCommander(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("KiCommander Desktop")
        self.settings = QSettings("KiCommander", "Desktop")
        
        # Restore window geometry
        self.restoreGeometry(self.settings.value("window/geometry", b""))
        self.restoreState(self.settings.value("window/state", b""))
        if not self.geometry().isValid():
            self.resize(1200, 800)

        self.setup_ui()

    def setup_ui(self):
        # Menu Bar
        menubar = self.menuBar()
        file_menu = menubar.addMenu("&Files")
        file_menu.addAction("Exit", self.close, "Alt+F4")
        
        cmd_menu = menubar.addMenu("&Commands")
        cmd_menu.addAction("Search", lambda: print("Search clicked"), "Alt+F7")

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Panels
        panels_layout = QHBoxLayout()
        self.left_panel = FilePanel("left", os.path.expanduser("~"))
        self.right_panel = FilePanel("right", "C:\\")
        
        panels_layout.addWidget(self.left_panel)
        panels_layout.addWidget(self.right_panel)
        main_layout.addLayout(panels_layout, 1)

        # Bottom Buttons
        btn_layout = QHBoxLayout()
        buttons = [
            ("F3 View", "eye"), ("F4 Edit", "edit"), ("F5 Copy", "copy"),
            ("F6 Move", "external-link-alt"), ("F7 NewFolder", "folder-plus"),
            ("F8 Delete", "trash-alt"), ("Alt+F4 Exit", "times-circle")
        ]
        
        for text, icon_name in buttons:
            btn = QPushButton(text)
            btn.setIcon(qta.icon(f"fa5s.{icon_name}"))
            btn_layout.addWidget(btn)
        
        main_layout.addLayout(btn_layout)

        # Status Bar
        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("Ready")

    def keyPressEvent(self, event):
        # Switch panels with Tab
        if event.key() == Qt.Key_Tab:
            if self.left_panel.table.hasFocus():
                self.right_panel.table.setFocus()
            else:
                self.left_panel.table.setFocus()
            return
        super().keyPressEvent(event)

    def closeEvent(self, event):
        # Save window settings on exit
        self.settings.setValue("window/geometry", self.saveGeometry())
        self.settings.setValue("window/state", self.saveState())
        super().closeEvent(event)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    window = KiCommander()
    window.show()
    sys.exit(app.exec())
