# Workflow: Academic Report Finalization

**Trigger**: User asks to finalize, revise, or prepare a research report for
release — especially after receiving reviewer/stakeholder feedback.

**Principle**: Front-load all information gathering and decision-making. Never
begin editing until you have a complete picture of what needs to change and why.

---

## Phase 1: Discovery (before ANY edits)

### 1.1 Gather prior work

- [ ] Search PKB for existing artifacts related to this report:
      `search_by_tag(tag=project)`, `search(query="report feedback comments")`,
      `task_search(query="report")`
- [ ] Check for reviewer comments, tracked changes, feedback documents
- [ ] Check for prior session decisions that may already be settled
- [ ] Read the current report draft end-to-end
- [ ] Read the methodology/METHODOLOGY.md file

### 1.2 Assess the evidence base

- [ ] What claims does the report make?
- [ ] What validation supports each claim? Is it sufficient?
- [ ] Where are the weakest claims? Do they need more evidence or should they
      be reframed/deferred?

### 1.3 Consolidate feedback

- [ ] Extract ALL reviewer comments into a single actionable list
- [ ] Group by: must-do, should-do, future work
- [ ] Cross-reference with any prior decisions already made
- [ ] Identify genuine decision points (where the user needs to choose between
      valid options) vs mechanical edits

**Gate**: Do not proceed to Phase 2 until the user has reviewed the consolidated
feedback and confirmed the approach for any genuine decision points.

---

## Phase 2: Planning

### 2.1 Build the task tree

- [ ] Create tasks organised by report section (not by theme)
- [ ] Each task lists specific reviewer items it addresses (with cross-refs)
- [ ] Link ALL PKB artifacts in a `## Related Artifacts` section
- [ ] Mark [DATA] items that need computation
- [ ] Identify dependencies (data computation unblocks results sections)
- [ ] Get approval once, then execute without per-step confirmation

**Gate**: User approves the task tree. After this, proceed autonomously through
implementation.

---

## Phase 3: Implementation

---

## Phase 4: Verification

### 4.1 Consistency check

- [ ] All numbers internally consistent
- [ ] Cross-references between sections work
- [ ] Introduction promises match what the report delivers
- [ ] Terminology is consistent throughout

### 4.2 Reviewer coverage

- [ ] Walk through the consolidated feedback list
- [ ] Verify every must-do item is addressed
- [ ] Note any should-do items that were deferred with rationale

### 4.3 Commit and report

- [ ] Commit changes with descriptive message
- [ ] Update PKB task status
- [ ] Summarise: what changed, what was deferred, what needs user review

## Anti-patterns

1. **Don't create task trees in a vacuum.** Search PKB for existing artifacts, prior decisions, and reviewer feedback FIRST.
2. **Don't present analysis without connecting to the deliverable.** Immediately explain what metrics mean for the report narrative.
3. **Don't ask permission at every phase transition.** After plan approval, execute. Only stop for genuine decision points.
4. **Don't rediscover what prior sessions decided.** Search PKB before proposing approaches that may already be settled.
5. **Don't start editing before gathering all feedback.** Discovering a restructuring requirement mid-edit is far more costly than reading all comments up front.
