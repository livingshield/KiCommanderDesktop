import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPlainTextEdit, QScrollArea, QPushButton, QTextBrowser)
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QPixmap, QFont
import qtawesome as qta
from syntax_highlighter import CodeHighlighter

try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
except ImportError:
    pass

class QuickViewWidget(QWidget):
    """
    Volitelný třetí panel pro okamžitý náhled vybraného souboru (text, markdown, obrázek).
    Je nezávislý na okně `PreviewDialog` (který ho teď může používat jako svůj centrální content).
    """
    
    # Signál případně emitovaný, kdyby panel chtěl interagovat zpátky nahoru (např close button)
    close_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.file_path = None
        self.player = None
        self.audio_output = None
        self._is_empty = True
        self.setup_ui()
        
    def setup_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(4, 4, 4, 4)
        
        # Obal pro obsah náhledu
        self.content_container = QWidget()
        self.content_layout = QVBoxLayout(self.content_container)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        
        self.main_layout.addWidget(self.content_container)
        
        # Nastavení defaultního vizuálu (Empty State)
        self.show_empty_state()
        
    def _clear_layout(self):
        """Smaže aktuální obsah (předchozí náhled)."""
        if self.player:
            self.player.stop()
            self.player = None
            self.audio_output = None
            
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
            elif item.layout() is not None:
                self._clear_sub_layout(item.layout())

    def _clear_sub_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_sub_layout(item.layout())
        layout.deleteLater()

    def show_empty_state(self):
        self._clear_layout()
        self._is_empty = True
        
        icon_lbl = QLabel()
        icon_lbl.setPixmap(qta.icon("fa5s.eye", color="#45475a").pixmap(64, 64))
        icon_lbl.setAlignment(Qt.AlignCenter)
        
        text_lbl = QLabel("No file selected for preview")
        text_lbl.setStyleSheet("color: #585b70; font-style: italic;")
        text_lbl.setAlignment(Qt.AlignCenter)
        
        self.content_layout.addStretch()
        self.content_layout.addWidget(icon_lbl)
        self.content_layout.addWidget(text_lbl)
        self.content_layout.addStretch()

    def load_file(self, file_path: str):
        """Načte a zobrazí soubor dle přípony. Pokud je cesta None, zobrazí prázdný stav."""
        if not file_path or not os.path.isfile(file_path):
            if not self._is_empty:
                self.show_empty_state()
            return

        # Zamezení zbytečného přenačítání stejného souboru
        if self.file_path == file_path:
            return

        self.file_path = file_path
        self._is_empty = False
        self._clear_layout()

        # Ochrana obřích souborů (max 50 MB pro txt/hex) - mediální/obrázky si poradí streamováním
        try:
            size_mb = os.path.getsize(file_path) / (1024 * 1024)
            if size_mb > 50:
                self._show_error(f"File too large for Quick View ({size_mb:.1f} MB).\nLimit is 50 MB.")
                return
        except OSError:
            pass

        ext = os.path.splitext(file_path)[1].lower()

        try:
            if ext in [".jpg", ".jpeg", ".png", ".bmp", ".gif", ".ico", ".svg", ".webp", ".heic"]:
                self.show_image()
            elif ext == ".md":
                self.show_markdown()
            elif ext in [".txt", ".py", ".json", ".xml", ".html", ".css", ".js",
                         ".csv", ".log", ".ini", ".cfg", ".yml", ".yaml", ".toml",
                         ".bat", ".cmd", ".sh", ".ps1", ".c", ".cpp", ".h", ".java",
                         ".rs", ".go", ".ts", ".tsx", ".jsx", ".vue", ".qss"]:
                self.show_text()
            elif ext in [".mp3", ".wav", ".m4a", ".flac", ".ogg"]:
                self.show_media(video=False)
            elif ext in [".mp4", ".mkv", ".avi", ".mov"]:
                self.show_media(video=True)
            else:
                self.show_hex()
        except Exception as e:
            self._show_error(f"Error loading preview: {e}")

    def _show_error(self, message: str):
        lbl = QLabel(message)
        lbl.setStyleSheet("color: #f38ba8;")  # Catppuccin red
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter) 
        self.content_layout.addWidget(lbl)

    def show_image(self):
        from PySide6.QtGui import QImage, QPixmap
        from PIL import Image
        import io

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background-color: transparent; border: none;")
        
        label = QLabel()
        label.setAlignment(Qt.AlignCenter)
        
        # Use Pillow for broader format support
        with Image.open(self.file_path) as pil_img:
            if pil_img.mode != "RGB" and pil_img.mode != "RGBA":
                pil_img = pil_img.convert("RGBA")
            
            # Convert to QImage directly
            byte_arr = io.BytesIO()
            pil_img.save(byte_arr, format='PNG')
            qimg = QImage.fromData(byte_arr.getvalue())
            pixmap = QPixmap.fromImage(qimg)
            
            if pixmap.width() > 1000:
                pixmap = pixmap.scaledToWidth(1000, Qt.SmoothTransformation)
            
            label.setPixmap(pixmap)
            
        scroll.setWidget(label)
        self.content_layout.addWidget(scroll)

    def show_text(self):
        editor = QPlainTextEdit()
        editor.setReadOnly(True)
        editor.setFont(QFont("Consolas", 10))
        editor.setStyleSheet("background-color: #181825; color: #cdd6f4; border: 1px solid #313244; border-radius: 4px;")
        
        ext = os.path.splitext(self.file_path)[1].lower()
        self.highlighter = CodeHighlighter(editor.document(), ext)
        
        with open(self.file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read(5 * 1024 * 1024)  # Read at most 5MB
        editor.setPlainText(content)
        self.content_layout.addWidget(editor)

    def show_markdown(self):
        browser = QTextBrowser()
        browser.setStyleSheet("background-color: #181825; color: #cdd6f4; border: 1px solid #313244; border-radius: 4px;")
        with open(self.file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read(5 * 1024 * 1024)
        browser.setMarkdown(content)
        self.content_layout.addWidget(browser)

    def show_media(self, video=True):
        container = QWidget()
        vbox = QVBoxLayout(container)
        vbox.setContentsMargins(0, 0, 0, 0)
        
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        
        if video:
            video_widget = QVideoWidget()
            video_widget.setMinimumHeight(200)
            vbox.addWidget(video_widget)
            self.player.setVideoOutput(video_widget)
        else:
            icon = QLabel()
            icon.setPixmap(qta.icon("fa5s.music", color="#89b4fa").pixmap(64, 64))
            icon.setAlignment(Qt.AlignCenter)
            vbox.addWidget(icon)

        controls = QHBoxLayout()
        play_btn = QPushButton(qta.icon("fa5s.play", color="#a6e3a1"), "Play")
        play_btn.clicked.connect(self.player.play)
        pause_btn = QPushButton(qta.icon("fa5s.pause", color="#f9e2af"), "Pause")
        pause_btn.clicked.connect(self.player.pause)
        
        controls.addWidget(play_btn)
        controls.addWidget(pause_btn)
        vbox.addLayout(controls)
        
        self.player.setSource(QUrl.fromLocalFile(self.file_path))
        self.content_layout.addWidget(container)
        # Nechceme automaticky spouštět z Quick View
        # self.player.play()

    def show_hex(self):
        editor = QPlainTextEdit()
        editor.setReadOnly(True)
        editor.setFont(QFont("Consolas", 10))
        editor.setStyleSheet("background-color: #181825; color: #cdd6f4; border: 1px solid #313244; border-radius: 4px;")
        
        with open(self.file_path, "rb") as f:
            data = f.read(8192) # Pouze prvních 8KB pro quick preview (hex je jinak dlouhý)
        
        lines = []
        for i in range(0, len(data), 16):
            chunk = data[i:i+16]
            hex_part = " ".join(f"{b:02X}" for b in chunk)
            ascii_part = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
            lines.append(f"{i:08X}  {hex_part:<48}  {ascii_part}")
        
        editor.setPlainText("\n".join(lines))
        self.content_layout.addWidget(editor)
