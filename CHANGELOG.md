# Changelog

## [0.6.0](https://github.com/nicsuzor/academicOps/compare/v0.5.0...v0.6.0) (2026-03-10)

### Features

- **daily:** add check-in prompt for task graph accuracy ([#842](https://github.com/nicsuzor/academicOps/issues/842)) ([8481fb6](https://github.com/nicsuzor/academicOps/commit/8481fb651767daa53ac7622dbfb79757da106ef9))
- **dashboard:** optimize graph visualizations and improve Threaded Tasks UX ([#839](https://github.com/nicsuzor/academicOps/issues/839)) ([dca1bc8](https://github.com/nicsuzor/academicOps/commit/dca1bc8b5b259d836b685b29070984e030ef410a))
- **dashboard:** treemap layout and UX refinements ([#837](https://github.com/nicsuzor/academicOps/issues/837)) ([f43f955](https://github.com/nicsuzor/academicOps/commit/f43f95598c0364694b5ca5534477fd43fee7d5d5))
- **gates:** skip all gate dispatch in subagent sessions ([#844](https://github.com/nicsuzor/academicOps/issues/844)) ([34cb726](https://github.com/nicsuzor/academicOps/commit/34cb7265d3288411bf59f0e251c8dbc155657835))
- introduce intentions as first-class concept ([#851](https://github.com/nicsuzor/academicOps/issues/851)) ([a9e42cc](https://github.com/nicsuzor/academicOps/commit/a9e42cc4e958ff1ffce0ea7768c2df249186ae4d))
- **sleep:** implement sleep cycle agent and task quality triage ([#845](https://github.com/nicsuzor/academicOps/issues/845)) ([f93d647](https://github.com/nicsuzor/academicOps/commit/f93d647d91177d5f5ff3238398fef500f5894315))
- **tests:** E2E gate tests with real DEBUG_HOOKS raw stdin ([#850](https://github.com/nicsuzor/academicOps/issues/850)) ([e60e4e5](https://github.com/nicsuzor/academicOps/commit/e60e4e5095ae5fb83d7664b847560c564b67587f))

### Bug Fixes

- deployment auto-trigger for release-plz and plugin.json path ([#834](https://github.com/nicsuzor/academicOps/issues/834)) ([a7530ae](https://github.com/nicsuzor/academicOps/commit/a7530ae6e1203e90da90e8e70ced7b2d9797715e))
- **hooks:** use gate mode defaults for non-shell runtimes ([#843](https://github.com/nicsuzor/academicOps/issues/843)) ([8229ae2](https://github.com/nicsuzor/academicOps/commit/8229ae29973ac852312afb69710776352c8f818f))
- **polecat:** enable hydration and require python-dev for testing tasks ([#852](https://github.com/nicsuzor/academicOps/issues/852)) ([f3341a6](https://github.com/nicsuzor/academicOps/commit/f3341a62852990c8adeaaf700384fa256430855f))
- prevent AOPS_SESSIONS environment variable leakage in test paths ([#840](https://github.com/nicsuzor/academicOps/issues/840)) ([7a6fd9e](https://github.com/nicsuzor/academicOps/commit/7a6fd9e59038b8499e723b0d880a36d0f4c08abc))

### Documentation

- STATUS.md update and knowledge diffusion roadmap ([#826](https://github.com/nicsuzor/academicOps/issues/826)) ([6427a8e](https://github.com/nicsuzor/academicOps/commit/6427a8e4f865e3d5da6f16affcfd490ed3a28dd3))

### Miscellaneous

- **tests:** prune slow test suite from 135 to 30 ([#838](https://github.com/nicsuzor/academicOps/issues/838)) ([f31ac76](https://github.com/nicsuzor/academicOps/commit/f31ac762f736c8933665d451fb654e413eb01929))

## [0.5.0](https://github.com/nicsuzor/academicOps/compare/v0.4.0...v0.5.0) (2026-03-09)

### Features

- **dashboard:** Finalize Treemap styling and Holographic layouts ([#822](https://github.com/nicsuzor/academicOps/issues/822)) ([a56f48c](https://github.com/nicsuzor/academicOps/commit/a56f48c5934d889996660bcea2bd1e33cafff5d3))

### Bug Fixes

- **e2e:** resolve claude hydration gate enforcement failures ([#824](https://github.com/nicsuzor/academicOps/issues/824)) ([be411da](https://github.com/nicsuzor/academicOps/commit/be411da003a02324c7c2ae6ec8e6d08d5eaa29d5))

## [0.4.0](https://github.com/nicsuzor/academicOps/compare/v0.3.0...v0.4.0) (2026-03-09)

### Features

- add agent interaction extraction tool for hydrator quality assessment ([b782aa6](https://github.com/nicsuzor/academicOps/commit/b782aa63817d5dfedeb271202791a55f034e3491))
- agent interaction extraction tool for hydrator QA ([efead18](https://github.com/nicsuzor/academicOps/commit/efead1835872d826efa50647e18075c8b4ce7114))

### Bug Fixes

- address P[#8](https://github.com/nicsuzor/academicOps/issues/8) violations in gemini_home fixture ([bad10f0](https://github.com/nicsuzor/academicOps/commit/bad10f02d7b62743d5f03b210844dd34ffe8e959))
- address review feedback — path traversal security and axiom violation ([36842ae](https://github.com/nicsuzor/academicOps/commit/36842ae5e9037d86b78fa8f2483fb7914515ed56))
- **ci:** address PR [#829](https://github.com/nicsuzor/academicOps/issues/829) review feedback ([1416e32](https://github.com/nicsuzor/academicOps/commit/1416e323aa871e33f711256a9ed150863698eb61))
- **ci:** resolve merge-prep pipeline failures ([179ec3c](https://github.com/nicsuzor/academicOps/commit/179ec3c10d995708ede3350570f32540e529988c))
- **ci:** resolve merge-prep pipeline failures ([4d30b0d](https://github.com/nicsuzor/academicOps/commit/4d30b0d2cc87af49989304872922087eaf981c40))
- clear PYTHONPATH in test fixture to prevent false skip ([8587940](https://github.com/nicsuzor/academicOps/commit/858794021c4a62e21b326e4f25b48160ddfb6c0b))
- gracefully skip tests when Gemini build prerequisites are missing ([001d875](https://github.com/nicsuzor/academicOps/commit/001d875ab06d470b12e38291459370a5826dfeb9))
- remove duplicate import and update stale docstring defaults ([1995a83](https://github.com/nicsuzor/academicOps/commit/1995a8392d972931206ee92b7907838ea18eecb5))

### Code Refactoring

- **ci:** replace environment gate with native checks + approval ([46065ce](https://github.com/nicsuzor/academicOps/commit/46065ceea9fe367c97f54507645579bcd37d3ea7))
- **ci:** replace environment gate with native checks + approval ([c7a4e51](https://github.com/nicsuzor/academicOps/commit/c7a4e51eb1e67f0c5bbf41cde512a3faaa1e2a00))

### Tests

- enable and verify Gemini CLI hooks in headless environment ([e1c8494](https://github.com/nicsuzor/academicOps/commit/e1c8494d8393e99065a25963272c494608ce7fce))
- enhance headless test harness and verify Gemini hooks ([3e4b11e](https://github.com/nicsuzor/academicOps/commit/3e4b11eb675319becc1a8ea507767bb28a1a1afa))

### Miscellaneous

- fix pytest failures by adding missing pytest-env dependency ([#821](https://github.com/nicsuzor/academicOps/issues/821)) ([7821228](https://github.com/nicsuzor/academicOps/commit/78212282b2f272ea065e7fdeaac4cc6e1e40c09b))

## [0.3.0](https://github.com/nicsuzor/academicOps/compare/v0.2.47...v0.3.0) (2026-03-08)

### Features

- add operator/spectral treemap patterns and enhanced node shapes ([ae432d9](https://github.com/nicsuzor/academicOps/commit/ae432d99b11938d3ef610d8ed8312c5187b315b8))
- **dashboard:** enhance layout, view settings, and add theme prototypes ([740c93c](https://github.com/nicsuzor/academicOps/commit/740c93c05446ffedd90126c5b995fb165008e011))
- **dashboard:** implement Operator System UI from Stitch PRD ([0e96a58](https://github.com/nicsuzor/academicOps/commit/0e96a58770515f588cbaf064197f6fc1c93e93c4))
- **dashboard:** read graph data from $AOPS_SESSIONS with per-layout API ([52236ef](https://github.com/nicsuzor/academicOps/commit/52236ef3d1d7d4b73a086241def462a9d818280c))
- **dashboard:** refactor Svelte dashboard with streamlined CSS and layout ([4e40054](https://github.com/nicsuzor/academicOps/commit/4e40054ee2e2147d316695a36cad3a49c0426516))
- **dashboard:** refine UI styling and add QA screenshots ([f29044a](https://github.com/nicsuzor/academicOps/commit/f29044ad16799aceab1937af38216ca84959b382))
- **dashboard:** SvelteKit overwhelm dashboard with 5 graph views ([cb8ee96](https://github.com/nicsuzor/academicOps/commit/cb8ee96a19de249056a3fbf705c8bd604d8d54a5))
- **dashboard:** update app.css and add QA screenshots ([a924e03](https://github.com/nicsuzor/academicOps/commit/a924e03ffef226861875a9e1d33e72da3e09cd18))
- **dashboard:** update test_dump and add QA screenshots ([97b7bb5](https://github.com/nicsuzor/academicOps/commit/97b7bb5b77a85be93ba679cbd4658e002b62f6fc))
- **dashboard:** wire SvelteKit dashboard to existing data files ([071d276](https://github.com/nicsuzor/academicOps/commit/071d27684db4688aa5ed68c9771c12675c9ef94e))
- **dashboard:** wire SvelteKit dashboard to existing data files ([3555460](https://github.com/nicsuzor/academicOps/commit/3555460b058004cbc467fa3bd976d8fe9dd167c6))

### Bug Fixes

- add 7 missing .md files to Gemini extension build ([f6c637d](https://github.com/nicsuzor/academicOps/commit/f6c637d0c14e76e56a6f659e6aea8fe5ff0e4c2c))
- add missing .md files to Gemini extension build ([24eb346](https://github.com/nicsuzor/academicOps/commit/24eb346c7c78447363dcde12de0bdff0a69c4199))
- add missing constants.ts required by graph data module ([fd42009](https://github.com/nicsuzor/academicOps/commit/fd420093b39fa40bcbe062dd182f1b739fc1b309))
- add missing constants.ts, remove leaked hostname, fix undefined CSS var ([9a6b526](https://github.com/nicsuzor/academicOps/commit/9a6b526d19281f4287dcab175d44ff27fa2defe4))
- address review feedback on hardcoded paths and CSS specificity ([4a312ae](https://github.com/nicsuzor/academicOps/commit/4a312ae74030f067d0c7849e1636722680cca3e8))
- correct manifest version to 0.2.47 and add missing changelog types ([d0c2cda](https://github.com/nicsuzor/academicOps/commit/d0c2cda9b4ead1c5f55cc8c90cec7ccc59bb97a6))
- **dashboard:** use relative paths and remove hardcoded Mac paths ([4b9ee7a](https://github.com/nicsuzor/academicOps/commit/4b9ee7a42bf3a6f31c9db4c43c2315ab16bdaafd))
- derive skip list from HOME env instead of hardcoding usernames ([815b472](https://github.com/nicsuzor/academicOps/commit/815b4726b0202ee180505d1d068c7f567ea0c663))
- fail fast on missing framework files instead of returning sentinel ([0099287](https://github.com/nicsuzor/academicOps/commit/0099287fb248efa15aeb877c1af9e6f066152a6e))
- fail fast when AOPS_SESSIONS is not set in graph API ([d9ce540](https://github.com/nicsuzor/academicOps/commit/d9ce5406e0db5723feb350ad0c1a5ca30cc3f51a))
- populate focusNeighborSet in toggleFocus and track reactive deps ([eabeaaa](https://github.com/nicsuzor/academicOps/commit/eabeaaad4330b9444d60d73748d03e2dbf71dbfa))
- remove 8.9MB unused stitch design assets and dead aliases ([97e2432](https://github.com/nicsuzor/academicOps/commit/97e243299214f83e090a0af3eb7fe2547e523e0a))
- remove dead Python bridge script from SvelteKit source tree ([4f4aa6b](https://github.com/nicsuzor/academicOps/commit/4f4aa6b872a80b70955d161dea8f80770f9c66b2))
- remove orphaned root PNGs and fix hardcoded path in test_dump.py ([2c64a0c](https://github.com/nicsuzor/academicOps/commit/2c64a0c46fe46eb36437e686ebde262c598e227a))
- remove out-of-scope artifact and dead store properties ([117a73a](https://github.com/nicsuzor/academicOps/commit/117a73ab1182c3c5b4aad5ec60495202e5ab0975))
- remove out-of-scope Python bridge script from SvelteKit PR ([76fb8c4](https://github.com/nicsuzor/academicOps/commit/76fb8c47d9b2f5f0ffbcd752a2e51932b5b5356d))
- remove out-of-scope root-level artifacts and dead Python bridge scripts ([72946f7](https://github.com/nicsuzor/academicOps/commit/72946f7affbe686326188aff97ed887bf936ffd3))
- return sentinel instead of empty string for missing framework files ([189a13b](https://github.com/nicsuzor/academicOps/commit/189a13bf7eeb249d5e8675d545c52415d3b67b2f))
- revert out-of-scope design-md skill assets from dashboard PR ([f73fae1](https://github.com/nicsuzor/academicOps/commit/f73fae1c8f519d38215952323cd569d5b31237bf))
- revert out-of-scope placeholder HTML files from repo root ([89b8b2a](https://github.com/nicsuzor/academicOps/commit/89b8b2aee4d6bd2adf43c5f2dbde207fdb45c4a0))
- sanitize layout parameter to prevent path traversal ([b8ffb3f](https://github.com/nicsuzor/academicOps/commit/b8ffb3fc3081761018d1fcbf0e3d94a10c616993))
- sentinel for missing framework files in hydrator context ([807e2dc](https://github.com/nicsuzor/academicOps/commit/807e2dcb03cf2e9e729e66a4dd72ef5bd971850c))

### Code Refactoring

- **tests:** use AST parsing for items_to_copy extraction ([f4caa11](https://github.com/nicsuzor/academicOps/commit/f4caa11e68d563a6d7a14e95f8ce567bb152773d))

### Documentation

- add data pipeline architecture spec for SvelteKit dashboard ([542d908](https://github.com/nicsuzor/academicOps/commit/542d9088c48306a9313fb36ec48881afeb7fa194))
- **qa:** add Svelte dashboard QA results 2026-03-07 ([3470c41](https://github.com/nicsuzor/academicOps/commit/3470c41df8ca99d475edb74d3791c4c752c5353d))
- save enhanced Stitch prompt for Overwhelm Dashboard UX refinement ([7192bfe](https://github.com/nicsuzor/academicOps/commit/7192bfe9a91cbfa0531c1adbbce4ba361e619448))
- update planning web theme guide ([1226cb9](https://github.com/nicsuzor/academicOps/commit/1226cb91fd1f71edc0d03d79c2677588d0ee17f4))

### CI/CD

- enable release-please for automated release management ([601a735](https://github.com/nicsuzor/academicOps/commit/601a735f852ab22841c3d6ea0b109127348a3c9f))
- enable release-please for automated releases ([1e281b9](https://github.com/nicsuzor/academicOps/commit/1e281b90ba311d473b767551431d7654a01aceae))

### Miscellaneous

- add dashboard HTML prototypes and DESIGN.md ([04e5037](https://github.com/nicsuzor/academicOps/commit/04e50376de1728a698d93364736c5b70befcfabb))
- add design-md skill assets and skills-lock.json ([e79ad79](https://github.com/nicsuzor/academicOps/commit/e79ad7950954473f2524cd613683471eee1b7480))
- add holographic dashboard screenshot ([de60f13](https://github.com/nicsuzor/academicOps/commit/de60f13c068a1d819eff6620c6e9e816ee78b1c2))
- add holographic task editor screenshot ([3a1aba7](https://github.com/nicsuzor/academicOps/commit/3a1aba7113b64a3ee6d158bf54e7bc21a9be03d5))
- add operator dashboard screenshot ([7c63fd3](https://github.com/nicsuzor/academicOps/commit/7c63fd3773facf9c9c794cf28c3f9e3ecb6a9a48))
- add operator task editor screenshot ([096c205](https://github.com/nicsuzor/academicOps/commit/096c2053d2b7dd852c089676dc2cac62670445f2))
- add operator task graph screenshots ([0e412c2](https://github.com/nicsuzor/academicOps/commit/0e412c20c8985fd1810b599c29a54709f885e478))
- update dashboard page and add threaded tasks screenshot ([24418f6](https://github.com/nicsuzor/academicOps/commit/24418f6ebbf13f53951d31665a109726175d366f))
