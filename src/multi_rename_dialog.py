import os
import re
import datetime
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTableView, 
                             QPushButton, QLabel, QLineEdit, QGroupBox, 
                             QHeaderView, QWidget, QSpinBox, QCheckBox, 
                             QSplitter, QMessageBox, QSizeGrip)
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex, Signal, QTimer
import qtawesome as qta

class RenameModel(QAbstractTableModel):
    def __init__(self, items=None):
        super().__init__()
        # list of [FileInfo, original_name, new_name, status_icon, full_path]
        self._items = []
        if items:
            for f in items:
                self._items.append([f, f.name, f.name, "", f.full_path])

    def rowCount(self, parent=QModelIndex()): return len(self._items)
    def columnCount(self, parent=QModelIndex()): return 3
    
    def headerData(self, section, orientation, role):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return ["Původní název", "Nový název", "Stav"][section]
        return None

    def data(self, index, role):
        if not index.isValid(): return None
        row, col = index.row(), index.column()
        
        if role == Qt.DisplayRole:
            if col == 0: return self._items[row][1]
            if col == 1: return self._items[row][2]
            if col == 2: return self._items[row][3]
        
        if role == Qt.ForegroundRole:
            if col == 2:
                if self._items[row][3] == "Chyba": return "#f38ba8"
                if self._items[row][3] == "OK": return "#a6e3a1"
            return None
            
        return None

    def update_new_names(self, new_names_list):
        self.layoutAboutToBeChanged.emit()
        for i, name in enumerate(new_names_list):
            if i < len(self._items):
                self._items[i][2] = name
        self.layoutChanged.emit()

