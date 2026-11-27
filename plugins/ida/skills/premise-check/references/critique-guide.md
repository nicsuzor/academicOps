# Premise-Check Critique Guide

Worked multi-layer exemplars, realistic defect patterns with 3-way remand cures, edge-case rulings, and appealable verdict reason templates for `ida:premise-check`.

## Defect Taxonomy (Plain-English Classes)

| Defect Class | What It Looks Like on the Record | Minimal Remand Cure |
| - | - | - |
| **Premise Smuggling (Bundled / Unsourced Claim)** | A premise packs multiple assertions into one sentence, states a first-person tool observation without a source/locator, or hides an unattributed assumption inside a subordinate clause, parenthetical, appositive, or omnibus relay (`"The same checked report found X and Y"`) under a source backing only part of the sentence. | `REVISE` when load-bearing / able to change the answer: break each assertion into its own numbered premise in the prose Argdown with its own stated source/locator (or mark it assumed / gather primary evidence). If non-load-bearing and unable to change the answer, `PASS` with a non-blocking note. |
| **Non-Argdown Agent-to-Agent Prose** | An inter-agent message includes conversational framing, a parallel prose summary, loose trailing bullets, or plain-prose replies outside prose Argdown blocks. | `REVISE`: rewrite the entire agent-to-agent message strictly as unfenced prose Argdown blocks. |
| **Missing Bridge / Non-Sequitur** | Conclusion introduces a new claim no premise supplies, skips an epistemic layer, or drops the inference bar. | `REVISE`: supply the missing bridge premise or intermediate inference bar. |
| **Circular or Empty Warrant** | Inference bar merely restates a premise ("because it passed, it passes") with no independent rule. | `REVISE`: state a licensing rule that could fail independently of the premises. |
| **Quantifier & Scope Drift** | Premises cover `n=1`, one region, or "some" while the conclusion asserts "all", "only", "never", or "systematically". | `REVISE`: narrow the qualifier to the observed sample, or supply a bounded search. |
| **Construct / Proxy Drift** | Premises observe a proxy (liveness, log count, wording match) while claiming a substantive construct (customer impact, completeness); or silently swap a specified medium/method. | `REVISE` or `FAIL`: restore specified medium/method, supply an empirical bridge, or narrow claim to the proxy. |
| **Domain-Mismatched Authority** | Warrant cites a rule, benchmark, or policy written for a different domain or operating regime without bridging the difference. | `REVISE`: cite authority governing the actual operating domain or narrow the recommendation. |
| **Unruled Rival Explanation** | A simpler or equally plausible world state produces the same quoted evidence (traffic burst, version skew, regional outage, or open "their call" deferral). | `REVISE`: name the rival explanation and either rule it out from primary evidence or qualify the conclusion. |
| **Observation-Surface Overreach** | Claim reaches beyond what the reported inspection can observe (e.g., concluding live runtime behavior from static file reads alone). | `REVISE`: qualify claim to static inspection, or run the live check. |
| **Secondary Summary Substitution** | Originating agent cites a task status, PKB note, or peer prose on live state instead of quoting the primary source inline. | `REVISE`: remand for direct primary observation with inline quote and locator. |
| **Stakes Laundering** | Stakes-bearing conclusion excuses weak evidence as "low-stakes", "reversible", or "obvious", or cites engine output as authority. | `REVISE`: require primary evidence matching real stakes and user or spec authority. |
| **Unanswered Ask / Authority Drift** | Message drops part of the upfront ask or acts beyond delegated scope (_ultra vires_). | `REVISE` (dropped ask) or `FAIL` (_ultra vires_): non-waivable. |
| **Non-Waivable Rule Breach** | Delivered work leaves a standing axiom or project rule breach in place without a higher rule or direct user waiver. | `REVISE` or `FAIL`: non-waivable; require compliant fix (disclosing an out-of-scope breach is compliant escalation). |
| **Bare Relay Stub** | Coordinator reports only `"subagent passed verdict-X"` without relaying substantive atomic premises, sources, qualifiers, or rule violations. | `REVISE`: relay each checked finding as its own numbered premise carrying verdict ID, primary source, and qualifiers. |

