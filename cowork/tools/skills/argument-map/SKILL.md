---
name: "argument-map"
description: "Build a reviewable map of a text's argument (thesis chapter, paper, submission, judgment, policy, or an author's own mind map). Gives a charitable reconstruction with every gap tagged, a list of what the argument still needs, and a readable overview page. Use for \"map the argument\", \"what does this argument still need\", \"show me how the chapter hangs together\", or for weaving an author's new notes or diagrams into an existing map. Not for plain extraction without assessment (use tools:argument-extraction), or for mind maps and concept maps with no inferential structure (use tools:diagram)."
---

# Argument map

Produce three things:

- **Canonical Argdown source.** This is the record; every picture is derived from it.
- **"What the argument still needs".** The open issues, part by part.
- **A readable page.** It leads with an overview and keeps the detailed maps below.

## Before starting

- **Name four things:** the text, its author, the reader of the map, and the map's job (supervising a draft, reviewing a submission, testing your own case). The job decides how hard to press. If you cannot name the job, ask, because a map with no stated purpose has nothing to be judged against.
- **Extend, don't duplicate.** Look for an existing map of the same text and extend it rather than starting a second one.

## Reconstruct

- **Extract first with `tools:argument-extraction`.** It sets the Argdown output contract: titles, `source` quotes with locators, implicit premises, and the parser loop. Then reconstruct on top of what it produces.
- **Follow the text's own structure.** Put the thesis first, then one Argdown section per part of the text, in the text's order. A reader checks a map against the text, so the map should match it.
- **Reconstruct charitably.** Build the strongest valid version of each step. Where validity needs a premise the author never states, add it, mark it implicit, and tag it `#missing`.
- **Read claims at the strength the evidence can carry.** When the wording overstates (for example "veto" where the evidence shows "sometimes limits"), narrow your label but keep the author's words verbatim in `source`. Record the narrower reading as a decision.
- **Attribute relations correctly.** Support is `+>`, attack is `->`, and undercut is `_>` (it attacks the inference, not a premise). Attach each relation to the argument that concludes or first states the claim, never to one that only borrows it as a premise. Otherwise the map shows links the text never makes.
- **Tag what is open.** Define the legend in the frontmatter. Keep any categories the author already uses (for example evidence versus theory) as extra tags.
  - `#missing`: a step you added.
  - `#needs-evidence`: a load-bearing premise without data or authority.
  - `#unanswered`: an objection the text raises but does not meet.
  - `#conflict`: two of the author's claims contradict each other, or a branch falls outside the thesis as stated.
- **Leave the author's judgement calls to the author.** Conflicts, scope choices and cut-offs are theirs. Tag each one and state the question it raises.

## Integrate new material

- **Put each new item in the part where it does its work.** Do not append it as a new part, because an appended block reads as a separate argument and hides how it changes the existing steps.
- **Merge restatements.** If an item restates an existing claim, merge it into that claim and keep both locators.
- **Re-check relations.** Afterwards, re-check every relation that touches a changed claim.

## Check before delivering

- **The source is sound.** The Argdown parses without errors. Every `#missing` item has a reason, and every quoted source has a locator.
- **The overview is complete.** No argument is left isolated. Every relation in the source is drawn, written on a box, or skipped under the attribution rule. List the skipped ones.
- **The links are real.** Trace three relations back to the text and check that the text makes each link.
- **The page renders.** Look at it at desktop and phone width. Check every cross-reference in the prose ("see the next section") against the actual order of the page.
- **It answers the ask.** Re-read the original ask and check that the page answers it.
- **The map is readable.** Ensure you check the visual renderings, not just the Argdown source. Revise the layout, labels, and colors until the output is clear and legible.

## Record

- **One home.** Keep the Argdown source and the decisions (narrowed readings, merges, dropped views) in the map's PKB note, one line per decision.
- **Rebuild, don't patch.** Rebuild the page from the source. Do not hand-edit the derived renders.
