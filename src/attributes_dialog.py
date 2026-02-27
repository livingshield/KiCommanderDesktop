import os
import sys
import stat
import time
from datetime import datetime
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QDialogButtonBox, QFormLayout, 
                             QDateTimeEdit, QCheckBox, QMessageBox, QGroupBox)
from PySide6.QtCore import Qt, QDateTime
import qtawesome as qta
from fs_worker import FileInfo
from logger import log

class AttributesDialog(QDialog):
    def __init__(self, files: list[FileInfo], is_vfs=False, parent=None):
        super().__init__(parent)
        self.files = files
        self.is_vfs = is_vfs
        self.setWindowTitle("Change Attributes and Timestamps")
        self.resize(350, 300)
        
        # New values stored if accepted
        self.new_mtime = None
        self.apply_hidden = None
        self.apply_readonly = None
        
        self.setup_ui()
        self._load_initial_data()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Multiple files warning or single file name
        if len(self.files) == 1:
            lbl = QLabel(f"<b>Soubor:</b> {self.files[0].name}")
        else:
            lbl = QLabel(f"<b>Vybrané soubory:</b> {len(self.files)}")
        layout.addWidget(lbl)
        
        # --- Timestamps ---
        ts_group = QGroupBox("Časová razítka")
        ts_layout = QFormLayout(ts_group)
        
        self.cb_change_time = QCheckBox("Změnit datum úpravy (MTime)")
        self.cb_change_time.toggled.connect(self._on_time_cb_toggled)
        ts_layout.addRow(self.cb_change_time)
        
        self.datetime_edit = QDateTimeEdit(QDateTime.currentDateTime())
        self.datetime_edit.setDisplayFormat("dd.MM.yyyy HH:mm:ss")
        self.datetime_edit.setEnabled(False)
        ts_layout.addRow("Nové datum:", self.datetime_edit)
        
        layout.addWidget(ts_group)
        
        # --- Attributes ---
        attr_group = QGroupBox("Atributy (pouze lokální FS)")
        attr_layout = QVBoxLayout(attr_group)
        
        if self.is_vfs:
            lbl_vfs = QLabel("Změna atributů je na VFS zakázána/nepodporována.")
            lbl_vfs.setStyleSheet("color: #f38ba8;")
            attr_layout.addWidget(lbl_vfs)
        else:
            # We track states: 0=No change, 1=Set, 2=Clear
            # Using simple checkboxes with partially checked states?
            # QCheckBox supports Tristate: PartiallyChecked (no change), Checked (set), Unchecked (clear).
            self.chk_readonly = QCheckBox("Read-only")
            self.chk_readonly.setTristate(True)
            self.chk_readonly.setCheckState(Qt.PartiallyChecked)
            
            self.chk_hidden = QCheckBox("Hidden")
            self.chk_hidden.setTristate(True)
            self.chk_hidden.setCheckState(Qt.PartiallyChecked)
            
            attr_layout.addWidget(self.chk_readonly)
            attr_layout.addWidget(self.chk_hidden)
            
        layout.addWidget(attr_group)
        
        # Buttons
        self.bbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.bbox.accepted.connect(self.validate_and_accept)
        self.bbox.rejected.connect(self.reject)
        layout.addWidget(self.bbox)

    def _load_initial_data(self):
        if len(self.files) == 1:
            # Pre-fill with single file's timestamp
            dt = QDateTime.fromSecsSinceEpoch(int(self.files[0].mtime))
            self.datetime_edit.setDateTime(dt)

            if not self.is_vfs:
                # Pre-fill attributes
                try:
                    mode = os.stat(self.files[0].full_path).st_mode
                    is_ro = not bool(mode & stat.S_IWRITE)
                    self.chk_readonly.setCheckState(Qt.Checked if is_ro else Qt.Unchecked)
                    
                    if sys.platform == "win32":
                        import ctypes
                        attrs = ctypes.windll.kernel32.GetFileAttributesW(self.files[0].full_path)
                        if attrs != -1:
                            is_hidden = bool(attrs & 2) # FILE_ATTRIBUTE_HIDDEN
                            self.chk_hidden.setCheckState(Qt.Checked if is_hidden else Qt.Unchecked)
                except Exception as e:
                    log.warning(f"Could not read attrs for {self.files[0].name}: {e}")
        else:
            pass

    def _on_time_cb_toggled(self, checked):
        self.datetime_edit.setEnabled(checked)

    def validate_and_accept(self):
        if self.cb_change_time.isChecked():
            self.new_mtime = self.datetime_edit.dateTime().toSecsSinceEpoch()
            
        if not self.is_vfs:
            state_ro = self.chk_readonly.checkState()
            if state_ro == Qt.Checked:
                self.apply_readonly = True
            elif state_ro == Qt.Unchecked:
                self.apply_readonly = False
                
            state_hd = self.chk_hidden.checkState()
            if state_hd == Qt.Checked:
                self.apply_hidden = True
            elif state_hd == Qt.Unchecked:
                self.apply_hidden = False
                
        self.accept()
