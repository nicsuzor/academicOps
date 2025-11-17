# Experiment: LOG.md Sufficiency Test - README.md Fix

**Date**: 2025-11-17
**Status**: In Progress
**Pattern**: #meta-framework #log-quality #knowledge-transfer

## Hypothesis

The LOG.md entry for "README.md Purpose Confusion" (2025-11-17) contains sufficient detail for a fresh Claude Code instance with no conversation history to correctly fix README.md by applying the authoritative vs instructional separation principle.

## Context

After logging the README.md bloat issue to LOG.md, user asked: "if you lost all memory now, would there be enough detail in the logs to fix the specific errors we just saw?"

This tests whether our learning log captures actionable patterns vs just observations.

## Test Design

**Setup**:
1. Current state: README.md contains bloat violations documented in LOG.md:116-124
2. Fresh agent command: `/meta Fix README.md based on the 2025-11-17 "README.md Purpose Confusion" entry in experiments/LOG.md. Apply authoritative vs instructional separation principle.`

**Success Criteria**:
- Agent removes instructional bloat:
  - "For Users: Quick Discovery" section with basic cat commands
  - "Adding New Components" workflow duplication (covered in framework/SKILL.md)
  - "Core Principles" duplication (AXIOMS.md should be in tree with description only)
  - "Architecture Evolution" historical context
  - Deployment implementation details (should be in separate file)
- Agent preserves/enhances authoritative content:
  - Directory structure with one-line abstracts for each file
  - Contact info
  - Session start loading sequence
  - Installation instruction (concise, practical)
- Agent applies correct pattern: reference with brief inline summary, don't explain

**Failure Modes to Watch**:
- Agent doesn't understand authoritative vs instructional from log alone
- Agent removes too much (e.g., deletes directory tree)
- Agent doesn't identify which sections are bloat
- Agent needs to ask clarifying questions instead of acting

## Execution

*[To be filled after running command with fresh agent]*

## Results

*[To be filled with observation of agent behavior]*

## Decision

*[keep/revert/iterate + rationale]*

## Learnings

*[What this reveals about LOG.md quality and knowledge transfer]*
