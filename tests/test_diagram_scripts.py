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
