#!/usr/bin/env python3
"""
Sync aOps framework to a project's .claude/ directory for web environments.

This creates a bundled .claude/ directory that works in limited environments
(like Claude Code Web) where only one repo is available and $AOPS is not set.

Usage:
    # Sync to another project (copies files)
    python sync_web_bundle.py /path/to/writing

    # Sync academicOps itself (uses symlinks)
    python sync_web_bundle.py --self

    # Sync without installing git hook
    python sync_web_bundle.py /path/to/writing --no-hook

What gets synced:
    - skills/ (all skill definitions)
    - commands/ (slash commands)
    - agents/ (agent definitions)
    - settings.json (web-compatible, no hooks)
    - CLAUDE.md (framework + project-specific if exists)
    - git post-commit hook (optional, for auto-sync)

Auto-sync features:
    - Git post-commit hook: Automatically syncs .claude/ on commits from full environments
    - GitHub Actions workflow: Template available in templates/github-workflow-sync-aops.yml
"""

import argparse
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import yaml

AOPS_ROOT = Path(__file__).parent.parent.resolve()


def get_aops_version() -> str:
    """Get current aOps commit SHA for version tracking."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=AOPS_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return "unknown"


def write_version_file(target: Path, dry_run: bool = False) -> None:
    """Write aOps version to .claude/.aops-version for tracking."""
    version = get_aops_version()
    version_file = target / ".aops-version"
    if dry_run:
        print(f"[DRY RUN] Would write version file: {version[:12]}...")
    else:
        version_file.write_text(version + "\n")
        print(f"  .aops-version ({version[:12]}...)")


def sync_to_self(dry_run: bool = False) -> int:
    """Sync .claude/ for academicOps repo itself using relative symlinks."""
    target = AOPS_ROOT / ".claude"
    if dry_run:
        print(f"[DRY RUN] Would create directory: {target}")
    else:
        target.mkdir(exist_ok=True)

    # Relative symlinks for self (academicOps IS the framework)
    links = {
        "skills": "../skills",
        "commands": "../commands",
        "agents": "../agents",
        "CLAUDE.md": "../CLAUDE.md",
        "settings.json": "../config/claude/settings-self.json",  # Self settings use CLAUDE_PROJECT_DIR
    }

    for name, rel_target in links.items():
        link_path = target / name
        if dry_run:
            print(f"[DRY RUN] Would create symlink: {name} -> {rel_target}")
            continue

        if link_path.is_symlink():
            current = link_path.readlink()
            if str(current) == rel_target:
                print(f"  {name} -> {rel_target} (unchanged)")
                continue
            link_path.unlink()
        elif link_path.exists():
            if link_path.is_dir():
                shutil.rmtree(link_path)
            else:
                link_path.unlink()

        link_path.symlink_to(rel_target)
        print(f"  {name} -> {rel_target}")

    if dry_run:
        print("\n[DRY RUN] Would sync academicOps .claude/ (symlinks to parent)")
    else:
        print("\nSynced academicOps .claude/ (symlinks to parent)")
    return 0


def install_git_hook(project_path: Path) -> bool:
    """Install git post-commit hook for auto-sync.

    Safety behavior:
    - If existing hook already contains aOps sync, skip (already installed)
    - If existing hook is NOT aOps, backup to post-commit.backup.{timestamp}
    - Append our hook content to existing hooks instead of overwriting
    """
    git_dir = project_path / ".git"
    if not git_dir.exists():
        print("  Skipping git hook (not a git repository)")
        return False

    hooks_dir = git_dir / "hooks"
    hooks_dir.mkdir(exist_ok=True)

    hook_src = AOPS_ROOT / "hooks" / "git-post-commit-sync-aops"
    hook_dst = hooks_dir / "post-commit"

    if not hook_src.exists():
        print(f"  Warning: Hook source not found: {hook_src}", file=sys.stderr)
        return False

    aops_hook_content = hook_src.read_text()
    aops_marker = "# aOps sync hook"  # Marker to identify our hook content

    # Check if hook already exists
    if hook_dst.exists():
        existing_content = hook_dst.read_text()

        # Check if aOps hook is already installed
        if aops_marker in existing_content or "aOps bundle" in existing_content:
            print("  git post-commit hook (aOps already installed, skipping)")
            return True

        # Existing hook is not aOps - backup before modifying
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_path = hooks_dir / f"post-commit.backup.{timestamp}"
        shutil.copy2(hook_dst, backup_path)
        print(f"  Backed up existing hook to {backup_path.name}")

        # Append our hook content to existing hook
        # Add a separator and marker for clarity
        combined_content = (
            existing_content.rstrip()
            + "\n\n"
            + "# "
            + "=" * 60
            + "\n"
            + f"{aops_marker} - installed by sync_web_bundle.py\n"
            + "# "
            + "=" * 60
            + "\n\n"
            + "# aOps sync logic (runs after existing hook)\n"
            + _extract_aops_logic(aops_hook_content)
        )

        hook_dst.write_text(combined_content)
        hook_dst.chmod(0o755)
        print("  git post-commit hook updated (aOps sync appended to existing)")
        return True

    # No existing hook - install fresh with marker
    marked_content = aops_hook_content.replace(
        "# Git post-commit hook to auto-sync aOps bundle",
        f"# Git post-commit hook to auto-sync aOps bundle\n{aops_marker}",
    )
    hook_dst.write_text(marked_content)
    hook_dst.chmod(0o755)
    print("  git post-commit hook installed (auto-sync on commit)")
    return True


def _extract_aops_logic(hook_content: str) -> str:
    """Extract the logic portion of the aOps hook (skip shebang for appending)."""
    lines = hook_content.split("\n")
    # Skip shebang and initial comments when appending to existing hook
    logic_lines = []
    in_logic = False
    for line in lines:
        if line.startswith("#!"):
            continue  # Skip shebang
        if not in_logic and line.startswith("#"):
            continue  # Skip header comments
        if not in_logic and line.strip() == "":
            continue  # Skip initial blank lines
        in_logic = True
        logic_lines.append(line)
    return "\n".join(logic_lines)


def sync_to_project(
    project_path: Path,
    force: bool = False,
    install_hook: bool = True,
    dry_run: bool = False,
) -> int:
    """Sync .claude/ to another project by copying files."""
    if not project_path.exists():
        print(f"Error: Project path does not exist: {project_path}", file=sys.stderr)
        return 1

    if not project_path.is_dir():
        print(
            f"Error: Project path must be a directory: {project_path}", file=sys.stderr
        )
        return 1

    target = project_path / ".claude"

    # Check for existing .claude with non-aops content
    if target.exists() and not force:
        marker = target / ".aops-bundle"
        if not marker.exists():
            print(
                f"Error: {target} exists but wasn't created by sync_web_bundle.py",
                file=sys.stderr,
            )
            print("Use --force to overwrite", file=sys.stderr)
            return 1

    # Clean and recreate
    if dry_run:
        if target.exists():
            print(f"[DRY RUN] Would remove existing: {target}")
        print(f"[DRY RUN] Would create directory: {target}")
    else:
        if target.exists():
            shutil.rmtree(target)
        target.mkdir()

    # Copy directories
    for dir_name in ["skills", "commands", "agents"]:
        src = AOPS_ROOT / dir_name
        dst = target / dir_name
        if src.exists():
            # Count files in source for reporting
            count = sum(1 for file_path in src.rglob("*") if file_path.is_file())
            if dry_run:
                print(f"[DRY RUN] Would copy {dir_name}/ ({count} files)")
            else:
                shutil.copytree(
                    src,
                    dst,
                    ignore=shutil.ignore_patterns(
                        "__pycache__", "*.pyc", ".pytest_cache", "tests"
                    ),
                )
                # Recount after copy (may differ due to ignore patterns)
                count = sum(1 for file_path in dst.rglob("*") if file_path.is_file())
                print(f"  {dir_name}/ ({count} files)")

    # Copy web-compatible settings
    settings_src = AOPS_ROOT / "config" / "claude" / "settings-web.json"
    settings_dst = target / "settings.json"
    if dry_run:
        print("[DRY RUN] Would copy settings.json (web-compatible, no hooks)")
    else:
        shutil.copy2(settings_src, settings_dst)
        print("  settings.json (web-compatible, no hooks)")

    # Generate CLAUDE.md
    claude_md = generate_claude_md(project_path)
    if dry_run:
        print("[DRY RUN] Would generate CLAUDE.md")
    else:
        (target / "CLAUDE.md").write_text(claude_md)
        print("  CLAUDE.md (generated)")

    # Create marker file
    if dry_run:
        print("[DRY RUN] Would create .aops-bundle marker")
    else:
        (target / ".aops-bundle").write_text(
            f"aOps bundle synced from {AOPS_ROOT}\n"
            f"This directory is managed by sync_web_bundle.py\n"
            f"Do not edit manually - changes will be overwritten\n"
        )

    # Write version file for tracking
    write_version_file(target, dry_run=dry_run)

    # Install git hook for auto-sync
    if install_hook:
        if dry_run:
            print("[DRY RUN] Would install git post-commit hook")
        else:
            install_git_hook(project_path)

    if dry_run:
        print(f"\n[DRY RUN] Would sync to {target} (copied files)")
    else:
        print(f"\nSynced to {target} (copied files)")
        print("Commit this .claude/ directory to use aOps on Claude Code Web")
        if install_hook:
            print(
                "Git hook installed - .claude/ will auto-sync on future commits from full environments"
            )
    return 0


def get_skills_for_bundle() -> list[dict]:
    """Scan skills directory and extract metadata from SKILL.md files.

    Returns:
        List of dicts with 'name' and 'description' keys for each skill.
    """
    skills_dir = AOPS_ROOT / "skills"
    skills = []

    if not skills_dir.exists():
        return skills

    for skill_dir in sorted(skills_dir.iterdir()):
        if not skill_dir.is_dir():
            continue

        skill_file = skill_dir / "SKILL.md"
        if not skill_file.exists():
            continue

        try:
            content = skill_file.read_text()
            # Parse YAML frontmatter (between first two ---)
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    frontmatter = yaml.safe_load(parts[1])
                    if frontmatter:
                        # Use 'name' or 'title' field
                        name = frontmatter.get("name") or frontmatter.get("title")
                        description = frontmatter.get("description", "")

                        if name:
                            # Truncate long descriptions
                            if len(description) > 60:
                                description = description[:60] + "..."

                            skills.append(
                                {
                                    "name": name,
                                    "description": description,
                                }
                            )
        except (yaml.YAMLError, OSError):
            # Skip malformed skills gracefully
            continue

    return skills


def generate_claude_md(project_path: Path) -> str:
    """Generate CLAUDE.md for a project bundle."""
    # Check for existing project-specific CLAUDE.md
    existing_claude_md = project_path / "CLAUDE.md"
    project_specific = ""
    if existing_claude_md.exists():
        content = existing_claude_md.read_text()
        # Check if it's not already an aops-generated one
        if "aOps Framework Bundle" not in content:
            project_specific = f"\n## Project-Specific Instructions\n\n{content}"

    # Generate dynamic skills table
    skills = get_skills_for_bundle()
    if skills:
        # Limit to top 10 skills for readability
        display_skills = skills[:10]
        skills_table = "| Skill | Purpose |\n|-------|---------|"
        for skill in display_skills:
            skills_table += f"\n| {skill['name']} | {skill['description']} |"
        if len(skills) > 10:
            skills_table += f"\n\n*...and {len(skills) - 10} more skills available*"
    else:
        skills_table = "*No skills found*"

    return f"""# aOps Framework Bundle

