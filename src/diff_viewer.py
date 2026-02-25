import difflib
from PySide6.QtWidgets import (QDialog, QHBoxLayout, QVBoxLayout, QPlainTextEdit, 
                             QPushButton, QLabel, QFrame)
from PySide6.QtCore import Qt
from PySide6.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor, QFont

class DiffHighlighter(QSyntaxHighlighter):
    """Zvýrazňuje řádky začínající na '+' (zeleně) nebo '-' (červeně)."""
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.removed_format = QTextCharFormat()
        self.removed_format.setBackground(QColor("#452f33")) # Jemně červená (Mocha-ish)
        self.removed_format.setForeground(QColor("#f38ba8"))
        
        self.added_format = QTextCharFormat()
        self.added_format.setBackground(QColor("#334533"))   # Jemně zelená
        self.added_format.setForeground(QColor("#a6e3a1"))

    def highlightBlock(self, text):
        if text.startswith("-"):
            self.setFormat(0, len(text), self.removed_format)
        elif text.startswith("+"):
            self.setFormat(0, len(text), self.added_format)

class DiffDialog(QDialog):
    def __init__(self, file1_path, file1_content, file2_path, file2_content, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Compare: {file1_path} vs {file2_path}")
        self.setMinimumSize(1000, 700)
        # Nastavení bez okrajů pro moderní vzhled (volitelné, ale ladí s Catppuccin)
        # self.setWindowFlags(Qt.FramelessWindowHint)
        
        self.setObjectName("DiffDialog")
        self.setStyleSheet("""
            #DiffDialog { background-color: #1e1e2e; color: #cdd6f4; }
            QLabel { color: #f5e0dc; font-weight: bold; }
            QPlainTextEdit { 
                background-color: #181825; 
                color: #cdd6f4; 
                border: 1px solid #313244;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 10pt;
            }
        """)

        layout = QVBoxLayout(self)
        
        # Header with filenames
        header = QHBoxLayout()
        header.addWidget(QLabel(f"← {file1_path}"))
        header.addStretch()
        header.addWidget(QLabel(f"→ {file2_path}"))
        layout.addLayout(header)

        # Editors layout
        editors_layout = QHBoxLayout()
        
        self.edit_left = QPlainTextEdit()
        self.edit_left.setReadOnly(True)
        self.edit_left.setLineWrapMode(QPlainTextEdit.NoWrap)
        
        self.edit_right = QPlainTextEdit()
        self.edit_right.setReadOnly(True)
        self.edit_right.setLineWrapMode(QPlainTextEdit.NoWrap)
        
        editors_layout.addWidget(self.edit_left)
        editors_layout.addWidget(self.edit_right)
        layout.addLayout(editors_layout)

        # Bottom buttons
        btns = QHBoxLayout()
        btns.addStretch()
        close_btn = QPushButton("Close")
        close_btn.setFixedWidth(100)
        close_btn.clicked.connect(self.accept)
        btns.addWidget(close_btn)
        layout.addLayout(btns)

        # Apply highlighters
        self.highlighter_left = DiffHighlighter(self.edit_left.document())
        self.highlighter_right = DiffHighlighter(self.edit_right.document())

        # Sync scrolling
        left_bar = self.edit_left.verticalScrollBar()
        right_bar = self.edit_right.verticalScrollBar()
        left_bar.valueChanged.connect(right_bar.setValue)
        right_bar.valueChanged.connect(left_bar.setValue)
        
        left_hor = self.edit_left.horizontalScrollBar()
        right_hor = self.edit_right.horizontalScrollBar()
        left_hor.valueChanged.connect(right_hor.setValue)
        right_hor.valueChanged.connect(left_hor.setValue)

        self._compare(file1_content, file2_content)

    def _compare(self, content1, content2):
        lines1 = content1.splitlines()
        lines2 = content2.splitlines()
        
        diff = list(difflib.ndiff(lines1, lines2))
        
        left_text = []
        right_text = []
        
        for line in diff:
            code = line[0]
            text = line[2:]
            
            if code == ' ':
                left_text.append(f"  {text}")
                right_text.append(f"  {text}")
            elif code == '-':
                left_text.append(f"- {text}")
                # Empty line on the other side to keep sync
                right_text.append("")
            elif code == '+':
                # Empty line on the other side to keep sync
                left_text.append("")
                right_text.append(f"+ {text}")
            elif code == '?':
                # Skip secondary diff lines for simplicity in this side-by-side view
                continue

        self.edit_left.setPlainText("\n".join(left_text))
        self.edit_right.setPlainText("\n".join(right_text))
