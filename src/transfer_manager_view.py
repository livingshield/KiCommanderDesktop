from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QTableWidget, QTableWidgetItem, QPushButton, 
                             QProgressBar, QHeaderView)
import qtawesome as qta
from queue_manager import QueueManager

class TransferManagerWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.manager = QueueManager.instance()
        self.setup_ui()
        self.manager.queue_updated.connect(self.refresh_queue)
        self.refresh_queue()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        # Header
        header = QHBoxLayout()
        title = QLabel("Transfer Manager")
        title.setStyleSheet("font-weight: bold; font-size: 14px; color: #89b4fa;")
        header.addWidget(title)
        header.addStretch()
        
        self.pause_btn = QPushButton()
        self.pause_btn.setIcon(qta.icon("fa5s.pause", color="#f9e2af"))
        self.pause_btn.setToolTip("Pause Queue")
        self.pause_btn.setFixedWidth(30)
        self.pause_btn.clicked.connect(self.toggle_pause)
        header.addWidget(self.pause_btn)
        
        clear_btn = QPushButton()
        clear_btn.setIcon(qta.icon("fa5s.trash-alt", color="#f38ba8"))
        clear_btn.setToolTip("Clear Finished")
        clear_btn.setFixedWidth(30)
        clear_btn.clicked.connect(self.clear_completed)
        header.addWidget(clear_btn)
        
        layout.addLayout(header)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Operation", "Target", "Status", "Progress"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setColumnWidth(0, 100)
        self.table.setColumnWidth(1, 150)
        self.table.setColumnWidth(2, 80)
        
        self.table.setStyleSheet("""
            QTableWidget { background-color: #1e1e2e; color: #cdd6f4; border: 1px solid #45475a; gridline-color: #313244; }
            QHeaderView::section { background-color: #313244; color: #cdd6f4; padding: 4px; border: 1px solid #45475a; }
            QTableWidget::item { padding: 4px; }
        """)
        layout.addWidget(self.table)

    def toggle_pause(self):
        self.manager.pause_queue(not self.manager.paused)
        icon = "fa5s.play" if self.manager.paused else "fa5s.pause"
        color = "#a6e3a1" if self.manager.paused else "#f9e2af"
        self.pause_btn.setIcon(qta.icon(icon, color=color))

    def clear_completed(self):
        # Filter out completed/error items
        finished_ids = [i.id for i in self.manager.items if i.status in ("Completed", "Error")]
        for fid in finished_ids:
            self.manager.remove_item(fid)
        self.refresh_queue()

    def refresh_queue(self):
        self.table.setRowCount(len(self.manager.items))
        for i, item in enumerate(self.manager.items):
            self.table.setItem(i, 0, QTableWidgetItem(f"{item.op_type.capitalize()}"))
            self.table.setItem(i, 1, QTableWidgetItem(item.target_path))
            
            status_item = QTableWidgetItem(item.status)
            if item.status == "Error":
                status_item.setForeground(Qt.red)
                status_item.setToolTip(item.error_msg)
            elif item.status == "Completed":
                status_item.setForeground(Qt.green)
            self.table.setItem(i, 2, status_item)
            
            # Progress bar for the last column
            progress_widget = QWidget()
            prog_layout = QVBoxLayout(progress_widget)
            prog_layout.setContentsMargins(4, 2, 4, 2)
            bar = QProgressBar()
            bar.setRange(0, 100)
            bar.setValue(item.progress)
            bar.setTextVisible(True)
            current = item.current_file if item.current_file else ""
            if len(current) > 20: current = "..." + current[-17:]
            bar.setFormat(f"%p% {current}")
            bar.setStyleSheet("""
                QProgressBar { border: 1px solid #45475a; border-radius: 4px; text-align: center; color: #cdd6f4; font-size: 10px; }
                QProgressBar::chunk { background-color: #89b4fa; }
            """)
            prog_layout.addWidget(bar)
            self.table.setCellWidget(i, 3, progress_widget)
