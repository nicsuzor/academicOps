import json
import re
import subprocess
from pathlib import Path

import pytest

# Locate the dist directory containing the built plugins
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DIST_ROOT = PROJECT_ROOT / "dist"
DOCKERFILE_PATH = PROJECT_ROOT / "Dockerfile"
DOCKERIGNORE_PATH = PROJECT_ROOT / ".dockerignore"


def get_plugin_dirs():
    """Returns a list of all built plugin directories in dist/."""
    if not DIST_ROOT.exists():
        return []

    plugin_dirs = []
    for d in DIST_ROOT.iterdir():
        if d.is_dir() and (d.name.endswith("-claude") or d.name.endswith("-antigravity")):
            plugin_dirs.append(d)
    return sorted(plugin_dirs)


@pytest.mark.parametrize("plugin_dir", get_plugin_dirs(), ids=lambda d: d.name)
def test_plugin_validates_against_cli(plugin_dir):
    """
    Checks each built plugin package against the native CLI plugin validate command.
    """
    # Determine which CLI to use based on the plugin's target platform
    if plugin_dir.name.endswith("-claude"):
        cli_command = ["claude", "plugin", "validate", str(plugin_dir)]
    elif plugin_dir.name.endswith("-antigravity"):
        cli_command = ["agy", "plugin", "validate", str(plugin_dir)]
    else:
        pytest.skip(f"Unrecognized plugin platform for directory: {plugin_dir.name}")

    try:
        # Execute the native CLI validation command
        result = subprocess.run(cli_command, capture_output=True, text=True, check=False)

        # Ensure the CLI considers the plugin manifest format valid
        assert result.returncode == 0, (
            f"Native plugin validation failed for {plugin_dir.name}.\n"
            f"Command: {' '.join(cli_command)}\n"
            f"Exit Code: {result.returncode}\n"
            f"Stdout:\n{result.stdout}\n"
            f"Stderr:\n{result.stderr}"
        )

    except FileNotFoundError:
        # Gracefully skip if the CLI tool is not installed in the current environment
        pytest.skip(
            f"CLI tool '{cli_command[0]}' not found on the system. Skipping native validation test."
        )


def _extract_hook_script_paths(hooks_config: dict) -> set[str]:
    """Pull every ``.py`` script path referenced by a hooks.json's command/args fields.

    Raw command strings can be a bare ``${CLAUDE_PLUGIN_ROOT}/hooks/foo.py`` arg,
    or a quoted path embedded in a ``bash -c '...'`` string (Claude Code's
    template shape). Either way, a real script path is a whitespace/quote-free
    token ending in ``.py``.
    """
    paths: set[str] = set()
    for event_entries in hooks_config.get("hooks", {}).values():
        for entry in event_entries:
            for hook in entry.get("hooks", []):
                pieces = []
                if "command" in hook:
                    pieces.append(hook["command"])
                pieces.extend(hook.get("args", []))
                for piece in pieces:
                    paths.update(re.findall(r'[^\s"\']+\.py', piece))
    return paths


def _resolve_hook_path(plugin_dir: Path, raw_path: str) -> Path:
    cleaned = raw_path.replace("${CLAUDE_PLUGIN_ROOT}", "").replace("${AGY_PLUGIN_ROOT}", "")
    cleaned = cleaned.lstrip("/")
    return plugin_dir / cleaned


@pytest.mark.parametrize("plugin_dir", get_plugin_dirs(), ids=lambda d: d.name)
def test_hooks_json_script_paths_resolve_to_shipped_files(plugin_dir):
    """Every hook command/args script path declared in a built plugin's hooks.json
    must resolve to a real file shipped inside that same plugin artifact.

    Structural-prevention regression test for the v0.5 core-plugin BLOCKER found
    by marsha's QA review (epic_21042b5f): `aops/templates/hooks.template.json`
    wired PreToolUse/Stop to `hooks/gate_dispatch.py`, a script that never
    shipped in the built core package (it moved to aops-jr in the jr/ida
    extraction, PR #2326, and core's own manifest was never repointed). Neither
    `claude plugin validate` nor the rest of the pytest suite caught this
    because nothing checked that a declared hook command resolves to a real
    file on disk — this test closes that coverage gap so the same class of
    defect fails a build instead of shipping silently.
    """
    if plugin_dir.name.endswith("-claude"):
        hooks_json_path = plugin_dir / "hooks" / "hooks.json"
    elif plugin_dir.name.endswith("-antigravity"):
        hooks_json_path = plugin_dir / "hooks.json"
    else:
        pytest.skip(f"Unrecognized plugin platform for directory: {plugin_dir.name}")

    if not hooks_json_path.exists():
        pytest.skip(f"No hooks.json shipped for {plugin_dir.name} (plugin declares no hooks)")

    with open(hooks_json_path) as f:
        hooks_config = json.load(f)

    script_paths = _extract_hook_script_paths(hooks_config)
    missing = []
    for raw_path in sorted(script_paths):
        resolved = _resolve_hook_path(plugin_dir, raw_path)
        if not resolved.is_file():
            missing.append(f"  {raw_path} -> {resolved} (does not exist)")

    assert not missing, (
        f"{plugin_dir.name}: hooks.json declares hook script(s) that do not exist "
        f"in the built artifact:\n" + "\n".join(missing)
    )


