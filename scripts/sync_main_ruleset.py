#!/usr/bin/env python3
"""Sync branch protection ruleset for main to GitHub via gh api.

Reads .github/rulesets/main-requires-review.yml and ensures the ruleset
is created and active on nicsuzor/academicOps targeting refs/heads/main.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import yaml

REPO = os.environ.get("REPO", "nicsuzor/academicOps")
RULESET_FILE = (
    Path(__file__).resolve().parent.parent / ".github" / "rulesets" / "main-requires-review.yml"
)


def main() -> int:
    if not RULESET_FILE.exists():
        print(f"ERROR: {RULESET_FILE} does not exist", file=sys.stderr)
        return 1

    with open(RULESET_FILE, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    payload = {
        "name": data["name"],
        "target": data["target"],
        "enforcement": data["enforcement"],
        "conditions": data["conditions"],
        "bypass_actors": data.get("bypass_actors") or [],
        "rules": data.get("rules", []),
    }
    payload_json = json.dumps(payload, indent=2)

    print("Target ruleset payload:")
    print(payload_json)

    # Check existing rulesets
    res = subprocess.run(
        ["gh", "api", f"repos/{REPO}/rulesets"],
        capture_output=True,
        text=True,
    )
    if res.returncode != 0:
        print(
            f"ERROR: Failed to list rulesets (exit {res.returncode}):\n{res.stderr}",
            file=sys.stderr,
        )
        return res.returncode

    rulesets = json.loads(res.stdout)
    existing_id = None
    for r in rulesets:
        # Check if ruleset targets main or matches name
        r_id = r["id"]
        detail_res = subprocess.run(
            ["gh", "api", f"repos/{REPO}/rulesets/{r_id}"],
            capture_output=True,
            text=True,
        )
        if detail_res.returncode == 0:
            detail = json.loads(detail_res.stdout)
            inc = detail.get("conditions", {}).get("ref_name", {}).get("include", [])
            if "refs/heads/main" in inc or detail.get("name") == data["name"]:
                existing_id = r_id
                print(f"Found matching ruleset ID: {existing_id}")
                break

    if existing_id:
        print(f"Updating ruleset {existing_id}...")
        put_res = subprocess.run(
            ["gh", "api", "-X", "PUT", f"repos/{REPO}/rulesets/{existing_id}", "--input", "-"],
            input=payload_json,
            capture_output=True,
            text=True,
        )
        if put_res.returncode != 0:
            print(f"ERROR: Failed to update ruleset:\n{put_res.stderr}", file=sys.stderr)
            return put_res.returncode
        print("Updated ruleset successfully:")
        print(put_res.stdout)
    else:
        print("Creating new ruleset for main...")
        post_res = subprocess.run(
            ["gh", "api", "-X", "POST", f"repos/{REPO}/rulesets", "--input", "-"],
            input=payload_json,
            capture_output=True,
            text=True,
        )
        if post_res.returncode != 0:
            print(f"ERROR: Failed to create ruleset:\n{post_res.stderr}", file=sys.stderr)
            return post_res.returncode
        print("Created ruleset successfully:")
        print(post_res.stdout)

    return 0


if __name__ == "__main__":
    sys.exit(main())
