#!/usr/bin/env python3
"""Validate that all @references in CLAUDE.md files resolve correctly.

This script:
1. Scans CLAUDE.md files for @reference syntax
2. Verifies referenced files exist
3. Checks reference paths are correct
4. Reports broken references
"""

import os
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class ReferenceStatus(Enum):
    """Status of a reference."""

    VALID = "valid"
    NOT_FOUND = "not_found"
    INVALID_PATH = "invalid_path"
    CIRCULAR = "circular"
    AMBIGUOUS = "ambiguous"


@dataclass
class Reference:
    """Represents a reference in a CLAUDE.md file."""

    source_file: Path
    line_number: int
    reference_text: str
    target_path: Path | None
    status: ReferenceStatus
    error_message: str | None = None


class ReferenceValidator:
    """Validates references in CLAUDE.md files."""

    # Pattern to match various reference formats
    REFERENCE_PATTERNS = [
        re.compile(r"@(bots/prompts/[^\s]+\.md)"),
        re.compile(r"@(references/[^\s]+\.md)"),
        re.compile(r"@(\.claude/prompts/[^\s]+\.md)"),
        re.compile(r"@(\$ACADEMICOPS/[^\s]+\.md)"),
        re.compile(r"@(\$ACADEMICOPS_PERSONAL/[^\s]+\.md)"),
        re.compile(r"@(\$CLAUDE_PROJECT_DIR/[^\s]+\.md)"),
        re.compile(r"@([^\s]+\.md)"),  # Catch-all for other patterns
    ]

    def __init__(self, base_dir: Path):
        """Initialize validator.

        Args:
            base_dir: Root directory to validate
        """
        self.base_dir = Path(base_dir).resolve()
        self.framework_dir = (
            Path(os.environ.get("ACADEMICOPS", "")).resolve()
            if os.environ.get("ACADEMICOPS")
            else None
        )
        self.personal_dir = (
            Path(os.environ.get("ACADEMICOPS_PERSONAL", "")).resolve()
            if os.environ.get("ACADEMICOPS_PERSONAL")
            else None
        )
        self.project_dir = Path(
            os.environ.get("CLAUDE_PROJECT_DIR", str(self.base_dir))
        ).resolve()

        self.references: list[Reference] = []
        self.valid_count = 0
        self.invalid_count = 0

    def validate_file(self, claude_file: Path) -> list[Reference]:
        """Validate references in a single CLAUDE.md file.

        Args:
            claude_file: Path to CLAUDE.md file

        Returns:
            List of references found and validated
        """
        content = claude_file.read_text()
        lines = content.splitlines()
        file_references = []

        for i, line in enumerate(lines, 1):
            # Find all references in line
            for pattern in self.REFERENCE_PATTERNS:
                for match in pattern.finditer(line):
                    ref_text = match.group(0)
                    ref_path = match.group(1)

                    reference = self._validate_reference(
                        claude_file, i, ref_text, ref_path
                    )
                    file_references.append(reference)
                    self.references.append(reference)

                    if reference.status == ReferenceStatus.VALID:
                        self.valid_count += 1
                    else:
                        self.invalid_count += 1

        return file_references

    def _validate_reference(
        self, source_file: Path, line_number: int, ref_text: str, ref_path: str
    ) -> Reference:
        """Validate a single reference.

        Args:
            source_file: File containing the reference
            line_number: Line number of reference
            ref_text: Full reference text
            ref_path: Path portion of reference

        Returns:
            Validated Reference object
        """
        # Handle environment variable references
        if ref_path.startswith("$"):
            target_path, status, error = self._resolve_env_reference(ref_path)
        else:
            target_path, status, error = self._resolve_relative_reference(
                source_file, ref_path
            )

        # Check for circular references
        if target_path and target_path == source_file:
            status = ReferenceStatus.CIRCULAR
            error = "Reference points to itself"

        return Reference(
            source_file=source_file,
            line_number=line_number,
            reference_text=ref_text,
            target_path=target_path,
            status=status,
            error_message=error,
        )

    def _resolve_env_reference(
        self, ref_path: str
    ) -> tuple[Path | None, ReferenceStatus, str | None]:
        """Resolve reference with environment variable.

        Args:
            ref_path: Reference path with env var

        Returns:
            Tuple of (resolved_path, status, error_message)
        """
        if ref_path.startswith("$ACADEMICOPS/"):
            if not self.framework_dir:
                return None, ReferenceStatus.INVALID_PATH, "$ACADEMICOPS not set"

            relative = ref_path.replace("$ACADEMICOPS/", "")
            target = self.framework_dir / relative

        elif ref_path.startswith("$ACADEMICOPS_PERSONAL/"):
            if not self.personal_dir:
                return (
                    None,
                    ReferenceStatus.INVALID_PATH,
                    "$ACADEMICOPS_PERSONAL not set",
                )

            relative = ref_path.replace("$ACADEMICOPS_PERSONAL/", "")
            target = self.personal_dir / relative

        elif ref_path.startswith("$CLAUDE_PROJECT_DIR/"):
            relative = ref_path.replace("$CLAUDE_PROJECT_DIR/", "")
            target = self.project_dir / relative

        else:
            return (
                None,
                ReferenceStatus.INVALID_PATH,
                f"Unknown environment variable in {ref_path}",
            )

        if target.exists():
            return target, ReferenceStatus.VALID, None
        return target, ReferenceStatus.NOT_FOUND, f"File not found: {target}"

    def _resolve_relative_reference(
        self, source_file: Path, ref_path: str
    ) -> tuple[Path | None, ReferenceStatus, str | None]:
        """Resolve relative reference.

        Args:
            source_file: File containing reference
            ref_path: Relative path

        Returns:
            Tuple of (resolved_path, status, error_message)
        """
        # Try relative to project root first
        target = self.base_dir / ref_path
        if target.exists():
            return target, ReferenceStatus.VALID, None

        # Try relative to source file directory
        target = source_file.parent / ref_path
        if target.exists():
            return target, ReferenceStatus.VALID, None

        # Try common locations
        common_locations = [
            self.base_dir / "bots" / "prompts",
            self.base_dir / ".claude" / "prompts",
            self.base_dir / "references",
        ]

        for location in common_locations:
            if location.exists():
                target = location / Path(ref_path).name
                if target.exists():
                    return target, ReferenceStatus.VALID, None

        return None, ReferenceStatus.NOT_FOUND, f"File not found: {ref_path}"

    def check_circular_references(self) -> list[list[Reference]]:
        """Check for circular reference chains.

        Returns:
            List of circular reference chains found
        """
        circular_chains = []

        # Build reference graph
        reference_graph: dict[Path, set[Path]] = {}

        for ref in self.references:
            if ref.status == ReferenceStatus.VALID and ref.target_path:
                if ref.source_file not in reference_graph:
                    reference_graph[ref.source_file] = set()
                reference_graph[ref.source_file].add(ref.target_path)

        # Check for cycles using DFS
        def find_cycle(
            node: Path, visited: set[Path], path: list[Path]
        ) -> list[Path] | None:
            if node in path:
                # Found cycle
                cycle_start = path.index(node)
                return [*path[cycle_start:], node]

            if node in visited:
                return None

            visited.add(node)
            path.append(node)

            if node in reference_graph:
                for neighbor in reference_graph[node]:
                    cycle = find_cycle(neighbor, visited, path.copy())
                    if cycle:
                        return cycle

            return None

        visited_global: set[Path] = set()

        for start_node in reference_graph:
            if start_node not in visited_global:
                cycle = find_cycle(start_node, visited_global, [])
                if cycle:
                    # Convert paths to references
                    cycle_refs = []
                    for i in range(len(cycle) - 1):
                        # Find reference from cycle[i] to cycle[i+1]
                        for ref in self.references:
                            if (
                                ref.source_file == cycle[i]
                                and ref.target_path == cycle[i + 1]
                            ):
                                cycle_refs.append(ref)
                                break
                    if cycle_refs:
                        circular_chains.append(cycle_refs)

        return circular_chains

    def print_report(self) -> None:
        """Print validation report."""
        print("\n📊 Reference Validation Report")
        print(f"   Total references: {len(self.references)}")
        print(f"   ✅ Valid: {self.valid_count}")
        print(f"   ❌ Invalid: {self.invalid_count}")

        if self.invalid_count == 0:
            print("\n✅ All references are valid!")
            return

        # Group invalid references by type
        by_status: dict[ReferenceStatus, list[Reference]] = {}
        for ref in self.references:
            if ref.status != ReferenceStatus.VALID:
                if ref.status not in by_status:
                    by_status[ref.status] = []
                by_status[ref.status].append(ref)

        # Print invalid references
        for status, refs in by_status.items():
            print(f"\n❌ {status.value.replace('_', ' ').title()} ({len(refs)}):")

            # Group by file
            by_file: dict[Path, list[Reference]] = {}
            for ref in refs:
                if ref.source_file not in by_file:
                    by_file[ref.source_file] = []
                by_file[ref.source_file].append(ref)

            for file_path, file_refs in by_file.items():
                print(f"\n   {file_path.relative_to(self.base_dir)}:")
                for ref in file_refs[:5]:  # Show first 5 per file
                    print(f"      Line {ref.line_number}: {ref.reference_text}")
                    if ref.error_message:
                        print(f"         → {ref.error_message}")
                if len(file_refs) > 5:
                    print(f"      ... and {len(file_refs) - 5} more")

        # Check for circular references
        circular_chains = self.check_circular_references()
        if circular_chains:
            print(f"\n🔄 Circular References Found ({len(circular_chains)} chains):")
            for i, chain in enumerate(circular_chains, 1):
                print(f"\n   Chain {i}:")
                for ref in chain:
                    print(
                        f"      {ref.source_file.name} → {ref.target_path.name if ref.target_path else 'unknown'}"
                    )

    def suggest_fixes(self) -> None:
        """Suggest fixes for invalid references."""
        invalid_refs = [r for r in self.references if r.status != ReferenceStatus.VALID]

        if not invalid_refs:
            return

        print("\n💡 Suggested Fixes:")

        # Group by error type
        not_found = [r for r in invalid_refs if r.status == ReferenceStatus.NOT_FOUND]

        if not_found:
            print("\n   For missing files:")
            # Find potential matches
            all_md_files = list(self.base_dir.rglob("*.md"))

            for ref in not_found[:5]:  # Show fixes for first 5
                ref_name = Path(ref.reference_text.replace("@", "")).name

                # Find files with similar names
                matches = [
                    f for f in all_md_files if ref_name.lower() in f.name.lower()
                ]

                if matches:
                    print(
                        f"\n      {ref.reference_text} in {ref.source_file.name}:{ref.line_number}"
                    )
                    print("         Possible matches:")
                    for match in matches[:3]:
                        relative = match.relative_to(self.base_dir)
                        print(f"            @{relative}")


