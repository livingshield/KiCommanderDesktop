import os
import time
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QFormLayout, QPushButton)
from PySide6.QtCore import Qt
import qtawesome as qta

class PropertiesDialog(QDialog):
    def __init__(self, file_path, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.setWindowTitle(f"Properties - {os.path.basename(file_path)}")
        self.setMinimumWidth(400)
        self.setup_ui()

    def setup_ui(self):
        self.setStyleSheet("""
            QDialog { background-color: #1e1e2e; }
            QLabel { color: #cdd6f4; font-size: 10pt; }
            QPushButton {
                background-color: #313244; border: 1px solid #45475a;
                border-radius: 4px; padding: 8px 18px; color: #cdd6f4;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #45475a; border-color: #89b4fa; }
        """)
        layout = QVBoxLayout(self)

        form = QFormLayout()
        
        name = os.path.basename(self.file_path)
        form.addRow("Name:", QLabel(name))
        form.addRow("Path:", QLabel(self.file_path))

        is_dir = os.path.isdir(self.file_path)
        form.addRow("Type:", QLabel("Directory" if is_dir else "File"))

        if not is_dir:
            ext = os.path.splitext(name)[1]
            form.addRow("Extension:", QLabel(ext if ext else "None"))

        try:
            stat = os.stat(self.file_path)
            
            if is_dir:
                total_size, file_count, dir_count = self._dir_size(self.file_path)
                form.addRow("Total Size:", QLabel(self._format_size(total_size)))
                form.addRow("Contains:", QLabel(f"{file_count} files, {dir_count} folders"))
            else:
                form.addRow("Size:", QLabel(f"{self._format_size(stat.st_size)} ({stat.st_size:,} bytes)"))

            form.addRow("Created:", QLabel(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stat.st_ctime))))
            form.addRow("Modified:", QLabel(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stat.st_mtime))))
            form.addRow("Accessed:", QLabel(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stat.st_atime))))
            
            # Attributes
            attrs = []
            if os.access(self.file_path, os.R_OK): attrs.append("Read")
            if os.access(self.file_path, os.W_OK): attrs.append("Write")
            if os.access(self.file_path, os.X_OK): attrs.append("Execute")
            form.addRow("Permissions:", QLabel(", ".join(attrs)))

        except OSError as e:
            form.addRow("Error:", QLabel(str(e)))

        layout.addLayout(form)

        # Close button
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

    @staticmethod
    def _dir_size(path):
        total = 0
        files = 0
        dirs = 0
        try:
            for dirpath, dirnames, filenames in os.walk(path):
                dirs += len(dirnames)
                for f in filenames:
                    files += 1
                    fp = os.path.join(dirpath, f)
                    try:
                        total += os.path.getsize(fp)
                    except OSError:
                        pass
        except OSError:
            pass
        return total, files, dirs

    @staticmethod
    def _format_size(size):
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.0f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"
