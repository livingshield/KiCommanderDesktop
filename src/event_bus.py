from PySide6.QtCore import QObject, Signal

class EventBus(QObject):
    """
    Centralized Event Bus for decoupled communication between components.
    Components should emit signals here instead of calling methods on other components.
    """
    
    # --- Global Actions ---
    # Triggered by UI (Shortcut, Button, Context Menu), e.g., "copy", "move", "mkdir"
    action_requested = Signal(str)
    
    # Emitted when a specific file operation is requested explicitly (like drag & drop)
    file_operation_requested = Signal(str, list, str) # op_type, sources, target_path
    
    # --- UI Events ---
    # Emitted when the UI needs to display a message to the user
    show_message = Signal(str, str, str) # level (info/warn/err), title, message
    
    # Emitted when a panel needs to be refreshed (after operations finish)
    refresh_panels = Signal() 

    # --- Quick View ---
    # Emitted when selected file changes in active panel
    selection_changed = Signal(object) # file_info
    
    # Emitted to toggle Quick View panel visibility
    toggle_quick_view = Signal() 
    
    # Emitted to toggle the embedded Terminal tab/panel visibility
    toggle_terminal = Signal() 
    
    # --- Directory Tree ---
    # Emitted to toggle the global directory tree panel
    toggle_tree = Signal()
    
    # Emitted when active panel changes directory, so tree can sync
    directory_selected = Signal(str)
    
    # --- Appearance ---
    # Emitted when application icon is changed
    app_icon_changed = Signal(str)
    
    # Emitted when application theme is changed
    app_theme_changed = Signal(str)


# Global singleton instance
bus = EventBus()
