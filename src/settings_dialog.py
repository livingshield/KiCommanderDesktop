import os
import sys
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, 
                             QLineEdit, QPushButton, QFileDialog, QDialogButtonBox,
                             QCheckBox, QLabel, QTabWidget, QWidget, QSizeGrip,
                             QComboBox)
from PySide6.QtCore import Qt, QSettings, QSize
from PySide6.QtGui import QPixmap, QIcon
from event_bus import bus
import qtawesome as qta

def get_assets_dir():
    """Return the assets directory regardless of whether we're running as a
    plain Python script or a PyInstaller bundle."""
    if getattr(sys, '_MEIPASS', None):
        return os.path.join(sys._MEIPASS, 'assets')
    else:
        src_dir = os.path.dirname(os.path.abspath(__file__))
        # settings_dialog.py is in src/, so assets is in src/../assets
        return os.path.abspath(os.path.join(src_dir, '..', 'assets'))

ASSETS_DIR = get_assets_dir()

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent, Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        self.setMouseTracking(True)
        self.settings = QSettings("KiCommander", "Desktop")
        self.original_icon = self.settings.value("appearance/app_icon", "icon.png")
        self.original_theme = self.settings.value("appearance/theme", "Mocha")
        self._drag_pos = None
        self._resize_margin = 8
        self._resizing = False
        self._resize_edge = None

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
        
        self.theme_combo = QComboBox()
        themes = ["Mocha", "Macchiato", "Frappé", "Latte"]
        self.theme_combo.addItems(themes)
        
        current_theme = self.settings.value("appearance/theme", "Mocha")
        idx = self.theme_combo.findText(current_theme)
        if idx >= 0:
            self.theme_combo.setCurrentIndex(idx)
            
        self.theme_combo.currentTextChanged.connect(lambda t: bus.app_theme_changed.emit(t))
        app_layout.addRow("Téma:", self.theme_combo)
        
        self.icon_combo = QComboBox()
        self.icon_combo.setIconSize(QSize(32, 32))
        
        icons = [
            ("Výchozí", "icon.png"),
            ("Ikona 1 (Minimalistický 'K')", "icon1.png"),
            ("Ikona 2 (3D Skleněné panely)", "icon2.png"),
            ("Ikona 3 (Neon Flat)", "icon3.png"),
            ("Ikona 4 (Futuristická)", "icon4.png"),
            ("Ikona 5 (3D macOS styl)", "icon5.png")
        ]
        
        for name, filename in icons:
            # Check both root and icons/ subfolder
            icon_path = os.path.join(ASSETS_DIR, filename)
            if not os.path.exists(icon_path):
                icon_path = os.path.join(ASSETS_DIR, "icons", filename)
                
            if os.path.exists(icon_path):
                self.icon_combo.addItem(QIcon(icon_path), name, filename)
            else:
                self.icon_combo.addItem(name, filename)
        
        current_icon = self.settings.value("appearance/app_icon", "icon.png")
        index = self.icon_combo.findData(current_icon)
        if index >= 0:
            self.icon_combo.setCurrentIndex(index)
            
        self.icon_preview = QLabel()
        self.icon_preview.setFixedSize(64, 64)
        self.icon_preview.setAlignment(Qt.AlignCenter)
        
        icon_layout = QHBoxLayout()
        icon_layout.addWidget(self.icon_combo)
        icon_layout.addWidget(self.icon_preview)
        
        self.icon_combo.currentIndexChanged.connect(self._update_icon_preview)
        
        app_layout.addRow("Ikona aplikace:", icon_layout)
        self._update_icon_preview()
        
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

        # Bottom Size Grip (the "dots")
        grip_layout = QHBoxLayout()
        grip_layout.setContentsMargins(0, 0, 0, 0)
        grip_layout.addStretch()
        grip = QSizeGrip(self)
        grip.setFixedSize(16, 16)
        grip_layout.addWidget(grip, 0, Qt.AlignBottom | Qt.AlignRight)
        self.main_layout.addLayout(grip_layout)

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

    def _update_icon_preview(self):
        icon_name = self.icon_combo.currentData()
        
        icon_path = os.path.join(ASSETS_DIR, icon_name)
        if not os.path.exists(icon_path):
            icon_path = os.path.join(ASSETS_DIR, "icons", icon_name)
            
        if os.path.exists(icon_path):
            self.icon_preview.setPixmap(QPixmap(icon_path).scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            # Immediate feedback: tell the rest of the app to change icon
            bus.app_icon_changed.emit(icon_name)
        else:
            self.icon_preview.setText("N/A")

    def _browse_editor(self):
        file, _ = QFileDialog.getOpenFileName(self, "Vybrat editor", "", "Spustitelné soubory (*.exe *.com *.bat *.sh);;Všechny soubory (*)")
        if file:
            self.editor_edit.setText(file)

    def _save_and_accept(self):
        self.settings.setValue("editor/path", self.editor_edit.text().strip())
        self.settings.setValue("behavior/confirm_delete", "true" if self.confirm_delete.isChecked() else "false")
        self.settings.setValue("appearance/app_icon", self.icon_combo.currentData())
        self.settings.setValue("appearance/theme", self.theme_combo.currentText())
        self.accept()

    def reject(self):
        # Revert icon and theme if changed but not saved
        bus.app_icon_changed.emit(self.original_icon)
        bus.app_theme_changed.emit(self.original_theme)
        super().reject()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            edge = self._get_edge(event.position().toPoint())
            if edge:
                self._resizing = True
                self._resize_edge = edge
                event.accept()
            elif self.title_bar.underMouse():
                self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                event.accept()

    def mouseMoveEvent(self, event):
        pos = event.position().toPoint()
        if not event.buttons():
            edge = self._get_edge(pos)
            self._update_cursor(edge)
            return

        if self._resizing and self._resize_edge:
            self._handle_resize(event.globalPosition().toPoint())
            event.accept()
        elif self._drag_pos and event.buttons() & Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        self._resizing = False
        self._resize_edge = None

    def _get_edge(self, pos):
        w, h = self.width(), self.height()
        m = self._resize_margin
        on_left = pos.x() < m
        on_right = pos.x() > w - m
        on_top = pos.y() < m
        on_bottom = pos.y() > h - m
        
        if on_left and on_top: return "top-left"
        if on_right and on_top: return "top-right"
        if on_left and on_bottom: return "bottom-left"
        if on_right and on_bottom: return "bottom-right"
        if on_left: return "left"
        if on_right: return "right"
        if on_top: return "top"
        if on_bottom: return "bottom"
        return None

    def _update_cursor(self, edge):
        if edge in ("top", "bottom"): self.setCursor(Qt.SizeVerCursor)
        elif edge in ("left", "right"): self.setCursor(Qt.SizeHorCursor)
        elif edge in ("top-left", "bottom-right"): self.setCursor(Qt.SizeBDiagCursor)
        elif edge in ("top-right", "bottom-left"): self.setCursor(Qt.SizeFDiagCursor)
        else: self.setCursor(Qt.ArrowCursor)

    def _handle_resize(self, global_pos):
        rect = self.geometry()
        edge = self._resize_edge
        min_w, min_h = self.minimumSize().width(), self.minimumSize().height()
        
        if "left" in edge:
            new_w = rect.right() - global_pos.x()
            if new_w >= min_w: rect.setLeft(global_pos.x())
        if "right" in edge: rect.setRight(global_pos.x())
        if "top" in edge:
            new_h = rect.bottom() - global_pos.y()
            if new_h >= min_h: rect.setTop(global_pos.y())
        if "bottom" in edge: rect.setBottom(global_pos.y())
        self.setGeometry(rect)
