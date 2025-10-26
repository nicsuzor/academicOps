#!/usr/bin/env python3
"""
Update Skill - Apply framework evolution updates to skills

Updates skills to current best practices and patterns.

Usage:
    update_skill.py <skill-name>           # Update single skill
    update_skill.py --all                  # Update all skills
    update_skill.py <skill-name> --auto    # Apply updates automatically

Examples:
    update_skill.py git-commit
    update_skill.py --all
    update_skill.py test-writing --auto
"""

import sys
import os
import re
import shutil
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime

# Get academicOps paths
ACADEMICOPS_BOT = os.environ.get("ACADEMICOPS_BOT", Path.home() / "src" / "bot")
SKILLS_DIR = Path(ACADEMICOPS_BOT) / "skills"
BACKUP_DIR = Path(__file__).parent / "backups"

# Update patterns
PATTERN_UPDATES = {
    "you_should": {
        "pattern": r"[Yy]ou\s+(should|must|will|can)\s+",
        "replacement": lambda m: "",
        "description": "Remove second-person language",
    },
    "agent_references": {
        "pattern": r"agent\s+(should|will|must)\s+",
        "replacement": lambda m: "",
        "description": "Remove agent-specific language",
    },
    "old_paths": {
        "pattern": r"\.claude/agents",
        "replacement": lambda m: ".claude/skills",
        "description": "Update old agent paths to skills",
    },
    "chunks_references": {
        "pattern": r"docs/_CHUNKS",
        "replacement": lambda m: "references",
        "description": "Update old chunk references",
    },
}


