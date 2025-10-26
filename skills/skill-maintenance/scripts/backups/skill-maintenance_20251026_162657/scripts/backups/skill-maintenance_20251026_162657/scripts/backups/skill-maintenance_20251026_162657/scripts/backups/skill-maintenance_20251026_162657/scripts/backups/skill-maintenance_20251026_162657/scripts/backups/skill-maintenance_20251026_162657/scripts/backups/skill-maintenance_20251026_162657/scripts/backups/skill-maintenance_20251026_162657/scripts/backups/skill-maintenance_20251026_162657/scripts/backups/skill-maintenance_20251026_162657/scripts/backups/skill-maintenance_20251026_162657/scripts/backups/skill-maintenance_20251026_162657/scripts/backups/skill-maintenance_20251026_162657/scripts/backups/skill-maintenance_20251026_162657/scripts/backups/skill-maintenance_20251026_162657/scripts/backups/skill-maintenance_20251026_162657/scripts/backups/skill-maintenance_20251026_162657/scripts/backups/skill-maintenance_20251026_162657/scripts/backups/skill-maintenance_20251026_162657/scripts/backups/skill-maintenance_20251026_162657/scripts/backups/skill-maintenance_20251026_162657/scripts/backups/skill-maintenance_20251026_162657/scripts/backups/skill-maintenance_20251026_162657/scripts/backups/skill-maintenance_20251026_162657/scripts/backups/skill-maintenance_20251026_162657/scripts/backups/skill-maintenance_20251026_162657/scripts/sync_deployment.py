#!/usr/bin/env python3
"""
Sync Deployment - Ensure deployment directory contains only symlinks to source

Detects and fixes divergence between source skills and deployed skills.

Usage:
    sync_deployment.py              # Check deployment status
    sync_deployment.py --fix        # Fix issues (create/fix symlinks)
    sync_deployment.py --clean      # Remove orphaned deployments

Examples:
    sync_deployment.py
    sync_deployment.py --fix
    sync_deployment.py --fix --clean
"""

import sys
import os
import shutil
from pathlib import Path
from typing import List, Dict, Any, Tuple

# Get paths
ACADEMICOPS_BOT = os.environ.get("ACADEMICOPS_BOT", Path.home() / "src" / "bot")
SOURCE_DIR = Path(ACADEMICOPS_BOT) / "skills"
DEPLOY_DIR = Path.home() / ".claude" / "skills"


def check_deployment(skill_name: str) -> Dict[str, Any]:
    """Check deployment status of a single skill."""
    source_path = SOURCE_DIR / skill_name
    deploy_path = DEPLOY_DIR / skill_name
    
    status = {
        "name": skill_name,
        "source": str(source_path),
        "deployment": str(deploy_path),
        "status": "unknown",
        "issues": [],
        "actions_needed": [],
    }
    
    # Check if source exists
    if not source_path.exists():
        status["status"] = "source_missing"
        status["issues"].append("Source skill not found")
        if deploy_path.exists():
            status["actions_needed"].append("Remove orphaned deployment")
        return status
    
    # Check if deployment exists
    if not deploy_path.exists():
        status["status"] = "not_deployed"
        status["issues"].append("Not deployed")
        status["actions_needed"].append("Create symlink")
        return status
    
    # Check if deployment is a symlink
    if deploy_path.is_symlink():
        # Check if symlink points to correct location
        target = deploy_path.resolve()
        if target == source_path.resolve():
            status["status"] = "correct"
        else:
            status["status"] = "wrong_symlink"
            status["issues"].append(f"Symlink points to wrong location: {target}")
            status["actions_needed"].append("Fix symlink")
    else:
        # Deployment exists but is not a symlink
        status["status"] = "not_symlink"
        status["issues"].append("Deployment is not a symlink (local copy)")
        status["actions_needed"].append("Replace with symlink")
    
    return status


def fix_deployment(skill_name: str) -> Dict[str, Any]:
    """Fix deployment issues for a single skill."""
    source_path = SOURCE_DIR / skill_name
    deploy_path = DEPLOY_DIR / skill_name
    
    result = {
        "name": skill_name,
        "fixed": False,
        "actions": [],
        "errors": [],
    }
    
    try:
        # Check current status
        status = check_deployment(skill_name)
        
        if status["status"] == "correct":
            result["fixed"] = True
            result["actions"].append("Already correct")
            return result
        
        if status["status"] == "source_missing":
            result["errors"].append("Source skill not found - cannot fix")
            return result
        
        # Create deployment directory if needed
        DEPLOY_DIR.mkdir(parents=True, exist_ok=True)
        
        # Remove existing deployment if needed
        if deploy_path.exists():
            if deploy_path.is_symlink():
                deploy_path.unlink()
                result["actions"].append("Removed incorrect symlink")
            else:
                # It's a directory - back it up first
                backup_path = deploy_path.with_suffix(".backup")
                if backup_path.exists():
                    shutil.rmtree(backup_path)
                shutil.move(str(deploy_path), str(backup_path))
                result["actions"].append(f"Backed up local copy to {backup_path.name}")
        
        # Create correct symlink
        deploy_path.symlink_to(source_path)
        result["actions"].append(f"Created symlink to {source_path}")
        result["fixed"] = True
        
    except Exception as e:
        result["errors"].append(str(e))
    
    return result


