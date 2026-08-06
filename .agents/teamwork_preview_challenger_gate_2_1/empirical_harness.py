import sys
from pathlib import Path

# Add lib/py to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "lib" / "py"))

from datetime import date

from transcripts.domain.skills import (
    SkillStatus,
    diagnose_skill,
    diagnose_skill_status,
)
from transcripts.domain.time import (
    get_brisbane_today,
    parse_due_date,
    parse_iso_utc,
)

from tests.test_dangling_plugin_refs import (
    SLASH_EMAIL_REGEX,
)


def run_case_1_tests():
    print(
        "=== Testing Case 1: Microsecond ISO timestamp parsing with explicit timezone offset (+10:00) ==="
    )

    test_cases = [
        ("2026-08-06T14:30:00.123456789+10:00", date(2026, 8, 6)),
        ("2026-08-06T14:30:00.123456+10:00", date(2026, 8, 6)),
        ("2026-08-06T14:30:00.123+10:00", date(2026, 8, 6)),
        ("2026-08-06T23:59:59.999999+10:00", date(2026, 8, 6)),
        ("2026-08-06T00:00:00.000000+10:00", date(2026, 8, 6)),
        ("2026-08-06T14:00:00.123456+00:00", date(2026, 8, 7)),
        ("2026-08-06T13:59:59.999999+00:00", date(2026, 8, 6)),
        ("2026-08-06T20:00:00.123456789-05:00", date(2026, 8, 7)),
        ("2026-08-06T00:00:00.123456789Z", date(2026, 8, 6)),
    ]

    failures = 0
    for ts_str, expected_date in test_cases:
        parsed_utc = parse_iso_utc(ts_str)
        brisbane_date_gbt = get_brisbane_today(ts_str)
        brisbane_date_pdd = parse_due_date(ts_str)

        print(f"Input: {ts_str}")
        print(f"  parse_iso_utc: {parsed_utc}")
        print(f"  get_brisbane_today: {brisbane_date_gbt} (Expected: {expected_date})")
        print(f"  parse_due_date:     {brisbane_date_pdd} (Expected: {expected_date})")

        if brisbane_date_gbt != expected_date:
            print(f"  [FAIL] get_brisbane_today got {brisbane_date_gbt}, expected {expected_date}")
            failures += 1
        if brisbane_date_pdd != expected_date:
            print(f"  [FAIL] parse_due_date got {brisbane_date_pdd}, expected {expected_date}")
            failures += 1

    print(f"Case 1 total failures: {failures}\n")
    return failures == 0


def run_case_2_tests():
    print("=== Testing Case 2: Slash command regex matching on sentence boundaries ===")

    positives = [
        "Use /email.",
        "Use /email!",
        "Use /email?",
        "Use /email,",
        "Use /email;",
        "Use /email:",
        "Use /email)",
        "Use (/email)",
        "Use /email to triage your inbox",
        "Run /email",
        "Available commands: /email, /daily",
        "Execute `/email` now",
    ]

    negatives = [
        "See /email.md for docs",
        "See /email.py",
        "See /email.json",
        "See [[wf-email-triage]] for workflow",
        "Process file email-triage.md",
        "import email_validator",
        "https://api.example.com/email/send",
        "https://files.pythonhosted.org/.../email_validator-2.3.0.tar.gz",
        "plugins/pkb/workflows/process/email-triage.md",
    ]

    failures = 0
    print("-- Testing Positive Matches (should match) --")
    for text in positives:
        match = SLASH_EMAIL_REGEX.search(text)
        if match is None:
            print(f"  [FAIL] Expected match for: '{text}'")
            failures += 1
        else:
            print(f"  [PASS] Matched '{text}' -> '{match.group(0)}'")

    print("\n-- Testing Negative Matches (should NOT match) --")
    for text in negatives:
        match = SLASH_EMAIL_REGEX.search(text)
        if match is not None:
            print(f"  [FAIL] Expected NO match for: '{text}', but matched '{match.group(0)}'")
            failures += 1
        else:
            print(f"  [PASS] No match for '{text}'")

    print(f"Case 2 total failures: {failures}\n")
    return failures == 0


def run_case_3_tests(tmp_path: Path):
    print("=== Testing Case 3: SkillStatus.INSTALL_FAILURE classification in skills.py ===")

    plugins_root = PROJECT_ROOT / "plugins"

    # 1. Deliberately removed
    status_daily = diagnose_skill_status("/daily", plugins_dir=plugins_root)
    print(f"Status for /daily: {status_daily}")

    # 2. Installed
    status_analyst = diagnose_skill_status("analyst", plugins_dir=plugins_root)
    print(f"Status for analyst: {status_analyst}")

    # 3. Missing
    status_missing = diagnose_skill_status("non_existent_skill_xyz", plugins_dir=plugins_root)
    print(f"Status for non_existent_skill_xyz: {status_missing}")

    # 4. Install failure (directory without SKILL.md)
    test_plugins_dir = tmp_path / "test_plugins"
    broken_skill_dir = test_plugins_dir / "category" / "broken_skill"
    broken_skill_dir.mkdir(parents=True, exist_ok=True)

    status_broken = diagnose_skill_status("broken_skill", plugins_dir=test_plugins_dir)
    diag_broken = diagnose_skill("broken_skill", plugins_dir=test_plugins_dir)
    print(f"Status for broken_skill (dir without SKILL.md): {status_broken}")
    print(f"Diagnostics: {diag_broken}")

    failures = 0
    if status_daily != SkillStatus.DELIBERATELY_REMOVED:
        print(f"  [FAIL] /daily status expected DELIBERATELY_REMOVED, got {status_daily}")
        failures += 1
    if status_analyst != SkillStatus.INSTALLED:
        print(f"  [FAIL] analyst status expected INSTALLED, got {status_analyst}")
        failures += 1
    if status_missing != SkillStatus.MISSING:
        print(f"  [FAIL] non_existent_skill_xyz status expected MISSING, got {status_missing}")
        failures += 1
    if status_broken != SkillStatus.INSTALL_FAILURE:
        print(f"  [FAIL] broken_skill status expected INSTALL_FAILURE, got {status_broken}")
        failures += 1
    if not diag_broken["is_install_failure"]:
        print(
            f"  [FAIL] is_install_failure boolean flag expected True, got {diag_broken['is_install_failure']}"
        )
        failures += 1

    print(f"Case 3 total failures: {failures}\n")
    return failures == 0


if __name__ == "__main__":
    import tempfile

    c1_ok = run_case_1_tests()
    c2_ok = run_case_2_tests()
    with tempfile.TemporaryDirectory() as tmpdir:
        c3_ok = run_case_3_tests(Path(tmpdir))

    if c1_ok and c2_ok and c3_ok:
        print("ALL EMPIRICAL TESTS PASSED SUCCESSFULLY!")
        sys.exit(0)
    else:
        print("EMPIRICAL TEST HARNESS DETECTED FAILURES!")
        sys.exit(1)