class MultiRenameDialog(QDialog):
    def __init__(self, selected_files, vfs=None, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMinimumSize(1100, 750)
        self.setMouseTracking(True)
        self.files = selected_files
        self.vfs = vfs
        self._drag_pos = None
        self._resize_margin = 8
        self._resizing = False
        self._resize_edge = None

        self.setup_ui()
        self._update_preview()

    def setup_ui(self):
        self.outer_layout = QVBoxLayout(self)
        self.outer_layout.setContentsMargins(0, 0, 0, 0)
        
        self.container = QWidget()
        self.container.setObjectName("DialogContainer")
        self.outer_layout.addWidget(self.container)
        
        self.main_layout = QVBoxLayout(self.container)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # Custom Title Bar
        self.title_bar = QWidget()
        self.title_bar.setObjectName("DialogTitleBar")
        self.title_bar.setFixedHeight(40)
        tb_layout = QHBoxLayout(self.title_bar)
        tb_layout.setContentsMargins(15, 0, 10, 0)
        
        title_icon = QLabel()
        title_icon.setPixmap(qta.icon("fa5s.edit", color="#89b4fa").pixmap(20, 20))
        tb_layout.addWidget(title_icon)
        
        title_label = QLabel("Hromadné přejmenování (Multi-Rename Tool)")
        title_label.setStyleSheet("font-weight: bold; color: #cdd6f4; font-size: 14px;")
        tb_layout.addWidget(title_label)
        
        tb_layout.addStretch()
        
        close_btn = QPushButton()
        close_btn.setIcon(qta.icon("fa5s.times", color="#cdd6f4"))
        close_btn.setFixedSize(30, 30)
        close_btn.setObjectName("TitleCloseBtn")
        close_btn.clicked.connect(self.reject)
        tb_layout.addWidget(close_btn)
        
        self.main_layout.addWidget(self.title_bar)

        # Content
        content = QWidget()
        content.setObjectName("DialogContent")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(15, 10, 15, 15)

        # Splitter for Table and Config
        splitter = QSplitter(Qt.Horizontal)
        
        # Left: Table
        self.table_view = QTableView()
        self.model = RenameModel(self.files)
        self.table_view.setModel(self.model)
        self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_view.setShowGrid(False)
        self.table_view.setAlternatingRowColors(True)
        splitter.addWidget(self.table_view)

        # Right: Config
        self.config_panel = QWidget()
        self.config_panel.setFixedWidth(350)
        config_layout = QVBoxLayout(self.config_panel)
        config_layout.setContentsMargins(10, 0, 0, 0)

        # Mask Group
        mask_group = QGroupBox("Maska přejmenování")
        mask_vbox = QVBoxLayout(mask_group)
        
        mask_vbox.addWidget(QLabel("Název:"))
        self.name_mask = QLineEdit("[N]")
        self.name_mask.setToolTip("[N] - Původní název\n[N1-5] - Výřez znaků\n[C] - Počítadlo\n[D] - Datum")
        self.name_mask.textChanged.connect(self._update_preview)
        mask_vbox.addWidget(self.name_mask)

        mask_vbox.addWidget(QLabel("Přípona:"))
        self.ext_mask = QLineEdit("[E]")
        self.ext_mask.textChanged.connect(self._update_preview)
        mask_vbox.addWidget(self.ext_mask)
        
        config_layout.addWidget(mask_group)

        # Regex Group
        regex_group = QGroupBox("Regulární výrazy (Search / Replace)")
        regex_vbox = QVBoxLayout(regex_group)
        
        regex_vbox.addWidget(QLabel("Hledat:"))
        self.regex_search = QLineEdit()
        self.regex_search.textChanged.connect(self._update_preview)
        regex_vbox.addWidget(self.regex_search)
        
        regex_vbox.addWidget(QLabel("Nahradit:"))
        self.regex_replace = QLineEdit()
        self.regex_replace.textChanged.connect(self._update_preview)
        regex_vbox.addWidget(self.regex_replace)
        
        self.regex_check = QCheckBox("Použít Regex")
        self.regex_check.toggled.connect(self._update_preview)
        regex_vbox.addWidget(self.regex_check)
        
        config_layout.addWidget(regex_group)

        # Counter Group
        counter_group = QGroupBox("Počítadlo [C]")
        count_layout = QHBoxLayout(counter_group)
        count_layout.addWidget(QLabel("Start:"))
        self.count_start = QSpinBox()
        self.count_start.setRange(0, 999999)
        self.count_start.setValue(1)
        self.count_start.valueChanged.connect(self._update_preview)
        count_layout.addWidget(self.count_start)
        
        count_layout.addWidget(QLabel("Krok:"))
        self.count_step = QSpinBox()
        self.count_step.setRange(1, 100)
        self.count_step.setValue(1)
        self.count_step.valueChanged.connect(self._update_preview)
        count_layout.addWidget(self.count_step)
        
        config_layout.addWidget(counter_group)
        config_layout.addStretch()

        splitter.addWidget(self.config_panel)
        layout.addWidget(splitter)

        # Buttons
        btns = QHBoxLayout()
        self.rename_btn = QPushButton(" Provést změny")
        self.rename_btn.setIcon(qta.icon("fa5s.check", color="#a6e3a1"))
        self.rename_btn.setStyleSheet("font-weight: bold; color: #a6e3a1;")
        self.rename_btn.clicked.connect(self._execute_rename)
        
        self.cancel_btn = QPushButton(" Zrušit")
        self.cancel_btn.clicked.connect(self.reject)
        
        btns.addStretch()
        btns.addWidget(self.cancel_btn)
        btns.addWidget(self.rename_btn)
        layout.addLayout(btns)
        self.main_layout.addWidget(content)

        # Bottom Size Grip (the "dots")
        grip_layout = QHBoxLayout()
        grip_layout.setContentsMargins(0, 0, 0, 0)
        grip_layout.addStretch()
        self.grip = QSizeGrip(self)
        self.grip.setFixedSize(16, 16)
        grip_layout.addWidget(self.grip, 0, Qt.AlignBottom | Qt.AlignRight)
        self.main_layout.addLayout(grip_layout)

        # Styles
        self.setStyleSheet("""
            #DialogContainer { background-color: #1e1e2e; border: 1px solid #313244; border-radius: 10px; }
            #DialogTitleBar { background-color: #11111b; border-top-left-radius: 10px; border-top-right-radius: 10px; border-bottom: 1px solid #313244; }
            #DialogContent { background-color: #1e1e2e; border-bottom-left-radius: 10px; border-bottom-right-radius: 10px; }
            #TitleCloseBtn { background: transparent; border: none; border-radius: 15px; }
            #TitleCloseBtn:hover { background-color: #f38ba8; }
            QTableView { background-color: #181825; color: #cdd6f4; border: 1px solid #313244; border-radius: 5px; }
            QHeaderView::section { background-color: #11111b; color: #cdd6f4; padding: 5px; border: none; border-right: 1px solid #313244; border-bottom: 1px solid #313244; font-weight: bold; }
            QGroupBox { color: #89b4fa; font-weight: bold; border: 1px solid #313244; border-radius: 5px; margin-top: 10px; padding-top: 10px; }
            QLineEdit, QSpinBox { background-color: #11111b; border: 1px solid #313244; border-radius: 4px; padding: 5px; color: #cdd6f4; }
            QPushButton { background-color: #313244; color: #cdd6f4; border: 1px solid #45475a; border-radius: 5px; padding: 8px 15px; }
            QPushButton:hover { background-color: #45475a; border-color: #89b4fa; }
        """)

    def _update_preview(self):
        new_names = []
        pattern_name = self.name_mask.text()
        pattern_ext = self.ext_mask.text()
        
        start = self.count_start.value()
        step = self.count_step.value()
        
        for i, f in enumerate(self.files):
            # 1. Base components
            name_base = os.path.splitext(f.name)[0]
            ext_base = os.path.splitext(f.name)[1].lstrip(".")
            
            # 2. Parse Mask [N], [E], [C], [D]
            res_name = self._parse_mask(pattern_name, name_base, ext_base, start + (i * step))
            res_ext = self._parse_mask(pattern_ext, name_base, ext_base, start + (i * step))
            
            final_name = res_name
            if res_ext:
                final_name += "." + res_ext
            
            # 3. Regex
            if self.regex_check.isChecked() and self.regex_search.text():
                try:
                    final_name = re.sub(self.regex_search.text(), self.regex_replace.text(), final_name)
                except re.error:
                    pass # Invalid regex
            
            new_names.append(final_name)
        
        self.model.update_new_names(new_names)

    def _parse_mask(self, pattern, name, ext, counter):
        # [N]
        pattern = pattern.replace("[N]", name)
        # [E]
        pattern = pattern.replace("[E]", ext)
        # [C]
        pattern = pattern.replace("[C]", str(counter))
        # [D] - Current date
        if "[D]" in pattern:
            now = datetime.datetime.now().strftime("%Y-%m-%d")
            pattern = pattern.replace("[D]", now)
        
        # Substring [N1-5]
        m = re.search(r"\[N(\d+)-(\d+)\]", pattern)
        if m:
            s, e = int(m.group(1)), int(m.group(2))
            pattern = pattern.replace(m.group(0), name[s-1:e])
            
        return pattern

    def _execute_rename(self):
        # Dry-run check for duplicates
        new_names = [item[2] for item in self.model._items]
        if len(new_names) != len(set(new_names)):
            QMessageBox.warning(self, "Chyba", "Zadaná maska generuje duplicitní názvy souborů!")
            return
            
        # Emit results to main window
        self.accept()

    def get_rename_map(self):
        # List of (old_full_path, new_name)
        return [(item[4], item[2]) for item in self.model._items if item[1] != item[2]]

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            edge = self._get_edge(event.position().toPoint())
            if edge:
                self._resizing = True
                self._resize_edge = edge
                event.accept()
            elif self.title_bar.underMouse():
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
