import os
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, 
                             QPushButton, QLabel, QTableWidget, QTableWidgetItem,
                             QComboBox, QCheckBox, QProgressBar, QHeaderView,
                             QGroupBox, QFileDialog)
from PySide6.QtCore import Qt, QThread, Signal, QObject
import qtawesome as qta

TEXT_EXTENSIONS = {
    ".txt", ".py", ".md", ".json", ".xml", ".html", ".css", ".js",
    ".csv", ".log", ".ini", ".cfg", ".yml", ".yaml", ".toml",
    ".bat", ".cmd", ".sh", ".ps1", ".c", ".cpp", ".h", ".java",
    ".rs", ".go", ".ts", ".tsx", ".jsx", ".vue", ".qss", ".sql",
    ".rb", ".php", ".pl", ".r", ".swift", ".kt", ".lua", ".vb",
}

class SearchWorker(QObject):
    found = Signal(str, str, str, str)  # name, path, size, match_info
    finished = Signal(int)
    progress = Signal(str)

    def __init__(self, root_path, name_pattern, content_pattern="",
                 case_sensitive=False, search_subdirs=True):
        super().__init__()
        self.root_path = root_path
        self.name_pattern = name_pattern
        self.content_pattern = content_pattern
        self.case_sensitive = case_sensitive
        self.search_subdirs = search_subdirs
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def _match_name(self, fname):
        """Check if filename matches the name pattern."""
        if not self.name_pattern:
            return True
        pattern = self.name_pattern if self.case_sensitive else self.name_pattern.lower()
        check = fname if self.case_sensitive else fname.lower()
        # Support wildcards: * matches anything
        if '*' in pattern:
            parts = pattern.split('*')
            if parts[0] and not check.startswith(parts[0]):
                return False
            if parts[-1] and not check.endswith(parts[-1]):
                return False
            return True
        return pattern in check

    def _search_content(self, filepath):
        """Search inside file for content_pattern. Returns matching line or empty string."""
        ext = os.path.splitext(filepath)[1].lower()
        if ext not in TEXT_EXTENSIONS:
            return ""
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                for line_num, line in enumerate(f, 1):
                    if line_num > 50000:  # Safety limit
                        break
                    check_line = line if self.case_sensitive else line.lower()
                    check_pattern = self.content_pattern if self.case_sensitive else self.content_pattern.lower()
                    if check_pattern in check_line:
                        return f"Line {line_num}: {line.strip()[:100]}"
        except (OSError, UnicodeDecodeError):
            pass
        return ""

    def run(self):
        count = 0
        for dirpath, dirnames, filenames in os.walk(self.root_path):
            if self._cancelled:
                break
            self.progress.emit(dirpath)
            
            for fname in filenames:
                if self._cancelled:
                    break
                
                full = os.path.join(dirpath, fname)
                name_ok = self._match_name(fname)
                
                # Content search mode
                if self.content_pattern:
                    if name_ok:
                        match_line = self._search_content(full)
                        if match_line:
                            size_str = self._get_size(full)
                            self.found.emit(fname, dirpath, size_str, match_line)
                            count += 1
                else:
                    # Name-only search
                    if name_ok:
                        size_str = self._get_size(full)
                        self.found.emit(fname, dirpath, size_str, "")
                        count += 1

            if not self.search_subdirs:
                break  # Only scan the top-level directory

        self.finished.emit(count)

    def _get_size(self, path):
        try:
            return self._format_size(os.path.getsize(path))
        except OSError:
            return "N/A"

    @staticmethod
    def _format_size(size):
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.0f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"


