---
title: Script Design Guide
type: reference
permalink: ref-script-design-guide
description: Framework principles for script design, distinguishing between simple utilities and agent orchestration
---

# Script Design: Orchestration vs Reasoning

**CRITICAL ANTI-PATTERN**: Writing scripts that duplicate Claude Code's built-in capabilities.

**The Framework Context**: We work in Claude Code (CLI tool) where agents have direct access to powerful tools: Read, Write, Edit, Grep, Glob, and full LLM reasoning. Scripts that replicate these capabilities are wrong.

**Related guidance**: See [[claude-code-config]], [[e2e-test-harness]], and [[testing-with-live-data]] for complementary patterns.

## When Scripts Are PROHIBITED

**❌ NEVER write scripts that**:

```python
# WRONG: Script reads files (use Read tool in agent)
def read_emails(path):
    with open(path) as f:
        return f.read()

# WRONG: Script filters with regex (use LLM judgment in agent)
def filter_important(emails):
    pattern = r'accepted|grant|published'
    return [e for e in emails if re.search(pattern, e)]

# WRONG: Script searches files (use Grep/Glob tools in agent)
def find_projects(directory):
    for file in Path(directory).glob("**/*.md"):
        if "project" in file.read_text():
            results.append(file)

# WRONG: Script extracts patterns (use LLM reasoning in agent)
GRANT_PATTERN = r'\b(DP|FT|LP)\d{6,10}\b'
grants = re.findall(GRANT_PATTERN, text)
```

**Why this is wrong**:
- Loses semantic understanding (regex vs LLM judgment)
- Duplicates built-in tools (Read/Grep/Glob exist)
- Violates DRY (tools already available)
- Increases maintenance burden
- Breaks LLM-first architecture

## When Scripts ARE Allowed (Simple Tools Only)

**✅ Scripts are SIMPLE TOOLS that agents call via Bash**:

### 1. Data Transformation - Mechanical format conversion

```python
def chunk_jsonl(input_file, output_dir, chunk_size=50):
    """Split JSONL into numbered chunk files."""
    # Pure mechanical operation: read, split by count, write
    # NO filtering, NO reasoning, NO decision-making
```

### 2. Aggregation - Combine structured outputs

```python
def merge_json_files(input_pattern, output_file):
    """Merge multiple JSON files into one."""
    # Pure mechanical operation: read JSONs, concatenate, write
    # NO filtering, NO analysis
```

**Scripts are utilities**. The AGENT orchestrates everything:
- Agent decides what to process
- Agent invokes script via Bash tool: `python chunk_emails.py archive.jsonl chunks/`
- Agent processes each chunk (using Read/LLM judgment)
- Agent invokes script via Bash tool: `python merge_results.py results/*.json summary.json`
- Agent analyzes final results

## The Correct Pattern

**Agents orchestrate → Scripts are simple tools → Agents reason**

### Example: Email Extraction

❌ **WRONG APPROACH**:
```python
# Script does everything (reads, filters, extracts, writes)
emails = read_jsonl("archive.jsonl")
important = [e for e in emails if re.search(r"grant|accept", e["body"])]
for email in important:
    extract_grant_id(email)  # regex extraction
    create_entity(email)      # file writes
```

✅ **CORRECT APPROACH**:

```python
# Script: chunk_emails.py - SIMPLE UTILITY
# Does ONE thing: split JSONL into chunks (mechanical only)
def chunk_jsonl(input_file, output_dir, chunk_size=50):
    with open(input_file) as f:
        for i, chunk in enumerate(batched(f, chunk_size)):
            Path(output_dir, f"chunk-{i:03d}.jsonl").write_text(chunk)
```

**Agent workflow** (the agent orchestrates everything):
1. Agent: Use Bash tool → `python chunk_emails.py archive.jsonl chunks/`
2. Agent: Use Glob tool → Find all chunks/chunk-*.jsonl
3. Agent: For each chunk:
   - Use Read tool → Read chunk content
   - Use LLM judgment → "Is this email important?"
   - Use LLM reasoning → Extract grant IDs, paper info, etc.
   - Use Skill(skill="remember") → Persist knowledge to memory server
4. Agent: Use Bash tool → `python merge_results.py results/*.json summary.json` (if needed)
5. Agent: Analyze aggregated results

**The agent does ALL orchestration, decision-making, and reasoning**.
**Scripts are dumb utilities the agent calls when needed**.

## Decision Framework

**Before writing ANY script, ask**:

1. "Am I duplicating Read/Write/Edit/Grep/Glob tools?" → Don't write it
2. "Am I filtering/searching/analyzing text?" → Don't write it (agent does this)
3. "Am I extracting patterns with regex?" → Don't write it (agent uses LLM)
4. "Am I orchestrating a workflow?" → Don't write it (agent orchestrates)
5. "Is this PURELY mechanical data transformation?" → Script OK (as simple tool)

**Script purpose test**:
- ✅ "Split this file into N-line chunks" → Simple tool, OK
- ✅ "Merge these JSON files" → Simple tool, OK
- ❌ "Find important emails" → Agent reasoning, not a script
- ❌ "Extract grant IDs" → Agent reasoning, not a script
- ❌ "Process this archive" → Agent orchestration, not a script

**Remember**: Scripts are utilities like `jq` or `split`. Agents call them via Bash.

## Enforcement

**Pre-implementation checklist**:
- [ ] Does script only chunk/parallel/aggregate?
- [ ] Zero use of open(), re.search(), pathlib.glob()?
- [ ] All reasoning delegated to agents?
- [ ] Integration test shows agent doing the work?

**Code review red flags**:
- Imports: `re`, `pathlib` (for file reading)
- Functions: reading files, pattern matching, filtering
- Hardcoded patterns: regex strings, skip lists, filter rules
- Business logic: "important", "should extract", "matches criteria"
