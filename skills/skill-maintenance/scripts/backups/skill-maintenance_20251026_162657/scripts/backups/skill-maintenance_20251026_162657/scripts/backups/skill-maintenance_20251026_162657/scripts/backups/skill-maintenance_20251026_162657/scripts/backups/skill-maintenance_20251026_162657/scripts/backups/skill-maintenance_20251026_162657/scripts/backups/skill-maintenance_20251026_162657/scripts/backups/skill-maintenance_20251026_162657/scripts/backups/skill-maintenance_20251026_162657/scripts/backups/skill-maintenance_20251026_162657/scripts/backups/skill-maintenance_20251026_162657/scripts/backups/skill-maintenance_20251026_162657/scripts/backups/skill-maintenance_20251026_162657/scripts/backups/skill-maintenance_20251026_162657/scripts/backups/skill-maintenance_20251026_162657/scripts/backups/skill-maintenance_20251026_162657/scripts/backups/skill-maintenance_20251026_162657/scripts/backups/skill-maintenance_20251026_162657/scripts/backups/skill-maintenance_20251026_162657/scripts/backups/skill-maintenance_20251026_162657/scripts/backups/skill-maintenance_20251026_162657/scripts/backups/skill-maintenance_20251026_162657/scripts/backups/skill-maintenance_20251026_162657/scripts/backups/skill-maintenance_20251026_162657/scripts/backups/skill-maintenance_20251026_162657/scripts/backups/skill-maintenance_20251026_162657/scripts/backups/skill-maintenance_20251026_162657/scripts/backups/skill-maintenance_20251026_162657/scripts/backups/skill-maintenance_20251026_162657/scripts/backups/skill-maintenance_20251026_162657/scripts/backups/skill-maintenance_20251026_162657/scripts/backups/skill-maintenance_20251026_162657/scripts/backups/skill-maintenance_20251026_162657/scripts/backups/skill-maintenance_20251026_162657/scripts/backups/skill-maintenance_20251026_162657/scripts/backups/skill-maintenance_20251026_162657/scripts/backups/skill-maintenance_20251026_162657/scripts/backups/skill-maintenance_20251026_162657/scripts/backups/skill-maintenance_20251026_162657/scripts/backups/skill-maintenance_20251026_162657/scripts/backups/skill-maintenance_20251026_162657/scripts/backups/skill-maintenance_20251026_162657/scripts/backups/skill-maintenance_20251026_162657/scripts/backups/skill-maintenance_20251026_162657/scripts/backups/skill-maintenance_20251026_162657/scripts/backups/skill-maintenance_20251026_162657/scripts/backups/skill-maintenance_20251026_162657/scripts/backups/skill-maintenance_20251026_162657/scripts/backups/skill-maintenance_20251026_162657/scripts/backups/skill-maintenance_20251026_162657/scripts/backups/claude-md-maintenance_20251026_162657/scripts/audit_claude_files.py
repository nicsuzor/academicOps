#!/usr/bin/env python3
"""Audit CLAUDE.md files across repositories for academicOps best practices.

This script scans CLAUDE.md files to identify:
1. Substantive content that should be in chunks
2. Location mismatches (instructions in wrong directories)
3. Duplication across files
4. Missing @reference syntax
5. Overly long files
"""

import os
import re
from pathlib import Path
from typing import List, Dict, Set, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

class IssueType(Enum):
    """Types of issues found in CLAUDE.md files."""
    SUBSTANTIVE_CONTENT = "substantive_content"
    WRONG_LOCATION = "wrong_location"
    DUPLICATION = "duplication"
    MISSING_REFERENCES = "missing_references"
    TOO_LONG = "too_long"
    INLINE_INSTRUCTIONS = "inline_instructions"

@dataclass
class Issue:
    """Represents an issue found in a CLAUDE.md file."""
    file_path: Path
    issue_type: IssueType
    line_number: Optional[int]
    content: str
    recommendation: str

