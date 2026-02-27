# KiCommander Desktop Task List - FINÁLNÍ STAV

- [x] Phase 1: Planning and Setup
- [x] Phase 2: Core Architecture & Async Reading
- [x] Phase 3: Navigation & State Persistence
- [x] Phase 4: Network Protocols (VFS Expansion)
  - [x] 4.1 SFTP/SSH Provider
  - [x] 4.2 SMB Provider
  - [x] 4.3 FTP Provider (Sjednoceno)
  - [x] 4.4 Connection Manager (Spuštěno)
  - [x] 4.5 VFS File Operations (Copy/Move/Delete)
- [x] Phase 5: Performance Optimization
  - [x] 5.1 Inkrementální načítání pro lokální FS
  - [x] 5.2 Inkrementální načítání pro VFS
- [x] Phase 6: Multi-platform Distribution
  - [x] 6.1 GitHub Actions (Win/Linux/Mac)
  - [x] 6.2 Platform-specific Tweaks (Specifikace icons/app bundle)
- [x] Phase 7: UI Customization & Settings
  - [x] 7.1 Settings Dialog
  - [x] 7.2 Externí editor (F4 Integration)
  - [x] 7.3 Deletion confirmation toggles
- [x] Phase 8: File Comparison (Diff Tool)
- [x] Phase 9: Duplicate Finder
- [x] Phase 10: Batch Operation Support (Hromadné mazání)
- [x] Phase 11: System Clipboard Integration (Ctrl+C, Ctrl+X, Ctrl+V)
- [x] Phase 12: Archiving Support (ZIP, 7z creation; RAR read-only)
- [x] Phase 13: Drag & Drop and TC-style Interaction
- [x] Phase 14: Queue Manager (Background operations)
- [x] Phase 15: Navigation Enhancements
- [x] Phase 16: Advanced Search (Grep, VFS support)
- [x] Phase 17: Duplicate Finder Redesign (v2 UI, Sorting, Extensions)
- [x] Phase 18: Multi-Rename Tool (UI, Templating, Regex, Queue) `1.8.0`
- [x] Phase 19: Folder Tabs (QTabWidget, Lock, Persistence) `1.8.0`
- [x] Phase 20: Directory Synchronization (Compare, Visual Matrix) `1.8.0`
- [x] Phase 21: Preview Improvements (Markdown, Media Player) `1.8.0`
- [x] Phase 23: Architectural Refactoring v1.8.0
  - [x] Extract ActionManager (Decouple logic from main window)
  - [x] FilePanel Decomposition (InteractionHandler & ContextMenuBuilder)
  - [x] Cleanup and Import Consolidation
- [x] Phase 24: UI Polish & Preview Fixes (v1.8.1)
  - [x] Fix F3 Preview (Text, Image, HEIC, WEBP)
  - [x] Implement Resizable Frameless Dialogs
  - [x] Add SizeGrips (Dots) to all major dialogs
  - [x] Add Cursor feedback for resizing
- [x] Phase 25: Enterprise Architectural Hardening (v1.9.0)
  - [x] 25.1 Zavedení robustní testovací infrastruktury (pytest, pytest-qt, mocking)
  - [x] 25.2 Striktní typování (Type Hinting & Mypy integrace)
  - [x] 25.3 Thread-Safe Logovací Systém (QueueHandler pro QThread)
  - [x] 25.4 Event Bus (Kompletní decoupling UI od logiky přes signály)

- [x] Phase 26: Architecture Integration & Risk Mitigation (v2.0.0)
  - [x] 26.1 EventBus Integration: Odpojení `FilePanel` od `ActionManager` monolitických volání pomocí custom signálů.
  - [x] 26.2 Queue & Action Refactor: Centralizace odchytu signálů v `ActionManageru` a zamezení přímým importům dialogů.
  - [x] 26.3 Unified Logging: Odstranění všech volných `print()` a logování přes centrální sběrnici v klíčových filech.
  - [x] 26.4 Exception Mitigation: Oprava tichých pádů `except: pass` aspoň na úroveň chyby v logu (archive_vfs, sftp_vfs atd.).
  - [x] 26.5 Aktualizace testů a finalizace V2 verze.

- [x] Phase 27: UX & Feature Expansion (v2.1.0)
  - [x] 27.1 Integrovaný Quick View Panel (Náhledový panel): Implementace bočního panelu pro okamžitý náhled souborů.
  - [x] 27.2 Rozšířené Povolení a Vlastníci (Permissions & Ownership)
  - [x] 27.3 Vestavěný Terminálový Emulátor / SSH Konzolový Tab
  - [x] 27.4 Directory Tree (Stromová Navigace) nad panely
  - [x] 27.5 Icon Preview (Náhled ikon v nastavení)

- [x] Phase 28: Advanced Search & Bookmarks (v2.2.0)
  - [x] 28.1 Perzistentní okno vyhledávání (Výsledky v samostatném tabu)
  - [x] 28.2 Správce záložek / Přenastavení oblíbených položek
  - [x] 28.3 Systém témat (Možnost přepnout Mocha/Macchiato/Frappé/Latte)
  - [x] 28.4 Cloud Drive Integration (Základní podpora pro Google Drive VFS)

- [ ] Phase 29: Advanced File Operations & Metadata (v2.3.0)
  - [ ] 29.1 Bulk Atributy a Časová razítka (Změna data vytvoření/úpravy v GUI)
  - [ ] 29.2 File Checksums (Verifikace a generování MD5, SHA1, SHA256 v dialogu Vlastnosti)
  - [ ] 29.3 File Splitting & Combining (Rozdělování a spojování velkých souborů)
  - [ ] 29.4 Integrovaný Hex/Binary Viewer v Quick View Panelu

## Aktuální verze: 2.2.0 (Search & Themes Update)

- **Novinky:**
  - Architektura poháněná **EventBus** odděluje UI okna a logických managerů.
  - Plnohodnotné **Mypy Type Hinting** bez kritických chyb (úroveň striktních chyb `0`).
  - **Asynchronní Logger** s frontou proti deadlockům.
  - Testovací integrace přes `pytest` a Mock.
  - Všechny tiché chyby aplikací VFS řešeny přes error handling.
  - Ostré nasazení pro Google Drive a FTP klienta.
  - Persistentní VFS struktura uvnitř vyhledávání.
  - Rychlý rozcestník pomocí BookmarksDialog manageru.
  - Dynamické `Catppuccin` barevné témata.
- **Design:** Catppuccin palety s plynulými animacemi a moderními prvky.
