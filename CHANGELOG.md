# Changelog

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
