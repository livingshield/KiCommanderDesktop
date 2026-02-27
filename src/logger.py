import logging
import logging.handlers
import sys
import os
import queue

def _get_log_dir() -> str:
    if getattr(sys, 'frozen', False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    log_dir = os.path.join(base, "logs")
    os.makedirs(log_dir, exist_ok=True)
    return log_dir

# Initialize root logger
def setup_logger():
    log_file = os.path.join(_get_log_dir(), "kicommander.log")
    
    # We use a RotatingFileHandler to cap logs at 5MB, keep 3 backups.
    file_handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=5*1024*1024, backupCount=3, encoding='utf-8'
    )
    
    # Format: [Time] [Level] [ThreadName] Message
    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] [%(threadName)s] %(message)s'
    )
    file_handler.setFormatter(formatter)
    
    # Console handler for development
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    
    # Thread-safe QueueHandler
    log_queue = queue.Queue(-1)
    queue_handler = logging.handlers.QueueHandler(log_queue)
    
    # The listener dispatches logs from the queue to the actual handlers
    listener = logging.handlers.QueueListener(
        log_queue, file_handler, console_handler
    )
    
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    # Clear existing handlers
    if root_logger.hasHandlers():
        root_logger.handlers.clear()
        
    root_logger.addHandler(queue_handler)
    listener.start()
    
    return listener

# Module-level access
log = logging.getLogger("KiCommander")
