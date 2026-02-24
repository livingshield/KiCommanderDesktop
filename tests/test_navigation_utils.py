"""Tests for navigation utilities – drive detection and quick links."""
import os
import sys
import platform
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# Need QApplication for QStandardPaths to work
from PySide6.QtWidgets import QApplication
app = QApplication.instance() or QApplication(sys.argv)

from navigation_utils import get_drives, get_quick_links


class TestGetDrives:
    def test_returns_list(self):
        drives = get_drives()
        assert isinstance(drives, list)

    def test_non_empty(self):
        drives = get_drives()
        assert len(drives) > 0, "At least one drive should exist"

    @pytest.mark.skipif(platform.system() != "Windows", reason="Windows only")
    def test_windows_c_drive(self):
        drives = get_drives()
        assert "C:\\" in drives, "C:\\ should always be present on Windows"

    @pytest.mark.skipif(platform.system() != "Windows", reason="Windows only")
    def test_windows_drive_format(self):
        drives = get_drives()
        for d in drives:
            assert len(d) == 3, f"Drive should be 3 chars (e.g. C:\\), got: {d}"
            assert d[1] == ":", f"Drive should have colon: {d}"
            assert d[2] == "\\", f"Drive should end with backslash: {d}"

    @pytest.mark.skipif(platform.system() == "Windows", reason="Unix only")
    def test_unix_root(self):
        drives = get_drives()
        assert "/" in drives


class TestGetQuickLinks:
    def test_returns_list(self):
        links = get_quick_links()
        assert isinstance(links, list)

    def test_links_have_required_keys(self):
        links = get_quick_links()
        for link in links:
            assert "name" in link, f"Link missing 'name': {link}"
            assert "path" in link, f"Link missing 'path': {link}"
            assert "icon" in link, f"Link missing 'icon': {link}"

    def test_links_paths_exist(self):
        links = get_quick_links()
        for link in links:
            assert os.path.exists(link["path"]), \
                f"Quick link '{link['name']}' path does not exist: {link['path']}"

    def test_desktop_present(self):
        links = get_quick_links()
        names = [l["name"] for l in links]
        assert "Desktop" in names, "Desktop should be in quick links"

    def test_downloads_present(self):
        links = get_quick_links()
        names = [l["name"] for l in links]
        assert "Downloads" in names, "Downloads should be in quick links"
