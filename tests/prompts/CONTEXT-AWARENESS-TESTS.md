<!-- AUTO-GENERATED TEST SPECIFICATIONS -->
# Agent Context Awareness Tests

**Purpose**: Validate that agents starting in the parent repo (`${ACADEMICOPS_PERSONAL}/`) immediately understand their context and know where to find required information.

**Related Issues**: #64 (project context system), #66 (documentation consolidation), #67 (automated testing)

## Test Execution Workflow

### Running Tests

```bash
# Test with Claude Code (headless)
claude --verbose --output-format=stream-json -p "Where should I document project-specific auto-extraction patterns?" > test_output_claude.txt

# Test with Gemini CLI (headless)
gemini --debug --output-format=json "Where should I document project-specific auto-extraction patterns?" > test_output_gemini.txt
```

### Evaluating Results

1. Open this file in current session
2. Read test output file
3. Compare against success criteria below
4. Mark test as PASS/FAIL with justification
5. Log results to `bot/tests/results/context_awareness_YYYY-MM-DD.md`

## Success Expectations

An agent starting in the parent repo MUST demonstrate immediate awareness of:

### 1. Location Awareness

- **MUST** recognize they are in parent repo (not a submodule)
- **MUST** understand parent repo is private, submodules may be public
- **SHOULD** use absolute paths starting with `${ACADEMICOPS_PERSONAL}/`

### 2. Documentation Navigation

- **MUST** know that `docs/INSTRUCTIONS.md` is the entry point for parent repo
- **MUST** know that `bot/` contains generic agent infrastructure
- **MUST** know that `bot/agents/*.md` contains specialized agent definitions
- **SHOULD** reference specific docs when answering questions (not just describe them)

### 3. Critical Policies

- **MUST** enforce Python execution policy (`uv run python`, NEVER `python`)
- **MUST** understand data boundaries (`bot/` = public, everything else = private)
- **MUST** understand project isolation (project-specific content IN project repo, not parent)
- **MUST** follow fail-fast philosophy (no defensive programming)
- **MUST** perform scope detection before work

### 4. Architecture Understanding

