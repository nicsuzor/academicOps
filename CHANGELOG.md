# Changelog

## [0.3.79](https://github.com/nicsuzor/academicOps/compare/v0.3.78...v0.3.79) (2026-07-13)

### Features

- **actions:** add rbg PR review workflow triggered by label ([0e58bfa](https://github.com/nicsuzor/academicOps/commit/0e58bfa957e1db88f780109c9028c5fbb5664a09))
- **aops-extras:** implement workflow-system pipeline skills (aops_d6ae35af) ([c7f109d](https://github.com/nicsuzor/academicOps/commit/c7f109d288743d22ee485e7ed9e0635be9ad691d))
- **aops:** add polecat container certification track to E2E workflow ([#2209](https://github.com/nicsuzor/academicOps/issues/2209)) ([4663f82](https://github.com/nicsuzor/academicOps/commit/4663f820e3c447d9affd56765c46c9c8132d7555))
- **gates:** consolidate exit-reflection Stop gate, retire turn-based rbg counter ([#2223](https://github.com/nicsuzor/academicOps/issues/2223)) ([9554982](https://github.com/nicsuzor/academicOps/commit/9554982ac8ef2f6ed1977fbfb4136af5765a0f07))
- **install:** local dev installs aops-extras/aops-pkb too; hard-fail all plugins ([d37554f](https://github.com/nicsuzor/academicOps/commit/d37554f01a0d1ebf2cc0f5696feb6dc5e96407d2))
- **planner:** hydrate Context section from PKB history at decomposition ([#2219](https://github.com/nicsuzor/academicOps/issues/2219)) ([eb2af40](https://github.com/nicsuzor/academicOps/commit/eb2af407691a5eafeaebe73a55eed398f0603eb4))
- **polecat:** add dev-loop harness for live plugin testing on claude+agy ([8898071](https://github.com/nicsuzor/academicOps/commit/889807120c2801638bbad98d7293dbfef77f22d4))
- **polecat:** add lightweight containerized agent wrapper polecat/cli_lite.py ([62e0544](https://github.com/nicsuzor/academicOps/commit/62e0544422272037aa014a0eb56c8f2ba02b4949))

### Bug Fixes

- **aops-extras:** address adversarial evaluation findings (WS8) ([3dfa773](https://github.com/nicsuzor/academicOps/commit/3dfa77383b261beae4623ddb9dbf9a588c04d1eb))
- **build:** claude hooks.json location, consolidate install-dev, wire axioms ([6f5db5e](https://github.com/nicsuzor/academicOps/commit/6f5db5e2477318a68b10e5a2bfb70e80a58aaed2))
- **commands:** repoint /q and /maintain to situate and graph-maintenance skills ([76c955e](https://github.com/nicsuzor/academicOps/commit/76c955e5353710009625ffc7cd0fc143b74786c7))
- correct stale single-prefix PKB MCP tool names in explicit-toollist agents ([#2216](https://github.com/nicsuzor/academicOps/issues/2216)) ([9f14518](https://github.com/nicsuzor/academicOps/commit/9f145189fab280b3e003edee46718343526bea4d))
- **dev-crew:** sanitize + to - in live-edit mount version paths ([#2226](https://github.com/nicsuzor/academicOps/issues/2226)) ([db06d88](https://github.com/nicsuzor/academicOps/commit/db06d885bea47aa3349ad745ed464913c4675693))
- **docker:** dist-only local build, drop aops-core/pkb/extras, fix enablement ([c84a952](https://github.com/nicsuzor/academicOps/commit/c84a95207a72f8599366163b4f1f670bb6a3b527))
- **hooks:** accept string tool_output on PostToolUseFailure in normalize_input ([#2215](https://github.com/nicsuzor/academicOps/issues/2215)) ([d283cce](https://github.com/nicsuzor/academicOps/commit/d283cce2065835bea8589bc315d040b7dfff8a55))
- **transcripts:** subagent identity from meta.json, backfill task_id to frontmatter ([#2213](https://github.com/nicsuzor/academicOps/issues/2213)) ([fab03b1](https://github.com/nicsuzor/academicOps/commit/fab03b12474d173aad9c8361b8c7146409eb5824))

### Documentation

- **agents:** codify personalities-not-skills doctrine + audit skill bindings ([#2217](https://github.com/nicsuzor/academicOps/issues/2217)) ([4d2b336](https://github.com/nicsuzor/academicOps/commit/4d2b336d688669200bcce8cb1c147a29620be39a))
- **aops:** pin Workflow 12 closing-pipeline evidence to an orchestrator-rendered transcript ([a6921dd](https://github.com/nicsuzor/academicOps/commit/a6921ddd36e5744c1a520d0090d9651e746de907))
- **build:** consolidate BUILD.md into specs/build-and-install.md, fix stale claims ([9d1e901](https://github.com/nicsuzor/academicOps/commit/9d1e90105a4441bb270251e953678707c1e0e4a6))
- **build:** fix cross-references after releasing.md relocation ([a51b4fe](https://github.com/nicsuzor/academicOps/commit/a51b4fef7515fc6c69f80392895405965dfcac7c))
- **build:** relocate RELEASING.md into specs/, fix cross-references ([2e2026c](https://github.com/nicsuzor/academicOps/commit/2e2026c431461b3425f3cbdd8a557374b96a24bc))
- **enforcement:** rewrite enforcement.md + siblings for v0.4 ratified plan ([154ab76](https://github.com/nicsuzor/academicOps/commit/154ab761b89a1fbc8cc42a27fde93a40516fbec0))
- **gates:** scope QA gate to required (block) for polecat run sessions ([#2224](https://github.com/nicsuzor/academicOps/issues/2224)) ([6416142](https://github.com/nicsuzor/academicOps/commit/6416142b8698ad1ab7bad042d1907dd8ff0cb8f2))

### Tests

- **gates:** regression test for audit-complete sentinel placement (aops-84a6d6fa) ([#2225](https://github.com/nicsuzor/academicOps/issues/2225)) ([388429b](https://github.com/nicsuzor/academicOps/commit/388429b09d2e552c8de2a0246348028ab2569688))
