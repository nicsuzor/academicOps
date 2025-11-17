#!/usr/bin/env python3
"""Generate Excalidraw visualization from task data.

This is a SIMPLE UTILITY that transforms structured task data into Excalidraw JSON.
The agent orchestrates all discovery, parsing, and reasoning - this script only does
mechanical layout generation.

Usage:
    python generate_task_viz.py input.json output.excalidraw

Input format (JSON):
    {
        "projects": [
            {
                "name": "framework",
                "tasks": [
                    {
                        "id": "task-001",
                        "title": "Active framework task",
                        "status": "active",
                        "priority": 1,
                        "blockers": []
                    }
                ]
            }
        ]
    }

Output: Valid Excalidraw JSON file
"""

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class LayoutConfig:
    """Layout configuration for visualization."""

    # Spacing
    project_vertical_gap: int = 300
    task_vertical_gap: int = 100
    task_horizontal_padding: int = 20
    task_vertical_padding: int = 15

    # Sizes
    task_width: int = 400
    task_height: int = 80
    project_label_height: int = 40

    # Starting position
    start_x: int = 100
    start_y: int = 100

    # Colors by status
    colors: dict[str, dict[str, str]] = None

    def __post_init__(self):
        """Initialize color mapping."""
        if self.colors is None:
            self.colors = {
                "active": {
                    "background": "#a5d8ff",  # Light blue
                    "stroke": "#1971c2",  # Dark blue
                },
                "blocked": {
                    "background": "#ffc9c9",  # Light red
                    "stroke": "#c92a2a",  # Dark red
                },
                "queued": {
                    "background": "#d0ebff",  # Very light blue
                    "stroke": "#4dabf7",  # Medium blue
                },
                "completed": {
                    "background": "#b2f2bb",  # Light green
                    "stroke": "#2f9e44",  # Dark green
                },
            }


def create_rectangle(
    element_id: str,
    x: int,
    y: int,
    width: int,
    height: int,
    background_color: str,
    stroke_color: str,
) -> dict[str, Any]:
    """Create Excalidraw rectangle element.

    Args:
        element_id: Unique element identifier
        x: X coordinate
        y: Y coordinate
        width: Rectangle width
        height: Rectangle height
        background_color: Fill color (hex)
        stroke_color: Border color (hex)

    Returns:
        Dictionary representing Excalidraw rectangle element
    """
    return {
        "id": element_id,
        "type": "rectangle",
        "x": x,
        "y": y,
        "width": width,
        "height": height,
        "angle": 0,
        "strokeColor": stroke_color,
        "backgroundColor": background_color,
        "fillStyle": "solid",
        "strokeWidth": 2,
        "strokeStyle": "solid",
        "roughness": 1,
        "opacity": 100,
        "groupIds": [],
        "roundness": {"type": 3},
        "seed": 1,
        "version": 1,
        "versionNonce": 1,
        "isDeleted": False,
        "boundElements": None,
        "updated": 1,
        "link": None,
        "locked": False,
    }


def create_text(
    element_id: str,
    x: int,
    y: int,
    text: str,
    font_size: int = 20,
    font_family: int = 1,
    text_align: str = "left",
    vertical_align: str = "top",
) -> dict[str, Any]:
    """Create Excalidraw text element.

    Args:
        element_id: Unique element identifier
        x: X coordinate
        y: Y coordinate
        text: Text content
        font_size: Font size in pixels
        font_family: Font family (1=Hand-drawn, 2=Normal, 3=Code)
        text_align: Horizontal alignment
        vertical_align: Vertical alignment

    Returns:
        Dictionary representing Excalidraw text element
    """
    return {
        "id": element_id,
        "type": "text",
        "x": x,
        "y": y,
        "width": 380,  # Approximate width for wrapping
        "height": 25,
        "angle": 0,
        "strokeColor": "#1e1e1e",
        "backgroundColor": "transparent",
        "fillStyle": "solid",
        "strokeWidth": 2,
        "strokeStyle": "solid",
        "roughness": 1,
        "opacity": 100,
        "groupIds": [],
        "roundness": None,
        "seed": 1,
        "version": 1,
        "versionNonce": 1,
        "isDeleted": False,
        "boundElements": None,
        "updated": 1,
        "link": None,
        "locked": False,
        "text": text,
        "fontSize": font_size,
        "fontFamily": font_family,
        "textAlign": text_align,
        "verticalAlign": vertical_align,
        "baseline": 18,
        "containerId": None,
        "originalText": text,
        "lineHeight": 1.25,
    }


