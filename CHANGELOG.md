# Changelog

## Unreleased

- **polecat:** PKB-poll termination watchdog kills runaway Gemini workers once their task reaches a terminal PKB status ([#521](https://github.com/nicsuzor/academicOps/issues/521))

## [0.3.18](https://github.com/nicsuzor/academicOps/compare/v0.3.17...v0.3.18) (2026-04-08)

### Features

- add CC auto mode classifier alongside custodiet gate ([#403](https://github.com/nicsuzor/academicOps/issues/403)) ([21e18af](https://github.com/nicsuzor/academicOps/commit/21e18af61d0b4ac8c388e0c897d185706e165383))
- **agents:** add critic agent — 10-move strategic review specialist ([#464](https://github.com/nicsuzor/academicOps/issues/464)) ([2d916a9](https://github.com/nicsuzor/academicOps/commit/2d916a9349d984b13a5251ba9eb7a8bc7c90d8a5))
- **agents:** add James — the orchestrator for strategic-review ([#466](https://github.com/nicsuzor/academicOps/issues/466)) ([bfece4a](https://github.com/nicsuzor/academicOps/commit/bfece4a38ec70f56cf6ef33ab5384d7b6083803d))
- auto-install autoMode classifier rules on session start ([#431](https://github.com/nicsuzor/academicOps/issues/431)) ([70280ee](https://github.com/nicsuzor/academicOps/commit/70280ee80f0055392abe24c54263597145e860a2))
- **axioms:** remove P[#48](https://github.com/nicsuzor/academicOps/issues/48) (Human Tasks Are Not Agent Tasks) + fix GHA agent axiom loading ([#465](https://github.com/nicsuzor/academicOps/issues/465)) ([24809b0](https://github.com/nicsuzor/academicOps/commit/24809b0b0c877539c3211193cfa28b491730d1d3))
- **build:** add Cowork plugin build target ([#444](https://github.com/nicsuzor/academicOps/issues/444)) ([f64e8cf](https://github.com/nicsuzor/academicOps/commit/f64e8cfc0f9dd92a63422a24da539f056aa8e048))
- **commands:** add /review-pr — James local PR review orchestrator ([#469](https://github.com/nicsuzor/academicOps/issues/469)) ([11167d2](https://github.com/nicsuzor/academicOps/commit/11167d20fec45e1f297f58e47a4d97fc4adcca2a))
- **daily:** use user prompt count as primary attention cost signal ([#421](https://github.com/nicsuzor/academicOps/issues/421)) ([9eb8442](https://github.com/nicsuzor/academicOps/commit/9eb84422c197ed6fb0393ca48e9c56446eebdbe1))
- enforcer agent — unified compliance replacing custodiet ([#435](https://github.com/nicsuzor/academicOps/issues/435)) ([07328be](https://github.com/nicsuzor/academicOps/commit/07328be7b82c1766d834dbbb150fd600052be77c))
- **james,daily:** close task completion loop on PR merge ([#479](https://github.com/nicsuzor/academicOps/issues/479)) ([cf32daa](https://github.com/nicsuzor/academicOps/commit/cf32daa50a4b204e79ef973f826733ba46112f31))
- PKB HTTP-only, transcript-based E2E, remove brain mount ([#419](https://github.com/nicsuzor/academicOps/issues/419)) ([96f8d16](https://github.com/nicsuzor/academicOps/commit/96f8d16e7ea8e158d3e8af28e80c7ab62e2fba0c))
- **pkb:** knowledge consolidation system — episodic→semantic transformation ([#445](https://github.com/nicsuzor/academicOps/issues/445)) ([aa1a33c](https://github.com/nicsuzor/academicOps/commit/aa1a33c5e3eae2f5cad7513c5389a091c866d455))
- plugin userConfig for env vars + build .git exclusion ([#418](https://github.com/nicsuzor/academicOps/issues/418)) ([0fb8112](https://github.com/nicsuzor/academicOps/commit/0fb8112e6dd63643ead49f9ea223deb665e6b78e))
- **project:** context-map audit workflow and updated map ([#460](https://github.com/nicsuzor/academicOps/issues/460)) ([3a4e958](https://github.com/nicsuzor/academicOps/commit/3a4e9582903882159588ff2fead3973549899f1b))
- **review:** add critic agent + strategic-review supervisor skill (v0.1) ([#456](https://github.com/nicsuzor/academicOps/issues/456)) ([c2b9ca8](https://github.com/nicsuzor/academicOps/commit/c2b9ca8b67d65765ee06613fd2c86794b350e4c9))
- **session-insights:** Claude-native extraction pipeline ([#449](https://github.com/nicsuzor/academicOps/issues/449)) ([99ff1fe](https://github.com/nicsuzor/academicOps/commit/99ff1fefc471d151a076a12da44bf2bb9d82850b))
- **skills:** create /project skill for repo scaffolding ([#433](https://github.com/nicsuzor/academicOps/issues/433)) ([26b26a7](https://github.com/nicsuzor/academicOps/commit/26b26a7a4cf239b0c6d742132ad87283fb29e20f))
- **sleep:** add Phase 5a — refile processing for user-flagged tasks ([#471](https://github.com/nicsuzor/academicOps/issues/471)) ([f8167db](https://github.com/nicsuzor/academicOps/commit/f8167db3db78cae4d22c8dc0cef9db6b547ea6e3))

### Bug Fixes

- add authorization & scope check to PR review agents ([#411](https://github.com/nicsuzor/academicOps/issues/411)) ([7f2e6d6](https://github.com/nicsuzor/academicOps/commit/7f2e6d66d982ce0c1fc3246efd8262b76095d2d9)), closes [#405](https://github.com/nicsuzor/academicOps/issues/405)
- **agents:** approve after self-fix — don't leave CHANGES_REQUESTED standing ([#467](https://github.com/nicsuzor/academicOps/issues/467)) ([beeb817](https://github.com/nicsuzor/academicOps/commit/beeb81707392544e6daccd457e405c9b44f5c198))
- browser tool mappings + fastmcp stdio proxy for PKB ([#422](https://github.com/nicsuzor/academicOps/issues/422)) ([46c6955](https://github.com/nicsuzor/academicOps/commit/46c695592b10e7caa4c64cdad5c2a17a3e3fca81))
- **build:** remove hardcoded model from generated GHA workflows ([#462](https://github.com/nicsuzor/academicOps/issues/462)) ([72aa4ee](https://github.com/nicsuzor/academicOps/commit/72aa4ee09e57078a543199d6ee790d1bb412f18b))
- **butler:** add gap principle and pre-flight investigation requirement ([#401](https://github.com/nicsuzor/academicOps/issues/401)) ([f52987e](https://github.com/nicsuzor/academicOps/commit/f52987e8bb9f4e0b97dc99498bd5e1f62173c8cf))
- **ci:** include dist/aops-cowork/ in build commit ([16d4bdb](https://github.com/nicsuzor/academicOps/commit/16d4bdbcbf52adea9484525586599fb43d77a458))
- **cowork:** ship MCP launch scripts in aops-cowork dist ([344aa9e](https://github.com/nicsuzor/academicOps/commit/344aa9e3d208c63843f9d4b6e626b32122178793))
- **crew:** chmod .cache dir for any-UID containers; add Docker socket tests ([#440](https://github.com/nicsuzor/academicOps/issues/440)) ([e0d51c3](https://github.com/nicsuzor/academicOps/commit/e0d51c396dc066832612e8082fd80b2e052f215c))
- **crew:** OAuth token support + Docker/Colima test fixes ([#439](https://github.com/nicsuzor/academicOps/issues/439)) ([1189130](https://github.com/nicsuzor/academicOps/commit/118913041452a69a3cf6bcb5ad83353830bdc956))
- daily skill fails fast when PKB or Outlook MCP unavailable ([ac2bdac](https://github.com/nicsuzor/academicOps/commit/ac2bdacfad695af3fc05226ea873b7a6d2d65f71))
- **daily:** research work leads synthesis, not infrastructure ([#434](https://github.com/nicsuzor/academicOps/issues/434)) ([dc265b0](https://github.com/nicsuzor/academicOps/commit/dc265b00f905a4ffcd9aa0aff03e29d88fef7be0))
- **docker:** install Claude Code via native installer instead of npm ([aab76bd](https://github.com/nicsuzor/academicOps/commit/aab76bd463cc61cf4b75d3489815d0214348ae7c))
- **docker:** make .gemini/ world-writable for host-UID containers ([67b529f](https://github.com/nicsuzor/academicOps/commit/67b529fbd4af1b3e02e36c329a71ce472af59d9f))
- **lint:** sort imports in polecat/cli.py and tests/conftest.py ([05986ac](https://github.com/nicsuzor/academicOps/commit/05986ac4e3ecef5bf615f6100ffd471422afef5b))
- mark PKB_MCP_URL as non-sensitive in plugin userConfig ([2d73986](https://github.com/nicsuzor/academicOps/commit/2d73986f5e684670ff24bb0ccaacf91e12ed267a))
- **mcp:** PATH bootstrap for plugin MCP + pre-commit hook ([#443](https://github.com/nicsuzor/academicOps/issues/443)) ([4e2c0d9](https://github.com/nicsuzor/academicOps/commit/4e2c0d9551e42c7963982f511c9faa7731035365))
- **merge-prep:** re-qualify PRs when late reviews arrive after success ([#436](https://github.com/nicsuzor/academicOps/issues/436)) ([74c234a](https://github.com/nicsuzor/academicOps/commit/74c234a9dd6aeb623f16be898116316d9d5b4efd))
- polecat init/sync fail fast when sessions repo missing ([65319b4](https://github.com/nicsuzor/academicOps/commit/65319b440a100c5d0a661fb7c08ae07d7f0e7678))
- **polecat:** Colima socket mount + remove pkb binary tests ([48e6d20](https://github.com/nicsuzor/academicOps/commit/48e6d206a878bf07000832512ee4e6d7f2e9f363))
- **polecat:** discover Docker socket for Colima on macOS ([#475](https://github.com/nicsuzor/academicOps/issues/475)) ([f611aef](https://github.com/nicsuzor/academicOps/commit/f611aef8e6d204e1f12b1cde96f187cc644a7dda))
- **polecat:** e2e test timeouts, crew sandbox, stale crew clones ([#442](https://github.com/nicsuzor/academicOps/issues/442)) ([9e8107c](https://github.com/nicsuzor/academicOps/commit/9e8107c8faa8b749e4c66eeb9bbce656f46728fc))
- **polecat:** make replicated Gemini auth dir writable by sandbox container ([0b468be](https://github.com/nicsuzor/academicOps/commit/0b468bee694b85a6e3ebcc77b35f9c8e609b4e73))
- **polecat:** split Docker -it into separate -i -t flags for interactive mode ([c4f69bb](https://github.com/nicsuzor/academicOps/commit/c4f69bb33e4c2a9b9122d66cc3a56e4a3f9c1cc6))
- **polecat:** switch pkb_bridge from stdio subprocess to HTTP transport ([e313325](https://github.com/nicsuzor/academicOps/commit/e313325480f0e7ee05bf2dd31cebffa8b38a74ea))
- **polecat:** wrap Gemini in our Docker container instead of --sandbox ([a20c2c6](https://github.com/nicsuzor/academicOps/commit/a20c2c6e241be2af8d0e62c73137aa9d6e1f1897))
- re-apply agent rename (pauli/rbg/marsha) from PR [#458](https://github.com/nicsuzor/academicOps/issues/458) ([#463](https://github.com/nicsuzor/academicOps/issues/463)) ([8a042c1](https://github.com/nicsuzor/academicOps/commit/8a042c1a659bf9a82bc671b18d469f2f1d613a70))
- recover unmerged commits from stale PR branches ([#426](https://github.com/nicsuzor/academicOps/issues/426)) ([14768af](https://github.com/nicsuzor/academicOps/commit/14768af3a4b8004f119610506bec1067cdcad646))
- stop staging host .mcp.json into crew containers ([5244155](https://github.com/nicsuzor/academicOps/commit/52441556062f1424feee914685e20c6847be880a))
- stop staging trustedFolders.json into crew containers ([8787841](https://github.com/nicsuzor/academicOps/commit/87878415845a34c6326260f3e44286eabe9173f9))
- **tests:** delete archived tests with broken imports, fix session_start imports ([d85a909](https://github.com/nicsuzor/academicOps/commit/d85a909513d18510536a9a9366fbb103ecf6d418))
- **tests:** delete dist/ hook tests — dist no longer built locally ([a14d385](https://github.com/nicsuzor/academicOps/commit/a14d38522ea819a52353ff7271e89a60f90a7bfb))
- **tests:** make E2E invocation path assertions resilient to LLM behavior ([6c51683](https://github.com/nicsuzor/academicOps/commit/6c51683b93cedfe2bff4f991a24711dd67e4b809))
- **tests:** remove dummy-key gemini tests, fix hooks assertion and session discovery ([e148934](https://github.com/nicsuzor/academicOps/commit/e148934a05010aa9a1d9dd19cd3c70b167631beb))
- **tests:** replace illegitimate pytest.skip with hard assertions ([704bdcf](https://github.com/nicsuzor/academicOps/commit/704bdcfb1b35584cb45047c625f2af9434fe5344))
- **tests:** reset fixture task via PKB HTTP API, not local file ([b6c0090](https://github.com/nicsuzor/academicOps/commit/b6c009099685571823c2426d03272ca3e02ce442))
- **tests:** support Gemini session files in E2E test discovery ([d2e675c](https://github.com/nicsuzor/academicOps/commit/d2e675c3706008e9a0296752b8549eca3950d95c))
- **tests:** unify run/crew paths on MEGA_PROMPT, remove PKB tool call ([4593c89](https://github.com/nicsuzor/academicOps/commit/4593c89aecfb221df46c34028b23e003d82782d1))

### Code Refactoring

- **agents:** unify agent names — custodiet→rbg, qa→marsha, critic→pauli ([47671ea](https://github.com/nicsuzor/academicOps/commit/47671ead8729959478b7018e8fadf7d3063dd197))
- centralise PATH bootstrap for CLI tool detection ([#447](https://github.com/nicsuzor/academicOps/issues/447)) ([47e9009](https://github.com/nicsuzor/academicOps/commit/47e9009947e929e193d0e5240564f6790f7eae6b))
- install aops from GitHub releases instead of building from source in Docker ([95947aa](https://github.com/nicsuzor/academicOps/commit/95947aa5410bb226854e08829f8723afec10d922))
- move butler skill to .agent/skills/framework (project-local) ([#414](https://github.com/nicsuzor/academicOps/issues/414)) ([88f4c7a](https://github.com/nicsuzor/academicOps/commit/88f4c7a23ea819c118e7c0082dcc2510fe08a588))
- **polecat:** replace bind mounts with docker cp for staging files ([c74b205](https://github.com/nicsuzor/academicOps/commit/c74b2050c73a60e23882a4b22d46d9fee2165eae))
- rename .agent/ to .agents/ for interop standard alignment ([#441](https://github.com/nicsuzor/academicOps/issues/441)) ([1b4818f](https://github.com/nicsuzor/academicOps/commit/1b4818f68dd78e290b4c0802a06f2c325dd949d6))
- rename swarm-supervisor to supervisor with epic-level ownership ([#400](https://github.com/nicsuzor/academicOps/issues/400)) ([ec9e788](https://github.com/nicsuzor/academicOps/commit/ec9e788eb9c9d33596e1af75ce18225852f7c986))
- **review-enforcement:** consolidate critic, enforcer, qa agents into fewer canonical homes ([#457](https://github.com/nicsuzor/academicOps/issues/457)) ([50601b4](https://github.com/nicsuzor/academicOps/commit/50601b4458d76e06998c364807f39344b1dfc976))

### Documentation

- **taxonomy:** rewrite with information-theoretic model ([#473](https://github.com/nicsuzor/academicOps/issues/473)) ([cd864de](https://github.com/nicsuzor/academicOps/commit/cd864de4b7e530d52075d7b6893aa064f20ff3c2))

### Tests

- add test for extension clean install and fix validation errors ([#483](https://github.com/nicsuzor/academicOps/issues/483)) ([341db2a](https://github.com/nicsuzor/academicOps/commit/341db2a7f8f1a9c1e37d08629f719d93f9952f6a))
- **e2e:** remove fake-repo Docker isolation tests ([347914f](https://github.com/nicsuzor/academicOps/commit/347914f8195064346cc0d01488b56a09aeb83800))

### Miscellaneous

- **dist:** separate build artifacts into nicsuzor/aops distribution repo ([#459](https://github.com/nicsuzor/academicOps/issues/459)) ([8a3604a](https://github.com/nicsuzor/academicOps/commit/8a3604aef3f2999a352dbd407f1db6cd4aff3846))
- Release v0.3.16 [skip ci] ([08d79ca](https://github.com/nicsuzor/academicOps/commit/08d79ca70fa1cc29486bd0454a90f15853652b8c))
- remove redundant axiom-review pipeline; document execution environments ([#468](https://github.com/nicsuzor/academicOps/issues/468)) ([9477f88](https://github.com/nicsuzor/academicOps/commit/9477f88291874a5a428bb35b42a030eb31f25bda))
- Testing release v0.3.16-dev.65 [skip ci] ([b1ed9b5](https://github.com/nicsuzor/academicOps/commit/b1ed9b5ebd46daa1de4f4b0348e8fb7150991fe5))
- Testing release v0.3.16-dev.66 [skip ci] ([e3105c6](https://github.com/nicsuzor/academicOps/commit/e3105c6a23290a8fbd95576298bbb295476b1b0b))
- Testing release v0.3.16-dev.67 [skip ci] ([336c098](https://github.com/nicsuzor/academicOps/commit/336c098de9c38045d36aff91885b43a00fbe1a29))
- Testing release v0.3.16-dev.68 [skip ci] ([5bcd36d](https://github.com/nicsuzor/academicOps/commit/5bcd36d5c39f1b10c8cde2993c935a5ce0517e60))
- Testing release v0.3.16-dev.69 [skip ci] ([979237e](https://github.com/nicsuzor/academicOps/commit/979237e40d4b29aae0d4847138bda08ebe8f7129))
- Testing release v0.3.16-dev.70 [skip ci] ([0274e2a](https://github.com/nicsuzor/academicOps/commit/0274e2aecd405c2bd21ed5de47a018ee85e41139))
- Testing release v0.3.16-dev.71 [skip ci] ([285675e](https://github.com/nicsuzor/academicOps/commit/285675e3adb5d6e11195cf7ca46927f76a2f6c15))
- Testing release v0.3.16-dev.72 [skip ci] ([cf0e7f5](https://github.com/nicsuzor/academicOps/commit/cf0e7f599d8b778cf5d6e3b07bc84da62fb86d77))
- Testing release v0.3.16-dev.73 [skip ci] ([cab9801](https://github.com/nicsuzor/academicOps/commit/cab98017a12c7b057d16d3183725632a0f90af34))
- Testing release v0.3.16-dev.74 [skip ci] ([c01199d](https://github.com/nicsuzor/academicOps/commit/c01199de71a217d862a966b6fb4251dfa775b8e9))
- Testing release v0.3.16-dev.75 [skip ci] ([fcd18fe](https://github.com/nicsuzor/academicOps/commit/fcd18fe26bb9474c54bf3fd25fd2ac39ec32f8b1))
- Testing release v0.3.16-dev.76 [skip ci] ([eb255b6](https://github.com/nicsuzor/academicOps/commit/eb255b6716a5cdb0ad99378c7552b4279960af47))
- Testing release v0.3.16-dev.77 [skip ci] ([79240e4](https://github.com/nicsuzor/academicOps/commit/79240e4df750a787bec6d97793cbbc9199c18fb8))
