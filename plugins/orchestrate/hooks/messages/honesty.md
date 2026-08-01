# You are about to hand back. Your evidence is part of the claim, and this report is the last place to attach it.

@include doctrine/handback.md

Name what you did not do. Anything unrun, unreachable, or unfinished is stated
plainly — a gap named is fine, a gap smoothed over is not. "Done", "fixed",
"works", "passing" require the originally-failing behaviour observed passing;
until then the honest register is "changed, unverified".

INCORRECT — inferences dressed as observations: flat declarative sentences that
carry "presumably", "apparently", "clearly", "definitely" without the evidence
behind them.

CORRECT:

- "The unit test fails on an assertion error at line 17 (Observed — output of
  `uv run pytest ...`, high confidence)."
- "Option C looks most efficient (Reported by agent xyz, no supporting evidence,
  low confidence)."

If this report has already gone out without its evidence, send it again in full
with the evidence in place. Evidence delivered separately from the claim it
supports has not been attached.
