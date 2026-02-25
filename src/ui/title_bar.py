import os
import sys
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
import qtawesome as qta

def get_assets_dir():
    """Return the assets directory regardless of whether we're running as a
    plain Python script or a PyInstaller bundle."""
    if getattr(sys, '_MEIPASS', None):
        return os.path.join(sys._MEIPASS, 'assets')
    else:
        src_dir = os.path.dirname(os.path.abspath(__file__))
        # We are in src/ui/ so assets are in src/../assets
        return os.path.abspath(os.path.join(src_dir, '..', '..', 'assets'))

ASSETS_DIR = get_assets_dir()

class CustomTitleBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setFixedHeight(35)
        self.setObjectName("TitleBar")
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 0, 0)
        layout.setSpacing(0)
        
        # Icon and title
        self.icon_label = QLabel()
        icon_path = os.path.join(ASSETS_DIR, "icon.png")
        if os.path.exists(icon_path):
            self.icon_label.setPixmap(QPixmap(icon_path).scaled(22, 22, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            self.icon_label.setPixmap(qta.icon("fa5s.rocket", color="#89b4fa").pixmap(22, 22))
        layout.addWidget(self.icon_label)
        
        self.title_label = QLabel("KiCommander Desktop")
        self.title_label.setObjectName("TitleLabel")
        layout.addWidget(self.title_label)
        
        layout.addStretch()
        
        # Window buttons
        btn_style = "QPushButton { border: none; padding: 5px; background: transparent; } QPushButton:hover { background-color: #313244; }"
        
        self.min_btn = QPushButton()
        self.min_btn.setIcon(qta.icon("fa5s.minus", color="#cdd6f4"))
        self.min_btn.setStyleSheet(btn_style)
        self.min_btn.clicked.connect(self.parent.showMinimized)
        layout.addWidget(self.min_btn)
        
        self.max_btn = QPushButton()
        self.max_btn.setIcon(qta.icon("fa5s.expand", color="#cdd6f4"))
        self.max_btn.setStyleSheet(btn_style)
        self.max_btn.clicked.connect(self.toggle_maximize)
        layout.addWidget(self.max_btn)
        
        self.close_btn = QPushButton()
        self.close_btn.setIcon(qta.icon("fa5s.times", color="#cdd6f4"))
        self.close_btn.setStyleSheet("QPushButton { border: none; padding: 5px; background: transparent; } QPushButton:hover { background-color: #f38ba8; }")
        self.close_btn.clicked.connect(self.parent.close)
        layout.addWidget(self.close_btn)
        
        self.drag_pos = None

    def toggle_maximize(self):
        if self.parent.isMaximized():
            self.parent.showNormal()
            self.max_btn.setIcon(qta.icon("fa5s.expand", color="#cdd6f4"))
        else:
            self.parent.showMaximized()
            self.max_btn.setIcon(qta.icon("fa5s.compress", color="#cdd6f4"))

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_pos = event.globalPosition().toPoint() - self.parent.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self.drag_pos:
            self.parent.move(event.globalPosition().toPoint() - self.drag_pos)
            event.accept()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.toggle_maximize()
