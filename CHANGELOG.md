# Changelog

## [0.3.41](https://github.com/nicsuzor/academicOps/compare/v0.3.40...v0.3.41) (2026-06-17)


### Features

* **commands:** split /pull into /pull (inline execute) + /dispatch (background); shared task-lifecycle skill; supervisor self-arms loop (aops-127c450c) ([#1855](https://github.com/nicsuzor/academicOps/issues/1855)) ([dba99f3](https://github.com/nicsuzor/academicOps/commit/dba99f32c2973a0b53e4e1704534b7adf81ef7ec))
* **enforcement:** wire rbg+qa to read repo-local RULES.md; populate process rules ([0f00ec0](https://github.com/nicsuzor/academicOps/commit/0f00ec09ba04f7c7449b27ba705caf322f1c63c8))
* **planner:** restore effectual planning philosophy inline into SKILL.md ([e3a48de](https://github.com/nicsuzor/academicOps/commit/e3a48ded69d778c2aec42e52776c045b5b232849))
* PR-B simplification — identity/cleanup (pauli/marsha/sleep/craft/dogfood/feature-spec) ([1f30e8f](https://github.com/nicsuzor/academicOps/commit/1f30e8f7fffe57d8e91ea92220a06a58abc1c9e7))
* **pr-pipeline:** admit PRs via review approval; retire pr-fix-loop Environment gate ([#1859](https://github.com/nicsuzor/academicOps/issues/1859)) ([24fc9e2](https://github.com/nicsuzor/academicOps/commit/24fc9e2124874647f35f10bea585b35b002932cb))
* **remember:** trim /remember SKILL.md 234→148 lines, add maintenance triggers ([8ee5f2f](https://github.com/nicsuzor/academicOps/commit/8ee5f2fced17907f42e1acc78d1aad6ca5c5477d))


### Bug Fixes

* **enforcement-map:** record authorized SKILL.md duplication exception at Verify runtime row ([1eb79af](https://github.com/nicsuzor/academicOps/commit/1eb79af514e3bd37cdd66f9fa554cb2e1b3d8e31))
* **hooks:** agy PreToolUse ALLOW must emit allowTool=true, not {} (aops-1e68682a) ([ebdb546](https://github.com/nicsuzor/academicOps/commit/ebdb546e14dbff156eac4aa78a681effbc54496f))
* **ida:** sharpen Stop reminder with restate-the-question / criterion-substitution check ([#1846](https://github.com/nicsuzor/academicOps/issues/1846)) ([f748f5a](https://github.com/nicsuzor/academicOps/commit/f748f5a61f9a97a13458afe6ed119dd6421a5bc6))
* **install:** handle marketplace name mismatch on reinstall ([64a8821](https://github.com/nicsuzor/academicOps/commit/64a88215a0b045b5d63d07259fd4e5b9617b503e))
* **install:** handle marketplace name mismatch on reinstall ([49acaff](https://github.com/nicsuzor/academicOps/commit/49acaffd1960f242e16ce1bc252eacc7c0e7931a))
* **install:** make `make install` clean-then-live for Claude + agy; drop gemini/openclaw ([#1860](https://github.com/nicsuzor/academicOps/issues/1860)) ([c42b3dc](https://github.com/nicsuzor/academicOps/commit/c42b3dc4dada34773d6399ca1446259a19b3caae))
* **install:** remove silent stderr suppression from marketplace fallback ([ab68cf0](https://github.com/nicsuzor/academicOps/commit/ab68cf00170352eb16f39e2dedf992a837fdffbf))
* **install:** remove silent stderr suppression from marketplace fallback ([64855e5](https://github.com/nicsuzor/academicOps/commit/64855e5f5405d95e7355a753a161985bcab4aa25))
* **junior:** operationalize no-homework rule for closing sweeps ([#1851](https://github.com/nicsuzor/academicOps/issues/1851)) ([#1852](https://github.com/nicsuzor/academicOps/issues/1852)) ([fb11a73](https://github.com/nicsuzor/academicOps/commit/fb11a732f0919a4defcb127de3e432f36f2b2814))
* **polecat:** remove stale sleep-skill bootstrap check ([a7ce057](https://github.com/nicsuzor/academicOps/commit/a7ce05717e33fa23c0fbe3812b4f745fa0c9aa7c))
* **rbg:** correct stale R1–R8 header to R1–R4 (only four rules defined) ([9efcaa1](https://github.com/nicsuzor/academicOps/commit/9efcaa1574ce80978bf30bc637b9c531fd5585c7)), closes [#1836](https://github.com/nicsuzor/academicOps/issues/1836)
* **secret-redaction:** spare numeric values from *TOKEN*/*KEY* over-match ([#1845](https://github.com/nicsuzor/academicOps/issues/1845)) ([14cf77b](https://github.com/nicsuzor/academicOps/commit/14cf77bbce414df4e9aa645e17f18538b37dd637))
* **supervisor:** §6 forbids relaying worker live-state claims as findings ([#943](https://github.com/nicsuzor/academicOps/issues/943)) ([#1854](https://github.com/nicsuzor/academicOps/issues/1854)) ([5792cf4](https://github.com/nicsuzor/academicOps/commit/5792cf4211e2d2869c8feab93051bba9c8086fec))
* **survey:** redirect retro reviewed_by provenance from transcript to PKB ([#1853](https://github.com/nicsuzor/academicOps/issues/1853)) ([060f48f](https://github.com/nicsuzor/academicOps/commit/060f48f4bfcabf7e70adc8842ed9a4c09635f87e))
* **tests:** delete orphaned docker-cmd-build tests left under TestNodeVersionKey ([#1857](https://github.com/nicsuzor/academicOps/issues/1857)) ([ad0a8f0](https://github.com/nicsuzor/academicOps/commit/ad0a8f018cdde8cf9679a36daee9331e8d44024b))
* **tests:** parametrize PreToolUse semantic tests over allow+warn (aops-1e68682a) ([87a6bc9](https://github.com/nicsuzor/academicOps/commit/87a6bc9115031668f62c8d7a51088efbd8e2d8bf))
* **triage:** stop labeling every red PR triage:escalate ([#1858](https://github.com/nicsuzor/academicOps/issues/1858)) ([f204566](https://github.com/nicsuzor/academicOps/commit/f204566f7e808bd8ba0e4cbe0c13d62c282a1e1f))
* **verify:** delete .agents/skills/verify/SKILL.md duplicate; update SSoT exception doc ([68f31ce](https://github.com/nicsuzor/academicOps/commit/68f31ce994a7d354cacbf73c7235699cd45d9c9f))
* **verify:** propagate project-rule check + Process compliance section to canonical SKILL.md ([d1f8f67](https://github.com/nicsuzor/academicOps/commit/d1f8f6705774142172fdb3b9cc4b10fe45ed27fc))


### Code Refactoring

* **agents:** factor shared PKB doctrine, fix tool-lists, namespaces, circular invoke ([#1818](https://github.com/nicsuzor/academicOps/issues/1818)) ([51ec7f3](https://github.com/nicsuzor/academicOps/commit/51ec7f34b4ce994a12285a016f9c94671642c032))
* **gates:** data-drive TOOL_CATEGORIES + lift HookContext/tool_categories to lib/ ([#1847](https://github.com/nicsuzor/academicOps/issues/1847)) ([40187b5](https://github.com/nicsuzor/academicOps/commit/40187b5b5c262daf4a29d7aa07a31a687b4b6080))
* **supervisor:** reduce SKILL.md 487→174 lines; consolidate dispatch rules ([#1834](https://github.com/nicsuzor/academicOps/issues/1834)) ([3a493dd](https://github.com/nicsuzor/academicOps/commit/3a493ddb9278de6a5cc1458d4f015b40d063399f))


### Documentation

* **conventions:** forbid conflating "don't merge/PR" with "don't commit/push" ([#1821](https://github.com/nicsuzor/academicOps/issues/1821)) ([250d36f](https://github.com/nicsuzor/academicOps/commit/250d36f088e391f451652cc9aecd056d73197751))
* **specs:** add framework connectivity index as specs/CONNECTIVITY.md ([15a8978](https://github.com/nicsuzor/academicOps/commit/15a89782c10c5fa7ad392d1ba6fd542f36b06628))


### Miscellaneous

* **axioms:** demote recusal from axiom to light /learn division-of-labor ([#1861](https://github.com/nicsuzor/academicOps/issues/1861)) ([af98dbc](https://github.com/nicsuzor/academicOps/commit/af98dbc63b436bee879d8bb205248ae5579b0684))

## [0.3.40](https://github.com/nicsuzor/academicOps/compare/v0.3.39...v0.3.40) (2026-06-14)

### Features

- **transcript:** add --force to bypass mtime gate for correlation backfill ([8e8bcd0](https://github.com/nicsuzor/academicOps/commit/8e8bcd07963a741e2ef138920448475afb7ff0b7))
- **transcript:** capture pull_requests from git branches in session summaries ([a5b7ec2](https://github.com/nicsuzor/academicOps/commit/a5b7ec26d9d2c3abfe959e42b2dac1b3e1c8c0bf))
- **transcript:** recover task_id/PR correlation from launch context ([cc574be](https://github.com/nicsuzor/academicOps/commit/cc574becadd3817eb6d9e0ac6ea57d211175a63f))

### Bug Fixes

- **agy:** correct injection-delivery root cause — delivery works, transcript does not log injectSteps ([fd9f595](https://github.com/nicsuzor/academicOps/commit/fd9f595c59ac9770b7469d799e602fad19d41e44))
- **agy:** correct PreInvocation injection status — agy-side delivery gap ([#1798](https://github.com/nicsuzor/academicOps/issues/1798)) ([18e85f9](https://github.com/nicsuzor/academicOps/commit/18e85f979f1e4e8a8eccad09f1e9d6359008a5b5))
- **agy:** extract toolCall from payload ROOT, not double-nested ([#1800](https://github.com/nicsuzor/academicOps/issues/1800)) ([c73984c](https://github.com/nicsuzor/academicOps/commit/c73984c8fd58eecbf73e8684674c04e8c924b3e2))
- correct Gemini tool translation block grouping logic ([#1817](https://github.com/nicsuzor/academicOps/issues/1817)) ([78b68b4](https://github.com/nicsuzor/academicOps/commit/78b68b4343a5b4f2960db2a9b0d998543b00c7e6))
- **cron:** single-instance flock guard for repo-sync-cron ([d62b4d1](https://github.com/nicsuzor/academicOps/commit/d62b4d17bfb2dac45083fdf0a5e7de23e38c678c))
- **transcript:** stop skipping polecat/crew branches in PR resolution ([3c82f73](https://github.com/nicsuzor/academicOps/commit/3c82f7325ca607adf083499377f99fed7c890f74))

### Tests

- **1798:** parametrize IDA invariant harness over agy + claude clients ([6ee647e](https://github.com/nicsuzor/academicOps/commit/6ee647e79618553b7368416f70acaea25569151c))
- **agy:** elimination harness for IDA-as-denyReason [#1798](https://github.com/nicsuzor/academicOps/issues/1798) ([188f218](https://github.com/nicsuzor/academicOps/commit/188f21867f2337b4df3bbb39e84bd6d3061410e2))

## [0.3.39](https://github.com/nicsuzor/academicOps/compare/v0.3.38...v0.3.39) (2026-06-12)

### Features

- Add support in polecat to commit to shared branch / existing draft PR ([#1749](https://github.com/nicsuzor/academicOps/issues/1749)) ([db727f8](https://github.com/nicsuzor/academicOps/commit/db727f83c4a3dd99c7a4a5c364a75b03c1dfd8d1))
- **config:** add is_repo flag to project definitions to support non-repository projects ([ed36ce9](https://github.com/nicsuzor/academicOps/commit/ed36ce9c240c3c2e16b983486c27d824197b7618))
- **config:** add is_repo flag to project definitions to support non-repository projects ([3aa3bed](https://github.com/nicsuzor/academicOps/commit/3aa3beda78ce1b64f66cb007cc3e98349ad16cb2))
- **dead-code:** dead-code sweep - delete 5 confirmed-orphaned code units ([74f1ad9](https://github.com/nicsuzor/academicOps/commit/74f1ad93556e0e613cd58e645802ed41e70de691))
- **gates:** close handover on pkb claim + edit tools in all sessions ([dd59e3b](https://github.com/nicsuzor/academicOps/commit/dd59e3b55481f1c40d4ee819165d31b5468c015b))
- **junior:** add point-of-contact closure rules — no homework for the user, diagnosis implies remediation (retro c9308eaf) ([ec896e0](https://github.com/nicsuzor/academicOps/commit/ec896e008ff24560027ddd3c65606a7290194115))
- **junior:** add point-of-contact closure rules (retro c9308eaf) ([1e6a471](https://github.com/nicsuzor/academicOps/commit/1e6a471915c15cbe4692109079c9e3e9b55e8cc5))
- **review:** unify /review-pr into /strategic-review (caller fans out, james reconciles) ([2164f27](https://github.com/nicsuzor/academicOps/commit/2164f2726fc72500c7287311f8276dc64988006a))
- **review:** unify review-pr into /strategic-review; caller fans out, james reconciles ([e7991b0](https://github.com/nicsuzor/academicOps/commit/e7991b02147883ac17230a3ce4c323e33430446d))
- **shared-branch:** add --promote option to run/finish and gate draft PR on is_shared ([876f845](https://github.com/nicsuzor/academicOps/commit/876f845373925b81f3eb5a97865a6f4be4be80c5))
- **skills:** split analyst into tech-agnostic core + aops-extras package ([cea811f](https://github.com/nicsuzor/academicOps/commit/cea811f9db384f4e2370cccf99d0eeb22c72385a))
- **skills:** split analyst into tech-agnostic core + aops-extras package ([1aff82b](https://github.com/nicsuzor/academicOps/commit/1aff82b6606e474876ad93b416838a6ee30fe889))
- **supervisor:** make supervision a required, skill-bound process ([ee63a97](https://github.com/nicsuzor/academicOps/commit/ee63a97b23802be4cad69d88afd32bde926a4e86))
- **supervisor:** port [#1792](https://github.com/nicsuzor/academicOps/issues/1792) proof superset; fix SSoT + gate-inflation ([8dc55b4](https://github.com/nicsuzor/academicOps/commit/8dc55b4217786a0c1412df83a3589cb755973cb2))

### Bug Fixes

- **agents:** replace stale /review-pr reference with /strategic-review in CORE.md ([e21e5c6](https://github.com/nicsuzor/academicOps/commit/e21e5c6e9e1e70b7fb7b671980c397909a20c1d0))
- **agy:** consolidated agy-hook fixes (cold-start + provider threading + summary-writer leak) ([399d9a6](https://github.com/nicsuzor/academicOps/commit/399d9a6f9766505f7ca99b29ae73973268fc20f1))
- **agy:** expose rbg enforcer gate to agy (antigravity) sessions ([549cfa3](https://github.com/nicsuzor/academicOps/commit/549cfa3421bff93be489d710f1bfb2a80635a1fe))
- **agy:** make aops-core hooks fully functional on Antigravity CLI ([d58f2e2](https://github.com/nicsuzor/academicOps/commit/d58f2e257c015cfb5051ffeda040ea22d8c70822))
- **agy:** make PreInvocation context injection fire and render on agy 1.0.7 ([eecc394](https://github.com/nicsuzor/academicOps/commit/eecc394b494ee6cd7fd961373cd6fa8ef5ac29f0))
- **agy:** PreInvocation context injection now fires + renders on agy 1.0.7 ([de09807](https://github.com/nicsuzor/academicOps/commit/de09807ea784326e89b22730c7923f9dc48ea470))
- **agy:** protojson DENY top-level shape + prebake config/plugins venv (aops-891c0e36) ([15e4b66](https://github.com/nicsuzor/academicOps/commit/15e4b668121e7e1ccb7f89f229c72bf9b3de69e5))
- **agy:** protojson DENY uses top-level allowTool/denyReason + prebake config/plugins venv ([fe68873](https://github.com/nicsuzor/academicOps/commit/fe68873e45fc0f76a07e5ca00a8a4781c3d10003))
- **agy:** thread provider into session-summary filename so agy summaries are -antigravity-, not -claude- ([4c3b523](https://github.com/nicsuzor/academicOps/commit/4c3b523e97a0710c53fea6a891f52efd535faf78))
- **agy:** verify HookInjectedStep oneof contract; document agy 1.0.7 PreInvocation no-op ([c0ebff3](https://github.com/nicsuzor/academicOps/commit/c0ebff390ff226df0ff26d14dfa230f184f54173))
- **build:** resolve install split-brain, ruff version skew, inline pyproject (epic-267fe017) ([#1811](https://github.com/nicsuzor/academicOps/issues/1811)) ([22643d7](https://github.com/nicsuzor/academicOps/commit/22643d7a17700d643d49f752307d0740bc5fa0e2))
- **ci:** repair red dev baseline — handover tests + build.py type errors ([893c376](https://github.com/nicsuzor/academicOps/commit/893c376525302ba2d00d6dc6b87cdd82fc4c7658))
- **daily:** commit note in Output step (minimal self-correction) ([5dd10c1](https://github.com/nicsuzor/academicOps/commit/5dd10c1327bbf731e90bb4866737897af3ab53f4))
- **daily:** commit the note on write, don't rely on auto-sync ([362c3e9](https://github.com/nicsuzor/academicOps/commit/362c3e93793ef31fd30a71029196d8555ef41333))
- **daily:** drop --no-verify from commit step (halt-on-failure) ([860a866](https://github.com/nicsuzor/academicOps/commit/860a86639af2f20a5e3b8f6b79b9ada21100e7d9))
- deduplicate intermediate-task verification steps in supervision-loop.md ([7cd21f0](https://github.com/nicsuzor/academicOps/commit/7cd21f011031abbabe60a7faca4532af5d21df7d))
- **hooks:** pre-bake hook venv at install time for all clients ([6a38952](https://github.com/nicsuzor/academicOps/commit/6a38952b8c354d64b15c7deaf007d205e2445cc4))
- **hooks:** stop SessionStart scaffolding a daily-note stub ([#1739](https://github.com/nicsuzor/academicOps/issues/1739)) ([0bd80d9](https://github.com/nicsuzor/academicOps/commit/0bd80d9c87dd16b9ecc6a10b29646fb77366ff10))
- **hooks:** stop SessionStart scaffolding a daily-note stub ([#1739](https://github.com/nicsuzor/academicOps/issues/1739)) ([fc1ee27](https://github.com/nicsuzor/academicOps/commit/fc1ee2793656dfa3016b5e776edf3d8166f4f0dd))
- **lib:** resolve session_* name collisions + dedupe divergent helpers ([f66d0e3](https://github.com/nicsuzor/academicOps/commit/f66d0e3e211e4c73874821d6af3e3aea9db7af36))
- **marsha:** add back-reference to design-rubric self-instance requirement ([0cc03ad](https://github.com/nicsuzor/academicOps/commit/0cc03add9f663f4ab313e46cbf4c02dcae825a2b))
- **peer-review:** canonicalise aops-tools peer-review to aops-core version ([9cc24d8](https://github.com/nicsuzor/academicOps/commit/9cc24d81e720ba519ce44685ba5fd062abc67aa1))
- **peer-review:** delete aops-core copy — aops-tools is now the sole home ([27522e1](https://github.com/nicsuzor/academicOps/commit/27522e14ffdbbb97f3c9901bb048f865bef742df))
- **peer-review:** make aops-tools peer-review the canonical aops-core version ([c1df288](https://github.com/nicsuzor/academicOps/commit/c1df2886813bb7cac1bd6918638ca3a4aeb135a7))
- **pkb-nudge:** counter MEMORY.md named-pointer shortcut ([#1807](https://github.com/nicsuzor/academicOps/issues/1807)) ([145d53b](https://github.com/nicsuzor/academicOps/commit/145d53b75368053424d618e47a2967c2d5d1c979))
- **pr-pipeline:** admit/check-admit gate on convergence, not green verdict ([c118335](https://github.com/nicsuzor/academicOps/commit/c11833515813df261f98507ee95e1ce6155c9a4a))
- **pr-pipeline:** stop alignment-queue filing alignment:queued issues (no drainer) ([5a72987](https://github.com/nicsuzor/academicOps/commit/5a72987b02df0b4b344423638a4ea071932671d1))
- **rbg:** add universal-claim inference step to R2 ([320690a](https://github.com/nicsuzor/academicOps/commit/320690a9e3cf12fd32ef12a150541e78a6c5340f))
- resolve basedpyright GateVerdict type errors in gate definitions ([698335e](https://github.com/nicsuzor/academicOps/commit/698335e494b965ca6b7c932fcb3e8c5d7b3cd127))
- **router:** unpack nested raw_input fields for antigravity client hooks ([8326a24](https://github.com/nicsuzor/academicOps/commit/8326a240d907fa19004c13160d54252b555bc7b8))
- **transcript_parser:** correct ParsedSession docstring — old name was SessionSummary, not ParsedSession ([51667a4](https://github.com/nicsuzor/academicOps/commit/51667a45e035556dc1cf933e8fd786cf40d3cad4))

### Code Refactoring

- **junior:** remove duplicate instructions and incident-specific rules ([02e351e](https://github.com/nicsuzor/academicOps/commit/02e351ec48e97db8d03d7bd8027013bc2527bd40))
- **planner:** dedup intent-authority rule, point to local canonical section ([2dd269b](https://github.com/nicsuzor/academicOps/commit/2dd269bcab970174dd0e8237501b41eba7ebc5c7))
- **sleep:** drop detector-bug workaround prose now fixed upstream (mem[#425](https://github.com/nicsuzor/academicOps/issues/425)) ([019ead6](https://github.com/nicsuzor/academicOps/commit/019ead6e6fa0d38faf1cbd8dd89ebdead1f85f1a))
- **supervisor:** fold /program in, cut deterministic brakes + merge-gate mechanics, trust the agent ([b045fcc](https://github.com/nicsuzor/academicOps/commit/b045fcc7b6b71f3270a77f3b965aec8618194d58))
- **supervisor:** inline holding-work-to-proof into the skill; add craft defect class ([b666939](https://github.com/nicsuzor/academicOps/commit/b66693940cfe66a6dcb71d292970552ef528cb84))

### Documentation

- **agents,skills:** propagate self-instance rule to design-rubric + marsha (+ verify cross-ref) ([aedc16a](https://github.com/nicsuzor/academicOps/commit/aedc16a7071f1a15ca6eb9b96dd455e6a2c7ce79))
- encode cohesive single-PR-epic pattern into planner/supervisor skills ([8e1af24](https://github.com/nicsuzor/academicOps/commit/8e1af24ab7eea93d6392828b317b7dd699935c74))
- resolve draft lifecycle contract, dispatch command formats, and single source of truth duplication ([245742c](https://github.com/nicsuzor/academicOps/commit/245742c3a6b5b84f2886e07978155d1d98285d31))

### Build System

- **cowork:** ship no hooks — rely on shared aops-core hook stack (aops-04075740) ([469cca8](https://github.com/nicsuzor/academicOps/commit/469cca855a7011ece6c4d4d07f266eb5a305ab98))

### Tests

- **agy:** fix two test-isolation bugs surfaced during agy-hook consolidation ([8a1af4d](https://github.com/nicsuzor/academicOps/commit/8a1af4d4c14c00089cfc698a463158b79c5d47b8))
- replace brittle mirror source tests with behavioral tests for finalize promote flag ([eaea5c9](https://github.com/nicsuzor/academicOps/commit/eaea5c9523fba78592e33d2223bc82353046e71a))

### Miscellaneous

- **integrity:** drop dead check_context_map_coverage() ([f0c0029](https://github.com/nicsuzor/academicOps/commit/f0c0029553d5d60e2090d09bd06fce42926fe407))
- **integrity:** drop dead check_context_map_coverage() ([2689127](https://github.com/nicsuzor/academicOps/commit/26891271ec9a673f01bcff87e249405de0f8208c))
- replace retired polecat/SSH dispatch commands with canonical uv run ([#1747](https://github.com/nicsuzor/academicOps/issues/1747)) ([1683d41](https://github.com/nicsuzor/academicOps/commit/1683d41004cdefe1f71dbcbeb38c2e57d056526f))
- saving uncommitted agent work ([5927778](https://github.com/nicsuzor/academicOps/commit/5927778dc4b6937b0e24fc2480b268fd8ff6a8f6))
- scope PR to agent-def reflex only ([961b6eb](https://github.com/nicsuzor/academicOps/commit/961b6eb15d7371517499c1d7309dc7afe445e413))

## [0.3.38](https://github.com/nicsuzor/academicOps/compare/v0.3.37...v0.3.38) (2026-06-10)

### Features

- **ci:** add workflow_dispatch inputs to claude.yml ([#1633](https://github.com/nicsuzor/academicOps/issues/1633)) ([464bb99](https://github.com/nicsuzor/academicOps/commit/464bb9920add31092563cf4f75ab561675dc2ad9))
- **hooks:** implement output_for_agy() — internal verdict → exa.hooks_pb.*Result protojson ([#1712](https://github.com/nicsuzor/academicOps/issues/1712)) ([a91ef0e](https://github.com/nicsuzor/academicOps/commit/a91ef0eb066899b383791bf568c45c2ec86c3d7b))
- implement ordered short-circuit for PR pipeline v2 ([#1632](https://github.com/nicsuzor/academicOps/issues/1632)) ([e0655f1](https://github.com/nicsuzor/academicOps/commit/e0655f1a483e12a60bfab9950171e207406204ae))
- **peer-review:** v3.0.0 — 5-stage adaptive loop, 11 verbatim probes, de-Nic-ify ([89f7506](https://github.com/nicsuzor/academicOps/commit/89f75061233ba6a6f79a6ab6cb19c924cd029b32))
- **planner:** add earn-its-keep / is-the-need-real gate before decomposition ([#1652](https://github.com/nicsuzor/academicOps/issues/1652)) ([4bad0ee](https://github.com/nicsuzor/academicOps/commit/4bad0ee5d7f659de154d6c84445d40c24c77aa18))
- **polecat:** persist agy cli.log to host session dir (aops-59e55ed3) ([5b87097](https://github.com/nicsuzor/academicOps/commit/5b87097b4f2e9f8d7231a6fdf33e21ca54e8329e))
- pr-pipeline-v2 P4 — Environment gate + admit-status + graduation (ruleset) ([e14e5a5](https://github.com/nicsuzor/academicOps/commit/e14e5a5329d50919de7effddfa798e35bd7981db))
- **remember:** add routing hint — axioms go to /framework, not brain/context ([#1636](https://github.com/nicsuzor/academicOps/issues/1636)) ([8135776](https://github.com/nicsuzor/academicOps/commit/813577687b4303fc8e028bffc31122070ac2355e))
- **security:** Layer 2 — pre-commit secret scanner for sessions repo (aops-00c0fa10) ([#1638](https://github.com/nicsuzor/academicOps/issues/1638)) ([a6999d1](https://github.com/nicsuzor/academicOps/commit/a6999d122d41b294061b193a17a836f52606573e))
- **session-classification:** lift single-turn-SDK + worker-host signals into canonical is_automated_session ([#1727](https://github.com/nicsuzor/academicOps/issues/1727)) ([1d46869](https://github.com/nicsuzor/academicOps/commit/1d46869b50c50fb30677be88a7be7226ba5fc7ed))
- **user_prompts:** filter automated sessions from catch-up timeline ([6aaa42f](https://github.com/nicsuzor/academicOps/commit/6aaa42f2b5f051a6ba05ce78453b2bd660130adf))

### Bug Fixes

- /learn transcript selection and self-review policy ([#1637](https://github.com/nicsuzor/academicOps/issues/1637)) ([5289d16](https://github.com/nicsuzor/academicOps/commit/5289d161ef0499fad024ca9e5175c99655effcf2))
- address PR review comments for peer-review skill v3 ([39bfcb0](https://github.com/nicsuzor/academicOps/commit/39bfcb0a38bd53b0e9d4ca7f1847fa019cb61255))
- address PR review comments for peer-review skill v3 ([2426d2b](https://github.com/nicsuzor/academicOps/commit/2426d2ba731c85290f2f4685906bacbe7ae36f93))
- **agents:** append explicit task directive to enforcer + qa prompts ([#1674](https://github.com/nicsuzor/academicOps/issues/1674)) ([c33e13e](https://github.com/nicsuzor/academicOps/commit/c33e13eccc8a8be5187e9793652cf7a0898c1153))
- **ci:** enforcer reliability — gate-integrity, retry, diagnostic ([43f47ad](https://github.com/nicsuzor/academicOps/commit/43f47adef39acc7cc3bf4f931e3e848df047eb29))
- **ci:** enforcer reliability — gate-integrity, retry, diagnostic (aops-221211fa) ([cf0f31a](https://github.com/nicsuzor/academicOps/commit/cf0f31ac62e78d8128d632c786b8877a0e5af80a))
- **ci:** enforcer retry survives cancellation (rate_limit_event) ([3529bab](https://github.com/nicsuzor/academicOps/commit/3529bab7c42d27894429918e8892b8c4ec6d9fbd))
- **ci:** enforcer retry survives cancellation (rate_limit_event) ([a29f1c5](https://github.com/nicsuzor/academicOps/commit/a29f1c519f7c8e53542fbe8fc25982044529dda0))
- **ci:** reap zombie enforcer agent + idempotent single verdict per SHA ([4800a37](https://github.com/nicsuzor/academicOps/commit/4800a376dfa9855f3fb4002af24beaa534c5cb4f))
- **ci:** retire pull_request trigger from enforcer/qa shims (aops-db83bad5) ([459ba52](https://github.com/nicsuzor/academicOps/commit/459ba528cf7399b13331938161527602a9255f88))
- deduplicate _ssh_github_to_https import; re-apply accurate spec corrections ([6245e46](https://github.com/nicsuzor/academicOps/commit/6245e46c7132aad9a303e3162a4c7b1bdf2c52b3))
- **enforcer:** always clone prompt files from main for self-runs ([#1650](https://github.com/nicsuzor/academicOps/issues/1650)) ([f6cb654](https://github.com/nicsuzor/academicOps/commit/f6cb6542d4a768787bd6c203c823727692938be2))
- **enforcer:** redact secrets in gate/narrative files before write ([#1635](https://github.com/nicsuzor/academicOps/issues/1635)) ([fabb646](https://github.com/nicsuzor/academicOps/commit/fabb64673a5540d4ada0633168502895c6c11530))
- **enforcer:** surface gh api errors verbatim + demote rationale from push tier ([9f63e23](https://github.com/nicsuzor/academicOps/commit/9f63e2386aada5291794cb41f94b51b607649fa4))
- **gha:** switch Stage-2 admission to in-pipeline Environment-gated job ([034b666](https://github.com/nicsuzor/academicOps/commit/034b66665e710a0cee3eaab99d4ddda6ba88a8ce))
- **gha:** switch Stage-2 admission to in-pipeline Environment-gated job ([ce897e0](https://github.com/nicsuzor/academicOps/commit/ce897e02a084c442910343e3424818e96635b6b0))
- **hooks:** check_no_fallbacks statement-aware allow-fallback checks and shell continuation support ([#1634](https://github.com/nicsuzor/academicOps/issues/1634)) ([ae8f8ec](https://github.com/nicsuzor/academicOps/commit/ae8f8ecb2ca755437cd39d1eaf1e203da669a95d))
- **polecat:** restore full class coverage for SSH URL normalization ([b8cf93e](https://github.com/nicsuzor/academicOps/commit/b8cf93eff80b187fe91f33db761d16f0ffc3729a))
- **release:** drop orphaned nicsuzor/aops mirror step; reconcile spec ([cf5320d](https://github.com/nicsuzor/academicOps/commit/cf5320deb0eabfb7dd8c5de08857f92d6dc08f5b))
- remove orphan code fences from reading-notes-format.md ([264bcc1](https://github.com/nicsuzor/academicOps/commit/264bcc1d472a3fecadae2b979b223852445091ce))
- require clean Docker build for verification (issue [#1452](https://github.com/nicsuzor/academicOps/issues/1452)) ([#1645](https://github.com/nicsuzor/academicOps/issues/1645)) ([28b85c7](https://github.com/nicsuzor/academicOps/commit/28b85c752bb598a4d5b02ad7b2dcbf12658853e4))
- resolve SSOT violations between enforcement.md and ENFORCEMENT-MAP.md ([d1661b8](https://github.com/nicsuzor/academicOps/commit/d1661b822202119cf52dbc5f6cfc804e272aa809))
- restore comprehensive SSH→HTTPS converter + resolve merge conflicts ([3126177](https://github.com/nicsuzor/academicOps/commit/312617700e3265dcc0adc70964b69a5b469a7a66))
- restore is_automated_session classifier + catch-up filtering clobbered by 2426d2ba ([a621298](https://github.com/nicsuzor/academicOps/commit/a6212987e4e1444ea67adee2aa52c9266adcda12))
- **ruleset:** drop stale admin always-bypass from SSoT YAML (aops-d62201ca) ([b096d2d](https://github.com/nicsuzor/academicOps/commit/b096d2d1697610f7c20d97d467fa049e3247b2ca))
- **spec:** correct two stale claims in ENFORCEMENT-MAP.md ([7201cc1](https://github.com/nicsuzor/academicOps/commit/7201cc15174166249ae144068074fa08989309d3))
- strip AC label parentheticals from runtime prompt ([bef05d4](https://github.com/nicsuzor/academicOps/commit/bef05d47b8f16c0054d31436fd029f31b37382ff))
- **transcript_parser:** surface PKB lookup failures in resolve_task_title ([4ad833e](https://github.com/nicsuzor/academicOps/commit/4ad833eab05f08e2a91e5a55eee54c506a7fe217))
- **transcript:** cowork surface, subagent JSON surface/client, by_skill, secret redaction ([1515384](https://github.com/nicsuzor/academicOps/commit/15153842e852e879aab280f4e632ce4865f118b3))
- **transcript:** extract thinking + tool_calls from antigravity PLANNER_RESPONSE ([a559815](https://github.com/nicsuzor/academicOps/commit/a559815ab4062f028395d27cab6bd228cd8402b6))
- **transcript:** extract thinking + tool_calls from antigravity PLANNER_RESPONSE ([5187145](https://github.com/nicsuzor/academicOps/commit/5187145dc9f6bb220bf5350db91a8af7e6b35d36))
- **transcript:** restore old-format PLANNER_RESPONSE compat + apply Gemini robustness fixes ([2469ad1](https://github.com/nicsuzor/academicOps/commit/2469ad14a19fb43bbcd0ccf1a04770e372c59dea))
- **transcript:** restore unknown-step surfacing in antigravity parser ([25b7eb3](https://github.com/nicsuzor/academicOps/commit/25b7eb3299ce24ad75e34362351fb027da953ce3))
- **types:** annotate `_extract` accumulator to match `_run_docker_container` ([#1715](https://github.com/nicsuzor/academicOps/issues/1715)) ([6af5fb2](https://github.com/nicsuzor/academicOps/commit/6af5fb2c16e754fab531550ffe1440b56e9d9d10))

### Documentation

- **aops:** self-test doctrine — liveness check before polling + caller-class check before extending ([#1029](https://github.com/nicsuzor/academicOps/issues/1029), [#1213](https://github.com/nicsuzor/academicOps/issues/1213)) ([#1647](https://github.com/nicsuzor/academicOps/issues/1647)) ([4bf73c3](https://github.com/nicsuzor/academicOps/commit/4bf73c32c3522292e09e347d74ae561fcdb479a1))
- **conventions:** forbid merge-gate/do-not-merge banners in PR bodies ([7b67868](https://github.com/nicsuzor/academicOps/commit/7b6786827903bdc9f2bc6dc4819783f676ed6f1d))
- **daily:** trim draft-status/sibling-specs header from architecture spec ([aa3390e](https://github.com/nicsuzor/academicOps/commit/aa3390e526a2de6e6d864d86108df2d172f963f6))
- **release:** note dev/testing builds now publish to dist (client opts in) ([77e1156](https://github.com/nicsuzor/academicOps/commit/77e11560011c9c2643e92dbbdcfd9635af26f242))
- **spec:** complete release/merge/publish/version-sync pipeline contract ([1eb7ac2](https://github.com/nicsuzor/academicOps/commit/1eb7ac21068c84755f5c3e390dbb63b74e9c8231))
- **spec:** consolidate PR-pipeline specs into one target-state SSoT ([8519814](https://github.com/nicsuzor/academicOps/commit/85198143890a6e545ca03ca333e1537a4cd49b9d))
- **spec:** consolidate PR-pipeline specs into one target-state SSoT (kill v1, fold merge-prep→mechanic, Stage-2 re-verify + loop bound) ([2078a83](https://github.com/nicsuzor/academicOps/commit/2078a8356d7561e390b2286626975b8d8edaf363))
- **spec:** reconcile enforcement.md with consolidated pr-pipeline SSoT ([7dc5968](https://github.com/nicsuzor/academicOps/commit/7dc596830d9111db2037f2eaa11845f49c39fce4))

### CI/CD

- **agents:** allow claude[bot]/github-actions[bot] on enforcer + qa self-runs ([f6dac24](https://github.com/nicsuzor/academicOps/commit/f6dac2481802de4cbda2dfc2894705b27af5a4bf))
- **agents:** allow claude[bot]/github-actions[bot] on enforcer + qa self-runs ([7d369f3](https://github.com/nicsuzor/academicOps/commit/7d369f30c8dd270dcaca33266abd37492bd75042))
- re-trigger enforcer/qa under human actor (flip from claude[bot] push) ([b66172e](https://github.com/nicsuzor/academicOps/commit/b66172e2009013dc9da9203e84fccfce63a43f57))
- re-trigger review after honest-epistemics fix in PR description ([eda0752](https://github.com/nicsuzor/academicOps/commit/eda0752ee7a325af5c2839327322dc60f954dab2))
- revert all workflow-file comment edits to dev (unblock App token exchange) ([9f9b7d5](https://github.com/nicsuzor/academicOps/commit/9f9b7d539dbf144fc105acd5680e8bc0a5c71fa6))
- revert comment-only edits to trigger-{enforcer,qa}.yml (unblock App token exchange) ([9435b7a](https://github.com/nicsuzor/academicOps/commit/9435b7a39ff3fb20bcf247af9c5822c0294f49e2))

### Tests

- **build:** align cowork-marketplace tests with build_coworklocal_plugin contract ([9f902ff](https://github.com/nicsuzor/academicOps/commit/9f902fffc09a800901010a22b9e603c1c6761b4a))
- **hooks:** consumer-side agy protojson accept-contract — close the test gap that let 4c73f02a silently disable agy gates ([a4d24d5](https://github.com/nicsuzor/academicOps/commit/a4d24d55885f06db49cd88b48a2b97845a344be4))
- **hooks:** consumer-side agy protojson accept-contract (close the 4c73f02a test gap) ([eade10a](https://github.com/nicsuzor/academicOps/commit/eade10af412e4881d4e6483da07c979638b197b6))

### Miscellaneous

- align release-please manifest to 0.3.37 ([90555db](https://github.com/nicsuzor/academicOps/commit/90555db6167334b1a47e4f4fc18e7647a5d887f6))
- **main:** release 0.3.35 ([672c42e](https://github.com/nicsuzor/academicOps/commit/672c42e28f502557bfc56219c263795c8dfceefb))

## [0.3.34](https://github.com/nicsuzor/academicOps/compare/v0.3.33...v0.3.34) (2026-06-04)

### Bug Fixes

- **docker:** revert Dockerfile to pull from nicsuzor/aops dist repo and use correct agy installation paths ([4a45cc6](https://github.com/nicsuzor/academicOps/commit/4a45cc6d35a12bdb521cd6b378586771073f7b3f))

### Miscellaneous

- **ci:** remove legacy aops dist repo deployment workflow ([65d77ad](https://github.com/nicsuzor/academicOps/commit/65d77adf44fff17990e77ea121ec88e38bee3096))
- **ci:** update marketplace.json for dist layout on main ([feeac8a](https://github.com/nicsuzor/academicOps/commit/feeac8af9fd4ea64b2f04b69f9641b5bb250cb38))
- **git:** add pre-commit hook to prevent manual commits to dist/ ([60ecf5b](https://github.com/nicsuzor/academicOps/commit/60ecf5b5b129cad41687fcc7557c6bde8d6f11cf))
- remove generated dist/ from git to avoid merge conflicts ([bf85b67](https://github.com/nicsuzor/academicOps/commit/bf85b671b86dc6b2c5b7b24f08abf8585fbd7966))

## [0.3.33](https://github.com/nicsuzor/academicOps/compare/v0.3.32...v0.3.33) (2026-06-04)

### Features

- add antigravity (agy) client to polecat ([#1543](https://github.com/nicsuzor/academicOps/issues/1543)) ([a096c8e](https://github.com/nicsuzor/academicOps/commit/a096c8e7d9136e64026c2ba34a884a500ff5aab3))
- add in-flight intervention detectors to existing surfaces ([c62682b](https://github.com/nicsuzor/academicOps/commit/c62682bfa8f221cb6b6fa65c1fa4fc36f83d0994))
- capture and aggregate new session metadata ([#1458](https://github.com/nicsuzor/academicOps/issues/1458)) ([745cf33](https://github.com/nicsuzor/academicOps/commit/745cf33de3c46bbb7845394b7762ef1c578cc3f5))
- **core:** redefine merge_ready as under review, remove CLI PR lock ([57754f6](https://github.com/nicsuzor/academicOps/commit/57754f64fb28eddab6361efffb48c45ddec96d44))
- **daily:** per-class priority-bar denominators with honest fallback ([2e450f0](https://github.com/nicsuzor/academicOps/commit/2e450f0efe1dd2041b90bfd52f4413aacd51bb4d))
- **dogfood,planner:** codify decomposition-quality eval + intent-before-mechanism ([3bb47ab](https://github.com/nicsuzor/academicOps/commit/3bb47ab2a082263d7cdf2b440b3e159b7221265a))
- **enforcement:** auto-mode classifier spec + L5 pyramid split + transcript observability ([504f93a](https://github.com/nicsuzor/academicOps/commit/504f93a6187757b1d6d51bca5f20d81df1be7d51))
- **enforcement:** auto-mode classifier spec + L5 pyramid split + transcript observability ([b63939e](https://github.com/nicsuzor/academicOps/commit/b63939e6113cbdc83b8fe8d84be269d69893af87))
- **hooks:** inject static PKB-search nudge on UserPromptSubmit (T0) ([83cb247](https://github.com/nicsuzor/academicOps/commit/83cb247a73da049c6606099420c82947fbb00f2d))
- **ida:** tier the honesty check — floor always, manifest at review-grade ([3a74b72](https://github.com/nicsuzor/academicOps/commit/3a74b72ad0491b03064d1017b9824b7ab952b599))
- **observability:** extract full categorical metadata in transcript.py ([b086260](https://github.com/nicsuzor/academicOps/commit/b086260894bcb88e66b9e643a43c1eed4e3f1257))
- **planner:** interrogate task epistemics before structuring a decomposition ([6845569](https://github.com/nicsuzor/academicOps/commit/6845569a7cc1f33d763e32be24a17f64d9e0e261))
- **planner:** interrogate task epistemics before structuring a decomposition ([e3cdc45](https://github.com/nicsuzor/academicOps/commit/e3cdc45bd3e484815ddb67eaaafc260e5e2371fc))
- **polecat:** partial-work core — `partial` state, draft-PR path, clause-2b self-cert, PKB-first preamble ([c743d1d](https://github.com/nicsuzor/academicOps/commit/c743d1d8acd340e4091ac419c3ed223923577aa7))
- **polecat:** partial-work core — partial state, draft-PR, clause-2b self-cert, PKB-first preamble ([a8d0373](https://github.com/nicsuzor/academicOps/commit/a8d0373550d59d50f696dd10e6467c858619caac))
- **polecat:** stream claude -p to docker logs; name local container; drop budget diagnostic ([366f7ea](https://github.com/nicsuzor/academicOps/commit/366f7ea6e56f672648da7dcd1cde64f326ea078b))
- **polecat:** stream claude -p to docker logs; name local container; drop budget diagnostic ([4952ca5](https://github.com/nicsuzor/academicOps/commit/4952ca55142c4fc49da6df008b804f034e7937b3))
- **review-pr:** launch James panel as a peer team, not a leaf subagent ([#1481](https://github.com/nicsuzor/academicOps/issues/1481)) ([ac65b10](https://github.com/nicsuzor/academicOps/commit/ac65b10b9886aeaaf0df187e4488131192c4f7fb))
- **scripts:** add user_prompts timeline script ([#1457](https://github.com/nicsuzor/academicOps/issues/1457)) ([a52cadc](https://github.com/nicsuzor/academicOps/commit/a52cadcb4fa1fcd6e0b886908ebe7bb3ea60b117))
- **strategic-review:** arch-fit lens v2.5.0 — hunt unregistered mechanisms + propagation completeness ([b086718](https://github.com/nicsuzor/academicOps/commit/b08671879815ba2cbaca89fdad3c5d803b37378a))
- **strategic-review:** arch-fit lens v2.5.0 — unregistered-mechanism + propagation-completeness hunts ([6e001c9](https://github.com/nicsuzor/academicOps/commit/6e001c9693d103e4c00f4836aa5295fd8c2e1ca1))
- **strategic-review:** harden arch-fit lens — 🔴 REJECT verdict + earn-its-keep/No-Shitty-NLP corollary ([70ccd2e](https://github.com/nicsuzor/academicOps/commit/70ccd2e0c16a1faf008c0cb3b4e24c44a9456bb3))
- **strategic-review:** harden arch-fit lens — add 🔴 REJECT + earn-its-keep/No-Shitty-NLP corollary ([b8e9bdc](https://github.com/nicsuzor/academicOps/commit/b8e9bdc7350bf08b17941e6f05c3116c7dfdf6c5))
- **survey:** sweep mode proceeds autonomously + queue-reduction dispositions ([1319c79](https://github.com/nicsuzor/academicOps/commit/1319c79ce9eff56f7b56f877ac22a204045351ab))
- **survey:** sweep mode proceeds autonomously + queue-reduction dispositions ([4b8bff0](https://github.com/nicsuzor/academicOps/commit/4b8bff0fa0bf628f84c3b49141fb397939bd0ec5))

### Bug Fixes

- address Gemini review — terminology consistency ([854815d](https://github.com/nicsuzor/academicOps/commit/854815d1f0c30737429cd8f1cdd87082f961aae4))
- address Gemini review feedback and CI test failure ([02b2533](https://github.com/nicsuzor/academicOps/commit/02b2533b33ccbf72dbbf81cacad9076dfea0346d))
- address Gemini review feedback on auto-mode classifier extraction ([5acf1fd](https://github.com/nicsuzor/academicOps/commit/5acf1fd9a3236c71fbec59040d88c16e29d0da4c))
- address review feedback ([dd825de](https://github.com/nicsuzor/academicOps/commit/dd825deeeb0f5a17c046077a77697eb24bdfca37))
- address review feedback — annotate optional fallbacks + defensive type checks ([f4a6d09](https://github.com/nicsuzor/academicOps/commit/f4a6d095f9d114af33bfc9eacfe9c85a891b52d7))
- address review feedback — classification consistency ([fccd19e](https://github.com/nicsuzor/academicOps/commit/fccd19e77c6d117ff5eb9da98736c57fd919f5e5))
- address review feedback — remove dead-code --name bypass block ([4724a32](https://github.com/nicsuzor/academicOps/commit/4724a32d6ac999d0f8fb92f163d3f6b0520f7d11))
- address review feedback — stale docstring, tool_input None guard, word-boundary deny matching ([d2feb49](https://github.com/nicsuzor/academicOps/commit/d2feb496c766baa5a606a7b0615170995cab0d5e))
- address review feedback — tighten slash-command patterns, annotate fallbacks ([52f9b94](https://github.com/nicsuzor/academicOps/commit/52f9b94f501f7f2999520e857273488938157155))
- annotate allow-fallback in check_no_fallbacks.py baseline reader ([168456b](https://github.com/nicsuzor/academicOps/commit/168456b709292088302894fdaae51ed9a746a4ce))
- apply Gemini review accuracy suggestions to instruction-budget.md ([4d77165](https://github.com/nicsuzor/academicOps/commit/4d7716596f46d960ff7024971d80d579876072dd))
- apply Gemini review improvements to check_no_fallbacks ([d6d7b2f](https://github.com/nicsuzor/academicOps/commit/d6d7b2fd5ab8f9c1ae7562cf2ef56070cbb43b7d))
- **automode:** unify autoMode SSoT + stabilise install fingerprint ([86508e6](https://github.com/nicsuzor/academicOps/commit/86508e653ceb307aa006754610f27c3f21432cd1))
- **automode:** unify autoMode SSoT + stabilise install fingerprint ([6f131a1](https://github.com/nicsuzor/academicOps/commit/6f131a1d7bf258575db548aa0a1d36917a200fc5))
- **build:** co-ship axioms into plugin payload + remove old_axioms.md decoy ([#1602](https://github.com/nicsuzor/academicOps/issues/1602)) ([f0210f5](https://github.com/nicsuzor/academicOps/commit/f0210f51ebfd6d0871ed9fdd4ae22b614efe0dde))
- **build:** exclude .uv-cache from packaging to stop bloat and lstat race ([280b051](https://github.com/nicsuzor/academicOps/commit/280b051c78c7def20a4e8b47d9db492dca2beb0e))
- **build:** exclude cache detritus from cowork zip (invalid-char upload error) ([02989c8](https://github.com/nicsuzor/academicOps/commit/02989c865a7e9761f7df8801fd806c72f1b58e0a))
- **build:** exclude sync-conflict and backup detritus from plugin builds ([ae6956d](https://github.com/nicsuzor/academicOps/commit/ae6956d0e2e6f636fb265372122277d42b8b614c))
- **check_no_fallbacks:** annotate self-referential fallbacks to pass lint ([fb83210](https://github.com/nicsuzor/academicOps/commit/fb832104527670a84d1a598f08d8d20164080759))
- clarify goal linkage to include work tasks (not targets only) ([c93e835](https://github.com/nicsuzor/academicOps/commit/c93e83512b5fc9aab1b7cb2d4f00644a8339df88))
- **cli:** restore review as enforced gate, keep merge_ready iterative ([26475c5](https://github.com/nicsuzor/academicOps/commit/26475c5c94709123629a6736b2b9ff26a6b89aa3))
- correct launchd fallback logic and reset providers cache per test ([23367c2](https://github.com/nicsuzor/academicOps/commit/23367c2171b2b8eee44bd91f8c80fbf8dd36836d))
- **daily:** correct broken relative links to TAXONOMY.md ([e57a6d3](https://github.com/nicsuzor/academicOps/commit/e57a6d36a5a3bd555f3b544065ab6224229e86e9))
- **dump_pr_state:** stop creating [Action Required] issues for escalated PRs ([#1490](https://github.com/nicsuzor/academicOps/issues/1490)) ([6e08011](https://github.com/nicsuzor/academicOps/commit/6e08011191b447feb4900daa6179468c66149581))
- **enforcement-map:** correct inaccurate 'always-on SessionStart load' axiom rows ([8331ea6](https://github.com/nicsuzor/academicOps/commit/8331ea672fd3bea550afc781430a5f71e94bbb96))
- **enforcer:** correct AC [#1](https://github.com/nicsuzor/academicOps/issues/1) to match the actual deployment decision ([e1094cb](https://github.com/nicsuzor/academicOps/commit/e1094cb0c9c5551cc97f73bbe7af2e3d23f22518))
- **enforcer:** correct wired-but-unseeded status to reflect zero-seed decision ([14a1f1e](https://github.com/nicsuzor/academicOps/commit/14a1f1e7ea07f10e4000e5ee7c42b177ddb5912e))
- **enforcer:** grant caller permissions so reusable enforcer workflow stops startup_failing ([bbe2ac6](https://github.com/nicsuzor/academicOps/commit/bbe2ac6828d014de4b88a3cb89a4aa39529b74a8))
- **enforcer:** grant caller permissions so reusable enforcer workflow stops startup_failing (aops-31798611) ([9fd8d8f](https://github.com/nicsuzor/academicOps/commit/9fd8d8f9f934e756465513118103f924d167f331))
- **enforcer:** only skip SHA on a genuine review, not on failed/skipped runs ([a98f1ec](https://github.com/nicsuzor/academicOps/commit/a98f1ec11f52c99be026727e651fb379560d24d9))
- **enforcer:** use --no-cone sparse-checkout so prompt files materialise ([ba37511](https://github.com/nicsuzor/academicOps/commit/ba375116291dd187ef2870d40db7f74a05fc8e49))
- extract _populate_session_linkage helper, apply getattr loop ([1687a55](https://github.com/nicsuzor/academicOps/commit/1687a55b05037d1c85981cab95a91c63a034c3aa))
- **gates:** don't re-arm session-end gates on slash-command turns ([833f227](https://github.com/nicsuzor/academicOps/commit/833f2277ce77d09281d27930d567fac18f56db1c))
- **gates:** don't re-arm session-end gates on slash-command turns ([b7b142a](https://github.com/nicsuzor/academicOps/commit/b7b142a9b52d3a289a1c1804c02eaac267fd0c02))
- **gates:** honesty + axioms are universal; only qa scales with register ([8ae7244](https://github.com/nicsuzor/academicOps/commit/8ae72442d6d2b0c5fb4efa591894e82d66efa38f))
- **gates:** honesty + axioms are universal; only qa scales with register ([1678d18](https://github.com/nicsuzor/academicOps/commit/1678d18807f2d46e8f6007eb33f020cc21a89b67))
- **gates:** instructions-first — revert gate enforcement, keep tiered ida ([07ad365](https://github.com/nicsuzor/academicOps/commit/07ad3651771b5f026017d115c003fe401e41cea8))
- **gates:** pin gate-file slug to "session" — decouple from transcript naming ([fa49979](https://github.com/nicsuzor/academicOps/commit/fa499795f0d1921738b8974a329b22a9e75cfafb))
- **gates:** pin gate-file slug to "session" — decouple from transcript naming ([6c98d18](https://github.com/nicsuzor/academicOps/commit/6c98d181378bbb3d080efaf079bc53c152bff2a4))
- **gemini:** translate Claude built-in tool names to agy native vocabulary ([#1494](https://github.com/nicsuzor/academicOps/issues/1494)) ([c307433](https://github.com/nicsuzor/academicOps/commit/c307433ad271b45e4996a53219ad255948fef902))
- handle dict in server_tool_use ([813c3f4](https://github.com/nicsuzor/academicOps/commit/813c3f440d96e6eef41d253c1b49ec2abb30172d))
- handle dict in server_tool_use for Claude Code 2.1+ compatibility ([a298101](https://github.com/nicsuzor/academicOps/commit/a29810151378cf59c9f33a39ceac571b5a5e4f36))
- **hooks:** stop agy session state leaking to ~/.claude/projects ([37c5416](https://github.com/nicsuzor/academicOps/commit/37c54163582d10df216069423ef306cc0bf0de9a))
- **hooks:** Stop-gate advisories no longer leak agent-facing scaffolding/syntax to the user ([#1459](https://github.com/nicsuzor/academicOps/issues/1459)) ([8bb7713](https://github.com/nicsuzor/academicOps/commit/8bb7713c9902a8f9a179a77aca67a12a177267a6))
- **junior:** delegation governs production not perception; ban source as rendered-state evidence ([3b257aa](https://github.com/nicsuzor/academicOps/commit/3b257aaf840c843186e84808e4d620c71099bedd))
- **junior:** delegation governs production not perception; ban source as rendered-state evidence ([83b8d72](https://github.com/nicsuzor/academicOps/commit/83b8d72442da4003c7d9d94ec498a952fbfe1e83))
- **merge-prep:** drop global serialisation, drain on completion, watchdog hung Claude ([#1464](https://github.com/nicsuzor/academicOps/issues/1464)) ([6dfec5a](https://github.com/nicsuzor/academicOps/commit/6dfec5a3b3c1e401b9faed150a95ef1e852cffe5))
- move AOPS_CC_OAUTH_TOKEN forwarding to polecat.yaml container_env_forward ([4e24c35](https://github.com/nicsuzor/academicOps/commit/4e24c35a3d2e61d29647604e2ab85b15194f0244))
- **polecat:** block host-leaked AOPS_GATE_FILE_* and AOPS_HOOK_LOG_PATH from container env ([#1463](https://github.com/nicsuzor/academicOps/issues/1463)) ([2b0c412](https://github.com/nicsuzor/academicOps/commit/2b0c412bee7f0ab79ac37248406ed133214b13f3))
- **polecat:** create worktree branches with --no-track to stop spurious origin/main tracking ([54079bf](https://github.com/nicsuzor/academicOps/commit/54079bf2952cfdd22be5bbbf75f00ebee9bfe1f9))
- **polecat:** create worktree branches with --no-track to stop spurious origin/main tracking ([0f8107a](https://github.com/nicsuzor/academicOps/commit/0f8107ae8ceb1213f565a10645a96d8e4719ba77))
- **polecat:** discover real transcript in flat local-daemon layout ([7cb9962](https://github.com/nicsuzor/academicOps/commit/7cb99629058b300201a1df23e49c3e6bd797ca0c))
- **polecat:** discover real transcript in flat local-daemon layout ([9ce3522](https://github.com/nicsuzor/academicOps/commit/9ce352295dd1b2e83efb650b8615759858eb1ff8))
- **polecat:** export AOPS_CC_OAUTH_TOKEN for ssh dispatch ([f44a296](https://github.com/nicsuzor/academicOps/commit/f44a296ba6f678d2c8d06e11696abd44716e94c4))
- **polecat:** nuke silent fallbacks in high-blast-radius hooks/ + polecat/ files ([9b6a24d](https://github.com/nicsuzor/academicOps/commit/9b6a24d2cdd349b15a458b355eceed4c910100cd))
- **polecat:** nuke silent fallbacks in high-blast-radius hooks/ + polecat/ files ([2391e71](https://github.com/nicsuzor/academicOps/commit/2391e71fdda1e12c7b65e4275b5e36383ac0ee38))
- **polecat:** restore `gemini` client alias dropped by PR [#1543](https://github.com/nicsuzor/academicOps/issues/1543) ([ece3950](https://github.com/nicsuzor/academicOps/commit/ece3950bc9d6ac497ac3bcd27abe632d6e408ae0))
- **polecat:** restore `gemini` client alias dropped by PR [#1543](https://github.com/nicsuzor/academicOps/issues/1543) ([dab4619](https://github.com/nicsuzor/academicOps/commit/dab4619b271a763c6213d0442677025469927a53))
- **polecat:** restore default tracking for existing-branch checkouts ([940973b](https://github.com/nicsuzor/academicOps/commit/940973b4bcfb190de0276abf4a4e616aa0c79be4))
- **pre-commit:** widen check-no-fallbacks scope to ALL first-party python ([#1585](https://github.com/nicsuzor/academicOps/issues/1585)) ([d41098c](https://github.com/nicsuzor/academicOps/commit/d41098cad08ac75558a0635ca79314c7fc57be92))
- **rbg:** resolve R8 rule contradiction between mandatory verdict and judgment-guide hedge ([85d0833](https://github.com/nicsuzor/academicOps/commit/85d083367995114e2cac8eccaaf68c68b2e04f9d))
- redirect broken wf12 refs in /aops SKILL.md router to wf11 §3 ([#1460](https://github.com/nicsuzor/academicOps/issues/1460)) ([d913c0b](https://github.com/nicsuzor/academicOps/commit/d913c0b3506fff4aa71b1180f39ed6e3c4915f4c))
- remove redundant TemplateRegistry import in pkb nudge try block ([6955694](https://github.com/nicsuzor/academicOps/commit/6955694800fef4a15a2200e3485f2a6d0182b71b))
- replace hardcoded transcript paths with \$AOPS_SESSIONS, gate on availability ([2c94014](https://github.com/nicsuzor/academicOps/commit/2c940146679f19892f693576b06c535c43c6fad8))
- replace instruction-budget.md with compact AXIOMS.md entry per reviewer direction ([912dd9d](https://github.com/nicsuzor/academicOps/commit/912dd9da7afb1f004ae2c6e6df89ecb20dd14154))
- resolve merge conflict + correct --home help text ([e144d1f](https://github.com/nicsuzor/academicOps/commit/e144d1f96dbf644197df25297ba11c632047981f))
- **self-test:** DRY the stderr-on-attachment lesson to satisfy C1 (116→99 lines) ([8b829e6](https://github.com/nicsuzor/academicOps/commit/8b829e6aaeccc234c851f7a7694cfda8150bf4a4))
- stale test timestamps, depersonalise spec, add cross-ref link ([d40697a](https://github.com/nicsuzor/academicOps/commit/d40697af0fbcf9114be190194d92b9eece43018b))
- stop/handover gate read-only exemption + Gemini loop-breaker ([#1465](https://github.com/nicsuzor/academicOps/issues/1465)) ([72a1f79](https://github.com/nicsuzor/academicOps/commit/72a1f79eb74651ea229fb7ed2e186c7ae225f8df))
- **strategic-review:** point arch-fit lens at the real vision/specs locations ([a8a25e5](https://github.com/nicsuzor/academicOps/commit/a8a25e55420e0f46adaf61fbef0ed1896ee3e156))
- **strategic-review:** point arch-fit lens at the real vision/specs locations ([f29a338](https://github.com/nicsuzor/academicOps/commit/f29a338e3a4fe34489fde1b4b21edaa788627de1))
- **supervision-loop:** complete ready_for_user_review → merge_ready migration ([87c0249](https://github.com/nicsuzor/academicOps/commit/87c024922a049d69da139de4f8c8bd5c122adbf8))
- **test:** replace 105 git-commit subprocesses with single fast-import in stale-branch fixture ([#1488](https://github.com/nicsuzor/academicOps/issues/1488)) ([7c0b9d2](https://github.com/nicsuzor/academicOps/commit/7c0b9d2591c34c7b06c9d2debbc56375b20ea835))
- **transcript:** ALWAYS emit started_at, last_modified, ended_at from event timestamps ([#1542](https://github.com/nicsuzor/academicOps/issues/1542)) ([999082c](https://github.com/nicsuzor/academicOps/commit/999082c7ab2fc87750e9066bb93851f27296686a))
- **transcript:** classify host Agent-SDK workers as claude-sdk surface ([#1592](https://github.com/nicsuzor/academicOps/issues/1592)) ([2c9a81e](https://github.com/nicsuzor/academicOps/commit/2c9a81ea333b8f86b84d3faf1abd93d93f953ed2))
- **transcript:** drop env-var fallback for insights crew ([#1559](https://github.com/nicsuzor/academicOps/issues/1559)) ([505f4dd](https://github.com/nicsuzor/academicOps/commit/505f4dd0530003cd986e4b3999280a769d587905))
- **transcript:** remove verbatim-duplicate fallback block in main() ([4cdcef5](https://github.com/nicsuzor/academicOps/commit/4cdcef5bdb11b46919a2c79b204fe5e587be0f52))
- **transcripts:** drop content-derived slug, use deterministic naming ([358d257](https://github.com/nicsuzor/academicOps/commit/358d257dd925e04cecf3bc541cc30ee53a9e5085))
- **transcripts:** freeze parent transcript slug at first-render time ([ba8915e](https://github.com/nicsuzor/academicOps/commit/ba8915e925a65630e054ca200f55fe9ed0cd3928))
- **transcripts:** freeze parent transcript slug at first-render time ([c5745fa](https://github.com/nicsuzor/academicOps/commit/c5745fa1b8127388176928f16c70f2e46171e8c0))
- **transcripts:** stop excluding short polecat sessions; refactor batch loop ([#1493](https://github.com/nicsuzor/academicOps/issues/1493)) ([77c8241](https://github.com/nicsuzor/academicOps/commit/77c82410d2278c3464656a923a49660d3be248c6))
- update stale test assertion and apply Gemini path/schema suggestions ([3508771](https://github.com/nicsuzor/academicOps/commit/35087711a963447ee1759c536cbae1fe5d5fd6ff))
- update test fixtures for polecat_home/antigravity_model + stale dates ([c3794a7](https://github.com/nicsuzor/academicOps/commit/c3794a7271aa5d6f016858ab682977262120f303))
- **verify:** force HALT on terminal QA defects + ban verdict-priming briefs ([#1587](https://github.com/nicsuzor/academicOps/issues/1587)) ([538a7e6](https://github.com/nicsuzor/academicOps/commit/538a7e6867f1e94a1276a36e85a593d713b9b48d))
- **worker:** halt-on-unsatisfiable AC instead of substituting an easy adjacent action ([991e845](https://github.com/nicsuzor/academicOps/commit/991e84541e02f21857f705c3ade4cd1824b53eb5))
- **workflows:** add permissions block to pr-pipeline shim ([#1558](https://github.com/nicsuzor/academicOps/issues/1558)) ([823b673](https://github.com/nicsuzor/academicOps/commit/823b67316755a152647c1fa910ab5b2e26b07b65))

### Code Refactoring

- **env:** standardise env vars, close OAuth leak, fix A8 fallbacks ([3fea33d](https://github.com/nicsuzor/academicOps/commit/3fea33de679a84a8f4e4513b4d7012496de05a70))
- **env:** standardise env vars, close OAuth leak, fix A8 fallbacks ([477e1e4](https://github.com/nicsuzor/academicOps/commit/477e1e4106423ae2c2f5306d0d4c572073b28af4))
- **hooks:** unify session-start self-diagnostics into new-style blocks ([#1484](https://github.com/nicsuzor/academicOps/issues/1484)) ([95e7894](https://github.com/nicsuzor/academicOps/commit/95e7894e58402453603b500bfbcc93c75dcac952))

### Documentation

- deployment guide for aops bot to repos ([#1377](https://github.com/nicsuzor/academicOps/issues/1377)) ([3d6a038](https://github.com/nicsuzor/academicOps/commit/3d6a038ecf476170a5746b4e9728e9d65a6d5817))
- **enforcement:** clean spec + map; add live PR-review-pipeline rows ([ca1818a](https://github.com/nicsuzor/academicOps/commit/ca1818a1cd8389593ad8aba812957fdf4a979cab))
- **enforcement:** rename cost-ladder framing to Braithwaite regulatory pyramid ([eb29a0f](https://github.com/nicsuzor/academicOps/commit/eb29a0f9095b4fc24a99a7874235bb28148735a5))
- **enforcement:** rename cost-ladder framing to Braithwaite regulatory pyramid ([c9dfa51](https://github.com/nicsuzor/academicOps/commit/c9dfa51568b98416f9a62392658aaa030aabbbac))
- **enforcement:** revise PR-review-pipeline rows per reviewer feedback ([37775cf](https://github.com/nicsuzor/academicOps/commit/37775cf071ec04fd307f18379d06600913dcb0e2))
- **pkb:** consolidate focus_score/priority model — remove residual stale references ([a68907c](https://github.com/nicsuzor/academicOps/commit/a68907ced00f57da399da6943d2b66122c445e1a))
- **planner:** reference VoI in plan-mode; prompt for classification in capture/decompose ([6ee4391](https://github.com/nicsuzor/academicOps/commit/6ee43913a497c353e5528efabee69fbc687f613f))
- stop pinning claude-opus-4-7 in instructions — use opus-4-8 / family alias ([921c854](https://github.com/nicsuzor/academicOps/commit/921c85429426609a7a4d65fb95a7fdda4e2f0529))
- v0.4 integrity & security release notes (fixes [#1385](https://github.com/nicsuzor/academicOps/issues/1385) quality issues) ([#1467](https://github.com/nicsuzor/academicOps/issues/1467)) ([0a9a351](https://github.com/nicsuzor/academicOps/commit/0a9a3516be967272534ae9066e018f6339d765d7))

### CI/CD

- add id-token write permission to enforcer workflows ([742fc68](https://github.com/nicsuzor/academicOps/commit/742fc68f86ecf85ffb0e13a5a2a6fb0dfe8728c9))
- add low-friction force-trigger for Enforcer (RBG) ([cc41591](https://github.com/nicsuzor/academicOps/commit/cc415913614346085a4249c896e859301c5fef97))
- add low-friction force-trigger for Enforcer (RBG) ([641eebd](https://github.com/nicsuzor/academicOps/commit/641eebd552bb003d6bf011cd735950d61456829d))
- fix Enforcer (RBG) auth by adding id-token: write ([6d5b244](https://github.com/nicsuzor/academicOps/commit/6d5b244ad957334372b320ad9d5b73abcd4da174))
- retrigger enforcer (transient 'agent run failed without verdict') ([040732f](https://github.com/nicsuzor/academicOps/commit/040732fb68c111226d67e617cce9eda3b90e8c09))

### Tests

- **deny-rules:** accept Claude's "sensitive file"/"protected" refusal phrasing ([1da84da](https://github.com/nicsuzor/academicOps/commit/1da84da669538e95f11ee41746329774fbaafc3a))
- **deny-rules:** accept Claude's "sensitive file"/"protected" refusal phrasing ([eb2f02f](https://github.com/nicsuzor/academicOps/commit/eb2f02f4d2c8ce7913d7b0f498a179f9f7ed25a9))
- detect stale dist/ in Gemini e2e tests to prevent phantom failures ([#1461](https://github.com/nicsuzor/academicOps/issues/1461)) ([af2b296](https://github.com/nicsuzor/academicOps/commit/af2b296522e048303bd9ae5738cfc036fa99968a))
- **e2e:** clear stale pr_url in fixture reset so pc run can re-dispatch ([28ea32c](https://github.com/nicsuzor/academicOps/commit/28ea32cf591671357f13b31271ddfa1d93e1e76a))
- **e2e:** drop gemini parameterization from invocation/transcript surface tests ([da1f59a](https://github.com/nicsuzor/academicOps/commit/da1f59ac062d8bab4a746743eefe2ac8afdf88f4))
- **e2e:** drop gemini parameterization from invocation/transcript surface tests ([cc421b6](https://github.com/nicsuzor/academicOps/commit/cc421b63f47faa647ebef3b05f634fe49f20a16d))
- **e2e:** finish gemini drop — remove termination test + dead gemini branches ([74bf04f](https://github.com/nicsuzor/academicOps/commit/74bf04f41b75139621e95c9983114ab3e20fe590))
- **e2e:** finish gemini drop — remove termination test + dead gemini branches ([c626e0d](https://github.com/nicsuzor/academicOps/commit/c626e0d5f3171a3fd23386e32984e9a124548262))
- **e2e:** match polecat SSoT hook log filename in crew discovery ([f8df988](https://github.com/nicsuzor/academicOps/commit/f8df98875d6c821a5144e1c1b4353118d5198c56))
- **e2e:** pass AOPS_BOT_GH_TOKEN to docker tooling/entrypoint tests ([eaa1e87](https://github.com/nicsuzor/academicOps/commit/eaa1e8730ab52683e56d58c4a687a41ede05bd33))
- green the slow suite after polecat config-SSoT ([#1561](https://github.com/nicsuzor/academicOps/issues/1561)), + fix transcript discovery ([fbee858](https://github.com/nicsuzor/academicOps/commit/fbee85850c1072f5b15cfce9534de0db5ac5f466))
- **pkb-persistence-e2e:** drop invalid "spike" task type so the run executes ([8a7f690](https://github.com/nicsuzor/academicOps/commit/8a7f6903dcc21e980acbced02ac54ee92aa6e5bf))
- **pkb-persistence-e2e:** drop invalid "spike" task type so the run executes ([3a609bb](https://github.com/nicsuzor/academicOps/commit/3a609bb47aaf16bebfa1a01e8c3cfadad290d365))
- **polecat:** adapt docker integration tests to config-is-SSoT contract ([949bb1f](https://github.com/nicsuzor/academicOps/commit/949bb1f8545aa2c47f90bf17f945a23dbc0d6e44))
- **security:** de-flake deny-rule check via structured permission_denials + robust prose ([b287798](https://github.com/nicsuzor/academicOps/commit/b287798c0ad54aa1ed996ef8dc7617b4f1935be4))
- **security:** de-flake deny-rule check via structured permission_denials + robust prose ([2db0411](https://github.com/nicsuzor/academicOps/commit/2db041174178350ec75e25f4eb0c58b7fd64fc7f))
- **slow:** remove opt-in env gates so e2e tests actually run; drop DinD test ([f249ff7](https://github.com/nicsuzor/academicOps/commit/f249ff713c562c5e6c4273a77ee59c1a2c9e4625))
- **slow:** remove opt-in env gates so e2e tests actually run; drop DinD test ([809e97f](https://github.com/nicsuzor/academicOps/commit/809e97f5c66c8208e65f84e982f0ce30253830be))
- **transcript-e2e:** repair bit-rot so the now-unskipped run actually executes ([7108de5](https://github.com/nicsuzor/academicOps/commit/7108de5f7ffa61eed405fc886b9442f8f2ed8b26))
- **transcript-e2e:** repair bit-rot so the now-unskipped run actually executes ([808f34c](https://github.com/nicsuzor/academicOps/commit/808f34c55f64468e5d2e9165b24156556617d113))

### Miscellaneous

- **survey:** add severity omit constraint for task nodes ([#1537](https://github.com/nicsuzor/academicOps/issues/1537)) ([455de87](https://github.com/nicsuzor/academicOps/commit/455de87853f68f24aab823a55a9f0199f38f5986))

## [0.3.32](https://github.com/nicsuzor/academicOps/compare/v0.3.31...v0.3.32) (2026-05-28)

### Features

- **antigravity:** map UserPromptSubmit/Stop to PreInvocation/PostInvocation in agy build ([#1421](https://github.com/nicsuzor/academicOps/issues/1421)) ([a47ad7a](https://github.com/nicsuzor/academicOps/commit/a47ad7ad164bfaa3309e5600a7514af3392b2a6c))
- **build:** ship aops-cowork as a separate plugin with PKB-native task-list sync ([a19169d](https://github.com/nicsuzor/academicOps/commit/a19169d64d46a96b3c9be7f0da40185dbfe9e267))
- **gates:** add sentinel gate for destructive env-op protection ([#1424](https://github.com/nicsuzor/academicOps/issues/1424)) ([24d9628](https://github.com/nicsuzor/academicOps/commit/24d96280b0049b313acbae587d23fb8171c17861))

### Bug Fixes

- address review feedback ([d8a08f7](https://github.com/nicsuzor/academicOps/commit/d8a08f7691d5c1353ac7646571552f52e7ac28ee))
- correct loop_detector source citation to agent-merge-prep.yml ([82126ae](https://github.com/nicsuzor/academicOps/commit/82126ae55e6c83bea5d343b7b8dbcf7b3ba359b0))
- **cowork-sync:** correct get_task_children param to id (was parent_id) ([bbcce5b](https://github.com/nicsuzor/academicOps/commit/bbcce5b58c51ae5e463e1804f85e92e2f710f113))
- **docker:** replace invalid for-loop one-liner with list comprehension ([#1417](https://github.com/nicsuzor/academicOps/issues/1417)) ([87e59ab](https://github.com/nicsuzor/academicOps/commit/87e59ab8aaf46f40f094ba4ad6cdf0b25d753aa8))
- **gates:** QA gate closes on task-claim only, not write-tool use ([#1418](https://github.com/nicsuzor/academicOps/issues/1418)) ([44cb0d8](https://github.com/nicsuzor/academicOps/commit/44cb0d80584a8931ae224d99d655905b88ddf53e))
- **hooks:** stop harness worktrees from pushing to main ([b993c1e](https://github.com/nicsuzor/academicOps/commit/b993c1ebdb00b63ea0fd40bae2ce55aaf113a300))
- **hooks:** stop harness worktrees from pushing to main ([6bb4293](https://github.com/nicsuzor/academicOps/commit/6bb42937423789e645cb2b42048a18b42c0bdbcf))
- **session-env:** use AOPS_BOT_GH_TOKEN exclusively for GitHub auth, fail-closed ([fa231e6](https://github.com/nicsuzor/academicOps/commit/fa231e6b1e65fb811e37fe57bd74110f37759180))

### Code Refactoring

- **hooks:** use invoke_agent for Gemini enforcer/qa calls ([#1419](https://github.com/nicsuzor/academicOps/issues/1419)) ([b61d483](https://github.com/nicsuzor/academicOps/commit/b61d483c52124d99cb4365ae27eae636c378d8a7))

### Documentation

- **self-test:** add plugin pre-check and permission mode guidance to §2 ([#1422](https://github.com/nicsuzor/academicOps/issues/1422)) ([68912c0](https://github.com/nicsuzor/academicOps/commit/68912c02d05bee3486e9965be9b0605fd8fbc4c1))

### Tests

- fix stale ANTHROPIC_API_KEY forwarding assertion ([d3a9b3d](https://github.com/nicsuzor/academicOps/commit/d3a9b3d5666f1a4f405a4151296785d1550b366c))
- verify agent vs user hook content routing across all events ([#1420](https://github.com/nicsuzor/academicOps/issues/1420)) ([f2b9697](https://github.com/nicsuzor/academicOps/commit/f2b969761b3b29a792d7522244078832bf9ff10f))

## [0.3.31](https://github.com/nicsuzor/academicOps/compare/v0.3.30...v0.3.31) (2026-05-27)

### Features

- add install-agy target for Antigravity CLI plugin ([7583417](https://github.com/nicsuzor/academicOps/commit/7583417770a1c7cf653eded9124c0a03f355e5af))
- automatic scheduling for issue-sweep loop driver ([#1376](https://github.com/nicsuzor/academicOps/issues/1376)) ([16f3126](https://github.com/nicsuzor/academicOps/commit/16f31263c5ac7e76a0babe3e020bd89df65126ab))
- **gates:** add sticky_until to GateTransition, replace ad-hoc latches ([8023aaf](https://github.com/nicsuzor/academicOps/commit/8023aaf5be0daa7c174571b400ec8380fcb902a7))
- **gates:** add sticky_until to GateTransition, replace ad-hoc latches ([06cf867](https://github.com/nicsuzor/academicOps/commit/06cf867856d19a54103ebc5eb41845ffb954f989))
- **gates:** handover gate session-type aware ([6d7c80e](https://github.com/nicsuzor/academicOps/commit/6d7c80e0965c1d7c62afb71cd9fd925e668417eb))
- **gates:** handover gate session-type aware — polecat starts CLOSED, interactive stays OPEN ([b91e208](https://github.com/nicsuzor/academicOps/commit/b91e208e43dc37720ba516e948a7156baae20ace))
- implement cross-session command center (aops sessions) ([e3083e1](https://github.com/nicsuzor/academicOps/commit/e3083e16b44c95052185d442a30e7fca09714275))
- **rbg:** add 7 verdict-composition discipline rules + ENFORCEMENT-MAP rows ([#1360](https://github.com/nicsuzor/academicOps/issues/1360)) ([c1e62ee](https://github.com/nicsuzor/academicOps/commit/c1e62ee13c2aa65612821761dc723d584339188c))
- refile flag now triggers full weight evaluation, not just reparenting ([f94eb89](https://github.com/nicsuzor/academicOps/commit/f94eb894bd83a2480b555ce6d332ecf40eae4335))
- refile flag triggers full weight evaluation ([785c595](https://github.com/nicsuzor/academicOps/commit/785c5952abc9be1c323249a87c55a4119e23d959))
- **supervisor:** auto-arm docker-events Monitor on first polecat dispatch ([#1381](https://github.com/nicsuzor/academicOps/issues/1381)) ([9923f71](https://github.com/nicsuzor/academicOps/commit/9923f714e0453142eaf4784ccc8602b29b8c139e))
- **survey:** add PR search and cross-linking for findings ([#1332](https://github.com/nicsuzor/academicOps/issues/1332)) ([3bc3da5](https://github.com/nicsuzor/academicOps/commit/3bc3da50ac8df4ddac9617f69b861e37fb3b2cc5))

### Bug Fixes

- /q capture silently routes teaching tasks to wrong project ([#1054](https://github.com/nicsuzor/academicOps/issues/1054)) ([#1342](https://github.com/nicsuzor/academicOps/issues/1342)) ([4900b0f](https://github.com/nicsuzor/academicOps/commit/4900b0f049af2cf2df51ab8e27de880578643d30))
- /sleep close-the-loop no longer auto re-queues closed-not-merged PRs ([#1361](https://github.com/nicsuzor/academicOps/issues/1361)) ([b644324](https://github.com/nicsuzor/academicOps/commit/b64432429ed9f6cc649f144cc88f9e4e22b7620f))
- 939: gemini crew session hooks/transcripts only sync on clean exit ([#1322](https://github.com/nicsuzor/academicOps/issues/1322)) ([b1f3311](https://github.com/nicsuzor/academicOps/commit/b1f3311edb98916c5b8b06f6410d6738492166fc))
- align Phase 8 severity/priority guidance with canonical SKILL.md rules ([2c886f1](https://github.com/nicsuzor/academicOps/commit/2c886f19031118a595bdb239a26f05b2700eccc8))
- **build:** strip Claude plugin namespace from Gemini tool names, preserve env vars ([#1399](https://github.com/nicsuzor/academicOps/issues/1399)) ([f005451](https://github.com/nicsuzor/academicOps/commit/f00545180c37ab7f29919c59898ed2679b48128e))
- cap basedpyright Node.js heap to prevent runner OOM in typecheck CI ([#1373](https://github.com/nicsuzor/academicOps/issues/1373)) ([180ed67](https://github.com/nicsuzor/academicOps/commit/180ed6797e9df242873078396aa22fd229fa74d0))
- **ci:** carry forward merge-prep success on synchronize events ([9544232](https://github.com/nicsuzor/academicOps/commit/9544232faa244a7bb1c313f5d4c99a116210c1b8))
- **ci:** carry forward merge-prep success on synchronize events ([e759f69](https://github.com/nicsuzor/academicOps/commit/e759f6946ce44787376be6324eeac71c3eb84d12))
- **ci:** pass force=true when dispatching re-qualified PRs ([f9f8ab6](https://github.com/nicsuzor/academicOps/commit/f9f8ab60ebb03283a9e1dfc1cc720ab3a3461da8))
- **ci:** pass force=true when dispatching re-qualified PRs ([be089e2](https://github.com/nicsuzor/academicOps/commit/be089e2df5364ddbcbef5612d5c7889975296574))
- clarify human approval gate and request reviewer on merge-prep approve ([092ded7](https://github.com/nicsuzor/academicOps/commit/092ded747261ec8f943195e014d164530cbda3c3))
- correct IDA warn-mode test assertion and bootstrap token env var ([1cae68c](https://github.com/nicsuzor/academicOps/commit/1cae68cc863dc8f6b3c3d6192314a28e1ed311f0))
- **docker:** copy marketplace.json to cache dir for CC plugin validation ([#1414](https://github.com/nicsuzor/academicOps/issues/1414)) ([1083f5e](https://github.com/nicsuzor/academicOps/commit/1083f5ef383e7dd4ea811502940e32292b5c85ec))
- **docker:** correct ~/.config dir permissions that blocked gh CLI auth ([#1357](https://github.com/nicsuzor/academicOps/issues/1357)) ([846fcbf](https://github.com/nicsuzor/academicOps/commit/846fcbf104ecf8877503d4ef733b94391a397b6f))
- **docker:** install Claude plugin and Gemini extension from single clone ([5d83db9](https://github.com/nicsuzor/academicOps/commit/5d83db9e1b4af170618a8eb0b5db1de9058481c4))
- **docker:** install Claude plugin and Gemini extension from single clone ([21d5d22](https://github.com/nicsuzor/academicOps/commit/21d5d223738f3da679987c2c0d64d55661d41af2))
- **docker:** install gemini extensions from subdirectories, not repo root ([d1213ed](https://github.com/nicsuzor/academicOps/commit/d1213ed0263cbfffa182656dd57e38f4d7c5993c))
- **docker:** patch known_marketplaces.json after deleting /tmp/aops-dist ([31b20e9](https://github.com/nicsuzor/academicOps/commit/31b20e9980e7ded3530c4cbcb59afe94cda14362))
- **docker:** trust source dir /tmp/aops-dist for gemini extensions install ([114c72c](https://github.com/nicsuzor/academicOps/commit/114c72ccd0c63c53767ba0380c52f56bb3a83ed3))
- **dogfood:** add "work must land" principle — silent drops are failures ([1b98513](https://github.com/nicsuzor/academicOps/commit/1b98513fb26adcdad5fa72ee5fddb56bffeead40))
- **gates:** allow Stop/SubagentStop events through gates for subagent sessions ([37a1466](https://github.com/nicsuzor/academicOps/commit/37a14668e574fcb85df4093db500c84a7720b698))
- **gates:** allow Stop/SubagentStop through gates for subagent sessions ([029e014](https://github.com/nicsuzor/academicOps/commit/029e0140a85e488b8dab15137bab4a59492fbab8))
- guard create_task against invalid status values (active, draft) ([#1319](https://github.com/nicsuzor/academicOps/issues/1319)) ([14d9fc7](https://github.com/nicsuzor/academicOps/commit/14d9fc7b15428b36f292b7d468b1a22ddc31f8b3))
- **lint:** rename unused loop variable in transcript_parser.py ([8bfccc5](https://github.com/nicsuzor/academicOps/commit/8bfccc59ecfc3d78a8d16e8ac3f81a5784b6fa1e))
- **lint:** rename unused loop variable in transcript_parser.py ([4cb86f1](https://github.com/nicsuzor/academicOps/commit/4cb86f11e578e6d63a42543b6e5be16af21d45a6))
- **marsha:** add algorithm-aware probe-region selection for visualisation QA ([#1328](https://github.com/nicsuzor/academicOps/issues/1328)) ([4dc44be](https://github.com/nicsuzor/academicOps/commit/4dc44be4dc3bffd66f4ec2322ecb4ca36bd897e1))
- parse Emergency Handover blocks from /dump sessions ([cba837d](https://github.com/nicsuzor/academicOps/commit/cba837dec5fd135dd328831d3a8f4345ad80944b))
- **polecat:** add oauthAccount placeholder to claude-config.json seed to fix worker authentication ([#1323](https://github.com/nicsuzor/academicOps/issues/1323)) ([5b41a71](https://github.com/nicsuzor/academicOps/commit/5b41a7182bf09f934d785baaf5fbdf9d295abea8))
- **polecat:** coerce tags to strings before join to avoid TypeError ([#1386](https://github.com/nicsuzor/academicOps/issues/1386)) ([11d9d09](https://github.com/nicsuzor/academicOps/commit/11d9d0974eb478a7c0a2b885e64ea54a3dba7eec))
- prevent QA gate endless loop after marsha verification ([50cd52b](https://github.com/nicsuzor/academicOps/commit/50cd52b69d73f246bec39f7cd23bebee3426e9a9))
- reconcile Step 0a batch auth with Step 4 no-confirmation policy ([f9562f8](https://github.com/nicsuzor/academicOps/commit/f9562f82f75f76a463da77d6fdcaa7271e69985d))
- register playwright MCP server for Gemini CLI agents ([#1354](https://github.com/nicsuzor/academicOps/issues/1354)) ([15f1af1](https://github.com/nicsuzor/academicOps/commit/15f1af13aa9838a252812643abc3c20b1a73d1ed))
- **remember:** close PKB quality gaps in sleep review ([#1346](https://github.com/nicsuzor/academicOps/issues/1346)) ([985ef6a](https://github.com/nicsuzor/academicOps/commit/985ef6ac8fb69b2d6620455d04416f3f1a551bc7))
- remove 26 brittle mirror tests that break on legitimate changes ([43bbd3f](https://github.com/nicsuzor/academicOps/commit/43bbd3ffbaf855ab052811c9f361426a923d0063))
- remove batch mode detail from Step 4 ([2baa1f6](https://github.com/nicsuzor/academicOps/commit/2baa1f6fb5cbeb93599c7696518487470639586c))
- remove brittle mirror tests that break on legitimate changes ([c4ad590](https://github.com/nicsuzor/academicOps/commit/c4ad590e559448680137bd13a05300adf731d1f4))
- remove cross-boundary references from aops-core plugin ([e487b43](https://github.com/nicsuzor/academicOps/commit/e487b43e23811384a1279998ea9a9febdef4668e))
- remove phantom permission gate from /review-pr Step 4 ([eb7c2a3](https://github.com/nicsuzor/academicOps/commit/eb7c2a3b88f86d65a1635b7425687d5240b584df))
- remove phantom permission gate from /review-pr Step 4 ([6305a37](https://github.com/nicsuzor/academicOps/commit/6305a3787ea406ac3516cc38efba2a7d3442275a)), closes [#1370](https://github.com/nicsuzor/academicOps/issues/1370)
- remove prematurely-committed test that depends on PR [#1334](https://github.com/nicsuzor/academicOps/issues/1334) ([84b0ee1](https://github.com/nicsuzor/academicOps/commit/84b0ee1642bd985d2b6aedfc237c2c4d6e497f00))
- remove remaining cross-boundary aops-core/ prefixed path references ([4c2ae8b](https://github.com/nicsuzor/academicOps/commit/4c2ae8b305de01392c33295d55909f924c9f7e3c))
- remove unused imports blocking ruff check on all PRs ([35b366d](https://github.com/nicsuzor/academicOps/commit/35b366dd4d988964ef93723bf1100fb58096d90e))
- replace priority-based sorting/surfacing with focus_score; enforce priority-is-user-intent ([0ea8e88](https://github.com/nicsuzor/academicOps/commit/0ea8e88f495eb2403a3baaec9ec93a7048c5eb45))
- replace triage:needs-judgment catch-all with triage:pipeline ([00872dd](https://github.com/nicsuzor/academicOps/commit/00872ddeb836edd8e154beabcacc3ec854d631ea))
- replace triage:needs-judgment catch-all with triage:pipeline ([137faaa](https://github.com/nicsuzor/academicOps/commit/137faaa1cbbeff375bb221430faa2cd0d3c5a796))
- resolve basedpyright type errors in scripts/generate.py ([7e81d18](https://github.com/nicsuzor/academicOps/commit/7e81d184cf463958afb7be5a493598c579bc2d20))
- **review-pr:** make posting mandatory — silent drops are review failures ([d2a50d6](https://github.com/nicsuzor/academicOps/commit/d2a50d67d5355b6f2f10e2e212ee92545fa9c466))
- **session-reader:** discover agy sessions at antigravity-cli path with workspace-based project attribution ([c476d30](https://github.com/nicsuzor/academicOps/commit/c476d301361882bcd3dc82843e733ccadd36cfc5))
- stop Ida gate leaking agent advisory text to user on Stop ([de257f0](https://github.com/nicsuzor/academicOps/commit/de257f0b91a30715750686afb90801d15c41250d))
- stop Ida gate leaking agent advisory to user on Stop ([49a370d](https://github.com/nicsuzor/academicOps/commit/49a370de5a94fd06bd1194364557e5af8c3c5a0c))
- survey/SKILL.md dispatch envelope Agent(tools=[...]) not honoured for sub-agents ([#1344](https://github.com/nicsuzor/academicOps/issues/1344)) ([0422910](https://github.com/nicsuzor/academicOps/commit/042291063c4bf474da2d4bbe6f46e4b08b979800))
- **tests:** address Gemini review feedback on handover session-type test ([5bb80b2](https://github.com/nicsuzor/academicOps/commit/5bb80b20193e20f780d5694e9fe756b5c76c93f5))
- **tests:** drop unused result variable flagged by ruff F841 ([660db34](https://github.com/nicsuzor/academicOps/commit/660db34d5bda5241a7c596df965df8746e74c0f3))

### Code Refactoring

- relocate state/audit/instruction files per doc-taxonomy ([#1365](https://github.com/nicsuzor/academicOps/issues/1365)) ([4ca88b4](https://github.com/nicsuzor/academicOps/commit/4ca88b482c15e1fd449e14f1ebe40617c3376833))
- trim scope per review — discard CLI and state writer ([54d6263](https://github.com/nicsuzor/academicOps/commit/54d6263d6722c71882a6901e535e170fe2d00a5f))

### Documentation

- add hook crash detection pre-flight to self-test workflow ([e1e98af](https://github.com/nicsuzor/academicOps/commit/e1e98afb4f9f3120e91634f8e35cb073b932f00d))
- add path pre-flight guard for messages_download_attachments ([f0ecd2b](https://github.com/nicsuzor/academicOps/commit/f0ecd2bd86a8ff69d41295a9b459ad3e2f3f30a6))
- codify pauli dispatch contract — strategist frames, doesn't investigate ([#1338](https://github.com/nicsuzor/academicOps/issues/1338)) ([23d4f1b](https://github.com/nicsuzor/academicOps/commit/23d4f1b0766614f4ec8052edd29583fd091e9c45))
- document gate configuration for users and fix resolution path ([aea3416](https://github.com/nicsuzor/academicOps/commit/aea3416e18ebfefeb1b5d028097d6b07f67a048c))
- document gate configuration for users and fix resolution path ([7b7bc65](https://github.com/nicsuzor/academicOps/commit/7b7bc6507f1def4b51cc471e5f4396a1cbe444ab))
- omcp messages_download_attachments path pre-flight guard ([e7bde16](https://github.com/nicsuzor/academicOps/commit/e7bde16b75de24c9dbf0659f4d824ae85ca1d664))
- update Phase 8 summary row to reflect weight evaluation scope ([26204cd](https://github.com/nicsuzor/academicOps/commit/26204cd327ecc9529628915e9ef81df9b2416818))

### Tests

- **gates:** replace synthetic handover fixtures with real hook log extracts ([a4c3c39](https://github.com/nicsuzor/academicOps/commit/a4c3c39b4eedb7f63be303be91c57ec87ff4dded))

## [0.3.30](https://github.com/nicsuzor/academicOps/compare/v0.3.29...v0.3.30) (2026-05-24)

### Bug Fixes

- **aops:** address PR [#1290](https://github.com/nicsuzor/academicOps/issues/1290) review — reframe self-test as live verification, broaden anti-synthetic prohibition ([374d492](https://github.com/nicsuzor/academicOps/commit/374d492d10c1380814de808ff0a6bbd914dc2dcf))
- **gates:** lock gate posture at SessionStart ([#1234](https://github.com/nicsuzor/academicOps/issues/1234)) ([03154cc](https://github.com/nicsuzor/academicOps/commit/03154ccf2ce07a83f7a46f58dcc75e8781ca2cdf))
- **gates:** lock gate posture at SessionStart, immune to mid-session env mutation ([#1234](https://github.com/nicsuzor/academicOps/issues/1234)) ([9a25448](https://github.com/nicsuzor/academicOps/commit/9a2544837689b49adbdf2eff3ca5bab341e2175c))
- **junior:** HALT-on-MCP-gap instruction + PKB Rules in CORE.md ([2fb8527](https://github.com/nicsuzor/academicOps/commit/2fb8527200d0b20faafab0b988e74c7728fe8073))
- **junior:** HALT-on-MCP-gap instruction in junior.md + CORE.md PKB Rules ([277701c](https://github.com/nicsuzor/academicOps/commit/277701c7fa06687ade71f6b993c81ab7686a9a7d))

### Reverts

- **gates:** remove posture-file machinery, read gate modes from os.environ ([3ca3e0d](https://github.com/nicsuzor/academicOps/commit/3ca3e0dad6b4a287c922e45b1c2e800d54c05439))

### Documentation

- **aops:** add self-test workflows 11+12 to SKILL.md routing, add transcript evaluation methodology ([2744f27](https://github.com/nicsuzor/academicOps/commit/2744f275d5f37f2f86641c23066680ed16a2037d))
- **aops:** add self-test workflows 11+12 to SKILL.md routing, add transcript evaluation methodology ([9bf8e64](https://github.com/nicsuzor/academicOps/commit/9bf8e64b6c28e3a606e0d988eed449bd82da71c5))

## [0.3.29](https://github.com/nicsuzor/academicOps/compare/v0.3.28...v0.3.29) (2026-05-24)

### Features

- **transcripts:** rotate into yyyy-mm subfolders (aops-b975b185) ([3a43adb](https://github.com/nicsuzor/academicOps/commit/3a43adbcd4d11a513d854605e3a9414481fb607c))

### Bug Fixes

- add brief-scope discipline to James review composition ([cd169be](https://github.com/nicsuzor/academicOps/commit/cd169be219403693e5deaca5deb48cf1ea12a6ed)), closes [#937](https://github.com/nicsuzor/academicOps/issues/937)
- add subprocess timeout and broaden exception handling in ensure_triage_labels ([346203e](https://github.com/nicsuzor/academicOps/commit/346203e33c4ebd47795c5b03207113f3a1080a67))
- **gates:** IDA warn-mode bug + per-turn gate lifecycle ([7d16d90](https://github.com/nicsuzor/academicOps/commit/7d16d902a8ed521eec70d73d23211074defb268a))
- **gates:** IDA warn-mode bug + per-turn lifecycle (aops-83f40207) ([110d72e](https://github.com/nicsuzor/academicOps/commit/110d72edc2a9164e28766be2e8a7f04ba22e8b76))
- **gates:** QA + handover warn-mode blocks Stop (aops-d8de4a55) ([eab16c5](https://github.com/nicsuzor/academicOps/commit/eab16c592910f82a65e5b6dc1133bbae7bebc495))
- **gates:** QA + handover warn-mode blocks Stop (same bug as IDA aops-83f40207) ([0923f2b](https://github.com/nicsuzor/academicOps/commit/0923f2bfe45faf8e2b23739d58fab4dfdbad9312))
- **polecat:** accept bare 'opus'/'sonnet'/'haiku' for --model ([b97a595](https://github.com/nicsuzor/academicOps/commit/b97a59522051298b67de8839153b91335741530b))
- **polecat:** accept bare 'opus'/'sonnet'/'haiku' for --model ([545a0ad](https://github.com/nicsuzor/academicOps/commit/545a0adf080281867c8e0c3fbefcbed2c95e89fb))
- prefer parent issue over anchor-in-child for meta-class cross-linking ([6480472](https://github.com/nicsuzor/academicOps/commit/6480472f47046cddf885604a0299401503394499))
- remove invalid hookSpecificOutput from non-accepted hook events ([577dbd0](https://github.com/nicsuzor/academicOps/commit/577dbd09af67bf8e2823ee666a6f6f56bd3c77b8))
- remove invalid hookSpecificOutput from non-accepted hook events ([0681318](https://github.com/nicsuzor/academicOps/commit/06813183cfadb88c66ded53f3675fe37c9d883b0))
- simplify compose-then-dispatch sections and rename verdict_malformed to verdict_fail ([712ee4d](https://github.com/nicsuzor/academicOps/commit/712ee4d694cf691156ff048c20d0051fadff8655))
- **transcripts:** detect gemini chat-jsonl at bind-mount-source paths ([09b35e0](https://github.com/nicsuzor/academicOps/commit/09b35e0c8f40de8c31b5fa0de9b807f96688b7ac))
- **transcripts:** detect gemini chat-jsonl at bind-mount-source paths ([afe55a3](https://github.com/nicsuzor/academicOps/commit/afe55a33129bce56e8c1ebd693c19652f8017097)), closes [#1153](https://github.com/nicsuzor/academicOps/issues/1153)
- **transcripts:** exclude Claude-shaped entries from message-style schema detection ([bddf316](https://github.com/nicsuzor/academicOps/commit/bddf316ee0bf3b3a909cfba2876a9ebf14fc0d03))

### Documentation

- add conversation discipline and narration guard to junior agent ([#1279](https://github.com/nicsuzor/academicOps/issues/1279)) ([fb749c6](https://github.com/nicsuzor/academicOps/commit/fb749c69b86e84ffcced4a505a9d8f474ccd4b6a))

## [0.3.28](https://github.com/nicsuzor/academicOps/compare/v0.3.27...v0.3.28) (2026-05-23)

### Features

- **polecat:** unified --model flag with alias resolution ([1b0db8f](https://github.com/nicsuzor/academicOps/commit/1b0db8f060f8799c41e3f942cb481167aa7cf02d))
- **polecat:** unified --model flag with alias resolution (aops-bc9cf926, aops-c54097aa) ([5c7a282](https://github.com/nicsuzor/academicOps/commit/5c7a282bf500842fcbbbaacac79bbc8c75f77b37))
- **self-test:** verify hook output channel routing per hook type (aops-45d4219f) ([069c15b](https://github.com/nicsuzor/academicOps/commit/069c15bcb25b538e6cef9196682adc2d24f54d67))

### Bug Fixes

- add forensic anchor reference to [#1197](https://github.com/nicsuzor/academicOps/issues/1197) ([2900c8e](https://github.com/nicsuzor/academicOps/commit/2900c8e78f81109207449333eb54bf82974138c7))
- address Gemini review — drop 'unknown' session ID fallback, fix cleanup path ([d59b151](https://github.com/nicsuzor/academicOps/commit/d59b151bd68b4d420135ea03fe55b3afbd5fbf19))
- address PR feedback to make ida-reminder concise ([e43cd05](https://github.com/nicsuzor/academicOps/commit/e43cd058f70e7cc5f1ddc46bef4cd53481c7a110))
- address PR feedback to make ida-reminder concise and remove comments from agent instructions ([d95c88b](https://github.com/nicsuzor/academicOps/commit/d95c88be712778ddd2208748cee41cd4ec5b36a2))
- **build:** drop unused gemini core_mcps assignment (F841) ([4225b8c](https://github.com/nicsuzor/academicOps/commit/4225b8c5c492aa7b222f02a24dfb5e570fc939d4))
- correct error message — aliases are hardcoded, not from polecat.yaml ([e39eb8f](https://github.com/nicsuzor/academicOps/commit/e39eb8f79aa56fe78a7871affe8dc59c75807704))
- **end_session:** respect /pull task binding ([#739](https://github.com/nicsuzor/academicOps/issues/739)) ([519f3eb](https://github.com/nicsuzor/academicOps/commit/519f3eb4bc48dfdd7453fabf595a7bbb588ce7fb))
- **end_session:** respect /pull task binding ([#739](https://github.com/nicsuzor/academicOps/issues/739)) ([01dfc38](https://github.com/nicsuzor/academicOps/commit/01dfc3836552d7b0d6d408902e5f34e729f3cc08))
- **gates:** wire qa gate close-on-work-begin trigger ([#1223](https://github.com/nicsuzor/academicOps/issues/1223)) ([5894df5](https://github.com/nicsuzor/academicOps/commit/5894df5d1b6bf09fbf1db30f3242ff7588c91837))
- **hooks:** route Stop hook advisory to agent context, not user chat (aops-d10e7db6) ([4f1e18b](https://github.com/nicsuzor/academicOps/commit/4f1e18b03b03858379d69beb1d58a06f65b210b2))
- **hooks:** route Stop hook advisory to agent context, not user chat (aops-d10e7db6) ([6e7602f](https://github.com/nicsuzor/academicOps/commit/6e7602fb58af7bab87f73332748b60826899bdb2))
- implement cluster [#1122](https://github.com/nicsuzor/academicOps/issues/1122) coordinator relay remediation ([d6fc810](https://github.com/nicsuzor/academicOps/commit/d6fc810d34818aefc8ccb3a798d6393304a337de))
- implement cluster [#1122](https://github.com/nicsuzor/academicOps/issues/1122) coordinator relay remediation ([20c25fd](https://github.com/nicsuzor/academicOps/commit/20c25fd248a66047bc4dec2928118d31285cf296))
- **merge-prep:** dispatch oldest qualifying PR, not newest ([#1129](https://github.com/nicsuzor/academicOps/issues/1129)) ([a7518ac](https://github.com/nicsuzor/academicOps/commit/a7518ac5b9e74f2ac06f28eaf914000bda66a660))
- **merge-prep:** dispatch oldest qualifying PR, not newest ([#1129](https://github.com/nicsuzor/academicOps/issues/1129)) ([1033028](https://github.com/nicsuzor/academicOps/commit/1033028dc89d6e5cdcf021aa1d3af87240a645eb))
- **merge-prep:** drop workflow_run trigger to stop dispatcher cascade ([5988e9a](https://github.com/nicsuzor/academicOps/commit/5988e9abf1083f0ede37f8d9c4c10c621797de2c))
- **merge-prep:** drop workflow_run trigger to stop dispatcher cascade ([209967c](https://github.com/nicsuzor/academicOps/commit/209967cb79ec140931d29edc423cf0c373ea5764))
- **pipeline:** move trigger shim to root and add discoverability check ([fa69fa6](https://github.com/nicsuzor/academicOps/commit/fa69fa640ba2f0c1325a34a7b53756cfe8b240ee))
- **polecat:** extend container claude-config seed with full trust gate set ([#1228](https://github.com/nicsuzor/academicOps/issues/1228)) ([a2cb448](https://github.com/nicsuzor/academicOps/commit/a2cb448cf1a3ec5fdd9a07a310ec1e85210b5ef4))
- **polecat:** restore crew bind-mount path (task-ac3e547b) ([4ee3db1](https://github.com/nicsuzor/academicOps/commit/4ee3db1c6f885901d1a72b74196fbc7252aed412))
- **polecat:** stamp gate env vars in run path ([#1196](https://github.com/nicsuzor/academicOps/issues/1196)) ([#1246](https://github.com/nicsuzor/academicOps/issues/1246)) ([d874cb8](https://github.com/nicsuzor/academicOps/commit/d874cb8917f83e18ecbbbbaa995eedbed184688e))
- **rbg:** narrow to axiom-violation check; route other enforcement via ENFORCEMENT-MAP ([7116091](https://github.com/nicsuzor/academicOps/commit/711609187432406736f17fe7d75f2419bcf266f7))
- **rbg:** strip PR-reviewer framing; reconcile enforcer-instruction dispatch ([#1059](https://github.com/nicsuzor/academicOps/issues/1059)) ([#1229](https://github.com/nicsuzor/academicOps/issues/1229)) ([c1121ab](https://github.com/nicsuzor/academicOps/commit/c1121abb5d926383cc95645080b95452775213f5))
- remove status:active drift across skills ([#1203](https://github.com/nicsuzor/academicOps/issues/1203)) ([d248849](https://github.com/nicsuzor/academicOps/commit/d248849a175c58223dbcfcb234062e8a07e454ad))
- remove status:active drift across skills ([#1203](https://github.com/nicsuzor/academicOps/issues/1203)) ([04a550e](https://github.com/nicsuzor/academicOps/commit/04a550e2d6b56cbae62c767e4c0eac3a7a430ba4))
- remove unused core_mcps_gemini variable in build.py (F841) ([bb260a2](https://github.com/nicsuzor/academicOps/commit/bb260a27205c689f18e40cef6fa4abb9f87b224b))
- replace ambiguous 'non-terminal status' with explicit set notation ([6290779](https://github.com/nicsuzor/academicOps/commit/62907791e6aac6581d6a6091ac285bb7347d2810))
- restore ambiguity exception prose and add trailing newline ([d4563cb](https://github.com/nicsuzor/academicOps/commit/d4563cb08617dbfc9fca945f54b2fdc5e09a653e))
- **self-test:** use distinct SYS/CTX markers and allow-verdict in hook routing test ([7504a26](https://github.com/nicsuzor/academicOps/commit/7504a26abe7ceacf94806daccdacdb1806a7a8c4))
- **skills:** update transcripts/*.md globs for yyyy-mm rotation (aops-cc4dccef) ([#1250](https://github.com/nicsuzor/academicOps/issues/1250)) ([f693d0a](https://github.com/nicsuzor/academicOps/commit/f693d0a20547b19a153b24af43c773b3f47bb603))
- **stop-hook:** make skill-invocation requirement explicit (aops-2db00caf) ([#1226](https://github.com/nicsuzor/academicOps/issues/1226)) ([c806bd7](https://github.com/nicsuzor/academicOps/commit/c806bd7725f0e016f58d6e9f0bcf0beea31c9007))
- strip -dirty suffix before promotion check in _with_build_metadata ([8a85e12](https://github.com/nicsuzor/academicOps/commit/8a85e1252e3489298fbcc1fb52946cd8a346a71c))
- **tests:** add task-ac3e547b anchor to POLECAT_HOME scrub comment ([fe67ba5](https://github.com/nicsuzor/academicOps/commit/fe67ba5c438ae4fce8084d935f4c8880326d7deb))
- **tests:** stop scrubbing POLECAT_HOME in autouse env fixture (task-ac3e547b) ([1db55ac](https://github.com/nicsuzor/academicOps/commit/1db55acc03de5cad2e43a7847c4c755f28b5f950))
- **tests:** use --allow-empty commits in stale branch test helper ([390af9a](https://github.com/nicsuzor/academicOps/commit/390af9a9b6e8bde27181a1f0e1461579be845973))
- **transcript:** drop POLECAT_CREW_NAME env fallback ([#768](https://github.com/nicsuzor/academicOps/issues/768)) ([0ed33f2](https://github.com/nicsuzor/academicOps/commit/0ed33f29fd2d26da10e5471ce1d3aca93d8a7b4d))
- **transcript:** drop POLECAT_CREW_NAME env fallback ([#768](https://github.com/nicsuzor/academicOps/issues/768)) ([882b92e](https://github.com/nicsuzor/academicOps/commit/882b92e49e3ad229b8aa47e00e0b94d86be76767))
- **types:** add TYPE_CHECKING stubs for PEP 562 lazy attrs in gate_config ([0f05f6b](https://github.com/nicsuzor/academicOps/commit/0f05f6b125331361bf178dc522935d9fcd455aab))
- **workflows:** pass pr_number as string to avoid startup_failure ([1f88e7f](https://github.com/nicsuzor/academicOps/commit/1f88e7f3776b5ae60fb451554c75f54977d75a7d))
- **workflows:** pass pr_number as string to enforcer ([1c4bc77](https://github.com/nicsuzor/academicOps/commit/1c4bc7709b3314bd9f883bc85cd58c3f668d7711))

### Reverts

- restore ida-reminder.md to compressed scale (PR [#1260](https://github.com/nicsuzor/academicOps/issues/1260) fix) ([234a6b1](https://github.com/nicsuzor/academicOps/commit/234a6b18693cc85673ecf100adc66b98b6076434))

### Code Refactoring

- **hooks:** consolidate sys_msg routing and clarify channel comments ([1808b5f](https://github.com/nicsuzor/academicOps/commit/1808b5f48a0871d0498f3a48b08c9c45193f5838))

### Documentation

- **self-test:** drop fragile footer-text boot signal from § 1 ([be4de47](https://github.com/nicsuzor/academicOps/commit/be4de47b53adfa542838151f60cbc3de7e96bbd9))
- **self-test:** drop fragile footer-text boot signal from § 1 ([32a0bb9](https://github.com/nicsuzor/academicOps/commit/32a0bb90d41cec03e8dcfd19299d559559ee11f2))
- **self-test:** restructure polecat validation as layered discriminator ([748671d](https://github.com/nicsuzor/academicOps/commit/748671d3b89ba9d1e059b9cc2332ef1f017ed10e))
- **self-test:** restructure polecat validation as layered discriminator ([dadc78b](https://github.com/nicsuzor/academicOps/commit/dadc78b8e4e0ee89e525b23f16ffd8ed3dbd5c69))
- **self-test:** verify hook output channel routing per hook type (aops-45d4219f) ([738c902](https://github.com/nicsuzor/academicOps/commit/738c90205f787385b32161e8aef1a103cc9756a6))

### CI/CD

- add timeout-breach regression check + clarify cap semantics ([#1232](https://github.com/nicsuzor/academicOps/issues/1232)) ([d0ff880](https://github.com/nicsuzor/academicOps/commit/d0ff880827fa7eae41c2e3defa0f3aa2bc5bac1b))
- cap merge-prep workflows at timeout-minutes: 30 ([#1230](https://github.com/nicsuzor/academicOps/issues/1230)) ([8e41bd9](https://github.com/nicsuzor/academicOps/commit/8e41bd95bfb06020b2fd61f6f1e75993b6c22a54))

### Build System

- promote dirty-tree builds at clean tags to pre-release ([d6f7d62](https://github.com/nicsuzor/academicOps/commit/d6f7d628ecc98ac66a2af32cc7512687da887011))

### Miscellaneous

- **spec:** mark polecat-dispatch-from-container-via-ssh as accepted ([#1257](https://github.com/nicsuzor/academicOps/issues/1257)) ([193ca30](https://github.com/nicsuzor/academicOps/commit/193ca30a037dd6d82180bbdf6fc912ec6a818cb8))

## [0.3.27](https://github.com/nicsuzor/academicOps/compare/v0.3.26...v0.3.27) (2026-05-21)

### Features

- **junior:** add salience-label filtering guardrail ([#1170](https://github.com/nicsuzor/academicOps/issues/1170)) ([6c7dc4b](https://github.com/nicsuzor/academicOps/commit/6c7dc4baf1f9c778cb421e97f9b2239c293bb586))

### Bug Fixes

- 1158: split issue-sweep comment-only disposition and tighten labels ([#1193](https://github.com/nicsuzor/academicOps/issues/1193)) ([b757b73](https://github.com/nicsuzor/academicOps/commit/b757b7345830f8c48f8de143fb337bb5dcea43d1))
- 1194: crew -- -p drops the -p flag in agent invocation ([#1199](https://github.com/nicsuzor/academicOps/issues/1199)) ([5aee876](https://github.com/nicsuzor/academicOps/commit/5aee8767f1b8571fbfccd161a63741a767fb71f8))
- 1195: nuke &lt;crew-name&gt; fails with ValueError when crew dir is absent or API bypasses CLI guard ([#1200](https://github.com/nicsuzor/academicOps/issues/1200)) ([6713615](https://github.com/nicsuzor/academicOps/commit/671361564226fc8677a133be9909621241bef64c))
- 785: supervisor misreads Gemini 429/QUOTA_EXHAUSTED as hard quota — real cause is polecat 45-min timeout ([#1186](https://github.com/nicsuzor/academicOps/issues/1186)) ([48fff07](https://github.com/nicsuzor/academicOps/commit/48fff07b20bcc5cb2d33aaa6c2e484c351c69ecb))
- address review feedback ([c7b76a7](https://github.com/nicsuzor/academicOps/commit/c7b76a7ea59d5eccf3913b40a98ee23dee8dfcbe))
- **cross-repo-shim:** grant explicit permissions on dispatch/merge-prep jobs ([#1163](https://github.com/nicsuzor/academicOps/issues/1163)) ([8cef3bb](https://github.com/nicsuzor/academicOps/commit/8cef3bb4eaca834410e3a107994a6494f64e263b))
- **custodiet:** reliability cluster — empty narratives, mid-work BLOCKs, WARN inertia, O(n²) parsing ([#1187](https://github.com/nicsuzor/academicOps/issues/1187)) ([48256b0](https://github.com/nicsuzor/academicOps/commit/48256b01aa5c1668824b4247c7f8538fa630c52c))
- gate_config Gemini regressions + Claude folder-trust seed ([#1205](https://github.com/nicsuzor/academicOps/issues/1205)) ([a8cccef](https://github.com/nicsuzor/academicOps/commit/a8cccef54c21c13ebd14b6fb5ccee749f4b87bbe))
- **gate-config:** bake in defaults so fresh install never tracebacks ([#1156](https://github.com/nicsuzor/academicOps/issues/1156)) ([5f72f80](https://github.com/nicsuzor/academicOps/commit/5f72f80a9a22fdf6f510324f6a6fd2d0756ece80))
- **james:** prescribe in-process Agent() dispatch, forbid subprocess ([#1178](https://github.com/nicsuzor/academicOps/issues/1178)) ([98a0afc](https://github.com/nicsuzor/academicOps/commit/98a0afc4d4b66b2d0f00af231d3fb910b691ef79))
- **james:** prescribe in-process Agent() dispatch, forbid subprocess ([#1178](https://github.com/nicsuzor/academicOps/issues/1178)) ([#1180](https://github.com/nicsuzor/academicOps/issues/1180)) ([f7431ff](https://github.com/nicsuzor/academicOps/commit/f7431ffbe83c8b86f41c028e164959bf46f6c446))
- **junior:** point framework vision to PKB doc, not removed docs/VISION.md ([d5ff480](https://github.com/nicsuzor/academicOps/commit/d5ff480cdd409fd0068badf8adae29eca4fed77e))
- **merge-prep-cron:** re-qualify success PRs when base advances and conflicts emerge ([#1168](https://github.com/nicsuzor/academicOps/issues/1168)) ([e9a2bda](https://github.com/nicsuzor/academicOps/commit/e9a2bda45883dd19ef9da92c3de7f6f33e42ca6d))
- **merge-prep:** add intent-vs-surface guidance to stop surface-only delta revisions ([#1184](https://github.com/nicsuzor/academicOps/issues/1184)) ([fc56665](https://github.com/nicsuzor/academicOps/commit/fc566653efaecc8d82c049c1a319a08ee4d06fd3)), closes [#983](https://github.com/nicsuzor/academicOps/issues/983)
- **pipeline:** Add terminal commit status on early pipeline failure in agent-merge-prep ([#1177](https://github.com/nicsuzor/academicOps/issues/1177)) ([32ea932](https://github.com/nicsuzor/academicOps/commit/32ea932ee08129c95193ab0977a76c97f1ee3536))
- **pkb-bridge:** self-heal mem indexer graph-binding race in create_task ([#1189](https://github.com/nicsuzor/academicOps/issues/1189)) ([72a8038](https://github.com/nicsuzor/academicOps/commit/72a803887a59d7b5310fab8eda07e24c0835e641))
- **planner:** reference Decision Surfacing Heuristic from decompose workflow ([6dd9ba8](https://github.com/nicsuzor/academicOps/commit/6dd9ba82de1294c365c6022c05ff76586708afa8))
- **polecat-crew:** seed .claude.json so claude workers skip onboarding ([3f9d394](https://github.com/nicsuzor/academicOps/commit/3f9d3948a3e3db2176ce32f0608eecafd46a6903))
- **polecat-worker:** preinstall gemini hook venv to skip cold-cache PyPI ([8601385](https://github.com/nicsuzor/academicOps/commit/8601385eb963b8838244e261cbe853dc8093ab2d))
- **polecat:** enable aops plugins in container claude-settings.json ([#1198](https://github.com/nicsuzor/academicOps/issues/1198)) ([d2b27ad](https://github.com/nicsuzor/academicOps/commit/d2b27ad1a3de2be93501c457025adb2603ef4b3b))
- **polecat:** record Claude Code version + e2e trust-seed runtime check ([#1220](https://github.com/nicsuzor/academicOps/issues/1220)) ([a85edc3](https://github.com/nicsuzor/academicOps/commit/a85edc3ca66aca19723bb42a1f074466e7c1f8ed))
- replace non-canonical kb- prefix example with aops- in IDA checklist ([dabe045](https://github.com/nicsuzor/academicOps/commit/dabe045f162513e947ddef2e689331788ee64e17))
- **supervisor:** use --model &lt;name&gt; in dispatch template, deprecate --opus/--gemini as model flags ([f23635b](https://github.com/nicsuzor/academicOps/commit/f23635b3ab0088a64856f67b4298d8a114f719ac))

### Documentation

- Compose-then-Dispatch separation (A17 propagated to dispatch surface) ([#1222](https://github.com/nicsuzor/academicOps/issues/1222)) ([1c99ebd](https://github.com/nicsuzor/academicOps/commit/1c99ebd6890df31341393408c380c37e6e1f90d8))
- **enforcement:** collapse two enforcement-maps + three tier ladders to one (aops-3c665002) ([#1192](https://github.com/nicsuzor/academicOps/issues/1192)) ([b3f8b2e](https://github.com/nicsuzor/academicOps/commit/b3f8b2e7255e1a0df028bf86a2e4748cc1aad28b))
- GATES.md cleanup per Pauli review ([#1218](https://github.com/nicsuzor/academicOps/issues/1218)) ([f53cdd1](https://github.com/nicsuzor/academicOps/commit/f53cdd13ac62090b155a21a1e5ad5faf13e6d5b9))
- **planner:** add 'deliverable-producing tasks wire to class-level production target' pattern ([#1219](https://github.com/nicsuzor/academicOps/issues/1219)) ([fab96b7](https://github.com/nicsuzor/academicOps/commit/fab96b717a72a82a412884413a86e046fd26b03f))
- **planner:** add Severity Assignment Rules + Deferring Work guidance ([#1164](https://github.com/nicsuzor/academicOps/issues/1164)) ([90784fb](https://github.com/nicsuzor/academicOps/commit/90784fba29e4bed238932ec33a0f88fc156b38aa))
- **self-test:** add polecat session validation as §2 of 11-self-test ([#1210](https://github.com/nicsuzor/academicOps/issues/1210)) ([9c71517](https://github.com/nicsuzor/academicOps/commit/9c71517a9b9a0cef01c6ed9f487c8d12e748aa99))
- **specs/agents:** A4 — collapse three agent-permission reps to spec pair + per-agent state + audit-artifact ([#1191](https://github.com/nicsuzor/academicOps/issues/1191)) ([a10b89e](https://github.com/nicsuzor/academicOps/commit/a10b89ebcc7a4767b3eb1aa21e359f5f057e6147))
- **specs:** land daily-pipeline spec series (PR 1/4) ([#1155](https://github.com/nicsuzor/academicOps/issues/1155)) ([ba752e5](https://github.com/nicsuzor/academicOps/commit/ba752e5387996591e4337bb103e3d422835f0d39))
- **supervisor:** add on-demand transcript refresh ([#1147](https://github.com/nicsuzor/academicOps/issues/1147)) ([6c971de](https://github.com/nicsuzor/academicOps/commit/6c971deeb63d6118c0572fe0d38f8d15ad7d54ea))
- **supervisor:** replace WORKERS.md with SURFACES.md execution-surface reference ([#1148](https://github.com/nicsuzor/academicOps/issues/1148)) ([3b4518b](https://github.com/nicsuzor/academicOps/commit/3b4518b0ea0d98511580f62d32a64b3b32fd47d6))
- **surfaces:** retire Mac Cowork→ssh-wsl, document WSL crew container as current (aops-e6a80f83) ([#1190](https://github.com/nicsuzor/academicOps/issues/1190)) ([dfe1c60](https://github.com/nicsuzor/academicOps/commit/dfe1c601bdd030347c8e0e0f5aa7af81dc18cda7))

## [0.3.26](https://github.com/nicsuzor/academicOps/compare/v0.3.25...v0.3.26) (2026-05-18)

### Features

- **daily:** codify PR triage dashboard process ([#1136](https://github.com/nicsuzor/academicOps/issues/1136)) ([74323eb](https://github.com/nicsuzor/academicOps/commit/74323ebf8330c586514999dfb0639a3a5e5f5972))
- **end_session:** update closing behaviors and resolve contradictions ([#1127](https://github.com/nicsuzor/academicOps/issues/1127)) ([0438437](https://github.com/nicsuzor/academicOps/commit/0438437dbe13babb24dd75510f05c3f22179136a))
- Gemini polecat auth validation — fail-fast in crew containers when credentials are missing ([#1106](https://github.com/nicsuzor/academicOps/issues/1106)) ([2e77391](https://github.com/nicsuzor/academicOps/commit/2e77391f7f2fece2de534c5364cc3318ac0bda6b))
- **instruction:** mandate point-of-discovery friction filing via /learn ([#1103](https://github.com/nicsuzor/academicOps/issues/1103)) ([0740a43](https://github.com/nicsuzor/academicOps/commit/0740a4394df6887ada23027d9056c4478d0fe199))
- **polecat:** add --max-turns CLI passthrough for deterministic budget-exhaustion testing ([#1094](https://github.com/nicsuzor/academicOps/issues/1094)) ([686edfc](https://github.com/nicsuzor/academicOps/commit/686edfc001a3ded7cff6d3a3c3d16a838c656cc3))
- **polecat:** add distinct budget-exhausted exit code and structured stderr resume hint ([#1112](https://github.com/nicsuzor/academicOps/issues/1112)) ([103b146](https://github.com/nicsuzor/academicOps/commit/103b1462a2651c9aa2c7dae3368cd3d15d7c56be))
- **supervisor:** add RBG axiom-check trigger to pauli preflight ([#1105](https://github.com/nicsuzor/academicOps/issues/1105)) ([9966d80](https://github.com/nicsuzor/academicOps/commit/9966d8062a8c75b881b4b5589ff77a43abfee2d3))

### Bug Fixes

- **#1128:** auto-heal Gemini-form MCP tool names at commit time ([#1143](https://github.com/nicsuzor/academicOps/issues/1143)) ([29c7150](https://github.com/nicsuzor/academicOps/commit/29c7150603b1cbac367cbcc919af799bc9dcccdc))
- **#1128:** CI guard against Gemini-form tool names escaping into source ([#1142](https://github.com/nicsuzor/academicOps/issues/1142)) ([bbee8eb](https://github.com/nicsuzor/academicOps/commit/bbee8eb5a461cfca4ba81a802669f1d7833ecfcc))
- address untriaged review feedback from PR batch ([#1098](https://github.com/nicsuzor/academicOps/issues/1098), [#1096](https://github.com/nicsuzor/academicOps/issues/1096)) ([#1140](https://github.com/nicsuzor/academicOps/issues/1140)) ([5515571](https://github.com/nicsuzor/academicOps/commit/5515571814867f4a5d6e3482f55a61be8f4fa46a))
- Deduplicate framework reflections across session continuations ([#1097](https://github.com/nicsuzor/academicOps/issues/1097)) ([f7f9eb0](https://github.com/nicsuzor/academicOps/commit/f7f9eb07d9dfd3b37695c3d9ee1f241313aa9cdf))
- **framework:** enforce intent+AC authoring convention for task bodies ([#1133](https://github.com/nicsuzor/academicOps/issues/1133)) ([09b672a](https://github.com/nicsuzor/academicOps/commit/09b672a71ffe485a9630ea3b26a50c60a6869132))
- **framework:** unify trust-the-worker authoring discipline ([#1138](https://github.com/nicsuzor/academicOps/issues/1138)) ([bff00e4](https://github.com/nicsuzor/academicOps/commit/bff00e42e8a85fa8da37d048bcff34fbf5d4d7dd))
- **junior:** reinforce anti-FM-1 instructions against 'Should I' tic ([#1131](https://github.com/nicsuzor/academicOps/issues/1131)) ([459c76f](https://github.com/nicsuzor/academicOps/commit/459c76fe607fc60655708d667cc2fe6214eac9f6))
- optimize basedpyright config to exclude non-Python files ([4091001](https://github.com/nicsuzor/academicOps/commit/4091001745416b14f4a33fff851a5544cd637792))
- **polecat:** route docker pull announce to stderr ([#1113](https://github.com/nicsuzor/academicOps/issues/1113)) ([7597893](https://github.com/nicsuzor/academicOps/commit/75978930e28b5d0897354dd81ba9c4750696f77f))
- resolve merge-prep workflow errors blocking PRs ([#1141](https://github.com/nicsuzor/academicOps/issues/1141)) ([33cbbb2](https://github.com/nicsuzor/academicOps/commit/33cbbb22e71e53a840c9544db4f0e6dab5f3920a))
- **survey:** tighten retro bump-comment guidance — delta only, no restatement ([#1088](https://github.com/nicsuzor/academicOps/issues/1088)) ([bbbd62b](https://github.com/nicsuzor/academicOps/commit/bbbd62bb273821cf4b633e7f021787270c5e2568))
- **transcript:** use local timezone for transcript session dates ([#1098](https://github.com/nicsuzor/academicOps/issues/1098)) ([19d6dde](https://github.com/nicsuzor/academicOps/commit/19d6dde45c2f6540d43aea0b04527aa1545ac969))

### Reverts

- **pyproject:** drop prototype-exclude smuggled into PR [#1119](https://github.com/nicsuzor/academicOps/issues/1119) ([0788263](https://github.com/nicsuzor/academicOps/commit/0788263cf3c522a7e03f881af0d1afd2be813c38))
- **pyproject:** drop scripts/*_prototype.py basedpyright exclude ([6749415](https://github.com/nicsuzor/academicOps/commit/6749415cae39e446b5a97c8aaa5991037fd2422a))

### Code Refactoring

- **survey:** simplify retro mode and remove rigid checklists ([#1101](https://github.com/nicsuzor/academicOps/issues/1101)) ([c1f2ffa](https://github.com/nicsuzor/academicOps/commit/c1f2ffa66dc71a6284a7a885920c93c2d5490af0))

### Documentation

- codify drive-by fix policy in SSoT ([#1135](https://github.com/nicsuzor/academicOps/issues/1135)) ([321b1ed](https://github.com/nicsuzor/academicOps/commit/321b1ed64b839d2ebc3895edeb1e3eef52825550))
- document transcript naming convention and discovery ([#1107](https://github.com/nicsuzor/academicOps/issues/1107)) ([581f278](https://github.com/nicsuzor/academicOps/commit/581f2784244be8b531fd8e1528fe2a551990d7c3))
- formalize policy on local sleep cycle auto-commits ([#1095](https://github.com/nicsuzor/academicOps/issues/1095)) ([f602548](https://github.com/nicsuzor/academicOps/commit/f60254848a423b8d72ff0cf3bee6cdeea4350277))
- **verify:** add Completeness-Verification Heuristic ([#1132](https://github.com/nicsuzor/academicOps/issues/1132)) ([c25d60d](https://github.com/nicsuzor/academicOps/commit/c25d60d9e53577a5617dd43043c8e2eb37e4ac4b))

### CI/CD

- add step-level timeouts for quick tests and fix typecheck ([30da8ad](https://github.com/nicsuzor/academicOps/commit/30da8ad07b8cc30c531c35a7b3cfc3113234a8ec))
- add step-level timeouts for quick tests and fix typecheck ([712abde](https://github.com/nicsuzor/academicOps/commit/712abde3a534d80de795083a31f4c778b1ba937c))
- capture reviewer agent transcripts ([#1108](https://github.com/nicsuzor/academicOps/issues/1108)) ([bacdc58](https://github.com/nicsuzor/academicOps/commit/bacdc58329e1cc79d8ca632259d34d183c052510)), closes [#166](https://github.com/nicsuzor/academicOps/issues/166)

### Miscellaneous

- exclude prototype files from type checking ([0a5f1a2](https://github.com/nicsuzor/academicOps/commit/0a5f1a268cb30f2e175f9b388ae58622fe43d32b))
- **ruleset:** disable Type Check required-check — explicit debt for burn-down (aops-1c3de214) ([0cc1384](https://github.com/nicsuzor/academicOps/commit/0cc138486277ec01aa80f12bb86981b3cc7feccd))
- **ruleset:** disable Type Check required-check — explicit debt for burn-down (aops-1c3de214) ([8aa0b6b](https://github.com/nicsuzor/academicOps/commit/8aa0b6b58d8bd2b97009862a020d996f5e6a50c7))

## [0.3.25](https://github.com/nicsuzor/academicOps/compare/v0.3.24...v0.3.25) (2026-05-16)

### Features

- **axioms:** split reviewer questions into AXIOMS-REVIEW.md ([a5058d0](https://github.com/nicsuzor/academicOps/commit/a5058d075724e96960d0bd0dbdbd3261a324da9f))
- **daily:** add human-action item coordinator ([797b0f8](https://github.com/nicsuzor/academicOps/commit/797b0f8821ad76c8269bc77c6afda94edbdce612))
- **daily:** add human-action item coordinator ([f84d533](https://github.com/nicsuzor/academicOps/commit/f84d533a1a05085a6d3f45e0215da2ed3ad72483))
- **diagram:** unified diagram skill replacing flowchart + excalidraw ([#967](https://github.com/nicsuzor/academicOps/issues/967)) ([e9d80ea](https://github.com/nicsuzor/academicOps/commit/e9d80ea40008a498334edfd42d16021ed36cf0d2))
- **enforcer:** migrate agent-enforcer.yml to v2 contract (Phase 1) ([69892d5](https://github.com/nicsuzor/academicOps/commit/69892d5d0eae8717095f029bae5785d27076834c))
- **enforcer:** migrate agent-enforcer.yml to v2 contract (Phase 1) ([d52db3b](https://github.com/nicsuzor/academicOps/commit/d52db3bff2f8804da732edb77d6a50e7886b4b2c))
- **extract:** absorb convert-to-md as docs-to-md route ([#966](https://github.com/nicsuzor/academicOps/issues/966)) ([654b0a5](https://github.com/nicsuzor/academicOps/commit/654b0a5a36e7fb25d520e924696078996407b381))
- implement auto-progress gate and autonomy tiers (A18) ([593782d](https://github.com/nicsuzor/academicOps/commit/593782ddf8482686c5348c142f2839ccbdf01a56))
- **install:** install aops-tools to local clients alongside aops-core ([#1053](https://github.com/nicsuzor/academicOps/issues/1053)) ([a7034f1](https://github.com/nicsuzor/academicOps/commit/a7034f16213b45eba011aa6cbc981cc5927d4cd2))
- **memory:** merge /remember + /sleep into unified memory skill ([82af014](https://github.com/nicsuzor/academicOps/commit/82af014ade8c2ff284d853dd022e8edf2900ec05))
- **memory:** merge /remember + /sleep into unified memory skill ([e10b044](https://github.com/nicsuzor/academicOps/commit/e10b044ef4ee02a877afdf0a31260d222f96ef98))
- **pkb:** enforce type-prefix-filename consistency in create_task ([#994](https://github.com/nicsuzor/academicOps/issues/994)) ([85766a6](https://github.com/nicsuzor/academicOps/commit/85766a63970dca308949f012739edd33c2aea8f0))
- **planner:** add interactive edge-wiring flow ([436966c](https://github.com/nicsuzor/academicOps/commit/436966c576ffb9432cd49d23251010c875d50ccf))
- **planner:** add interactive edge-wiring flow and Renooij-Witteman scale ([0829d8e](https://github.com/nicsuzor/academicOps/commit/0829d8eb8dcb964444cf49c54e1646bf4ab39c26))
- **polecat:** auto-finish orphaned worktrees when watchdog kills agent ([#1018](https://github.com/nicsuzor/academicOps/issues/1018)) ([5eda6ed](https://github.com/nicsuzor/academicOps/commit/5eda6ed1d0cc0b5d986d95ebf39991a5a2bbd70a))
- **polecat:** bypass watchdog kills for interactive/crew sessions and add telemetry ([#996](https://github.com/nicsuzor/academicOps/issues/996)) ([778565f](https://github.com/nicsuzor/academicOps/commit/778565fd0910718ec7fb588cdcec5a72ff67106e))
- **polecat:** implement mounts support, worker prompt verification, and pc finish error improvement ([fb1a1fa](https://github.com/nicsuzor/academicOps/commit/fb1a1fa48f9ac05a9e9231934706b9f004265e7e))
- **polecat:** implement mounts support, worker prompt verification, and pc finish error improvement ([f1ddb51](https://github.com/nicsuzor/academicOps/commit/f1ddb519941cf77bca02856eb065061bbec899c2))
- **pr-triage:** auto-bin classification and routing rules ([88c2d22](https://github.com/nicsuzor/academicOps/commit/88c2d22649ed1ddde485f6a68e222f915b56813e))
- **project:** provision canonical label set on repo init ([fcb7441](https://github.com/nicsuzor/academicOps/commit/fcb744124259298c8b796d1bd2d2c3a810cbe2a5))
- **project:** provision canonical label set on repo init ([e1ec695](https://github.com/nicsuzor/academicOps/commit/e1ec695df5d84e5a1a7d608d0c029dd845677be7))
- re-shape /learn toward systems-level findings ([#1006](https://github.com/nicsuzor/academicOps/issues/1006)) ([7dd7d72](https://github.com/nicsuzor/academicOps/commit/7dd7d72422ac59b001c9e1ac2186b2ee561261d8))
- **session-summary:** enrich metadata with surface/client/crew + subagent names ([ddb3200](https://github.com/nicsuzor/academicOps/commit/ddb32009dc961622fb07411f6ea59eedccdae6bc))
- **skills:** merge /critic into /strategic-review as mode=critic ([#965](https://github.com/nicsuzor/academicOps/issues/965)) ([08028d4](https://github.com/nicsuzor/academicOps/commit/08028d41c802cc856b4285568a2470b69784fd12))
- **skills:** replace /qa with bundled /verify skill (m:n dispatch) ([#968](https://github.com/nicsuzor/academicOps/issues/968)) ([774700d](https://github.com/nicsuzor/academicOps/commit/774700d7c73c8e62fcaeb33995ece0b423356e65))
- **supervisor:** add design-only preflight gate variant ([1db1c6c](https://github.com/nicsuzor/academicOps/commit/1db1c6c2710f18eada464677458ba19ff9d9afed))
- **supervisor:** add design-only preflight gate variant ([6e2dd87](https://github.com/nicsuzor/academicOps/commit/6e2dd87344c5cb2d709722ece27718e1e61d879c))
- **supervisor:** add Row 0 pre-flight check for open pr_url ([690027b](https://github.com/nicsuzor/academicOps/commit/690027b876b445ac17ad120fe37908a4d9002c3f))
- **survey:** merge /retro + /trend-review + /issue-sweep into unified /survey skill ([#972](https://github.com/nicsuzor/academicOps/issues/972)) ([ad938e4](https://github.com/nicsuzor/academicOps/commit/ad938e43b51467623fa70c8a179742578c3d3271))

### Bug Fixes

- address enforcer review feedback on apply_triage ([0f118e9](https://github.com/nicsuzor/academicOps/commit/0f118e977332a362e1b77af3b4f59b63e802d1b5))
- address nicsuzor review concerns more accurately ([6cbb684](https://github.com/nicsuzor/academicOps/commit/6cbb684e8e4297cc4432b37620786d64eabf67b2))
- address nicsuzor review feedback on supervisor/worker-dispatch ([59aeff8](https://github.com/nicsuzor/academicOps/commit/59aeff8edbd9c60f46fa30cfa048c50d9635ee7e))
- address review feedback ([27c9bd8](https://github.com/nicsuzor/academicOps/commit/27c9bd8906f48b5d87b2089985aed56938eb7691))
- address review feedback ([5324308](https://github.com/nicsuzor/academicOps/commit/5324308271311867e1d3f609ed5b61e42bd8a948))
- address review feedback + merge origin/main ([84a7212](https://github.com/nicsuzor/academicOps/commit/84a721233a97f0ad32a20eab4a31c944d3496ad4))
- address review feedback on auto-archive and CONFIRM format ([fcba325](https://github.com/nicsuzor/academicOps/commit/fcba325e1abe791eb89c02f13f41e1c70fb28f78))
- address review feedback on polecat trust framing ([565c154](https://github.com/nicsuzor/academicOps/commit/565c15481e61daa47a63e4a22d1c2a7a066f0a7d))
- address review feedback on supervisor SKILL.md ([5de03e5](https://github.com/nicsuzor/academicOps/commit/5de03e55a1419546bfe48da6e38d54b60220f720))
- **build:** strip H1 headers from inlined axioms content ([66b8b75](https://github.com/nicsuzor/academicOps/commit/66b8b758acdcce7e4065f4aa8f4db5fccb339d78))
- **ci:** eliminate merge-prep concurrency waste ([87f1eda](https://github.com/nicsuzor/academicOps/commit/87f1edaeba8693b5a07c5d2a3c5cd840c7f7e73e))
- **ci:** eliminate merge-prep concurrency waste ([5999cff](https://github.com/nicsuzor/academicOps/commit/5999cff97fe1e9d525172924949fb9075103b9b1))
- **ci:** gate initialize on same-repo, decouple lint from initialize ([245fed0](https://github.com/nicsuzor/academicOps/commit/245fed09c6f02e4869b3e5983b49c88178450252))
- **ci:** gate initialize on same-repo, decouple lint from initialize ([630423a](https://github.com/nicsuzor/academicOps/commit/630423a0c39e7b0661c4fbfceb9a6b0ad7edd4a7))
- correct broken INSTALL.md relative link in BUILD.md ([0c07bbb](https://github.com/nicsuzor/academicOps/commit/0c07bbb9d0783565a8c73c0890db03f3e47180b0))
- correct docstring — handover gate hard-fails, does not silently default ([06c31d9](https://github.com/nicsuzor/academicOps/commit/06c31d94de20d12ad957d06fca947fdf1868d613))
- correct review-dismissal API call in enforcer prompt ([7c80849](https://github.com/nicsuzor/academicOps/commit/7c80849c99f3a99fb7d5be180291447d295bf5d0))
- **daily:** log skip reasons for mobile captures ([44c8b34](https://github.com/nicsuzor/academicOps/commit/44c8b340322087fe2c30c92e681fce9ee2f38390))
- **docker:** tag aops-crew image under ghcr.io/nicsuzor namespace ([#955](https://github.com/nicsuzor/academicOps/issues/955)) ([c9bc184](https://github.com/nicsuzor/academicOps/commit/c9bc184768b55bf2862847d1c8298ac22c8b1221))
- drop project: example that contradicted Gate 3 and required body access ([258eee8](https://github.com/nicsuzor/academicOps/commit/258eee821b61d74dcbb519a93a32220c62a6bdba))
- **dump_pr_state:** label-edit failures no longer abort open_prs/recent_merged fetch ([be880d1](https://github.com/nicsuzor/academicOps/commit/be880d1607328b8a6482ae0ca539980644f06977))
- **dump_pr_state:** label-edit failures no longer abort open_prs/recent_merged fetch ([7f604e1](https://github.com/nicsuzor/academicOps/commit/7f604e1ecbd635c0bc90fb6d20ef40614555f3f3))
- **enforcer:** address nicsuzor review — update rbg.md capabilities and decouple enforcer framing ([100e450](https://github.com/nicsuzor/academicOps/commit/100e45092e2d3975d56c82f799897b9fb2c77d8f))
- **enforcer:** remove branches-ignore that prevented trigger on PRs to main ([a116f90](https://github.com/nicsuzor/academicOps/commit/a116f9096c7bc9297fb04acb71c9c4dde99ed615))
- **enforcer:** remove branches-ignore that prevented trigger on PRs to main ([1225d52](https://github.com/nicsuzor/academicOps/commit/1225d52112027784710a339c98cd418344c2da62))
- **enforcer:** remove unverified condition field; harden build fallback ([19e3822](https://github.com/nicsuzor/academicOps/commit/19e38227c56dcec200dc1874b79df6c3ce41899a))
- guard autonomy field access against null frontmatter ([7d3ae71](https://github.com/nicsuzor/academicOps/commit/7d3ae7141d02d8f62eb0822c4f8f9e26f186c197))
- guard backlog against overwrite; fix yaml.safe_load None crash ([b07b5dd](https://github.com/nicsuzor/academicOps/commit/b07b5dd0a46a84474f68a2a55cda34e9d11b3578))
- include 'to' in contributes_to canonical fields list ([dc70738](https://github.com/nicsuzor/academicOps/commit/dc707387c7df89a317cc81cd6d4a72737485e2b8))
- **install:** apply best-effort aops-tools pattern to install-gemini ([15dc517](https://github.com/nicsuzor/academicOps/commit/15dc51769e6fca3d805eec02a446333e4809ac25))
- **install:** tolerate missing aops-tools in dist marketplace ([9c35bdd](https://github.com/nicsuzor/academicOps/commit/9c35bdd1db618098dac75c16e123b36701d5481b))
- **install:** tolerate missing aops-tools in dist marketplace ([cc2df57](https://github.com/nicsuzor/academicOps/commit/cc2df575add7a9cc7a279431180933d32039062f))
- **issue-sweep:** reconcile step 5 with halt-after-one-cycle ([#829](https://github.com/nicsuzor/academicOps/issues/829)) ([6803eb9](https://github.com/nicsuzor/academicOps/commit/6803eb90453bf8edc28eb7e1945475a8e0b583d9))
- **make:** derive short tag from DOCKER_IMAGE via notdir ([21c93c3](https://github.com/nicsuzor/academicOps/commit/21c93c3134bc274124baa8d06796a225abfd8427))
- **make:** tag aops-crew image under both names on build ([7377dbc](https://github.com/nicsuzor/academicOps/commit/7377dbc809052f0aa85067ab9fe782dda829e1b9))
- **make:** tag aops-crew image under both names on build ([dd5f16b](https://github.com/nicsuzor/academicOps/commit/dd5f16b3a515576803bacdd943ec2ac619b91d0f))
- **memory:** correct procedures→references path in sub-agent dispatch example ([c2a5c79](https://github.com/nicsuzor/academicOps/commit/c2a5c79ee8920cbbe2f2f42e7eb4d977cdc7cdf2))
- **merge-prep:** fix SHA drift and per-PR concurrency hazards ([74599d1](https://github.com/nicsuzor/academicOps/commit/74599d1e1641441c6a8d32eb9675fc07a9857d62))
- **merge-prep:** fix SHA drift and per-PR concurrency hazards ([1de6f13](https://github.com/nicsuzor/academicOps/commit/1de6f1319a5bedf8f3a9e5ffcea41fb7835b6628))
- **merge-prep:** use consumer repo's default branch, not hardcoded 'main' ([182a88e](https://github.com/nicsuzor/academicOps/commit/182a88effd1506eb65546269c73dbb2bea6b182a))
- **merge-prep:** use consumer repo's default branch, not hardcoded 'main' ([2e3e5aa](https://github.com/nicsuzor/academicOps/commit/2e3e5aa471a974ea44091c693820729092306553))
- **planner:** add wire mode triggers to SKILL.md frontmatter ([1ac018d](https://github.com/nicsuzor/academicOps/commit/1ac018db5cdc1034d477a90899c827ab69be8273))
- **polecat:** label stale worktrees in polecat list via Docker liveness check ([#964](https://github.com/nicsuzor/academicOps/issues/964)) ([ea5efb9](https://github.com/nicsuzor/academicOps/commit/ea5efb9931d25238d0aa9a60247663b5ec961add))
- **polecat:** quiet-by-default output ([c394ac8](https://github.com/nicsuzor/academicOps/commit/c394ac8b3df12f92fdaab278de42a878acb5e0de))
- **polecat:** quiet-by-default output (suppress missing-project warnings + Docker noise) ([9e6dce1](https://github.com/nicsuzor/academicOps/commit/9e6dce1ea9e7995ef778902f5a5adcfb2f3126c1))
- **polecat:** robust reachability check in integrity gate ([#992](https://github.com/nicsuzor/academicOps/issues/992)) ([78796a2](https://github.com/nicsuzor/academicOps/commit/78796a29e1f45b2b678bb28c8f39ff3e50eafee6))
- **polecat:** use absolute imports and add entry point ([#1037](https://github.com/nicsuzor/academicOps/issues/1037)) ([62e0659](https://github.com/nicsuzor/academicOps/commit/62e0659be699edb8790087d08702cb3edad8fff3))
- prevent project name truncation in session transcripts ([#1031](https://github.com/nicsuzor/academicOps/issues/1031)) ([538005b](https://github.com/nicsuzor/academicOps/commit/538005b6ec15f9ea2437d09b1d49a4332e12d6b4))
- remove extant references to 'aops' as a binary (renamed to pkb) ([#963](https://github.com/nicsuzor/academicOps/issues/963)) ([7240001](https://github.com/nicsuzor/academicOps/commit/724000176b4ce0610e43d1273aef36b7453043e1))
- resolve project alias and use cfg-relative paths in mounts block ([266909f](https://github.com/nicsuzor/academicOps/commit/266909f0c957f2780da8e45e24ebf0b144e5ba7e))
- restore project-resolution-from-ancestors in both preflight variants ([4be9884](https://github.com/nicsuzor/academicOps/commit/4be9884aa043358eaf0f2e5d0b5877dea95e7113))
- simplify subprocess stderr handling with text=True; log actual command ([e5e7d08](https://github.com/nicsuzor/academicOps/commit/e5e7d08788c64c52f038aa1906751c923ea3a407))
- **sleep:** correct maintenance-phases.md path in backwards-compat stub ([3d45aee](https://github.com/nicsuzor/academicOps/commit/3d45aee070eab9efa48e31f3408acc3748511f52))
- **spec:** redact ts.net hostname from pr-pipeline-v2.md (A9/R4) ([0465435](https://github.com/nicsuzor/academicOps/commit/0465435cee53b737647da5ae3becf6ef7b418fba))
- **transcript:** skip empty hook payload blocks ([8f01bc8](https://github.com/nicsuzor/academicOps/commit/8f01bc875742cd7ecaa7f9a326ab9aebfe2daf49))
- trust polecats as full-judgment in-repo agents (GH [#957](https://github.com/nicsuzor/academicOps/issues/957)) ([f5ad384](https://github.com/nicsuzor/academicOps/commit/f5ad3848235b115e3b7ebe7855161dda2a3cfb56))
- **typecheck:** exclude tests/ from pyrightconfig.json and suppress reportUntypedBaseClass ([b3f7b0f](https://github.com/nicsuzor/academicOps/commit/b3f7b0fff5a7ac32e298fa43cd8da1cdd8a7a3f5))
- **typecheck:** resolve remaining possibly-unbound and argument-type errors ([308a3fe](https://github.com/nicsuzor/academicOps/commit/308a3fe1c22507c6f5a090c6abe81e71956abb16))
- **typecheck:** restore CI after pyrightconfig.json strict mode introduced by main ([97b9c61](https://github.com/nicsuzor/academicOps/commit/97b9c61ae31887caaea21359d7399e686a2eeb55))
- **typecheck:** simplify pyrightconfig.json exclude list ([0599cd6](https://github.com/nicsuzor/academicOps/commit/0599cd69597466090be49b340679b31f83ca61f9))
- **typecheck:** use correct basedpyright rule name and revert None initializations ([26ff05c](https://github.com/nicsuzor/academicOps/commit/26ff05c3c9765dda5debb284cfeb035cb26c1dd9))
- update polecat config for model fields ([b1ef756](https://github.com/nicsuzor/academicOps/commit/b1ef75609b7eff60aac20958039d011e70191512))
- **vocab:** align gate/lens/consolidate/audit usage in sleep and rbg ([#954](https://github.com/nicsuzor/academicOps/issues/954)) ([f1b7db2](https://github.com/nicsuzor/academicOps/commit/f1b7db202fbefc1742ba54c5511664c71434c94c))
- **worker-dispatch:** cite A4 source for User intent rationale ([33a1ace](https://github.com/nicsuzor/academicOps/commit/33a1ace24a317bc03300aad819cbec02218d54bb))
- **workers-md:** correct polecat.yaml citation to existing .example file ([a1bdee5](https://github.com/nicsuzor/academicOps/commit/a1bdee57c506fb7d1fa2a5b29883d697609e2f82))
- **workers-md:** remove unjustified 'claude only' routing guidance ([cf1f805](https://github.com/nicsuzor/academicOps/commit/cf1f8052de1741bf629bc06094299f536dc69ea6))

### Reverts

- drop A18 axiom and autonomy-tier infrastructure per review ([0c8f4d9](https://github.com/nicsuzor/academicOps/commit/0c8f4d95ebec51b391bf326ec5300f701fc1207e))

### Code Refactoring

- **ida:** compress stop-hook reminder to 3-sentence cue ([#958](https://github.com/nicsuzor/academicOps/issues/958)) ([6f4ede9](https://github.com/nicsuzor/academicOps/commit/6f4ede942cccc271d3922d6fe71be5e75e6fdbb1))
- **supervisor:** golden-path-first; shrink pre-flight gates ([8b6d819](https://github.com/nicsuzor/academicOps/commit/8b6d8197d58f3f76c92833dbb65e097511425589))
- **supervisor:** golden-path-first; shrink pre-flight gates ([61b10df](https://github.com/nicsuzor/academicOps/commit/61b10df27e37b8335251251e0fef386af7fa89ad))
- **transcript:** unify hook rendering across all event types ([6c9f869](https://github.com/nicsuzor/academicOps/commit/6c9f8692499fc76b6f617cad3f8613cc9f79babb))
- **transcript:** unify hook rendering across all event types ([4c3033c](https://github.com/nicsuzor/academicOps/commit/4c3033c04cb1841ef9eb306ce4f66e052283d01e))

### Documentation

- draft Trust Over Prescription heuristic ([#1055](https://github.com/nicsuzor/academicOps/issues/1055)) ([639d862](https://github.com/nicsuzor/academicOps/commit/639d8625e01a42c933649f21b8bae9f3d0ba2c64))
- **enforcement-map:** mark Phase 1 operative; regenerate agent matrix ([0fcb46d](https://github.com/nicsuzor/academicOps/commit/0fcb46d2cc0dbed6e8514547f88bb6ac9c3a3408))
- **taxonomy:** narrow project to polecat slug; collapse hierarchy; formalize contributes_to ([6d8f411](https://github.com/nicsuzor/academicOps/commit/6d8f41116e9b8fa24f6e8e68be8b9012018371c8))
- **taxonomy:** narrow project to polecat slug; collapse hierarchy; formalize contributes_to edges ([d381088](https://github.com/nicsuzor/academicOps/commit/d3810880a5586001e735c500c6aeb0f7e9073ca4))
- **taxonomy:** narrow project to polecat slug; collapse hierarchy; formalize contributes_to edges ([90fbaba](https://github.com/nicsuzor/academicOps/commit/90fbaba59ebce3fa526fcda216921f858aec66da))

### Tests

- update polecat.yaml fixtures for claude_model/gemini_model split ([f179d0e](https://github.com/nicsuzor/academicOps/commit/f179d0ec8404d5302794c07f4638a4952a61761e))

### Miscellaneous

- **main:** release 0.3.24 ([8faa85c](https://github.com/nicsuzor/academicOps/commit/8faa85c22aba0d32b9ee2d129d79e30048559e07))
- **main:** release 0.3.24 ([1549742](https://github.com/nicsuzor/academicOps/commit/15497427130ad96cde4d47f5856937a898cebbd4))
- remove lingering commit gate references ([3baf221](https://github.com/nicsuzor/academicOps/commit/3baf221bb415c83ca6d58daef91a71857994ded9))
- remove show_path.py references and progress-sync bloat ([77f06e4](https://github.com/nicsuzor/academicOps/commit/77f06e48c9808af355d2b87c5241c1106499e39b))
- **supervisor:** surface RBG axiom-check in Decompose phase ([93b09b6](https://github.com/nicsuzor/academicOps/commit/93b09b69cebd9c4adbe8f19173f1d6971bc64b31))
- **supervisor:** surface RBG axiom-check in Decompose phase table ([42bca83](https://github.com/nicsuzor/academicOps/commit/42bca8335e5841ac402db09c25c0bf578c33bc60))
- update uv.lock for release ([2399d4e](https://github.com/nicsuzor/academicOps/commit/2399d4e7942ba2db6a7b121f1fc89d6301f4aca8))

## [0.3.24](https://github.com/nicsuzor/academicOps/compare/v0.3.23...v0.3.24) (2026-05-16)

### Features

- **axioms:** split reviewer questions into AXIOMS-REVIEW.md ([a5058d0](https://github.com/nicsuzor/academicOps/commit/a5058d075724e96960d0bd0dbdbd3261a324da9f))
- **cron:** add raw PR-state dumper to repo-sync-cron ([#924](https://github.com/nicsuzor/academicOps/issues/924)) ([892911f](https://github.com/nicsuzor/academicOps/commit/892911ffe46a74187003a0ef00b6fb61115e652a))
- **daily:** add human-action item coordinator ([797b0f8](https://github.com/nicsuzor/academicOps/commit/797b0f8821ad76c8269bc77c6afda94edbdce612))
- **daily:** add human-action item coordinator ([f84d533](https://github.com/nicsuzor/academicOps/commit/f84d533a1a05085a6d3f45e0215da2ed3ad72483))
- **daily:** implement target-driven urgency grouping and badging ([#922](https://github.com/nicsuzor/academicOps/issues/922)) ([5aef997](https://github.com/nicsuzor/academicOps/commit/5aef997161fcc16caddcecbce367f42424fc5513))
- **diagram:** unified diagram skill replacing flowchart + excalidraw ([#967](https://github.com/nicsuzor/academicOps/issues/967)) ([e9d80ea](https://github.com/nicsuzor/academicOps/commit/e9d80ea40008a498334edfd42d16021ed36cf0d2))
- **enforcer:** migrate agent-enforcer.yml to v2 contract (Phase 1) ([69892d5](https://github.com/nicsuzor/academicOps/commit/69892d5d0eae8717095f029bae5785d27076834c))
- **enforcer:** migrate agent-enforcer.yml to v2 contract (Phase 1) ([d52db3b](https://github.com/nicsuzor/academicOps/commit/d52db3bff2f8804da732edb77d6a50e7886b4b2c))
- **extract:** absorb convert-to-md as docs-to-md route ([#966](https://github.com/nicsuzor/academicOps/issues/966)) ([654b0a5](https://github.com/nicsuzor/academicOps/commit/654b0a5a36e7fb25d520e924696078996407b381))
- implement auto-progress gate and autonomy tiers (A18) ([593782d](https://github.com/nicsuzor/academicOps/commit/593782ddf8482686c5348c142f2839ccbdf01a56))
- **install:** install aops-tools to local clients alongside aops-core ([#1053](https://github.com/nicsuzor/academicOps/issues/1053)) ([a7034f1](https://github.com/nicsuzor/academicOps/commit/a7034f16213b45eba011aa6cbc981cc5927d4cd2))
- **memory:** merge /remember + /sleep into unified memory skill ([82af014](https://github.com/nicsuzor/academicOps/commit/82af014ade8c2ff284d853dd022e8edf2900ec05))
- **memory:** merge /remember + /sleep into unified memory skill ([e10b044](https://github.com/nicsuzor/academicOps/commit/e10b044ef4ee02a877afdf0a31260d222f96ef98))
- **pkb:** enforce type-prefix-filename consistency in create_task ([#994](https://github.com/nicsuzor/academicOps/issues/994)) ([85766a6](https://github.com/nicsuzor/academicOps/commit/85766a63970dca308949f012739edd33c2aea8f0))
- **planner:** add interactive edge-wiring flow ([436966c](https://github.com/nicsuzor/academicOps/commit/436966c576ffb9432cd49d23251010c875d50ccf))
- **planner:** add interactive edge-wiring flow and Renooij-Witteman scale ([0829d8e](https://github.com/nicsuzor/academicOps/commit/0829d8eb8dcb964444cf49c54e1646bf4ab39c26))
- **polecat:** auto-finish orphaned worktrees when watchdog kills agent ([#1018](https://github.com/nicsuzor/academicOps/issues/1018)) ([5eda6ed](https://github.com/nicsuzor/academicOps/commit/5eda6ed1d0cc0b5d986d95ebf39991a5a2bbd70a))
- **polecat:** bypass watchdog kills for interactive/crew sessions and add telemetry ([#996](https://github.com/nicsuzor/academicOps/issues/996)) ([778565f](https://github.com/nicsuzor/academicOps/commit/778565fd0910718ec7fb588cdcec5a72ff67106e))
- **polecat:** consolidate session config into polecat.yaml SSoT ([#921](https://github.com/nicsuzor/academicOps/issues/921)) ([042e0fb](https://github.com/nicsuzor/academicOps/commit/042e0fb15286d312d961809364a246cb533f0c52))
- **polecat:** implement mounts support, worker prompt verification, and pc finish error improvement ([fb1a1fa](https://github.com/nicsuzor/academicOps/commit/fb1a1fa48f9ac05a9e9231934706b9f004265e7e))
- **polecat:** implement mounts support, worker prompt verification, and pc finish error improvement ([f1ddb51](https://github.com/nicsuzor/academicOps/commit/f1ddb519941cf77bca02856eb065061bbec899c2))
- **pr-triage:** auto-bin classification and routing rules ([88c2d22](https://github.com/nicsuzor/academicOps/commit/88c2d22649ed1ddde485f6a68e222f915b56813e))
- **project:** provision canonical label set on repo init ([fcb7441](https://github.com/nicsuzor/academicOps/commit/fcb744124259298c8b796d1bd2d2c3a810cbe2a5))
- **project:** provision canonical label set on repo init ([e1ec695](https://github.com/nicsuzor/academicOps/commit/e1ec695df5d84e5a1a7d608d0c029dd845677be7))
- re-shape /learn toward systems-level findings ([#1006](https://github.com/nicsuzor/academicOps/issues/1006)) ([7dd7d72](https://github.com/nicsuzor/academicOps/commit/7dd7d72422ac59b001c9e1ac2186b2ee561261d8))
- **session-summary:** enrich metadata with surface/client/crew + subagent names ([ddb3200](https://github.com/nicsuzor/academicOps/commit/ddb32009dc961622fb07411f6ea59eedccdae6bc))
- **skills:** merge /critic into /strategic-review as mode=critic ([#965](https://github.com/nicsuzor/academicOps/issues/965)) ([08028d4](https://github.com/nicsuzor/academicOps/commit/08028d41c802cc856b4285568a2470b69784fd12))
- **skills:** replace /qa with bundled /verify skill (m:n dispatch) ([#968](https://github.com/nicsuzor/academicOps/issues/968)) ([774700d](https://github.com/nicsuzor/academicOps/commit/774700d7c73c8e62fcaeb33995ece0b423356e65))
- **supervisor:** add design-only preflight gate variant ([1db1c6c](https://github.com/nicsuzor/academicOps/commit/1db1c6c2710f18eada464677458ba19ff9d9afed))
- **supervisor:** add design-only preflight gate variant ([6e2dd87](https://github.com/nicsuzor/academicOps/commit/6e2dd87344c5cb2d709722ece27718e1e61d879c))
- **supervisor:** add Row 0 pre-flight check for open pr_url ([690027b](https://github.com/nicsuzor/academicOps/commit/690027b876b445ac17ad120fe37908a4d9002c3f))
- **supervisor:** v2 — stateless tick + subagent contracts (aops-c5cfa714) ([e0c7533](https://github.com/nicsuzor/academicOps/commit/e0c753387a3c5002fb89a5263e90cc25780dcf64))
- **survey:** merge /retro + /trend-review + /issue-sweep into unified /survey skill ([#972](https://github.com/nicsuzor/academicOps/issues/972)) ([ad938e4](https://github.com/nicsuzor/academicOps/commit/ad938e43b51467623fa70c8a179742578c3d3271))
- **transcript_parser:** add attention counters to per-session summary ([cc82384](https://github.com/nicsuzor/academicOps/commit/cc82384e7c20aebb4b81b07a042b95e1dc2c4743))
- **transcript_parser:** attention counters + reviewer verdicts (Safeguard ROI v0 Builds A + B) ([81cacb8](https://github.com/nicsuzor/academicOps/commit/81cacb80d781e29bd16db7d802c913ec016cfce7))
- **transcript_parser:** per-invocation reviewer verdicts in session summary ([ecbee6e](https://github.com/nicsuzor/academicOps/commit/ecbee6e0398ac03f117b7b502b64241692a48f00))

### Bug Fixes

- address enforcer review feedback on apply_triage ([0f118e9](https://github.com/nicsuzor/academicOps/commit/0f118e977332a362e1b77af3b4f59b63e802d1b5))
- address nicsuzor review concerns more accurately ([6cbb684](https://github.com/nicsuzor/academicOps/commit/6cbb684e8e4297cc4432b37620786d64eabf67b2))
- address nicsuzor review feedback on supervisor/worker-dispatch ([59aeff8](https://github.com/nicsuzor/academicOps/commit/59aeff8edbd9c60f46fa30cfa048c50d9635ee7e))
- address review feedback ([27c9bd8](https://github.com/nicsuzor/academicOps/commit/27c9bd8906f48b5d87b2089985aed56938eb7691))
- address review feedback ([5324308](https://github.com/nicsuzor/academicOps/commit/5324308271311867e1d3f609ed5b61e42bd8a948))
- address review feedback + merge origin/main ([84a7212](https://github.com/nicsuzor/academicOps/commit/84a721233a97f0ad32a20eab4a31c944d3496ad4))
- address review feedback on auto-archive and CONFIRM format ([fcba325](https://github.com/nicsuzor/academicOps/commit/fcba325e1abe791eb89c02f13f41e1c70fb28f78))
- address review feedback on polecat trust framing ([565c154](https://github.com/nicsuzor/academicOps/commit/565c15481e61daa47a63e4a22d1c2a7a066f0a7d))
- address review feedback on supervisor SKILL.md ([5de03e5](https://github.com/nicsuzor/academicOps/commit/5de03e55a1419546bfe48da6e38d54b60220f720))
- **build:** apply short-name rule generically, not as named-instance dict ([f5f8dce](https://github.com/nicsuzor/academicOps/commit/f5f8dce8ba3477ee6c93d9dde266ccb33455ba47))
- **build:** promote zipfile to module-level import ([c216794](https://github.com/nicsuzor/academicOps/commit/c216794b84fd9675a59c93f3ab89533d835108a2))
- **build:** strip H1 headers from inlined axioms content ([66b8b75](https://github.com/nicsuzor/academicOps/commit/66b8b758acdcce7e4065f4aa8f4db5fccb339d78))
- **ci:** eliminate merge-prep concurrency waste ([87f1eda](https://github.com/nicsuzor/academicOps/commit/87f1edaeba8693b5a07c5d2a3c5cd840c7f7e73e))
- **ci:** eliminate merge-prep concurrency waste ([5999cff](https://github.com/nicsuzor/academicOps/commit/5999cff97fe1e9d525172924949fb9075103b9b1))
- **ci:** gate initialize on same-repo, decouple lint from initialize ([245fed0](https://github.com/nicsuzor/academicOps/commit/245fed09c6f02e4869b3e5983b49c88178450252))
- **ci:** gate initialize on same-repo, decouple lint from initialize ([630423a](https://github.com/nicsuzor/academicOps/commit/630423a0c39e7b0661c4fbfceb9a6b0ad7edd4a7))
- correct broken INSTALL.md relative link in BUILD.md ([0c07bbb](https://github.com/nicsuzor/academicOps/commit/0c07bbb9d0783565a8c73c0890db03f3e47180b0))
- correct review-dismissal API call in enforcer prompt ([7c80849](https://github.com/nicsuzor/academicOps/commit/7c80849c99f3a99fb7d5be180291447d295bf5d0))
- **daily:** log skip reasons for mobile captures ([44c8b34](https://github.com/nicsuzor/academicOps/commit/44c8b340322087fe2c30c92e681fce9ee2f38390))
- **docker:** tag aops-crew image under ghcr.io/nicsuzor namespace ([#955](https://github.com/nicsuzor/academicOps/issues/955)) ([c9bc184](https://github.com/nicsuzor/academicOps/commit/c9bc184768b55bf2862847d1c8298ac22c8b1221))
- **docs:** Jr → Junior in CORE.md Core Agents table ([6f2254a](https://github.com/nicsuzor/academicOps/commit/6f2254a4141293b9b19578891e9a3eade2284304))
- drop project: example that contradicted Gate 3 and required body access ([258eee8](https://github.com/nicsuzor/academicOps/commit/258eee821b61d74dcbb519a93a32220c62a6bdba))
- **dump_pr_state:** label-edit failures no longer abort open_prs/recent_merged fetch ([be880d1](https://github.com/nicsuzor/academicOps/commit/be880d1607328b8a6482ae0ca539980644f06977))
- **dump_pr_state:** label-edit failures no longer abort open_prs/recent_merged fetch ([7f604e1](https://github.com/nicsuzor/academicOps/commit/7f604e1ecbd635c0bc90fb6d20ef40614555f3f3))
- **enforcer:** address nicsuzor review — update rbg.md capabilities and decouple enforcer framing ([100e450](https://github.com/nicsuzor/academicOps/commit/100e45092e2d3975d56c82f799897b9fb2c77d8f))
- **enforcer:** remove branches-ignore that prevented trigger on PRs to main ([a116f90](https://github.com/nicsuzor/academicOps/commit/a116f9096c7bc9297fb04acb71c9c4dde99ed615))
- **enforcer:** remove branches-ignore that prevented trigger on PRs to main ([1225d52](https://github.com/nicsuzor/academicOps/commit/1225d52112027784710a339c98cd418344c2da62))
- **enforcer:** remove unverified condition field; harden build fallback ([19e3822](https://github.com/nicsuzor/academicOps/commit/19e38227c56dcec200dc1874b79df6c3ce41899a))
- **env:** kill silent fallback defaults; enforce A8 in pre-commit ([#931](https://github.com/nicsuzor/academicOps/issues/931)) ([7c35283](https://github.com/nicsuzor/academicOps/commit/7c3528315b368661a6aa4c4d95f6180614589f48))
- guard autonomy field access against null frontmatter ([7d3ae71](https://github.com/nicsuzor/academicOps/commit/7d3ae7141d02d8f62eb0822c4f8f9e26f186c197))
- guard backlog against overwrite; fix yaml.safe_load None crash ([b07b5dd](https://github.com/nicsuzor/academicOps/commit/b07b5dd0a46a84474f68a2a55cda34e9d11b3578))
- include 'to' in contributes_to canonical fields list ([dc70738](https://github.com/nicsuzor/academicOps/commit/dc707387c7df89a317cc81cd6d4a72737485e2b8))
- **install:** apply best-effort aops-tools pattern to install-gemini ([15dc517](https://github.com/nicsuzor/academicOps/commit/15dc51769e6fca3d805eec02a446333e4809ac25))
- **install:** tolerate missing aops-tools in dist marketplace ([9c35bdd](https://github.com/nicsuzor/academicOps/commit/9c35bdd1db618098dac75c16e123b36701d5481b))
- **install:** tolerate missing aops-tools in dist marketplace ([cc2df57](https://github.com/nicsuzor/academicOps/commit/cc2df575add7a9cc7a279431180933d32039062f))
- **issue-sweep:** reconcile step 5 with halt-after-one-cycle ([#829](https://github.com/nicsuzor/academicOps/issues/829)) ([6803eb9](https://github.com/nicsuzor/academicOps/commit/6803eb90453bf8edc28eb7e1945475a8e0b583d9))
- **make:** derive short tag from DOCKER_IMAGE via notdir ([21c93c3](https://github.com/nicsuzor/academicOps/commit/21c93c3134bc274124baa8d06796a225abfd8427))
- **make:** tag aops-crew image under both names on build ([7377dbc](https://github.com/nicsuzor/academicOps/commit/7377dbc809052f0aa85067ab9fe782dda829e1b9))
- **make:** tag aops-crew image under both names on build ([dd5f16b](https://github.com/nicsuzor/academicOps/commit/dd5f16b3a515576803bacdd943ec2ac619b91d0f))
- **memory:** correct procedures→references path in sub-agent dispatch example ([c2a5c79](https://github.com/nicsuzor/academicOps/commit/c2a5c79ee8920cbbe2f2f42e7eb4d977cdc7cdf2))
- **merge-prep:** fix SHA drift and per-PR concurrency hazards ([74599d1](https://github.com/nicsuzor/academicOps/commit/74599d1e1641441c6a8d32eb9675fc07a9857d62))
- **merge-prep:** fix SHA drift and per-PR concurrency hazards ([1de6f13](https://github.com/nicsuzor/academicOps/commit/1de6f1319a5bedf8f3a9e5ffcea41fb7835b6628))
- **merge-prep:** use consumer repo's default branch, not hardcoded 'main' ([182a88e](https://github.com/nicsuzor/academicOps/commit/182a88effd1506eb65546269c73dbb2bea6b182a))
- **merge-prep:** use consumer repo's default branch, not hardcoded 'main' ([2e3e5aa](https://github.com/nicsuzor/academicOps/commit/2e3e5aa471a974ea44091c693820729092306553))
- **planner:** add wire mode triggers to SKILL.md frontmatter ([1ac018d](https://github.com/nicsuzor/academicOps/commit/1ac018db5cdc1034d477a90899c827ab69be8273))
- **polecat:** distinguish watchdog SIGKILL from OOM in exit-137 reporting ([#919](https://github.com/nicsuzor/academicOps/issues/919)) ([f14d395](https://github.com/nicsuzor/academicOps/commit/f14d395d37592927a2aa598c1f9f202da16602b6))
- **polecat:** label stale worktrees in polecat list via Docker liveness check ([#964](https://github.com/nicsuzor/academicOps/issues/964)) ([ea5efb9](https://github.com/nicsuzor/academicOps/commit/ea5efb9931d25238d0aa9a60247663b5ec961add))
- **polecat:** quiet-by-default output ([c394ac8](https://github.com/nicsuzor/academicOps/commit/c394ac8b3df12f92fdaab278de42a878acb5e0de))
- **polecat:** quiet-by-default output (suppress missing-project warnings + Docker noise) ([9e6dce1](https://github.com/nicsuzor/academicOps/commit/9e6dce1ea9e7995ef778902f5a5adcfb2f3126c1))
- **polecat:** robust reachability check in integrity gate ([#992](https://github.com/nicsuzor/academicOps/issues/992)) ([78796a2](https://github.com/nicsuzor/academicOps/commit/78796a29e1f45b2b678bb28c8f39ff3e50eafee6))
- **polecat:** use absolute imports and add entry point ([#1037](https://github.com/nicsuzor/academicOps/issues/1037)) ([62e0659](https://github.com/nicsuzor/academicOps/commit/62e0659be699edb8790087d08702cb3edad8fff3))
- prevent project name truncation in session transcripts ([#1031](https://github.com/nicsuzor/academicOps/issues/1031)) ([538005b](https://github.com/nicsuzor/academicOps/commit/538005b6ec15f9ea2437d09b1d49a4332e12d6b4))
- remove extant references to 'aops' as a binary (renamed to pkb) ([#963](https://github.com/nicsuzor/academicOps/issues/963)) ([7240001](https://github.com/nicsuzor/academicOps/commit/724000176b4ce0610e43d1273aef36b7453043e1))
- remove orphaned method calls and improve user-message detection ([5a117e5](https://github.com/nicsuzor/academicOps/commit/5a117e5e1e98668f8706b928a4844b0bc7cbac6e))
- resolve merge conflict — accept main's hook removal in router.py ([f341b6d](https://github.com/nicsuzor/academicOps/commit/f341b6d85b89fcbca57d0e07d1219a6da3bf9db3))
- resolve project alias and use cfg-relative paths in mounts block ([266909f](https://github.com/nicsuzor/academicOps/commit/266909f0c957f2780da8e45e24ebf0b144e5ba7e))
- restore project-resolution-from-ancestors in both preflight variants ([4be9884](https://github.com/nicsuzor/academicOps/commit/4be9884aa043358eaf0f2e5d0b5877dea95e7113))
- simplify subprocess stderr handling with text=True; log actual command ([e5e7d08](https://github.com/nicsuzor/academicOps/commit/e5e7d08788c64c52f038aa1906751c923ea3a407))
- **sleep:** correct maintenance-phases.md path in backwards-compat stub ([3d45aee](https://github.com/nicsuzor/academicOps/commit/3d45aee070eab9efa48e31f3408acc3748511f52))
- **spec:** redact ts.net hostname from pr-pipeline-v2.md (A9/R4) ([0465435](https://github.com/nicsuzor/academicOps/commit/0465435cee53b737647da5ae3becf6ef7b418fba))
- **transcript_parser:** eliminate duplicate _estimate_tokens implementation ([b1765b7](https://github.com/nicsuzor/academicOps/commit/b1765b74be324cba7a24f9aacfa7a40e01ea0f8d))
- **transcript:** skip empty hook payload blocks ([8f01bc8](https://github.com/nicsuzor/academicOps/commit/8f01bc875742cd7ecaa7f9a326ab9aebfe2daf49))
- **transcript:** structured verdict markers, per-tool tokens, condense Hook header ([4675a65](https://github.com/nicsuzor/academicOps/commit/4675a65f2225e5ded37a145b5ce35475e0bfdec7))
- trust polecats as full-judgment in-repo agents (GH [#957](https://github.com/nicsuzor/academicOps/issues/957)) ([f5ad384](https://github.com/nicsuzor/academicOps/commit/f5ad3848235b115e3b7ebe7855161dda2a3cfb56))
- **typecheck:** exclude tests/ from pyrightconfig.json and suppress reportUntypedBaseClass ([b3f7b0f](https://github.com/nicsuzor/academicOps/commit/b3f7b0fff5a7ac32e298fa43cd8da1cdd8a7a3f5))
- **typecheck:** resolve remaining possibly-unbound and argument-type errors ([308a3fe](https://github.com/nicsuzor/academicOps/commit/308a3fe1c22507c6f5a090c6abe81e71956abb16))
- **typecheck:** restore CI after pyrightconfig.json strict mode introduced by main ([97b9c61](https://github.com/nicsuzor/academicOps/commit/97b9c61ae31887caaea21359d7399e686a2eeb55))
- **typecheck:** simplify pyrightconfig.json exclude list ([0599cd6](https://github.com/nicsuzor/academicOps/commit/0599cd69597466090be49b340679b31f83ca61f9))
- **typecheck:** use correct basedpyright rule name and revert None initializations ([26ff05c](https://github.com/nicsuzor/academicOps/commit/26ff05c3c9765dda5debb284cfeb035cb26c1dd9))
- update polecat config for model fields ([b1ef756](https://github.com/nicsuzor/academicOps/commit/b1ef75609b7eff60aac20958039d011e70191512))
- **vocab:** align gate/lens/consolidate/audit usage in sleep and rbg ([#954](https://github.com/nicsuzor/academicOps/issues/954)) ([f1b7db2](https://github.com/nicsuzor/academicOps/commit/f1b7db202fbefc1742ba54c5511664c71434c94c))
- **worker-dispatch:** cite A4 source for User intent rationale ([33a1ace](https://github.com/nicsuzor/academicOps/commit/33a1ace24a317bc03300aad819cbec02218d54bb))
- **workers-md:** correct polecat.yaml citation to existing .example file ([a1bdee5](https://github.com/nicsuzor/academicOps/commit/a1bdee57c506fb7d1fa2a5b29883d697609e2f82))
- **workers-md:** remove unjustified 'claude only' routing guidance ([cf1f805](https://github.com/nicsuzor/academicOps/commit/cf1f8052de1741bf629bc06094299f536dc69ea6))

### Reverts

- drop A18 axiom and autonomy-tier infrastructure per review ([0c8f4d9](https://github.com/nicsuzor/academicOps/commit/0c8f4d95ebec51b391bf326ec5300f701fc1207e))

### Code Refactoring

- **ida:** compress stop-hook reminder to 3-sentence cue ([#958](https://github.com/nicsuzor/academicOps/issues/958)) ([6f4ede9](https://github.com/nicsuzor/academicOps/commit/6f4ede942cccc271d3922d6fe71be5e75e6fdbb1))
- **supervisor:** golden-path-first; shrink pre-flight gates ([8b6d819](https://github.com/nicsuzor/academicOps/commit/8b6d8197d58f3f76c92833dbb65e097511425589))
- **supervisor:** golden-path-first; shrink pre-flight gates ([61b10df](https://github.com/nicsuzor/academicOps/commit/61b10df27e37b8335251251e0fef386af7fa89ad))
- **transcript:** unify hook rendering across all event types ([6c9f869](https://github.com/nicsuzor/academicOps/commit/6c9f8692499fc76b6f617cad3f8613cc9f79babb))
- **transcript:** unify hook rendering across all event types ([4c3033c](https://github.com/nicsuzor/academicOps/commit/4c3033c04cb1841ef9eb306ce4f66e052283d01e))

### Documentation

- draft Trust Over Prescription heuristic ([#1055](https://github.com/nicsuzor/academicOps/issues/1055)) ([639d862](https://github.com/nicsuzor/academicOps/commit/639d8625e01a42c933649f21b8bae9f3d0ba2c64))
- **enforcement-map:** mark Phase 1 operative; regenerate agent matrix ([0fcb46d](https://github.com/nicsuzor/academicOps/commit/0fcb46d2cc0dbed6e8514547f88bb6ac9c3a3408))
- **taxonomy:** narrow project to polecat slug; collapse hierarchy; formalize contributes_to ([6d8f411](https://github.com/nicsuzor/academicOps/commit/6d8f41116e9b8fa24f6e8e68be8b9012018371c8))
- **taxonomy:** narrow project to polecat slug; collapse hierarchy; formalize contributes_to edges ([d381088](https://github.com/nicsuzor/academicOps/commit/d3810880a5586001e735c500c6aeb0f7e9073ca4))
- **taxonomy:** narrow project to polecat slug; collapse hierarchy; formalize contributes_to edges ([90fbaba](https://github.com/nicsuzor/academicOps/commit/90fbaba59ebce3fa526fcda216921f858aec66da))

### Build System

- package Cowork plugin as upload-ready zip, drop install-cowork target ([44a9103](https://github.com/nicsuzor/academicOps/commit/44a9103c5e6e1ee10bbab0109470a7f33a7e523f))

### Tests

- drop test_build_cowork_includes; update remaining cowork refs ([db92a4c](https://github.com/nicsuzor/academicOps/commit/db92a4cb9e2827508dad62e244a06109d328e8ad))
- update polecat.yaml fixtures for claude_model/gemini_model split ([f179d0e](https://github.com/nicsuzor/academicOps/commit/f179d0ec8404d5302794c07f4638a4952a61761e))

### Miscellaneous

- **pr-state:** strip fields no consumer reads (10592→3218 lines) ([0d37cc5](https://github.com/nicsuzor/academicOps/commit/0d37cc54b3e8fcc15a116e39f65a7fb0154652d9))
- **pr-state:** strip fields no consumer reads (10592→3218 lines) ([c007f54](https://github.com/nicsuzor/academicOps/commit/c007f54c6ea630d734a861e3252569077e14afcc))
- remove show_path.py references and progress-sync bloat ([77f06e4](https://github.com/nicsuzor/academicOps/commit/77f06e48c9808af355d2b87c5241c1106499e39b))
- **supervisor:** surface RBG axiom-check in Decompose phase ([93b09b6](https://github.com/nicsuzor/academicOps/commit/93b09b69cebd9c4adbe8f19173f1d6971bc64b31))
- **supervisor:** surface RBG axiom-check in Decompose phase table ([42bca83](https://github.com/nicsuzor/academicOps/commit/42bca8335e5841ac402db09c25c0bf578c33bc60))

## [0.3.23](https://github.com/nicsuzor/academicOps/compare/v0.3.22...v0.3.23) (2026-05-05)

### Features

- **sleep:** /sleep loop-close — Phase 6 + Phase 7 additions (Part B of dispatch improvements) ([#909](https://github.com/nicsuzor/academicOps/issues/909)) ([0cce5bb](https://github.com/nicsuzor/academicOps/commit/0cce5bb7c73049d83d1ee6886e3f00a31eaefbf1))
- **supervisor:** pre-flight confirmation summary (Part A of dispatch improvements) ([#908](https://github.com/nicsuzor/academicOps/issues/908)) ([d6667ac](https://github.com/nicsuzor/academicOps/commit/d6667ac8f8dcb471cc5e9d5c8c74270902e0a685))

### Bug Fixes

- address review feedback + merge main ([22ce15a](https://github.com/nicsuzor/academicOps/commit/22ce15ac973f294024375bbfe0941d4f8912ff75))
- **gates:** remove orchestrator_boundary refs left by delete-dispositor ([fb7e02b](https://github.com/nicsuzor/academicOps/commit/fb7e02b94c1041b9c5bc21248130ebb22b8134b9))
- **polecat:** drop CI=true for gemini crew so REPL stays interactive ([41bb286](https://github.com/nicsuzor/academicOps/commit/41bb286d037660381553f50daaf9dd83a110fbdf))
- **polecat:** launch gemini crew with --approval-mode=yolo, not plan ([b6ef88c](https://github.com/nicsuzor/academicOps/commit/b6ef88c256311f79819fb29002af199ae418c86c))
- **router:** remove fallback logic from output_for_gemini deny path ([af221a4](https://github.com/nicsuzor/academicOps/commit/af221a43dfbb53c73a316dcf25f7464ab4803a2d))
- **router:** surface deny-branch context_injection to gemini model ([421a7cc](https://github.com/nicsuzor/academicOps/commit/421a7cc2797467d0bf94e36df287be4b1d428f1f))
- **transcripts,hooks:** parse gemini chat-jsonl + route deny recovery to model ([88682f0](https://github.com/nicsuzor/academicOps/commit/88682f0480301e1cec10e3acfce08fd4a49dc95d))
- **transcripts,hooks:** parse gemini chat-jsonl + route deny recovery to model ([44c8791](https://github.com/nicsuzor/academicOps/commit/44c87914ac25a0b9079284d83add1e9b719cd926))

### Build System

- **cowork:** trim aops-cowork to RO dispatch surface ([#910](https://github.com/nicsuzor/academicOps/issues/910)) ([28bb396](https://github.com/nicsuzor/academicOps/commit/28bb39695700ef17feafc0d78b8382a952c6cc6e))

## [0.3.22](https://github.com/nicsuzor/academicOps/compare/v0.3.21...v0.3.22) (2026-05-04)

### Features

- **commands:** add /issue-sweep — quality-gated GitHub issue triage ([#820](https://github.com/nicsuzor/academicOps/issues/820)) ([a2ad9a1](https://github.com/nicsuzor/academicOps/commit/a2ad9a1844663356ae9cf3eaf72b24a679517bb5))
- **core:** point agents at PKB specs first ([#876](https://github.com/nicsuzor/academicOps/issues/876)) ([05e4e0d](https://github.com/nicsuzor/academicOps/commit/05e4e0d19f8571a964bfc46eebc6aa96f521f39a))
- **cowork:** implement Cowork audit log ingestion and normalization ([#776](https://github.com/nicsuzor/academicOps/issues/776)) ([1972b2b](https://github.com/nicsuzor/academicOps/commit/1972b2bedf307e36825b7b72310714a1d898112c))
- **docker:** trust extension and config folders in worker image ([#757](https://github.com/nicsuzor/academicOps/issues/757)) ([3bfb227](https://github.com/nicsuzor/academicOps/commit/3bfb22744c2237e169748f491f4e02bd55019303))
- **dump,transcript:** require framework reflection + output link + tasks-worked list ([#855](https://github.com/nicsuzor/academicOps/issues/855)) ([19fc612](https://github.com/nicsuzor/academicOps/commit/19fc612307132fb0b0e65fcb0988ce2b83ec871e))
- **dump:** cross-reference current epic in project file ([#825](https://github.com/nicsuzor/academicOps/issues/825)) ([7465931](https://github.com/nicsuzor/academicOps/commit/7465931198b06a0e1a30d32601b968c178a6679c))
- **enforcer:** block (not defer) PRs that add gates without updating enforcement-map (Closes [#803](https://github.com/nicsuzor/academicOps/issues/803)) ([#859](https://github.com/nicsuzor/academicOps/issues/859)) ([d429d67](https://github.com/nicsuzor/academicOps/commit/d429d67052c36d3167e172da03568f8ebd1ac1ba))
- **epic-319a8797:** Phase A — handoff architecture + RBG surgery ([ed6abc8](https://github.com/nicsuzor/academicOps/commit/ed6abc8ff183c6a62496778ec824e2b83a773885))
- **epic-319a8797:** Phase B — supervisor template generalisation ([417adf3](https://github.com/nicsuzor/academicOps/commit/417adf3f05049abf4e2dffa5d1455cc93ff68a6a))
- **heuristics:** age is not a staleness signal — garden surfaces, never cancels (Closes [#185](https://github.com/nicsuzor/academicOps/issues/185)) ([#860](https://github.com/nicsuzor/academicOps/issues/860)) ([f5c5f83](https://github.com/nicsuzor/academicOps/commit/f5c5f839cc920b804836e5f2b7632b26fae2ad14))
- **heuristics:** age is not a staleness signal ([#837](https://github.com/nicsuzor/academicOps/issues/837)) ([4a7907e](https://github.com/nicsuzor/academicOps/commit/4a7907e39b20894eb8b024651d74227e9a81f54f))
- **hooks:** log client_type to distinguish claude vs gemini sessions (Closes task-c5d2e2da) ([#867](https://github.com/nicsuzor/academicOps/issues/867)) ([944c833](https://github.com/nicsuzor/academicOps/commit/944c83338d9c0ac1e499e774e2cd8ff038d3c6b9))
- **maintain:** /maintain anti-inflation surface + /daily SEV4 warning ([#879](https://github.com/nicsuzor/academicOps/issues/879)) ([c375600](https://github.com/nicsuzor/academicOps/commit/c3756009f1ab10cff86bb549c16f184fe5f25994))
- **mcp:** standardise transport on HTTP/SSE for non-local targets ([#781](https://github.com/nicsuzor/academicOps/issues/781)) ([f0bf332](https://github.com/nicsuzor/academicOps/commit/f0bf332f5df12faed68a69a942313ee41c630dbd))
- **observability:** improve session JSON metadata for downstream analytics ([e88995e](https://github.com/nicsuzor/academicOps/commit/e88995ef689b3ff435ff0309c7d0e39479ecdf2a))
- **observability:** improve session JSON metadata for downstream analytics ([8f393f5](https://github.com/nicsuzor/academicOps/commit/8f393f50cddb2736f7ec23b230bff7a580255bae))
- **observability:** session ID alignment + naming + git-sync (P3 group, 5 tasks) ([#858](https://github.com/nicsuzor/academicOps/issues/858)) ([6abcfdf](https://github.com/nicsuzor/academicOps/commit/6abcfdfd5181a0faaa182d1d0ac30c4696192d46))
- **planner:** add decision-surfacing heuristic to teach DECIDE/DEFER/SURFACE classification ([#818](https://github.com/nicsuzor/academicOps/issues/818)) ([81d4b71](https://github.com/nicsuzor/academicOps/commit/81d4b71ca3f288681e2e886679eebacaf1aee2a9))
- **planner:** default new tasks to P3 unless user signals urgency ([#842](https://github.com/nicsuzor/academicOps/issues/842)) ([43e8fba](https://github.com/nicsuzor/academicOps/commit/43e8fba40b4fc331aacb3ac988bc326cad99a1af))
- **polecat:** add --force flag to run command ([#861](https://github.com/nicsuzor/academicOps/issues/861)) ([1432558](https://github.com/nicsuzor/academicOps/commit/1432558f818e39b6339deba6b10e9da9871e68a5))
- **polecat:** CLI/lifecycle polish — --force, sweep removal, lifecycle stubs, transcript surfacing ([#850](https://github.com/nicsuzor/academicOps/issues/850)) ([e5b5962](https://github.com/nicsuzor/academicOps/commit/e5b5962cae63dae80bf571c9bbff3f675ef281d5))
- **polecat:** remove sweep subcommand — supervisor handles PR-state directly ([#868](https://github.com/nicsuzor/academicOps/issues/868)) ([3e7a4ad](https://github.com/nicsuzor/academicOps/commit/3e7a4ade3da7af929268d181a4c37189fa75cf15))
- **polecat:** surface real transcript path in task body and PR ([#872](https://github.com/nicsuzor/academicOps/issues/872)) ([146a182](https://github.com/nicsuzor/academicOps/commit/146a1826b7342602bc5668030868034f49f6de74))
- **pull:** dispatch to specialist agent when assignee names one (Closes [#733](https://github.com/nicsuzor/academicOps/issues/733)) ([#857](https://github.com/nicsuzor/academicOps/issues/857)) ([21091d3](https://github.com/nicsuzor/academicOps/commit/21091d3e4984afb412dec38229e16e7eedbed03f))
- **rbg:** A2 class-coverage check + structured exemption schema (Closes epic-e1ddba21, refs [#794](https://github.com/nicsuzor/academicOps/issues/794), [#811](https://github.com/nicsuzor/academicOps/issues/811)) ([#878](https://github.com/nicsuzor/academicOps/issues/878)) ([bf79450](https://github.com/nicsuzor/academicOps/commit/bf79450abd080b448cf56ff9ae7efab274168837))
- **rules:** R5.6 — no new orphan markdown + pre-commit gate ([#793](https://github.com/nicsuzor/academicOps/issues/793)) ([dc8917a](https://github.com/nicsuzor/academicOps/commit/dc8917ac79b812332893956c84deb620e9a9833a))
- **sessions:** align task ID across all session-artifact filenames ([#882](https://github.com/nicsuzor/academicOps/issues/882)) ([5886669](https://github.com/nicsuzor/academicOps/commit/58866699863af2dbb8da120a0c205882bafdfec9))
- **skills:** /daily and /pull consume urgency signal (task-0e12ef8d) ([#846](https://github.com/nicsuzor/academicOps/issues/846)) ([153a595](https://github.com/nicsuzor/academicOps/commit/153a5954ed8458bea9814f6078ba4233e59c8b82))
- **skills:** /maintain anti-inflation surface for graph hygiene ([#848](https://github.com/nicsuzor/academicOps/issues/848)) ([b037723](https://github.com/nicsuzor/academicOps/commit/b0377235a3af5dc1ac7cb61f8276291f3827a32a))
- **sleep:** mode-aware pacing with brain auto-merge ([#712](https://github.com/nicsuzor/academicOps/issues/712)) ([#833](https://github.com/nicsuzor/academicOps/issues/833)) ([3844ed3](https://github.com/nicsuzor/academicOps/commit/3844ed35c1491a20435207ac737f45271edae7a7))
- **supervisor,rbg:** A8 composition-time enforcement ([#877](https://github.com/nicsuzor/academicOps/issues/877)) ([754ab07](https://github.com/nicsuzor/academicOps/commit/754ab07428db867ec003a8b9827bb5411ea96de5))
- **supervisor:** add WORKERS.md worker registry ([#828](https://github.com/nicsuzor/academicOps/issues/828)) ([eee2f7e](https://github.com/nicsuzor/academicOps/commit/eee2f7e4b89500d88d90dc2179ca5f7761a135d7))
- **transcript:** surface injected/read context in Session Context section (Closes task-8b3e3cfd) ([#875](https://github.com/nicsuzor/academicOps/issues/875)) ([e9cbae2](https://github.com/nicsuzor/academicOps/commit/e9cbae251b47e347541b745939e00d444e9aa3af))

### Bug Fixes

- add skip guard to Propagate agent exit status step ([a78c50c](https://github.com/nicsuzor/academicOps/commit/a78c50cbfaf3c98b257bc2f938908e3bdeccb71c))
- **agents:** add PKB write tools and normalise frontmatter schema ([#639](https://github.com/nicsuzor/academicOps/issues/639), [#679](https://github.com/nicsuzor/academicOps/issues/679)) ([b78b052](https://github.com/nicsuzor/academicOps/commit/b78b052eb33b1203d0b66c5d1158118403eea972))
- **agents:** add PKB write tools and normalise frontmatter schema ([#639](https://github.com/nicsuzor/academicOps/issues/639), [#679](https://github.com/nicsuzor/academicOps/issues/679)) ([eadee0e](https://github.com/nicsuzor/academicOps/commit/eadee0e9ef38e6f416d0d09253305b38786c4aee))
- **cron:** tie sync_gha_sessions.py into the local transcript cron ([#766](https://github.com/nicsuzor/academicOps/issues/766)) ([2742df3](https://github.com/nicsuzor/academicOps/commit/2742df325b1572465b59ba1e3103e32655a3fa30)), closes [#765](https://github.com/nicsuzor/academicOps/issues/765)
- **daily:** anchor day-of-week and work-date on today's calendar date ([75dfaae](https://github.com/nicsuzor/academicOps/commit/75dfaaeddec2d32e3e8863e97d168f09028fb63e))
- **daily:** anchor day-of-week and work-date on today's calendar date ([#759](https://github.com/nicsuzor/academicOps/issues/759)) ([62faf20](https://github.com/nicsuzor/academicOps/commit/62faf20ddd7f733863ffbc66a4f4b92907634925))
- **daily:** read completion signals before regenerating ([#847](https://github.com/nicsuzor/academicOps/issues/847)) ([3b20deb](https://github.com/nicsuzor/academicOps/commit/3b20debf9fafb35e7368350b2519edd4d5548cc2))
- **enforcer:** pin academicOps checkout to pipeline-v1 ([45753d2](https://github.com/nicsuzor/academicOps/commit/45753d2d920e9da455d7daeadb3eb1b2abce962e))
- **enforcer:** pin academicOps checkout to pipeline-v1 ([1df278d](https://github.com/nicsuzor/academicOps/commit/1df278dd31ddbdaaf582b8da12786335951a4ae9))
- **hooks,e2e:** polecat-aware paths + e2e fixture corrections ([#788](https://github.com/nicsuzor/academicOps/issues/788)) ([9380549](https://github.com/nicsuzor/academicOps/commit/9380549e657814058e09267381c92c89415d7d02))
- **hooks:** point periodic-enforcer at aops-core:rbg ([#817](https://github.com/nicsuzor/academicOps/issues/817)) ([#832](https://github.com/nicsuzor/academicOps/issues/832)) ([5c054e7](https://github.com/nicsuzor/academicOps/commit/5c054e77341729bd12ad3d3c73dc52d25c85abb3))
- **mcp:** resolve PKB_MCP_URL in run-mcp.sh, drop broken env block ([7f82976](https://github.com/nicsuzor/academicOps/commit/7f8297693e57f08485ef3ac650e4763a105668b2))
- **merge-prep-cron:** drop reserved GITHUB_TOKEN from workflow_call secrets ([b6008a6](https://github.com/nicsuzor/academicOps/commit/b6008a65add9919302fceae2752e42e7ec1f2c9c))
- **merge-prep-cron:** hoist defaults out of job-level env to fix workflow_run trigger ([#792](https://github.com/nicsuzor/academicOps/issues/792)) ([079958b](https://github.com/nicsuzor/academicOps/commit/079958b83cb0a26cbdf7eb442fcea6bfc4f15b4b))
- **merge-prep:** load prompt from academicOps, not caller's repo ([cc011a9](https://github.com/nicsuzor/academicOps/commit/cc011a9b55e2f991d63c5da9ff1845fb34dc2c5f))
- **merge-prep:** load prompt from academicOps, not caller's repo ([0b920b5](https://github.com/nicsuzor/academicOps/commit/0b920b5057ef54eb1ff9e4e25fc52a8f3f2eed02))
- **observability:** add is_error to tool_call dedup key ([eb2a3ef](https://github.com/nicsuzor/academicOps/commit/eb2a3efce3a42ae2d5f6f1806950cbccea305bb8))
- **orchestrator-boundary:** scope dispositor reminder to brain repo only ([#805](https://github.com/nicsuzor/academicOps/issues/805)) ([41ba536](https://github.com/nicsuzor/academicOps/commit/41ba5362f3ab4b40f14ed16a59dcd8dfa56e9e76))
- **p65:** update enforcement map for rbg surgery + user-side cron ([afc8b8e](https://github.com/nicsuzor/academicOps/commit/afc8b8ebde6fb985a9df1db50313e2b73c3925c7))
- **p65:** update ENFORCEMENT-MAP for new rbg enforcement gates added in PR [#896](https://github.com/nicsuzor/academicOps/issues/896) ([980a071](https://github.com/nicsuzor/academicOps/commit/980a071b58ffa740c3646687590ca7d7344f7477))
- **p65:** update ENFORCEMENT-MAP for PR [#895](https://github.com/nicsuzor/academicOps/issues/895) revert changes ([78cb298](https://github.com/nicsuzor/academicOps/commit/78cb2987f8e10b0ff154f72f21119203563edada))
- **pkb-mcp:** declare deps via PEP 723 so uv resolves them at launch ([#813](https://github.com/nicsuzor/academicOps/issues/813)) ([12295b2](https://github.com/nicsuzor/academicOps/commit/12295b220935d064b71e9f71a9cd8b13804d63a7))
- **pkb:** default new tasks to priority 3 instead of 2 (task-2b01a9e4) ([#851](https://github.com/nicsuzor/academicOps/issues/851)) ([b9018a2](https://github.com/nicsuzor/academicOps/commit/b9018a2e79ec649d11d9848ff04a17611f640612))
- **planner:** consult CORE.md Component Topology before parent assignment (Closes [#663](https://github.com/nicsuzor/academicOps/issues/663)) ([#835](https://github.com/nicsuzor/academicOps/issues/835)) ([38aab93](https://github.com/nicsuzor/academicOps/commit/38aab9308d1bd2af9147c3305bae11ad0eca05bb))
- **planner:** externalise follow-up action items as separate linked tasks (Closes [#582](https://github.com/nicsuzor/academicOps/issues/582)) ([#838](https://github.com/nicsuzor/academicOps/issues/838)) ([bc38d2e](https://github.com/nicsuzor/academicOps/commit/bc38d2e1803e8e9b563d06e235afffd17a0a6dfe))
- **polecat:** add Step 0 pre-push gate-recheck to worker template ([#583](https://github.com/nicsuzor/academicOps/issues/583)) ([#831](https://github.com/nicsuzor/academicOps/issues/831)) ([5a8e9b9](https://github.com/nicsuzor/academicOps/commit/5a8e9b950b37b8f0b67ce154ca2b9fa83dec92b6))
- **polecat:** collapse 6 hardcoded forwarding blocks into agent-env-map.conf SSoT ([#824](https://github.com/nicsuzor/academicOps/issues/824)) ([ffbd572](https://github.com/nicsuzor/academicOps/commit/ffbd5723464c323f675e74b9125712343d185f14))
- **polecat:** replace literal — escape with actual em-dash in comment ([9e10c38](https://github.com/nicsuzor/academicOps/commit/9e10c38964737da17c297cccf3dad9383e556ba1))
- **polecat:** retry pkb_bridge `_post` once on chunked-read TimeoutError (aops-aaa98cf7) ([#852](https://github.com/nicsuzor/academicOps/issues/852)) ([000e247](https://github.com/nicsuzor/academicOps/commit/000e2476cdbe8a43e7beba24c9a5fa34ea873a03))
- **polecat:** robust docker binary resolution + accurate command-not-found message ([2adcffa](https://github.com/nicsuzor/academicOps/commit/2adcffa219f76a4116948a69afc3d4f6d9c234c7))
- **polecat:** robust docker binary resolution + accurate FileNotFoundError message ([db71cd9](https://github.com/nicsuzor/academicOps/commit/db71cd9df3f2b4c031dc0934cbe0c7aee12033a7))
- **policies:** use gemini snake_case tool names in deny-extension-writes.toml ([608ce59](https://github.com/nicsuzor/academicOps/commit/608ce597315aa93e25be3da9f1065c11c847106a))
- **rbg:** criterion-substitution + unverified-keystone + sensitive-data scan ([#853](https://github.com/nicsuzor/academicOps/issues/853)) ([3c88fe9](https://github.com/nicsuzor/academicOps/commit/3c88fe93fce82bd2ac081a2cc9a0218d71f15356))
- **rbg:** restore required sections removed by [#891](https://github.com/nicsuzor/academicOps/issues/891) RBG surgery ([dfcff2c](https://github.com/nicsuzor/academicOps/commit/dfcff2c71099ed1f2f9c01e98e9ff64cef94fca1))
- resolve merge conflicts with main (PR [#891](https://github.com/nicsuzor/academicOps/issues/891) RBG surgery) ([13fc07c](https://github.com/nicsuzor/academicOps/commit/13fc07c2bcb933d26effc0aeb70b0d6c67a35c0d))
- restore load-bearing sections in rbg.md stripped by clean-up commit ([38282ae](https://github.com/nicsuzor/academicOps/commit/38282aee09e788f0285d3edadf3cbfece9a35ba2))
- restore rbg.md full content to keep test suite green ([c036209](https://github.com/nicsuzor/academicOps/commit/c036209dc2e2ce2bccb157af54d78578f20addd0))
- **review:** disclose polecat 401 auth issue in run_judge comment ([0b48a1d](https://github.com/nicsuzor/academicOps/commit/0b48a1dc23069b7e0ef35e6c218c255a9e20dc72))
- **scripts:** move re import to module level in transcript.py ([b98f22f](https://github.com/nicsuzor/academicOps/commit/b98f22f6bf266cda3a5127fe916a50280cfbd251))
- **session-writer:** dedupe timeline_events to prevent double-recording (Closes task-955f405d) ([#864](https://github.com/nicsuzor/academicOps/issues/864)) ([5268c30](https://github.com/nicsuzor/academicOps/commit/5268c3002bf73f9db9156da8a240c42a4fd8c606))
- **session-writer:** resolve worktree paths to main repo (Closes task-ea880699) ([#862](https://github.com/nicsuzor/academicOps/issues/862)) ([b576cba](https://github.com/nicsuzor/academicOps/commit/b576cbab3b2780e67a95b2743a8a8f66b340d9e8))
- **sessions:** fix 00:00 filename collision for date-only strings ([#753](https://github.com/nicsuzor/academicOps/issues/753)) ([6d4ca56](https://github.com/nicsuzor/academicOps/commit/6d4ca568216bc24a47177d0e1b59ba0c9650dcf1))
- **sessions:** unify per-session artefact paths; provider in filename ([#903](https://github.com/nicsuzor/academicOps/issues/903)) ([8d2f93e](https://github.com/nicsuzor/academicOps/commit/8d2f93e36896f067a81081487d6756fac27af4f7))
- **sleep:** attach PKB MCP toolset to Phase 2/4 sub-agents ([#841](https://github.com/nicsuzor/academicOps/issues/841)) ([411aec9](https://github.com/nicsuzor/academicOps/commit/411aec913b2184c373d1676a3e02fe1607d39875))
- stop RBG enforcer running when no PR is found on workflow_run ([111741c](https://github.com/nicsuzor/academicOps/commit/111741c791e340d57f9d29c5ead6cf6f06394272))
- stop RBG enforcer running when no PR is found on workflow_run ([1641b20](https://github.com/nicsuzor/academicOps/commit/1641b203f04761ecfc6a724ca818d25d4dcb93d6))
- **supervisor:** halt on infeasible dispatch — never silently swap worker types ([#827](https://github.com/nicsuzor/academicOps/issues/827)) ([d9c0cf2](https://github.com/nicsuzor/academicOps/commit/d9c0cf24820dd20b757364a762da004da20c6e16)), closes [#643](https://github.com/nicsuzor/academicOps/issues/643)
- **supervisor:** mandatory host-check + ping-pkb gate for dispatch reliability ([#836](https://github.com/nicsuzor/academicOps/issues/836)) ([ff8af50](https://github.com/nicsuzor/academicOps/commit/ff8af50c771b9566c10506cf32a29ee894cfba6d))
- **tests:** F-group fixture race in temp_polecat_home ([#856](https://github.com/nicsuzor/academicOps/issues/856)) ([cce05af](https://github.com/nicsuzor/academicOps/commit/cce05aff982ac3969c93a78003a7d2f55b0fcdc9))
- **test:** update `_extract_section` to stop at new ### Hook: per-turn rendering ([c4e439d](https://github.com/nicsuzor/academicOps/commit/c4e439d44f2b7fd3e7dc9a19e87c674ad4b32a47))
- **test:** update rbg tools test for PR [#895](https://github.com/nicsuzor/academicOps/issues/895) architectural change ([46b2e99](https://github.com/nicsuzor/academicOps/commit/46b2e990796550d693ad4b76ac28d05299f41fb9))
- **transcript:** read hook gate results from CanonicalHookOutput.output (Closes task-fc938187) ([28dda57](https://github.com/nicsuzor/academicOps/commit/28dda5735f698331c725593b95115a80c45a782a))
- **transcript:** refresh insights JSON when source jsonl grows ([#764](https://github.com/nicsuzor/academicOps/issues/764)) ([9ec17de](https://github.com/nicsuzor/academicOps/commit/9ec17de52430d880853dfba8b22199721aa7db22))
- **transcript:** render hook verdicts/messages in session markdown ([3b067b2](https://github.com/nicsuzor/academicOps/commit/3b067b24541eb88593e3d2847d4c46b5ee989d17))
- **transcript:** respect full_mode in standalone hook message truncation ([06db00c](https://github.com/nicsuzor/academicOps/commit/06db00cd8d184d572d7bba108f5fa25b88960f2a))
- use complete_task for rbg verdicts; add regression test (P[#82](https://github.com/nicsuzor/academicOps/issues/82)) ([2a10429](https://github.com/nicsuzor/academicOps/commit/2a104294dd449b23f4c2ee73b1f9bef275b142b3))

### Reverts

- **epic-319a8797:** remove cron, GHA label workflow, RBG case-law ([2c0bdf3](https://github.com/nicsuzor/academicOps/commit/2c0bdf31d907885040614598810c7655b2a5163e))
- **epic-319a8797:** remove cron, GHA label workflow, RBG case-law ([9bc02e8](https://github.com/nicsuzor/academicOps/commit/9bc02e8e9e3780ba5094a6b457c5df57d7897dec))

### Code Refactoring

- **config:** projects.yaml as SSoT; drop polecat.yaml ([#799](https://github.com/nicsuzor/academicOps/issues/799)) ([a873edb](https://github.com/nicsuzor/academicOps/commit/a873edb0ad5c148b1ba6b8cadb2d088f8f38eddc))
- **insights:** remove dead prompt-loader functions (Closes task-83932f98) ([#871](https://github.com/nicsuzor/academicOps/issues/871)) ([03a2ef9](https://github.com/nicsuzor/academicOps/commit/03a2ef9e1b5fe47756def9c1b696a82f24d5a7e8))
- **polecat:** consolidate claim + extract finalize, remove `_sync_working_repo` from dispatch (Step 2 of Polecat v2 epic-4234682b) ([#884](https://github.com/nicsuzor/academicOps/issues/884)) ([1b99a6a](https://github.com/nicsuzor/academicOps/commit/1b99a6a59ae1dc6674973ed53222b09284818afb))
- **polecat:** extract swarm/watch/analyze/reset_stalled/summary into modules (Step 1 of Polecat v2 epic-4234682b) ([#880](https://github.com/nicsuzor/academicOps/issues/880)) ([af28012](https://github.com/nicsuzor/academicOps/commit/af28012c34b3763d23e13ca9929d443944f442d8))
- **transcript:** remove dead shim, deduplicate `_keep_hook` predicate ([583e3ab](https://github.com/nicsuzor/academicOps/commit/583e3ab8a634d4efae7cfb26dd5b3cc222cb25ed))

### Documentation

- Add Playwright MCP to tool capabilities section ([f5a6510](https://github.com/nicsuzor/academicOps/commit/f5a651025662a4d99649c5225822c4b87f7cb3cb))
- Add tool capabilities reference for dispatched sessions ([dfc9dec](https://github.com/nicsuzor/academicOps/commit/dfc9dec4f943e9d8e3ec8e8d5d480fe00679c5e3))
- align surfaces to focus_score as primary ranking signal (task-d997a904) ([6434528](https://github.com/nicsuzor/academicOps/commit/64345282069b846ce1d114541019596235b16438))
- **planner:** default new tasks to P3 unless user indicates urgency (Closes task-e410b794) ([#873](https://github.com/nicsuzor/academicOps/issues/873)) ([f29c59a](https://github.com/nicsuzor/academicOps/commit/f29c59a33edad518c5f5624a5eebc2898de72696))
- **polecat:** align spec with reality + drop out-of-date crew merge section ([#769](https://github.com/nicsuzor/academicOps/issues/769)) ([39ea6fc](https://github.com/nicsuzor/academicOps/commit/39ea6fc62df0dfb5a55597e05cd256e3dfc0ad9c))
- **priority:** canonical P0–P4 definitions ([#840](https://github.com/nicsuzor/academicOps/issues/840)) ([8a39ffe](https://github.com/nicsuzor/academicOps/commit/8a39ffe5baf201833cd65c68390fac6a2aec6928))
- **priority:** canonicalize P0–P4 in TAXONOMY ([#863](https://github.com/nicsuzor/academicOps/issues/863)) ([c8c9a92](https://github.com/nicsuzor/academicOps/commit/c8c9a9262adb38abe0b87a1c529b8770067bf8ae))
- reference list_tasks project filter in skill bodies (Closes task-3dfb97b5) ([#870](https://github.com/nicsuzor/academicOps/issues/870)) ([3689ee1](https://github.com/nicsuzor/academicOps/commit/3689ee1ae331aa5810ac7543de2eff1cce9f915c))
- reference new list_tasks project filter in skills ([#849](https://github.com/nicsuzor/academicOps/issues/849)) ([b135754](https://github.com/nicsuzor/academicOps/commit/b1357542c6cf072df07e7668da13938c09da7169))
- **remember:** clarify confidence is numeric and synthesized/sources required for knowledge (partial Closes task-2e8b1498) ([#883](https://github.com/nicsuzor/academicOps/issues/883)) ([bbbc038](https://github.com/nicsuzor/academicOps/commit/bbbc03850faffcb0a159cf24b5a8defef1eeabd8))
- remove stale references to non-existent session-insights skill (Closes task-c5fa4dd6) ([#869](https://github.com/nicsuzor/academicOps/issues/869)) ([22c846d](https://github.com/nicsuzor/academicOps/commit/22c846d444d474d49328ffd6340817c3b6cb6ff5))
- **supervisor:** document manual merge-prep trigger to skip bazaar wait ([#830](https://github.com/nicsuzor/academicOps/issues/830)) ([1b9e498](https://github.com/nicsuzor/academicOps/commit/1b9e498aaa15a938168647fe477329787c110082))
- **supervisor:** document uv run form for polecat in non-interactive shells ([#826](https://github.com/nicsuzor/academicOps/issues/826)) ([148ff21](https://github.com/nicsuzor/academicOps/commit/148ff218d231458676b304c5b5fdf3054435349d)), closes [#618](https://github.com/nicsuzor/academicOps/issues/618)

### Tests

- **gemini:** pin PKB MCP config; add non-PR persistence E2E; capability matrix ([#787](https://github.com/nicsuzor/academicOps/issues/787)) ([a1ee0ec](https://github.com/nicsuzor/academicOps/commit/a1ee0ecd77dadfeab00de93304cc6c5bd5c05b87))
- **polecat:** parametrise transcript-persistence e2e for Gemini variant ([#881](https://github.com/nicsuzor/academicOps/issues/881)) ([efa5442](https://github.com/nicsuzor/academicOps/commit/efa5442f5a991bd777b29a0b87ad24ea72c1de0e))
- **transcript:** add test coverage for thoughts/thinking rendering (task-df03f1d9) ([#874](https://github.com/nicsuzor/academicOps/issues/874)) ([fbddbd7](https://github.com/nicsuzor/academicOps/commit/fbddbd78a6188a81545f99fcb19af298fdecf476))

### Miscellaneous

- add timeout-minutes: 45 to all GHA jobs ([#772](https://github.com/nicsuzor/academicOps/issues/772)) ([d806b00](https://github.com/nicsuzor/academicOps/commit/d806b0087a7112f40917e42cf06c108bb7a27544))
- **epic-319a8797:** remove seed marker on integration ([2b2dd4b](https://github.com/nicsuzor/academicOps/commit/2b2dd4be8430059fda8a96f27294ad6fec85d733))
- **epic-319a8797:** seed shared branch for coordinated dispatch ([7745f9b](https://github.com/nicsuzor/academicOps/commit/7745f9bdb34a4efa4c467f5a6e6dcd89450ae96e))
- move plugin manifests to templates/ to remove client-confusion vectors ([#796](https://github.com/nicsuzor/academicOps/issues/796)) ([6303e8e](https://github.com/nicsuzor/academicOps/commit/6303e8e20da7869507c02c71963156802adbb407))
- **pkb:** remove downstream_weight from academicOps surfaces (task-412c3443) ([6f13da1](https://github.com/nicsuzor/academicOps/commit/6f13da1fcb94b8ab279e8fd0fd9cafd1bc50358f))
- **pkb:** replace user-facing downstream_weight with urgency (task-412c3443) ([4ca842c](https://github.com/nicsuzor/academicOps/commit/4ca842c9e313dc94cf0d94510cc870218d4cabc4))
- stop packaging project-local CORE.md into plugin distributions ([#783](https://github.com/nicsuzor/academicOps/issues/783)) ([79d4faa](https://github.com/nicsuzor/academicOps/commit/79d4faa64e18fa5eacef66fba87876b3cd03f738))

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
