# Framework Agent Instructions

Universal operational invariants for agents executing with academicOps plugins:

- **Axioms**: Universal axioms in `plugins/rbg/skills/axioms/` govern all operations; local project rules narrow but never weaken axioms.
- **Authority**: Operate strictly within assigned task scope. Do not exceed delegated authority or second-guess direct user instructions.
- **Fail-Fast**: Stop immediately on tool failures, missing dependencies, or conflicting instructions; ad-hoc workarounds and silent fallbacks are prohibited.
- **Intake**: On receiving direction or a brief, subagents must verify on Turn 1 that all required inputs and target artifacts are present; if omitted, immediately return `REVISE` via `send_message` to the caller (without running `verdict.py`). Record deliverables as an explicit acceptance checklist on a PKB task before work starts.
- **Inspection & Edits**: Read entire target files before editing. Edit files using native file tools, never shell scripts or heredocs.
- **Truth & Traceability**: Persist durable state, task tracking, and knowledge in the PKB. Outgoing reports and assertions follow `ida:premise-check` and Argdown syntax (`ida:argdown-toulmin`). Direct all session, prompt, and execution trace lookups exclusively to Arize Phoenix via `ida:session-trace`; scraping local `.system_generated/logs/transcript*.jsonl` or `/tmp/aops_debug_hooks_*.jsonl` files is strictly prohibited.
- **Research Data**: Raw research data and evaluation artifacts are immutable.
