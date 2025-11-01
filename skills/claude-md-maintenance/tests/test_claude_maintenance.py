#!/usr/bin/env python3
"""Tests for CLAUDE.md maintenance skill.

Tests audit, extraction, refactoring, and validation of CLAUDE.md files.
"""

import json
import sys
import tempfile
from pathlib import Path
from typing import Dict, List

import pytest

# Add scripts to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from audit_claude_files import ClaudeFileAuditor, IssueType
from extract_chunks import ChunkExtractor
from refactor_references import ReferenceRefactorer
from validate_references import ReferenceValidator, ReferenceStatus


def load_fixture(filename: str) -> str:
    """Load text fixture file."""
    fixture_path = Path(__file__).parent / "fixtures" / filename
    return fixture_path.read_text()


def load_json_fixture(filename: str) -> Dict:
    """Load JSON fixture file."""
    fixture_path = Path(__file__).parent / "fixtures" / filename
    return json.loads(fixture_path.read_text())


class TestClaudeFileAuditor:
    """Test CLAUDE.md file auditing functionality."""

    def test_audit_detects_substantive_content(self, tmp_path):
        """Test that auditor detects inline substantive content."""
        # Create test file with substantive content
        claude_file = tmp_path / "CLAUDE.md"
        claude_file.write_text(load_fixture("bloated_claude.md"))
        
        auditor = ClaudeFileAuditor(tmp_path)
        issues = auditor.audit()
        
        # Should detect substantive content issues
        substantive_issues = [
            i for i in issues 
            if i.issue_type == IssueType.SUBSTANTIVE_CONTENT
        ]
        assert len(substantive_issues) > 0
        
        # Should recommend extraction to chunks
        for issue in substantive_issues:
            assert "bots/prompts/" in issue.recommendation

    def test_audit_detects_long_files(self, tmp_path):
        """Test that auditor detects files that are too long."""
        # Create long file
        claude_file = tmp_path / "CLAUDE.md"
        lines = ["Line content"] * 60  # Over 50 line threshold
        claude_file.write_text("\n".join(lines))
        
        auditor = ClaudeFileAuditor(tmp_path)
        issues = auditor.audit()
        
        # Should detect file length issue
        length_issues = [
            i for i in issues
            if i.issue_type == IssueType.TOO_LONG
        ]
        assert len(length_issues) > 0
        assert "60 lines" in length_issues[0].content

    def test_audit_detects_duplication(self, tmp_path):
        """Test that auditor detects duplicated content across files."""
        # Create multiple files with duplicate content
        duplicate_data = load_json_fixture("duplicated_content.json")
        
        for filepath, lines in duplicate_data["files"].items():
            file_path = tmp_path / filepath.lstrip("/")
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text("\n".join(lines))
        
        auditor = ClaudeFileAuditor(tmp_path)
        issues = auditor.audit()
        
        # Should detect duplication
        dup_issues = [
            i for i in issues
            if i.issue_type == IssueType.DUPLICATION
        ]
        assert len(dup_issues) > 0

    def test_audit_clean_file_passes(self, tmp_path):
        """Test that clean CLAUDE.md with only references passes audit."""
        claude_file = tmp_path / "CLAUDE.md"
        claude_file.write_text(load_fixture("claude_with_references.md"))
        
        auditor = ClaudeFileAuditor(tmp_path)
        issues = auditor.audit()
        
        # Clean file should have no issues
        assert len(issues) == 0


