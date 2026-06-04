#!/usr/bin/env python3
import sys


def main():
    for file in sys.argv[1:]:
        if file.startswith("dist/"):
            print("ERROR: Manual commits to dist/ are prohibited.")
            print(
                "The dist/ folder is automatically generated and committed by the release-please GitHub Action."
            )
            print("Committing dist/ manually causes severe merge conflicts.")
            print("Please unstage these files using: git restore --staged dist/")
            sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
