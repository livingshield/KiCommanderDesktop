# KiCommander Desktop - Initial Implementation

I have completed the foundation of KiCommander Desktop. The application is now functional with dual file panels and asynchronous directory scanning.

## Key Features Implemented

- **Double-Panel Layout:** Two independent file browsers allowing simultaneous view of different directories.
- **Asynchronous I/O:** File system scanning is performed in a background thread (`QThread`), ensuring the UI stays responsive even with large directories.
- **MVC Architecture:** A custom `FileModel` based on `QAbstractTableModel` handles data separation from the UI.
- **Navigation:** Navigation via double-click or **Enter key** is fully functional, including the `[..]` parent directory entry.
- **Panel Switching:** Use the **Tab key** to quickly switch focus between the left and right panels.
- **State Persistence:** The application now remembers your last visited directories, window size, and position using `QSettings`.
- **Menu Bar:** Added functional Menu Bar with "Files" and "Commands" (Exit, Search placeholders).
- **Configuration:** Integrated `ConfigManager` for secure API key handling.

## Changes Made

- **main.py:** Updated with `QSettings`, `eventFilter` for Enter key, and `keyPressEvent` for Tab navigation.
- **file_model.py:** Refined for better Qt compatibility.
- **config_manager.py:** Added to manage application secrets.
- **Docs/:** Moved all planning and task files to the `Docs/` directory.

## How to Run

1. Ensure you have the dependencies installed:

   ```bash
   pip install PySide6 qtawesome
   ```

2. Run the application:

   ```bash
   python main.py
   ```

## Next Steps

- **Phase 4:** Adding interactive file operations (Copy, Move, Delete) and multi-selection logic.
- **Phase 5:** Applying a comprehensive modern dark theme and final icons.
