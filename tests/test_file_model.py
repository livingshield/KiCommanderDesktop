"""Tests for FileModel – sorting, data access, update logic."""
import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
app = QApplication.instance() or QApplication(sys.argv)

from file_model import FileModel
from fs_worker import FileInfo


def make_file(name, ext, size_bytes, mtime, is_dir=False):
    """Helper to create a FileInfo object."""
    return FileInfo(
        name=name,
        ext=ext,
        size="<DIR>" if is_dir else f"{size_bytes} B",
        date="01.01.2025 12:00",
        is_dir=is_dir,
        full_path=f"/fake/{name}",
        size_bytes=size_bytes,
        mtime=mtime,
    )


@pytest.fixture
def sample_files():
    return [
        make_file("..", "", 0, 0, is_dir=True),
        make_file("docs", "", 0, 1000, is_dir=True),
        make_file("src", "", 0, 2000, is_dir=True),
        make_file("readme.md", "md", 1024, 3000),
        make_file("main.py", "py", 4096, 4000),
        make_file("data.csv", "csv", 512, 1500),
    ]


@pytest.fixture
def model(sample_files):
    m = FileModel(sample_files)
    return m


class TestFileModelBasics:
    def test_row_count(self, model, sample_files):
        assert model.rowCount() == len(sample_files)

    def test_column_count(self, model):
        assert model.columnCount() == 6

    def test_headers(self, model):
        for i, name in enumerate(["Name", "Ext", "Size", "Date", "Attr", "Owner"]):
            header = model.headerData(i, Qt.Horizontal)
            assert name in header

    def test_get_file_valid(self, model):
        fi = model.get_file(0)
        assert fi is not None

    def test_get_file_invalid(self, model):
        fi = model.get_file(999)
        assert fi is None

    def test_get_file_negative(self, model):
        fi = model.get_file(-1)
        assert fi is None

    def test_data_name_column(self, model):
        # Row 0 should be ".." after sort
        idx = model.index(0, 0)
        assert model.data(idx, Qt.DisplayRole) == ".."

    def test_data_invalid_index(self, model):
        from PySide6.QtCore import QModelIndex
        assert model.data(QModelIndex(), Qt.DisplayRole) is None


class TestFileModelSorting:
    def test_dotdot_always_first(self, model):
        """'..' should always be the first row regardless of sort."""
        model.sort(0, Qt.AscendingOrder)
        fi = model.get_file(0)
        assert fi.name == ".."

        model.sort(0, Qt.DescendingOrder)
        fi = model.get_file(0)
        assert fi.name == ".."

    def test_dirs_before_files(self, model):
        """Directories should come after '..' but before files."""
        model.sort(0, Qt.AscendingOrder)
        # After sort: .., dirs (docs, src), files (data.csv, main.py, readme.md)
        fi_1 = model.get_file(1)
        fi_2 = model.get_file(2)
        assert fi_1.is_dir, f"Expected dir at row 1, got {fi_1.name}"
        assert fi_2.is_dir, f"Expected dir at row 2, got {fi_2.name}"

    def test_sort_name_ascending(self, model):
        model.sort(0, Qt.AscendingOrder)
        dirs = [model.get_file(i) for i in range(1, 3)]
        files = [model.get_file(i) for i in range(3, 6)]
        
        # Dirs sorted alphabetically
        assert dirs[0].name == "docs"
        assert dirs[1].name == "src"
        
        # Files sorted alphabetically
        assert files[0].name == "data.csv"
        assert files[1].name == "main.py"
        assert files[2].name == "readme.md"

    def test_sort_name_descending(self, model):
        model.sort(0, Qt.DescendingOrder)
        dirs = [model.get_file(i) for i in range(1, 3)]
        files = [model.get_file(i) for i in range(3, 6)]
        
        # Dirs reversed
        assert dirs[0].name == "src"
        assert dirs[1].name == "docs"

    def test_sort_by_size(self, model):
        model.sort(2, Qt.AscendingOrder)
        files = [model.get_file(i) for i in range(3, 6)]
        sizes = [f._size_bytes for f in files]
        assert sizes == sorted(sizes), f"Files not sorted by size ascending: {sizes}"

    def test_sort_by_size_descending(self, model):
        model.sort(2, Qt.DescendingOrder)
        files = [model.get_file(i) for i in range(3, 6)]
        sizes = [f._size_bytes for f in files]
        assert sizes == sorted(sizes, reverse=True), f"Files not sorted by size desc: {sizes}"

    def test_sort_by_date(self, model):
        model.sort(3, Qt.AscendingOrder)
        files = [model.get_file(i) for i in range(3, 6)]
        times = [f._mtime for f in files]
        assert times == sorted(times), f"Files not sorted by date ascending: {times}"


class TestFileModelUpdate:
    def test_update_files(self, model):
        new_files = [
            make_file("new.txt", "txt", 100, 5000),
        ]
        model.update_files(new_files)
        assert model.rowCount() == 1

    def test_update_preserves_sort(self, model):
        model.sort(0, Qt.DescendingOrder)
        new_files = [
            make_file("..", "", 0, 0, is_dir=True),
            make_file("zzz", "", 0, 1000, is_dir=True),
            make_file("aaa", "", 0, 1000, is_dir=True),
            make_file("file_b.txt", "txt", 200, 2000),
            make_file("file_a.txt", "txt", 100, 1000),
        ]
        model.update_files(new_files)
        # '..' first, then dirs descending, then files descending
        assert model.get_file(0).name == ".."
        assert model.get_file(1).name == "zzz"
        assert model.get_file(2).name == "aaa"
        assert model.get_file(3).name == "file_b.txt"
        assert model.get_file(4).name == "file_a.txt"

    def test_update_empty(self, model):
        model.update_files([])
        assert model.rowCount() == 0


class TestFileModelIcons:
    def test_dir_icon(self, model):
        model.sort(0, Qt.AscendingOrder)
        idx = model.index(1, 0)  # first dir after ".."
        icon = model.data(idx, Qt.DecorationRole)
        assert icon is not None

    def test_up_icon(self, model):
        idx = model.index(0, 0)  # ".."
        icon = model.data(idx, Qt.DecorationRole)
        assert icon is not None

    def test_file_icon(self, model):
        model.sort(0, Qt.AscendingOrder)
        idx = model.index(3, 0)  # first file
        icon = model.data(idx, Qt.DecorationRole)
        assert icon is not None
