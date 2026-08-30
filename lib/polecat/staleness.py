#!/usr/bin/env python3
"""Polecat container image staleness detection and surfacing.

Implements spec: specs/polecat/spec-image-staleness-detection.md (aops_866c0666).
Detects when the plugin payload baked into a container image lags behind
the workspace under test, surfacing clear banners to the operator and agent
while strictly enforcing the "warn, never refuse" invariant.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ImageProvenance:
    dist_source: str = "local"  # "local" | "remote" | "unknown"
    commit_sha: str = ""
    short_sha: str = ""
    version: str = ""
    is_dirty: bool = False
    dist_ref: str = ""
    repo_url: str = ""
    built_at: str = ""
    raw_labels: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _get_git_head_and_dirty(path: Path | str) -> tuple[str, bool]:
    """Return (HEAD sha, is_dirty) for git repository at path."""
    sha = ""
    is_dirty = False
    try:
        res = subprocess.run(
            ["git", "-C", str(path), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
        )
        if res.returncode == 0 and res.stdout:
            sha = res.stdout.strip()
    except Exception:
        pass

    try:
        res = subprocess.run(
            ["git", "-C", str(path), "status", "--porcelain"],
            capture_output=True,
            text=True,
            check=False,
        )
        if res.returncode == 0 and res.stdout:
            is_dirty = bool(res.stdout.strip())
    except Exception:
        pass

    return sha, is_dirty


def inspect_image_provenance(image: str) -> ImageProvenance:
    """Read build-time provenance metadata from Docker image labels."""
    try:
        res = subprocess.run(
            ["docker", "image", "inspect", "--format", "{{json .Config.Labels}}", image],
            capture_output=True,
            text=True,
            check=False,
        )
        if res.returncode == 0 and res.stdout:
            raw_str = res.stdout.strip()
            if raw_str and raw_str != "null":
                labels = json.loads(raw_str) or {}
                commit_sha = labels.get("org.opencontainers.image.revision") or ""
                version = labels.get("org.opencontainers.image.version") or ""
                dist_source = labels.get("aops.dist_source") or (
                    "remote" if "remote" in image else "local"
                )
                dist_ref = labels.get("aops.dist_ref") or ""
                build_dirty_raw = str(labels.get("aops.build_dirty", "0")).lower()
                is_dirty = build_dirty_raw in ("1", "true", "yes")
                short_sha = commit_sha[:8] if commit_sha else ""

                return ImageProvenance(
                    dist_source=dist_source,
                    commit_sha=commit_sha,
                    short_sha=short_sha,
                    version=version,
                    is_dirty=is_dirty,
                    dist_ref=dist_ref,
                    raw_labels=labels,
                )
    except Exception:
        pass

    # Fallback when docker inspect is unavailable or image has no labels
    return ImageProvenance(
        dist_source="remote" if "remote" in image else "local",
        commit_sha="",
        short_sha="",
        version="",
        is_dirty=False,
        dist_ref="",
    )


def format_fresh_header(
    *,
    session_id: str,
    agent: str,
    workspace_dir: Path | str,
    workspace_short: str,
    image_ref: str,
    image_short: str,
) -> str:
    return (
        "================================================================================\n"
        f"POLECAT DISPATCH: {session_id} [{agent or 'none'}]\n"
        f"Workspace: {workspace_dir} (commit: {workspace_short})\n"
        f"Image:     {image_ref} (local build @ {image_short})\n"
        "Status:    PLUGINS FRESH [local match]\n"
        "================================================================================"
    )


def format_stale_banner(
    *,
    image_commit: str,
    workspace_commit: str,
    build_date: str = "",
) -> str:
    built_info = f" (built: {build_date})" if build_date else ""
    return (
        "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n"
        "WARNING: POLECAT IMAGE PLUGINS ARE STALE\n"
        "The plugins baked into this container image DO NOT MATCH the workspace under test!\n"
        f"- Baked Image Commit:    {image_commit}{built_info}\n"
        f"- Workspace Test Commit: {workspace_commit}\n"
        "- Impact:                Container agent will execute OLD plugins/skills/hooks.\n"
        "- Remedy:                Run `make docker-build` to rebuild with current source.\n"
        "Proceeding with execution (warn-only policy enabled)...\n"
        "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
    )


def format_remote_header(
    *,
    session_id: str,
    agent: str,
    workspace_dir: Path | str,
    branch: str,
    workspace_short: str,
    image_ref: str,
    dist_ref: str,
) -> str:
    return (
        "================================================================================\n"
        f"POLECAT DISPATCH: {session_id} [{agent or 'none'}]\n"
        f"Workspace: {workspace_dir} (branch: {branch} @ {workspace_short})\n"
        f"Image:     {image_ref} (remote release @ {dist_ref})\n"
        "Status:    REMOTE RELEASE IMAGE [testing against released plugin baseline]\n"
        "================================================================================"
    )


def evaluate_staleness(
    image_provenance: ImageProvenance | dict[str, Any],
    workspace_dir: Path | str,
    *,
    dispatch_mode: str = "direct",
    base_sha: str | None = None,
    session_id: str = "",
    agent: str = "",
    branch: str | None = None,
    image_ref: str = "",
) -> dict[str, Any]:
    if isinstance(image_provenance, dict):
        raw_labels = image_provenance.get("raw_labels", {})
        prov = ImageProvenance(
            dist_source=image_provenance.get("dist_source", "local"),
            commit_sha=image_provenance.get("commit_sha", ""),
            short_sha=image_provenance.get("short_sha", ""),
            version=image_provenance.get("version", ""),
            is_dirty=image_provenance.get("is_dirty", False),
            dist_ref=image_provenance.get("dist_ref", ""),
            built_at=image_provenance.get("built_at", ""),
            raw_labels=raw_labels,
        )
    else:
        prov = image_provenance

    if base_sha:
        workspace_sha = base_sha
        workspace_dirty = False
    else:
        workspace_sha, workspace_dirty = _get_git_head_and_dirty(workspace_dir)

    workspace_short = workspace_sha[:8] if workspace_sha else "unknown"
    image_short = prov.short_sha or (prov.commit_sha[:8] if prov.commit_sha else "unknown")
    image_version = prov.version or "0.9.1"
    dist_ref = prov.dist_ref or "dev"

    if prov.dist_source == "remote":
        is_stale = False
        if (
            prov.commit_sha
            and workspace_sha
            and (
                prov.commit_sha == workspace_sha
                or prov.commit_sha.startswith(workspace_sha)
                or workspace_sha.startswith(prov.commit_sha)
            )
        ):
            status = "FRESH_REMOTE_BUILD"
        else:
            status = "REMOTE_RELEASE_RUN"
        reason = None
        warning_banner = None
        header_banner = format_remote_header(
            session_id=session_id,
            agent=agent,
            workspace_dir=workspace_dir,
            branch=branch or "feature",
            workspace_short=workspace_short,
            image_ref=image_ref,
            dist_ref=dist_ref or image_version,
        )
        plugins_version_str = f"{image_version} (remote:release)"
    else:
        # Local source build
        if (
            prov.commit_sha
            and workspace_sha
            and not (
                prov.commit_sha == workspace_sha
                or prov.commit_sha.startswith(workspace_sha)
                or workspace_sha.startswith(prov.commit_sha)
            )
        ):
            is_stale = True
            status = "STALE_LOCAL_BUILD"
            reason = f"image commit {image_short} behind workspace commit {workspace_short}"
            warning_banner = format_stale_banner(
                image_commit=image_short,
                workspace_commit=workspace_short,
                build_date=prov.built_at,
            )
            header_banner = None
            plugins_version_str = f"{image_version} (local:stale)"
        elif workspace_dirty and not prov.is_dirty:
            is_stale = True
            status = "DIRTY_WORKSPACE_UNBAKED"
            reason = "workspace has uncommitted changes not baked into image"
            warning_banner = format_stale_banner(
                image_commit=image_short,
                workspace_commit=f"{workspace_short} (dirty)",
                build_date=prov.built_at,
            )
            header_banner = None
            plugins_version_str = f"{image_version} (local:dirty)"
        else:
            is_stale = False
            status = "FRESH_LOCAL_BUILD"
            reason = None
            warning_banner = None
            header_banner = format_fresh_header(
                session_id=session_id,
                agent=agent,
                workspace_dir=workspace_dir,
                workspace_short=workspace_short,
                image_ref=image_ref,
                image_short=image_short,
            )
            plugins_version_str = f"{image_version} (local:match)"

    return {
        "is_stale": is_stale,
        "staleness_status": status,
        "staleness_reason": reason,
        "image_source": prov.dist_source,
        "image_commit": prov.commit_sha or image_short,
        "workspace_commit": workspace_sha or workspace_short,
        "header_banner": header_banner,
        "warning_banner": warning_banner,
        "plugins_version_str": plugins_version_str,
    }
