import os
import time
import stat as stat_module
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QFormLayout, QPushButton)
from PySide6.QtCore import Qt, QThread, Signal, QObject
import qtawesome as qta


class DirSizeWorker(QObject):
    """Calculates directory size in background thread."""
    finished = Signal(int, int, int)  # total_bytes, file_count, dir_count

    def __init__(self, path):
        super().__init__()
        self.path = path

    def run(self):
        total = 0
        files = 0
        dirs = 0
        try:
            for dirpath, dirnames, filenames in os.walk(self.path):
                dirs += len(dirnames)
                for f in filenames:
                    files += 1
                    try:
                        total += os.path.getsize(os.path.join(dirpath, f))
                    except OSError:
                        pass
        except OSError:
            pass
        self.finished.emit(total, files, dirs)


class PropertiesDialog(QDialog):
    def __init__(self, file_path, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.setWindowTitle(f"Properties - {os.path.basename(file_path)}")
        self.setMinimumWidth(450)
        self.setup_ui()
        self.setWindowIcon(qta.icon("fa5s.info-circle", color="#89b4fa"))

    def setup_ui(self):
        self.setStyleSheet("""
            QDialog { background-color: #1e1e2e; }
            QLabel { color: #cdd6f4; font-size: 10pt; }
            QLabel#ValueLabel { color: #bac2de; }
            QLabel#HeaderLabel { color: #89b4fa; font-weight: bold; font-size: 11pt; }
            QPushButton {
                background-color: #313244; border: 1px solid #45475a;
                border-radius: 4px; padding: 8px 18px; color: #cdd6f4;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #45475a; border-color: #89b4fa; }
        """)
        layout = QVBoxLayout(self)

        # Header with icon
        header = QHBoxLayout()
        is_dir = os.path.isdir(self.file_path)
        icon_name = "fa5s.folder" if is_dir else "fa5s.file-alt"
        icon_color = "#f9e2af" if is_dir else "#89b4fa"
        icon_label = QLabel()
        icon_label.setPixmap(qta.icon(icon_name, color=icon_color).pixmap(32, 32))
        header.addWidget(icon_label)
        name_label = QLabel(os.path.basename(self.file_path))
        name_label.setObjectName("HeaderLabel")
        header.addWidget(name_label)
        header.addStretch()
        layout.addLayout(header)

        # Separator
        sep = QLabel()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background-color: #313244;")
        layout.addWidget(sep)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)
        form.setHorizontalSpacing(16)
        form.setVerticalSpacing(8)

        # Path
        path_label = QLabel(self.file_path)
        path_label.setWordWrap(True)
        path_label.setObjectName("ValueLabel")
        form.addRow("Location:", path_label)

        # Type
        form.addRow("Type:", self._val("Directory" if is_dir else "File"))

        if not is_dir:
            ext = os.path.splitext(self.file_path)[1]
            form.addRow("Extension:", self._val(ext if ext else "None"))

        try:
            st = os.stat(self.file_path)

            if is_dir:
                # Show placeholder, start background calculation
                self.size_label = self._val("Calculating...")
                self.contains_label = self._val("Calculating...")
                form.addRow("Total Size:", self.size_label)
                form.addRow("Contains:", self.contains_label)
                self._start_dir_size()
            else:
                size_str = f"{self._format_size(st.st_size)}  ({st.st_size:,} bytes)"
                form.addRow("Size:", self._val(size_str))

            # Timestamps
            form.addRow("Created:", self._val(
                time.strftime("%d.%m.%Y  %H:%M:%S", time.localtime(st.st_ctime))))
            form.addRow("Modified:", self._val(
                time.strftime("%d.%m.%Y  %H:%M:%S", time.localtime(st.st_mtime))))
            form.addRow("Accessed:", self._val(
                time.strftime("%d.%m.%Y  %H:%M:%S", time.localtime(st.st_atime))))

            # Permissions
            attrs = []
            if os.access(self.file_path, os.R_OK): attrs.append("Read")
            if os.access(self.file_path, os.W_OK): attrs.append("Write")
            if os.access(self.file_path, os.X_OK): attrs.append("Execute")
            form.addRow("Permissions:", self._val(", ".join(attrs) if attrs else "None"))

            # Windows-specific attributes
            if hasattr(st, 'st_file_attributes'):
                win_attrs = []
                fa = st.st_file_attributes
                if fa & stat_module.FILE_ATTRIBUTE_READONLY:
                    win_attrs.append("Read-Only")
                if fa & stat_module.FILE_ATTRIBUTE_HIDDEN:
                    win_attrs.append("Hidden")
                if fa & stat_module.FILE_ATTRIBUTE_SYSTEM:
                    win_attrs.append("System")
                if fa & stat_module.FILE_ATTRIBUTE_ARCHIVE:
                    win_attrs.append("Archive")
                if win_attrs:
                    form.addRow("Attributes:", self._val(", ".join(win_attrs)))

        except OSError as e:
            form.addRow("Error:", self._val(str(e)))

        layout.addLayout(form)

        # Close button
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        close_btn = QPushButton("  Close")
        close_btn.setIcon(qta.icon("fa5s.times", color="#cdd6f4"))
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

    def _val(self, text):
        """Create a styled value label."""
        label = QLabel(str(text))
        label.setObjectName("ValueLabel")
        label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        return label

    def _start_dir_size(self):
        """Start background directory size calculation."""
        self._thread = QThread(self)
        self._worker = DirSizeWorker(self.file_path)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_dir_size_done)
        self._worker.finished.connect(self._thread.quit)
        self._thread.start()

    def _on_dir_size_done(self, total, files, dirs):
        self.size_label.setText(f"{self._format_size(total)}  ({total:,} bytes)")
        self.contains_label.setText(f"{files:,} files, {dirs:,} folders")

    @staticmethod
    def _format_size(size):
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.0f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"
