"""Adversarial Test Suite for Final Milestone Verification.

Executes targeted stress tests on:
1. Timestamp microsecond formatting and parsing
2. 10-hour Brisbane boundary transitions (14:00-24:00 UTC)
3. Slash command regex boundary checks
4. Skill status queries
"""

import re
import sys
from datetime import date
from pathlib import Path

# Add /workspace/lib/py to path
sys.path.insert(0, "/workspace/lib/py")

from transcripts.domain.skills import (
    SkillStatus,
    diagnose_skill_status,
)
from transcripts.domain.time import (
    bucket_due_date,
    format_iso_utc,
    get_brisbane_today,
    get_event_timestamps,
    parse_due_date,
    parse_iso_utc,
)
from transcripts.model import NormalizedEvent

findings = []


def record_finding(category: str, description: str, severity: str, details: str):
    findings.append(
        {
            "category": category,
            "description": description,
            "severity": severity,
            "details": details,
        }
    )
    print(f"[{severity.upper()}] {category}: {description}")
    print(f"   Details: {details}\n")


print("=== RUNNING ADVERSARIAL TEST SUITE ===\n")

# -------------------------------------------------------------
# AREA 1: Timestamp Microsecond Formatting & Parsing
# -------------------------------------------------------------
print("--- Area 1: Timestamp Microsecond Formatting & Parsing ---")

# Test 1.1: Format with microseconds output structure
ts_now = format_iso_utc()
if not re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}\+00:00$", ts_now):
    record_finding(
        "Timestamps",
        "format_iso_utc default format mismatch",
        "HIGH",
        f"Output {ts_now} does not match exact format YYYY-MM-DDTHH:MM:SS.ffffff+00:00",
    )

# Test 1.2: Parsing various microsecond precisions
micro_cases = [
    ("2026-08-06T14:30:00.1Z", 100000),
    ("2026-08-06T14:30:00.12Z", 120000),
    ("2026-08-06T14:30:00.123Z", 123000),
    ("2026-08-06T14:30:00.123456Z", 123456),
    ("2026-08-06T14:30:00.123456789Z", 123456),  # truncated to 6 digits
]
for raw_ts, expected_us in micro_cases:
    parsed = parse_iso_utc(raw_ts)
    if parsed is None:
        record_finding(
            "Timestamps",
            f"parse_iso_utc returned None for {raw_ts}",
            "HIGH",
            f"Failed to parse valid ISO string {raw_ts}",
        )
    elif parsed.microsecond != expected_us:
        record_finding(
            "Timestamps",
            f"parse_iso_utc microsecond mismatch for {raw_ts}",
            "MEDIUM",
            f"Expected {expected_us}, got {parsed.microsecond}",
        )

# Test 1.3: Timestamps with explicit timezone offsets and microseconds
tz_micro_cases = [
    ("2026-08-06T14:30:00.123456+10:00", 4, 30, 0),  # 14:30+10:00 is 04:30 UTC
    ("2026-08-06T14:30:00.123456-05:00", 19, 30, 0),  # 14:30-05:00 is 19:30 UTC
]
for raw_ts, exp_h, exp_m, _exp_s in tz_micro_cases:
    parsed = parse_iso_utc(raw_ts)
    if parsed is None:
        record_finding(
            "Timestamps",
            f"parse_iso_utc returned None for tz+micro string {raw_ts}",
            "HIGH",
            f"Failed to parse {raw_ts}",
        )
    else:
        if parsed.hour != exp_h or parsed.minute != exp_m:
            record_finding(
                "Timestamps",
                f"parse_iso_utc timezone conversion error for {raw_ts}",
                "HIGH",
                f"Expected UTC hour {exp_h}:{exp_m}, got {parsed.hour}:{parsed.minute}",
            )

# Test 1.4: get_event_timestamps handling timestamps with offset / dots
try:
    ev1 = NormalizedEvent(
        event_id="e1",
        timestamp="2026-08-06T14:30:00.123456+02:00",
        source="user",
        type="message",
        content="test",
    )
    ev2 = NormalizedEvent(
        event_id="e2",
        timestamp="2026-08-06T15:30:00.654321+02:00",
        source="user",
        type="message",
        content="test",
    )
    s, m, e = get_event_timestamps([ev1, ev2])
except Exception as ex:
    record_finding(
        "Timestamps", "get_event_timestamps crashed on offset with microseconds", "HIGH", str(ex)
    )

