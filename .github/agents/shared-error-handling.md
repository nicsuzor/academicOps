## Error Handling (Anti-Silent-Failure)

If any tool or API call you depend on to complete your mandated action fails (e.g. a `gh api` call returns non-zero / 403, a file edit or push fails), you MUST NOT fail silently or surface the problem only in your transcript. Post a comment to the relevant PR (or issue) that states: (a) which tool/call failed and the error, (b) the verdict / result you would have produced had it succeeded, and (c) that this needs human or workflow attention. Then exit. Surfacing-via-comment is mandatory; the run log is not a sufficient channel.
