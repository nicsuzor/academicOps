import sys

# Add lib/overwhelm to path to find the module
sys.path.append("lib/overwhelm")

from task_graph_d3 import generate_graph_from_tasks


class MockTask:
    def __init__(self, id, title, status="active", priority=2, project=None, type="task", depends_on=None, parent=None):
        self.id = id
        self.title = title
        self.status = status
        self.priority = priority
        self.project = project
        self.type = type
        self.depends_on = depends_on or []
        self.parent = parent

def test_generate_graph_simple():
    tasks = [
        MockTask(id="1", title="Task 1"),
        MockTask(id="2", title="Task 2", depends_on=["1"]),
    ]

    graph = generate_graph_from_tasks(tasks)

    assert len(graph["nodes"]) == 2
    assert len(graph["links"]) == 1

    link = graph["links"][0]
    assert link["source"] == "1"
    assert link["target"] == "2"
    assert link["type"] == "dependency"

def test_generate_graph_with_parent():
    tasks = [
        MockTask(id="parent", title="Parent"),
        MockTask(id="child", title="Child", parent="parent"),
    ]

    graph = generate_graph_from_tasks(tasks)

    assert len(graph["nodes"]) == 2
    assert len(graph["links"]) == 1

    link = graph["links"][0]
    assert link["source"] == "parent"
    assert link["target"] == "child"
    assert link["type"] == "parent"

def test_generate_graph_from_dicts():
    tasks = [
        {"id": "1", "title": "Task 1", "status": "active", "priority": 1, "project": "p1", "type": "task"},
        {"id": "2", "title": "Task 2", "depends_on": ["1"], "status": "active", "priority": 1, "project": "p1", "type": "task"},
    ]

    graph = generate_graph_from_tasks(tasks)

    assert len(graph["nodes"]) == 2
    assert len(graph["links"]) == 1

    link = graph["links"][0]
    assert link["source"] == "1"
    assert link["target"] == "2"
