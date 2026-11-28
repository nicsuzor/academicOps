# Premise-Check Critique Guide

Worked exemplars, defect patterns with 3-way remand cures, edge-case rulings, and appealable verdict reason templates for `ida:premise-check`.

## Defect Taxonomy (Plain-English Classes)

**Materiality & amendment rule:** Every remand cure below (outside non-waivable authority or standing-rule breaches requiring sender rework) applies only when curing the defect could change what is relayed or done next and cannot be fixed without ambiguity on the record. Where every defect is clearly fixable without ambiguity from the record, accept with `AMENDED` and correct the claim directly rather than remanding. Immaterial slips receive `PASS` with a brief non-blocking note omitted from upward relays.

| Defect Class | What It Looks Like on the Record | Minimal Remand Cure |
| - | - | - |
| **Premise Smuggling** | Load-bearing premise packs independent assertions into one sentence, hides an unsourced claim in a clause/parenthetical/appositive or omnibus relay (`"The same checked report found X and Y"`), or makes a first-person tool claim (`"I read..."`, `"I ran..."`, `"I checked..."`) lacking a locator/output when stakes warrant one. (Identifying an already-verified `verdict-...` without new unverified claims passes.) | `REVISE`: split each load-bearing assertion into its own numbered premise with inline basis (or mark assumed / gather primary evidence). |
| **Non-Argdown Prose** | Material non-Argdown prose outside blocks (framing, parallel summary, loose bullets, plain reply) obscures grounds or warrants. (Readable internal scaffolding -- bulleted `(n)` lines, bold handles, step pointers -- passes unless support is ambiguous.) | `REVISE`: rewrite strictly as unfenced prose Argdown blocks. |
| **Missing Bridge** | Conclusion introduces a claim no premise supplies, skips a layer, or drops `-- ... --`. | `REVISE`: add missing bridge premise or inference bar. |
| **Circular Warrant** | Bar merely restates a premise ("because it passed, it passes") with no independent rule. | `REVISE`: state a licensing rule that could fail independently. |
| **Quantifier / Scope Drift** | Narrow sample or single case supports an unqualified universal ("all", "only", "never") outrunning the applicable standard. | `REVISE`: narrow qualifier to premises/standard, or run a bounded search. |
| **Construct / Proxy Drift** | Premises observe a proxy (liveness, log count) while claiming a substantive construct (customer impact, completeness); or silently swap a specified medium/method. | `REVISE`/`FAIL`: restore medium/method, bridge proxy to construct, or narrow claim. |
| **Domain-Mismatched Authority** | Warrant cites a rule or policy for a different domain or regime without bridging the gap. | `REVISE`: cite governing authority or narrow recommendation. |
| **Unruled Rival** | A simpler or equally plausible world state yields the same quoted evidence (burst, version skew, `"their call"` deferral). | `REVISE`: rule out the rival from primary evidence or qualify conclusion. |
| **Observation-Surface Overreach** | Claim exceeds what the inspection can observe (e.g., live runtime behavior from static file reads). | `REVISE`: qualify to static inspection, or run live check. |
| **Secondary Summary Substitution** | On a stakes-bearing live-state conclusion where direct inspection could change next action, originator cites a task status, PKB note, or peer prose instead of primary source. (Qualified summaries pass on low-stakes read-only sweeps.) | `REVISE`: remand for primary observation with inline quote and locator. |
| **Stakes Laundering** | High-stakes, irreversible, or primary-decision conclusion is disguised as `"low-stakes"` or `"obvious"` (or cites engine output as authority) without showing why that standard fits. (Light scrutiny on genuinely low-stakes, read-only, or cheaply redone work complies.) | `REVISE`: justify standard fit, narrow conclusion, or gather primary evidence. |
| **Facial Contradiction** | Incompatible assertions on the face of the message (conflicting counts/states, claiming work premises show never ran) or unexplained material contradictions across the same sender's own revisions on an unchanged claim in an active remand. | `FAIL`: cite exact contradiction on the text (optionally noting clean severable parts), strictly without outside or forensic checks. |
| **Unanswered Ask / Authority Drift** | Drops a material part of the upfront ask or acts beyond delegated scope (_ultra vires_). | `REVISE` (dropped ask) or `FAIL` (_ultra vires_): non-waivable. |
| **Non-Waivable Rule Breach** | Delivered work leaves a standing axiom or project rule breach in place without a higher rule or direct user waiver. | `REVISE`/`FAIL`: non-waivable; require compliant fix (disclosing out-of-scope breaches complies). |
| **Bare Relay Stub** | Coordinator reports only `"subagent passed verdict-X"` without relaying premises, sources, qualifiers, or rule breaches. | `REVISE`: relay each checked finding in its own premise with verdict ID, primary locator, and qualifiers. |

