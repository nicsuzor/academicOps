#!/usr/bin/env python3
"""Refactor CLAUDE.md files to use proper @reference syntax.

This script:
1. Identifies inline instructions that should be references
2. Checks for existing chunks that match content
3. Updates CLAUDE.md files to use @references
4. Consolidates duplicate references
"""

import os
import re
from pathlib import Path
from typing import List, Dict, Set, Optional, Tuple
from dataclasses import dataclass
import difflib

@dataclass
class ReferenceCandidate:
    """Content that could be replaced with a reference."""
    file_path: Path
    line_start: int
    line_end: int
    content: str
    suggested_reference: Optional[str]
    existing_chunk: Optional[Path]

class ReferenceRefactorer:
    """Refactors CLAUDE.md files to use references."""

    REFERENCE_PATTERN = re.compile(r'@(?:bots/prompts/|references/|\.claude/prompts/|\$ACADEMICOPS_[A-Z]+/)[^\s]+\.md')

    def __init__(self, base_dir: Path):
        """Initialize refactorer.
        
        Args:
            base_dir: Root directory to work in
        """
        self.base_dir = Path(base_dir).resolve()
        self.framework_dir = Path(os.environ.get("ACADEMICOPS", "")).resolve() if os.environ.get("ACADEMICOPS") else None
        self.personal_dir = Path(os.environ.get("ACADEMICOPS_PERSONAL", "")).resolve() if os.environ.get("ACADEMICOPS_PERSONAL") else None
        
        # Cache of existing chunks
        self.existing_chunks = self._scan_existing_chunks()

    def _scan_existing_chunks(self) -> Dict[str, Path]:
        """Scan for existing chunk files.
        
        Returns:
            Map of chunk content signatures to paths
        """
        chunks = {}
        
        # Scan project chunks
        project_chunks = self.base_dir / "bots" / "prompts"
        if project_chunks.exists():
            for chunk_file in project_chunks.glob("*.md"):
                content_sig = self._get_content_signature(chunk_file)
                if content_sig:
                    chunks[content_sig] = chunk_file
        
        # Scan framework chunks
        if self.framework_dir:
            framework_chunks = self.framework_dir / "bots" / "prompts"
            if framework_chunks.exists():
                for chunk_file in framework_chunks.glob("*.md"):
                    content_sig = self._get_content_signature(chunk_file)
                    if content_sig:
                        chunks[content_sig] = chunk_file
        
        # Scan personal chunks
        if self.personal_dir:
            personal_chunks = self.personal_dir / "prompts"
            if personal_chunks.exists():
                for chunk_file in personal_chunks.glob("*.md"):
                    content_sig = self._get_content_signature(chunk_file)
                    if content_sig:
                        chunks[content_sig] = chunk_file
        
        return chunks

    def _get_content_signature(self, file_path: Path) -> Optional[str]:
        """Get normalized signature of file content.
        
        Args:
            file_path: Path to file
            
        Returns:
            Normalized content signature
        """
        try:
            content = file_path.read_text()
            # Remove headers and normalize
            lines = [
                line.strip().lower()
                for line in content.splitlines()
                if line.strip() and not line.startswith("#")
            ]
            return " ".join(lines[:10])  # First 10 meaningful lines
        except Exception:
            return None

    def refactor_file(self, claude_file: Path, dry_run: bool = False) -> List[ReferenceCandidate]:
        """Refactor a single CLAUDE.md file.
        
        Args:
            claude_file: Path to CLAUDE.md file
            dry_run: If True, don't write changes
            
        Returns:
            List of reference candidates found
        """
        content = claude_file.read_text()
        lines = content.splitlines()
        
        # Find candidates for refactoring
        candidates = self._find_candidates(claude_file, lines)
        
        # Apply refactoring
        if candidates and not dry_run:
            self._apply_refactoring(claude_file, lines, candidates)
        
        return candidates

    def _find_candidates(self, file_path: Path, lines: List[str]) -> List[ReferenceCandidate]:
        """Find content that could be replaced with references.
        
        Args:
            file_path: Source file
            lines: File content lines
            
        Returns:
            List of reference candidates
        """
        candidates = []
        
        # Look for instruction patterns
        instruction_patterns = [
            r"^[A-Z][A-Z ]+:$",  # ALL CAPS headers
            r"^(Always|Never|Must|Should|Do not|Don't)",  # Imperative starts
            r"^(When|If|Before|After) .+:",  # Conditional instructions
            r"^- (Use|Create|Check|Verify|Ensure)",  # Bulleted instructions
        ]
        
        in_instruction_block = False
        block_start = 0
        current_block = []
        
        for i, line in enumerate(lines):
            # Check if line is a reference already
            if self.REFERENCE_PATTERN.search(line):
                if current_block:
                    # End current block
                    candidate = self._create_candidate(file_path, current_block, block_start, i - 1)
                    if candidate:
                        candidates.append(candidate)
                    current_block = []
                    in_instruction_block = False
                continue
            
            # Check for instruction patterns
            is_instruction = any(re.match(pattern, line.strip()) for pattern in instruction_patterns)
            
            if is_instruction and not in_instruction_block:
                # Start new instruction block
                if current_block:
                    candidate = self._create_candidate(file_path, current_block, block_start, i - 1)
                    if candidate:
                        candidates.append(candidate)
                in_instruction_block = True
                block_start = i
                current_block = [line]
            elif in_instruction_block:
                # Continue or end block
                if line.strip() and not line.strip().startswith("#"):
                    current_block.append(line)
                elif len(current_block) > 2:
                    # End block if substantial
                    candidate = self._create_candidate(file_path, current_block, block_start, i - 1)
                    if candidate:
                        candidates.append(candidate)
                    current_block = []
                    in_instruction_block = False
                else:
                    # Too small, discard
                    current_block = []
                    in_instruction_block = False
        
        # Check final block
        if current_block and len(current_block) > 2:
            candidate = self._create_candidate(file_path, current_block, block_start, len(lines) - 1)
            if candidate:
                candidates.append(candidate)
        
        # Also look for duplicated content across files
        candidates.extend(self._find_duplicate_content(file_path, lines))
        
        return candidates

    def _create_candidate(
        self,
        file_path: Path,
        content_lines: List[str],
        start_line: int,
        end_line: int
    ) -> Optional[ReferenceCandidate]:
        """Create a reference candidate.
        
        Args:
            file_path: Source file
            content_lines: Content to potentially reference
            start_line: Start line number
            end_line: End line number
            
        Returns:
            ReferenceCandidate if applicable
        """
        content = "\n".join(content_lines)
        
        # Check if this matches existing chunk
        content_sig = " ".join([line.strip().lower() for line in content_lines if line.strip()])
        
        best_match = None
        best_score = 0.0
        
        for chunk_sig, chunk_path in self.existing_chunks.items():
            # Calculate similarity
            similarity = difflib.SequenceMatcher(None, content_sig, chunk_sig).ratio()
            if similarity > 0.8 and similarity > best_score:
                best_match = chunk_path
                best_score = similarity
        
        if best_match:
            # Found existing chunk
            reference = self._generate_reference(file_path, best_match)
            return ReferenceCandidate(
                file_path=file_path,
                line_start=start_line,
                line_end=end_line,
                content=content,
                suggested_reference=reference,
                existing_chunk=best_match
            )
        elif len(content_lines) > 5:
            # Suggest creating new chunk
            return ReferenceCandidate(
                file_path=file_path,
                line_start=start_line,
                line_end=end_line,
                content=content,
                suggested_reference=None,
                existing_chunk=None
            )
        
        return None

    def _find_duplicate_content(self, file_path: Path, lines: List[str]) -> List[ReferenceCandidate]:
        """Find content duplicated in other CLAUDE.md files.
        
        Args:
            file_path: Current file
            lines: File content
            
        Returns:
            List of candidates for deduplication
        """
        candidates = []
        
        # This would need access to other CLAUDE.md files
        # For now, returning empty list
        # Full implementation would scan all CLAUDE.md files
        
        return candidates

    def _generate_reference(self, source_file: Path, chunk_file: Path) -> str:
        """Generate appropriate reference syntax.
        
        Args:
            source_file: File containing the reference
            chunk_file: File being referenced
            
        Returns:
            Reference string
        """
        # If chunk is in same repository
        if self.base_dir in chunk_file.parents:
            relative = chunk_file.relative_to(self.base_dir)
            return f"@{relative.as_posix()}"
        
        # If chunk is in framework
        if self.framework_dir and self.framework_dir in chunk_file.parents:
            relative = chunk_file.relative_to(self.framework_dir)
            return f"@$ACADEMICOPS/{relative.as_posix()}"
        
        # If chunk is in personal
        if self.personal_dir and self.personal_dir in chunk_file.parents:
            relative = chunk_file.relative_to(self.personal_dir)
            return f"@$ACADEMICOPS_PERSONAL/{relative.as_posix()}"
        
        return f"@{chunk_file.name}"

    def _apply_refactoring(
        self,
        file_path: Path,
        lines: List[str],
        candidates: List[ReferenceCandidate]
    ) -> None:
        """Apply refactoring to file.
        
        Args:
            file_path: File to update
            lines: Original lines
            candidates: References to apply
        """
        new_lines = []
        i = 0
        
        # Sort candidates by start line
        candidates_sorted = sorted(candidates, key=lambda c: c.line_start)
        candidate_idx = 0
        
        # Track which references we've added
        added_references: Set[str] = set()
        
        while i < len(lines):
            # Check if we're at a candidate start
            if candidate_idx < len(candidates_sorted) and i == candidates_sorted[candidate_idx].line_start:
                candidate = candidates_sorted[candidate_idx]
                
                if candidate.suggested_reference:
                    # Add reference if not already added
                    if candidate.suggested_reference not in added_references:
                        new_lines.append(candidate.suggested_reference)
                        added_references.add(candidate.suggested_reference)
                else:
                    # Keep original content (needs chunk creation first)
                    for j in range(candidate.line_start, candidate.line_end + 1):
                        if j < len(lines):
                            new_lines.append(lines[j])
                
                # Skip to end of candidate
                i = candidate.line_end + 1
                candidate_idx += 1
            else:
                new_lines.append(lines[i])
                i += 1
        
        # Write updated file
        file_path.write_text("\n".join(new_lines))
        print(f"✅ Refactored {file_path}")

    def consolidate_references(self, claude_file: Path, dry_run: bool = False) -> int:
        """Consolidate duplicate references in a file.
        
        Args:
            claude_file: File to consolidate
            dry_run: If True, don't write changes
            
        Returns:
            Number of duplicates removed
        """
        content = claude_file.read_text()
        lines = content.splitlines()
        
        seen_references: Set[str] = set()
        new_lines = []
        duplicates_removed = 0
        
        for line in lines:
            # Check if line is a reference
            ref_match = self.REFERENCE_PATTERN.search(line)
            if ref_match:
                reference = ref_match.group()
                if reference in seen_references:
                    # Skip duplicate
                    duplicates_removed += 1
                    continue
                seen_references.add(reference)
            
            new_lines.append(line)
        
        if duplicates_removed > 0 and not dry_run:
            claude_file.write_text("\n".join(new_lines))
            print(f"✅ Removed {duplicates_removed} duplicate references from {claude_file}")
        
        return duplicates_removed

    def print_report(self, candidates: List[ReferenceCandidate]) -> None:
        """Print refactoring report.
        
        Args:
            candidates: Reference candidates found
        """
        if not candidates:
            print("\n✅ No refactoring needed!")
            return
        
        print(f"\n📋 Found {len(candidates)} refactoring opportunities:\n")
        
        # Group by type
        with_existing = [c for c in candidates if c.existing_chunk]
        need_chunks = [c for c in candidates if not c.existing_chunk]
        
        if with_existing:
            print(f"🔗 Can reference existing chunks ({len(with_existing)}):")
            for candidate in with_existing[:5]:
                print(f"   {candidate.file_path.name}:{candidate.line_start}")
                print(f"      → {candidate.suggested_reference}")
            if len(with_existing) > 5:
                print(f"   ... and {len(with_existing) - 5} more")
        
        if need_chunks:
            print(f"\n📝 Need new chunks created ({len(need_chunks)}):")
            for candidate in need_chunks[:5]:
                print(f"   {candidate.file_path.name}:{candidate.line_start}")
                print(f"      Content: {candidate.content[:80]}...")
            if len(need_chunks) > 5:
                print(f"   ... and {len(need_chunks) - 5} more")


