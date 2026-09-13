"""Tests for the UserPromptSubmit hook in plugins/aops/hooks/handlers.py.

PKB search (`search_the_pkb`) moved to plugins/pkb/hooks/handlers.py -- see
tests/test_pkb_handlers.py. This file covers what aops still owns: the tracer
handlers wired to UserPromptSubmit.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
LIB_HOOKS = REPO_ROOT / "lib" / "hooks"
AOPS_HOOKS = REPO_ROOT / "plugins" / "aops" / "hooks"

if str(LIB_HOOKS) not in sys.path:
    sys.path.insert(0, str(LIB_HOOKS))
if str(AOPS_HOOKS) not in sys.path:
    sys.path.insert(0, str(AOPS_HOOKS))

import importlib.util

handlers_spec = importlib.util.spec_from_file_location("aops_handlers", AOPS_HOOKS / "handlers.py")
assert handlers_spec is not None and handlers_spec.loader is not None
handlers = importlib.util.module_from_spec(handlers_spec)
# Deliberately NOT registered as sys.modules["handlers"]: that name collides
# with plugins/rbg/hooks/handlers.py, which tests/test_cope.py imports under
# the bare name "handlers". Under pytest-xdist, whichever module registers
# that slot first wins it for every test in the worker, so a bare "handlers"
# registration here causes test_cope.py's handlers.evaluate(...) calls to
# raise AttributeError against the wrong module.
handlers_spec.loader.exec_module(handlers)


def test_user_prompt_submit_registered_in_handlers():
    """Verify that user_prompt_submit and agy_user_prompt_submit are wired to UserPromptSubmit."""
    assert "UserPromptSubmit" in handlers.HANDLERS
    registered = handlers.HANDLERS["UserPromptSubmit"]
    assert handlers.user_prompt_submit in registered
    assert handlers.agy_user_prompt_submit in registered
    assert not hasattr(handlers, "search_the_pkb"), "search_the_pkb moved to the pkb plugin"
