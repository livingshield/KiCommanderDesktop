import os
from PySide6.QtWidgets import QWidget, QVBoxLayout, QTreeView, QFileSystemModel
from PySide6.QtCore import Qt, QDir, Signal
from event_bus import bus

class DirectoryTreeWidget(QWidget):
    """
    A global directory tree panel.
    When a directory is clicked, it navigates the active panel to that directory.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(4, 4, 4, 4)
        
        self.tree = QTreeView()
        self.tree.setStyleSheet("""
            QTreeView {
                background-color: #181825;
                color: #cdd6f4;
                border: 1px solid #313244;
                border-radius: 4px;
            }
            QTreeView::item:selected {
                background-color: #45475a;
                color: #89b4fa;
            }
        """)
        
        self.model = QFileSystemModel()
        self.model.setFilter(QDir.NoDotAndDotDot | QDir.AllDirs)
        
        # Only local FS is supported natively by QFileSystemModel
        self.model.setRootPath("") 
        
        self.tree.setModel(self.model)
        
        # Hide standard columns to only show name
        for i in range(1, self.model.columnCount()):
            self.tree.hideColumn(i)
            
        self.tree.setHeaderHidden(True)
        self.tree.clicked.connect(self.on_clicked)
        
        self.layout.addWidget(self.tree)
        
        bus.directory_selected.connect(self.sync_tree)

    def on_clicked(self, index):
        path = self.model.filePath(index)
        if os.path.exists(path):
            bus.action_requested.emit(f"navigate|{path}")

    def sync_tree(self, path):
        """Expand and scroll to the currently navigated path if it's local."""
        if path and os.path.exists(path):
            idx = self.model.index(path)
            if idx.isValid():
                self.tree.scrollTo(idx)
                self.tree.setCurrentIndex(idx)
