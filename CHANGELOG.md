# Changelog

## [0.3.22](https://github.com/nicsuzor/academicOps/compare/v0.3.21...v0.3.22) (2026-05-04)


### Features

* **commands:** add /issue-sweep — quality-gated GitHub issue triage ([#820](https://github.com/nicsuzor/academicOps/issues/820)) ([a2ad9a1](https://github.com/nicsuzor/academicOps/commit/a2ad9a1844663356ae9cf3eaf72b24a679517bb5))
* **core:** point agents at PKB specs first ([#876](https://github.com/nicsuzor/academicOps/issues/876)) ([05e4e0d](https://github.com/nicsuzor/academicOps/commit/05e4e0d19f8571a964bfc46eebc6aa96f521f39a))
* **cowork:** implement Cowork audit log ingestion and normalization ([#776](https://github.com/nicsuzor/academicOps/issues/776)) ([1972b2b](https://github.com/nicsuzor/academicOps/commit/1972b2bedf307e36825b7b72310714a1d898112c))
* **docker:** trust extension and config folders in worker image ([#757](https://github.com/nicsuzor/academicOps/issues/757)) ([3bfb227](https://github.com/nicsuzor/academicOps/commit/3bfb22744c2237e169748f491f4e02bd55019303))
* **dump,transcript:** require framework reflection + output link + tasks-worked list ([#855](https://github.com/nicsuzor/academicOps/issues/855)) ([19fc612](https://github.com/nicsuzor/academicOps/commit/19fc612307132fb0b0e65fcb0988ce2b83ec871e))
* **dump:** cross-reference current epic in project file ([#825](https://github.com/nicsuzor/academicOps/issues/825)) ([7465931](https://github.com/nicsuzor/academicOps/commit/7465931198b06a0e1a30d32601b968c178a6679c))
* **enforcer:** block (not defer) PRs that add gates without updating enforcement-map (Closes [#803](https://github.com/nicsuzor/academicOps/issues/803)) ([#859](https://github.com/nicsuzor/academicOps/issues/859)) ([d429d67](https://github.com/nicsuzor/academicOps/commit/d429d67052c36d3167e172da03568f8ebd1ac1ba))
* **epic-319a8797:** Phase A — handoff architecture + RBG surgery ([ed6abc8](https://github.com/nicsuzor/academicOps/commit/ed6abc8ff183c6a62496778ec824e2b83a773885))
* **epic-319a8797:** Phase B — supervisor template generalisation ([417adf3](https://github.com/nicsuzor/academicOps/commit/417adf3f05049abf4e2dffa5d1455cc93ff68a6a))
* **heuristics:** age is not a staleness signal — garden surfaces, never cancels (Closes [#185](https://github.com/nicsuzor/academicOps/issues/185)) ([#860](https://github.com/nicsuzor/academicOps/issues/860)) ([f5c5f83](https://github.com/nicsuzor/academicOps/commit/f5c5f839cc920b804836e5f2b7632b26fae2ad14))
* **heuristics:** age is not a staleness signal ([#837](https://github.com/nicsuzor/academicOps/issues/837)) ([4a7907e](https://github.com/nicsuzor/academicOps/commit/4a7907e39b20894eb8b024651d74227e9a81f54f))
* **hooks:** log client_type to distinguish claude vs gemini sessions (Closes task-c5d2e2da) ([#867](https://github.com/nicsuzor/academicOps/issues/867)) ([944c833](https://github.com/nicsuzor/academicOps/commit/944c83338d9c0ac1e499e774e2cd8ff038d3c6b9))
* **maintain:** /maintain anti-inflation surface + /daily SEV4 warning ([#879](https://github.com/nicsuzor/academicOps/issues/879)) ([c375600](https://github.com/nicsuzor/academicOps/commit/c3756009f1ab10cff86bb549c16f184fe5f25994))
* **mcp:** standardise transport on HTTP/SSE for non-local targets ([#781](https://github.com/nicsuzor/academicOps/issues/781)) ([f0bf332](https://github.com/nicsuzor/academicOps/commit/f0bf332f5df12faed68a69a942313ee41c630dbd))
* **observability:** improve session JSON metadata for downstream analytics ([e88995e](https://github.com/nicsuzor/academicOps/commit/e88995ef689b3ff435ff0309c7d0e39479ecdf2a))
* **observability:** improve session JSON metadata for downstream analytics ([8f393f5](https://github.com/nicsuzor/academicOps/commit/8f393f50cddb2736f7ec23b230bff7a580255bae))
* **observability:** session ID alignment + naming + git-sync (P3 group, 5 tasks) ([#858](https://github.com/nicsuzor/academicOps/issues/858)) ([6abcfdf](https://github.com/nicsuzor/academicOps/commit/6abcfdfd5181a0faaa182d1d0ac30c4696192d46))
* **planner:** add decision-surfacing heuristic to teach DECIDE/DEFER/SURFACE classification ([#818](https://github.com/nicsuzor/academicOps/issues/818)) ([81d4b71](https://github.com/nicsuzor/academicOps/commit/81d4b71ca3f288681e2e886679eebacaf1aee2a9))
* **planner:** default new tasks to P3 unless user signals urgency ([#842](https://github.com/nicsuzor/academicOps/issues/842)) ([43e8fba](https://github.com/nicsuzor/academicOps/commit/43e8fba40b4fc331aacb3ac988bc326cad99a1af))
* **polecat:** add --force flag to run command ([#861](https://github.com/nicsuzor/academicOps/issues/861)) ([1432558](https://github.com/nicsuzor/academicOps/commit/1432558f818e39b6339deba6b10e9da9871e68a5))
* **polecat:** CLI/lifecycle polish — --force, sweep removal, lifecycle stubs, transcript surfacing ([#850](https://github.com/nicsuzor/academicOps/issues/850)) ([e5b5962](https://github.com/nicsuzor/academicOps/commit/e5b5962cae63dae80bf571c9bbff3f675ef281d5))
* **polecat:** remove sweep subcommand — supervisor handles PR-state directly ([#868](https://github.com/nicsuzor/academicOps/issues/868)) ([3e7a4ad](https://github.com/nicsuzor/academicOps/commit/3e7a4ade3da7af929268d181a4c37189fa75cf15))
* **polecat:** surface real transcript path in task body and PR ([#872](https://github.com/nicsuzor/academicOps/issues/872)) ([146a182](https://github.com/nicsuzor/academicOps/commit/146a1826b7342602bc5668030868034f49f6de74))
* **pull:** dispatch to specialist agent when assignee names one (Closes [#733](https://github.com/nicsuzor/academicOps/issues/733)) ([#857](https://github.com/nicsuzor/academicOps/issues/857)) ([21091d3](https://github.com/nicsuzor/academicOps/commit/21091d3e4984afb412dec38229e16e7eedbed03f))
* **rbg:** A2 class-coverage check + structured exemption schema (Closes epic-e1ddba21, refs [#794](https://github.com/nicsuzor/academicOps/issues/794), [#811](https://github.com/nicsuzor/academicOps/issues/811)) ([#878](https://github.com/nicsuzor/academicOps/issues/878)) ([bf79450](https://github.com/nicsuzor/academicOps/commit/bf79450abd080b448cf56ff9ae7efab274168837))
* **rules:** R5.6 — no new orphan markdown + pre-commit gate ([#793](https://github.com/nicsuzor/academicOps/issues/793)) ([dc8917a](https://github.com/nicsuzor/academicOps/commit/dc8917ac79b812332893956c84deb620e9a9833a))
* **sessions:** align task ID across all session-artifact filenames ([#882](https://github.com/nicsuzor/academicOps/issues/882)) ([5886669](https://github.com/nicsuzor/academicOps/commit/58866699863af2dbb8da120a0c205882bafdfec9))
* **skills:** /daily and /pull consume urgency signal (task-0e12ef8d) ([#846](https://github.com/nicsuzor/academicOps/issues/846)) ([153a595](https://github.com/nicsuzor/academicOps/commit/153a5954ed8458bea9814f6078ba4233e59c8b82))
* **skills:** /maintain anti-inflation surface for graph hygiene ([#848](https://github.com/nicsuzor/academicOps/issues/848)) ([b037723](https://github.com/nicsuzor/academicOps/commit/b0377235a3af5dc1ac7cb61f8276291f3827a32a))
* **sleep:** mode-aware pacing with brain auto-merge ([#712](https://github.com/nicsuzor/academicOps/issues/712)) ([#833](https://github.com/nicsuzor/academicOps/issues/833)) ([3844ed3](https://github.com/nicsuzor/academicOps/commit/3844ed35c1491a20435207ac737f45271edae7a7))
* **supervisor,rbg:** A8 composition-time enforcement ([#877](https://github.com/nicsuzor/academicOps/issues/877)) ([754ab07](https://github.com/nicsuzor/academicOps/commit/754ab07428db867ec003a8b9827bb5411ea96de5))
* **supervisor:** add WORKERS.md worker registry ([#828](https://github.com/nicsuzor/academicOps/issues/828)) ([eee2f7e](https://github.com/nicsuzor/academicOps/commit/eee2f7e4b89500d88d90dc2179ca5f7761a135d7))
* **transcript:** surface injected/read context in Session Context section (Closes task-8b3e3cfd) ([#875](https://github.com/nicsuzor/academicOps/issues/875)) ([e9cbae2](https://github.com/nicsuzor/academicOps/commit/e9cbae251b47e347541b745939e00d444e9aa3af))


### Bug Fixes

* add skip guard to Propagate agent exit status step ([a78c50c](https://github.com/nicsuzor/academicOps/commit/a78c50cbfaf3c98b257bc2f938908e3bdeccb71c))
* **agents:** add PKB write tools and normalise frontmatter schema ([#639](https://github.com/nicsuzor/academicOps/issues/639), [#679](https://github.com/nicsuzor/academicOps/issues/679)) ([b78b052](https://github.com/nicsuzor/academicOps/commit/b78b052eb33b1203d0b66c5d1158118403eea972))
* **agents:** add PKB write tools and normalise frontmatter schema ([#639](https://github.com/nicsuzor/academicOps/issues/639), [#679](https://github.com/nicsuzor/academicOps/issues/679)) ([eadee0e](https://github.com/nicsuzor/academicOps/commit/eadee0e9ef38e6f416d0d09253305b38786c4aee))
* **cron:** tie sync_gha_sessions.py into the local transcript cron ([#766](https://github.com/nicsuzor/academicOps/issues/766)) ([2742df3](https://github.com/nicsuzor/academicOps/commit/2742df325b1572465b59ba1e3103e32655a3fa30)), closes [#765](https://github.com/nicsuzor/academicOps/issues/765)
* **daily:** anchor day-of-week and work-date on today's calendar date ([75dfaae](https://github.com/nicsuzor/academicOps/commit/75dfaaeddec2d32e3e8863e97d168f09028fb63e))
* **daily:** anchor day-of-week and work-date on today's calendar date ([#759](https://github.com/nicsuzor/academicOps/issues/759)) ([62faf20](https://github.com/nicsuzor/academicOps/commit/62faf20ddd7f733863ffbc66a4f4b92907634925))
* **daily:** read completion signals before regenerating ([#847](https://github.com/nicsuzor/academicOps/issues/847)) ([3b20deb](https://github.com/nicsuzor/academicOps/commit/3b20debf9fafb35e7368350b2519edd4d5548cc2))
* **enforcer:** pin academicOps checkout to pipeline-v1 ([45753d2](https://github.com/nicsuzor/academicOps/commit/45753d2d920e9da455d7daeadb3eb1b2abce962e))
* **enforcer:** pin academicOps checkout to pipeline-v1 ([1df278d](https://github.com/nicsuzor/academicOps/commit/1df278dd31ddbdaaf582b8da12786335951a4ae9))
* **hooks,e2e:** polecat-aware paths + e2e fixture corrections ([#788](https://github.com/nicsuzor/academicOps/issues/788)) ([9380549](https://github.com/nicsuzor/academicOps/commit/9380549e657814058e09267381c92c89415d7d02))
* **hooks:** point periodic-enforcer at aops-core:rbg ([#817](https://github.com/nicsuzor/academicOps/issues/817)) ([#832](https://github.com/nicsuzor/academicOps/issues/832)) ([5c054e7](https://github.com/nicsuzor/academicOps/commit/5c054e77341729bd12ad3d3c73dc52d25c85abb3))
* **mcp:** resolve PKB_MCP_URL in run-mcp.sh, drop broken env block ([7f82976](https://github.com/nicsuzor/academicOps/commit/7f8297693e57f08485ef3ac650e4763a105668b2))
* **merge-prep-cron:** drop reserved GITHUB_TOKEN from workflow_call secrets ([b6008a6](https://github.com/nicsuzor/academicOps/commit/b6008a65add9919302fceae2752e42e7ec1f2c9c))
* **merge-prep-cron:** hoist defaults out of job-level env to fix workflow_run trigger ([#792](https://github.com/nicsuzor/academicOps/issues/792)) ([079958b](https://github.com/nicsuzor/academicOps/commit/079958b83cb0a26cbdf7eb442fcea6bfc4f15b4b))
* **merge-prep:** load prompt from academicOps, not caller's repo ([cc011a9](https://github.com/nicsuzor/academicOps/commit/cc011a9b55e2f991d63c5da9ff1845fb34dc2c5f))
* **merge-prep:** load prompt from academicOps, not caller's repo ([0b920b5](https://github.com/nicsuzor/academicOps/commit/0b920b5057ef54eb1ff9e4e25fc52a8f3f2eed02))
* **observability:** add is_error to tool_call dedup key ([eb2a3ef](https://github.com/nicsuzor/academicOps/commit/eb2a3efce3a42ae2d5f6f1806950cbccea305bb8))
* **orchestrator-boundary:** scope dispositor reminder to brain repo only ([#805](https://github.com/nicsuzor/academicOps/issues/805)) ([41ba536](https://github.com/nicsuzor/academicOps/commit/41ba5362f3ab4b40f14ed16a59dcd8dfa56e9e76))
* **p65:** update enforcement map for rbg surgery + user-side cron ([afc8b8e](https://github.com/nicsuzor/academicOps/commit/afc8b8ebde6fb985a9df1db50313e2b73c3925c7))
* **p65:** update ENFORCEMENT-MAP for new rbg enforcement gates added in PR [#896](https://github.com/nicsuzor/academicOps/issues/896) ([980a071](https://github.com/nicsuzor/academicOps/commit/980a071b58ffa740c3646687590ca7d7344f7477))
* **p65:** update ENFORCEMENT-MAP for PR [#895](https://github.com/nicsuzor/academicOps/issues/895) revert changes ([78cb298](https://github.com/nicsuzor/academicOps/commit/78cb2987f8e10b0ff154f72f21119203563edada))
* **pkb-mcp:** declare deps via PEP 723 so uv resolves them at launch ([#813](https://github.com/nicsuzor/academicOps/issues/813)) ([12295b2](https://github.com/nicsuzor/academicOps/commit/12295b220935d064b71e9f71a9cd8b13804d63a7))
* **pkb:** default new tasks to priority 3 instead of 2 (task-2b01a9e4) ([#851](https://github.com/nicsuzor/academicOps/issues/851)) ([b9018a2](https://github.com/nicsuzor/academicOps/commit/b9018a2e79ec649d11d9848ff04a17611f640612))
* **planner:** consult CORE.md Component Topology before parent assignment (Closes [#663](https://github.com/nicsuzor/academicOps/issues/663)) ([#835](https://github.com/nicsuzor/academicOps/issues/835)) ([38aab93](https://github.com/nicsuzor/academicOps/commit/38aab9308d1bd2af9147c3305bae11ad0eca05bb))
* **planner:** externalise follow-up action items as separate linked tasks (Closes [#582](https://github.com/nicsuzor/academicOps/issues/582)) ([#838](https://github.com/nicsuzor/academicOps/issues/838)) ([bc38d2e](https://github.com/nicsuzor/academicOps/commit/bc38d2e1803e8e9b563d06e235afffd17a0a6dfe))
* **polecat:** add Step 0 pre-push gate-recheck to worker template ([#583](https://github.com/nicsuzor/academicOps/issues/583)) ([#831](https://github.com/nicsuzor/academicOps/issues/831)) ([5a8e9b9](https://github.com/nicsuzor/academicOps/commit/5a8e9b950b37b8f0b67ce154ca2b9fa83dec92b6))
* **polecat:** collapse 6 hardcoded forwarding blocks into agent-env-map.conf SSoT ([#824](https://github.com/nicsuzor/academicOps/issues/824)) ([ffbd572](https://github.com/nicsuzor/academicOps/commit/ffbd5723464c323f675e74b9125712343d185f14))
* **polecat:** replace literal — escape with actual em-dash in comment ([9e10c38](https://github.com/nicsuzor/academicOps/commit/9e10c38964737da17c297cccf3dad9383e556ba1))
* **polecat:** retry pkb_bridge _post once on chunked-read TimeoutError (aops-aaa98cf7) ([#852](https://github.com/nicsuzor/academicOps/issues/852)) ([000e247](https://github.com/nicsuzor/academicOps/commit/000e2476cdbe8a43e7beba24c9a5fa34ea873a03))
* **polecat:** robust docker binary resolution + accurate command-not-found message ([2adcffa](https://github.com/nicsuzor/academicOps/commit/2adcffa219f76a4116948a69afc3d4f6d9c234c7))
* **polecat:** robust docker binary resolution + accurate FileNotFoundError message ([db71cd9](https://github.com/nicsuzor/academicOps/commit/db71cd9df3f2b4c031dc0934cbe0c7aee12033a7))
* **policies:** use gemini snake_case tool names in deny-extension-writes.toml ([608ce59](https://github.com/nicsuzor/academicOps/commit/608ce597315aa93e25be3da9f1065c11c847106a))
* **rbg:** criterion-substitution + unverified-keystone + sensitive-data scan ([#853](https://github.com/nicsuzor/academicOps/issues/853)) ([3c88fe9](https://github.com/nicsuzor/academicOps/commit/3c88fe93fce82bd2ac081a2cc9a0218d71f15356))
* **rbg:** restore required sections removed by [#891](https://github.com/nicsuzor/academicOps/issues/891) RBG surgery ([dfcff2c](https://github.com/nicsuzor/academicOps/commit/dfcff2c71099ed1f2f9c01e98e9ff64cef94fca1))
* resolve merge conflicts with main (PR [#891](https://github.com/nicsuzor/academicOps/issues/891) RBG surgery) ([13fc07c](https://github.com/nicsuzor/academicOps/commit/13fc07c2bcb933d26effc0aeb70b0d6c67a35c0d))
* restore load-bearing sections in rbg.md stripped by clean-up commit ([38282ae](https://github.com/nicsuzor/academicOps/commit/38282aee09e788f0285d3edadf3cbfece9a35ba2))
* restore rbg.md full content to keep test suite green ([c036209](https://github.com/nicsuzor/academicOps/commit/c036209dc2e2ce2bccb157af54d78578f20addd0))
* **review:** disclose polecat 401 auth issue in run_judge comment ([0b48a1d](https://github.com/nicsuzor/academicOps/commit/0b48a1dc23069b7e0ef35e6c218c255a9e20dc72))
* **scripts:** move re import to module level in transcript.py ([b98f22f](https://github.com/nicsuzor/academicOps/commit/b98f22f6bf266cda3a5127fe916a50280cfbd251))
* **session-writer:** dedupe timeline_events to prevent double-recording (Closes task-955f405d) ([#864](https://github.com/nicsuzor/academicOps/issues/864)) ([5268c30](https://github.com/nicsuzor/academicOps/commit/5268c3002bf73f9db9156da8a240c42a4fd8c606))
* **session-writer:** resolve worktree paths to main repo (Closes task-ea880699) ([#862](https://github.com/nicsuzor/academicOps/issues/862)) ([b576cba](https://github.com/nicsuzor/academicOps/commit/b576cbab3b2780e67a95b2743a8a8f66b340d9e8))
* **sessions:** fix 00:00 filename collision for date-only strings ([#753](https://github.com/nicsuzor/academicOps/issues/753)) ([6d4ca56](https://github.com/nicsuzor/academicOps/commit/6d4ca568216bc24a47177d0e1b59ba0c9650dcf1))
* **sessions:** unify per-session artefact paths; provider in filename ([#903](https://github.com/nicsuzor/academicOps/issues/903)) ([8d2f93e](https://github.com/nicsuzor/academicOps/commit/8d2f93e36896f067a81081487d6756fac27af4f7))
* **sleep:** attach PKB MCP toolset to Phase 2/4 sub-agents ([#841](https://github.com/nicsuzor/academicOps/issues/841)) ([411aec9](https://github.com/nicsuzor/academicOps/commit/411aec913b2184c373d1676a3e02fe1607d39875))
* stop RBG enforcer running when no PR is found on workflow_run ([111741c](https://github.com/nicsuzor/academicOps/commit/111741c791e340d57f9d29c5ead6cf6f06394272))
* stop RBG enforcer running when no PR is found on workflow_run ([1641b20](https://github.com/nicsuzor/academicOps/commit/1641b203f04761ecfc6a724ca818d25d4dcb93d6))
* **supervisor:** halt on infeasible dispatch — never silently swap worker types ([#827](https://github.com/nicsuzor/academicOps/issues/827)) ([d9c0cf2](https://github.com/nicsuzor/academicOps/commit/d9c0cf24820dd20b757364a762da004da20c6e16)), closes [#643](https://github.com/nicsuzor/academicOps/issues/643)
* **supervisor:** mandatory host-check + ping-pkb gate for dispatch reliability ([#836](https://github.com/nicsuzor/academicOps/issues/836)) ([ff8af50](https://github.com/nicsuzor/academicOps/commit/ff8af50c771b9566c10506cf32a29ee894cfba6d))
* **tests:** F-group fixture race in temp_polecat_home ([#856](https://github.com/nicsuzor/academicOps/issues/856)) ([cce05af](https://github.com/nicsuzor/academicOps/commit/cce05aff982ac3969c93a78003a7d2f55b0fcdc9))
* **test:** update _extract_section to stop at new ### Hook: per-turn rendering ([c4e439d](https://github.com/nicsuzor/academicOps/commit/c4e439d44f2b7fd3e7dc9a19e87c674ad4b32a47))
* **test:** update rbg tools test for PR [#895](https://github.com/nicsuzor/academicOps/issues/895) architectural change ([46b2e99](https://github.com/nicsuzor/academicOps/commit/46b2e990796550d693ad4b76ac28d05299f41fb9))
* **transcript:** read hook gate results from CanonicalHookOutput.output (Closes task-fc938187) ([28dda57](https://github.com/nicsuzor/academicOps/commit/28dda5735f698331c725593b95115a80c45a782a))
* **transcript:** refresh insights JSON when source jsonl grows ([#764](https://github.com/nicsuzor/academicOps/issues/764)) ([9ec17de](https://github.com/nicsuzor/academicOps/commit/9ec17de52430d880853dfba8b22199721aa7db22))
* **transcript:** render hook verdicts/messages in session markdown ([3b067b2](https://github.com/nicsuzor/academicOps/commit/3b067b24541eb88593e3d2847d4c46b5ee989d17))
* **transcript:** respect full_mode in standalone hook message truncation ([06db00c](https://github.com/nicsuzor/academicOps/commit/06db00cd8d184d572d7bba108f5fa25b88960f2a))
* use complete_task for rbg verdicts; add regression test (P[#82](https://github.com/nicsuzor/academicOps/issues/82)) ([2a10429](https://github.com/nicsuzor/academicOps/commit/2a104294dd449b23f4c2ee73b1f9bef275b142b3))


### Reverts

* **epic-319a8797:** remove cron, GHA label workflow, RBG case-law ([2c0bdf3](https://github.com/nicsuzor/academicOps/commit/2c0bdf31d907885040614598810c7655b2a5163e))
* **epic-319a8797:** remove cron, GHA label workflow, RBG case-law ([9bc02e8](https://github.com/nicsuzor/academicOps/commit/9bc02e8e9e3780ba5094a6b457c5df57d7897dec))


### Code Refactoring

* **config:** projects.yaml as SSoT; drop polecat.yaml ([#799](https://github.com/nicsuzor/academicOps/issues/799)) ([a873edb](https://github.com/nicsuzor/academicOps/commit/a873edb0ad5c148b1ba6b8cadb2d088f8f38eddc))
* **insights:** remove dead prompt-loader functions (Closes task-83932f98) ([#871](https://github.com/nicsuzor/academicOps/issues/871)) ([03a2ef9](https://github.com/nicsuzor/academicOps/commit/03a2ef9e1b5fe47756def9c1b696a82f24d5a7e8))
* **polecat:** consolidate claim + extract finalize, remove _sync_working_repo from dispatch (Step 2 of Polecat v2 epic-4234682b) ([#884](https://github.com/nicsuzor/academicOps/issues/884)) ([1b99a6a](https://github.com/nicsuzor/academicOps/commit/1b99a6a59ae1dc6674973ed53222b09284818afb))
* **polecat:** extract swarm/watch/analyze/reset_stalled/summary into modules (Step 1 of Polecat v2 epic-4234682b) ([#880](https://github.com/nicsuzor/academicOps/issues/880)) ([af28012](https://github.com/nicsuzor/academicOps/commit/af28012c34b3763d23e13ca9929d443944f442d8))
* **transcript:** remove dead shim, deduplicate _keep_hook predicate ([583e3ab](https://github.com/nicsuzor/academicOps/commit/583e3ab8a634d4efae7cfb26dd5b3cc222cb25ed))


### Documentation

* Add Playwright MCP to tool capabilities section ([f5a6510](https://github.com/nicsuzor/academicOps/commit/f5a651025662a4d99649c5225822c4b87f7cb3cb))
* Add tool capabilities reference for dispatched sessions ([dfc9dec](https://github.com/nicsuzor/academicOps/commit/dfc9dec4f943e9d8e3ec8e8d5d480fe00679c5e3))
* align surfaces to focus_score as primary ranking signal (task-d997a904) ([6434528](https://github.com/nicsuzor/academicOps/commit/64345282069b846ce1d114541019596235b16438))
* **planner:** default new tasks to P3 unless user indicates urgency (Closes task-e410b794) ([#873](https://github.com/nicsuzor/academicOps/issues/873)) ([f29c59a](https://github.com/nicsuzor/academicOps/commit/f29c59a33edad518c5f5624a5eebc2898de72696))
* **polecat:** align spec with reality + drop out-of-date crew merge section ([#769](https://github.com/nicsuzor/academicOps/issues/769)) ([39ea6fc](https://github.com/nicsuzor/academicOps/commit/39ea6fc62df0dfb5a55597e05cd256e3dfc0ad9c))
* **priority:** canonical P0–P4 definitions ([#840](https://github.com/nicsuzor/academicOps/issues/840)) ([8a39ffe](https://github.com/nicsuzor/academicOps/commit/8a39ffe5baf201833cd65c68390fac6a2aec6928))
* **priority:** canonicalize P0–P4 in TAXONOMY ([#863](https://github.com/nicsuzor/academicOps/issues/863)) ([c8c9a92](https://github.com/nicsuzor/academicOps/commit/c8c9a9262adb38abe0b87a1c529b8770067bf8ae))
* reference list_tasks project filter in skill bodies (Closes task-3dfb97b5) ([#870](https://github.com/nicsuzor/academicOps/issues/870)) ([3689ee1](https://github.com/nicsuzor/academicOps/commit/3689ee1ae331aa5810ac7543de2eff1cce9f915c))
* reference new list_tasks project filter in skills ([#849](https://github.com/nicsuzor/academicOps/issues/849)) ([b135754](https://github.com/nicsuzor/academicOps/commit/b1357542c6cf072df07e7668da13938c09da7169))
* **remember:** clarify confidence is numeric and synthesized/sources required for knowledge (partial Closes task-2e8b1498) ([#883](https://github.com/nicsuzor/academicOps/issues/883)) ([bbbc038](https://github.com/nicsuzor/academicOps/commit/bbbc03850faffcb0a159cf24b5a8defef1eeabd8))
* remove stale references to non-existent session-insights skill (Closes task-c5fa4dd6) ([#869](https://github.com/nicsuzor/academicOps/issues/869)) ([22c846d](https://github.com/nicsuzor/academicOps/commit/22c846d444d474d49328ffd6340817c3b6cb6ff5))
* **supervisor:** document manual merge-prep trigger to skip bazaar wait ([#830](https://github.com/nicsuzor/academicOps/issues/830)) ([1b9e498](https://github.com/nicsuzor/academicOps/commit/1b9e498aaa15a938168647fe477329787c110082))
* **supervisor:** document uv run form for polecat in non-interactive shells ([#826](https://github.com/nicsuzor/academicOps/issues/826)) ([148ff21](https://github.com/nicsuzor/academicOps/commit/148ff218d231458676b304c5b5fdf3054435349d)), closes [#618](https://github.com/nicsuzor/academicOps/issues/618)


### Tests

* **gemini:** pin PKB MCP config; add non-PR persistence E2E; capability matrix ([#787](https://github.com/nicsuzor/academicOps/issues/787)) ([a1ee0ec](https://github.com/nicsuzor/academicOps/commit/a1ee0ecd77dadfeab00de93304cc6c5bd5c05b87))
* **polecat:** parametrise transcript-persistence e2e for Gemini variant ([#881](https://github.com/nicsuzor/academicOps/issues/881)) ([efa5442](https://github.com/nicsuzor/academicOps/commit/efa5442f5a991bd777b29a0b87ad24ea72c1de0e))
* **transcript:** add test coverage for thoughts/thinking rendering (task-df03f1d9) ([#874](https://github.com/nicsuzor/academicOps/issues/874)) ([fbddbd7](https://github.com/nicsuzor/academicOps/commit/fbddbd78a6188a81545f99fcb19af298fdecf476))


### Miscellaneous

* add timeout-minutes: 45 to all GHA jobs ([#772](https://github.com/nicsuzor/academicOps/issues/772)) ([d806b00](https://github.com/nicsuzor/academicOps/commit/d806b0087a7112f40917e42cf06c108bb7a27544))
* **epic-319a8797:** remove seed marker on integration ([2b2dd4b](https://github.com/nicsuzor/academicOps/commit/2b2dd4be8430059fda8a96f27294ad6fec85d733))
* **epic-319a8797:** seed shared branch for coordinated dispatch ([7745f9b](https://github.com/nicsuzor/academicOps/commit/7745f9bdb34a4efa4c467f5a6e6dcd89450ae96e))
* move plugin manifests to templates/ to remove client-confusion vectors ([#796](https://github.com/nicsuzor/academicOps/issues/796)) ([6303e8e](https://github.com/nicsuzor/academicOps/commit/6303e8e20da7869507c02c71963156802adbb407))
* **pkb:** remove downstream_weight from academicOps surfaces (task-412c3443) ([6f13da1](https://github.com/nicsuzor/academicOps/commit/6f13da1fcb94b8ab279e8fd0fd9cafd1bc50358f))
* **pkb:** replace user-facing downstream_weight with urgency (task-412c3443) ([4ca842c](https://github.com/nicsuzor/academicOps/commit/4ca842c9e313dc94cf0d94510cc870218d4cabc4))
* stop packaging project-local CORE.md into plugin distributions ([#783](https://github.com/nicsuzor/academicOps/issues/783)) ([79d4faa](https://github.com/nicsuzor/academicOps/commit/79d4faa64e18fa5eacef66fba87876b3cd03f738))

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
