#!/usr/bin/env python3
"""
Validate Skill - Comprehensive validation of skill completeness and functionality

Validates skill structure, scripts, references, and cross-references.

Usage:
    validate_skill.py <skill-name>     # Validate single skill
    validate_skill.py --all             # Validate all skills
    validate_skill.py <skill-name> --fix  # Auto-fix fixable issues

Examples:
    validate_skill.py git-commit
    validate_skill.py --all
    validate_skill.py test-writing --fix
"""

import sys
import os
import ast
import subprocess
import yaml
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

# Get academicOps paths
ACADEMICOPS = os.environ.get("ACADEMICOPS", Path.home() / "src" / "bot")
SKILLS_DIR = Path(ACADEMICOPS) / "skills"


class SkillValidator:
    """Comprehensive skill validation system."""
    
    def __init__(self, skill_path: Path):
        self.skill_path = skill_path
        self.skill_name = skill_path.name
        self.errors = []
        self.warnings = []
        self.fixes_applied = []
    
    def validate(self, auto_fix: bool = False) -> Dict[str, Any]:
        """Run all validation checks."""
        result = {
            "skill": self.skill_name,
            "path": str(self.skill_path),
            "valid": True,
            "errors": [],
            "warnings": [],
            "fixes_applied": [],
        }
        
        # Check skill exists
        if not self.skill_path.exists():
            result["valid"] = False
            result["errors"].append(f"Skill directory not found: {self.skill_path}")
            return result
        
        # Run validations
        self.validate_structure()
        self.validate_frontmatter()
        self.validate_scripts()
        self.validate_references()
        self.validate_assets()
        self.validate_cross_references()
        
        # Apply fixes if requested
        if auto_fix and self.errors:
            self.apply_fixes()
        
        # Compile results
        result["errors"] = self.errors
        result["warnings"] = self.warnings
        result["fixes_applied"] = self.fixes_applied
        result["valid"] = len(self.errors) == 0
        
        return result
    
    def validate_structure(self):
        """Validate directory structure and required files."""
        # Check SKILL.md exists
        skill_md_path = self.skill_path / "SKILL.md"
        if not skill_md_path.exists():
            self.errors.append("Required file SKILL.md not found")
            return
        
        # Check for valid subdirectories
        allowed_dirs = {"scripts", "references", "assets"}
        for item in self.skill_path.iterdir():
            if item.is_dir() and item.name not in allowed_dirs:
                if not item.name.startswith("."):
                    self.warnings.append(f"Unexpected directory: {item.name}")
        
        # Check for README or other unnecessary files
        unnecessary_files = {"README.md", "readme.md", ".DS_Store"}
        for filename in unnecessary_files:
            if (self.skill_path / filename).exists():
                self.warnings.append(f"Unnecessary file: {filename}")
    
    def validate_frontmatter(self):
        """Validate YAML frontmatter in SKILL.md."""
        skill_md_path = self.skill_path / "SKILL.md"
        if not skill_md_path.exists():
            return
        
        content = skill_md_path.read_text()
        
        # Extract frontmatter
        if not content.startswith("---"):
            self.errors.append("SKILL.md missing YAML frontmatter")
            return
        
        try:
            # Find end of frontmatter
            end_idx = content.index("\n---\n", 4)
            frontmatter = content[4:end_idx]
            
            # Parse YAML
            data = yaml.safe_load(frontmatter)
            
            # Check required fields
            if "name" not in data:
                self.errors.append("Frontmatter missing required 'name' field")
            elif data["name"] != self.skill_name:
                self.errors.append(f"Frontmatter name '{data['name']}' doesn't match directory '{self.skill_name}'")
            
            if "description" not in data:
                self.errors.append("Frontmatter missing required 'description' field")
            elif len(data.get("description", "")) < 50:
                self.warnings.append("Description too short (< 50 chars)")
            elif not data.get("description", "").startswith("This skill"):
                self.warnings.append("Description should start with 'This skill'")
            
        except ValueError:
            self.errors.append("Invalid YAML frontmatter format")
        except yaml.YAMLError as e:
            self.errors.append(f"YAML parsing error: {e}")
    
    def validate_scripts(self):
        """Validate scripts in scripts/ directory."""
        scripts_dir = self.skill_path / "scripts"
        if not scripts_dir.exists():
            return
        
        for script_path in scripts_dir.glob("*.py"):
            # Check executable
            if not os.access(script_path, os.X_OK):
                self.warnings.append(f"Script not executable: {script_path.name}")
            
            # Check syntax
            try:
                with open(script_path) as f:
                    ast.parse(f.read())
            except SyntaxError as e:
                self.errors.append(f"Python syntax error in {script_path.name}: {e}")
            
            # Check shebang
            with open(script_path) as f:
                first_line = f.readline()
                if not first_line.startswith("#!/usr/bin/env python"):
                    self.warnings.append(f"Missing or incorrect shebang in {script_path.name}")
        
        # Check for example.py
        if (scripts_dir / "example.py").exists():
            self.warnings.append("Example file scripts/example.py should be removed")
    
    def validate_references(self):
        """Validate reference documents."""
        refs_dir = self.skill_path / "references"
        if not refs_dir.exists():
            return
        
        for ref_path in refs_dir.glob("*.md"):
            # Check file is not empty
            if ref_path.stat().st_size == 0:
                self.warnings.append(f"Empty reference file: {ref_path.name}")
            
            # Check for proper markdown
            content = ref_path.read_text()
            if not content.strip():
                self.warnings.append(f"Reference file has no content: {ref_path.name}")
            elif not any(content.startswith(h) for h in ["#", "##"]):
                self.warnings.append(f"Reference file missing headers: {ref_path.name}")
        
        # Check for example files
        example_files = ["api_reference.md", "example_reference.md"]
        for example in example_files:
            if (refs_dir / example).exists():
                self.warnings.append(f"Example file references/{example} should be removed")
    
    def validate_assets(self):
        """Validate asset files."""
        assets_dir = self.skill_path / "assets"
        if not assets_dir.exists():
            return
        
        for asset_path in assets_dir.iterdir():
            if asset_path.is_file():
                # Check for example files
                if "example" in asset_path.name.lower():
                    self.warnings.append(f"Example asset should be removed: {asset_path.name}")
                
                # Check file size (warn if > 10MB)
                size_mb = asset_path.stat().st_size / (1024 * 1024)
                if size_mb > 10:
                    self.warnings.append(f"Large asset file ({size_mb:.1f}MB): {asset_path.name}")
    
    def validate_cross_references(self):
        """Validate references to other skills and files."""
        skill_md_path = self.skill_path / "SKILL.md"
        if not skill_md_path.exists():
            return
        
        content = skill_md_path.read_text()
        
        # Find references to scripts/
        script_refs = re.findall(r'scripts/([a-zA-Z0-9_\-]+\.py)', content)
        for script_name in script_refs:
            script_path = self.skill_path / "scripts" / script_name
            if not script_path.exists():
                self.errors.append(f"Referenced script not found: scripts/{script_name}")
        
        # Find references to references/
        ref_refs = re.findall(r'references/([a-zA-Z0-9_\-]+\.md)', content)
        for ref_name in ref_refs:
            ref_path = self.skill_path / "references" / ref_name
            if not ref_path.exists():
                self.errors.append(f"Referenced document not found: references/{ref_name}")
        
        # Find references to assets/
        asset_refs = re.findall(r'assets/([a-zA-Z0-9_\-]+\.[a-zA-Z0-9]+)', content)
        for asset_name in asset_refs:
            asset_path = self.skill_path / "assets" / asset_name
            if not asset_path.exists():
                self.warnings.append(f"Referenced asset not found: assets/{asset_name}")
    
    def apply_fixes(self):
        """Apply automatic fixes for common issues."""
        # Make scripts executable
        scripts_dir = self.skill_path / "scripts"
        if scripts_dir.exists():
            for script_path in scripts_dir.glob("*.py"):
                if not os.access(script_path, os.X_OK):
                    os.chmod(script_path, 0o755)
                    self.fixes_applied.append(f"Made executable: {script_path.name}")
        
        # Remove example files
        example_files = [
            self.skill_path / "scripts" / "example.py",
            self.skill_path / "references" / "api_reference.md",
            self.skill_path / "references" / "example_reference.md",
            self.skill_path / "assets" / "example_asset.txt",
        ]
        for example_file in example_files:
            if example_file.exists():
                example_file.unlink()
                self.fixes_applied.append(f"Removed example file: {example_file.relative_to(self.skill_path)}")


