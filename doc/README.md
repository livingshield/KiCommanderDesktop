# KiCommander Desktop v1.8.0

Moderní open-source dvou-panelový správce souborů pro Windows/Linux/Mac, inspirovaný legendárním Total Commanderem.

## Hlavní Funkce

- **Dvoupanelové rozhraní se záložkami (Tabs)**: Možnost otevírat, zavírat a zamykat záložky v obou panelech.
- **VFS (Virtual File System)**: Plná podpora pro ZIP, 7z a síťové protokoly FTP, SFTP/SSH a SMB.
- **Hromadné přejmenování (Multi-Rename)**: Pokročilý nástroj s maskami `[N]`, `[E]`, `[C]`, `[D]` a podporou regulárních výrazů.
- **Synchronizace složek**: Vizuální porovnání obsahu dvou adresářů a jejich sjednocení.
- **Queue Manager**: Všechny operace (kopírování, přejmenování) běží na pozadí a neblokují UI.
- **Pokročilý Prohlížeč (F3)**: Renderování Markdownu, přehrávání médií (Audio/Video), zvýrazňování syntaxe a hexadecimální režim.
- **Integrovaná Příkazová Řádka**: Podpora pro lokální subprocess i vzdálené příkazy přes SSH (u SFTP panelů).

## Klávesové Zkratky

- `F3` - Prohlížení (Markdown, Obrázek, Video, Text)
- `F4` - Upravit (v externím editoru)
- `F5` - Kopírovat (do druhého panelu / záložky)
- `F6` - Přesunout
- `F7` - Nová složka
- `F8` - Smazat
- `F11` - Hromadné přejmenování (Multi-Rename)
- `Alt+Y` - Synchronizace složek
- `Ctrl+Up` - Otevřít aktuální složku v novém tabu
- `Prostřední tlačítko myši` - Otevřít složku v novém tabu
- `Alt+F7` - Hledání (včetně Grepu a VFS)
- `Ctrl+D` - Oblíbené (Hotlist)
- `Ctrl+R` - Obnovit seznam souborů

## Technologie

- **Framework**: PySide6 (Qt)
- **Ikony**: FontAwesome 5 (přes qtawesome)
- **Design**: Catppuccin Mocha Theme (Vanilla CSS v `style.qss`)
- **Protokoly**: Paramiko, SMBProtocol, PYSNMP

## Instalace a Vývoj

1. `pip install -r requirements.txt`
2. `python src/main.py`
3. Pro build (.exe): `pyinstaller KiCommander.spec`
