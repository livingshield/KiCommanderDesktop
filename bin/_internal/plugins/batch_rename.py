"""
Batch Rename Plugin – renames selected files using a pattern.
"""
import os
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
                             QWidget, QHeaderView)
from PySide6.QtCore import Qt

# Plugin interface
name = "Batch Rename"
menu_text = "Batch Rename..."


class BatchRenameDialog(QDialog):
    def __init__(self, files, parent=None):
        super().__init__(parent)
        self.files = files
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMinimumSize(600, 400)
        self._drag_pos = None
        self.setup_ui()

    def setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        container = QWidget()
        container.setObjectName("DialogContainer")
        outer.addWidget(container)
        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Title bar
        title_bar = QWidget()
        title_bar.setFixedHeight(38)
        title_bar.setObjectName("DialogTitleBar")
        tb = QHBoxLayout(title_bar)
        tb.setContentsMargins(12, 0, 6, 0)
        title = QLabel("Batch Rename")
        title.setStyleSheet("color: #cdd6f4; font-weight: bold; font-size: 10pt;")
        tb.addWidget(title)
        tb.addStretch()
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(28, 28)
        close_btn.setObjectName("TitleCloseBtn")
        close_btn.clicked.connect(self.reject)
        tb.addWidget(close_btn)
        main_layout.addWidget(title_bar)

        content = QWidget()
        content.setObjectName("DialogContent")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(12, 8, 12, 12)
        main_layout.addWidget(content, 1)

        self.setStyleSheet("""
            #DialogContainer { background-color: #1e1e2e; border: 1px solid #313244; border-radius: 8px; }
            #DialogTitleBar { background-color: #11111b; border-top-left-radius: 8px; border-top-right-radius: 8px; border-bottom: 1px solid #313244; }
            #TitleCloseBtn { background: transparent; border: none; border-radius: 14px; color: #cdd6f4; }
            #TitleCloseBtn:hover { background-color: #f38ba8; }
            #DialogContent { background-color: #1e1e2e; }
            QLabel { color: #cdd6f4; font-size: 10pt; }
            QLineEdit { background-color: #11111b; border: 1px solid #313244; border-radius: 4px; padding: 6px; color: #f5c2e7; font-size: 10pt; }
            QLineEdit:focus { border: 1px solid #89b4fa; }
            QPushButton { background-color: #313244; border: 1px solid #45475a; border-radius: 4px; padding: 6px 16px; color: #cdd6f4; font-weight: bold; }
            QPushButton:hover { background-color: #45475a; border-color: #89b4fa; }
            QTableWidget { background-color: #181825; border: 1px solid #313244; color: #cdd6f4; font-size: 10pt; }
            QHeaderView::section { background-color: #11111b; color: #a6adc8; padding: 6px; border: none; border-right: 1px solid #313244; font-weight: bold; }
        """)

        # Find & Replace row
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Find:"))
        self.find_input = QLineEdit()
        self.find_input.setPlaceholderText("text to find in filenames")
        self.find_input.textChanged.connect(self.update_preview)
        row1.addWidget(self.find_input)
        row1.addWidget(QLabel("Replace:"))
        self.replace_input = QLineEdit()
        self.replace_input.setPlaceholderText("replacement text")
        self.replace_input.textChanged.connect(self.update_preview)
        row1.addWidget(self.replace_input)
        layout.addLayout(row1)

        # Preview table
        self.table = QTableWidget(len(self.files), 2)
        self.table.setHorizontalHeaderLabels(["Original", "New Name"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        for i, f in enumerate(self.files):
            self.table.setItem(i, 0, QTableWidgetItem(os.path.basename(f)))
            self.table.setItem(i, 1, QTableWidgetItem(os.path.basename(f)))
        layout.addWidget(self.table)

        # Buttons
        btns = QHBoxLayout()
        btns.addStretch()
        rename_btn = QPushButton("Rename All")
        rename_btn.clicked.connect(self.do_rename)
        btns.addWidget(rename_btn)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btns.addWidget(cancel_btn)
        layout.addLayout(btns)

    def update_preview(self):
        find = self.find_input.text()
        replace = self.replace_input.text()
        for i, f in enumerate(self.files):
            old_name = os.path.basename(f)
            if find:
                new_name = old_name.replace(find, replace)
            else:
                new_name = old_name
            self.table.setItem(i, 1, QTableWidgetItem(new_name))

    def do_rename(self):
        find = self.find_input.text()
        replace = self.replace_input.text()
        if not find:
            return
        for f in self.files:
            old_name = os.path.basename(f)
            new_name = old_name.replace(find, replace)
            if new_name != old_name:
                new_path = os.path.join(os.path.dirname(f), new_name)
                try:
                    os.rename(f, new_path)
                except OSError:
                    pass
        self.accept()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and event.position().y() < 38:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if self._drag_pos and event.buttons() & Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None


def action(selected_files, panel):
    """Plugin entry point – called by KiCommander."""
    if not selected_files:
        return
    dlg = BatchRenameDialog(selected_files, panel)
    if dlg.exec():
        panel.refresh_path(panel.current_path)
