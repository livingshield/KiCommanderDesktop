from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QDialogButtonBox)
import qtawesome as qta

class CopyMoveDialog(QDialog):
    def __init__(self, op_type, source_names, target_path, parent=None):
        super().__init__(parent)
        self.op_type = op_type # 'copy' or 'move'
        self.target_path = target_path
        self.result_mode = "immediate" # "immediate" or "queue"
        
        self.setWindowTitle(f"{op_type.capitalize()} Files")
        self.setMinimumWidth(450)
        self.setup_ui(source_names)

    def setup_ui(self, source_names):
        layout = QVBoxLayout(self)
        
        # Info text
        count = len(source_names)
        if count == 1:
            msg = f"Do you want to {self.op_type} <b>{source_names[0]}</b> to:"
        else:
            msg = f"Do you want to {self.op_type} <b>{count} items</b> to:"
        
        label = QLabel(msg)
        label.setWordWrap(True)
        layout.addWidget(label)

        # Path input
        self.path_edit = QLineEdit(self.target_path)
        layout.addWidget(self.path_edit)
        
        layout.addSpacing(10)

        # Buttons
        btn_layout = QHBoxLayout()
        
        self.btn_ok = QPushButton(f"&{self.op_type.capitalize()}")
        self.btn_ok.setIcon(qta.icon(f"fa5s.{'copy' if self.op_type == 'copy' else 'external-link-alt'}", color="#a6e3a1"))
        self.btn_ok.clicked.connect(self.accept)
        btn_layout.addWidget(self.btn_ok)

        self.btn_queue = QPushButton("F2 &Queue")
        self.btn_queue.setIcon(qta.icon("fa5s.list-ol", color="#89b4fa"))
        self.btn_queue.clicked.connect(self.on_queue_clicked)
        btn_layout.addWidget(self.btn_queue)
        
        btn_layout.addStretch()

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)
        
        layout.addLayout(btn_layout)

    def on_queue_clicked(self):
        self.result_mode = "queue"
        self.target_path = self.path_edit.text()
        self.accept()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_F2:
            self.on_queue_clicked()
        else:
            super().keyPressEvent(event)

    def get_target_path(self):
        return self.path_edit.text()
