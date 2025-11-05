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

    def test_scanner_collects_command_load_instructions_dependencies(self, repo_root):
        """
        VALIDATES: Repository scanner discovers load_instructions.py calls in command files.

        Test structure:
        - Scan repository (repo_root fixture)
        - Verify commands with load_instructions.py calls have 'dependencies' field
        - Test with /dev command which loads DEVELOPMENT.md, TESTING.md, DEBUGGING.md, STYLE.md
        - Verify dependencies are in 3-tier format (loaded from framework/personal/project)

        This verifies:
        - Scanner parses command markdown files for load_instructions.py calls
        - Scanner extracts filenames from uv run python ... load_instructions.py FILENAME.md
        - Dependencies stored in command metadata
        - Format shows 3-tier loading pattern
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

        # ASSERT - dev command has dependencies from load_instructions.py calls
        dev_command = next((c for c in components['commands'] if c['name'] == 'dev'), None)
        assert dev_command is not None, "dev command should exist"
        assert 'dependencies' in dev_command, "dev command should have dependencies field"

        dependencies = dev_command['dependencies']
        assert len(dependencies) > 0, "dev command should have at least one dependency"

        # Check for known loaded files (from commands/dev.md)
        # Expected: DEVELOPMENT.md, TESTING.md, DEBUGGING.md, STYLE.md
        assert 'DEVELOPMENT.md' in dependencies, "Should find DEVELOPMENT.md in load_instructions calls"
        assert 'TESTING.md' in dependencies, "Should find TESTING.md in load_instructions calls"
        assert 'DEBUGGING.md' in dependencies, "Should find DEBUGGING.md in load_instructions calls"
        assert 'STYLE.md' in dependencies, "Should find STYLE.md in load_instructions calls"

    def test_markdown_displays_component_dependencies(self, repo_root):
        """
        VALIDATES: Markdown generator displays instruction dependencies under each component.

        Test structure:
        - Scan repository to get components with dependencies
        - Generate markdown section
        - Verify dependencies appear under component descriptions
        - Test format: "Loads: file1, file2, file3"

        This verifies:
        - Skills with symlink dependencies show "Resources: ..." or "References: ..."
        - Commands with load_instructions.py show "Loads: FILENAME.md (3-tier)"
        - Dependencies appear immediately after component description
        - Format is clear and readable
        """
        # ARRANGE - Scan and generate markdown
        import sys
        from pathlib import Path

        repo_scripts = repo_root / 'scripts'
        if str(repo_scripts) not in sys.path:
            sys.path.insert(0, str(repo_scripts))

        from generate_instruction_tree import scan_repository, generate_markdown_tree

        components = scan_repository(repo_root)
        markdown = generate_markdown_tree(components, repo_root)

        # ASSERT - analyst skill shows its dependencies
        # Should see: - **analyst** - description
        #              - Dependencies: docs/_CHUNKS/MATPLOTLIB.md, docs/_CHUNKS/STATSMODELS.md, ...
        assert '**analyst**' in markdown, "Should list analyst skill"
        analyst_section = markdown[markdown.index('**analyst**'):markdown.index('**analyst**') + 500]
        assert 'Dependencies:' in analyst_section or 'Loads:' in analyst_section, \
            "Analyst skill should show dependencies"
        assert 'MATPLOTLIB' in analyst_section or 'matplotlib' in analyst_section.lower(), \
            "Should mention MATPLOTLIB dependency"

        # ASSERT - git-commit skill shows its dependencies
        assert '**git-commit**' in markdown, "Should list git-commit skill"
        git_commit_section = markdown[markdown.index('**git-commit**'):markdown.index('**git-commit**') + 500]
        assert 'Dependencies:' in git_commit_section or 'Loads:' in git_commit_section, \
            "git-commit skill should show dependencies"
        assert 'FAIL-FAST' in git_commit_section or 'fail-fast' in git_commit_section.lower(), \
            "Should mention FAIL-FAST dependency"

        # ASSERT - /dev command shows its load_instructions.py dependencies
        assert '**/dev**' in markdown or '**dev**' in markdown, "Should list dev command"
        # Find dev command (with or without /)
        if '**/dev**' in markdown:
            dev_section_start = markdown.index('**/dev**')
        else:
            dev_section_start = markdown.index('**dev**')
        dev_section = markdown[dev_section_start:dev_section_start + 500]
        assert 'Loads:' in dev_section or 'Dependencies:' in dev_section, \
            "dev command should show loaded instructions"
        assert 'DEVELOPMENT.md' in dev_section or 'TESTING.md' in dev_section, \
            "Should mention loaded instruction files"
        assert '3-tier' in dev_section or 'framework' in dev_section or 'personal' in dev_section or 'project' in dev_section, \
            "Should indicate 3-tier loading pattern"

    def test_markdown_includes_reverse_dependency_index(self, repo_root):
        """
        VALIDATES: Markdown generator includes reverse index showing which components use each instruction file.

        Test structure:
        - Scan repository to get all components and dependencies
        - Generate markdown section
        - Verify "Instruction Files" section exists
        - Verify instruction files listed with their consumers

        This verifies:
        - Reverse index section appears in markdown
        - Instruction files grouped by type (chunks, core, etc.)
        - Each file shows which components use it
        - Format: "FILENAME.md - Used by: skill1, skill2, command1"
        """
        # ARRANGE - Scan and generate markdown
        import sys
        from pathlib import Path

        repo_scripts = repo_root / 'scripts'
        if str(repo_scripts) not in sys.path:
            sys.path.insert(0, str(repo_scripts))

        from generate_instruction_tree import scan_repository, generate_markdown_tree

        components = scan_repository(repo_root)
        markdown = generate_markdown_tree(components, repo_root)

        # ASSERT - Reverse index section exists
        assert '### Instruction Files' in markdown or '## Instruction Files' in markdown, \
            "Should have Instruction Files reverse index section"

        # ASSERT - Find the instruction files section
        if '### Instruction Files' in markdown:
            files_section_start = markdown.index('### Instruction Files')
        else:
            files_section_start = markdown.index('## Instruction Files')

        files_section = markdown[files_section_start:]

        # ASSERT - MATPLOTLIB.md shows analyst skill as consumer
        assert 'MATPLOTLIB.md' in files_section or 'matplotlib' in files_section.lower(), \
            "Should list MATPLOTLIB.md instruction file"
        # Find MATPLOTLIB section and check for analyst
        if 'MATPLOTLIB.md' in files_section:
            matplotlib_line = files_section[files_section.index('MATPLOTLIB.md'):files_section.index('MATPLOTLIB.md') + 200]
            assert 'analyst' in matplotlib_line.lower(), \
                "MATPLOTLIB.md should show analyst skill as user"

        # ASSERT - FAIL-FAST.md shows git-commit skill as consumer
        assert 'FAIL-FAST.md' in files_section or 'fail-fast' in files_section.lower(), \
            "Should list FAIL-FAST.md instruction file"
        if 'FAIL-FAST.md' in files_section:
            failfast_line = files_section[files_section.index('FAIL-FAST.md'):files_section.index('FAIL-FAST.md') + 200]
            assert 'git-commit' in failfast_line, \
                "FAIL-FAST.md should show git-commit skill as user"

        # ASSERT - DEVELOPMENT.md shows /dev command as consumer
        assert 'DEVELOPMENT.md' in files_section, \
            "Should list DEVELOPMENT.md instruction file"
        dev_line = files_section[files_section.index('DEVELOPMENT.md'):files_section.index('DEVELOPMENT.md') + 200]
        assert '/dev' in dev_line or 'dev command' in dev_line.lower(), \
            "DEVELOPMENT.md should show /dev command as user"

    def test_scanner_finds_all_instruction_files_including_orphans(self, repo_root):
        """
        VALIDATES: Scanner discovers ALL instruction files, not just those referenced by components.

        Test structure:
        - Scan repository to get all instruction files
        - Verify ALL 21 expected .md files found:
          * core/*.md (6 files)
          * chunks/*.md (4 files)
          * docs/_CHUNKS/*.md (11 files)
        - Includes orphaned files with no references

        This verifies:
        - Complete file discovery in core/, chunks/, docs/_CHUNKS/
        - Orphaned files not missed (HYDRA.md, DBT.md, etc.)
        - Result includes 'all_instruction_files' key with complete list
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

        # ASSERT - Scanner returns all_instruction_files key
        assert 'all_instruction_files' in components, \
            "Scanner should return 'all_instruction_files' with complete file list"

        all_files = components['all_instruction_files']
        file_names = [Path(f).name for f in all_files]

        # ASSERT - Core files present (6 files)
        assert '_CORE.md' in file_names, "Should find _CORE.md"
        assert 'DEBUGGING.md' in file_names, "Should find DEBUGGING.md"
        assert 'DEVELOPMENT.md' in file_names, "Should find DEVELOPMENT.md"
        assert 'INSTRUCTIONS.md' in file_names, "Should find INSTRUCTIONS.md"
        assert 'STYLE.md' in file_names, "Should find STYLE.md"
        assert 'TESTING.md' in file_names, "Should find TESTING.md"

        # ASSERT - Chunks files present (4 files)
        assert 'AGENT-BEHAVIOR.md' in file_names, "Should find AGENT-BEHAVIOR.md"
        assert 'AXIOMS.md' in file_names, "Should find AXIOMS.md"
        assert 'INFRASTRUCTURE.md' in file_names, "Should find INFRASTRUCTURE.md"
        assert 'SKILL-PRIMER.md' in file_names, "Should find SKILL-PRIMER.md"

        # ASSERT - docs/_CHUNKS files present (11 files) - includes orphans!
        assert 'DBT.md' in file_names, "Should find DBT.md (orphan)"
        assert 'E2E-TESTING.md' in file_names, "Should find E2E-TESTING.md (orphan)"
        assert 'FAIL-FAST.md' in file_names, "Should find FAIL-FAST.md"
        assert 'GIT-WORKFLOW.md' in file_names, "Should find GIT-WORKFLOW.md"
        assert 'HYDRA.md' in file_names, "Should find HYDRA.md (orphan)"
        assert 'MATPLOTLIB.md' in file_names, "Should find MATPLOTLIB.md"
        assert 'PYTHON-DEV.md' in file_names, "Should find PYTHON-DEV.md"
        assert 'README.md' in file_names, "Should find README.md (orphan)"
        assert 'SEABORN.md' in file_names, "Should find SEABORN.md"
        assert 'STATSMODELS.md' in file_names, "Should find STATSMODELS.md"
        assert 'STREAMLIT.md' in file_names, "Should find STREAMLIT.md (orphan)"
        assert 'TESTS.md' in file_names, "Should find TESTS.md"

        # ASSERT - Total count correct (21 files)
        assert len(all_files) >= 21, f"Should find at least 21 instruction files, found {len(all_files)}"

    def test_compact_format_truncates_descriptions_to_7_words(self, repo_root):
        """
        VALIDATES: Compact format truncates descriptions to ~7 words max for scanability.

        Test structure:
        - Scan repository to get components
        - Generate compact markdown format
        - Verify descriptions truncated to first clause (5-7 words)
        - Verify format: "- NAME - Short description"
        - Verify full descriptions NOT present in output

        This verifies:
        - Compact format enabled via parameter
        - Descriptions truncated at first meaningful clause
        - No file paths shown in compact mode
        - Format optimized for quick scanning
        """
        # ARRANGE - Import functions
        import sys
        from pathlib import Path

        repo_scripts = repo_root / 'scripts'
        if str(repo_scripts) not in sys.path:
            sys.path.insert(0, str(repo_scripts))

        from generate_instruction_tree import scan_repository, generate_markdown_tree

        components = scan_repository(repo_root)

        # ACT - Generate markdown in compact format
        markdown = generate_markdown_tree(components, repo_root, compact=True)

        # ASSERT - Verify compact format structure
        assert '### Agents' in markdown, "Should have Agents section"

        # ASSERT - Verify DEVELOPER agent has truncated description (no full description)
        dev_agent = next((a for a in components['agents'] if a['name'] == 'DEVELOPER'), None)
        assert dev_agent is not None, "DEVELOPER agent should exist"
        full_description = dev_agent['description']

        # Full description should NOT appear in compact output
        assert full_description not in markdown, \
            f"Compact format should not include full description: {full_description}"

        # ASSERT - Verify compact format: "- DEVELOPER - A specialized developer. Your purpose is to write"
        assert '- DEVELOPER -' in markdown, "Should have compact format prefix"
        dev_line_start = markdown.index('- DEVELOPER -')
        dev_line_end = markdown.index('\n', dev_line_start)
        dev_line = markdown[dev_line_start:dev_line_end]

        # Count words in description part (after "- DEVELOPER - ")
        # Format is: "- DEVELOPER - Description text here"
        # After the agent name and dash, we get the description
        parts = dev_line.split(' - ', 1)  # Split on first " - "
        assert len(parts) == 2, f"Expected format '- NAME - description', got: {dev_line}"
        description_part = parts[1].strip()
        word_count = len(description_part.split())
        assert word_count <= 10, f"Description should be <=10 words, got {word_count}: {description_part}"

        # ASSERT - No file paths in compact mode
        assert '`agents/DEVELOPER.md`' not in markdown, \
            "Compact format should not include file paths"

        # ASSERT - Verify test-writing skill has truncated description
        test_skill = next((s for s in components['skills'] if s['name'] == 'test-writing'), None)
        assert test_skill is not None, "test-writing skill should exist"
        full_skill_description = test_skill['description']

        # Full description should NOT appear
        assert full_skill_description not in markdown, \
            f"Compact format should not include full skill description: {full_skill_description}"

        # ASSERT - Verify analyst skill shows dependencies inline
        assert '- analyst -' in markdown, "Should list analyst skill"
        analyst_line_start = markdown.index('- analyst -')
        analyst_line_end = markdown.index('\n', analyst_line_start)
        analyst_line = markdown[analyst_line_start:analyst_line_end]

        # Dependencies should appear inline in compact format
        assert 'MATPLOTLIB' in analyst_line or 'matplotlib' in analyst_line.lower(), \
            "Compact format should show dependencies inline"

    def test_compact_format_includes_instruction_flow_tree(self, repo_root):
        """
        VALIDATES: Compact format includes instruction flow tree showing file dependencies.

        Test structure:
        - Scan repository to get components
        - Generate compact markdown with instruction flow
        - Verify "### Instruction Flow" section exists
        - Verify tree format with └─ and ├─ symbols
        - Verify SessionStart section shows core/_CORE.md dependencies
        - Verify /dev command section shows loaded files
        - Verify skill sections show their dependencies

        This verifies:
        - Instruction Flow section appears in compact format
        - Tree visualization uses proper Unicode box drawing characters
        - Dependencies grouped by loading context (SessionStart, commands, skills)
        - Clear hierarchy showing file relationships
        """
        # ARRANGE - Import functions
        import sys
        from pathlib import Path

        repo_scripts = repo_root / 'scripts'
        if str(repo_scripts) not in sys.path:
            sys.path.insert(0, str(repo_scripts))

        from generate_instruction_tree import scan_repository, generate_markdown_tree

        components = scan_repository(repo_root)

        # ACT - Generate compact markdown (should include instruction flow)
        markdown = generate_markdown_tree(components, repo_root, compact=True)

        # ASSERT - Instruction Flow section exists
        assert '### Instruction Flow' in markdown or '## Instruction Flow' in markdown, \
            "Compact format should include Instruction Flow section"

        # ASSERT - Find instruction flow section
        if '### Instruction Flow' in markdown:
            flow_start = markdown.index('### Instruction Flow')
        else:
            flow_start = markdown.index('## Instruction Flow')

        flow_section = markdown[flow_start:]

        # ASSERT - Tree format with Unicode box drawing characters
        assert '└─' in flow_section or '├─' in flow_section, \
            "Instruction flow should use tree visualization characters"

        # ASSERT - SessionStart section showing core/_CORE.md
        assert 'SessionStart' in flow_section or 'session start' in flow_section.lower(), \
            "Should show SessionStart instruction loading"
        assert '_CORE.md' in flow_section, \
            "Should show core/_CORE.md loaded at SessionStart"

        # ASSERT - core/_CORE.md shows its chunk dependencies
        assert 'AXIOMS.md' in flow_section, \
            "Should show AXIOMS.md as dependency of _CORE.md"
        assert 'INFRASTRUCTURE.md' in flow_section, \
            "Should show INFRASTRUCTURE.md as dependency of _CORE.md"
        assert 'AGENT-BEHAVIOR.md' in flow_section, \
            "Should show AGENT-BEHAVIOR.md as dependency of _CORE.md"

        # ASSERT - /dev command shows loaded instructions
        assert '/dev' in flow_section or 'dev command' in flow_section.lower(), \
            "Should show /dev command instruction loading"
        assert 'DEVELOPMENT.md' in flow_section or 'TESTING.md' in flow_section, \
            "Should show instruction files loaded by /dev command"

        # ASSERT - Skills section shows dependencies
        assert 'analyst' in flow_section.lower(), \
            "Should show analyst skill dependencies"
        assert 'MATPLOTLIB' in flow_section or 'matplotlib' in flow_section.lower(), \
            "Should show MATPLOTLIB.md dependency for analyst skill"

    def test_compact_format_includes_quick_stats_with_orphan_detection(self, repo_root):
        """
        VALIDATES: Compact format includes Quick Stats section with orphan detection.

        Test structure:
        - Scan repository to get all components and instruction files
        - Generate compact markdown with Quick Stats
        - Verify "### Quick Stats" section exists BEFORE component listings
        - Verify counts displayed (agents, skills, commands, hooks, instruction files)
        - Verify orphaned files detected and listed with ⚠️ marker
        - Verify potential overlaps detected (e.g., scribe vs task-manager)

        This verifies:
        - Quick Stats section appears at top of compact format
        - Component counts displayed
        - Orphaned instruction files identified (files in chunks/docs/_CHUNKS not referenced)
        - Overlap warnings for similar agent/skill responsibilities
        - Warning markers (⚠️) prominently displayed
        """
        # ARRANGE - Import functions
        import sys
        from pathlib import Path

        repo_scripts = repo_root / 'scripts'
        if str(repo_scripts) not in sys.path:
            sys.path.insert(0, str(repo_scripts))

        from generate_instruction_tree import scan_repository, generate_markdown_tree

        components = scan_repository(repo_root)

        # ACT - Generate compact markdown (should include Quick Stats)
        markdown = generate_markdown_tree(components, repo_root, compact=True)

        # ASSERT - Quick Stats section exists
        assert '### Quick Stats' in markdown or '## Quick Stats' in markdown, \
            "Compact format should include Quick Stats section"

        # ASSERT - Quick Stats appears BEFORE Agents section
        stats_idx = markdown.index('Quick Stats')
        agents_idx = markdown.index('### Agents')
        assert stats_idx < agents_idx, \
            "Quick Stats should appear before component listings"

        # ASSERT - Find Quick Stats section
        if '### Quick Stats' in markdown:
            stats_start = markdown.index('### Quick Stats')
        else:
            stats_start = markdown.index('## Quick Stats')

        stats_end = markdown.index('### Agents')
        stats_section = markdown[stats_start:stats_end]

        # ASSERT - Component counts displayed
        assert 'agents' in stats_section.lower(), "Should show agent count"
        assert 'skills' in stats_section.lower(), "Should show skill count"
        assert 'commands' in stats_section.lower(), "Should show command count"
        assert 'hooks' in stats_section.lower(), "Should show hook count"
        assert 'instruction' in stats_section.lower(), "Should show instruction file count"

        # ASSERT - Orphaned files section with warning marker
        assert '⚠️' in stats_section or 'orphan' in stats_section.lower(), \
            "Should flag orphaned files with warning marker or label"

        # Known orphans from repository:
        # - HYDRA.md (not loaded by any component)
        # - DBT.md (not loaded by any component)
        # - E2E-TESTING.md (not loaded by any component)
        # - STREAMLIT.md (not loaded by any component)
        if 'orphan' in stats_section.lower():
            assert 'HYDRA' in stats_section or 'DBT' in stats_section or 'E2E-TESTING' in stats_section, \
                "Should list known orphaned instruction files"

        # ASSERT - Potential overlaps detected (optional - if implemented)
        # Example overlap: scribe vs task-manager (both extract tasks)
        if 'overlap' in stats_section.lower() or '⚠️ OVERLAP' in stats_section:
            # If overlap detection implemented, verify format
            assert 'scribe' in stats_section.lower() or 'task-manager' in stats_section.lower() or 'task' in stats_section.lower(), \
                "Should mention components with potential overlap"
