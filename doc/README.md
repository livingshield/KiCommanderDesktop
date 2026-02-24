# KiCommander Desktop

Moderní souborový manažer inspirovaný Total Commanderem, postavený na Pythonu a PySide6. Aplikace nabízí dvoupanelové rozhraní s důrazem na rychlost, asynchronní operace a prémiový Catppuccin Mocha design.

## 📋 Aktuální stav implementace

Projekt je plně funkční se třemi dokončenými fázemi vývoje. Všechny plánované funkce jsou implementovány a nasazeny.

### ✅ Fáze 1 – Power-User Features

| Feature | Stav | Popis |
|---------|------|-------|
| Auto-refresh | ✅ Hotovo | `QFileSystemWatcher` s 300ms debounce – panel se automaticky aktualizuje při změnách v souborovém systému |
| Syntax Highlighting (F3) | ✅ Hotovo | Zvýrazňování syntaxe pro Python, JS, HTML, CSS, JSON, YAML, C/C++, Shell v preview dialogu |
| Filtry ve vyhledávání (Alt+F7) | ✅ Hotovo | Filtrování výsledků podle velikosti (min/max) a data (od/do) |
| Properties dialog (Alt+Enter) | ✅ Hotovo | Výpočet velikosti složky na pozadí, Windows atributy, custom title bar |

### ✅ Fáze 2 – Architektura

| Feature | Stav | Popis |
|---------|------|-------|
| Archive VFS | ✅ Hotovo | Procházení ZIP/TAR/GZ archivů jako virtuálních složek – double-click vstoupí do archivu, extrakce souborů |
| Plugin System | ✅ Hotovo | Automatická detekce pluginů z `plugins/`, zobrazení v menu Commands |
| Batch Rename Plugin | ✅ Hotovo | Hromadné přejmenování souborů s find/replace a live preview |

### ✅ Fáze 3 – DevEx & Distribuce

| Feature | Stav | Popis |
|---------|------|-------|
| Testy | ✅ 41 testů | `test_file_ops.py`, `test_navigation_utils.py`, `test_file_model.py` |
| CI/CD | ✅ Hotovo | GitHub Actions – automatické testy + build na push do main |
| requirements.txt | ✅ Hotovo | Definované závislosti pro reprodukovatelné instalace |

### Hlavní funkce

- **Dvoupanelové rozhraní:** Nezávislé procházení dvou různých adresářů současně.
- **Asynchronní I/O:** Načítání obsahu adresářů probíhá na pozadí (QThread), UI nikdy nezamrzá.
- **Auto-refresh:** `QFileSystemWatcher` automaticky aktualizuje panel při změnách souborů.
- **Kompletní správa souborů:**
  - Kopírování (F5)
  - Přesun (F6)
  - Vytvoření složky (F7)
  - Mazání (F8 / Delete) s potvrzením
  - Přejmenování (F2)
- **Pokročilá navigace:**
  - **Drive Selector:** Rychlé přepínání disků (C:, D:, USB atd.).
  - **Quick Links Sidebar:** Postranní lišta pro okamžitý přístup k systémovým složkám.
  - Navigace klávesnicí (Enter) i myší (double-click).
- **Vyhledávání (Alt+F7):**
  - Rekurzivní vyhledávání podle názvu a obsahu souborů.
  - Filtry: velikost (min/max KB/MB/GB), datum modifikace (od/do).
  - Výsledky s možností navigace na nalezený soubor.
- **Preview (F3):**
  - Text s **syntax highlighting** (Python, JS, HTML, CSS, JSON, YAML, C/C++, Shell).
  - Obrázky (JPG, PNG, BMP, GIF, SVG).
  - Hex dump pro binární soubory.
- **Archive VFS:**
  - Procházení ZIP, TAR, TAR.GZ, TAR.BZ2, TAR.XZ archivů jako složek.
  - Extrakce jednotlivých souborů nebo celého archivu.
  - Preview souborů přímo z archivu.
- **Plugin System:**
  - Pluginy z `plugins/` složky automaticky detekovány a přidány do menu.
  - Dodaný plugin: **Batch Rename** (hromadné přejmenování s find/replace).
- **Properties (Alt+Enter):**
  - Velikost složky počítána na pozadí.
  - Windows atributy (Read-Only, Hidden, System, Archive).
  - Datum vytvoření, modifikace, přístupu.
- **Interaktivita & UI:**
  - Multi-selection mezerníkem.
  - Integrovaná příkazová řádka.
  - Tooltips na všech prvcích.
  - **Catppuccin Mocha** dark theme s custom frameless title bary na všech dialozích.
  - Řazení sloupců kliknutím na hlavičku (▲/▼ indikátor).
- **Perzistence:** Pamatuje si cesty, velikost a pozici okna.

---

