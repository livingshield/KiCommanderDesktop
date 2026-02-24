from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex

class FileModel(QAbstractTableModel):
    def __init__(self, files=None):
        super().__init__()
        self.files = files or []
        self.headers = ["Name", "Ext", "Size", "Date"]

    def rowCount(self, parent=QModelIndex()):
        if parent.isValid():
            return 0
        return len(self.files)

    def columnCount(self, parent=QModelIndex()):
        return len(self.headers)

    def data(self, index, role=Qt.DisplayRole):
        if role == Qt.TextAlignmentRole:
            col = index.column()
            if col in [1, 2]: # Ext and Size aligned right
                return Qt.AlignRight | Qt.AlignVCenter
            return Qt.AlignLeft | Qt.AlignVCenter

        if role != Qt.DisplayRole:
            return None

        file = self.files[index.row()]
        col = index.column()

        if col == 0: return file.name
        if col == 1: return file.ext
        if col == 2: return file.size
        if col == 3: return file.date
        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.headers[section]
        return None

    def update_files(self, files):
        self.beginResetModel()
        self.files = files
        self.endResetModel()

    def get_file(self, row):
        if 0 <= row < len(self.files):
            return self.files[row]
        return None
