## Error Handling (Anti-Silent-Failure)

If any tool or API call you depend on to complete your mandated action fails (e.g. a `gh api` call returns non-zero / 403, a file edit or push fails), you MUST NOT fail silently or surface the problem only in your transcript. Post a comment to the relevant PR (or issue) that states: (a) which tool/call failed and the error, (b) the verdict / result you would have produced had it succeeded, and (c) that this needs human or workflow attention. Then exit. Surfacing-via-comment is mandatory; the run log is not a sufficient channel.

## Escape content in `gh` CLI / API calls

When passing review or comment text to `gh` (e.g. `gh pr review`, `gh pr comment`, `gh api`), always quote/escape the content. Unquoted text containing shell brace patterns (`{...}`) or other shell metacharacters can be mangled by expansion before it reaches GitHub. Prefer `--body-file` or a quoted heredoc over inline `--body "$VAR"`.

## Review scope & economy (read before you review)

You share this PR with other reviewers (the other named agent, Gemini, and humans) and you may have reviewed an earlier SHA of it yourself. Read what already exists before adding to it. This is not optional courtesy — repeated, redundant review prose is the dominant cost when a PR churns across many pushes.

**1. Read the existing thread first.** Before forming your verdict, read the prior reviews and the comment thread on this PR:

```bash
gh pr view "$PR_NUMBER" --repo "$REPO" --comments
gh api "repos/$REPO/pulls/$PR_NUMBER/reviews?per_page=100" \
  --jq '.[] | {author: .user.login, state, sha: .commit_id, body: (.body // "" | .[0:280])}'
```

**2. Don't re-investigate code that hasn't changed since your last review.** If a prior verdict of yours already stands on an earlier SHA, scope your work to what changed since then — review `git diff <last-reviewed-sha>..$HEAD_SHA`, not the whole PR again. Findings you already raised on untouched lines stand on their own; do not re-derive or re-state them. (This is in addition to the SHA-idempotency skip your agent file already specifies — that skips an identical re-review of the _same_ SHA; this avoids redundant re-review _across_ SHAs.)

**3. Don't restate objections already raised by someone else.** If another reviewer (or an open thread) has already made a point, do not repeat it in full. At most reference it in one line ("Concur with QA on the `is_shared` NameError") so your verdict is self-consistent — then move on. Re-litigating another reviewer's finding is noise, not diligence. Stay in your lane (axioms / runtime / strategy); raise only what your lane owns and others have not already covered.

**4. Be concise.** Lead with the verdict. Include only load-bearing findings, each with `file:line` and the minimum the mechanic needs to act — no diff summary, no recap of what the PR does, no preamble. A clean pass is the single marker line your agent file specifies. Length is not thoroughness; a long review of an unchanged or already-covered concern is the failure mode this section exists to prevent.

**Still post your own verdict every run.** Economy governs the _prose in the body_, never the verdict itself — the workflow keys off your review **state** (APPROVED / CHANGES_REQUESTED), so you must always post it, even when your body is one line because everything worth saying was already said.
