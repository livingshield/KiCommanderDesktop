import os
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, 
                             QLineEdit, QPushButton, QFileDialog, QDialogButtonBox,
                             QCheckBox, QLabel, QTabWidget, QWidget)
from PySide6.QtCore import Qt, QSettings
import qtawesome as qta

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent, Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMinimumWidth(500)
        self.settings = QSettings("KiCommander", "Desktop")
        self._drag_pos = None

        self.setup_ui()

    def setup_ui(self):
        self.outer_layout = QVBoxLayout(self)
        self.outer_layout.setContentsMargins(10, 10, 10, 10)
        
        self.container = QWidget()
        self.container.setObjectName("DialogContainer")
        self.outer_layout.addWidget(self.container)
        
        self.main_layout = QVBoxLayout(self.container)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # Title Bar
        self.title_bar = QWidget()
        self.title_bar.setObjectName("DialogTitleBar")
        self.title_bar.setFixedHeight(40)
        tb_layout = QHBoxLayout(self.title_bar)
        tb_layout.setContentsMargins(15, 0, 10, 0)
        
        title_icon = QLabel()
        title_icon.setPixmap(qta.icon("fa5s.cog", color="#89b4fa").pixmap(20, 20))
        tb_layout.addWidget(title_icon)
        
        title_label = QLabel("Nastavení KiCommander")
        title_label.setStyleSheet("font-weight: bold; color: #cdd6f4;")
        tb_layout.addWidget(title_label)
        tb_layout.addStretch()
        
        close_btn = QPushButton()
        close_btn.setIcon(qta.icon("fa5s.times", color="#cdd6f4"))
        close_btn.setFixedSize(30, 30); close_btn.setObjectName("TitleCloseBtn"); close_btn.clicked.connect(self.reject)
        tb_layout.addWidget(close_btn)
        self.main_layout.addWidget(self.title_bar)

        content = QWidget()
        content.setObjectName("DialogContent")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(15, 10, 15, 15)

        self.tabs = QTabWidget()
        
        # --- General Tab ---
        general_tab = QWidget()
        gen_layout = QFormLayout(general_tab)
        
        self.editor_edit = QLineEdit()
        self.editor_edit.setText(self.settings.value("editor/path", ""))
        self.editor_edit.setPlaceholderText("Default system editor")
        
        editor_btn = QPushButton("Procházet...")
        editor_btn.clicked.connect(self._browse_editor)
        
        editor_row = QHBoxLayout()
        editor_row.addWidget(self.editor_edit)
        editor_row.addWidget(editor_btn)
        
        gen_layout.addRow("Externí editor:", editor_row)
        
        self.confirm_delete = QCheckBox("Potvrdit před smazáním")
        self.confirm_delete.setChecked(self.settings.value("behavior/confirm_delete", "true") == "true")
        gen_layout.addRow(self.confirm_delete)
        
        self.tabs.addTab(general_tab, "Obecné")
        
        # --- Appearance Tab ---
        app_tab = QWidget()
        app_layout = QFormLayout(app_tab)
        app_layout.addRow(QLabel("Téma: Catppuccin Mocha (Výchozí)"))
        self.tabs.addTab(app_tab, "Vzhled")

        layout.addWidget(self.tabs)
        
        btns = QHBoxLayout()
        self.save_btn = QPushButton("Uložit")
        self.save_btn.setObjectName("SaveBtn")
        self.save_btn.clicked.connect(self._save_and_accept)
        self.cancel_btn = QPushButton("Zrušit")
        self.cancel_btn.clicked.connect(self.reject)
        
        btns.addStretch()
        btns.addWidget(self.cancel_btn)
        btns.addWidget(self.save_btn)
        layout.addLayout(btns)
        
        self.main_layout.addWidget(content)

        self.setStyleSheet("""
            #DialogContainer { background-color: #1e1e2e; border: 1px solid #313244; border-radius: 10px; }
            #DialogTitleBar { background-color: #11111b; border-top-left-radius: 10px; border-top-right-radius: 10px; border-bottom: 1px solid #313244; }
            #DialogContent { background-color: #1e1e2e; border-bottom-left-radius: 10px; border-bottom-right-radius: 10px; }
            #TitleCloseBtn { background: transparent; border: none; border-radius: 15px; }
            #TitleCloseBtn:hover { background-color: #f38ba8; }
            QTabWidget::pane { border: 1px solid #313244; background: #181825; border-radius: 4px; }
            QTabBar::tab { background: #11111b; color: #a6adc8; padding: 8px 15px; border: 1px solid #313244; border-bottom: none; border-top-left-radius: 4px; border-top-right-radius: 4px; }
            QTabBar::tab:selected { background: #1e1e2e; color: #89b4fa; border-bottom: 2px solid #89b4fa; }
            QLineEdit { background: #11111b; border: 1px solid #313244; padding: 5px; color: #cdd6f4; border-radius: 4px; }
            QPushButton { background-color: #313244; color: #cdd6f4; border: 1px solid #45475a; border-radius: 5px; padding: 6px 15px; }
            QPushButton#SaveBtn { background-color: #89b4fa; color: #11111b; font-weight: bold; }
        """)

    def _browse_editor(self):
        file, _ = QFileDialog.getOpenFileName(self, "Vybrat editor", "", "Spustitelné soubory (*.exe *.com *.bat *.sh);;Všechny soubory (*)")
        if file:
            self.editor_edit.setText(file)

    def _save_and_accept(self):
        self.settings.setValue("editor/path", self.editor_edit.text().strip())
        self.settings.setValue("behavior/confirm_delete", "true" if self.confirm_delete.isChecked() else "false")
        self.accept()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.title_bar.underMouse():
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
    def mouseMoveEvent(self, event):
        if self._drag_pos and event.buttons() & Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
    def mouseReleaseEvent(self, event): self._drag_pos = None
