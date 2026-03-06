# Dashboard QA Assessment - 2026-03-06

**Assessor**: Claude (crew/barbara_5)
**Dashboard**: Cognitive Load Dashboard on port 8501
**Verdict**: ISSUES FOUND - 4 major areas need improvement

---

## Focus Area 1: Bogus Project Cards on Front Page

**Severity**: HIGH
**Finding**: Multiple empty project cards with nonsensical names appear on the dashboard front page.

Observed bogus cards (from screenshots):

- "3", "4", "2" (bare numbers)
- "865", "f1x", "cor", "e40", "n", "c55", "17ca", "017" (hash/ID fragments)
- "sessions", "overwhel", "e2b" (truncated or non-project names)

**Root cause** (`dashboard.py:5062-5065`): When a task has no `project` field, the code splits the task ID on `-` and takes the first segment as the "project". Task IDs like `865-some-task` or `f1x-something` produce these bogus names.

The `is_valid_project()` filter (`dashboard.py:5124-5135`) only rejects hex strings of 8+ characters and a small hardcoded exclusion list (`hooks`, `unknown`, `tasks`, `inbox`, `tmp`). Short hash fragments and numbers pass through.

Additionally, the filter at line 5216-5221 only drops cards with no sessions, no tasks, no accomplishments, and no session count. But many bogus "projects" have at least one task mapped to them, so they survive.

**Fix needed**:

1. Strengthen `is_valid_project()` to require the name exists in `valid_project_ids` (tasks with `type == "project"` or explicit `project` field values)
2. Stop inferring project from task ID prefix - this is the main source of garbage
3. Add a minimum length/content filter (reject single chars, bare numbers)

## Focus Area 2: Summaries That Don't Help

**Severity**: MEDIUM
**Finding**: Several summary sections convey minimal useful information.

Issues observed:

- **TODAY'S STORY**: Lists `"[sessions] Commit changed files"` twice and `"[explorations] Record buttermilk generation"` - these are auto-generated slug summaries, not meaningful narratives
- **DONE (0)**: Shows "0" done but then lists items like "Record buttermilk generation; Commit changed files" - contradictory
- **ALIGNMENT**: Always shows "No session outcomes recorded" - this section adds no value
- **TOKENS (5 sessions)**: "7K total, 100% cache" - useful but buried
- **SESSION INSIGHTS**: "In/Out: 143/7K" and "Cache Read: 679K" - cryptic without context

The FOCUS SYNTHESIS section is 40min old and provides useful meta-information, but the sub-sections (TODAY'S STORY, DONE, ALIGNMENT) feel like placeholders rather than genuine summaries.

**Fix needed**:

1. Remove or rethink ALIGNMENT section - it's always empty
2. Fix DONE count mismatch (shows 0 but lists items)
3. Make TODAY'S STORY use real session summaries instead of filename slugs
4. Consider collapsing TOKENS and SESSION INSIGHTS into a single compact line

## Focus Area 3: Task Graph Color Scheme and Legend

**Severity**: MEDIUM
**Finding**: The color scheme is functional but has significant readability issues.

Current state:

- **Legend**: Shows 6 items (Active/blue, Blocked/red, Done/green, Parent/blue line, Dependency/red dashed, Recent 7d/yellow border). This is minimal and correct but incomplete.
- **Missing from legend**: Node shapes (pill=goal, rounded=project, hexagon=epic, rect=task), border colors (priority 0=red, 1=orange, 2=gray), assignee border colors (nic=purple, bot=teal), weight-based sizing, structural/muted nodes
- **Color problems on dark background**: The pastel fill colors (STATUS_FILLS) were designed for light backgrounds. On the dark Streamlit theme, light blue (#dbeafe for active) and light gray (#f1f5f9 for inbox) look washed out and hard to distinguish.
- **Node text readability**: Small font sizes (8-10px) on pastel backgrounds against a dark canvas are hard to read at default zoom.
- **Weight-based desaturation**: Heavy nodes are more saturated, light nodes are desaturated toward gray. This is backwards for readability - the most important nodes should pop more, but the desaturation effect is subtle and unexplained.

**Fix needed**:

1. Add a comprehensive legend showing: node shapes by type, border colors by priority/assignee, size meaning
2. Improve color contrast for dark theme - either darken fills or add stronger borders
3. Increase minimum font size from 8px to 10px
4. Consider a simpler, more distinct color palette with fewer overlapping hues

## Focus Area 4: Leaf Mode Toggle - Verdict

**Severity**: MEDIUM
**Finding**: Leaf mode DOES do something significant, but it's confusing and the UX doesn't explain it.

Observations:

- **Normal view**: 94 active nodes, 238 links (filtered by "Top N by importance" = 80)
- **Leaf mode**: 612 active nodes, 1272 links (shows ALL leaf tasks, ignores importance filter)
- The visual change is dramatic - the graph goes from a readable clustered layout to an overwhelming wall of tiny nodes
- There's a "Leaf view stats" expander in the sidebar but it's collapsed by default
- The help tooltip exists but is small and easy to miss

**Verdict**: Leaf mode serves a different purpose (seeing ALL actionable items) than the default view (seeing the most important items in context). These are fundamentally different questions:

1. "What should I work on?" -> Top N by importance (current default)
2. "What's everything on my plate?" -> Leaf view (flat list of all actionable items)

The toggle approach is wrong because the two views need completely different rendering parameters (zoom level, layout algorithm, clustering). Toggling leaf mode with the same graph settings produces an unreadable mess.

**Recommendation**: Remove the leaf mode checkbox. Instead, create a dedicated "Workload Overview" view that uses a treemap or circle-pack layout purpose-built for showing all leaf tasks grouped by project. This aligns with the epic's design insight: "different questions need different visualizations."

---

## Additional Observations

### YOUR PATH Section

- Useful but very long - shows raw session transcripts that scroll for pages
- Project names in YOUR PATH ("AOPS", "MEM", "GEMINI-OVERWH", "EXPLORATIONS") are truncated and inconsistent with the project cards below
- Contains raw prompt text that's hard to scan

### Epic Progress Widget

- "Epic: Framework Core" at 46% with 16 done, 18 in progress, 1 blocked - this is useful and well-formatted
- But it's the ONLY epic shown at the top level; other epics are buried inside project cards

### Quick Capture

- Clean and functional, no issues

---

## Priority Ranking for Improvements

1. **P0**: Fix bogus project cards (remove ID-prefix inference, strengthen validation)
2. **P0**: Improve color scheme for dark theme + expand legend
3. **P1**: Clean up summary sections (remove ALIGNMENT, fix DONE count, improve TODAY'S STORY)
4. **P1**: Replace leaf mode toggle with purpose-built workload overview view
5. **P2**: Tighten YOUR PATH section (truncate, consistent naming)
6. **P2**: Surface more epics at top level, not just Framework Core
