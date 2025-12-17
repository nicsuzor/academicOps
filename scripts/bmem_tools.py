#!/usr/bin/env python3
"""
Basic Memory (bmem) Format Tools

Validation and conversion utilities for bmem-formatted markdown files.
"""

import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

import yaml


@dataclass
class ValidationError:
    """Represents a validation error in a bmem file."""

    file: Path
    line: int | None
    message: str
    severity: str  # 'error' or 'warning'

    def __str__(self):
        location = f"{self.file}:{self.line}" if self.line else str(self.file)
        return f"{self.severity.upper()}: {location}: {self.message}"


class BmemValidator:
    """Validates markdown files against bmem format specification."""

    # Directories that MUST use bmem format
    REQUIRED_BMEM_DIRS: ClassVar[list[str]] = [
        "data/context",
        "data/goals",
        "data/projects",
        "data/playbooks",
        "data/tasks/inbox",
        "data/tasks/completed",
    ]

    # Files/patterns exempt from bmem requirements
    EXEMPT_PATTERNS: ClassVar[list[str]] = [
        "**/README.md",
        "papers/**",
        "reviews/**",
        "talks/**",
        "templates/**",
        "data/tasks/archived/**",  # Archived tasks may have old format
    ]

    # Valid observation categories
    # Note: This is not exhaustive - unknown categories generate warnings not errors
    VALID_CATEGORIES: ClassVar[set[str]] = {
        "fact",
        "idea",
        "decision",
        "technique",
        "requirement",
        "question",
        "insight",
        "problem",
        "solution",
        "action",
        "goal",
        "strategy",
        "challenge",
        "task",
        "classification",
        "recommendation",
        "feature",
        "plan",
        "lesson-learned",
        "risk",
        "principle",
        "audience",
        "message",
        "focus",
        "priority",
        "outcome",
        "metric",
        "deadline",
        "constraint",
        "approach",
        "architecture",
        "framework",
        "design",
        "tool",
        "benefit",
        "blocker",
        "concern",
        "consideration",
        "opportunity",
        "milestone",
        "timeline",
        "allocation",
        "strategic",
        "assessment",
        "purpose",
        "philosophy",
        "pattern",
        "structure",
        "relationship",
        "value",
        "capability",
        "collaboration",
        "competitive-advantage",
        "deliverable",
        "event",
        "format",
        "need",
        "positioning",
        "topic",
        "transition",
        "urgent",
        "advantage",
        "categorization",
        "category",
        "contact",
        "metrics",
        "mitigations",
        "risks",
        "completed",
        "audience-tailoring",
    }

    # Valid relation types
    VALID_RELATIONS: ClassVar[set[str]] = {
        "relates_to",
        "implements",
        "requires",
        "extends",
        "part_of",
        "supports",
        "contrasts_with",
        "caused_by",
        "leads_to",
        "similar_to",
        "incorporates_lessons_from",
        "underpins",
        "defines_allocation_for",
        "builds_on",
        "references",
        "follows_up",
        "affects",
        "replaces",
        "depends_on",
        "includes",
        "monitored_by",
        "deployed_to",
        "integrates_with",
        "blocked_by",
        "built_on",
        "built_with",
        "continuation_of",
        "continues",
        "enabled_by",
        "enables",
        "informed",
        "informs",
        "shares_architecture_with",
        "supported_by",
        "tracks_progress_for",
        "uses_architecture_from",
        "visualizes",
    }

    def __init__(self, repo_root: Path):
        self.repo_root = Path(repo_root).resolve()
        self.errors: list[ValidationError] = []

    def should_validate(self, file_path: Path) -> bool:
        """Check if file should be validated for bmem format."""
        file_path = file_path.resolve()
        rel_path = file_path.relative_to(self.repo_root)

        # Check if exempt
        for pattern in self.EXEMPT_PATTERNS:
            if rel_path.match(pattern):
                return False

        # Check if in required directory
        for req_dir in self.REQUIRED_BMEM_DIRS:
            if str(rel_path).startswith(req_dir):
                return True

        return False

    def validate_file(self, file_path: Path) -> list[ValidationError]:
        """Validate a single markdown file."""
        self.errors = []

        if not file_path.exists():
            self.errors.append(
                ValidationError(
                    file=file_path,
                    line=None,
                    message="File does not exist",
                    severity="error",
                )
            )
            return self.errors

        content = file_path.read_text()
        lines = content.split("\n")

        # Check for frontmatter
        frontmatter, fm_end_line = self._extract_frontmatter(lines)
        if frontmatter is None:
            self.errors.append(
                ValidationError(
                    file=file_path,
                    line=1,
                    message="Missing YAML frontmatter",
                    severity="error",
                )
            )
            return self.errors

        # Validate frontmatter fields
        self._validate_frontmatter(file_path, frontmatter)

        # Find sections
        sections = self._find_sections(lines[fm_end_line:], fm_end_line)

        # Validate title consistency
        h1_line = self._find_first_h1(lines[fm_end_line:])
        if h1_line and frontmatter.get("title"):
            h1_text = lines[fm_end_line + h1_line].lstrip("#").strip()
            if h1_text != frontmatter["title"]:
                self.errors.append(
                    ValidationError(
                        file=file_path,
                        line=fm_end_line + h1_line + 1,
                        message=f"H1 heading '{h1_text}' doesn't match frontmatter title '{frontmatter['title']}'",
                        severity="error",
                    )
                )

        # Validate Observations section
        if "Observations" not in sections:
            self.errors.append(
                ValidationError(
                    file=file_path,
                    line=None,
                    message="Missing ## Observations section",
                    severity="warning",
                )
            )
        else:
            self._validate_observations(file_path, lines, sections["Observations"])

        # Validate Relations section
        if "Relations" not in sections:
            self.errors.append(
                ValidationError(
                    file=file_path,
                    line=None,
                    message="Missing ## Relations section",
                    severity="warning",
                )
            )
        else:
            self._validate_relations(file_path, lines, sections["Relations"])

        return self.errors

    def _extract_frontmatter(self, lines: list[str]) -> tuple[dict | None, int]:
        """Extract YAML frontmatter from lines."""
        if not lines or lines[0].strip() != "---":
            return None, 0

        end_idx = None
        for i, line in enumerate(lines[1:], 1):
            if line.strip() == "---":
                end_idx = i
                break

        if end_idx is None:
            return None, 0

        try:
            fm_text = "\n".join(lines[1:end_idx])
            frontmatter = yaml.safe_load(fm_text) or {}
            return frontmatter, end_idx + 1
        except yaml.YAMLError:
            return {}, end_idx + 1

    def _validate_frontmatter(self, file_path: Path, fm: dict):
        """Validate frontmatter fields."""
        required = ["title", "type", "tags"]

        for field in required:
            if field not in fm:
                self.errors.append(
                    ValidationError(
                        file=file_path,
                        line=None,
                        message=f"Missing required frontmatter field: {field}",
                        severity="error",
                    )
                )

        # Validate permalink if present
        if "permalink" in fm:
            permalink = fm["permalink"]
            if permalink and not re.match(r"^[a-z0-9-]+$", permalink):
                self.errors.append(
                    ValidationError(
                        file=file_path,
                        line=None,
                        message=f"Invalid permalink '{permalink}' - must be lowercase alphanumeric with hyphens",
                        severity="error",
                    )
                )
            elif not permalink:
                self.errors.append(
                    ValidationError(
                        file=file_path,
                        line=None,
                        message="Permalink field is empty",
                        severity="warning",
                    )
                )

        # Validate tags
        if "tags" in fm and (not isinstance(fm["tags"], list) or len(fm["tags"]) == 0):
            self.errors.append(
                ValidationError(
                    file=file_path,
                    line=None,
                    message="Tags must be a non-empty list",
                    severity="warning",
                )
            )

    def _find_sections(self, lines: list[str], offset: int) -> dict[str, int]:
        """Find section headings (## Heading) in content."""
        sections = {}
        for i, line in enumerate(lines):
            if line.startswith("## "):
                heading = line[3:].strip()
                sections[heading] = i + offset
        return sections

    def _find_first_h1(self, lines: list[str]) -> int | None:
        """Find first H1 heading."""
        for i, line in enumerate(lines):
            if line.startswith("# ") and not line.startswith("## "):
                return i
        return None

    def _validate_observations(
        self, file_path: Path, lines: list[str], start_line: int
    ):
        """Validate Observations section."""
        # Find observations (list items after ## Observations)
        i = start_line + 1
        found_observations = False

        while i < len(lines):
            line = lines[i].strip()

            # Stop at next section
            if line.startswith("## "):
                break

            # Check for observation syntax
            if line.startswith("- ["):
                found_observations = True
                match = re.match(r"^- \[([a-z-]+)\] (.+)", line)
                if not match:
                    self.errors.append(
                        ValidationError(
                            file=file_path,
                            line=i + 1,
                            message=f"Invalid observation syntax: {line}",
                            severity="error",
                        )
                    )
                else:
                    category = match.group(1)
                    if category not in self.VALID_CATEGORIES:
                        self.errors.append(
                            ValidationError(
                                file=file_path,
                                line=i + 1,
                                message=f"Unknown observation category: [{category}]",
                                severity="warning",
                            )
                        )

            i += 1

        if not found_observations:
            self.errors.append(
                ValidationError(
                    file=file_path,
                    line=start_line + 1,
                    message="Observations section is empty",
                    severity="warning",
                )
            )

    def _validate_relations(self, file_path: Path, lines: list[str], start_line: int):
        """Validate Relations section."""
        i = start_line + 1
        found_relations = False

        while i < len(lines):
            line = lines[i].strip()

            # Stop at next section
            if line.startswith("## "):
                break

            # Check for relation syntax
            if line.startswith("- "):
                found_relations = True
                match = re.match(r"^- ([a-z_]+) \[\[(.+)\]\]", line)
                if not match:
                    self.errors.append(
                        ValidationError(
                            file=file_path,
                            line=i + 1,
                            message=f"Invalid relation syntax: {line}",
                            severity="error",
                        )
                    )
                else:
                    relation_type = match.group(1)
                    if relation_type not in self.VALID_RELATIONS:
                        self.errors.append(
                            ValidationError(
                                file=file_path,
                                line=i + 1,
                                message=f"Unknown relation type: {relation_type}",
                                severity="warning",
                            )
                        )

            i += 1

        if not found_relations:
            self.errors.append(
                ValidationError(
                    file=file_path,
                    line=start_line + 1,
                    message="Relations section is empty",
                    severity="warning",
                )
            )


