#!/usr/bin/env python3
"""
Audit Skills - Comprehensive skill ecosystem auditing

Detects outdated patterns, missing features, and validation issues across skills.

Usage:
    audit_skills.py <skill-name>      # Audit single skill
    audit_skills.py --all              # Audit all skills
    audit_skills.py --all --json       # Output as JSON

Examples:
    audit_skills.py git-commit
    audit_skills.py --all
    audit_skills.py --all --json > audit-report.json
"""

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Get academicOps paths
ACADEMICOPS = os.environ.get("ACADEMICOPS", Path.home() / "src" / "bot")
SKILLS_DIR = Path(ACADEMICOPS) / "skills"

# Patterns to detect
OUTDATED_PATTERNS = {
    "agent-based": r"agent\s+(should|will|must)",
    "you-should": r"[Yy]ou\s+(should|must|will|can)",
    "old-references": r"docs/_CHUNKS",
    "pre-skills": r"\.claude/agents",
    "old-enforce": r"(axiomlevel|axiom-level)",
}

MISSING_FEATURES = {
    "@reference": r"@[a-zA-Z_]+",
    "claude-md": r"CLAUDE\.md",
    "enforcement": r"(Scripts?\s*>\s*Hooks?|Hooks?\s*>\s*Config)",
    "skill-refs": r"(skill|Skill):\s*\w+",
}

REQUIRED_STRUCTURE = {
    "frontmatter": r"^---\s*\nname:\s*\S+\s*\ndescription:\s*.+\n---",
    "imperative": r"^(Create|Build|Execute|Run|Generate|Validate|Update|Remove)",
}


def load_skill(skill_path: Path) -> dict[str, Any]:
    """Load a skill and extract its components."""
    result = {
        "name": skill_path.name,
        "path": str(skill_path),
        "exists": skill_path.exists(),
        "skill_md": None,
        "scripts": [],
        "references": [],
        "assets": [],
        "errors": [],
    }

    if not skill_path.exists():
        result["errors"].append(f"Skill directory not found: {skill_path}")
        return result

    # Load SKILL.md
    skill_md_path = skill_path / "SKILL.md"
    if skill_md_path.exists():
        try:
            result["skill_md"] = skill_md_path.read_text()
        except Exception as e:
            result["errors"].append(f"Failed to read SKILL.md: {e}")
    else:
        result["errors"].append("SKILL.md not found")

    # Find scripts
    scripts_dir = skill_path / "scripts"
    if scripts_dir.exists():
        result["scripts"] = [
            str(f.relative_to(skill_path)) for f in scripts_dir.glob("*.py")
        ]

    # Find references
    refs_dir = skill_path / "references"
    if refs_dir.exists():
        result["references"] = [
            str(f.relative_to(skill_path)) for f in refs_dir.glob("*.md")
        ]

    # Find assets
    assets_dir = skill_path / "assets"
    if assets_dir.exists():
        result["assets"] = [
            str(f.relative_to(skill_path)) for f in assets_dir.iterdir() if f.is_file()
        ]

    return result


def audit_outdated_patterns(skill: dict[str, Any]) -> dict[str, list[str]]:
    """Check for outdated patterns in skill content."""
    issues = {}

    if not skill.get("skill_md"):
        return {"error": ["No SKILL.md to audit"]}

    content = skill["skill_md"]

    for pattern_name, pattern_regex in OUTDATED_PATTERNS.items():
        matches = re.findall(pattern_regex, content, re.IGNORECASE | re.MULTILINE)
        if matches:
            issues[pattern_name] = [
                f"Found {len(matches)} instances of '{pattern_name}' pattern"
            ]
            # Add first few examples
            for match in matches[:3]:
                issues[pattern_name].append(f"  Example: ...{match}...")

    return issues


