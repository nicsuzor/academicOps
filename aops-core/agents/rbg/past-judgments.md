# RBG past-judgments library

A small library of real mistakes that slipped past prior reviews. Each example: brief context, what a naive review missed, what the judge should ask. **These are illustrative, not exhaustive.** A motivated paraphrase that preserves the structural defect is still a violation. Pattern-match the _shape_, not the strings.

When you encounter a PR whose shape rhymes with one of these, treat it as a strong prior toward the verdict shown — then verify against the actual diff.

---

## 1. Parallel enforcement layer with no documented relationship — A8 / P#65 instinct

**Context (PR #877).** Added a third A8 enforcement point (RBG composition-time scan) on top of two existing ones. ENFORCEMENT-MAP.md gained the new rows but didn't mark the post-hoc periodic enforcer as superseded, complementary, or scoped-down.

**What naive review missed.** Each layer was individually well-formed. The defect is _between_ layers: four enforcement points with no stated relationship. VISION had warned twice that parallel A8 layers cost more than they save.

**The judge should ask.** "Does this PR add a fourth/Nth gate parallel to existing ones? If yes — does it state the relationship (supersedes / complements / parallel-and-justified)?" If no relationship is documented, REVISE.

---

## 2. Self-applying rule that exempts itself — P#65 / bootstrap gap

**Context (PR #859).** Introduced a P#65 BLOCKING rule requiring ENFORCEMENT-MAP updates whenever a gate changes. The PR itself added a composition-time gate (the new RBG rule) but did not register a row in the map for itself — the rule's own bootstrap.

**What naive review missed.** RBG didn't yet contain the rule when it reviewed the PR introducing the rule. Self-application gap: the rule's introducing PR is always a free pass.

**The judge should ask.** "Does this PR add a rule that should apply to itself? If yes — does the same PR backfill the rule's own audit row?" Missing self-application = REVISE.

---

## 3. Touchpoint list narrower than the rule it implements — P#65 instinct

**Context (PR #859 follow-up).** P#65 enumerated six touchpoint paths. The map's own taxonomy includes a fifth section sourced from `aops-core/agents/*.md` and `aops-core/skills/*/SKILL.md`. Those paths weren't in the touchpoint list. Result: the rule systematically misses the very class of changes that introduced it.

**What naive review missed.** The list reads complete. It isn't — it under-covers the map's own categories.

**The judge should ask.** "Is the rule's enumeration a strict subset of the surface it claims to govern? Compare touchpoints against the map taxonomy." Subset coverage on a BLOCKING rule = REVISE.

---

## 4. Phrase-list test that pins the example string — A8 / Goodhart

**Context (PR #877).** Tests asserted exact substrings (`test_workspace_writes_visible_on_host`, `_is_remote_daemon()`, `WSL2`) were present in prompt files. This proves typo regression is caught — not that the rule fires at runtime. The verbatim worked example becomes a fixed point: future maintainers can't generalise without breaking tests.

**What naive review missed.** "Tests pass" looked like coverage. The tests were tautological — string-presence checks between two strings, no agent invoked. Same class of test-without-runtime-verification A8 forbids.

**The judge should ask.** "Does this test exercise the rule, or does it just assert the rule's source text is present? Is the example pinned by string, blocking future generalisation?" Tautological test = REVISE with "add LLM-in-the-loop replay against the documented historic transcript".

---

## 5. Composition-time vs post-hoc enforcement framing — A8 instinct

**Context (issues #720 / #821).** General-agent emitted a workaround menu after MCP crash; supervisor decomposition emitted "drift candidate" framing. Periodic post-hoc enforcers fired _after_ the workaround had already reached the user.

**What naive review missed.** The post-hoc check existed and "covered" the case in the test sense. The defect is timing: by the time post-hoc fires, the user has already seen the menu.

**The judge should ask.** "Is enforcement at the right phase? Composition-time vs post-hoc is not a stylistic choice — it determines whether the workaround reaches the user." Post-hoc-only coverage on a user-facing surface = BLOCK.

---

## 6. Criterion substitution — diff is _about_ the change, not the change

**Context (PR #610, #621).** PR title claimed a behaviour/config fix; diff contained only `*.md` describing how the change _should_ look. Reviewer approved because the description was thorough.

**What naive review missed.** Documentation about a fix is not a fix. The artifact landed at a path that does not take effect.

**The judge should ask.** "Does the diff _contain_ the change the title claims, or only artifacts _about_ it?" Mismatch = BLOCK with one-line redirect to the path that actually takes effect. Carve-out: doc-only PRs whose title says "document X" are fine.

---

## 7. Scope error — fix lives in a different repo

**Context (issue #789).** PR claimed to fix behaviour X; X was implemented in a different repo / user-global config (`~/.config/...`, `~/.claude/...`). The diff edited a checked-in template that has no effect.

**What naive review missed.** Reading the diff in isolation looked fine. The defect is locality: the edited file is not on the path that runs.

**The judge should ask.** "Where does this artifact actually take effect? Is the diff editing the live path or a template/example?" Wrong-repo / wrong-surface = BLOCK with redirect.

---

## 8. Threshold mismatch — loud-and-wrong UX

**Context (PR #295).** Set a 60-second alert threshold against a 5-minute cron interval. Always loud, never right.

**What naive review missed.** The threshold was internally consistent and well-tested. Defect emerges only when you reason about the interval it observes.

**The judge should ask.** "Are the thresholds in this PR coherent with the cadence of the thing they observe? Will this alert be loud-and-wrong by construction?"

---

## 9. Repeating yesterday's lesson — placement violation

**Context (PR #293).** Added validation in a handler instead of the SSoT — the exact lesson PR #288 had taught one day earlier.

**What naive review missed.** Each PR seen alone looks reasonable. The defect is institutional memory: the framework just learned this; learning it again is a regress.

**The judge should ask.** "Has this surface been corrected recently for the same reason? Search PKB / recent merged PRs for the same placement decision." Same-week regress = REVISE with cite.

---

## 10. Overfit tooling for a one-off — strategic alignment

**Context (PR #866).** Added a permanent P# allocator to handle a single observed scenario. Permanent generality for a one-off case.

**What naive review missed.** The tool worked. Defect is proportionality: durable infrastructure for ephemeral need.

**The judge should ask.** "Is the durability of this artifact proportional to the durability of the need? Would Pauli ship permanent tooling for this?" Disproportionate = REVISE.

---

## 11. Sensitive data committed to public repo

**Context (recurring class).** Tailscale `*.ts.net` hostnames, RFC1918 IPs, internal `*.lan` / `*.nicwin` hostnames committed to durable surfaces (production code, configs, workflows, ships-with-the-repo docs).

**The judge should ask.** "Where in the repo does this match appear? Production/config/workflow surface = BLOCK; test fixture or `*.example` with illustrative comment = WARN; diff is _removing_ the match = PASS." Carve-out: `.agents/CAPABILITIES.md`-style env-orientation docs default to WARN.

---

## 12. Unverified keystone — load-bearing claim with no evidence

**Context (GH #624).** PR's fix depended on a structural claim ("tool X routes through hook Y", "Gemini Policy Engine `allow` overrides `--approval-mode plan`"). No test, no spec cite, no runtime trace.

**What naive review missed.** The claim was plausible. Plausible is not verified.

**The judge should ask.** "What technical claim does this fix depend on? Is there a test, runtime trace, or cited spec? If not, does the PR body explicitly disclose the claim is unverified, with a follow-up task?" Undisclosed unverified keystone = REVISE.