# -------------------------------------------------------------
d_at_boundary = get_brisbane_today("2026-08-06T14:00:00.000000Z")
if d_at_boundary != date(2026, 8, 7):
    record_finding(
        "Brisbane Boundary",
        "get_brisbane_today miscalculated date at 14:00 UTC boundary",
        "CRITICAL",
        f"Expected 2026-08-07, got {d_at_boundary}",
    )

# 2026-08-06 23:59:59 UTC -> 2026-08-07 09:59:59 AEST -> Brisbane date 2026-08-07
d_end_of_utc_day = get_brisbane_today("2026-08-06T23:59:59.999999Z")
if d_end_of_utc_day != date(2026, 8, 7):
    record_finding(
        "Brisbane Boundary",
        "get_brisbane_today miscalculated date at end of UTC day",
        "CRITICAL",
        f"Expected 2026-08-07, got {d_end_of_utc_day}",
    )

# Test 2.2: parse_due_date & get_brisbane_today with timezone offsets and microseconds!
# Test input: "2026-08-06T14:30:00.123456+10:00" -> This is 14:30 Brisbane local time on Aug 6 (which is 04:30 UTC on Aug 6).
# Correct Brisbane date is 2026-08-06.
b_date_with_offset = get_brisbane_today("2026-08-06T14:30:00.123456+10:00")
if b_date_with_offset != date(2026, 8, 6):
    record_finding(
        "Brisbane Boundary",
        "get_brisbane_today failed on timestamp with timezone offset + microseconds",
        "HIGH",
        f"Input '2026-08-06T14:30:00.123456+10:00' expected Brisbane date 2026-08-06, got {b_date_with_offset}",
    )

parsed_due_with_offset = parse_due_date("2026-08-06T14:30:00.123456+10:00")
if parsed_due_with_offset != date(2026, 8, 6):
    record_finding(
        "Brisbane Boundary",
        "parse_due_date failed on timestamp with timezone offset + microseconds",
        "HIGH",
        f"Input '2026-08-06T14:30:00.123456+10:00' expected Brisbane date 2026-08-06, got {parsed_due_with_offset}",
    )

# Test 2.3: Bucketing tasks across 10-hour boundary
# Ref time: 2026-08-06T16:00:00Z (In Brisbane, this is 2026-08-07 02:00 AEST -> Today is Aug 7)
# Task due on 2026-08-07 -> Bucket should be "today"
# Task due on 2026-08-06 -> Bucket should be "overdue"
# Task due on 2026-08-08 -> Bucket should be "tomorrow"
b_today = bucket_due_date("2026-08-07", reference_time="2026-08-06T16:00:00Z")
b_overdue = bucket_due_date("2026-08-06", reference_time="2026-08-06T16:00:00Z")
b_tomorrow = bucket_due_date("2026-08-08", reference_time="2026-08-06T16:00:00Z")

if b_today != "today":
    record_finding(
        "Brisbane Boundary",
        f"bucket_due_date failed for today: got {b_today}",
        "HIGH",
        f"Due 2026-08-07 at ref 2026-08-06T16:00:00Z (Aug 7 AEST) returned {b_today}",
    )
if b_overdue != "overdue":
    record_finding(
        "Brisbane Boundary",
        f"bucket_due_date failed for overdue: got {b_overdue}",
        "HIGH",
        f"Due 2026-08-06 at ref 2026-08-06T16:00:00Z (Aug 7 AEST) returned {b_overdue}",
    )
if b_tomorrow != "tomorrow":
    record_finding(
        "Brisbane Boundary",
        f"bucket_due_date failed for tomorrow: got {b_tomorrow}",
        "HIGH",
        f"Due 2026-08-08 at ref 2026-08-06T16:00:00Z (Aug 7 AEST) returned {b_tomorrow}",
    )


# -------------------------------------------------------------
# AREA 3: Slash Command Regex Boundary Checks
# -------------------------------------------------------------
print("\n--- Area 3: Slash Command Regex Boundary Checks ---")

# Let's inspect test_dangling_plugin_refs.py's regex and scan all files in plugins/ and dist/
dangling_regex = re.compile(r"(?<![a-zA-Z0-9_/-])/email\b")