## Edge-Case Rulings & Proportionality Standards

- **Stakes-bearing conclusions**: Any conclusion answering a primary ask or acceptance criterion, recommending a design, reaching the user, or authorizing a merge, send, or approval bears stakes. Reject "low-stakes", "reversible", or "obvious" as excuses for weak evidence; authority is user words or a governing specification only, never engine output.
- **Deliverable form & method fidelity**: When `## Ask` or active user turns specify a method, form, design, value, or medium noun (canvas, diagram, map, code, spec), audit departures independently rather than trusting `"no departures"`. Harmless rewording preserving the construct passes; silent medium or method swaps fail.
- **Strike baseless run-will-settle doubts**: An unexplained worry about whether a route, tool, or step will work when run ("haven't checked whether X works") with no stated reason it would fail is speculation. Judge valid as if absent -- never remand for a probe or relay it as a risk.
- **Never strike admitted unchecked facts readable now**: When a writer admits a load-bearing fact inspectable now is unchecked ("haven't checked whether PR merged", "assumed"), treat the premise as weak, not speculative. Judge whether its qualifier bears the step's stakes; live-state claims bound for the user resting on unchecked premises fail.
- **Exited-worker presentation rewrite**: When an exited worker leaves a complete primary evidentiary record with rough presentation only, the receiver may restate the argument cleanly from that recorded evidence. Evidentiary gaps, logical defects, or dropped asks still route to a fresh worker.
- **Unreachability by construction**: When an ask demanded an outcome unfulfillable at the reporter's stopping point and the report validly proves unreachability from quoted facts, treat that ask as answered rather than issuing `REVISE` or `FAIL`.
- **First-person tool observations & non-material defects**: First-person tool observations (`"I read..."`, `"I ran..."`) are not exempt from the source floor and must carry a checkable locator or command/output. However, only defects that could change the answer (load-bearing premises, validity, stakes-bearing support, ask coverage, authority, or non-waivable rule breaches) warrant a blocking `REVISE`; defects that cannot change the answer (such as an unsourced background claim about a brief or rule) get `PASS` with a non-blocking note and are omitted from upward relays.

## Worked Exemplar: Multi-Layer Diagnostic & Recommendation

Notice how every observation sits in its own atomic numbered premise with an exact locator, cross-block references cite the exact block that established each fact, zero facts are smuggled into inference bars, and each block passes its own Contrast Test:

