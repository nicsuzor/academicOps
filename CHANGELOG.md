# Changelog

## [0.3.21](https://github.com/nicsuzor/academicOps/compare/v0.3.20...v0.3.21) (2026-04-26)

### Features

- **automode:** rewrite classifier rules against A1–A10 axioms as prose-with-reasoning ([#729](https://github.com/nicsuzor/academicOps/issues/729)) ([7afc572](https://github.com/nicsuzor/academicOps/commit/7afc57267ee9101dab4f19c2fff56848d73b8108))
- **daily:** editor-friendly note + work-date targeting fix ([#674](https://github.com/nicsuzor/academicOps/issues/674)) ([bb8dec6](https://github.com/nicsuzor/academicOps/commit/bb8dec6f8170666811b92bc22456d00a5ac9dc91))
- **daily:** ensure today's daily note exists at session start ([#741](https://github.com/nicsuzor/academicOps/issues/741)) ([bb8202c](https://github.com/nicsuzor/academicOps/commit/bb8202c9733d8df3325ebbb129fab431fc161472))
- **daily:** strip prioritisation — report, don't rank ([#716](https://github.com/nicsuzor/academicOps/issues/716)) ([636efae](https://github.com/nicsuzor/academicOps/commit/636efae41692c4f786e4bb39c9c8da12b4f633ec))
- **daily:** Today's Log as editorial synthesis; retire Session Log table ([#719](https://github.com/nicsuzor/academicOps/issues/719)) ([88f2edf](https://github.com/nicsuzor/academicOps/commit/88f2edf5960c54f33032050c0b88d01b3aa7d20f))
- **enforcement:** orchestrator boundary Level 2 + Level 4 detection ([#682](https://github.com/nicsuzor/academicOps/issues/682)) ([bd115e7](https://github.com/nicsuzor/academicOps/commit/bd115e77dee15075d4350acad1c13d8f4e9dfab4))
- **gemini:** add handover and dump to activate_skill enum ([#710](https://github.com/nicsuzor/academicOps/issues/710)) ([b341ae9](https://github.com/nicsuzor/academicOps/commit/b341ae908690c28b4c92682dd243e61d04865da4))
- **lint:** add linter for autoMode axiom/rule references ([#748](https://github.com/nicsuzor/academicOps/issues/748)) ([8824e10](https://github.com/nicsuzor/academicOps/commit/8824e10dd4661ad5d5b2de177e428450cf368713))
- **marsha:** expand browser MCP toolset for runtime UX verification ([#706](https://github.com/nicsuzor/academicOps/issues/706)) ([a64aca0](https://github.com/nicsuzor/academicOps/commit/a64aca09e914ebfdeaabd09ce5ed6d659b1843d2))
- **planner:** show ASCII context tree after capture mode task creation ([#705](https://github.com/nicsuzor/academicOps/issues/705)) ([fe23eec](https://github.com/nicsuzor/academicOps/commit/fe23eec1145de0200f5d5b3615407cbd560e7485))
- **polecat:** push-or-fail integrity gates for A3/A8 ([#687](https://github.com/nicsuzor/academicOps/issues/687)) ([581994c](https://github.com/nicsuzor/academicOps/commit/581994c19712602dab61962cd8f1503fe72ca4e2))
- **project:** add idempotency, partial failure, secrets & polecat decisions to init.md ([#701](https://github.com/nicsuzor/academicOps/issues/701)) ([537cd2e](https://github.com/nicsuzor/academicOps/commit/537cd2ebcdbe1136ba94492af930969ef8a30016))
- **rules:** RULES.md as SSOT for fine-grained operational rules ([#732](https://github.com/nicsuzor/academicOps/issues/732)) ([2e21aaf](https://github.com/nicsuzor/academicOps/commit/2e21aafb311329fee03f63059f7dcbae9a6de0e7))
- **session-summary:** add hostname field to session metadata ([#708](https://github.com/nicsuzor/academicOps/issues/708)) ([d6ff84a](https://github.com/nicsuzor/academicOps/commit/d6ff84a2d48dfa121213a863f93c6e8289341147))
- ship aops-tools as a standalone plugin/extension ([#725](https://github.com/nicsuzor/academicOps/issues/725)) ([4dd27d0](https://github.com/nicsuzor/academicOps/commit/4dd27d04eac01b988bf07136021594009c7ffb3e))
- **spec:** scope /aops enforcement evidence loop (Steps 4-5) ([#749](https://github.com/nicsuzor/academicOps/issues/749)) ([7f17b83](https://github.com/nicsuzor/academicOps/commit/7f17b83cbe75bd8f9edb9cb3ed42ce6de36af697))
- **transcript:** support /dump handover blocks and full prompts in timeline_events ([#751](https://github.com/nicsuzor/academicOps/issues/751)) ([e03e258](https://github.com/nicsuzor/academicOps/commit/e03e2583787e6a5203445c0ac2dec8b899533dee))

### Bug Fixes

- **build:** remove MCP server config from antigravity dist ([cf3969e](https://github.com/nicsuzor/academicOps/commit/cf3969e12c9ebd30d9c420ca5bc336044d8f4bd5))
- **build:** remove MCP server config from antigravity dist ([#660](https://github.com/nicsuzor/academicOps/issues/660)) ([e66e5a7](https://github.com/nicsuzor/academicOps/commit/e66e5a73ef44abdcf5fc70ed88cb007c8550a7b9))
- **crew:** make /ms-playwright writable for Playwright MCP session cache ([#694](https://github.com/nicsuzor/academicOps/issues/694)) ([70a643b](https://github.com/nicsuzor/academicOps/commit/70a643bc9240c653e8bc3d3c1cf1c7b5970106d8))
- **docker:** pre-commit venv shebang, Stop hook timeout, pkb empty-release guard ([#672](https://github.com/nicsuzor/academicOps/issues/672)) ([2b2c680](https://github.com/nicsuzor/academicOps/commit/2b2c680231948a6d48c46853b77bde46695f1f0a))
- **enforcement:** register H91 Deadline heuristic in enforcement-map.md ([d7d49fc](https://github.com/nicsuzor/academicOps/commit/d7d49fcf6621b3b35f1e7e3407c2f36b8a3c8dc9))
- **enforcer:** give the GHA enforcer Edit/Write tools so it can push fixes ([#752](https://github.com/nicsuzor/academicOps/issues/752)) ([7f7f982](https://github.com/nicsuzor/academicOps/commit/7f7f982eb484ac61f89c53dac0e7bb0030abe0aa))
- **hooks:** categorize release_task as infrastructure to prevent handover gate re-trip ([#747](https://github.com/nicsuzor/academicOps/issues/747)) ([a6f3ebe](https://github.com/nicsuzor/academicOps/commit/a6f3ebef66a7d195d2d995ee0deb283f0073d6cb))
- **merge-prep:** verify server-side mergeability; diagnose squash-merge ghosts ([#722](https://github.com/nicsuzor/academicOps/issues/722)) ([c3005c9](https://github.com/nicsuzor/academicOps/commit/c3005c9eba4c294813d7b1547515e906a02c4e64))
- persist JSONL path so transcript.py finds Claude polecat sessions ([#671](https://github.com/nicsuzor/academicOps/issues/671)) ([51bda50](https://github.com/nicsuzor/academicOps/commit/51bda50f53587afd89701eac4bc0e906a95d10b4))
- **polecat:** branch fresh when re-dispatching squash-merged or stale-behind tasks ([#703](https://github.com/nicsuzor/academicOps/issues/703)) ([fb2de37](https://github.com/nicsuzor/academicOps/commit/fb2de37ed7fa46d79b2532186357af9cedb06513))
- **polecat:** friendly PKB_MCP_URL check at top of `polecat run` ([#698](https://github.com/nicsuzor/academicOps/issues/698)) ([568990a](https://github.com/nicsuzor/academicOps/commit/568990ae3a98eaa410d520f4f6845013e26afead))
- **polecat:** install build-essential so cc can link in aops-crew image ([#683](https://github.com/nicsuzor/academicOps/issues/683)) ([bc8ce6a](https://github.com/nicsuzor/academicOps/commit/bc8ce6abd79e2f835d5ef1df5c3646f22aa26040))
- **polecat:** pc sync reports success but doesn't close stale-mirror warning ([#736](https://github.com/nicsuzor/academicOps/issues/736)) ([2795263](https://github.com/nicsuzor/academicOps/commit/279526366b419b231feede69cd19a2f95c416080))
- **polecat:** pre-authorize shell for autonomous workers ([#702](https://github.com/nicsuzor/academicOps/issues/702)) ([25f52b0](https://github.com/nicsuzor/academicOps/commit/25f52b07aee092bb76482363012d3ac676b63972))
- **polecat:** pre-trust /workspace for Claude and Gemini in container ([#673](https://github.com/nicsuzor/academicOps/issues/673)) ([478783d](https://github.com/nicsuzor/academicOps/commit/478783d1d339502abb654af7e62e359dd9d698f4))
- **polecat:** robust task claiming and retry on PKB timeouts ([3dd71d0](https://github.com/nicsuzor/academicOps/commit/3dd71d03c318b0e17c1dfdf7e1fb85fdbcb28776))

### Code Refactoring

- move TAXONOMY.md into /remember skill ([#700](https://github.com/nicsuzor/academicOps/issues/700)) ([910b2cd](https://github.com/nicsuzor/academicOps/commit/910b2cdaafe3d8ab82c0908d714ca09ecb83f46a))

### Documentation

- clean up stale intentions.yaml references ([#665](https://github.com/nicsuzor/academicOps/issues/665)) ([a03f08e](https://github.com/nicsuzor/academicOps/commit/a03f08ec7fb10b49f568d2e2ba739398ea33f590))
- define deadline escalation and status independence for focus scoring ([d443796](https://github.com/nicsuzor/academicOps/commit/d4437960dafd9aa990dd1c7e56f687ed4981e8c9))
- document target/goal alias, consequence, goals[] linking; fix stale daily-skill note ([#726](https://github.com/nicsuzor/academicOps/issues/726)) ([4a5faec](https://github.com/nicsuzor/academicOps/commit/4a5faec0e2869d086081a5c6ed0b876ad30921a5))
- **enforcement-map:** restore PR [#728](https://github.com/nicsuzor/academicOps/issues/728) trim; preserve PR [#729](https://github.com/nicsuzor/academicOps/issues/729) rule-name updates ([#730](https://github.com/nicsuzor/academicOps/issues/730)) ([fa69edb](https://github.com/nicsuzor/academicOps/commit/fa69edb25e238483b8fa43f078133fb88a5cc341))
- **specs:** trim enforcement-map.md and collapse rule tables ([#728](https://github.com/nicsuzor/academicOps/issues/728)) ([126ae05](https://github.com/nicsuzor/academicOps/commit/126ae0580a0f98bca2f0da7a4b4da7efef4941bc))

### Tests

- release-certification suites for Claude Code and Gemini extensions ([#688](https://github.com/nicsuzor/academicOps/issues/688)) ([d8a8be4](https://github.com/nicsuzor/academicOps/commit/d8a8be4702772564ef485b71e1d9c6135543d804))

### Miscellaneous

- delete synthesize_dashboard.py ([#685](https://github.com/nicsuzor/academicOps/issues/685)) ([18bfe44](https://github.com/nicsuzor/academicOps/commit/18bfe4474ccd4e13b78fbdd0e292d4c70e84270e))
- saving uncommitted agent work ([843e9d2](https://github.com/nicsuzor/academicOps/commit/843e9d2c68013ffef14609fb79f81f09f154d0b3))

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
