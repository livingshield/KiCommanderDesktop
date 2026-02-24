# KiCommander Desktop - Initial Implementation

I have completed the foundation of KiCommander Desktop. The application is now functional with dual file panels and asynchronous directory scanning.

## Key Features Implemented

- **Double-Panel Layout:** Two independent file browsers allowing simultaneous view of different directories.
- **Asynchronous I/O:** File system scanning is performed in a background thread (`QThread`), ensuring the UI stays responsive.
- **MVC Architecture:** A custom `FileModel` based on `QAbstractTableModel` handles data separation.
- **Navigation:** Navigation via double-click or **Enter key** is fully functional.
- **Selection:** Multi-selection supported via **Spacebar** (Total Commander style).
- **File Operations:** Fully functional **F5 (Copy)**, **F6 (Move)**, **F7 (New Folder)**, and **F8 (Delete)**.
- **Command Line:** Integrated command bar for executing system commands in the current directory.
- **Modern UI:** Premium dark theme with **Catppuccin-inspired** colors and high-quality **FontAwesome** icons.
- **File Icons:** Specific icons for folders, archives, executables, and images with color coding.
- **State Persistence:** Remembers directories, window size, and position via `QSettings`.
- **Configuration:** Secure API key management with Git protection.

## Changes Made

- **src/main.py:** Complete application logic with UI and event handling.
- **src/file_model.py:** Enhanced with icon support and color coding.
- **src/file_ops.py:** Dedicated logic for background file operations (copy, move, delete).
- **src/style.qss:** Modern CSS-like styling for a premium look.
- **src/fs_worker.py:** Threaded directory scanner.

## How to Run

1. Ensure you have the dependencies installed:

   ```bash
   pip install PySide6 qtawesome
   ```

2. Run the application from the root:

   ```bash
   python src/main.py
   ```

## Next Steps

- **Phase 4:** Adding interactive file operations (Copy, Move, Delete) and multi-selection logic.
- **Phase 5:** Applying a comprehensive modern dark theme and final icons.
