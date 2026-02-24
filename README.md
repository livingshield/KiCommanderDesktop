# KiCommander Desktop

Moderní souborový manažer inspirovaný Total Commanderem, postavený na Pythonu a PySide6. Aplikace nabízí dvoupanelové rozhraní s důrazem na rychlost, asynchronní operace a moderní design.

## 📋 Aktuální stav implementace

Projekt je ve fázi plně funkčního prototypu se všemi klíčovými vlastnostmi pro každodenní správu souborů.

### Hlavní funkce

- **Dvoupanelové rozhraní:** Nezávislé procházení dvou různých adresářů současně.
- **Asynchronní I/O:** Načítání obsahu adresářů probíhá na pozadí (QThread), takže UI nikdy nezamrzá (ani u velkých disků).
- **Kompletní správa souborů:**
  - Kopírování (F5)
  - Přesun (F6)
  - Vytvoření složky (F7)
  - Mazání (F8 / Delete) s potvrzením.
- **Pokročilá navigace:**
  - **Drive Selector:** Rychlé přepínání disků (C:, D:, USB atd.).
  - **Quick Links Sidebar:** Postranní lišta pro okamžitý přístup k systémovým složkám (Plocha, Stahování, Dokumenty atd.).
  - Navigace pomocí klávesnice (Enter) i myši (double-click).
- **Interaktivita & UI:**
  - **Multi-selection:** Označování souborů mezerníkem (Spacebar) pro hromadné operace.
  - **Příkazová řádka:** Integrovaný terminál pro spouštění systémových příkazů v aktivní složce.
  - **Informativní bubliny (Tooltips):** Nápověda při najetí myší na jakýkoliv ovládací prvek.
  - **Moderní Dark Theme:** Prémiový vzhled založený na QSS s ikonami z knihovny FontAwesome.
- **Perzistence:** Aplikace si pamatuje poslední otevřené cesty, velikost a pozici okna.

---

## 🏗️ Struktura projektu

```text
KiCommanderDesktop/
├── bin/                    # Zkompilovaná spustitelná verze
│   └── KiCommander.exe     # Samostatný EXE soubor pro Windows
├── build/                  # Dočasné soubory pro kompilaci (ignorováno gitem)
├── Docs/                   # Dokumentace a plány vývoje
│   ├── implementation_plan.md
│   ├── task.md
│   └── walkthrough.md
├── src/                    # Zdrojové kódy aplikace
│   ├── config_manager.py   # Správa konfigurace a tajných klíčů
│   ├── file_model.py       # MVC Model pro reprezentaci dat (QAbstractTableModel)
│   ├── file_ops.py         # Logika pro souborové operace na pozadí
│   ├── fs_worker.py        # Asynchronní skener souborového systému
│   ├── main.py             # Hlavní vstupní bod a GUI logika
│   ├── navigation_utils.py # Pomocné funkce pro detekci disků a cest
│   └── style.qss           # Moderní stylový předpis pro design
├── .gitignore              # Definice ignorovaných souborů pro Git
├── run_build.bat           # Batch skript pro automatické sestavení EXE
├── secrets.json            # Lokální úložiště tajných klíčů (ignorováno gitem)
└── README.md               # Tato dokumentace
```

---

## 🛠️ Technologie a Architektura

- **Jazyk:** Python 3.11+
- **GUI Framework:** PySide6 (Qt for Python)
- **Architektura:** MVC (Model-View-Controller) – striktní oddělení dat od zobrazení.
- **Ikonky:** `qtawesome` (FontAwesome 5 Free)
- **Kompilace:** `PyInstaller` (vytváří samostatný .exe soubor)

---

## 🚀 Jak aplikaci spustit

### Ze zdrojových kódů

1. Nainstalujte závislosti:

   ```bash
   pip install PySide6 qtawesome pyinstaller
   ```

2. Spusťte aplikaci:

   ```bash
   python src/main.py
   ```

### Spustitelná verze (Windows)

Přejděte do složky `bin/` a spusťte soubor `KiCommander.exe`.

---

## ⌨️ Ovládání a zkratky

| Klávesa | Akce |
| :--- | :--- |
| **Enter** | Otevře složku nebo spustí soubor |
| **Tab** | Přepíná zaměření (focus) mezi panely |
| **Spacebar** | Vybere/označí soubor (multi-selection) |
| **F5** | Kopíruje označené položky do protějšího panelu |
| **F6** | Přesune označené položky do protějšího panelu |
| **F7** | Vytvoří nový adresář |
| **F8 / Del** | Smaže označené položky |
| **Ctrl + R** | Obnoví (refresh) seznam souborů |
| **Alt + F4** | Ukončí aplikaci |
| **Alt + Enter** | (Plánováno) Vlastnosti souboru |

---

## 🔐 Bezpečnost a Konfigurace

Aplikace používá `secrets.json` pro ukládání API klíčů a citlivých dat. Tento soubor není součástí Git repozitáře. Pro nové instalace použijte šablonu (pokud je dostupná) nebo vytvořte prázdný JSON objekt `{}`.
