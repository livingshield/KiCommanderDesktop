"""
Plugin Manager – discovers and loads plugins from the plugins/ directory.
Each plugin is a Python module exporting:
  - name: str          – display name
  - menu_text: str     – text shown in Commands menu
  - action(selected_files: list[str], panel) -> None  – the action to run
"""
import os
import importlib
import importlib.util
import sys
from logger import log


class PluginInfo:
    """Holds info about a discovered plugin."""
    def __init__(self, name, menu_text, action_fn, module):
        self.name = name
        self.menu_text = menu_text
        self.action = action_fn
        self.module = module


def discover_plugins(plugins_dir: str) -> list[PluginInfo]:
    """
    Scan plugins_dir for Python files that export the plugin interface.
    Returns list of PluginInfo.
    """
    plugins: list[PluginInfo] = []
    if not os.path.isdir(plugins_dir):
        return plugins

    for fname in sorted(os.listdir(plugins_dir)):
        if fname.startswith("_") or not fname.endswith(".py"):
            continue
        fpath = os.path.join(plugins_dir, fname)
        mod_name = f"plugin_{fname[:-3]}"

        try:
            spec = importlib.util.spec_from_file_location(mod_name, fpath)
            if spec is None or spec.loader is None:
                continue
            mod = importlib.util.module_from_spec(spec)
            sys.modules[mod_name] = mod
            spec.loader.exec_module(mod)

            # Validate plugin interface
            name = getattr(mod, "name", None)
            menu_text = getattr(mod, "menu_text", None)
            action_fn = getattr(mod, "action", None)

            if name and menu_text and callable(action_fn):
                plugins.append(PluginInfo(name, menu_text, action_fn, mod))
        except Exception as e:
            log.error(f"[PluginManager] Failed to load {fname}: {e}")

    return plugins