class SearchDialog(QDialog):
    navigate_to = Signal(str)

    def __init__(self, start_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Search Files (Alt+F7)")
        self.setMinimumSize(750, 550)
        self.start_path = start_path
        self.thread = None
        self.worker = None
        self.setup_ui()

    def setup_ui(self):
        self.setStyleSheet("""
            QDialog { background-color: #1e1e2e; }
            QLabel { color: #cdd6f4; font-size: 10pt; }
            QLabel#HelpLabel { color: #6c7086; font-size: 9pt; font-style: italic; }
            QLineEdit {
                background-color: #11111b; border: 1px solid #313244;
                border-radius: 4px; padding: 8px; color: #f5c2e7;
                font-size: 10pt;
            }
            QLineEdit:focus { border: 1px solid #89b4fa; }
            QPushButton {
                background-color: #313244; border: 1px solid #45475a;
                border-radius: 4px; padding: 8px 18px; color: #cdd6f4;
                font-weight: bold; font-size: 10pt;
            }
            QPushButton:hover { background-color: #45475a; border-color: #89b4fa; }
            QPushButton:disabled { color: #585b70; }
            QCheckBox { color: #cdd6f4; font-size: 10pt; spacing: 6px; }
            QGroupBox {
                color: #89b4fa; font-weight: bold; font-size: 10pt;
                border: 1px solid #313244; border-radius: 6px;
                margin-top: 8px; padding-top: 14px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px; padding: 0 6px;
            }
            QTableWidget {
                background-color: #181825; border: 1px solid #313244;
                border-radius: 4px; gridline-color: #313244;
                selection-background-color: rgba(137, 180, 250, 0.2);
                selection-color: #89b4fa; color: #cdd6f4; font-size: 10pt;
            }
            QTableWidget::item { padding: 5px; border-bottom: 1px solid #1e1e2e; }
            QTableWidget::item:selected { background-color: rgba(137, 180, 250, 0.2); color: #89b4fa; }
            QHeaderView::section {
                background-color: #11111b; color: #a6adc8; padding: 8px;
                border: none; border-right: 1px solid #313244;
                border-bottom: 2px solid #313244; font-weight: bold;
            }
            QToolTip {
                background-color: #313244; color: #cdd6f4;
                border: 1px solid #89b4fa; padding: 6px 10px;
                border-radius: 4px; font-size: 9pt;
            }
        """)
        layout = QVBoxLayout(self)

        # --- Search by name ---
        name_group = QGroupBox("Search by filename")
        name_layout = QVBoxLayout(name_group)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Filename:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("e.g.  *.py   or   report   or   *.txt")
        self.search_input.setToolTip(
            "Enter part of a filename to search for.\n"
            "Examples:\n"
            "  report     – finds all files containing 'report' in name\n"
            "  *.py       – finds all Python files\n"
            "  *.txt      – finds all text files\n"
            "  data*      – finds files starting with 'data'"
        )
        self.search_input.returnPressed.connect(self.start_search)
        row1.addWidget(self.search_input)
        name_layout.addLayout(row1)

        help_name = QLabel("💡 Enter part of filename or use * as wildcard (e.g. *.py, report*, data*.csv)")
        help_name.setObjectName("HelpLabel")
        name_layout.addWidget(help_name)
        layout.addWidget(name_group)

        # --- Search by content ---
        content_group = QGroupBox("Search by file content (optional)")
        content_layout = QVBoxLayout(content_group)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Contains:"))
        self.content_input = QLineEdit()
        self.content_input.setPlaceholderText("e.g.  def main   or   TODO   or   import os")
        self.content_input.setToolTip(
            "Search inside text files for this string.\n"
            "Supported: .py, .txt, .md, .json, .html, .css, .js, .csv, .log, etc.\n"
            "Leave empty to search by filename only."
        )
        self.content_input.returnPressed.connect(self.start_search)
        row2.addWidget(self.content_input)
        content_layout.addLayout(row2)

        help_content = QLabel("💡 Searches inside text files (.py, .txt, .md, .json, .html, .css, .js ...). Leave empty to skip.")
        help_content.setObjectName("HelpLabel")
        content_layout.addWidget(help_content)
        layout.addWidget(content_group)

        # --- Options row ---
        opts_layout = QHBoxLayout()
        opts_layout.addWidget(QLabel("In directory:"))
        self.path_input = QLineEdit(self.start_path)
        self.path_input.setToolTip("Root directory to start the search from.")
        opts_layout.addWidget(self.path_input)
        browse_btn = QPushButton()
        browse_btn.setIcon(qta.icon("fa5s.folder-open", color="#f9e2af"))
        browse_btn.setFixedWidth(40)
        browse_btn.setToolTip("Browse for directory...")
        browse_btn.clicked.connect(self.browse_directory)
        opts_layout.addWidget(browse_btn)
        layout.addLayout(opts_layout)

        checks_layout = QHBoxLayout()
        self.subdirs_check = QCheckBox("Include subdirectories")
        self.subdirs_check.setChecked(True)
        self.subdirs_check.setToolTip("When checked, search recursively through all subdirectories.")
        checks_layout.addWidget(self.subdirs_check)

        self.case_check = QCheckBox("Case sensitive")
        self.case_check.setToolTip("When checked, 'Report' and 'report' are treated as different words.")
        checks_layout.addWidget(self.case_check)
        checks_layout.addStretch()
        layout.addLayout(checks_layout)

        # --- Buttons ---
        btn_layout = QHBoxLayout()
        self.search_btn = QPushButton("  Search")
        self.search_btn.setIcon(qta.icon("fa5s.search", color="#a6e3a1"))
        self.search_btn.clicked.connect(self.start_search)
        self.search_btn.setToolTip("Start searching (Enter)")
        btn_layout.addWidget(self.search_btn)
        
        self.cancel_btn = QPushButton("  Cancel")
        self.cancel_btn.setIcon(qta.icon("fa5s.times", color="#f38ba8"))
        self.cancel_btn.clicked.connect(self.cancel_search)
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.setToolTip("Stop the current search")
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # --- Progress ---
        self.progress_label = QLabel("Ready")
        layout.addWidget(self.progress_label)

        # --- Results table ---
        self.results_table = QTableWidget(0, 4)
        self.results_table.setHorizontalHeaderLabels(["Name", "Path", "Size", "Match"])
        self.results_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Interactive)
        self.results_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.results_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Interactive)
        self.results_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Interactive)
        self.results_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.results_table.doubleClicked.connect(self.on_result_double_click)
        self.results_table.setColumnWidth(0, 180)
        self.results_table.setColumnWidth(2, 70)
        self.results_table.setColumnWidth(3, 200)
        self.results_table.setToolTip("Double-click a result to navigate to its directory.")
        layout.addWidget(self.results_table)

        # --- Status ---
        self.status_label = QLabel("")
        layout.addWidget(self.status_label)

    def browse_directory(self):
        directory = QFileDialog.getExistingDirectory(
            self, "Select search directory", self.path_input.text()
        )
        if directory:
            self.path_input.setText(directory)

    def start_search(self):
        name_pattern = self.search_input.text().strip()
        content_pattern = self.content_input.text().strip()
        
        if not name_pattern and not content_pattern:
            return
        
        root = self.path_input.text().strip()
        if not os.path.isdir(root):
            return

        self.results_table.setRowCount(0)
        self.search_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.progress_label.setText("Searching...")

        self.thread = QThread()
        self.worker = SearchWorker(
            root, name_pattern, content_pattern,
            case_sensitive=self.case_check.isChecked(),
            search_subdirs=self.subdirs_check.isChecked()
        )
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.found.connect(self.on_found)
        self.worker.progress.connect(lambda d: self.progress_label.setText(f"Scanning: {d}"))
        self.worker.finished.connect(self.on_search_finished)
        self.thread.start()

    def cancel_search(self):
        if self.worker:
            self.worker.cancel()

    def on_found(self, name, path, size, match_info):
        row = self.results_table.rowCount()
        self.results_table.insertRow(row)
        self.results_table.setItem(row, 0, QTableWidgetItem(name))
        self.results_table.setItem(row, 1, QTableWidgetItem(path))
        self.results_table.setItem(row, 2, QTableWidgetItem(size))
        self.results_table.setItem(row, 3, QTableWidgetItem(match_info))

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
