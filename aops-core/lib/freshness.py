"""freshness.py — read-only project-state freshness diff (Layer 1 of the
project-state reconcile epic, aops-46b5c0ad / epic-ef498cc7).

Given a project's *narrative anchors* (PKB project-knowledge docs / meta-epic
bodies, repo README/CLAUDE.md) and the repo's *ground truth* (git HEAD + commit
log, report/output tree), this computes a cheap freshness delta per anchor and
emits a staleness verdict: ``FRESH`` / ``DRIFTED`` / ``STALE``, with
``UNKNOWN -> STALE`` as the non-negotiable fail-safe.

Design (ratified note-d74d0acf, §Q2 layer 1):

* **Ground truth is Tier 1, authoritative.** git HEAD/log + report tree.
* **Narrative anchors are Tier 2, lag-prone.** Each carries (or should carry) a
  last-recorded SHA and a ``modified`` timestamp.
* **A claim is only relayable once its freshness is checked and surfaced.** The
  verdict is produced by the read path, never by a coordinator choosing to be
  diligent.
* **Fail toward STALE.** If the check itself cannot run (no recorded SHA, repo
  unreachable, git unavailable, SHA unknown to the repo) the verdict is STALE,
  never a confident relay.

This module is strictly read-only: it shells out to ``git`` with read-only
plumbing commands and reads files. It never writes to the repo or the PKB.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path

import yaml

__all__ = [
    "Band",
    "Thresholds",
    "Anchor",
    "RepoState",
    "FreshnessVerdict",
    "ProjectFreshness",
    "parse_anchor",
    "read_repo_state",
    "evaluate_anchor",
    "evaluate_project",
]


class Band(StrEnum):
    """Staleness band. Ordered FRESH < DRIFTED < STALE for ``max``-of-signals."""

    FRESH = "FRESH"
    DRIFTED = "DRIFTED"
    STALE = "STALE"

    @property
    def _rank(self) -> int:
        return {"FRESH": 0, "DRIFTED": 1, "STALE": 2}[self.value]

    def worse_of(self, other: Band) -> Band:
        return self if self._rank >= other._rank else other


@dataclass(frozen=True)
class Thresholds:
    """Band boundaries. Defaults calibrated to the TJA failure (74 commits /
    ~35 days was decisively STALE). All boundaries are configurable so the tool
    can be tuned per project without a code change.

    A signal is FRESH below its ``drifted`` boundary, DRIFTED at/above
    ``drifted`` but below ``stale``, and STALE at/above ``stale``. The overall
    band is the worst of the commit signal, the day signal, and (optionally) the
    missing-artifact signal.
    """

    drifted_commits: int = 1
    stale_commits: int = 20
    drifted_days: int = 3
    stale_days: int = 30
    # Unmentioned ground-truth artifacts never push past DRIFTED on their own
    # (they are a "relay with a banner" signal, not a "do not relay" signal).
    artifacts_elevate_to_drifted: bool = True

    def band_for_commits(self, commits_behind: int) -> Band:
        if commits_behind >= self.stale_commits:
            return Band.STALE
        if commits_behind >= self.drifted_commits:
            return Band.DRIFTED
        return Band.FRESH

    def band_for_days(self, days_behind: int) -> Band:
        if days_behind >= self.stale_days:
            return Band.STALE
        if days_behind >= self.drifted_days:
            return Band.DRIFTED
        return Band.FRESH


# A bare git SHA: 7-40 lowercase hex chars. Used to pull a HEAD claim out of
# anchor prose when no explicit frontmatter field carries it.
_SHA_RE = r"[0-9a-f]{7,40}"

# Frontmatter keys that, if present, carry the anchor's last-recorded HEAD SHA.
# Checked in order; first non-empty wins. This is the robust path — prose
# extraction is only a fallback.
_SHA_FRONTMATTER_KEYS = ("repo_head", "last_recorded_sha", "head_sha", "last_sha")

# Prose cues that mark a SHA as the *current HEAD* the narrative is anchored to.
# Deliberately conservative: we only trust a SHA the prose explicitly calls HEAD
# (so "last-known commit `<old>`" does NOT get mistaken for the current claim).
# The char class excludes only the backtick (not newlines) so a "HEAD is now\n
# `<sha>`" claim that wraps a line still matches; the {0,40} bound keeps the
# match local to the HEAD cue rather than reaching across the document.
_PROSE_HEAD_PATTERNS = (
    re.compile(rf"\bHEAD\b[^`]{{0,40}}?`({_SHA_RE})`", re.IGNORECASE),
    re.compile(rf"`({_SHA_RE})`[^`]{{0,25}}?\bis\s+(?:now\s+)?HEAD\b", re.IGNORECASE),
)


@dataclass
class Anchor:
    """A Tier-2 narrative anchor parsed from a markdown source (PKB doc, epic
    body, or repo prose)."""

    id: str
    last_recorded_sha: str | None
    modified: datetime | None
    mentioned_artifacts: set[str] = field(default_factory=set)
    source_path: Path | None = None
    sha_source: str = "none"  # "frontmatter" | "prose" | "none"


@dataclass
class RepoState:
    """Tier-1 ground truth read from a git repo."""

    head_sha: str | None
    head_date: datetime | None
    reachable: bool
    artifacts: set[str] = field(default_factory=set)
    error: str | None = None


@dataclass
class FreshnessVerdict:
    """The load-bearing output: a per-anchor staleness verdict."""

    anchor_id: str
    band: Band
    commits_behind: int | None
    days_behind: int | None
    missing_artifacts: list[str]
    rationale: str
    is_failsafe: bool  # True when band was forced to STALE by UNKNOWN

    def to_dict(self) -> dict:
        return {
            "anchor_id": self.anchor_id,
            "band": self.band.value,
            "commits_behind": self.commits_behind,
            "days_behind": self.days_behind,
            "missing_artifacts": self.missing_artifacts,
            "rationale": self.rationale,
            "is_failsafe": self.is_failsafe,
        }

    def banner(self) -> str:
        """The drift banner a coordinator must attach when relaying a DRIFTED
        narrative. Empty for FRESH; an explicit do-not-relay note for STALE."""
        if self.band is Band.FRESH:
            return ""
        if self.band is Band.DRIFTED:
            cb = "?" if self.commits_behind is None else self.commits_behind
            db = "?" if self.days_behind is None else self.days_behind
            return (
                f"narrative is {cb} commits / {db} days behind HEAD; treat decisions as provisional"
            )
        return "narrative is STALE; do NOT relay as fact — reconcile against ground truth first"


@dataclass
class ProjectFreshness:
    """Per-anchor verdicts plus the project-level aggregate (worst band)."""

    project: str
    anchors: list[FreshnessVerdict]

    @property
    def aggregate_band(self) -> Band:
        band = Band.FRESH
        for v in self.anchors:
            band = band.worse_of(v.band)
        return band

    def to_dict(self) -> dict:
        return {
            "project": self.project,
            "aggregate_band": self.aggregate_band.value,
            "anchors": [v.to_dict() for v in self.anchors],
        }


# --------------------------------------------------------------------------- #
# Anchor parsing
# --------------------------------------------------------------------------- #


def _parse_timestamp(value: object) -> datetime | None:
    """Tolerant ISO-8601 parse. Handles the PKB's nanosecond-precision
    ``modified`` stamps (e.g. ``2026-06-10T07:29:35.394217934+00:00``) which
    ``datetime.fromisoformat`` rejects, and naive/`Z`-suffixed forms. Returns a
    tz-aware datetime (assumes UTC when no offset is given)."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    s = str(value).strip()
    if not s:
        return None
    s = s.replace("Z", "+00:00")
    # Truncate sub-second precision to 6 digits (microseconds) — Python's
    # fromisoformat caps there; nanosecond PKB stamps would otherwise raise.
    m = re.match(r"^(.*\.\d{6})\d*([+-]\d{2}:?\d{2})?$", s)
    if m:
        s = m.group(1) + (m.group(2) or "")  # allow-fallback: tz offset is an optional regex group
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        try:
            dt = datetime.fromisoformat(s[:10])  # bare date fallback
        except ValueError:
            return None
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def _split_frontmatter(text: str) -> tuple[dict, str]:
    """Return ``(frontmatter_dict, body)``. Finds the first ``---``-fenced YAML
    block (tolerating a leading markdown title line, as some PKB renders carry).
    Returns ``({}, text)`` when no frontmatter is present."""
    lines = text.splitlines()
    start = None
    # Allow a few leading non-fence lines (e.g. a "## Title" echo) before the
    # frontmatter fence.
    for i, line in enumerate(lines[:6]):
        if line.strip() == "---":
            start = i
            break
    if start is None:
        return {}, text
    for j in range(start + 1, len(lines)):
        if lines[j].strip() == "---":
            block = "\n".join(lines[start + 1 : j])
            body = "\n".join(lines[j + 1 :])
            try:
                data = (
                    yaml.safe_load(block) or {}
                )  # allow-fallback: empty frontmatter block -> no fields
            except yaml.YAMLError:
                data = {}
            if not isinstance(data, dict):
                data = {}
            return data, body
    return {}, text


