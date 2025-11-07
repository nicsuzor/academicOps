#!/usr/bin/env python3
"""
Package Skills - Generate distribution packages from source skills

Creates validated .zip files for skill distribution.

Usage:
    package_skills.py <skill-name>     # Package single skill
    package_skills.py --all             # Package all skills
    package_skills.py <skill-name> --output <dir>  # Specify output directory

Examples:
    package_skills.py git-commit
    package_skills.py --all
    package_skills.py test-writing --output ./dist/skills
"""

import os
import subprocess
import sys
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

# Get academicOps paths
ACADEMICOPS = os.environ.get("ACADEMICOPS", Path.home() / "src" / "bot")
SKILLS_DIR = Path(ACADEMICOPS) / "skills"
DEFAULT_OUTPUT_DIR = Path(ACADEMICOPS) / "dist" / "skills"

# Files to exclude from packages
EXCLUDE_PATTERNS = {
    "__pycache__",
    ".pyc",
    ".pyo",
    ".DS_Store",
    ".git",
    ".gitignore",
    "*.swp",
    "*.bak",
    "*~",
    "Thumbs.db",
}


def should_exclude(path: Path) -> bool:
    """Check if a file should be excluded from packaging."""
    name = path.name

    # Check exact matches
    if name in EXCLUDE_PATTERNS:
        return True

    # Check patterns
    for pattern in EXCLUDE_PATTERNS:
        if pattern.startswith("*") and name.endswith(pattern[1:]):
            return True

    # Check if it's a cache directory
    return bool(path.is_dir() and name == "__pycache__")


