import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from PySide6.QtWidgets import QApplication
app = QApplication.instance() or QApplication(sys.argv)

from queue_manager import QueueManager, QueueItem

@pytest.fixture(autouse=True)
def mock_qthread(mocker):
    # Prevent real threads from spinning up during tests
    mocker.patch('queue_manager.QThread')
    mocker.patch('queue_manager.VfsOperationWorker')
    
@pytest.fixture
def queue_manager():
    # Reset singleton for clean slate
    QueueManager._instance = None
    qm = QueueManager.instance()
    # Ensure items are empty
    qm.items = []
    return qm

def test_singleton(queue_manager):
    qm2 = QueueManager.instance()
    assert queue_manager is qm2

def test_add_to_queue(queue_manager, mocker):
    mocker.patch.object(queue_manager, '_check_next')
    
    item_id = queue_manager.add_to_queue("copy", ["/src/a.txt"], "/dest")
    
    assert len(queue_manager.items) == 1
    item = queue_manager.items[0]
    assert item.id == item_id
    assert item.op_type == "copy"
    assert item.sources == ["/src/a.txt"]
    assert item.target_path == "/dest"
    assert item.status == "Waiting"
    
    # Ensure _check_next was called to start the item
    queue_manager._check_next.assert_called_once()

def test_remove_item(queue_manager):
    item_id = queue_manager.add_to_queue("move", ["/test"], "/dest")
    
    # Assuming the queue wasn't immediately started due to test env, or we can just mock
    # the thread starting. Let's force status to Waiting to test removal.
    queue_manager.items[0].status = "Waiting"
    
    queue_manager.remove_item(item_id)
    assert len(queue_manager.items) == 0

def test_pause_queue(queue_manager, mocker):
    mocker.patch.object(queue_manager, '_check_next')
    
    queue_manager.pause_queue(True)
    assert queue_manager.paused is True
    # Should not call _check_next when pausing
    queue_manager._check_next.assert_not_called()
    
    queue_manager.pause_queue(False)
    assert queue_manager.paused is False
    # Should call _check_next when unpausing
    queue_manager._check_next.assert_called_once()

def test_on_progress(queue_manager):
    item_id = queue_manager.add_to_queue("copy", ["/src"], "/dest")
    
    queue_manager._on_progress(item_id, 50, "test.txt")
    
    item = queue_manager.items[0]
    assert item.progress == 50
    assert item.current_file == "test.txt"

def test_on_finished(queue_manager, mocker):
    item_id = queue_manager.add_to_queue("copy", ["/src"], "/dest")
    
    # Mock QThread to avoid actual thread management errors
    mocker.patch.object(queue_manager, 'current_thread')
    mocker.patch.object(queue_manager, '_check_next')
    
    # Simulate completion
    queue_manager._on_finished(item_id, True, "Success")
    
    item = queue_manager.items[0]
    assert item.status == "Completed"
    assert item.progress == 100
    assert queue_manager.current_thread is None
    assert queue_manager.current_worker is None
    queue_manager._check_next.assert_called_once()

def test_on_finished_error(queue_manager, mocker):
    item_id = queue_manager.add_to_queue("copy", ["/src"], "/dest")
    
    mocker.patch.object(queue_manager, 'current_thread')
    mocker.patch.object(queue_manager, '_check_next')
    
    # Simulate error
    queue_manager._on_finished(item_id, False, "Access Denied")
    
    item = queue_manager.items[0]
    assert item.status == "Error"
    assert item.error_msg == "Access Denied"
