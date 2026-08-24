---
id: workflows-three-source-template-discovery
title: Three-Source Workflow Template Discovery Contract
type: spec
category: workflow
status: ready
tags: [spec, workflow, templates, discovery, three-tier, resolution, brief, v0.8]
related: [[workflows-template-library]], [[workflows-task-pipeline]], [[aops-composable-workflow-system]]
---

# Three-Source Workflow Template Discovery Contract

## 1. Context and Architectural Foundation

Workflow templates provide the reusable operational units that composing passes (such as `brief` §5) assemble to structure execution and verification. In v0.4 through v0.7, template discovery relied on a hybrid registry model where templates in the Personal Knowledge Base (PKB) were gated by explicit registration in central index documents (`pkb-workflow-index` and `inde_1c34dd83`), enforcing the invariant that _"A template document exists in the PKB only once it is listed below"_.

This specification establishes the **Three-Source Workflow Template Discovery Contract**, restoring and extending dynamic discovery across three tiers:

1. **Project Tier**: Project-local templates in `$CWD/.agents/templates/*.md`.
2. **PKB Tier**: Dynamic personal templates stored across the PKB graph discovered by `type: template`.
3. **Universal Core Tier**: Shipped framework templates in `plugins/pkb/workflows/process/*.md`.

This contract removes the registry gate requirement, specifies the project tier convention, formalizes the resolution order and collision semantics, settles the fate of existing registries, and provides deterministic blind-scanning rules for composing agents.

## 2. Framework Gate Output Block

Per `framework-gate` requirements for modifications to shipped skills and workflow library contracts:

```yaml
framework-gate:
  component_modified:
    - "plugins/pkb/skills/brief/SKILL.md (Section 5: Dual-Tier -> Three-Source)"
    - "specs/workflows/template-library.md (Architectural references)"
    - "specs/workflows/three-source-template-discovery.md (New contract spec)"
  relevant_spec: "specs/workflows/three-source-template-discovery.md"
  indices_needing_update:
    - "specs/workflows/template-library.md"
    - "plugins/pkb/workflows/INDEX.md"
    - "pkb-workflow-index (Transition to MoC)"
    - "inde_1c34dd83 (Transition to MoC)"
  governance_level: "Framework Code & Workflow Specification (Requires human sign-off via aops_1f0a5f4c prior to implementation merge)"
```

## 3. The Three Sources (AC 2)

Composing agents discover candidate templates by scanning three distinct sources:

| Source Tier           | Location / Target                    | Enumeration Method                                                                     | Resolution Position         | Collision Rule                                                                   |
| :-------------------- | :----------------------------------- | :------------------------------------------------------------------------------------- | :-------------------------- | :------------------------------------------------------------------------------- |
| **1. Project Tier**   | `$CWD/.agents/templates/*.md`        | Directory enumeration over filesystem at `$CWD/.agents/templates/` matching `*.md`     | **1st (Highest priority)**  | Overrides both PKB and Universal templates with matching slug.                   |
| **2. PKB Tier**       | PKB Knowledge Graph                  | Dynamic query via MCP `list_documents(type="template")` (or `search(type="template")`) | **2nd (Medium priority)**   | Overrides Universal templates with matching slug; shadowed by Project templates. |
| **3. Universal Tier** | `plugins/pkb/workflows/process/*.md` | Enumerate `.md` files in plugin workflow process directory via git / filesystem        | **3rd (Baseline priority)** | Fallback baseline. Shadowed by Project and PKB templates.                        |

### Resolution Order and Collision Semantics (Fork 1)

When a template identifier or normalized slug (e.g. `feature-dev`, `email-triage`, `wf-qa`) resolves in more than one source:

1. **Resolution Priority**:
   $$\text{Project Tier} \succ \text{PKB Tier} \succ \text{Universal Tier}$$
2. **Slug Normalization**: Matching is case-insensitive and normalized with respect to the `wf-` prefix (e.g., `feature-dev`, `wf-feature-dev`, and `wf_feature_dev` are treated as the same logical slug).
3. **Atomic Shadowing**: A higher-priority source completely and atomically shadows a lower-priority source with the same slug. No multi-tier AST or section-level merging is performed; workflow templates are atomic markdown documents composed in-context by agent comprehension.
4. **Observability**: When a template collision is resolved via shadowing, the composing pass logs an informational note in the composition trace (e.g. `Resolved 'feature-dev' from Project tier; shadowed Universal 'feature-dev.md'`).