## Edge-Case Rulings & Proportionality Standards

- **Proportional effort & materiality**: Scale checking depth, evidentiary detail, and verdict reasons to stakes (doing less on low-stakes, read-only, or cheaply redone work). Immaterial slips receive `PASS` with a brief non-blocking note omitted from relays.
- **Unambiguous deterministic amendment (`AMENDED`)**: Where every defect is clearly fixable without ambiguity from what is already on the message (such as narrowing an overstated qualifier or scoping a claim to the subset already established in its own premises), accept with `AMENDED`, amend the claim directly so it is fully accurate, record the original defect and resulting amended claim in the reason, and relay the amended claim without remanding to the sender. Never invent facts or check outside sources to amend (closed-record bounds still hold); reserve `REVISE` for missing evidence, unruled rivals, or non-deterministic defects requiring sender judgment.
- **Severability & partial relay**: Because `verdict.py` records one token per claim, sever multi-part messages explicitly: dropping an unneeded weak part gets `PASS` naming strictly the supported relayable subset; remanding or rejecting a materially defective part gets `REVISE`/`FAIL`, optionally naming clean independent parts with scope bounds (preventing rework on remand and allowing those independently verified parts to relay separately, while never relaying failed or remanded claims).
- **Closed record & suspected invention**: The record is the message under review and nothing outside it. Never rely on, consult, or test against anything outside the message (in-context state, prior unrelated turns, harness state/telemetry, tool logs, external sources, or other agents) to verify truth, confirm execution, or authenticate values, and never escalate receipt precision as an anti-fabrication proxy at any stakes level. Separately verify ask coverage against the originating ask and catch unexplained material contradictions across the same sender's own successive submissions on an unchanged claim in an active remand. Without a material facial defect, `PASS` on the message alone without commissioning ad-hoc fact-checkers (deliverable QA and `/learn` sit outside `premise-check`).
- **Relaying senders pass remands down**: When a relaying sender receives an evidentiary `REVISE` or `FAIL`, it passes the remand down to the originating agent (or routes per the composed workflow if the sender exited or is discredited by facial contradiction) rather than opening primary sources itself.
- **Standard of proof in all the circumstances**: Setting the standard of proof is always the principal's choice. Where unset, the writer applies (and justifies where non-obvious) a standard reasonable and appropriate in all the circumstances, and the checker judges whether the conclusion is supported without demanding certainty where none exists. Unjustified hand-waves (`"obvious"`, engine output as authority) fail on contested, non-obvious, or stakes-bearing conclusions; routine or obvious warrants pass without ceremony on low-stakes steps.
- **Legitimate discretion & layout neutrality**: Judgment within remit that is not clearly wrong passes under administrative-law judicial review. Never substitute phrasing/design preferences or remand over Argdown layout, numbering, or scaffolding unless support relations are ambiguous.
- **Authorized pauses & partial handovers**: At a principal-requested pause, handover, or user-reserved choice, open-question premises qualifying settled conclusions satisfy ask coverage without violating `exercise-authority`.
- **Premature, duplicate, & superseded handbacks**: Subagents await child runs and report once at their stopping point unless async tracking was requested; premature `"still running"` reports get `REVISE`. Once settled, never query the sender about refused transports; if a duplicate/superseded packet arms the gate, inspect its actual lines (never pasting prior reasons) and record a concise verdict relaying zero new claims beyond the settled `verdict-<id>`.
- **Deliverable form & method fidelity**: When `## Ask` or user turns specify a method, form, design, value, or medium noun (canvas, diagram, map, code, spec), check departures on the face of the message against the ask. Construct-preserving rewording passes; silent material swaps fail.
- **Strike baseless run-will-settle doubts**: Unexplained worries about whether a route or tool will work (`"haven't checked whether X works"`) with no stated failure reason are speculation -- judge valid as if absent; never remand for a probe or relay as risk.
- **Never strike admitted unchecked facts readable now**: Admitting a readable load-bearing fact is unchecked (`"haven't checked if PR merged"`, `"assumed"`) marks a weak premise, not speculation. Fail material live-state claims whose cure could change user action; sever or omit immaterial unchecked asides.
- **Exited-worker presentation rewrite**: If an exited worker leaves a complete primary record with rough presentation only, the receiver may restate it cleanly from that evidence; gaps or dropped asks route per the composed workflow.
- **Unreachability by construction**: When an ask was unfulfillable at the reporter's stopping point and quoted facts validly prove unreachability, treat the ask as answered.

