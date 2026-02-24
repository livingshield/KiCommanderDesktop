import os
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPlainTextEdit, QTabWidget, QWidget, QScrollArea)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QFont
import qtawesome as qta

class PreviewDialog(QDialog):
    def __init__(self, file_path, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.setWindowTitle(f"Preview - {os.path.basename(file_path)}")
        self.setMinimumSize(700, 500)
        self.setup_ui()
        self.setWindowIcon(qta.icon("fa5s.eye", color="#89b4fa"))

    def setup_ui(self):
        self.setStyleSheet("""
            QDialog { background-color: #1e1e2e; }
            QLabel { color: #cdd6f4; font-size: 10pt; }
            QPlainTextEdit {
                background-color: #181825; color: #cdd6f4;
                border: 1px solid #313244; border-radius: 4px; padding: 4px;
                font-family: 'Consolas', 'Courier New', monospace; font-size: 10pt;
            }
            QScrollArea { background-color: #181825; border: none; }
        """)
        layout = QVBoxLayout(self)
        
        # File info header
        info = QHBoxLayout()
        info.addWidget(QLabel(f"File: {self.file_path}"))
        try:
            size = os.path.getsize(self.file_path)
            info.addWidget(QLabel(f"Size: {self._format_size(size)}"))
        except OSError:
            pass
        info.addStretch()
        layout.addLayout(info)

        ext = os.path.splitext(self.file_path)[1].lower()

        # Image preview
        if ext in [".jpg", ".jpeg", ".png", ".bmp", ".gif", ".ico", ".svg"]:
            self.show_image(layout)
        # Text preview
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
                content = f.read(1024 * 512)  # Max 512KB preview
            editor.setPlainText(content)
        except Exception as e:
            editor.setPlainText(f"Error reading file: {e}")
        layout.addWidget(editor)

    def show_hex(self, layout):
        editor = QPlainTextEdit()
        editor.setReadOnly(True)
        editor.setFont(QFont("Consolas", 10))
        try:
            with open(self.file_path, "rb") as f:
                data = f.read(4096)  # First 4KB
            
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

    @staticmethod
    def _format_size(size):
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.0f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"
