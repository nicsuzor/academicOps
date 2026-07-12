#!/usr/bin/env -S uv run python
"""
Sync GHA claude-session artifacts to $AOPS_SESSIONS/github/

Lists artifacts from configured GitHub repositories, downloads new ones,
and processes them with transcript.py.
"""

import argparse
import json
import os
import subprocess
import sys
import zipfile
from datetime import datetime
from pathlib import Path

# Add framework roots to path for lib imports
SCRIPT_DIR = Path(__file__).parent.resolve()
AOPS_CORE_ROOT = SCRIPT_DIR.parent
FRAMEWORK_ROOT = AOPS_CORE_ROOT.parent

sys.path.insert(0, str(FRAMEWORK_ROOT))
sys.path.insert(0, str(AOPS_CORE_ROOT))

from lib.paths import get_sessions_repo


def get_gha_sessions_dir() -> Path:
    """Get the directory where GHA sessions are stored."""
    sessions_root = get_sessions_repo()
    gha_dir = sessions_root / "github"
    gha_dir.mkdir(parents=True, exist_ok=True)
    return gha_dir


def load_state() -> dict:
    """Load sync state from manifest file."""
    state_file = get_gha_sessions_dir() / ".sync-state.json"
    if state_file.exists():
        try:
            return json.loads(state_file.read_text())
        except Exception as e:
            print(f"Warning: could not load sync state from {state_file}: {e}", file=sys.stderr)
            return {}
    return {}


def save_state(state: dict):
    """Save sync state to manifest file."""
    state_file = get_gha_sessions_dir() / ".sync-state.json"
    state_file.write_text(json.dumps(state, indent=2))


def get_repos(args):
    """Get list of repos to sync."""
    if args.repos:
        return [r.strip() for r in args.repos.split(",") if r.strip()]

    # Try env var
    env_repos = os.environ.get("AOPS_GHA_REPOS")
    if env_repos:
        return [r.strip() for r in env_repos.split(",") if r.strip()]

    # Fallback to default
    return ["nicsuzor/academicOps"]


def run_gh_api(path: str) -> dict:
    """Run gh api and return JSON result."""
    cmd = ["gh", "api", path]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error running gh api {path}: {result.stderr.strip()}", file=sys.stderr)
        return {}
    try:
        return json.loads(result.stdout)
    except Exception as e:
        print(f"Error parsing JSON from gh api {path}: {e}", file=sys.stderr)
        return {}