## Worked Exemplar: Multi-Layer Diagnostic & Recommendation

Each load-bearing observation sits in its own numbered premise with an exact locator, cross-block references cite the establishing block, zero facts sit in bars, and each block passes its Contrast Test:

```markdown
**Original Ask (`task-42/AC1-AC2`):** (AC1) Diagnose the p95 latency jump in the notification worker after deploy `c81f4a2`; (AC2) recommend the lowest-risk fix.

**Main Conclusion:** The p95 spike (`420 ms` -> `4,850 ms`) is isolated to HTTP 429 retries caused by raising `worker_concurrency` (`4` -> `16`) and replacing jittered exponential backoff with fixed `0.5s` retries in `worker/pool.py:34-48` (subject to unobservable sub-minute partner burst limits). Reverting to `worker_concurrency = 4` and jittered backoff is the lowest-risk fix, pending staging load confirmation.

### Latency Pattern Isolation

(1) Production traces for `2026-10-12 00:00-06:00 UTC` (`n = 1,420`, commit `c81f4a2`) show p95 latency rose to `4,850 ms` from `420 ms` on baseline `2026-10-11` (`n = 1,388`, commit `9d0e11b`).
(2) Across both windows (`c81f4a2` vs. `9d0e11b`), median latency stayed flat (`190 ms` vs. `185 ms`).
(3) On `2026-10-12`, 100% of spans exceeding `1,500 ms` (`n = 89`) hit `status = 429` before retrying; non-429 spans (`n = 1,331`) held p95 at `210 ms`.
(4) Partner headers logged `X-RateLimit-Limit: 60/min` unchanged across both windows.
-- A tail jump confined to HTTP 429 spans while median and non-429 p95 stay flat under an unchanged quota isolates contention/retry behavior rather than network degradation or quota cuts. An external traffic burst could also trip the limit; tested next. --
(5) So the p95 spike at `c81f4a2` is isolated to HTTP 429 retry paths under an unchanged `60/min` partner quota.

### Root Cause Diagnosis and Rival Check

(1) From `Latency Pattern Isolation`, the p95 spike at `c81f4a2` is isolated to HTTP 429 retries under a `60/min` quota.
(2) Dispatch volume on `2026-10-12` (`1,420` jobs, peak `18/min`) matched baseline `2026-10-11` (`1,388` jobs, peak `19/min`).
(3) `git diff 9d0e11b..c81f4a2 -- worker/pool.py:34-48` changed `worker_concurrency` from `4` to `16`.
(4) The same diff (`worker/pool.py:34-48`) replaced jittered exponential backoff with fixed `0.5s` retry sleeps.
(5) Bounded search (`grep -rn "429\|retry_delay\|worker_concurrency" worker/`) found `0` other outbound dispatchers outside `worker/pool.py`.
(6) Partner API headers (`docs/partner-api.md:22`) expose only per-minute quotas and zero sub-minute burst telemetry.
-- Holding load and quota constant, quadrupling concurrency without backoff jitter creates synchronized retry storms that trip a 60/min limit. Traffic surge is ruled out by (2) and alternate dispatchers by (5); undocumented sub-minute burst throttling remains an unruled caveat from (6). --
(7) So the `worker/pool.py:34-48` concurrency and retry change (`c81f4a2`) is the primary cause of the p95 spike, qualified by unobservable sub-minute burst limits.

### Lowest-Risk Remediation

(1) From `Latency Pattern Isolation`, baseline `9d0e11b` held p95 at `420 ms` (`n = 1,388`, `2026-10-11`).
(2) From `Root Cause Diagnosis and Rival Check`, `worker/pool.py:34-48` (`c81f4a2`) drives 429 retry spikes under `18/min` peak load (vs. `19/min` on `9d0e11b`).
(3) Service SLA (`docs/worker-sla.md:14`) mandates p95 `< 500 ms`, jittered backoff on 429, and concurrency `<= 8` unless a client-side token bucket is deployed.
(4) Bounded search (`grep -rn "token_bucket\|RateLimiter" worker/`) returned `0` matches in `worker/`.
-- Reverting to baseline settings that already met the SLA (`<= 8` concurrency, `420 ms` vs. `500 ms` SLO) ends retry storms without new stateful infrastructure. A token bucket adds unnecessary rollout risk at `18/min` peak; staging load confirmation remains needed post-revert. --
(5) So revert `worker/pool.py:34-48` to `worker_concurrency = 4` and jittered backoff, then run a staging load test to verify p95 `< 500 ms`.
```

