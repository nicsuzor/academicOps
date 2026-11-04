"""Tests for version validation in academicOps build and release pipeline.

Verifies that invalid Python package versions (such as '1.0-rc0.1', which downstream
builds cannot parse per PEP 440) are refused before any tag or publish step, and that
valid versions are accepted.
"""

import subprocess
import sys
from pathlib import Path

import pytest

from build.build import build_all
from build.errors import BuildError
from build.version import validate_version

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TESTDATA = PROJECT_ROOT / "build" / "testdata"
MARKETPLACE = TESTDATA / "marketplace.toml"


@pytest.mark.parametrize(
    "valid_version",
    [
        "0.10.25",
        "1.0.0",
        "1.0.0rc1",
        "1.0.0-rc.1",
        "0.10-rc1",
        "1.0.0-beta.1",
        "1.0.0+g12345678",
        "v1.0.0",
        "v0.10.26",
        "1.0-rc7",
        "v1.0-rc7",
        "v1.0-rc0",
    ],
)
def test_validate_version_accepts_valid_pep440(valid_version: str) -> None:
    norm = validate_version(valid_version)
    assert norm is not None
    assert len(norm) > 0


@pytest.mark.parametrize(
    "invalid_version",
    [
        "1.0-rc0.1",
        "v1.0-rc0.1",
        "1.0-rc0.2",
        "not-a-version",
        "1.0.0-invalid_label",
    ],
)
def test_validate_version_rejects_unparseable_python_version(invalid_version: str) -> None:
    with pytest.raises(ValueError, match="Invalid Python package version"):
        validate_version(invalid_version)


def test_build_all_rejects_unparseable_version(tmp_path: Path) -> None:
    dist_root = tmp_path / "dist"
    with pytest.raises(BuildError, match="Invalid Python package version"):
        build_all(
            TESTDATA,
            dist_root,
            marketplace_path=MARKETPLACE,
            version="1.0-rc0.1",
        )


def test_build_all_accepts_valid_version(tmp_path: Path) -> None:
    dist_root = tmp_path / "dist"
    built = build_all(
        TESTDATA,
        dist_root,
        marketplace_path=MARKETPLACE,
        version="0.10.26",
    )
    assert len(built) > 0


def test_version_cli_validate_flag_rejects_invalid_version() -> None:
    cmd = [sys.executable, "-m", "build.version", "--validate", "1.0-rc0.1"]
    res = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True, check=False)
    assert res.returncode != 0
    assert "invalid python package version" in res.stderr.lower()


def test_version_cli_validate_flag_accepts_valid_version() -> None:
    cmd = [sys.executable, "-m", "build.version", "--validate", "0.10.26"]
    res = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True, check=False)
    assert res.returncode == 0
    assert "valid python package version" in res.stdout.lower()