# Test regex false positives / false negatives on adversarial strings:
test_strings = [
    ("/email", True),  # Bare slash command
    ("/email triage", True),  # Slash command with arg
    ("/email.md", False),  # File extension / path
    ("http://domain/email", False),  # URL path
    ("email/triage", False),  # Relative path
    ("/email-triage", False),  # Hyphenated extension
    ("/email_triage", False),  # Underscored extension
    ("/EMAIL", False),  # Uppercase (or True depending on case insensitivity)
    ("`/email`", True),  # Markdown code block (is dangling slash command reference)
    ("Check /email command", True),  # Text context
    ("pkg/email", False),  # Package path
]

for s, expected in test_strings:
    match = bool(dangling_regex.search(s))
    if match != expected:
        record_finding(
            "Slash Command Regex",
            f"Regex misclassified string: '{s}'",
            "MEDIUM",
            f"Expected match={expected}, got match={match}",
        )


# Scan all source files in plugins/ and dist/ for dangling /email
root = Path("/workspace")
plugins_dir = root / "plugins"
dist_dir = root / "dist"

dangling_in_plugins = []
if plugins_dir.exists():
    for f in plugins_dir.rglob("*"):
        if f.is_file() and f.name != "wf-email-triage.md" and f.name != "INDEX.md":
            try:
                content = f.read_text(errors="ignore")
                matches = dangling_regex.findall(content)
                if matches:
                    dangling_in_plugins.append((str(f), matches))
            except Exception:
                pass

if dangling_in_plugins:
    record_finding(
        "Dangling Plugin Refs",
        "Found dangling /email in plugins/",
        "HIGH",
        f"Files: {dangling_in_plugins}",
    )
else:
    print("✓ 0 dangling /email references found in plugins/")

dangling_in_dist = []
if dist_dir.exists():
    for f in dist_dir.rglob("*"):
        if f.is_file() and "email-triage" not in f.name:
            try:
                content = f.read_text(errors="ignore")
                matches = dangling_regex.findall(content)
                if matches:
                    dangling_in_dist.append((str(f), matches))
            except Exception:
                pass

if dangling_in_dist:
    record_finding(
        "Dangling Plugin Refs",
        "Found dangling /email in dist/",
        "HIGH",
        f"Files: {dangling_in_dist}",
    )
else:
    print("✓ 0 dangling /email references found in dist/")


# -------------------------------------------------------------
# AREA 4: Skill Status Queries
# -------------------------------------------------------------
print("\n--- Area 4: Skill Status Queries ---")

# Test 4.1: Retiring /daily variants
daily_variants = [
    "daily",
    "/daily",
    "daily-note-template",
    "/daily-note-template",
    "aops-core:daily",
]
for variant in daily_variants:
    st = diagnose_skill_status(variant)
    if st != SkillStatus.DELIBERATELY_REMOVED:
        record_finding(
            "Skill Status",
            f"Skill '{variant}' misdiagnosed",
            "HIGH",
            f"Expected deliberately_removed, got {st}",
        )

# Test 4.2: Case sensitivity / Whitespace in skill queries
cases_extra = [
    ("/DAILY", SkillStatus.MISSING),  # case sensitivity check
    ("  /daily  ", SkillStatus.DELIBERATELY_REMOVED),
    ("  daily  ", SkillStatus.DELIBERATELY_REMOVED),
    ("analyst", SkillStatus.INSTALLED),
    ("/analyst", SkillStatus.INSTALLED),
    ("brief", SkillStatus.INSTALLED),
    ("non_existent_skill_xyz", SkillStatus.MISSING),
]
for skill_str, exp_st in cases_extra:
    st = diagnose_skill_status(skill_str)
    if st != exp_st:
        record_finding(
            "Skill Status",
            f"Skill query '{skill_str}' mismatch",
            "MEDIUM",
            f"Expected {exp_st}, got {st}",
        )

# Test 4.3: Edge input types to diagnose_skill
edge_skills = ["", "/", "   "]
for edge in edge_skills:
    try:
        st = diagnose_skill_status(edge)
        print(f"Edge input '{edge}' -> status: {st}")
    except Exception as ex:
        record_finding(
            "Skill Status", f"diagnose_skill_status crashed on '{edge}'", "HIGH", str(ex)
        )


print("\n=== SUMMARY OF FINDINGS ===")
print(f"Total findings: {len(findings)}")
for f in findings:
    print(f"- [{f['severity']}] {f['category']}: {f['description']} -> {f['details']}")
