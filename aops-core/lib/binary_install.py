"""Check pkb binary availability and return setup instructions if missing."""

import shutil


def check_pkb_available() -> str | None:
    """Check if pkb is on PATH.

    Returns an instruction message if pkb is missing, or None if available.
    """
    if shutil.which("pkb"):
        return None

    return (
        "WARNING: pkb MCP server binary not found on PATH.\n"
        "The personal knowledge base (pkb) will not be available this session.\n"
        "To install, run:\n"
        "  cargo binstall --git https://github.com/nicsuzor/mem --no-confirm mem\n"
        "(This installs the `pkb` binary from the `mem` project; requires cargo-binstall: "
        "cargo install cargo-binstall)\n"
        "Or: make install-cli"
    )
