## Error Handling (Anti-Silent-Failure)

If any tool or API call you depend on to complete your mandated action fails (e.g. a `gh api` call returns non-zero / 403, a file edit or push fails), you MUST NOT fail silently or surface the problem only in your transcript. Post a comment to the relevant PR (or issue) that states: (a) which tool/call failed and the error, (b) the verdict / result you would have produced had it succeeded, and (c) that this needs human or workflow attention. Then exit. Surfacing-via-comment is mandatory; the run log is not a sufficient channel.

## Escape content in `gh` CLI / API calls

When passing review or comment text to `gh` (e.g. `gh pr review`, `gh pr comment`, `gh api`), always quote/escape the content. Unquoted text containing shell brace patterns (`{...}`) or other shell metacharacters can be mangled by expansion before it reaches GitHub. Prefer `--body-file` or a quoted heredoc over inline `--body "$VAR"`.
