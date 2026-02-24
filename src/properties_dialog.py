import os
import time
import stat as stat_module
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QFormLayout, QPushButton, QWidget)
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
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMinimumWidth(450)
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
        icon_lbl.setPixmap(qta.icon("fa5s.info-circle", color="#89b4fa").pixmap(16, 16))
        tb_layout.addWidget(icon_lbl)
        title_lbl = QLabel(f"Properties – {os.path.basename(self.file_path)}")
        title_lbl.setStyleSheet("color: #cdd6f4; font-weight: bold; font-size: 10pt;")
        tb_layout.addWidget(title_lbl)
        tb_layout.addStretch()
        close_btn = QPushButton()
        close_btn.setIcon(qta.icon("fa5s.times", color="#cdd6f4"))
        close_btn.setFixedSize(28, 28)
        close_btn.setObjectName("TitleCloseBtn")
        close_btn.clicked.connect(self.accept)
        tb_layout.addWidget(close_btn)
        main_layout.addWidget(title_bar)

        # Content area
        content = QWidget()
        content.setObjectName("DialogContent")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(16, 12, 16, 16)
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
            QLabel#ValueLabel { color: #bac2de; }
            QLabel#HeaderLabel { color: #89b4fa; font-weight: bold; font-size: 11pt; }
            QPushButton {
                background-color: #313244; border: 1px solid #45475a;
                border-radius: 4px; padding: 8px 18px; color: #cdd6f4;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #45475a; border-color: #89b4fa; }
        """)

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
                self.size_label = self._val("Calculating...")
                self.contains_label = self._val("Calculating...")
                form.addRow("Total Size:", self.size_label)
                form.addRow("Contains:", self.contains_label)
                self._start_dir_size()
            else:
                size_str = f"{self._format_size(st.st_size)}  ({st.st_size:,} bytes)"
                form.addRow("Size:", self._val(size_str))

            form.addRow("Created:", self._val(
                time.strftime("%d.%m.%Y  %H:%M:%S", time.localtime(st.st_ctime))))
            form.addRow("Modified:", self._val(
                time.strftime("%d.%m.%Y  %H:%M:%S", time.localtime(st.st_mtime))))
            form.addRow("Accessed:", self._val(
                time.strftime("%d.%m.%Y  %H:%M:%S", time.localtime(st.st_atime))))

            attrs = []
            if os.access(self.file_path, os.R_OK): attrs.append("Read")
            if os.access(self.file_path, os.W_OK): attrs.append("Write")
            if os.access(self.file_path, os.X_OK): attrs.append("Execute")
            form.addRow("Permissions:", self._val(", ".join(attrs) if attrs else "None"))

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
        close_btn2 = QPushButton("  Close")
        close_btn2.setIcon(qta.icon("fa5s.times", color="#cdd6f4"))
        close_btn2.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn2)
        layout.addLayout(btn_layout)

    def _val(self, text):
        label = QLabel(str(text))
        label.setObjectName("ValueLabel")
        label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        return label

    def _start_dir_size(self):
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