This project uses the academicOps framework for Claude Code.

## Environment

This is a **bundled** installation for limited environments (Claude Code Web).

**Available features:**
- Skills: Use `Skill(skill="...")` to invoke specialized workflows
- Commands: Use `/command` for slash commands
- Agents: Agent definitions for Task tool

**Not available in this environment:**
- Hooks (require full $AOPS environment)
- MCP servers (require local setup)

## Key Skills

{skills_table}

## Usage

Invoke skills as needed:
```
Skill(skill="python-dev")  # For Python development
Skill(skill="analyst")      # For data analysis
```

## Updating

To update this bundle, run from the academicOps repo:
```bash
python scripts/sync_web_bundle.py /path/to/{project_path.name}
```
{project_specific}
"""


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sync aOps framework to a project's .claude/ directory"
    )

    # Mutually exclusive: either --self or project_path (one required)
    target_group = parser.add_mutually_exclusive_group(required=True)
    target_group.add_argument(
        "project_path",
        nargs="?",
        type=Path,
        help="Path to target project directory",
    )
    target_group.add_argument(
        "--self",
        action="store_true",
        dest="sync_self",
        help="Sync academicOps itself (uses symlinks)",
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing .claude/ even if not created by sync",
    )
    parser.add_argument(
        "--no-hook",
        action="store_true",
        help="Skip installing git post-commit hook",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )

    args = parser.parse_args()

    print("aOps Web Bundle Sync")
    print("=" * 40)
    if args.dry_run:
        print("[DRY RUN MODE - no changes will be made]\n")

    if args.sync_self:
        return sync_to_self(dry_run=args.dry_run)
    else:
        return sync_to_project(
            args.project_path.resolve(),
            force=args.force,
            install_hook=not args.no_hook,
            dry_run=args.dry_run,
        )


if __name__ == "__main__":
    sys.exit(main())
