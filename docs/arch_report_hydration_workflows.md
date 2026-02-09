# Architectural Report: Hydration & Workflow Injection

## Investigation Findings

### 1. Whitelisting Logic in `user_prompt_submit.py`
The current implementation in `user_prompt_submit.py` uses a **hardcoded filename whitelist** for local workflow injection:
- It only checks for `TESTING.md`, `DEBUGGING.md`, and `DEVELOPMENT.md`.
- It uses a static mapping of keywords for these specific files.
- **Impact**: Any local workflow with a different name (e.g., `manual-qa.md`, `deploy.md`) is completely ignored, even if it's highly relevant to the user prompt.

### 2. Global Workflow Injection
The hook currently loads only the **index file** (`aops-core/WORKFLOWS.md`).
- While the index contains a table of workflows and signals, the **content** (the specific steps) of global workflows (like `workflows/design.md`) is NOT injected into the hydration context.
- **Impact**: The hydrator (Haiku) must either guess the steps based on the name or use its own internal knowledge, which may deviate from the project's actual workflow definitions.

### 3. Instruction Contradiction
- `agents/prompt-hydrator.md` system prompt says: **"DO NOT READ files beyond your input file"**.
- `hooks/templates/prompt-hydrator-context.md` task description says: **"Read all workflow files you have selected"**.
- **Impact**: Ambiguous behavior for the hydrator agent, leading to either missed context (if it follows system prompt) or slow execution (if it follows template and makes multiple `read_file` calls).

### 4. Authoritative Location for Local Workflows
- **Location**: `.agent/workflows/` (files) or `.agent/WORKFLOWS.md` (index).
- **Maintenance**: Currently manual. There is no automated process to sync or validate these against the global index.

### 5. Format Optimality
The current `WORKFLOWS.md` format uses `[[wikilinks]]` which are good for human navigation but require additional resolution logic for LLMs if they are to be followed.

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
