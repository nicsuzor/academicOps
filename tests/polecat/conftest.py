"""Keep real operator credentials out of the polecat tests entirely.

These tests build and inspect the environment polecat hands to `docker run`,
and that environment is `{**os.environ, **env}` — it carries every credential
the developer's own shell happens to export. A single failing assertion that
renders such a dict publishes all of them to the terminal and to CI logs.

That is not hypothetical. On the machine this was written, the dict a failing
assertion would render held 24 live credentials — GH_TOKEN, an OAuth token,
LANGFUSE_SECRET_KEY, UNIFI_NETWORK_PASSWORD, HASS_TOKEN and more — none of
which any test here names or needs.

So: strip them before every test in this package. Tests that need a credential
set their own sentinel afterwards, and a sentinel is the only thing left that
a failure can print. Assertions in this package should still prefer comparing
*names* over comparing values, but this fixture is what makes a slip harmless
rather than a disclosure.
"""

import os
import re

import pytest

#: Name shapes that carry secrets. Deliberately broad: the cost of stripping a
#: variable no test needed is zero, the cost of missing one is disclosure.
_SECRET_NAME = re.compile(
    r"TOKEN|SECRET|PASSWORD|PASSWD|API_KEY|_KEY$|^.*_KEY_|CREDENTIAL|OAUTH|SESSION_KEY",
    re.IGNORECASE,
)

#: `git` fails outright when GIT_CONFIG_COUNT outlives the GIT_CONFIG_KEY_n /
#: GIT_CONFIG_VALUE_n pairs it counts, and GIT_CONFIG_VALUE_3 is where this
#: host keeps a credential helper with the bot token inlined. So the whole
#: block goes together or not at all — several tests here run real `git`.
_GIT_CONFIG = re.compile(r"^GIT_CONFIG_(COUNT|KEY_\d+|VALUE_\d+)$")


@pytest.fixture(autouse=True)
def _strip_real_credentials(monkeypatch):
    for name in list(os.environ):
        if _SECRET_NAME.search(name) or _GIT_CONFIG.match(name):
            monkeypatch.delenv(name, raising=False)


@pytest.fixture(autouse=True)
def _strip_real_pkb_mcp_url(monkeypatch):
    """The container launch path fails closed when no knowledge-base URL
    resolves. A
    session running these tests routinely has a real $PKB_MCP_URL exported
    (e.g. inside a polecat container), which would silently make every test
    depend on that ambient value instead of on what it sets up itself. Tests
    that need one set it, or pass --no-pkb, explicitly."""
    monkeypatch.delenv("PKB_MCP_URL", raising=False)
