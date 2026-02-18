#!/usr/bin/env python3
"""
Assessment tool for gate agent inputs (v1.1).

This script processes samples collected via AOPS_SAMPLE_INPUTS=1
and facilitates human/agent assessment of whether the agents
(hydrator, custodiet, qa) had sufficient information.

Note:
    Uses lib.paths.get_data_root() for canonical path resolution.
"""

import json
import sys
from pathlib import Path

# Add aops-core to path for lib imports
SCRIPT_DIR = Path(__file__).parent.resolve()
AOPS_CORE_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(AOPS_CORE_ROOT))

from lib.paths import get_data_root


def list_samples(category=None):
    try:
        data_root = get_data_root()
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    sample_root = data_root / "samples" / "v1.1"
    if not sample_root.exists():
        print(f"No samples found at {sample_root}")
        return []

    categories = [category] if category else [d.name for d in sample_root.iterdir() if d.is_dir()]

    samples = []
    for cat in categories:
        cat_dir = sample_root / cat
        for meta_file in cat_dir.glob("*.json"):
            try:
                with open(meta_file) as f:
                    meta = json.load(f)

                content_file = meta_file.with_suffix(".md")
                if content_file.exists():
                    samples.append(
                        {
                            "id": meta_file.stem,
                            "category": cat,
                            "timestamp": meta.get("timestamp"),
                            "session_id": meta.get("session_id"),
                            "metadata": meta.get("metadata", {}),
                            "content_path": content_file,
                            "meta_path": meta_file,
                        }
                    )
            except Exception as e:
                print(f"Error loading sample {meta_file}: {e}")

    return sorted(samples, key=lambda x: x["timestamp"], reverse=True)


def assess_sample(sample):
    print(f"{'=' * 80}")
    print(f"ASSESSING SAMPLE: {sample['id']}")
    print(f"Category:  {sample['category']}")
    print(f"Session:   {sample['session_id']}")
    print(f"Timestamp: {sample['timestamp']}")
    print(f"{'=' * 80}")

    # Show metadata context
    if sample["category"] == "hydrator":
        print(f"USER PROMPT: {sample['metadata'].get('prompt')}")
    elif sample["category"] == "custodiet":
        print(f"TRIGGER TOOL: {sample['metadata'].get('tool_name')}")

    print(f"Input context file: {sample['content_path']}")
    print(f"{'-' * 40}")

    # Quick peek at content
    with open(sample["content_path"]) as f:
        lines = f.readlines()
        print("Content Preview (first 20 lines):")
        for line in lines[:20]:
            print(f"  {line.rstrip()}")

    print(f"{'-' * 40}")

    # Assessment questions
    print("ASSESSMENT QUESTIONS:")
    print("1. Did the agent have the necessary project-specific paths?")
    print("2. Were the relevant AXIOMS/HEURISTICS selected/available?")
    print("3. Was the session history sufficient for this turn?")
    print("4. Any critical information missing?")

    # In a real CLI tool, we'd take input here.
    # For now, this script serves as the infrastructure for assessment.


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "list":
        samples = list_samples()
        print(f"Found {len(samples)} samples:")
        for s in samples:
            print(f"[{s['timestamp']}] {s['category']:<10} {s['session_id'][:8]} {s['id']}")
    elif len(sys.argv) > 2 and sys.argv[1] == "show":
        samples = list_samples()
        target = sys.argv[2]
        sample = next((s for s in samples if s["id"] == target), None)
        if sample:
            assess_sample(sample)
        else:
            print(f"Sample {target} not found.")
    else:
        print("Usage:")
        print("  assess_samples.py list")
        print("  assess_samples.py show <sample_id>")


if __name__ == "__main__":
    main()