class TestChunkExtractor:
    """Test content extraction to chunks."""

    def test_extract_creates_chunks(self, tmp_path):
        """Test that extractor creates chunk files from substantive content."""
        # Setup test file
        claude_file = tmp_path / "CLAUDE.md"
        claude_file.write_text(load_fixture("bloated_claude.md"))
        
        # Create bots/prompts directory
        chunks_dir = tmp_path / "bots" / "prompts"
        chunks_dir.mkdir(parents=True)
        
        extractor = ChunkExtractor(tmp_path)
        chunks = extractor.extract_from_file(claude_file)
        
        # Should create chunk files
        assert len(chunks) > 0
        
        # Verify chunks were created
        chunk_files = list(chunks_dir.glob("*.md"))
        assert len(chunk_files) > 0

    def test_extract_replaces_with_references(self, tmp_path):
        """Test that extraction replaces content with @references."""
        claude_file = tmp_path / "CLAUDE.md"
        original_content = load_fixture("bloated_claude.md")
        claude_file.write_text(original_content)
        
        # Create bots/prompts directory
        (tmp_path / "bots" / "prompts").mkdir(parents=True)
        
        extractor = ChunkExtractor(tmp_path)
        extractor.extract_from_file(claude_file)
        
        # Check updated content has references
        updated_content = claude_file.read_text()
        assert "@bots/prompts/" in updated_content or "@" in updated_content
        assert len(updated_content.splitlines()) < len(original_content.splitlines())

    def test_extract_determines_correct_tier(self, tmp_path):
        """Test that extractor places chunks in correct tier."""
        # Test with project-specific content
        claude_file = tmp_path / "CLAUDE.md"
        claude_file.write_text("# Project Specific\nThis is specific to buttermilk project.")
        
        extractor = ChunkExtractor(tmp_path)
        chunks = extractor.extract_from_file(claude_file, dry_run=True)
        
        if chunks:
            # Project-specific content should go to PROJECT_ prefixed files
            assert any("PROJECT_" in str(c.target_path) for c in chunks)

    def test_extract_dry_run_no_changes(self, tmp_path):
        """Test that dry run doesn't modify files."""
        claude_file = tmp_path / "CLAUDE.md"
        original_content = load_fixture("bloated_claude.md")
        claude_file.write_text(original_content)
        
        extractor = ChunkExtractor(tmp_path)
        chunks = extractor.extract_from_file(claude_file, dry_run=True)
        
        # Should identify chunks but not modify file
        assert len(chunks) > 0
        assert claude_file.read_text() == original_content


class TestReferenceRefactorer:
    """Test reference refactoring functionality."""

    def test_refactor_finds_instruction_patterns(self, tmp_path):
        """Test that refactorer identifies instruction patterns."""
        claude_file = tmp_path / "CLAUDE.md"
        content = """
# CLAUDE.md

Always use pytest for testing.
Never mock internal code.
Must validate all inputs.
Should follow TDD practices.
"""
        claude_file.write_text(content)
        
        refactorer = ReferenceRefactorer(tmp_path)
        candidates = refactorer.refactor_file(claude_file, dry_run=True)
        
        # Should find instruction patterns
        assert len(candidates) > 0

    def test_refactor_consolidates_duplicates(self, tmp_path):
        """Test that refactorer consolidates duplicate references."""
        claude_file = tmp_path / "CLAUDE.md"
        content = """
@bots/prompts/testing.md
@bots/prompts/python.md
@bots/prompts/testing.md
@bots/prompts/python.md
@bots/prompts/testing.md
"""
        claude_file.write_text(content)
        
        refactorer = ReferenceRefactorer(tmp_path)
        removed = refactorer.consolidate_references(claude_file)
        
        # Should remove duplicates
        assert removed > 0
        
        # Check file has no duplicates
        updated = claude_file.read_text()
        lines = updated.strip().splitlines()
        assert len(lines) == len(set(lines))

    def test_refactor_matches_existing_chunks(self, tmp_path):
        """Test that refactorer matches content with existing chunks."""
        # Create existing chunk
        chunks_dir = tmp_path / "bots" / "prompts"
        chunks_dir.mkdir(parents=True)
        chunk_file = chunks_dir / "testing_practices.md"
        chunk_file.write_text("Always use pytest for testing.")
        
        # Create CLAUDE.md with matching content
        claude_file = tmp_path / "CLAUDE.md"
        claude_file.write_text("Always use pytest for testing.")
        
        refactorer = ReferenceRefactorer(tmp_path)
        # Force rescan of chunks
        refactorer.existing_chunks = refactorer._scan_existing_chunks()
        
        candidates = refactorer.refactor_file(claude_file, dry_run=True)
        
        # Should find matching chunk
        if candidates:
            assert any(c.existing_chunk is not None for c in candidates)


