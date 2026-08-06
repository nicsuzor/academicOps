# Adversarial Challenge Report: Milestone R4 (4-Tier Transcript System & Renderer Hardening)

**Agent**: Challenger 1 (Milestone R4 Empirical Challenger)  
**Roles**: critic, specialist  
**Working Directory**: `/workspace/.agents/teamwork_preview_challenger_r4_1/`  
**Milestone**: R4  
**Date**: 2026-08-06  
**Verdict**: **REJECT**  

---

## 1. Observation

### 1.1 Requirements Audit & Test Suite Execution
- **Unit Test Execution**: Executed `/home/worker/.venv/bin/pytest tests/transcripts/`. Output: **118 passed in 3.37s**.
- **Adversarial Stress Harness Execution**: Executed custom stress harnesses (`/workspace/.agents/teamwork_preview_challenger_r4_1/stress_test_r4.py` and `deep_escape_test.py`). Output: Identified 4 confirmed empirical failure modes in XML/HTML escaping and Markdown rendering safety.

### 1.2 Empirical Failure Modes Observed

#### Observation 2.1: Model Message Content in Markdown Renderers Lacks HTML/XML Escaping
- **File**: `lib/py/transcripts/domain/renderer.py`, lines 338–340
- **Code Quote**:
  ```python
  338:             else:
  339:                 lines.append(content)
  340:                 lines.append("")
  ```
- **Empirical Result**: When `event.source == "model"` (Assistant response), `content` containing raw XML/HTML tags (such as `<file_content>`, `<thinking>`, `<USER_REQUEST>`, `<script>alert('model')</script>`) is appended directly into `lines` without calling `_escape_html()`.
- **Verbatim Output**: In `.controller.md` and `.full.md`:
  `RAW LINE: "I am reviewing <file_content> and <USER_REQUEST> for tags <thinking> and <script>alert('model')</script>."`
- **Impact**: HTML-based Markdown parsers (GitHub, VS Code, grip, marked.js) treat raw `<file_content>`, `<thinking>`, and `<USER_REQUEST>` as HTML tags and swallow (hide) them from the rendered DOM, corrupting text visibility and failing Requirement R4 ("Escape XML/HTML tags in tool outputs and prompts to prevent layout breakage").

#### Observation 2.2: Subagent Table Descriptions in Markdown Renderers Lack HTML/XML Escaping
- **File**: `lib/py/transcripts/domain/renderer.py`, lines 127–130
- **Code Quote**:
  ```python
  127:         description = (subagent.description or "").strip().replace("\n", " ")
  128:         if len(description) > 80:
  129:             description = description[:77] + "..."
  130:         description = description.replace("|", "\\|")
  ```
- **Empirical Result**: `subagent.description` in `_render_subagent_index()` only escapes pipe characters (`|`), omitting `_escape_html()`.
- **Verbatim Output**:
  `RAW TABLE ROW: "| 1 | \`sub_x\` | | ? | 0 | 0 | | Task for <USER_REQUEST> with <script>alert('sub')</script> |"`
- **Impact**: Tags inside subagent descriptions are swallowed or executed as raw HTML in the subagent summary tables of `.controller.md`, `.full.md`, and `.md`.

#### Observation 2.3: Tool Output Code Block Breakouts via Triple Backticks
- **File**: `lib/py/transcripts/domain/renderer.py`, lines 232–252
- **Code Quote**:
  ```python
  232: def _format_tool_output_markdown(content: str) -> list[str]:
  233:     byte_count = len(content.encode("utf-8"))
  234:     is_large = len(content) > 500 or len(content.splitlines()) > 10
  235:     if is_large:
  ...
  240:             "```",
  241:             content,
  242:             "```",
  ```
- **Empirical Result**: If a tool output contains triple backticks (e.g. code blocks, git diffs, Markdown files), the inner backticks prematurely close the opening ` ``` ` code block.
- **Verbatim Output**:
  ```markdown
  #### 🛠️ Tool `(2026-08-06T12:00:00Z)`

  ```
  Output with backticks:
  ```python
  print('<script>alert(1)</script>')
  ```
  End of output.
  ```
  ```