# --- .dockerignore vs Dockerfile COPY sources ---------------------------------
#
# Structural-prevention regression test: `make build-docker` failed with
# `failed to calculate checksum of ref ...: "/aops/polecat/defaults/...": not
# found` because `.dockerignore` denies everything (`**`) and then allowlists
# specific top-level dirs (`!/aops-jr/**`, `/scripts/**`, ...) but never
# `!/aops/**` — so the entire `aops/` core plugin directory, which several
# `COPY` instructions in the Dockerfile read from, was excluded from the build
# context. This test resolves every context-relative `COPY` source in the
# Dockerfile against `.dockerignore`'s own allow/deny rules (mirroring how
# BuildKit itself decides context inclusion) and fails if any source is
# excluded — closing this class of defect the same way
# `test_hooks_json_script_paths_resolve_to_shipped_files` above closes the
# hooks.json-vs-shipped-files gap. Scope: this implements the pattern shapes
# actually used by this repo's `.dockerignore` (`**`, `!/dir`, `!/dir/**`,
# `**/name`, plain paths) — not the full BuildKit ignore-pattern grammar.


def _dockerignore_pattern_to_regex(pattern: str) -> re.Pattern:
    """Translate a single (already-stripped-of-leading-`!`) dockerignore
    pattern into a regex that fullmatches a context-relative path.

    A trailing `/**` (the "allow this whole directory" idiom this repo's
    `.dockerignore` uses, e.g. `!/aops/**`) also matches the bare directory
    path itself (`aops`, not just `aops/...`), matching BuildKit's actual
    behavior — a `COPY aops/... ` source is the directory name itself, not a
    path underneath it.
    """
    pattern = pattern.strip().lstrip("/")
    trailing_dir_wildcard = pattern.endswith("/**")
    if trailing_dir_wildcard:
        pattern = pattern[: -len("/**")]

    tokens = re.split(r"(\*\*/|\*\*|\*|\?)", pattern)
    regex_parts = []
    for tok in tokens:
        if tok == "**/":
            regex_parts.append("(?:.*/)?")
        elif tok == "**":
            regex_parts.append(".*")
        elif tok == "*":
            regex_parts.append("[^/]*")
        elif tok == "?":
            regex_parts.append("[^/]")
        elif tok == "":
            continue
        else:
            regex_parts.append(re.escape(tok))
    body = "".join(regex_parts)
    if trailing_dir_wildcard:
        body += "(?:/.*)?"
    return re.compile("^" + body + "$")


def _load_dockerignore_rules(dockerignore_path: Path) -> list[tuple[re.Pattern, bool]]:
    """Parse `.dockerignore` into an ordered list of (regex, negate) rules."""
    rules = []
    for raw_line in dockerignore_path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        negate = line.startswith("!")
        if negate:
            line = line[1:]
        rules.append((_dockerignore_pattern_to_regex(line), negate))
    return rules


def _is_excluded_by_dockerignore(rel_path: str, rules: list[tuple[re.Pattern, bool]]) -> bool:
    """Whether `rel_path` (context-relative, no leading `/`) is excluded from
    the Docker build context by the given ordered dockerignore rules. Later
    matching rules override earlier ones, matching BuildKit's own semantics.
    A rule also matches if it matches an ancestor directory of `rel_path`
    (a directory-level exclude/include covers everything beneath it).
    """
    parts = rel_path.split("/")
    candidates = ["/".join(parts[:k]) for k in range(1, len(parts) + 1)]
    excluded = False
    for regex, negate in rules:
        if any(regex.match(candidate) for candidate in candidates):
            excluded = not negate
    return excluded


def _extract_dockerfile_copy_sources(dockerfile_path: Path) -> list[str]:
    """Every context-relative source path read by a `COPY` instruction in the
    Dockerfile. `COPY --from=<stage>` instructions are skipped — their source
    is another build stage, not the host build context, so `.dockerignore`
    does not apply to them.
    """
    sources = []
    for line in dockerfile_path.read_text().splitlines():
        stripped = line.strip()
        if not re.match(r"^COPY\b", stripped, re.IGNORECASE):
            continue
        tokens = stripped.split()[1:]  # drop the leading "COPY"
        flags = [t for t in tokens if t.startswith("--")]
        if any(f.startswith("--from=") for f in flags):
            continue  # copies from another build stage, not the build context
        args = [t for t in tokens if not t.startswith("--")]
        if len(args) < 2:
            continue  # malformed / not a src...dest COPY
        sources.extend(args[:-1])  # every arg except the destination is a source
    return sources


def test_dockerfile_copy_sources_included_in_build_context():
    """Every build-context `COPY` source in the Dockerfile must survive
    `.dockerignore` filtering, or `docker build` fails with a checksum/"not
    found" error at build time (see module-level comment above)."""
    rules = _load_dockerignore_rules(DOCKERIGNORE_PATH)
    sources = _extract_dockerfile_copy_sources(DOCKERFILE_PATH)
    assert sources, "expected to find at least one build-context COPY source in the Dockerfile"

    excluded = [src for src in sources if _is_excluded_by_dockerignore(src, rules)]
    assert not excluded, (
        "Dockerfile COPY source(s) excluded from the build context by .dockerignore "
        "(docker build will fail with a checksum/\"not found\" error):\n"
        + "\n".join(f"  {src}" for src in excluded)
        + "\n\nFix: add an allowlist entry (e.g. `!/<top-level-dir>/**`) to .dockerignore."
    )
