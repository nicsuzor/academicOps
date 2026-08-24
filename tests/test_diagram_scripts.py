import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT_DIR = Path(__file__).parent.parent / "plugins" / "tools" / "skills" / "diagram" / "scripts"
VIEW_SCRIPT = SCRIPT_DIR / "excalidraw-view.py"
EDIT_SCRIPT = SCRIPT_DIR / "excal-edit.py"


@pytest.fixture
def sample_excalidraw(tmp_path):
    doc = {
        "type": "excalidraw",
        "version": 2,
        "source": "https://excalidraw.com",
        "elements": [
            {
                "id": "rect1",
                "type": "rectangle",
                "x": 100,
                "y": 100,
                "width": 200,
                "height": 100,
                "angle": 0,
                "strokeColor": "#000000",
                "backgroundColor": "#ffffff",
                "fillStyle": "hachure",
                "strokeWidth": 1,
                "strokeStyle": "solid",
                "roughness": 1,
                "opacity": 100,
                "groupIds": [],
                "frameId": None,
                "index": "a0",
                "version": 1,
                "versionNonce": 12345,
                "isDeleted": False,
                "boundElements": [{"id": "text1", "type": "text"}],
                "updated": 1000,
                "link": None,
                "locked": False,
            },
            {
                "id": "text1",
                "type": "text",
                "x": 110,
                "y": 120,
                "width": 180,
                "height": 30,
                "angle": 0,
                "strokeColor": "#000000",
                "backgroundColor": "transparent",
                "fillStyle": "hachure",
                "strokeWidth": 1,
                "strokeStyle": "solid",
                "roughness": 1,
                "opacity": 100,
                "groupIds": [],
                "frameId": None,
                "index": "a1",
                "version": 1,
                "versionNonce": 12346,
                "isDeleted": False,
                "boundElements": None,
                "updated": 1000,
                "link": None,
                "locked": False,
                "text": "Short Text",
                "fontSize": 20,
                "fontFamily": 1,
                "textAlign": "center",
                "verticalAlign": "middle",
                "containerId": "rect1",
                "originalText": "Short Text",
                "lineHeight": 1.25,
            },
            {
                "id": "rect2",
                "type": "rectangle",
                "x": 400,
                "y": 100,
                "width": 150,
                "height": 100,
                "angle": 0,
                "strokeColor": "#000000",
                "backgroundColor": "#76c893",
                "fillStyle": "hachure",
                "strokeWidth": 1,
                "strokeStyle": "solid",
                "roughness": 1,
                "opacity": 100,
                "groupIds": [],
                "frameId": None,
                "index": "a2",
                "version": 1,
                "versionNonce": 12347,
                "isDeleted": False,
                "boundElements": [],
                "updated": 1000,
                "link": None,
                "locked": False,
            },
        ],
        "appState": {"gridSize": None, "viewBackgroundColor": "#ffffff"},
        "files": {},
    }
    p = tmp_path / "sample.excalidraw"
    p.write_text(json.dumps(doc, indent=2))
    return p