```markdown
**Original Ask (`task-42/AC1-AC2`):** (AC1) Diagnose the primary cause of the p95 latency jump in the notification worker after deploy `c81f4a2`; (AC2) recommend the lowest-risk fix.

**Main Conclusion:** The p95 tail-latency spike (`420 ms` -> `4,850 ms`) is isolated to HTTP 429 retry paths caused by quadrupling `worker_concurrency` (`4` -> `16`) and replacing jittered exponential backoff with fixed `0.5s` retries in `worker/pool.py:34-48` (subject to unobservable sub-minute partner burst throttling). Reverting `worker_concurrency` to `4` and restoring jittered exponential backoff is the lowest-risk fix, pending staging load confirmation.

### Latency Pattern Isolation

(1) Production traces for `2026-10-12 00:00-06:00 UTC` (`n = 1,420` dispatches, commit `c81f4a2`) show p95 delivery latency rose to `4,850 ms` from `420 ms` on baseline `2026-10-11` (`n = 1,388`, commit `9d0e11b`).
(2) Across those same two trace windows (`c81f4a2` vs. `9d0e11b`), median delivery latency stayed flat (`190 ms` vs. `185 ms`).
(3) Grouping the `1,420` spans on `2026-10-12` by HTTP status shows 100% of spans exceeding `1,500 ms` (`n = 89`) hit `status = 429` before retrying, while non-429 spans (`n = 1,331`) held p95 at `210 ms`.
(4) Downstream partner headers logged `X-RateLimit-Limit: 60/min` unchanged across both windows.
-- When a tail-latency jump appears exclusively on HTTP 429 retry spans while median and non-429 tail latency stay flat under an unchanged advertised rate limit, the bottleneck lies in rate-limit contention and retry behavior rather than general network degradation or a quota reduction. An external traffic burst could also trip an unchanged limit; that rival is tested directly in the next block. --
(5) So the p95 latency spike at commit `c81f4a2` is isolated to HTTP 429 retry paths under an unchanged `60/min` partner quota.

### Root Cause Diagnosis and Rival Check

(1) From `Latency Pattern Isolation`, the p95 spike at commit `c81f4a2` is isolated to HTTP 429 retry paths under an unchanged `60/min` partner quota.
(2) Incoming dispatch volume in `2026-10-12 00:00-06:00 UTC` was `1,420` jobs (mean `3.9/min`, peak `18/min`), matching baseline `2026-10-11` (`1,388` jobs, peak `19/min`).
(3) `git diff 9d0e11b..c81f4a2 -- worker/pool.py:34-48` changed `worker_concurrency` from `4` to `16`.
(4) The same diff (`worker/pool.py:34-48`) replaced jittered exponential backoff (`base * 2**attempt + uniform(0, 1)`) with a fixed `0.5s` retry sleep.
(5) Bounded search (`grep -rn "429\|retry_delay\|worker_concurrency" worker/`) returned zero other outbound notification dispatchers or retry handlers outside `worker/pool.py`.
(6) Partner API response headers (`docs/partner-api.md:22`) expose only per-minute quota windows (`X-RateLimit-Limit: 60/min`) and zero sub-minute burst telemetry.
-- Holding incoming job volume and advertised partner quota constant, raising concurrency fourfold while removing backoff jitter produces synchronized retry bursts that trip a 60/min limit and stretch tail latency. A traffic surge is ruled out by (2) and an unrelated dispatcher is ruled out by (5); undocumented sub-minute partner burst throttling remains an unruled caveat because (6) shows partner headers expose only per-minute telemetry. --
(7) So the concurrency and fixed-retry change in `worker/pool.py:34-48` (commit `c81f4a2`) is the primary cause of the p95 tail-latency spike, qualified by the unobservability of sub-minute partner burst limits.

### Lowest-Risk Remediation

(1) From `Latency Pattern Isolation`, baseline commit `9d0e11b` held p95 latency at `420 ms` across `n = 1,388` dispatches (`2026-10-11`).
(2) From `Root Cause Diagnosis and Rival Check`, raising `worker_concurrency` (`4` -> `16`) and replacing jittered exponential backoff with fixed `0.5s` retries in `worker/pool.py:34-48` drives synchronized 429 retry spikes under `18/min` peak load (vs. `19/min` on baseline `9d0e11b`).
(3) The service reliability standard (`docs/worker-sla.md:14`) mandates p95 delivery latency under `500 ms`, bounded jittered exponential backoff on HTTP 429, and outbound concurrency `<= 8` unless a client-side token bucket is deployed.
(4) Bounded search (`grep -rn "token_bucket\|RateLimiter" worker/`) returned `0` matches, confirming no client-side token bucket exists in `worker/`.
-- Reverting the exact configuration drift to baseline settings that already met the reliability standard (`<= 8` concurrency and `420 ms` vs. the `500 ms` SLO) eliminates synchronized retry bursts without introducing new stateful infrastructure. A client-side token bucket would allow higher future throughput but adds state and rollout risk unnecessary at `18/min` peak load; because no post-revert load run has executed yet, staging load verification remains required to confirm p95 returns under the `500 ms` SLO. --
(5) So the lowest-risk fix is to revert `worker/pool.py:34-48` to `worker_concurrency = 4` and jittered exponential backoff, followed by a staging load test to verify p95 recovery under `500 ms`.
```

### Multi-Hop Coordinator Relay (Atomic Relayed Premises, Zero Bundling)

Notice how each relayed finding stands as its own numbered premise citing both `verdict-84a1c2e0` and the primary locator it came from -- never bundled into an omnibus `"The same checked report confirmed X, Y, and Z"` sentence:

