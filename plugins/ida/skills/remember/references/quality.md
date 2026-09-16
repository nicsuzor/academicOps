# Note Quality Standards

Evaluate knowledge notes against five core criteria:

1. **Traceable**: Every claim cites its source (memory ID, session reference, PR number, date).
2. **User voice**: Grounded in specific user experience rather than generic assistant summaries.
3. **Single topic**: Dedicated to one coherent subject without trailing unrelated sections.
4. **Concrete**: Grounded in real numbers, names, and incidents rather than abstract platitudes.
5. **Right abstraction**: Generalises enough to inform adjacent work without hardcoding transient environment paths.

## Synthesis vs. Concatenation

Identify the unifying principle across instances rather than concatenating source bullet points. The ideal source depth is four to six inputs.

## Antipatterns

- **Stray sections**: Unrelated content appended to a note. Move to dedicated notes.
- **Overlap**: Parallel notes on the same topic. Merge into the canonical note and delete the duplicate.
- **Fabrication**: Assertions not found in the underlying sources.
- **Under-attribution**: Unreferenced claims.
- **Aging detail**: Ephemeral version strings or tooling trivia that expire quickly.
- **Unmarked sensitive content**: Unflagged personal, institutional, or financial data.

## Quality Test

Before finalizing a note, verify:

1. Can every claim be traced to an explicit source?
2. Is the voice grounded in user experience rather than assistant exposition?
3. Does the note address exactly one topic?
4. Is the insight transferable to future work?
5. Does the synthesis reveal principles not stated in any single source?