def validate_all_skills(auto_fix: bool = False) -> Dict[str, Any]:
    """Validate all skills in the ecosystem."""
    if not SKILLS_DIR.exists():
        return {"error": f"Skills directory not found: {SKILLS_DIR}"}
    
    # Find all skills
    skills = [
        d for d in SKILLS_DIR.iterdir()
        if d.is_dir() and (d / "SKILL.md").exists()
    ]
    
    results = {
        "total_skills": len(skills),
        "valid_skills": 0,
        "invalid_skills": 0,
        "skills": {},
    }
    
    for skill_path in sorted(skills):
        validator = SkillValidator(skill_path)
        result = validator.validate(auto_fix=auto_fix)
        results["skills"][skill_path.name] = result
        
        if result["valid"]:
            results["valid_skills"] += 1
        else:
            results["invalid_skills"] += 1
    
    return results


def format_validation_result(result: Dict[str, Any]) -> str:
    """Format validation result for human reading."""
    output = []
    
    if "skills" in result:
        # Multiple skills
        output.append("=" * 60)
        output.append("SKILL VALIDATION REPORT")
        output.append("=" * 60)
        output.append(f"Total Skills: {result['total_skills']}")
        output.append(f"✅ Valid: {result['valid_skills']}")
        output.append(f"❌ Invalid: {result['invalid_skills']}")
        output.append("")
        
        for skill_name, skill_result in sorted(result["skills"].items()):
            output.extend(format_single_validation(skill_name, skill_result))
            output.append("")
    else:
        # Single skill
        output.extend(format_single_validation(result.get("skill", "Unknown"), result))
    
    return "\n".join(output)


