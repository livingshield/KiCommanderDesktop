import os
import hashlib
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTableView, 
                             QPushButton, QLabel, QProgressBar, QCheckBox, 
                             QWidget, QHeaderView, QMenu)
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex, Signal, QThread, QSize, QObject
import qtawesome as qta
from fs_worker import ScanWorker, FileInfo
from queue_manager import QueueManager

class SyncModel(QAbstractTableModel):
    def __init__(self):
        super().__init__()
        # list of [checked, name, left_path, right_path, status (==, ->, <-, !=, !), size, date]
        self._items = []

    def rowCount(self, parent=QModelIndex()): return len(self._items)
    def columnCount(self, parent=QModelIndex()): return 4 # Check, Name, Dir, Action
    
    def headerData(self, section, orientation, role):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return ["", "Název", "Akce", "Stav"][section]
        return None

    def data(self, index, role):
        if not index.isValid(): return None
        row, col = index.row(), index.column()
        
        if role == Qt.CheckStateRole and col == 0:
            return Qt.Checked if self._items[row][0] else Qt.Unchecked
        
        if role == Qt.DisplayRole:
            if col == 1: return self._items[row][1]
            if col == 3: return self._items[row][4] # Arrow icon or symbol
            return ""
            
        if role == Qt.TextAlignmentRole:
            return Qt.AlignCenter
            
        if role == Qt.ForegroundRole:
            status = self._items[row][4]
            if status == "==": return "#a6e3a1" # Green
            if status in ["->", "<-"]: return "#89b4fa" # Blue
            if status == "!=": return "#f38ba8" # Red
            return None
            
        return None

    def setData(self, index, value, role):
        if role == Qt.CheckStateRole and index.column() == 0:
            self._items[index.row()][0] = (value == Qt.Checked)
            self.dataChanged.emit(index, index)
            return True
        return False

    def flags(self, index):
        f = Qt.ItemIsEnabled | Qt.ItemIsSelectable
        if index.column() == 0: f |= Qt.ItemIsUserCheckable
        return f

class SyncWorker(QObject):
    finished = Signal(list)
    progress = Signal(str)

    def __init__(self, left_dir, right_dir):
        super().__init__()
        self.left_dir = left_dir
        self.right_dir = right_dir

    def run(self):
        # 1. Scan both sides
        left_files = self._scan(self.left_dir)
        right_files = self._scan(self.right_dir)
        
        # 2. Compare
        results = []
        all_names = sorted(list(set(left_files.keys()) | set(right_files.keys())))
        
        for name in all_names:
            l = left_files.get(name)
            r = right_files.get(name)
            
            # [checked, name, left_full, right_full, status]
            if l and not r:
                results.append([True, name, l.full_path, None, "->"])
            elif not l and r:
                results.append([True, name, None, r.full_path, "<-"])
            else:
                # Both exist
                if l.size_bytes == r.size_bytes and abs(l.mtime - r.mtime) < 2:
                    results.append([False, name, l.full_path, r.full_path, "=="])
                else:
                    results.append([True, name, l.full_path, r.full_path, "!="])
                    
        self.finished.emit(results)

    def _scan(self, path):
        # Simplified recursive scan
        data = {}
        for root, dirs, files in os.walk(path):
            for f in files:
                full = os.path.join(root, f)
                rel = os.path.relpath(full, path)
                stat = os.stat(full)
                data[rel] = FileInfo(f, "", "", "", False, full, stat.st_size, stat.st_mtime)
        return data

