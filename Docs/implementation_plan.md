# KiCommander Desktop Implementation Plan

Project goal: Create a robust, production-ready Python desktop application inspired by Total Commander using PySide6.

## Proposed Changes

### Tech Stack Refinement

- **GUI Framework:** PySide6 (Qt for Python).
- **Concurrent I/O:** `QThread` and `QRunnable` for non-blocking file system scanning.
- **Architecture:** Strict MVC using `QAbstractTableModel` and `QTableView`.
- **Persistence:** `QSettings` for window dimensions, last paths, and user preferences.
- **Monitoring:** `QFileSystemWatcher` for automated UI refreshes on external changes.

### Revised Phases

### Phase 2: Core Architecture & Async Reading

- **Model:** Implement `FileModel(QAbstractTableModel)` to handle data (Name, Ext, Size, Date).
- **Async Scanner:** Implement a worker class that uses `QThread` to scan directories without freezing the GUI.
- **View:** Set up the main window with two `QTableView` widgets.
- **Error Handling:** Implement graceful handling of "Access Denied" or disk disconnection errors during the scanning phase.

### Phase 3: Navigation & State Persistence

- **Navigation logic:** Handle double-click/Enter to drill down and `..` to go up.
- **Selection:** Implement keyboard-based navigation (arrows) and focus management between panels (Tab).
- **Persistence:** Use `QSettings` to save and restore:
  - Last visited directory for both panels.
  - Column widths and window geometry.
- **UI:** Implement the menu bar and the bottom informational bars.

### Phase 4: Interactive Operations (F3-F8)

- **Multi-selection:** Implement marking files (e.g., via Spacebar or Insert).
- **File Ops:** Implement F3 (View), F4 (Edit), F5 (Copy), F6 (Move), F7 (NewFolder), F8 (Delete).
- **Shell:** Add a command line input for quick shell executions in the current path.

### Phase 5: Polishing & Live Updates

- **FS Watcher:** Attach `QFileSystemWatcher` to current visible directories to refresh the view on changes.
- **Styling:** Apply a modern QSS theme with high-quality icons.
- **Unit Testing:** Focus tests on `FileModel` and async worker logic.

## Verification Plan

### Automated Tests

- Test `FileModel` sorting and formatting logic.
- Verify thread safety between the async scanner and the UI model.

### Manual Verification

- Test navigation in "heavy" directories like `C:\Windows`.
- Verify that permissions errors are caught and reported without crashing the app.
- Check that the application restores its state correctly after restart.
