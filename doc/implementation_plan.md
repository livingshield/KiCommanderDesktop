# KiCommander – Technická Dokumentace Architektury (v1.8.0)

Tento dokument slouží jako technická reference pro architekturu aplikace ve verzi 1.8.0 (Refactored).

## 1. Jádro a VFS (Virtual File System)

Jádro aplikace je postaveno na asynchronním modelu, který odděluje UI vlákno od operací se souborovým systémem.

### Inkrementální načítání (Performance Pack)

- **Chunking**: `ScanWorker` a `VfsWorker` nečekají na načtení celého adresáře. Emitují signál `chunk_filled` každých 100 nalezených položek.
- **Model Integration**: `FileModel` využívá `beginInsertRows` pro postupné přidávání dat. To umožňuje uživateli vidět první výsledky v milisekundách i u složek s 10 000+ soubory.

### VFS Provideři

- **SFTPVFS**: Využívá `paramiko` pro SSH přenosy.
- **SMBVFS**: Využívá `pysmb`. Podporuje Windows Shares přes IP i hostname.
- **ArchiveVFS**: Read-only přístup k ZIP/TAR souborům bez nutnosti celého rozbalení.

## 2. Správa operací (`vfs_ops.py`)

Centrální worker pro souborové operace.

- **Cross-Platform Transfer**: Implementuje logiku pro kopírování mezi různými VFS typy (např. FTP -> SMB) pomocí dočasných temp souborů.
- **Overwrite Resolver**: Detekuje konflikty jmen a přes signály vyvolává UI srovnávací dialog, který vrací instrukce (Overwrite/Skip/Cancel).
- **Queue Integration**: Podpora pro asynchronní řazení operací přes `QueueManager`. Operace jsou spouštěny sekvenčně pro minimalizaci zátěže disku (I/O optimalizace).

## 3. Konfigurace a Persistence

- **Settings System**: Dialog `settings_dialog.py` ukládá cesty k externím editorům a globální flagy (confirm_delete) do systémového registru/plistu přes `QSettings`.
- **Connection Manager**: Serializace ověřených připojení do `data/connections.json`.
- **Theme Engine**: Komplexní stylopis `style.qss` definující Catppuccin Mocha paletu pro všechny Qt Widgety (včetně QTabWidget, QComboBox, QSpinBox atd.).

## 4. Build a Distribuce

- **Specifikace**: `KiCommander.spec` je navržen jako multiplatformní. Automaticky detekuje `sys.platform` a přizpůsobuje ikony a strukturu balíčku.
- **CI/CD**: GitHub Actions workflow (`build.yml`) testuje a kompiluje kód paralelně na Windows, Ubuntu a macOS při každém pushi.

## 5. Externí utility

- **Diff Tool**: Side-by-side implementace založená na `difflib.ndiff` se synchronizovanými scrollbary.
- **Duplicate Scanner v2**: Třífázový sken s novým UI. Podporuje řazení výsledků, filtraci podle přípon a interaktivní výběr k smazání.

## 6. Clipboard a Systémová Integrace

- **System Clipboard**: Plná integrace s `QMimeData` a `preferredDropEffect`. Podporuje Copy/Cut/Paste mezi KiCommanderem a Průzkumníkem Windows.
- **Archivace**: Modul `archiver.py` pro asynchronní tvorbu ZIP a 7z archivů. RAR je podporován v režimu read-only přes VFS.

## 7. Architektura a Modularita (v1.8.0 Updates)

V verzi 1.8.0 proběhla zásadní refaktorizace směrem k "Separation of Concerns".

### Action Manager (`action_manager.py`)

Centrální mozek aplikace. Všechny operativní metody (`op_*`) byly vyjmuty z hlavního okna `KiCommander`.

- **Zodpovědnost**: Provádění souborových operací, správa síťových připojení, spouštění dialogů (Search, Sync, Rename) a koordinace VFS workerů.
- **Signal Handling**: Spravuje zpětnou vazbu z fronty (`QueueManager`) a VFS vláken.

### Dekompozice FilePanelu

Třída `FilePanel` byla rozdělena na menší, specializované komponenty pro lepší udržovatelnost:

- **InteractionHandler**: Zapouzdřuje veškeré vstupní události (klávesnice, myš, Drag & Drop). Implementuje "Total Commander styl" výběru pravým tlačítkem a paint selection.
- **ContextMenuBuilder**: Dynamicky generuje kontextové menu pro soubory, složky i prázdné oblasti panelu.
- **Selection Logic**: Pravé tlačítko myši je vyhrazeno pro označování (včetně tažení/paint selection). Kontextové menu je vyvoláno dlouhým stiskem (>0.5s) nebo přes `InteractionHandler`.

### Drag & Drop

Implementováno ruční spouštění `QDrag` v `InteractionHandler` s vynucenou operací kopírování pro bezpečnost dat při přenosu na pracovní plochu.

## 8. Systém fronty (Queue Manager)

Zaveden v v1.7 pro správu pozadí dlouhotrvajících operací.

- **Singleton Pattern**: `QueueManager` udržuje globální seznam úloh.
- **Progress Tracking**: UI komponenta `TransferManagerWidget` v reálném čase vizualizuje postup, rychlost a zbývající čas úloh ve frontě.

## 9. Navigace a Vyhledávání (v1.7+)

- **Interactive Breadcrumbs**: Rozklad cesty na klikatelné komponenty v `navigation_utils.py`. Automatická synchronizace s VFS cestami.
- **Directory History**: Per-panel implementace `deque(maxlen=20)` pro bleskový návrat.
- **Advanced Search**: Rozšíření o VFS podporu. Prohledávání archivů a síťových disků využívá temp extrakci do paměti/disku pro Grep operace.
