"""Tests for file operations – copy, move, delete in temporary directories."""
import os
import sys
import shutil
import tempfile
import pytest

# Ensure src/ is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


@pytest.fixture
def temp_tree(tmp_path):
    """Create a temporary directory tree for testing file operations."""
    # Create structure:
    #   tmp/
    #     src_dir/
    #       file1.txt  (content: "hello")
    #       file2.py   (content: "print('hi')")
    #       subdir/
    #         nested.md (content: "# Title")
    #     dest_dir/
    src_dir = tmp_path / "src_dir"
    src_dir.mkdir()
    (src_dir / "file1.txt").write_text("hello", encoding="utf-8")
    (src_dir / "file2.py").write_text("print('hi')", encoding="utf-8")
    sub = src_dir / "subdir"
    sub.mkdir()
    (sub / "nested.md").write_text("# Title", encoding="utf-8")

    dest_dir = tmp_path / "dest_dir"
    dest_dir.mkdir()

    return {"src": src_dir, "dest": dest_dir, "root": tmp_path}


class TestCopyOperations:
    def test_copy_file(self, temp_tree):
        src = temp_tree["src"] / "file1.txt"
        dest = temp_tree["dest"] / "file1.txt"
        shutil.copy2(str(src), str(dest))
        assert dest.exists()
        assert dest.read_text(encoding="utf-8") == "hello"

    def test_copy_preserves_content(self, temp_tree):
        src = temp_tree["src"] / "file2.py"
        dest = temp_tree["dest"] / "file2.py"
        shutil.copy2(str(src), str(dest))
        assert dest.read_text(encoding="utf-8") == "print('hi')"

    def test_copy_directory(self, temp_tree):
        src = temp_tree["src"]
        dest = temp_tree["dest"] / "src_copy"
        shutil.copytree(str(src), str(dest))
        assert dest.is_dir()
        assert (dest / "file1.txt").exists()
        assert (dest / "subdir" / "nested.md").exists()

    def test_copy_nonexistent_fails(self, temp_tree):
        with pytest.raises(FileNotFoundError):
            shutil.copy2(str(temp_tree["root"] / "nonexistent.txt"),
                        str(temp_tree["dest"]))


class TestMoveOperations:
    def test_move_file(self, temp_tree):
        src = temp_tree["src"] / "file1.txt"
        dest = temp_tree["dest"] / "file1.txt"
        shutil.move(str(src), str(dest))
        assert dest.exists()
        assert not src.exists()

    def test_move_preserves_content(self, temp_tree):
        src = temp_tree["src"] / "file2.py"
        dest = temp_tree["dest"] / "file2.py"
        shutil.move(str(src), str(dest))
        assert dest.read_text(encoding="utf-8") == "print('hi')"

    def test_move_directory(self, temp_tree):
        src = temp_tree["src"] / "subdir"
        dest = temp_tree["dest"] / "subdir"
        shutil.move(str(src), str(dest))
        assert dest.is_dir()
        assert (dest / "nested.md").exists()
        assert not src.exists()


class TestDeleteOperations:
    def test_delete_file(self, temp_tree):
        target = temp_tree["src"] / "file1.txt"
        assert target.exists()
        os.remove(str(target))
        assert not target.exists()

    def test_delete_directory(self, temp_tree):
        target = temp_tree["src"] / "subdir"
        assert target.is_dir()
        shutil.rmtree(str(target))
        assert not target.exists()

    def test_delete_nonexistent_fails(self, temp_tree):
        with pytest.raises(FileNotFoundError):
            os.remove(str(temp_tree["root"] / "ghost.txt"))

    def test_delete_file_doesnt_affect_siblings(self, temp_tree):
        target = temp_tree["src"] / "file1.txt"
        sibling = temp_tree["src"] / "file2.py"
        os.remove(str(target))
        assert sibling.exists()
