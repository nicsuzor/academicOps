# Changelog

## [0.3.20](https://github.com/nicsuzor/academicOps/compare/v0.3.19...v0.3.20) (2026-04-21)

### Features

- /deep-research skill — Gemini Deep Research → PKB capture ([#650](https://github.com/nicsuzor/academicOps/issues/650)) ([d4bc1df](https://github.com/nicsuzor/academicOps/commit/d4bc1df54ee017337696ba622fb49955af0a26a9))
- **aops-core:** add end_session skill as default session close ([#652](https://github.com/nicsuzor/academicOps/issues/652)) ([ce64d54](https://github.com/nicsuzor/academicOps/commit/ce64d54a782c05cdf7d1631c981ae107ccca20e8))
- **daily:** add PR/workflow monitoring and auto-close loop ([#590](https://github.com/nicsuzor/academicOps/issues/590)) ([25fdbe2](https://github.com/nicsuzor/academicOps/commit/25fdbe2b3d14437fd560fef7b4e10346191fea70))
- define agent consumption path for context-map.json ([#595](https://github.com/nicsuzor/academicOps/issues/595)) ([9c4d84a](https://github.com/nicsuzor/academicOps/commit/9c4d84a1c2031df5d0ed6a152d30451b009f6b49))
- extend polecat sweep to scan review tasks and add completion evidence ([#603](https://github.com/nicsuzor/academicOps/issues/603)) ([aebfa62](https://github.com/nicsuzor/academicOps/commit/aebfa62e166d1bb663cf8c34c9b1d3fdd770d39f))
- **polecat:** set default model to claude-sonnet-4-6 for Claude crew sessions ([#608](https://github.com/nicsuzor/academicOps/issues/608)) ([92bb7e9](https://github.com/nicsuzor/academicOps/commit/92bb7e9be6c308d2b7b5ac320361cd75cd353e76))
- **review-pipeline:** context-map spec_dirs convention for spec-awar… ([#645](https://github.com/nicsuzor/academicOps/issues/645)) ([f8b3fae](https://github.com/nicsuzor/academicOps/commit/f8b3faefb0932b68ff3ef7a04027e0398cb0c7a2))
- **review-pr:** batch preflight, prior-review consolidation, halt conditions ([#634](https://github.com/nicsuzor/academicOps/issues/634)) ([e921c3a](https://github.com/nicsuzor/academicOps/commit/e921c3ad693cdef85c04294dd160698609b8186d))
- **review-pr:** tiered classifier for PR triage ([#632](https://github.com/nicsuzor/academicOps/issues/632)) ([9ee6293](https://github.com/nicsuzor/academicOps/commit/9ee62931f6afb4ba5dfc70b7df7d6deaabd0631f))
- **supervisor+review:** plan-review gate + context-map spec_dirs + /pull queued drift fix ([#638](https://github.com/nicsuzor/academicOps/issues/638)) ([1f51ae4](https://github.com/nicsuzor/academicOps/commit/1f51ae4fcc6e08e1f5aec75e9b60861cc11ef559))
- **supervisor:** plan-review gate — halt on non-queued, dispatch on queued ([#646](https://github.com/nicsuzor/academicOps/issues/646)) ([6e93888](https://github.com/nicsuzor/academicOps/commit/6e93888020333df21cda29020fb09be86fd6081b))
- **taxonomy:** add paused/someday; align status drift across specs ([#656](https://github.com/nicsuzor/academicOps/issues/656)) ([89853a0](https://github.com/nicsuzor/academicOps/commit/89853a08ba6f6e339d810e456c987f86477ef657))

### Bug Fixes

- **build:** replace CLAUDE_PLUGIN_ROOT with extensionPath in Gemini agent body text ([#622](https://github.com/nicsuzor/academicOps/issues/622)) ([926e476](https://github.com/nicsuzor/academicOps/commit/926e476cb250c10356f20a820a1c6bb28396212e))
- **commands:** /pull and consumers pull from queued (taxonomy drift fix) ([#644](https://github.com/nicsuzor/academicOps/issues/644)) ([1d79035](https://github.com/nicsuzor/academicOps/commit/1d79035daae8211c6531ccbd5f2b138423372370))
- **daily:** update mobile-capture-triage section reference (3 → 4) ([#630](https://github.com/nicsuzor/academicOps/issues/630)) ([cc48b55](https://github.com/nicsuzor/academicOps/commit/cc48b550c79319e9aaad71d8c7836d3084491a96))
- **dispatcher:** pass force=true on manual merge-prep override ([#586](https://github.com/nicsuzor/academicOps/issues/586)) ([044908b](https://github.com/nicsuzor/academicOps/commit/044908ba5524e058adf398febd678db2719287c7))
- **dispatcher:** skip trailer guard on RE-QUALIFY path in merge-prep-cron ([#587](https://github.com/nicsuzor/academicOps/issues/587)) ([ad4e59b](https://github.com/nicsuzor/academicOps/commit/ad4e59b7d19c732629124c90a061d60a961cd46a))
- **docker:** add gcc so cargo check works in polecat environment ([#648](https://github.com/nicsuzor/academicOps/issues/648)) ([2055689](https://github.com/nicsuzor/academicOps/commit/2055689ac67b566c6ac81b3039e713e334279306))
- **gemini:** ensure aops_core_rbg is accessible in plan mode ([#623](https://github.com/nicsuzor/academicOps/issues/623)) ([04be22a](https://github.com/nicsuzor/academicOps/commit/04be22a0c3746a4bb9e2b95e457d854636c64f11))
- **polecat/sync:** remove bootstrap guard; --check stops before mirrors ([#647](https://github.com/nicsuzor/academicOps/issues/647)) ([5a4cb74](https://github.com/nicsuzor/academicOps/commit/5a4cb74d3a4b407da249e75c5d169e20a17f5e3e))
- **polecat:** bound worktrees to $POLECAT_HOME/worktrees/ subdir ([#576](https://github.com/nicsuzor/academicOps/issues/576)) ([843506b](https://github.com/nicsuzor/academicOps/commit/843506bdaf74986659b3d6eb777ed2480fb58cc3))
- **polecat:** CLI -p flag overrides task.project throughout run lifecycle ([#578](https://github.com/nicsuzor/academicOps/issues/578)) ([3e56ef1](https://github.com/nicsuzor/academicOps/commit/3e56ef1aca3e429bda6b91abe144ca39024895a0))
- **polecat:** stub transcript records path to real Claude session transcript ([#593](https://github.com/nicsuzor/academicOps/issues/593)) ([0e40715](https://github.com/nicsuzor/academicOps/commit/0e40715dce78b770d3c217a1f19633e0afe074d5))
- **rbg:** plugin-relative AXIOMS.md include ([#607](https://github.com/nicsuzor/academicOps/issues/607)) ([07bb63d](https://github.com/nicsuzor/academicOps/commit/07bb63d38f1ab89146ea6ea5aed98ba56cf6bf0b))
- regenerate uv.lock in release-please PRs ([#606](https://github.com/nicsuzor/academicOps/issues/606)) ([9626f8b](https://github.com/nicsuzor/academicOps/commit/9626f8b50e60b3d646b231d8f15c689e077d270a))
- **tests:** accept Claude Code built-in tool names in agent validator ([#654](https://github.com/nicsuzor/academicOps/issues/654)) ([c521d20](https://github.com/nicsuzor/academicOps/commit/c521d20633c789a9a079df939ce247b502aa536d))
- **tests:** remove mix_stderr kwarg dropped in Click 8.2 ([#594](https://github.com/nicsuzor/academicOps/issues/594)) ([0b1b868](https://github.com/nicsuzor/academicOps/commit/0b1b8683cfcdfbe876a3fef6d866c6c62c2acfd3))
- **tests:** repair e2e integration test suite for v0.3.18 ([45852fe](https://github.com/nicsuzor/academicOps/commit/45852feb04033dabcaf63c61fc158d371d3c5b04))
- **tests:** repair e2e integration test suite for v0.3.18 ([#659](https://github.com/nicsuzor/academicOps/issues/659)) ([4c2f635](https://github.com/nicsuzor/academicOps/commit/4c2f6356dbb45ec7d465c9f4bdde51cdc33bafd3))
- update callers for PKB create_task structured return ([#585](https://github.com/nicsuzor/academicOps/issues/585)) ([961f6eb](https://github.com/nicsuzor/academicOps/commit/961f6eb714411d52033b47e3e8a1113aa4eb62ea))

### Code Refactoring

- **framework:** enforcement spec rewrite + custodiet→enforcer rename ([#625](https://github.com/nicsuzor/academicOps/issues/625)) ([1a5585d](https://github.com/nicsuzor/academicOps/commit/1a5585d4563a903665fede47245cf9f83d2b093d))
- merge butler + framework into aops skill with jr agent ([#581](https://github.com/nicsuzor/academicOps/issues/581)) ([7dd8f89](https://github.com/nicsuzor/academicOps/commit/7dd8f890aae46995d203681269cac6b8f40f6171))

### Documentation

- **specs:** observability SSoT — files × environments × processes + $AOPS_SESSIONS retirement analysis ([#592](https://github.com/nicsuzor/academicOps/issues/592)) ([2ce19f7](https://github.com/nicsuzor/academicOps/commit/2ce19f792559ead7187bbbdabc4a0556db87286c))
- **supervisor:** add event-driven monitoring instructions ([#605](https://github.com/nicsuzor/academicOps/issues/605)) ([1c10a57](https://github.com/nicsuzor/academicOps/commit/1c10a57fe0a229786adf9760046cd6cfa03b392f))
- **supervisor:** promote remote polecat SSH+tmux dispatch instructions ([cf4932f](https://github.com/nicsuzor/academicOps/commit/cf4932f10c57e9bd70c2bae1ddd0841358695935))
- **supervisor:** promote remote polecat SSH+tmux dispatch instructions ([#597](https://github.com/nicsuzor/academicOps/issues/597)) ([619010b](https://github.com/nicsuzor/academicOps/commit/619010b2b0c7ccd2449a7309fb48719822d758e8))
- **supervisor:** refine remote polecat dispatch and address review feedback ([#599](https://github.com/nicsuzor/academicOps/issues/599)) ([c98c6cb](https://github.com/nicsuzor/academicOps/commit/c98c6cb864223d042f8d988bba107b3c4300eb10))

### CI/CD

- update claude code workflows to use sonnet ([#619](https://github.com/nicsuzor/academicOps/issues/619)) ([e03b861](https://github.com/nicsuzor/academicOps/commit/e03b861646672ddbb8e3374b63aa423b9b36d7c3))

### Tests

- **e2e:** enable test_workspace_writes_visible_on_host for run paths ([414f428](https://github.com/nicsuzor/academicOps/commit/414f428ea222d699340a4690be7908ea2fc1f558))

### Miscellaneous

- **gha:** reduce GHA/Claude quota — delete 4 workflows, wire enforcer on CI trigger ([62599e8](https://github.com/nicsuzor/academicOps/commit/62599e86fab0b700626b1de668198022851e55b2))