class BmemConverter:
    """Converts existing markdown files to bmem format."""

    def __init__(self, repo_root: Path):
        self.repo_root = Path(repo_root).resolve()

    def convert_file(self, file_path: Path, dry_run: bool = True) -> str | None:
        """
        Convert a markdown file to bmem format.

        Args:
            file_path: Path to markdown file
            dry_run: If True, return converted content without writing

        Returns:
            Converted content if successful, None otherwise
        """
        if not file_path.exists():
            return None

        content = file_path.read_text()

        # Check if already has frontmatter
        if content.startswith("---\n"):
            # Already has frontmatter, may just need structure additions
            return self._enhance_existing(content, file_path)

        # Generate frontmatter
        title = self._extract_title(content, file_path)
        permalink = self._generate_permalink(title)

        frontmatter = {
            "title": title,
            "permalink": permalink,
            "type": "note",
            "tags": [],
        }

        # Build bmem structure
        result = self._build_bmem_structure(frontmatter, content)

        if not dry_run:
            file_path.write_text(result)

        return result

    def _extract_title(self, content: str, file_path: Path) -> str:
        """Extract title from content or filename."""
        # Look for first H1
        match = re.search(r"^# (.+)$", content, re.MULTILINE)
        if match:
            return match.group(1).strip()

        # Use filename
        return file_path.stem.replace("-", " ").replace("_", " ").title()

    def _generate_permalink(self, title: str) -> str:
        """Generate URL-safe permalink from title."""
        permalink = title.lower()
        permalink = re.sub(r"[^a-z0-9\s-]", "", permalink)
        return re.sub(r"\s+", "-", permalink)

    def _enhance_existing(self, content: str, _file_path: Path) -> str:
        """Enhance existing frontmatter file with bmem structure."""
        # For files that already have frontmatter, just ensure sections exist
        if "## Observations" not in content:
            # Add placeholder Observations section before Relations or at end
            if "## Relations" in content:
                content = content.replace(
                    "## Relations", "## Observations\n\n- [fact] \n\n## Relations"
                )
            else:
                content += "\n## Observations\n\n- [fact] \n"

        if "## Relations" not in content:
            content += "\n## Relations\n\n- relates_to [[]]\n"

        return content

    def _build_bmem_structure(self, frontmatter: dict, content: str) -> str:
        """Build complete bmem-formatted content."""
        # Build frontmatter
        fm_lines = ["---"]
        for key, value in frontmatter.items():
            if isinstance(value, list):
                fm_lines.append(f"{key}:")
                for item in value:
                    fm_lines.append(f"  - {item}")
            else:
                fm_lines.append(f"{key}: {value}")
        fm_lines.append("---")
        fm_lines.append("")

        # Extract or create title
        title = frontmatter["title"]
        if not content.startswith(f"# {title}"):
            fm_lines.append(f"# {title}")
            fm_lines.append("")

        # Add Context section if not present
        if "## Context" not in content:
            fm_lines.append("## Context")
            fm_lines.append("")
            fm_lines.append("TODO: Add context")
            fm_lines.append("")

        # Add content
        fm_lines.append(content)
        fm_lines.append("")

        # Add Observations section
        fm_lines.append("## Observations")
        fm_lines.append("")
        fm_lines.append("- [fact] TODO: Add observations")
        fm_lines.append("")

        # Add Relations section
        fm_lines.append("## Relations")
        fm_lines.append("")
        fm_lines.append("- relates_to [[]]")
        fm_lines.append("")

        return "\n".join(fm_lines)


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="bmem format tools")
    parser.add_argument(
        "command", choices=["validate", "convert"], help="Command to run"
    )
    parser.add_argument(
        "files", nargs="*", help="Files to process (default: all in data/)"
    )
    parser.add_argument("--repo-root", default=".", help="Repository root directory")
    parser.add_argument(
        "--strict", action="store_true", help="Treat warnings as errors"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Show changes without writing"
    )

    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()

    if args.command == "validate":
        validator = BmemValidator(repo_root)

        # Find files to validate
        if args.files:
            files = [Path(f) for f in args.files]
        else:
            files = list(repo_root.glob("data/**/*.md"))

        all_errors = []
        for file_path in files:
            if not validator.should_validate(file_path):
                continue

            errors = validator.validate_file(file_path)
            all_errors.extend(errors)

        # Print results
        has_errors = False
        for error in all_errors:
            try:
                file_display = error.file.relative_to(repo_root)
            except ValueError:
                file_display = error.file
            print(
                f"{error.severity.upper()}: {file_display}:{error.line or ''} {error.message}"
            )
            if error.severity == "error" or (
                args.strict and error.severity == "warning"
            ):
                has_errors = True

        if has_errors:
            sys.exit(1)
        else:
            print(f"✓ Validated {len(files)} files")
            sys.exit(0)

    elif args.command == "convert":
        converter = BmemConverter(repo_root)

        # Find files to convert
        if args.files:
            files = [Path(f) for f in args.files]
        else:
            print("Error: Must specify files to convert", file=sys.stderr)
            sys.exit(1)

        for file_path in files:
            print(f"Converting {file_path.relative_to(repo_root)}...")
            result = converter.convert_file(file_path, dry_run=args.dry_run)

            if args.dry_run:
                print(result)
                print("---")


if __name__ == "__main__":
    main()
