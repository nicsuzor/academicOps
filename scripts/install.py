#!/usr/bin/env python3
"""
Installation script for AcademicOps Gemini framework.
Replaces setup.sh logic.
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

# Add shared lib to path
SCRIPT_DIR = Path(__file__).parent.resolve()
sys.path.append(str(SCRIPT_DIR / "lib"))

try:
    from build_utils import (
        check_installed_plugin_version,
        emit_version_mismatch_warning,
        get_git_commit_sha,
        safe_symlink,
    )
except ImportError:
    print("Error: Could not import build_utils.", file=sys.stderr)
    sys.exit(1)


def run_command(cmd, shell=False, env=None, check=True, **kwargs):
    """Run a command and check for errors."""
    try:
        subprocess.run(cmd, check=check, shell=shell, env=env, **kwargs)
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {e}")
        if check:
            sys.exit(1)


def check_env():
    """Check required environment variables."""
    aops = os.environ.get("AOPS")
    aca_data = os.environ.get("ACA_DATA")

    if not aops:
        aops = str(Path(__file__).parent.parent.resolve())
        os.environ["AOPS"] = aops
        print(f"Info: AOPS set to {aops}")

    if not aca_data:
        print("Error: ACA_DATA environment variable must be set.")
        print("Example: export ACA_DATA=~/aca-data")
        sys.exit(1)

    return Path(aops), Path(aca_data)


def install_cron_jobs(aops_path: Path, aca_data_path: str):
    """Install cron jobs."""
    print("Installing cron jobs...")
    try:
        current_crontab = subprocess.check_output(
            ["crontab", "-l"], stderr=subprocess.DEVNULL
        ).decode()
    except subprocess.CalledProcessError:
        current_crontab = ""

    new_crontab_lines = []

    for line in current_crontab.splitlines():
        if "# aOps task index" in line or "scripts/regenerate_task_index.py" in line:
            continue
        if "# aOps transcripts" in line or "scripts/transcript.py" in line:
            continue
        if "# aOps session insights" in line or "scripts/cron_session_insights.sh" in line:
            continue
        new_crontab_lines.append(line)

    new_crontab_lines.append("# aOps quick sync (brain + transcripts)")
    quick_sync_cmd = f"*/5 * * * * {aops_path}/scripts/repo-sync-cron.sh --quick >> /tmp/repo-sync-quick.log 2>&1"
    new_crontab_lines.append(quick_sync_cmd)

    new_crontab_lines.append("# aOps full maintenance (viz + sessions)")
    full_sync_cmd = (
        f"0 * * * * {aops_path}/scripts/repo-sync-cron.sh >> /tmp/repo-sync-cron.log 2>&1"
    )
    new_crontab_lines.append(full_sync_cmd)

    new_crontab_lines.append("# aOps refinery")
    refinery_cmd = f"*/5 * * * * cd {aops_path} && ACA_DATA={aca_data_path} uv run python scripts/refinery.py > /dev/null 2>&1"
    new_crontab_lines.append(refinery_cmd)

    new_crontab = "\n".join(new_crontab_lines) + "\n"

    p = subprocess.Popen(["crontab", "-"], stdin=subprocess.PIPE)
    p.communicate(input=new_crontab.encode())
    print("✓ Cron jobs installed")


def uninstall_framework(aops_path: Path):
    """Uninstall the framework."""
    print("Uninstalling framework...")

    # 1. Cron Jobs
    try:
        current_crontab = subprocess.check_output(
            ["crontab", "-l"], stderr=subprocess.DEVNULL
        ).decode()
        new_lines = []
        for line in current_crontab.splitlines():
            if "# aOps quick sync" in line or "repo-sync-cron.sh --quick" in line:
                continue
            if "# aOps full maintenance" in line or "repo-sync-cron.sh" in line:
                if "repo-sync-cron.sh --quick" not in line:
                    continue
            if "# aOps transcripts" in line or "scripts/transcript.py" in line:
                continue
            if "# aOps task index" in line or "scripts/regenerate_task_index.py" in line:
                continue
            if "# aOps session insights" in line or "scripts/cron_session_insights.sh" in line:
                continue
            if "# aOps refinery" in line or "scripts/refinery.py" in line:
                continue
            new_lines.append(line)

        new_crontab = "\n".join(new_lines) + "\n"
        p = subprocess.Popen(["crontab", "-"], stdin=subprocess.PIPE)
        p.communicate(input=new_crontab.encode())
        print("✓ Cron jobs removed")
    except Exception as e:
        print(f"Warning removing cron jobs: {e}")

    # 2. Gemini Extensions
    if shutil.which("gemini"):
        run_command(["gemini", "extensions", "uninstall", "aops-core"], check=False)
        print("✓ Gemini extensions uninstalled")

    # 3. Cleanup Files
    gemini_dir = Path.home() / ".gemini"

    # Remove symlinks
    for item in ["hooks", "commands", "GEMINI.md"]:
        path = gemini_dir / item
        if path.is_symlink() or path.exists():
            if path.is_dir() and not path.is_symlink():
                shutil.rmtree(path)
            else:
                path.unlink()

    # Clean Antigravity global workflow symlink
    ag_gw = gemini_dir / "antigravity" / "global_workflows" / "GEMINI.md"
    if ag_gw.exists():
        ag_gw.unlink()

    # Clean Project Rules
    project_rules = aops_path / ".agent" / "rules"
    if project_rules.exists():
        shutil.rmtree(project_rules)

    print("✓ Files cleaned up")
    print("Uninstallation complete.")


def generate_paths_md(aops_root: Path):
    """Run generate_framework_paths.py."""
    print("Generating .agent/PATHS.md...")
    script = aops_root / "aops-core" / "scripts" / "generate_framework_paths.py"
    if script.exists():
        run_command([sys.executable, str(script)], env=os.environ, check=False)


def main():
    parser = argparse.ArgumentParser(description="Install AcademicOps Gemini Framework")
    parser.add_argument("--disable", action="store_true", help="Disable/Uninstall framework")
    args = parser.parse_args()

    aops_path_str = os.environ.get("AOPS")
    # Quick resolve for uninstall even if env not set
    if not aops_path_str:
        aops_path_str = str(Path(__file__).parent.parent.resolve())

    aops_root = Path(aops_path_str)

    if args.disable:
        uninstall_framework(aops_root)
        return

    # For install, do full check
    _, aca_data_path = check_env()

    # 1. Run Build
    print("=== Phase 1: Build ===")
    run_command([sys.executable, str(aops_root / "scripts" / "build.py")], env=os.environ)

    print("\n=== Phase 2: Install ===")

    # Install Cron Jobs
    install_cron_jobs(aops_root, str(aca_data_path))

    generate_paths_md(aops_root)

    gemini_dir = Path.home() / ".gemini"
    gemini_dir.mkdir(exist_ok=True)

    src_gemini_md = aops_root / "aops-core" / "GEMINI.md"
    if src_gemini_md.exists():
        shutil.copy2(src_gemini_md, gemini_dir / "GEMINI.md")
        print("✓ Copied GEMINI.md to ~/.gemini/GEMINI.md")

    ag_dir = gemini_dir / "antigravity"
    ag_dir.mkdir(parents=True, exist_ok=True)
    global_workflows = ag_dir / "global_workflows"
    global_workflows.mkdir(exist_ok=True)
    safe_symlink(gemini_dir / "GEMINI.md", global_workflows / "GEMINI.md")

    # Install Skills
    print("Installing Skills...")
    global_skills = ag_dir / "global_skills"
    global_skills.mkdir(exist_ok=True)
    # Link from dist to ensure auto-generated agent skills are included.
    # New build naming uses 'aops-...' (aops-claude, aops-gemini, aops-antigravity)
    # Fall back to legacy 'aops-core' layout if present.
    candidate_skill_dirs = [
        aops_root / "dist" / "aops" / "skills",
        aops_root / "dist" / "aops-core" / "skills",
        aops_root / "dist" / "aops-claude" / "skills",
        aops_root / "dist" / "aops-gemini" / "skills",
        aops_root / "dist" / "aops-antigravity" / "skills",
    ]
    for skills_src in candidate_skill_dirs:
        if skills_src.exists() and skills_src.is_dir():
            for item in skills_src.iterdir():
                if item.is_dir() and not item.name.startswith("."):
                    safe_symlink(item, global_skills / item.name)
            break

    # Install Workflows
    print("Installing Workflows...")
    # 1. From workflows dir
    workflows_src = aops_root / "aops-core" / "workflows"
    if workflows_src.exists():
        for item in workflows_src.iterdir():
            if item.is_file() and not item.name.startswith("."):
                safe_symlink(item, global_workflows / item.name)

    # 2. Convert Commands to Workflows (symlink commands to global_workflows)
    # The user requested that commands also be available as workflows.
    commands_src = aops_root / "aops-core" / "commands"
    if commands_src.exists():
        for item in commands_src.iterdir():
            if item.is_file() and not item.name.startswith("."):
                # Symlink to global_workflows
                safe_symlink(item, global_workflows / item.name)

    # Install Commands (Legacy / Gemini CLI native)
    print("Installing Commands (Gemini)...")
    global_commands = ag_dir / "global_commands"
    global_commands.mkdir(exist_ok=True)
    if commands_src.exists():
        for item in commands_src.iterdir():
            if item.is_file() and not item.name.startswith("."):
                safe_symlink(item, global_commands / item.name)

    # mcp_config may be under dist/antigravity or dist/aops-antigravity depending on build
    for candidate in (
        aops_root / "dist" / "antigravity" / "mcp_config.json",
        aops_root / "dist" / "aops-antigravity" / "mcp_config.json",
    ):
        if candidate.exists():
            safe_symlink(candidate, ag_dir / "mcp_config.json")
            break

    # Check for version mismatches with installed Claude plugins
    print("\n=== Version Check ===")
    source_commit = get_git_commit_sha(aops_root)
    if source_commit:
        matches, installed_commit = check_installed_plugin_version("aops-core", source_commit)
        if not matches and installed_commit:
            emit_version_mismatch_warning("aops-core", source_commit, installed_commit)
        if matches:
            print(f"✓ Source commit {source_commit} matches installed plugin")
    else:
        print("⚠️  Could not determine source commit (not a git repo?)")

    print("\n=== Phase 3: Link Extensions ===")
    if shutil.which("gemini"):
        # Link Gemini extension. New builds name the directory 'aops-gemini'
        dist_core_gemini = None
        for name in ("aops-core-gemini", "aops-gemini"):
            candidate = aops_root / "dist" / name
            if candidate.exists():
                dist_core_gemini = candidate
                break

        if dist_core_gemini:
            print(f"Installing Gemini extension from: {dist_core_gemini}")
            print(f"This sets {dist_core_gemini.name}/ as the extension root.")
            # Uninstall first to avoid "already installed" error
            run_command(["gemini", "extensions", "uninstall", "aops-core"], check=False)
            run_command(
                [
                    "gemini",
                    "extensions",
                    "link",
                    str(dist_core_gemini),
                    "--consent",
                ],
                check=False,
            )
        else:
            print("Warning: Gemini extension dist not found. Skipping link.")
    else:
        print("Warning: 'gemini' executable not found. Skipping extension linking.")


if __name__ == "__main__":
    main()