def _extract_sha_from_prose(body: str) -> str | None:
    """Best-effort: pull the SHA the prose explicitly marks as current HEAD.
    Conservative by design — returns None rather than guess from an ambiguous
    SHA mention (which would risk a false-FRESH on a stale anchor)."""
    for pat in _PROSE_HEAD_PATTERNS:
        m = pat.search(body)
        if m:
            return m.group(1).lower()
    return None


def parse_anchor(
    path: str | Path | None = None,
    *,
    text: str | None = None,
    anchor_id: str | None = None,
    artifact_terms: set[str] | None = None,
) -> Anchor:
    """Parse a narrative anchor from a markdown file or raw ``text``.

    Last-recorded SHA resolution order: explicit frontmatter key
    (``repo_head`` / ``last_recorded_sha`` / ...) first, then a conservative
    prose extraction of an explicit "HEAD is `<sha>`" claim. If neither yields a
    SHA the anchor's ``last_recorded_sha`` is None, which drives the
    UNKNOWN -> STALE fail-safe downstream.

    ``artifact_terms`` is the set of ground-truth artifact names to check for
    mention in the anchor prose; any not mentioned become a drift signal.
    """
    if text is None:
        if path is None:
            raise ValueError("parse_anchor requires either path or text")
        text = Path(path).read_text(encoding="utf-8")
    fm, body = _split_frontmatter(text)

    resolved_id = anchor_id or str(fm.get("id") or (Path(path).stem if path else "anchor"))

    sha: str | None = None
    sha_source = "none"
    for key in _SHA_FRONTMATTER_KEYS:
        raw = fm.get(key)
        if raw:
            candidate = str(raw).strip().lower()
            if re.fullmatch(_SHA_RE, candidate):
                sha, sha_source = candidate, "frontmatter"
                break
    if sha is None:
        prose_sha = _extract_sha_from_prose(body)
        if prose_sha:
            sha, sha_source = prose_sha, "prose"

    mentioned: set[str] = set()
    if artifact_terms:
        lowered = body.lower()
        for term in artifact_terms:
            if term.lower() in lowered:
                mentioned.add(term)

    return Anchor(
        id=resolved_id,
        last_recorded_sha=sha,
        modified=_parse_timestamp(fm.get("modified") or fm.get("date")),
        mentioned_artifacts=mentioned,
        source_path=Path(path) if path else None,
        sha_source=sha_source,
    )


