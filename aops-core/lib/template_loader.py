"""Template loading utilities for framework hooks and scripts.

Provides a shared function to load .md template files, strip YAML frontmatter,
and optionally interpolate variables. Used by hooks to externalize messages.

Exit behavior: Functions raise exceptions (fail-fast). Callers handle graceful degradation.
"""

from pathlib import Path


def load_template(template_path: Path, variables: dict[str, str] | None = None) -> str:
    """Load template and optionally format with variables.

    Templates are markdown files with optional YAML frontmatter.
    The frontmatter (between opening and closing ---) is stripped.
    Content after frontmatter can use {variable} placeholders.

    Args:
        template_path: Path to .md template file
        variables: Optional dict of variables to interpolate using str.format()

    Returns:
        Template content with frontmatter stripped and variables interpolated

    Raises:
        FileNotFoundError: If template file doesn't exist
        KeyError: If template references variable not in variables dict

    Example:
        >>> content = load_template(Path("hooks/templates/block-message.md"))
        >>> formatted = load_template(
        ...     Path("hooks/templates/instruction.md"),
        ...     {"temp_path": "/tmp/foo.md"}
        ... )
    """
    if not template_path.exists():
        raise FileNotFoundError(f"Template not found: {template_path}")

    content = template_path.read_text()

    # Strip YAML frontmatter if present
    content = _strip_frontmatter(content)

    # Interpolate variables if provided
    if variables:
        content = content.format(**variables)

    return content


def _strip_frontmatter(content: str) -> str:
    """Strip YAML frontmatter from markdown content.

    Handles the standard pattern: ---\\nmetadata\\n---\\ncontent

    Only strips the first frontmatter block. Preserves any --- horizontal
    rules in the content body.

    Args:
        content: Raw markdown content

    Returns:
        Content with frontmatter removed, stripped of leading/trailing whitespace
    """
    if not content.startswith("---"):
        return content.strip()

    # Find the closing --- after the opening one
    # Skip the opening "---" and find the next occurrence
    try:
        first_newline = content.index("\n")
        rest = content[first_newline + 1 :]

        if "\n---\n" in rest:
            # Standard case: frontmatter ends with \n---\n
            closing_idx = rest.index("\n---\n")
            return rest[closing_idx + 5 :].strip()  # Skip \n---\n (5 chars)
        elif "\n---" in rest and rest.rstrip().endswith("---"):
            # Edge case: frontmatter only, no content after
            return ""
        else:
            # No closing frontmatter found - return original
            return content.strip()
    except ValueError:
        # index() failed - malformed, return original
        return content.strip()