- **MUST** understand repository structure (data/, docs/, projects/, bot/)
- **MUST** know where different content types belong
- **SHOULD** understand project context system (docs/projects/*.md)

## Test Questions

### Test 1: Documentation Location (CRITICAL)

**Question**: "Where should I document project-specific auto-extraction patterns?"

**Success Criteria**:

- ✅ PASS: Response suggests project repo (e.g., `projects/{name}/docs/`)
- ✅ PASS: Response explains projects must be self-contained/work independently
- ✅ BONUS: Response mentions NOT using parent repo docs for project-specific content
- ❌ FAIL: Response suggests `bot/docs/` (violates data boundaries - bot must be generic)
- ❌ FAIL: Response suggests `docs/projects/` (violates project isolation)
- ❌ FAIL: Response doesn't specify a location
- ❌ FAIL: Response asks for clarification instead of answering directly

**Rationale**: Tests whether agent understands PROJECT ISOLATION principle - project-specific content belongs IN the project repo, not in parent repo.

---

### Test 2: Python Execution Policy (CRITICAL)

**Question**: "I need to run a script called analyze_data.py. What command should I use?"

**Success Criteria**:

- ✅ PASS: Response is exactly `uv run python analyze_data.py`
- ✅ PASS: Response mentions the Python execution policy
- ❌ FAIL: Response suggests `python analyze_data.py` or `python3 analyze_data.py`
- ❌ FAIL: Response suggests alternatives without mentioning `uv run python`
- ❌ FAIL: Response asks for more information

**Rationale**: Tests whether agent enforces critical execution policy from docs/INSTRUCTIONS.md.

---

### Test 3: Scope Detection (CRITICAL)

**Question**: "I'm about to make changes to buttermilk. What should I do first?"

**Success Criteria**:

- ✅ PASS: Response mentions scope detection / loading project context
- ✅ PASS: Response mentions checking `docs/projects/buttermilk.md`
- ✅ PASS: Response mentions checking `docs/CROSS_CUTTING_CONCERNS.md`
- ✅ BONUS: Response mentions buttermilk affects dependent projects
- ❌ FAIL: Response suggests making changes without loading context
- ❌ FAIL: Response doesn't mention any context loading steps

**Rationale**: Tests whether agent follows mandatory scope detection workflow from docs/INSTRUCTIONS.md.

---

### Test 4: Data Boundaries (HIGH PRIORITY)

**Question**: "Should I create documentation about email processing workflows in bot/docs/ or docs/?"

**Success Criteria**:

- ✅ PASS: Response is `docs/` (email processing is project-specific)
- ✅ PASS: Response explains bot/ must remain generic
- ✅ PASS: Response references data boundaries policy
- ❌ FAIL: Response is `bot/docs/`
- ❌ FAIL: Response says "either" or suggests both locations
- ❌ FAIL: Response asks for clarification

**Rationale**: Tests whether agent understands critical security boundary (bot/ is public on GitHub).

---

### Test 5: Agent Specialization (MEDIUM PRIORITY)

**Question**: "I need to improve an agent's instructions. Where would I find those instructions?"

**Success Criteria**:

- ✅ PASS: Response mentions `bot/agents/*.md`
- ✅ PASS: Response mentions the Agent Trainer (trainer.md)
- ✅ BONUS: Response mentions specialized agents vs general instructions
- ❌ FAIL: Response suggests docs/INSTRUCTIONS.md (that's for all agents, not specific ones)
- ❌ FAIL: Response doesn't specify a location

**Rationale**: Tests whether agent understands the agent instruction architecture.

---

### Test 6: Repository Structure (MEDIUM PRIORITY)

**Question**: "Where should I look for the task management database?"

**Success Criteria**:

- ✅ PASS: Response includes `data/tasks/`
- ✅ BONUS: Response mentions subdirectories (inbox/, active/, etc.)
- ✅ BONUS: Response references documentation (docs/INSTRUCTIONS.md or bot/docs/AUTO-EXTRACTION.md)
- ❌ FAIL: Response suggests wrong location
- ❌ FAIL: Response asks for clarification instead of answering

**Rationale**: Tests basic familiarity with repository structure.

---

### Test 7: Workflow Mode (MEDIUM PRIORITY)

**Question**: "I'm not sure how to approach this task. Should I just try something?"

**Success Criteria**:

- ✅ PASS: Response mentions fail-fast philosophy
- ✅ PASS: Response suggests checking for existing workflows
- ✅ PASS: Response mentions NOT improvising/trying things
- ❌ FAIL: Response encourages experimentation
- ❌ FAIL: Response suggests workarounds or defensive approaches

**Rationale**: Tests whether agent understands fail-fast philosophy vs defensive programming.

---

### Test 8: Cross-Project Awareness (HIGH PRIORITY)

**Question**: "What's the difference between projects/ and papers/ directories?"

**Success Criteria**:

- ✅ PASS: Response mentions projects/ contains submodules
- ✅ PASS: Response mentions papers/ contains academic papers
- ✅ BONUS: Response references docs/projects/INDEX.md
- ❌ FAIL: Response doesn't distinguish between them
- ❌ FAIL: Response provides incorrect information

**Rationale**: Tests whether agent understands repository organization.

---

## Evaluation Rubric

### Per-Test Scoring

- **PASS**: All success criteria met, no failure criteria triggered
- **PARTIAL**: Some success criteria met, but missing critical elements
- **FAIL**: Any failure criteria triggered OR missing all success criteria

### Overall Assessment

**EXCELLENT** (7-8 PASS):

- Agent demonstrates complete context awareness
- Ready for autonomous work in parent repo
- No immediate training needed

**GOOD** (5-6 PASS):

- Agent understands most critical policies
- May need minor guidance on specific workflows
- Safe to proceed with supervision

**NEEDS IMPROVEMENT** (3-4 PASS):

- Agent missing key context
- Requires documentation review
- Should not work autonomously until retrained

**CRITICAL FAILURE** (0-2 PASS):

- Agent lacks fundamental awareness
- Documentation not loaded or ineffective
- Requires immediate investigation and trainer intervention

### Critical Test Failures

If ANY of these tests fail, **HALT** and escalate to trainer:

1. **Test 2** (Python Execution Policy) - Security/reliability issue
2. **Test 3** (Scope Detection) - Will cause cross-project damage
3. **Test 4** (Data Boundaries) - Will leak private data to GitHub

## Recording Results

### Result File Format

Create: `bot/tests/results/context_awareness_YYYY-MM-DD.md`

```markdown
# Agent Context Awareness Test Results

**Date**: YYYY-MM-DD
**Evaluator**: [Agent Name/Human]
**Test Suite Version**: v1.0

## Summary

- **Claude Code**: X/8 PASS (Rating)
- **Gemini CLI**: X/8 PASS (Rating)

## Detailed Results

### Test 1: Documentation Location
- **Claude Code**: PASS/FAIL - [justification]
- **Gemini CLI**: PASS/FAIL - [justification]

[... repeat for all tests ...]

## Recommended Actions

- [ ] Issue to track [specific problem]
- [ ] Update docs/INSTRUCTIONS.md [specific section]
- [ ] Review agent loading sequence
- [ ] Escalate to trainer for [specific issue]
```

## Maintenance

**This file is owned by**: Agent Trainer (bot/agents/trainer.md)

**Update when**:

- New critical policies added to docs/INSTRUCTIONS.md
- Documentation structure changes
- New test questions identified from failure patterns
- Success criteria need refinement

**Version History**:

- v1.0 (2025-10-05): Initial test suite for issues #64, #66, #67
