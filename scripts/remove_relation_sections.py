#!/usr/bin/env python3
"""Remove Relations/References/See Also/Related sections from markdown files.

Per H7b: Links belong inline in prose, not in metadata sections.
"""

import re
import sys
from pathlib import Path


def remove_relation_sections(content: str) -> tuple[str, list[str]]:
    """Remove relation-type sections from markdown content.

    Returns tuple of (cleaned_content, list_of_removed_sections).
    """
    # Pattern matches ## Relations, ## References, ## See Also, ## Related, ## Cross-References
    # and captures everything until the next ## heading or end of file
    pattern = r'^## (?:Relations|References|See Also|Related|Cross-References)\s*\n(?:(?!^## ).*\n?)*'

    removed = []

    def track_removal(match):
        removed.append(match.group(0).strip())
        return ''

    cleaned = re.sub(pattern, track_removal, content, flags=re.MULTILINE)

    # Clean up multiple consecutive blank lines left behind
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)

    # Remove trailing whitespace
    cleaned = cleaned.rstrip() + '\n'

    return cleaned, removed


def process_file(filepath: Path, dry_run: bool = False) -> bool:
    """Process a single file. Returns True if file was modified."""
    try:
        content = filepath.read_text(encoding='utf-8')
    except Exception as e:
        print(f"ERROR reading {filepath}: {e}", file=sys.stderr)
        return False

    cleaned, removed = remove_relation_sections(content)

    if not removed:
        return False

    if dry_run:
        print(f"WOULD MODIFY: {filepath}")
        for section in removed:
            # Show first line of each removed section
            first_line = section.split('\n')[0]
            print(f"  - {first_line}")
    else:
        filepath.write_text(cleaned, encoding='utf-8')
        print(f"MODIFIED: {filepath}")
        for section in removed:
            first_line = section.split('\n')[0]
            print(f"  - {first_line}")

    return True


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Remove relation sections from markdown files')
    parser.add_argument('paths', nargs='+', help='Files or directories to process')
    parser.add_argument('--dry-run', '-n', action='store_true', help='Show what would be done without making changes')
    parser.add_argument('--recursive', '-r', action='store_true', help='Process directories recursively')
    args = parser.parse_args()

    files_to_process = []

    for path_str in args.paths:
        path = Path(path_str)
        if path.is_file() and path.suffix == '.md':
            files_to_process.append(path)
        elif path.is_dir():
            if args.recursive:
                files_to_process.extend(path.rglob('*.md'))
            else:
                files_to_process.extend(path.glob('*.md'))

    modified_count = 0
    for filepath in files_to_process:
        if process_file(filepath, dry_run=args.dry_run):
            modified_count += 1

    action = "Would modify" if args.dry_run else "Modified"
    print(f"\n{action} {modified_count} files out of {len(files_to_process)} scanned.")


if __name__ == '__main__':
    main()
