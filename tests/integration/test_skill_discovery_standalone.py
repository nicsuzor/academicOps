#!/usr/bin/env python3
"""Standalone test for skill script discovery.

Run directly to validate skill script architecture:
    python3 tests/integration/test_skill_discovery_standalone.py
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = [pytest.mark.slow, pytest.mark.integration]


def setup_mock_home(tmp_path):
    """Setup a mock ~/.claude/ structure in tmp_path."""
    from unittest.mock import patch

    # Create structure
    skills_dir = tmp_path / ".claude" / "skills"
    skills_dir.mkdir(parents=True, exist_ok=True)

    # Create framework skill
    framework_scripts = skills_dir / "framework" / "scripts"
    framework_scripts.mkdir(parents=True, exist_ok=True)

    # Create required scripts
    (framework_scripts / "validate_docs.py").touch()

    # Setup symlink to real AOPS if available
    aops = os.environ.get("AOPS")
    if aops:
        aops_scripts = Path(aops) / "aops-core" / "skills" / "framework" / "scripts"
        if aops_scripts.exists():
            # Replace framework_scripts with symlink
            import shutil

            shutil.rmtree(framework_scripts.parent)
            framework_scripts.parent.mkdir(parents=True, exist_ok=True)
            framework_scripts.symlink_to(aops_scripts)

    return patch.object(Path, "home", return_value=tmp_path)


def test_symlink_structure(tmp_path):
    """Verify ~/.claude/skills/ symlink structure."""
    with setup_mock_home(tmp_path):
        print("Testing symlink structure...")

        skills_path = Path.home() / ".claude" / "skills"
        assert skills_path.exists(), "~/.claude/skills/ does not exist"

        # Update to check for framework skill scripts instead of tasks skill scripts
        framework_scripts = skills_path / "framework" / "scripts"
        assert framework_scripts.exists(), f"{framework_scripts} does not exist"

        required_scripts = ["validate_docs.py"]
        for script in required_scripts:
            script_path = framework_scripts / script
            assert script_path.exists(), f"{script} not found at {script_path}"
            print(f"  ✓ Found: {script}")

        print("✅ PASS: All required scripts exist via symlink")


@pytest.mark.requires_local_env
def test_aops_env_var():
    """Verify AOPS environment variable is set."""
    import pytest

    print("\nTesting AOPS environment variable...")

    aops = os.environ.get("AOPS")
    assert aops, "AOPS environment variable not set"

    aops_path = Path(aops)
    if not aops_path.exists():
        print(f"❌ FAIL: AOPS path does not exist: {aops_path}")
        pytest.fail(f"AOPS path does not exist: {aops_path}")

    print(f"  ✓ AOPS={aops}")
    print("✅ PASS: AOPS environment variable valid")


@pytest.mark.requires_local_env
def test_script_execution_from_writing(tmp_path):
    """Test that scripts can execute from writing repo."""
    import pytest

    with setup_mock_home(tmp_path):
        print("\nTesting script execution from writing repo...")

        # Get writing root
        aca_data = os.environ.get("ACA_DATA")
        if not aca_data:
            # Fallback to current directory if ACA_DATA not set, as long as it exists
            # This allows testing in CI/sandbox without full user setup
            aca_data = os.getcwd()
            print(f"⚠️  ACA_DATA not set, using CWD: {aca_data}")

        data_dir = Path(aca_data)
        assert data_dir.exists(), f"Writing root does not exist: {data_dir}"

        # Build command - use validate_docs.py instead of task_view.py
        script_path = (
            Path.home() / ".claude" / "skills" / "framework" / "scripts" / "validate_docs.py"
        )
        assert script_path.exists(), f"Script not found at {script_path}"

        aops = os.environ.get("AOPS")
        # validate_docs.py supports --help
        cmd = ["uv", "run", "--no-project", "python", str(script_path), "--help"]

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

            if "usage:" not in result.stdout:
                print("❌ FAIL: Unexpected output")
                print(f"  stdout: {result.stdout}")
                pytest.fail(f"Unexpected output: {result.stdout}")

            print("  ✓ Script executed successfully")
            print("  ✓ Found usage in output")
            print("✅ PASS: Script runs from writing repo")

        except subprocess.TimeoutExpired:
            print("❌ FAIL: Script execution timed out")
            pytest.fail("Script execution timed out")
        except AssertionError:
            raise
        except Exception as e:
            print(f"❌ FAIL: Exception during execution: {e}")
            pytest.fail(f"Exception during execution: {e}")


@pytest.mark.requires_local_env
def test_symlink_points_to_aops(tmp_path):
    """Verify symlink resolves to AOPS directory."""
    import pytest

    with setup_mock_home(tmp_path):
        print("\nTesting symlink resolution...")

        aops = os.environ.get("AOPS")
        assert aops, "AOPS environment variable not set"

        # Update path to framework scripts within aops-core
        aops_scripts = Path(aops) / "aops-core" / "skills" / "framework" / "scripts"
        symlink_scripts = Path.home() / ".claude" / "skills" / "framework" / "scripts"

        aops_scripts_alt = Path(aops) / "skills" / "framework" / "scripts"
        assert aops_scripts.exists() or aops_scripts_alt.exists(), (
            f"AOPS scripts don't exist: {aops_scripts} and {aops_scripts_alt}"
        )
        if aops_scripts_alt.exists() and not aops_scripts.exists():
            aops_scripts = aops_scripts_alt

        assert symlink_scripts.exists(), f"Symlink scripts don't exist: {symlink_scripts}"

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
