#!/usr/bin/env python3
"""
Installation script for AcademicOps Gemini framework.
Replaces setup.sh logic.
"""

import os
import sys
import shutil
import json
import subprocess
import argparse
from pathlib import Path

# Add shared lib to path
SCRIPT_DIR = Path(__file__).parent.resolve()
sys.path.append(str(SCRIPT_DIR / "lib"))

try:
    from build_utils import safe_symlink
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


def configure_memory_server(aca_data_path: str):
    """Configure the memory MCP server."""
    print("Configuring memory server...")
    memory_config_dir = Path.home() / ".memory"
    memory_config = memory_config_dir / "config.json"

    config_data = {}
    if memory_config.exists():
        try:
            with open(memory_config) as f:
                config_data = json.load(f)
        except json.JSONDecodeError:
            pass

    if not memory_config_dir.exists():
        memory_config_dir.mkdir(parents=True)

    projects = config_data.get("projects", {})
    projects["main"] = aca_data_path

    config_data["projects"] = projects
    config_data["default_project"] = "main"
    config_data["default_project_mode"] = True

    with open(memory_config, "w") as f:
        json.dump(config_data, f, indent=2)
    print("✓ Memory server configured")


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
        if (
            "# aOps session insights" in line
            or "scripts/cron_session_insights.sh" in line
        ):
            continue
        new_crontab_lines.append(line)

    new_crontab_lines.append("# aOps task index")
    cron_cmd = f"*/5 * * * * cd {aops_path} && ACA_DATA={aca_data_path} uv run python scripts/regenerate_task_index.py >> /tmp/task-index.log 2>&1"
    new_crontab_lines.append(cron_cmd)

    new_crontab_lines.append("# aOps transcripts")
    transcript_cmd = f"*/30 * * * * cd {aops_path} && ACA_DATA={aca_data_path} uv run python aops-core/scripts/transcript.py --recent >> /tmp/aops-transcripts.log 2>&1"
    new_crontab_lines.append(transcript_cmd)

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
            if (
                "# aOps task index" in line
                or "scripts/regenerate_task_index.py" in line
            ):
                continue
            if "# aOps transcripts" in line or "scripts/transcript.py" in line:
                continue
            if (
                "# aOps session insights" in line
                or "scripts/cron_session_insights.sh" in line
            ):
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
        for ext in ["aops-core", "aops-tools", "academic-ops-core"]:
            run_command(["gemini", "extensions", "uninstall", ext], check=False)
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
    parser.add_argument(
        "--disable", action="store_true", help="Disable/Uninstall framework"
    )
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
    run_command(
        [sys.executable, str(aops_root / "scripts" / "build.py")], env=os.environ
    )

    print("\n=== Phase 2: Install ===")

    generate_paths_md(aops_root)

    gemini_dir = Path.home() / ".gemini"
    gemini_dir.mkdir(exist_ok=True)

    src_gemini_md = aops_root / "aops-core" / "GEMINI.md"
    if src_gemini_md.exists():
        content = src_gemini_md.read_text()
        content = content.replace("${AOPS}", str(aops_root))
        content = content.replace("${ACA_DATA}", str(aca_data_path))
        (gemini_dir / "GEMINI.md").write_text(content)
        print("✓ Generated ~/.gemini/GEMINI.md")

    ag_dir = gemini_dir / "antigravity"
    ag_dir.mkdir(parents=True, exist_ok=True)
    global_workflows = ag_dir / "global_workflows"
    global_workflows.mkdir(exist_ok=True)
    safe_symlink(gemini_dir / "GEMINI.md", global_workflows / "GEMINI.md")

    # Install Skills
    print("Installing Skills...")
    global_skills = ag_dir / "global_skills"
    global_skills.mkdir(exist_ok=True)
    skills_src = aops_root / "aops-core" / "skills"
    if skills_src.exists():
        for item in skills_src.iterdir():
            if item.is_dir() and not item.name.startswith("."):
                safe_symlink(item, global_skills / item.name)

    # Install Commands
    print("Installing Commands...")
    global_commands = ag_dir / "global_commands"
    global_commands.mkdir(exist_ok=True)
    commands_src = aops_root / "aops-core" / "commands"
    if commands_src.exists():
        for item in commands_src.iterdir():
            if item.is_file() and not item.name.startswith("."):
                safe_symlink(item, global_commands / item.name)

    dist_mcp_config = aops_root / "dist" / "antigravity" / "mcp_config.json"
    if dist_mcp_config.exists():
        safe_symlink(dist_mcp_config, ag_dir / "mcp_config.json")

    print("\n=== Phase 3: Link Extensions ===")
    if shutil.which("gemini"):
        # Link aops-core
        dist_core = aops_root / "dist" / "aops-core"
        if dist_core.exists():
            print(f"Installing extension: {dist_core}")
            # Uninstall first to avoid "already installed" error
            run_command(["gemini", "extensions", "uninstall", "aops-core"], check=False)
            run_command(
                [
                    "gemini",
                    "extensions",
                    "link",
                    str(dist_core),
                    "--consent",
                    # "--pre-release",
                ],
                check=False,
            )
        else:
            print(f"Warning: {dist_core} not found. Skipping link.")

        # Link aops-tools
        dist_tools = aops_root / "dist" / "aops-tools"
        if dist_tools.exists():
            print(f"Installing extension: {dist_tools}")
            # Uninstall first to avoid "already installed" error
            run_command(
                ["gemini", "extensions", "uninstall", "aops-tools"], check=False
            )
            run_command(
                [
                    "gemini",
                    "extensions",
                    "link",
                    str(dist_tools),
                    "--consent",
                    # "--pre-release",
                ],
                check=False,
            )
    else:
        print("Warning: 'gemini' executable not found. Skipping extension linking.")


if __name__ == "__main__":
    main()