class TestReferenceValidator:
    """Test reference validation functionality."""

    def test_validate_valid_references(self, tmp_path):
        """Test that validator accepts valid references."""
        # Create referenced files
        (tmp_path / "bots" / "prompts").mkdir(parents=True)
        (tmp_path / "bots" / "prompts" / "PROJECT_overview.md").write_text("Content")
        
        # Create CLAUDE.md with reference
        claude_file = tmp_path / "CLAUDE.md"
        claude_file.write_text("@bots/prompts/PROJECT_overview.md")
        
        validator = ReferenceValidator(tmp_path)
        references = validator.validate_file(claude_file)
        
        # Should be valid
        assert len(references) == 1
        assert references[0].status == ReferenceStatus.VALID

    def test_validate_missing_references(self, tmp_path):
        """Test that validator detects missing referenced files."""
        claude_file = tmp_path / "CLAUDE.md"
        claude_file.write_text("@bots/prompts/nonexistent.md")
        
        validator = ReferenceValidator(tmp_path)
        references = validator.validate_file(claude_file)
        
        # Should detect missing file
        assert len(references) == 1
        assert references[0].status == ReferenceStatus.NOT_FOUND

    def test_validate_env_var_references(self, tmp_path, monkeypatch):
        """Test that validator handles environment variable references."""
        # Set environment variable
        framework_dir = tmp_path / "framework"
        framework_dir.mkdir()
        (framework_dir / "bots" / "prompts").mkdir(parents=True)
        (framework_dir / "bots" / "prompts" / "python.md").write_text("Content")
        
        monkeypatch.setenv("ACADEMICOPS", str(framework_dir))
        
        claude_file = tmp_path / "CLAUDE.md"
        claude_file.write_text("@$ACADEMICOPS/bots/prompts/python.md")
        
        validator = ReferenceValidator(tmp_path)
        references = validator.validate_file(claude_file)
        
        # Should resolve env var reference
        assert len(references) == 1
        assert references[0].status == ReferenceStatus.VALID

    def test_validate_circular_references(self, tmp_path):
        """Test that validator detects circular references."""
        # Create self-referencing file
        claude_file = tmp_path / "CLAUDE.md"
        claude_file.write_text(f"@CLAUDE.md")
        
        validator = ReferenceValidator(tmp_path)
        references = validator.validate_file(claude_file)
        
        # Should detect circular reference
        assert len(references) == 1
        assert references[0].status == ReferenceStatus.CIRCULAR


class TestIntegration:
    """Integration tests for complete workflow."""

    def test_full_workflow(self, tmp_path):
        """Test complete audit → extract → refactor → validate workflow."""
        # Setup bloated CLAUDE.md
        claude_file = tmp_path / "CLAUDE.md"
        claude_file.write_text(load_fixture("bloated_claude.md"))
        
        # Step 1: Audit
        auditor = ClaudeFileAuditor(tmp_path)
        issues = auditor.audit()
        assert len(issues) > 0  # Should find issues
        
        # Step 2: Extract
        (tmp_path / "bots" / "prompts").mkdir(parents=True)
        extractor = ChunkExtractor(tmp_path)
        chunks = extractor.extract_from_file(claude_file)
        assert len(chunks) > 0  # Should extract chunks
        
        # Step 3: Refactor
        refactorer = ReferenceRefactorer(tmp_path)
        refactorer.consolidate_references(claude_file)
        
        # Step 4: Validate
        validator = ReferenceValidator(tmp_path)
        references = validator.validate_file(claude_file)
        
        # All references should be valid after extraction
        invalid = [r for r in references if r.status != ReferenceStatus.VALID]
        assert len(invalid) == 0
        
        # Step 5: Re-audit - should be clean
        final_issues = auditor.audit()
        assert len(final_issues) == 0  # Clean!

    def test_multi_repository_support(self, tmp_path, monkeypatch):
        """Test that skill works across different repository contexts."""
        # Setup multiple repository contexts
        framework_repo = tmp_path / "framework"
        personal_repo = tmp_path / "personal"
        project_repo = tmp_path / "project"
        
        for repo in [framework_repo, personal_repo, project_repo]:
            repo.mkdir()
            (repo / "CLAUDE.md").write_text("Test content for extraction")
        
        # Test in each context
        for repo in [framework_repo, personal_repo, project_repo]:
            monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(repo))
            
            auditor = ClaudeFileAuditor(repo)
            issues = auditor.audit()
            
            # Should work in any repository
            assert isinstance(issues, list)


# Test helper for pytest execution
def test_skill_scripts_executable(tmp_path):
    """Verify all scripts are executable and have proper structure."""
    scripts_dir = Path(__file__).parent.parent / "scripts"
    
    required_scripts = [
        "audit_claude_files.py",
        "extract_chunks.py", 
        "refactor_references.py",
        "validate_references.py"
    ]
    
    for script_name in required_scripts:
        script_path = scripts_dir / script_name
        assert script_path.exists(), f"Script {script_name} not found"
        
        # Check shebang
        first_line = script_path.read_text().splitlines()[0]
        assert first_line.startswith("#!/usr/bin/env python"), f"{script_name} missing shebang"
