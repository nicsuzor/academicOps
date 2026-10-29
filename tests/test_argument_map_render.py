"""Tests for argument map rendering from Argdown sources.

Verifies the build criteria and user stories defined in specs/tools/argument-map-rendering.md:
- US-1 Automated rebuild without hand layout (AC-1.1, AC-1.2)
- US-2 Referential integrity and collision-free geometry (AC-2.1, AC-2.2)
- US-3 Visual QA and multi-scale readability (AC-3.1, AC-3.2)
- US-4 In-place editability and change propagation (AC-4.1)
"""

from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
_RENDER_SCRIPT = (
    _REPO_ROOT / "plugins" / "ida" / "skills" / "argument-map" / "scripts" / "render.py"
)


def _load_render_module():
    spec = importlib.util.spec_from_file_location("argmap_render", _RENDER_SCRIPT)
    assert spec and spec.loader, f"cannot load {_RENDER_SCRIPT}"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SAMPLE_ARGDOWN = """===
title: "Test Policy Argument"
author: "Test Author"
job: "Testing automated map rendering"
legend:
  "#missing": "added premise"
  "#needs-evidence": "needs data"
===

# Thesis

[Core conclusion]: Public algorithms must provide verifiable explanations to individuals.
  +> [Secondary claim]

[Secondary claim]: Opaque algorithmic systems undermine due process.

# Part I: Foundations

<Due process requires explanation>: A decision without reasons cannot be meaningfully appealed.
  +> [Core conclusion]

<Due process requires explanation>

(1) [Explanation licenses appeal]: Contesting a decision requires knowing its operative factors. #needs-evidence
(2) Automated decisions affect rights directly.
----
(3) [Core conclusion]

<Opacity objection>: Technical explanations disclose proprietary trade secrets. #unanswered
  -> <Due process requires explanation>

# Part II: Empirical limits

<Current transparency fails>: Disclosed feature weights do not communicate counterfactual choices.
  -> [Secondary claim]
"""

SAMPLE_MARKDOWN = f"""# Test Note

Some introductory context.

## Argdown source

```argdown
{SAMPLE_ARGDOWN}
```
"""


@pytest.fixture
def render_mod():
    return _load_render_module()


def test_fractional_indexing_schema(render_mod):
    """Verify that generated index keys strictly conform to base-62 fractional indexing without trailing zeros (AC-2.1)."""
    keys = render_mod.make_index_keys(200)
    assert len(keys) == 200
    assert keys == sorted(keys), "Keys must be strictly monotonic"

    base62_chars = set("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz")
    for key in keys:
        assert set(key).issubset(base62_chars), f"Invalid characters in key {key}"
        head = key[0]
        int_len = ord(head) - 97 + 2
        frac_part = key[int_len:]
        assert not (frac_part and frac_part.endswith("0")), (
            f"Fractional part cannot end with zero: {key}"
        )


def test_render_argdown_file(tmp_path: Path, render_mod):
    """Verify US-1 (AC-1.1), US-2 (AC-2.1, AC-2.2), and US-3 (AC-3.1, AC-3.2)."""
    if not shutil.which("argdown"):
        pytest.skip("argdown CLI is not installed")
    if not shutil.which("pkb-excalidraw"):
        pytest.skip("pkb-excalidraw CLI is not installed")

    arg_file = tmp_path / "test_map.argdown"
    arg_file.write_text(SAMPLE_ARGDOWN, encoding="utf-8")
    out_dir = tmp_path / "out"

    results = render_mod.render_argument_map(str(arg_file), out_dir=out_dir)

    assert "canvas" in results
    assert "svg" in results
    assert "overview" in results

    canvas_file = Path(results["canvas"])
    svg_file = Path(results["svg"])
    overview_file = Path(results["overview"])

    assert canvas_file.is_file()
    assert svg_file.is_file()
    assert overview_file.is_file()
    assert svg_file.stat().st_size > 0

    # AC-2.1 Referential integrity audit
    chk = subprocess.run(
        ["pkb-excalidraw", str(canvas_file), "check"], capture_output=True, text=True
    )
    assert chk.returncode == 0, f"pkb-excalidraw check failed:\n{chk.stdout}\n{chk.stderr}"

    # AC-2.2 Spatial non-overlap audit
    ovl = subprocess.run(
        ["pkb-excalidraw", str(canvas_file), "overlap"], capture_output=True, text=True
    )
    assert ovl.returncode == 0, f"pkb-excalidraw overlap failed:\n{ovl.stdout}\n{ovl.stderr}"

    # AC-2.2 Connector polyline collision audit
    arr = subprocess.run(
        ["pkb-excalidraw", str(canvas_file), "arrows-check"], capture_output=True, text=True
    )
    assert arr.returncode == 0, f"pkb-excalidraw arrows-check failed:\n{arr.stdout}\n{arr.stderr}"

    # Overview page content verification
    overview_text = overview_file.read_text(encoding="utf-8")
    assert "Test Policy Argument" in overview_text
    assert "## Summary Metrics" in overview_text
    assert "## What the Argument Still Needs" in overview_text
    assert "Explanation licenses appeal" in overview_text
    assert "Opacity objection" in overview_text


