import os
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPlainTextEdit, QTabWidget, QWidget, QScrollArea,
                             QPushButton)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QFont
import qtawesome as qta
from syntax_highlighter import CodeHighlighter

class PreviewDialog(QDialog):
    def __init__(self, file_path, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMinimumSize(700, 500)
        self._drag_pos = None
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
            QPlainTextEdit {
                background-color: #181825; color: #cdd6f4;
                border: 1px solid #313244; border-radius: 4px; padding: 4px;
                font-family: 'Consolas', 'Courier New', monospace; font-size: 10pt;
            }
            QScrollArea { background-color: #181825; border: none; }
        """)

        ext = os.path.splitext(self.file_path)[1].lower()

        if ext in [".jpg", ".jpeg", ".png", ".bmp", ".gif", ".ico", ".svg"]:
            self.show_image(layout)
        elif ext in [".txt", ".py", ".md", ".json", ".xml", ".html", ".css", ".js",
                     ".csv", ".log", ".ini", ".cfg", ".yml", ".yaml", ".toml",
                     ".bat", ".cmd", ".sh", ".ps1", ".c", ".cpp", ".h", ".java",
                     ".rs", ".go", ".ts", ".tsx", ".jsx", ".vue", ".qss"]:
            self.show_text(layout)
        else:
            self.show_hex(layout)

    def show_image(self, layout):
        scroll = QScrollArea()
        label = QLabel()
        pixmap = QPixmap(self.file_path)
        if pixmap.width() > 680:
            pixmap = pixmap.scaledToWidth(680, Qt.SmoothTransformation)
        label.setPixmap(pixmap)
        label.setAlignment(Qt.AlignCenter)
        scroll.setWidget(label)
        scroll.setWidgetResizable(True)
        layout.addWidget(scroll)

    def show_text(self, layout):
        editor = QPlainTextEdit()
        editor.setReadOnly(True)
        editor.setFont(QFont("Consolas", 10))
        try:
            with open(self.file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read(1024 * 512)
            editor.setPlainText(content)
            ext = os.path.splitext(self.file_path)[1]
            self._highlighter = CodeHighlighter(editor.document(), ext)
        except Exception as e:
            editor.setPlainText(f"Error reading file: {e}")
        layout.addWidget(editor)

    def show_hex(self, layout):
        editor = QPlainTextEdit()
        editor.setReadOnly(True)
        editor.setFont(QFont("Consolas", 10))
        try:
            with open(self.file_path, "rb") as f:
                data = f.read(4096)
            lines = []
            for i in range(0, len(data), 16):
                chunk = data[i:i+16]
                hex_part = " ".join(f"{b:02X}" for b in chunk)
                ascii_part = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
                lines.append(f"{i:08X}  {hex_part:<48}  {ascii_part}")
            editor.setPlainText("\n".join(lines))
        except Exception as e:
            editor.setPlainText(f"Error reading file: {e}")
        layout.addWidget(editor)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and event.position().y() < 38:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_pos and event.buttons() & Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

    @staticmethod
    def _format_size(size):
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.0f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"