### Multi-Hop Coordinator Relay (Separate Sourced Premises, Zero Bundling)

Each relayed finding sits in its own premise citing `verdict-84a1c2e0` and its primary locator -- never bundled into an omnibus sentence:

```markdown
**Original Ask (`req-12`):** Report the notification latency spike cause and recommended fix.

**Main Conclusion:** Synchronized HTTP 429 retries from `worker/pool.py:34-48` (`c81f4a2`) caused the p95 spike (`420 ms` -> `4,850 ms`); reverting to `worker_concurrency = 4` and jittered backoff is the lowest-risk fix (pending staging verification vs. `500 ms` SLO; sub-minute burst limits unobservable).

### Relayed Diagnostic Findings

(1) Production traces (`2026-10-12`, `n = 1,420`, `verdict-84a1c2e0` PASS) isolated all `> 1,500 ms` spans (`n = 89`; p95 `4,850 ms` vs. `420 ms` baseline) to HTTP 429 retries under flat peak load (`18/min` vs. `19/min`) and `60/min` quota.
(2) `git diff 9d0e11b..c81f4a2 -- worker/pool.py:34-48` (`verdict-84a1c2e0` PASS) raised `worker_concurrency` (`4` -> `16`) and replaced jittered backoff with fixed `0.5s` retries.
(3) Bounded grep across `worker/` (`verdict-84a1c2e0` PASS) returned `0` other dispatchers or token buckets.
(4) `docs/worker-sla.md:14` (`verdict-84a1c2e0` PASS) mandates p95 `< 500 ms`, jittered backoff, and concurrency `<= 8` without a token bucket.
(5) `docs/partner-api.md:22` (`verdict-84a1c2e0` PASS) exposes only per-minute quota headers, leaving sub-minute burst throttling unobservable.
(6) `verdict-84a1c2e0` (PASS) disclosed zero rule violations.
-- Verified child claims with individual primary locators, verdict ID, and qualifiers relay upward without substantive checking outside the message when each distinct source stands separately and caveats travel intact. (1)-(6) preserve each source, zero breaches, the sub-minute caveat (5), and pending staging confirmation (4). --
(7) So revert `worker/pool.py:34-48` to `worker_concurrency = 4` and jittered backoff, then verify p95 `< 500 ms` in staging, noting the sub-minute throttle caveat.
```

## Realistic Subtle Defects & Minimal Remand Cures

1. **Premise Smuggling**: _Defective_: `(3) Checked report (verdict-3a1b9c0d) found gateway logs recording channel:beta because config/auth.env omits BETA_KEY.` (`channel:beta` is unsourced.) _Split_: `(3) config/auth.env:12 (verdict-3a1b9c0d PASS) omits BETA_KEY.` / `(4) Gateway logs record channel:beta [assumed].` _Cure (`REVISE`)_: (b) split premises and (c) quote logs for `(4)` or (a) drop/qualify it.
2. **Construct / Proxy Drift**: Quoting `0` `app.log` errors and `HTTP 200` on `/health` after a migration to claim `"zero customer impact"` confuses liveness with payment integrity. _Cure (`REVISE`)_: (a) narrow to liveness, or (c) check post-migration order counts vs. baseline.
3. **Domain-Mismatched Authority**: Citing batch-ETL tuning ("fixed 200ms retries") to remove jitter on a rate-limited third-party API client. _Cure (`REVISE`)_: (b) cite rate-limited API authority or bridge why batch rules transfer.
4. **Unbounded Exclusive Claim**: Inspecting `n = 2` `us-east` failures and claiming `"only the new serializer causes timeouts across all regions."` _Cure (`REVISE`)_: (a) narrow to those two traces, or (c) run a cross-region control.
5. **Diagnosis-to-Remedy Mismatch**: Diagnosing missing read-replica indexes while recommending larger write-primary pools without bridging the two. _Cure (`REVISE`)_: (b) align remedy to replica indexes or add the bridge.
6. **Bare Relay Stub**: Writing `"(1) Worker passed verdict-9f2a1b3c PASS. So the design is approved."` _Cure (`REVISE`)_: (b) relay each checked finding with primary locator, verdict ID, qualifiers, and disclosed breaches.

