from PySide6.QtWidgets import QDialog, QFormLayout, QLineEdit, QSpinBox, QDialogButtonBox, QVBoxLayout, QLabel
from PySide6.QtCore import Qt

class SFTPConnectDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Connect to SFTP/SSH")
        self.setMinimumWidth(320)
        
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.host_edit = QLineEdit()
        self.host_edit.setPlaceholderText("e.g. example.com")
        self.user_edit = QLineEdit()
        self.pass_edit = QLineEdit()
        self.pass_edit.setEchoMode(QLineEdit.Password)
        self.port_spin = QSpinBox()
        self.port_spin.setRange(1, 65535)
        self.port_spin.setValue(22)

        form.addRow("Host:", self.host_edit)
        form.addRow("Port:", self.port_spin)
        form.addRow("Username:", self.user_edit)
        form.addRow("Password:", self.pass_edit)
        
        layout.addLayout(form)

        self.btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.btns.accepted.connect(self.accept)
        self.btns.rejected.connect(self.reject)
        layout.addWidget(self.btns)

    def get_data(self):
        return {
            "host": self.host_edit.text().strip(),
            "port": self.port_spin.value(),
            "user": self.user_edit.text().strip(),
            "pass": self.pass_edit.text()
        }

class SMBConnectDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Connect to SMB / Windows Share")
        self.setMinimumWidth(360)
        
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.host_edit = QLineEdit()
        self.host_edit.setPlaceholderText("e.g. 192.168.1.10 or server-name")
        self.share_edit = QLineEdit()
        self.share_edit.setPlaceholderText("e.g. public")
        self.user_edit = QLineEdit()
        self.pass_edit = QLineEdit()
        self.pass_edit.setEchoMode(QLineEdit.Password)
        self.domain_edit = QLineEdit()
        self.domain_edit.setPlaceholderText("Optional – leave blank for workgroup")
        self.port_spin = QSpinBox()
        self.port_spin.setRange(1, 65535)
        self.port_spin.setValue(445)

        form.addRow("Host:", self.host_edit)
        form.addRow("Share name:", self.share_edit)
        form.addRow("Port:", self.port_spin)
        form.addRow("Username:", self.user_edit)
        form.addRow("Password:", self.pass_edit)
        form.addRow("Domain:", self.domain_edit)
        
        layout.addLayout(form)

        self.btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.btns.accepted.connect(self.accept)
        self.btns.rejected.connect(self.reject)
        layout.addWidget(self.btns)

    def get_data(self):
        return {
            "host": self.host_edit.text().strip(),
            "share": self.share_edit.text().strip(),
            "port": self.port_spin.value(),
            "user": self.user_edit.text().strip(),
            "pass": self.pass_edit.text(),
            "domain": self.domain_edit.text().strip()
        }