def main():
    """Main entry point."""
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description="Refactor CLAUDE.md files to use references")
    parser.add_argument("path", nargs="?", default=".", help="Path to CLAUDE.md file or directory")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be changed without writing")
    parser.add_argument("--consolidate", action="store_true", help="Consolidate duplicate references")
    
    args = parser.parse_args()
    
    path = Path(args.path).resolve()
    
    if not path.exists():
        print(f"❌ Path not found: {path}")
        sys.exit(1)
    
    refactorer = ReferenceRefactorer(path.parent if path.is_file() else path)
    
    if path.is_file() and path.name == "CLAUDE.md":
        print(f"📝 Refactoring: {path}")
        
        if args.consolidate:
            duplicates = refactorer.consolidate_references(path, dry_run=args.dry_run)
            print(f"   Removed {duplicates} duplicate references")
        
        candidates = refactorer.refactor_file(path, dry_run=args.dry_run)
        refactorer.print_report(candidates)
        
    elif path.is_dir():
        print(f"📁 Refactoring CLAUDE.md files in: {path}")
        claude_files = list(path.rglob("CLAUDE.md"))
        
        all_candidates = []
        for claude_file in claude_files:
            print(f"\n📝 Processing: {claude_file.relative_to(path)}")
            
            if args.consolidate:
                duplicates = refactorer.consolidate_references(claude_file, dry_run=args.dry_run)
                if duplicates:
                    print(f"   Removed {duplicates} duplicate references")
            
            candidates = refactorer.refactor_file(claude_file, dry_run=args.dry_run)
            all_candidates.extend(candidates)
        
        refactorer.print_report(all_candidates)
    else:
        print(f"❌ Path must be a CLAUDE.md file or directory: {path}")
        sys.exit(1)


if __name__ == "__main__":
    main()
