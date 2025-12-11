# Hooks Design Principles

## Architecture: Hooks Never Call LLM APIs

**CRITICAL**: Hooks MUST NOT call the Claude/Anthropic API directly from Python.

Hooks are synchronous lifecycle events with timeouts. They inject context and instructions - they don't do LLM reasoning themselves.

**Correct pattern**: Hook injects `additionalContext` that tells Claude Code what to do
```python
output = {"additionalContext": "MANDATORY: Invoke the X skill before proceeding"}
```

**Wrong pattern**: Hook calls Anthropic API directly
```python
# NEVER DO THIS IN A HOOK
client = anthropic.Anthropic()
response = client.messages.create(...)  # WRONG
```

**Why this matters**:
- Hooks have timeouts (2-30 seconds) - API calls may exceed them
- Creates parallel LLM calls outside the main conversation context
- Expensive (API costs) and architecturally wrong
- The main Claude Code agent should orchestrate all LLM work

**If you need LLM analysis in a hook's logic**: The hook should inject instructions telling Claude Code to spawn an agent (e.g., Haiku via Task tool) - not call the API itself.

## Current Violations

These hooks violate the principle and need redesign:
- `verify_conclusions.py` - calls Anthropic API directly
- `extract_session_knowledge.py` - calls Anthropic API directly
