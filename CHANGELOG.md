# Changelog

## [0.4.0](https://github.com/nicsuzor/academicOps/compare/v0.3.2...v0.4.0) (2026-03-15)

### Features

- add multi-client Docker environment and verification harness ([2aad6ef](https://github.com/nicsuzor/academicOps/commit/2aad6efbf16e5a468c388de6e1c7a06a75e62f64))
- **architecture:** merge hydration with formal decomposition ([af06c82](https://github.com/nicsuzor/academicOps/commit/af06c8261cd54714da120b46e1e63beedae9a1ef))
- **architecture:** redefine hydration as task enrichment ([f6a8ffa](https://github.com/nicsuzor/academicOps/commit/f6a8ffa32850a7b8e29f42a11fb51967a067ae8c))
- **ci:** sequence workflows natively via workflow_call to save quota ([23d12e2](https://github.com/nicsuzor/academicOps/commit/23d12e27a64a60495af9d874b200c48285e18d0b))
- **ci:** sequence workflows natively via workflow_call to save quota ([8495df5](https://github.com/nicsuzor/academicOps/commit/8495df5308ddbbd4d8765f114f91a9c372877cff))
- consolidate hydrators into single hydrator skill ([512d766](https://github.com/nicsuzor/academicOps/commit/512d7666dcb1455abccb8b2f797389b80cc7dbb6))
- consolidate hydrators into single hydrator skill, move WORKFLOWS.md into skill package ([6ba1c18](https://github.com/nicsuzor/academicOps/commit/6ba1c182f3402c60c85a0889cc612986d29fc5c6))
- Gemini Docker sandbox for crew workers + typecheck fix ([d7a47ec](https://github.com/nicsuzor/academicOps/commit/d7a47ec42b5e2237a4d2f69b9723d9a73d267cb6))
- **hydrator:** implement task-hydrator Phase 1 prototype ([0486953](https://github.com/nicsuzor/academicOps/commit/04869533c6d2e6727a36c88fb32595737be94a20))
- Multi-client Docker Environment and Verification ([67786b8](https://github.com/nicsuzor/academicOps/commit/67786b876383969dd97f657d664540e9b7b46f60))
- prune old plugin cache versions in install-dev ([eb08972](https://github.com/nicsuzor/academicOps/commit/eb0897254a495c745488af8208585923cfaf4d91))
- replace polecat worktrees with local clones ([25ec62e](https://github.com/nicsuzor/academicOps/commit/25ec62e292169d45cebb0e2a189997d8e265e02a))
- replace polecat worktrees with local clones ([37c6c24](https://github.com/nicsuzor/academicOps/commit/37c6c24217b7078e6fd06850ba78ab8fd2d5776d))
- **spec:** add User Expectations to daily-briefing-bundle.md ([15efe62](https://github.com/nicsuzor/academicOps/commit/15efe62614c4182a91050ec255ce9e83774ba0ad))
- **workflows:** add outbound-review workflow for pre-send quality gate ([514ccb2](https://github.com/nicsuzor/academicOps/commit/514ccb25e499dc1b7a3131e734d09b49439abb59))
- wrap polecat agent execution in docker container ([46d1900](https://github.com/nicsuzor/academicOps/commit/46d19009acc158ef931495166c8e72166e5396fc))
- wrap polecat agent execution in docker container ([4a54977](https://github.com/nicsuzor/academicOps/commit/4a54977df237d6d150db7e8e35a6202c222c7552))

### Bug Fixes

- add requires_local_env markers and fix test_gate_path_not_in_tmp ([5c84d30](https://github.com/nicsuzor/academicOps/commit/5c84d3041829c394b458fa5306c83d41b387e110))
- add requires_local_env markers to tests needing CLI/env setup ([1da8e51](https://github.com/nicsuzor/academicOps/commit/1da8e5100c10ed53c78d6f3de0761b72915fab24))
- address review feedback — enforcement map, hook templates, VISION.md ([1ba772e](https://github.com/nicsuzor/academicOps/commit/1ba772efe82c1dc70ac5e56af74fe5ef2689b6b3))
- address review feedback — npm cache cleanup and Docker image cleanup trap ([f52b75c](https://github.com/nicsuzor/academicOps/commit/f52b75c9e912df1b8cc3899581a34d43e9f3b917))
- address test failures and environmental dependencies ([cf35b47](https://github.com/nicsuzor/academicOps/commit/cf35b47578931aed45e797572bbd4fa629dbe903))
- align command-intercept spec with P[#8](https://github.com/nicsuzor/academicOps/issues/8) fail-fast requirement ([ba3be29](https://github.com/nicsuzor/academicOps/commit/ba3be29ae2f6c1aa05168d4d1a8692cffb644ca1))
- align test stub with fail-fast config behavior ([0a98a21](https://github.com/nicsuzor/academicOps/commit/0a98a21e4ec9340519d19c89bba46debfb43670e))
- **audit-protocol:** address P[#115](https://github.com/nicsuzor/academicOps/issues/115) conflict and duplicate criteria ([355129d](https://github.com/nicsuzor/academicOps/commit/355129dffaa065207cb6b7c7c11e262747d7623e))
- **build:** retain mcp_ prefix for gemini tool names ([3115b3d](https://github.com/nicsuzor/academicOps/commit/3115b3d0116a23a79ae46e87e4d5c0c96eee9ea1))
- **ci:** add 120s settle delay before agent-fix; revert failure-only condition ([5dde060](https://github.com/nicsuzor/academicOps/commit/5dde060564fd61bfdf5d166c9a10d2a7ecaa9e2c))
- **ci:** cancel duplicate build runs when one is already in progress ([a625130](https://github.com/nicsuzor/academicOps/commit/a625130db680c1a8351893cb91d0ba6e2a029265))
- **ci:** cancel duplicate build runs when one is already in progress ([756e683](https://github.com/nicsuzor/academicOps/commit/756e683d9ba97498ac7e5d5f2c18388cf6a7ba53))
- **ci:** exclude demo tests from default run; increase autofix timeout ([23bfab1](https://github.com/nicsuzor/academicOps/commit/23bfab175dc0c63b766e21aa1531fd58745a3542))
- **ci:** only run autofix when CI fails; fix job-level timeout ([0eba116](https://github.com/nicsuzor/academicOps/commit/0eba116f5a5599647916c745059273f702040e52))
- **ci:** restrict CI to unit tests; mark e2e/integration tests as slow ([f89b496](https://github.com/nicsuzor/academicOps/commit/f89b49678e5e76ae457da4bf445909312c71101c))
- correct Gemini tool name translation and add settings validation ([81041fe](https://github.com/nicsuzor/academicOps/commit/81041fea3fcff678533f81e0e61f4d7640b1adc9))
- correct status symbol mapping for review/merge_ready in spec ([c64af20](https://github.com/nicsuzor/academicOps/commit/c64af20ada9f45bd5bea1b913f6a10bc876d6845))
- correct workflow name reference in user expectations ([9c942d9](https://github.com/nicsuzor/academicOps/commit/9c942d9ae7dee4c8c9056efd78ddab3b4cd38848))
- delete redundant math smoke test and update conftest ([79f52a5](https://github.com/nicsuzor/academicOps/commit/79f52a587c96a53a6a8c0b327b91a796aae4fd0d))
- finalize environmental fixes and confirm auth working ([ea7a214](https://github.com/nicsuzor/academicOps/commit/ea7a214a16d77ca33e136f2d1414355fcb1a1097))
- finalize environmental test fixes and address failures ([cd90f52](https://github.com/nicsuzor/academicOps/commit/cd90f526312857089d1036c7decc7d4b258abf7d))
- fix Enum test assignment in test_subagent_gates ([9f5f077](https://github.com/nicsuzor/academicOps/commit/9f5f0778056c4829ebd5218ba6b6b469109afb7b))
- handle nested job names in ruleset alignment check ([6680069](https://github.com/nicsuzor/academicOps/commit/6680069d252b7f9673bcbe3c63d33660f3d77d39))
- **hooks:** fix test failures and remove butler from compliance types ([a8c3c95](https://github.com/nicsuzor/academicOps/commit/a8c3c954182afb5f118a0dddaae2b56cc8759d3d))
- **hooks:** standardise verdict comparisons in gate engine ([920bb60](https://github.com/nicsuzor/academicOps/commit/920bb604122a8e8d7b7a5baf6da87bb7b4a9cd56))
- **hooks:** update Gemini sub-agent tool calls and fix uv pathing ([00184ee](https://github.com/nicsuzor/academicOps/commit/00184eec4bfa9a2458d20cb71e9b7e24a00e6f76))
- **hooks:** update Gemini sub-agent tool calls and fix uv pathing ([7afceab](https://github.com/nicsuzor/academicOps/commit/7afceab0de27ecd91c3e2d19b27ce395141c07cb))
- **hydrator:** remove positive statement from What You Don't Do section ([443c40b](https://github.com/nicsuzor/academicOps/commit/443c40b24fbcf04b0b4723039e94382fdf765115))
- implement proper logging for headless tests ([8069a49](https://github.com/nicsuzor/academicOps/commit/8069a49ee01988aaa8b53dc2891cda03b4b0cca9))
- move jsonschema from runtime to dev dependencies ([baa0c88](https://github.com/nicsuzor/academicOps/commit/baa0c88d187f62ae30a4fa4e9c7d5d9928de478e))
- **polecat:** set GH_PROMPT_DISABLED=1 for all workers; expand finish instructions ([0222ee8](https://github.com/nicsuzor/academicOps/commit/0222ee8249f54e28f2d8df50d5ff6a50eea7b1bd))
- **polecat:** set GH_PROMPT_DISABLED=1 for all workers; expand finish instructions ([9d5a929](https://github.com/nicsuzor/academicOps/commit/9d5a929b596ae072feba7129a37ff01b1a926bc5))
- **polecat:** set GH_PROMPT_DISABLED=1 for all workers; expand finish instructions ([c3972b8](https://github.com/nicsuzor/academicOps/commit/c3972b8fabd82a033c40ee5a6c214dc1ee1166a3))
- propagate git identity from source repo to clones ([1605de8](https://github.com/nicsuzor/academicOps/commit/1605de894a271303e38bc38e70f2b97c7cfa24a1))
- remove duplicate hydrator entries flagged in review ([6640a4b](https://github.com/nicsuzor/academicOps/commit/6640a4b61bbb3d7a819bb55e3a8ad4914da232c2))
- remove manual auth manipulation and finalize loud failure state ([0d2a279](https://github.com/nicsuzor/academicOps/commit/0d2a2798f69712350216fa4bbdefbd5fe0f4ea91))
- remove remaining duplicate hydrator keyword in file_index.py ([2ec7f3b](https://github.com/nicsuzor/academicOps/commit/2ec7f3bd0606349ec82592c7c9341e0badf7dbab))
- remove stale temp_path required_vars from hydrator.instruction template spec ([7e31e77](https://github.com/nicsuzor/academicOps/commit/7e31e77f5917c88b539faba86d4aff929eada9ff))
- remove unused cmd variables, merge main ([146b562](https://github.com/nicsuzor/academicOps/commit/146b562c2d1ce280d323f066fb9fe8531266a9f0))
- resolve basedpyright type error in gates engine ([d0cbab9](https://github.com/nicsuzor/academicOps/commit/d0cbab937ca04f4ebc11cc06c272c69e8758f9be))
- resolve basedpyright type error in gates engine ([acec004](https://github.com/nicsuzor/academicOps/commit/acec004c7a1a24fb4575a32a7037ce21c4c82bcb))
- resolve gemini extension install and agent tool name errors ([98cc101](https://github.com/nicsuzor/academicOps/commit/98cc1019b10bc130856df363daadc58f382455f7))
- resolve gemini extension install and agent tool name errors ([cf80100](https://github.com/nicsuzor/academicOps/commit/cf8010059943d6ebc8296c8a35106c98000c96d0))
- resolve P[#54](https://github.com/nicsuzor/academicOps/issues/54) collision, update enforcement-map and VISION.md ([80f8e01](https://github.com/nicsuzor/academicOps/commit/80f8e0156563d5f49eaf35aba7cb5c9244ff0a4e))
- resolve self-contradiction in command-intercept Feature Purpose ([8bb05a1](https://github.com/nicsuzor/academicOps/commit/8bb05a19b7a7f9201b65707f5af222d7ffb3bd39))
- resolve self-contradictions in command-intercept spec ([dfb7401](https://github.com/nicsuzor/academicOps/commit/dfb740122e4d7bf8d14040d716deef4df8f27a04))
- **spec:** align Design and Acceptance Criteria paths with current implementation ([a123b3f](https://github.com/nicsuzor/academicOps/commit/a123b3fba2361ae0577dfdf9ef2e9904f7fb2d4f))
- **spec:** align transcript naming convention with implementation ([064984a](https://github.com/nicsuzor/academicOps/commit/064984acb3043545fe0b4d8ade02cf81a88f0b23))
- **spec:** update Output Format section to reflect daily note implementation ([5a2c7b2](https://github.com/nicsuzor/academicOps/commit/5a2c7b23f953365f4fac372222076f3625c1e2fe))
- **spec:** use wikilink format for Implementation links in daily-briefing-bundle ([03d5bdb](https://github.com/nicsuzor/academicOps/commit/03d5bdbbeef831540e43f6339cc68bca763722c0))
- update Gemini tool name mapping and add settings validation ([79c9e9d](https://github.com/nicsuzor/academicOps/commit/79c9e9d9ad9847585edc48ec8c830edef6869d28))
- update test_hydrator to use task-hydrator agent name ([0bcbf83](https://github.com/nicsuzor/academicOps/commit/0bcbf833ce84dbee031fe3a46e56ee8921e4243c))
- use managed headless runners in credential isolation tests ([e63e9fa](https://github.com/nicsuzor/academicOps/commit/e63e9fa6ed17f5b1f087887f2655a10dc5e6c85c))

### Code Refactoring

- **hooks:** address PR review comments for Gemini sub-agent routing ([003d1a8](https://github.com/nicsuzor/academicOps/commit/003d1a898201294f8437d95fb261df6eff504812))
- **hydrator:** constrain hydrator to workflow planning only ([a06bf8b](https://github.com/nicsuzor/academicOps/commit/a06bf8b4505957f9443a4b1c1e1b62f670451583))
- **hydrator:** constrain hydrator to workflow planning only, forbid deep investigation ([19d1bb1](https://github.com/nicsuzor/academicOps/commit/19d1bb1e4dca9c793eaa887d8da91fc75726066e))
- **hydrator:** constrain hydrator to workflow planning, forbid deep investigation ([62f125c](https://github.com/nicsuzor/academicOps/commit/62f125c3736c28846d5d3fe50e518d063c7eb021))
- **hydrator:** strictly constrain prompt-hydrator to workflow planning, forbid codebase investigation and detailed planning to prevent Gemini agent timeouts ([bbff210](https://github.com/nicsuzor/academicOps/commit/bbff2106079b846d8a61d70e80ba3a7fa34799a9))
- remove uv-dynamic-versioning and simplify Dockerfile ([29472d0](https://github.com/nicsuzor/academicOps/commit/29472d0b6aa1f89ed57bb077227b2cdb5083c038))
- **tests:** replace requires_local_env marker with integration ([c18f41d](https://github.com/nicsuzor/academicOps/commit/c18f41d752af100eea70fabae6414cde5d4f9ff1))

### Documentation

- [aops-a64c48a2] update user expectations for constraint-checking-tests ([9fb24ce](https://github.com/nicsuzor/academicOps/commit/9fb24cea4aee625bec24038d29e30079adc3e041))
- [aops-aa9f382e] Update User Expectations for bd-markdown-integration spec ([b50b454](https://github.com/nicsuzor/academicOps/commit/b50b454c1a4417960745c30aebaacf10206cae44))
- audit spec and add User Expectations for effectual-planning-agent (aops-25f5d76e) ([45bb1cc](https://github.com/nicsuzor/academicOps/commit/45bb1cc78b8e291ae4688eddb4119faa67891a88))
- clarify hydrator/planner distinction and phase 1 prototype goals ([24dab2d](https://github.com/nicsuzor/academicOps/commit/24dab2df5cdecc40faf5e602051c4dc95879116b))
- clarify keyword matching in Epic Decomposition testable condition ([73c7dcc](https://github.com/nicsuzor/academicOps/commit/73c7dcc3ca7861c548ed3e16b705b12d086a5dd4))
- formalize loud failures and environment redirection heuristics ([e61e686](https://github.com/nicsuzor/academicOps/commit/e61e686ff1531426cdf487f9744da3d0b208fbdf))
- narrow pytest.skip exceptions and enforce loud failures ([f88342e](https://github.com/nicsuzor/academicOps/commit/f88342e5d9851da6b393322488a17014bd286852))
- **spec:** add User Expectations to research-decomposition ([c9a8fa4](https://github.com/nicsuzor/academicOps/commit/c9a8fa41cf7b331cbdad45db8be19be94c8e09c1))
- **spec:** audit and update decision-queue-spec.md ([ec5ebcd](https://github.com/nicsuzor/academicOps/commit/ec5ebcd52af802004f0846eda8453668eb86d88f))
- **spec:** fix enforcement diagram connections and clarify QA gate status ([b5f1551](https://github.com/nicsuzor/academicOps/commit/b5f1551a1674090d866fc795f15ebbf42aa95fc3))
- **specs:** add user expectations to audit-protocol.md ([af8379c](https://github.com/nicsuzor/academicOps/commit/af8379c32ae42420a8b817d3a11ef11c73479375))
- **spec:** update enforcement spec with current architecture and user expectations [aops-47e7b177] ([a68a595](https://github.com/nicsuzor/academicOps/commit/a68a595292b5c7683a06880d95bff2fd82879a91))
- **spec:** update user expectations for collaborate-workflow (aops-c3e311a9) ([fb42b9f](https://github.com/nicsuzor/academicOps/commit/fb42b9f408902a2eae7926dd501a42e8016bc123))
- use 'qa skill' instead of 'qa agent' for planning-phase verification ([a465467](https://github.com/nicsuzor/academicOps/commit/a4654678fc546fa410a8d9d5f83ec675cedfccaa))

### CI/CD

- add missing permissions to pr-pipeline.yml ([6e44dc3](https://github.com/nicsuzor/academicOps/commit/6e44dc3e24bceabf0777e9b76894601b480d308e))
- fix string type coercion in PR pipeline workflow call ([aba5c34](https://github.com/nicsuzor/academicOps/commit/aba5c34027e9dbf079d109c90cd298be8e77e3c4))
- gracefully skip merge prep approval when blocked by github actions permissions ([5f066c0](https://github.com/nicsuzor/academicOps/commit/5f066c04b8a1161de5f087852b639901fc11def9))

### Tests

- **gates:** fetch active gate from GateRegistry before monkeypatching ([9beb696](https://github.com/nicsuzor/academicOps/commit/9beb696985502c2bb57dd85f463fa01b6236c099))
- **gates:** use enum value string in monkeypatch for GateVerdict ([81a902f](https://github.com/nicsuzor/academicOps/commit/81a902f3ecabf64c499e68501eb99119866385e3))

### Miscellaneous

- delete overengineered command-intercept spec ([d6c9b27](https://github.com/nicsuzor/academicOps/commit/d6c9b27ea5dfb41a1897a802bf4c4ec711dac7a2))
- **framework:** codify non-interactive execution constraint ([763168a](https://github.com/nicsuzor/academicOps/commit/763168af91ffdbcdc13936d8e1becc167de5aafa))
- **framework:** shift to abstraction layer architecture ([27d2352](https://github.com/nicsuzor/academicOps/commit/27d2352433f732e8a4a832f869f24ad4a02c9b20))
- sync pyproject versioning with release-please ([a12feb0](https://github.com/nicsuzor/academicOps/commit/a12feb077e3dd35b1145fae177d2ca7ed5514989))
- temporarily disable all Claude Code workflows to save quota ([972ab60](https://github.com/nicsuzor/academicOps/commit/972ab60460b9c9962c30f8798c002d0e016c3461))
- temporarily disable all Claude Code workflows to save quota ([1ca9130](https://github.com/nicsuzor/academicOps/commit/1ca91304c6f83cfa5120fede15d3a02840424ede))
- update ruleset to match PR pipeline check names ([ecaedd2](https://github.com/nicsuzor/academicOps/commit/ecaedd29dc4940119acff59816ba07f836645442))

## [0.3.2](https://github.com/nicsuzor/academicOps/compare/v0.3.1...v0.3.2) (2026-03-12)

### Bug Fixes

- revert to PEP 440 versioning for Python packaging compatibility ([a6d6c73](https://github.com/nicsuzor/academicOps/commit/a6d6c733dcc1f01df81efb6032a630a97158fd90))
- use semver for prerelease versions ([0c6e1c9](https://github.com/nicsuzor/academicOps/commit/0c6e1c9d12382f4780d23cadc113b9d84991d1e5))
- use semver format for prerelease versions instead of PEP 440 ([18bcd06](https://github.com/nicsuzor/academicOps/commit/18bcd0630c76234dee8e783f8cd2c961114b3323))

### Miscellaneous

- **main:** release 0.3.1 ([6e0fd47](https://github.com/nicsuzor/academicOps/commit/6e0fd47eb4c975b2633c57e7a7f0f45c421c7e4d))
- **main:** release 0.3.1 ([0cc7507](https://github.com/nicsuzor/academicOps/commit/0cc7507af5e28bb7734723b7252285bcbfac6155))

## [0.3.1](https://github.com/nicsuzor/academicOps/compare/v0.3.0...v0.3.1) (2026-03-12)

### Bug Fixes

- revert to PEP 440 versioning for Python packaging compatibility ([a6d6c73](https://github.com/nicsuzor/academicOps/commit/a6d6c733dcc1f01df81efb6032a630a97158fd90))
- use semver for prerelease versions ([0c6e1c9](https://github.com/nicsuzor/academicOps/commit/0c6e1c9d12382f4780d23cadc113b9d84991d1e5))
- use semver format for prerelease versions instead of PEP 440 ([18bcd06](https://github.com/nicsuzor/academicOps/commit/18bcd0630c76234dee8e783f8cd2c961114b3323))

## [0.3.0](https://github.com/nicsuzor/academicOps/compare/v0.2.0...v0.3.0) (2026-03-12)

### Features

- **build:** unified local dev workflow and improved version detection ([b8854af](https://github.com/nicsuzor/academicOps/commit/b8854af1c6b3e1ee8b079fbd9553f071e06e30a7))
- **hooks:** resolve plugin root internally in router.sh ([462f0df](https://github.com/nicsuzor/academicOps/commit/462f0dfc1185c418479864f2d7fe6f61da69669b))
- **hooks:** resolve plugin root internally in router.sh ([cc8ddbc](https://github.com/nicsuzor/academicOps/commit/cc8ddbcdc5ac8512126ae9db55c7616d9d6ad29f))
- **qa:** introduce visual analysis protocol for UI evaluation ([ccbafbe](https://github.com/nicsuzor/academicOps/commit/ccbafbe4088a3012e0e9db782bf8d67ce5c8b74e))
- **qa:** introduce visual analysis protocol for UI evaluation ([746936a](https://github.com/nicsuzor/academicOps/commit/746936a632c3fdac9d564911f554893502e4173f))

### Bug Fixes

- align learn.toml transcript discovery with learn.md and P79 ([ffe98ff](https://github.com/nicsuzor/academicOps/commit/ffe98ff5dff04e117cfbfa242a0b6de2719f503b))
- check_blocked must inspect both output and result fields ([29f954b](https://github.com/nicsuzor/academicOps/commit/29f954b981e75aa0d1176f062f5b2a5224334b43))
- **ci:** use OAuth token for iOS note capture instead of API key ([10b59e3](https://github.com/nicsuzor/academicOps/commit/10b59e350507c6f728f801a453c61dba9b733c25))
- **ci:** use PAT instead of SSH deploy key for dist repo clone ([6a293dc](https://github.com/nicsuzor/academicOps/commit/6a293dc587c36d353086e5401ee8d886d772cb75))
- **hooks:** require CLAUDE_PLUGIN_ROOT explicitly, remove silent fallback ([3fae724](https://github.com/nicsuzor/academicOps/commit/3fae72467046df5a2d8ff425cce6841ec492df2c))
- Resolve CI failures and update tests ([7a4b42e](https://github.com/nicsuzor/academicOps/commit/7a4b42e5cc739f28bf1628f20b04e4958ce1bfb8))
- restore check_blocked to inspect both output and result fields ([5698199](https://github.com/nicsuzor/academicOps/commit/5698199742530239119f159e3bf11e287f4a9526))
- restore strict AND logic for glob-bypasses-hydration negative assertion ([9860a18](https://github.com/nicsuzor/academicOps/commit/9860a18788c8880c4b433bbbd144a1be1f172108))
- restrict auto-commit to ACA_DATA and sessions only ([1845589](https://github.com/nicsuzor/academicOps/commit/18455892016faeb79ed3c70fdf98b779c5e485c7))
- **tests:** Update hydration gate e2e test to read pyproject.toml instead of /etc/hosts ([03edec5](https://github.com/nicsuzor/academicOps/commit/03edec53bb5abce062811f25372483c1c086c985))
- **tests:** Update hydration gate e2e test to read pyproject.toml instead of /etc/hosts ([c518816](https://github.com/nicsuzor/academicOps/commit/c518816bf64d904de56c782d452a9b4ced274399))
- update /learn command for deployed sessions and safe issue tracking ([2c8b57c](https://github.com/nicsuzor/academicOps/commit/2c8b57c1401aaf4c2980bac0e4d947d75265c690))
- Update /learn command for deployed sessions and safe issue tracking ([a4e2db2](https://github.com/nicsuzor/academicOps/commit/a4e2db230971a35701c5e1b8cd7d612dbbe67583))
- Update /learn command for deployed sessions and safe issue tracking ([8124b82](https://github.com/nicsuzor/academicOps/commit/8124b823bd96fc1d553c14cc41a46c8015d92436))
- Update learn command and create analysis workflow ([b3e3c3e](https://github.com/nicsuzor/academicOps/commit/b3e3c3eba832d4cbfeac2d880b52580ff603baec))
- update test to check claude_code_oauth_token ([108ebdd](https://github.com/nicsuzor/academicOps/commit/108ebddba3fe57ea674aa3c7adcab54aa362bd15))
- update test to check claude_code_oauth_token instead of anthropic_api_key ([d6ace7d](https://github.com/nicsuzor/academicOps/commit/d6ace7d6331554536113a248052e353b71c61d7a))

### Tests

- Fix environment variable leakage in test_session_paths.py\n\nThe previous failures were not due to incorrect logic, but rather host environment variables (such as AOPS_SESSIONS) leaking into the test runtime and overriding temporary fixture paths. This commit adds a module-level fixture that properly unsets these variables, resolving the failures. ([55a1418](https://github.com/nicsuzor/academicOps/commit/55a1418cddf6bd7132ac1dc2cc82182c5f9de781))
- robust gate block detection helper function in E2E tests ([79b405b](https://github.com/nicsuzor/academicOps/commit/79b405b4386c1c4f6b17d436cf422a3b5ef6c3cc))
- robust gate block detection helper function in E2E tests ([fbacc02](https://github.com/nicsuzor/academicOps/commit/fbacc021a6e85b4ee25b9ccb512c39dac4735ae7))

### Miscellaneous

- remove stale SvelteKit overwhelm-dashboard source files ([af623a0](https://github.com/nicsuzor/academicOps/commit/af623a01fc246b5c66c1e2d4b2368681a6b0ec41))
- use 'uv run python' in hooks and scripts (v0.2.1) ([eb7f467](https://github.com/nicsuzor/academicOps/commit/eb7f46790f772431630857a7df79425dc14ffc5a))

## Changelog