class SkillUpdater:
    """Update skills to current framework patterns."""
    
    def __init__(self, skill_path: Path):
        self.skill_path = skill_path
        self.skill_name = skill_path.name
        self.changes_made = []
        self.backups_created = []
    
    def update(self, auto_apply: bool = False) -> Dict[str, Any]:
        """Update skill to current patterns."""
        result = {
            "skill": self.skill_name,
            "path": str(self.skill_path),
            "updated": False,
            "changes": [],
            "backups": [],
            "errors": [],
        }
        
        # Check skill exists
        if not self.skill_path.exists():
            result["errors"].append(f"Skill not found: {self.skill_path}")
            return result
        
        # Create backup
        backup_path = self.create_backup()
        if backup_path:
            self.backups_created.append(backup_path)
            result["backups"].append(str(backup_path))
        
        # Update SKILL.md
        skill_md_updates = self.update_skill_md(auto_apply)
        if skill_md_updates:
            result["changes"].extend(skill_md_updates)
        
        # Update scripts
        script_updates = self.update_scripts(auto_apply)
        if script_updates:
            result["changes"].extend(script_updates)
        
        # Update references
        ref_updates = self.update_references(auto_apply)
        if ref_updates:
            result["changes"].extend(ref_updates)
        
        # Fix structure issues
        structure_fixes = self.fix_structure(auto_apply)
        if structure_fixes:
            result["changes"].extend(structure_fixes)
        
        result["updated"] = len(result["changes"]) > 0
        
        return result
    
    def create_backup(self) -> Optional[Path]:
        """Create backup of skill before updates."""
        try:
            BACKUP_DIR.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = BACKUP_DIR / f"{self.skill_name}_{timestamp}"
            
            if self.skill_path.exists():
                shutil.copytree(self.skill_path, backup_path)
                return backup_path
        except Exception as e:
            print(f"Warning: Failed to create backup: {e}")
        return None
    
    def update_skill_md(self, auto_apply: bool) -> List[Dict[str, str]]:
        """Update SKILL.md content."""
        changes = []
        skill_md_path = self.skill_path / "SKILL.md"
        
        if not skill_md_path.exists():
            return changes
        
        content = skill_md_path.read_text()
        original_content = content
        
        # Apply pattern updates
        for update_name, update_info in PATTERN_UPDATES.items():
            pattern = update_info["pattern"]
            matches = re.findall(pattern, content)
            
            if matches:
                if auto_apply:
                    # Apply replacement
                    if callable(update_info["replacement"]):
                        content = re.sub(pattern, update_info["replacement"], content)
                    else:
                        content = re.sub(pattern, update_info["replacement"], content)
                    
                    changes.append({
                        "file": "SKILL.md",
                        "type": update_name,
                        "description": update_info["description"],
                        "count": len(matches),
                        "applied": True,
                    })
                else:
                    changes.append({
                        "file": "SKILL.md",
                        "type": update_name,
                        "description": update_info["description"],
                        "count": len(matches),
                        "applied": False,
                        "preview": f"Found {len(matches)} instances",
                    })
        
        # Convert to imperative form
        imperative_changes = self.convert_to_imperative(content)
        if imperative_changes:
            if auto_apply:
                content = imperative_changes
                changes.append({
                    "file": "SKILL.md",
                    "type": "imperative_form",
                    "description": "Convert headings to imperative form",
                    "applied": True,
                })
            else:
                changes.append({
                    "file": "SKILL.md",
                    "type": "imperative_form",
                    "description": "Convert headings to imperative form",
                    "applied": False,
                    "preview": "Would convert section headings",
                })
        
        # Write changes if applied
        if auto_apply and content != original_content:
            skill_md_path.write_text(content)
        
        return changes
    
    def convert_to_imperative(self, content: str) -> Optional[str]:
        """Convert section headings to imperative form."""
        lines = content.split("\n")
        changed = False
        
        for i, line in enumerate(lines):
            if line.startswith("#") and " " in line:
                # Extract heading level and text
                match = re.match(r"(#+)\s*(.+)", line)
                if match:
                    level, heading = match.groups()
                    
                    # Skip metadata and overview sections
                    if heading.lower() in ["overview", "introduction", "description"]:
                        continue
                    
                    # Convert common patterns
                    new_heading = heading
                    
                    # "How to X" -> "X"
                    if re.match(r"How to ", heading, re.IGNORECASE):
                        new_heading = re.sub(r"How to ", "", heading, flags=re.IGNORECASE)
                        new_heading = new_heading[0].upper() + new_heading[1:] if new_heading else new_heading
                    
                    # "X Process" -> "Execute X"
                    elif heading.endswith(" Process"):
                        base = heading[:-8]
                        new_heading = f"Execute {base}"
                    
                    # "X Workflow" -> "Follow X Workflow"
                    elif heading.endswith(" Workflow"):
                        new_heading = f"Follow {heading}"
                    
                    if new_heading != heading:
                        lines[i] = f"{level} {new_heading}"
                        changed = True
        
        return "\n".join(lines) if changed else None
    
    def update_scripts(self, auto_apply: bool) -> List[Dict[str, str]]:
        """Update scripts in scripts/ directory."""
        changes = []
        scripts_dir = self.skill_path / "scripts"
        
        if not scripts_dir.exists():
            return changes
        
        for script_path in scripts_dir.glob("*.py"):
            script_changes = self.update_python_file(script_path, auto_apply)
            if script_changes:
                changes.extend(script_changes)
        
        return changes
    
    def update_references(self, auto_apply: bool) -> List[Dict[str, str]]:
        """Update reference documents."""
        changes = []
        refs_dir = self.skill_path / "references"
        
        if not refs_dir.exists():
            return changes
        
        for ref_path in refs_dir.glob("*.md"):
            content = ref_path.read_text()
            original_content = content
            
            # Apply pattern updates
            for update_name, update_info in PATTERN_UPDATES.items():
                pattern = update_info["pattern"]
                matches = re.findall(pattern, content)
                
                if matches:
                    if auto_apply:
                        if callable(update_info["replacement"]):
                            content = re.sub(pattern, update_info["replacement"], content)
                        else:
                            content = re.sub(pattern, update_info["replacement"], content)
                        
                        changes.append({
                            "file": f"references/{ref_path.name}",
                            "type": update_name,
                            "description": update_info["description"],
                            "count": len(matches),
                            "applied": True,
                        })
                    else:
                        changes.append({
                            "file": f"references/{ref_path.name}",
                            "type": update_name,
                            "description": update_info["description"],
                            "count": len(matches),
                            "applied": False,
                        })
            
            # Write changes if applied
            if auto_apply and content != original_content:
                ref_path.write_text(content)
        
        return changes
    
    def update_python_file(self, file_path: Path, auto_apply: bool) -> List[Dict[str, str]]:
        """Update a Python file."""
        changes = []
        
        # Ensure shebang
        with open(file_path) as f:
            first_line = f.readline()
            content = f.read()
        
        if not first_line.startswith("#!/usr/bin/env python"):
            if auto_apply:
                new_content = "#!/usr/bin/env python3\n" + first_line + content
                file_path.write_text(new_content)
                changes.append({
                    "file": f"scripts/{file_path.name}",
                    "type": "shebang",
                    "description": "Add Python shebang",
                    "applied": True,
                })
            else:
                changes.append({
                    "file": f"scripts/{file_path.name}",
                    "type": "shebang",
                    "description": "Add Python shebang",
                    "applied": False,
                })
        
        # Ensure executable
        if not os.access(file_path, os.X_OK):
            if auto_apply:
                os.chmod(file_path, 0o755)
                changes.append({
                    "file": f"scripts/{file_path.name}",
                    "type": "permissions",
                    "description": "Make script executable",
                    "applied": True,
                })
            else:
                changes.append({
                    "file": f"scripts/{file_path.name}",
                    "type": "permissions",
                    "description": "Make script executable",
                    "applied": False,
                })
        
        return changes
    
    def fix_structure(self, auto_apply: bool) -> List[Dict[str, str]]:
        """Fix structural issues in skill."""
        changes = []
        
        # Remove example files
        example_files = [
            self.skill_path / "scripts" / "example.py",
            self.skill_path / "references" / "api_reference.md",
            self.skill_path / "references" / "example_reference.md",
            self.skill_path / "assets" / "example_asset.txt",
        ]
        
        for example_file in example_files:
            if example_file.exists():
                if auto_apply:
                    example_file.unlink()
                    changes.append({
                        "file": str(example_file.relative_to(self.skill_path)),
                        "type": "cleanup",
                        "description": "Remove example file",
                        "applied": True,
                    })
                else:
                    changes.append({
                        "file": str(example_file.relative_to(self.skill_path)),
                        "type": "cleanup",
                        "description": "Remove example file",
                        "applied": False,
                    })
        
        return changes