def main():
    parser = argparse.ArgumentParser(description="Sync GHA claude-session artifacts")
    parser.add_argument("--repos", help="Comma-separated list of repos (owner/repo)")
    parser.add_argument("--limit", type=int, default=100, help="Max artifacts to fetch per repo")
    args = parser.parse_args()

    # Check gh auth
    auth_check = subprocess.run(["gh", "auth", "status"], capture_output=True)
    if auth_check.returncode != 0:
        print(
            "Error: gh CLI is not authenticated or not installed. Please run 'gh auth login'.",
            file=sys.stderr,
        )
        sys.exit(1)

    repos = get_repos(args)
    state = load_state()
    gha_sessions_dir = get_gha_sessions_dir()

    # Note: a previous version appended `github/` to `$AOPS_SESSIONS/.gitignore`
    # on every run. That auto-registration is no longer needed: under the
    # current policy (PKB kb-d8f58167) the sessions repo default-denies
    # everything except `transcripts/` and `summaries/`, so `github/` is
    # already ignored. The legacy block was also racy with cron and produced
    # 800+ duplicate `github/` lines in the .gitignore.

    total_new = 0
    total_skipped = 0

    for repo in repos:
        repo_slug = repo.split("/")[-1].lower()

        # List artifacts
        # We might need pagination if there are many artifacts, but start with default page
        data = run_gh_api(f"repos/{repo}/actions/artifacts?per_page={args.limit}")
        if not data or "artifacts" not in data:
            print(f"⚠️  No artifacts found for {repo}")
            continue

        artifacts = data["artifacts"]
        new_count = 0
        skipped_count = 0

        for art in artifacts:
            name = art["name"]
            if not name.startswith("claude-session-"):
                continue

            if art.get("expired"):
                continue

            art_id = art["id"]
            run_id = art["workflow_run"]["id"]

            # Parse attempt from name: claude-session-{workflow}-{run_id}-{attempt}
            parts = name.split("-")
            run_id_str = str(run_id)
            attempt = "1"
            if run_id_str in parts:
                idx = parts.index(run_id_str)
                if idx + 1 < len(parts) and parts[idx + 1].isdigit():
                    attempt = parts[idx + 1]

            state_key = f"{repo}/{run_id}/{attempt}"
            if state_key in state and state[state_key]["id"] == art_id:
                skipped_count += 1
                continue

            # Download
            dest_dir = gha_sessions_dir / repo_slug / str(run_id) / attempt
            dest_dir.mkdir(parents=True, exist_ok=True)

            print(f"📥 Downloading {name} to {dest_dir}...")
            # gh run download -R repo -p name -D dest_dir
            # Wait, gh run download uses -n for artifact name.
            cmd = [
                "gh",
                "run",
                "download",
                "-R",
                repo,
                str(run_id),
                "-n",
                name,
                "-D",
                str(dest_dir),
            ]
            dl_result = subprocess.run(cmd, capture_output=True, text=True)
            if dl_result.returncode != 0:
                print(f"  ❌ Error downloading {name}: {dl_result.stderr.strip()}")
                continue

            # Find the jsonl file
            jsonl_files = list(dest_dir.rglob("*.jsonl"))
            if not jsonl_files:
                # Check for zip (sometimes gh CLI behavior varies)
                zip_files = list(dest_dir.rglob("*.zip"))
                for zf in zip_files:
                    try:
                        with zipfile.ZipFile(zf, "r") as zip_ref:
                            zip_ref.extractall(dest_dir)
                        zf.unlink()
                    except Exception as e:
                        print(f"  ❌ Error unzipping {zf}: {e}")
                jsonl_files = list(dest_dir.glob("*.jsonl"))

            if not jsonl_files:
                print(f"  ⚠️  No .jsonl found in artifact {name}")
                continue

            # Process with transcript.py
            # shortform = gha-{workflow}-{repo}-claude
            # name = claude-session-{workflow}-{run_id}-{attempt}
            # Workflow is everything between 'claude-session-' and 'run_id'
            workflow = (
                "-".join(parts[2 : parts.index(str(run_id))])
                if str(run_id) in parts
                else "-".join(parts[2:-2])
            )
            shortform = f"gha-{workflow}-{repo_slug}-claude"

            artifact_success = True
            for jf in jsonl_files:
                print(f"  📝 Transcribing {jf.name} (shortform: {shortform})...")
                transcript_cmd = [
                    sys.executable,
                    str(AOPS_CORE_ROOT / "scripts" / "transcript.py"),
                    str(jf),
                    "--shortform",
                    shortform,
                    "--no-sync",  # We don't want to sync each individual file
                ]
                # Inherit environment so lib imports work in subprocess
                if subprocess.run(transcript_cmd, check=False).returncode != 0:
                    print(f"  ❌ Error transcribing {jf.name}")
                    artifact_success = False

            if artifact_success:
                state[state_key] = {
                    "id": art_id,
                    "name": name,
                    "synced_at": datetime.now().isoformat(),
                }
                new_count += 1

        print(f"✅ {repo}: fetched {new_count} new sessions, skipped {skipped_count} cached")
        total_new += new_count
        total_skipped += skipped_count

    if total_new > 0:
        save_state(state)
        # Optional: run git_sync once at the end if needed?
        # But sync_gha_sessions is usually part of a larger pipeline.


if __name__ == "__main__":
    main()