## 4. The `$CWD/.agents/templates` Project Convention (Fork 2, AC 3)

The Project Tier enables repository-specific and project-local workflow templates to live directly within the working codebase.

### Specification

1. **Path**: Exactly `$CWD/.agents/templates/` relative to the active workspace root / current working directory (`$CWD`).
2. **File Format & Structure**:
   - Flat directory of markdown files ending in `.md` (e.g., `$CWD/.agents/templates/deploy-staging.md`).
   - YAML Frontmatter Schema:
     ```yaml
     ---
     title: "Deploy to Staging Pipeline"
     type: template
     category: process # or gate
     description: "One-line routing summary for agent scanning"
     tags: [deploy, staging, release]
     ---
     ```
   - Standard Body Sections:
     - `## Purpose / Routing Signals` — When to select and when NOT to select this template.
     - `## Steps / Checklist` — Concrete sequence of operational activities.
     - `## Exit Routing / Acceptance Criteria` — Verification gates required for completion.
3. **VCS and Synchronization**:
   - Tracked in the project's own version control system (Git) alongside repository code.
   - Project-local: Not automatically synced into the personal PKB graph or academicOps core distribution.
4. **Defined Behaviour When Directory is Absent**:
   - The absence of `$CWD/.agents/templates/` is the standard baseline case across standard repositories.
   - If the directory does not exist or contains no `.md` files, the Project Tier enumeration returns an empty list (`[]`) immediately without raising errors, warnings, or interactive prompts.
   - The discovery process falls through cleanly to the PKB and Universal tiers.

## 5. Deprecation of Registry Gate & Fate of Registries (Fork 3, AC 4)

### Repeal of Registry Exclusivity

The invariant _"A template document exists in the PKB only once it is listed below"_ in `pkb-workflow-index` is explicitly repealed. Dynamic discovery via `type: template` is the authoritative mechanism for the PKB tier.

### Recommendation for Registries (`pkb-workflow-index` & `inde_1c34dd83`)

Submitted for human sign-off on [[aops_1f0a5f4c]]:

- **Transition to Curated Maps of Content (MoCs)**: Both `pkb-workflow-index` (portable templates) and `inde_1c34dd83` (non-portable templates) are retained as `type: index` Maps of Content for human review, taxonomy navigation, and agent orientation.
- **Decoupled from Composition**: Composing passes (`brief` §5) no longer consult or require registration in either index.

### Colocation of Warnings & Metadata

To eliminate drift between registry notes and document bodies, all operational warnings are colocated directly on the template documents:

1. **Stage-2 Composition Fragments**:
   - Frontmatter tag: `tags: [..., wf-fragment]` or frontmatter field `composition_type: fragment`.
   - Body banner:
     ```markdown
     > [!WARNING]
     > **Stage-2 Composition Fragment**: This document defines sub-process logic for composing passes. NEVER dispatch standalone.
     ```
2. **Retired / Superseded Templates**:
   - Frontmatter: `status: retired`, `superseded_by: "<canonical-id>"`, `tags: [..., retired]`.
   - Body banner:
     ```markdown
     > [!IMPORTANT]
     > **RETIRED TEMPLATE**: Superseded by [[<canonical-id>]]. Do not compose.
     ```
3. **Custom / Non-Portable Templates**:
   - Frontmatter tag: `tags: [..., custom-template, <project-name>]` or frontmatter field `scope: project`.
   - Body description naming the repo/infrastructure dependency.

## 6. Blind-Scanning Classification Rules & Live 42-Document Validation (Fork 4, AC 5)

Without relying on a registry index, a blind-scanning composing agent evaluates PKB documents matching `type: template` using deterministic rules:

### Blind-Scanning Rules