```markdown
**Original Ask (`req-12`):** Report the cause of the notification latency spike and recommended fix.

**Main Conclusion:** Synchronized HTTP 429 retries from `worker/pool.py:34-48` (commit `c81f4a2`) caused the p95 spike (`420 ms` -> `4,850 ms`); reverting to `worker_concurrency = 4` and jittered exponential backoff is the recommended lowest-risk fix (pending staging load verification against the `500 ms` p95 SLO; sub-minute partner burst limits remain unobservable).

### Relayed Diagnostic Findings

(1) Production traces (`2026-10-12`, `n = 1,420`, via `verdict-84a1c2e0` PASS) showed p95 latency rose to `4,850 ms` from `420 ms` on baseline `9d0e11b` (`2026-10-11`, `n = 1,388`).
(2) Grouping the `1,420` spans on `2026-10-12` by HTTP status (via `verdict-84a1c2e0` PASS) isolated 100% of `> 1,500 ms` spans (`n = 89`) to HTTP 429 retries.
(3) Downstream partner headers (`2026-10-11` and `2026-10-12`, via `verdict-84a1c2e0` PASS) logged `X-RateLimit-Limit: 60/min` unchanged across both windows.
(4) Dispatch-rate telemetry (`2026-10-12` vs. `2026-10-11`, via `verdict-84a1c2e0` PASS) showed peak incoming volume stayed flat (`18/min` vs. `19/min`).
(5) `git diff 9d0e11b..c81f4a2 -- worker/pool.py:34-48` (via `verdict-84a1c2e0` PASS) raised `worker_concurrency` from `4` to `16`.
(6) The same diff (`worker/pool.py:34-48`, via `verdict-84a1c2e0` PASS) replaced jittered exponential backoff with a fixed `0.5s` retry sleep.
(7) Bounded search (`grep -rn "429\|retry_delay\|worker_concurrency" worker/`, via `verdict-84a1c2e0` PASS) found `0` other outbound dispatchers outside `worker/pool.py`.
(8) `docs/worker-sla.md:14` (via `verdict-84a1c2e0` PASS) mandates p95 latency under `500 ms`, jittered exponential backoff, and concurrency `<= 8` unless a client-side token bucket is deployed.
(9) Bounded search (`grep -rn "token_bucket\|RateLimiter" worker/`, via `verdict-84a1c2e0` PASS) returned `0` token-bucket matches in `worker/`.
(10) `docs/partner-api.md:22` (via `verdict-84a1c2e0` PASS) exposes only per-minute quota headers, leaving sub-minute partner burst throttling unobservable.
(11) `verdict-84a1c2e0` (PASS) disclosed no rule violations.
-- Verified child claims carrying individual primary locators, verdict ID, and original qualifiers relay upward without de novo source re-inspection, provided each fact stands on its own source so no unsourced assumption rides inside another statement and every caveat travels intact. Here (1)-(11) preserve each primary source separately, (11) discloses zero rule violations, and both the unobservable sub-minute caveat in (10) and pending staging verification against the `500 ms` SLO in (8) are preserved below. --
(12) So `worker/pool.py:34-48` should revert to `worker_concurrency = 4` and jittered exponential backoff, followed by staging load verification against the `500 ms` p95 SLO, noting the unobservable sub-minute partner throttle caveat.
```

## Realistic Subtle Defects & Minimal Remand Cures

1. **Premise Smuggling (Bundled / Unsourced Claim)** -- Contrastive pair:
   - _Defective (bundled)_: `(3) The same checked report (verdict-3a1b9c0d) found gateway logs recording account channel:beta because config/auth.env omits BETA_KEY.` (The checked report only observed `BETA_KEY` unset in `config/auth.env`; the logged account `channel:beta` is an unsourced assumption hitchhiking inside the same sentence.)
   - _Broken out (exposes the gap)_: `(3) config/auth.env:12 (via verdict-3a1b9c0d PASS) omits BETA_KEY.` / `(4) Gateway logs record account channel:beta [assumed -- no primary log quote or verdict source].`
   - _Minimal remand cure (`REVISE`)_: (b) break each assertion into its own numbered premise and either (c) supply primary log evidence for `(4)` or (a) drop/qualify the unsourced assumption.
2. **Quiet Construct / Proxy Drift**: A worker quotes `0` errors in `app.log` and `HTTP 200` on `/health` after a database migration and concludes `"the checkout migration succeeded with zero customer impact."` Infrastructure liveness cannot observe silent payment drops.
   - _Minimal remand cure (`REVISE`)_: (a) narrow the qualifier to service liveness, or (c) inspect post-migration order/payment completion counts against baseline.
