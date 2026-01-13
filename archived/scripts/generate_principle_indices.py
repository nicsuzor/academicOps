#!/usr/bin/env python3
"""
AXIOMS.md and HEURISTICS.md are now manually maintained or consolidated via one-off scripts.
This script no longer auto-generates them to prevent overwriting manual refinements.
"""

import sys


def main() -> int:
    print("AXIOMS.md and HEURISTICS.md are now manually maintained.")
    print("Auto-generation has been disabled.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
