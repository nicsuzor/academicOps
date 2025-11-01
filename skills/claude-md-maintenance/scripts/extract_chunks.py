#!/usr/bin/env python3
"""Extract substantive content from CLAUDE.md files into proper chunks.

This script:
1. Identifies substantive content in CLAUDE.md files
2. Creates appropriate chunk files in the right tier
3. Replaces content with @reference syntax
"""

import os
import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import hashlib

@dataclass
class ContentChunk:
    """Represents content to be extracted to a chunk."""
    original_file: Path
    content: str
    start_line: int
    end_line: int
    chunk_name: str
    target_path: Path
    reference: str

class ChunkExtractor:
    """Extracts substantive content to chunk files."""

    REFERENCE_PATTERN = re.compile(r'@(?:bots/prompts/|references/|\.claude/prompts/)[^\s]+\.md')

    def __init__(self, base_dir: Path):
        """Initialize extractor.
        
        Args:
            base_dir: Root directory to work in
        """
        self.base_dir = Path(base_dir).resolve()
        self.framework_dir = Path(os.environ.get("ACADEMICOPS", "")).resolve() if os.environ.get("ACADEMICOPS") else None
        self.personal_dir = Path(os.environ.get("ACADEMICOPS_PERSONAL", "")).resolve() if os.environ.get("ACADEMICOPS_PERSONAL") else None
        self.chunks_created: List[ContentChunk] = []

    def extract_from_file(self, claude_file: Path, dry_run: bool = False) -> List[ContentChunk]:
        """Extract chunks from a single CLAUDE.md file.
        
        Args:
            claude_file: Path to CLAUDE.md file
            dry_run: If True, don't write files
            
        Returns:
            List of chunks extracted
        """
        content = claude_file.read_text()
        lines = content.splitlines()
        
        # Find substantive content blocks
        chunks = self._identify_chunks(claude_file, lines)
        
        if not dry_run:
            # Create chunk files
            for chunk in chunks:
                self._write_chunk(chunk)
            
            # Update CLAUDE.md with references
            self._update_claude_file(claude_file, chunks)
        
        self.chunks_created.extend(chunks)
        return chunks

    def _identify_chunks(self, file_path: Path, lines: List[str]) -> List[ContentChunk]:
        """Identify content blocks to extract.
        
        Args:
            file_path: Source file path
            lines: File content lines
            
        Returns:
            List of content chunks to extract
        """
        chunks = []
        in_code_block = False
        current_block = []
        block_start = 0
        
        for i, line in enumerate(lines):
            # Track code blocks
            if line.strip().startswith("```"):
                in_code_block = not in_code_block
                if current_block and not in_code_block:
                    # End of code block
                    current_block.append(line)
                    chunk = self._create_chunk(file_path, current_block, block_start, i)
                    if chunk:
                        chunks.append(chunk)
                    current_block = []
                elif in_code_block:
                    block_start = i
                    current_block = [line]
                continue
            
            # Skip references and empty lines
            if self.REFERENCE_PATTERN.search(line) or not line.strip():
                if current_block and not in_code_block:
                    # End of content block
                    chunk = self._create_chunk(file_path, current_block, block_start, i - 1)
                    if chunk:
                        chunks.append(chunk)
                    current_block = []
                continue
            
            # Skip section headers
            if line.strip().startswith("#") and not in_code_block:
                if current_block:
                    chunk = self._create_chunk(file_path, current_block, block_start, i - 1)
                    if chunk:
                        chunks.append(chunk)
                    current_block = []
                continue
            
            # Accumulate content
            if in_code_block or len(line.strip()) > 20:
                if not current_block:
                    block_start = i
                current_block.append(line)
        
        # Check final block
        if current_block:
            chunk = self._create_chunk(file_path, current_block, block_start, len(lines) - 1)
            if chunk:
                chunks.append(chunk)
        
        return chunks

    def _create_chunk(
        self,
        source_file: Path,
        content_lines: List[str],
        start_line: int,
        end_line: int
    ) -> Optional[ContentChunk]:
        """Create a chunk from content lines.
        
        Args:
            source_file: Source CLAUDE.md file
            content_lines: Lines of content
            start_line: Starting line number
            end_line: Ending line number
            
        Returns:
            ContentChunk if worth extracting, None otherwise
        """
        # Skip small blocks
        if len(content_lines) < 4:
            return None
        
        content = "\n".join(content_lines)
        
        # Skip if mostly whitespace
        if len(content.strip()) < 100:
            return None
        
        # Determine chunk name and location
        chunk_name = self._generate_chunk_name(content)
        target_path = self._determine_target_path(source_file, content, chunk_name)
        reference = self._generate_reference(target_path)
        
        return ContentChunk(
            original_file=source_file,
            content=content,
            start_line=start_line,
            end_line=end_line,
            chunk_name=chunk_name,
            target_path=target_path,
            reference=reference
        )

    def _generate_chunk_name(self, content: str) -> str:
        """Generate appropriate chunk name from content.
        
        Args:
            content: Content to analyze
            
        Returns:
            Chunk filename (without .md)
        """
        # Extract key terms for naming
        lower_content = content.lower()
        
        # Common patterns
        if "test" in lower_content and "pytest" in lower_content:
            return "pytest_practices"
        elif "python" in lower_content and "type" in lower_content:
            return "python_typing"
        elif "python" in lower_content:
            return "python_development"
        elif "git" in lower_content and "commit" in lower_content:
            return "git_commit_practices"
        elif "git" in lower_content:
            return "git_workflow"
        elif "docker" in lower_content:
            return "docker_configuration"
        elif "api" in lower_content:
            return "api_guidelines"
        elif "debug" in lower_content:
            return "debugging_workflow"
        elif "config" in lower_content:
            return "configuration_practices"
        else:
            # Generate hash-based name for unique content
            content_hash = hashlib.md5(content.encode()).hexdigest()[:8]
            return f"instructions_{content_hash}"

    def _determine_target_path(self, source_file: Path, content: str, chunk_name: str) -> Path:
        """Determine where to place the chunk file.
        
        Args:
            source_file: Original CLAUDE.md file
            content: Content being extracted
            chunk_name: Name for the chunk
            
        Returns:
            Target path for chunk file
        """
        # Check if project-specific
        project_markers = ["buttermilk", "academicops", self.base_dir.name.lower()]
        is_project_specific = any(marker in content.lower() for marker in project_markers)
        
        # Check if reusable
        reusable_markers = ["python", "test", "git", "docker", "general", "standard", "best practice"]
        is_reusable = any(marker in content.lower() for marker in reusable_markers) and not is_project_specific
        
        if is_project_specific:
            # Project tier
            return self.base_dir / "bots" / "prompts" / f"PROJECT_{chunk_name}.md"
        elif is_reusable and self.framework_dir:
            # Framework tier (if available)
            return self.framework_dir / "bots" / "prompts" / f"{chunk_name}.md"
        elif self.personal_dir:
            # User tier (if available)
            return self.personal_dir / "prompts" / f"{chunk_name}.md"
        else:
            # Default to project tier
            return self.base_dir / "bots" / "prompts" / f"{chunk_name}.md"

    def _generate_reference(self, target_path: Path) -> str:
        """Generate @reference syntax for the chunk.
        
        Args:
            target_path: Path where chunk will be stored
            
        Returns:
            Reference string (e.g., @bots/prompts/chunk.md)
        """
        # If in current project
        if self.base_dir in target_path.parents:
            relative = target_path.relative_to(self.base_dir)
            return f"@{relative.as_posix()}"
        
        # If in framework dir
        if self.framework_dir and self.framework_dir in target_path.parents:
            relative = target_path.relative_to(self.framework_dir)
            return f"@$ACADEMICOPS/{relative.as_posix()}"
        
        # If in personal dir
        if self.personal_dir and self.personal_dir in target_path.parents:
            relative = target_path.relative_to(self.personal_dir)
            return f"@$ACADEMICOPS_PERSONAL/{relative.as_posix()}"
        
        # Fallback
        return f"@{target_path.name}"

    def _write_chunk(self, chunk: ContentChunk) -> None:
        """Write chunk content to file.
        
        Args:
            chunk: Chunk to write
        """
        # Create directory if needed
        chunk.target_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Add header to chunk file
        header = f"""# {chunk.chunk_name.replace('_', ' ').title()}

Extracted from: {chunk.original_file.relative_to(self.base_dir)}

---

"""
        
        # Write content
        full_content = header + chunk.content
        chunk.target_path.write_text(full_content)
        
        print(f"✅ Created chunk: {chunk.target_path}")

    def _update_claude_file(self, claude_file: Path, chunks: List[ContentChunk]) -> None:
        """Update CLAUDE.md file with references.
        
        Args:
            claude_file: File to update
            chunks: Chunks that were extracted
        """
        lines = claude_file.read_text().splitlines()
        new_lines = []
        i = 0
        
        # Sort chunks by start line
        chunks_sorted = sorted(chunks, key=lambda c: c.start_line)
        chunk_idx = 0
        
        while i < len(lines):
            # Check if we're at a chunk start
            if chunk_idx < len(chunks_sorted) and i == chunks_sorted[chunk_idx].start_line:
                chunk = chunks_sorted[chunk_idx]
                # Add reference instead of content
                new_lines.append(chunk.reference)
                # Skip to end of chunk
                i = chunk.end_line + 1
                chunk_idx += 1
            else:
                new_lines.append(lines[i])
                i += 1
        
        # Write updated file
        claude_file.write_text("\n".join(new_lines))
        print(f"✅ Updated {claude_file} with references")

    def print_summary(self) -> None:
        """Print extraction summary."""
        if not self.chunks_created:
            print("\n📋 No chunks extracted")
            return
        
        print(f"\n📋 Extraction Summary:")
        print(f"   Chunks created: {len(self.chunks_created)}")
        
        # Group by target directory
        by_tier: Dict[str, List[ContentChunk]] = {}
        for chunk in self.chunks_created:
            if self.framework_dir and self.framework_dir in chunk.target_path.parents:
                tier = "Framework"
            elif self.personal_dir and self.personal_dir in chunk.target_path.parents:
                tier = "Personal"
            else:
                tier = "Project"
            
            if tier not in by_tier:
                by_tier[tier] = []
            by_tier[tier].append(chunk)
        
        for tier, chunks in by_tier.items():
            print(f"\n   {tier} Tier ({len(chunks)} chunks):")
            for chunk in chunks[:5]:  # Show first 5
                print(f"      - {chunk.chunk_name}")
            if len(chunks) > 5:
                print(f"      ... and {len(chunks) - 5} more")


def main():
    """Main entry point."""
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description="Extract chunks from CLAUDE.md files")
    parser.add_argument("path", nargs="?", default=".", help="Path to CLAUDE.md file or directory")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be extracted without writing files")
    
    args = parser.parse_args()
    
    path = Path(args.path).resolve()
    
    if not path.exists():
        print(f"❌ Path not found: {path}")
        sys.exit(1)
    
    extractor = ChunkExtractor(path.parent if path.is_file() else path)
    
    if path.is_file() and path.name == "CLAUDE.md":
        print(f"📝 Extracting chunks from: {path}")
        chunks = extractor.extract_from_file(path, dry_run=args.dry_run)
    elif path.is_dir():
        print(f"📁 Extracting chunks from CLAUDE.md files in: {path}")
        claude_files = list(path.rglob("CLAUDE.md"))
        for claude_file in claude_files:
            print(f"\n📝 Processing: {claude_file.relative_to(path)}")
            extractor.extract_from_file(claude_file, dry_run=args.dry_run)
    else:
        print(f"❌ Path must be a CLAUDE.md file or directory: {path}")
        sys.exit(1)
    
    extractor.print_summary()


if __name__ == "__main__":
    main()