def update_all_skills(auto_apply: bool = False) -> Dict[str, Any]:
    """Update all skills in the ecosystem."""
    if not SKILLS_DIR.exists():
        return {"error": f"Skills directory not found: {SKILLS_DIR}"}
    
    # Find all skills
    skills = [
        d for d in SKILLS_DIR.iterdir()
        if d.is_dir() and (d / "SKILL.md").exists()
    ]
    
    results = {
        "timestamp": datetime.now().isoformat(),
        "total_skills": len(skills),
        "updated": 0,
        "unchanged": 0,
        "errors": 0,
        "skills": {},
    }
    
    for skill_path in sorted(skills):
        print(f"Updating {skill_path.name}...")
        updater = SkillUpdater(skill_path)
        result = updater.update(auto_apply=auto_apply)
        results["skills"][skill_path.name] = result
        
        if result.get("errors"):
            results["errors"] += 1
        elif result["updated"]:
            results["updated"] += 1
        else:
            results["unchanged"] += 1
    
    return results


def format_update_result(result: Dict[str, Any]) -> str:
    """Format update result for human reading."""
    output = []
    
    if "skills" in result:
        # Multiple skills
        output.append("=" * 60)
        output.append("SKILL UPDATE REPORT")
        output.append("=" * 60)
        output.append(f"Timestamp: {result['timestamp']}")
        output.append(f"Total Skills: {result['total_skills']}")
        output.append(f"✅ Updated: {result['updated']}")
        output.append(f"➖ Unchanged: {result['unchanged']}")
        output.append(f"❌ Errors: {result['errors']}")
        output.append("")
        
        for skill_name, skill_result in sorted(result["skills"].items()):
            if skill_result.get("changes") or skill_result.get("errors"):
                output.extend(format_single_update(skill_name, skill_result))
                output.append("")
    else:
        # Single skill
        output.extend(format_single_update(result.get("skill", "Unknown"), result))
    
    return "\n".join(output)


def format_single_update(skill_name: str, result: Dict[str, Any]) -> List[str]:
    """Format a single skill update result."""
    output = []
    
    if result.get("errors"):
        output.append(f"❌ {skill_name}")
        for error in result["errors"]:
            output.append(f"   Error: {error}")
    elif result.get("changes"):
        output.append(f"✅ {skill_name}")
        
        # Group changes by file
        by_file = {}
        for change in result["changes"]:
            file_name = change["file"]
            if file_name not in by_file:
                by_file[file_name] = []
            by_file[file_name].append(change)
        
        for file_name, file_changes in by_file.items():
            output.append(f"   📄 {file_name}:")
            for change in file_changes:
                status = "✅" if change.get("applied") else "🔍"
                output.append(f"      {status} {change['description']}")
                if change.get("preview"):
                    output.append(f"         Preview: {change['preview']}")
        
        if result.get("backups"):
            output.append(f"   💾 Backup: {result['backups'][0]}")
    else:
        output.append(f"➖ {skill_name} (no updates needed)")
    
    return output


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    auto_apply = "--auto" in sys.argv
    
    if auto_apply:
        print("🤖 Running in AUTO mode - will apply updates automatically")
    else:
        print("🔍 Running in PREVIEW mode - will show potential updates")
    
    if "--all" in sys.argv:
        result = update_all_skills(auto_apply=auto_apply)
    else:
        skill_name = sys.argv[1]
        if skill_name.startswith("--"):
            print(f"Error: Invalid skill name: {skill_name}")
            print(__doc__)
            sys.exit(1)
        
        skill_path = SKILLS_DIR / skill_name
        updater = SkillUpdater(skill_path)
        result = updater.update(auto_apply=auto_apply)
    
    print(format_update_result(result))
    
    if not auto_apply:
        print("\n💡 To apply these updates, run with --auto flag")


if __name__ == "__main__":
    main()