3. **Domain-Mismatched Authority**: A worker cites an offline batch-ETL tuning policy ("retry immediately with fixed 200ms sleeps") to justify removing backoff jitter on a third-party rate-limited API client.
   - _Minimal remand cure (`REVISE`)_: (b) cite authority governing externally rate-limited APIs or bridge why batch-ETL rules transfer without causing retry storms.
4. **Unbounded Evidence for an Exclusive Claim**: A worker inspects two failing requests in `us-east` (`n = 2`) and concludes `"only the new serializer causes timeouts across all regions."`
   - _Minimal remand cure (`REVISE`)_: (a) narrow the claim to the two observed `us-east` traces, or (c) run a cross-region control comparison holding the serializer constant.
5. **Diagnosis-to-Remedy Mismatch**: Block 1 diagnoses slow queries caused by missing composite indexes on read replicas; Block 2 recommends raising write-primary connection pool limits without bridging the two.
   - _Minimal remand cure (`REVISE`)_: (b) align the remedy to the diagnosed replica index bottleneck or supply the missing bridge.
6. **Bare Verdict-Relay Stub**: A coordinator writes `"(1) Worker passed verdict-9f2a1b3c PASS. So the design is approved."`
   - _Minimal remand cure (`REVISE`)_: (b) break out and relay each checked observation with its primary locator, verdict ID, scope qualifiers, and disclosed rule violations.

## Appealable Administrative-Law Verdict Reasons

The templates below are for the `--reason-file` OTel audit record passed to `verdict.py`; sending a verdict or remand back to another agent is an inter-agent message and must use unfenced prose Argdown blocks only.

### Example PASS Reason

```text
PASS on claim-84a1c2e0 (asks task-42/AC1 and task-42/AC2).

Formal compliance holds on the face of the record:
- Latency Pattern Isolation: Premises (1)-(4) are atomic and quote exact trace windows, sample sizes (n=1,420 vs. n=1,388), p95/median splits, 429 isolation (89/89 spans > 1,500 ms), and unchanged partner quota headers; the inference validly narrows the anomaly to 429 retry paths without overclaiming.
- Root Cause Diagnosis and Rival Check: Premises (1)-(6) break out the diff changes (worker/pool.py:34-48), peak job rates (19/min vs. 18/min), bounded grep across worker/, and per-minute-only header granularity (docs/partner-api.md:22). The Contrast Test rules out traffic bursts and alternate dispatchers while qualifying unobservable sub-minute limits.
- Lowest-Risk Remediation: Premises (1)-(4) accurately cite each upstream block, anchor the remedy in docs/worker-sla.md:14, confirm 0 token-bucket matches, and note pending staging load verification.
- Ask coverage, authority, and rules: Both AC1 and AC2 are answered from primary observations bearing the stakes; zero bundled unsourced premises or rule breaches.

Relayable checked conclusions: worker/pool.py:34-48 (commit c81f4a2) caused the p95 429 tail-latency spike (subject to unobservable sub-minute partner limits); reverting to worker_concurrency=4 and jittered exponential backoff is the lowest-risk fix, pending staging load confirmation against the 500 ms p95 SLO.
```

### Example REVISE (Remand) Reason

```text
REVISE on claim-91d0f4a2 (ask task-55/AC1: confirm checkout migration 014 succeeded with zero customer impact).

Remanded to the originating agent on the face of the record (zero de novo verification performed):
- Construct / Proxy Drift: Premises (1)-(2) quote only app.log error count (0) and HTTP 200 on /health, which prove process liveness rather than checkout transaction integrity or customer impact.
- Unruled Rival Explanation: A broken checkout write path or silent validation drop leaves /health at 200 and app.log clean unless errors log there; nothing on the record rules this out.
- Minimal remand cure: Load ida:premise-check and either (a) narrow the claim strictly to service liveness if transaction telemetry is out of reach, or (c) inspect primary post-migration checkout completion counts against baseline, quote the deciding counts and window inline, and resubmit solely in prose Argdown blocks.

Relayable checked conclusions: none.
```
