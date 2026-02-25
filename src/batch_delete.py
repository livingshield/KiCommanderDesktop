import os
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QListWidget, 
                             QPushButton, QLabel, QMessageBox, QWidget)
from PySide6.QtCore import Qt
import qtawesome as qta

class BatchDeleteDialog(QDialog):
    def __init__(self, file_paths, parent=None):
        super().__init__(parent, Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMinimumSize(550, 450)
        self.file_paths = file_paths
        self._drag_pos = None

        self.setup_ui()

    def setup_ui(self):
        self.outer_layout = QVBoxLayout(self)
        self.outer_layout.setContentsMargins(10, 10, 10, 10)
        
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
        
        title_icon = QLabel()
        title_icon.setPixmap(qta.icon("fa5s.trash-alt", color="#f38ba8").pixmap(20, 20))
        tb_layout.addWidget(title_icon)
        
        title_label = QLabel("Potvrzení smazání")
        title_label.setStyleSheet("font-weight: bold; color: #cdd6f4;")
        tb_layout.addWidget(title_label)
        tb_layout.addStretch()
        
        close_btn = QPushButton()
        close_btn.setIcon(qta.icon("fa5s.times", color="#cdd6f4"))
        close_btn.setFixedSize(30, 30); close_btn.setObjectName("TitleCloseBtn"); close_btn.clicked.connect(self.reject)
        tb_layout.addWidget(close_btn)
        self.main_layout.addWidget(self.title_bar)

        content = QWidget()
        content.setObjectName("DialogContent")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(15, 10, 15, 15)

        warning = QLabel(f"<b>Opravdu chcete nenávratně smazat {len(self.file_paths)} souborů?</b>")
        warning.setWordWrap(True)
        warning.setStyleSheet("color: #f38ba8; margin-bottom: 5px;")
        layout.addWidget(warning)

        self.list_widget = QListWidget()
        display_limit = 15
        for path in self.file_paths[:display_limit]:
            self.list_widget.addItem(path)
        if len(self.file_paths) > display_limit:
            self.list_widget.addItem(f"... a dalších {len(self.file_paths)-display_limit} souborů")
        layout.addWidget(self.list_widget)

        btns = QHBoxLayout()
        self.cancel_btn = QPushButton("Zrušit")
        self.cancel_btn.clicked.connect(self.reject)
        self.delete_btn = QPushButton("Smazat vše")
        self.delete_btn.setObjectName("DeleteBtn")
        self.delete_btn.clicked.connect(self.accept)
        btns.addStretch()
        btns.addWidget(self.cancel_btn)
        btns.addWidget(self.delete_btn)
        layout.addLayout(btns)
        
        self.main_layout.addWidget(content)

        self.setStyleSheet("""
            #DialogContainer { background-color: #1e1e2e; border: 1px solid #313244; border-radius: 10px; }
            #DialogTitleBar { background-color: #11111b; border-top-left-radius: 10px; border-top-right-radius: 10px; border-bottom: 1px solid #313244; }
            #DialogContent { background-color: #1e1e2e; border-bottom-left-radius: 10px; border-bottom-right-radius: 10px; }
            #TitleCloseBtn { background: transparent; border: none; border-radius: 15px; }
            #TitleCloseBtn:hover { background-color: #f38ba8; }
            QListWidget { background-color: #181825; color: #cdd6f4; border: 1px solid #313244; border-radius: 5px; }
            QPushButton { background-color: #313244; color: #cdd6f4; border: 1px solid #45475a; border-radius: 5px; padding: 6px 15px; }
            QPushButton#DeleteBtn { background-color: #f38ba8; color: #11111b; font-weight: bold; border: none; }
            QPushButton#DeleteBtn:hover { background-color: #f17b9b; }
        """)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.title_bar.underMouse():
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
    def mouseMoveEvent(self, event):
        if self._drag_pos and event.buttons() & Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
    def mouseReleaseEvent(self, event): self._drag_pos = None

    @staticmethod
    def execute_deletion(paths):
        success_count = 0
        errors = []
        for p in paths:
            try:
                if os.path.exists(p):
                    os.remove(p)
                    success_count += 1
            except Exception as e:
                errors.append(f"{os.path.basename(p)}: {e}")
        return success_count, errors
