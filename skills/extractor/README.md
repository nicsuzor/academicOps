---
title: Email Archive Knowledge Extraction
type: note
permalink: skills/extractor/readme
description: Automated system for extracting important professional knowledge from archived emails and converting them to properly formatted markdown knowledge base entries.
tags: [skill, extractor, email, knowledge-extraction, memory]
---

# Email Archive Knowledge Extraction

Automated system for extracting important professional knowledge from archived emails and converting them to properly formatted markdown knowledge base entries.

## Quick Start

### Check Status

```bash
uv run python bots/skills/archive/scripts/batch_next.py status
```

### Process Next File

Simply run the slash command:

```
/archive
```

This will:

1. Get the next file from `archive/incoming/`
2. Evaluate its importance
3. Extract and create properly formatted markdown files in `data/archive/` if important
4. Delete the source file
5. Log the decision

### Process Multiple Files

Run `/archive` repeatedly, or use a simple loop (future enhancement: automated batch processor).

## Architecture

```
archive/
├── incoming/          # Email files to process (gets consumed)
├── processed/         # Empty (files deleted after processing)
├── failed/            # Files that failed processing
├── processing.log     # Log of all decisions
└── processing_state.json  # Resume state

bots/skills/archive/
├── SKILL.md           # Classification criteria and extraction guidelines
├── README.md          # This file
├── scripts/
│   └── batch_next.py  # Batch management (pop, confirm, fail)
└── tests/
    └── test_archive_integration.sh  # Integration tests

bots/commands/
└── archive.md         # /archive slash command

data/archive/          # Output: Properly formatted markdown knowledge entries
```

## Components

### 1. Archive Skill (`SKILL.md`)

Defines importance classification criteria:

**Important** (extract):

- External collaborations and grant proposals
- People met while traveling
- Significant events and speaking invitations
- Important career milestones

**Unimportant** (skip):

- Routine meetings and logistics
- Newsletters and bulk mail
- Normal student/staff interactions

**Test**: "Is this important enough to mention at a monthly research meeting?"

### 2. Batch Manager (`scripts/batch_next.py`)

Stateful file processing with safe deletion:

```bash
# Get next file
uv run python bots/skills/archive/scripts/batch_next.py next

# Confirm processing complete (deletes source)
uv run python bots/skills/archive/scripts/batch_next.py confirm <filename>

# Mark as failed (moves to failed/)
uv run python bots/skills/archive/scripts/batch_next.py fail <filename> "reason"

# Check status
uv run python bots/skills/archive/scripts/batch_next.py status

# Reset state (DANGEROUS - only for testing)
uv run python bots/skills/archive/scripts/batch_next.py reset
```

### 3. Slash Command (`/archive`)

Long-lived processing entry point. Each invocation processes ONE file to avoid context overflow.

## Output Format

Generated knowledge base entries follow structured format:

### Person Entity

```markdown
---
title: [Name] - [Affiliation]
type: contact
tags: [person, research-area, location, connection-type]
---

# [Name] - [Affiliation]

## Context

[Who they are, their work, how Nic knows them]

## Observations

- [fact] [Position] at [Institution] #affiliation
- [research] Focus on [topic] #research
- [connection] Met at [Event] #meeting
- [contact] Email: [email] #contact

## Relations

- met_at [[Event]]
- affiliated_with [[Institution]]
- researches [[Topic]]
```

### Collaboration/Project

```markdown
---
title: [Project Name]
type: project
status: [proposed|active|completed]
tags: [collaboration, research-area, partners]
---

# [Project Name]

## Context

[Description of collaboration]

## Observations

- [goal] [Objective] #objective
- [fact] Partners: [list] #partners
- [timeline] [dates] #timeline

## Relations

- involves [[Person]]
- relates_to [[Topic]]
```

## Processing Log

All decisions logged to `archive/processing.log`:

```
2025-11-10 14:30:00 | collaboration_santos.txt | EXTRACT | External collaboration proposal
2025-11-10 14:30:15 | room_booking.txt | SKIP | Routine logistics
2025-11-10 14:30:20 | newsletter.txt | SKIP | Bulk newsletter
```

## Safety Features

1. **Destructive processing**: Source files deleted only after successful extraction and validation
2. **State tracking**: Can resume from interruption
3. **Error handling**: Failed files moved to `archive/failed/`, not deleted
4. **Validation**: All output validated before confirmation
5. **Logging**: All decisions logged for review

## Testing

Run integration tests:

```bash
bots/skills/archive/tests/test_archive_integration.sh
```

Tests verify:

- Batch script functionality
- Directory structure
- Slash command configuration
- Skill documentation completeness

## Future Enhancements

1. **Automated batch processing**: Script to run /archive repeatedly
2. **PDF/DOCX support**: Process non-text formats
3. **Email thread reconstruction**: Link related messages
4. **Confidence scoring**: Flag uncertain classifications
5. **Progress reporting**: Dashboard for processing status
6. **Resume capability**: Better handling of interruptions

## Troubleshooting

**No files to process**:

```bash
# Check incoming directory
ls -la archive/incoming/
```

**Processing stuck**:

```bash
# Check current state
uv run python bots/skills/archive/scripts/batch_next.py status

# If needed, reset (WARNING: cannot recover deleted files)
uv run python bots/skills/archive/scripts/batch_next.py reset
```

**Invalid output**:

- Check `data/archive/` for malformed files
- Review skill examples in `SKILL.md` for proper format
- Ensure all entries use properly formatted markdown

**File failed to process**:

- Check `archive/failed/` directory
- Review `archive/processing.log` for error details
- Fix issue and manually move file back to `archive/incoming/`
