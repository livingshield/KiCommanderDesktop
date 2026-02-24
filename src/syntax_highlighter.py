"""
Syntax highlighter for the Preview dialog (F3).
Supports Python, JavaScript, HTML, CSS, JSON, YAML, C/C++, and shell scripts.
Uses Catppuccin Mocha color palette.
"""
import re
from PySide6.QtCore import Qt
from PySide6.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor, QFont


# Catppuccin Mocha palette
COLORS = {
    "keyword":   "#cba6f7",  # Mauve
    "builtin":   "#f38ba8",  # Red
    "string":    "#a6e3a1",  # Green
    "comment":   "#6c7086",  # Overlay0
    "number":    "#fab387",  # Peach
    "function":  "#89b4fa",  # Blue
    "decorator": "#f9e2af",  # Yellow
    "tag":       "#f38ba8",  # Red (HTML tags)
    "attr":      "#fab387",  # Peach (HTML attributes)
    "operator":  "#89dceb",  # Sky
    "type":      "#f9e2af",  # Yellow
    "constant":  "#fab387",  # Peach
}


def _fmt(color, bold=False, italic=False):
    """Create a QTextCharFormat with the given color and style."""
    f = QTextCharFormat()
    f.setForeground(QColor(color))
    if bold:
        f.setFontWeight(QFont.Bold)
    if italic:
        f.setFontItalic(True)
    return f


# Language-specific rule sets: list of (regex_pattern, format)
PYTHON_RULES = [
    (r'\b(and|as|assert|async|await|break|class|continue|def|del|elif|else|except|'
     r'finally|for|from|global|if|import|in|is|lambda|nonlocal|not|or|pass|'
     r'raise|return|try|while|with|yield)\b', _fmt(COLORS["keyword"], bold=True)),
    (r'\b(True|False|None|self|cls)\b', _fmt(COLORS["constant"], bold=True)),
    (r'\b(print|len|range|int|str|float|list|dict|set|tuple|type|isinstance|'
     r'super|open|map|filter|zip|enumerate|sorted|reversed|any|all|min|max|'
     r'abs|sum|round|input|hasattr|getattr|setattr|property|staticmethod|'
     r'classmethod|ValueError|TypeError|KeyError|IndexError|Exception)\b', _fmt(COLORS["builtin"])),
    (r'@\w+', _fmt(COLORS["decorator"])),
    (r'\bdef\s+(\w+)', _fmt(COLORS["function"])),
    (r'\bclass\s+(\w+)', _fmt(COLORS["type"], bold=True)),
    (r'#[^\n]*', _fmt(COLORS["comment"], italic=True)),
    (r'"""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\'', _fmt(COLORS["string"])),
    (r'"[^"\\]*(\\.[^"\\]*)*"', _fmt(COLORS["string"])),
    (r"'[^'\\]*(\\.[^'\\]*)*'", _fmt(COLORS["string"])),
    (r'\b\d+\.?\d*\b', _fmt(COLORS["number"])),
]

JS_RULES = [
    (r'\b(var|let|const|function|return|if|else|for|while|do|switch|case|break|'
     r'continue|new|this|class|extends|import|export|default|from|try|catch|'
     r'finally|throw|async|await|yield|typeof|instanceof|in|of|delete|void)\b',
     _fmt(COLORS["keyword"], bold=True)),
    (r'\b(true|false|null|undefined|NaN|Infinity)\b', _fmt(COLORS["constant"], bold=True)),
    (r'\b(console|document|window|Math|JSON|Array|Object|String|Number|'
     r'Promise|setTimeout|setInterval|fetch|require|module|exports)\b', _fmt(COLORS["builtin"])),
    (r'//[^\n]*', _fmt(COLORS["comment"], italic=True)),
    (r'/\*[\s\S]*?\*/', _fmt(COLORS["comment"], italic=True)),
    (r'`[^`]*`', _fmt(COLORS["string"])),
    (r'"[^"\\]*(\\.[^"\\]*)*"', _fmt(COLORS["string"])),
    (r"'[^'\\]*(\\.[^'\\]*)*'", _fmt(COLORS["string"])),
    (r'\b\d+\.?\d*\b', _fmt(COLORS["number"])),
    (r'\b(\w+)\s*\(', _fmt(COLORS["function"])),
]

HTML_RULES = [
    (r'<!--[\s\S]*?-->', _fmt(COLORS["comment"], italic=True)),
    (r'</?[\w-]+', _fmt(COLORS["tag"], bold=True)),
    (r'/?\s*>', _fmt(COLORS["tag"], bold=True)),
    (r'\b[\w-]+(?==)', _fmt(COLORS["attr"])),
    (r'"[^"]*"', _fmt(COLORS["string"])),
    (r"'[^']*'", _fmt(COLORS["string"])),
]

CSS_RULES = [
    (r'/\*[\s\S]*?\*/', _fmt(COLORS["comment"], italic=True)),
    (r'[.#][\w-]+', _fmt(COLORS["function"])),
    (r'\b(color|background|border|margin|padding|font|display|position|'
     r'width|height|top|left|right|bottom|flex|grid|overflow|opacity|'
     r'transition|transform|animation|z-index|cursor|visibility)\b', _fmt(COLORS["keyword"])),
    (r':\s*[^;{]+', _fmt(COLORS["string"])),
    (r'#[0-9a-fA-F]{3,8}\b', _fmt(COLORS["number"])),
    (r'\b\d+\.?\d*(px|em|rem|%|vh|vw|pt|s|ms)?\b', _fmt(COLORS["number"])),
]

