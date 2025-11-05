"""Integration tests for instruction tree generation.

These tests verify that the instruction tree generator correctly scans
the repository and produces accurate documentation of all components.

Test philosophy:
- Uses real repository structure (repo_root fixture)
- No mocking of file system operations
- Tests complete workflow: scan → generate → validate
"""
import json
from pathlib import Path

import pytest


class TestInstructionTreeGeneration:
    """Test instruction tree generation from repository scan."""

    def test_repository_scanner_finds_all_components(self, repo_root):
        """
        VALIDATES: Repository scanner discovers all instruction components.

        Test structure:
        - Import scan_repository from scripts/generate_instruction_tree
        - Scan the real academicOps repository (repo_root fixture)
        - Verify all component types discovered (agents, skills, commands, hooks, core)
        - Verify specific known components exist

        This verifies:
        - Script can scan agents/*.md files
        - Script can scan skills/*/ directories
        - Script can scan commands/*.md files
        - Script can scan hooks/*.py files
        - Script can scan core/_CORE.md and parse @references
        """
        # ARRANGE - Import the scanner function (will fail initially - TDD)
        import sys
        from pathlib import Path

        # Add scripts to path for import
        repo_scripts = repo_root / 'scripts'
        if str(repo_scripts) not in sys.path:
            sys.path.insert(0, str(repo_scripts))

        from generate_instruction_tree import scan_repository

        # ACT - Scan the actual repository
        components = scan_repository(repo_root)

        # ASSERT - Verify all component types discovered
        assert 'agents' in components, "Should discover agents/"
        assert 'skills' in components, "Should discover skills/"
        assert 'commands' in components, "Should discover commands/"
        assert 'hooks' in components, "Should discover hooks/"
        assert 'core' in components, "Should discover core/"

        # ASSERT - Verify agents discovered
        agent_names = [a['name'] for a in components['agents']]
        assert len(agent_names) > 0, "Should find at least one agent"
        assert 'DEVELOPER' in agent_names, "Should find DEVELOPER.md agent"
        assert 'SUPERVISOR' in agent_names, "Should find SUPERVISOR.md agent"

        # ASSERT - Verify skills discovered
        skill_names = [s['name'] for s in components['skills']]
        assert len(skill_names) > 0, "Should find at least one skill"
        assert 'test-writing' in skill_names, "Should find test-writing skill"
        assert 'git-commit' in skill_names, "Should find git-commit skill"
        assert 'aops-trainer' in skill_names, "Should find aops-trainer skill"

        # ASSERT - Verify commands discovered
        command_names = [c['name'] for c in components['commands']]
        assert len(command_names) > 0, "Should find at least one command"
        assert 'dev' in command_names, "Should find dev.md command"
        assert 'trainer' in command_names, "Should find trainer.md command"

        # ASSERT - Verify hooks discovered
        hook_names = [h['name'] for h in components['hooks']]
        assert len(hook_names) > 0, "Should find at least one hook"
        assert 'load_instructions' in hook_names, "Should find load_instructions.py hook"
        assert 'validate_tool' in hook_names, "Should find validate_tool.py hook"

        # ASSERT - Verify core discovered
        assert 'file' in components['core'], "Should have core file path"
        assert 'references' in components['core'], "Should parse @references from core/_CORE.md"
