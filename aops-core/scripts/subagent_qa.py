#!/usr/bin/env python3
"""
Subagent QA Tool

Test any framework subagent by showing the context it would receive and
optionally invoking the LLM to see its response.

Supported subagents:
- hydrator: Builds full hydration context from loaders
- critic: Reviews plans/conclusions (pass context directly)
- custodiet: Compliance checking (pass audit file path)
- qa: End-to-end verification
- butler: Framework coordination
- Any other: Pass context directly via --context or --context-file

Usage:
    # Test hydrator (default)
    uv run python scripts/subagent_qa.py "your test prompt"

    # Test critic with a plan
    uv run python scripts/subagent_qa.py --subagent critic --context "Review this plan: ..."

    # Test custodiet with audit file
    uv run python scripts/subagent_qa.py --subagent custodiet --context-file /path/to/audit.md

    # Run the subagent and see response
    uv run python scripts/subagent_qa.py "test prompt" --run
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# Add framework roots to path for lib imports
SCRIPT_DIR = Path(__file__).parent.resolve()
AOPS_CORE_ROOT = SCRIPT_DIR.parent
FRAMEWORK_ROOT = AOPS_CORE_ROOT.parent

sys.path.insert(0, str(FRAMEWORK_ROOT))
sys.path.insert(0, str(AOPS_CORE_ROOT))

# Agent configurations
AGENTS_DIR = AOPS_CORE_ROOT / "agents"
HOOK_DIR = AOPS_CORE_ROOT / "hooks"

# Model mapping (from agent frontmatter)
AGENT_MODELS = {
    "prompt-hydrator": "claude-3-5-haiku-latest",
    "hydrator": "claude-3-5-haiku-latest",
    "custodiet": "claude-3-5-haiku-latest",
    "critic": "claude-opus-4-20250514",
    "qa": "claude-3-5-haiku-latest",
    "butler": "claude-3-5-haiku-latest",
    "effectual-planner": "claude-3-5-haiku-latest",
}

# Aliases
AGENT_ALIASES = {
    "hydrator": "prompt-hydrator",
}


def get_agent_name(subagent: str) -> str:
    """Resolve agent alias to canonical name."""
    return AGENT_ALIASES.get(subagent, subagent)


def get_agent_model(subagent: str) -> str:
    """Get the model for a subagent."""
    canonical = get_agent_name(subagent)
    return AGENT_MODELS.get(canonical, "claude-3-5-haiku-latest")


def load_agent_system_prompt(subagent: str) -> str:
    """Load the agent system prompt from its definition file."""
    canonical = get_agent_name(subagent)
    agent_file = AGENTS_DIR / f"{canonical}.md"

    if not agent_file.exists():
        return f"ERROR: Agent file not found: {agent_file}"

    content = agent_file.read_text(encoding="utf-8")
    # Remove frontmatter
    if content.startswith("---"):
        end = content.find("---", 3)
        if end != -1:
            content = content[end + 3:].strip()
    return content


def build_hydrator_context(prompt: str, session_context: str = "") -> str:
    """
    Build the hydration context for the prompt-hydrator agent.

    This mirrors build_hydration_instruction() but returns just the context.
    """
    from lib.file_index import get_formatted_relevant_paths
    from lib.hydration.context_loaders import (
        get_task_work_state,
        load_glossary,
        load_mcp_tools_context,
        load_project_context_index,
        load_project_paths_context,
        load_project_rules,
        load_scripts_index,
        load_skills_index,
        load_workflows_index,
    )
    from lib.template_loader import load_template

    context_template_file = HOOK_DIR / "templates" / "prompt-hydrator-context.md"

    # Load all context components
    glossary = load_glossary()
    mcp_tools = load_mcp_tools_context()
    project_paths = load_project_paths_context()
    workflows_index = load_workflows_index(prompt)
    skills_index = load_skills_index()
    scripts_index = load_scripts_index()
    project_rules = load_project_rules()
    task_state = get_task_work_state()
    relevant_files = get_formatted_relevant_paths(prompt, max_files=10)
    project_context_index = load_project_context_index()

    # Build full context
    context_template = load_template(context_template_file)
    full_context = context_template.format(
        prompt=prompt,
        session_context=session_context,
        glossary=glossary,
        framework_paths="",
        mcp_tools=mcp_tools,
        env_vars="",
        project_paths=project_paths,
        project_context_index=project_context_index,
        project_rules=project_rules,
        relevant_files=relevant_files,
        workflows_index=workflows_index,
        skills_index=skills_index,
        scripts_index=scripts_index,
        task_state=task_state,
    )
    return full_context


def build_context(
    subagent: str,
    prompt: str | None = None,
    context: str | None = None,
    context_file: Path | None = None,
    session_context: str = "",
) -> str:
    """
    Build context for any subagent.

    Args:
        subagent: The subagent type
        prompt: Test prompt (for hydrator)
        context: Direct context string
        context_file: Path to context file
        session_context: Optional session context

    Returns:
        The context string to feed to the subagent
    """
    canonical = get_agent_name(subagent)

    # If context file provided, read it
    if context_file:
        if not context_file.exists():
            return f"ERROR: Context file not found: {context_file}"
        return context_file.read_text(encoding="utf-8")

    # If direct context provided, use it
    if context:
        return context

    # Special handling for hydrator - build full context
    if canonical == "prompt-hydrator":
        if not prompt:
            return "ERROR: Hydrator requires a prompt argument"
        return build_hydrator_context(prompt, session_context)

    # For other agents, require explicit context
    if prompt:
        # Use prompt as context for non-hydrator agents
        return prompt

    return "ERROR: No context provided. Use --context, --context-file, or provide a prompt."


def build_api_request(model: str, system_prompt: str, user_content: str) -> dict:
    """Build the API request that would be sent."""
    return {
        "model": model,
        "max_tokens": 4096,
        "system": system_prompt[:500] + "..." if len(system_prompt) > 500 else system_prompt,
        "messages": [
            {
                "role": "user",
                "content": user_content[:500] + "..." if len(user_content) > 500 else user_content,
            }
        ],
        "_note": "Truncated for display. Full content shown in context section.",
    }


def call_llm(model: str, system_prompt: str, user_content: str) -> str:
    """
    Call the appropriate LLM model.

    Args:
        model: Model identifier
        system_prompt: The system prompt
        user_content: The user content

    Returns:
        The model's response text
    """
    try:
        import anthropic
    except ImportError:
        return "ERROR: anthropic package not installed. Run: uv add anthropic"

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return (
            "ERROR: ANTHROPIC_API_KEY environment variable not set.\n"
            "Set it with: export ANTHROPIC_API_KEY='your-key'"
        )

    client = anthropic.Anthropic(api_key=api_key)

    try:
        response = client.messages.create(
            model=model,
            max_tokens=4096,
            system=system_prompt,
            messages=[{"role": "user", "content": user_content}],
        )
        return response.content[0].text
    except anthropic.APIConnectionError:
        return "ERROR: Could not connect to Anthropic API. Check your network."
    except anthropic.RateLimitError:
        return "ERROR: Rate limited. Wait and try again."
    except anthropic.APIStatusError as e:
        return f"ERROR: API error {e.status_code}: {e.message}"
    except Exception as e:
        return f"ERROR: Unexpected error: {type(e).__name__}: {e}"


def list_agents() -> str:
    """List available agents."""
    lines = ["Available subagents:"]
    for agent_file in sorted(AGENTS_DIR.glob("*.md")):
        name = agent_file.stem
        model = AGENT_MODELS.get(name, "haiku")
        lines.append(f"  - {name} (model: {model})")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Test any framework subagent by showing context and optionally running it",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Test hydrator (default)
    uv run python scripts/subagent_qa.py "add a new test"

    # Test critic with a plan
    uv run python scripts/subagent_qa.py --subagent critic --context "Review this plan: ..."

    # Test custodiet with audit file
    uv run python scripts/subagent_qa.py --subagent custodiet --context-file /tmp/audit.md

    # Run the subagent and see response
    uv run python scripts/subagent_qa.py "test prompt" --run

    # List available agents
    uv run python scripts/subagent_qa.py --list
        """,
    )

    parser.add_argument(
        "prompt",
        nargs="?",
        help="Test prompt (required for hydrator, optional for others)",
    )
    parser.add_argument(
        "--subagent",
        "-a",
        default="hydrator",
        help="Subagent to test (default: hydrator)",
    )
    parser.add_argument(
        "--context",
        "-c",
        help="Direct context to pass to the subagent",
    )
    parser.add_argument(
        "--context-file",
        "-f",
        metavar="PATH",
        help="Path to file containing context for the subagent",
    )
    parser.add_argument(
        "--run",
        "-r",
        action="store_true",
        help="Invoke the LLM and show the response",
    )
    parser.add_argument(
        "--dry-run",
        "-d",
        action="store_true",
        help="Show API request that would be made, without calling",
    )
    parser.add_argument(
        "--save",
        "-s",
        metavar="FILE",
        help="Save output to a file instead of stdout",
    )
    parser.add_argument(
        "--session-file",
        metavar="PATH",
        help="Path to session JSONL file for session context (hydrator only)",
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress informational messages",
    )
    parser.add_argument(
        "--list",
        "-l",
        action="store_true",
        help="List available subagents",
    )

    args = parser.parse_args()

    # Handle --list
    if args.list:
        print(list_agents())
        return 0

    # Validate args
    if not args.prompt and not args.context and not args.context_file:
        parser.error("Provide a prompt, --context, or --context-file")

    # Load session context if provided
    session_context = ""
    if args.session_file:
        session_path = Path(args.session_file)
        if not session_path.exists():
            print(f"ERROR: Session file not found: {session_path}", file=sys.stderr)
            return 1
        try:
            from lib.session_reader import extract_router_context

            ctx = extract_router_context(session_path)
            session_context = f"\n\n{ctx}" if ctx else ""
        except Exception as e:
            session_context = f"\n\n## Session Context (Error)\n\nFailed to extract: {e}"

    # Build context
    if not args.quiet:
        print(f"Building context for {args.subagent}...", file=sys.stderr)

    context_file_path = Path(args.context_file) if args.context_file else None
    context = build_context(
        args.subagent,
        prompt=args.prompt,
        context=args.context,
        context_file=context_file_path,
        session_context=session_context,
    )

    if context.startswith("ERROR:"):
        print(context, file=sys.stderr)
        return 1

    # Load agent system prompt
    agent_prompt = load_agent_system_prompt(args.subagent)
    if agent_prompt.startswith("ERROR:"):
        print(agent_prompt, file=sys.stderr)
        return 1

    model = get_agent_model(args.subagent)

    # Build output
    output_parts = []
    output_parts.append("# Subagent QA Report\n")
    output_parts.append(f"**Subagent:** {args.subagent}")
    output_parts.append(f"**Model:** {model}")
    if args.prompt:
        output_parts.append(f"**Prompt:** {args.prompt}")
    output_parts.append("")

    output_parts.append("## Context (Input to Subagent)\n")
    output_parts.append("```markdown")
    output_parts.append(context)
    output_parts.append("```\n")

    # Handle dry-run
    if args.dry_run:
        output_parts.append("\n## API Request (Dry Run)\n")
        api_request = build_api_request(model, agent_prompt, context)
        output_parts.append("```json")
        output_parts.append(json.dumps(api_request, indent=2))
        output_parts.append("```\n")

    # Handle actual run
    if args.run:
        if not args.quiet:
            print(f"Invoking {model}...", file=sys.stderr)

        response = call_llm(model, agent_prompt, context)

        output_parts.append(f"\n## {args.subagent.title()} Response\n")
        output_parts.append(response)

    output = "\n".join(output_parts)

    # Output results
    if args.save:
        save_path = Path(args.save)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        save_path.write_text(output, encoding="utf-8")
        if not args.quiet:
            print(f"Output saved to: {save_path}", file=sys.stderr)
    else:
        print(output)

    # Print stats
    if not args.quiet:
        context_lines = context.count("\n")
        context_chars = len(context)
        print("\n--- Stats ---", file=sys.stderr)
        print(f"Subagent: {args.subagent} (model: {model})", file=sys.stderr)
        print(f"Context: {context_lines} lines, {context_chars:,} chars", file=sys.stderr)
        print(f"Estimated tokens: ~{context_chars // 4:,}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
