#!/usr/bin/env python3
"""Demo test for Session Transcript Generation.

Demonstrates the complete workflow for generating markdown transcripts from
real Claude session JSONL files. This test walks through:

1. **Session Discovery**: Finding real session files from ~/.claude/projects/
2. **Session Selection**: Choosing a suitable session (with minimum size)
3. **Transcript Generation**: Running session_transcript.py script
4. **Output Validation**: Verifying both full and abridged variants created

The transcript generation pipeline converts raw JSONL session logs into
human-readable markdown documents. Two variants are produced:
- **Full transcript**: Complete conversation with all details
- **Abridged transcript**: Condensed version for quick review

This test uses REAL session data from your local Claude projects directory,
proving that the transcript generation pipeline works on actual production data.

Run with: uv run pytest tests/demo/test_demo_transcript_generation.py -v -s -n 0 -m demo

Related:
- scripts/session_transcript.py - Transcript generation script
- lib/session_reader.py - Session parsing utilities
- skills/transcript/SKILL.md - Transcript skill documentation
"""

import subprocess
from pathlib import Path

import pytest


@pytest.mark.demo
class TestTranscriptGenerationDemo:
    """Demo test for session transcript generation workflow."""

    def test_demo_generate_transcript_from_real_session(self, tmp_path: Path) -> None:
        """Demo: Generate full and abridged transcripts from a real session.

        This demonstrates the complete transcript generation pipeline that
        converts JSONL session logs into readable markdown documents.

        The workflow:
        1. Find real session files in ~/.claude/projects/
        2. Select a session with sufficient content (>5KB)
        3. Run session_transcript.py to generate both variants
        4. Validate the output files were created correctly
        """
        print("\n" + "=" * 80)
        print("TRANSCRIPT GENERATION DEMO: Session → Markdown Pipeline")
        print("=" * 80)

        # === STEP 1: Discover Session Files ===
        print("\n--- STEP 1: Session Discovery ---")
        projects_dir = Path.home() / ".claude" / "projects"

        if not projects_dir.exists():
            pytest.skip(f"Claude projects directory not found: {projects_dir}")

        print(f"Scanning: {projects_dir}")
        session_files = list(projects_dir.rglob("*.jsonl"))

        # Filter out hook files and subagent files (for main session demos)
        session_files = [
            f
            for f in session_files
            if not f.name.endswith("-hooks.jsonl") and "subagent" not in str(f)
        ]

        if not session_files:
            pytest.skip(f"No main session files found in {projects_dir}")

        print(f"Found {len(session_files)} session file(s)")

        # === STEP 2: Select Suitable Session ===
        print("\n--- STEP 2: Session Selection ---")

        # Sort by size and find one with enough content
        MIN_SIZE = 5000  # 5KB minimum per spec
        session_files_with_size = [(f, f.stat().st_size) for f in session_files]
        session_files_with_size.sort(key=lambda x: -x[1])  # Largest first

        print(f"Looking for session >= {MIN_SIZE:,} bytes...")

        # Show size distribution
        size_ranges = {
            "<1KB": 0,
            "1-5KB": 0,
            "5-50KB": 0,
            "50-500KB": 0,
            ">500KB": 0,
        }
        for _, size in session_files_with_size:
            if size < 1000:
                size_ranges["<1KB"] += 1
            elif size < 5000:
                size_ranges["1-5KB"] += 1
            elif size < 50000:
                size_ranges["5-50KB"] += 1
            elif size < 500000:
                size_ranges["50-500KB"] += 1
            else:
                size_ranges[">500KB"] += 1

        print("Size distribution:")
        for range_name, count in size_ranges.items():
            print(f"  {range_name}: {count} files")

        # Find files meeting minimum size - prefer larger files for realistic demos
        large_enough = [(f, s) for f, s in session_files_with_size if s >= MIN_SIZE]
        if not large_enough:
            pytest.skip(f"No session files >= {MIN_SIZE} bytes found")

        # Use most recent among those large enough
        session_file = max(
            [f for f, _ in large_enough], key=lambda f: f.stat().st_mtime
        )
        file_size = session_file.stat().st_size

        print(f"\nSelected: {session_file.name}")
        print(f"  Project: {session_file.parent.name}")
        print(f"  Size: {file_size:,} bytes")
        print(f"  Path: {session_file}")

        # === STEP 3: Generate Transcripts ===
        print("\n--- STEP 3: Transcript Generation ---")

        output_base = tmp_path / "demo-transcript"
        script_path = (
            Path(__file__).parent.parent.parent / "scripts" / "session_transcript.py"
        )

        print(f"Script: {script_path}")
        print(f"Input: {session_file}")
        print(f"Output base: {output_base}")

        if not script_path.exists():
            pytest.skip(f"Transcript script not found: {script_path}")

        print("\nRunning transcript generation...")

        result = subprocess.run(
            [
                "uv",
                "run",
                "python",
                str(script_path),
                str(session_file),
                "-o",
                str(output_base),
            ],
            capture_output=True,
            text=True,
            cwd=script_path.parent.parent,
            timeout=300,  # 5 minutes for large session files
        )

        print(f"Exit code: {result.returncode}")

        if result.returncode != 0:
            print("\n❌ Script failed!")
            print(f"STDERR:\n{result.stderr[:500]}")
            pytest.fail(f"Transcript generation failed: {result.stderr[:200]}")

        print("✅ Script completed successfully")

        # === STEP 4: Validate Output Files ===
        print("\n--- STEP 4: Output Validation ---")

        full_file = tmp_path / "demo-transcript-full.md"
        abridged_file = tmp_path / "demo-transcript-abridged.md"

        print("Expected outputs:")
        print(f"  Full: {full_file}")
        print(f"  Abridged: {abridged_file}")

        # Check existence
        full_exists = full_file.exists()
        abridged_exists = abridged_file.exists()

        print("\nFile existence:")
        print(f"  [{'OK' if full_exists else 'MISSING'}] Full transcript")
        print(f"  [{'OK' if abridged_exists else 'MISSING'}] Abridged transcript")

        assert full_exists, f"Full transcript not created: {full_file}"
        assert abridged_exists, f"Abridged transcript not created: {abridged_file}"

        # Check sizes
        full_size = full_file.stat().st_size
        abridged_size = abridged_file.stat().st_size

        print("\nFile sizes:")
        print(f"  Full: {full_size:,} bytes")
        print(f"  Abridged: {abridged_size:,} bytes")
        print(f"  Compression ratio: {abridged_size/full_size*100:.1f}%")

        assert full_size > 0, "Full transcript is empty"
        assert abridged_size > 0, "Abridged transcript is empty"

        # === STEP 5: Content Preview ===
        print("\n--- STEP 5: Content Preview ---")

        # Show beginning of abridged transcript
        abridged_content = abridged_file.read_text()
        full_content = full_file.read_text()

        print("\n📄 Abridged Transcript Preview (first 500 chars):")
        print("-" * 40)
        print(abridged_content[:500])
        if len(abridged_content) > 500:
            print("...")
        print("-" * 40)

        # Count markdown elements
        def count_elements(content: str) -> dict:
            lines = content.split("\n")
            return {
                "headings": sum(1 for line in lines if line.startswith("#")),
                "code_blocks": content.count("```"),
                "total_lines": len(lines),
            }

        full_stats = count_elements(full_content)
        abridged_stats = count_elements(abridged_content)

        print("\n📊 Content Statistics:")
        print(f"  {'Metric':<20} {'Full':>10} {'Abridged':>10}")
        print(f"  {'-'*20} {'-'*10} {'-'*10}")
        print(
            f"  {'Lines':<20} {full_stats['total_lines']:>10,} {abridged_stats['total_lines']:>10,}"
        )
        print(
            f"  {'Headings':<20} {full_stats['headings']:>10} {abridged_stats['headings']:>10}"
        )
        print(
            f"  {'Code blocks':<20} {full_stats['code_blocks']:>10} {abridged_stats['code_blocks']:>10}"
        )

        # === Final Summary ===
        print("\n" + "=" * 80)
        print("VALIDATION CRITERIA")
        print("=" * 80)

        criteria = [
            ("Script executed successfully", result.returncode == 0),
            ("Full transcript created", full_exists),
            ("Abridged transcript created", abridged_exists),
            ("Full transcript has content", full_size > 0),
            ("Abridged transcript has content", abridged_size > 0),
            # Note: For very small sessions, abridged may be similar size due to metadata
        ]

        all_passed = True
        for name, passed in criteria:
            status = "PASS" if passed else "FAIL"
            if not passed:
                all_passed = False
            print(f"  [{status}] {name}")

        print("\n" + "=" * 80)
        print("DEMO SUMMARY")
        print("=" * 80)
        print(
            f"""
This demo showed the complete transcript generation pipeline:

1. DISCOVERY: Found {len(session_files)} session files in {projects_dir}
2. SELECTION: Chose session with {file_size:,} bytes of content
3. GENERATION: Ran session_transcript.py to create both variants
4. VALIDATION: Verified outputs exist and have content

The transcript pipeline produces:
- Full transcript ({full_size:,} bytes): Complete conversation details
- Abridged transcript ({abridged_size:,} bytes): {abridged_size/full_size*100:.1f}% of full

These transcripts are used for:
- Human review of agent sessions
- Documentation and knowledge capture
- Debugging and analysis
- Compliance auditing

This proves the transcript generation pipeline works on REAL production data.
"""
        )
        print("=" * 80)
        if all_passed:
            print("PASS: Transcript generation demo completed successfully")
        else:
            pytest.fail("Transcript generation validation failed")
        print("=" * 80)

        assert all_passed, "Transcript validation criteria not met"