def audit_missing_features(skill: dict[str, Any]) -> dict[str, list[str]]:
    """Check for missing modern features."""
    issues = {}

    if not skill.get("skill_md"):
        return {"error": ["No SKILL.md to audit"]}

    content = skill["skill_md"]

    for feature_name, feature_regex in MISSING_FEATURES.items():
        if not re.search(feature_regex, content):
            issues[feature_name] = [f"Missing '{feature_name}' pattern"]

    return issues


def audit_structure(skill: dict[str, Any]) -> dict[str, list[str]]:
    """Validate skill structure and organization."""
    issues = {}

    # Check SKILL.md exists
    if not skill.get("skill_md"):
        issues["skill_md"] = ["SKILL.md file missing"]
        return issues

    content = skill["skill_md"]

    # Check frontmatter
    if not re.match(REQUIRED_STRUCTURE["frontmatter"], content, re.MULTILINE):
        issues["frontmatter"] = ["Invalid or missing YAML frontmatter"]

    # Check for imperative form
    lines = content.split("\n")
    non_imperative = []
    for i, line in enumerate(lines, 1):
        if line.startswith("#") and i > 10:  # Skip frontmatter area
            if not re.match(r"^#+\s*(" + REQUIRED_STRUCTURE["imperative"] + r")", line):
                # Check if it's not a general heading
                if re.match(r"^#+\s*[A-Z]", line) and " " in line:
                    non_imperative.append(f"Line {i}: {line[:50]}")

    if non_imperative:
        issues["imperative"] = ["Non-imperative headings found:", *non_imperative[:5]]

    # Check scripts are executable
    for script in skill.get("scripts", []):
        script_path = Path(skill["path"]) / script
        if script_path.exists() and not os.access(script_path, os.X_OK):
            if "scripts" not in issues:
                issues["scripts"] = []
            issues["scripts"].append(f"Script not executable: {script}")

    # Check references exist
    for ref in skill.get("references", []):
        ref_path = Path(skill["path"]) / ref
        if not ref_path.exists():
            if "references" not in issues:
                issues["references"] = []
            issues["references"].append(f"Reference not found: {ref}")

    return issues


def calculate_health_score(audit_result: dict[str, Any]) -> int:
    """Calculate overall health score for a skill (0-100)."""
    if audit_result.get("errors"):
        return 0

    score = 100

    # Deduct for outdated patterns (30 points max)
    outdated = audit_result.get("outdated_patterns", {})
    score -= min(len(outdated) * 10, 30)

    # Deduct for missing features (30 points max)
    missing = audit_result.get("missing_features", {})
    score -= min(len(missing) * 10, 30)

    # Deduct for structure issues (40 points max)
    structure = audit_result.get("structure_issues", {})
    score -= min(len(structure) * 15, 40)

    return max(score, 0)


def audit_skill(skill_name: str) -> dict[str, Any]:
    """Perform comprehensive audit of a single skill."""
    skill_path = SKILLS_DIR / skill_name

    # Load skill
    skill = load_skill(skill_path)

    # Run audits
    result = {
        "skill": skill_name,
        "path": str(skill_path),
        "timestamp": datetime.now().isoformat(),
        "errors": skill.get("errors", []),
    }

    if not result["errors"]:
        result["outdated_patterns"] = audit_outdated_patterns(skill)
        result["missing_features"] = audit_missing_features(skill)
        result["structure_issues"] = audit_structure(skill)
        result["health_score"] = calculate_health_score(result)
        result["resources"] = {
            "scripts": len(skill.get("scripts", [])),
            "references": len(skill.get("references", [])),
            "assets": len(skill.get("assets", [])),
        }
    else:
        result["health_score"] = 0

    return result


