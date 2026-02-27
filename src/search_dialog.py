import os
import time
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, 
                             QPushButton, QLabel, QTableWidget, QTableWidgetItem,
                             QComboBox, QCheckBox, QProgressBar, QHeaderView,
                             QGroupBox, QFileDialog, QSpinBox, QDateEdit, QWidget, QSizeGrip)
from PySide6.QtCore import Qt, QThread, Signal, QObject, QDate
import qtawesome as qta
import stat

from fs_worker import FileInfo

TEXT_EXTENSIONS = {
    ".txt", ".py", ".md", ".json", ".xml", ".html", ".css", ".js",
    ".csv", ".log", ".ini", ".cfg", ".yml", ".yaml", ".toml",
    ".bat", ".cmd", ".sh", ".ps1", ".c", ".cpp", ".h", ".java",
    ".rs", ".go", ".ts", ".tsx", ".jsx", ".vue", ".qss", ".sql",
    ".rb", ".php", ".pl", ".r", ".swift", ".kt", ".lua", ".vb",
}

class SearchWorker(QObject):
    found = Signal(object, str)  # file_info, match_info
    finished = Signal(int)
    progress = Signal(str)

    def __init__(self, root_path, name_pattern, content_pattern="",
                 case_sensitive=False, search_subdirs=True,
                 min_size=0, max_size=0, min_date=0, max_date=0,
                 vfs=None):
        super().__init__()
        self.root_path = root_path
        self.vfs = vfs
        self.name_pattern = name_pattern
        self.content_pattern = content_pattern
        self.case_sensitive = case_sensitive
        self.search_subdirs = search_subdirs
        self.min_size = min_size    # bytes, 0 = no limit
        self.max_size = max_size    # bytes, 0 = no limit
        self.min_date = min_date    # epoch, 0 = no limit
        self.max_date = max_date    # epoch, 0 = no limit
        self._cancelled = False
        self.count = 0

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

    def _check_size_date(self, filepath):
        """Check file against size and date filters. Returns True if passes."""
        try:
            st = os.stat(filepath)
            if self.min_size and st.st_size < self.min_size:
                return False
            if self.max_size and st.st_size > self.max_size:
                return False
            if self.min_date and st.st_mtime < self.min_date:
                return False
            if self.max_date and st.st_mtime > self.max_date:
                return False
        except OSError:
            return False
        return True

    def run(self):
        self.count = 0
        if self.vfs:
            self._walk_vfs(self.root_path)
        else:
            for dirpath, dirnames, filenames in os.walk(self.root_path):
                if self._cancelled:
                    break
                self.progress.emit(dirpath)
                
                for fname in filenames:
                    if self._cancelled:
                        break
                    
                    full = os.path.join(dirpath, fname)
                    name_ok = self._match_name(fname)
                    
                    if not name_ok:
                        continue
                    
                    # Apply size/date filters
                    if (self.min_size or self.max_size or self.min_date or self.max_date):
                        if not self._check_size_date(full):
                            continue
                    
                    # Stat the file for FileInfo
                    try:
                        stats = os.stat(full)
                        size_bytes = stats.st_size
                        mtime = stats.st_mtime
                        size_str = self.format_size(size_bytes)
                        date_str = time.strftime('%d.%m.%Y %H:%M', time.localtime(mtime))
                        ext = os.path.splitext(fname)[1].lstrip('.')
                        perms = stat.filemode(stats.st_mode)
                        file_info = FileInfo(fname, ext, size_str, date_str, False, full, size_bytes, mtime, permissions=perms)
                    except OSError:
                        # Fallback
                        file_info = FileInfo(fname, "", "0 B", "", False, full)

                    # Content search mode
                    if self.content_pattern:
                        match_line = self._search_content(full)
                        if match_line:
                            self.found.emit(file_info, match_line)
                            self.count += 1
                    else:
                        self.found.emit(file_info, "")
                        self.count += 1

                if not self.search_subdirs:
                    break

        self.finished.emit(self.count)

    def _walk_vfs(self, path):
        """Recursive VFS listing."""
        if self._cancelled: return
        
        self.progress.emit(path)
        try:
            items = self.vfs.list_dir(path)
        except Exception:
            return

        for item in items:
            if self._cancelled: break
            if item.name == "..": continue
            
            if item.is_dir:
                if self.search_subdirs:
                    self._walk_vfs(item.full_path)
            else:
                # File
                name_ok = self._match_name(item.name)
                if not name_ok: continue
                
                # Filters
                if (self.min_size and item.size_bytes < self.min_size) or \
                   (self.max_size and item.size_bytes > self.max_size) or \
                   (self.min_date and item.mtime < self.min_date) or \
                   (self.max_date and item.mtime > self.max_date):
                    continue
                
                # Content
                match_line = ""
                if self.content_pattern:
                    import tempfile
                    with tempfile.TemporaryDirectory() as tmp:
                        try:
                            local_tmp = self.vfs.extract_file(item.full_path, tmp)
                            if local_tmp:
                                match_line = self._search_content(local_tmp)
                        except Exception as e:
                            log.error(f"[SearchWorker] VFS extraction failed for {item.name}: {e}")
                
                if not self.content_pattern or match_line:
                    self.found.emit(item, match_line)
                    self.count += 1

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
    feed_to_panel = Signal(list)

    def __init__(self, start_path, parent=None, vfs=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMinimumSize(800, 600)
        self.setMouseTracking(True)
        self.start_path = start_path
        self.vfs = vfs
        self.thread = None
        self.worker = None
        self._drag_pos = None
        self._resize_margin = 8
        self._resizing = False
        self._resize_edge = None
        self.results_data = [] # List of FileInfo objects
        self.setup_ui()

    def setup_ui(self):
        # Outer wrapper for rounded corners
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        container = QWidget()
        container.setObjectName("DialogContainer")
        outer.addWidget(container)
        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Custom title bar
        title_bar = QWidget()
        title_bar.setFixedHeight(38)
        title_bar.setObjectName("DialogTitleBar")
        tb_layout = QHBoxLayout(title_bar)
        tb_layout.setContentsMargins(12, 0, 6, 0)
        tb_layout.setSpacing(8)
        icon_lbl = QLabel()
        icon_lbl.setPixmap(qta.icon("fa5s.search", color="#89b4fa").pixmap(16, 16))
        tb_layout.addWidget(icon_lbl)
        title_lbl = QLabel("Search Files")
        title_lbl.setStyleSheet("color: #cdd6f4; font-weight: bold; font-size: 10pt;")
        tb_layout.addWidget(title_lbl)
        tb_layout.addStretch()
        close_btn = QPushButton()
        close_btn.setIcon(qta.icon("fa5s.times", color="#cdd6f4"))
        close_btn.setFixedSize(28, 28)
        close_btn.setObjectName("TitleCloseBtn")
        close_btn.clicked.connect(self.reject)
        tb_layout.addWidget(close_btn)
        main_layout.addWidget(title_bar)

        # Content area
        content = QWidget()
        content.setObjectName("DialogContent")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(12, 8, 12, 12)
        main_layout.addWidget(content, 1)

        self.setStyleSheet("""
            #DialogContainer {
                background-color: #1e1e2e;
                border: 1px solid #313244;
                border-radius: 8px;
            }
            #DialogTitleBar {
                background-color: #11111b;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                border-bottom: 1px solid #313244;
            }
            #TitleCloseBtn {
                background: transparent; border: none; border-radius: 14px;
            }
            #TitleCloseBtn:hover { background-color: #f38ba8; }
            #DialogContent { background-color: #1e1e2e; border-bottom-left-radius: 8px; border-bottom-right-radius: 8px; }
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
            QCheckBox::indicator {
                width: 16px; height: 16px;
                border: 1px solid #45475a; border-radius: 3px;
                background-color: #11111b;
            }
            QCheckBox::indicator:checked {
                background-color: #89b4fa; border-color: #89b4fa;
            }
            QGroupBox {
                color: #89b4fa; font-weight: bold; font-size: 10pt;
                border: 1px solid #313244; border-radius: 6px;
                margin-top: 8px; padding-top: 14px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px; padding: 0 6px;
            }
            QSpinBox, QComboBox, QDateEdit {
                background-color: #11111b; border: 1px solid #313244;
                border-radius: 4px; padding: 5px 8px; color: #cdd6f4;
                font-size: 10pt; min-width: 70px;
            }
            QSpinBox:focus, QComboBox:focus, QDateEdit:focus {
                border: 1px solid #89b4fa;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                background-color: #313244; border: none; width: 18px;
            }
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {
                background-color: #45475a;
            }
            QSpinBox::up-arrow { image: none; border-left: 4px solid transparent; border-right: 4px solid transparent; border-bottom: 5px solid #cdd6f4; }
            QSpinBox::down-arrow { image: none; border-left: 4px solid transparent; border-right: 4px solid transparent; border-top: 5px solid #cdd6f4; }
            QComboBox::drop-down {
                border: none; background-color: #313244;
                width: 24px; border-top-right-radius: 4px; border-bottom-right-radius: 4px;
            }
            QComboBox::down-arrow { image: none; border-left: 5px solid transparent; border-right: 5px solid transparent; border-top: 6px solid #cdd6f4; }
            QComboBox QAbstractItemView {
                background-color: #1e1e2e; border: 1px solid #313244;
                color: #cdd6f4; selection-background-color: #313244;
                selection-color: #89b4fa;
            }
            QDateEdit::drop-down {
                border: none; background-color: #313244;
                width: 24px; border-top-right-radius: 4px; border-bottom-right-radius: 4px;
            }
            QDateEdit::down-arrow { image: none; border-left: 5px solid transparent; border-right: 5px solid transparent; border-top: 6px solid #cdd6f4; }
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
            QCalendarWidget { background-color: #1e1e2e; color: #cdd6f4; }
            QCalendarWidget QToolButton { color: #cdd6f4; background-color: #313244; }
            QCalendarWidget QAbstractItemView { background-color: #181825; color: #cdd6f4; selection-background-color: #89b4fa; }
        """)

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

        # --- Filters (Size & Date) ---
        filter_group = QGroupBox("Filters (optional)")
        filter_layout = QVBoxLayout(filter_group)

        # Size filter row
        size_row = QHBoxLayout()
        size_row.addWidget(QLabel("Size:"))
        self.min_size_spin = QSpinBox()
        self.min_size_spin.setRange(0, 999999)
        self.min_size_spin.setSpecialValueText("No min")
        self.min_size_spin.setToolTip("Minimum file size")
        size_row.addWidget(self.min_size_spin)
        self.min_size_unit = QComboBox()
        self.min_size_unit.addItems(["KB", "MB", "GB"])
        size_row.addWidget(self.min_size_unit)
        size_row.addWidget(QLabel(" – "))
        self.max_size_spin = QSpinBox()
        self.max_size_spin.setRange(0, 999999)
        self.max_size_spin.setSpecialValueText("No max")
        self.max_size_spin.setToolTip("Maximum file size")
        size_row.addWidget(self.max_size_spin)
        self.max_size_unit = QComboBox()
        self.max_size_unit.addItems(["KB", "MB", "GB"])
        size_row.addWidget(self.max_size_unit)
        size_row.addStretch()
        filter_layout.addLayout(size_row)

        # Date filter row
        date_row = QHBoxLayout()
        date_row.addWidget(QLabel("Modified:"))
        self.date_from_check = QCheckBox("From:")
        date_row.addWidget(self.date_from_check)
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDate(QDate.currentDate().addMonths(-1))
        self.date_from.setEnabled(False)
        self.date_from_check.toggled.connect(self.date_from.setEnabled)
        date_row.addWidget(self.date_from)
        self.date_to_check = QCheckBox("To:")
        date_row.addWidget(self.date_to_check)
        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDate(QDate.currentDate())
        self.date_to.setEnabled(False)
        self.date_to_check.toggled.connect(self.date_to.setEnabled)
        date_row.addWidget(self.date_to)
        date_row.addStretch()
        filter_layout.addLayout(date_row)

        layout.addWidget(filter_group)

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
        
        self.feed_btn = QPushButton("  Zobrazit v panelu")
        self.feed_btn.setIcon(qta.icon("fa5s.list-ul", color="#cba6f7"))
        self.feed_btn.clicked.connect(self.feed_results)
        self.feed_btn.setEnabled(False)
        self.feed_btn.setToolTip("Display results in a new file panel tab")
        btn_layout.addWidget(self.feed_btn)
        
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

    def _size_to_bytes(self, value, unit_combo):
        """Convert spin value + unit combo to bytes."""
        if value == 0:
            return 0
        unit = unit_combo.currentText()
        mult = {"KB": 1024, "MB": 1024**2, "GB": 1024**3}
        return value * mult.get(unit, 1024)

    def start_search(self):
        name_pattern = self.search_input.text().strip()
        content_pattern = self.content_input.text().strip()
        
        if not name_pattern and not content_pattern:
            return
        
        root = self.path_input.text().strip()
        if not os.path.isdir(root):
            return

        # Compute size filters
        min_size = self._size_to_bytes(self.min_size_spin.value(), self.min_size_unit)
        max_size = self._size_to_bytes(self.max_size_spin.value(), self.max_size_unit)

        # Compute date filters (epoch timestamps)
        min_date = 0
        max_date = 0
        if self.date_from_check.isChecked():
            d = self.date_from.date()
            min_date = time.mktime(time.strptime(d.toString("yyyy-MM-dd"), "%Y-%m-%d"))
        if self.date_to_check.isChecked():
            d = self.date_to.date()
            # End of day
            max_date = time.mktime(time.strptime(d.toString("yyyy-MM-dd"), "%Y-%m-%d")) + 86399

        self.results_table.setRowCount(0)
        self.search_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.progress_label.setText("Searching...")

        self.thread = QThread()
        self.worker = SearchWorker(
            root, name_pattern, content_pattern,
            case_sensitive=self.case_check.isChecked(),
            search_subdirs=self.subdirs_check.isChecked(),
            min_size=min_size, max_size=max_size,
            min_date=min_date, max_date=max_date,
            vfs=self.vfs
        )
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.found.connect(self.on_found)
        self.worker.progress.connect(lambda d: self.progress_label.setText(f"Scanning: {d}"))
        self.worker.finished.connect(self.on_search_finished)
        
        self.results_data.clear()
        self.feed_btn.setEnabled(False)
        self.thread.start()

    def cancel_search(self):
        if self.worker:
            self.worker.cancel()

    def on_found(self, file_info, match_info):
        self.results_data.append(file_info)
        row = self.results_table.rowCount()
        self.results_table.insertRow(row)
        dirpath = os.path.dirname(file_info.full_path)
        self.results_table.setItem(row, 0, QTableWidgetItem(file_info.name))
        self.results_table.setItem(row, 1, QTableWidgetItem(dirpath))
        self.results_table.setItem(row, 2, QTableWidgetItem(file_info.size))
        self.results_table.setItem(row, 3, QTableWidgetItem(match_info))

    def on_search_finished(self, count):
        self.search_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        if count > 0:
            self.feed_btn.setEnabled(True)
            
        self.progress_label.setText("Done")
        self.status_label.setText(f"Found {count} files.")
        if self.thread:
            self.thread.quit()

    def on_result_double_click(self, index):
        row = index.row()
        path = self.results_table.item(row, 1).text()
        self.navigate_to.emit(path)
        self.accept()

    def feed_results(self):
        self.feed_to_panel.emit(self.results_data)
        self.accept()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            edge = self._get_edge(event.position().toPoint())
            if edge:
                self._resizing = True
                self._resize_edge = edge
                event.accept()
            elif event.position().y() < 38:
                self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                event.accept()

    def mouseMoveEvent(self, event):
        pos = event.position().toPoint()
        if not event.buttons():
            edge = self._get_edge(pos)
            self._update_cursor(edge)
            return

        if self._resizing and self._resize_edge:
            self._handle_resize(event.globalPosition().toPoint())
            event.accept()
        elif self._drag_pos and event.buttons() & Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        self._resizing = False
        self._resize_edge = None

    def _get_edge(self, pos):
        w, h = self.width(), self.height()
        m = self._resize_margin
        on_left = pos.x() < m
        on_right = pos.x() > w - m
        on_top = pos.y() < m
        on_bottom = pos.y() > h - m
        
        if on_left and on_top: return "top-left"
        if on_right and on_top: return "top-right"
        if on_left and on_bottom: return "bottom-left"
        if on_right and on_bottom: return "bottom-right"
        if on_left: return "left"
        if on_right: return "right"
        if on_top: return "top"
        if on_bottom: return "bottom"
        return None

    def _update_cursor(self, edge):
        if edge in ("top", "bottom"): self.setCursor(Qt.SizeVerCursor)
        elif edge in ("left", "right"): self.setCursor(Qt.SizeHorCursor)
        elif edge in ("top-left", "bottom-right"): self.setCursor(Qt.SizeBDiagCursor)
        elif edge in ("top-right", "bottom-left"): self.setCursor(Qt.SizeFDiagCursor)
        else: self.setCursor(Qt.ArrowCursor)

    def _handle_resize(self, global_pos):
        rect = self.geometry()
        edge = self._resize_edge
        min_w, min_h = self.minimumSize().width(), self.minimumSize().height()
        if "left" in edge:
            new_w = rect.right() - global_pos.x()
            if new_w >= min_w: rect.setLeft(global_pos.x())
        if "right" in edge: rect.setRight(global_pos.x())
        if "top" in edge:
            new_h = rect.bottom() - global_pos.y()
            if new_h >= min_h: rect.setTop(global_pos.y())
        if "bottom" in edge: rect.setBottom(global_pos.y())
        self.setGeometry(rect)
