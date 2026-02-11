# Architectural Report: Hydration & Workflow Injection

## Investigation Findings (Pre-change state)

The following findings describe the system behavior **before** the workflow-hydration refactor introduced in this PR.

### 1. Whitelisting Logic in `user_prompt_submit.py`

Before this change, the implementation in `user_prompt_submit.py` used a **hardcoded filename whitelist** for local workflow injection:

- It only checked for `TESTING.md`, `DEBUGGING.md`, and `DEVELOPMENT.md`.
- It used a static mapping of keywords for these specific files.
- **Impact**: Any local workflow with a different name (e.g., `manual-qa.md`, `deploy.md`) was completely ignored, even if it was highly relevant to the user prompt.

### 2. Global Workflow Injection

Before this change, the hook loaded only the **index file** (`aops-core/WORKFLOWS.md`).

- While the index contained a table of workflows and signals, the **content** (the specific steps) of global workflows (like `workflows/design.md`) was NOT injected into the hydration context.
- **Impact**: The hydrator (Haiku) had to either guess the steps based on the name or use its own internal knowledge, which could deviate from the project's actual workflow definitions.

### 3. Instruction Contradiction

- `agents/prompt-hydrator.md` system prompt said: **"DO NOT READ files beyond your input file"**.
- `hooks/templates/prompt-hydrator-context.md` task description said: **"Read all workflow files you have selected"**.
- **Impact**: Ambiguous behavior for the hydrator agent, leading to either missed context (if it followed the system prompt) or slow execution (if it followed the template and made multiple `read_file` calls).

### 4. Authoritative Location for Local Workflows

- **Location**: `.agent/workflows/` (files) or `.agent/WORKFLOWS.md` (index).
- **Maintenance**: At the time of this analysis, maintenance was manual. There was no automated process to sync or validate these against the global index.

### 5. Format Optimality

At the time of this analysis, the `WORKFLOWS.md` format used `[[wikilinks]]`, which are good for human navigation but require additional resolution logic for LLMs if they are to be followed.

## Refined Strategy

### Phase 1: Fix Injection Logic (Short Term)

1. **Remove Filename Whitelist**: Update `_load_project_workflows` to iterate through ALL `.md` files in `.agent/workflows/`.
2. **Content-Aware Matching**: For each file, check if its filename or its first few lines match keywords in the user prompt.
3. **Inject Global Content**: Update `load_workflows_index` to also selectively load the content of global workflows that match the prompt, using the existing `FILE_INDEX` or a new `WORKFLOW_INDEX`.

### Phase 2: Architectural Alignment (Medium Term)

1. **Resolve Contradictions**: Update `prompt-hydrator.md` and the context template to be consistent. Pre-loading is preferred for speed (AXIOM #7: Fail-fast/Speed).
2. **Standardize Indexing**: Use a common `IndexEntry` pattern for both global and local workflows to allow uniform discovery and injection.

### Phase 3: Validation (Continuous)

1. Add tests to `tests/test_post_hydration.py` (or similar) that verify a dummy local workflow is successfully "seen" by the hydrator.

## Proof of Concept (Plan)

1. Create a local workflow `.agent/workflows/POC-WORKFLOW.md`.
2. Update `user_prompt_submit.py` with the refined injection logic.
3. Simulate a hydration call and verify `POC-WORKFLOW.md` content is present in the temp file.
