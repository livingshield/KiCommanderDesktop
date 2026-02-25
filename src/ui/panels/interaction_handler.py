import os
from PySide6.QtCore import Qt, QEvent, QTimer, QItemSelectionModel
from PySide6.QtWidgets import QTabWidget, QApplication

class InteractionHandler:
    def __init__(self, panel):
        self.p = panel # FilePanel instance
        
        # RMB selection timer (Total Commander style)
        self._rmb_timer = QTimer(self.p)
        self._rmb_timer.setSingleShot(True)
        self._rmb_timer.timeout.connect(self._on_rmb_timer)
        self._rmb_pos = None
        self._rmb_index = None
        
        self._drag_start_pos = None

    def eventFilter(self, source, event):
        if event.type() == QEvent.KeyPress and source is self.p.table:
            # Enter to open
            if event.key() in (Qt.Key_Return, Qt.Key_Enter):
                index = self.p.table.currentIndex()
                if index.isValid():
                    self.p.on_double_click(index)
                    return True
            # Space to toggle selection (Total Commander style)
            elif event.key() == Qt.Key_Space:
                index = self.p.table.currentIndex()
                if index.isValid():
                    self.p.table.selectionModel().select(index, QItemSelectionModel.Toggle | QItemSelectionModel.Rows)
                    self.p.table.setCurrentIndex(self.p.model.index(index.row() + 1, 0))
                    return True
            # Ctrl + Up for New Tab: Open current path in a new tab
            if event.key() == Qt.Key_Up and (event.modifiers() & Qt.ControlModifier):
                p = self.p.current_path if not self.p._vfs else self.p._vfs_inner
                tw = self.p.parent()
                while tw and not isinstance(tw, QTabWidget):
                    tw = tw.parent()
                if tw:
                    self.p.window().add_tab(tw, p)
                return True
            elif event.key() == Qt.Key_F2:
                index = self.p.table.currentIndex()
                if index.isValid():
                    file_info = self.p.model.get_file(index.row())
                    if file_info and file_info.name != "..":
                        self.p.rename_file(file_info)
                        return True
            # Escape to deselect all or close filter
            elif event.key() == Qt.Key_Escape:
                if self.p.filter_visible:
                    self.p.toggle_filter()
                else:
                    self.p.table.selectionModel().clearSelection()
                return True
            # Alt + Down for History
            elif event.key() == Qt.Key_Down and (event.modifiers() & Qt.AltModifier):
                self.p.show_history()
                return True
        
        if event.type() == QEvent.FocusIn:
            self.p.got_focus.emit(self.p)
            return False

        # --- Total Commander Style Mouse Handling ---
        elif event.type() == QEvent.MouseButtonPress and source is self.p.table.viewport():
            self.p.got_focus.emit(self.p)
            index = self.p.table.indexAt(event.position().toPoint())
            if event.button() == Qt.RightButton:
                if index.isValid():
                    self._rmb_index = index
                    self._rmb_pos = event.position().toPoint()
                    self._rmb_timer.start(500)
                    return True
            elif event.button() == Qt.MiddleButton:
                if index.isValid():
                    f = self.p.model.get_file(index.row())
                    if f and f.is_dir and f.name != "..":
                        p = f.full_path
                        tw = self.p.parent()
                        while tw and not isinstance(tw, QTabWidget):
                            tw = tw.parent()
                        if tw:
                            self.p.window().add_tab(tw, p)
                        return True
            elif event.button() == Qt.LeftButton:
                self._drag_start_pos = event.position().toPoint()
                if index.isValid():
                    # If item NOT selected, make it a focal selection
                    if not self.p.table.selectionModel().isSelected(index):
                        self.p.table.selectionModel().clearSelection()
                        self.p.table.selectionModel().select(index, QItemSelectionModel.Select | QItemSelectionModel.Rows)
                        self.p.table.setCurrentIndex(index)
                    else:
                        self.p.table.setCurrentIndex(index)
                    # Don't return True, we need this for DND
                    return False

        elif event.type() == QEvent.MouseMove and source is self.p.table.viewport():
            pos = event.position().toPoint()
            # 1. Check for Drag Start (Left Button)
            if (event.buttons() & Qt.LeftButton) and self._drag_start_pos:
                if (pos - self._drag_start_pos).manhattanLength() >= QApplication.startDragDistance():
                    self.p._start_manual_drag()
                    self._drag_start_pos = None
                    return True

            # 2. Check for RMB Paint Selection
            if self._rmb_pos:
                if (pos - self._rmb_pos).manhattanLength() > 5:
                    self._rmb_timer.stop()
                    index = self.p.table.indexAt(pos)
                    if index.isValid():
                        self.p.table.selectionModel().select(index, QItemSelectionModel.Select | QItemSelectionModel.Rows)
                    return True

        elif event.type() == QEvent.MouseButtonRelease and source is self.p.table.viewport():
            if event.button() == Qt.RightButton:
                if self._rmb_timer.isActive():
                    self._rmb_timer.stop()
                    if self._rmb_index and self._rmb_index.isValid():
                        self.p.table.selectionModel().select(self._rmb_index, QItemSelectionModel.Toggle | QItemSelectionModel.Rows)
                self._rmb_pos = None
                self._rmb_index = None
                return True
            elif event.button() == Qt.LeftButton:
                self._drag_start_pos = None

        # --- Drag and Drop Handling (Accept from both table and its viewport) ---
        elif event.type() == QEvent.DragEnter and source in (self.p.table, self.p.table.viewport()):
            if event.mimeData().hasUrls():
                event.acceptProposedAction()
                return True
        elif event.type() == QEvent.DragMove and source in (self.p.table, self.p.table.viewport()):
            event.acceptProposedAction()
            return True
        elif event.type() == QEvent.Drop and source in (self.p.table, self.p.table.viewport()):
            urls = event.mimeData().urls()
            sources = [u.toLocalFile() for u in urls if u.isLocalFile()]
            if not sources:
                # Might be internal VFS paths
                sources = [u.toString() for u in urls]
                
            if sources:
                target_path = self.p.current_path
                if self.p._vfs:
                    target_path = self.p._vfs_inner
                
                # If dropped on a specific folder, use it as target
                index = self.p.table.indexAt(event.position().toPoint())
                if index.isValid():
                    row = index.row()
                    if self.p.filter_visible: row = self.p.proxy.mapToSource(index).row()
                    f = self.p.model.get_file(row)
                    if f and f.is_dir and f.name != "..":
                        target_path = f.full_path if not self.p._vfs else os.path.join(self.p._vfs_inner, f.name)

                self.p.window().actions.run_op('copy', sources, target_path)
                event.acceptProposedAction()
                return True

        return False

    def _on_rmb_timer(self):
        """Called when RMB is held long enough to show context menu."""
        if self._rmb_pos:
            self.p.menu_builder.build_and_show(self._rmb_pos)
            self._rmb_pos = None
            self._rmb_index = None
