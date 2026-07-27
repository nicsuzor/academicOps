"""Installer for the aops-owned slice of Claude Code's `autoMode` settings.

specs/ARCHITECTURE.md "Installation": installation is the only stage
permitted to touch a client installation, and it touches only what it
declares. Claude Code applies always-on rules through `autoMode` in
~/.claude/settings.json, read only from that file. The build emits one
axioms.jsonl per plugin that ships `trigger: always_on` axioms (see
build/clients/claude.py); this merges them in.

The merge is scoped, idempotent, and reversible:

- it writes only into `autoMode.soft_deny`, and only entries it owns —
  tracked in a sidecar state file, never guessed from content — so it never
  replaces a whole settings block it did not author
- re-running install first retracts its own previously-recorded entries,
  then adds the current set, so a renamed or removed axiom never lingers
- uninstall removes exactly what the state file says was added, then
  deletes the state file — idempotent if run twice

specs/ARCHITECTURE.md "Enforcement": autoMode is advisory, one of two
overlapping mechanisms (the other is `cope`), never the real gate — this
module only keeps its data in sync, it does not evaluate or enforce anything.

Any real failure (unreadable/malformed settings.json or state file,
unwritable settings.json, a malformed axioms.jsonl) is a hard, non-zero
failure — never swallowed into a print. Finding zero axioms.jsonl files under
dist/ is not a failure: there is legitimately nothing to merge, and that is
reported as such, not treated as an error.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

DEFAULT_SETTINGS_PATH = Path.home() / ".claude" / "settings.json"
DEFAULT_STATE_PATH = Path.home() / ".claude" / ".aops-automode-state.json"


class InstallError(Exception):
    """A real install/uninstall failure — never swallowed into a print."""


def _load_axiom_entries(dist_root: Path) -> list[str]:
    """One `slug: description` string per always-on axiom, deduplicated and
    sorted, gathered from every plugin's dist/<name>-claude/axioms.jsonl —
    whichever plugin(s) actually ship always-on axioms, never hardcoded to
    one plugin name."""
    entries: set[str] = set()
    for jsonl_path in sorted(dist_root.glob("*-claude/axioms.jsonl")):
        try:
            lines = jsonl_path.read_text(encoding="utf-8").splitlines()
        except OSError as e:
            raise InstallError(f"cannot read {jsonl_path}: {e}") from e

        for lineno, line in enumerate(lines, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                axiom = json.loads(line)
                entry = f"{axiom['slug']}: {axiom['description']}"
            except (json.JSONDecodeError, KeyError) as e:
                raise InstallError(f"{jsonl_path}:{lineno}: malformed axiom entry: {e}") from e
            entries.add(entry)
    return sorted(entries)


def _load_json(path: Path, *, what: str) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        raise InstallError(f"cannot read {what} at {path}: {e}") from e


def _write_json(path: Path, data: dict[str, Any]) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    except OSError as e:
        raise InstallError(f"cannot write {path}: {e}") from e


def install_automode(
    dist_root: Path,
    settings_path: Path | None = None,
    state_path: Path | None = None,
) -> str:
    """Merge every dist/*-claude/axioms.jsonl into settings.json's
    autoMode.soft_deny, scoped by the state file. Returns a human-readable
    summary on success; raises InstallError on any real failure."""
    settings_path = settings_path or DEFAULT_SETTINGS_PATH
    state_path = state_path or DEFAULT_STATE_PATH

    desired = _load_axiom_entries(dist_root)

    settings = _load_json(settings_path, what="settings.json")
    state = _load_json(state_path, what="aops install state")
    previously_owned = set(state.get("soft_deny", []))

    auto_mode = dict(settings.get("autoMode", {}))
    current = list(auto_mode.get("soft_deny", []))

    # Retract our own previous entries by record (never by guessing at
    # content), then add the current set — a renamed/removed axiom can never
    # linger, and nothing the user added by hand is ever touched.
    retained = [entry for entry in current if entry not in previously_owned]
    merged = retained + [entry for entry in desired if entry not in retained]

    auto_mode["soft_deny"] = merged
    settings["autoMode"] = auto_mode

    _write_json(settings_path, settings)
    _write_json(state_path, {"soft_deny": desired})

    if not desired:
        return f"found no axioms.jsonl under {dist_root} — nothing to merge (0 aops entries in {settings_path})"
    return f"merged {len(desired)} aops axiom rule(s) into {settings_path} (autoMode.soft_deny)"


def uninstall_automode(
    settings_path: Path | None = None,
    state_path: Path | None = None,
) -> str:
    """Remove exactly the entries this installer previously added, then
    delete the state file. Idempotent — a missing state file is a no-op."""
    settings_path = settings_path or DEFAULT_SETTINGS_PATH
    state_path = state_path or DEFAULT_STATE_PATH

    if not state_path.exists():
        return f"no aops install state at {state_path} — nothing to remove"

    state = _load_json(state_path, what="aops install state")
    owned = set(state.get("soft_deny", []))

    settings = _load_json(settings_path, what="settings.json")
    auto_mode = dict(settings.get("autoMode", {}))
    remaining = [entry for entry in auto_mode.get("soft_deny", []) if entry not in owned]

    if remaining:
        auto_mode["soft_deny"] = remaining
    else:
        auto_mode.pop("soft_deny", None)
    if auto_mode:
        settings["autoMode"] = auto_mode
    else:
        settings.pop("autoMode", None)

    _write_json(settings_path, settings)
    try:
        state_path.unlink()
    except OSError as e:
        raise InstallError(f"cannot remove {state_path}: {e}") from e

    return f"removed {len(owned)} aops axiom rule(s) from {settings_path} (autoMode.soft_deny)"


def main() -> int:
    parser = argparse.ArgumentParser(description="Merge/remove aops-owned autoMode entries")
    parser.add_argument("action", choices=["install", "uninstall"])
    parser.add_argument(
        "--dist-root",
        type=Path,
        default=None,
        help="Where to find */-claude/axioms.jsonl (install only; default: <repo>/dist)",
    )
    parser.add_argument("--settings-path", type=Path, default=DEFAULT_SETTINGS_PATH)
    parser.add_argument("--state-path", type=Path, default=DEFAULT_STATE_PATH)
    args = parser.parse_args()

    try:
        if args.action == "install":
            dist_root = args.dist_root or (Path(__file__).resolve().parent.parent / "dist")
            message = install_automode(dist_root, args.settings_path, args.state_path)
        else:
            message = uninstall_automode(args.settings_path, args.state_path)
    except InstallError as e:
        print(f"x {e}", file=sys.stderr)
        return 1

    print(f"✓ {message}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
