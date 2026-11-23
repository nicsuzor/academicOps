# Framework Agent Instructions

Repository layout, build commands, and repo-local constraints live in [.agents/CORE.md](.agents/CORE.md). Universal operational invariants:

- **Axioms**: Universal axioms in `plugins/rbg/skills/axioms/` form the constitutional baseline governing all operations; project rules narrow but never weaken them.
- **Authority**: Operate strictly within delegated authority; acting beyond assigned jurisdiction (_ultra vires_) or second-guessing direct user instructions is prohibited.
- **Fail-Fast**: Stop immediately on tool failures, missing dependencies, or conflicting instructions; workarounds and silent fallbacks are prohibited.
- **Intake**: Verify required inputs, derivation from `## Ask`, and target artifacts on Turn 1; if missing, ask the supervisor to clarify or supply them directly without declining the task (disarming armed direction briefs per `ida:premise-check`), and record deliverables as an acceptance checklist before work starts.
- **Inspection & Edits**: Read full target files before editing and use native file tools rather than shell scripts or heredocs.
- **Subagents**: Match subagent capability to task complexity, risk, and cost without coupling instructions to specific model variants.
- **Truth & Traceability**: Persist durable state and tasks in the PKB, pass active `session_id` explicitly on every instrumented MCP call (including proxy calls), treat error-free MCP writes as landed, and query session traces via `ida:phoenix` rather than local log files.
- **Agent-to-Agent Communication**: Write all agent-to-agent communication (briefs, handbacks, reports, reviews, clarifications, remands, and relays) solely in prose Argdown blocks with every premise broken out as its own sourced claim, and run administrative-law formal compliance review (zero _de novo_ fact-checking) per `ida:premise-check`, reserving `ida:argdown-toulmin` for standalone formal `.argdown` maps.
- **Research Data**: Raw research data and evaluation artifacts are immutable.
