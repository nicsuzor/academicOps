#!/usr/bin/env python3
"""
Package aOps framework for deployment to GitHub releases.

Creates a distributable archive containing everything needed for users to
install aOps into their .claude directory.

Excludes:
- Development/testing files (tests/, experiments/)
- Git metadata (.git/, .gitignore)
- Unused/temporary files (docs/_UNUSED/, docs/unsorted/)
- Python cache (__pycache__/, *.pyc)
- Environment-specific files (.env, .venv)
"""

import argparse
import json
import shutil
import subprocess
import sys
import tarfile
from datetime import datetime
from pathlib import Path
from typing import List, Set


def get_version() -> str:
    """Get version from git tag or generate from date."""
    try:
        result = subprocess.run(
            ["git", "describe", "--tags", "--abbrev=0"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass

    # Fallback to date-based version
    return f"v{datetime.now().strftime('%Y.%m.%d')}"


def get_git_commit() -> str:
    """Get current git commit hash."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except Exception:
        return "unknown"


def should_exclude(path: Path, repo_root: Path) -> bool:
    """Determine if a path should be excluded from the archive."""
    relative = path.relative_to(repo_root)
    parts = relative.parts

    # Exclude patterns
    exclude_dirs = {
        ".git",
        "__pycache__",
        ".pytest_cache",
        "tests",
        "experiments",
        ".venv",
        "venv",
        "node_modules",
        # Exclude the SOURCE .claude directory (created by setup.sh for development)
        # Users will create their own TARGET ~/.claude directory with symlinks
        ".claude",
    }

    exclude_doc_dirs = {
        "_UNUSED",
        "unsorted",
    }

    exclude_suffixes = {
        ".pyc",
        ".pyo",
        ".pyd",
        ".so",
        ".dylib",
        ".egg-info",
        ".env",
        ".DS_Store",
        ".gitignore",
        ".gitattributes",
    }

    # Check directory exclusions
    for part in parts:
        if part in exclude_dirs:
            return True
        if len(parts) > 1 and parts[0] == "docs" and part in exclude_doc_dirs:
            return True

    # Check suffix exclusions
    if any(str(path).endswith(suffix) for suffix in exclude_suffixes):
        return True

    return False


def get_files_to_package(repo_root: Path) -> List[Path]:
    """Get list of files to include in the package."""
    files: List[Path] = []

    # Required top-level files
    required_files = [
        "README.md",
        "CLAUDE.md",
        "LICENSE",  # If exists
    ]

    for file in required_files:
        file_path = repo_root / file
        if file_path.exists():
            files.append(file_path)

    # Required directories
    required_dirs = [
        "skills",
        "hooks",
        "scripts",
        "config",
        "docs",
        "agents",
        "commands",
    ]

    for dir_name in required_dirs:
        dir_path = repo_root / dir_name
        if not dir_path.exists():
            print(f"⚠️  Warning: Required directory {dir_name}/ not found")
            continue

        # Walk directory and add non-excluded files
        for item in dir_path.rglob("*"):
            if item.is_file() and not should_exclude(item, repo_root):
                files.append(item)

    return sorted(files)


def create_manifest(
    files: List[Path],
    repo_root: Path,
    version: str,
    commit: str,
) -> dict:
    """Create manifest with package metadata."""
    return {
        "name": "aops",
        "version": version,
        "commit": commit,
        "created": datetime.now().isoformat(),
        "description": "LLM Agent Infrastructure for Claude Code",
        "files": [str(f.relative_to(repo_root)) for f in files],
        "file_count": len(files),
    }


def create_install_guide(version: str) -> str:
    """Create installation guide content."""
    return f"""# aOps Installation Guide

Version: {version}

## Quick Install

1. Extract this archive to a directory of your choice:
   ```bash
   tar -xzf aops-{version}.tar.gz
   cd aops-{version}
   ```

2. Run the setup script:
   ```bash
   bash scripts/setup.sh
   ```

   This will:
   - Create symlinks in `~/.claude/` for global use
   - Create `.claude/` in this directory for remote coding
   - All symlinks point to the extracted files

3. Verify installation:
   ```bash
   ls -la ~/.claude/
   ```

   You should see symlinks to:
   - settings.json
   - hooks/
   - skills/
   - commands/
   - agents/
   - CLAUDE.md

## What Gets Installed

- **Skills**: Specialized workflows (analyst, tasks, git-commit, etc.)
- **Hooks**: Lifecycle automation (validation, logging, instruction loading)
- **Scripts**: Utility scripts for tasks, analysis, etc.
- **Config**: Claude Code settings and MCP server configuration
- **Docs**: Core axioms, patterns, and reference documentation
- **Commands**: Slash commands (/ttd, /err)
- **Agents**: Agent definitions (DEVELOPER.md)

## Usage

After installation, launch Claude Code from any directory. The aOps framework
will be available globally through the ~/.claude/ symlinks.

For remote coding (Claude on the web), the repository's .claude/ directory
will be automatically detected and used.

## Updating

To update to a new version:

1. Extract the new version to a different directory
2. Run the setup script again - it will replace the symlinks
3. Old files can be safely deleted

## Uninstallation

Remove the symlinks from ~/.claude/:

```bash
rm -rf ~/.claude/settings.json
rm -rf ~/.claude/hooks
rm -rf ~/.claude/skills
rm -rf ~/.claude/commands
rm -rf ~/.claude/agents
rm -rf ~/.claude/CLAUDE.md
```

## Troubleshooting

**Problem**: Symlinks are broken
**Solution**: Re-run `scripts/setup.sh` from the extracted directory

**Problem**: Skills not loading
**Solution**: Check that ~/.claude/skills/ points to the correct location

**Problem**: Hooks not running
**Solution**: Verify Claude Code settings enable hooks

## Support

For issues and questions:
- Repository: https://github.com/nicsuzor/aops
- Documentation: See docs/ directory
- Axioms: See docs/AXIOMS.md
"""


def create_archive(
    files: List[Path],
    repo_root: Path,
    output_path: Path,
    version: str,
    commit: str,
) -> None:
    """Create tar.gz archive with all files."""
    print(f"\n📦 Creating archive: {output_path}")

    # Create manifest
    manifest = create_manifest(files, repo_root, version, commit)

    # Create install guide
    install_guide = create_install_guide(version)

    try:
        with tarfile.open(output_path, "w:gz") as tar:
            # Add files
            for file_path in files:
                arcname = f"aops-{version}/{file_path.relative_to(repo_root)}"
                tar.add(file_path, arcname=arcname)
                print(f"  ✓ {file_path.relative_to(repo_root)}")

            # Add manifest
            import io
            manifest_data = json.dumps(manifest, indent=2).encode("utf-8")
            manifest_info = tarfile.TarInfo(name=f"aops-{version}/MANIFEST.json")
            manifest_info.size = len(manifest_data)
            tar.addfile(manifest_info, io.BytesIO(manifest_data))
            print(f"  ✓ MANIFEST.json")

            # Add install guide
            guide_data = install_guide.encode("utf-8")
            guide_info = tarfile.TarInfo(name=f"aops-{version}/INSTALL.md")
            guide_info.size = len(guide_data)
            tar.addfile(guide_info, io.BytesIO(guide_data))
            print(f"  ✓ INSTALL.md")
    except (OSError, tarfile.TarError) as e:
        print(f"❌ Error creating archive: {e}")
        print(f"   Possible causes:")
        print(f"   - Insufficient disk space")
        print(f"   - Permission denied for output path")
        print(f"   - File access issues during archiving")
        raise

    print(f"\n✅ Archive created: {output_path}")
    print(f"   Version: {version}")
    print(f"   Commit: {commit}")
    print(f"   Files: {len(files) + 2}")  # +2 for manifest and install guide
    print(f"   Size: {output_path.stat().st_size / 1024 / 1024:.2f} MB")


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Package aOps framework for deployment"
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        help="Output file path (default: dist/aops-VERSION.tar.gz)",
    )
    parser.add_argument(
        "--version",
        "-v",
        type=str,
        help="Version string (default: git tag or date-based)",
    )

    args = parser.parse_args()

    # Get repository root
    repo_root = Path(__file__).parent.parent.resolve()

    # Get version
    version = args.version or get_version()
    commit = get_git_commit()

    print(f"📋 aOps Deployment Packager")
    print(f"   Repository: {repo_root}")
    print(f"   Version: {version}")
    print(f"   Commit: {commit}")

    # Get files to package
    print("\n🔍 Scanning files...")
    files = get_files_to_package(repo_root)

    if not files:
        print("❌ Error: No files found to package")
        return 1

    print(f"   Found {len(files)} files")

    # Create output directory
    if args.output:
        output_path = args.output.resolve()
    else:
        dist_dir = repo_root / "dist"
        dist_dir.mkdir(exist_ok=True)
        output_path = dist_dir / f"aops-{version}.tar.gz"

    # Create archive
    create_archive(files, repo_root, output_path, version, commit)

    print(f"\n🚀 Ready for deployment!")
    print(f"\nNext steps:")
    print(f"  1. Test the archive:")
    print(f"     tar -tzf {output_path} | head -20")
    print(f"  2. Create GitHub release:")
    print(f"     gh release create {version} {output_path}")
    print(f"  3. Or upload manually to GitHub Releases")

    return 0


if __name__ == "__main__":
    sys.exit(main())