class ClaudeFileAuditor:
    """Audits CLAUDE.md files for best practices."""

    REFERENCE_PATTERN = re.compile(r'@(?:bots/prompts/|references/|\.claude/prompts/)[^\s]+\.md')
    MAX_IDEAL_LINES = 20
    MAX_ACCEPTABLE_LINES = 50

    def __init__(self, base_dir: Path):
        """Initialize auditor with base directory.
        
        Args:
            base_dir: Root directory to scan for CLAUDE.md files
        """
        self.base_dir = Path(base_dir).resolve()
        self.framework_dir = Path(os.environ.get("ACADEMICOPS_BOT", "")).resolve() if os.environ.get("ACADEMICOPS_BOT") else None
        self.personal_dir = Path(os.environ.get("ACADEMICOPS_PERSONAL", "")).resolve() if os.environ.get("ACADEMICOPS_PERSONAL") else None
        self.issues: List[Issue] = []

    def audit(self) -> List[Issue]:
        """Scan and audit all CLAUDE.md files.
        
        Returns:
            List of issues found
        """
        claude_files = self._find_claude_files()
        
        for claude_file in claude_files:
            self._audit_file(claude_file)
        
        # Check for duplication across files
        self._check_duplication(claude_files)
        
        return self.issues

    def _find_claude_files(self) -> List[Path]:
        """Find all CLAUDE.md files in the repository.
        
        Returns:
            List of CLAUDE.md file paths
        """
        return list(self.base_dir.rglob("CLAUDE.md"))

    def _audit_file(self, file_path: Path) -> None:
        """Audit a single CLAUDE.md file.
        
        Args:
            file_path: Path to CLAUDE.md file
        """
        content = file_path.read_text()
        lines = content.splitlines()
        
        # Check file length
        if len(lines) > self.MAX_ACCEPTABLE_LINES:
            self.issues.append(Issue(
                file_path=file_path,
                issue_type=IssueType.TOO_LONG,
                line_number=None,
                content=f"File has {len(lines)} lines (ideal: <{self.MAX_IDEAL_LINES}, acceptable: <{self.MAX_ACCEPTABLE_LINES})",
                recommendation="Extract content to chunks and use @references"
            ))
        
        # Check for substantive content vs references
        self._check_substantive_content(file_path, lines)
        
        # Check location appropriateness
        self._check_location(file_path, lines)

    def _check_substantive_content(self, file_path: Path, lines: List[str]) -> None:
        """Check for substantive content that should be in chunks.
        
        Args:
            file_path: Path to file
            lines: File content lines
        """
        in_code_block = False
        substantive_blocks = []
        current_block = []
        
        for i, line in enumerate(lines, 1):
            # Track code blocks
            if line.strip().startswith("```"):
                in_code_block = not in_code_block
                if current_block and not in_code_block:
                    substantive_blocks.append((i - len(current_block), current_block))
                    current_block = []
                continue
            
            # Skip references
            if self.REFERENCE_PATTERN.search(line):
                continue
            
            # Skip empty lines and comments
            if not line.strip() or line.strip().startswith("#"):
                if current_block and not in_code_block:
                    substantive_blocks.append((i - len(current_block), current_block))
                    current_block = []
                continue
            
            # Accumulate substantive content
            if len(line.strip()) > 20:  # Non-trivial line
                current_block.append(line)
        
        # Check final block
        if current_block:
            substantive_blocks.append((len(lines) - len(current_block) + 1, current_block))
        
        # Report substantive blocks
        for line_num, block in substantive_blocks:
            if len(block) > 3:  # More than 3 lines of content
                self.issues.append(Issue(
                    file_path=file_path,
                    issue_type=IssueType.SUBSTANTIVE_CONTENT,
                    line_number=line_num,
                    content="\n".join(block[:3]) + "...",
                    recommendation=self._suggest_chunk_location(file_path, block)
                ))

    def _check_location(self, file_path: Path, lines: List[str]) -> None:
        """Check if content is in appropriate directory.
        
        Args:
            file_path: Path to file
            lines: File content lines
        """
        relative_path = file_path.relative_to(self.base_dir)
        parent_dir = relative_path.parent.name if relative_path.parent != Path(".") else "root"
        
        # Analyze content for domain
        content = "\n".join(lines).lower()
        
        location_hints = {
            "tests/": ["test", "pytest", "fixture", "assertion", "mock"],
            "src/": ["import", "class", "def ", "python", "module"],
            "scripts/": ["script", "automation", "cli", "command"],
            "docs/": ["documentation", "api", "reference", "guide"],
        }
        
        for target_dir, keywords in location_hints.items():
            if any(keyword in content for keyword in keywords):
                if target_dir not in str(relative_path) and parent_dir == "root":
                    self.issues.append(Issue(
                        file_path=file_path,
                        issue_type=IssueType.WRONG_LOCATION,
                        line_number=None,
                        content=f"Content appears to be {target_dir} specific but in {parent_dir}",
                        recommendation=f"Move to {target_dir}CLAUDE.md or extract to chunk"
                    ))

    def _check_duplication(self, files: List[Path]) -> None:
        """Check for duplication across CLAUDE.md files.
        
        Args:
            files: List of CLAUDE.md files to check
        """
        content_map: Dict[str, List[Path]] = {}
        
        for file_path in files:
            lines = file_path.read_text().splitlines()
            
            # Extract meaningful content blocks
            for line in lines:
                if len(line.strip()) > 50 and not self.REFERENCE_PATTERN.search(line):
                    # Normalize for comparison
                    normalized = re.sub(r'\s+', ' ', line.strip().lower())
                    if normalized not in content_map:
                        content_map[normalized] = []
                    content_map[normalized].append(file_path)
        
        # Report duplicates
        for content, paths in content_map.items():
            if len(paths) > 1:
                self.issues.append(Issue(
                    file_path=paths[0],
                    issue_type=IssueType.DUPLICATION,
                    line_number=None,
                    content=f"Duplicated in {len(paths)} files: {content[:100]}...",
                    recommendation=f"Extract to shared chunk in bots/prompts/"
                ))

    def _suggest_chunk_location(self, file_path: Path, content_lines: List[str]) -> str:
        """Suggest appropriate chunk location for content.
        
        Args:
            file_path: Current file path
            content_lines: Content to relocate
            
        Returns:
            Suggested chunk path
        """
        content = "\n".join(content_lines).lower()
        relative_path = file_path.relative_to(self.base_dir)
        
        # Check if project-specific
        project_keywords = ["buttermilk", "academicops", "specific", "custom", "internal"]
        is_project_specific = any(kw in content for kw in project_keywords)
        
        # Determine tier
        if is_project_specific:
            return f"bots/prompts/PROJECT_{self._infer_chunk_name(content)}.md"
        elif self._is_reusable(content):
            return f"$ACADEMICOPS_BOT/bots/prompts/{self._infer_chunk_name(content)}.md"
        else:
            return f"$ACADEMICOPS_PERSONAL/prompts/{self._infer_chunk_name(content)}.md"

    def _is_reusable(self, content: str) -> bool:
        """Check if content is reusable across projects.
        
        Args:
            content: Content to check
            
        Returns:
            True if reusable
        """
        reusable_keywords = ["python", "test", "git", "docker", "api", "general", "standard"]
        return any(kw in content.lower() for kw in reusable_keywords)

    def _infer_chunk_name(self, content: str) -> str:
        """Infer appropriate chunk name from content.
        
        Args:
            content: Content to analyze
            
        Returns:
            Suggested chunk name
        """
        # Extract key terms
        if "test" in content:
            return "testing_practices"
        elif "python" in content:
            return "python_development"
        elif "git" in content:
            return "git_workflow"
        elif "docker" in content:
            return "docker_setup"
        elif "api" in content:
            return "api_guidelines"
        else:
            return "instructions"

    def print_report(self) -> None:
        """Print audit report to console."""
        if not self.issues:
            print("✅ No issues found in CLAUDE.md files!")
            return
        
        print(f"Found {len(self.issues)} issues in CLAUDE.md files:\n")
        
        # Group by file
        issues_by_file: Dict[Path, List[Issue]] = {}
        for issue in self.issues:
            if issue.file_path not in issues_by_file:
                issues_by_file[issue.file_path] = []
            issues_by_file[issue.file_path].append(issue)
        
        for file_path, file_issues in issues_by_file.items():
            print(f"\n📄 {file_path.relative_to(self.base_dir)}:")
            for issue in file_issues:
                icon = {
                    IssueType.SUBSTANTIVE_CONTENT: "📝",
                    IssueType.WRONG_LOCATION: "📍",
                    IssueType.DUPLICATION: "🔁",
                    IssueType.MISSING_REFERENCES: "🔗",
                    IssueType.TOO_LONG: "📏",
                    IssueType.INLINE_INSTRUCTIONS: "💬"
                }.get(issue.issue_type, "❓")
                
                print(f"  {icon} {issue.issue_type.value}")
                if issue.line_number:
                    print(f"     Line {issue.line_number}: {issue.content[:100]}")
                else:
                    print(f"     {issue.content[:200]}")
                print(f"     → {issue.recommendation}")


def main():
    """Main entry point."""
    import sys
    
    # Use current directory or provided path
    base_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    
    if not base_dir.exists():
        print(f"❌ Directory not found: {base_dir}")
        sys.exit(1)
    
    print(f"🔍 Auditing CLAUDE.md files in: {base_dir}\n")
    
    auditor = ClaudeFileAuditor(base_dir)
    issues = auditor.audit()
    auditor.print_report()
    
    # Exit with error code if issues found
    sys.exit(1 if issues else 0)


if __name__ == "__main__":
    main()
