---
name: heuristics
title: Heuristics
type: instruction
category: instruction
description: Working hypotheses validated by evidence.
---

# Heuristics

## Skills Contain No Dynamic Content (P#19)

**Statement**: Current state lives in $ACA_DATA, not in skills.

**Derivation**: Skills are shared framework infrastructure. Dynamic content in skills creates merge conflicts and state corruption.

---

## Semantic Link Density (P#54)

**Statement**: Related files MUST link to each other. Orphan files break navigation.

**Derivation**: Links create navigable knowledge graphs. Orphans are undiscoverable.

---

## File Category Classification (P#56)

**Statement**: Every file has exactly one category (spec, ref, docs, script, instruction, template, state).

**Derivation**: Mixed-category files are hard to maintain. Clear classification enables appropriate handling.

---

## Never Bypass Locks Without User Direction (P#57)

**Statement**: Agents must NOT remove or bypass lock files (sync locks, file locks, process locks) without explicit user authorization.

**Derivation**: Locks exist to prevent data corruption from concurrent operations. Removing a lock without understanding whether another process is active risks corrupting git state, SQLite databases, or file systems. Multi-agent concurrency is not currently architected. When encountering locks, agents must HALT and ask the user rather than attempting workarounds.

---

## Action Over Clarification (P#59)

**Statement**: When user signals "go" and multiple equivalent ready tasks exist, pick one and start. Don't ask for preference.

**Derivation**: Asking "which one?" when tasks are fungible wastes a round-trip. If the user cared about order, they'd specify. Bias toward motion.

---

## Indices Before Exploration (P#58)

**Statement**: Prefer curated indices (memory server, zotero, bd) over broad filesystem searches for exploratory queries.

**Derivation**: Grep is for needles, not fishing expeditions. Semantic search tools exist precisely to answer "find things related to X" - broad pattern matching across directories is wasteful and may surface irrelevant or sensitive content.

---

## Local AGENTS.md Over Central Docs (P#60)

**Statement**: Place agent instructions in the directory where agents will work, not in central docs.

**Derivation**: `lib/AGENTS.md` is discovered when an agent enters `lib/`. A `docs/SUBMODULES.md` linked from root requires agents to know the link exists. Discoverability beats indirection.

---

## Internal Records Before External APIs (P#61)

**Statement**: When user asks "do we have a record" or "what do we know about X", search bd and memory FIRST before querying external APIs.

**Derivation**: "Do we have" implies checking our knowledge stores, not fetching new data. Internal-first respects the question's scope and avoids unnecessary API calls.

---