JSON_RULES = [
    (r'"[^"]*"\s*:', _fmt(COLORS["keyword"])),
    (r'"[^"]*"', _fmt(COLORS["string"])),
    (r'\b(true|false|null)\b', _fmt(COLORS["constant"], bold=True)),
    (r'-?\b\d+\.?\d*([eE][+-]?\d+)?\b', _fmt(COLORS["number"])),
]

C_RULES = [
    (r'\b(auto|break|case|char|const|continue|default|do|double|else|enum|'
     r'extern|float|for|goto|if|int|long|register|return|short|signed|sizeof|'
     r'static|struct|switch|typedef|union|unsigned|void|volatile|while|'
     r'#include|#define|#ifdef|#ifndef|#endif|#pragma|#if|#else)\b',
     _fmt(COLORS["keyword"], bold=True)),
    (r'\b(NULL|true|false|TRUE|FALSE)\b', _fmt(COLORS["constant"], bold=True)),
    (r'//[^\n]*', _fmt(COLORS["comment"], italic=True)),
    (r'/\*[\s\S]*?\*/', _fmt(COLORS["comment"], italic=True)),
    (r'"[^"\\]*(\\.[^"\\]*)*"', _fmt(COLORS["string"])),
    (r"'[^'\\]*(\\.[^'\\]*)*'", _fmt(COLORS["string"])),
    (r'\b\d+\.?\d*[fFlLuU]?\b', _fmt(COLORS["number"])),
    (r'\b(int|char|float|double|void|long|short|unsigned|signed|bool|size_t|'
     r'uint8_t|uint16_t|uint32_t|uint64_t|int8_t|int16_t|int32_t|int64_t)\b',
     _fmt(COLORS["type"], bold=True)),
]

YAML_RULES = [
    (r'#[^\n]*', _fmt(COLORS["comment"], italic=True)),
    (r'^[\w.-]+\s*:', _fmt(COLORS["keyword"], bold=True)),
    (r'"[^"]*"', _fmt(COLORS["string"])),
    (r"'[^']*'", _fmt(COLORS["string"])),
    (r'\b(true|false|yes|no|null|~)\b', _fmt(COLORS["constant"], bold=True)),
    (r'-?\b\d+\.?\d*\b', _fmt(COLORS["number"])),
]

SHELL_RULES = [
    (r'\b(if|then|else|elif|fi|for|while|do|done|case|esac|in|function|'
     r'return|exit|local|export|source|alias|unalias|set|unset|echo|printf|'
     r'cd|ls|cp|mv|rm|mkdir|chmod|chown|grep|sed|awk|find|xargs|cat|head|'
     r'tail|wc|sort|uniq|cut|tr|tee|pipe)\b', _fmt(COLORS["keyword"], bold=True)),
    (r'#[^\n]*', _fmt(COLORS["comment"], italic=True)),
    (r'"[^"\\]*(\\.[^"\\]*)*"', _fmt(COLORS["string"])),
    (r"'[^']*'", _fmt(COLORS["string"])),
    (r'\$\{?[\w]+\}?', _fmt(COLORS["builtin"])),
    (r'\b\d+\.?\d*\b', _fmt(COLORS["number"])),
]


# Extension → rule set mapping
LANG_MAP = {
    ".py":   PYTHON_RULES,
    ".pyw":  PYTHON_RULES,
    ".js":   JS_RULES,
    ".jsx":  JS_RULES,
    ".ts":   JS_RULES,
    ".tsx":  JS_RULES,
    ".mjs":  JS_RULES,
    ".html": HTML_RULES,
    ".htm":  HTML_RULES,
    ".xml":  HTML_RULES,
    ".svg":  HTML_RULES,
    ".css":  CSS_RULES,
    ".qss":  CSS_RULES,
    ".scss": CSS_RULES,
    ".json": JSON_RULES,
    ".c":    C_RULES,
    ".cpp":  C_RULES,
    ".cxx":  C_RULES,
    ".cc":   C_RULES,
    ".h":    C_RULES,
    ".hpp":  C_RULES,
    ".java": C_RULES,
    ".rs":   C_RULES,
    ".go":   C_RULES,
    ".yml":  YAML_RULES,
    ".yaml": YAML_RULES,
    ".toml": YAML_RULES,
    ".sh":   SHELL_RULES,
    ".bash": SHELL_RULES,
    ".zsh":  SHELL_RULES,
    ".bat":  SHELL_RULES,
    ".cmd":  SHELL_RULES,
    ".ps1":  SHELL_RULES,
}


class CodeHighlighter(QSyntaxHighlighter):
    """Applies syntax highlighting rules based on file extension."""

    def __init__(self, document, extension: str):
        super().__init__(document)
        ext = extension.lower()
        self._rules = [(re.compile(pat), fmt) for pat, fmt in LANG_MAP.get(ext, [])]

    def highlightBlock(self, text):
        for pattern, fmt in self._rules:
            for match in pattern.finditer(text):
                start = match.start()
                length = match.end() - start
                self.setFormat(start, length, fmt)
