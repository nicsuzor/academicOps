#!/usr/bin/env python3
"""Update all hooks to use lib.paths instead of sys.path.insert and Path.cwd()."""

from pathlib import Path
import re

HOOKS_DIR = Path(__file__).parent / "hooks"

# Files to update
FILES_TO_UPDATE = [
    "log_pretooluse.py",
    "log_sessionstart.py",
    "log_subagentstop.py",
    "log_userpromptsubmit.py",
    "autocommit_state.py",
    "extract_session_knowledge.py",
]

def update_hook_file(filepath: Path) -> None:
    """Update a single hook file."""
    content = filepath.read_text()
    original = content

    # Remove sys.path.insert lines
    content = re.sub(
        r'sys\.path\.insert\(0,\s*str\(Path\(__file__\)\.parent\)\)\n',
        '',
        content
    )

    # Update import statement - add hooks. prefix
    content = re.sub(
        r'from session_logger import',
        'from hooks.session_logger import',
        content
    )

    # Replace Path.cwd() in get_project_dir or similar contexts
    content = re.sub(
        r'project_dir = Path\.cwd\(\)',
        'from lib.paths import get_data_root\n        project_dir = get_data_root()',
        content
    )

    # Replace standalone Path.cwd() calls
    content = re.sub(
        r'(\s+)project_dir = Path\.cwd\(\)\n(\s+)while project_dir.*?\n(\s+)if \(project_dir.*?\.git.*?\n(\s+)break\n(\s+)project_dir = project_dir\.parent',
        r'\1project_dir = get_data_root()',
        content,
        flags=re.DOTALL
    )

    # Add lib.paths import if not present
    if 'from lib.paths import' not in content and 'get_data_root' in content:
        # Find the imports section
        import_match = re.search(r'(import \w+\nfrom \w+)', content)
        if import_match:
            content = content.replace(
                import_match.group(0),
                f"{import_match.group(0)}\n\nfrom lib.paths import get_data_root"
            )

    if content != original:
        filepath.write_text(content)
        print(f"✓ Updated {filepath.name}")
    else:
        print(f"- No changes needed for {filepath.name}")

def main():
    """Update all hook files."""
    for filename in FILES_TO_UPDATE:
        filepath = HOOKS_DIR / filename
        if filepath.exists():
            try:
                update_hook_file(filepath)
            except Exception as e:
                print(f"✗ Error updating {filename}: {e}")
        else:
            print(f"✗ File not found: {filename}")

if __name__ == "__main__":
    main()
