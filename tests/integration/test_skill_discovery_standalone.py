#!/usr/bin/env python3
"""Standalone test for skill script discovery - no pytest required.

Run directly to validate skill script architecture:
    python3 tests/integration/test_skill_discovery_standalone.py
"""

import os
import subprocess
import sys
from pathlib import Path


def test_symlink_structure():
    """Verify ~/.claude/skills/ symlink structure."""
    print("Testing symlink structure...")

    skills_path = Path.home() / ".claude" / "skills"
    if not skills_path.exists():
        print("❌ FAIL: ~/.claude/skills/ does not exist")
        return False

    task_scripts = skills_path / "tasks" / "scripts"
    if not task_scripts.exists():
        print(f"❌ FAIL: {task_scripts} does not exist")
        return False

    required_scripts = ["task_view.py", "task_add.py", "task_archive.py"]
    for script in required_scripts:
        script_path = task_scripts / script
        if not script_path.exists():
            print(f"❌ FAIL: {script} not found at {script_path}")
            return False
        print(f"  ✓ Found: {script}")

    print("✅ PASS: All required scripts exist via symlink")
    return True


def test_aops_env_var():
    """Verify AOPS environment variable is set."""
    print("\nTesting AOPS environment variable...")

    aops = os.environ.get("AOPS")
    if not aops:
        print("❌ FAIL: AOPS environment variable not set")
        return False

    aops_path = Path(aops)
    if not aops_path.exists():
        print(f"❌ FAIL: AOPS path does not exist: {aops_path}")
        return False

    print(f"  ✓ AOPS={aops}")
    print("✅ PASS: AOPS environment variable valid")
    return True


def test_script_execution_from_writing():
    """Test that scripts can execute from writing repo."""
    print("\nTesting script execution from writing repo...")

    # Get writing root
    aca_data = os.environ.get("ACA_DATA")
    if not aca_data:
        print("⚠️  SKIP: ACA_DATA not set, cannot test writing repo")
        return True

    data_dir = Path(aca_data)
    if not data_dir.exists():
        print(f"⚠️  SKIP: Writing root does not exist: {data_dir}")
        return True

    # Build command
    script_path = (
        Path.home() / ".claude" / "skills" / "tasks" / "scripts" / "task_view.py"
    )
    if not script_path.exists():
        print(f"❌ FAIL: Script not found: {script_path}")
        return False

    aops = os.environ.get("AOPS")
    cmd = ["uv", "run", "--no-project", "python", str(script_path), "--compact"]

    # Set environment
    env = os.environ.copy()
    env["PYTHONPATH"] = aops

    print(f"  Running from: {data_dir}")
    print(f"  Command: {' '.join(cmd)}")

    # Execute
    try:
        result = subprocess.run(
            cmd,
            cwd=data_dir,
            capture_output=True,
            text=True,
            timeout=30,
            env=env,
            check=False,
        )

        if result.returncode != 0:
            print("❌ FAIL: Script execution failed")
            print(f"  stdout: {result.stdout}")
            print(f"  stderr: {result.stderr}")
            return False

        if "Using data_dir:" not in result.stdout:
            print("❌ FAIL: Unexpected output")
            print(f"  stdout: {result.stdout}")
            return False

        print("  ✓ Script executed successfully")
        print("  ✓ Found data directory in output")
        print("✅ PASS: Script runs from writing repo")
        return True

    except subprocess.TimeoutExpired:
        print("❌ FAIL: Script execution timed out")
        return False
    except Exception as e:
        print(f"❌ FAIL: Exception during execution: {e}")
        return False


def test_symlink_points_to_aops():
    """Verify symlink resolves to AOPS directory."""
    print("\nTesting symlink resolution...")

    aops = os.environ.get("AOPS")
    if not aops:
        print("❌ FAIL: AOPS not set")
        return False

    aops_scripts = Path(aops) / "skills" / "tasks" / "scripts"
    symlink_scripts = Path.home() / ".claude" / "skills" / "tasks" / "scripts"

    if not aops_scripts.exists():
        print(f"❌ FAIL: AOPS scripts don't exist: {aops_scripts}")
        return False

    if not symlink_scripts.exists():
        print(f"❌ FAIL: Symlink scripts don't exist: {symlink_scripts}")
        return False

    # Resolve both paths
    aops_resolved = aops_scripts.resolve()
    symlink_resolved = symlink_scripts.resolve()

    if aops_resolved != symlink_resolved:
        print("❌ FAIL: Paths don't match:")
        print(f"  AOPS:    {aops_resolved}")
        print(f"  Symlink: {symlink_resolved}")
        return False

    print(f"  ✓ Both resolve to: {aops_resolved}")
    print("✅ PASS: Symlink correctly points to AOPS")
    return True


def main():
    """Run all tests."""
    print("=" * 70)
    print("SKILL SCRIPT DISCOVERY TEST SUITE")
    print("=" * 70)

    tests = [
        test_aops_env_var,
        test_symlink_structure,
        test_symlink_points_to_aops,
        test_script_execution_from_writing,
    ]

    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"\n❌ EXCEPTION in {test.__name__}: {e}")
            results.append(False)

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    passed = sum(results)
    total = len(results)

    print(f"Passed: {passed}/{total}")

    if passed == total:
        print("\n🎉 ALL TESTS PASSED")
        return 0
    else:
        print(f"\n❌ {total - passed} TESTS FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())