def format_single_validation(skill_name: str, result: Dict[str, Any]) -> List[str]:
    """Format a single skill validation result."""
    output = []
    
    icon = "✅" if result["valid"] else "❌"
    output.append(f"{icon} {skill_name}")
    
    if result.get("errors"):
        output.append("   ERRORS:")
        for error in result["errors"]:
            output.append(f"     ❌ {error}")
    
    if result.get("warnings"):
        output.append("   WARNINGS:")
        for warning in result["warnings"]:
            output.append(f"     ⚠️  {warning}")
    
    if result.get("fixes_applied"):
        output.append("   FIXES APPLIED:")
        for fix in result["fixes_applied"]:
            output.append(f"     ✅ {fix}")
    
    if result["valid"] and not result.get("warnings"):
        output.append("   ✨ All validations passed!")
    
    return output


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    auto_fix = "--fix" in sys.argv
    
    if "--all" in sys.argv:
        result = validate_all_skills(auto_fix=auto_fix)
    else:
        skill_name = sys.argv[1]
        if skill_name.startswith("--"):
            print(f"Error: Invalid skill name: {skill_name}")
            print(__doc__)
            sys.exit(1)
        
        skill_path = SKILLS_DIR / skill_name
        validator = SkillValidator(skill_path)
        result = validator.validate(auto_fix=auto_fix)
    
    print(format_validation_result(result))
    
    # Exit with error if validation failed
    if "skills" in result:
        sys.exit(0 if result["invalid_skills"] == 0 else 1)
    else:
        sys.exit(0 if result["valid"] else 1)


if __name__ == "__main__":
    main()
