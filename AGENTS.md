# Framework Agent Instructions

Universal operational invariants for agents executing with academicOps plugins:

- **Axioms**: Universal axioms in `plugins/rbg/skills/axioms/` govern all operations; local project rules narrow but never weaken axioms.
- **Authority**: Operate strictly within assigned task scope. Do not exceed delegated authority or second-guess direct user instructions.
- **Fail-Fast**: Stop immediately on tool failures, missing dependencies, or conflicting instructions; ad-hoc workarounds and silent fallbacks are prohibited.
- **Intake**: On receiving direction or a brief, record deliverables as an explicit acceptance checklist before starting work.
- **Inspection & Edits**: Read entire target files before editing. Edit files using native file tools, never shell scripts or heredocs.
- **Truth & Traceability**: Persist durable state, task tracking, and knowledge in the PKB. Outgoing reports and assertions follow `ida:premise-check` and Argdown syntax (`ida:argdown-toulmin`).
- **Research Data**: Raw research data and evaluation artifacts are immutable.
