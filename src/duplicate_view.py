import csv
import os
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTableView, 
                             QPushButton, QLabel, QFileDialog, QMessageBox, 
                             QProgressBar, QHeaderView, QWidget)
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex, QPoint, Signal
import qtawesome as qta
from duplicate_finder import DuplicateFinderThread
from batch_delete import BatchDeleteDialog

class DuplicateModel(QAbstractTableModel):
    def __init__(self, data=None):
        super().__init__()
        self._items = []  # list of [checked, name, ext, path, size, hash_group]
        if data:
            self.set_data(data)

    def set_data(self, data):
        self.beginResetModel()
        self._items = []
        if data:
            for h, paths in data.items():
                for p in paths:
                    try:
                        size = os.path.getsize(p) if os.path.exists(p) else 0
                        name = os.path.basename(p)
                        ext = os.path.splitext(p)[1].lower()
                        # [Checked, Name, Ext, Path, Size, Hash]
                        self._items.append([False, name, ext, p, size, h[:8]])
                    except:
                        pass
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()): return len(self._items)
    def columnCount(self, parent=QModelIndex()): return 6
    
    def headerData(self, section, orientation, role):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return ["", "Název", "Přípona", "Cesta", "Velikost (B)", "Skupina"][section]
        return None

    def data(self, index, role):
        if not index.isValid(): return None
        row, col = index.row(), index.column()
        
        if role == Qt.CheckStateRole and col == 0:
            return Qt.Checked if self._items[row][0] else Qt.Unchecked
        
        if role == Qt.DisplayRole:
            val = self._items[row][col]
            if col == 4: # Size
                return f"{val:,}".replace(",", " ")
            return val
        
        if role == Qt.TextAlignmentRole:
            if col == 4: return Qt.AlignRight | Qt.AlignVCenter
            return Qt.AlignLeft | Qt.AlignVCenter
            
        if role == Qt.ForegroundRole:
            if col == 5: # Hash/Group
                return qta.icon("fa5s.circle", color="#89b4fa") # Just a hint, but usually Color
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
        if index.column() == 0:
            f |= Qt.ItemIsUserCheckable
        return f

    def sort(self, column, order=Qt.AscendingOrder):
        self.layoutAboutToBeChanged.emit()
        reverse = (order == Qt.DescendingOrder)
        self._items.sort(key=lambda x: x[column], reverse=reverse)
        self.layoutChanged.emit()

    def get_checked_paths(self):
        return [item[3] for item in self._items if item[0]]

