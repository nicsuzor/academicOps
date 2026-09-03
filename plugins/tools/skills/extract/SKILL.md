---
name: extract
description: Pull structured information out of a source document and file it in the right place — training pairs from marked-up peer reviews, durable facts from email and correspondence archives, key information from a single document, or a plain format conversion of DOCX/PDF/XLSX/PPTX/MSG to markdown. Use for "extract", "ingest", "parse this", "convert to markdown", "pull the feedback out of this review", "get what matters out of this archive". Routes to the matching workflow and keeps sensitive material out of the public repository. Not for writing knowledge to the PKB directly (use `remember`) and not for authoring or capturing deep-research documents (use `deep-research`).
---

# Extract

Route an input to the matching extraction workflow, then store the result on the correct
side of the sensitive/public boundary.

## Search before creating

Search the PKB for existing knowledge on the subject before creating any extracted content:

```
mcp__services__pkb__search(query="[topic/person/document subject]")
```

Augment a match rather than creating a second document, and pull existing relationship
context for any person named in the source, so the extraction is grounded in what is
already known instead of accreting beside it.

## Routing

| Input                                                                                                                            | Workflow                                                                                                                                       |
| -------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| Review feedback plus its source document; tracked changes, comments, annotations; an ask about "training", "patterns", "dataset" | Training data extraction, below                                                                                                                |
| Email archive, correspondence, receipts, historical documents                                                                    | Archive extraction, below                                                                                                                      |
| One document whose key information is wanted, not for training                                                                   | Apply the extraction steps below directly; store per the content — PKB or framework docs                                                       |
| A document file (DOCX, PDF, XLSX, TXT, PPTX, MSG, DOC, DOTX) to be turned into markdown                                          | `scripts/pdf2md.py` for PDFs, pandoc for everything else, reading the tool's own documentation for flags. The `.md` lands beside the original. |

Ask the user to state the extraction goal when the input fits none of these cleanly.

## Training data extraction

Sources come in three shapes: a single document carrying both text and inline comments; a
review and its source document as separate files; or a revision history, where each revision
is paired with the one before it.

1. Convert to markdown, preserving markup, and read the whole document before extracting.
2. Extract feedback units — each a text span paired with the comment on it, plus enough
   surrounding source for the pairing to be learnable.
3. Categorise each unit by type, scope, and action.
4. Group similar units and name the principle underneath each group.
5. Generalise each principle far enough to transfer and specifically enough to apply, and
   record where it does not hold.
6. Split the results across the storage boundary below.

Flag a unit whose feedback is ambiguous as `"quality": "ambiguous"` and keep it with the
caveat attached rather than dropping it or resolving the ambiguity by guess.

## Archive extraction

Most archival documents have no long-term value, so extract selectively: concrete outcomes,
significant relationships, and financial records. Skip newsletters, invitations,
administrative routine, and mass communications. Store through `Skill(skill="remember")`
with tags and canonical identifiers.

## The storage boundary

Training data carries author names, unpublished work, and specific critiques of individuals,
so it splits in two.

**Sensitive material** goes to `$ACA_DATA/processed/review_training/{collection_name}/` —
outside any repository, never committed — as `extracted_examples.json` (full text/feedback
pairs), `training_pairs.jsonl`, `collection_summary.md` (identifying information intact),
and `source_documents/` where sources are retained. Email material goes under
`$ACA_DATA/processed/email_archive/`. When the right location is unclear, default to
`$ACA_DATA/processed/` and confirm with the user.

**Generalised patterns** go to the public framework — principles into
`plugins/tools/skills/peer-review/references/`, depersonalised examples into the relevant
skill's own `references/` directory.

Depersonalisation means the published pair carries the reviewer's reasoning and none of the
identifiers: no names, institutions, grant or manuscript titles, or dates that would
re-identify the submission; roles ("Author", "Reviewer") in place of people; generic
descriptions in place of work titles. Where the reasoning cannot survive that strip, the
pair does not go to the public surface at all — construct a synthetic example carrying the
same principle instead.

## Before reporting done

Confirm by inspecting the written files, not from intent: every extractable item is either
processed or skipped with a stated reason; the output files exist at the paths above; the
public surface contains no identifying information; and the collection summary records the
decisions and ambiguities the extraction ran into.
