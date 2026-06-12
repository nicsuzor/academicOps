#!/usr/bin/env -S uv run python
"""
Session Transcript Generator

Converts Claude Code JSONL and Gemini JSON session files to readable markdown transcripts.

Usage:
    uv run python aops-core/scripts/transcript.py session.jsonl
    uv run python aops-core/scripts/transcript.py session.jsonl -o output.md
    uv run python aops-core/scripts/transcript.py --all  # Process all sessions
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

# Add framework roots to path for lib imports
SCRIPT_DIR = Path(__file__).parent.resolve()
AOPS_CORE_ROOT = SCRIPT_DIR.parent
FRAMEWORK_ROOT = AOPS_CORE_ROOT.parent

sys.path.insert(0, str(FRAMEWORK_ROOT))
sys.path.insert(0, str(AOPS_CORE_ROOT))

import lib.session_naming as session_naming
from lib.insights_generator import (  # noqa: E402
    InsightsValidationError,
    find_existing_insights,
    get_insights_file_path,
    merge_insights,
    validate_insights_schema,
    write_insights_file,
)
from lib.paths import get_sessions_repo, get_transcripts_dir  # noqa: E402
from lib.session_reader import find_sessions  # noqa: E402
from lib.subagent_transcript import (  # noqa: E402
    maybe_append_subagent_footer,
    write_subagent_transcripts,
)
from lib.transcript_parser import (  # noqa: E402
    ParsedSession,
    SessionProcessor,
    UsageStats,
    aggregate_session_metadata,
    extract_initial_prompt,
    extract_reflection_from_entries,
    extract_timeline_events,
    extract_working_dir_from_content,
    extract_working_dir_from_entries,
    format_reflection_header,
    infer_project_from_working_dir,
    normalize_gemini_project,
    reflection_to_insights,
)
from lib.transcript_paths import (  # noqa: E402
    ensure_rotated_dir,
    extract_date_from_filename,
    iter_rotated_files,
)


def _load_transcript_config() -> dict:
    """Load transcript config from $AOPS_SESSIONS/polecat.yaml.

    Returns the 'transcripts' section, or empty dict if not found.
    Example config:
        transcripts:
          exclude_projects:
            - sessions
    """
    registry = get_sessions_repo() / "polecat.yaml"
    if not registry.exists():
        return {}
    try:
        import yaml

        with open(registry) as f:
            config = yaml.safe_load(f) or {}
        return config.get("transcripts", {}) or {}
    except (OSError, Exception) as e:
        print(f"Warning: Could not load transcript config from {registry}: {e}", file=sys.stderr)
        return {}


# Note: the former `sync_client_log` / `_sweep_legacy_client_logs` mirror to
# `$AOPS_SESSIONS/client-logs/` was removed on 2026-05-02. Per PKB kb-d8f58167,
# raw client logs are local-only and live where the provider writes them
# (`~/.claude/projects/<workspace>/<sid>.jsonl`, `~/.gemini/tmp/...`,
# `$POLECAT_HOME/polecats/<task-id>/...`). The sessions repo only carries
# distilled `transcripts/` and `summaries/`.


def _resolve_project_key(name: str, match_suffix: bool = False) -> str:
    """Resolve a project name to its registry key from polecat.yaml.

    If the name matches a slug, repo name, or alias, returns the slug.
    If match_suffix is True, also checks if name ends with a dash/underscore followed by a key.
    Otherwise returns the name verbatim (or the extracted suffix if match_suffix was used).
    """
    registry = get_sessions_repo() / "polecat.yaml"
    if not registry.exists():
        if match_suffix:
            # Best effort fallback: extract last dash segment
            parts = name.strip("-").split("-")
            return parts[-1] if parts else name
        return name

    try:
        import yaml

        with open(registry) as f:
            config = yaml.safe_load(f) or {}
        projects = config.get("projects", {}) or {}

        valid_keys = {}  # map valid_key -> slug
        for slug, proj in projects.items():
            valid_keys[slug] = slug
            proj = proj or {}
            if proj.get("repo"):
                valid_keys[proj["repo"]] = slug
            aliases = proj.get("aliases", [])
            if isinstance(aliases, str):
                aliases = [aliases]
            for alias in aliases:
                valid_keys[alias] = slug

        if not match_suffix:
            if name in valid_keys:
                return valid_keys[name]
        else:
            # Sort keys by length descending so overwhelm-dashboard matches before dashboard
            sorted_keys = sorted(valid_keys.keys(), key=len, reverse=True)
            for key in sorted_keys:
                if name == key or name.endswith("-" + key) or name.endswith("_" + key):
                    return valid_keys[key]

            # Fallback if no suffix matches registry
            parts = name.strip("-").split("-")
            return parts[-1] if parts else name

    except (OSError, Exception) as e:
        print(f"Warning: could not load polecat.yaml registry: {e}", file=sys.stderr)

    if match_suffix:
        parts = name.strip("-").split("-")
        return parts[-1] if parts else name
    return name


_PR_SKIP_BRANCHES: set[str] = {"HEAD", "dev", "main", "master"}
_PR_SKIP_PREFIXES: tuple[str, ...] = ("polecat/", "crew/", "release-please--", "worktree-")


def _slug_to_github_repo(slug: str) -> str | None:
    """Map a project slug to 'owner/repo' via polecat.yaml."""
    registry = get_sessions_repo() / "polecat.yaml"
    if not registry.exists():
        return None
    try:
        import yaml

        with open(registry) as f:
            config = yaml.safe_load(f) or {}  # allow-fallback: empty polecat.yaml is valid
        org = config.get("github_org", "nicsuzor")
        projects = (
            config.get("projects", {}) or {}
        )  # allow-fallback: projects section may be absent
        if slug in projects:
            proj = projects[slug] or {}
            repo = proj.get("repo", slug)
            return f"{org}/{repo}"
    except Exception:
        pass
    return None


def _resolve_pr_numbers(branches: list[str], repo_slug: str | None) -> list[int]:
    """Resolve qualifying branch names to PR numbers via gh CLI.

    Skips base branches (dev, main, HEAD) and internal prefixes (polecat/, crew/).
    Returns a sorted, deduplicated list of PR numbers.
    """
    if not branches or not repo_slug:
        return []
    github_repo = _slug_to_github_repo(repo_slug)
    if not github_repo:
        return []

    pr_numbers: set[int] = set()
    for branch in branches:
        if branch in _PR_SKIP_BRANCHES:
            continue
        if any(branch.startswith(p) for p in _PR_SKIP_PREFIXES):
            continue
        try:
            result = subprocess.run(
                [
                    "gh",
                    "pr",
                    "list",
                    "--head",
                    branch,
                    "--state",
                    "all",
                    "--json",
                    "number",
                    "--repo",
                    github_repo,
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                pr_numbers.update(pr["number"] for pr in json.loads(result.stdout))
        except Exception:
            pass
    return sorted(pr_numbers)


def _is_excluded_project(project: str, config: dict | None = None) -> bool:
    """Check if a project should be excluded from transcript generation.

    Args:
        project: Project name to check
        config: Transcript config dict (from _load_transcript_config)

    Returns:
        True if project is in the exclude list
    """
    if not config:
        return False
    exclude_list = config.get("exclude_projects", []) or []
    exclude_set = {p.lower() for p in exclude_list}
    return project.lower() in exclude_set


def format_markdown(file_path: Path) -> bool:
    """Format markdown file with dprint.

    Checks multiple locations for dprint, preferring local installs for speed.
    Skips formatting if no local dprint found (npx is too slow).
    Returns True if formatting succeeded or skipped, False on error.
    """
    # Check locations in order of preference (fastest first)
    dprint_locations = [
        Path.home() / ".dprint" / "bin" / "dprint",  # Official installer
        Path(__file__).parent.parent / "node_modules" / ".bin" / "dprint",  # Local npm
    ]

    dprint_path = None
    for path in dprint_locations:
        if path.exists():
            dprint_path = path
            break

    if dprint_path is None:
        # No local dprint found, skip formatting (npx is too slow)
        return True

    try:
        result = subprocess.run(
            [str(dprint_path), "fmt", str(file_path)],
            capture_output=True,
            timeout=30,
            check=False,
        )
        # Exit code 0 = success, 14 = no matching files (OK for external paths)
        return result.returncode in (0, 14)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


# Reflection-derived fields. If a re-run produces an empty value for one of
# these but the existing insights file had a non-empty value (typically authored
# by a Framework Reflection in the markdown transcript), we preserve the
# existing value rather than clobbering it. This is what makes regeneration
# safe to call repeatedly as the source jsonl grows.
_REFLECTION_FIELDS = (
    "summary",
    "outcome",
    "accomplishments",
    "friction_points",
    "proposed_changes",
    "framework_reflections",
    "next_step",
    "root_cause",
    # Timeline-derived but still preserve-on-empty: if a later pass somehow
    # fails to re-extract the initial prompt (e.g. truncated read), keep the
    # value an earlier pass already captured rather than downgrading to empty
    # (aops-efffc1f7).
    "initial_prompt",
)


def _is_empty_value(v) -> bool:
    """True if v is None, '', [], or {}."""
    if v is None:
        return True
    if isinstance(v, str | list | dict | tuple) and len(v) == 0:
        return True
    return False


def _preserve_reflection_fields(new: dict, existing: dict) -> dict:
    """For each reflection-derived field, prefer existing if new is empty.

    Mutates and returns ``new``.
    """
    for field in _REFLECTION_FIELDS:
        if field in existing and not _is_empty_value(existing.get(field)):
            if _is_empty_value(new.get(field)):
                new[field] = existing[field]
    return new


def _should_overwrite_existing(new: dict, existing: dict) -> str | None:
    """Decide whether to overwrite an existing insights file.

    Returns the trigger reason string if overwrite should happen, or None to
    skip. Heuristic: overwrite when the new run has *more* signal than what's
    on disk — typically because the source jsonl has grown since the previous
    run. We compare timeline_events length (the most reliable indicator) and a
    few coarse signals.
    """
    new_events = new.get("timeline_events") or []
    old_events = existing.get("timeline_events") or []
    if len(new_events) > len(old_events):
        return "jsonl grew"

    # Backfill the user's initial intent onto older summaries that predate the
    # field (aops-efffc1f7). The event count may be unchanged, so this is not
    # caught by the length check above.
    if new.get("initial_prompt") and not existing.get("initial_prompt"):
        return "initial_prompt appeared"

    # Backfill empty user_prompt descriptions: an older run (or an older code
    # version) may have written user_prompt events with empty descriptions. If
    # this run populated more of them — even at the same event count — refresh.
    def _populated_descriptions(events: list) -> int:
        count = 0
        for e in events:
            if e.get("type") != "user_prompt":
                continue
            desc = e.get("description") or ""  # allow-fallback: description optional; "" = no text
            if desc.strip():
                count += 1
        return count

    if _populated_descriptions(new_events) > _populated_descriptions(old_events):
        return "timeline descriptions populated"

    # If the new run picked up token_metrics that weren't there before, refresh.
    if new.get("token_metrics") and not existing.get("token_metrics"):
        return "token_metrics appeared"

    # If a fresher reflection emerged (existing was minimal, new has one), refresh.
    new_refl = new.get("framework_reflections") or []
    old_refl = existing.get("framework_reflections") or []
    if len(new_refl) > len(old_refl):
        return "framework_reflections grew"

    # If the new run resolves surface/client metadata that was missing on disk
    # (e.g. old summary predates path-based inference), refresh in place.
    if new.get("surface") and not existing.get("surface"):
        return "surface metadata appeared"
    if new.get("client") and not existing.get("client"):
        return "client metadata appeared"

    return None


def _cleanup_legacy_suffixed_summaries(canonical_path: Path) -> None:
    """Delete legacy `-1.json`, `-2.json`, ... siblings produced by an older
    multi-reflection layout. Reflections now live in a single file's
    framework_reflections[] array; the suffixed files are stale duplicates.
    """
    base = canonical_path.stem
    parent = canonical_path.parent
    for sibling in parent.glob(f"{base}-*.json"):
        rest = sibling.stem[len(base) + 1 :]
        if rest.isdigit():
            try:
                sibling.unlink()
                print(f"🧹 Removed legacy suffixed summary: {sibling.name}")
            except OSError as e:
                print(f"⚠️  Could not remove {sibling}: {e}", file=sys.stderr)


def _load_existing_insights(path: Path) -> dict | None:
    """Load existing insights JSON, or None on any error."""
    try:
        import json as _json

        return _json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        print(f"⚠️  Could not read existing insights {path}: {e}", file=sys.stderr)
        return None


def _save_minimal_token_summary(
    session_id: str,
    date_str: str,
    project: str,
    slug: str,
    timestamp: datetime | None,
    usage_stats: "UsageStats",
    session_duration_minutes: float | None,
    timeline_events: list[dict] | None = None,
    shortform: str | None = None,
    provider: str | None = None,
    session_path: Path | None = None,
    origin_override: dict[str, str | None] | None = None,
    session_ctx: dict | None = None,
    session_summary: ParsedSession | None = None,
) -> None:
    """Save minimal summary with just token_metrics when no reflection exists.

    This ensures token usage data is captured even for sessions without
    a Framework Reflection output.
    """
    # Generate ISO 8601 timestamp
    if timestamp:
        date_iso = timestamp.isoformat()
    else:
        date_iso = datetime.now().astimezone().replace(microsecond=0).isoformat()

    task_id = os.environ.get("AOPS_TASK_ID")
    if not task_id and timeline_events:
        for event in timeline_events:
            if event.get("type") in (
                "task_create",
                "task_update",
                "task_complete",
                "task_release",
            ) and event.get("task_id"):
                task_id = event["task_id"]
                break

    # Determine stable project if we only have a UUID fragment
    stable_project = project
    if (
        not stable_project
        or re.match(r"^[0-9a-f]{8,}$", stable_project)
        or re.match(r"^[0-9a-f\-]{36}$", stable_project)
    ):
        if timeline_events:
            for event in timeline_events:
                if event.get("type") == "task_create" and event.get("project"):
                    stable_project = event["project"]
                    break

    # Infer surface/client/crew from the persisted session path. The live env
    # ($GITHUB_ACTIONS, $AOPS_POLECAT_CONTAINER, $POLECAT_CREW_NAME) is gone by
    # the time the offline converter runs, so without this overrides every
    # GHA/crew/polecat summary mis-stamps `surface: claude-code-cli`. The
    # caller may also pass origin_override when it has scanned the entries
    # for a more specific signal (e.g. Claude Desktop LAM marker).
    if origin_override is not None:
        origin = origin_override
    elif session_path is not None:
        origin = session_naming.infer_session_origin_from_path(session_path, provider=provider)
    else:
        origin = {}

    # Build minimal insights with token_metrics
    insights = {
        "session_id": session_id,
        "date": date_iso,
        "project": stable_project,
        "summary": None,  # No reflection = no summary
        "outcome": None,  # No reflection = unknown outcome
        "accomplishments": [],
        "friction_points": [],
        "proposed_changes": [],
        # Metadata (aops-d9ba7159, aops-eaf402f5)
        **session_naming.get_session_metadata(provider=provider, **origin),
        "repo": stable_project,
        "task_id": task_id,
        "token_metrics": usage_stats.to_token_metrics(session_duration_minutes),
    }

    if usage_stats:
        insights["attribution"] = {
            "plugins": list(usage_stats.attribution["plugins"]),
            "skills": list(usage_stats.attribution["skills"]),
            "mcp_servers": usage_stats.attribution["mcp_servers"],
            "mcp_tools": usage_stats.attribution["mcp_tools"],
        }
        insights["stop_reasons"] = usage_stats.stop_reasons
        insights["thinking_turns"] = usage_stats.thinking_turns

    if session_ctx:
        for k, v in session_ctx.items():
            if k == "models":
                pass  # already in token_metrics by_model
            elif v is not None:
                insights[k] = v

    if session_summary:
        if session_summary.session_type:
            insights["session_type"] = session_summary.session_type
        if session_summary.pull_requests:
            insights["pull_requests"] = session_summary.pull_requests
        if session_summary.gemini_version:
            insights["gemini_version"] = session_summary.gemini_version
        if session_summary.details:
            if "gates" in session_summary.details:
                insights["gates"] = session_summary.details["gates"]
            if "global_turn_count" in session_summary.details:
                insights["global_turn_count"] = session_summary.details["global_turn_count"]
            if "main_agent_todos" in session_summary.details:
                insights["main_agent"] = {"todos": session_summary.details["main_agent_todos"]}
            if "started_at" in session_summary.details:
                insights["started_at"] = session_summary.details["started_at"]
            if "last_modified" in session_summary.details:
                insights["last_modified"] = session_summary.details["last_modified"]
            if "ended_at" in session_summary.details:
                insights["ended_at"] = session_summary.details["ended_at"]

        for _attr in (
            "agent",
            "commissioned_as",
            "parent_session",
            "launched_by",
            "subagent_type",
            "crew",
            "session_kind",
            "client",
            "surface",
            "provider",
        ):
            _val = getattr(session_summary, _attr, None)
            if _val:
                insights[_attr] = _val

    # Timeline events for path reconstruction
    if timeline_events:
        insights["timeline_events"] = timeline_events
        # Capture the user's initial intent so the dashboard can orient even on
        # no-reflection / still-running sessions (aops-efffc1f7).
        initial_prompt = extract_initial_prompt(timeline_events)
        if initial_prompt:
            insights["initial_prompt"] = initial_prompt
        # Elevate PR URL to root if found
        for event in timeline_events:
            if event.get("type") == "pr_create" and event.get("pr_url"):
                insights["pr_url"] = event["pr_url"]
                break

    try:
        # Check for existing insights. If the source jsonl has grown since the
        # previous run, we want to refresh rather than skip — but we preserve
        # any reflection-derived fields the existing file has (e.g. authored
        # by a later Framework Reflection or a previous reflection-bearing run).
        existing_path = find_existing_insights(date_str, session_id)
        if existing_path:
            existing = _load_existing_insights(existing_path)
            if existing is None:
                # Couldn't read — be conservative, don't clobber
                print(
                    f"⏭️  Insights already exist for session {session_id} (unreadable, "
                    f"skipping): {existing_path.name}"
                )
                return
            reason = _should_overwrite_existing(insights, existing)
            if not reason:
                print(f"⏭️  Insights already exist for session {session_id}: {existing_path.name}")
                return
            insights = _preserve_reflection_fields(insights, existing)
            # Reuse the existing file path so we overwrite in place rather
            # than creating a duplicate with a different slug.
            write_insights_file(existing_path, insights, session_id=session_id)
            print(
                f"🔄 Refreshed insights ({reason}, "
                f"{len(existing.get('timeline_events') or [])} → "
                f"{len(insights.get('timeline_events') or [])} events): {existing_path}"
            )
            return

        date_for_insights = (
            timestamp if timestamp else f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
        )
        insights_path = get_insights_file_path(
            date_for_insights, session_id, slug, None, project, shortform=shortform
        )
        write_insights_file(insights_path, insights, session_id=session_id)
        print(f"📊 Token metrics saved (no reflection): {insights_path}")
    except Exception as e:
        print(f"⚠️  Failed to save token metrics: {e}", file=sys.stderr)


def _process_reflection(
    entries: list,
    session_id: str,
    date_str: str,
    project: str,
    slug: str = "",
    agent_entries: dict | None = None,
    timestamp: datetime | None = None,
    usage_stats: "UsageStats | None" = None,
    session_duration_minutes: float | None = None,
    timeline_events: list[dict] | None = None,
    shortform: str | None = None,
    provider: str | None = None,
    session_path: Path | None = None,
    origin_override: dict[str, str | None] | None = None,
    session_ctx: dict | None = None,
    session_summary: ParsedSession | None = None,
) -> tuple[str | None, list[dict] | None]:
    """Extract reflections from entries and save to insights JSON files.

    Args:
        entries: List of parsed session entries
        session_id: 8-char session ID
        date_str: Date in YYYY-MM-DD format
        project: Project name
        slug: Short descriptive slug for the session filename
        agent_entries: Optional dict of agent/subagent entries
        timestamp: Optional datetime for ISO 8601 timestamp in insights
        usage_stats: Optional UsageStats for token_metrics field in insights
        session_duration_minutes: Optional session duration for efficiency metrics
        timeline_events: Optional list of timeline event dicts for path reconstruction

    Returns:
        Tuple of (combined_reflection_header_markdown, list_of_reflection_dicts)
        Both are None if no reflections found
    """
    reflections = extract_reflection_from_entries(entries, agent_entries)

    if not reflections:
        # No reflection found, but still save token_metrics if available
        if usage_stats and usage_stats.has_data():
            _save_minimal_token_summary(
                session_id,
                date_str,
                project,
                slug,
                timestamp,
                usage_stats,
                session_duration_minutes,
                timeline_events,
                shortform=shortform,
                provider=provider,
                session_path=session_path,
                origin_override=origin_override,
                session_ctx=session_ctx,
                session_summary=session_summary,
            )
        return None, None

    # Build display headers and per-reflection insights dicts in one pass.
    # Multiple reflections in a single session collapse into ONE summary file
    # with framework_reflections[] holding each entry, rather than the legacy
    # `-1.json`, `-2.json` sibling files (which duplicated all session-level
    # metadata). Old suffixed files are cleaned up below.
    headers = []
    per_reflection_insights = []
    for i, reflection in enumerate(reflections):
        header = format_reflection_header(reflection)
        if len(reflections) > 1:
            header = f"### Reflection {i + 1} of {len(reflections)}\n\n{header}"
        headers.append(header)

        per_reflection_insights.append(
            reflection_to_insights(
                reflection,
                session_id,
                date_str,
                project,
                timestamp=timestamp,
                usage_stats=usage_stats,
                session_duration_minutes=session_duration_minutes,
                # timeline_events is session-level; only attach once (last reflection
                # so the merged dict's scalar fields and timeline_events come from
                # the same source — i.e. the most recent reflection in the session).
                timeline_events=timeline_events if i == len(reflections) - 1 else None,
                provider=provider,
                session_path=session_path,
                origin_override=origin_override,
                session_ctx=session_ctx,
            )
        )

    # Merge all reflections into a single insights dict. Strategy:
    # - List fields (accomplishments, friction_points, proposed_changes,
    #   framework_reflections, ...) concatenate across reflections.
    # - Scalar fields (summary, outcome, next_step, root_cause, ...) take the
    #   last reflection's value — it represents the session's final state.
    # This is what `merge_insights` does, applied left-to-right.
    insights = per_reflection_insights[0]
    for nxt in per_reflection_insights[1:]:
        insights = merge_insights(insights, nxt)

    # Capture the user's initial intent (aops-efffc1f7). timeline_events is
    # attached to the last per-reflection dict, so it survives the merge above.
    initial_prompt = extract_initial_prompt(insights.get("timeline_events"))
    if initial_prompt:
        insights["initial_prompt"] = initial_prompt

    try:
        validate_insights_schema(insights)

        existing_path = find_existing_insights(date_str, session_id)
        if existing_path:
            existing = _load_existing_insights(existing_path)
            if existing is None:
                print(
                    f"⏭️  Insights already exist for session {session_id} (unreadable, "
                    f"skipping): {existing_path.name}"
                )
            else:
                reason = _should_overwrite_existing(insights, existing)
                if not reason:
                    print(
                        f"⏭️  Insights already exist for session {session_id}: {existing_path.name}"
                    )
                else:
                    insights = _preserve_reflection_fields(insights, existing)
                    write_insights_file(existing_path, insights, session_id=session_id)
                    print(
                        f"🔄 Refreshed insights ({reason}, "
                        f"{len(existing.get('timeline_events') or [])} → "
                        f"{len(timeline_events or [])} events, "
                        f"{len(reflections)} reflection(s)): {existing_path}"
                    )
                    _cleanup_legacy_suffixed_summaries(existing_path)
        else:
            date_for_insights = (
                timestamp if timestamp else f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
            )
            insights_path = get_insights_file_path(
                date_for_insights, session_id, slug, None, project, shortform=shortform
            )
            write_insights_file(insights_path, insights, session_id=session_id)
            print(f"💡 Saved insights ({len(reflections)} reflection(s)): {insights_path}")
            _cleanup_legacy_suffixed_summaries(insights_path)

        # Surface /dump quality warnings (missing Output / Tasks worked /
        # bare-id references / feature-suggestion smell). See
        # aops-core/skills/end_session/transcript-metadata-schema.md.
        for warning in insights.get("quality_warnings") or []:
            print(f"⚠️  Quality warning: {warning}", file=sys.stderr)
    except InsightsValidationError as e:
        print(f"⚠️  Insights validation failed: {e}", file=sys.stderr)
    except Exception as e:
        print(f"⚠️  Failed to save insights: {e}", file=sys.stderr)

    combined_header = "\n\n---\n\n".join(headers)
    return combined_header, reflections


def _is_test_session(p: Path) -> bool:
    """Heuristically detect obvious test/demo sessions to exclude from batch runs.

    Excludes paths under /tmp and filenames or parent folders containing
    keywords like test, demo, scratch, sample, example, tmp, local, dev.
    """
    s = str(p).lower()

    name = p.name.lower()
    parts = [part.lower() for part in p.parts]

    # Whitelist Gemini tmp directory
    if ".gemini/tmp" in s:
        return False

    # Whitelist Cowork audit logs (they contain 'local' in the path)
    if "local-agent-mode-sessions" in s and name == "audit.jsonl":
        return False

    # Exclude /tmp paths
    if s.startswith("/tmp") or "/tmp/" in s:
        return True

    keywords = (
        "test",
        "tests",
        "demo",
        "scratch",
        "sample",
        "example",
        "tmp",
        "local",
        "dev",
    )
    if any(k in name for k in keywords):
        return True
    if any(k in parts for k in keywords):
        return True

    return False


def _compute_session_duration(entries: list) -> float | None:
    """Compute session duration in minutes from entry timestamps.

    Args:
        entries: List of parsed session entries

    Returns:
        Duration in minutes, or None if timestamps unavailable
    """
    first_ts = None
    last_ts = None

    for entry in entries:
        if entry.timestamp:
            if first_ts is None:
                first_ts = entry.timestamp
            last_ts = entry.timestamp

    if first_ts and last_ts and first_ts != last_ts:
        delta = last_ts - first_ts
        return delta.total_seconds() / 60.0

    return None


def _output_exists(out_dir: Path, slug: str) -> bool:
    """Check if output files already exist for this session."""
    pattern = f"*{slug}*-full.md"
    return any(out_dir.glob(pattern))


def _filter_recent_sessions(sessions: list, days: int = 7) -> list:
    """Filter sessions to those modified within the last N days.

    Args:
        sessions: List of session objects (with .path attribute) or Path objects
        days: Number of days to look back (default: 7)

    Returns:
        Filtered list of sessions with mtime within the cutoff period
    """
    # Cutoff: midnight N days ago (local timezone)
    cutoff = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(
        days=days
    )
    cutoff_ts = cutoff.timestamp()

    filtered = []
    for s in sessions:
        session_path = s.path if hasattr(s, "path") else Path(str(s))
        if session_path.exists() and session_path.stat().st_mtime >= cutoff_ts:
            filtered.append(s)
    return filtered


def _get_session_id(session_path: Path) -> str:
    """Extract session ID from filename without parsing the file.

    Args:
        session_path: Path to session file

    Returns:
        8-character session ID
    """
    if session_path.is_dir():
        # Antigravity brain directory
        return session_path.name[:8]

    # Cowork ingested: cowork-logs/<session_id>/session.jsonl
    if session_path.name == "session.jsonl" and "cowork-logs" in str(session_path):
        return session_path.parent.name[:8]

    # Cowork: audit.jsonl inside local_<uuid>/ — extract ID from parent dir
    if session_path.name == "audit.jsonl":
        parent_name = session_path.parent.name  # local_<uuid>
        uuid_part = parent_name.replace("local_", "")
        return uuid_part[:8]

    session_id = session_path.stem
    if len(session_id) > 8:
        if session_id.startswith("session-"):
            # Gemini format: session-2026-01-08T08-18-a5234d3e -> a5234d3e
            parts = session_id.split("-")
            session_id = parts[-1]
        else:
            # Claude format: UUID -> first 8 chars
            session_id = session_id[:8]
    return session_id


# GHA agents (rbg, merge-prep, enforcer-review, fix, review, …) inject their
# own ``name: <slug>`` frontmatter at the head of the very first user prompt.
# Extracting that slug recovers the workflow identity even when we're seeing
# the jsonl long after the action ran (no artifact name available).
_GHA_NAME_FRONTMATTER = re.compile(
    r"(?im)^---\s*\n(?:.*\n)*?name:\s*([A-Za-z][A-Za-z0-9_-]*)\s*\n",
)
_GHA_NAME_SIMPLE = re.compile(r"(?im)^name:\s*([A-Za-z][A-Za-z0-9_-]*)\b")


def _infer_agent_from_entries(entries: list) -> str | None:
    """Heuristically identify which agent/workflow drove a session.

    Extracts the ``name:`` slug from the agent frontmatter in the first user prompt
    (e.g. ``name: rbg``, ``name: merge-prep``, ``name: enforcer-review``).
    """

    def _entry_text(entry) -> str:
        msg = (
            getattr(entry, "message", None) or {}
        )  # allow-fallback: synthetic entries have no message
        content = msg.get("content") if isinstance(msg, dict) else None
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = []
            for block in content:
                if isinstance(block, dict):
                    t = block.get("text") or block.get("content") or ""
                    if isinstance(t, str):
                        parts.append(t)
                elif isinstance(block, str):
                    parts.append(block)
            return "\n".join(parts)
        return ""

    # Walk forward until we hit a user-role message with content. GHA jsonls
    # are front-padded with synthetic ``ai-title`` / ``last-prompt`` entries
    # before the real first user prompt, so the first few slots are usually
    # empty.
    sample = ""
    for entry in entries[:40]:
        msg = (
            getattr(entry, "message", None) or {}
        )  # allow-fallback: synthetic entries have no message
        if isinstance(msg, dict) and msg.get("role") and msg.get("role") != "user":
            continue
        text = _entry_text(entry)
        if text:
            sample = text[:4096]
            break
    if not sample:
        return None

    # Prefer fenced YAML frontmatter (---\nname: …\n…\n---) since it's the
    # canonical agent identity. Fall back to a bare `name:` line for prompts
    # that injected the agent header without fences.
    match = _GHA_NAME_FRONTMATTER.search(sample) or _GHA_NAME_SIMPLE.search(sample)
    if match:
        return match.group(1).lower()
    return None


def _populate_session_linkage(session_summary: "ParsedSession", entries: list) -> None:
    """Populate agent identity and parent/spawn linkage fields on session_summary."""
    agent_name = _infer_agent_from_entries(entries)
    if agent_name:
        session_summary.agent = agent_name
        session_summary.commissioned_as = agent_name
        if not session_summary.session_kind:
            session_summary.session_kind = "subagent"

    if entries:
        first_entry = entries[0]
        if first_entry.hook_context:
            parent_id = first_entry.hook_context.get("parent_session_id")
            if parent_id:
                session_summary.parent_session = parent_id
                session_summary.launched_by = parent_id
            sub_type = first_entry.hook_context.get("subagent_type")
            if sub_type:
                session_summary.subagent_type = sub_type

        # Fallback to direct entry fields (for CC 2.1 native subagents)
        if not session_summary.parent_session and first_entry.parent_uuid:
            session_summary.parent_session = first_entry.parent_uuid[:8]
            session_summary.launched_by = first_entry.parent_uuid[:8]
        if not session_summary.subagent_type and first_entry.subagent_id:
            session_summary.subagent_type = first_entry.subagent_id


def _generate_transcript_filename(
    session_path: Path,
    entries: list,
    slug: str | None = None,
    processor: "SessionProcessor | None" = None,
    shortform: str | None = None,
) -> tuple[str, str, str, str, str]:
    """Generate consistent transcript filename using session_naming."""
    # 1. Detect crew_name from path if applicable
    # (Matches _infer_project's Polecat/Crew logic)
    crew_name = None
    parts = session_path.parts
    for category_plural in ("polecats", "crew"):
        if category_plural in parts:
            idx = parts.index(category_plural)
            if len(parts) > idx + 1:
                crew_name = parts[idx + 1]
                break

    # 2. Detect provider from path
    provider = session_naming.infer_provider_from_path(session_path)

    # 3. Get timestamp
    timestamp = None
    for entry in entries:
        if entry.timestamp:
            timestamp = entry.timestamp
            break
    if not timestamp:
        timestamp = datetime.fromtimestamp(session_path.stat().st_mtime).astimezone()

    # 4. Project/Repo
    repo = _infer_project(session_path, entries)

    # 4b. Synthesise a "gha-…" shortform when batch-mode discovery picks up a
    # GHA session directly out of $AOPS_SESSIONS/github/. Without this the
    # transcript filename collapses to "academicops-claude" and loses the
    # workflow distinction that sync_gha_sessions.py would have preserved.
    # Layout: github/<repo>/<run_id>/<attempt>/<workspace>/<uuid>.jsonl
    if shortform is None and "github" in parts:
        idx = parts.index("github")
        if len(parts) > idx + 1:
            repo_slug = parts[idx + 1]
            workflow = _infer_agent_from_entries(entries)
            workflow_segment = f"-{workflow}" if workflow else ""
            shortform = f"gha{workflow_segment}-{repo_slug}-claude"

    # 5. Session ID
    session_id = _get_session_id(session_path)

    # 6. Slug — only used when explicitly provided via --slug CLI arg.
    # No auto-generation from session content: transcript filenames are deterministic.

    # Generate base name via naming module
    # (unified format: {YYYYMMDD}-{HHMM}-{session_id}-{shortform} or with explicit slug)
    # task_id from $AOPS_TASK_ID is passed through so transcript filenames are task-grep-friendly.
    base = session_naming.generate_base_name(
        session_id=session_id,
        timestamp=timestamp,
        slug=slug or None,
        crew_name=crew_name,
        repo=repo,
        provider=provider,
        shortform=shortform,
        task_id=os.environ.get("AOPS_TASK_ID"),
    )

    # Return components for compatibility with transcript.py callers
    # filename (base), date_str, short_project, session_id, slug
    return (
        base,
        timestamp.astimezone().strftime("%Y%m%d"),
        repo,
        session_id,
        slug or "",
    )


def _find_existing_transcripts(out_dir: Path, session_id: str) -> list[Path]:
    """Find all existing transcript files by session ID.

    Args:
        out_dir: Output directory to search
        session_id: 8-character session ID

    Returns:
        List of all matching transcript files (both -full.md and -abridged.md)
    """
    # Search for transcripts with this session_id across both the flat legacy
    # layout (``transcripts/<file>``) and the rotated layout
    # (``transcripts/YYYY-MM/<file>``) introduced for aops-b975b185.
    # v4.0.0+ Pattern: YYYYMMDD-HHMM-sessionID-shortform-slug-variant.md
    # v3.7.0+ Pattern: with hour (e.g., 20260105-17-writing-3bf94f77-session-full.md)
    # Legacy Pattern: without hour (e.g., 20260105-writing-3bf94f77-session-full.md)
    matches: list[Path] = []
    for suffix in ("-full.md", "-abridged.md"):
        # Unified format with HHMM (4 digits)
        matches.extend(iter_rotated_files(out_dir, f"*-????-{session_id}-*{suffix}"))
        # Format with hour (2 digits)
        matches.extend(iter_rotated_files(out_dir, f"*-??-*-{session_id}-*{suffix}"))
        matches.extend(iter_rotated_files(out_dir, f"*-??-*-{session_id}{suffix}"))
        # Legacy format without hour
        matches.extend(iter_rotated_files(out_dir, f"*-{session_id}-*{suffix}"))
        matches.extend(iter_rotated_files(out_dir, f"*-{session_id}{suffix}"))
    return list(set(matches))  # Deduplicate


def _find_existing_transcript(out_dir: Path, session_id: str) -> Path | None:
    """Find existing transcript file by session ID.

    Args:
        out_dir: Output directory to search
        session_id: 8-character session ID

    Returns:
        Path to existing -full.md transcript if found, None otherwise
    """
    matches = [
        p for p in _find_existing_transcripts(out_dir, session_id) if p.name.endswith("-full.md")
    ]
    return matches[0] if matches else None


def _transcript_is_current(session_path: Path, transcript_path: Path) -> bool:
    """Check if transcript is current (newer than session file).

    Args:
        session_path: Path to source session file
        transcript_path: Path to transcript file

    Returns:
        True if transcript mtime >= session mtime
    """
    return transcript_path.stat().st_mtime >= session_path.stat().st_mtime


def _infer_project(
    session_path: Path,
    entries: list | None = None,
) -> str:
    """Infer project name from session path and/or entries.

    Uses multiple strategies:
    1. For Claude sessions: decode the project folder name (-home-nic-src-myproject)
    2. For Antigravity brain directories: try to extract from content
    3. For Gemini sessions: use hash prefix
    4. Fallback: extract from path or use "unknown"

    Args:
        session_path: Path to session file or directory
        entries: Optional list of parsed session entries for content-based extraction

    Returns:
        Project name string
    """
    # Handle Cowork ingested sessions — both the parent thread (session.jsonl)
    # and the nested native task bundles (<task-uuid>.jsonl), which both live
    # under cowork-logs/ and carry a metadata.json holding the conversation
    # title. Naming both from that title files the recovered subagent bundles
    # under the same `cowork-<title>` repo as their parent, so they group
    # together and are findable when browsing cowork transcripts (GH #1621).
    # This drives BOTH the filename slug token and the frontmatter `repo:` field.
    if "cowork-logs" in str(session_path) and session_path.suffix == ".jsonl":
        metadata_json = session_path.parent / "metadata.json"
        if metadata_json.exists():
            try:
                import json as _json

                meta = _json.loads(metadata_json.read_text())
                title = meta.get("title", "")
                if title:
                    words = title.lower().split()[:3]
                    return "cowork-" + "-".join(w for w in words if w.isalnum())
            except (OSError, ValueError):
                pass
        return "cowork"

    # Handle Cowork audit.jsonl — infer project from metadata JSON
    if session_path.name == "audit.jsonl":
        conv_dir = session_path.parent  # local_<uuid>/
        org_dir = conv_dir.parent
        metadata_json = org_dir / f"{conv_dir.name}.json"
        if metadata_json.exists():
            try:
                import json as _json

                meta = _json.loads(metadata_json.read_text())
                title = meta.get("title", "")
                if title:
                    words = title.lower().split()[:3]
                    return "cowork-" + "-".join(w for w in words if w.isalnum())
            except (OSError, ValueError):
                pass
        return "cowork"

    # Handle Antigravity brain directories
    if session_path.is_dir():
        # Authoritative source first: agy maps each conversation UUID (the brain
        # dir name) to its workspace via history.jsonl / last_conversations.json.
        # The new antigravity-cli format carries no "Working directory:" line in
        # its transcript, so content-scraping below would otherwise fall back to
        # the bare "antigravity" default and lose the real project.
        try:
            from lib.session_reader import _load_agy_workspace_map

            workspace = _load_agy_workspace_map().get(session_path.name)
            if workspace:
                return _resolve_project_key(Path(workspace).name)
        except Exception:  # noqa: BLE001 — never let project inference hard-fail
            pass

        # Try to extract working dir from brain content
        if entries:
            working_dir = extract_working_dir_from_entries(entries)
            if working_dir:
                project = infer_project_from_working_dir(working_dir)
                if project:
                    return _resolve_project_key(project)

        # Try to extract from markdown content in the brain directory
        for md_file in ["task.md", "implementation_plan.md"]:
            md_path = session_path / md_file
            if md_path.exists():
                try:
                    content = md_path.read_text(encoding="utf-8")
                    working_dir = extract_working_dir_from_content(content)
                    if working_dir:
                        project = infer_project_from_working_dir(working_dir)
                        if project:
                            return _resolve_project_key(project)
                except OSError:
                    continue

        return "antigravity"  # Default for brain directories

    # Handle Gemini JSON/JSONL sessions (Gemini chat dumps may use either ext)
    if session_path.suffix in (".json", ".jsonl"):
        project = session_path.parent.name
        if project == "chats":
            return normalize_gemini_project(session_path.parent.parent.name)
        # ``.json`` extension alone is a strong Gemini signal (Claude uses
        # .jsonl for transcripts), but ``.jsonl`` is shared — fall through so
        # Claude/Polecat detection can run.
        if session_path.suffix == ".json":
            return "gemini"

    # Handle Polecat/Crew sessions.
    # Path layout: {category}/{worker_name}/{project}/...
    # We want the project (the segment AFTER the worker), not
    # ``{category}-{worker}`` — the worker is already carried separately
    # via ``crew_name`` and stuffing it into ``repo`` produces redundant
    # filenames like ``jewelle-crewjewelle-…``. Use path parts directly
    # to avoid false positives from partial string matches.
    parts = session_path.parts
    for category_plural in ("polecats", "crew"):
        if category_plural in parts:
            idx = parts.index(category_plural)
            if len(parts) > idx + 2:
                project = parts[idx + 2]
                # Skip workspace markers and reach the real project dir.
                if project.lstrip("-_") and not project.startswith(("-workspace", "_workspace")):
                    return _resolve_project_key(project)
            # Fallback when there's no project segment: return ``{category}``
            # (singular) so downstream still has a sensible repo name without
            # duplicating the worker.
            return category_plural.rstrip("s")

    # Handle Claude JSONL sessions
    project = session_path.parent.name

    # Try to extract project from entries first
    if entries:
        working_dir = extract_working_dir_from_entries(entries)
        if working_dir:
            inferred = infer_project_from_working_dir(working_dir)
            if inferred:
                return _resolve_project_key(inferred)

    # Decode Claude project path format: -home-nic-src-myproject
    if project.startswith("-"):
        return _resolve_project_key(project, match_suffix=True)

    # Fallback: do not truncate, just resolve the name verbatim
    clean_project = project.strip("-")
    return _resolve_project_key(clean_project) if clean_project else "unknown"


def _emit_subagent_artifacts(
    session_path: Path,
    parent_session_id: str,
    session_summary,
    entries,
    agent_entries,
    processor,
    parent_full_path: Path,
) -> None:
    """Emit per-subagent transcripts + insights and link from the parent.

    No-op when ``agent_entries`` is empty (most sessions have zero
    subagent invocations). Failures here are non-fatal — the parent
    transcript has already been written by the time we run.
    """
    if not agent_entries:
        return
    try:
        # Main thread = parent's non-sidechain entries (subagent invocations
        # are loaded via _load_agent_files and carry is_sidechain=True on
        # their own entries).
        main_entries = [e for e in entries if not getattr(e, "is_sidechain", False)]
        artifacts = write_subagent_transcripts(
            parent_session_path=session_path,
            parent_session_id=parent_session_id,
            parent_summary=session_summary,
            main_entries=main_entries,
            agent_entries=agent_entries,
            processor=processor,
        )
        if artifacts:
            print(f"🧵 Emitted {len(artifacts)} subagent transcript(s)")
            for art in artifacts:
                if art.transcript_path:
                    print(
                        f"   ↳ {art.subagent_type or 'unknown'} ({art.child_session_id}): "
                        f"{art.transcript_path}"
                    )
            maybe_append_subagent_footer(parent_full_path, artifacts)
    except Exception as e:  # noqa: BLE001
        print(f"⚠️  Subagent transcript emission failed: {e}", file=sys.stderr)


def git_sync():
    """Commit and push changes in the sessions repository."""
    try:
        sessions_root = get_sessions_repo()
        if not (sessions_root / ".git").exists():
            print(f"Skipping git sync: {sessions_root} is not a git repository")
            return

        print(f"Syncing changes in {sessions_root}...")

        # Policy: only transcripts/, summaries/, and their subagent siblings
        # are pushed. Raw substrate (client-logs/, hooks/, polecats/, github/)
        # is local-only — see PKB kb-d8f58167 (Session Log Observability Map).
        # Subagent dirs (task-b483e037) follow the same policy. ``--ignore-errors``
        # tolerates the case where a directory doesn't exist yet (e.g. a sessions
        # repo that has never had any subagent invocations).
        subprocess.run(
            [
                "git",
                "add",
                "--ignore-errors",
                "transcripts/",
                "summaries/",
                "subagent-transcripts/",
                "subagent-summaries/",
            ],
            cwd=str(sessions_root),
            check=False,
        )

        status = subprocess.run(
            ["git", "diff", "--cached", "--quiet"], cwd=str(sessions_root), check=False
        ).returncode

        if status == 0:
            print("No changes to sync.")
            return

        commit_msg = "Auto-commit: session transcripts and insights updated"
        subprocess.run(["git", "commit", "-m", commit_msg], cwd=str(sessions_root), check=True)
        print("Committed changes.")

        print("Attempting push...")
        push_result = subprocess.run(
            ["git", "push"], cwd=str(sessions_root), capture_output=True, text=True
        )

        if push_result.returncode == 0:
            print("Push successful.")
        else:
            print(f"Push failed (non-blocking):\n{push_result.stderr}")

    except Exception as e:
        print(f"Git sync failed: {e}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(
        description="Convert Claude Code JSONL or Gemini JSON sessions to markdown transcripts",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python transcript.py session.jsonl                    # Auto-names in sessions/claude/
  python transcript.py session.json                     # Generates Gemini transcript
  python transcript.py session.jsonl -o transcript      # Uses sessions/claude/transcript-{full,abridged}.md
  python transcript.py session.jsonl -o /abs/path/name  # Uses absolute path
  python transcript.py                                  # Process recent sessions (last 7 days, default)
  python transcript.py --all                            # Process ALL sessions in ~/.claude/projects/
        """,
    )

    parser.add_argument(
        "session_file",
        nargs="?",
        help="Path to Session file (Claude .jsonl or Gemini .json)",
    )
    parser.add_argument(
        "-o", "--output", help="Output base name (generates -full.md and -abridged.md)"
    )
    parser.add_argument(
        "--slug",
        help="Brief slug describing session work (auto-generated if not provided)",
    )
    parser.add_argument(
        "--shortform",
        help="Explicit shortform to use in the filename (overrides crew/repo detection)",
    )
    parser.add_argument(
        "--recent",
        action="store_true",
        default=True,
        help="Process sessions from last 7 days (default behavior)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Process ALL sessions (overrides --recent filter)",
    )
    parser.add_argument(
        "--no-sync",
        action="store_true",
        help="Skip git commit and push after generating transcripts",
    )

    args = parser.parse_args()

    # Default output directory
    sessions_claude = get_transcripts_dir()
    sessions_claude.mkdir(parents=True, exist_ok=True)

    processor = SessionProcessor()

    # Batch mode: process sessions (default when no file specified)
    # --recent (default): last 7 days only
    # --all: all sessions regardless of date
    if args.all or not args.session_file:
        sessions = find_sessions()
        if not sessions:
            print("No sessions found.", file=sys.stderr)
            return 0

        # Load transcript config for project exclusion
        transcript_config = _load_transcript_config()

        # Exclude obvious test/demo sessions
        sessions = [
            s
            for s in sessions
            if not _is_test_session(s.path if hasattr(s, "path") else Path(str(s)))
        ]

        # Exclude configured projects (e.g. sessions repo)
        if transcript_config.get("exclude_projects"):
            before = len(sessions)
            sessions = [
                s
                for s in sessions
                if not _is_excluded_project(
                    s.project if hasattr(s, "project") and s.project else "", transcript_config
                )
            ]
            excluded = before - len(sessions)
            if excluded:
                print(f"🚫 Excluded {excluded} sessions from configured projects")

        # Apply --recent filter (default) unless --all specified
        if not args.all:
            original_count = len(sessions)
            sessions = _filter_recent_sessions(sessions, days=7)
            print(f"📅 Filtering to last 7 days: {len(sessions)} of {original_count} sessions")

        # Process newest sessions first (reverse chronological)
        sessions = sorted(
            sessions,
            key=lambda s: s.path.stat().st_mtime if hasattr(s, "path") and s.path.exists() else 0,
            reverse=True,
        )

        processed = 0
        skipped = 0
        errors = 0

        for s in sessions:
            session_path = Path(str(s))
            try:
                session_path = s.path if hasattr(s, "path") else session_path
                session_id = _get_session_id(session_path)

                # Early mtime check: skip if transcript already exists and is current
                existing_transcript = _find_existing_transcript(sessions_claude, session_id)
                if existing_transcript and _transcript_is_current(
                    session_path, existing_transcript
                ):
                    skipped += 1
                    continue

                # Process the session
                print(f"📝 Processing session: {session_path}")
                session_summary, entries, agent_entries = processor.parse_session_file(
                    str(session_path)
                )

                # Augment summary with inferred metadata (aops-d9ba7159)
                session_summary.repo = session_summary.repo or _infer_project(session_path, entries)
                session_summary.machine = session_summary.machine or os.environ.get("AOPS_MACHINE")
                session_summary.hostname = session_summary.hostname or session_naming.get_hostname()
                session_summary.task_id = session_summary.task_id or os.environ.get("AOPS_TASK_ID")
                # Crew and provider are already partially handled by parse_session_file,
                # but let's be thorough.
                if not session_summary.crew:
                    for category_plural in ("polecats", "crew"):
                        if category_plural in session_path.parts:
                            idx = session_path.parts.index(category_plural)
                            if len(session_path.parts) > idx + 1:
                                session_summary.crew = session_path.parts[idx + 1]
                                break
                if not session_summary.provider:
                    session_summary.provider = session_naming.infer_provider_from_path(session_path)

                # Resolve launch surface/client. Path-based detection handles
                # GHA / crew / polecat / Gemini; entry-content scan upgrades a
                # bare claude-code-cli to claude-code-desktop when the JSONL
                # references the Claude Desktop GUI's LAM plugin cache.
                path_origin = session_naming.infer_session_origin_from_path(
                    session_path, provider=session_summary.provider
                )
                session_origin = session_naming.infer_session_origin_from_entries(
                    entries, path_origin
                )
                session_summary.surface = session_summary.surface or session_origin.get("surface")
                session_summary.client = session_summary.client or session_origin.get("client")

                # Check for meaningful content — polecats have exactly 1 user + 1
                # agent turn so we accept sessions with at least 1 meaningful entry.
                MIN_MEANINGFUL_ENTRIES = 1
                meaningful_count = sum(
                    1
                    for e in entries
                    if e.type in ("user", "assistant")
                    and not (
                        hasattr(e, "message")
                        and e.message
                        and e.message.get("subtype") in ("system", "informational")
                    )
                )
                if meaningful_count < MIN_MEANINGFUL_ENTRIES:
                    print(
                        f"⏭️  Skipping: only {meaningful_count} meaningful entries (need {MIN_MEANINGFUL_ENTRIES}+)"
                    )
                    skipped += 1
                    continue

                # ── Content check passed ── File mutations permitted from this point ──
                # No rename/delete may precede this line; the check above is the gate.

                # Generate output name (always computed for metadata: date_str, project, slug)
                (
                    filename,
                    date_str,
                    short_project,
                    session_id,
                    slug,
                ) = _generate_transcript_filename(session_path, entries, processor=processor)

                # Re-render: reuse the existing transcript's base name so re-renders
                # write to the same path (idempotent, no churn).
                # First render: generate rotated output path normally (aops-b975b185).
                if existing_transcript:
                    base_name = str(existing_transcript)[: -len("-full.md")]
                else:
                    rotation_dt = extract_date_from_filename(filename) or datetime.strptime(
                        date_str, "%Y%m%d"
                    ).replace(tzinfo=UTC)
                    out_subdir = ensure_rotated_dir(sessions_claude, rotation_dt)
                    base_name = str(out_subdir / filename)
                    # Remove any stale transcripts for this session now that we're
                    # writing a fresh one (slug was previously volatile; clean up orphans).
                    stale_files = _find_existing_transcripts(sessions_claude, session_id)
                    new_paths = {
                        Path(f"{base_name}-full.md").resolve(),
                        Path(f"{base_name}-abridged.md").resolve(),
                    }
                    for stale in stale_files:
                        if stale.resolve() not in new_paths:
                            print(f"🗑️  Removing stale transcript: {stale.name}")
                            try:
                                stale.unlink()
                            except OSError as e:
                                print(
                                    f"⚠️  Could not remove stale transcript {stale}: {e}",
                                    file=sys.stderr,
                                )

                # Extract and process reflection (if present)
                # Convert date format from YYYYMMDD to YYYY-MM-DD for insights
                date_iso = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
                # Get timestamp from entries for ISO 8601 output
                session_timestamp = None
                for entry in entries:
                    if entry.timestamp:
                        session_timestamp = entry.timestamp.astimezone()
                        break

                # Compute usage stats and session duration for token_metrics
                usage_stats = processor._aggregate_session_usage(entries, agent_entries)
                session_duration_minutes = _compute_session_duration(entries)

                # Extract timeline events for path reconstruction
                turns = processor.group_entries_into_turns(entries, agent_entries)
                timeline_events = extract_timeline_events(turns, session_id)

                # Augment summary with explicit session metadata from entries (CC 2.1+)
                session_ctx = aggregate_session_metadata(entries)
                session_summary.session_kind = session_ctx.get("session_kind")
                session_summary.user_type = session_ctx.get("user_type")
                session_summary.entrypoint = session_ctx.get("entrypoint")
                session_summary.cwd = session_ctx.get("cwd")
                session_summary.client_version = session_ctx.get("client_version")
                session_summary.git_branches = session_ctx.get("git_branches", [])
                session_summary.permission_modes = session_ctx.get("permission_modes", [])
                session_summary.models = session_ctx.get("models", [])
                session_summary.permission_denials = session_ctx.get(
                    "permission_denials", []
                )  # allow-fallback: absent on pre-classifier sessions
                session_summary.terminal_reason = session_ctx.get("terminal_reason")

                # Auto-mode classifier denials live on the result envelope, not in
                # the per-turn stream — surface each as an explicit timeline event so
                # the evidence loop (/retro, /trend-review) can measure fire rate.
                for _d in (
                    session_summary.permission_denials
                    or []  # allow-fallback: field always exists but may be falsy
                ):
                    _dn = _d if isinstance(_d, dict) else {}
                    tool_name = _dn.get("tool_name") or _dn.get("toolName")
                    tool_use_id = _dn.get("tool_use_id") or _dn.get("toolUseId")
                    timeline_events.append(
                        {
                            "timestamp": None,
                            "type": "permission_denial",
                            "tool": tool_name,
                            "tool_use_id": tool_use_id,
                            "description": (f"auto-mode denied {tool_name} ({tool_use_id})"),
                        }
                    )

                _populate_session_linkage(session_summary, entries)

                session_summary.session_type = session_naming.classify_session_type(
                    session_summary.surface,
                    client=session_summary.client,
                    task_id=session_summary.task_id,
                    subagent_type=session_summary.subagent_type,
                    parent_session=session_summary.parent_session,
                    crew=session_summary.crew,
                    session_kind=session_summary.session_kind,
                    initial_prompt=extract_initial_prompt(timeline_events),
                )
                session_summary.pull_requests = _resolve_pr_numbers(
                    session_summary.git_branches, session_summary.repo
                )

                # Fetch existing outcome if available (from insights JSON)
                existing_path = find_existing_insights(date_iso, session_id)
                if existing_path:
                    existing_insights = _load_existing_insights(existing_path)
                    if existing_insights:
                        session_summary.outcome = existing_insights.get("outcome")

                reflection_header, _ = _process_reflection(
                    entries,
                    session_id,
                    date_iso,
                    short_project,
                    slug,
                    agent_entries,
                    session_timestamp,
                    usage_stats,
                    session_duration_minutes,
                    timeline_events,
                    provider=session_summary.provider,
                    session_path=session_path,
                    origin_override=session_origin,
                    session_ctx=session_ctx,
                    session_summary=session_summary,
                )

                # Generate full version
                full_path = Path(f"{base_name}-full.md")
                markdown_full = processor.format_session_as_markdown(
                    session_summary,
                    entries,
                    agent_entries,
                    include_tool_results=True,
                    variant="full",
                    source_file=str(session_path.resolve()),
                    reflection_header=reflection_header,
                    usage_stats=usage_stats,
                    session_duration_minutes=session_duration_minutes,
                )
                with open(full_path, "w", encoding="utf-8") as f:
                    f.write(markdown_full)
                format_markdown(full_path)
                file_size = full_path.stat().st_size
                print(f"✅ Full transcript: {full_path} ({file_size:,} bytes)")

                # Generate abridged version
                abridged_path = Path(f"{base_name}-abridged.md")
                markdown_abridged = processor.format_session_as_markdown(
                    session_summary,
                    entries,
                    agent_entries,
                    include_tool_results=False,
                    variant="abridged",
                    source_file=str(session_path.resolve()),
                    reflection_header=reflection_header,
                    usage_stats=usage_stats,
                    session_duration_minutes=session_duration_minutes,
                )
                with open(abridged_path, "w", encoding="utf-8") as f:
                    f.write(markdown_abridged)
                format_markdown(abridged_path)
                file_size = abridged_path.stat().st_size
                print(f"✅ Abridged transcript: {abridged_path} ({file_size:,} bytes)")

                # Emit per-subagent transcripts + insights (task-b483e037)
                _emit_subagent_artifacts(
                    session_path=session_path,
                    parent_session_id=session_id,
                    session_summary=session_summary,
                    entries=entries,
                    agent_entries=agent_entries,
                    processor=processor,
                    parent_full_path=full_path,
                )

                processed += 1

            except Exception as e:
                errors += 1
                print(f"❌ Error processing {session_path}: {e}", file=sys.stderr)

        print(f"Processed: {processed}", file=sys.stderr)
        print(f"Skipped: {skipped}", file=sys.stderr)
        print(f"Errors: {errors}", file=sys.stderr)

        return 0

    # Single session mode (specific file provided)
    # Validate input file
    session_path = Path(args.session_file)
    if not session_path.exists():
        print(f"❌ Error: File not found: {session_path}")
        return 1

    # Check if this is a hooks file and find the actual session file
    if session_path.name.endswith("-hooks.jsonl"):
        import json

        with open(session_path) as f:
            first_line = f.readline().strip()
            if first_line:
                try:
                    data = json.loads(first_line)
                    transcript_path = data.get("transcript_path")
                    if transcript_path:
                        actual_session = Path(transcript_path)
                        if actual_session.exists():
                            print(f"⚠️  Hooks file provided. Using actual session: {actual_session}")
                            session_path = actual_session
                        else:
                            print(
                                f"❌ Error: Hooks file references missing session: {transcript_path}"
                            )
                            return 1
                except json.JSONDecodeError:
                    print("❌ Error: Could not parse hooks file")
                    return 1

    # Process the session
    try:
        print(f"📝 Processing session: {session_path}")

        session_id = _get_session_id(session_path)

        session_summary, entries, agent_entries = processor.parse_session_file(str(session_path))

        # Augment summary with inferred metadata (aops-d9ba7159)
        session_summary.repo = session_summary.repo or _infer_project(session_path, entries)
        session_summary.machine = session_summary.machine or os.environ.get("AOPS_MACHINE")
        session_summary.hostname = session_summary.hostname or session_naming.get_hostname()
        session_summary.task_id = session_summary.task_id or os.environ.get("AOPS_TASK_ID")
        if not session_summary.crew:
            for category_plural in ("polecats", "crew"):
                if category_plural in session_path.parts:
                    idx = session_path.parts.index(category_plural)
                    if len(session_path.parts) > idx + 1:
                        session_summary.crew = session_path.parts[idx + 1]
                        break
        if not session_summary.provider:
            session_summary.provider = session_naming.infer_provider_from_path(session_path)

        # Resolve launch surface/client. Path-based detection handles
        # GHA / crew / polecat / Gemini; entry-content scan upgrades a
        # bare claude-code-cli to claude-code-desktop when the JSONL
        # references the Claude Desktop GUI's LAM plugin cache.
        path_origin = session_naming.infer_session_origin_from_path(
            session_path, provider=session_summary.provider
        )
        session_origin = session_naming.infer_session_origin_from_entries(entries, path_origin)
        session_summary.surface = session_summary.surface or session_origin.get("surface")
        session_summary.client = session_summary.client or session_origin.get("client")

        # Generate output base name
        output_dir = None
        base_name = None

        if args.output:
            output_path = Path(args.output)

            # Check if -o is a directory path
            if output_path.is_dir():
                # Use the directory but auto-generate filename
                output_dir = output_path
                # Will fall through to auto-generation logic below
            else:
                output_base = args.output
                # Strip .md suffix if provided
                if output_base.endswith(".md"):
                    output_base = output_base[:-3]
                # Strip -full or -abridged suffix if provided
                if output_base.endswith("-full") or output_base.endswith("-abridged"):
                    output_base = output_base.rsplit("-", 1)[0]

                # If output is just a basename (no directory), place in sessions/claude/
                output_path = Path(output_base)
                if not output_path.is_absolute() and output_path.parent == Path("."):
                    base_name = str(sessions_claude / output_base)
                else:
                    base_name = output_base

        # If base_name was set (explicit output file specified), use explicit path logic
        if base_name:
            print(f"📊 Found {len(entries)} entries")

            # Check for meaningful content — accept sessions with at least 1 entry.
            MIN_MEANINGFUL_ENTRIES = 1
            meaningful_count = sum(
                1
                for e in entries
                if e.type in ("user", "assistant")
                and not (
                    hasattr(e, "message")
                    and e.message
                    and e.message.get("subtype") in ("system", "informational")
                )
            )
            if meaningful_count < MIN_MEANINGFUL_ENTRIES:
                print(
                    f"⏭️  Skipping: only {meaningful_count} meaningful entries (need {MIN_MEANINGFUL_ENTRIES}+)"
                )
                return 2

            # Extract reflection (get date and project from path for insights)
            date_iso = datetime.now().astimezone().replace(microsecond=0).isoformat()
            session_timestamp = None
            for entry in entries:
                if entry.timestamp:
                    date_iso = entry.timestamp.astimezone().strftime("%Y-%m-%d")
                    session_timestamp = entry.timestamp.astimezone()
                    break
            # Get session ID and project from path
            sid = _get_session_id(session_path)
            proj = _infer_project(session_path, entries)
            slug = ""

            # Compute usage stats and session duration for token_metrics
            usage_stats = processor._aggregate_session_usage(entries, agent_entries)
            session_duration_minutes = _compute_session_duration(entries)

            # Extract timeline events for path reconstruction
            turns = processor.group_entries_into_turns(entries, agent_entries)
            timeline_events = extract_timeline_events(turns, sid)

            # Augment summary with explicit session metadata from entries (CC 2.1+)
            session_ctx = aggregate_session_metadata(entries)
            session_summary.session_kind = session_ctx.get("session_kind")
            session_summary.user_type = session_ctx.get("user_type")
            session_summary.entrypoint = session_ctx.get("entrypoint")
            session_summary.cwd = session_ctx.get("cwd")
            session_summary.client_version = session_ctx.get("client_version")
            session_summary.git_branches = session_ctx.get("git_branches", [])
            session_summary.permission_modes = session_ctx.get("permission_modes", [])
            session_summary.models = session_ctx.get("models", [])

            _populate_session_linkage(session_summary, entries)

            session_summary.session_type = session_naming.classify_session_type(
                session_summary.surface,
                client=session_summary.client,
                task_id=session_summary.task_id,
                subagent_type=session_summary.subagent_type,
                parent_session=session_summary.parent_session,
                crew=session_summary.crew,
                session_kind=session_summary.session_kind,
                initial_prompt=extract_initial_prompt(timeline_events),
            )
            session_summary.pull_requests = _resolve_pr_numbers(
                session_summary.git_branches, session_summary.repo
            )

            reflection_header, _ = _process_reflection(
                entries,
                sid,
                date_iso,
                proj,
                slug,
                agent_entries,
                session_timestamp,
                usage_stats,
                session_duration_minutes,
                timeline_events,
                provider=session_summary.provider,
                session_path=session_path,
                origin_override=session_origin,
                session_ctx=session_ctx,
                session_summary=session_summary,
            )

            # Generate transcripts and return
            full_path = Path(f"{base_name}-full.md")
            markdown_full = processor.format_session_as_markdown(
                session_summary,
                entries,
                agent_entries,
                include_tool_results=True,
                variant="full",
                source_file=str(session_path.resolve()),
                reflection_header=reflection_header,
                usage_stats=usage_stats,
                session_duration_minutes=session_duration_minutes,
            )
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(markdown_full)
            format_markdown(full_path)
            file_size = full_path.stat().st_size
            print(f"✅ Full transcript: {full_path} ({file_size:,} bytes)")

            abridged_path = Path(f"{base_name}-abridged.md")
            markdown_abridged = processor.format_session_as_markdown(
                session_summary,
                entries,
                agent_entries,
                include_tool_results=False,
                variant="abridged",
                source_file=str(session_path.resolve()),
                reflection_header=reflection_header,
                usage_stats=usage_stats,
                session_duration_minutes=session_duration_minutes,
            )
            with open(abridged_path, "w", encoding="utf-8") as f:
                f.write(markdown_abridged)
            format_markdown(abridged_path)
            file_size = abridged_path.stat().st_size
            print(f"✅ Abridged transcript: {abridged_path} ({file_size:,} bytes)")

            # Emit per-subagent transcripts + insights (task-b483e037)
            _emit_subagent_artifacts(
                session_path=session_path,
                parent_session_id=sid,
                session_summary=session_summary,
                entries=entries,
                agent_entries=agent_entries,
                processor=processor,
                parent_full_path=full_path,
            )

            return 0

        # If output_dir not set yet (no -o specified), use default
        if not output_dir:
            output_dir = sessions_claude

        # Auto-generate filename: YYYYMMDD-HH-shortproject-sessionid-slug
        # (Used when -o is a directory or not specified)
        (
            filename,
            date_str,
            short_project,
            session_id,
            slug,
        ) = _generate_transcript_filename(
            session_path,
            entries,
            slug=args.slug,
            processor=processor,
            shortform=args.shortform,
        )

        # Rotate into <output_dir>/YYYY-MM/ keyed off session start
        # (aops-b975b185). Only rotate when the output_dir is the default
        # transcripts dir; explicit --output paths are honoured verbatim.
        if output_dir == sessions_claude:
            rotation_dt = extract_date_from_filename(filename) or datetime.strptime(
                date_str, "%Y%m%d"
            ).replace(tzinfo=UTC)
            output_dir = ensure_rotated_dir(sessions_claude, rotation_dt)
        base_name = str(output_dir / filename)
        print(f"📛 Generated filename: {filename}")

        print(f"📊 Found {len(entries)} entries")

        # Check for meaningful content — accept sessions with at least 1 entry.
        MIN_MEANINGFUL_ENTRIES = 1
        meaningful_count = sum(
            1
            for e in entries
            if e.type in ("user", "assistant")
            and not (
                hasattr(e, "message")
                and e.message
                and e.message.get("subtype") in ("system", "informational")
            )
        )
        if meaningful_count < MIN_MEANINGFUL_ENTRIES:
            print(
                f"⏭️  Skipping: only {meaningful_count} meaningful entries (need {MIN_MEANINGFUL_ENTRIES}+)"
            )
            return 2  # Exit 2 = skipped (no content), distinct from 0 (success) and 1 (error)

        # Extract and process reflection (if present)
        # Convert date format from YYYYMMDD to YYYY-MM-DD for insights
        date_iso = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
        # Get timestamp from entries for ISO 8601 output
        session_timestamp = None
        for entry in entries:
            if entry.timestamp:
                session_timestamp = entry.timestamp.astimezone()
                break

        # Compute usage stats and session duration for token_metrics
        usage_stats = processor._aggregate_session_usage(entries, agent_entries)
        session_duration_minutes = _compute_session_duration(entries)

        # Extract timeline events for path reconstruction
        turns = processor.group_entries_into_turns(entries, agent_entries)
        timeline_events = extract_timeline_events(turns, session_id)

        # Augment summary with explicit session metadata from entries (CC 2.1+)
        session_ctx = aggregate_session_metadata(entries)
        session_summary.session_kind = session_ctx.get("session_kind")
        session_summary.user_type = session_ctx.get("user_type")
        session_summary.entrypoint = session_ctx.get("entrypoint")
        session_summary.cwd = session_ctx.get("cwd")
        session_summary.client_version = session_ctx.get("client_version")
        session_summary.git_branches = session_ctx.get("git_branches", [])
        session_summary.permission_modes = session_ctx.get("permission_modes", [])
        session_summary.models = session_ctx.get(
            "models", []
        )  # allow-fallback: field optional in older transcripts

        _populate_session_linkage(session_summary, entries)

        session_summary.session_type = session_naming.classify_session_type(
            session_summary.surface,
            client=session_summary.client,
            task_id=session_summary.task_id,
            subagent_type=session_summary.subagent_type,
            parent_session=session_summary.parent_session,
            crew=session_summary.crew,
            session_kind=session_summary.session_kind,
            initial_prompt=extract_initial_prompt(timeline_events),
        )
        session_summary.pull_requests = _resolve_pr_numbers(
            session_summary.git_branches, session_summary.repo
        )

        reflection_header, _ = _process_reflection(
            entries,
            session_id,
            date_iso,
            short_project,
            slug,
            agent_entries,
            session_timestamp,
            usage_stats,
            session_duration_minutes,
            timeline_events,
            shortform=args.shortform,
            provider=session_summary.provider,
            session_path=session_path,
            origin_override=session_origin,
            session_ctx=session_ctx,
            session_summary=session_summary,
        )

        # Generate full version
        full_path = Path(f"{base_name}-full.md")
        markdown_full = processor.format_session_as_markdown(
            session_summary,
            entries,
            agent_entries,
            include_tool_results=True,
            variant="full",
            source_file=str(session_path.resolve()),
            reflection_header=reflection_header,
            usage_stats=usage_stats,
            session_duration_minutes=session_duration_minutes,
        )
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(markdown_full)
        format_markdown(full_path)
        file_size = full_path.stat().st_size
        print(f"✅ Full transcript: {full_path} ({file_size:,} bytes)")

        # Generate abridged version
        abridged_path = Path(f"{base_name}-abridged.md")
        markdown_abridged = processor.format_session_as_markdown(
            session_summary,
            entries,
            agent_entries,
            include_tool_results=False,
            variant="abridged",
            source_file=str(session_path.resolve()),
            reflection_header=reflection_header,
            usage_stats=usage_stats,
            session_duration_minutes=session_duration_minutes,
        )
        with open(abridged_path, "w", encoding="utf-8") as f:
            f.write(markdown_abridged)
        format_markdown(abridged_path)
        file_size = abridged_path.stat().st_size
        print(f"✅ Abridged transcript: {abridged_path} ({file_size:,} bytes)")

        # Emit per-subagent transcripts + insights (task-b483e037)
        _emit_subagent_artifacts(
            session_path=session_path,
            parent_session_id=session_id,
            session_summary=session_summary,
            entries=entries,
            agent_entries=agent_entries,
            processor=processor,
            parent_full_path=full_path,
        )

        return 0

    except Exception as e:
        print(f"❌ Error processing session: {e}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    # Sync after successful or skipped runs (exit code 2 = skipped/insufficient content)
    if exit_code in (0, 2) and not any(a in sys.argv for a in ("--no-sync",)):
        git_sync()
    sys.exit(exit_code)
