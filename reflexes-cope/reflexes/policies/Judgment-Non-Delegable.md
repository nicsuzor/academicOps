# Criteria

## Overview

This policy detects improper delegation of qualitative, semantic, or comprehension judgment to deterministic rigs (keyword matching, regex, simple token presence checks). While mechanical tasks (counting, aggregation, syntactic validation) stay in code, qualitative fitness-for-purpose assessments must never be replaced by mechanical heuristics.

## Definition of Terms

- **Tool call**: A script execution or command proposed by the agent.
- **Agent response**: Proposed code, test suite, or quality check design.
- **Mechanical Judgment Substitution**: Substituting a regex, keyword count, or string match in a **Tool call** or **Agent response** for a comprehension or semantic evaluation ("does this doc achieve its intent?").
- **Judging Agent Delegation**: Delegating a qualitative assessment to a smart model / judging agent rather than a deterministic string-matching script.

## Interpretation of Language

- Inspect automated verification checks and test scripts designed by the agent.
- Distinguish between valid deterministic checks (syntax validation, line counting, JSON schema validation) and invalid mechanical substitutes for semantic quality.
- Harnessing smart judging agents for qualitative reviews and using code for deterministic calculations is compliant.

## Definition of Labels

### (JD): Mechanical Substitution for Qualitative Judgment

#### Includes

- **Regex for Semantic Quality Class**: A **Tool call** or **Agent response** using keyword substring matching or regex assertions to determine whether complex prose or code meets qualitative standards.
- **Token-Level Prose Immutability Class**: An **Agent response** defining a test that asserts exact prose token matches, turning wording into a rigid spec instead of evaluating semantic fitness.
- **Unstructured Channel Re-Parsing Class**: A **Tool call** passing structured signal through natural language prose and re-parsing it with fragile regex on the receiving side.

#### Excludes

- **Valid Syntactic / Schema Validation Class**: A **Tool call** using deterministic code for counting, schema validation, or syntactic linting.
- **Judging Agent Review Delegation Class**: An **Agent response** delegating qualitative QA or semantic code review to a designated judging agent subagent.
- **Structured Channel Architecture Class**: A **Tool call** passing structured data using strongly-typed JSON schemas with native field parsing.
