import os
import sys
import threading
import traceback
from PySide6.QtWidgets import QWidget, QVBoxLayout, QPlainTextEdit, QMessageBox
from PySide6.QtCore import Qt, QProcess, Signal, Slot
from PySide6.QtGui import QFont, QTextCursor, QKeyEvent
import qtawesome as qta
from logger import log

class TerminalWidget(QWidget):
    """
    A simple integrated terminal emulator.
    Supports local shell (cmd.exe or bash) and SSH (via paramiko if configured).
    """
    
    # Custom signal to update text from background threads safely
    append_text_signal = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        self.term = QPlainTextEdit(self)
        self.term.setFont(QFont("Consolas", 10))
        self.term.setStyleSheet("background-color: #11111b; color: #a6adc8; border: 1px solid #313244; border-radius: 4px; padding: 4px;")
        
        self.layout.addWidget(self.term)
        
        self.append_text_signal.connect(self._safe_append)
        
        self._mode = "local" # local or ssh
        self._process = None
        self._ssh_client = None
        self._ssh_channel = None
        self._ssh_thread = None
        
        self.input_buffer = ""
        
        # Override keyPressEvent
        self.term.keyPressEvent = self.handle_key_press

    def stop(self):
        """Stops the underlying process or SSH channel."""
        if self._process:
            self._process.kill()
            self._process = None
        
        if self._ssh_channel:
            self._ssh_channel.close()
            self._ssh_channel = None
        
        if self._ssh_client:
            self._ssh_client.close()
            self._ssh_client = None

    def start_local(self, working_dir=None):
        """Starts a local terminal process."""
        self.stop()
        self._mode = "local"
        
        self.term.clear()
        self.input_buffer = ""
        
        self._process = QProcess(self)
        if working_dir and os.path.exists(working_dir):
            self._process.setWorkingDirectory(working_dir)
            
        self._process.readyReadStandardOutput.connect(self.handle_stdout)
        self._process.readyReadStandardError.connect(self.handle_stderr)
        self._process.finished.connect(self.handle_finished)

        # On Windows wait for powershell or cmd, on Unix bash
        if sys.platform == "win32":
            # Using cmd.exe
            self._process.start("cmd.exe")
        else:
            self._process.start("bash", ["-i"])

    def start_ssh(self, sftp_vfs):
        """Starts an SSH terminal using the established SFTPVFS credentials."""
        self.stop()
        self._mode = "ssh"
        
        self.term.clear()
        self.input_buffer = ""
        self.append_text_signal.emit(f"Connecting to SSH: {sftp_vfs.host}...\n")
        
        def run_ssh():
            try:
                import paramiko
                self._ssh_client = paramiko.SSHClient()
                self._ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                
                # Fetch port from sftp_vfs if available
                port = getattr(sftp_vfs, 'port', 22)
                
                self._ssh_client.connect(
                    sftp_vfs.host,
                    port=port,
                    username=sftp_vfs.user,
                    password=sftp_vfs.passwd
                )
                
                self._ssh_channel = self._ssh_client.invoke_shell()
                self.append_text_signal.emit("SSH connection established.\n")
                
                # Receive loop
                while True:
                    if self._ssh_channel.recv_ready():
                        data = self._ssh_channel.recv(4096)
                        if not data:
                            break
                        # decode safely
                        text = data.decode("utf-8", errors="replace")
                        # Basic ANSI strip (very raw)
                        import re
                        text = re.sub(r'\x1b\[.*?m', '', text)
                        self.append_text_signal.emit(text)
                        
                    if self._ssh_channel.exit_status_ready():
                        break
                        
            except Exception as e:
                log.error(f"SSH Term error: {e}")
                self.append_text_signal.emit(f"\n[SSH Error: {e}]\n")
                
        self._ssh_thread = threading.Thread(target=run_ssh, daemon=True)
        self._ssh_thread.start()

    def handle_stdout(self):
        if not self._process: return
        data = self._process.readAllStandardOutput().data()
        # Decode and strip basic ANSI if forced
        text = data.decode("utf-8", errors="replace")
        self.append_text_signal.emit(text)
        
    def handle_stderr(self):
        if not self._process: return
        data = self._process.readAllStandardError().data()
        text = data.decode("utf-8", errors="replace")
        self.append_text_signal.emit(text)
        
    def handle_finished(self):
        self.append_text_signal.emit("\n[Process exited]\n")

    @Slot(str)
    def _safe_append(self, text):
        cursor = self.term.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.term.setTextCursor(cursor)
        
        # We don't want to break the user's input buffer visually if they are typing,
        # but in a simple implementation we just append.
        self.term.insertPlainText(text)
        
        cursor.movePosition(QTextCursor.End)
        self.term.setTextCursor(cursor)
        
        # Scroll to bottom
        scrollbar = self.term.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def handle_key_press(self, event):
        """Intercept keystrokes to send to the running process."""
        # Allow standard Qt copy/paste if needed, but we intercept typing
        if event.matches(QKeyEvent.Copy):
            self.term.copy()
            return
            
        if event.matches(QKeyEvent.Paste):
            # Paste into our buffer
            clipboard = self.term.window().clipboard()
            text = clipboard.text()
            self._send_input(text)
            self.append_text_signal.emit(text)
            return

        key = event.key()
        
        if key == Qt.Key_Return or key == Qt.Key_Enter:
            self._send_input(self.input_buffer + "\n")
            self.input_buffer = ""
            # Do NOT emit newline here for SSH as the server usually echoes it back
            # For local CMD it echoes too
        elif key == Qt.Key_Backspace:
            if len(self.input_buffer) > 0:
                self.input_buffer = self.input_buffer[:-1]
                # Send backspace to terminal
                self._send_input("\b")
                # Visually delete it
                cursor = self.term.textCursor()
                cursor.deletePreviousChar()
        elif key == Qt.Key_C and (event.modifiers() & Qt.ControlModifier):
            # Ctrl+C
            if self._mode == "local" and self._process:
                # Can't easily send SIGINT to cmd via QProcess, but we can try byte
                self._send_input("\x03")
            elif self._mode == "ssh" and self._ssh_channel:
                self._send_input("\x03")
        else:
            char = event.text()
            if char:
                self.input_buffer += char
                # Wait for Enter to send?
                # Real terminals send char immediately, but local CMD expects line buffering via stdin.
                # Let's see:
                if self._mode == "ssh":
                    # SSH shells usually intercept immediately
                    self._send_input(char)
                    self.input_buffer = "" # Flush
                else:
                    # Echo locally
                    self.append_text_signal.emit(char)
                    
    def _send_input(self, text):
        if self._mode == "local" and self._process:
            self._process.write(text.encode("utf-8"))
        elif self._mode == "ssh" and self._ssh_channel:
            self._ssh_channel.send(text)