class SyncDialog(QDialog):
    def __init__(self, left_path, right_path, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMinimumSize(1000, 700)
        self.left_path = left_path
        self.right_path = right_path
        self._drag_pos = None

        self.setup_ui()

    def setup_ui(self):
        self.outer_layout = QVBoxLayout(self)
        self.outer_layout.setContentsMargins(0, 0, 0, 0)
        self.container = QWidget()
        self.container.setObjectName("DialogContainer")
        self.outer_layout.addWidget(self.container)
        
        self.main_layout = QVBoxLayout(self.container)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # Title Bar
        self.title_bar = QWidget()
        self.title_bar.setObjectName("DialogTitleBar")
        self.title_bar.setFixedHeight(40)
        tb_layout = QHBoxLayout(self.title_bar)
        tb_layout.setContentsMargins(15, 0, 10, 0)
        title_icon = QLabel(); title_icon.setPixmap(qta.icon("fa5s.sync", color="#89b4fa").pixmap(20, 20))
        tb_layout.addWidget(title_icon)
        title_label = QLabel(f"Synchronizace: {os.path.basename(self.left_path)} ↔ {os.path.basename(self.right_path)}")
        title_label.setStyleSheet("font-weight: bold; color: #cdd6f4;")
        tb_layout.addWidget(title_label)
        tb_layout.addStretch()
        close_btn = QPushButton(); close_btn.setIcon(qta.icon("fa5s.times", color="#cdd6f4"))
        close_btn.setFixedSize(30, 30); close_btn.setObjectName("TitleCloseBtn"); close_btn.clicked.connect(self.reject)
        tb_layout.addWidget(close_btn)
        self.main_layout.addWidget(self.title_bar)

        # Content
        content = QWidget()
        content.setObjectName("DialogContent")
        layout = QVBoxLayout(content)
        
        self.status_label = QLabel("Připraven k porovnání...")
        layout.addWidget(self.status_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0); self.progress_bar.hide()
        layout.addWidget(self.progress_bar)

        self.table_view = QTableView()
        self.model = SyncModel()
        self.table_view.setModel(self.model)
        self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_view.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table_view.setShowGrid(False)
        self.table_view.setAlternatingRowColors(True)
        layout.addWidget(self.table_view)

        btns = QHBoxLayout()
        self.compare_btn = QPushButton(" Porovnat složky")
        self.compare_btn.setIcon(qta.icon("fa5s.search", color="#89b4fa"))
        self.compare_btn.clicked.connect(self._start_compare)
        
        self.sync_btn = QPushButton(" Provést synchronizaci")
        self.sync_btn.setIcon(qta.icon("fa5s.bolt", color="#a6e3a1"))
        self.sync_btn.setEnabled(False)
        self.sync_btn.clicked.connect(self._execute_sync)
        
        btns.addWidget(self.compare_btn)
        btns.addStretch()
        btns.addWidget(self.sync_btn)
        layout.addLayout(btns)
        self.main_layout.addWidget(content)

        self.setStyleSheet("""
            #DialogContainer { background-color: #1e1e2e; border: 1px solid #313244; border-radius: 10px; }
            #DialogTitleBar { background-color: #11111b; border-top-left-radius: 10px; border-top-right-radius: 10px; border-bottom: 1px solid #313244; }
            #DialogContent { background-color: #1e1e2e; border-bottom-left-radius: 10px; border-bottom-right-radius: 10px; }
            #TitleCloseBtn { background: transparent; border: none; border-radius: 15px; }
            #TitleCloseBtn:hover { background-color: #f38ba8; }
            QTableView { background-color: #181825; color: #cdd6f4; border: 1px solid #313244; }
            QHeaderView::section { background-color: #11111b; color: #cdd6f4; padding: 5px; border: none; border-right: 1px solid #313244; border-bottom: 1px solid #313244; font-weight: bold; }
            QPushButton { background-color: #313244; color: #cdd6f4; border: 1px solid #45475a; border-radius: 5px; padding: 8px 15px; }
            QPushButton:hover { background-color: #45475a; border-color: #89b4fa; }
        """)

    def _start_compare(self):
        self.compare_btn.setEnabled(False)
        self.progress_bar.show()
        self.status_label.setText("Porovnávám soubory...")
        
        self.thread = QThread()
        self.worker = SyncWorker(self.left_path, self.right_path)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self._on_finished)
        self.thread.start()

    def _on_finished(self, results):
        self.thread.quit(); self.thread.wait()
        self.progress_bar.hide()
        self.compare_btn.setEnabled(True)
        self.sync_btn.setEnabled(True)
        
        self.model.beginResetModel()
        self.model._items = results
        self.model.endResetModel()
        self.status_label.setText(f"Porovnání dokončeno. Nalezeno {len(results)} položek.")

    def _execute_sync(self):
        # Sort items into copy tasks
        to_right = []
        to_left = []
        
        for item in self.model._items:
            if not item[0]: continue # Not checked
            
            if item[4] in ["->", "!="]:
                to_right.append(item[2])
            elif item[4] == "<-":
                to_left.append(item[3])
                
        if to_right:
            QueueManager.instance().add_to_queue('copy', to_right, self.right_path)
        if to_left:
            QueueManager.instance().add_to_queue('copy', to_left, self.left_path)
            
        self.accept()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.title_bar.underMouse():
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
    def mouseMoveEvent(self, event):
        if self._drag_pos and event.buttons() & Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
    def mouseReleaseEvent(self, event): self._drag_pos = None

