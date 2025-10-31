#!/usr/bin/env python3
import argparse
import json
import os
import socket
import sys
import uuid
from datetime import datetime


def parse_priority(value: str) -> int:
    """Parse priority value accepting both numeric (0-3) and prefixed (P0-P3) formats.

    Args:
        value: Priority as string - either '0'/'1'/'2'/'3' or 'P0'/'P1'/'P2'/'P3'

    Returns:
        int: Normalized priority value (0-3)

    Raises:
        argparse.ArgumentTypeError: If value is not a valid priority format
    """
    # Handle P-prefixed format (P0, P1, P2, P3)
    if value.upper().startswith('P'):
        try:
            priority_num = int(value[1:])
            if 0 <= priority_num <= 3:
                return priority_num
        except (ValueError, IndexError):
            pass

    # Handle numeric format (0, 1, 2, 3)
    try:
        priority_num = int(value)
        if 0 <= priority_num <= 3:
            return priority_num
    except ValueError:
        pass

    # Invalid format
    raise argparse.ArgumentTypeError(
        f"Invalid priority '{value}'. Valid formats: 0-3 or P0-P3 "
        f"(e.g., '0' or 'P0' for urgent, '1' or 'P1' for high priority)"
    )


def main():
    parser = argparse.ArgumentParser(description="Create a new task.")
    parser.add_argument("--title", required=True, help="The title of the task.")
    parser.add_argument(
        "--priority",
        type=parse_priority,
        help="Priority level: 0-3 or P0-P3 (0/P0=urgent, 1/P1=high, 2/P2=medium, 3/P3=low)"
    )
    parser.add_argument("--type", default="todo", help="Type of the task.")
    parser.add_argument("--project", default="", help="Project slug.")
    parser.add_argument("--due", help="Due date in ISO8601 format.")
    parser.add_argument("--preview", default="", help="A short preview of the task.")

    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--summary",
        "--details",
        dest="summary",
        default="",
        help="A detailed summary of the task.",
    )
    group.add_argument(
        "--details-from-file", help="Path to a file containing the task details."
    )

    parser.add_argument("--metadata", default="{}", help="JSON string for metadata.")

    args = parser.parse_args()

    # If details-from-file is provided, read it
    summary = args.summary
    if args.details_from_file:
        try:
            with open(args.details_from_file) as f:
                summary = f.read()
        except FileNotFoundError:
            print(
                f"Error: File not found for --details-from-file: {args.details_from_file}",
                file=sys.stderr,
            )
            sys.exit(1)

    # Generate ID
    timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    hostname = socket.gethostname().split(".")[0]
    task_uuid = str(uuid.uuid4()).split("-")[0]
    task_id = f"{timestamp}-{hostname}-{task_uuid}"
    created_iso = datetime.utcnow().isoformat() + "Z"

    # Validate and parse metadata
    try:
        metadata_dict = json.loads(args.metadata)
    except json.JSONDecodeError:
        print("Error: --metadata must be a valid JSON string.", file=sys.stderr)
        sys.exit(1)

    # Create task dictionary
    task = {
        "id": task_id,
        "priority": args.priority,
        "type": args.type,
        "title": args.title,
        "preview": args.preview,
        "summary": summary,
        "project": args.project,
        "created": created_iso,
        "due": args.due,
        "source": {},
        "metadata": metadata_dict,
    }

    # Define file path and create directory
    file_path = os.path.join("data", "tasks", "inbox", f"{task_id}.json")
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    # Write JSON to file
    with open(file_path, "w") as f:
        json.dump(task, f, indent=2)

    # Print JSON to stdout
    print(json.dumps(task, indent=2))


if __name__ == "__main__":
    main()
