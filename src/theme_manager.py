import os
import re

# Base Mocha Theme Hex codes used in style.qss
MOCHA_COLORS = {
    "base": "#1e1e2e",
    "crust": "#11111b",
    "mantle": "#181825",
    "surface0": "#313244",
    "surface1": "#45475a",
    "text": "#cdd6f4",
    "subtext0": "#a6adc8",
    "overlay0": "#6c7086",
    "blue": "#89b4fa",
    "green": "#a6e3a1",
    "yellow": "#f9e2af",
    "red": "#f38ba8",
    "pink": "#f5c2e7",
    "mauve": "#cba6f7",
    "peach": "#fab387",
    "rosewater": "#f5e0dc"
}

THEMES = {
    "Mocha": MOCHA_COLORS,
    "Macchiato": {
        "base": "#24273a",
        "crust": "#181926",
        "mantle": "#1e2030",
        "surface0": "#363a4f",
        "surface1": "#494d64",
        "text": "#cad3f5",
        "subtext0": "#a5adcb",
        "overlay0": "#6e738d",
        "blue": "#8aadf4",
        "green": "#a6da95",
        "yellow": "#eed49f",
        "red": "#ed8796",
        "pink": "#f5bde6",
        "mauve": "#c6a0f6",
        "peach": "#f5a97f",
        "rosewater": "#f4dbd6"
    },
    "Frappé": {
        "base": "#303446",
        "crust": "#232634",
        "mantle": "#292c3c",
        "surface0": "#414559",
        "surface1": "#51576d",
        "text": "#c6d0f5",
        "subtext0": "#a5adce",
        "overlay0": "#737994",
        "blue": "#8caaee",
        "green": "#a6d189",
        "yellow": "#e5c890",
        "red": "#e78284",
        "pink": "#f4b8e4",
        "mauve": "#ca9ee6",
        "peach": "#ef9f76",
        "rosewater": "#f2d5cf"
    },
    "Latte": {
        "base": "#eff1f5",
        "crust": "#dce0e8",
        "mantle": "#e6e9ef",
        "surface0": "#ccd0da",
        "surface1": "#bcc0cc",
        "text": "#4c4f69",
        "subtext0": "#5c5f77",
        "overlay0": "#9ca0b0",
        "blue": "#1e66f5",
        "green": "#40a02b",
        "yellow": "#df8e1d",
        "red": "#d20f39",
        "pink": "#ea76cb",
        "mauve": "#8839ef",
        "peach": "#fe640b",
        "rosewater": "#dc8a78"
    }
}

class ThemeManager:
    @staticmethod
    def get_theme_colors(theme_name: str) -> dict:
        return THEMES.get(theme_name, THEMES["Mocha"])

    @staticmethod
    def compile_stylesheet(original_qss: str, target_theme: str) -> str:
        """Replace all Mocha colors in the QSS string with target theme colors."""
        if target_theme == "Mocha" or target_theme not in THEMES:
            return original_qss
            
        target_palette = THEMES[target_theme]
        compiled = original_qss
        
        # We replace longest strings first (not strictly needed since they are fixed 7-char #RRGGBB)
        # However, to avoid double-replacing #1e1e2e -> #eff1f5 and then finding a collision, 
        # we can use a regex sub with a mapping dict.
        
        # Create mapping of Mocha color -> Target color
        replacements = {}
        for key, mocha_hex in MOCHA_COLORS.items():
            target_hex = target_palette.get(key)
            if target_hex and target_hex != mocha_hex:
                replacements[mocha_hex] = target_hex
                
        if not replacements:
            return compiled
            
        # Pattern to match any Mocha hex code case-insensitively
        pattern = re.compile("|".join(re.escape(k) for k in replacements.keys()), re.IGNORECASE)
        
        def repl(match):
            return replacements[match.group(0).lower()]
            
        compiled = pattern.sub(repl, original_qss)
        return compiled

    @staticmethod
    def apply_theme(app, qss_path: str, theme_name: str):
        if not os.path.exists(qss_path):
            return
            
        with open(qss_path, "r", encoding="utf-8") as f:
            qss_content = f.read()
            
        compiled = ThemeManager.compile_stylesheet(qss_content, theme_name)
        app.setStyleSheet(compiled)
