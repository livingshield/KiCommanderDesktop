import os
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QWidget, QPushButton, QSizeGrip)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QFont
import qtawesome as qta
from quick_view_widget import QuickViewWidget

class PreviewDialog(QDialog):
    def __init__(self, file_path, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMinimumSize(700, 500)
        self.setMouseTracking(True)
        self._drag_pos = None
        self._resize_margin = 8
        self._resizing = False
        self._resize_edge = None # Can be 'left', 'right', 'top', 'bottom', 'top-left', etc.
        self.setup_ui()

    def setup_ui(self):
        # Outer wrapper
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
        icon_lbl.setPixmap(qta.icon("fa5s.eye", color="#89b4fa").pixmap(16, 16))
        tb_layout.addWidget(icon_lbl)
        title_lbl = QLabel(f"Preview – {os.path.basename(self.file_path)}")
        title_lbl.setStyleSheet("color: #cdd6f4; font-weight: bold; font-size: 10pt;")
        tb_layout.addWidget(title_lbl)
        tb_layout.addStretch()
        # File size in title bar
        try:
            size = os.path.getsize(self.file_path)
            size_lbl = QLabel(self._format_size(size))
            size_lbl.setStyleSheet("color: #6c7086; font-size: 9pt;")
            tb_layout.addWidget(size_lbl)
        except OSError:
            pass
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
        layout.setContentsMargins(8, 8, 8, 8)
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
            QScrollArea { background-color: #181825; border: none; }
        """)

        # Využití nového unifikovaného komponentu pro prohlížení souborů
        self.viewer = QuickViewWidget(self)
        layout.addWidget(self.viewer)
        self.viewer.load_file(self.file_path)

        # Autoplay if media (chceme zachovat chování pro samostatné preview okno)
        if hasattr(self.viewer, 'player') and self.viewer.player:
             self.viewer.player.play()

        # Footer with Size Grip (the "dots")
        footer_layout = QHBoxLayout()
        footer_layout.setContentsMargins(0, 0, 0, 0)
        footer_layout.addStretch()
        
        # We'll use a QSizeGrip which already has the dots in most styles,
        # but we'll ensure it's positioned correctly.
        grip = QSizeGrip(self)
        grip.setFixedSize(16, 16)
        footer_layout.addWidget(grip, 0, Qt.AlignBottom | Qt.AlignRight)
        
        main_layout.addLayout(footer_layout)



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
            # Update cursor based on edge
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
        """Returns the edge/corner at the given local position."""
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
            if new_w >= min_w:
                rect.setLeft(global_pos.x())
        if "right" in edge:
            rect.setRight(global_pos.x())
        if "top" in edge:
            new_h = rect.bottom() - global_pos.y()
            if new_h >= min_h:
                rect.setTop(global_pos.y())
        if "bottom" in edge:
            rect.setBottom(global_pos.y())
            
        self.setGeometry(rect)

    @staticmethod
    def _format_size(size):
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.0f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"
