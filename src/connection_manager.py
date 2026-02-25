"""
Connection Manager Dialog – save, load and manage FTP/SFTP/SMB connections.
Connections are stored in data/connections.json next to the executable.
"""
import os
import json
import sys
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QFormLayout, QLineEdit, QComboBox, QSpinBox,
    QDialogButtonBox, QMessageBox, QLabel, QGroupBox, QWidget
)
from PySide6.QtCore import Qt


# --------------------------------------------------------------------------- #
#  Helpers
# --------------------------------------------------------------------------- #

def _get_data_dir() -> str:
    if getattr(sys, 'frozen', False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(base, "data")
    os.makedirs(data_dir, exist_ok=True)
    return data_dir


def _connections_path() -> str:
    return os.path.join(_get_data_dir(), "connections.json")


def load_connections() -> list:
    path = _connections_path()
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []


def save_connections(connections: list):
    with open(_connections_path(), "w", encoding="utf-8") as f:
        json.dump(connections, f, indent=2, ensure_ascii=False)


# --------------------------------------------------------------------------- #
#  Edit Connection Dialog
# --------------------------------------------------------------------------- #

class EditConnectionDialog(QDialog):
    def __init__(self, parent=None, connection: dict | None = None):
        super().__init__(parent)
        self.setWindowTitle("Connection Details")
        self.setMinimumWidth(380)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("My Server")

        self.type_combo = QComboBox()
        self.type_combo.addItems(["FTP", "SFTP", "SMB"])
        self.type_combo.currentTextChanged.connect(self._on_type_changed)

        self.host_edit = QLineEdit()
        self.host_edit.setPlaceholderText("hostname or IP")

        self.port_spin = QSpinBox()
        self.port_spin.setRange(1, 65535)
        self.port_spin.setValue(21)

        self.share_edit = QLineEdit()
        self.share_edit.setPlaceholderText("Share name (SMB only)")

        self.user_edit = QLineEdit()
        self.pass_edit = QLineEdit()
        self.pass_edit.setEchoMode(QLineEdit.Password)

        self.domain_edit = QLineEdit()
        self.domain_edit.setPlaceholderText("Optional domain (SMB only)")

        form.addRow("Name:", self.name_edit)
        form.addRow("Protocol:", self.type_combo)
        form.addRow("Host:", self.host_edit)
        form.addRow("Port:", self.port_spin)
        form.addRow("Share:", self.share_edit)
        form.addRow("Username:", self.user_edit)
        form.addRow("Password:", self.pass_edit)
        form.addRow("Domain:", self.domain_edit)

        layout.addLayout(form)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self._validate_and_accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

        self._share_row = form
        if connection:
            self._populate(connection)
        else:
            self._on_type_changed("FTP")

    def _on_type_changed(self, ptype: str):
        defaults = {"FTP": 21, "SFTP": 22, "SMB": 445}
        self.port_spin.setValue(defaults.get(ptype, 21))
        smb = (ptype == "SMB")
        self.share_edit.setEnabled(smb)
        self.domain_edit.setEnabled(smb)

    def _populate(self, c: dict):
        self.name_edit.setText(c.get("name", ""))
        idx = self.type_combo.findText(c.get("type", "FTP"))
        self.type_combo.setCurrentIndex(max(0, idx))
        self.host_edit.setText(c.get("host", ""))
        self.port_spin.setValue(c.get("port", 21))
        self.share_edit.setText(c.get("share", ""))
        self.user_edit.setText(c.get("user", ""))
        self.pass_edit.setText(c.get("pass", ""))
        self.domain_edit.setText(c.get("domain", ""))
        self._on_type_changed(c.get("type", "FTP"))

    def _validate_and_accept(self):
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "Validation", "Name is required.")
            return
        if not self.host_edit.text().strip():
            QMessageBox.warning(self, "Validation", "Host is required.")
            return
        if self.type_combo.currentText() == "SMB" and not self.share_edit.text().strip():
            QMessageBox.warning(self, "Validation", "Share name is required for SMB.")
            return
        self.accept()

    def get_connection(self) -> dict:
        return {
            "name": self.name_edit.text().strip(),
            "type": self.type_combo.currentText(),
            "host": self.host_edit.text().strip(),
            "port": self.port_spin.value(),
            "share": self.share_edit.text().strip(),
            "user": self.user_edit.text().strip(),
            "pass": self.pass_edit.text(),
            "domain": self.domain_edit.text().strip(),
        }


# --------------------------------------------------------------------------- #
#  Connection Manager Dialog
# --------------------------------------------------------------------------- #

class ConnectionManagerDialog(QDialog):
    """Shows saved connections and lets the user connect, add, edit or delete."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Connection Manager")
        self.setMinimumSize(540, 360)
        self._connections = load_connections()
        self._selected_connection: dict | None = None

        layout = QVBoxLayout(self)

        # List + buttons side-by-side
        top = QHBoxLayout()

        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(self._connect_selected)
        top.addWidget(self.list_widget, 1)

        btn_col = QVBoxLayout()
        self.btn_connect = QPushButton("Connect")
        self.btn_connect.setDefault(True)
        self.btn_connect.clicked.connect(self._connect_selected)
        self.btn_add = QPushButton("Add…")
        self.btn_add.clicked.connect(self._add_connection)
        self.btn_edit = QPushButton("Edit…")
        self.btn_edit.clicked.connect(self._edit_connection)
        self.btn_delete = QPushButton("Delete")
        self.btn_delete.clicked.connect(self._delete_connection)
        btn_col.addWidget(self.btn_connect)
        btn_col.addWidget(self.btn_add)
        btn_col.addWidget(self.btn_edit)
        btn_col.addWidget(self.btn_delete)
        btn_col.addStretch()
        top.addLayout(btn_col)

        layout.addLayout(top)

        close_btns = QDialogButtonBox(QDialogButtonBox.Close)
        close_btns.rejected.connect(self.reject)
        layout.addWidget(close_btns)

        self._refresh_list()

    # ------------------------------------------------------------------ #

    def _refresh_list(self):
        self.list_widget.clear()
        for c in self._connections:
            label = f"[{c.get('type', '?')}]  {c.get('name', '?')}  →  {c.get('host', '')}"
            if c.get("type") == "SMB" and c.get("share"):
                label += f"\\{c['share']}"
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, c)
            self.list_widget.addItem(item)

    def _current_conn(self) -> dict | None:
        item = self.list_widget.currentItem()
        return item.data(Qt.UserRole) if item else None

    def _add_connection(self):
        dlg = EditConnectionDialog(self)
        if dlg.exec() == QDialog.Accepted:
            self._connections.append(dlg.get_connection())
            save_connections(self._connections)
            self._refresh_list()

    def _edit_connection(self):
        c = self._current_conn()
        if not c:
            return
        dlg = EditConnectionDialog(self, c)
        if dlg.exec() == QDialog.Accepted:
            idx = self._connections.index(c)
            self._connections[idx] = dlg.get_connection()
            save_connections(self._connections)
            self._refresh_list()

    def _delete_connection(self):
        c = self._current_conn()
        if not c:
            return
        reply = QMessageBox.question(self, "Delete", f"Delete connection \"{c.get('name')}\"?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self._connections.remove(c)
            save_connections(self._connections)
            self._refresh_list()

    def _connect_selected(self):
        c = self._current_conn()
        if not c:
            return
        self._selected_connection = c
        self.accept()

    def get_selected_connection(self) -> dict | None:
        return self._selected_connection