def main():
    """Main entry point."""
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        description="Validate references in CLAUDE.md files"
    )
    parser.add_argument(
        "path", nargs="?", default=".", help="Path to CLAUDE.md file or directory"
    )
    parser.add_argument("--fix", action="store_true", help="Show suggested fixes")

    args = parser.parse_args()

    path = Path(args.path).resolve()

    if not path.exists():
        print(f"❌ Path not found: {path}")
        sys.exit(1)

    validator = ReferenceValidator(path.parent if path.is_file() else path)

    if path.is_file() and path.name == "CLAUDE.md":
        print(f"🔍 Validating references in: {path}")
        validator.validate_file(path)
    elif path.is_dir():
        print(f"🔍 Validating references in CLAUDE.md files under: {path}")
        claude_files = list(path.rglob("CLAUDE.md"))

        if not claude_files:
            print("   No CLAUDE.md files found")
            sys.exit(0)

        for claude_file in claude_files:
            print(f"   Checking: {claude_file.relative_to(path)}")
            validator.validate_file(claude_file)
    else:
        print(f"❌ Path must be a CLAUDE.md file or directory: {path}")
        sys.exit(1)

    validator.print_report()

    if args.fix:
        validator.suggest_fixes()

    # Exit with error if invalid references found
    sys.exit(1 if validator.invalid_count > 0 else 0)


if __name__ == "__main__":
    main()
