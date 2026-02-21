from __future__ import annotations
from unittest.mock import MagicMock
import pytest

from lib.task_index import TaskIndexEntry
from lib.ascii_tree import AsciiTreeGenerator

class TestAsciiTreeGenerator:
    def test_generate_simple_tree(self):
        # Create mock index entries using keyword arguments
        root = TaskIndexEntry(
            id="aops-nn1l", title="Write TJA paper", type="epic", status="active",
            priority=1, order=0, parent=None, children=["aops-lr01", "aops-da01", "aops-wr01", "aops-wr02"],
            depends_on=[], blocks=[], path=""
        )
        lr = TaskIndexEntry(
            id="aops-lr01", title="Literature review", type="task", status="active",
            priority=2, order=0, parent="aops-nn1l", children=["aops-lr02", "aops-lr03"],
            depends_on=[], blocks=[], path=""
        )
        lr2 = TaskIndexEntry(
            id="aops-lr02", title="Search databases for [terms]", type="action", status="done",
            priority=2, order=0, parent="aops-lr01", children=[],
            depends_on=[], blocks=[], path="", assignee="bot"
        )
        lr3 = TaskIndexEntry(
            id="aops-lr03", title="Screen 50 abstracts", type="task", status="active",
            priority=2, order=1, parent="aops-lr01", children=[],
            depends_on=[], blocks=[], path=""
        )

        # Mock index
        index = MagicMock()

        def get_task_side_effect(tid):
            mapping = {
                "aops-nn1l": root,
                "aops-lr01": lr,
                "aops-lr02": lr2,
                "aops-lr03": lr3
            }
            return mapping.get(tid)

        index.get_task.side_effect = get_task_side_effect

        def get_children_side_effect(tid):
            mapping = {
                "aops-nn1l": [lr], # Simplified for test
                "aops-lr01": [lr2, lr3],
                "aops-lr02": [],
                "aops-lr03": []
            }
            return mapping.get(tid, [])

        index.get_children.side_effect = get_children_side_effect

        generator = AsciiTreeGenerator(index)
        tree = generator.generate_tree("aops-nn1l")

        # Expected output matching spec
        expected = (
            "○ aops-nn1l [P1] [epic] Write TJA paper\n"
            "└─○ aops-lr01 [P2] Literature review\n"
            "  ├─● aops-lr02 [P2] @bot Search databases for [terms]\n"
            "  └─○ aops-lr03 [P2] Screen 50 abstracts"
        )

        print(f"Generated:\n{tree}")
        print(f"Expected:\n{expected}")

        assert tree.strip() == expected.strip()

    def test_status_symbols(self):
        # Create minimal entries
        def make_entry(tid, status, order=0):
            return TaskIndexEntry(
                id=tid, title=tid.capitalize(), type="task", status=status,
                priority=2, order=order, parent="root", children=[], depends_on=[], blocks=[], path=""
            )

        root = make_entry("root", "active")
        root.parent = None

        t1 = make_entry("t1", "active", 0)
        t2 = make_entry("t2", "done", 1)
        t3 = make_entry("t3", "in_progress", 2)
        t4 = make_entry("t4", "blocked", 3)
        t5 = make_entry("t5", "cancelled", 4)
        t6 = make_entry("t6", "waiting", 5)

        index = MagicMock()

        def get_task_side_effect(tid):
            if tid == "root": return root
            if tid == "t1": return t1
            if tid == "t2": return t2
            if tid == "t3": return t3
            if tid == "t4": return t4
            if tid == "t5": return t5
            if tid == "t6": return t6
            return None
        index.get_task.side_effect = get_task_side_effect

        def get_children_side_effect(tid):
            if tid == "root":
                return [t1, t2, t3, t4, t5, t6]
            return []
        index.get_children.side_effect = get_children_side_effect

        generator = AsciiTreeGenerator(index)
        tree = generator.generate_tree("root")

        # Check symbols
        assert "○ t1" in tree # active
        assert "● t2" in tree # done
        assert "◐ t3" in tree # in_progress
        assert "⊘ t4" in tree # blocked
        assert "● t5" in tree # cancelled (closed)
        assert "○ t6" in tree # waiting (open)

    def test_generate_project_tree(self):
        # Create tasks for project "proj1"
        r1 = TaskIndexEntry(id="r1", title="Root 1", type="task", status="active", priority=1, order=0, parent=None, children=["c1"], depends_on=[], blocks=[], path="", project="proj1")
        c1 = TaskIndexEntry(id="c1", title="Child 1", type="task", status="done", priority=2, order=0, parent="r1", children=[], depends_on=[], blocks=[], path="", project="proj1")
        r2 = TaskIndexEntry(id="r2", title="Root 2", type="task", status="active", priority=2, order=0, parent=None, children=[], depends_on=[], blocks=[], path="", project="proj1")

        index = MagicMock()
        index.get_by_project.return_value = [r1, c1, r2]

        def get_task_side_effect(tid):
            mapping = {"r1": r1, "c1": c1, "r2": r2}
            return mapping.get(tid)
        index.get_task.side_effect = get_task_side_effect

        def get_children_side_effect(tid):
            mapping = {"r1": [c1], "c1": [], "r2": []}
            return mapping.get(tid, [])
        index.get_children.side_effect = get_children_side_effect

        generator = AsciiTreeGenerator(index)
        tree = generator.generate_project_tree("proj1")

        expected = (
            "○ r1 [P1] Root 1\n"
            "└─● c1 [P2] Child 1\n\n"
            "○ r2 [P2] Root 2"
        )

        print(f"Generated:\n{tree}")
        print(f"Expected:\n{expected}")

        assert tree.strip() == expected.strip()
