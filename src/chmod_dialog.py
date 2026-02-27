import stat
import os
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QWidget, QCheckBox, QGridLayout, QMessageBox)
from PySide6.QtCore import Qt

class ChmodDialog(QDialog):
    def __init__(self, file_info, is_vfs=False, parent=None):
        super().__init__(parent)
        self.file_info = file_info
        self.is_vfs = is_vfs
        self.new_mode = 0
        self.setWindowTitle(f"Change Permissions - {file_info.name}")
        self.setup_ui()
        self.load_permissions()

    def setup_ui(self):
        self.setMinimumWidth(300)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setStyleSheet("""
            QDialog { background-color: #1e1e2e; }
            QLabel { color: #cdd6f4; font-size: 10pt; }
            QCheckBox { color: #cdd6f4; font-size: 10pt; }
            QPushButton {
                background-color: #313244; border: 1px solid #45475a;
                border-radius: 4px; padding: 6px 16px; color: #cdd6f4;
            }
            QPushButton:hover { background-color: #45475a; border-color: #89b4fa; }
        """)

        layout = QVBoxLayout(self)
        
        info_layout = QHBoxLayout()
        info_layout.addWidget(QLabel("Owner:"))
        self.lbl_owner = QLabel(self.file_info.owner if hasattr(self.file_info, 'owner') and self.file_info.owner else "N/A")
        self.lbl_owner.setStyleSheet("color: #89b4fa; font-weight: bold;")
        info_layout.addWidget(self.lbl_owner)
        
        info_layout.addSpacing(10)
        
        info_layout.addWidget(QLabel("Group:"))
        self.lbl_group = QLabel(self.file_info.group if hasattr(self.file_info, 'group') and self.file_info.group else "N/A")
        self.lbl_group.setStyleSheet("color: #a6e3a1; font-weight: bold;")
        info_layout.addWidget(self.lbl_group)
        info_layout.addStretch()
        layout.addLayout(info_layout)

        grid = QGridLayout()
        grid.setSpacing(10)

        # Headers
        grid.addWidget(QLabel("<b>Read</b>"), 0, 1, Qt.AlignCenter)
        grid.addWidget(QLabel("<b>Write</b>"), 0, 2, Qt.AlignCenter)
        grid.addWidget(QLabel("<b>Execute</b>"), 0, 3, Qt.AlignCenter)

        # Owner
        grid.addWidget(QLabel("Owner"), 1, 0)
        self.cb_ur = QCheckBox()
        self.cb_uw = QCheckBox()
        self.cb_ux = QCheckBox()
        grid.addWidget(self.cb_ur, 1, 1, Qt.AlignCenter)
        grid.addWidget(self.cb_uw, 1, 2, Qt.AlignCenter)
        grid.addWidget(self.cb_ux, 1, 3, Qt.AlignCenter)

        # Group
        grid.addWidget(QLabel("Group"), 2, 0)
        self.cb_gr = QCheckBox()
        self.cb_gw = QCheckBox()
        self.cb_gx = QCheckBox()
        grid.addWidget(self.cb_gr, 2, 1, Qt.AlignCenter)
        grid.addWidget(self.cb_gw, 2, 2, Qt.AlignCenter)
        grid.addWidget(self.cb_gx, 2, 3, Qt.AlignCenter)

        # Other
        grid.addWidget(QLabel("Other"), 3, 0)
        self.cb_or = QCheckBox()
        self.cb_ow = QCheckBox()
        self.cb_ox = QCheckBox()
        grid.addWidget(self.cb_or, 3, 1, Qt.AlignCenter)
        grid.addWidget(self.cb_ow, 3, 2, Qt.AlignCenter)
        grid.addWidget(self.cb_ox, 3, 3, Qt.AlignCenter)

        self.cbs = {
            stat.S_IRUSR: self.cb_ur, stat.S_IWUSR: self.cb_uw, stat.S_IXUSR: self.cb_ux,
            stat.S_IRGRP: self.cb_gr, stat.S_IWGRP: self.cb_gw, stat.S_IXGRP: self.cb_gx,
            stat.S_IROTH: self.cb_or, stat.S_IWOTH: self.cb_ow, stat.S_IXOTH: self.cb_ox
        }
        
        # Connect changes
        for cb in self.cbs.values():
            cb.stateChanged.connect(self.update_octal)

        layout.addLayout(grid)

        # Octal display
        octal_layout = QHBoxLayout()
        octal_layout.addWidget(QLabel("Octal Mode:"))
        self.lbl_octal = QLabel("000")
        self.lbl_octal.setStyleSheet("color: #fab387; font-weight: bold; font-family: monospace;")
        octal_layout.addWidget(self.lbl_octal)
        octal_layout.addStretch()
        layout.addLayout(octal_layout)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_ok = QPushButton("Apply")
        btn_ok.clicked.connect(self.accept)
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_ok)
        btn_layout.addWidget(btn_cancel)
        
        layout.addLayout(btn_layout)

    def load_permissions(self):
        try:
            mode = 0
            if self.is_vfs:
                # We need to rely on the permissions string if we don't have direct access
                # Or wait, SFTP/OS does give us the raw attributes if we fetch it, but lets use OS stat if local
                pass
                
            if not self.is_vfs and os.path.exists(self.file_info.full_path):
                st = os.stat(self.file_info.full_path)
                mode = st.st_mode
            else:
                # Approximate from string '-rwxr-xr-x'
                perm_str = getattr(self.file_info, 'permissions', "")
                if perm_str and len(perm_str) >= 10:
                    mode = self.parse_sym_mode(perm_str)

            for flag, cb in self.cbs.items():
                cb.setChecked(bool(mode & flag))
                
            self.update_octal()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not load permissions: {e}")

    def parse_sym_mode(self, perm_str):
        # perm_str: drwxr-xr-x
        mode = 0
        if len(perm_str) < 10: return mode
        if perm_str[1] == 'r': mode |= stat.S_IRUSR
        if perm_str[2] == 'w': mode |= stat.S_IWUSR
        if perm_str[3] == 'x' or perm_str[3] == 's': mode |= stat.S_IXUSR
        if perm_str[4] == 'r': mode |= stat.S_IRGRP
        if perm_str[5] == 'w': mode |= stat.S_IWGRP
        if perm_str[6] == 'x' or perm_str[6] == 's': mode |= stat.S_IXGRP
        if perm_str[7] == 'r': mode |= stat.S_IROTH
        if perm_str[8] == 'w': mode |= stat.S_IWOTH
        if perm_str[9] == 'x' or perm_str[9] == 't': mode |= stat.S_IXOTH
        return mode

    def update_octal(self):
        mode = 0
        for flag, cb in self.cbs.items():
            if cb.isChecked():
                mode |= flag
        self.new_mode = mode
        self.lbl_octal.setText(oct(mode)[-3:].zfill(3))
