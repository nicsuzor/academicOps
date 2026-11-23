"""Installer for the aops-owned slice of Claude Code's `autoMode` settings.

specs/ARCHITECTURE.md "Installation": installation is the only stage
permitted to touch a client installation, and it touches only what it
declares. Claude Code applies classifier rules through `autoMode` in
~/.claude/settings.json, read only from that file (and managed settings).
The build emits one `auto-mode.json` per plugin that declares Claude Code
classifier rules in `manifest/auto-mode.json` (see build/clients/claude.py);
this merges them in. Always-on axioms are delivered separately as agent
instructions (`rules/*.md` and `axioms.jsonl`), never dumped wholesale into
the per-tool-call classifier (see specs/enforcement/auto-mode-classifier.md).

Setting any `autoMode` section array (`allow`, `soft_deny`, `hard_deny`,
`environment`) replaces Claude Code's built-in list for that section
wholesale, unless the array contains the literal string `"$defaults"` --
the splice point at which the live built-ins are inserted. Every section
this module writes carries the sentinel so Claude Code's own protections
stay live across releases.

The merge is scoped, idempotent, and reversible:

- it touches only sections declared in shipped `auto-mode.json` files (plus
  any section recorded in the sidecar state file from a prior install), and
  only entries it owns -- tracked in the state file, never guessed from
  content. Sections the installer never writes (such as user-configured
  `environment` or `hard_deny`) are untouched
- the sentinel is never recorded as owned and never retracted while user
  entries remain; it is placed once, first, and left wherever the user
  later moves it
- re-running install first retracts its own previously-recorded entries per
  section (including legacy `soft_deny`-only axiom entries from older
  installs), then adds the current set, so a renamed or removed rule never
  lingers
- uninstall removes exactly what the state file says was added across all
  owned sections, then deletes the state file -- idempotent if run twice.
  A section left holding nothing but the sentinel is dropped with it

specs/ARCHITECTURE.md "Enforcement": autoMode is advisory, one of two
overlapping mechanisms (the other is `cope`), never the real gate -- this
module only keeps its data in sync, it does not evaluate or enforce anything.

Any real failure (unreadable/malformed settings.json, state file, or
auto-mode.json; unwritable settings.json; unknown section key) is a hard,
non-zero failure -- never swallowed into a print. Finding zero
auto-mode.json files under dist/ is not a failure: there is legitimately
nothing to merge, and that is reported as such.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

DEFAULT_SETTINGS_PATH = Path.home() / ".claude" / "settings.json"
DEFAULT_STATE_PATH = Path.home() / ".claude" / ".aops-automode-state.json"
DEFAULT_GEMINI_PLUGINS_DIR = Path.home() / ".gemini" / "config" / "plugins"

# The splice point at which Claude Code inserts its own built-in rules for a
# section. An array written without it discards those built-ins entirely.
DEFAULTS_SENTINEL = "$defaults"

# Valid Claude Code autoMode array sections, in canonical write order.
AUTOMODE_SECTIONS: tuple[str, ...] = ("allow", "soft_deny", "hard_deny", "environment")


class InstallError(Exception):
    """A real install/uninstall failure -- never swallowed into a print."""


def _load_automode_entries(dist_root: Path) -> dict[str, list[str]]:
    """Gather curated autoMode rules per section from every plugin's
    `dist/<name>-claude/auto-mode.json`, deduplicated per section while
    preserving declaration order -- never hardcoded to one plugin name."""
    per_section: dict[str, list[str]] = {}
    seen: dict[str, set[str]] = {}

    for json_path in sorted(dist_root.glob("*-claude/auto-mode.json")):
        try:
            raw = json.loads(json_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            raise InstallError(f"cannot read {json_path}: {e}") from e

        if not isinstance(raw, dict):
            raise InstallError(
                f"{json_path}: malformed auto-mode.json: expected JSON object, "
                f"got {type(raw).__name__}"
            )

        for section, entries in raw.items():
            if section not in AUTOMODE_SECTIONS:
                raise InstallError(
                    f"{json_path}: unknown autoMode section {section!r} "
                    f"(expected one of {list(AUTOMODE_SECTIONS)})"
                )
            if not isinstance(entries, list):
                raise InstallError(
                    f"{json_path}: section {section!r} must be a list of strings, "
                    f"got {type(entries).__name__}"
                )
            section_list = per_section.setdefault(section, [])
            section_seen = seen.setdefault(section, set())
            for idx, entry in enumerate(entries):
                if not isinstance(entry, str) or not entry.strip():
                    raise InstallError(
                        f"{json_path}: section {section!r}[{idx}] must be a non-empty string"
                    )
                if entry == DEFAULTS_SENTINEL:
                    raise InstallError(
                        f"{json_path}: section {section!r}[{idx}] must not include "
                        f'"{DEFAULTS_SENTINEL}" (the installer manages sentinel placement)'
                    )
                if entry not in section_seen:
                    section_seen.add(entry)
                    section_list.append(entry)

    return {section: entries for section, entries in per_section.items() if entries}


def _load_json(path: Path, *, what: str) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        raise InstallError(f"cannot read {what} at {path}: {e}") from e
    if not isinstance(data, dict):
        raise InstallError(f"cannot read {what} at {path}: expected JSON object")
    return data


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
    """Merge every `dist/*-claude/auto-mode.json` into settings.json's
    `autoMode` sections, scoped by the state file, keeping Claude Code's own
    built-in rules spliced in via `"$defaults"` per written section. Returns a
    human-readable summary on success; raises InstallError on any real failure."""
    settings_path = settings_path or DEFAULT_SETTINGS_PATH
    state_path = state_path or DEFAULT_STATE_PATH

    desired_by_section = _load_automode_entries(dist_root)

    settings = _load_json(settings_path, what="settings.json")
    state = _load_json(state_path, what="aops install state")

    auto_mode = dict(settings.get("autoMode", {}))
    new_state: dict[str, list[str]] = {}
    restored_sentinels: list[str] = []

    sections_to_touch = [
        section
        for section in AUTOMODE_SECTIONS
        if section in desired_by_section or bool(state.get(section))
    ]

    for section in sections_to_touch:
        previously_owned = set(state.get(section, []))
        desired = desired_by_section.get(section, [])
        current = list(auto_mode.get(section, []))

        # Retract our own previous entries by record (never by guessing at
        # content), then add the current set -- a renamed/removed rule can
        # never linger, and nothing the user added by hand is ever touched.
        retained = [entry for entry in current if entry not in previously_owned]

        if desired:
            merged = retained + [entry for entry in desired if entry not in retained]
            # Writing a section array at all discards Claude Code's built-in
            # rules for that section unless the sentinel splices them back in.
            # Only ever placed, never recorded as owned and never retracted
            # while user entries remain -- so a re-run finds it already in
            # `retained` and adds no second copy, and a user is free to move it.
            if DEFAULTS_SENTINEL not in merged:
                merged.insert(0, DEFAULTS_SENTINEL)
                restored_sentinels.append(section)
            auto_mode[section] = merged
            new_state[section] = desired
        else:
            # All aops entries for this section were withdrawn. Drop the
            # section if nothing user-owned remains (a sentinel-only list
            # resolves identically to an absent section).
            if retained and retained != [DEFAULTS_SENTINEL]:
                auto_mode[section] = retained
            else:
                auto_mode.pop(section, None)

    if auto_mode:
        settings["autoMode"] = auto_mode
    else:
        settings.pop("autoMode", None)

    if sections_to_touch or settings_path.exists():
        _write_json(settings_path, settings)

    if new_state:
        _write_json(state_path, new_state)
    elif state_path.exists():
        try:
            state_path.unlink()
        except OSError as e:
            raise InstallError(f"cannot remove {state_path}: {e}") from e

    total = sum(len(entries) for entries in new_state.values())
    if total == 0:
        return (
            f"found no auto-mode.json under {dist_root} -- nothing to merge "
            f"(0 aops entries in {settings_path})"
        )

    section_summary = ", ".join(f"{s}={len(new_state[s])}" for s in new_state)
    sentinel_note = (
        f' and restored "{DEFAULTS_SENTINEL}" in {", ".join(restored_sentinels)}'
        if restored_sentinels
        else ""
    )
    return (
        f"merged {total} aops autoMode rule(s) into {settings_path} "
        f"({section_summary}{sentinel_note})"
    )


def uninstall_automode(
    settings_path: Path | None = None,
    state_path: Path | None = None,
) -> str:
    """Remove exactly the entries this installer previously added across all
    owned sections, then delete the state file. Any section left holding only
    the `"$defaults"` sentinel goes too -- it resolves to the built-in list
    either way. Idempotent -- a missing state file is a no-op."""
    settings_path = settings_path or DEFAULT_SETTINGS_PATH
    state_path = state_path or DEFAULT_STATE_PATH

    if not state_path.exists():
        return f"no aops install state at {state_path} -- nothing to remove"

    state = _load_json(state_path, what="aops install state")
    settings = _load_json(settings_path, what="settings.json")
    auto_mode = dict(settings.get("autoMode", {}))

    removed_counts: dict[str, int] = {}
    for section in AUTOMODE_SECTIONS:
        owned = set(state.get(section, []))
        if not owned:
            continue
        removed_counts[section] = len(owned)
        remaining = [entry for entry in auto_mode.get(section, []) if entry not in owned]
        if remaining and remaining != [DEFAULTS_SENTINEL]:
            auto_mode[section] = remaining
        else:
            auto_mode.pop(section, None)

    if auto_mode:
        settings["autoMode"] = auto_mode
    else:
        settings.pop("autoMode", None)

    _write_json(settings_path, settings)
    try:
        state_path.unlink()
    except OSError as e:
        raise InstallError(f"cannot remove {state_path}: {e}") from e

    total = sum(removed_counts.values())
    section_summary = ", ".join(f"{s}={n}" for s, n in removed_counts.items()) or "none"
    return f"removed {total} aops autoMode rule(s) from {settings_path} ({section_summary})"


def main() -> int:
    parser = argparse.ArgumentParser(description="Merge/remove aops-owned autoMode entries")
    parser.add_argument("action", choices=["install", "uninstall"])
    parser.add_argument(
        "--dist-root",
        type=Path,
        default=None,
        help="Where to find dist directories (default: <repo>/dist)",
    )
    parser.add_argument("--settings-path", type=Path, default=DEFAULT_SETTINGS_PATH)
    parser.add_argument("--state-path", type=Path, default=DEFAULT_STATE_PATH)
    parser.add_argument(
        "--gemini-plugins-dir",
        type=Path,
        default=DEFAULT_GEMINI_PLUGINS_DIR,
        help="Where agy's installed plugins live (default: ~/.gemini/config/plugins)",
    )
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
