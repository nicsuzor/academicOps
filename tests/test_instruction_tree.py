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

        # ASSERT - Verify command descriptions extracted
        dev_command = next(c for c in components['commands'] if c['name'] == 'dev')
        assert 'description' in dev_command, "Should extract description from command frontmatter"
        assert len(dev_command['description']) > 0, "Description should not be empty"
        assert 'development' in dev_command['description'].lower() or 'dev' in dev_command['description'].lower(), "Description should mention development"

        # ASSERT - Verify hooks discovered
        hook_names = [h['name'] for h in components['hooks']]
        assert len(hook_names) > 0, "Should find at least one hook"
        assert 'load_instructions' in hook_names, "Should find load_instructions.py hook"
        assert 'validate_tool' in hook_names, "Should find validate_tool.py hook"

        # ASSERT - Verify hook descriptions extracted from docstrings
        load_hook = next(h for h in components['hooks'] if h['name'] == 'load_instructions')
        assert 'description' in load_hook, "Should extract description from hook docstring"
        assert len(load_hook['description']) > 0, "Description should not be empty"
        assert 'load' in load_hook['description'].lower() or 'instruction' in load_hook['description'].lower(), "Description should mention loading/instructions"

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

    def test_markdown_includes_component_descriptions(self, repo_root):
        """
        VALIDATES: Markdown output includes descriptions for all component types.

        Test structure:
        - Scan repository to get components with descriptions
        - Generate markdown section from components
        - Verify descriptions appear in formatted output
        - Verify format: **name** - Description (`path`)

        This verifies:
        - generate_markdown_tree() includes description field
        - Format matches specification
        - Descriptions appear for agents, skills, commands, hooks
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

        # ASSERT - Verify DEVELOPER agent has description in correct format
        # Expected format: - **DEVELOPER** - {description} (`agents/DEVELOPER.md`)
        dev_agent = next((a for a in components['agents'] if a['name'] == 'DEVELOPER'), None)
        assert dev_agent is not None, "DEVELOPER agent should exist for testing"
        assert dev_agent['description'], "DEVELOPER agent should have description"

        # Check that markdown contains agent name, description, and path in proper format
        assert '**DEVELOPER**' in markdown, "Should include agent name in bold"
        assert dev_agent['description'] in markdown, f"Should include description: {dev_agent['description']}"
        assert '`agents/DEVELOPER.md`' in markdown, "Should include agent path in backticks"

        # ASSERT - Verify test-writing skill has description in correct format
        # Expected format: - **test-writing** - {description} (`skills/test-writing`)
        test_skill = next((s for s in components['skills'] if s['name'] == 'test-writing'), None)
        assert test_skill is not None, "test-writing skill should exist for testing"
        assert test_skill['description'], "test-writing skill should have description"

        assert '**test-writing**' in markdown, "Should include skill name in bold"
        assert test_skill['description'] in markdown, f"Should include description: {test_skill['description']}"
        assert '`skills/test-writing`' in markdown, "Should include skill path in backticks"

        # ASSERT - Verify dev command has description in correct format
        # Expected format: - **/dev** - {description} (`commands/dev.md`)
        dev_command = next((c for c in components['commands'] if c['name'] == 'dev'), None)
        assert dev_command is not None, "dev command should exist for testing"
        assert dev_command['description'], "dev command should have description"

        assert '**/dev**' in markdown or '**dev**' in markdown, "Should include command name in bold"
        assert dev_command['description'] in markdown, f"Should include description: {dev_command['description']}"
        assert '`commands/dev.md`' in markdown, "Should include command path in backticks"

        # ASSERT - Verify load_instructions hook has description in correct format
        # Expected format: - **load_instructions** - {description} (`hooks/load_instructions.py`)
        load_hook = next((h for h in components['hooks'] if h['name'] == 'load_instructions'), None)
        assert load_hook is not None, "load_instructions hook should exist for testing"
        assert load_hook['description'], "load_instructions hook should have description"

        assert '**load_instructions**' in markdown, "Should include hook name in bold"
        assert load_hook['description'] in markdown, f"Should include description: {load_hook['description']}"
        assert '`hooks/load_instructions.py`' in markdown, "Should include hook path in backticks"

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

    def test_aops_trainer_documents_description_maintenance_and_architectural_analysis(self):
        """
        VALIDATES: aops-trainer skill documents Phase 3 enhancements:
        - Description maintenance workflow
        - Architectural analysis using descriptions

        Test structure:
        - Read aops-trainer SKILL.md file
        - Verify description maintenance workflow documented
        - Verify architectural analysis workflow documented
        - Verify integration with existing workflows

        This verifies Phase 3 completion:
        - Description maintenance: when/how to extract and verify descriptions
        - Architectural analysis: overlap/fragmentation/confusion detection
        - References to generate_instruction_tree.py script
        - Integration with "When to Use This Skill" triggers
        """
        # ARRANGE - Locate aops-trainer skill
        skill_path = Path.home() / ".claude" / "skills" / "aops-trainer" / "SKILL.md"

        if not skill_path.exists():
            pytest.skip(f"aops-trainer skill not found at {skill_path}")

        # ACT - Read skill documentation
        skill_content = skill_path.read_text()
        skill_content_lower = skill_content.lower()

        # ASSERT - Description maintenance workflow documented
        assert "description maintenance" in skill_content_lower or "description" in skill_content_lower, \
            "Skill should document description maintenance"
        assert "extract" in skill_content_lower and "description" in skill_content_lower, \
            "Skill should explain how to extract descriptions"
        assert "verify" in skill_content_lower or "validate" in skill_content_lower, \
            "Skill should explain how to verify descriptions"

        # ASSERT - Architectural analysis workflow documented
        assert "architectural analysis" in skill_content_lower or "architecture" in skill_content_lower, \
            "Skill should document architectural analysis"
        assert "overlap" in skill_content_lower, \
            "Skill should mention overlap detection"
        assert "fragmentation" in skill_content_lower or "fragment" in skill_content_lower, \
            "Skill should mention fragmentation detection"

        # ASSERT - Reference to instruction tree script
        assert "generate_instruction_tree" in skill_content_lower or "instruction tree" in skill_content_lower, \
            "Skill should reference instruction tree generation"

        # ASSERT - Examples of architectural problems to detect
        assert "similar" in skill_content_lower or "duplicate" in skill_content_lower, \
            "Skill should mention detecting similar/duplicate responsibilities"

        # ASSERT - Integration with existing workflow
        # Check that description maintenance appears in appropriate sections
        assert ("when to use" in skill_content_lower and "description" in skill_content_lower) or \
               ("instruction tree" in skill_content_lower and "maintenance" in skill_content_lower), \
            "Skill should integrate description maintenance into existing triggers/workflows"

    def test_scanner_collects_skill_symlink_dependencies(self, repo_root):
        """
        VALIDATES: Repository scanner discovers symlinks in skills/ directories.

        Test structure:
        - Scan repository (repo_root fixture)
        - Verify skills with symlinks have 'dependencies' field
        - Verify symlink targets are resolved to relative paths
        - Test with analyst skill (has symlinks to MATPLOTLIB.md, STATSMODELS.md, etc.)
        - Test with git-commit skill (has symlinks to FAIL-FAST.md, TESTS.md, etc.)

        This verifies:
        - Scanner discovers symlinks in skills/*/references/ directories
        - Scanner discovers symlinks in skills/*/resources/ directories
        - Scanner resolves symlink targets to repository-relative paths
        - Dependencies stored in skill metadata
        """
        # ARRANGE - Import scanner
        import sys
        from pathlib import Path

        repo_scripts = repo_root / 'scripts'
        if str(repo_scripts) not in sys.path:
            sys.path.insert(0, str(repo_scripts))

        from generate_instruction_tree import scan_repository

        # ACT - Scan repository
        components = scan_repository(repo_root)

        # ASSERT - analyst skill has dependencies from references/ symlinks
        analyst_skill = next((s for s in components['skills'] if s['name'] == 'analyst'), None)
        assert analyst_skill is not None, "analyst skill should exist"
        assert 'dependencies' in analyst_skill, "analyst skill should have dependencies field"

        dependencies = analyst_skill['dependencies']
        assert len(dependencies) > 0, "analyst skill should have at least one dependency"

        # Check for known symlinked files
        dep_basenames = [Path(d).name for d in dependencies]
        assert 'MATPLOTLIB.md' in dep_basenames, "Should find MATPLOTLIB.md symlink"
        assert 'STATSMODELS.md' in dep_basenames, "Should find STATSMODELS.md symlink"

        # ASSERT - git-commit skill has dependencies from references/ symlinks
        git_commit_skill = next((s for s in components['skills'] if s['name'] == 'git-commit'), None)
        assert git_commit_skill is not None, "git-commit skill should exist"
        assert 'dependencies' in git_commit_skill, "git-commit skill should have dependencies field"

        git_dependencies = git_commit_skill['dependencies']
        assert len(git_dependencies) > 0, "git-commit skill should have at least one dependency"

        # Check for known symlinked files
        git_dep_basenames = [Path(d).name for d in git_dependencies]
        assert 'FAIL-FAST.md' in git_dep_basenames, "Should find FAIL-FAST.md symlink"
        assert 'TESTS.md' in git_dep_basenames, "Should find TESTS.md symlink"

        # ASSERT - aops-trainer skill has dependencies from resources/ symlinks
        trainer_skill = next((s for s in components['skills'] if s['name'] == 'aops-trainer'), None)
        assert trainer_skill is not None, "aops-trainer skill should exist"
        assert 'dependencies' in trainer_skill, "aops-trainer skill should have dependencies field"

        trainer_dependencies = trainer_skill['dependencies']
        assert len(trainer_dependencies) > 0, "aops-trainer skill should have at least one dependency"

        # Check for known symlinked files
        trainer_dep_basenames = [Path(d).name for d in trainer_dependencies]
        assert 'AXIOMS.md' in trainer_dep_basenames, "Should find AXIOMS.md symlink"
        assert 'SKILL-PRIMER.md' in trainer_dep_basenames, "Should find SKILL-PRIMER.md symlink"
