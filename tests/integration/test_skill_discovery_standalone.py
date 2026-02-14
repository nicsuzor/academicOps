#!/usr/bin/env python3
"""Standalone test for skill script discovery.

Run directly to validate skill script architecture:
    python3 tests/integration/test_skill_discovery_standalone.py
"""

import os
import subprocess
import sys
from pathlib import Path


def test_symlink_structure():
    """Verify ~/.claude/skills/ symlink structure."""
    import pytest

    print("Testing symlink structure...")

    skills_path = Path.home() / ".claude" / "skills"
    if not skills_path.exists():
        print("⚠️  SKIP: ~/.claude/skills/ does not exist")
        pytest.skip("~/.claude/skills/ does not exist - local setup only")

    task_scripts = skills_path / "tasks" / "scripts"
    if not task_scripts.exists():
        print(f"⚠️  SKIP: {task_scripts} does not exist")
        pytest.skip(f"{task_scripts} does not exist - local setup only")

    required_scripts = ["task_view.py", "task_add.py", "task_archive.py"]
    for script in required_scripts:
        script_path = task_scripts / script
        if not script_path.exists():
            print(f"⚠️  SKIP: {script} not found at {script_path}")
            pytest.skip(f"{script} not found - local setup only")
        print(f"  ✓ Found: {script}")

    print("✅ PASS: All required scripts exist via symlink")


def test_aops_env_var():
    """Verify AOPS environment variable is set."""
    import pytest

    print("\nTesting AOPS environment variable...")

    aops = os.environ.get("AOPS")
    if not aops:
        print("⚠️  SKIP: AOPS environment variable not set")
        pytest.skip("AOPS environment variable not set - local setup only")

    aops_path = Path(aops)
    if not aops_path.exists():
        print(f"❌ FAIL: AOPS path does not exist: {aops_path}")
        pytest.fail(f"AOPS path does not exist: {aops_path}")

    print(f"  ✓ AOPS={aops}")
    print("✅ PASS: AOPS environment variable valid")


def test_script_execution_from_writing():
    """Test that scripts can execute from writing repo."""
    import pytest

    print("\nTesting script execution from writing repo...")

    # Get writing root
    aca_data = os.environ.get("ACA_DATA")
    if not aca_data:
        print("⚠️  SKIP: ACA_DATA not set, cannot test writing repo")
        pytest.skip("ACA_DATA not set")

    data_dir = Path(aca_data)
    if not data_dir.exists():
        print(f"⚠️  SKIP: Writing root does not exist: {data_dir}")
        pytest.skip(f"Writing root does not exist: {data_dir}")

    # Build command
    script_path = Path.home() / ".claude" / "skills" / "tasks" / "scripts" / "task_view.py"
    if not script_path.exists():
        print(f"⚠️  SKIP: Script not found: {script_path}")
        pytest.skip(f"Script not found: {script_path} - local setup only")

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
            pytest.fail(f"Script execution failed: {result.stderr}")

        if "Using data_dir:" not in result.stdout:
            print("❌ FAIL: Unexpected output")
            print(f"  stdout: {result.stdout}")
            pytest.fail(f"Unexpected output: {result.stdout}")

        print("  ✓ Script executed successfully")
        print("  ✓ Found data directory in output")
        print("✅ PASS: Script runs from writing repo")

    except subprocess.TimeoutExpired:
        print("❌ FAIL: Script execution timed out")
        pytest.fail("Script execution timed out")
    except AssertionError:
        raise
    except Exception as e:
        print(f"❌ FAIL: Exception during execution: {e}")
        pytest.fail(f"Exception during execution: {e}")


def test_symlink_points_to_aops():
    """Verify symlink resolves to AOPS directory."""
    import pytest

    print("\nTesting symlink resolution...")

    aops = os.environ.get("AOPS")
    if not aops:
        print("⚠️  SKIP: AOPS not set")
        pytest.skip("AOPS not set - local setup only")

    aops_scripts = Path(aops) / "skills" / "tasks" / "scripts"
    symlink_scripts = Path.home() / ".claude" / "skills" / "tasks" / "scripts"

    if not aops_scripts.exists():
        print(f"⚠️  SKIP: AOPS scripts don't exist: {aops_scripts}")
        pytest.skip(f"AOPS scripts don't exist: {aops_scripts} - local setup only")

    if not symlink_scripts.exists():
        print(f"⚠️  SKIP: Symlink scripts don't exist: {symlink_scripts}")
        pytest.skip("Symlink scripts don't exist - local setup only")

    # Resolve both paths
    aops_resolved = aops_scripts.resolve()
    symlink_resolved = symlink_scripts.resolve()

    if aops_resolved != symlink_resolved:
        print("❌ FAIL: Paths don't match:")
        print(f"  AOPS:    {aops_resolved}")
        print(f"  Symlink: {symlink_resolved}")
        pytest.fail(f"Paths don't match: AOPS={aops_resolved}, Symlink={symlink_resolved}")

    print(f"  ✓ Both resolve to: {aops_resolved}")
    print("✅ PASS: Symlink correctly points to AOPS")


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
            test()
            results.append(True)
        except AssertionError as e:
            print(f"\n❌ FAIL in {test.__name__}: {e}")
            results.append(False)
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
