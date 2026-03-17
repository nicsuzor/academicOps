# Changelog

## [0.3.11](https://github.com/nicsuzor/academicOps/compare/v0.3.10...v0.3.11) (2026-03-17)


### Features

* **hydrator:** add JIT quality escalation process and hook gate context ([341fcf4](https://github.com/nicsuzor/academicOps/commit/341fcf4d2e4662a5be3df513442432490e2328a2))


### Bug Fixes

* cron pipeline uses polecat sync correctly ([de9e919](https://github.com/nicsuzor/academicOps/commit/de9e91976d39fb10cde8bc3220da8cdd95778894))
* cron pipeline uses polecat sync correctly, remove dead viz step ([efc1ccf](https://github.com/nicsuzor/academicOps/commit/efc1ccffa66f6fee6472c5e493b29b24748018cb))
* **install:** resolve uv path at install time for cron jobs ([8930976](https://github.com/nicsuzor/academicOps/commit/893097639ecb6c03795f967f9b8794756488eabd))
* **polecat:** forward gate mode env vars + hydrator JIT quality escalation ([4d52c36](https://github.com/nicsuzor/academicOps/commit/4d52c3648f7f88f809ede6b59f29bcb547c85e7a))
* **polecat:** forward gate mode env vars into Docker crew containers ([3948148](https://github.com/nicsuzor/academicOps/commit/39481484280a7f5d3c7d149d7f1f42d493c2598b))
* **polecat:** resolve crew container env forwarding, sync conflict, and extension replication ([d0bf8c3](https://github.com/nicsuzor/academicOps/commit/d0bf8c3631125c1ca1193f1dccb628fe1e080d7d))
* resolve polecat crew container extension failure ([6d6187e](https://github.com/nicsuzor/academicOps/commit/6d6187e591e974a4ef1048bd2603683557e3a811))


### Miscellaneous

* configure release-please to update version in uv.lock ([a3b2754](https://github.com/nicsuzor/academicOps/commit/a3b2754b56a509339d5595e3504142b3ccdd32cc))
* configure release-please to update version in uv.lock ([937d87e](https://github.com/nicsuzor/academicOps/commit/937d87e068449ac488dbdbcc81f59bd2d043963a))

## [0.3.10](https://github.com/nicsuzor/academicOps/compare/v0.3.9...v0.3.10) (2026-03-16)


### Bug Fixes

* **build:** restore hooks wrapper in Gemini hooks.json ([fbf083b](https://github.com/nicsuzor/academicOps/commit/fbf083b6d859b40b5b570ab07c6f18aefbbbd0ed))
* **build:** restore hooks wrapper in Gemini hooks.json — hooks must be an object ([835b143](https://github.com/nicsuzor/academicOps/commit/835b1430b782d42643838e9ebba4daad8235002b))

## [0.3.9](https://github.com/nicsuzor/academicOps/compare/v0.3.8...v0.3.9) (2026-03-16)

### Bug Fixes

- address Gemini review feedback on safe_copy/safe_symlink and loop constant ([8102585](https://github.com/nicsuzor/academicOps/commit/81025853ca7ba251f8a0491904be7d7f4e728fb6))
- **build:** correct Gemini hook mappings and include AfterAgent ([70e22c4](https://github.com/nicsuzor/academicOps/commit/70e22c4a3ade09a31c3cea05dffc40ddd997d7fa))
- **build:** correct Gemini hook mappings and include AfterAgent ([9193d38](https://github.com/nicsuzor/academicOps/commit/9193d38c8c835358234697f7205d01a471e01cce))

## [0.3.8](https://github.com/nicsuzor/academicOps/compare/v0.3.7...v0.3.8) (2026-03-16)

### Bug Fixes

- **build:** correct Gemini hooks.json structure ([55a760b](https://github.com/nicsuzor/academicOps/commit/55a760b7362c2a5c0c963463de2325babb33b25c))
- **build:** remove redundant top-level 'hooks' key from Gemini hooks.json ([b9f0169](https://github.com/nicsuzor/academicOps/commit/b9f0169c5ed786174ce04d63238df12da5efdbd0))

## [0.3.7](https://github.com/nicsuzor/academicOps/compare/v0.3.6...v0.3.7) (2026-03-16)

### Bug Fixes

- **tests:** remove redundant HOME env var test for Docker ([00c8b0c](https://github.com/nicsuzor/academicOps/commit/00c8b0c5944f65829f803664f1de46f3720f913b))
- **tests:** remove redundant HOME env var test for Docker ([6254f0b](https://github.com/nicsuzor/academicOps/commit/6254f0ba9ae91413253b77a9e481c9a697a45654))

## [0.3.6](https://github.com/nicsuzor/academicOps/compare/v0.3.5...v0.3.6) (2026-03-16)

### Features

- **aops-core:** update `build_audit_session_context` to filter recent history ([f095d79](https://github.com/nicsuzor/academicOps/commit/f095d79f7e5b0b4e95c7a5d8fad3aff7500334ea))
- **aops-core:** update `build_audit_session_context` to filter recent history ([47a2f01](https://github.com/nicsuzor/academicOps/commit/47a2f01f0a53d4681745281c3049ee55b6af93ca))
- **docker:** install code quality tools ([3b876bd](https://github.com/nicsuzor/academicOps/commit/3b876bd70be90e9aec4788b866fbfcee45acfb05))
- **learn:** enforce root cause analysis and ENFORCEMENT.md integration ([cf8d4de](https://github.com/nicsuzor/academicOps/commit/cf8d4dea9e7b6b37289f5b234e7540f06fca6887))
- persist Claude session transcripts from Docker crew sessions ([4b4e643](https://github.com/nicsuzor/academicOps/commit/4b4e6435e7a4ddb976cf3e9d6ccb9238f94abd69))
- **polecat:** add setup command and install claude extensions ([3b5d6ce](https://github.com/nicsuzor/academicOps/commit/3b5d6ce0b27692d6b5323ce38e0375fc44d329cd))
- **polecat:** configure git identity, credentials, and timezone in Docker ([2404d5d](https://github.com/nicsuzor/academicOps/commit/2404d5daaa5955398e2a15a7342b89bec2cd88c5))
- **polecat:** enable 24-bit color for interactive crew sessions ([004f4a6](https://github.com/nicsuzor/academicOps/commit/004f4a624e489aa9e4abe29546655967406bfaf9))
- **polecat:** enable 24-bit color for interactive sessions ([37ee1b9](https://github.com/nicsuzor/academicOps/commit/37ee1b91711bfe098f2c03d6544e49bc9b5781c0))
- **polecat:** mount host uv cache into docker and forward github tokens ([de84af2](https://github.com/nicsuzor/academicOps/commit/de84af2a08cda01c6ab075ae5c2ee591c2209db2))
- **polecat:** persist Claude session transcripts from Docker crew sessions ([1fe585b](https://github.com/nicsuzor/academicOps/commit/1fe585b153a6a31df6df79aa18f52ef4179a59d1))
- **polecat:** persist crew session transcripts from Docker ([dd72beb](https://github.com/nicsuzor/academicOps/commit/dd72beb199a709a2436cd45a6c6b7eeb270beee3))
- remove ogdf and all task_graph scripts ([f54164d](https://github.com/nicsuzor/academicOps/commit/f54164df5c276bce3ccca19faafac5a9ca519383))
- **sleep:** add active-loop protocol and graph maintenance phases ([aec6020](https://github.com/nicsuzor/academicOps/commit/aec6020d1c52278812d39eba5e4b12a8d59c60eb))
- **tests:** add claude_docker fixture for containerised integration tests ([2aa5e52](https://github.com/nicsuzor/academicOps/commit/2aa5e52c54612031c7a3beea66092f41b806f06c))
- **tests:** extend cli_headless to 4 backends with Gemini auth replication ([7c3d520](https://github.com/nicsuzor/academicOps/commit/7c3d5209679e7cf359bebb7c674b8a983d5fccd2))

### Bug Fixes

- add requires_local_env marker to TestHookLogDiscovery ([8d075e9](https://github.com/nicsuzor/academicOps/commit/8d075e9a47b409dda064ef3521dfa9eff53dd176))
- address review feedback — temp file leak and silent error swallowing ([fe8d40b](https://github.com/nicsuzor/academicOps/commit/fe8d40b33cc4307010ffdc3b5030b73b5458e214))
- address review feedback and CI test failures ([1ab4d8b](https://github.com/nicsuzor/academicOps/commit/1ab4d8b7c599ab32978148e3630c684025e1574f))
- **ci:** cancel duplicate build runs when one is already in progress ([a625130](https://github.com/nicsuzor/academicOps/commit/a625130db680c1a8351893cb91d0ba6e2a029265))
- **ci:** cancel duplicate build runs when one is already in progress ([756e683](https://github.com/nicsuzor/academicOps/commit/756e683d9ba97498ac7e5d5f2c18388cf6a7ba53))
- **ci:** fix autofix auth, add merge-prep agent, tune merge-prep qualification ([874b007](https://github.com/nicsuzor/academicOps/commit/874b007515af6c3e06343ce83f6bb5fed0abf1d4))
- **ci:** fix autofix auth, add merge-prep agent, tune merge-prep qualification ([413e460](https://github.com/nicsuzor/academicOps/commit/413e46045b192e140ce4acdf00c9d12fd3b2a045))
- **docker:** fix GPG key signing, consolidate Makefile, fix .dockerignore ([e67333b](https://github.com/nicsuzor/academicOps/commit/e67333ba257cf67c4b2530efff4242f9831a24ae))
- **docker:** install plugin at build time, mount only auth files at runtime ([c12ab87](https://github.com/nicsuzor/academicOps/commit/c12ab87dc14d58ef991773a9d81de342763461b9))
- **docker:** install plugin at build time, mount only auth files at runtime ([967c539](https://github.com/nicsuzor/academicOps/commit/967c539e8723d3aec9fd0fe1f40b9de8b5c39d53))
- **docker:** set UV_CACHE_DIR to /tmp/uv-cache for non-root container user ([2c6bc18](https://github.com/nicsuzor/academicOps/commit/2c6bc181f60f3fc08e546a7770512fa89fdab29d))
- enable plugin hooks in Docker E2E tests and add debug diagnostics ([522a1a1](https://github.com/nicsuzor/academicOps/commit/522a1a1236aaa488d9d88910fe647265faf917d9))
- **install:** show install sources, simplify version report, add dock… ([14a20c9](https://github.com/nicsuzor/academicOps/commit/14a20c94653972b99960d0a4a575520bc0e89d15))
- **install:** show install sources, simplify version report, add docker check ([501ab2d](https://github.com/nicsuzor/academicOps/commit/501ab2d937cc822fdba149dfc1fc083af20dc37c))
- **install:** uninstall before install and report versions; bump to 0.3.4 ([66377af](https://github.com/nicsuzor/academicOps/commit/66377af6195e08f2f1ed17ab938508ae0e1ee888))
- mark CLI-dependent integration tests as requires_local_env ([e226862](https://github.com/nicsuzor/academicOps/commit/e226862eeca57b98ec6e3e152b59ba285fc83702))
- plugin load failure — remove duplicate hooks decl, add uninstall-dev ([a8cfd58](https://github.com/nicsuzor/academicOps/commit/a8cfd58e82f3e50f3f4aff2a6356d9b799557938))
- **polecat:** detect system timezone instead of hardcoding Australia/Brisbane ([2bbf81f](https://github.com/nicsuzor/academicOps/commit/2bbf81fd3493561e321d28675692174e1b096ec5))
- **polecat:** Docker containerization + sync consolidation ([4634fce](https://github.com/nicsuzor/academicOps/commit/4634fced1da3a345753cc20935c0410f2a6df687))
- **polecat:** fix Docker execution for Claude and Gemini crew/run ([e2b7cbc](https://github.com/nicsuzor/academicOps/commit/e2b7cbc0aaa53414cd5e99b9beeddec2facfed7c))
- **polecat:** fix GEMINI_CLI_HOME path in _replicate_gemini_auth ([9685455](https://github.com/nicsuzor/academicOps/commit/96854557712b4870496108a22971107e4dda21d9))
- **polecat:** mount pkb binary and ACA_DATA in Docker container ([277c426](https://github.com/nicsuzor/academicOps/commit/277c42682316bf0962408013b60faad3baa2b347))
- **polecat:** remove --tmpfs mount that hides .claude config in Docker ([f209b85](https://github.com/nicsuzor/academicOps/commit/f209b8524caa40bae3e3b41944273c3095ef82a2))
- **polecat:** remove incorrect Gemini key forwarding from Claude Docker path ([0ee26ae](https://github.com/nicsuzor/academicOps/commit/0ee26ae257689ac3b0fc6e9810129b19836a9337))
- **polecat:** revert read-only .claude mount; fix crew terminology ([b3335e7](https://github.com/nicsuzor/academicOps/commit/b3335e7d334de2f10f75abc5cb32f518e0af1e9a))
- **polecat:** save remote version before auto-resolving rebase conflicts ([d314493](https://github.com/nicsuzor/academicOps/commit/d314493972ccaf3118fab91ed661856bcaec8f78))
- **polecat:** semver NVM sort, auth key forwarding, read-only config mounts ([9c0e856](https://github.com/nicsuzor/academicOps/commit/9c0e856ca87fbace70ac92ec01f87d1e93d2c337))
- prevent eager version bumps pre-v1 ([ea4747a](https://github.com/nicsuzor/academicOps/commit/ea4747ad13d560b8f1b62d8e9a266c84f28f20d8))
- properly strip mcp__ prefix in gemini tool translation ([efbe8d6](https://github.com/nicsuzor/academicOps/commit/efbe8d6cc07fbb63e84cc63313b63e949b16e272))
- remove insecure chmod 777 from Dockerfiles; add CLI path resolution to run() ([f5923bf](https://github.com/nicsuzor/academicOps/commit/f5923bff9530e8b476517982423f226ed79de548))
- remove redundant asserts after pytest.skip and delete plan.md ([12341d2](https://github.com/nicsuzor/academicOps/commit/12341d2d429e9a260af2801c9aa0f241219b57fc))
- remove stale tests for deleted symbols and fix test markers ([2fff096](https://github.com/nicsuzor/academicOps/commit/2fff096bee650374a9e261e182857b341183965f))
- resolve 'expected' pending checks in PR pipeline and bump to 0.3.3 ([4752d8b](https://github.com/nicsuzor/academicOps/commit/4752d8b578fca2e0f901cfa00eaac224274dda2f))
- restore status descriptions and correct tool names in planning SKILL.md ([2aaf302](https://github.com/nicsuzor/academicOps/commit/2aaf3023567f560e693fd1b79595f63b9060d5f4))
- **sleep:** add repo topology guardrail to prevent false task cancellation ([aa63098](https://github.com/nicsuzor/academicOps/commit/aa630983508f0769d1f150c86ac03fa073bb49ee)), closes [#82](https://github.com/nicsuzor/academicOps/issues/82)
- sync version to 0.3.5 and fix release-please config ([7999621](https://github.com/nicsuzor/academicOps/commit/799962163873db5d4eefbed75704edae02c86ed0))
- sync version to 0.3.5 and fix release-please config and uv.lock ([8769b0f](https://github.com/nicsuzor/academicOps/commit/8769b0f4a7f352091d8ec4cd5deb43dc16fdf940))
- **tests:** add sys.path for polecat in _run_gemini_docker ([54390fb](https://github.com/nicsuzor/academicOps/commit/54390fb0bbb038f89801cbfe916d652384b039e5))
- **tests:** fix false positive in test_no_pkb_mount_when_missing ([6a58708](https://github.com/nicsuzor/academicOps/commit/6a58708afa423244a9857caafd55e7d3c8d9ff6e))
- use consistent {repo} placeholder in merge-prep agent ([07f6ed4](https://github.com/nicsuzor/academicOps/commit/07f6ed42d7dc99ec04c9a69b62f8113d10f6bae7))
- wrap !failure() && !cancelled() in ${{ }} expression syntax ([6be8b3e](https://github.com/nicsuzor/academicOps/commit/6be8b3e3b0ee9a6672889bfe129c9024ad35a14e))
- wrap GitHub Actions expression in ${{ }} on pr-pipeline.yml line 69 ([5f3d604](https://github.com/nicsuzor/academicOps/commit/5f3d604849417006642f7a3fd342b0d45cfa9f97))

### Code Refactoring

- delete builder.py; gate engine handles hydration natively ([240f011](https://github.com/nicsuzor/academicOps/commit/240f011e88ef884656a4d558c489f1f49e2ae318))
- delete hydrator context injection pipeline + planning skill package ([1e5af22](https://github.com/nicsuzor/academicOps/commit/1e5af220a8518288274d3db64336c39b331bc6e7))
- delete hydrator context injection pipeline entirely ([831ff0c](https://github.com/nicsuzor/academicOps/commit/831ff0cc02988769762257615d0e5e5bd507b9f8))
- make is_hydratable declarative; delete skip_check + user_prompt_submit ([281e973](https://github.com/nicsuzor/academicOps/commit/281e9733a40c28aab299c031351b5e0a405d9e6a))
- make is_hydratable declarative; delete skip_check + user_prompt_submit ([715cea9](https://github.com/nicsuzor/academicOps/commit/715cea901654cca1dbb3130119e8eaef5927f19a))
- migrate planning to standalone skill, delete dynamic hydrator injection ([61dbace](https://github.com/nicsuzor/academicOps/commit/61dbace9aa0b256fed56bf19c9cd20b5b2990b60))
- **polecat:** merge repo-sync.sh into pc sync command ([01c18c6](https://github.com/nicsuzor/academicOps/commit/01c18c6d673cc9af7c73185fa22255150455ed31))
- unify main and sandbox docker images ([dae4207](https://github.com/nicsuzor/academicOps/commit/dae4207660bd4ac7bfd9534f75d208cd018ef270))

### Miscellaneous

- **main:** release 0.4.0 ([35f341f](https://github.com/nicsuzor/academicOps/commit/35f341f3320babe8b5feda514933de87b21049f1))
- **main:** release 0.4.0 ([29df15f](https://github.com/nicsuzor/academicOps/commit/29df15fb4318236f12e6972878908f8a250257d7))
- remove bump-my-version ([a50cdef](https://github.com/nicsuzor/academicOps/commit/a50cdef33695600c6675939e74929cd97ce87102))
- remove standalone repo-sync.sh (superseded by pc sync) ([bb2ed24](https://github.com/nicsuzor/academicOps/commit/bb2ed24b240ae8542bb8aa078c6fb02e5192e420))

## [0.4.0](https://github.com/nicsuzor/academicOps/compare/v0.3.4...v0.4.0) (2026-03-16)

### Features

- add multi-client Docker environment and verification harness ([2aad6ef](https://github.com/nicsuzor/academicOps/commit/2aad6efbf16e5a468c388de6e1c7a06a75e62f64))
- **architecture:** merge hydration with formal decomposition ([af06c82](https://github.com/nicsuzor/academicOps/commit/af06c8261cd54714da120b46e1e63beedae9a1ef))
- **architecture:** redefine hydration as task enrichment ([f6a8ffa](https://github.com/nicsuzor/academicOps/commit/f6a8ffa32850a7b8e29f42a11fb51967a067ae8c))
- consolidate hydrators into single hydrator skill ([512d766](https://github.com/nicsuzor/academicOps/commit/512d7666dcb1455abccb8b2f797389b80cc7dbb6))
- consolidate hydrators into single hydrator skill, move WORKFLOWS.md into skill package ([6ba1c18](https://github.com/nicsuzor/academicOps/commit/6ba1c182f3402c60c85a0889cc612986d29fc5c6))
- **docker:** install code quality tools ([3b876bd](https://github.com/nicsuzor/academicOps/commit/3b876bd70be90e9aec4788b866fbfcee45acfb05))
- Gemini Docker sandbox for crew workers + typecheck fix ([d7a47ec](https://github.com/nicsuzor/academicOps/commit/d7a47ec42b5e2237a4d2f69b9723d9a73d267cb6))
- **hydrator:** implement task-hydrator Phase 1 prototype ([0486953](https://github.com/nicsuzor/academicOps/commit/04869533c6d2e6727a36c88fb32595737be94a20))
- Multi-client Docker Environment and Verification ([67786b8](https://github.com/nicsuzor/academicOps/commit/67786b876383969dd97f657d664540e9b7b46f60))
- **polecat:** add setup command and install claude extensions ([3b5d6ce](https://github.com/nicsuzor/academicOps/commit/3b5d6ce0b27692d6b5323ce38e0375fc44d329cd))
- **polecat:** configure git identity, credentials, and timezone in Docker ([2404d5d](https://github.com/nicsuzor/academicOps/commit/2404d5daaa5955398e2a15a7342b89bec2cd88c5))
- **polecat:** enable 24-bit color for interactive crew sessions ([004f4a6](https://github.com/nicsuzor/academicOps/commit/004f4a624e489aa9e4abe29546655967406bfaf9))
- **polecat:** enable 24-bit color for interactive sessions ([37ee1b9](https://github.com/nicsuzor/academicOps/commit/37ee1b91711bfe098f2c03d6544e49bc9b5781c0))
- **polecat:** mount host uv cache into docker and forward github tokens ([de84af2](https://github.com/nicsuzor/academicOps/commit/de84af2a08cda01c6ab075ae5c2ee591c2209db2))
- prune old plugin cache versions in install-dev ([eb08972](https://github.com/nicsuzor/academicOps/commit/eb0897254a495c745488af8208585923cfaf4d91))
- remove ogdf and all task_graph scripts ([f54164d](https://github.com/nicsuzor/academicOps/commit/f54164df5c276bce3ccca19faafac5a9ca519383))
- replace polecat worktrees with local clones ([25ec62e](https://github.com/nicsuzor/academicOps/commit/25ec62e292169d45cebb0e2a189997d8e265e02a))
- replace polecat worktrees with local clones ([37c6c24](https://github.com/nicsuzor/academicOps/commit/37c6c24217b7078e6fd06850ba78ab8fd2d5776d))
- **tests:** add claude_docker fixture for containerised integration tests ([2aa5e52](https://github.com/nicsuzor/academicOps/commit/2aa5e52c54612031c7a3beea66092f41b806f06c))
- **tests:** extend cli_headless to 4 backends with Gemini auth replication ([7c3d520](https://github.com/nicsuzor/academicOps/commit/7c3d5209679e7cf359bebb7c674b8a983d5fccd2))
- wrap polecat agent execution in docker container ([46d1900](https://github.com/nicsuzor/academicOps/commit/46d19009acc158ef931495166c8e72166e5396fc))
- wrap polecat agent execution in docker container ([4a54977](https://github.com/nicsuzor/academicOps/commit/4a54977df237d6d150db7e8e35a6202c222c7552))

### Bug Fixes

- add requires_local_env marker to TestHookLogDiscovery ([8d075e9](https://github.com/nicsuzor/academicOps/commit/8d075e9a47b409dda064ef3521dfa9eff53dd176))
- add requires_local_env markers and fix test_gate_path_not_in_tmp ([5c84d30](https://github.com/nicsuzor/academicOps/commit/5c84d3041829c394b458fa5306c83d41b387e110))
- add requires_local_env markers to tests needing CLI/env setup ([1da8e51](https://github.com/nicsuzor/academicOps/commit/1da8e5100c10ed53c78d6f3de0761b72915fab24))
- address review feedback — enforcement map, hook templates, VISION.md ([1ba772e](https://github.com/nicsuzor/academicOps/commit/1ba772efe82c1dc70ac5e56af74fe5ef2689b6b3))
- address review feedback — npm cache cleanup and Docker image cleanup trap ([f52b75c](https://github.com/nicsuzor/academicOps/commit/f52b75c9e912df1b8cc3899581a34d43e9f3b917))
- address review feedback — temp file leak and silent error swallowing ([fe8d40b](https://github.com/nicsuzor/academicOps/commit/fe8d40b33cc4307010ffdc3b5030b73b5458e214))
- address test failures and environmental dependencies ([cf35b47](https://github.com/nicsuzor/academicOps/commit/cf35b47578931aed45e797572bbd4fa629dbe903))
- align command-intercept spec with P[#8](https://github.com/nicsuzor/academicOps/issues/8) fail-fast requirement ([ba3be29](https://github.com/nicsuzor/academicOps/commit/ba3be29ae2f6c1aa05168d4d1a8692cffb644ca1))
- align test stub with fail-fast config behavior ([0a98a21](https://github.com/nicsuzor/academicOps/commit/0a98a21e4ec9340519d19c89bba46debfb43670e))
- **ci:** add 120s settle delay before agent-fix; revert failure-only condition ([5dde060](https://github.com/nicsuzor/academicOps/commit/5dde060564fd61bfdf5d166c9a10d2a7ecaa9e2c))
- **ci:** cancel duplicate build runs when one is already in progress ([a625130](https://github.com/nicsuzor/academicOps/commit/a625130db680c1a8351893cb91d0ba6e2a029265))
- **ci:** cancel duplicate build runs when one is already in progress ([756e683](https://github.com/nicsuzor/academicOps/commit/756e683d9ba97498ac7e5d5f2c18388cf6a7ba53))
- **ci:** exclude demo tests from default run; increase autofix timeout ([23bfab1](https://github.com/nicsuzor/academicOps/commit/23bfab175dc0c63b766e21aa1531fd58745a3542))
- **ci:** fix autofix auth, add merge-prep agent, tune merge-prep qualification ([874b007](https://github.com/nicsuzor/academicOps/commit/874b007515af6c3e06343ce83f6bb5fed0abf1d4))
- **ci:** fix autofix auth, add merge-prep agent, tune merge-prep qualification ([413e460](https://github.com/nicsuzor/academicOps/commit/413e46045b192e140ce4acdf00c9d12fd3b2a045))
- **ci:** only run autofix when CI fails; fix job-level timeout ([0eba116](https://github.com/nicsuzor/academicOps/commit/0eba116f5a5599647916c745059273f702040e52))
- **ci:** restrict CI to unit tests; mark e2e/integration tests as slow ([f89b496](https://github.com/nicsuzor/academicOps/commit/f89b49678e5e76ae457da4bf445909312c71101c))
- delete redundant math smoke test and update conftest ([79f52a5](https://github.com/nicsuzor/academicOps/commit/79f52a587c96a53a6a8c0b327b91a796aae4fd0d))
- finalize environmental fixes and confirm auth working ([ea7a214](https://github.com/nicsuzor/academicOps/commit/ea7a214a16d77ca33e136f2d1414355fcb1a1097))
- finalize environmental test fixes and address failures ([cd90f52](https://github.com/nicsuzor/academicOps/commit/cd90f526312857089d1036c7decc7d4b258abf7d))
- handle nested job names in ruleset alignment check ([6680069](https://github.com/nicsuzor/academicOps/commit/6680069d252b7f9673bcbe3c63d33660f3d77d39))
- implement proper logging for headless tests ([8069a49](https://github.com/nicsuzor/academicOps/commit/8069a49ee01988aaa8b53dc2891cda03b4b0cca9))
- **install:** show install sources, simplify version report, add dock… ([14a20c9](https://github.com/nicsuzor/academicOps/commit/14a20c94653972b99960d0a4a575520bc0e89d15))
- **install:** show install sources, simplify version report, add docker check ([501ab2d](https://github.com/nicsuzor/academicOps/commit/501ab2d937cc822fdba149dfc1fc083af20dc37c))
- **install:** uninstall before install and report versions; bump to 0.3.4 ([66377af](https://github.com/nicsuzor/academicOps/commit/66377af6195e08f2f1ed17ab938508ae0e1ee888))
- plugin load failure — remove duplicate hooks decl, add uninstall-dev ([a8cfd58](https://github.com/nicsuzor/academicOps/commit/a8cfd58e82f3e50f3f4aff2a6356d9b799557938))
- **polecat:** detect system timezone instead of hardcoding Australia/Brisbane ([2bbf81f](https://github.com/nicsuzor/academicOps/commit/2bbf81fd3493561e321d28675692174e1b096ec5))
- **polecat:** Docker containerization + sync consolidation ([4634fce](https://github.com/nicsuzor/academicOps/commit/4634fced1da3a345753cc20935c0410f2a6df687))
- **polecat:** fix Docker execution for Claude and Gemini crew/run ([e2b7cbc](https://github.com/nicsuzor/academicOps/commit/e2b7cbc0aaa53414cd5e99b9beeddec2facfed7c))
- **polecat:** fix GEMINI_CLI_HOME path in _replicate_gemini_auth ([9685455](https://github.com/nicsuzor/academicOps/commit/96854557712b4870496108a22971107e4dda21d9))
- **polecat:** mount pkb binary and ACA_DATA in Docker container ([277c426](https://github.com/nicsuzor/academicOps/commit/277c42682316bf0962408013b60faad3baa2b347))
- **polecat:** remove --tmpfs mount that hides .claude config in Docker ([f209b85](https://github.com/nicsuzor/academicOps/commit/f209b8524caa40bae3e3b41944273c3095ef82a2))
- **polecat:** remove incorrect Gemini key forwarding from Claude Docker path ([0ee26ae](https://github.com/nicsuzor/academicOps/commit/0ee26ae257689ac3b0fc6e9810129b19836a9337))
- **polecat:** revert read-only .claude mount; fix crew terminology ([b3335e7](https://github.com/nicsuzor/academicOps/commit/b3335e7d334de2f10f75abc5cb32f518e0af1e9a))
- **polecat:** semver NVM sort, auth key forwarding, read-only config mounts ([9c0e856](https://github.com/nicsuzor/academicOps/commit/9c0e856ca87fbace70ac92ec01f87d1e93d2c337))
- propagate git identity from source repo to clones ([1605de8](https://github.com/nicsuzor/academicOps/commit/1605de894a271303e38bc38e70f2b97c7cfa24a1))
- properly strip mcp__ prefix in gemini tool translation ([efbe8d6](https://github.com/nicsuzor/academicOps/commit/efbe8d6cc07fbb63e84cc63313b63e949b16e272))
- properly strip mcp__ prefix in gemini tool translation ([aa52678](https://github.com/nicsuzor/academicOps/commit/aa52678b676c654d08ef5e5b772bedd92ea7c5b5))
- remove duplicate hydrator entries flagged in review ([6640a4b](https://github.com/nicsuzor/academicOps/commit/6640a4b61bbb3d7a819bb55e3a8ad4914da232c2))
- remove insecure chmod 777 from Dockerfiles; add CLI path resolution to run() ([f5923bf](https://github.com/nicsuzor/academicOps/commit/f5923bff9530e8b476517982423f226ed79de548))
- remove manual auth manipulation and finalize loud failure state ([0d2a279](https://github.com/nicsuzor/academicOps/commit/0d2a2798f69712350216fa4bbdefbd5fe0f4ea91))
- remove redundant asserts after pytest.skip and delete plan.md ([12341d2](https://github.com/nicsuzor/academicOps/commit/12341d2d429e9a260af2801c9aa0f241219b57fc))
- remove remaining duplicate hydrator keyword in file_index.py ([2ec7f3b](https://github.com/nicsuzor/academicOps/commit/2ec7f3bd0606349ec82592c7c9341e0badf7dbab))
- remove stale temp_path required_vars from hydrator.instruction template spec ([7e31e77](https://github.com/nicsuzor/academicOps/commit/7e31e77f5917c88b539faba86d4aff929eada9ff))
- remove stale tests for deleted symbols and fix test markers ([2fff096](https://github.com/nicsuzor/academicOps/commit/2fff096bee650374a9e261e182857b341183965f))
- remove unused cmd variables, merge main ([146b562](https://github.com/nicsuzor/academicOps/commit/146b562c2d1ce280d323f066fb9fe8531266a9f0))
- resolve 'expected' pending checks in PR pipeline and bump to 0.3.3 ([4752d8b](https://github.com/nicsuzor/academicOps/commit/4752d8b578fca2e0f901cfa00eaac224274dda2f))
- resolve basedpyright type error in gates engine ([d0cbab9](https://github.com/nicsuzor/academicOps/commit/d0cbab937ca04f4ebc11cc06c272c69e8758f9be))
- resolve basedpyright type error in gates engine ([acec004](https://github.com/nicsuzor/academicOps/commit/acec004c7a1a24fb4575a32a7037ce21c4c82bcb))
- resolve gemini extension install and agent tool name errors ([98cc101](https://github.com/nicsuzor/academicOps/commit/98cc1019b10bc130856df363daadc58f382455f7))
- resolve gemini extension install and agent tool name errors ([cf80100](https://github.com/nicsuzor/academicOps/commit/cf8010059943d6ebc8296c8a35106c98000c96d0))
- resolve P[#54](https://github.com/nicsuzor/academicOps/issues/54) collision, update enforcement-map and VISION.md ([80f8e01](https://github.com/nicsuzor/academicOps/commit/80f8e0156563d5f49eaf35aba7cb5c9244ff0a4e))
- resolve self-contradiction in command-intercept Feature Purpose ([8bb05a1](https://github.com/nicsuzor/academicOps/commit/8bb05a19b7a7f9201b65707f5af222d7ffb3bd39))
- resolve self-contradictions in command-intercept spec ([dfb7401](https://github.com/nicsuzor/academicOps/commit/dfb740122e4d7bf8d14040d716deef4df8f27a04))
- restore mcp_ prefix in gemini body tool translation for consistency ([4b29853](https://github.com/nicsuzor/academicOps/commit/4b298536ccca1479dd49cfcf2e4fdfaad3756ec1))
- restore status descriptions and correct tool names in planning SKILL.md ([2aaf302](https://github.com/nicsuzor/academicOps/commit/2aaf3023567f560e693fd1b79595f63b9060d5f4))
- **sleep:** add repo topology guardrail to prevent false task cancellation ([aa63098](https://github.com/nicsuzor/academicOps/commit/aa630983508f0769d1f150c86ac03fa073bb49ee)), closes [#82](https://github.com/nicsuzor/academicOps/issues/82)
- **spec:** align Design and Acceptance Criteria paths with current implementation ([a123b3f](https://github.com/nicsuzor/academicOps/commit/a123b3fba2361ae0577dfdf9ef2e9904f7fb2d4f))
- **spec:** align transcript naming convention with implementation ([064984a](https://github.com/nicsuzor/academicOps/commit/064984acb3043545fe0b4d8ade02cf81a88f0b23))
- **tests:** fix false positive in test_no_pkb_mount_when_missing ([6a58708](https://github.com/nicsuzor/academicOps/commit/6a58708afa423244a9857caafd55e7d3c8d9ff6e))
- update test_hydrator to use task-hydrator agent name ([0bcbf83](https://github.com/nicsuzor/academicOps/commit/0bcbf833ce84dbee031fe3a46e56ee8921e4243c))
- use consistent {repo} placeholder in merge-prep agent ([07f6ed4](https://github.com/nicsuzor/academicOps/commit/07f6ed42d7dc99ec04c9a69b62f8113d10f6bae7))
- use managed headless runners in credential isolation tests ([e63e9fa](https://github.com/nicsuzor/academicOps/commit/e63e9fa6ed17f5b1f087887f2655a10dc5e6c85c))

### Code Refactoring

- delete builder.py; gate engine handles hydration natively ([240f011](https://github.com/nicsuzor/academicOps/commit/240f011e88ef884656a4d558c489f1f49e2ae318))
- delete hydrator context injection pipeline + planning skill package ([1e5af22](https://github.com/nicsuzor/academicOps/commit/1e5af220a8518288274d3db64336c39b331bc6e7))
- delete hydrator context injection pipeline entirely ([831ff0c](https://github.com/nicsuzor/academicOps/commit/831ff0cc02988769762257615d0e5e5bd507b9f8))
- make is_hydratable declarative; delete skip_check + user_prompt_submit ([281e973](https://github.com/nicsuzor/academicOps/commit/281e9733a40c28aab299c031351b5e0a405d9e6a))
- make is_hydratable declarative; delete skip_check + user_prompt_submit ([715cea9](https://github.com/nicsuzor/academicOps/commit/715cea901654cca1dbb3130119e8eaef5927f19a))
- migrate planning to standalone skill, delete dynamic hydrator injection ([61dbace](https://github.com/nicsuzor/academicOps/commit/61dbace9aa0b256fed56bf19c9cd20b5b2990b60))
- **polecat:** merge repo-sync.sh into pc sync command ([01c18c6](https://github.com/nicsuzor/academicOps/commit/01c18c6d673cc9af7c73185fa22255150455ed31))
- remove uv-dynamic-versioning and simplify Dockerfile ([29472d0](https://github.com/nicsuzor/academicOps/commit/29472d0b6aa1f89ed57bb077227b2cdb5083c038))
- **tests:** replace requires_local_env marker with integration ([c18f41d](https://github.com/nicsuzor/academicOps/commit/c18f41d752af100eea70fabae6414cde5d4f9ff1))
- unify main and sandbox docker images ([dae4207](https://github.com/nicsuzor/academicOps/commit/dae4207660bd4ac7bfd9534f75d208cd018ef270))

### Documentation

- clarify hydrator/planner distinction and phase 1 prototype goals ([24dab2d](https://github.com/nicsuzor/academicOps/commit/24dab2df5cdecc40faf5e602051c4dc95879116b))
- formalize loud failures and environment redirection heuristics ([e61e686](https://github.com/nicsuzor/academicOps/commit/e61e686ff1531426cdf487f9744da3d0b208fbdf))
- narrow pytest.skip exceptions and enforce loud failures ([f88342e](https://github.com/nicsuzor/academicOps/commit/f88342e5d9851da6b393322488a17014bd286852))
- **spec:** update user expectations for collaborate-workflow (aops-c3e311a9) ([fb42b9f](https://github.com/nicsuzor/academicOps/commit/fb42b9f408902a2eae7926dd501a42e8016bc123))

### CI/CD

- add missing permissions to pr-pipeline.yml ([6e44dc3](https://github.com/nicsuzor/academicOps/commit/6e44dc3e24bceabf0777e9b76894601b480d308e))
- fix string type coercion in PR pipeline workflow call ([aba5c34](https://github.com/nicsuzor/academicOps/commit/aba5c34027e9dbf079d109c90cd298be8e77e3c4))

### Miscellaneous

- delete overengineered command-intercept spec ([d6c9b27](https://github.com/nicsuzor/academicOps/commit/d6c9b27ea5dfb41a1897a802bf4c4ec711dac7a2))
- **framework:** codify non-interactive execution constraint ([763168a](https://github.com/nicsuzor/academicOps/commit/763168af91ffdbcdc13936d8e1becc167de5aafa))
- **framework:** shift to abstraction layer architecture ([27d2352](https://github.com/nicsuzor/academicOps/commit/27d2352433f732e8a4a832f869f24ad4a02c9b20))
- remove bump-my-version ([a50cdef](https://github.com/nicsuzor/academicOps/commit/a50cdef33695600c6675939e74929cd97ce87102))
- remove standalone repo-sync.sh (superseded by pc sync) ([bb2ed24](https://github.com/nicsuzor/academicOps/commit/bb2ed24b240ae8542bb8aa078c6fb02e5192e420))
- sync pyproject versioning with release-please ([a12feb0](https://github.com/nicsuzor/academicOps/commit/a12feb077e3dd35b1145fae177d2ca7ed5514989))
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
