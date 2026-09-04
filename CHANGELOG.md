# Changelog

## [0.9.2](https://github.com/nicsuzor/academicOps/compare/v0.9.1...v0.9.2) (2026-09-04)

### Features

- **dispatch:** add aops sandbox kit and move kits to lib/kits ([9d9c866](https://github.com/nicsuzor/academicOps/commit/9d9c866535a834e2a0193c840e74f796f38cfe1a))
- **hooks:** ground UserPromptSubmit in pkb search with fallback ([152d04f](https://github.com/nicsuzor/academicOps/commit/152d04fa2963a23d8831c300a53360657eacc657))
- **hooks:** ground UserPromptSubmit in pkb search with fallback ([9474539](https://github.com/nicsuzor/academicOps/commit/947453933abab30952c4cd83d23685d148e319cc))

### Bug Fixes

- **build:** resolve orchestrate-to-aops migration fallout and client mcp splitting ([4bbaa22](https://github.com/nicsuzor/academicOps/commit/4bbaa222270b57e6d908b068ba426b896241ebe6))
- **build:** ship kits from lib/kits, not lib/polecat/kits ([d5113e3](https://github.com/nicsuzor/academicOps/commit/d5113e379b6c1424ece7cc501bbd8776ffefcda2))
- **hooks:** address review comments and make test suite green ([7d16446](https://github.com/nicsuzor/academicOps/commit/7d16446a4fc403d307a71622afa74536b2153e76))
- **hooks:** resolve pkb binary from PATH or hook cwd without hardcoded paths ([57be841](https://github.com/nicsuzor/academicOps/commit/57be841a90476a1e46a56e7c5540c1b93b79ce63))
- **kits:** put agy on a PATH the sandbox agent user can reach ([06530ca](https://github.com/nicsuzor/academicOps/commit/06530cad5c10a6458f073137c04dee7e3c0ecd1a))
- resolve review comments, restore tooling dependencies, and align test suite ([3075275](https://github.com/nicsuzor/academicOps/commit/3075275dff775f03e5ecafd91456380c8fd1593c))

### Documentation

- enforce task branch naming, container naming after branch, and single PR ([1c10ed7](https://github.com/nicsuzor/academicOps/commit/1c10ed7d6e62f935693474809ff79f1f558e663d))

### Miscellaneous

- **dev:** release 0.9.1 ([b7c4cf0](https://github.com/nicsuzor/academicOps/commit/b7c4cf026296ff4705db1034052fad88f6db6ac7))
- update uv.lock for release ([32d2e89](https://github.com/nicsuzor/academicOps/commit/32d2e89a3bd07905a501e49718c928b08b538c93))

### Features

- **dispatch:** add aops sandbox kit and move kits to lib/kits ([9d9c866](https://github.com/nicsuzor/academicOps/commit/9d9c866535a834e2a0193c840e74f796f38cfe1a))
- **hooks:** ground UserPromptSubmit in pkb search with fallback ([152d04f](https://github.com/nicsuzor/academicOps/commit/152d04fa2963a23d8831c300a53360657eacc657))
- **hooks:** ground UserPromptSubmit in pkb search with fallback ([9474539](https://github.com/nicsuzor/academicOps/commit/947453933abab30952c4cd83d23685d148e319cc))

### Bug Fixes

- **build:** resolve orchestrate-to-aops migration fallout and client mcp splitting ([4bbaa22](https://github.com/nicsuzor/academicOps/commit/4bbaa222270b57e6d908b068ba426b896241ebe6))
- **build:** ship kits from lib/kits, not lib/polecat/kits ([d5113e3](https://github.com/nicsuzor/academicOps/commit/d5113e379b6c1424ece7cc501bbd8776ffefcda2))
- **hooks:** address review comments and make test suite green ([7d16446](https://github.com/nicsuzor/academicOps/commit/7d16446a4fc403d307a71622afa74536b2153e76))
- **hooks:** resolve pkb binary from PATH or hook cwd without hardcoded paths ([57be841](https://github.com/nicsuzor/academicOps/commit/57be841a90476a1e46a56e7c5540c1b93b79ce63))
- **kits:** put agy on a PATH the sandbox agent user can reach ([06530ca](https://github.com/nicsuzor/academicOps/commit/06530cad5c10a6458f073137c04dee7e3c0ecd1a))
- resolve review comments, restore tooling dependencies, and align test suite ([3075275](https://github.com/nicsuzor/academicOps/commit/3075275dff775f03e5ecafd91456380c8fd1593c))

### Documentation

- enforce task branch naming, container naming after branch, and single PR ([1c10ed7](https://github.com/nicsuzor/academicOps/commit/1c10ed7d6e62f935693474809ff79f1f558e663d))

### Miscellaneous

- **dev:** release 0.9.1 ([b7c4cf0](https://github.com/nicsuzor/academicOps/commit/b7c4cf026296ff4705db1034052fad88f6db6ac7))
- update uv.lock for release ([32d2e89](https://github.com/nicsuzor/academicOps/commit/32d2e89a3bd07905a501e49718c928b08b538c93))

## [0.9.1](https://github.com/nicsuzor/academicOps/compare/v0.9.0...v0.9.1) (2026-09-03)

### Features

- **analyst:** enforce canonical path resolution and ground-truth parity validation ([#1428](https://github.com/nicsuzor/academicOps/issues/1428), [#1429](https://github.com/nicsuzor/academicOps/issues/1429)) ([f4cea8e](https://github.com/nicsuzor/academicOps/commit/f4cea8e5fbfbb372211831c969c9e04e348c17d3))
- **aops:** make q, decompose, and brief skills idempotent ([6ba6a18](https://github.com/nicsuzor/academicOps/commit/6ba6a18804c5c38cf0303d96d9dd9605f4e8ca98))
- **build:** add OpenClaw client adapter and distribution target ([f51cf4f](https://github.com/nicsuzor/academicOps/commit/f51cf4fbffd57897a222030f9853b94e8e28c013))
- **craft:** encode research-adjudicated authoring standard with evidence base ([a40d819](https://github.com/nicsuzor/academicOps/commit/a40d819bc6e712351d10d53204bbce8616e4d972))
- default to james agent and restore --model flag ([ee62631](https://github.com/nicsuzor/academicOps/commit/ee626313b3a1b0d000d848abef5cba95e597f10f))
- **distribution:** add Claude and Gemini marketplace manifests for direct repository distribution ([ed255c3](https://github.com/nicsuzor/academicOps/commit/ed255c308d16a8c6c6177babfbb1e7d61529a7a3))
- **gates:** implement pre-push/pre-PR task-body mandatory gate (closes [#583](https://github.com/nicsuzor/academicOps/issues/583), epic-50b5ade9.3, epic-50b5ade9.4) ([c10a6bc](https://github.com/nicsuzor/academicOps/commit/c10a6bc48ccee9b8f9a7f34591886b9a29fe4db1))
- **lint:** add no-em-dashes rule and autofix for no-horizontal-rules ([16bd6b1](https://github.com/nicsuzor/academicOps/commit/16bd6b1641c21de96502ffbe56b40f9dfc13e086))
- **orchestrate:** add minimal sara agent definition ([d8daa99](https://github.com/nicsuzor/academicOps/commit/d8daa999e01a647c02632b66adf57ccd1d26fdb0))
- **orchestrate:** forced per-claim OTel verdict script + dispatch gate for Ida ([ebbd415](https://github.com/nicsuzor/academicOps/commit/ebbd4151c9eeeabc34071c90764d01e94e317188))
- **orchestrate:** forced per-claim OTel verdict script + dispatch gate for Ida ([e0f6601](https://github.com/nicsuzor/academicOps/commit/e0f660133effaa1bec4345f06a4cf7ced1faa529))
- **orchestrate:** ship premise check in skill, bake questions, and arm on PostToolBatch ([55d6447](https://github.com/nicsuzor/academicOps/commit/55d6447174b4f266960bcb1e7be8673a36cb3985))
- **otel:** enrich spans with agent.id, parent.session_id, agent.name, and tool.call_id ([9245854](https://github.com/nicsuzor/academicOps/commit/9245854bbe36b1bf3167b5ffb415175773218c75))
- **pkb:** land current-state-only doctrine for task and note bodies (aops_81ba220a) ([310ab27](https://github.com/nicsuzor/academicOps/commit/310ab278cb0ad942827a8ad434bd120a267a3a1b))
- **polecat:** container seed construction and detached launch (aops_9160e382) ([86a3e8f](https://github.com/nicsuzor/academicOps/commit/86a3e8f9744b4cbd3d69868f30be7c3c34b5d752))
- **polecat:** container seed construction and detached launch (aops_9160e382) ([a808bcc](https://github.com/nicsuzor/academicOps/commit/a808bcc439482171ba1ea8fdd739b641039dc792))
- **polecat:** define project aliases in polecat.yaml and auto-canonicalize across polecat and OTEL ([e459a35](https://github.com/nicsuzor/academicOps/commit/e459a351fd7ba77767b8d832f971ffe8dfa9261b))
- **polecat:** polecat base-ref resolution and remote freshness (aops_bb5d538b) ([e6a44a6](https://github.com/nicsuzor/academicOps/commit/e6a44a645f9850a469c2454ea48dc84c066ec526))
- **polecat:** provide option to mount shared scratch space at /scratch ([56dc12c](https://github.com/nicsuzor/academicOps/commit/56dc12c3b792104917bf088135b8591e4117a523))
- **polecat:** surface and warn on container image staleness (aops_40a3faa8) ([e14a148](https://github.com/nicsuzor/academicOps/commit/e14a14837016edcd549aee9bdaf3c1ce933535c4))
- **reconcile:** wire sent-mail ground-truth into the existing aged-task check ([8e55155](https://github.com/nicsuzor/academicOps/commit/8e55155ae0cccf49a23806acb4690a23e86bf5de))
- **reconcile:** wire sent-mail ground-truth into the existing aged-task check ([953f848](https://github.com/nicsuzor/academicOps/commit/953f8483a0223e958a0f9a7b9e86919471dc2cc5))
- rename priority to intent, establish scoring authority, and author pauli prioritisation doctrine ([#2555](https://github.com/nicsuzor/academicOps/issues/2555)) ([d0b3ab0](https://github.com/nicsuzor/academicOps/commit/d0b3ab0e1d849bb82d062ea2f26ab4ae1dbf0456))
- **rules:** add No Shitty NLP and Agentic-First Design project rule ([31daca2](https://github.com/nicsuzor/academicOps/commit/31daca21cd0160b9e9177686c781ff19c5444141))
- **rules:** enforce no filesystem fallback and PKB target weight SSOT ([#2560](https://github.com/nicsuzor/academicOps/issues/2560)) ([f308383](https://github.com/nicsuzor/academicOps/commit/f308383287dba4536481251e951840054379d2e1))
- **scripts:** add 4-pane tmux launcher script for persistent named agents ([f9bdf4e](https://github.com/nicsuzor/academicOps/commit/f9bdf4e0d501977a1af297da67b66d68cde57983))
- **scripts:** add 4-pane tmux launcher script for persistent named agents (aops_93bca999) ([e7d94d5](https://github.com/nicsuzor/academicOps/commit/e7d94d588fca388516ccf0ce21fbd4fa7a0a62f0))
- show otel tracing config in SessionStart hook ([15cabe5](https://github.com/nicsuzor/academicOps/commit/15cabe5d5f865044e8ce94afde80cf26f7cfa682))
- show plugin/pkb versions and injected files in SessionStart hook ([645f541](https://github.com/nicsuzor/academicOps/commit/645f541bd0eff9b3a2c2b2ee960acf23534f15f7))
- **spec:** establish task/filename naming standards, graph-relationship decisions, and canonical task body template ([c6c3ece](https://github.com/nicsuzor/academicOps/commit/c6c3ece8264810340b6874c07e84170ef145c5b2))
- **specs:** add short-form linked rule references to enforcement map column 1 ([69be526](https://github.com/nicsuzor/academicOps/commit/69be5264db843c19041d148f0d3762fd246e2771))
- **specs:** consolidate enforcement map with severity index and repo-local template ([8604815](https://github.com/nicsuzor/academicOps/commit/86048151447288e531ece0a52cd40ed4fc420ed0))
- **specs:** decouple underlying substantive norms from persona prompt carriers in enforcement map ([92ea759](https://github.com/nicsuzor/academicOps/commit/92ea7596439f784623b4de43dd536ed65740ad32))
- **tracing:** parent subagent traces hierarchically ([e48c2a4](https://github.com/nicsuzor/academicOps/commit/e48c2a410dd8a99cf0ea471ba17c26a861bea678))
- **v0.9.1:** remove dist repo/branch distribution; distribute directly from repository ([233569e](https://github.com/nicsuzor/academicOps/commit/233569e6e88d5a9300925b62e5f6882d72ebc96c))
- **workflows:** archive composed workflow templates across tiers for v0.9 reset (aops_f74b7e6c) ([9abde0c](https://github.com/nicsuzor/academicOps/commit/9abde0ce53de6a35388458f573546a7015438a24))
- **workflows:** archive composed workflow templates across tiers for v0.9 reset (aops_f74b7e6c) ([fcfa5f7](https://github.com/nicsuzor/academicOps/commit/fcfa5f71a082f0ce40c06bb98d7ac1acd1d90bf6))

### Bug Fixes

- **agents:** add held-turn contract and absorb-only gap-flags to ida, forbid sleep barriers in james (closes [#2475](https://github.com/nicsuzor/academicOps/issues/2475), [#2476](https://github.com/nicsuzor/academicOps/issues/2476), [#2435](https://github.com/nicsuzor/academicOps/issues/2435)) ([#2550](https://github.com/nicsuzor/academicOps/issues/2550)) ([0c1180c](https://github.com/nicsuzor/academicOps/commit/0c1180c451e7f0d4e0668267705886c54f6cd6f4))
- **brief:** remove instructions to emit speculative review and sign-off nodes ([758413d](https://github.com/nicsuzor/academicOps/commit/758413dedfb4e64d9db31ad77e619d7ea57175a5))
- **brief:** run /q first if prompt arrives without task id ([1c7b9a4](https://github.com/nicsuzor/academicOps/commit/1c7b9a4df2199ed645295c9325ef6476744d8e6e))
- **framework-gate:** rename bare human-approval to wf-human-approval ([3ffebf8](https://github.com/nicsuzor/academicOps/commit/3ffebf87b0c18c4905665a4e23fa702cd488db05))
- **framework-gate:** rename bare human-approval to wf-human-approval ([79ad733](https://github.com/nicsuzor/academicOps/commit/79ad733e816d1c94abb307a85ad33fa8c0738f38))
- **hearsay:** add status/provenance-first logic-check to hearsay.md and james.md:50 ([ae0b0af](https://github.com/nicsuzor/academicOps/commit/ae0b0af28e9aaa728a7ef7b4083b12f46a7ea499))
- **hearsay:** status/provenance-first logic-check ([#2570](https://github.com/nicsuzor/academicOps/issues/2570)) ([5c2326e](https://github.com/nicsuzor/academicOps/commit/5c2326ea47ada4dbf4cc7fd37519663c1da39a13))
- **isp-orphans-bundle-s1:** retire pr-reviewer.agent.md, restore probes.md evidence, wire assumption_checks.py ([04379fa](https://github.com/nicsuzor/academicOps/commit/04379fa25a85bc4fb8cace9398fd59bfb4f8159d))
- **isp-orphans:** retire pr-reviewer.agent.md, restore probes.md evidence, wire assumption_checks.py ([5e2f9a0](https://github.com/nicsuzor/academicOps/commit/5e2f9a0aa41c93b2320c17cc47e42452625cffdc))
- **learn:** sharpen root-cause validity rules and remedy fit ([bac06a7](https://github.com/nicsuzor/academicOps/commit/bac06a7eb0fa28dd68002d0e853f9808dbf986cc))
- **learn:** sharpen root-cause validity rules and remedy fit ([884a96e](https://github.com/nicsuzor/academicOps/commit/884a96ed611b454dbe420c17b5f7411b2585fa5d))
- **lint:** make dprint the only markdown formatter, autofix house rules ([4b88f48](https://github.com/nicsuzor/academicOps/commit/4b88f4832ed000ebab7d7e900bb65ff68211bd27))
- **lint:** move the em-dash ban out of markdownlint into its own hook ([06d5bef](https://github.com/nicsuzor/academicOps/commit/06d5bef537ba84781a8a867ad2e0662ef736da3e))
- **otel:** add parent_span_id extraction to agy_tracer and fallback to transcriptPath ([eb66295](https://github.com/nicsuzor/academicOps/commit/eb66295e9885956db2d307b36acc73f2fd800606))
- **otel:** unify Phoenix project naming to academicOps, decouple task IDs, and purge legacy arthur attributes ([50ecb01](https://github.com/nicsuzor/academicOps/commit/50ecb01b47fe62b4db396671de5e0696856ef1ba))
- **otel:** unify Phoenix project naming to academicOps, decouple task IDs, and purge legacy arthur attributes ([fa8e4b6](https://github.com/nicsuzor/academicOps/commit/fa8e4b624325979d0a271e043a7266efb585235b))
- **pauli:** no meta-commentary or task links in bodies; route body writing through craft ([9ee8db5](https://github.com/nicsuzor/academicOps/commit/9ee8db5c962e49961ddd840beaa2bd44e39c0f34))
- **pauli:** task bodies enumerate outcomes and instruct rather than argue ([7efe017](https://github.com/nicsuzor/academicOps/commit/7efe017cfc9d7699dd2709eabf7b771d067398c8))
- **pkb:** enforce two-step status mutation contract and forbid batch_update for demotions (aops_bf223645) ([4caa9dc](https://github.com/nicsuzor/academicOps/commit/4caa9dc765a68a164fbfe0d77272c13d705c455d))
- **pkb:** enforce two-step status mutation contract and forbid batch_update for demotions (Closes aops_bf223645) ([87d44cc](https://github.com/nicsuzor/academicOps/commit/87d44cc049bfe414b283b7b9c8c628a6a3190a6c))
- **pkb:** remove direct status: blocked write paths and enforce derived blocks edges ([a443356](https://github.com/nicsuzor/academicOps/commit/a443356c089decd9477852b7ba9851f683ea1c90))
- **pkb:** remove direct status: blocked write paths and enforce derived blocks edges ([43aff84](https://github.com/nicsuzor/academicOps/commit/43aff84a6011348aa250fa02a7ddecf4d3d89f86))
- **polecat:** anchor staleness check to canonical HEAD, not clone base_sha ([8b58052](https://github.com/nicsuzor/academicOps/commit/8b580528dbb7e39b2f4b228b203948378e1452df))
- **polecat:** seed /aops:pull, not /pkb:pull, in container launch ([6dd392e](https://github.com/nicsuzor/academicOps/commit/6dd392e35cb430d6149c160d3d85216b38a8b375))
- **polecat:** seed /aops:pull, not /pkb:pull, in container launch ([edc8598](https://github.com/nicsuzor/academicOps/commit/edc859826456d2a767ba540c1c8b499326340688))
- **polecat:** STALE_LOCAL_BUILD fires on missed release, not any commit diff ([6c6ad92](https://github.com/nicsuzor/academicOps/commit/6c6ad92159505c26747a47f65f70385e5b66f23f))
- **polecat:** STALE_LOCAL_BUILD fires on missed release, not any commit diff ([d346d3e](https://github.com/nicsuzor/academicOps/commit/d346d3e1dbe0e510d58d765c5767c74419465db5))
- **polecat:** staleness check disagrees with docker-build about 'current' (aops_81849370) ([3d5e3a6](https://github.com/nicsuzor/academicOps/commit/3d5e3a6f4f14b333fa87285ee3335c62059a5c72))
- **polecat:** target worktree base HEAD for push/PRs and forward base branch env ([96a8673](https://github.com/nicsuzor/academicOps/commit/96a8673910558a9516c1ab0a0586a1e0f714a2fc))
- prohibit direct runtime plugin edits and add strategic-review spec (closes [#2390](https://github.com/nicsuzor/academicOps/issues/2390), [#2424](https://github.com/nicsuzor/academicOps/issues/2424)) ([18dab11](https://github.com/nicsuzor/academicOps/commit/18dab1109144121d6dd8e9a6472cb920bd3ad112))
- prohibit direct runtime plugin edits and add strategic-review spec (closes [#2390](https://github.com/nicsuzor/academicOps/issues/2390), [#2424](https://github.com/nicsuzor/academicOps/issues/2424)) ([7c23503](https://github.com/nicsuzor/academicOps/commit/7c2350332466519c6d02d9b50d7b3a901167fecb))
- **refs:** correct plugins/pkb references to plugins/aops-core and set PKB_MCP_URL in test_detached_mode ([ce13f51](https://github.com/nicsuzor/academicOps/commit/ce13f5163104fec74026c2066118110713c6e510))
- **refs:** make `make lint` green on v0.9.1 ([#2558](https://github.com/nicsuzor/academicOps/issues/2558)) ([d1657d7](https://github.com/nicsuzor/academicOps/commit/d1657d7bbc59498ad73eefc652958c678aa681dc))
- **refs:** update plugins/aops-core paths to plugins/aops in ida-supervision-migration.md ([d8555a9](https://github.com/nicsuzor/academicOps/commit/d8555a99206a37d397a6b24320a84b64bbf03926))
- repair test-suite fallout from PR [#2498](https://github.com/nicsuzor/academicOps/issues/2498)'s ida-into-pkb merge ([d51eaad](https://github.com/nicsuzor/academicOps/commit/d51eaadb6891a4b713577772f5061ad705f120d7))
- **scripts:** launch named agents from WSL host with docker exec for containerized roles ([bfa0633](https://github.com/nicsuzor/academicOps/commit/bfa0633000fb4e545c64eea3c2656e3283e2ca0e))
- **security:** reinstate Layer 2 commit-time secret backstop (aops_8c697102) ([e085c36](https://github.com/nicsuzor/academicOps/commit/e085c3671112947a2affd0fe8f21d3680b97c8df))
- **security:** reinstate Layer 2 commit-time secret backstop (aops_8c697102) ([bcb1744](https://github.com/nicsuzor/academicOps/commit/bcb174468cc23788838f421b9136425e4731c185))
- **skills:** harden brief and q skills against nine verified defects and adopt ideal brief spec ([1659c27](https://github.com/nicsuzor/academicOps/commit/1659c2754f2399473784f4413ce99f5d563a306f))
- **skills:** remove non-canonical task status mandates (#aops_c038247b) ([cff3388](https://github.com/nicsuzor/academicOps/commit/cff33881a0c62008ab23dd1a9779d19a52523148))
- **skills:** use on-PATH polecat executable in polecat launcher skill ([d590475](https://github.com/nicsuzor/academicOps/commit/d590475e6757f7fabd3e1df2a540504d5ba48449))
- **skills:** use on-PATH polecat executable in polecat launcher skill ([6ada336](https://github.com/nicsuzor/academicOps/commit/6ada33622c318564f92f450a79b47af557538411))
- spare HTML numeric metrics from redaction; update agent-authority spec (closes [#2406](https://github.com/nicsuzor/academicOps/issues/2406), [#2397](https://github.com/nicsuzor/academicOps/issues/2397), [#2407](https://github.com/nicsuzor/academicOps/issues/2407)) ([#2546](https://github.com/nicsuzor/academicOps/issues/2546)) ([bc58389](https://github.com/nicsuzor/academicOps/commit/bc583894c7d0f2e11845a9b06da35ba81be36a72))
- **specs:** correct drifted line citations and unbacked rows in ENFORCEMENT-MAP.md (closes aops_373e4364) ([1d90c2e](https://github.com/nicsuzor/academicOps/commit/1d90c2e2798724475d67aa486fb3f5730092707e))
- **specs:** correct drifted line citations and unbacked rows in ENFORCEMENT-MAP.md (closes aops_373e4364) ([ddea2c7](https://github.com/nicsuzor/academicOps/commit/ddea2c717a8b123e923e93591a29ad1d0c0ceb61))
- **specs:** update prompt-hydration spec status from implemented to proposed (closes [#2439](https://github.com/nicsuzor/academicOps/issues/2439)) ([1125cd4](https://github.com/nicsuzor/academicOps/commit/1125cd43eed8a3a3be2635dd661cc09160083087))
- **specs:** update prompt-hydration spec status from implemented to proposed (closes [#2439](https://github.com/nicsuzor/academicOps/issues/2439)) ([6af2a74](https://github.com/nicsuzor/academicOps/commit/6af2a74315561176911b2cdcba5156815040da7a))
- **specs:** update supervision-split spec with shipped supervised-development doctrine (closes [#2415](https://github.com/nicsuzor/academicOps/issues/2415)) ([1db8690](https://github.com/nicsuzor/academicOps/commit/1db8690104ce651a8dc42eccf981820d19b28422))
- **specs:** update supervision-split spec with shipped supervised-development doctrine (closes [#2415](https://github.com/nicsuzor/academicOps/issues/2415)) ([92a2a5f](https://github.com/nicsuzor/academicOps/commit/92a2a5fa0bf813f47a9d8fe14e970bc7def475c3))
- **templates:** daemon contradiction, Excalidraw dedupe, frontmatter, false parser claim ([1222eb7](https://github.com/nicsuzor/academicOps/commit/1222eb718e3b03994991cbda8ce3b69ce2fcda0c))
- **templates:** resolve daemon contradiction, dedupe Excalidraw mechanics, close frontmatter, fix false parser claim ([e570a79](https://github.com/nicsuzor/academicOps/commit/e570a797fe39af8f097eb639e7e4549113be8330))
- **templates:** resolve wf-brief-composition-verify contradiction and dead refs ([bc08cd8](https://github.com/nicsuzor/academicOps/commit/bc08cd8ff605c48029945ecf7c1b06c9df1a5f1b))
- **templates:** resolve wf-brief-composition-verify contradiction and dead refs ([0fc1676](https://github.com/nicsuzor/academicOps/commit/0fc1676cc96ac541e6ee7d206f110bcf4d7491de))
- **tests:** set PKB_MCP_URL in test_image_staleness base mocks ([b4345b7](https://github.com/nicsuzor/academicOps/commit/b4345b7174b0abc7581ca6eaa426ccb87227c663))
- **tracing:** forward all GENAI_ENGINE env vars on polecat and launchd ([e862e73](https://github.com/nicsuzor/academicOps/commit/e862e733b07b6c21559880cffd8566b02fe314fd))
- **transcripts:** redact quoted secrets with spaces, escaped quotes, and fullwidth colons (closes [#2405](https://github.com/nicsuzor/academicOps/issues/2405)) ([#2547](https://github.com/nicsuzor/academicOps/issues/2547)) ([df585d6](https://github.com/nicsuzor/academicOps/commit/df585d6d9dbb2a7388e5c7f72aafc06e5141a410))
- update broken references post-skill-reorganization and allow historical spec paths ([1f959a5](https://github.com/nicsuzor/academicOps/commit/1f959a5b0652982ca90942fd0242097c38ade7a6))
- update broken references post-skill-reorganization and allow historical spec paths ([ec0c186](https://github.com/nicsuzor/academicOps/commit/ec0c186189b3cc886bb90a2fd37654665ebf0efc))
- **workflows:** restore 10 workflow templates to universal tier and resolve duplicate pairs ([4937d42](https://github.com/nicsuzor/academicOps/commit/4937d4278690339abe9cca0e0aa9cc6a5e9b52c7))

### Code Refactoring

- **craft:** ship craft as a generic plugin skill ([ac2e4dd](https://github.com/nicsuzor/academicOps/commit/ac2e4dde3acf8adbb5983894f85aed2b178f2495))
- **debug:** dedupe Phoenix span-store facts into lib/, split debug SKILL.md ([ba47aae](https://github.com/nicsuzor/academicOps/commit/ba47aae3caf3bf551293aa8655a73bed2f918ae0))
- **debug:** dedupe Phoenix span-store facts, split debug SKILL.md ([08d2644](https://github.com/nicsuzor/academicOps/commit/08d26446dd8cea2a9fcd483fa7a5e8ce77869ed6))
- **dist:** remove dist branch distribution; distribute directly from repository ([16cdf26](https://github.com/nicsuzor/academicOps/commit/16cdf26e5d9a7537a86b5aa201dbddd5b433e95e))
- **learn:** revoke the /learn skill's remedy authority (aops_ae92a692) ([f737376](https://github.com/nicsuzor/academicOps/commit/f737376dbdc1f1482c02af665c0a7aa190a4dd62))
- **learn:** revoke the skill's remedy authority (aops_ae92a692) ([18f958c](https://github.com/nicsuzor/academicOps/commit/18f958c5b39e2046daba599f4fb1e66c806601d5))
- **packaging:** rename pkb plugin back to aops-core (aops_ed8ee345) ([8a8b4a7](https://github.com/nicsuzor/academicOps/commit/8a8b4a794bcc49d70c44b1aebac005889dca80d5))
- **pkb:** rewrite brief skill to ideal-task-brief spec (aops_20260828_pauli_instructions) ([8371ad9](https://github.com/nicsuzor/academicOps/commit/8371ad9734ddb2e7e79fba0c8f2ca2bd32af8c5f))
- **plugins:** merge orchestrate plugin into aops ([2de5739](https://github.com/nicsuzor/academicOps/commit/2de5739796a5099a98baf63f4752a33562fcb7df))
- **skills:** update reconcile and consolidation to call /q for repositioning and deduplicate instructions ([5efa385](https://github.com/nicsuzor/academicOps/commit/5efa3859786bcc94cb7a2a1c7eab2ab80ba6c102))
- **skills:** update reconcile and consolidation to call /q for repositioning and deduplicate instructions by reference ([d372767](https://github.com/nicsuzor/academicOps/commit/d3727674348bda225118ba410a158515f255e7d2))
- **workflows:** restructure the universal template library ([512c430](https://github.com/nicsuzor/academicOps/commit/512c4306370d3677787f1268222fd5f47aafb96e))

### Documentation

- cull agent-authority, dead references, and prose-pinning tests ([16981ef](https://github.com/nicsuzor/academicOps/commit/16981ef1c204436ac6d1fc0394bc1b73b053c93e))
- delete instruction-authoring guidance craft now owns ([460f71a](https://github.com/nicsuzor/academicOps/commit/460f71a5270338719792df3f218eb51fe04a4367))
- **enforcement-map:** correct stale polecat invocation citation ([b94e4b2](https://github.com/nicsuzor/academicOps/commit/b94e4b2ef39d78fea756f743abfe7ac2de8cda1d))
- **enforcement:** reorder bands and promote canonical escalation ladder (aops_75f3ee84) ([6a5f2d0](https://github.com/nicsuzor/academicOps/commit/6a5f2d0d688731487773e46d6b9cc60a86887c8c))
- fix install/config claim and hook wiring drift in ARCHITECTURE.md ([8782095](https://github.com/nicsuzor/academicOps/commit/878209599a2af4716a7779ad9731be5587fba580))
- fix install/config claim and hook wiring drift in ARCHITECTURE.md ([f9be314](https://github.com/nicsuzor/academicOps/commit/f9be314123ae8925f879e0b89355dec39626db3e))
- **ida,sara:** establish dispatch boundary between Ida and Sara ([1786df5](https://github.com/nicsuzor/academicOps/commit/1786df55464bdccea630a6aafbde086bd9dcafb6))
- **ida,sara:** establish dispatch boundary between Ida and Sara ([fb2fe11](https://github.com/nicsuzor/academicOps/commit/fb2fe11b6cf8aef99027e82c49a757cb2624d61c))
- radically simplify 27 instruction and spec files under the craft standard ([da70baa](https://github.com/nicsuzor/academicOps/commit/da70baae332d7c2cdd62f83e67710c781d39dea5))
- repoint dangling refs and reconcile stale claims in shipped surfaces ([b7acc3e](https://github.com/nicsuzor/academicOps/commit/b7acc3ee17a8d591e844de7e5129ab8f54f1f837))
- repoint dangling refs and reconcile stale claims in shipped surfaces ([11db986](https://github.com/nicsuzor/academicOps/commit/11db986919958e89f5337bb89451c5a92c324dd8))
- second craft wave — cut 11.4k lines across skills, agents, and specs ([b4c5174](https://github.com/nicsuzor/academicOps/commit/b4c5174a02efbc5c5ed9722b48d9bb61408342ce))
- **specs:** inventory instruction-authoring guidance and map consolidation into craft ([5157fab](https://github.com/nicsuzor/academicOps/commit/5157fabcbddd3fe592582d7472034f14dcc4e82b))
- **specs:** update supervision-split to reference authoritative excalidraw map ([c577ee0](https://github.com/nicsuzor/academicOps/commit/c577ee073192d5de8f9444a08c78fc7164af4f26))
- **specs:** update supervision-split to reference authoritative excalidraw map ([7482d8c](https://github.com/nicsuzor/academicOps/commit/7482d8c841eb91c0b57fceaaa4d24e7de952b87e))
- **sync:** clarify sessions git-sync comment ([946cea0](https://github.com/nicsuzor/academicOps/commit/946cea02576b08fdfeb28541a20b651f748e1bd9))
- **sync:** clarify sessions git-sync comment for v0.9.1 ([7acf791](https://github.com/nicsuzor/academicOps/commit/7acf79155be13f349e1a9f0afa74112c86a10ea5))
- tighten specs governing tasks, workflow templates, PKB, and axioms ([cabd317](https://github.com/nicsuzor/academicOps/commit/cabd317515aa1de4370e6280fcaa06b481424758))
- tighten specs governing tasks, workflow templates, PKB, and axioms ([722f823](https://github.com/nicsuzor/academicOps/commit/722f82318ac14dcb27d287e772476a660b1faaa7))

### CI/CD

- run CI on release-line pushes and gate the tag publish on pytest ([#2557](https://github.com/nicsuzor/academicOps/issues/2557)) ([7b262d8](https://github.com/nicsuzor/academicOps/commit/7b262d88f9810706b12a889b654c6100541512d9))

### Tests

- **orchestrate:** assert handlers.py only reaches for tracer attrs that exist ([86911ae](https://github.com/nicsuzor/academicOps/commit/86911ae79933b29f6b9edfcbb823c829a86f18f2))
- pin check_refs.py coverage of plugins/_/skills/**/_.md ([376e761](https://github.com/nicsuzor/academicOps/commit/376e761902537ca9a3fe8184cefed2d7db1f0207))
- pin check_refs.py coverage of plugins/_/skills/**/_.md ([84d3d6a](https://github.com/nicsuzor/academicOps/commit/84d3d6adc25bbd164ad7008098e06e3a6f88601c))
- **polecat:** assert staleness check still fires when image is genuinely behind canonical_head ([d14da75](https://github.com/nicsuzor/academicOps/commit/d14da757d79a287aac6c383181e54711d2b418a2))
- realign axiom-roster and honesty-gate tests with shipped behaviour ([078f88d](https://github.com/nicsuzor/academicOps/commit/078f88d3b3cb8dd5926acb698d176380fe451423))
- remove test_sixteen_simultaneous_evaluations_are_all_answered_in_parallel ([64d32db](https://github.com/nicsuzor/academicOps/commit/64d32db04fa1cf0645b46e880d8604728a2a2dd5))

### Miscellaneous

- delete 20 dead files across specs, plugins, lib, and tests ([0b0e090](https://github.com/nicsuzor/academicOps/commit/0b0e090cab93f44411db0ed34a12bed676be029b))
- delete plugins.disabled dead halves, dead PKB hook, and unship plugin tests ([4ca54c2](https://github.com/nicsuzor/academicOps/commit/4ca54c2375ed22c5d11e80749a96000555bc937e))
- make pytest output more concise ([4133ea5](https://github.com/nicsuzor/academicOps/commit/4133ea570195d0e57aee166b53632f0b180f1595))
- **tests:** remove dead demo marker and addopts filter ([00ee458](https://github.com/nicsuzor/academicOps/commit/00ee458a8b5f5d5ee1cf1970aecda47b85ed61b8))
- **tests:** remove dead demo marker and addopts filter ([6fc9306](https://github.com/nicsuzor/academicOps/commit/6fc9306a7d1212aec405d6d40e287e54ff7638de))

## [0.9.0](https://github.com/nicsuzor/academicOps/compare/v0.8.1...v0.9.0) (2026-08-27)

### Features

- **pkb:** sharpen Discord executive briefing standard and ADHD accommodations ([6187d9d](https://github.com/nicsuzor/academicOps/commit/6187d9d55dde7c4485ff83f2a3020e427b61dd36))
- **pkb:** sharpen Discord executive briefing standard and ADHD accommodations ([034ecd2](https://github.com/nicsuzor/academicOps/commit/034ecd26c3f6d8410a13b4b46a645b9f8b2e29f2))

### Bug Fixes

- **pkb:** reconcile must record merged PRs as settled and never re-open human decisions ([1bc49a9](https://github.com/nicsuzor/academicOps/commit/1bc49a9a3ce9ce0e6286627bbfc8cda2a5446ec9))
- **pkb:** reconcile must record merged PRs as settled and never re-open human decisions ([5ba0c8d](https://github.com/nicsuzor/academicOps/commit/5ba0c8d7316d7db62a2269f9d7d809ea601e7ce3))
- **pkb:** remove pkb_context references from q and brief skills ([ebbb9fc](https://github.com/nicsuzor/academicOps/commit/ebbb9fc51e82e773d1d3546eccf22e7def73b802))
- **pkb:** remove pkb_context references from q and brief skills ([e443f64](https://github.com/nicsuzor/academicOps/commit/e443f642e9d10f54f699dac4b8263824bf24823f))

### Documentation

- **core:** remove container field-test requirement from CORE.md (aops_609edb82) ([24f6e6a](https://github.com/nicsuzor/academicOps/commit/24f6e6ac3ac303f613893605f9e7a928c3d71ca6))

### Miscellaneous

- pin next release to 0.9.0 ([143bc24](https://github.com/nicsuzor/academicOps/commit/143bc24e23c0175a82a8be6602ceadce2430e839))

## [0.8.1](https://github.com/nicsuzor/academicOps/compare/v0.8.0...v0.8.1) (2026-08-22)

### Features

- **epistemics:** enforce subagent return contract and basis-gated negative claims ([42f6a06](https://github.com/nicsuzor/academicOps/commit/42f6a062514304c3c20038ad54455c77c4a3aca5))
- **epistemics:** enforce subagent return contract and basis-gated negative claims ([6e7a9e6](https://github.com/nicsuzor/academicOps/commit/6e7a9e6058a49c7129765f912db435b8a9cc290f))
- **pkb:** add immediate PKB task update obligation to email workflows ([2fab33d](https://github.com/nicsuzor/academicOps/commit/2fab33d33df135d4cd2d7739fe57d7d6fe87b815))
- **pkb:** add immediate PKB task update obligation to email workflows ([3439d31](https://github.com/nicsuzor/academicOps/commit/3439d315bd2c77ce9b84a3c89249917a7d0b6d70))

### Documentation

- **ida:** add subagent return channel rule to dispatch workflow ([a25692b](https://github.com/nicsuzor/academicOps/commit/a25692bcb6e63d955db0ef2b52768dc7ae5ac037))
- **ida:** add subagent return channel rule to dispatch workflow ([bccd1cd](https://github.com/nicsuzor/academicOps/commit/bccd1cdbaf5eeaa5fbf3bdfb46d7ced62a5ac241))

## [0.8.0](https://github.com/nicsuzor/academicOps/compare/v0.7.3...v0.8.0) (2026-08-21)

### Features

- **ida:** document SSH dispatch path for pc, host from POLECAT_HOST ([129f987](https://github.com/nicsuzor/academicOps/commit/129f98794621e54faf9cbe7bbdc75098235434fd))
- **orchestrate:** add session-trace skill for Phoenix span export ([3862271](https://github.com/nicsuzor/academicOps/commit/38622714a4e0ca96a9d4f9815cbfc7fd5cc45352))
- **orchestrate:** session-trace skill — export a session's Phoenix spans as trees, controller view, and contamination report ([e5b160f](https://github.com/nicsuzor/academicOps/commit/e5b160f0a2ee0bc0d0441f0d1741ad8a1384e270))
- **pkb,orchestrate:** routine capture floor, pipeline re-cut, academic paper spine, pc timeout convention ([b6b2b33](https://github.com/nicsuzor/academicOps/commit/b6b2b3328f93e6e6fa21abeacb234e42c792edc7))
- **polecat:** add dynamic host port mapping (-P/--port) for container port 8080 ([5855111](https://github.com/nicsuzor/academicOps/commit/5855111823715ac12ddec80d0e67b8ba1e5f7565))
- **polecat:** expose container port 8080 and publish dynamic host port by default ([a7130fc](https://github.com/nicsuzor/academicOps/commit/a7130fc45d30818ca86b5ce26c4daf818f513f79))
- **polecat:** forward GENAI_ENGINE_TRACE_ENDPOINT and protocol from env, set task identifier ([f9e3941](https://github.com/nicsuzor/academicOps/commit/f9e39418b7f7ced64fd2a39fafba92421d7d4f0b))
- **polecat:** read configs in a DRY way from polecat.yaml with no env var fallback ([b78be37](https://github.com/nicsuzor/academicOps/commit/b78be3785a8576f9000495881775c255357037d1))
- **polecat:** resolve source branch from --branch, fallback to origin refs, and speed up clones with --no-checkout ([c45c28f](https://github.com/nicsuzor/academicOps/commit/c45c28f528d4bbcd46a0b0bb2d6551fa97a91042))
- **pre-commit:** reinstall H39 horizontal rule prohibition and R5.6 orphan md gate ([a2b5d20](https://github.com/nicsuzor/academicOps/commit/a2b5d20efd10eeb3743369dcb80d72cba6bbd13a))
- **telemetry:** leverage Phoenix MCP in debug skill and enforce trace endpoint in entrypoint ([b1119a3](https://github.com/nicsuzor/academicOps/commit/b1119a39841a7985ef9f8c65807185e2540e07ff))
- **transcripts:** replace legacy transcript pipeline with Phoenix OTel trace renderer ([4f9db74](https://github.com/nicsuzor/academicOps/commit/4f9db749d6f90b7f7c13d531fc97977e5ab150cb))
- **transcripts:** replace legacy transcript pipeline with Phoenix OTel trace renderer ([987f863](https://github.com/nicsuzor/academicOps/commit/987f863dee643742ed815a6ce975020258e7609c))

### Bug Fixes

- address review comments on PR [#2469](https://github.com/nicsuzor/academicOps/issues/2469) and resolve broken doc reference ([c4d4cec](https://github.com/nicsuzor/academicOps/commit/c4d4cec333cfa495faf03f507157bad93b3c61de))
- **build/agy:** omit tools frontmatter when no tools are specified ([403c97a](https://github.com/nicsuzor/academicOps/commit/403c97a9911b485a0065ad1683b91f64df0a7b29))
- **build/agy:** restore explicit tools vocabulary emission for agy agents ([c9b2d10](https://github.com/nicsuzor/academicOps/commit/c9b2d10d83dc3f394139e1e0d5d58d8e5054e755))
- **build/agy:** restrict agy accepted tools to registered set in container ([76c0af7](https://github.com/nicsuzor/academicOps/commit/76c0af74b8af8a5b8e5d79038fb74aee2991a7f9))
- **ida:** give §2 an arrival-time contract — state + action, not prohibition ([a8a0bcb](https://github.com/nicsuzor/academicOps/commit/a8a0bcb8262d600cd436fd054f8a695db629bc19))
- **ida:** give §2 an arrival-time contract — state + action, not prohibition ([4ae7f3c](https://github.com/nicsuzor/academicOps/commit/4ae7f3c139c87262d6da3a3ecd3edf1927b90e60))
- **ida:** ssh -t must precede the destination in pc's attach command ([fde691d](https://github.com/nicsuzor/academicOps/commit/fde691d122dafe0820fce9cb1a59fa9f383baa64))
- **orchestrate:** delete dead otel_tracer_core.py ([43ab64b](https://github.com/nicsuzor/academicOps/commit/43ab64b078ad73011f290c10519d2e07fc705982))
- **orchestrate:** fail-fast session.id, share root id with subagents, drop dead trace-inheritance machinery ([cde7211](https://github.com/nicsuzor/academicOps/commit/cde7211d2ffad8d3892bda573e61e46d42ec2837))
- **orchestrate:** guard agy_stop to the genuine end-of-turn payload ([9e5684c](https://github.com/nicsuzor/academicOps/commit/9e5684c49b1beefbf4dba0b2ca4abadfe7176a48))
- **orchestrate:** make OTel tracer hooks harness-agnostic, fix agy_tracer.discover_config ([c7f564a](https://github.com/nicsuzor/academicOps/commit/c7f564a64add8ff59b1133302eb14d67b2f9424c))
- **orchestrate:** remap agy PostInvocation to no-op, fix agy span parentage/kinds ([88564db](https://github.com/nicsuzor/academicOps/commit/88564dbcd9ce7cf6db1bb7e6bf74bfd234b14678))
- **polecat/permissions:** grant unrestricted permissions and fix session_start handler ([6e4ef8a](https://github.com/nicsuzor/academicOps/commit/6e4ef8aa247a05c7151380a7e7621be045b3aed4))
- **polecat:** widen mapping annotation in _resolve_section_env to Mapping ([8787ab3](https://github.com/nicsuzor/academicOps/commit/8787ab31c511cdf722dcd790551f00eb88f3f2ba))
- **polecat:** widen mapping annotation in _resolve_section_env to Mapping ([538c5c6](https://github.com/nicsuzor/academicOps/commit/538c5c63dd37df463c6b0f6958b8f2f3202f8a79))
- **refs:** repoint stale plugins/rbg/pyproject.toml references ([f973352](https://github.com/nicsuzor/academicOps/commit/f9733529f0cd3c28ea224fc3bde155f8ad989c2a))
- **transcripts:** address PR [#2470](https://github.com/nicsuzor/academicOps/issues/2470) review comments on trace markdown and CLI modes ([a8083df](https://github.com/nicsuzor/academicOps/commit/a8083df757bfd88ce446866451672215727d228d))
- untrack otel.txt, patch.diff, tests/test_cope.py.orig ([ff911a6](https://github.com/nicsuzor/academicOps/commit/ff911a69066c11183e092f5a20e9ba676b710316))

### Documentation

- **debug skill:** add subagent lifecycle correlation recipes to Phoenix forensics ([035dcb7](https://github.com/nicsuzor/academicOps/commit/035dcb79781e28ec951b4bed6c26d3e0eca2ed7d))
- **debug:** record agy tool-vocabulary contract, fix MCP scoring, add live-fix-loop ([bb905fb](https://github.com/nicsuzor/academicOps/commit/bb905fb8aa7318b46ae68627aec2bfc240be287d))
- **pkb:** mark daily-skill spec as superseded by tpl_daily ([23278b0](https://github.com/nicsuzor/academicOps/commit/23278b02650dc76c8adf291ec1cdbe9115d5b26e))
- **session-trace:** update skill instructions to search sessions by short slug ([6731095](https://github.com/nicsuzor/academicOps/commit/6731095e182aa384b48cf61822ece8ca22b27565))
- **specs:** pc's recorded grants now include ssh ([570506a](https://github.com/nicsuzor/academicOps/commit/570506a2c9333633921f6a8507eaef9666785b24))

### Miscellaneous

- **dev:** release 0.7.3 ([c302af8](https://github.com/nicsuzor/academicOps/commit/c302af8f8e8e0d69d7787a8d361145d87a2baaa3))
- pin next release to 0.8.0 ([69a8d63](https://github.com/nicsuzor/academicOps/commit/69a8d6385a08200e0cc49de05e4f43d9652593c5))

## [0.7.3](https://github.com/nicsuzor/academicOps/compare/v0.7.2...v0.7.3) (2026-08-16)

### Features

- agent build variants, polecat runner options, transcript caching, orchestration hooks & skills ([7e33d95](https://github.com/nicsuzor/academicOps/commit/7e33d95490818c4ac31dc460899d74c2cf248551))
- **build:** resolve per-client agent variants, and let agy frontmatter be native ([4f1125c](https://github.com/nicsuzor/academicOps/commit/4f1125c91ccf5058e4fe4f9fdc4398dd16af1e3e))
- **ida:** re-enable agy.md agent with conditional sandbox rule ([2b2af3a](https://github.com/nicsuzor/academicOps/commit/2b2af3a288081ae4ecd3e331c4e36973e52f7be5))
- **ida:** render the completion line into the daily note, and stop announcing the gate ([201c21f](https://github.com/nicsuzor/academicOps/commit/201c21fa7187aeca29152c5f7c8933452d17b8d6))
- **ida:** the completion line — render it from the graph, and stop announcing the gate ([3195dba](https://github.com/nicsuzor/academicOps/commit/3195dba4eab813c8aab9867bac7c99829b6a29f6))
- **orchestrate,pkb:** refine james instructions, enable hearsay batch hook, and format pull skill headers ([bd58f6d](https://github.com/nicsuzor/academicOps/commit/bd58f6d71fd1460cb6843ac04caf1aee251c0cc1))
- **orchestrate:** add session id, datetime+tz, host, cwd to SessionStart hook ([aea98c1](https://github.com/nicsuzor/academicOps/commit/aea98c19a53c884465b5eff153393a8ddc0fc82d))
- **orchestrate:** add session id, datetime+tz, host, cwd to SessionStart hook ([952990a](https://github.com/nicsuzor/academicOps/commit/952990a2af71e031f91cb669bdbcc3d69b0d16b2))
- **orchestrate:** split james into per-client files, both team-oriented ([36a940d](https://github.com/nicsuzor/academicOps/commit/36a940d4c085feb69d200d7be832be19b9cde3a8))
- **polecat,orchestrate:** default agent james, --no-agent flag, james rewrite with client-conditional sections and pkb mcpServers ([a0c3176](https://github.com/nicsuzor/academicOps/commit/a0c3176f3b5148f1a2d40642829f08d75086aa96))
- **polecat:** reintegrate sessions mount and --branch override capabilities ([1ba6888](https://github.com/nicsuzor/academicOps/commit/1ba68885a319a719370809dfa649509fdb61beac))
- **polecat:** reintegrate sessions mount and --branch override capabilities ([abbf5f8](https://github.com/nicsuzor/academicOps/commit/abbf5f8905d4c0c3c2d4cf7c62ca8c8fa19edd63))
- **polecat:** remove default agent; only pass --agent when specified ([3dac085](https://github.com/nicsuzor/academicOps/commit/3dac085f24533db5b8061b4d88632357d6f2458e))
- **polecat:** set CLAUDE_CODE_ENABLE_TODO_TOOLS=1 in containers ([2ec494d](https://github.com/nicsuzor/academicOps/commit/2ec494da4187e1465aea5cfc8394d5d3abb05bb9))
- **polecat:** set CLAUDE_CODE_ENABLE_TODO_TOOLS=1 in containers ([30f7219](https://github.com/nicsuzor/academicOps/commit/30f7219da8b0ded87baf51bf2174a8caac113cd8))
- **polecat:** support --output-format and --prompt options with clean stdout ([f98e31f](https://github.com/nicsuzor/academicOps/commit/f98e31fc51b1178e095110deff8c85aa71ca3040))

### Bug Fixes

- **agents,specs:** standardize agent frontmatter, reconcile authority spec, and cleanup docs ([5682508](https://github.com/nicsuzor/academicOps/commit/5682508d768ff45c7e87709ef6ba9c7edac799f7))
- **agents,specs:** standardize agent frontmatter, reconcile authority spec, and cleanup docs ([4951ada](https://github.com/nicsuzor/academicOps/commit/4951ada68dd8c6f815c02f8e352bf5c105f991a9))
- **agents:** dispatch agy by redirect, never through a pipe ([12800a3](https://github.com/nicsuzor/academicOps/commit/12800a377f4236fa7b8bae3918c0dca42fe0b9e2))
- **agents:** restore allowedTools, disallowedTools, and permissionMode in agent frontmatter ([88e8069](https://github.com/nicsuzor/academicOps/commit/88e80696381b03f35c394ce0eb53c4cf6e22b71d))
- **build/agy:** restore full tool vocabulary fallback for agents omitting tools: ([250921f](https://github.com/nicsuzor/academicOps/commit/250921f8db5ab9d70c38c335207276d26d9a3c4d))
- **build:** add ListAgents to the tool_map vocabulary ([42bdb80](https://github.com/nicsuzor/academicOps/commit/42bdb80c9bc72bb7f670ed8f1ce3d9cce81c8ec2))
- **build:** add ListAgents to the tool_map vocabulary ([2e67764](https://github.com/nicsuzor/academicOps/commit/2e67764bc723b4add2a4d98f6e867483b009266d))
- **build:** omit mcpServers string list in agy agent frontmatter ([9edb529](https://github.com/nicsuzor/academicOps/commit/9edb52973f802a46dc38ec090054199c3b92e046))
- **build:** omit mcpServers string list in agy agent frontmatter ([f7f5335](https://github.com/nicsuzor/academicOps/commit/f7f53355d72ba2818caec4a23369e9eb7ea2734b))
- **hooks,spec:** reconcile canonical hook events, honesty on SubagentStart, and debug skill agy MCP status ([1e0153a](https://github.com/nicsuzor/academicOps/commit/1e0153aca9502e56b3b162bfacba1d2324b34c8a))
- **orchestrate:** fix pc.md citation in plugin.toml and expand allowedTools in pc.md ([5990337](https://github.com/nicsuzor/academicOps/commit/5990337e21884b249830e1911814eeba0b35360a))
- **pc:** add pc to bashScopes to match allowedTools Bash(pc *) ([cf93b77](https://github.com/nicsuzor/academicOps/commit/cf93b772cd2afd5b60b4c7fcc5a3c887ebeda518))
- **polecat:** keep credential values off the docker command line ([cce3c16](https://github.com/nicsuzor/academicOps/commit/cce3c1613f4ba165f7d0291c17477c545f34868e))
- **polecat:** keep credential values off the docker command line ([84d1b76](https://github.com/nicsuzor/academicOps/commit/84d1b76da862a1bf909630715b227443652d83ea))
- **polecat:** output full inner_cmd without truncation on Running stderr message ([334f6a5](https://github.com/nicsuzor/academicOps/commit/334f6a5d7440452ac896d5698b77e6bc6fb857c8))
- **polecat:** stop the new tests leaking real credentials, require run_env ([caaf8f9](https://github.com/nicsuzor/academicOps/commit/caaf8f948792c0bc7aee21359d686874314c1f71))
- repair the 12 failing tests and the type-check gate ([4e482cb](https://github.com/nicsuzor/academicOps/commit/4e482cb98717a8623debc62926201d1480a50833))
- stop-gate blocks again (drop async on rbg stop hooks); preserve workspace on failed dispatch ([542e519](https://github.com/nicsuzor/academicOps/commit/542e519fb5af0d1942ce1f0fb757872c077c2c54))

### Code Refactoring

- **build:** expect &lt;name&gt;.&lt;client&gt;.md instead of &lt;name&gt;.md.&lt;client&gt; ([75bc6ed](https://github.com/nicsuzor/academicOps/commit/75bc6edb62648609e3cad83b2be171d0169c44f5))
- **polecat:** consolidate claude and agy container default configurations ([6d53df2](https://github.com/nicsuzor/academicOps/commit/6d53df2a8b9e2e4e48aff639aaa3caa0fd03aa39))
- **polecat:** remove env var fallback for branch override in favor of strict CLI option ([ab15746](https://github.com/nicsuzor/academicOps/commit/ab15746b1fc22428dabde07ee53fd709deeaad47))

### Documentation

- **core:** require a live-client field test, owned by marsha, for every plugin change ([1e6af5c](https://github.com/nicsuzor/academicOps/commit/1e6af5c8f14db31e966fa993d3628be429424ba9))
- **enforcement:** clarify blocking hooks policy across Claude Code and agy ([b93b134](https://github.com/nicsuzor/academicOps/commit/b93b13460d38f2fa60071a7f9236a04000ab1f71))
- **ida:** extend hearsay rule to require observed/inferred labelling ([f44bbcd](https://github.com/nicsuzor/academicOps/commit/f44bbcd178f2435b377111a79e441f58b333ba94))
- **ida:** extend hearsay rule to require observed/inferred labelling ([a94949f](https://github.com/nicsuzor/academicOps/commit/a94949f61b5760f7c9d58e0cc155eb807754d100))
- **james:** make agent naming an obligation, not advice ([65ddb54](https://github.com/nicsuzor/academicOps/commit/65ddb542fcaae02711bc252408c2b8a52414ab21))
- **james:** make agent naming an obligation, not advice ([d2c44af](https://github.com/nicsuzor/academicOps/commit/d2c44af9cf1c4c409350e534e52382a836ecd870))
- **peer-review:** framing pass, no pre-committed results, scribe length budget ([3c6d22f](https://github.com/nicsuzor/academicOps/commit/3c6d22f5520da9645aa092635d9ff72eab6209fa))
- **specs/future:** orchestrator client-split plan, reconciled review verdict, and teammate-return defect evidence ([70cd597](https://github.com/nicsuzor/academicOps/commit/70cd5975fff8b5fb6ccb7d5cc8f141c08cf2680f))
- **specs:** document allowedTools/hooks/memory/initialPrompt as valid agent frontmatter ([edd6fb2](https://github.com/nicsuzor/academicOps/commit/edd6fb2ea9b353239256079071cff4fa7b49775b))
- **specs:** record q's allowed-tools row in the enforcement register ([7c4009d](https://github.com/nicsuzor/academicOps/commit/7c4009d08abe2b2c932102026b29acac7e643860))
- **triage:** point trend-mode prompt mining at live transcript sidecars ([8ddb364](https://github.com/nicsuzor/academicOps/commit/8ddb36404e33f46e4c537a5c3340fe9fc8f8c19f))

### CI/CD

- run PR Pipeline for pull requests based on agenttools ([2f59208](https://github.com/nicsuzor/academicOps/commit/2f59208a1ac0e0ee40657ef06eaf8072610e6f10))
- run PR Pipeline for pull requests based on agenttools ([56e8b56](https://github.com/nicsuzor/academicOps/commit/56e8b56a0d532753ed6543848cdeaf63a3edde01))

### Build System

- **agy:** translate mcp tools, format mcpServers, strip redundant frontmatter, and output wildcard for absent tools ([d1d9fea](https://github.com/nicsuzor/academicOps/commit/d1d9fea02515f1564e2d8d59f5603bdd2345334e))

## [0.7.2](https://github.com/nicsuzor/academicOps/compare/v0.7.1...v0.7.2) (2026-08-12)

### Features

- **build:** rewrite agy agent tool translation according to verified semantics ([a4e5679](https://github.com/nicsuzor/academicOps/commit/a4e5679c2d8b5fced590384954e8e4764999b835))
- **diagram:** add excal-edit.py arrows check and render --region ([2351fc0](https://github.com/nicsuzor/academicOps/commit/2351fc0e0c414cb0ca10553a2eefb668ed75fe16))
- **diagram:** excal-edit.py arrows check + render --region ([8e639ef](https://github.com/nicsuzor/academicOps/commit/8e639ef0b9c6fe1ac197046f3192dd154898c66c))
- **ida:** fold final-reply standing discipline rules into ida agent definition (task_ff6f26ed) ([3ae45c9](https://github.com/nicsuzor/academicOps/commit/3ae45c90a4757b8146ef5230060a42ca17129e89))
- **ida:** fold final-reply standing discipline rules into ida agent definition (task_ff6f26ed) ([5c3b9d7](https://github.com/nicsuzor/academicOps/commit/5c3b9d7a4d7c3af35c4c9eb165433ba2e4bdc4f8))
- **ida:** sharpen ADHD executive briefing standard and hook rules ([b178a6b](https://github.com/nicsuzor/academicOps/commit/b178a6b8414ef2c57517a1d7d9c2da7ec7730b0d))
- **orchestrate:** import Claude Code OTel gRPC tracer into orchestrate plugin ([bc98f41](https://github.com/nicsuzor/academicOps/commit/bc98f4103e11ab655646b7d97a19f12055a7d9f6))
- **orchestrate:** import Claude Code OTel gRPC tracer into orchestrate plugin ([16da41a](https://github.com/nicsuzor/academicOps/commit/16da41a717ee8e79d85a90b33edbf9951ab5fb00))
- **v0.7.2:** OpenInference OTel tracer, AGY tool translation, transcript engine overhaul, and agent discipline ([6170917](https://github.com/nicsuzor/academicOps/commit/6170917179fe933c292c62ee146345669da3548a))

### Bug Fixes

- **build:** let AGY_VERSION/CLAUDE_CODE_VERSION actually refresh their layers; correct MCP registration docstring ([4e56f08](https://github.com/nicsuzor/academicOps/commit/4e56f086dbc79b9df58cf80f891c489aa81f76e3))
- **hooks:** log a warning when claude_code_tracer fails to import ([c595e8e](https://github.com/nicsuzor/academicOps/commit/c595e8ebb53675dc02557a72d989b3db9a98af08))
- **ida:** point quiet.md at the briefing standard instead of restating it ([d001827](https://github.com/nicsuzor/academicOps/commit/d0018278ae3709e9e5e2092d06c4bf4c0de67221))
- **ida:** restore PostToolBatch hook wiring and update assertions ([28d74ba](https://github.com/nicsuzor/academicOps/commit/28d74bab3f23382a8cc23429143744e1574f67ce))
- **orchestrate:** add doc/diagram QA criteria to marsha and strategic-review ([fe364ae](https://github.com/nicsuzor/academicOps/commit/fe364ae39cdebe01652f2aef9811b679a5e7a495))
- **orchestrate:** address strategic review feedback for OTel tracer PR [#2425](https://github.com/nicsuzor/academicOps/issues/2425) ([1a180cc](https://github.com/nicsuzor/academicOps/commit/1a180cc7e85b5953b4d873eaab196c1ddf1e795d))
- **polecat:** do not install ida plugin in polecat containers ([2b6c9ac](https://github.com/nicsuzor/academicOps/commit/2b6c9ac75d2a350fff1950fb0ca936daa62c2dc7))
- **rbg:** unregister hooks again — agy PostInvocation→Stop fires the rule gate on every tool call ([9e5c62a](https://github.com/nicsuzor/academicOps/commit/9e5c62a16b67a0ab74ba7b177993d7a923b8f01d))
- **tracer:** annotate TracerProvider kwargs dict as dict[str, Any] ([6e8ad0e](https://github.com/nicsuzor/academicOps/commit/6e8ad0e1d8d97e330ebe83175a079fa257c888f2))
- **tracer:** bound OTLP span export with a 2s timeout ([04cfee7](https://github.com/nicsuzor/academicOps/commit/04cfee73b7bd8895bb62a4aefd418a73457fd906))

### Reverts

- **dogfood:** drop the process-scoped hypothesis clause — blind re-test showed no gap to close ([d5759f0](https://github.com/nicsuzor/academicOps/commit/d5759f0ee55b03288fbf3037b05326407af984a0))

### Documentation

- **build:** label the call_mcp_tool omission as a dated [#2422](https://github.com/nicsuzor/academicOps/issues/2422) mitigation ([a6237f9](https://github.com/nicsuzor/academicOps/commit/a6237f9c21787e1e5de88d92b42885292ddce04c))
- **core:** update agy defect note to MCP issue [#2422](https://github.com/nicsuzor/academicOps/issues/2422) and fix test docstrings ([3158803](https://github.com/nicsuzor/academicOps/commit/3158803caf30acfcab654e3298602645a6b43815))
- **debug:** update agy diagnostic advice for frontmatter tools and retire defect [#2387](https://github.com/nicsuzor/academicOps/issues/2387) reference ([63388f0](https://github.com/nicsuzor/academicOps/commit/63388f0277549ab3f81edc30d46d9e86a81bac95))
- **ida:** correct agy wrapper invocation, MCP and skill forms ([e93b1dc](https://github.com/nicsuzor/academicOps/commit/e93b1dcc6beee250996f72e06443b3a922bbab66))
- **ida:** warn against briefing findings instead of the user's task ([20c7ed9](https://github.com/nicsuzor/academicOps/commit/20c7ed932be294a1cbfe1a6476d0fa3c379d21a6))
- **reconcile:** add concise task status reconciliation instruction ([d89a639](https://github.com/nicsuzor/academicOps/commit/d89a639ae78d09fc86e05e196bd9b68af0f41675))
- **skills:** make hypotheses falsifiable, keep doctrine out of briefs, bar verdicts from absence ([4ca9d2c](https://github.com/nicsuzor/academicOps/commit/4ca9d2cff54c0e231959ee2f0309630153e0fde2))
- **specs:** mark the enforcement carriers this branch deleted ([04b584e](https://github.com/nicsuzor/academicOps/commit/04b584eda6b0cdb8b5acef48b253ee8e8a165f1e))
- **specs:** reconcile ARCHITECTURE with what the branch ships ([829d17f](https://github.com/nicsuzor/academicOps/commit/829d17fec6efb219ad81ec934162689bbe950a36))
- **tracer:** record why transcript discovery cannot reuse lib/py/transcripts ([edacc46](https://github.com/nicsuzor/academicOps/commit/edacc46bd4b3d47c8f093f6c3178bcfdfbb3704a))

### Tests

- **tracer:** assert the export timeout on both exporter constructions ([9eeac2e](https://github.com/nicsuzor/academicOps/commit/9eeac2ef42ea28c85d4f5c6e30e82ee93bb20d83))

## [0.7.1](https://github.com/nicsuzor/academicOps/compare/v0.7.0...v0.7.1) (2026-08-07)

### Features

- Add unified ida-flat orchestrator ([bd74ab6](https://github.com/nicsuzor/academicOps/commit/bd74ab610d0d5b06f24c14695b3786d6501933c7))
- add unified ida-flat orchestrator for testing flat delegation hierarchy ([8b847ba](https://github.com/nicsuzor/academicOps/commit/8b847ba714924545bebbf3d88e340da8cb075644))
- **aops-jr:** restore exit_reflection gate and finalize face plugin extraction ([e9da3fc](https://github.com/nicsuzor/academicOps/commit/e9da3fc3217e23b03b2bbefce7fb40b72d0ae545))
- **diagram:** add prose guidelines, diff mode, resize fit, overlap & render scripts to diagram skill ([6c984ab](https://github.com/nicsuzor/academicOps/commit/6c984abc653968bddafa1d9af2f8262718633d28))
- **diagram:** address library items from the edit scripts ([1b6d4e2](https://github.com/nicsuzor/academicOps/commit/1b6d4e21703e72a96f90b67d2e434e5b1508f257))
- **diagram:** bundle ten planning libraries ([00c9d95](https://github.com/nicsuzor/academicOps/commit/00c9d951f6a0f804d725872f263a0e9c4801ce7b))
- **diagram:** efficient .excalidraw handling, library addressing, and ten planning libraries ([5131281](https://github.com/nicsuzor/academicOps/commit/51312812a69469a15a42c3e3a2831bc9dcfd8b09))
- **diagram:** read/edit protocol + canned viewer for large .excalidraw files ([918877f](https://github.com/nicsuzor/academicOps/commit/918877f41be3598a2ab0bfb6b6bd25f0af5780f3))
- **enforcement:** take the rule roster and permission surface dark ([9f4644e](https://github.com/nicsuzor/academicOps/commit/9f4644eeca3c70ac58f2c1df5d41b01078ae9bcf))
- **hooks:** consolidate Stop-time reminders into the exit_reflection gate ([3a1efa5](https://github.com/nicsuzor/academicOps/commit/3a1efa51d45c2dc464bf3811aa3f89faf7762ba2))
- **hooks:** consolidate Stop-time reminders into the exit_reflection gate ([622cb11](https://github.com/nicsuzor/academicOps/commit/622cb1198411bf79b74e3372f67ff0e7a635bf7d))
- **hooks:** suppress verify-reminder PostToolUse hook for background Agent launches (aops_c6a13ad1) ([430e3b9](https://github.com/nicsuzor/academicOps/commit/430e3b9ca03e10ebc20d0507303a1624448d5325))
- **hooks:** suppress verify-reminder PostToolUse hook for background Agent launches (aops_c6a13ad1) ([#2323](https://github.com/nicsuzor/academicOps/issues/2323)) ([06d3f9c](https://github.com/nicsuzor/academicOps/commit/06d3f9c334001c1068f443a7dfb7505ba52e4b5f))
- **packaging:** package aops-pkb as standalone installable plugin (aops_de6e9b52) ([a0b3d4d](https://github.com/nicsuzor/academicOps/commit/a0b3d4daee0f0a4b5e5a17b9ea6857421f8d0d4f))
- **pkb:** ship the task pipeline — capture, situate, brief, reconcile ([18eb80b](https://github.com/nicsuzor/academicOps/commit/18eb80b4afb71c265451141ec856d3a4c98cef80))
- **polecat:** persist run record exit code, commits, image digest, container id, seeded prompt to run.json (aops_9b03ee22) ([b6f391c](https://github.com/nicsuzor/academicOps/commit/b6f391c53cacc276853082d5e903437fa5d95e21))
- **polecat:** relocate polecat dispatch into core + rescope aops-jr ([abef6b4](https://github.com/nicsuzor/academicOps/commit/abef6b4a39fe1d3bc25920d194fd87d89d23b9c6))
- **polecat:** relocate polecat dispatch into core + rescope aops-jr ([e2ec427](https://github.com/nicsuzor/academicOps/commit/e2ec427314e15c534c06894396b004244490eb4c))
- **polecat:** require git identity in polecat.yaml with no host env fallback ([15f1bdc](https://github.com/nicsuzor/academicOps/commit/15f1bdcc5b3ca2e4d1df6d9bafd383d41a9cdd41))
- **polecat:** resolve isolated workspace HEAD and origin from canonical_dir ([a5a02c6](https://github.com/nicsuzor/academicOps/commit/a5a02c6f40e4d9f5d23a9df8a0568c7e913919ae))
- **polecat:** set push.autoSetupRemote=true on local clone ([c7dceb9](https://github.com/nicsuzor/academicOps/commit/c7dceb9cfe05309ea35d51c068dea2bdd1ed1d8c))
- **pr-reviewer:** add enforcement-change doc-currency check ([749a2ee](https://github.com/nicsuzor/academicOps/commit/749a2ee5e30d34488dbf033bcfc4edfb94ec7978))
- **pr-reviewer:** add enforcement-change doc-currency check ([8cb7d57](https://github.com/nicsuzor/academicOps/commit/8cb7d5753bd0d0e27c62a6b2007285630691669e))
- transcript discovery, launcher sanitization, OTEL telemetry, and 4-tier renderer hardening ([9ebb6d8](https://github.com/nicsuzor/academicOps/commit/9ebb6d872224bcc89444264d3b1cdbb57f580175))
- **transcripts:** differentiate human prompts from hook-injected context (aops_94fee2b1) ([204f6fb](https://github.com/nicsuzor/academicOps/commit/204f6fb43fd500ba645f07246db7228e4648ae7c))
- **transcripts:** discover polecat sessions under $AOPS_SESSIONS/logs/ (aops_3bb813f6) ([8b491e1](https://github.com/nicsuzor/academicOps/commit/8b491e16b082b3cfea382102c5c8442501dd9260))
- **v0.5:** install ergonomics for aops-jr and reflexes-cope optional plugins (epic_9a866589) ([1de9abd](https://github.com/nicsuzor/academicOps/commit/1de9abd2526ac003be643b1bcd7e093524c00595))
- **v0.5:** redirect PR [#2306](https://github.com/nicsuzor/academicOps/issues/2306) to reflexes-cope plugin and strip core quality gates (epic_7015bc7b, epic_2150b2b4) ([af17e3b](https://github.com/nicsuzor/academicOps/commit/af17e3bf14f29a973802d131ace3cbd4f3fbd870))
- **v0.5:** redirect PR [#2306](https://github.com/nicsuzor/academicOps/issues/2306) to reflexes-cope plugin and strip core quality gates (epic_7015bc7b, epic_2150b2b4) ([a9e7e13](https://github.com/nicsuzor/academicOps/commit/a9e7e1350d2ad72d3e0bd8dd717d00ec9952f5a6))

### Bug Fixes

- address Copilot review comments on ida-flat PR ([9bcc99f](https://github.com/nicsuzor/academicOps/commit/9bcc99f49ce26ba7adef2fdfe489f70125728496))
- **agents:** break agent/skill fork cycles and repair the hearsay handler ([b2de4b1](https://github.com/nicsuzor/academicOps/commit/b2de4b1f59511faf70f392567b9506b7832038c4))
- **aops-jr:** configure hatchling build to allow empty package list ([#2324](https://github.com/nicsuzor/academicOps/issues/2324)) ([a7923ba](https://github.com/nicsuzor/academicOps/commit/a7923ba5bd8aced91ba2dc2fa74794104a6d6e11))
- **aops-jr:** stop building aops-jr as a wheel — package = false ([2849438](https://github.com/nicsuzor/academicOps/commit/2849438efc026968c9fa60b792218d245f67dc36))
- **aops-jr:** stop building aops-jr as a wheel — package = false ([d9e46c0](https://github.com/nicsuzor/academicOps/commit/d9e46c05b6ad66b3e3dc2e33d04efda6db39f92d))
- **brief:** resolve the index-drift conflict and give brief a raw-note path ([12acf86](https://github.com/nicsuzor/academicOps/commit/12acf867a97b8eb18536f8da475f19fee514385d))
- **build:** clean install-dev agy plugin handling and repoint specs to orchestrate ([01a9fca](https://github.com/nicsuzor/academicOps/commit/01a9fca7f739806db4572549df12a147a71a1b84))
- **build:** clean install-dev agy plugin handling and repoint specs to orchestrate ([80baa8b](https://github.com/nicsuzor/academicOps/commit/80baa8b168745c0c1e56fbe44f4f1e43b8daff06))
- **build:** dedupe orchestrate entry in marketplace.toml from merge ([e272642](https://github.com/nicsuzor/academicOps/commit/e27264267c3aadb60258842fe5c9977639eb6dae))
- **build:** wire orchestrate into the build, fix agy hook regression, address review ([a262cf6](https://github.com/nicsuzor/academicOps/commit/a262cf611006f1495d3bfbbd4aa2355af0c4dd7c))
- **build:** wire the PKB MCP server for agy via the resolvable placeholder ([fefcb21](https://github.com/nicsuzor/academicOps/commit/fefcb21b4eaa55fea8ed17374fda976b9de407b7))
- **cloud-setup:** retry tailscale install, correct plugin install list ([463beee](https://github.com/nicsuzor/academicOps/commit/463beee523f5823c1ef414141706cd100b1eb47b))
- correct PKB tool-permission name in james and rbg ([28b4103](https://github.com/nicsuzor/academicOps/commit/28b41031fe4251ee188d3d60f761b4a75f068a60))
- **cron:** pin repo-sync fetch to origin and force HTTPS for all git subprocesses ([90d2721](https://github.com/nicsuzor/academicOps/commit/90d2721128e04925f68e06d4b80151aa5868efb7))
- **cron:** pin repo-sync fetch to origin and force HTTPS for all git subprocesses ([bd9a3d7](https://github.com/nicsuzor/academicOps/commit/bd9a3d70ed9e0bad37c0787e85212fc08f4b2b33))
- **dogfood:** restore force of named-surface invariant ([48fbbff](https://github.com/nicsuzor/academicOps/commit/48fbbffd0ee337351c2a0b896978e0ef148da475))
- **gates:** canonicalize gate_dispatch.py into aops/hooks/, remove plugin duplicates ([e25759f](https://github.com/nicsuzor/academicOps/commit/e25759fecc8e076a1eba1d3b840dc266cd8e6da6))
- **gates:** remove reflexes-cope's hand-maintained gate primitives, use canonical fan-out ([6b70ee5](https://github.com/nicsuzor/academicOps/commit/6b70ee555f5a79894fcf8e7c4a2f02e3249c1714))
- **harness:** headless non-interactive fail-fast + PEP420 hooks namespace (aops_87e42d7c, aops_bb21f24e) — recovered from undelivered worker run ([72781ce](https://github.com/nicsuzor/academicOps/commit/72781cee9d30ec47dcb9fe4db6918699516594e0))
- **hooks:** drop the cross-plugin read of rbg's OTel module ([065997f](https://github.com/nicsuzor/academicOps/commit/065997fab8b2b4379693226e77092951f45cc9b3)), closes [#2373](https://github.com/nicsuzor/academicOps/issues/2373)
- **hooks:** restore the Stop registrations and rbg's ruleset advisory ([fd346e4](https://github.com/nicsuzor/academicOps/commit/fd346e4b3c1cfe190c3d144697dd1f8eda34f530))
- **hooks:** use datetime.UTC alias in the hook-fire log timestamp ([f6c3de9](https://github.com/nicsuzor/academicOps/commit/f6c3de9c206893bd0416e97cfa664f5301396b10))
- **hooks:** write polecat-session-hooks.jsonl on every hook fire ([e19c252](https://github.com/nicsuzor/academicOps/commit/e19c2523a5e9dd50f98804c2412e0067b85da8bd))
- **lint:** widen refcheck to root-level docs; fix stale copilot-instructions claims ([9f6f840](https://github.com/nicsuzor/academicOps/commit/9f6f840355fbb43f0515f624503d921c4f79ef9d))
- make the credential-isolation message truthful ([73529b0](https://github.com/nicsuzor/academicOps/commit/73529b0ee77aaa5e86a8a526a31a223530151a28))
- narrow sessionId so basedpyright accepts it, and run it in make lint ([f9ef1c8](https://github.com/nicsuzor/academicOps/commit/f9ef1c88f3e53dd242203d4a7af1c4adb6fe667f))
- **pkb:** /q places captured work properly; drop carried-forward scars ([20514f8](https://github.com/nicsuzor/academicOps/commit/20514f84d5281eb0421b4eddcdd8daff0f28451a))
- **pkb:** cut on who does the work, not on whether it blocks ([5b11d74](https://github.com/nicsuzor/academicOps/commit/5b11d741c24d506c323ff8d8e333ba42cd89dc40))
- **polecat:** a loopback service URL was unreachable from every container ([325c7e6](https://github.com/nicsuzor/academicOps/commit/325c7e63271dd416ab0d18c9efda82e7620f717c))
- **polecat:** add harness delivery guard against uncommitted changes and unpushed commits (aops_651f7e5c) ([684ecb7](https://github.com/nicsuzor/academicOps/commit/684ecb78b4f9b1d1fc471bb9268b742045d79532))
- **polecat:** interpolate resolved polecat_home in workspace error ([a2f238b](https://github.com/nicsuzor/academicOps/commit/a2f238b2b58a31cea0174940b009222badea5ddc))
- **polecat:** interpolate resolved polecat_home in workspace error ([64dc3b0](https://github.com/nicsuzor/academicOps/commit/64dc3b041b44e891b7bbf667de643d8dac39063c))
- **polecat:** isolate worker workspace via per-session git worktree ([ac8a6bb](https://github.com/nicsuzor/academicOps/commit/ac8a6bb29d0aa412a699da9b0c86d2959d8cfcf4))
- **polecat:** isolate workspaces via standalone clone, not linked worktree ([eb39a0e](https://github.com/nicsuzor/academicOps/commit/eb39a0ee0f7a7015b0864028b1a176bb03e9f44f))
- **polecat:** supply git_identity in test mocks and type annotations ([213ba83](https://github.com/nicsuzor/academicOps/commit/213ba83d88e34d83b5ce1e9dd82451e1a7dc1239))
- **provenance:** widen _load_json's catch so a bad registry can't drop the handler ([e6e124a](https://github.com/nicsuzor/academicOps/commit/e6e124aadfe6def84bc5b76555b9ebee471d4b98))
- reconstruct whole sessions, and let an empty session come back ([97138d6](https://github.com/nicsuzor/academicOps/commit/97138d6cf6d7c57483330f5e3e3b04fb3b2178b2))
- redact the sidecar's values, not its serialised text ([0f0e4bb](https://github.com/nicsuzor/academicOps/commit/0f0e4bba51b956400a01ba9ebae9f63f45b66453))
- repair live v0.6 defects found by self-test diagnosis and PR review ([b7eb711](https://github.com/nicsuzor/academicOps/commit/b7eb71153adc6e7c5fd3cf386d6ed8e15cf6258f))
- satisfy ruff import ordering in orchestrate hooks ([dc916a2](https://github.com/nicsuzor/academicOps/commit/dc916a24abbfd13cc75b02aff322e488787025e2))
- **telemetry:** stop reporting against a denominator a hook can't observe ([c925263](https://github.com/nicsuzor/academicOps/commit/c9252639277985b2f4d5106e952a611760d7a6a4))
- **tests:** update aops-jr/polecat -&gt; aops/polecat import paths post-relocation ([65b1f96](https://github.com/nicsuzor/academicOps/commit/65b1f96e59dd956478fc1540f530d109c5f01d01))
- **transcripts:** bound the push in a retry loop against the cross-host race ([1b626ac](https://github.com/nicsuzor/academicOps/commit/1b626ac4375d82edae79ad836ae9ae5b6ffabbdc))
- **transcripts:** corrected token and cost accounting (aops_6d2abff5) ([6332bed](https://github.com/nicsuzor/academicOps/commit/6332bed7b9ce7c126a4ede158647674f890e6080))
- **transcripts:** pull before pushing the sessions repo ([7787f5d](https://github.com/nicsuzor/academicOps/commit/7787f5da42f565263084f2a0f7a2bcb954de504f))
- **transcripts:** pull before pushing the sessions repo (non-fast-forward push silently drops transcripts) ([6bdaf28](https://github.com/nicsuzor/academicOps/commit/6bdaf281a20b624890e12cb1386b82ac865622aa))
- **transcripts:** reinstate secret redaction and fail the aops-ts sync closed ([1e5ef49](https://github.com/nicsuzor/academicOps/commit/1e5ef491b3f32420fdc55cc6351d09f6225062c1))
- **transcripts:** reinstate secret redaction, fail aops-ts sync closed ([48ed4f2](https://github.com/nicsuzor/academicOps/commit/48ed4f26e6de13376774bbafcb95e9138721afae))
- **transcripts:** stop HTML escaping from defeating credential redaction ([#2373](https://github.com/nicsuzor/academicOps/issues/2373) remediation) ([950f432](https://github.com/nicsuzor/academicOps/commit/950f432b0d79e732c9d235bc64e9977a76a9392a))
- **transcripts:** stop HTML-escaping from defeating credential redaction ([3788cd1](https://github.com/nicsuzor/academicOps/commit/3788cd13838f90a74a3886fd5b8e702ab11bcc7a)), closes [#2373](https://github.com/nicsuzor/academicOps/issues/2373)
- **v0.5:** repoint core hooks to shipped files, dedupe PostToolUse, fix topology spec, add INSTALL.md ([82b1b34](https://github.com/nicsuzor/academicOps/commit/82b1b34ad54197d4c3c2913593cf05ba2f6f05c0))
- **workflows:** investigation composed an empty review set and halted brief ([bb23d55](https://github.com/nicsuzor/academicOps/commit/bb23d5520db6bc74dd914628fdbea83fcab59d45))

### Performance Improvements

- **docker:** order polecat image layers by invalidation frequency ([6e13894](https://github.com/nicsuzor/academicOps/commit/6e138940589bb18f85f8554c0a9d0726183f51ca))

### Code Refactoring

- **diagram:** drop the v1 libraries ([b4ccbd8](https://github.com/nicsuzor/academicOps/commit/b4ccbd890d1d74751a829e0db060be9db9886f4c))
- **gates:** establish single canonical source for gate primitives and strip build artifacts from plugins ([6243c4a](https://github.com/nicsuzor/academicOps/commit/6243c4ad52789ef713e8caa466069ab07def199b))
- **ida:** plan becomes strategize and moves to ida ([08215b8](https://github.com/nicsuzor/academicOps/commit/08215b85fc100c907b6094b63d620e8fad6c9d42))
- **instructions:** decouple brief's review gate and dispatch's own rules ([59301f8](https://github.com/nicsuzor/academicOps/commit/59301f831f4a16bc6f8ff5ee4884a136f4b0c373))
- **instructions:** fold situate into brief, cut library cookbooks ([ced61e0](https://github.com/nicsuzor/academicOps/commit/ced61e026b631b719acbca7b1b2c62a108ec276a))
- **instructions:** v0.7 instruction–design alignment audit ([d4aae7f](https://github.com/nicsuzor/academicOps/commit/d4aae7f61c8d6bf4608c3acbd7986adf75826620))
- **instructions:** v0.7 instruction–design alignment audit (−6,908 lines, −38%) ([b60072b](https://github.com/nicsuzor/academicOps/commit/b60072b3754698130b8070da3258f3a314e95cc8))
- Migrate doctrine to axioms and remove includes from agents ([e3b3666](https://github.com/nicsuzor/academicOps/commit/e3b3666241e572261eae50b5aaf28d64c15b848f))
- **pkb:** merge workflow into brief; brief composes and stops ([98359b9](https://github.com/nicsuzor/academicOps/commit/98359b91d05d27c13699f14a1d71539d73e2e0fc))
- **polecat:** drift cleanup — no dispatch exceptions, no settings-mirror tests ([ad922dc](https://github.com/nicsuzor/academicOps/commit/ad922dc41d673ffaaf651a4d255790cd54614168))
- reorganise into a shared core with six plugins ([32695d9](https://github.com/nicsuzor/academicOps/commit/32695d9eff822ddfa31b04dc20d2ec01e1d0d17d))
- v0.6 reorganise into a shared core with six plugins ([f3f44bf](https://github.com/nicsuzor/academicOps/commit/f3f44bfd0e4b5b97e0c01a47f6d8445bb49b94a5))

### Documentation

- add enforcement register, slim the enforcement spec ([740098d](https://github.com/nicsuzor/academicOps/commit/740098d0a692f1a1bfbbd4edbfcd674ba0360a94))
- **audit:** commit sentinel handoff and multi-agent execution audit records ([4e36e53](https://github.com/nicsuzor/academicOps/commit/4e36e53232ecda2efc20bd40a26d701c73fee36f))
- commit/push discipline + diagram tandem-editing rules ([#2367](https://github.com/nicsuzor/academicOps/issues/2367)) ([866724a](https://github.com/nicsuzor/academicOps/commit/866724a29f0cbe6acd27461bbe66521e6cda271f))
- **core:** require immediate commit+push, forbid backup files ([0afd38e](https://github.com/nicsuzor/academicOps/commit/0afd38e426b95ed2639a6593953764fa839aad18))
- correct transcript converter availability references ([8533888](https://github.com/nicsuzor/academicOps/commit/8533888bd7147803514031b687f316420ad7f753))
- **debug:** document double-dash flag separation and response assertions in debug skill ([f0b2748](https://github.com/nicsuzor/academicOps/commit/f0b2748439e101e8d0f9156636045a81bba8c85a))
- **debug:** require verifying model response string in section 3 ([6277788](https://github.com/nicsuzor/academicOps/commit/627778861fa5b4d810f357fd188efb601a847f5f))
- **diagram:** document the live tandem-editing workflow ([a64a950](https://github.com/nicsuzor/academicOps/commit/a64a9504654e0ea8f146fc5864d9e42c8458adb5))
- **diagram:** forbid narrating change history in diagrams ([1cbbca2](https://github.com/nicsuzor/academicOps/commit/1cbbca2a58ad2d9be1158df146b12058ae4a4173))
- **doctrine:** named-teammate spawns cannot carry a return contract ([2855822](https://github.com/nicsuzor/academicOps/commit/2855822e668d16f576969fedc8f96390f3b6f68d))
- **doctrine:** promote seven ratified junior rules into the plugins ([bb54a7c](https://github.com/nicsuzor/academicOps/commit/bb54a7ccc824f084467981dba3fcb4e03ac34866))
- **dogfood:** add surface invariant to skill ([12a2211](https://github.com/nicsuzor/academicOps/commit/12a22119e1b22a64ef20cafd405399d1c82f3d39))
- **enforcement:** update enforcement.md currency for reflexes-cope advisory evaluator (epic_612a4efb, epic_c01c4dca) ([dcb29c7](https://github.com/nicsuzor/academicOps/commit/dcb29c71c13b04ec02fde081f67a70171db2d6ed))
- **packaging:** resolve doctrine-source deferral in v0.5 topology spec ([1364edf](https://github.com/nicsuzor/academicOps/commit/1364edff4a72f2508cb99c18e2d2ee25f5a7ce37))
- plugin-rename drift, rbg stop-gate contradiction, dangling refs ([9bc918e](https://github.com/nicsuzor/academicOps/commit/9bc918e4aa89005f9cd16ebac63ae2c9b26431fe))
- **polecat:** document POLECAT_AGENT_HOME in the agy dev-loop ([6463d05](https://github.com/nicsuzor/academicOps/commit/6463d05281bcba51a2715566e6543d38f6e914af))
- **polecat:** document seed-delivery verification guard ([6235dfc](https://github.com/nicsuzor/academicOps/commit/6235dfc140b7b0427abf6ea0edb0f5a8167c07b5))
- **polecat:** document seed-delivery verification guard ([93df470](https://github.com/nicsuzor/academicOps/commit/93df470a528540f7fc33877367841124d0685ba8))
- **polecat:** fix agy transcript path in tmux-interactive-driving spec ([c4788cf](https://github.com/nicsuzor/academicOps/commit/c4788cf9bffd11e338934f8b0444f90ad39cbfd7))
- re-verify the enforcement register against v7.1 ([8f598c7](https://github.com/nicsuzor/academicOps/commit/8f598c7d144d5d51ec53a16e8507285c21e1a10f))
- **readme:** repoint stale aops-jr/polecat + aops-pkb/agents paths to v0.5 layout ([475869e](https://github.com/nicsuzor/academicOps/commit/475869e34a7b48e1004c4d17bd36f411f124f2ba))
- replace dead scripts/format.sh reference with real commands ([abb8839](https://github.com/nicsuzor/academicOps/commit/abb88398b876a4a3973331aa9234b6a59954eb70))
- repoint references left dangling by the lib/doctrine dissolution ([ac08dbe](https://github.com/nicsuzor/academicOps/commit/ac08dbef9b815adbd2842072ff5fd2b3278caeb5))
- repoint references that moved, remove those with no successor ([1142b0a](https://github.com/nicsuzor/academicOps/commit/1142b0ad8c5c37ec2d09c2ef2b3d8ca6ddcb27ae))
- resolve the dangling lesson-routing include and the add-rule dead ends ([180c7a2](https://github.com/nicsuzor/academicOps/commit/180c7a200dfbd68986c78dbb6570f0caf059eb49))
- **skills:** field-test — end-to-end validation guide as goals and checks ([370e25c](https://github.com/nicsuzor/academicOps/commit/370e25c6f305a5f9b636f6ecd4c7745433e2747d))
- **skills:** field-test §11 — publish grades on the wired map ([3dffc3c](https://github.com/nicsuzor/academicOps/commit/3dffc3c3e24b3ea4c80c911382840e35bfd3ce77))
- **specs:** add v0.5 modular topology + gate disposition spec ([fb42f21](https://github.com/nicsuzor/academicOps/commit/fb42f21e7d119563ec4d33eda07c3a2773a7b34e))
- **specs:** apply strategic-review findings to v0.5 topology spec ([77cdeeb](https://github.com/nicsuzor/academicOps/commit/77cdeeb20507ad7a28c8478a839a00272f052dc1))
- **specs:** correct stale findings in v0.5 topology spec ([d047c12](https://github.com/nicsuzor/academicOps/commit/d047c129e201137e00a399e742d6f52c97a0189c))
- **specs:** correct stale findings in v0.5 topology spec ([154fd63](https://github.com/nicsuzor/academicOps/commit/154fd6375a51c5450eb5cf6b033594430325d811))
- **specs:** correct two records the merge made untrue ([2b8c8c4](https://github.com/nicsuzor/academicOps/commit/2b8c8c490fa98d30ef5d0133d6723787d92288fa)), closes [#2373](https://github.com/nicsuzor/academicOps/issues/2373)
- **specs:** dist size is not a constraint ([115000d](https://github.com/nicsuzor/academicOps/commit/115000dc86291458764c4e36e00b3144b0240eeb))
- **specs:** fold plugin README pointer into the layout paragraph ([a8524ae](https://github.com/nicsuzor/academicOps/commit/a8524ae855a2dc472e72a2f550b53dbc9b764ac7))
- **specs:** govern plugin READMEs from the doc taxonomy ([67f86e2](https://github.com/nicsuzor/academicOps/commit/67f86e29710f26337b670e5abd77cb985f3820f3))
- **specs:** govern plugin READMEs from the doc taxonomy ([c4210c4](https://github.com/nicsuzor/academicOps/commit/c4210c49159b8ddd08358ae6e72319b6f7bb4196))
- **specs:** v0.5 modular topology + gate-disposition spec ([48d04de](https://github.com/nicsuzor/academicOps/commit/48d04def34d947c598a619bf6d6aa0f773612182))
- the rule channel has three delivery paths, not two ([c122b0c](https://github.com/nicsuzor/academicOps/commit/c122b0ce1baac77b4e9d5e4152bc6cd7fbada399))
- update CORE.md with established cause of [#2387](https://github.com/nicsuzor/academicOps/issues/2387) ([948ef29](https://github.com/nicsuzor/academicOps/commit/948ef29e6bd0247b3dc84a5c8c8253259233aba9))
- update ida's quiet gate docs to warn-shaped, not blocking ([9ae663e](https://github.com/nicsuzor/academicOps/commit/9ae663e694bdb7247e059036045db44a460eb836))
- **v0.4:** reconcile hook/enforcement specs with shipped code ([103de19](https://github.com/nicsuzor/academicOps/commit/103de19c32ae721fada35fb25bda6f625266c6ad))
- **v0.4:** reconcile hook/enforcement specs with shipped code ([6ad4580](https://github.com/nicsuzor/academicOps/commit/6ad458098bdcf66e372dab69fa068655cc136e44))
- **v0.4:** redirect deleted ENFORCEMENT-MAP.md references to enforcement.md ([1857fb8](https://github.com/nicsuzor/academicOps/commit/1857fb812cb9accdda40651ef505afaa72a02fde))
- worker proves, dispatcher bounces ([067a01f](https://github.com/nicsuzor/academicOps/commit/067a01f0a73c65aabf09fe6757b330bd8499d747))

### CI/CD

- build dist before pytest so shipped-artifact tests actually run ([c433d70](https://github.com/nicsuzor/academicOps/commit/c433d70ff9dc2092a6c7379713029a5c2b950346))

### Build System

- **agy:** reconcile the reapplied pkb MCP fix with the shipped-config sweep ([f41e191](https://github.com/nicsuzor/academicOps/commit/f41e191634defd7496e35042801f951f161c10fd))

### Tests

- restore ida Stop-gate message-fidelity coverage, warn-shaped ([00934dd](https://github.com/nicsuzor/academicOps/commit/00934dd03cb7145b941f2762a7cdd69dcbc6cc08))
- restore suite to green after the lib/hooks consolidation ([35bd591](https://github.com/nicsuzor/academicOps/commit/35bd591307d391089457592bb192b96f98b01ea3))
- skip manifest checks on an unbuilt tree instead of erroring at collection ([9330369](https://github.com/nicsuzor/academicOps/commit/9330369019fd1691e137a9b6367cb28fa83ace6d))
- skip manifest checks on an unbuilt tree instead of erroring at collection ([798a79a](https://github.com/nicsuzor/academicOps/commit/798a79a7cec2054f9a183975725fe7a0987886e5))
- **transcripts:** align assertions with Markdown carrying text verbatim ([9b89796](https://github.com/nicsuzor/academicOps/commit/9b8979677aeb776e4319d54c02d8e38f1d095ee5)), closes [#2373](https://github.com/nicsuzor/academicOps/issues/2373)

### Miscellaneous

- **agents:** strip dangling Curia reference from qa.agent.md ([14582da](https://github.com/nicsuzor/academicOps/commit/14582da3289a20b410465a12f6b54d64d2bf908a))
- **dev:** release 0.3.80 ([6f2f7d1](https://github.com/nicsuzor/academicOps/commit/6f2f7d16aea4b12f72aa115c88e9861da3c509f3))
- **dev:** release 0.3.81 ([33f9e41](https://github.com/nicsuzor/academicOps/commit/33f9e41d4ef6f66d239ad690e4bf2d2cf8192a84))
- **dev:** release 0.3.81 ([c0c5923](https://github.com/nicsuzor/academicOps/commit/c0c59234ade9eed6ade6d9a619c8d66945144c8a))
- drop agent scratch workspaces committed under .agents/ ([226cb7e](https://github.com/nicsuzor/academicOps/commit/226cb7eed41e8bfad4d0b2b24c5b1b831469c44b))
- **instructions:** revise all agent & skill instruction files to prompting best practices ([b7f3c6e](https://github.com/nicsuzor/academicOps/commit/b7f3c6e0ab7a55ae4ecfb4f6d700c06339eb53e7))
- remove [@include](https://github.com/include) functionality and inline single-use doctrines ([7e6519b](https://github.com/nicsuzor/academicOps/commit/7e6519b056867bb721d8b61c9299626c8a6171a1))
- update uv.lock for release ([a1c751e](https://github.com/nicsuzor/academicOps/commit/a1c751edb711c271b324b8f10902d7b115497626))
- update uv.lock for release ([3f7517b](https://github.com/nicsuzor/academicOps/commit/3f7517b0939a83838c6e2bb89259d5333c4a70ac))
- update version to v0.7.0 ([544b151](https://github.com/nicsuzor/academicOps/commit/544b15113af96dae008594276ad470021bb0829a))

## [0.7.0](https://github.com/nicsuzor/academicOps/compare/v0.3.80...v0.3.81) (2026-08-04)

### Features

- Add unified ida-flat orchestrator ([bd74ab6](https://github.com/nicsuzor/academicOps/commit/bd74ab610d0d5b06f24c14695b3786d6501933c7))
- add unified ida-flat orchestrator for testing flat delegation hierarchy ([8b847ba](https://github.com/nicsuzor/academicOps/commit/8b847ba714924545bebbf3d88e340da8cb075644))
- **aops-jr:** restore exit_reflection gate and finalize face plugin extraction ([e9da3fc](https://github.com/nicsuzor/academicOps/commit/e9da3fc3217e23b03b2bbefce7fb40b72d0ae545))
- **diagram:** address library items from the edit scripts ([1b6d4e2](https://github.com/nicsuzor/academicOps/commit/1b6d4e21703e72a96f90b67d2e434e5b1508f257))
- **diagram:** bundle ten planning libraries ([00c9d95](https://github.com/nicsuzor/academicOps/commit/00c9d951f6a0f804d725872f263a0e9c4801ce7b))
- **diagram:** efficient .excalidraw handling, library addressing, and ten planning libraries ([5131281](https://github.com/nicsuzor/academicOps/commit/51312812a69469a15a42c3e3a2831bc9dcfd8b09))
- **diagram:** read/edit protocol + canned viewer for large .excalidraw files ([918877f](https://github.com/nicsuzor/academicOps/commit/918877f41be3598a2ab0bfb6b6bd25f0af5780f3))
- **enforcement:** take the rule roster and permission surface dark ([9f4644e](https://github.com/nicsuzor/academicOps/commit/9f4644eeca3c70ac58f2c1df5d41b01078ae9bcf))
- **hooks:** consolidate Stop-time reminders into the exit_reflection gate ([3a1efa5](https://github.com/nicsuzor/academicOps/commit/3a1efa51d45c2dc464bf3811aa3f89faf7762ba2))
- **hooks:** consolidate Stop-time reminders into the exit_reflection gate ([622cb11](https://github.com/nicsuzor/academicOps/commit/622cb1198411bf79b74e3372f67ff0e7a635bf7d))
- **hooks:** suppress verify-reminder PostToolUse hook for background Agent launches (aops_c6a13ad1) ([430e3b9](https://github.com/nicsuzor/academicOps/commit/430e3b9ca03e10ebc20d0507303a1624448d5325))
- **hooks:** suppress verify-reminder PostToolUse hook for background Agent launches (aops_c6a13ad1) ([#2323](https://github.com/nicsuzor/academicOps/issues/2323)) ([06d3f9c](https://github.com/nicsuzor/academicOps/commit/06d3f9c334001c1068f443a7dfb7505ba52e4b5f))
- **packaging:** package aops-pkb as standalone installable plugin (aops_de6e9b52) ([a0b3d4d](https://github.com/nicsuzor/academicOps/commit/a0b3d4daee0f0a4b5e5a17b9ea6857421f8d0d4f))
- **pkb:** ship the task pipeline — capture, situate, brief, reconcile ([18eb80b](https://github.com/nicsuzor/academicOps/commit/18eb80b4afb71c265451141ec856d3a4c98cef80))
- **polecat:** relocate polecat dispatch into core + rescope aops-jr ([abef6b4](https://github.com/nicsuzor/academicOps/commit/abef6b4a39fe1d3bc25920d194fd87d89d23b9c6))
- **polecat:** relocate polecat dispatch into core + rescope aops-jr ([e2ec427](https://github.com/nicsuzor/academicOps/commit/e2ec427314e15c534c06894396b004244490eb4c))
- **polecat:** require git identity in polecat.yaml with no host env fallback ([15f1bdc](https://github.com/nicsuzor/academicOps/commit/15f1bdcc5b3ca2e4d1df6d9bafd383d41a9cdd41))
- **polecat:** resolve isolated workspace HEAD and origin from canonical_dir ([a5a02c6](https://github.com/nicsuzor/academicOps/commit/a5a02c6f40e4d9f5d23a9df8a0568c7e913919ae))
- **polecat:** set push.autoSetupRemote=true on local clone ([c7dceb9](https://github.com/nicsuzor/academicOps/commit/c7dceb9cfe05309ea35d51c068dea2bdd1ed1d8c))
- **pr-reviewer:** add enforcement-change doc-currency check ([749a2ee](https://github.com/nicsuzor/academicOps/commit/749a2ee5e30d34488dbf033bcfc4edfb94ec7978))
- **pr-reviewer:** add enforcement-change doc-currency check ([8cb7d57](https://github.com/nicsuzor/academicOps/commit/8cb7d5753bd0d0e27c62a6b2007285630691669e))
- **v0.5:** install ergonomics for aops-jr and reflexes-cope optional plugins (epic_9a866589) ([1de9abd](https://github.com/nicsuzor/academicOps/commit/1de9abd2526ac003be643b1bcd7e093524c00595))
- **v0.5:** redirect PR [#2306](https://github.com/nicsuzor/academicOps/issues/2306) to reflexes-cope plugin and strip core quality gates (epic_7015bc7b, epic_2150b2b4) ([af17e3b](https://github.com/nicsuzor/academicOps/commit/af17e3bf14f29a973802d131ace3cbd4f3fbd870))
- **v0.5:** redirect PR [#2306](https://github.com/nicsuzor/academicOps/issues/2306) to reflexes-cope plugin and strip core quality gates (epic_7015bc7b, epic_2150b2b4) ([a9e7e13](https://github.com/nicsuzor/academicOps/commit/a9e7e1350d2ad72d3e0bd8dd717d00ec9952f5a6))

### Bug Fixes

- address Copilot review comments on ida-flat PR ([9bcc99f](https://github.com/nicsuzor/academicOps/commit/9bcc99f49ce26ba7adef2fdfe489f70125728496))
- **agents:** break agent/skill fork cycles and repair the hearsay handler ([b2de4b1](https://github.com/nicsuzor/academicOps/commit/b2de4b1f59511faf70f392567b9506b7832038c4))
- **aops-jr:** configure hatchling build to allow empty package list ([#2324](https://github.com/nicsuzor/academicOps/issues/2324)) ([a7923ba](https://github.com/nicsuzor/academicOps/commit/a7923ba5bd8aced91ba2dc2fa74794104a6d6e11))
- **aops-jr:** stop building aops-jr as a wheel — package = false ([2849438](https://github.com/nicsuzor/academicOps/commit/2849438efc026968c9fa60b792218d245f67dc36))
- **aops-jr:** stop building aops-jr as a wheel — package = false ([d9e46c0](https://github.com/nicsuzor/academicOps/commit/d9e46c05b6ad66b3e3dc2e33d04efda6db39f92d))
- **brief:** resolve the index-drift conflict and give brief a raw-note path ([12acf86](https://github.com/nicsuzor/academicOps/commit/12acf867a97b8eb18536f8da475f19fee514385d))
- **build:** clean install-dev agy plugin handling and repoint specs to orchestrate ([01a9fca](https://github.com/nicsuzor/academicOps/commit/01a9fca7f739806db4572549df12a147a71a1b84))
- **build:** clean install-dev agy plugin handling and repoint specs to orchestrate ([80baa8b](https://github.com/nicsuzor/academicOps/commit/80baa8b168745c0c1e56fbe44f4f1e43b8daff06))
- **build:** dedupe orchestrate entry in marketplace.toml from merge ([e272642](https://github.com/nicsuzor/academicOps/commit/e27264267c3aadb60258842fe5c9977639eb6dae))
- **build:** wire orchestrate into the build, fix agy hook regression, address review ([a262cf6](https://github.com/nicsuzor/academicOps/commit/a262cf611006f1495d3bfbbd4aa2355af0c4dd7c))
- **build:** wire the PKB MCP server for agy via the resolvable placeholder ([fefcb21](https://github.com/nicsuzor/academicOps/commit/fefcb21b4eaa55fea8ed17374fda976b9de407b7))
- **cloud-setup:** retry tailscale install, correct plugin install list ([463beee](https://github.com/nicsuzor/academicOps/commit/463beee523f5823c1ef414141706cd100b1eb47b))
- correct PKB tool-permission name in james and rbg ([28b4103](https://github.com/nicsuzor/academicOps/commit/28b41031fe4251ee188d3d60f761b4a75f068a60))
- **gates:** canonicalize gate_dispatch.py into aops/hooks/, remove plugin duplicates ([e25759f](https://github.com/nicsuzor/academicOps/commit/e25759fecc8e076a1eba1d3b840dc266cd8e6da6))
- **gates:** remove reflexes-cope's hand-maintained gate primitives, use canonical fan-out ([6b70ee5](https://github.com/nicsuzor/academicOps/commit/6b70ee555f5a79894fcf8e7c4a2f02e3249c1714))
- **harness:** headless non-interactive fail-fast + PEP420 hooks namespace (aops_87e42d7c, aops_bb21f24e) — recovered from undelivered worker run ([72781ce](https://github.com/nicsuzor/academicOps/commit/72781cee9d30ec47dcb9fe4db6918699516594e0))
- **hooks:** restore the Stop registrations and rbg's ruleset advisory ([fd346e4](https://github.com/nicsuzor/academicOps/commit/fd346e4b3c1cfe190c3d144697dd1f8eda34f530))
- **hooks:** use datetime.UTC alias in the hook-fire log timestamp ([f6c3de9](https://github.com/nicsuzor/academicOps/commit/f6c3de9c206893bd0416e97cfa664f5301396b10))
- **hooks:** write polecat-session-hooks.jsonl on every hook fire ([e19c252](https://github.com/nicsuzor/academicOps/commit/e19c2523a5e9dd50f98804c2412e0067b85da8bd))
- **lint:** widen refcheck to root-level docs; fix stale copilot-instructions claims ([9f6f840](https://github.com/nicsuzor/academicOps/commit/9f6f840355fbb43f0515f624503d921c4f79ef9d))
- make the credential-isolation message truthful ([73529b0](https://github.com/nicsuzor/academicOps/commit/73529b0ee77aaa5e86a8a526a31a223530151a28))
- narrow sessionId so basedpyright accepts it, and run it in make lint ([f9ef1c8](https://github.com/nicsuzor/academicOps/commit/f9ef1c88f3e53dd242203d4a7af1c4adb6fe667f))
- **pkb:** /q places captured work properly; drop carried-forward scars ([20514f8](https://github.com/nicsuzor/academicOps/commit/20514f84d5281eb0421b4eddcdd8daff0f28451a))
- **pkb:** cut on who does the work, not on whether it blocks ([5b11d74](https://github.com/nicsuzor/academicOps/commit/5b11d741c24d506c323ff8d8e333ba42cd89dc40))
- **polecat:** a loopback service URL was unreachable from every container ([325c7e6](https://github.com/nicsuzor/academicOps/commit/325c7e63271dd416ab0d18c9efda82e7620f717c))
- **polecat:** add harness delivery guard against uncommitted changes and unpushed commits (aops_651f7e5c) ([684ecb7](https://github.com/nicsuzor/academicOps/commit/684ecb78b4f9b1d1fc471bb9268b742045d79532))
- **polecat:** interpolate resolved polecat_home in workspace error ([a2f238b](https://github.com/nicsuzor/academicOps/commit/a2f238b2b58a31cea0174940b009222badea5ddc))
- **polecat:** interpolate resolved polecat_home in workspace error ([64dc3b0](https://github.com/nicsuzor/academicOps/commit/64dc3b041b44e891b7bbf667de643d8dac39063c))
- **polecat:** isolate worker workspace via per-session git worktree ([ac8a6bb](https://github.com/nicsuzor/academicOps/commit/ac8a6bb29d0aa412a699da9b0c86d2959d8cfcf4))
- **polecat:** isolate workspaces via standalone clone, not linked worktree ([eb39a0e](https://github.com/nicsuzor/academicOps/commit/eb39a0ee0f7a7015b0864028b1a176bb03e9f44f))
- **polecat:** supply git_identity in test mocks and type annotations ([213ba83](https://github.com/nicsuzor/academicOps/commit/213ba83d88e34d83b5ce1e9dd82451e1a7dc1239))
- **provenance:** widen _load_json's catch so a bad registry can't drop the handler ([e6e124a](https://github.com/nicsuzor/academicOps/commit/e6e124aadfe6def84bc5b76555b9ebee471d4b98))
- reconstruct whole sessions, and let an empty session come back ([97138d6](https://github.com/nicsuzor/academicOps/commit/97138d6cf6d7c57483330f5e3e3b04fb3b2178b2))
- redact the sidecar's values, not its serialised text ([0f0e4bb](https://github.com/nicsuzor/academicOps/commit/0f0e4bba51b956400a01ba9ebae9f63f45b66453))
- repair live v0.6 defects found by self-test diagnosis and PR review ([b7eb711](https://github.com/nicsuzor/academicOps/commit/b7eb71153adc6e7c5fd3cf386d6ed8e15cf6258f))
- satisfy ruff import ordering in orchestrate hooks ([dc916a2](https://github.com/nicsuzor/academicOps/commit/dc916a24abbfd13cc75b02aff322e488787025e2))
- **telemetry:** stop reporting against a denominator a hook can't observe ([c925263](https://github.com/nicsuzor/academicOps/commit/c9252639277985b2f4d5106e952a611760d7a6a4))
- **tests:** update aops-jr/polecat -&gt; aops/polecat import paths post-relocation ([65b1f96](https://github.com/nicsuzor/academicOps/commit/65b1f96e59dd956478fc1540f530d109c5f01d01))
- **transcripts:** reinstate secret redaction and fail the aops-ts sync closed ([1e5ef49](https://github.com/nicsuzor/academicOps/commit/1e5ef491b3f32420fdc55cc6351d09f6225062c1))
- **transcripts:** reinstate secret redaction, fail aops-ts sync closed ([48ed4f2](https://github.com/nicsuzor/academicOps/commit/48ed4f26e6de13376774bbafcb95e9138721afae))
- **v0.5:** repoint core hooks to shipped files, dedupe PostToolUse, fix topology spec, add INSTALL.md ([82b1b34](https://github.com/nicsuzor/academicOps/commit/82b1b34ad54197d4c3c2913593cf05ba2f6f05c0))
- **workflows:** investigation composed an empty review set and halted brief ([bb23d55](https://github.com/nicsuzor/academicOps/commit/bb23d5520db6bc74dd914628fdbea83fcab59d45))

### Performance Improvements

- **docker:** order polecat image layers by invalidation frequency ([6e13894](https://github.com/nicsuzor/academicOps/commit/6e138940589bb18f85f8554c0a9d0726183f51ca))

### Code Refactoring

- **diagram:** drop the v1 libraries ([b4ccbd8](https://github.com/nicsuzor/academicOps/commit/b4ccbd890d1d74751a829e0db060be9db9886f4c))
- **gates:** establish single canonical source for gate primitives and strip build artifacts from plugins ([6243c4a](https://github.com/nicsuzor/academicOps/commit/6243c4ad52789ef713e8caa466069ab07def199b))
- **ida:** plan becomes strategize and moves to ida ([08215b8](https://github.com/nicsuzor/academicOps/commit/08215b85fc100c907b6094b63d620e8fad6c9d42))
- **instructions:** decouple brief's review gate and dispatch's own rules ([59301f8](https://github.com/nicsuzor/academicOps/commit/59301f831f4a16bc6f8ff5ee4884a136f4b0c373))
- **instructions:** fold situate into brief, cut library cookbooks ([ced61e0](https://github.com/nicsuzor/academicOps/commit/ced61e026b631b719acbca7b1b2c62a108ec276a))
- **instructions:** v0.7 instruction–design alignment audit ([d4aae7f](https://github.com/nicsuzor/academicOps/commit/d4aae7f61c8d6bf4608c3acbd7986adf75826620))
- **instructions:** v0.7 instruction–design alignment audit (−6,908 lines, −38%) ([b60072b](https://github.com/nicsuzor/academicOps/commit/b60072b3754698130b8070da3258f3a314e95cc8))
- Migrate doctrine to axioms and remove includes from agents ([e3b3666](https://github.com/nicsuzor/academicOps/commit/e3b3666241e572261eae50b5aaf28d64c15b848f))
- **pkb:** merge workflow into brief; brief composes and stops ([98359b9](https://github.com/nicsuzor/academicOps/commit/98359b91d05d27c13699f14a1d71539d73e2e0fc))
- **polecat:** drift cleanup — no dispatch exceptions, no settings-mirror tests ([ad922dc](https://github.com/nicsuzor/academicOps/commit/ad922dc41d673ffaaf651a4d255790cd54614168))
- reorganise into a shared core with six plugins ([32695d9](https://github.com/nicsuzor/academicOps/commit/32695d9eff822ddfa31b04dc20d2ec01e1d0d17d))
- v0.6 reorganise into a shared core with six plugins ([f3f44bf](https://github.com/nicsuzor/academicOps/commit/f3f44bfd0e4b5b97e0c01a47f6d8445bb49b94a5))

### Documentation

- **debug:** document double-dash flag separation and response assertions in debug skill ([f0b2748](https://github.com/nicsuzor/academicOps/commit/f0b2748439e101e8d0f9156636045a81bba8c85a))
- **debug:** require verifying model response string in section 3 ([6277788](https://github.com/nicsuzor/academicOps/commit/627778861fa5b4d810f357fd188efb601a847f5f))
- **doctrine:** named-teammate spawns cannot carry a return contract ([2855822](https://github.com/nicsuzor/academicOps/commit/2855822e668d16f576969fedc8f96390f3b6f68d))
- **enforcement:** update enforcement.md currency for reflexes-cope advisory evaluator (epic_612a4efb, epic_c01c4dca) ([dcb29c7](https://github.com/nicsuzor/academicOps/commit/dcb29c71c13b04ec02fde081f67a70171db2d6ed))
- **packaging:** resolve doctrine-source deferral in v0.5 topology spec ([1364edf](https://github.com/nicsuzor/academicOps/commit/1364edff4a72f2508cb99c18e2d2ee25f5a7ce37))
- plugin-rename drift, rbg stop-gate contradiction, dangling refs ([9bc918e](https://github.com/nicsuzor/academicOps/commit/9bc918e4aa89005f9cd16ebac63ae2c9b26431fe))
- **polecat:** document POLECAT_AGENT_HOME in the agy dev-loop ([6463d05](https://github.com/nicsuzor/academicOps/commit/6463d05281bcba51a2715566e6543d38f6e914af))
- **polecat:** document seed-delivery verification guard ([6235dfc](https://github.com/nicsuzor/academicOps/commit/6235dfc140b7b0427abf6ea0edb0f5a8167c07b5))
- **polecat:** document seed-delivery verification guard ([93df470](https://github.com/nicsuzor/academicOps/commit/93df470a528540f7fc33877367841124d0685ba8))
- **polecat:** fix agy transcript path in tmux-interactive-driving spec ([c4788cf](https://github.com/nicsuzor/academicOps/commit/c4788cf9bffd11e338934f8b0444f90ad39cbfd7))
- **readme:** repoint stale aops-jr/polecat + aops-pkb/agents paths to v0.5 layout ([475869e](https://github.com/nicsuzor/academicOps/commit/475869e34a7b48e1004c4d17bd36f411f124f2ba))
- repoint references that moved, remove those with no successor ([1142b0a](https://github.com/nicsuzor/academicOps/commit/1142b0ad8c5c37ec2d09c2ef2b3d8ca6ddcb27ae))
- **skills:** field-test — end-to-end validation guide as goals and checks ([370e25c](https://github.com/nicsuzor/academicOps/commit/370e25c6f305a5f9b636f6ecd4c7745433e2747d))
- **skills:** field-test §11 — publish grades on the wired map ([3dffc3c](https://github.com/nicsuzor/academicOps/commit/3dffc3c3e24b3ea4c80c911382840e35bfd3ce77))
- **specs:** add v0.5 modular topology + gate disposition spec ([fb42f21](https://github.com/nicsuzor/academicOps/commit/fb42f21e7d119563ec4d33eda07c3a2773a7b34e))
- **specs:** apply strategic-review findings to v0.5 topology spec ([77cdeeb](https://github.com/nicsuzor/academicOps/commit/77cdeeb20507ad7a28c8478a839a00272f052dc1))
- **specs:** correct stale findings in v0.5 topology spec ([d047c12](https://github.com/nicsuzor/academicOps/commit/d047c129e201137e00a399e742d6f52c97a0189c))
- **specs:** correct stale findings in v0.5 topology spec ([154fd63](https://github.com/nicsuzor/academicOps/commit/154fd6375a51c5450eb5cf6b033594430325d811))
- **specs:** dist size is not a constraint ([115000d](https://github.com/nicsuzor/academicOps/commit/115000dc86291458764c4e36e00b3144b0240eeb))
- **specs:** fold plugin README pointer into the layout paragraph ([a8524ae](https://github.com/nicsuzor/academicOps/commit/a8524ae855a2dc472e72a2f550b53dbc9b764ac7))
- **specs:** govern plugin READMEs from the doc taxonomy ([67f86e2](https://github.com/nicsuzor/academicOps/commit/67f86e29710f26337b670e5abd77cb985f3820f3))
- **specs:** govern plugin READMEs from the doc taxonomy ([c4210c4](https://github.com/nicsuzor/academicOps/commit/c4210c49159b8ddd08358ae6e72319b6f7bb4196))
- **specs:** v0.5 modular topology + gate-disposition spec ([48d04de](https://github.com/nicsuzor/academicOps/commit/48d04def34d947c598a619bf6d6aa0f773612182))
- update ida's quiet gate docs to warn-shaped, not blocking ([9ae663e](https://github.com/nicsuzor/academicOps/commit/9ae663e694bdb7247e059036045db44a460eb836))
- **v0.4:** reconcile hook/enforcement specs with shipped code ([103de19](https://github.com/nicsuzor/academicOps/commit/103de19c32ae721fada35fb25bda6f625266c6ad))
- **v0.4:** reconcile hook/enforcement specs with shipped code ([6ad4580](https://github.com/nicsuzor/academicOps/commit/6ad458098bdcf66e372dab69fa068655cc136e44))
- **v0.4:** redirect deleted ENFORCEMENT-MAP.md references to enforcement.md ([1857fb8](https://github.com/nicsuzor/academicOps/commit/1857fb812cb9accdda40651ef505afaa72a02fde))
- worker proves, dispatcher bounces ([067a01f](https://github.com/nicsuzor/academicOps/commit/067a01f0a73c65aabf09fe6757b330bd8499d747))

### CI/CD

- build dist before pytest so shipped-artifact tests actually run ([c433d70](https://github.com/nicsuzor/academicOps/commit/c433d70ff9dc2092a6c7379713029a5c2b950346))

### Build System

- **agy:** reconcile the reapplied pkb MCP fix with the shipped-config sweep ([f41e191](https://github.com/nicsuzor/academicOps/commit/f41e191634defd7496e35042801f951f161c10fd))

### Tests

- restore ida Stop-gate message-fidelity coverage, warn-shaped ([00934dd](https://github.com/nicsuzor/academicOps/commit/00934dd03cb7145b941f2762a7cdd69dcbc6cc08))
- restore suite to green after the lib/hooks consolidation ([35bd591](https://github.com/nicsuzor/academicOps/commit/35bd591307d391089457592bb192b96f98b01ea3))
- skip manifest checks on an unbuilt tree instead of erroring at collection ([9330369](https://github.com/nicsuzor/academicOps/commit/9330369019fd1691e137a9b6367cb28fa83ace6d))
- skip manifest checks on an unbuilt tree instead of erroring at collection ([798a79a](https://github.com/nicsuzor/academicOps/commit/798a79a7cec2054f9a183975725fe7a0987886e5))

### Miscellaneous

- **agents:** strip dangling Curia reference from qa.agent.md ([14582da](https://github.com/nicsuzor/academicOps/commit/14582da3289a20b410465a12f6b54d64d2bf908a))
- **instructions:** revise all agent & skill instruction files to prompting best practices ([b7f3c6e](https://github.com/nicsuzor/academicOps/commit/b7f3c6e0ab7a55ae4ecfb4f6d700c06339eb53e7))

## [0.3.80](https://github.com/nicsuzor/academicOps/compare/v0.3.79...v0.3.80) (2026-07-21)

### Features

- add install-cowork-windows target, fix empty-username silent skip ([#2265](https://github.com/nicsuzor/academicOps/issues/2265)) ([7b38529](https://github.com/nicsuzor/academicOps/commit/7b385298a53e23d85eb0c35920bb69727ca878aa))
- **agents:** add add-rule skill; wire CLAUDE.md into .agents/CORE.md ([ddb0cb7](https://github.com/nicsuzor/academicOps/commit/ddb0cb7ed662757f067ded758f50903e95971e39))
- **agents:** add agent-side capability & constraint map ([#2298](https://github.com/nicsuzor/academicOps/issues/2298)) ([3e59596](https://github.com/nicsuzor/academicOps/commit/3e59596acca6a5cc94df04bec04105c7c2199502))
- **aops-jr:** extract polecat CLI and dispatch skill into standalone coordinator plugin ([44aef03](https://github.com/nicsuzor/academicOps/commit/44aef037195f05b0d092e549a5bd82f4633a050f))
- **aops-jr:** wire into build/marketplace pipeline; record debug + packaging decisions ([#2272](https://github.com/nicsuzor/academicOps/issues/2272)) ([0c31d08](https://github.com/nicsuzor/academicOps/commit/0c31d088835d16db50d784f22188659da82e6ced))
- **aops:** add aops:debug skill for interactive polecat debugging ([44c5e0d](https://github.com/nicsuzor/academicOps/commit/44c5e0d4de763b041641b336de86ec8445ed4bb8))
- **daily:** reconceive daily note within consolidated cognitive-prosthesis layer ([d56c211](https://github.com/nicsuzor/academicOps/commit/d56c2115f7d16a76aef4ad29cbc7b3ca68f1302b))
- **daily:** reconceive daily note within consolidated cognitive-prosthesis layer (supersedes [#2293](https://github.com/nicsuzor/academicOps/issues/2293)) ([05795ad](https://github.com/nicsuzor/academicOps/commit/05795ad396100531600962711548e378eab5642b))
- **hooks:** minimal function-per-gate hook/gate system ([#2248](https://github.com/nicsuzor/academicOps/issues/2248)) ([2828481](https://github.com/nicsuzor/academicOps/commit/2828481680eae5e4e346d16a70750bde7b934aa6))
- **polecat:** forward options/prompts through to inner agent, default --task to /pull ([65cc921](https://github.com/nicsuzor/academicOps/commit/65cc921e3bd26ef8b0fcffde43d821b5a5ecff0e))
- **transcripts:** Claude adapter wrapping claude-code-log + tolerant loader + contract/snapshot tests ([0babfce](https://github.com/nicsuzor/academicOps/commit/0babfce975a4ce7f918bc8e952909a2c5f9218fe))
- **transcripts:** implement Layer B domain modules, runner, cron script, and specs ([c5e6097](https://github.com/nicsuzor/academicOps/commit/c5e60974764112b7bfdf18be27c8ce2f75eba3c2))
- **transcripts:** implement Layer B domain modules, runner, cron script, and specs ([d53a76f](https://github.com/nicsuzor/academicOps/commit/d53a76f16be32abc0dd6644aea3bbf77ccdfb433))
- **transcripts:** implement normalized model and agy adapter behind uniform interface ([#2267](https://github.com/nicsuzor/academicOps/issues/2267)) ([ae1144e](https://github.com/nicsuzor/academicOps/commit/ae1144e6d7bd3779c1b166b2e7ea2d5e6ef957bd))
- **workflows:** format Markdown files and clean whitespace ([5fc3189](https://github.com/nicsuzor/academicOps/commit/5fc31898fb2301421178e7827cb67fb0d304c6f2))
- **workflows:** implement PKB workflow-template discovery/loading for pauli decompose ([21f6031](https://github.com/nicsuzor/academicOps/commit/21f6031a0a1c4adff5571843d0ec61d4a1a6f0f0))
- **workflows:** implement PKB workflow-template discovery/loading for pauli decompose ([6e9e2ce](https://github.com/nicsuzor/academicOps/commit/6e9e2cee7d74cea16436113ce3b683bdd83ba989))

### Bug Fixes

- **agents:** use canonical double-underscore MCP tool glob names ([#2247](https://github.com/nicsuzor/academicOps/issues/2247)) ([cb351ec](https://github.com/nicsuzor/academicOps/commit/cb351ec0e7cd6b5c6cc296093e57f596896946f6))
- **aops-jr:** fail fast on unrecognized leading flags in `polecat run` ([88a6cf9](https://github.com/nicsuzor/academicOps/commit/88a6cf9a059a16903d262a9795abab557b39e676))
- **aops-jr:** fail fast on unrecognized leading flags in polecat run ([290bdc8](https://github.com/nicsuzor/academicOps/commit/290bdc8f9165fece2ea5c88cca6edb952199c722))
- **aops-jr:** repoint test + doc refs to relocated polecat under aops-jr ([#2271](https://github.com/nicsuzor/academicOps/issues/2271)) ([f285372](https://github.com/nicsuzor/academicOps/commit/f28537205c4c3e37910a134259a0c0766cfe5f77))
- **aops-jr:** resolve installed-plugin root at runtime, not $AOPS repo path ([#2274](https://github.com/nicsuzor/academicOps/issues/2274)) ([faf98c4](https://github.com/nicsuzor/academicOps/commit/faf98c4fbf6a07075d807050f09e6ed9293af4e6))
- **build:** drop redundant autoMode manifest key to clear validate warning ([97facd7](https://github.com/nicsuzor/academicOps/commit/97facd7b8b5ec7a1bf873657ff73f3a49d834933))
- **dispatch:** mandate skill-mediated dispatch + sibling-task PR bundling ([a7637fb](https://github.com/nicsuzor/academicOps/commit/a7637fb1665df9d77b05e1cb34e40be77d349a93))
- **dispatch:** mandate skill-mediated dispatch + sibling-task PR bundling ([795ede6](https://github.com/nicsuzor/academicOps/commit/795ede6de0dc496dea20c42b1afd32f06874e0ec))
- **docs:** repoint 7 unambiguous stale aops refs ([20bab0e](https://github.com/nicsuzor/academicOps/commit/20bab0e818234aadca4c4e442251fe7788119841))
- **hooks:** rephrase SubagentStop honesty reminder as re-output, not self-audit ([d1d50a3](https://github.com/nicsuzor/academicOps/commit/d1d50a3fda7ab1dd68c3c42bf9ae3912011c980c))
- **launchd:** remove hardcoded machine paths from envvars plist ([#2254](https://github.com/nicsuzor/academicOps/issues/2254)) ([598afdb](https://github.com/nicsuzor/academicOps/commit/598afdb6de398275cfcc17b854fe61be35b0cfcc))
- **macos:** restore launchd gh-auth injection + session-scoped SSH isolation ([#2251](https://github.com/nicsuzor/academicOps/issues/2251)) ([7bea600](https://github.com/nicsuzor/academicOps/commit/7bea600aff4173cf502a84deab2081a3e04d377f))
- **pkb:** finish dead PKB-prefix sweep on operational surfaces ([f5e01a5](https://github.com/nicsuzor/academicOps/commit/f5e01a511e073cb96c6350fca29b8f74e7ab5c94))
- **pkb:** reconcile stale PKB MCP tool names to live services namespace ([4473f2c](https://github.com/nicsuzor/academicOps/commit/4473f2c8cc8e75ae7b9bf8978dada9ebcb6b925f))
- **polecat:** agy dispatch exits via --print instead of idling on --prompt-interactive ([ada9a2f](https://github.com/nicsuzor/academicOps/commit/ada9a2f2cdca2befddf83a6ca3aac8fc857ff076))
- **polecat:** cli_lite.py never requests -it without a real TTY ([fef8259](https://github.com/nicsuzor/academicOps/commit/fef8259749874ed795e8e050803b42fc21387400))
- **polecat:** make agy -t task-seed failures observable and fail-fast ([f27546b](https://github.com/nicsuzor/academicOps/commit/f27546b998bd255dfa7d730355824333d1d3765d))
- **polecat:** make agy `-t` task-seed failures observable and fail-fast ([d6c6abd](https://github.com/nicsuzor/academicOps/commit/d6c6abd0761b6d48512881e2a15a9ca456e18eee))
- **polecat:** never let local dispatch pull a stale/registry image; version-stamp SessionStart ([#2246](https://github.com/nicsuzor/academicOps/issues/2246)) ([6c298d6](https://github.com/nicsuzor/academicOps/commit/6c298d692e6e7bdfbac01f25c14465960cb78d73))
- **polecat:** put --print-timeout before --print in agy headless dispatch ([75563e6](https://github.com/nicsuzor/academicOps/commit/75563e6124a167720d1c9ac68783711011db47f0))
- **polecat:** reapply lost agy dispatch fix — prompt-interactive, log-file, mount pre-creation ([43be417](https://github.com/nicsuzor/academicOps/commit/43be417cf5816b85bf279cbe91cfb849a785039e))
- **polecat:** regenerate minimal ~/.gemini/settings.json instead of copying host verbatim ([6c056cd](https://github.com/nicsuzor/academicOps/commit/6c056cd4cd902f0079b5ba9dfcd041ffe01b9b51))
- **polecat:** rename cli_lite.py to cli.py, fix stale crew/nuke doc refs ([732b881](https://github.com/nicsuzor/academicOps/commit/732b881fc6d9b24bef55a641aedad6bf3bd5ea68))
- **polecat:** reorder --print-timeout before --print in agy headless dispatch ([049f26e](https://github.com/nicsuzor/academicOps/commit/049f26eb1f01cbe56d65598d6073266ff332e9bb))
- **polecat:** restore plugin activation and PKB MCP config in polecat images ([#2249](https://github.com/nicsuzor/academicOps/issues/2249)) ([9fefc43](https://github.com/nicsuzor/academicOps/commit/9fefc4302b77b1ac3eb1f101ff98d99f78781cb6))
- **polecat:** stop leaking host Gemini/Antigravity credentials into containers ([7469d75](https://github.com/nicsuzor/academicOps/commit/7469d756d9028acf77dd277b47cd5503b9a35b5a))
- remove Docker socket access by default, add opt-in mechanism (aops_624a462e, aops_e3b194fb) ([2ed7304](https://github.com/nicsuzor/academicOps/commit/2ed73047a3289e2c7ba34f82435d66f76c2ae3b6))
- **specs:** strip dated debug narration from specs, cite doc-taxonomy ([#2242](https://github.com/nicsuzor/academicOps/issues/2242)) ([862d023](https://github.com/nicsuzor/academicOps/commit/862d02351e218660a1591f331c35b84ec9a95845))
- **transcripts:** surface tool results, solve truncation, and add cost fields ([#2297](https://github.com/nicsuzor/academicOps/issues/2297)) ([fb9bd53](https://github.com/nicsuzor/academicOps/commit/fb9bd53427f7b5158598289eb30b1014d612fd3b))
- update build workflow ([65eeaaa](https://github.com/nicsuzor/academicOps/commit/65eeaaad3dd1605d51d6eda575443c6b3a487659))

### Documentation

- create skill capability and constraint map ([#2296](https://github.com/nicsuzor/academicOps/issues/2296)) ([6f2972b](https://github.com/nicsuzor/academicOps/commit/6f2972bd04afddf0ab847429bae68d895b6c72d6))
- **flow-map:** add specs/FLOW-MAP.md — component/trigger SSoT + README link ([#2268](https://github.com/nicsuzor/academicOps/issues/2268)) ([f7b4bfc](https://github.com/nicsuzor/academicOps/commit/f7b4bfc62df399917e84ba46b2a1b2181fca08fd))
- merge aops/README into root README, correct stale architecture claims ([9edb1e6](https://github.com/nicsuzor/academicOps/commit/9edb1e614be7763a6c9c0c7b46b71e11d5288878))
- **polecat:** fix stale crew/nuke references, flag architecture gap ([b321d30](https://github.com/nicsuzor/academicOps/commit/b321d3074d3fc965fc0294abc3a5d99bf6360e8d))
- **polecat:** fold agy-debugging lessons into debug skill and specs ([64c3569](https://github.com/nicsuzor/academicOps/commit/64c35699da2d41873ef5fb6767c08f171cdccf80))
- **polecat:** move tmux-driving mechanics from README to a spec ([7265e5c](https://github.com/nicsuzor/academicOps/commit/7265e5c9f43f6270225d666d4cba88fd3ee1f1f5))
- **specs:** complete worker-contract reframe across remaining specs and skills ([49fb578](https://github.com/nicsuzor/academicOps/commit/49fb578fef5b566d6464928c7b51845e6c141c73))
- **specs:** de-emphasise review-independence per 2026-07-19 ruling ([daab20b](https://github.com/nicsuzor/academicOps/commit/daab20bd0b7fb6799c0a33c2e2a487906e131efe))
- **specs:** fold unified worker-contract reframe into FLOW-MAP + reconcile overlapping specs/skills ([67d9e17](https://github.com/nicsuzor/academicOps/commit/67d9e1721f5040562c551fbca5be826926fb1681))
- **workflows:** migrate gates to PKB templates to match v0.4 plan ([464a765](https://github.com/nicsuzor/academicOps/commit/464a765d8499afce8cf1fee1bf2e449e01c81397))
- **workflows:** Migrate workflow gates to PKB templates ([3a7e587](https://github.com/nicsuzor/academicOps/commit/3a7e5872ec50aa696336e70e71a5f8e4f7b701f6))

### Tests

- **transcripts:** land anonymized Claude and agy transcript fixtures ([2377634](https://github.com/nicsuzor/academicOps/commit/23776346bce7bdbb8672e0a066e2ad2d1e209052))
- **transcripts:** re-anonymize username and PKB ID leaks ([e706b45](https://github.com/nicsuzor/academicOps/commit/e706b45970ac98cfbff986c970d49df9c80df03b))

### Miscellaneous

- retire Gemini CLI as a supported client surface ([#2252](https://github.com/nicsuzor/academicOps/issues/2252)) ([57ca2a6](https://github.com/nicsuzor/academicOps/commit/57ca2a6f2407fb687d2b84d8c70995fb05b14af5))
- **transcripts:** drop scheduled drift workflow, rely on the pytest ([#2266](https://github.com/nicsuzor/academicOps/issues/2266)) ([5ffea69](https://github.com/nicsuzor/academicOps/commit/5ffea699a1f025abe149f72b145427ac2188fc33))
- **v0.4:** normalize services MCP rename + aops→aops consolidation ([5910671](https://github.com/nicsuzor/academicOps/commit/591067125cce0495aff682d2867a4490da26438e))

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
- **docker:** dist-only local build, drop aops/pkb/extras, fix enablement ([c84a952](https://github.com/nicsuzor/academicOps/commit/c84a95207a72f8599366163b4f1f670bb6a3b527))
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
