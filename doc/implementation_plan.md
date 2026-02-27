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

## 10. UI Polish a Vizualizace (v1.8.x)

- **Frameless Resizability**: Implementace vlastní logiky pro změnu velikosti bezrámových oken. Detekce okrajů (`_get_edge`) a dynamická aktualizace kurzorů (`setCursor(Qt.SizeHorCursor)` atd.).
- **Visual Grips**: Integrace `QSizeGrip` do všech modálních dialogů pro vizuální vedení uživatele.
- **Preview Engine**: Rozšíření prohlížeče (F3) o `Pillow` a `pillow-heif` pro nativní podporu Apple HEIC a moderních WEBP formátů.

## Enterprise Architectural Hardening (v1.9.0 Plan - Completed)

- **Robustní Testovací Infrastruktura**: Zaveden `pytest` a mockování QThread vláken pro asynchronní manažery.
- **Parametry & Typování**: Projekt je validován přes `Mypy` s fixními VFS a paramiko / 7z rozhraními.
- **Logování**: Zaveden `QueueHandler` logger pro Thread-Safe odchytávání výjimek z dělníků.
- **Event Bus Pobočka**: Připraven objekt EventBus pro decouple.

## Architecture Integration & Risk Mitigation (v2.0.0 - Phase 26 - Plan)

> [!WARNING]
> Během kompletní kontroly aplikace pro verzi 1.9 byly identifikovány závažné "slepé body" a nedostatečně propojené architektury. Tyto body představují technický dluh, který ohrožuje stabilitu aplikace při dalším rozšiřování.

### Identified Risks & Weak Points

1. **Unused EventBus (Mrtvý kód) & Těsná vazba (Tight Coupling)**
   - Nově vytvořený `event_bus.py` není nikde napojen.
   - `action_manager.py` je stále Monolit (God Object - ~600 řádků), který ručně importuje desítky UI dialogů a je spouštěn přímými handlery z `file_panel.py`.
   - **Riziko**: Kód je těžko testovatelný a UI nelze snadno modifikovat bez rozbití logiky.

2. **Incomplete Logger Adoption (Částečné logování)**
   - VFS moduly používají nový logger, ale kritické komponenty jako `action_manager.py`, `queue_manager.py`, `archiver.py` a `fs_worker.py` logger dosud nevyužívají naplno.
   - **Riziko**: Pokud spadne asynchronní kopírování kvůli nečekaným chybám disku, v logu nebude stopa.

3. **Silent Failures (`except: pass`)**
   - Různé moduly (`archive_vfs.py`, `sftp_vfs.py`, `search_dialog.py`) aktivně "polykají" chyby pomocí `except: pass`.
   - **Riziko**: Poškozené archivy nebo dočasné neočekávané síťové pády nevygenerují exception a selžou tiše, což způsobí zmatení uživatele.

### Proposed Solutions (Next Steps)

#### 1. Implementace Event Bus & Demontáž Monolitu

- Přepsat volání z `FilePanel`, `ContextMenu` a klávesových zkratek, aby pouze vysílaly signály (např. `bus.file_operation_requested.emit()`).
- Refaktorovat `ActionManager`, aby pouze naslouchal na `EventBus` a neobsahoval žádnou logiku vykreslování UI.

#### 2. Centralizace a vynucení Loggování

- Nahradit zbývající potlačené výjimky (`except: pass`) strukturou `except Exception as e: log.error(f"Error ctx: {e}")`.
- Napojit logování na `QueueManager` a zrušit používání print() / debug hlášek v `search_dialog.py` a `fs_worker.py`.

#### 3. Testovací pokrytí Event Busu

- Po zapojení event busu garantovat, že staré unit testy a fronty reagují na simulované signály z Event Busu.

## Verification Plan pro Phase 26

- Spustit pytest nad celým nově odpojeným systémem.
- Zapnout Event Bus a demonstrovat volání bez UI referencí.
- Zkontrolovat `logs/kicommander.log`, zda chytá pády z `archive_vfs.py` při simulaci rozbitých zipů.
