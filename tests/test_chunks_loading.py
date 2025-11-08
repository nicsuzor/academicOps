"""Integration tests for chunks architecture using live Claude Code headless mode.

These tests verify that the modular chunks architecture actually works by:
1. Running Claude Code CLI in headless mode (--print)
2. Making real Claude API calls (not mocked)
3. Verifying chunks content appears in agent's actual context
4. Testing both main agent (SessionStart) and skills (resources/ symlinks)

Test approach:
- Create isolated test repository with academicOps setup
- Run `claude --print "verify you know about [X]"`
- Check response contains unique content from chunks/
- Fail fast if infrastructure broken

Status: TDD - Writing failing tests first
"""

import json
import os
import subprocess

import pytest


@pytest.mark.timeout(60)  # Claude API calls need more time than default 10s
class TestChunksLoadingInfrastructure:
    """Test that chunks load into agent context via @references and symlinks."""

    def test_axioms_chunk_loads_via_core_reference(self, tmp_path):
        """
        VALIDATES: AXIOMS.md content loads into agent context via _CORE.md @reference

        Test structure:
        - Create test repo with academicOps-style structure
        - core/_CORE.md contains @../chunks/AXIOMS.md
        - chunks/AXIOMS.md contains unique content "Core Axioms (Inviolable Rules)"
        - Run claude --print asking agent to confirm knowledge
        - Agent response should include axioms content

        This verifies:
        - @reference resolution works
        - SessionStart hooks load _CORE.md
        - Chunks content reaches agent context
        - Full chain: SessionStart -> _CORE.md -> @../chunks/AXIOMS.md -> agent memory
        """
        # ARRANGE - Set up test repository structure
        test_repo = tmp_path / "test_project"
        test_repo.mkdir()

        # Create academicOps-style directory structure
        (test_repo / "core").mkdir()
        (test_repo / "chunks").mkdir()

        # Create chunks/AXIOMS.md with unique testable content
        axioms_content = """# Universal Principles

## Core Axioms (Inviolable Rules)

1. **DO ONE THING** - Complete the task requested, then STOP.
2. **Namespace Separation**: NEVER mix agent instructions with human documentation
3. **Fail-Fast Philosophy (Code)**: No defaults, no fallbacks, no workarounds
"""
        (test_repo / "chunks" / "AXIOMS.md").write_text(axioms_content)

        # Create core/_CORE.md with @reference to chunks
        core_content = """# Generic Agent Instructions

## Universal Principles

@../chunks/AXIOMS.md
"""
        (test_repo / "core" / "_CORE.md").write_text(core_content)

        # Create minimal .claude/settings.json with SessionStart hook
        claude_dir = test_repo / ".claude"
        claude_dir.mkdir()

        settings = {
            "hooks": {
                "SessionStart": [
                    {
                        "matcher": {"type": "all"},
                        "context": [{"type": "file", "path": "core/_CORE.md"}],
                    }
                ]
            }
        }
        (claude_dir / "settings.json").write_text(json.dumps(settings, indent=2))

        # ACT - Run Claude Code in headless mode asking about axioms
        prompt = "List the first 3 Core Axioms you know about. Just list them briefly."

        result = subprocess.run(
            ["claude", "--print", "--output-format", "text", prompt],
            check=False,
            cwd=test_repo,
            capture_output=True,
            text=True,
            timeout=30,
            env={**os.environ, "CLAUDE_CODE_ENABLE_TELEMETRY": "0"},
        )

        # ASSERT - Verify chunks content loaded into agent context
        assert result.returncode == 0, f"Claude CLI failed: {result.stderr}"

        response = result.stdout.lower()

        # Check for evidence that AXIOMS.md content was loaded
        # Agent should mention the axioms if it has access to them
        assert "do one thing" in response or "one thing" in response, (
            f"Agent doesn't know about 'DO ONE THING' axiom. Response: {result.stdout}"
        )

        # Additional check - should know about fail-fast
        assert "fail" in response and "fast" in response, (
            f"Agent doesn't know about 'Fail-Fast' axiom. Response: {result.stdout}"
        )

    def test_infrastructure_chunk_loads_via_core_reference(self, tmp_path):
        """
        VALIDATES: INFRASTRUCTURE.md content loads via _CORE.md @reference

        Similar to axioms test but for different chunk.
        Verifies the @reference mechanism works for multiple chunks.
        """
        # ARRANGE - Set up test repository
        test_repo = tmp_path / "test_project"
        test_repo.mkdir()

        (test_repo / "core").mkdir()
        (test_repo / "chunks").mkdir()

        # Create chunks/INFRASTRUCTURE.md with unique content
        infra_content = """# Framework Infrastructure

## Environment Variables

- AOPS - Points to framework root
- ACA - Points to personal repository

## Directory Structure

Framework provides agents, skills, commands, hooks.
"""
        (test_repo / "chunks" / "INFRASTRUCTURE.md").write_text(infra_content)

        # Create core/_CORE.md referencing infrastructure
        core_content = """# Generic Agent Instructions

## Framework Infrastructure

@../chunks/INFRASTRUCTURE.md
"""
        (test_repo / "core" / "_CORE.md").write_text(core_content)

        # Create SessionStart hook
        claude_dir = test_repo / ".claude"
        claude_dir.mkdir()

        settings = {
            "hooks": {
                "SessionStart": [
                    {
                        "matcher": {"type": "all"},
                        "context": [{"type": "file", "path": "core/_CORE.md"}],
                    }
                ]
            }
        }
        (claude_dir / "settings.json").write_text(json.dumps(settings, indent=2))

        # ACT - Ask Claude about environment variables
        prompt = "What is the AOPS environment variable used for? Brief answer."

        result = subprocess.run(
            ["claude", "--print", "--output-format", "text", prompt],
            check=False,
            cwd=test_repo,
            capture_output=True,
            text=True,
            timeout=30,
            env={**os.environ, "CLAUDE_CODE_ENABLE_TELEMETRY": "0"},
        )

        # ASSERT - Verify infrastructure content loaded
        assert result.returncode == 0, f"Claude CLI failed: {result.stderr}"

        response = result.stdout.lower()

        # Should know what AOPS is for
        assert "academicops" in response, (
            f"Agent doesn't know about AOPS variable. Response: {result.stdout}"
        )

        assert "framework" in response or "root" in response, (
            f"Agent doesn't understand AOPS purpose. Response: {result.stdout}"
        )

    def test_skill_resources_symlinks_load_chunks(self, tmp_path):
        """
        VALIDATES: Skill resources/ symlinks load chunks when skill invoked

        Test structure:
        - Create skill with resources/ directory
        - resources/AXIOMS.md -> symlink to chunks/AXIOMS.md
        - Skill SKILL.md contains @resources/AXIOMS.md
        - Invoke skill via Skill tool
        - Verify agent has axioms content

        This verifies:
        - Symlinks resolve correctly
        - Skills can access chunks via resources/
        - @resources/ references work in skills
        """
        # ARRANGE - Set up test repository with skill structure
        test_repo = tmp_path / "test_framework"
        test_repo.mkdir()

        # Create chunks directory with AXIOMS.md
        chunks_dir = test_repo / "chunks"
        chunks_dir.mkdir()

        axioms_content = """# Universal Principles

## Core Axioms (Inviolable Rules)

1. **DO ONE THING** - Complete the task requested, then STOP.
2. **Fail-Fast Philosophy**: No defaults, no fallbacks, no workarounds
3. **Use Standard Tools**: Never reinvent when industry standard exists
"""
        (chunks_dir / "AXIOMS.md").write_text(axioms_content)

        # Create skill structure in .claude/skills/
        claude_dir = test_repo / ".claude"
        claude_dir.mkdir()
        skills_dir = claude_dir / "skills"
        skills_dir.mkdir()
        test_skill_dir = skills_dir / "test-skill"
        test_skill_dir.mkdir()

        # Create resources/ directory with symlink to chunks
        resources_dir = test_skill_dir / "resources"
        resources_dir.mkdir()

        # Create symlink: resources/AXIOMS.md -> ../../../chunks/AXIOMS.md
        axioms_symlink = resources_dir / "AXIOMS.md"
        axioms_symlink.symlink_to("../../../chunks/AXIOMS.md")

        # Create SKILL.md that references resources/AXIOMS.md
        skill_content = """---
name: test-skill
description: Test skill for verifying chunk loading
---

# Test Skill

## Framework Context

@resources/AXIOMS.md

## Task

When asked about axioms, list the core axioms you know from your instructions.
"""
        (test_skill_dir / "SKILL.md").write_text(skill_content)

        # ACT - Invoke skill asking about axioms
        prompt = "Use the test-skill skill. List the first 2 Core Axioms. Be brief."

        result = subprocess.run(
            ["claude", "--print", "--output-format", "text", prompt],
            check=False,
            cwd=test_repo,
            capture_output=True,
            text=True,
            timeout=45,
            env={**os.environ, "CLAUDE_CODE_ENABLE_TELEMETRY": "0"},
        )

        # ASSERT - Verify chunks content loaded via symlink
        assert result.returncode == 0, f"Claude CLI failed: {result.stderr}"

        response = result.stdout.lower()

        # Should know about DO ONE THING axiom from symlinked resource
        assert "do one thing" in response or "one thing" in response, (
            f"Skill doesn't have access to AXIOMS via symlink. Response: {result.stdout}"
        )

        # Should know about fail-fast
        assert "fail" in response, (
            f"Skill doesn't know about Fail-Fast axiom. Response: {result.stdout}"
        )

    def test_academicops_env_var_available_to_agent(self, tmp_path):
        """
        VALIDATES: $AOPS environment variable available to agent

        Test structure:
        - Set AOPS env var pointing to test framework
        - Run claude --print asking agent to use the variable
        - Verify agent can access and use it correctly

        This verifies:
        - Environment variables passed through to agent
        - Agent can reference $AOPS in context
        - Framework paths resolve correctly
        """
        # ARRANGE - Set up test framework directory
        test_framework = tmp_path / "academicops_test"
        test_framework.mkdir()

        # Create a marker file that agent can verify exists
        (test_framework / "FRAMEWORK_MARKER.txt").write_text(
            "This is the framework root"
        )

        # Create chunks directory
        chunks_dir = test_framework / "chunks"
        chunks_dir.mkdir()
        (chunks_dir / "TEST.md").write_text(
            "# Test Chunk\n\nThis file exists in framework."
        )

        # ACT - Run Claude with AOPS pointing to test framework
        prompt = (
            "What is the value of the AOPS environment variable? Just state the path."
        )

        env = os.environ.copy()
        env["AOPS"] = str(test_framework)
        env["CLAUDE_CODE_ENABLE_TELEMETRY"] = "0"

        result = subprocess.run(
            ["claude", "--print", "--output-format", "text", prompt],
            check=False,
            cwd=tmp_path,
            capture_output=True,
            text=True,
            timeout=30,
            env=env,
        )

        # ASSERT - Verify agent knows about AOPS
        assert result.returncode == 0, f"Claude CLI failed: {result.stderr}"

        response = result.stdout

        # Agent should mention the environment variable or its value
        # Note: Claude may or may not have direct access to env vars, so we test what it knows
        assert "academicops" in response.lower() or str(test_framework) in response, (
            f"Agent doesn't seem to know about AOPS. Response: {result.stdout}"
        )
