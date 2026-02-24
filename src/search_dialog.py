import os
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, 
                             QPushButton, QLabel, QTableWidget, QTableWidgetItem,
                             QComboBox, QCheckBox, QProgressBar, QHeaderView)
from PySide6.QtCore import Qt, QThread, Signal, QObject
import qtawesome as qta

class SearchWorker(QObject):
    found = Signal(str, str, str)  # name, path, size
    finished = Signal(int)  # total found
    progress = Signal(str)  # current dir being scanned

    def __init__(self, root_path, pattern, search_content=False, case_sensitive=False):
        super().__init__()
        self.root_path = root_path
        self.pattern = pattern.lower()
        self.search_content = search_content
        self.case_sensitive = case_sensitive
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        count = 0
        for dirpath, dirnames, filenames in os.walk(self.root_path):
            if self._cancelled:
                break
            self.progress.emit(dirpath)
            for fname in filenames:
                if self._cancelled:
                    break
                check_name = fname if self.case_sensitive else fname.lower()
                if self.pattern in check_name:
                    full = os.path.join(dirpath, fname)
                    try:
                        size = os.path.getsize(full)
                        size_str = self._format_size(size)
                    except OSError:
                        size_str = "N/A"
                    self.found.emit(fname, dirpath, size_str)
                    count += 1
        self.finished.emit(count)

    @staticmethod
    def _format_size(size):
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.0f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"


class SearchDialog(QDialog):
    navigate_to = Signal(str)  # Emits full path to navigate to

    def __init__(self, start_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Search Files (Alt+F7)")
        self.setMinimumSize(700, 500)
        self.start_path = start_path
        self.thread = None
        self.worker = None
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Search input row
        input_layout = QHBoxLayout()
        input_layout.addWidget(QLabel("Search for:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Enter filename pattern...")
        self.search_input.returnPressed.connect(self.start_search)
        input_layout.addWidget(self.search_input)
        layout.addLayout(input_layout)

        # Options row
        opts_layout = QHBoxLayout()
        opts_layout.addWidget(QLabel("In:"))
        self.path_input = QLineEdit(self.start_path)
        opts_layout.addWidget(self.path_input)
        self.case_check = QCheckBox("Case sensitive")
        opts_layout.addWidget(self.case_check)
        layout.addLayout(opts_layout)

        # Buttons
        btn_layout = QHBoxLayout()
        self.search_btn = QPushButton("Search")
        self.search_btn.setIcon(qta.icon("fa5s.search", color="#cdd6f4"))
        self.search_btn.clicked.connect(self.start_search)
        btn_layout.addWidget(self.search_btn)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setIcon(qta.icon("fa5s.times", color="#f38ba8"))
        self.cancel_btn.clicked.connect(self.cancel_search)
        self.cancel_btn.setEnabled(False)
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # Progress
        self.progress_label = QLabel("Ready")
        layout.addWidget(self.progress_label)

        # Results table
        self.results_table = QTableWidget(0, 3)
        self.results_table.setHorizontalHeaderLabels(["Name", "Path", "Size"])
        self.results_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Interactive)
        self.results_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.results_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Interactive)
        self.results_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.results_table.doubleClicked.connect(self.on_result_double_click)
        self.results_table.setColumnWidth(0, 200)
        self.results_table.setColumnWidth(2, 80)
        layout.addWidget(self.results_table)

        # Status
        self.status_label = QLabel("")
        layout.addWidget(self.status_label)

    def start_search(self):
        pattern = self.search_input.text().strip()
        if not pattern:
            return
        
        root = self.path_input.text().strip()
        if not os.path.isdir(root):
            return

        self.results_table.setRowCount(0)
        self.search_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.progress_label.setText("Searching...")

        self.thread = QThread()
        self.worker = SearchWorker(root, pattern, case_sensitive=self.case_check.isChecked())
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.found.connect(self.on_found)
        self.worker.progress.connect(lambda d: self.progress_label.setText(f"Scanning: {d}"))
        self.worker.finished.connect(self.on_search_finished)
        self.thread.start()

    def cancel_search(self):
        if self.worker:
            self.worker.cancel()

    def on_found(self, name, path, size):
        row = self.results_table.rowCount()
        self.results_table.insertRow(row)
        self.results_table.setItem(row, 0, QTableWidgetItem(name))
        self.results_table.setItem(row, 1, QTableWidgetItem(path))
        self.results_table.setItem(row, 2, QTableWidgetItem(size))

    def on_search_finished(self, count):
        self.search_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.progress_label.setText("Done")
        self.status_label.setText(f"Found {count} files.")
        if self.thread:
            self.thread.quit()

    def on_result_double_click(self, index):
        row = index.row()
        path = self.results_table.item(row, 1).text()
        self.navigate_to.emit(path)
        self.accept()
