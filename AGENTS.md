# Framework Agent Instructions

Repository layout, build commands, and repo-local constraints live in [.agents/CORE.md](.agents/CORE.md). Universal operational invariants:

- **Axioms**: Universal axioms in `plugins/rbg/skills/axioms/` govern all operations; project rules narrow but never weaken axioms.
- **Authority**: Operate strictly within delegated task scope; never exceed authority or second-guess direct user instructions.
- **Fail-Fast**: Stop immediately on tool failures, missing dependencies, or conflicting instructions; workarounds and silent fallbacks are prohibited.
- **Intake**: Verify required inputs and target artifacts on Turn 1; if missing, return `REVISE` immediately, and record deliverables as an acceptance checklist before work starts.
- **Inspection & Edits**: Read full target files before editing and use native file tools rather than shell scripts or heredocs.
- **Subagents**: Match subagent capability to task complexity, risk, and cost without coupling instructions to specific model variants.
- **Truth & Traceability**: Persist durable state and tasks in the PKB, treat error-free MCP writes as landed, format outgoing reports per `ida:premise-check` and `ida:argdown-toulmin`, and query session traces via `ida:phoenix` rather than local log files.
- **Research Data**: Raw research data and evaluation artifacts are immutable.