- **Impact**: Content following the inner ` ``` ` (including `End of output.`) spills out into the Markdown document body as unescaped text/HTML, breaking document formatting and exposing tags to DOM parser swallowing.

#### Observation 2.4: HTML Metadata Header Box Unescaped Format Interpolation
- **File**: `lib/py/transcripts/domain/renderer.py`, lines 813–822
- **Code Quote**:
  ```python
  813:             <div class="meta-item"><strong>Slug</strong>{slug}</div>
  814:             <div class="meta-item"><strong>Started At</strong>{started_at}</div>
  815:             <div class="meta-item"><strong>Ended At</strong>{ended_at}</div>
  816:             <div class="meta-item"><strong>User Context</strong>{str(has_user_context)}</div>
  817:             <div class="meta-item"><strong>Project</strong>{correlation.get("project") or "N/A"}</div>
  818:             <div class="meta-item"><strong>Task ID</strong>{correlation.get("task_id") or "N/A"}</div>
  ```
- **Empirical Result**: `slug`, `started_at`, `ended_at`, `project`, and `task_id` are interpolated into HTML string formatting without passing through `_escape_html()`.
- **Verbatim Output**: Setting `project="<script>alert('xss_project')</script>"` and `task_id="<iframe src='x'></iframe>"` outputs raw `<script>` and `<iframe>` elements inside the HTML header box.
- **Impact**: Enables tag injection and potential XSS in `.html` transcript renders.

### 1.3 Area Checks Passing Conformance
1. **4-Tier Artifact Generation**: `process_single_session()` generates all 5 files (`.controller.md`, `.full.md`, `.md`, `.html`, `.json`) with proper file extension structure.
2. **Collapsible Blocks Boundary Size**: Tested 499, 500, 501 chars, 10, 11 lines, and multi-byte UTF-8 strings. Boundary threshold `>500` chars or `>10` lines accurately triggers `<details><summary>` wrapping.
3. **Subagents & Message Echoes**: Handled unlinked subagents with missing metadata without exceptions, and correctly deduplicated inter-agent message echoes sharing parent event IDs.
4. **Sparse `step_index`**: agy transcripts with non-contiguous step indices (1, 5, 20, 100) produced zero false degradation warnings (`degraded == []`).
5. **Token/Cost Split Accounting**: YAML frontmatter and JSON sidecar metadata accurately split `controller_tokens`, `subagent_tokens`, `controller_cost_usd`, `subagent_cost_usd`, `total_tokens_used`, and `total_cost_usd`.

---

## 2. Logic Chain

1. **Requirement R4 Mandate**: R4 explicitly specifies: *"Escape XML/HTML tags in tool outputs and prompts to prevent layout breakage"* and *"HTML/XML special characters in user prompts or tool outputs are properly executed/escaped without breaking renderer output."*
2. **Observation 2.1 Link**: `_render_events_markdown()` applies `_escape_html()` to user prompts and thinking blocks, but omits it for model message content (line 339). When model messages contain tags like `<thinking>`, `<USER_REQUEST>`, `<file_content>`, or `<script>`, the output in `.controller.md` and `.full.md` contains unescaped raw tags.
3. **Observation 2.2 Link**: `_render_subagent_index()` omits `_escape_html()` for `subagent.description` (line 130). Unlinked or custom subagent descriptions carrying XML tags render unescaped into Markdown tables.
4. **Observation 2.3 Link**: `_format_tool_output_markdown()` uses static ` ``` ` delimiters without fence escaping or backtick count adjustment. Tool outputs containing backticks escape the code block fence and dump remaining output as raw unescaped text into the Markdown document.
5. **Observation 2.4 Link**: `render_to_html()` interpolates `slug`, `started_at`, `ended_at`, `project`, and `task_id` into HTML without `_escape_html()`. Metadata containing special characters creates valid raw HTML element injections.
6. **Deduction & Verdict**: Because multiple core escaping and rendering hardening requirements fail empirically, Milestone R4 cannot be approved in its current state. The verdict is **REJECT**.

---

## 3. Caveats

- **Scope Limit**: The non-transcript test failures observed in the full repository `pytest` run (e.g. `tests/test_shipped_hooks.py`, `tests/test_build.py`) belong to other hook/build components outside Requirement R4 and were not factored into this transcript verdict.
- **Assumptions**: Tested against Python 3.12 environment `/home/worker/.venv/bin/python`.

---

## 4. Conclusion

Milestone R4 successfully implements 4-tier artifact output generation, accurate token/cost split accounting, sparse step index tolerance, and subagent echo deduplication. However, the implementation **fails core renderer hardening and XML/HTML tag escaping requirements** in Markdown and HTML outputs.

**Verdict**: **REJECT**

### Required Remediations for Approval:
1. Apply `_escape_html()` to model message content in `_render_events_markdown()` (`renderer.py` line 339).
2. Apply `_escape_html()` to `subagent.description` in `_render_subagent_index()` (`renderer.py` line 130).
3. Escape code block fences (e.g., using 4+ backticks ` ```` ` or sanitizing inner backticks) in `_format_tool_output_markdown()`.
4. Wrap `slug`, `started_at`, `ended_at`, `project`, and `task_id` in `_escape_html()` inside `render_to_html()` (`renderer.py` lines 813–818).

---

## 5. Verification Method

To independently verify these empirical findings:

1. **Run Adversarial Stress Harness**:
   ```bash
   /home/worker/.venv/bin/python /workspace/.agents/teamwork_preview_challenger_r4_1/stress_test_r4.py
   /home/worker/.venv/bin/python /workspace/.agents/teamwork_preview_challenger_r4_1/deep_escape_test.py
   ```
2. **Inspect Output**:
   Observe raw unescaped tags (`<file_content>`, `<USER_REQUEST>`, `<script>`) in `controller_md` and `html` metadata fields.
3. **Invalidation Condition**:
   The findings are invalidated if all model content, subagent descriptions, code block fences, and HTML metadata header fields escape `<, >, &, ", '` such that no raw XML/HTML tags appear unescaped in Markdown or HTML outputs.
