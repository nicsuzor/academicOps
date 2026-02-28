import os

import streamlit.components.v1 as components

_component_func = components.declare_component(
    "d3_task_graph", path=os.path.join(os.path.dirname(os.path.abspath(__file__)))
)


def d3_task_graph(data, width="100%", height=600, force_settings=None, key=None):
    """
    Renders the D3 Task Graph as a bi-directional Streamlit component.
    Returns the clicked action and node ID: e.g. {"action": "edit", "id": "task_1"}
    """
    if force_settings is None:
        force_settings = {}  # All defaults now in FORCE_CONFIG (task_graph_d3.py)

    component_value = _component_func(
        data=data, width=width, height=height, force=force_settings, key=key, default=None
    )
    return component_value