def test_excal_edit_fit(sample_excalidraw):
    long_text = "This is a much longer line of text\nthat spans multiple lines cleanly"
    res = subprocess.run(
        [sys.executable, str(EDIT_SCRIPT), str(sample_excalidraw), "fit", "rect1", long_text],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "Resized text 'text1'" in res.stdout
    assert "container 'rect1'" in res.stdout

    # Verify JSON was updated and container grew
    with open(sample_excalidraw) as f:
        data = json.load(f)
    rect1 = next(e for e in data["elements"] if e["id"] == "rect1")
    text1 = next(e for e in data["elements"] if e["id"] == "text1")

    assert text1["text"] == long_text
    assert rect1["width"] > 200  # container grew centered
    # Check text is centered in rect1
    cx_rect = rect1["x"] + rect1["width"] / 2.0
    cx_text = text1["x"] + text1["width"] / 2.0
    assert abs(cx_rect - cx_text) < 1e-3


def test_excal_edit_overlap_no_collision(sample_excalidraw):
    res = subprocess.run(
        [sys.executable, str(EDIT_SCRIPT), str(sample_excalidraw), "overlap"],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0
    assert "OK: no overlapping non-nested sibling elements found" in res.stdout


def test_excal_edit_overlap_collision(sample_excalidraw):
    with open(sample_excalidraw) as f:
        data = json.load(f)
    # Move rect2 so it overlaps rect1 (rect1 is x:100..300, y:100..200)
    rect2 = next(e for e in data["elements"] if e["id"] == "rect2")
    rect2["x"] = 150
    rect2["y"] = 120
    with open(sample_excalidraw, "w") as f:
        json.dump(data, f)

    res = subprocess.run(
        [sys.executable, str(EDIT_SCRIPT), str(sample_excalidraw), "overlap"],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 1
    assert "FAIL: 1 AABB collision(s) detected" in res.stdout


def test_excalidraw_view_diff(sample_excalidraw, tmp_path):
    # Create modified copy
    with open(sample_excalidraw) as f:
        data2 = json.load(f)
    # Delete rect2, add rect3
    data2["elements"] = [e for e in data2["elements"] if e["id"] != "rect2"]
    data2["elements"].append(
        {
            "id": "rect3",
            "type": "rectangle",
            "x": 600,
            "y": 100,
            "width": 100,
            "height": 100,
            "index": "a3",
            "isDeleted": False,
        }
    )
    p2 = tmp_path / "modified.excalidraw"
    p2.write_text(json.dumps(data2, indent=2))

    res = subprocess.run(
        [sys.executable, str(VIEW_SCRIPT), str(sample_excalidraw), "diff", str(p2)],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "Summary Diff: 3 elements -> 3 elements" in res.stdout
    assert "Disappeared elements (1):" in res.stdout
    assert "rect2" in res.stdout
    assert "Added elements (1):" in res.stdout
    assert "rect3" in res.stdout


def test_excal_edit_render(sample_excalidraw, tmp_path):
    import importlib.util

    out_png = tmp_path / "output.png"
    has_matplotlib = importlib.util.find_spec("matplotlib") is not None

    if not has_matplotlib:
        res = subprocess.run(
            [sys.executable, str(EDIT_SCRIPT), str(sample_excalidraw), "render", str(out_png)],
            capture_output=True,
            text=True,
        )
        assert res.returncode == 1
        assert "render mode requires matplotlib" in res.stderr
    else:
        res = subprocess.run(
            [sys.executable, str(EDIT_SCRIPT), str(sample_excalidraw), "render", str(out_png)],
            capture_output=True,
            text=True,
            check=True,
        )
        assert "Rendered diagram to" in res.stdout
        assert out_png.exists()
        assert out_png.stat().st_size > 0


@pytest.fixture
def card_with_sibling_texts(tmp_path):
    doc = {
        "type": "excalidraw",
        "version": 2,
        "source": "https://excalidraw.com",
        "elements": [
            {
                "id": "card1",
                "type": "rectangle",
                "x": 100,
                "y": 100,
                "width": 250,
                "height": 130,
                "angle": 0,
                "strokeColor": "#404040",
                "backgroundColor": "#ffffff",
                "fillStyle": "hachure",
                "strokeWidth": 1,
                "strokeStyle": "solid",
                "roughness": 1,
                "opacity": 100,
                "groupIds": [],
                "frameId": None,
                "index": "a0",
                "version": 1,
                "versionNonce": 1001,
                "isDeleted": False,
                "boundElements": [
                    {"id": "card1-label", "type": "text"},
                    {"id": "card1-sub", "type": "text"},
                    {"id": "card1-id", "type": "text"},
                ],
                "updated": 1000,
                "link": None,
                "locked": False,
            },
            {
                "id": "card1-label",
                "type": "text",
                "x": 110,
                "y": 115,
                "width": 200,
                "height": 30,
                "angle": 0,
                "strokeColor": "#1a1a1a",
                "backgroundColor": "transparent",
                "fillStyle": "hachure",
                "strokeWidth": 1,
                "strokeStyle": "solid",
                "roughness": 1,
                "opacity": 100,
                "groupIds": [],
                "frameId": None,
                "index": "a1",
                "version": 1,
                "versionNonce": 1002,
                "isDeleted": False,
                "boundElements": None,
                "updated": 1000,
                "link": None,
                "locked": False,
                "text": "Card Main Label",
                "originalText": "Card Main Label",
                "fontSize": 20,
                "fontFamily": 1,
                "textAlign": "center",
                "verticalAlign": "middle",
                "containerId": "card1",
                "lineHeight": 1.25,
            },
            {
                "id": "card1-sub",
                "type": "text",
                "x": 110,
                "y": 150,
                "width": 180,
                "height": 25,
                "angle": 0,
                "strokeColor": "#888888",
                "backgroundColor": "transparent",
                "fillStyle": "hachure",
                "strokeWidth": 1,
                "strokeStyle": "solid",
                "roughness": 1,
                "opacity": 100,
                "groupIds": [],
                "frameId": None,
                "index": "a2",
                "version": 1,
                "versionNonce": 1003,
                "isDeleted": False,
                "boundElements": None,
                "updated": 1000,
                "link": None,
                "locked": False,
                "text": "Card Subtitle Text",
                "originalText": "Card Subtitle Text",
                "fontSize": 14,
                "fontFamily": 1,
                "textAlign": "center",
                "verticalAlign": "middle",
                "containerId": "card1",
                "lineHeight": 1.25,
            },
            {
                "id": "card1-id",
                "type": "text",
                "x": 110,
                "y": 180,
                "width": 120,
                "height": 20,
                "angle": 0,
                "strokeColor": "#888888",
                "backgroundColor": "transparent",
                "fillStyle": "hachure",
                "strokeWidth": 1,
                "strokeStyle": "solid",
                "roughness": 1,
                "opacity": 100,
                "groupIds": [],
                "frameId": None,
                "index": "a3",
                "version": 1,
                "versionNonce": 1004,
                "isDeleted": False,
                "boundElements": None,
                "updated": 1000,
                "link": None,
                "locked": False,
                "text": "task-48234949",
                "originalText": "task-48234949",
                "fontSize": 12,
                "fontFamily": 1,
                "textAlign": "center",
                "verticalAlign": "middle",
                "containerId": "card1",
                "lineHeight": 1.25,
            },
        ],
        "appState": {"gridSize": None, "viewBackgroundColor": "#ffffff"},
        "files": {},
    }
    p = tmp_path / "card_sample.excalidraw"
    p.write_text(json.dumps(doc, indent=2))
    return p


def test_excal_edit_overlap_detects_sibling_text_collision(card_with_sibling_texts):
    # Injected fault: move card1-sub so its y is 120, directly overprinting card1-label (y=115..145)
    with open(card_with_sibling_texts) as f:
        data = json.load(f)
    sub = next(e for e in data["elements"] if e["id"] == "card1-sub")
    sub["y"] = 120
    with open(card_with_sibling_texts, "w") as f:
        json.dump(data, f)

    res = subprocess.run(
        [sys.executable, str(EDIT_SCRIPT), str(card_with_sibling_texts), "overlap"],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 1
    assert "FAIL: 1 AABB collision(s) detected" in res.stdout
    assert "card1-label" in res.stdout
    assert "card1-sub" in res.stdout


def test_excal_edit_overlap_baseline_file(card_with_sibling_texts, tmp_path):
    # Inject fault
    with open(card_with_sibling_texts) as f:
        data = json.load(f)
    sub = next(e for e in data["elements"] if e["id"] == "card1-sub")
    sub["y"] = 120
    with open(card_with_sibling_texts, "w") as f:
        json.dump(data, f)

    # Create baseline JSON file with known collision
    baseline_file = tmp_path / "baseline.json"
    baseline_file.write_text(json.dumps([["card1-label", "card1-sub"]]))

    res = subprocess.run(
        [
            sys.executable,
            str(EDIT_SCRIPT),
            str(card_with_sibling_texts),
            "overlap",
            "--baseline",
            str(baseline_file),
        ],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0
    assert "OK" in res.stdout

    # Now add an unrelated second collision
    with open(card_with_sibling_texts) as f:
        data = json.load(f)
    data["elements"].append(
        {
            "id": "unrelated_rect",
            "type": "rectangle",
            "x": 100,
            "y": 100,
            "width": 50,
            "height": 50,
            "index": "a4",
            "isDeleted": False,
        }
    )
    with open(card_with_sibling_texts, "w") as f:
        json.dump(data, f)

    res2 = subprocess.run(
        [
            sys.executable,
            str(EDIT_SCRIPT),
            str(card_with_sibling_texts),
            "overlap",
            "--baseline",
            str(baseline_file),
        ],
        capture_output=True,
        text=True,
    )
    assert res2.returncode == 1
    assert "FAIL: 1 AABB collision(s) detected" in res2.stdout
    assert "unrelated_rect" in res2.stdout


def test_excal_edit_overlap_baseline_inline(card_with_sibling_texts):
    with open(card_with_sibling_texts) as f:
        data = json.load(f)
    sub = next(e for e in data["elements"] if e["id"] == "card1-sub")
    sub["y"] = 120
    with open(card_with_sibling_texts, "w") as f:
        json.dump(data, f)

    res = subprocess.run(
        [
            sys.executable,
            str(EDIT_SCRIPT),
            str(card_with_sibling_texts),
            "overlap",
            "--baseline",
            "card1-label:card1-sub",
        ],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0
    assert "OK" in res.stdout


def test_excal_edit_restack_repairs_overprint(card_with_sibling_texts):
    # Injected overprint
    with open(card_with_sibling_texts) as f:
        data = json.load(f)
    sub = next(e for e in data["elements"] if e["id"] == "card1-sub")
    sub["y"] = 118
    with open(card_with_sibling_texts, "w") as f:
        json.dump(data, f)

    # Run restack on card1
    res = subprocess.run(
        [sys.executable, str(EDIT_SCRIPT), str(card_with_sibling_texts), "restack", "card1"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "Restacked" in res.stdout

    # Verify positions
    with open(card_with_sibling_texts) as f:
        data = json.load(f)
    lbl = next(e for e in data["elements"] if e["id"] == "card1-label")
    sub = next(e for e in data["elements"] if e["id"] == "card1-sub")
    cid = next(e for e in data["elements"] if e["id"] == "card1-id")
    card = next(e for e in data["elements"] if e["id"] == "card1")

    # Card rectangle geometry unchanged
    assert card["x"] == 100
    assert card["y"] == 100
    assert card["width"] == 250
    assert card["height"] == 130

    # Texts ordered vertically without collision
    assert sub["y"] >= lbl["y"] + lbl["height"] + 4.9
    assert cid["y"] >= sub["y"] + sub["height"] + 4.9
    assert cid["y"] + cid["height"] <= card["y"] + card["height"]

    # Verify overlap check is now completely clean
    res_overlap = subprocess.run(
        [sys.executable, str(EDIT_SCRIPT), str(card_with_sibling_texts), "overlap"],
        capture_output=True,
        text=True,
    )
    assert res_overlap.returncode == 0
    assert "OK: no overlapping non-nested sibling elements found" in res_overlap.stdout


def test_excal_edit_restack_convention_independent(tmp_path):
    # Tests that restack discovers sibling texts without any suffix assumptions
    doc = {
        "type": "excalidraw",
        "version": 2,
        "source": "https://excalidraw.com",
        "elements": [
            {
                "id": "node_box_xyz",
                "type": "rectangle",
                "x": 200,
                "y": 200,
                "width": 300,
                "height": 150,
                "index": "a0",
                "isDeleted": False,
                "boundElements": [
                    {"id": "title_elem_1", "type": "text"},
                    {"id": "meta_badge_2", "type": "text"},
                ],
            },
            {
                "id": "title_elem_1",
                "type": "text",
                "x": 210,
                "y": 220,
                "width": 250,
                "height": 40,
                "index": "a1",
                "containerId": "node_box_xyz",
                "text": "Heading Without Standard Suffix",
                "originalText": "Heading Without Standard Suffix",
                "isDeleted": False,
            },
            {
                "id": "meta_badge_2",
                "type": "text",
                "x": 210,
                "y": 230,  # colliding inside title_elem_1
                "width": 200,
                "height": 30,
                "index": "a2",
                "containerId": "node_box_xyz",
                "text": "Arbitrary Id Sibling",
                "originalText": "Arbitrary Id Sibling",
                "isDeleted": False,
            },
        ],
        "appState": {},
        "files": {},
    }
    p = tmp_path / "custom_naming.excalidraw"
    p.write_text(json.dumps(doc, indent=2))

    res = subprocess.run(
        [sys.executable, str(EDIT_SCRIPT), str(p), "restack", "node_box_xyz"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "Restacked" in res.stdout

    with open(p) as f:
        data = json.load(f)
    t1 = next(e for e in data["elements"] if e["id"] == "title_elem_1")
    t2 = next(e for e in data["elements"] if e["id"] == "meta_badge_2")
    assert t2["y"] >= t1["y"] + t1["height"] + 4.9


def test_excal_edit_restack_fail_closed_overflow(tmp_path):
    doc = {
        "type": "excalidraw",
        "version": 2,
        "elements": [
            {
                "id": "small_card",
                "type": "rectangle",
                "x": 100,
                "y": 100,
                "width": 100,
                "height": 40,  # Only 40px tall
                "index": "a0",
                "isDeleted": False,
                "boundElements": [
                    {"id": "t1", "type": "text"},
                    {"id": "t2", "type": "text"},
                ],
            },
            {
                "id": "t1",
                "type": "text",
                "x": 105,
                "y": 105,
                "width": 80,
                "height": 30,  # 30px
                "index": "a1",
                "containerId": "small_card",
                "text": "Text 1",
                "originalText": "Text 1",
                "isDeleted": False,
            },
            {
                "id": "t2",
                "type": "text",
                "x": 105,
                "y": 110,
                "width": 80,
                "height": 30,  # 30px -> total 30 + 5 + 30 = 65px > 40px
                "index": "a2",
                "containerId": "small_card",
                "text": "Text 2",
                "originalText": "Text 2",
                "isDeleted": False,
            },
        ],
    }
    p = tmp_path / "overflow.excalidraw"
    original_bytes = json.dumps(doc, indent=2)
    p.write_text(original_bytes)

    res = subprocess.run(
        [sys.executable, str(EDIT_SCRIPT), str(p), "restack", "small_card"],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 1
    assert "overflow" in res.stderr.lower() or "overflow" in res.stdout.lower()
    # File must be untouched
    assert p.read_text() == original_bytes


def test_excal_edit_restack_fail_closed_no_other_mutations(card_with_sibling_texts):
    with open(card_with_sibling_texts) as f:
        data_before = json.load(f)

    res = subprocess.run(
        [sys.executable, str(EDIT_SCRIPT), str(card_with_sibling_texts), "restack", "card1"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert res.returncode == 0

    with open(card_with_sibling_texts) as f:
        data_after = json.load(f)

    # Compare non-restacked element fingerprints and restacked text invariants
    for e_before, e_after in zip(data_before["elements"], data_after["elements"], strict=True):
        if e_before["id"] == "card1":
            assert e_before == e_after
        elif e_before["id"] in ("card1-label", "card1-sub", "card1-id"):
            for key in (
                "id",
                "type",
                "width",
                "height",
                "text",
                "originalText",
                "fontSize",
                "index",
                "isDeleted",
            ):
                assert e_before[key] == e_after[key]