class DuplicateDialog(QDialog):
    def __init__(self, start_folders, parent=None):
        super().__init__(parent, Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMinimumSize(1000, 700)
        self.start_folders = start_folders
        self._drag_pos = None

        self.setup_ui()

    def setup_ui(self):
        # Outer container for rounded corners and shadow
        self.outer_layout = QVBoxLayout(self)
        self.outer_layout.setContentsMargins(10, 10, 10, 10) # Padding for shadow
        
        self.container = QWidget()
        self.container.setObjectName("DialogContainer")
        self.outer_layout.addWidget(self.container)
        
        self.main_layout = QVBoxLayout(self.container)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # Custom Title Bar
        self.title_bar = QWidget()
        self.title_bar.setObjectName("DialogTitleBar")
        self.title_bar.setFixedHeight(45)
        tb_layout = QHBoxLayout(self.title_bar)
        tb_layout.setContentsMargins(15, 0, 10, 0)
        
        title_icon = QLabel()
        title_icon.setPixmap(qta.icon("fa5s.clone", color="#89b4fa").pixmap(20, 20))
        tb_layout.addWidget(title_icon)
        
        title_label = QLabel("Vyhledávač duplicitních souborů")
        title_label.setStyleSheet("font-weight: bold; color: #cdd6f4; font-size: 14px;")
        tb_layout.addWidget(title_label)
        
        tb_layout.addStretch()
        
        close_btn = QPushButton()
        close_btn.setIcon(qta.icon("fa5s.times", color="#cdd6f4"))
        close_btn.setFixedSize(32, 32)
        close_btn.setObjectName("TitleCloseBtn")
        close_btn.clicked.connect(self.reject)
        tb_layout.addWidget(close_btn)
        
        self.main_layout.addWidget(self.title_bar)

        # Content area
        self.content = QWidget()
        self.content.setObjectName("DialogContent")
        layout = QVBoxLayout(self.content)
        layout.setContentsMargins(15, 10, 15, 15)
        
        self.status_label = QLabel("Připraven ke skenování...")
        self.status_label.setStyleSheet("color: #a6adc8; margin-bottom: 5px;")
        layout.addWidget(self.status_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.hide()
        self.progress_bar.setFixedHeight(4)
        self.progress_bar.setStyleSheet("QProgressBar::chunk { background-color: #89b4fa; }")
        layout.addWidget(self.progress_bar)

        self.table_view = QTableView()
        self.model = DuplicateModel()
        self.table_view.setModel(self.model)
        self.table_view.setSortingEnabled(True)
        self.table_view.setSelectionBehavior(QTableView.SelectRows)
        self.table_view.setShowGrid(False)
        self.table_view.setAlternatingRowColors(True)
        
        self.table_view.horizontalHeader().setStretchLastSection(True)
        self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table_view.verticalHeader().setVisible(False)
        
        layout.addWidget(self.table_view)

        # Buttons
        btns_layout = QHBoxLayout()
        btns_layout.setContentsMargins(0, 10, 0, 0)
        
        self.scan_btn = QPushButton(" Spustit sken")
        self.scan_btn.setIcon(qta.icon("fa5s.play", color="#a6e3a1"))
        self.scan_btn.clicked.connect(self._start_scan)
        
        self.export_btn = QPushButton(" Exportovat CSV")
        self.export_btn.setIcon(qta.icon("fa5s.file-csv", color="#f9e2af"))
        self.export_btn.clicked.connect(self._export_csv)
        self.export_btn.setEnabled(False)

        self.delete_btn = QPushButton(" Smazat vybrané")
        self.delete_btn.setIcon(qta.icon("fa5s.trash-alt", color="#f38ba8"))
        self.delete_btn.setStyleSheet("QPushButton { color: #f38ba8; font-weight: bold; }")
        self.delete_btn.clicked.connect(self._delete_selected)
        self.delete_btn.setEnabled(False)

        btns_layout.addWidget(self.scan_btn)
        btns_layout.addWidget(self.export_btn)
        btns_layout.addStretch()
        btns_layout.addWidget(self.delete_btn)
        layout.addLayout(btns_layout)
        
        self.main_layout.addWidget(self.content)

        # Set Styles
        self.setStyleSheet("""
            #DialogContainer {
                background-color: #1e1e2e;
                border: 1px solid #313244;
                border-radius: 10px;
            }
            #DialogTitleBar {
                background-color: #11111b;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
                border-bottom: 1px solid #313244;
            }
            #DialogContent {
                background-color: #1e1e2e;
                border-bottom-left-radius: 10px;
                border-bottom-right-radius: 10px;
            }
            #TitleCloseBtn {
                background: transparent; border: none; border-radius: 15px;
            }
            #TitleCloseBtn:hover { background-color: #f38ba8; }
            
            QTableView {
                background-color: #181825;
                color: #cdd6f4;
                border: 1px solid #313244;
                gridline-color: #313244;
                selection-background-color: #313244;
                selection-color: #89b4fa;
                border-radius: 5px;
            }
            QHeaderView::section {
                background-color: #11111b !important;
                color: #cdd6f4 !important;
                padding: 10px;
                border: none;
                border-right: 1px solid #313244;
                border-bottom: 2px solid #313244;
                font-weight: bold;
            }
            QPushButton {
                background-color: #313244;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 5px;
                padding: 8px 15px;
                font-size: 13px;
            }
            QPushButton:hover { background-color: #45475a; border-color: #89b4fa; }
            QPushButton:disabled { color: #585b70; border-color: #313244; }
            
            QProgressBar {
                background-color: #313244;
                border: none;
                border-radius: 2px;
                text-align: center;
            }
        """)

        self.thread = None

    def _start_scan(self):
        self.scan_btn.setEnabled(False)
        self.progress_bar.show()
        self.status_label.setText("Skenuji... (to může chvíli trvat)")
        
        self.thread = DuplicateFinderThread(self.start_folders)
        self.thread.worker.progress.connect(self.status_label.setText)
        self.thread.worker.finished.connect(self._on_finished)
        self.thread.worker.error.connect(self._on_error)
        self.thread.start()

    def _on_finished(self, results):
        self.progress_bar.hide()
        self.scan_btn.setEnabled(True)
        self.model.set_data(results)
        self.export_btn.setEnabled(True)
        self.delete_btn.setEnabled(True)
        self.status_label.setText(f"Nalezeno {len(self.model._items)} souborů v {len(results)} skupinách duplicit.")
        
        # Set Column Widths
        header = self.table_view.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents) # Checkbox
        header.setSectionResizeMode(1, QHeaderView.Interactive)      # Name
        header.setSectionResizeMode(2, QHeaderView.Interactive)      # Ext
        header.setSectionResizeMode(3, QHeaderView.Stretch)          # Path (Widest)
        header.setSectionResizeMode(4, QHeaderView.Interactive)      # Size
        header.setSectionResizeMode(5, QHeaderView.Interactive)      # Group

        self.table_view.setColumnWidth(1, 150) # Name
        self.table_view.setColumnWidth(2, 70)  # Ext
        self.table_view.setColumnWidth(4, 120) # Size
        self.table_view.setColumnWidth(5, 100) # Group

    def _on_error(self, err):
        self.progress_bar.hide()
        self.scan_btn.setEnabled(True)
        QMessageBox.critical(self, "Chyba skenu", err)

    def _export_csv(self):
        path, _ = QFileDialog.getSaveFileName(self, "Exportovat výsledky", "", "CSV Files (*.csv)")
        if path:
            try:
                with open(path, "w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow(["Název", "Přípona", "Cesta", "Velikost", "Skupina"])
                    for item in self.model._items:
                        writer.writerow(item[1:])
                QMessageBox.information(self, "Export", "Výsledky byly úspěšně uloženy.")
            except Exception as e:
                QMessageBox.critical(self, "Chyba exportu", str(e))

    def _delete_selected(self):
        paths = self.model.get_checked_paths()
        if not paths:
            QMessageBox.information(self, "Smazat", "Nejdříve zaškrtněte soubory ke smazání.")
            return

        dlg = BatchDeleteDialog(paths, self)
        if dlg.exec() == QDialog.Accepted:
            count, errors = BatchDeleteDialog.execute_deletion(paths)
            QMessageBox.information(self, "Smazáno", f"Úspěšně smazáno {count} souborů.")
            if errors:
                QMessageBox.warning(self, "Chyby při mazání", "\n".join(errors[:10]))
            
            self.model.layoutAboutToBeChanged.emit()
            self.model._items = [i for i in self.model._items if i[3] not in paths]
            self.model.layoutChanged.emit()

    # Move window via title bar
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.title_bar.underMouse():
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_pos and event.buttons() & Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