def clean_orphaned_deployments() -> List[Dict[str, Any]]:
    """Remove deployments that have no corresponding source."""
    if not DEPLOY_DIR.exists():
        return []
    
    cleaned = []
    
    for item in DEPLOY_DIR.iterdir():
        if item.is_dir() or item.is_symlink():
            skill_name = item.name
            source_path = SOURCE_DIR / skill_name
            
            if not source_path.exists():
                # Orphaned deployment
                try:
                    if item.is_symlink():
                        item.unlink()
                        action = "Removed orphaned symlink"
                    else:
                        backup_path = item.with_suffix(".orphaned")
                        if backup_path.exists():
                            shutil.rmtree(backup_path)
                        shutil.move(str(item), str(backup_path))
                        action = f"Moved to {backup_path.name}"
                    
                    cleaned.append({
                        "name": skill_name,
                        "action": action,
                        "success": True,
                    })
                except Exception as e:
                    cleaned.append({
                        "name": skill_name,
                        "error": str(e),
                        "success": False,
                    })
    
    return cleaned


def sync_all_deployments(fix: bool = False, clean: bool = False) -> Dict[str, Any]:
    """Sync all skill deployments."""
    results = {
        "source_dir": str(SOURCE_DIR),
        "deploy_dir": str(DEPLOY_DIR),
        "skills_checked": 0,
        "correct": 0,
        "issues": 0,
        "fixed": 0,
        "orphaned": 0,
        "details": {},
    }
    
    # Check all source skills
    if SOURCE_DIR.exists():
        for skill_dir in SOURCE_DIR.iterdir():
            if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
                skill_name = skill_dir.name
                results["skills_checked"] += 1
                
                if fix:
                    fix_result = fix_deployment(skill_name)
                    results["details"][skill_name] = fix_result
                    if fix_result["fixed"]:
                        if fix_result["actions"] != ["Already correct"]:
                            results["fixed"] += 1
                        else:
                            results["correct"] += 1
                    else:
                        results["issues"] += 1
                else:
                    status = check_deployment(skill_name)
                    results["details"][skill_name] = status
                    if status["status"] == "correct":
                        results["correct"] += 1
                    else:
                        results["issues"] += 1
    
    # Clean orphaned deployments if requested
    if clean:
        orphaned = clean_orphaned_deployments()
        results["orphaned_cleaned"] = orphaned
        results["orphaned"] = len(orphaned)
    
    return results


def format_sync_result(result: Dict[str, Any]) -> str:
    """Format sync result for human reading."""
    output = []
    
    output.append("=" * 60)
    output.append("DEPLOYMENT SYNC REPORT")
    output.append("=" * 60)
    output.append(f"Source: {result['source_dir']}")
    output.append(f"Deployment: {result['deploy_dir']}")
    output.append(f"Skills Checked: {result['skills_checked']}")
    output.append(f"✅ Correct: {result['correct']}")
    output.append(f"⚠️  Issues: {result['issues']}")
    
    if "fixed" in result:
        output.append(f"🔧 Fixed: {result['fixed']}")
    
    if "orphaned" in result:
        output.append(f"🗑️  Orphaned Cleaned: {result['orphaned']}")
    
    output.append("")
    
    # Detailed results
    if result.get("details"):
        output.append("DETAILS:")
        output.append("-" * 40)
        
        for skill_name, details in sorted(result["details"].items()):
            if "status" in details:
                # Check mode
                icon = "✅" if details["status"] == "correct" else "⚠️"
                output.append(f"{icon} {skill_name}")
                if details["status"] != "correct":
                    output.append(f"   Status: {details['status']}")
                    if details.get("issues"):
                        for issue in details["issues"]:
                            output.append(f"   Issue: {issue}")
                    if details.get("actions_needed"):
                        for action in details["actions_needed"]:
                            output.append(f"   Needed: {action}")
            else:
                # Fix mode
                icon = "✅" if details.get("fixed") else "❌"
                output.append(f"{icon} {skill_name}")
                if details.get("actions"):
                    for action in details["actions"]:
                        if action != "Already correct":
                            output.append(f"   ✅ {action}")
                if details.get("errors"):
                    for error in details["errors"]:
                        output.append(f"   ❌ {error}")
    
    # Orphaned deployments
    if result.get("orphaned_cleaned"):
        output.append("")
        output.append("ORPHANED DEPLOYMENTS CLEANED:")
        output.append("-" * 40)
        for item in result["orphaned_cleaned"]:
            if item["success"]:
                output.append(f"✅ {item['name']}: {item['action']}")
            else:
                output.append(f"❌ {item['name']}: {item.get('error', 'Unknown error')}")
    
    return "\n".join(output)


def main():
    """Main entry point."""
    fix = "--fix" in sys.argv
    clean = "--clean" in sys.argv
    
    if fix:
        print("🔧 Running in FIX mode - will create/fix symlinks")
    if clean:
        print("🗑️  Running with CLEAN - will remove orphaned deployments")
    
    result = sync_all_deployments(fix=fix, clean=clean)
    print(format_sync_result(result))
    
    # Exit with error if issues remain
    if fix:
        # In fix mode, error if we couldn't fix everything
        sys.exit(0 if result["issues"] == 0 else 1)
    else:
        # In check mode, error if issues found
        sys.exit(0 if result["issues"] == 0 else 1)


if __name__ == "__main__":
    main()
