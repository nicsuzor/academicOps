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

        # ASSERT - Verify agent descriptions extracted
        dev_agent = next(a for a in components['agents'] if a['name'] == 'DEVELOPER')
        assert 'description' in dev_agent, "Should extract description from agent frontmatter"
        assert len(dev_agent['description']) > 0, "Description should not be empty"
        assert 'developer' in dev_agent['description'].lower(), "Description should mention developer"

        # ASSERT - Verify skills discovered
        skill_names = [s['name'] for s in components['skills']]
        assert len(skill_names) > 0, "Should find at least one skill"
        assert 'test-writing' in skill_names, "Should find test-writing skill"
        assert 'git-commit' in skill_names, "Should find git-commit skill"
        assert 'aops-trainer' in skill_names, "Should find aops-trainer skill"

        # ASSERT - Verify skill descriptions extracted
        test_writing_skill = next(s for s in components['skills'] if s['name'] == 'test-writing')
        assert 'description' in test_writing_skill, "Should extract description from skill SKILL.md frontmatter"
        assert len(test_writing_skill['description']) > 0, "Description should not be empty"
        assert 'test' in test_writing_skill['description'].lower(), "Description should mention testing"

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

    def test_markdown_generator_produces_readme_section(self, repo_root):
        """
        VALIDATES: Markdown generator creates formatted README section from scan results.

        Test structure:
        - Scan repository to get components
        - Generate markdown section from components
        - Verify markdown contains all component types
        - Verify markdown is properly formatted
        - Verify specific components listed

        This verifies:
        - generate_markdown_tree() produces valid markdown
        - All component types appear in output
        - Output includes counts and descriptions
        - Format is README-compatible
        """
        # ARRANGE - Scan and import generator
        import sys
        from pathlib import Path

        repo_scripts = repo_root / 'scripts'
        if str(repo_scripts) not in sys.path:
            sys.path.insert(0, str(repo_scripts))

        from generate_instruction_tree import scan_repository, generate_markdown_tree

        components = scan_repository(repo_root)

        # ACT - Generate markdown
        markdown = generate_markdown_tree(components, repo_root)

        # ASSERT - Verify markdown structure
        assert isinstance(markdown, str), "Should return string"
        assert len(markdown) > 100, "Should have substantial content"

        # ASSERT - Verify section headers present
        assert '## Agents' in markdown or '### Agents' in markdown, "Should have Agents section"
        assert '## Skills' in markdown or '### Skills' in markdown, "Should have Skills section"
        assert '## Commands' in markdown or '### Commands' in markdown, "Should have Commands section"
        assert '## Hooks' in markdown or '### Hooks' in markdown, "Should have Hooks section"

        # ASSERT - Verify specific known components listed
        assert 'DEVELOPER' in markdown, "Should list DEVELOPER agent"
        assert 'test-writing' in markdown, "Should list test-writing skill"
        assert 'dev' in markdown or '/dev' in markdown, "Should list dev command"
        assert 'load_instructions' in markdown, "Should list load_instructions hook"

        # ASSERT - Verify counts present
        assert 'agent' in markdown.lower(), "Should mention agents"
        assert 'skill' in markdown.lower(), "Should mention skills"
        assert 'command' in markdown.lower(), "Should mention commands"

        # ASSERT - Verify markdown formatting (lists or tables)
        assert '-' in markdown or '|' in markdown, "Should use markdown list or table format"

    def test_readme_update_preserves_content_outside_markers(self, repo_root, tmp_path):
        """
        VALIDATES: update_readme_with_tree() updates content between markers while preserving other content.

        Test structure:
        - Create temporary README.md with marker comments
        - Generate tree content from repository scan
        - Call update_readme_with_tree() to update README
        - Verify content between markers was replaced
        - Verify content before markers preserved
        - Verify content after markers preserved

        This verifies:
        - Function finds marker comments correctly
        - Content replacement works
        - Manual content is preserved
        - File is written correctly
        """
        # ARRANGE - Import function and set up test README
        import sys
        from pathlib import Path

        repo_scripts = repo_root / 'scripts'
        if str(repo_scripts) not in sys.path:
            sys.path.insert(0, str(repo_scripts))

        from generate_instruction_tree import scan_repository, generate_markdown_tree, update_readme_with_tree

        # Create test README with markers
        test_readme = tmp_path / "README.md"
        original_content = """# Test Project

This is the introduction.

<!-- INSTRUCTION_TREE_START -->
OLD CONTENT TO BE REPLACED
<!-- INSTRUCTION_TREE_END -->

This is the conclusion.
"""
        test_readme.write_text(original_content)

        # Generate new tree content
        components = scan_repository(repo_root)
        new_tree_content = generate_markdown_tree(components, repo_root)

        # ACT - Update README with new tree
        update_readme_with_tree(test_readme, new_tree_content)

        # ASSERT - Read updated README
        updated_content = test_readme.read_text()

        # ASSERT - Content before markers preserved
        assert "# Test Project" in updated_content, "Title should be preserved"
        assert "This is the introduction." in updated_content, "Introduction should be preserved"

        # ASSERT - Content after markers preserved
        assert "This is the conclusion." in updated_content, "Conclusion should be preserved"

        # ASSERT - Old content replaced with new tree
        assert "OLD CONTENT TO BE REPLACED" not in updated_content, "Old content should be removed"
        assert "## Instruction Tree" in new_tree_content or "### Agents" in new_tree_content, "New tree content should be present"

        # ASSERT - Markers still present
        assert "<!-- INSTRUCTION_TREE_START -->" in updated_content, "Start marker should remain"
        assert "<!-- INSTRUCTION_TREE_END -->" in updated_content, "End marker should remain"

        # ASSERT - New tree content is between markers
        start_idx = updated_content.index("<!-- INSTRUCTION_TREE_START -->")
        end_idx = updated_content.index("<!-- INSTRUCTION_TREE_END -->")
        assert start_idx < end_idx, "Start marker should come before end marker"

        content_between_markers = updated_content[start_idx:end_idx]
        # Check that some of the generated content appears between markers
        assert "Agents" in content_between_markers or "Skills" in content_between_markers, "Generated tree should be between markers"

    def test_validation_script_detects_stale_instruction_tree(self, repo_root, tmp_path):
        """
        VALIDATES: Validation script detects when instruction tree in README.md doesn't match repository state.

        Test structure:
        - Create temporary repository with README.md containing instruction tree
        - Run validation script - should pass with current tree
        - Modify repository state (add new agent file)
        - Run validation script - should FAIL with stale tree
        - Regenerate tree
        - Run validation script - should pass again

        This verifies:
        - validate_instruction_tree.py script exists and is executable
        - Script compares README tree against actual repository state
        - Script exits with code 0 when tree is current
        - Script exits with code 1 when tree is stale
        - Script provides helpful error message showing what changed
        """
        # ARRANGE - Import functions and validation script
        import sys
        import subprocess
        from pathlib import Path

        repo_scripts = repo_root / 'scripts'
        if str(repo_scripts) not in sys.path:
            sys.path.insert(0, str(repo_scripts))

        from generate_instruction_tree import scan_repository, generate_markdown_tree, update_readme_with_tree

        # Import the validation function (will fail initially - TDD)
        from validate_instruction_tree import validate_tree_is_current

        # Create temporary repository structure
        test_repo = tmp_path / "test_repo"
        test_repo.mkdir()

        # Create agents directory with initial agent
        agents_dir = test_repo / "agents"
        agents_dir.mkdir()
        (agents_dir / "DEVELOPER.md").write_text("# Developer Agent\nInitial content")

        # Create skills directory with initial skill
        skills_dir = test_repo / "skills"
        skills_dir.mkdir()
        test_skill_dir = skills_dir / "test-skill"
        test_skill_dir.mkdir()
        (test_skill_dir / "SKILL.md").write_text("# Test Skill\nInitial content")

        # Create commands directory
        commands_dir = test_repo / "commands"
        commands_dir.mkdir()
        (commands_dir / "dev.md").write_text("# Dev Command")

        # Create hooks directory
        hooks_dir = test_repo / "hooks"
        hooks_dir.mkdir()
        (hooks_dir / "load_instructions.py").write_text("# Load instructions hook")

        # Create core directory
        core_dir = test_repo / "core"
        core_dir.mkdir()
        (core_dir / "_CORE.md").write_text("# Core\n@../chunks/AXIOMS.md")

        # Create README.md with markers and current tree
        test_readme = test_repo / "README.md"
        test_readme.write_text("""# Test Project

<!-- INSTRUCTION_TREE_START -->
<!-- INSTRUCTION_TREE_END -->
""")

        # Generate and write current tree
        components = scan_repository(test_repo)
        tree = generate_markdown_tree(components, test_repo)
        update_readme_with_tree(test_readme, tree)

        # ACT & ASSERT - Validation should pass with current tree
        is_current, message = validate_tree_is_current(test_repo)
        assert is_current, f"Validation should pass with current tree. Message: {message}"
        assert message == "" or "current" in message.lower(), "Success message should indicate tree is current"

        # ACT - Modify repository (add new agent)
        (agents_dir / "SUPERVISOR.md").write_text("# Supervisor Agent\nNew agent content")

        # ASSERT - Validation should fail with stale tree
        is_current, message = validate_tree_is_current(test_repo)
        assert not is_current, f"Validation should fail with stale tree. Message: {message}"
        assert "stale" in message.lower() or "outdated" in message.lower() or "mismatch" in message.lower(), \
            "Error message should indicate tree is stale"
        assert "SUPERVISOR" in message or "agent" in message.lower(), \
            "Error message should mention what changed"

        # ACT - Regenerate tree
        new_components = scan_repository(test_repo)
        new_tree = generate_markdown_tree(new_components, test_repo)
        update_readme_with_tree(test_readme, new_tree)

        # ASSERT - Validation should pass again
        is_current, message = validate_tree_is_current(test_repo)
        assert is_current, f"Validation should pass after tree regeneration. Message: {message}"

    def test_aops_trainer_skill_documents_instruction_tree_maintenance(self):
        """
        VALIDATES: aops-trainer skill includes instruction tree maintenance as a core responsibility.

        Test structure:
        - Read aops-trainer SKILL.md file
        - Verify "instruction tree" or "documentation maintenance" mentioned
        - Verify maintenance script references included
        - Verify workflow guidance provided

        This verifies:
        - aops-trainer skill documents its responsibility for instruction tree
        - Skill includes references to maintenance scripts
        - Skill provides guidance on when to update documentation
        """
        # ARRANGE - Locate aops-trainer skill
        skill_path = Path.home() / ".claude" / "skills" / "aops-trainer" / "SKILL.md"

        if not skill_path.exists():
            pytest.skip(f"aops-trainer skill not found at {skill_path}")

        # ACT - Read skill documentation
        skill_content = skill_path.read_text().lower()

        # ASSERT - Instruction tree maintenance is documented
        assert "instruction tree" in skill_content or "documentation maintenance" in skill_content, \
            "Skill should mention instruction tree or documentation maintenance"

        # ASSERT - Script references present
        assert "generate_instruction_tree" in skill_content or "validate_instruction_tree" in skill_content, \
            "Skill should reference instruction tree scripts"

        # ASSERT - Maintenance workflow described
        assert "readme" in skill_content or "documentation" in skill_content, \
            "Skill should describe documentation maintenance workflow"
