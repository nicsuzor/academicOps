# Changelog

## [0.3.80](https://github.com/nicsuzor/academicOps/compare/v0.3.79...v0.3.80) (2026-07-21)


### Features

* add install-cowork-windows target, fix empty-username silent skip ([#2265](https://github.com/nicsuzor/academicOps/issues/2265)) ([7b38529](https://github.com/nicsuzor/academicOps/commit/7b385298a53e23d85eb0c35920bb69727ca878aa))
* **agents:** add add-rule skill; wire CLAUDE.md into .agents/CORE.md ([ddb0cb7](https://github.com/nicsuzor/academicOps/commit/ddb0cb7ed662757f067ded758f50903e95971e39))
* **agents:** add agent-side capability & constraint map ([#2298](https://github.com/nicsuzor/academicOps/issues/2298)) ([3e59596](https://github.com/nicsuzor/academicOps/commit/3e59596acca6a5cc94df04bec04105c7c2199502))
* **aops-jr:** extract polecat CLI and dispatch skill into standalone coordinator plugin ([44aef03](https://github.com/nicsuzor/academicOps/commit/44aef037195f05b0d092e549a5bd82f4633a050f))
* **aops-jr:** wire into build/marketplace pipeline; record debug + packaging decisions ([#2272](https://github.com/nicsuzor/academicOps/issues/2272)) ([0c31d08](https://github.com/nicsuzor/academicOps/commit/0c31d088835d16db50d784f22188659da82e6ced))
* **aops:** add aops:debug skill for interactive polecat debugging ([44c5e0d](https://github.com/nicsuzor/academicOps/commit/44c5e0d4de763b041641b336de86ec8445ed4bb8))
* **daily:** reconceive daily note within consolidated cognitive-prosthesis layer ([d56c211](https://github.com/nicsuzor/academicOps/commit/d56c2115f7d16a76aef4ad29cbc7b3ca68f1302b))
* **daily:** reconceive daily note within consolidated cognitive-prosthesis layer (supersedes [#2293](https://github.com/nicsuzor/academicOps/issues/2293)) ([05795ad](https://github.com/nicsuzor/academicOps/commit/05795ad396100531600962711548e378eab5642b))
* **hooks:** minimal function-per-gate hook/gate system ([#2248](https://github.com/nicsuzor/academicOps/issues/2248)) ([2828481](https://github.com/nicsuzor/academicOps/commit/2828481680eae5e4e346d16a70750bde7b934aa6))
* **polecat:** forward options/prompts through to inner agent, default --task to /pull ([65cc921](https://github.com/nicsuzor/academicOps/commit/65cc921e3bd26ef8b0fcffde43d821b5a5ecff0e))
* **transcripts:** Claude adapter wrapping claude-code-log + tolerant loader + contract/snapshot tests ([0babfce](https://github.com/nicsuzor/academicOps/commit/0babfce975a4ce7f918bc8e952909a2c5f9218fe))
* **transcripts:** implement Layer B domain modules, runner, cron script, and specs ([c5e6097](https://github.com/nicsuzor/academicOps/commit/c5e60974764112b7bfdf18be27c8ce2f75eba3c2))
* **transcripts:** implement Layer B domain modules, runner, cron script, and specs ([d53a76f](https://github.com/nicsuzor/academicOps/commit/d53a76f16be32abc0dd6644aea3bbf77ccdfb433))
* **transcripts:** implement normalized model and agy adapter behind uniform interface ([#2267](https://github.com/nicsuzor/academicOps/issues/2267)) ([ae1144e](https://github.com/nicsuzor/academicOps/commit/ae1144e6d7bd3779c1b166b2e7ea2d5e6ef957bd))
* **workflows:** format Markdown files and clean whitespace ([5fc3189](https://github.com/nicsuzor/academicOps/commit/5fc31898fb2301421178e7827cb67fb0d304c6f2))
* **workflows:** implement PKB workflow-template discovery/loading for pauli decompose ([21f6031](https://github.com/nicsuzor/academicOps/commit/21f6031a0a1c4adff5571843d0ec61d4a1a6f0f0))
* **workflows:** implement PKB workflow-template discovery/loading for pauli decompose ([6e9e2ce](https://github.com/nicsuzor/academicOps/commit/6e9e2cee7d74cea16436113ce3b683bdd83ba989))


### Bug Fixes

* **agents:** use canonical double-underscore MCP tool glob names ([#2247](https://github.com/nicsuzor/academicOps/issues/2247)) ([cb351ec](https://github.com/nicsuzor/academicOps/commit/cb351ec0e7cd6b5c6cc296093e57f596896946f6))
* **aops-jr:** fail fast on unrecognized leading flags in `polecat run` ([88a6cf9](https://github.com/nicsuzor/academicOps/commit/88a6cf9a059a16903d262a9795abab557b39e676))
* **aops-jr:** fail fast on unrecognized leading flags in polecat run ([290bdc8](https://github.com/nicsuzor/academicOps/commit/290bdc8f9165fece2ea5c88cca6edb952199c722))
* **aops-jr:** repoint test + doc refs to relocated polecat under aops-jr ([#2271](https://github.com/nicsuzor/academicOps/issues/2271)) ([f285372](https://github.com/nicsuzor/academicOps/commit/f28537205c4c3e37910a134259a0c0766cfe5f77))
* **aops-jr:** resolve installed-plugin root at runtime, not $AOPS repo path ([#2274](https://github.com/nicsuzor/academicOps/issues/2274)) ([faf98c4](https://github.com/nicsuzor/academicOps/commit/faf98c4fbf6a07075d807050f09e6ed9293af4e6))
* **build:** drop redundant autoMode manifest key to clear validate warning ([97facd7](https://github.com/nicsuzor/academicOps/commit/97facd7b8b5ec7a1bf873657ff73f3a49d834933))
* **dispatch:** mandate skill-mediated dispatch + sibling-task PR bundling ([a7637fb](https://github.com/nicsuzor/academicOps/commit/a7637fb1665df9d77b05e1cb34e40be77d349a93))
* **dispatch:** mandate skill-mediated dispatch + sibling-task PR bundling ([795ede6](https://github.com/nicsuzor/academicOps/commit/795ede6de0dc496dea20c42b1afd32f06874e0ec))
* **docs:** repoint 7 unambiguous stale aops-core refs ([20bab0e](https://github.com/nicsuzor/academicOps/commit/20bab0e818234aadca4c4e442251fe7788119841))
* **hooks:** rephrase SubagentStop honesty reminder as re-output, not self-audit ([d1d50a3](https://github.com/nicsuzor/academicOps/commit/d1d50a3fda7ab1dd68c3c42bf9ae3912011c980c))
* **launchd:** remove hardcoded machine paths from envvars plist ([#2254](https://github.com/nicsuzor/academicOps/issues/2254)) ([598afdb](https://github.com/nicsuzor/academicOps/commit/598afdb6de398275cfcc17b854fe61be35b0cfcc))
* **macos:** restore launchd gh-auth injection + session-scoped SSH isolation ([#2251](https://github.com/nicsuzor/academicOps/issues/2251)) ([7bea600](https://github.com/nicsuzor/academicOps/commit/7bea600aff4173cf502a84deab2081a3e04d377f))
* **pkb:** finish dead PKB-prefix sweep on operational surfaces ([f5e01a5](https://github.com/nicsuzor/academicOps/commit/f5e01a511e073cb96c6350fca29b8f74e7ab5c94))
* **pkb:** reconcile stale PKB MCP tool names to live services namespace ([4473f2c](https://github.com/nicsuzor/academicOps/commit/4473f2c8cc8e75ae7b9bf8978dada9ebcb6b925f))
* **polecat:** agy dispatch exits via --print instead of idling on --prompt-interactive ([ada9a2f](https://github.com/nicsuzor/academicOps/commit/ada9a2f2cdca2befddf83a6ca3aac8fc857ff076))
* **polecat:** cli_lite.py never requests -it without a real TTY ([fef8259](https://github.com/nicsuzor/academicOps/commit/fef8259749874ed795e8e050803b42fc21387400))
* **polecat:** make agy -t task-seed failures observable and fail-fast ([f27546b](https://github.com/nicsuzor/academicOps/commit/f27546b998bd255dfa7d730355824333d1d3765d))
* **polecat:** make agy `-t` task-seed failures observable and fail-fast ([d6c6abd](https://github.com/nicsuzor/academicOps/commit/d6c6abd0761b6d48512881e2a15a9ca456e18eee))
* **polecat:** never let local dispatch pull a stale/registry image; version-stamp SessionStart ([#2246](https://github.com/nicsuzor/academicOps/issues/2246)) ([6c298d6](https://github.com/nicsuzor/academicOps/commit/6c298d692e6e7bdfbac01f25c14465960cb78d73))
* **polecat:** put --print-timeout before --print in agy headless dispatch ([75563e6](https://github.com/nicsuzor/academicOps/commit/75563e6124a167720d1c9ac68783711011db47f0))
* **polecat:** reapply lost agy dispatch fix — prompt-interactive, log-file, mount pre-creation ([43be417](https://github.com/nicsuzor/academicOps/commit/43be417cf5816b85bf279cbe91cfb849a785039e))
* **polecat:** regenerate minimal ~/.gemini/settings.json instead of copying host verbatim ([6c056cd](https://github.com/nicsuzor/academicOps/commit/6c056cd4cd902f0079b5ba9dfcd041ffe01b9b51))
* **polecat:** rename cli_lite.py to cli.py, fix stale crew/nuke doc refs ([732b881](https://github.com/nicsuzor/academicOps/commit/732b881fc6d9b24bef55a641aedad6bf3bd5ea68))
* **polecat:** reorder --print-timeout before --print in agy headless dispatch ([049f26e](https://github.com/nicsuzor/academicOps/commit/049f26eb1f01cbe56d65598d6073266ff332e9bb))
* **polecat:** restore plugin activation and PKB MCP config in polecat images ([#2249](https://github.com/nicsuzor/academicOps/issues/2249)) ([9fefc43](https://github.com/nicsuzor/academicOps/commit/9fefc4302b77b1ac3eb1f101ff98d99f78781cb6))
* **polecat:** stop leaking host Gemini/Antigravity credentials into containers ([7469d75](https://github.com/nicsuzor/academicOps/commit/7469d756d9028acf77dd277b47cd5503b9a35b5a))
* remove Docker socket access by default, add opt-in mechanism (aops_624a462e, aops_e3b194fb) ([2ed7304](https://github.com/nicsuzor/academicOps/commit/2ed73047a3289e2c7ba34f82435d66f76c2ae3b6))
* **specs:** strip dated debug narration from specs, cite doc-taxonomy ([#2242](https://github.com/nicsuzor/academicOps/issues/2242)) ([862d023](https://github.com/nicsuzor/academicOps/commit/862d02351e218660a1591f331c35b84ec9a95845))
* **transcripts:** surface tool results, solve truncation, and add cost fields ([#2297](https://github.com/nicsuzor/academicOps/issues/2297)) ([fb9bd53](https://github.com/nicsuzor/academicOps/commit/fb9bd53427f7b5158598289eb30b1014d612fd3b))
* update build workflow ([65eeaaa](https://github.com/nicsuzor/academicOps/commit/65eeaaad3dd1605d51d6eda575443c6b3a487659))


### Documentation

* create skill capability and constraint map ([#2296](https://github.com/nicsuzor/academicOps/issues/2296)) ([6f2972b](https://github.com/nicsuzor/academicOps/commit/6f2972bd04afddf0ab847429bae68d895b6c72d6))
* **flow-map:** add specs/FLOW-MAP.md — component/trigger SSoT + README link ([#2268](https://github.com/nicsuzor/academicOps/issues/2268)) ([f7b4bfc](https://github.com/nicsuzor/academicOps/commit/f7b4bfc62df399917e84ba46b2a1b2181fca08fd))
* merge aops/README into root README, correct stale architecture claims ([9edb1e6](https://github.com/nicsuzor/academicOps/commit/9edb1e614be7763a6c9c0c7b46b71e11d5288878))
* **polecat:** fix stale crew/nuke references, flag architecture gap ([b321d30](https://github.com/nicsuzor/academicOps/commit/b321d3074d3fc965fc0294abc3a5d99bf6360e8d))
* **polecat:** fold agy-debugging lessons into debug skill and specs ([64c3569](https://github.com/nicsuzor/academicOps/commit/64c35699da2d41873ef5fb6767c08f171cdccf80))
* **polecat:** move tmux-driving mechanics from README to a spec ([7265e5c](https://github.com/nicsuzor/academicOps/commit/7265e5c9f43f6270225d666d4cba88fd3ee1f1f5))
* **specs:** complete worker-contract reframe across remaining specs and skills ([49fb578](https://github.com/nicsuzor/academicOps/commit/49fb578fef5b566d6464928c7b51845e6c141c73))
* **specs:** de-emphasise review-independence per 2026-07-19 ruling ([daab20b](https://github.com/nicsuzor/academicOps/commit/daab20bd0b7fb6799c0a33c2e2a487906e131efe))
* **specs:** fold unified worker-contract reframe into FLOW-MAP + reconcile overlapping specs/skills ([67d9e17](https://github.com/nicsuzor/academicOps/commit/67d9e1721f5040562c551fbca5be826926fb1681))
* **workflows:** migrate gates to PKB templates to match v0.4 plan ([464a765](https://github.com/nicsuzor/academicOps/commit/464a765d8499afce8cf1fee1bf2e449e01c81397))
* **workflows:** Migrate workflow gates to PKB templates ([3a7e587](https://github.com/nicsuzor/academicOps/commit/3a7e5872ec50aa696336e70e71a5f8e4f7b701f6))


### Tests

* **transcripts:** land anonymized Claude and agy transcript fixtures ([2377634](https://github.com/nicsuzor/academicOps/commit/23776346bce7bdbb8672e0a066e2ad2d1e209052))
* **transcripts:** re-anonymize username and PKB ID leaks ([e706b45](https://github.com/nicsuzor/academicOps/commit/e706b45970ac98cfbff986c970d49df9c80df03b))


### Miscellaneous

* retire Gemini CLI as a supported client surface ([#2252](https://github.com/nicsuzor/academicOps/issues/2252)) ([57ca2a6](https://github.com/nicsuzor/academicOps/commit/57ca2a6f2407fb687d2b84d8c70995fb05b14af5))
* **transcripts:** drop scheduled drift workflow, rely on the pytest ([#2266](https://github.com/nicsuzor/academicOps/issues/2266)) ([5ffea69](https://github.com/nicsuzor/academicOps/commit/5ffea699a1f025abe149f72b145427ac2188fc33))
* **v0.4:** normalize services MCP rename + aops-core→aops consolidation ([5910671](https://github.com/nicsuzor/academicOps/commit/591067125cce0495aff682d2867a4490da26438e))

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