# --------------------------------------------------------------------------- #
# Ground truth
# --------------------------------------------------------------------------- #


def _git(repo: Path, *args: str) -> tuple[int, str, str]:
    """Run a read-only git command, return (returncode, stdout, stderr)."""
    proc = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def read_repo_state(repo: str | Path, *, artifact_globs: list[str] | None = None) -> RepoState:
    """Read Tier-1 ground truth from a git repo. Degrades gracefully: an
    unreachable/non-git path yields ``reachable=False`` with an ``error`` rather
    than raising, so the verdict layer can fail toward STALE."""
    repo = Path(repo)
    if not repo.exists():
        return RepoState(None, None, reachable=False, error=f"repo path does not exist: {repo}")
    rc, _, err = _git(repo, "rev-parse", "--is-inside-work-tree")
    if rc != 0:
        return RepoState(None, None, reachable=False, error=f"not a git repo: {err or repo}")

    rc, head_sha, err = _git(repo, "rev-parse", "HEAD")
    if rc != 0:
        return RepoState(None, None, reachable=False, error=f"cannot read HEAD: {err}")

    head_date = None
    rc, iso, _ = _git(repo, "show", "-s", "--format=%cI", "HEAD")
    if rc == 0 and iso:
        head_date = _parse_timestamp(iso.splitlines()[-1])

    artifacts: set[str] = set()
    for pattern in (
        artifact_globs or []
    ):  # allow-fallback: artifact_globs is optional (no artifact check)
        for p in sorted(repo.glob(pattern)):
            if p.is_file():
                artifacts.add(p.name)

    return RepoState(
        head_sha=head_sha.lower(), head_date=head_date, reachable=True, artifacts=artifacts
    )


def _commits_behind(repo: Path, anchor_sha: str) -> int | None:
    """``git rev-list --count <anchor_sha>..HEAD`` — commits on HEAD not on the
    anchor's recorded SHA. None if the SHA is unknown to the repo (which drives
    UNKNOWN -> STALE)."""
    rc, out, _ = _git(repo, "rev-list", "--count", f"{anchor_sha}..HEAD")
    if rc != 0:
        return None
    try:
        return int(out.strip())
    except ValueError:
        return None


