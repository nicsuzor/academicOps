#!/usr/bin/env python3
"""Manual test runner for integration tests (no pytest required)."""

from __future__ import annotations

import sys
import traceback
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import test module
from tests.test_task_server_integration import (
    TestArchiveTasks,
    TestCreateTask,
    TestEndToEndWorkflow,
    TestErrorHandling,
    TestModifyTask,
    TestPerformance,
    TestUnarchiveTasks,
    TestViewTasks,
    test_data_dir,
)


def run_test_class(test_class, test_data_dir_fixture):
    """Run all test methods in a class."""
    class_name = test_class.__name__
    print(f"\n{'=' * 70}")
    print(f"Running {class_name}")
    print(f"{'=' * 70}")

    instance = test_class()
    test_methods = [m for m in dir(instance) if m.startswith("test_")]

    passed = 0
    failed = 0
    errors = []

    for method_name in test_methods:
        method = getattr(instance, method_name)
        test_name = f"{class_name}::{method_name}"

        try:
            # Create fresh test data dir for each test
            import tempfile

            tmp_path = Path(tempfile.mkdtemp())
            data_dir = test_data_dir_fixture(tmp_path)

            # Run test
            method(data_dir)

            print(f"✓ {test_name}")
            passed += 1

            # Cleanup
            import shutil

            shutil.rmtree(tmp_path)

        except AssertionError as e:
            print(f"✗ {test_name}")
            print(f"  AssertionError: {e}")
            failed += 1
            errors.append((test_name, str(e)))

        except Exception as e:
            print(f"✗ {test_name}")
            print(f"  Error: {e}")
            traceback.print_exc()
            failed += 1
            errors.append((test_name, str(e)))

    return passed, failed, errors


def main():
    """Run all integration tests."""
    print("FastMCP Task Server - Integration Test Suite")
    print("=" * 70)

    test_classes = [
        TestViewTasks,
        TestArchiveTasks,
        TestUnarchiveTasks,
        TestCreateTask,
        TestModifyTask,
        TestEndToEndWorkflow,
        TestPerformance,
        TestErrorHandling,
    ]

    total_passed = 0
    total_failed = 0
    all_errors = []

    for test_class in test_classes:
        passed, failed, errors = run_test_class(test_class, test_data_dir)
        total_passed += passed
        total_failed += failed
        all_errors.extend(errors)

    print(f"\n{'=' * 70}")
    print("Test Summary")
    print(f"{'=' * 70}")
    print(f"Total tests: {total_passed + total_failed}")
    print(f"Passed: {total_passed}")
    print(f"Failed: {total_failed}")

    if all_errors:
        print(f"\n{'=' * 70}")
        print("Failed Tests Details")
        print(f"{'=' * 70}")
        for test_name, error in all_errors:
            print(f"\n{test_name}:")
            print(f"  {error}")

    # Exit with appropriate code
    sys.exit(0 if total_failed == 0 else 1)


if __name__ == "__main__":
    main()