## 🏗️ Struktura projektu

```text
KiCommanderDesktop/
├── .github/
│   └── workflows/
│       └── build.yml           # CI/CD – automatické testy + build
├── assets/
│   └── icon.ico                # Ikona aplikace
├── bin/                        # Zkompilovaná spustitelná verze
│   └── KiCommander.exe         # Samostatný EXE soubor pro Windows
├── doc/                        # Dokumentace
│   └── README.md               # Tento soubor
├── plugins/                    # Uživatelské pluginy
│   ├── __init__.py
│   └── batch_rename.py         # Plugin: hromadné přejmenování
├── src/                        # Zdrojové kódy aplikace
│   ├── archive_vfs.py          # Virtual File System pro archivy (ZIP/TAR)
│   ├── file_model.py           # MVC Model (QAbstractTableModel) s řazením
│   ├── file_ops.py             # Souborové operace na pozadí
│   ├── fs_worker.py            # Asynchronní skener souborového systému
│   ├── main.py                 # Hlavní vstupní bod a GUI logika
│   ├── navigation_utils.py     # Detekce disků a quick links
│   ├── plugin_manager.py       # Správa pluginů
│   ├── preview_dialog.py       # F3 Preview (text, obrázky, hex)
│   ├── properties_dialog.py    # Alt+Enter Properties dialog
│   ├── search_dialog.py        # Alt+F7 vyhledávání s filtry
│   ├── style.qss               # Catppuccin Mocha QSS stylesheet
│   └── syntax_highlighter.py   # Zvýrazňování syntaxe pro preview
├── tests/                      # Pytest testy (41 testů)
│   ├── test_file_model.py      # Testy FileModel: řazení, aktualizace, ikony
│   ├── test_file_ops.py        # Testy souborových operací: copy, move, delete
│   └── test_navigation_utils.py # Testy navigace: disky, quick links
├── KiCommander.spec            # PyInstaller specifikace
├── requirements.txt            # Python závislosti
└── run_build.bat               # Ruční build skript
```

---

## 🛠️ Technologie a Architektura

- **Jazyk:** Python 3.11+
- **GUI Framework:** PySide6 (Qt for Python)
- **Architektura:** MVC (Model-View-Controller) – striktní oddělení dat od zobrazení
- **Ikonky:** `qtawesome` (FontAwesome 5 Free)
- **Design:** Catppuccin Mocha dark theme s custom frameless dialogy
- **Kompilace:** PyInstaller (samostatný .exe)
- **Testy:** pytest (41 testů)
- **CI/CD:** GitHub Actions (automatické testy + build na push do main)

---

## 🚀 Jak aplikaci spustit

### Ze zdrojových kódů

1. Nainstalujte závislosti:

   ```bash
   pip install -r requirements.txt
   ```

2. Spusťte aplikaci:

   ```bash
   python src/main.py
   ```

3. Spusťte testy:

   ```bash
   python -m pytest tests/ -v
   ```

### Spustitelná verze (Windows)

Přejděte do složky `bin/` a spusťte soubor `KiCommander.exe`.

---

## ⌨️ Ovládání a zkratky

| Klávesa | Akce |
| :--- | :--- |
| **Enter** | Otevře složku, soubor, nebo vstoupí do archivu |
| **Tab** | Přepíná zaměření (focus) mezi panely |
| **Spacebar** | Vybere/označí soubor (multi-selection) |
| **F2** | Přejmenuje soubor |
| **F3** | Preview souboru (text se syntax highlighting, obrázky, hex) |
| **F5** | Kopíruje označené položky do protějšího panelu |
| **F6** | Přesune označené položky do protějšího panelu |
| **F7** | Vytvoří nový adresář |
| **F8 / Del** | Smaže označené položky |
| **Ctrl + R** | Obnoví (refresh) seznam souborů |
| **Ctrl + F** | Filtr v aktuálním panelu |
| **Alt + F7** | Pokročilé vyhledávání s filtry (název, obsah, velikost, datum) |
| **Alt + Enter** | Vlastnosti souboru/složky |
| **Alt + F4** | Ukončí aplikaci |

---

## 🧩 Plugin System

Pluginy jsou Python soubory v složce `plugins/`. Každý plugin musí exportovat:

```python
name = "Název pluginu"           # Zobrazí se v error dialozích
menu_text = "Text v menu..."     # Zobrazí se v Commands menu
def action(selected_files, panel):  # Funkce volaná při kliknutí
    ...
```

Pluginy se automaticky detekují při spuštění a zobrazí se v menu **Commands** s ikonou 🧩.

---

## 📦 Vytvoření EXE (Build)

```bash
pyinstaller KiCommander.spec --noconfirm
```

Výstup bude v `dist/KiCommander/`. Pro deployment přesuňte obsah do `bin/`.