def _commit_date(repo: Path, sha: str) -> datetime | None:
    """Committer date of a SHA, from git ground truth. None if unresolvable."""
    rc, out, _ = _git(repo, "show", "-s", "--format=%cI", sha)
    if rc != 0 or not out:
        return None
    return _parse_timestamp(out.splitlines()[-1])


# --------------------------------------------------------------------------- #
# Verdict
# --------------------------------------------------------------------------- #


def _failsafe(anchor_id: str, reason: str) -> FreshnessVerdict:
    return FreshnessVerdict(
        anchor_id=anchor_id,
        band=Band.STALE,
        commits_behind=None,
        days_behind=None,
        missing_artifacts=[],
        rationale=f"UNKNOWN -> STALE (fail-safe): {reason}",
        is_failsafe=True,
    )


def evaluate_anchor(
    anchor: Anchor,
    repo_state: RepoState,
    repo: str | Path | None = None,
    thresholds: Thresholds | None = None,
) -> FreshnessVerdict:
    """Diff one anchor against ground truth and emit a verdict.

    Fail-safe (UNKNOWN -> STALE) fires when: the repo is unreachable, the anchor
    carries no recorded SHA, or the recorded SHA is unknown to the repo. In every
    such case the verdict is STALE — never a confident FRESH.
    """
    th = thresholds or Thresholds()

    if not repo_state.reachable:
        return _failsafe(anchor.id, repo_state.error or "repo unreachable")
    if not anchor.last_recorded_sha:
        return _failsafe(anchor.id, "anchor carries no recorded SHA")

    if repo is None:
        if anchor.source_path is None and repo_state.head_sha is None:
            return _failsafe(anchor.id, "no repo path to compute commit delta")
    commits_behind: int | None = None
    if anchor.last_recorded_sha == repo_state.head_sha:
        commits_behind = 0
    elif repo is not None:
        commits_behind = _commits_behind(Path(repo), anchor.last_recorded_sha)
    if commits_behind is None:
        return _failsafe(
            anchor.id,
            f"recorded SHA {anchor.last_recorded_sha} not reachable in repo",
        )

    # Days behind: HEAD commit date minus the *recorded SHA's commit date* —
    # pure git ground truth, measuring how much time elapsed in the codebase
    # since the anchor's basis. This is more faithful than the anchor's
    # ``modified`` stamp: a narrative can be edited (modified bumped) while still
    # pointing at an old SHA — the TJA anchor was touched 2026-05-30 yet anchored
    # at an April commit. Fall back to ``modified`` only when the SHA's date is
    # unresolvable. Clamped at 0 (an anchor at/after HEAD is not "behind").
    days_behind: int | None = None
    basis_date = _commit_date(Path(repo), anchor.last_recorded_sha) if repo is not None else None
    if basis_date is None:
        basis_date = anchor.modified
    if basis_date and repo_state.head_date:
        days_behind = max(0, (repo_state.head_date - basis_date).days)

    # Missing artifacts: ground-truth files the anchor prose never mentions.
    missing = sorted(repo_state.artifacts - anchor.mentioned_artifacts)

    commit_band = th.band_for_commits(commits_behind)
    day_band = th.band_for_days(days_behind) if days_behind is not None else Band.FRESH
    band = commit_band.worse_of(day_band)
    if missing and th.artifacts_elevate_to_drifted:
        band = band.worse_of(Band.DRIFTED)

    parts = [f"{commits_behind} commits behind HEAD"]
    if days_behind is not None:
        parts.append(f"{days_behind} days behind")
    else:
        parts.append("days-behind unknown (no anchor/HEAD date)")
    if missing:
        shown = ", ".join(missing[:5]) + (" …" if len(missing) > 5 else "")
        parts.append(f"{len(missing)} unmentioned artifact(s): {shown}")
    rationale = "; ".join(parts) + f" -> {band.value}"

    return FreshnessVerdict(
        anchor_id=anchor.id,
        band=band,
        commits_behind=commits_behind,
        days_behind=days_behind,
        missing_artifacts=missing,
        rationale=rationale,
        is_failsafe=False,
    )


def evaluate_project(
    project: str,
    anchors: list[Anchor],
    repo_state: RepoState,
    repo: str | Path | None = None,
    thresholds: Thresholds | None = None,
) -> ProjectFreshness:
    """Evaluate every anchor for a project and aggregate (worst band wins)."""
    verdicts = [evaluate_anchor(a, repo_state, repo=repo, thresholds=thresholds) for a in anchors]
    return ProjectFreshness(project=project, anchors=verdicts)
