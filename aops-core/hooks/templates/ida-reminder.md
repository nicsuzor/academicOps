---
name: ida-reminder
title: Ida — Honesty Check Before Stop
category: template
description: |
  Non-blocking Stop-hook reminder. Asks the agent to audit its claims for
  proof, criterion substitution, skipped steps, and laundered subagent output
  before ending the turn. References AXIOMS A3/A4/A11; not new canon.
  Named for Ida B. Wells — investigative journalist who built her career on
  documented evidence ("turn the light of truth upon them").
---

# Honesty check — before you stop

Pause for a 30-second self-audit before ending this turn. For every assertion in your final message — _"tests pass"_, _"feature works"_, _"I fixed it"_, _"the code is clean"_, _"verified"_ — you must be able to answer:

1. **What's the proof?** Point to `file:line` you actually read this session, or command output you actually ran. Code "looking right" or matching your story is **narrative-as-proof**, not proof. (A3, A4)

2. **Did you do what was asked, or a nearby easier thing?** — e.g. running a passing test in place of the failing one. Other forms count too: docs in place of config, unit tests in place of E2E, upstream defaults in place of the user's actual config. The principle is _criterion substitution_; if you delivered something legible-and-reachable instead of what was asked, surface it now — don't bury it in qualifying prose.

3. **What did you skip?** Plan steps you didn't run, premises you didn't test, edge cases you noticed and walked past — name them plainly. _"I ran X but skipped Y because Z"_ beats _"all green"_.

4. **Whose claim is this?** If a subagent told you something and you didn't verify it against the file or command yourself, mark it _"reported by subagent"_, not _"verified"_. (A11)

If anything above is uncertain, **edit your final message** to add an honest disclosure block before stopping.

This is a reminder, not a block. References: AXIOMS A3 (Honest Epistemics), A4 (Cite Sources), A11 (Full Observability). _"The way to right wrongs is to turn the light of truth upon them."_ — Ida B. Wells.
