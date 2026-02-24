from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex
from PySide6.QtGui import QColor, QBrush, QFont
import qtawesome as qta
import os, time, math

class FileModel(QAbstractTableModel):
    def __init__(self, files=None):
        super().__init__()
        self._source_files = files or []
        self.files = list(self._source_files)
        self.headers = ["Name", "Ext", "Size", "Date"]
        
        self._sort_col = 0        # default: Name
        self._sort_asc = True     # default: ascending
        
        # Pre-cache icons
        self.icon_folder = qta.icon("fa5s.folder", color="#f9e2af")
        self.icon_file   = qta.icon("fa5s.file-alt", color="#bac2de")
        self.icon_up     = qta.icon("fa5s.arrow-up", color="#fab387")
        self.icon_zip    = qta.icon("fa5s.file-archive", color="#a6e3a1")
        self.icon_exe    = qta.icon("fa5s.terminal", color="#f38ba8")
        self.icon_img    = qta.icon("fa5s.file-image", color="#cba6f7")

    # ------------------------------------------------------------------ sorting
    def _sort_key(self, f):
        """Return sort key tuple for a FileInfo object based on current column."""
        if self._sort_col == 0:   # Name
            return f.name.lower()
        elif self._sort_col == 1: # Ext
            return f.ext.lower()
        elif self._sort_col == 2: # Size – numeric sort by raw bytes
            return f._size_bytes
        elif self._sort_col == 3: # Date – epoch timestamp
            return f._mtime
        return f.name.lower()

    def _apply_sort(self):
        """Sort self.files keeping '..' always first, dirs before files."""
        up    = [f for f in self.files if f.name == ".."]
        dirs  = [f for f in self.files if f.is_dir and f.name != ".."]
        files = [f for f in self.files if not f.is_dir]
        dirs.sort(key=self._sort_key, reverse=not self._sort_asc)
        files.sort(key=self._sort_key, reverse=not self._sort_asc)
        self.files = up + dirs + files

    def sort(self, column: int, order: Qt.SortOrder = Qt.AscendingOrder):
        """Called by QHeaderView when user clicks a column header."""
        self._sort_col = column
        self._sort_asc = (order == Qt.AscendingOrder)
        self.layoutAboutToBeChanged.emit()
        self._apply_sort()
        self.layoutChanged.emit()

    # ------------------------------------------------------------------ Qt API
    def rowCount(self, parent=QModelIndex()):
        if parent.isValid(): return 0
        return len(self.files)

    def columnCount(self, parent=QModelIndex()):
        return len(self.headers)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
            
        file = self.files[index.row()]
        col  = index.column()

        if role == Qt.DecorationRole and col == 0:
            if file.name == "..": return self.icon_up
            if file.is_dir: return self.icon_folder
            ext = file.ext.lower()
            if ext in ["zip", "7z", "rar", "tar", "gz"]: return self.icon_zip
            if ext in ["exe", "bat", "cmd", "sh", "py"]:  return self.icon_exe
            if ext in ["jpg", "jpeg", "png", "gif", "bmp", "svg"]: return self.icon_img
            return self.icon_file

        if role == Qt.ForegroundRole:
            if file.is_dir:    return QBrush(QColor("#f9e2af"))
            if file.name == "..": return QBrush(QColor("#fab387"))

        if role == Qt.TextAlignmentRole:
            if col in [1, 2]:
                return Qt.AlignRight | Qt.AlignVCenter
            return Qt.AlignLeft | Qt.AlignVCenter

        if role != Qt.DisplayRole:
            return None

        if col == 0: return file.name
        if col == 1: return file.ext
        if col == 2: return file.size
        if col == 3: return file.date
        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal:
            if role == Qt.DisplayRole:
                label = self.headers[section]
                if section == self._sort_col:
                    label += "  ▲" if self._sort_asc else "  ▼"
                return label
            if role == Qt.FontRole and section == self._sort_col:
                f = QFont()
                f.setBold(True)
                return f
        return None

    def update_files(self, files):
        self.beginResetModel()
        self.files = list(files)
        self._apply_sort()          # keep current sort after refresh
        self.endResetModel()

    def get_file(self, row):
        if 0 <= row < len(self.files):
            return self.files[row]
        return None