## Appealable Administrative-Law Verdict Reasons

Templates below are for the `--reason` / `--reason-file` OTel record passed to `verdict.py`; sending a verdict or remand to another agent uses unfenced prose Argdown blocks only.

### Example Low-Stakes / Read-Only PASS Reason (`--reason`)

```text
PASS on claim-3b7e20c1 (ask task-19: list hooks referencing retry_delay). Judicial review on the message alone (zero substantive checking outside it): bounded grep locator and 2 matching file:line paths answer the read-only lookup directly; zero material defects. Relayable: hooks/retry.py:14 and hooks/pool.py:88 reference retry_delay.
```

### Example High-Stakes Multi-Layer PASS Reason (`--reason-file`)

```text
PASS on claim-84a1c2e0 (asks task-42/AC1 and task-42/AC2).

Judicial review passes on the message alone (zero substantive checking outside it):
- Latency Pattern Isolation: Premises (1)-(4) quote trace windows, n=1,420 vs. n=1,388, p95/median splits, 429 isolation (89/89 > 1,500 ms), and unchanged partner quota; inference narrows the spike to 429 retries.
- Root Cause & Rival Check: Premises (1)-(6) separate diff changes (worker/pool.py:34-48), peak rates (19/min vs. 18/min), bounded grep, and per-minute header limits (docs/partner-api.md:22). Contrast Test rules out bursts and other dispatchers while qualifying sub-minute limits.
- Remediation & Compliance: Premises (1)-(4) anchor the revert in docs/worker-sla.md:14, confirm 0 token buckets, note pending staging verification, and answer AC1-AC2 with zero bundled unsourced premises or rule breaches.

Relayable checked conclusions: worker/pool.py:34-48 (c81f4a2) caused the p95 429 spike (subject to unobservable sub-minute limits); reverting to worker_concurrency=4 and jittered backoff is the lowest-risk fix, pending staging confirmation under 500 ms.
```

### Example AMENDED Reason (`--reason` / `--reason-file`)

```text
AMENDED on claim-5c2a81d0 (ask task-31/AC1: verify unit test suite status after refactor).

Accepted with deterministic amendment on the message alone (zero substantive checking outside it):
- Quantifier Drift: Conclusion states "all tests pass", whereas premise (1) quotes pytest running only tests/auth/ and tests/billing/ (48 passed).
- Amendment applied: Narrowed claim to "tests/auth/ and tests/billing/ pass (48 passed); remaining test directories unrun".
- No outside facts added; remaining grounds hold.

Relayable amended conclusion: tests/auth/ and tests/billing/ pass (48 passed); other test directories were not run in this check.
```

### Example REVISE (Remand) Reason (`--reason-file`)

```text
REVISE on claim-91d0f4a2 (ask task-55/AC1: confirm checkout migration 014 succeeded with zero customer impact).

Remanded to the originating agent on the message alone (zero substantive checking outside it):
- Construct / Proxy Drift: Premises (1)-(2) quote only 0 app.log errors and HTTP 200 on /health, proving liveness rather than checkout integrity or customer impact.
- Unruled Rival: A broken checkout write path or silent validation drop leaves /health 200 and app.log clean; nothing on the record rules this out.
- Minimal cure: Load ida:premise-check and either (a) narrow strictly to service liveness, or (c) quote primary post-migration checkout completion counts against baseline in prose Argdown blocks.

Relayable checked conclusions: none.
```