def audit_all_skills() -> dict[str, Any]:
    """Audit entire skill ecosystem."""
    if not SKILLS_DIR.exists():
        return {
            "error": f"Skills directory not found: {SKILLS_DIR}",
            "timestamp": datetime.now().isoformat(),
        }

    # Find all skills
    skills = [
        d.name for d in SKILLS_DIR.iterdir() if d.is_dir() and (d / "SKILL.md").exists()
    ]

    results = {
        "timestamp": datetime.now().isoformat(),
        "skills_dir": str(SKILLS_DIR),
        "total_skills": len(skills),
        "skills": {},
        "summary": {
            "healthy": 0,
            "warning": 0,
            "critical": 0,
            "error": 0,
        },
    }

    for skill_name in sorted(skills):
        audit_result = audit_skill(skill_name)
        results["skills"][skill_name] = audit_result

        # Categorize health
        score = audit_result.get("health_score", 0)
        if audit_result.get("errors"):
            results["summary"]["error"] += 1
        elif score >= 80:
            results["summary"]["healthy"] += 1
        elif score >= 50:
            results["summary"]["warning"] += 1
        else:
            results["summary"]["critical"] += 1

    return results


def format_audit_result(result: dict[str, Any], verbose: bool = True) -> str:
    """Format audit result for human reading."""
    output = []

    if "skills" in result:
        # Full ecosystem audit
        output.append("=" * 60)
        output.append("SKILL ECOSYSTEM AUDIT REPORT")
        output.append("=" * 60)
        output.append(f"Timestamp: {result['timestamp']}")
        output.append(f"Skills Directory: {result['skills_dir']}")
        output.append(f"Total Skills: {result['total_skills']}")
        output.append("")

        # Summary
        summary = result["summary"]
        output.append("SUMMARY")
        output.append("-" * 40)
        output.append(f"✅ Healthy (80-100): {summary['healthy']}")
        output.append(f"⚠️  Warning (50-79): {summary['warning']}")
        output.append(f"❌ Critical (0-49): {summary['critical']}")
        output.append(f"🚫 Error: {summary['error']}")
        output.append("")

        if verbose:
            # Individual skill reports
            for skill_name, skill_result in sorted(result["skills"].items()):
                output.append("-" * 60)
                output.extend(format_single_skill(skill_name, skill_result))
                output.append("")
    else:
        # Single skill audit
        output.extend(format_single_skill(result.get("skill", "Unknown"), result))

    return "\n".join(output)


def format_single_skill(skill_name: str, result: dict[str, Any]) -> list[str]:
    """Format a single skill audit result."""
    output = []

    score = result.get("health_score", 0)
    if score >= 80:
        icon = "✅"
    elif score >= 50:
        icon = "⚠️"
    else:
        icon = "❌"

    output.append(f"{icon} {skill_name} (Health: {score}/100)")
    output.append(f"   Path: {result.get('path', 'Unknown')}")

    if result.get("errors"):
        output.append("   🚫 ERRORS:")
        for error in result["errors"]:
            output.append(f"      - {error}")

    if result.get("outdated_patterns"):
        output.append("   📛 Outdated Patterns:")
        for pattern, issues in result["outdated_patterns"].items():
            output.append(f"      {pattern}:")
            for issue in issues[:3]:
                output.append(f"        - {issue}")

    if result.get("missing_features"):
        output.append("   ⚠️  Missing Features:")
        for feature, issues in result["missing_features"].items():
            output.append(f"      {feature}: {issues[0]}")

    if result.get("structure_issues"):
        output.append("   🏗️  Structure Issues:")
        for issue_type, issues in result["structure_issues"].items():
            output.append(f"      {issue_type}:")
            for issue in issues[:3]:
                output.append(f"        - {issue}")

    if result.get("resources"):
        res = result["resources"]
        output.append(
            f"   📦 Resources: {res['scripts']} scripts, {res['references']} refs, {res['assets']} assets"
        )

    return output


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    json_output = "--json" in sys.argv

    if "--all" in sys.argv:
        result = audit_all_skills()
    else:
        skill_name = sys.argv[1]
        if skill_name.startswith("--"):
            print(f"Error: Invalid skill name: {skill_name}")
            print(__doc__)
            sys.exit(1)
        result = audit_skill(skill_name)

    if json_output:
        print(json.dumps(result, indent=2))
    else:
        print(format_audit_result(result, verbose=True))


if __name__ == "__main__":
    main()