def generate_visualization(
    task_data: dict[str, Any], config: LayoutConfig
) -> dict[str, Any]:
    """Generate Excalidraw visualization from task data.

    Args:
        task_data: Structured task data with projects and tasks
        config: Layout configuration

    Returns:
        Complete Excalidraw JSON structure

    Raises:
        ValueError: If task_data is malformed
    """
    if "projects" not in task_data:
        raise ValueError("task_data must contain 'projects' key")

    elements = []
    element_counter = 0
    current_y = config.start_y

    # Generate elements for each project
    for project in task_data["projects"]:
        project_name = project.get("name", "Unknown Project")
        tasks = project.get("tasks", [])

        # Project label
        project_label_id = f"project-label-{element_counter}"
        element_counter += 1

        elements.append(
            create_text(
                element_id=project_label_id,
                x=config.start_x,
                y=current_y,
                text=f"📁 {project_name.upper()}",
                font_size=24,
                font_family=2,  # Normal font for labels
            )
        )

        current_y += config.project_label_height + config.task_vertical_gap

        # Generate task elements
        for task in tasks:
            task_id = task.get("id", f"task-{element_counter}")
            title = task.get("title", "Untitled Task")
            status = task.get("status", "queued")
            priority = task.get("priority", 2)
            blockers = task.get("blockers", [])

            # Get colors for status
            colors = config.colors.get(
                status, {"background": "#e9ecef", "stroke": "#495057"}
            )

            # Create task rectangle
            rect_id = f"rect-{element_counter}"
            element_counter += 1

            elements.append(
                create_rectangle(
                    element_id=rect_id,
                    x=config.start_x,
                    y=current_y,
                    width=config.task_width,
                    height=config.task_height,
                    background_color=colors["background"],
                    stroke_color=colors["stroke"],
                )
            )

            # Create task title text
            text_id = f"text-{element_counter}"
            element_counter += 1

            # Format task text with priority and blockers
            priority_indicator = "!" * priority if priority <= 3 else "!!!"
            blocker_text = f" 🚫 {', '.join(blockers)}" if blockers else ""

            task_text = f"{priority_indicator} {title}{blocker_text}"

            elements.append(
                create_text(
                    element_id=text_id,
                    x=config.start_x + config.task_horizontal_padding,
                    y=current_y + config.task_vertical_padding,
                    text=task_text,
                    font_size=16,
                    font_family=1,  # Hand-drawn font for tasks
                )
            )

            current_y += config.task_height + config.task_vertical_gap

        # Add gap between projects
        current_y += config.project_vertical_gap - config.task_vertical_gap

    # Create complete Excalidraw structure
    return {
        "type": "excalidraw",
        "version": 2,
        "source": "https://excalidraw.com",
        "elements": elements,
        "appState": {
            "gridSize": None,
            "viewBackgroundColor": "#ffffff",
        },
        "files": {},
    }


def main() -> int:
    """Main entry point.

    Returns:
        Exit code (0 for success, 1 for error)
    """
    if len(sys.argv) != 3:
        print("Usage: python generate_task_viz.py input.json output.excalidraw")
        print()
        print("This script transforms structured task data into Excalidraw visualization.")
        print("The agent orchestrates discovery and parsing - this script only does layout.")
        return 1

    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])

    # Validate input exists
    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}", file=sys.stderr)
        return 1

    try:
        # Read input data
        task_data = json.loads(input_path.read_text())

        # Generate visualization
        config = LayoutConfig()
        excalidraw_data = generate_visualization(task_data, config)

        # Write output
        output_path.write_text(json.dumps(excalidraw_data, indent=2))

        print(f"✅ Generated visualization: {output_path}")
        return 0

    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in input file: {e}", file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"Error: Invalid task data structure: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: Failed to generate visualization: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
