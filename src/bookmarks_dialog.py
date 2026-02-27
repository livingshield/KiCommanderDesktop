import json
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, 
                               QTableWidgetItem, QPushButton, QHeaderView, QWidget,
                               QInputDialog, QMessageBox, QSizeGrip, QLabel)
from PySide6.QtCore import Qt, QSettings
import qtawesome as qta
from event_bus import bus

class BookmarksDialog(QDialog):
    def __init__(self, current_vfs_tag, current_path, parent=None):
        super().__init__(parent, Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMinimumSize(600, 400)
        self.settings = QSettings("KiCommander", "Desktop")
        
        # Get active panel current info
        self.current_vfs_tag = current_vfs_tag
        self.current_path = current_path

        self._load_bookmarks()

        self._drag_pos = None
        self._resize_margin = 8
        self._resizing = False
        self._resize_edge = None

        self.setup_ui()

    def _load_bookmarks(self):
        saved = self.settings.value("bookmarks/data", "[]")
        if isinstance(saved, str):
            try:
                self.bookmarks = json.loads(saved)
            except:
                self.bookmarks = []
        else:
            self.bookmarks = []
            
        # Migrate old favorites if they exist
        old_favs = self.settings.value("favorites/list", [])
        if isinstance(old_favs, str):
            old_favs = [old_favs]
        if old_favs:
            for p in old_favs:
                self.bookmarks.append({"name": p, "path": p})
            self.settings.remove("favorites/list")
            self._save_bookmarks()

    def _save_bookmarks(self):
        self.settings.setValue("bookmarks/data", json.dumps(self.bookmarks))

    def setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        
        container = QWidget()
        container.setObjectName("DialogContainer")
        outer.addWidget(container)
        
        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Title Bar
        title_bar = QWidget()
        title_bar.setFixedHeight(38)
        title_bar.setObjectName("DialogTitleBar")
        tb_layout = QHBoxLayout(title_bar)
        tb_layout.setContentsMargins(12, 0, 6, 0)
        icon_lbl = QLabel()
        icon_lbl.setPixmap(qta.icon("fa5s.bookmark", color="#fab387").pixmap(16, 16))
        tb_layout.addWidget(icon_lbl)
        title_lbl = QLabel("Správce záložek (Hotlist)")
        title_lbl.setStyleSheet("color: #cdd6f4; font-weight: bold;")
        tb_layout.addWidget(title_lbl)
        tb_layout.addStretch()
        close_btn = QPushButton()
        close_btn.setIcon(qta.icon("fa5s.times", color="#cdd6f4"))
        close_btn.setFixedSize(28, 28)
        close_btn.setObjectName("TitleCloseBtn")
        close_btn.clicked.connect(self.reject)
        tb_layout.addWidget(close_btn)
        main_layout.addWidget(title_bar)

        content = QWidget()
        content.setObjectName("DialogContent")
        layout = QHBoxLayout(content)
        layout.setContentsMargins(12, 12, 12, 12)
        
        # Table
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Název", "Cesta"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setColumnWidth(0, 150)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        layout.addWidget(self.table, 1)

        # Buttons Right
        btn_layout = QVBoxLayout()
        
        btn_add_curr = QPushButton(" Přidat aktuální")
        btn_add_curr.setIcon(qta.icon("fa5s.plus", color="#a6e3a1"))
        btn_add_curr.clicked.connect(self.add_current)
        btn_layout.addWidget(btn_add_curr)

        btn_add = QPushButton(" Přidat novou...")
        btn_add.setIcon(qta.icon("fa5s.folder-plus", color="#89b4fa"))
        btn_add.clicked.connect(self.add_new)
        btn_layout.addWidget(btn_add)
        
        btn_edit = QPushButton(" Upravit...")
        btn_edit.setIcon(qta.icon("fa5s.edit", color="#f9e2af"))
        btn_edit.clicked.connect(self.edit_selected)
        btn_layout.addWidget(btn_edit)

        btn_del = QPushButton(" Smazat")
        btn_del.setIcon(qta.icon("fa5s.trash", color="#f38ba8"))
        btn_del.clicked.connect(self.delete_selected)
        btn_layout.addWidget(btn_del)
        
        btn_layout.addSpacing(15)
        
        btn_up = QPushButton(" Nahoru")
        btn_up.setIcon(qta.icon("fa5s.arrow-up", color="#cdd6f4"))
        btn_up.clicked.connect(self.move_up)
        btn_layout.addWidget(btn_up)
        
        btn_down = QPushButton(" Dolů")
        btn_down.setIcon(qta.icon("fa5s.arrow-down", color="#cdd6f4"))
        btn_down.clicked.connect(self.move_down)
        btn_layout.addWidget(btn_down)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        main_layout.addWidget(content, 1)

        grip_layout = QHBoxLayout()
        grip_layout.setContentsMargins(0, 0, 0, 0)
        grip_layout.addStretch()
        grip = QSizeGrip(self)
        grip.setFixedSize(16, 16)
        grip_layout.addWidget(grip, 0, Qt.AlignBottom | Qt.AlignRight)
        main_layout.addLayout(grip_layout)
        
        self.setStyleSheet("""
            #DialogContainer { background-color: #1e1e2e; border: 1px solid #313244; border-radius: 8px; }
            #DialogTitleBar { background-color: #11111b; border-top-left-radius: 8px; border-top-right-radius: 8px; border-bottom: 1px solid #313244; }
            #TitleCloseBtn { background: transparent; border: none; border-radius: 14px; }
            #TitleCloseBtn:hover { background-color: #f38ba8; }
            #DialogContent { background-color: #1e1e2e; border-bottom-left-radius: 8px; border-bottom-right-radius: 8px; }
            QTableWidget { background-color: #181825; border: 1px solid #313244; color: #cdd6f4; gridline-color: #313244; }
            QHeaderView::section { background-color: #11111b; color: #a6adc8; padding: 4px; border: 1px solid #313244; }
            QPushButton { background-color: #313244; color: #cdd6f4; border: 1px solid #45475a; border-radius: 4px; padding: 6px 12px; }
            QPushButton:hover { background-color: #45475a; border-color: #89b4fa; }
        """)

        self.populate_table()

    def populate_table(self):
        self.table.setRowCount(0)
        for b in self.bookmarks:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(b.get("name", "")))
            self.table.setItem(row, 1, QTableWidgetItem(b.get("path", "")))

    def add_current(self):
        path = self.current_vfs_tag if self.current_vfs_tag else self.current_path
        name, ok = QInputDialog.getText(self, "Přidat záložku", "Název:", text=path)
        if ok and name:
            self.bookmarks.append({"name": name, "path": path})
            self._save_bookmarks()
            self.populate_table()

    def add_new(self):
        name, ok = QInputDialog.getText(self, "Nová záložka", "Název:")
        if ok and name:
            path, ok2 = QInputDialog.getText(self, "Nová záložka", "Cesta:", text="")
            if ok2 and path:
                self.bookmarks.append({"name": name, "path": path})
                self._save_bookmarks()
                self.populate_table()

    def edit_selected(self):
        row = self.table.currentRow()
        if row >= 0:
            b = self.bookmarks[row]
            name, ok = QInputDialog.getText(self, "Upravit", "Název:", text=b.get("name", ""))
            if ok and name:
                path, ok2 = QInputDialog.getText(self, "Upravit", "Cesta:", text=b.get("path", ""))
                if ok2 and path:
                    self.bookmarks[row] = {"name": name, "path": path}
                    self._save_bookmarks()
                    self.populate_table()
                    self.table.selectRow(row)

    def delete_selected(self):
        row = self.table.currentRow()
        if row >= 0:
            del self.bookmarks[row]
            self._save_bookmarks()
            self.populate_table()

    def move_up(self):
        row = self.table.currentRow()
        if row > 0:
            self.bookmarks[row], self.bookmarks[row-1] = self.bookmarks[row-1], self.bookmarks[row]
            self._save_bookmarks()
            self.populate_table()
            self.table.selectRow(row-1)

    def move_down(self):
        row = self.table.currentRow()
        if row >= 0 and row < len(self.bookmarks) - 1:
            self.bookmarks[row], self.bookmarks[row+1] = self.bookmarks[row+1], self.bookmarks[row]
            self._save_bookmarks()
            self.populate_table()
            self.table.selectRow(row+1)

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