1. **Filter 1 (Lifecycle State)**: If document has `status: retired` or `status: cancelled`, or tags include `retired` / `superseded`, exclude from candidate composition pool. **Frontmatter alone is not sufficient**: some retired templates are marked only in the body, by an opening `# RETIRED` heading or a `## Retired — superseded by …` section. Read the opening lines, not just the frontmatter.
2. **Filter 2 (Instantiation / Instance Nodes)**: If document title or id contains datestamp patterns (e.g. `-\d{8}-\d{4}-`) or represents an active execution task, exclude from template library pool.
3. **Filter 3 (Composition Fragments vs. Dispatchable Templates)**: A fragment is a sub-step that is only meaningful composed into another process and must never be dispatched standalone. Identify it by the `planner-data` tag, which as of 2026-08-24 marks the fragment set exactly and nothing else, corroborated by the fragment's own first heading (`## <slug> — step: …`). Confirm against the document body before classifying. Note that `module-f` sits on every v0.4-era template and `prose-lens` separates process templates from gate templates — **neither distinguishes a fragment**, and a `wf-fragment` tag does not occur anywhere in the corpus.
4. **Filter 4 (Project Scope Matching)**: If document is tagged `custom-template` or has project-specific tags (e.g. `wikijuris`), match only if the current task's project matches. Scope may also be carried in a `project:` frontmatter field rather than a tag; check both.

### Empirical Validation on the Live PKB Template Corpus

Measured on 2026-08-20 via `pkb__list_documents(type="template")`, when the corpus held 42 documents.

**This table is a dated measurement, not the library.** Re-measured 2026-08-24: 47 documents. All 42 rows below still resolve; five templates have been added since and are not listed here (`temp_007e629e`, `temp_8804b618`, `temp_c8694d7e`, `temp_f30d20cb`, `tpl_launch_pattern_smoke_test`). Enumerate the tier to see the library; read this table only for the classification worked examples. The `workflow-library` skill produces a current listing on demand, which is why this table is not maintained.