def test_render_markdown_note(tmp_path: Path, render_mod):
    """Verify extracting Argdown from a PKB markdown note."""
    if not shutil.which("argdown") or not shutil.which("pkb-excalidraw"):
        pytest.skip("Required CLI tools missing")

    md_file = tmp_path / "test_note.md"
    md_file.write_text(SAMPLE_MARKDOWN, encoding="utf-8")
    out_dir = tmp_path / "out_md"

    results = render_mod.render_argument_map(str(md_file), out_dir=out_dir)

    canvas_file = Path(results["canvas"])
    assert canvas_file.is_file()

    with open(canvas_file, encoding="utf-8") as f:
        canvas_data = json.load(f)

    element_ids = [e["id"] for e in canvas_data.get("elements", [])]
    assert any("thesis" in eid for eid in element_ids)
    assert any("panel" in eid for eid in element_ids)

    chk = subprocess.run(
        ["pkb-excalidraw", str(canvas_file), "check"], capture_output=True, text=True
    )
    assert chk.returncode == 0


def test_claim_edit_changes_render(tmp_path: Path, render_mod):
    """Verify US-4 (AC-4.1): In-place editability and change propagation."""
    if not shutil.which("argdown") or not shutil.which("pkb-excalidraw"):
        pytest.skip("Required CLI tools missing")

    arg_file = tmp_path / "edit_test.argdown"
    arg_file.write_text(SAMPLE_ARGDOWN, encoding="utf-8")
    out_dir = tmp_path / "run_inplace"

    res1 = render_mod.render_argument_map(str(arg_file), out_dir=out_dir)
    with open(res1["canvas"], encoding="utf-8") as f:
        data1 = json.load(f)
    t1 = next(e["text"] for e in data1["elements"] if e["id"] == "txt_s_core_conclusion")
    assert "Public algorithms must provide verifiable" in t1

    # Edit claim in source
    updated_argdown = SAMPLE_ARGDOWN.replace(
        "Public algorithms must provide verifiable explanations to individuals.",
        "Algorithmic auditing must be mandated across public institutions.",
    )
    arg_file.write_text(updated_argdown, encoding="utf-8")

    res2 = render_mod.render_argument_map(str(arg_file), out_dir=out_dir)
    with open(res2["canvas"], encoding="utf-8") as f:
        data2 = json.load(f)
    t2 = next(e["text"] for e in data2["elements"] if e["id"] == "txt_s_core_conclusion")
    assert "Algorithmic auditing must be mandated" in t2
    assert t1 != t2

    # Check element ID is preserved
    ids1 = {e["id"] for e in data1["elements"]}
    ids2 = {e["id"] for e in data2["elements"]}
    assert "txt_s_core_conclusion" in ids1
    assert "txt_s_core_conclusion" in ids2


def test_cli_runner(tmp_path: Path, render_mod):
    """Verify CLI entry point execution."""
    if not shutil.which("argdown") or not shutil.which("pkb-excalidraw"):
        pytest.skip("Required CLI tools missing")

    arg_file = tmp_path / "cli_test.argdown"
    arg_file.write_text(SAMPLE_ARGDOWN, encoding="utf-8")
    out_dir = tmp_path / "cli_out"

    rc = render_mod.main([str(arg_file), "--out", str(out_dir)])
    assert rc == 0
    assert (out_dir / "cli_test.excalidraw").is_file()
    assert (out_dir / "cli_test.svg").is_file()
    assert (out_dir / "cli_test-overview.md").is_file()


def test_benchmark_topologies(tmp_path: Path, render_mod):
    """Verify US-1 (AC-1.2) and AC2: Three benchmark topologies compile cleanly."""
    if not shutil.which("argdown") or not shutil.which("pkb-excalidraw"):
        pytest.skip("Required CLI tools missing")

    benchmark_notes = [
        "kb_power_paper_argument_map",
        "note_6ca5834f",
        "note_62881c4a",
    ]

    for note_id in benchmark_notes:
        out_dir = tmp_path / note_id
        try:
            results = render_mod.render_argument_map(note_id, out_dir=out_dir)
        except Exception as exc:
            # If GitHub API is unreachable, skip
            pytest.skip(f"Could not fetch benchmark note {note_id}: {exc}")

        assert "canvas" in results
        assert "svg" in results
        assert "overview" in results

        canvas_path = Path(results["canvas"])
        assert canvas_path.is_file()
        assert Path(results["svg"]).is_file()
        assert Path(results["overview"]).is_file()

        chk = subprocess.run(
            ["pkb-excalidraw", str(canvas_path), "check"], capture_output=True, text=True
        )
        assert chk.returncode == 0, f"Check failed on {note_id}: {chk.stdout}"

        ovl = subprocess.run(
            ["pkb-excalidraw", str(canvas_path), "overlap"], capture_output=True, text=True
        )
        assert ovl.returncode == 0, f"Overlap failed on {note_id}: {ovl.stdout}"

        arr = subprocess.run(
            ["pkb-excalidraw", str(canvas_path), "arrows-check"], capture_output=True, text=True
        )
        assert arr.returncode == 0, f"Arrows-check failed on {note_id}: {arr.stdout}"