def validate_skill_before_packaging(skill_path: Path) -> tuple[bool, list[str]]:
    """Validate skill before packaging."""
    errors = []

    # Check SKILL.md exists
    skill_md = skill_path / "SKILL.md"
    if not skill_md.exists():
        errors.append("SKILL.md not found")
        return False, errors

    # Run validation script if available
    validate_script = Path(__file__).parent / "validate_skill.py"
    if validate_script.exists():
        try:
            result = subprocess.run(
                [sys.executable, str(validate_script), skill_path.name],
                check=False,
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0:
                errors.append("Validation failed")
                if result.stdout:
                    # Extract error lines
                    for line in result.stdout.split("\n"):
                        if "❌" in line or "ERROR" in line:
                            errors.append(line.strip())
        except subprocess.TimeoutExpired:
            errors.append("Validation timeout")
        except Exception as e:
            errors.append(f"Validation error: {e}")

    return len(errors) == 0, errors


def package_skill(skill_name: str, output_dir: Path) -> dict[str, Any]:
    """Package a single skill into a zip file."""
    skill_path = SKILLS_DIR / skill_name

    result = {
        "skill": skill_name,
        "source": str(skill_path),
        "success": False,
        "output": None,
        "errors": [],
        "warnings": [],
        "stats": {},
    }

    # Check skill exists
    if not skill_path.exists():
        result["errors"].append(f"Skill not found: {skill_path}")
        return result

    # Validate before packaging
    valid, validation_errors = validate_skill_before_packaging(skill_path)
    if not valid:
        result["errors"].extend(validation_errors)
        result["errors"].append("Skill validation failed - cannot package")
        return result

    # Create output directory if needed
    output_dir.mkdir(parents=True, exist_ok=True)

    # Output file path
    output_file = output_dir / f"{skill_name}.zip"

    # Create zip file
    try:
        with zipfile.ZipFile(output_file, "w", zipfile.ZIP_DEFLATED) as zf:
            file_count = 0
            total_size = 0

            # Add all files from skill directory
            for root, dirs, files in os.walk(skill_path):
                root_path = Path(root)

                # Filter directories
                dirs[:] = [d for d in dirs if not should_exclude(root_path / d)]

                for file in files:
                    file_path = root_path / file

                    if should_exclude(file_path):
                        continue

                    # Calculate relative path for zip
                    rel_path = file_path.relative_to(skill_path.parent)

                    # Add file to zip
                    zf.write(file_path, rel_path)
                    file_count += 1
                    total_size += file_path.stat().st_size

                    # Preserve executable permissions for scripts
                    if file_path.suffix == ".py" and "scripts" in str(rel_path):
                        # Get file info
                        info = zf.getinfo(str(rel_path))
                        # Set executable bit (Unix)
                        info.external_attr = 0o755 << 16

        # Verify zip file
        with zipfile.ZipFile(output_file, "r") as zf:
            if zf.testzip() is not None:
                result["errors"].append("Zip file verification failed")
                output_file.unlink()
                return result

        # Success
        result["success"] = True
        result["output"] = str(output_file)
        result["stats"] = {
            "files": file_count,
            "size_bytes": total_size,
            "size_mb": round(total_size / (1024 * 1024), 2),
            "compressed_size_bytes": output_file.stat().st_size,
            "compressed_size_mb": round(output_file.stat().st_size / (1024 * 1024), 2),
        }

    except Exception as e:
        result["errors"].append(f"Packaging error: {e}")
        if output_file.exists():
            output_file.unlink()

    return result


def package_all_skills(output_dir: Path) -> dict[str, Any]:
    """Package all skills in the ecosystem."""
    if not SKILLS_DIR.exists():
        return {"error": f"Skills directory not found: {SKILLS_DIR}"}

    # Find all skills
    skills = [
        d.name for d in SKILLS_DIR.iterdir() if d.is_dir() and (d / "SKILL.md").exists()
    ]

    results = {
        "timestamp": datetime.now().isoformat(),
        "output_dir": str(output_dir),
        "total_skills": len(skills),
        "packaged": 0,
        "failed": 0,
        "skills": {},
    }

    for skill_name in sorted(skills):
        print(f"Packaging {skill_name}...")
        result = package_skill(skill_name, output_dir)
        results["skills"][skill_name] = result

        if result["success"]:
            results["packaged"] += 1
        else:
            results["failed"] += 1

    return results


def format_package_result(result: dict[str, Any]) -> str:
    """Format packaging result for human reading."""
    output = []

    if "skills" in result:
        # Multiple skills
        output.append("=" * 60)
        output.append("SKILL PACKAGING REPORT")
        output.append("=" * 60)
        output.append(f"Timestamp: {result['timestamp']}")
        output.append(f"Output Directory: {result['output_dir']}")
        output.append(f"Total Skills: {result['total_skills']}")
        output.append(f"✅ Packaged: {result['packaged']}")
        output.append(f"❌ Failed: {result['failed']}")
        output.append("")

        for skill_name, skill_result in sorted(result["skills"].items()):
            output.extend(format_single_package(skill_name, skill_result))
            output.append("")
    else:
        # Single skill
        output.extend(format_single_package(result.get("skill", "Unknown"), result))

    return "\n".join(output)


def format_single_package(skill_name: str, result: dict[str, Any]) -> list[str]:
    """Format a single skill packaging result."""
    output = []

    icon = "✅" if result["success"] else "❌"
    output.append(f"{icon} {skill_name}")

    if result["success"]:
        output.append(f"   📦 Output: {result['output']}")
        if result.get("stats"):
            stats = result["stats"]
            output.append(
                f"   📊 Stats: {stats['files']} files, {stats['size_mb']}MB → {stats['compressed_size_mb']}MB"
            )

    if result.get("errors"):
        output.append("   ERRORS:")
        for error in result["errors"]:
            output.append(f"     ❌ {error}")

    if result.get("warnings"):
        output.append("   WARNINGS:")
        for warning in result["warnings"]:
            output.append(f"     ⚠️  {warning}")

    return output


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    # Parse output directory
    output_dir = DEFAULT_OUTPUT_DIR
    if "--output" in sys.argv:
        idx = sys.argv.index("--output")
        if idx + 1 < len(sys.argv):
            output_dir = Path(sys.argv[idx + 1])

    if "--all" in sys.argv:
        result = package_all_skills(output_dir)
    else:
        skill_name = sys.argv[1]
        if skill_name.startswith("--"):
            print(f"Error: Invalid skill name: {skill_name}")
            print(__doc__)
            sys.exit(1)

        result = package_skill(skill_name, output_dir)

    print(format_package_result(result))

    # Exit with error if packaging failed
    if "skills" in result:
        sys.exit(0 if result["failed"] == 0 else 1)
    else:
        sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    main()