| #  | ID / Permalink                | Document Title                                              | Blind-Scan Classification | Operational Routing / Disposition                                                                                                                                                                                         |
| :- | :---------------------------- | :---------------------------------------------------------- | :------------------------ | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 1  | `tpl_daily`                   | Instructions for creating or updating a daily note          | Canonical Workflow        | Dispatchable: Sole canonical daily note protocol                                                                                                                                                                          |
| 2  | `brain_arc_12bb1c27`          | TEMPLATE: ARC grant review preparation (per application)    | Specialized Template      | Dispatchable: Scoped to ARC grant peer review                                                                                                                                                                             |
| 3  | `brain-481c5692`              | TEMPLATE: Process a session/plenary transcript              | Specialized Template      | Dispatchable: Scoped to transcript synthesis                                                                                                                                                                              |
| 4  | `temp_6ade71d9`               | TEMPLATE: acceptance spot-check — dispatched worker round   | Specialized Template      | Dispatchable: QA spot-check procedure                                                                                                                                                                                     |
| 5  | `temp_16ba109c`               | Template: Blind Comparison & Transcript Audit Procedure     | Specialized Template      | Dispatchable: Audit benchmarking procedure                                                                                                                                                                                |
| 6  | `aops_cd98ee81`               | Template: Step-by-Step Interactive Agent Instruction Tuning | Specialized Template      | Dispatchable: Harness tuning procedure                                                                                                                                                                                    |
| 7  | `temp_f4a9cb82`               | wf-agentic-e2e-certification                                | Portable Process Template | Dispatchable: Framework certification workflow                                                                                                                                                                            |
| 8  | `wf_audit_e1822280`           | wf-audit-governance                                         | Portable Process Template | Dispatchable: Governance audit workflow                                                                                                                                                                                   |
| 9  | `wf_batch_21baa604`           | wf-batch-fanout                                             | Portable Process Template | Dispatchable: Batch fanout workflow                                                                                                                                                                                       |
| 10 | `wf-blind-proof`              | wf-blind-proof                                              | Portable Process Template | Dispatchable: Verification procedure                                                                                                                                                                                      |
| 11 | `wf_boundary_7088958d`        | wf-boundary-review                                          | **Stage-2 Fragment**      | Fragment: Sub-step review only; never dispatch standalone                                                                                                                                                                 |
| 12 | `wf-brief-composition-verify` | wf-brief-composition-verify                                 | Portable Gate Template    | Dispatchable: Composition verification gate                                                                                                                                                                               |
| 13 | `wf_capstone_73d7ce86`        | wf-capstone-verify                                          | **Stage-2 Fragment**      | Fragment: Sub-step verification only; never dispatch standalone                                                                                                                                                           |
| 14 | `wf-constraint-check`         | wf-constraint-check                                         | Portable Gate Template    | Dispatchable: Constraint verification gate                                                                                                                                                                                |
| 15 | `wf_critique_decd156b`        | wf-critique-lens                                            | Portable Process Template | Dispatchable: Critique evaluation workflow                                                                                                                                                                                |
| 16 | `wf-daily-note`               | wf-daily-note — Daily Note Generation Protocol              | **Retired Template**      | Excluded: Superseded by `tpl_daily` (`tags: [retired, superseded]`)                                                                                                                                                       |
| 17 | `kb_cbe83893`                 | wf-debug-framework-issue                                    | Portable Process Template | Dispatchable: Root cause analysis workflow                                                                                                                                                                                |
| 18 | `wf_1aa15796`                 | wf-decompose                                                | Portable Process Template | Dispatchable: Task decomposition workflow                                                                                                                                                                                 |
| 19 | `wf-design-conversation`      | wf-design-conversation                                      | Portable Process Template | Dispatchable: Iterative design workflow                                                                                                                                                                                   |
| 20 | `kb_d1f982cd`                 | wf-design-new-component                                     | Portable Process Template | Dispatchable: Component architecture workflow                                                                                                                                                                             |
| 21 | `wf_635eab64`                 | wf-draft                                                    | **Stage-2 Fragment**      | Fragment: Draft formulation only; never dispatch standalone                                                                                                                                                               |
| 22 | `wf_fact_b828c939`            | wf-fact-check                                               | **Stage-2 Fragment**      | Fragment: Fact check step only; never dispatch standalone                                                                                                                                                                 |
| 23 | `wf_d0e942d3`                 | wf-handback                                                 | Portable Process Template | Dispatchable: Handback procedure                                                                                                                                                                                          |
| 24 | `wf-handover`                 | wf-handover                                                 | Portable Gate Template    | Dispatchable: Session handover gate                                                                                                                                                                                       |
| 25 | `wf-human-approval`           | wf-human-approval                                           | Portable Gate Template    | Dispatchable: Sign-off approval gate                                                                                                                                                                                      |
| 26 | `wf_23a5a1c6`                 | wf-hydrate                                                  | **Stage-2 Fragment**      | Fragment: Disambiguation index step; never dispatch standalone                                                                                                                                                            |
| 27 | `wf-map-then-wire`            | wf-map-then-wire                                            | Portable Process Template | Dispatchable: Incremental wiring workflow                                                                                                                                                                                 |
| 28 | `wf-outbound-review`          | wf-outbound-review                                          | Portable Gate Template    | Dispatchable: Outbound review gate                                                                                                                                                                                        |
| 29 | `wf-pkb-memory-consolidation` | wf-pkb-memory-consolidation                                 | Portable Process Template | Dispatchable: Zettelkasten consolidation protocol                                                                                                                                                                         |
| 30 | `wf-qa`                       | wf-qa                                                       | Portable Gate Template    | Dispatchable: Standard QA gate                                                                                                                                                                                            |
| 31 | `wf_qa_b4b7f9c5`              | wf-qa-around                                                | **Stage-2 Fragment**      | Fragment: Sub-step QA loop; never dispatch standalone                                                                                                                                                                     |
| 32 | `wf_qa_d27c104b`              | wf-qa-verify                                                | Portable Gate Template    | Dispatchable: QA verification gate                                                                                                                                                                                        |
| 33 | `wf_refine_6ef85da2`          | wf-refine-loop                                              | **Stage-2 Fragment**      | Fragment: Refinement loop step; never dispatch standalone                                                                                                                                                                 |
| 34 | `wf_risk_79290491`            | wf-risk-profiles                                            | Portable Process Template | Dispatchable today. Retirement is recommended but **not performed** and is sequenced behind other work ([[task_retire_risk_profiles]]) — the document carries no retirement marker and every composing pass still sees it |
| 35 | `kb_831042d0`                 | wf-self-test                                                | Portable Gate Template    | Dispatchable: Framework hook self-test gate                                                                                                                                                                               |
| 36 | `kb_4d8dc3c6`                 | wf-session-hook-forensics                                   | Portable Process Template | Dispatchable: Session forensics workflow                                                                                                                                                                                  |
| 37 | `wf_signoff_16985750`         | wf-signoff-brief                                            | **Stage-2 Fragment**      | Fragment: Signoff brief spec; never dispatch standalone                                                                                                                                                                   |
| 38 | `wf-signoff-loop`             | wf-signoff-loop                                             | Portable Gate Template    | Dispatchable: Principal signoff review loop                                                                                                                                                                               |
| 39 | `wf_tdd_5b47ec98`             | wf-tdd-cycle                                                | Portable Process Template | Dispatchable: TDD development cycle                                                                                                                                                                                       |
| 40 | `wf-verification`             | wf-verification                                             | Portable Gate Template    | Dispatchable: Core evidence verification gate                                                                                                                                                                             |
| 41 | `wf-visual-qa-loop`           | wf-visual-qa-loop                                           | Portable Process Template | Dispatchable: Visual screenshot QA convergence loop                                                                                                                                                                       |
| 42 | `temp_b47ca185`               | wf-wikijuris-external-contribution-integration              | Custom / Scoped Template  | Dispatchable IFF project is `wikijuris`                                                                                                                                                                                   |

