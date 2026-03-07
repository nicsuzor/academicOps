# Decision Coversheet Template

Use this template for every item in the **Decisions** section of the bundle.

## Template

```markdown
### [Title] -- [[project]]

**Decision needed**: [One line: what exactly Nic needs to decide]
**Recommended action**: **[Accept/Decline/Approve/Defer]** -- [one sentence justification]
**Deadline**: [date, with "X days overdue" if applicable]
**Stakes**: [What happens if deferred another week]

**Key context**:

- [Most important fact]
- [Second most important fact]
- [Relevant constraint or consideration]

**Task**: [[task-id]]

- [ ] Resolved

<!-- @nic: approved / decline / defer to DATE / other -->

<details><summary>Supporting detail</summary>

[Extended context, email excerpts, related tasks -- only if needed]

</details>

<details><summary>Draft email (recommended action)</summary>

To: recipient@example.com
Subject: Re: [Original subject]
In-Reply-To: [entry_id]

Hi [Name],

[Draft text per email conventions]

Best,
Nic

</details>
```

## Rules

1. **Max 15 non-blank lines above the fold** (before `<details>`). If you're writing more, move content into the details section.
2. **Max 5 bullet points of key context.** If you need more than 5, you're including too much.
3. **The recommendation is explicit and justified in one sentence.** Never write "it depends."
4. **Decision summary is not a task description.** Write what Nic needs to decide, not what the task is about.
5. **Stakes are concrete.** "Nothing happens" is a valid answer -- it means the item can be deferred.
6. **For accept/decline decisions**, pre-draft both options. Recommended option is the visible details section; alternative goes in a second collapsed section labelled "Draft email (alternative)".
7. **Include the Outlook `entry_id`** in email drafts for threading via `In-Reply-To`.
8. **The coversheet alone must be sufficient to decide.** No "see task for details" -- excerpt what's needed inline.
