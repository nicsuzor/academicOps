"""Tests for lib/binary_install.py — pkb availability check."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

aops_core_dir = Path(__file__).parent.parent.parent / "aops-core"
if str(aops_core_dir) not in sys.path:
    sys.path.insert(0, str(aops_core_dir))

from lib.binary_install import check_pkb_available


class TestCheckPkbAvailable:
    """Test check_pkb_available under different PATH scenarios."""

    def test_pkb_on_path_returns_none(self):
        """When pkb is found, return None (no action needed)."""
        with patch("lib.binary_install.shutil.which", return_value="/usr/local/bin/pkb"):
            assert check_pkb_available() is None

    def test_pkb_missing_returns_instructions(self):
        """When pkb is not found, return install instructions."""
        with patch("lib.binary_install.shutil.which", return_value=None):
            result = check_pkb_available()
            assert "WARNING" in result
            assert "pkb" in result
            assert "cargo binstall" in result
            assert "make install-cli" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