## 7. Specification for `brief` §5 Rewrite (AC 6)

The implementation replacing `plugins/pkb/skills/brief/SKILL.md` Section 5 ("The Dual-Tier Library Architecture", lines 220–229) shall read as follows:

```markdown
### The Three-Source Workflow Template Discovery Architecture

Composing passes discover workflow templates dynamically across three sources without requiring central registry lookups:

1. **Project-Local Templates (Project Tier)** — `$CWD/.agents/templates/*.md`. Project-specific workflows and overrides. If `$CWD/.agents/templates` is absent, returns empty list.
2. **PKB Graph Templates (PKB Tier)** — Dynamic templates stored in the PKB. Discover via `pkb__list_documents(type="template")` (or `pkb__search(type="template")`). Filter out retired templates (`status: retired` or tag `retired`), datestamped instance notes, and distinguish Stage-2 composition fragments (`wf-hydrate`, `wf-draft`, etc.) from dispatchable templates.
3. **Universal Core Workflows (Core Tier)** — `plugins/pkb/workflows/process/*.md` catalogued in `plugins/pkb/workflows/INDEX.md`. Universal, immutable, version-controlled baseline templates.

#### Resolution and Collision Order:

When template slugs collide across sources, apply deterministic resolution order:
$$\text{Project Tier} \succ \text{PKB Tier} \succ \text{Universal Tier}$$

The higher-priority template cleanly shadows the lower-priority template.

**DO NOT GUESS.** Read and critically apply each template at composition time, every time.

**HALT IF THERE IS NO PROCESS.** If a template you need exists in none of the three tiers, that is a library gap. Name it. Do not freelance a process to fill it.
```

## 8. Integration Test Design (AC 8)

The integration test suite maps one test per acceptance criterion (AC 2 through AC 6), each verifying correct behavior and asserting against distinct failure modes:

```python
# test_three_source_template_discovery.py
import pytest
from pathlib import Path

class TestThreeSourceTemplateDiscovery:
    """Integration tests for Three-Source Template Discovery Contract (AC 2-6)."""

    def test_ac2_resolution_order_and_collision_shadowing(self, tmp_path, mock_pkb, mock_universal):
        """
        AC 2: Verify Project > PKB > Universal resolution priority and collision shadowing.
        Failure mode detected: Lower tier incorrectly takes precedence or collision causes illegal merge.
        """
        slug = "feature-dev"
        # Setup duplicate template across all 3 tiers with distinct markers
        project_dir = tmp_path / ".agents" / "templates"
        project_dir.mkdir(parents=True)
        (project_dir / f"{slug}.md").write_text("TIER: PROJECT")
        mock_pkb.add_document(id=f"wf-{slug}", type="template", body="TIER: PKB")
        mock_universal.add_template(f"{slug}.md", body="TIER: UNIVERSAL")

        resolved = discover_template(slug, cwd=tmp_path, pkb_client=mock_pkb, universal_root=mock_universal)
        assert resolved.source == "project"
        assert "TIER: PROJECT" in resolved.content

        # Remove project tier -> PKB should win over Universal
        (project_dir / f"{slug}.md").unlink()
        resolved_pkb = discover_template(slug, cwd=tmp_path, pkb_client=mock_pkb, universal_root=mock_universal)
        assert resolved_pkb.source == "pkb"
        assert "TIER: PKB" in resolved_pkb.content

    def test_ac3_project_tier_absent_directory_and_structure(self, tmp_path, mock_pkb, mock_universal):
        """
        AC 3: Verify $CWD/.agents/templates convention and clean fallthrough when absent.
        Failure mode detected: Unhandled FileNotFoundError or error raised when .agents/templates does not exist.
        """
        empty_cwd = tmp_path / "empty_repo"
        empty_cwd.mkdir()
        assert not (empty_cwd / ".agents" / "templates").exists()

        # Must return empty list for project tier without throwing
        project_templates = enumerate_project_templates(cwd=empty_cwd)
        assert project_templates == []

        # Overall discovery succeeds seamlessly using remaining tiers
        all_templates = enumerate_all_sources(cwd=empty_cwd, pkb_client=mock_pkb, universal_root=mock_universal)
        assert len(all_templates) > 0
        assert all(t.source in ["pkb", "universal"] for t in all_templates)

    def test_ac4_registry_decoupling_and_colocated_warnings(self, mock_pkb):
        """
        AC 4: Verify dynamic discovery finds templates not listed in pkb-workflow-index and reads warnings from document.
        Failure mode detected: Unregistered template is invisible or warnings are missed without index.
        """
        # Create un-indexed PKB template
        doc_id = "wf-brand-new-pipeline"
        mock_pkb.add_document(
            id=doc_id,
            type="template",
            tags=["workflow", "wf-template"],
            body="> [!WARNING]\n> Stage-2 Composition Fragment\n\nContent..."
        )
        # Ensure it is NOT in pkb-workflow-index
        index_doc = mock_pkb.get_document("pkb-workflow-index")
        assert doc_id not in index_doc.body

        # Discovery by type finds it
        pkb_templates = enumerate_pkb_templates(pkb_client=mock_pkb)
        found = next((t for t in pkb_templates if t.id == doc_id), None)
        assert found is not None
        assert found.is_fragment is True

    def test_ac5_blind_scan_filtering_on_42_document_set(self, live_42_pkb_corpus):
        """
        AC 5: Verify blind scan rules accurately classify fragments, retired templates, and dispatchable templates.
        Failure mode detected: Composition fragment or retired template misclassified as standalone dispatchable.
        """
        classified = [classify_pkb_template(doc) for doc in live_42_pkb_corpus]
        
        # Verify exactly 8 fragments identified
        fragments = [c for c in classified if c.category == "fragment"]
        assert len(fragments) == 8
        fragment_ids = {f.id for f in fragments}
        expected_fragments = {
            "wf_boundary_7088958d", "wf_capstone_73d7ce86", "wf_635eab64",
            "wf_fact_b828c939", "wf_23a5a1c6", "wf_qa_b4b7f9c5",
            "wf_refine_6ef85da2", "wf_signoff_16985750"
        }
        assert fragment_ids == expected_fragments

        # Verify retired templates excluded
        retired = [c for c in classified if c.category == "retired"]
        retired_ids = {r.id for r in retired}
        assert "wf-daily-note" in retired_ids

        # Verify canonical daily note identified
        canonical_daily = next(c for c in classified if c.id == "tpl_daily")
        assert canonical_daily.category == "canonical_workflow"

    def test_ac6_brief_section_5_composition_pass(self, sample_brief_input, mock_environment):
        """
        AC 6: Verify brief §5 composition pass executes 3-source discovery without forks.
        Failure mode detected: Brief composition halts or requires interactive disambiguation across sources.
        """
        composed_process = run_brief_section_5(sample_brief_input, env=mock_environment)
        assert composed_process.is_valid
        assert len(composed_process.inner_checklist) > 0
        assert len(composed_process.outer_nodes) > 0
```

## 9. Governance & Sign-off Gate (AC 9)

In accordance with `framework-gate` and `develop-specification` step 11:

- This specification contract is delivered via pull request referencing task `aops_50b695bb`.
- Implementation of skill updates (`plugins/pkb/skills/brief/SKILL.md`) and engine code is gated by human review and sign-off on [[aops_1f0a5f4c]] by Nic.
- No implementation PR shall be merged until `aops_1f0a5f4c` is resolved.
