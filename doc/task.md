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

## Aktuální verze: 1.8.0 (Stable Refactored)

- **Novinky:**
  - Plnohodnotný **Multi-Rename Tool** s podporou regulárních výrazů a šablon.
  - **Flexibilní záložky (Tabs)** pro oba panely s možností zamykání.
  - **Synchronizace složek** s vizuálním náhledem změn a asynchronním provedením.
  - **Vylepšený prohlížeč (F3)**: Renderování Markdownu a přehrávání videa/audia.
  - **SSH Command Line**: Možnost spouštět příkazy přímo na vzdáleném serveru v SFTP panelu.
- **Design:** Catppuccin Mocha s plynulými animacemi a moderními prvky.
