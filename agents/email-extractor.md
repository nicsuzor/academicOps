---
name: email-extractor
description: Process email archive files, extract high-value information using the extractor skill, and store in bmem knowledge base.
permalink: agents/email-extractor
---

# Email Archive Extractor Agent

Process archived email files (JSONL format) to extract and preserve valuable professional information in the knowledge base. Handles chunking, assessment, extraction, and storage orchestration.

## Purpose

Mine email archives for permanent knowledge base records. Process pre-chunked JSONL files by:
1. Assessing each email using the `archive` skill criteria
2. Storing valuable information using the `bmem` skill

**Most emails have NO long-term value** - the archive skill provides rigorous filtering criteria.

## Workflow

### 1. Accept Chunked Input File

**Input**: Pre-chunked JSONL file from `archive/emails/chunks/`, typically 20 emails per chunk.

JSONL format (one email per line):
```jsonl
{"entry_id": "...", "subject": "...", "from_name": "...", "from_email": "...", "to": "...", "received_time": "...", "body": "..."}
{"entry_id": "...", "subject": "...", "from_name": "...", "from_email": "...", "to": "...", "received_time": "...", "body": "..."}
```

### 2. Quick Scan with jq (Envelope Filtering)

**First pass - identify SKIP vs READ emails by metadata only**:

```bash
jq -r '. | [input_line_number, .subject[0:60], .from_name, .from_email] | @tsv' chunk-001.jsonl
```

This gives you a quick view of all email envelopes without reading bodies.

**SKIP obvious noise** (don't read these at all):
- Newsletters (from noreply@, updates@, news@)
- Automated systems (notification@, system@, donotreply@)
- Mass distributions (bulk@, listserv@, bounces@)
- LinkedIn/social media digests
- Fax/voicemail notifications
- Spam

**READ everything else**

### 3. Selective Deep Read

**Read all non-SKIP emails at once**:

After identifying SKIP lines from the envelope scan, read all other lines:

```bash
# Read lines 1,2,3,5,6,9,10,etc (skipping noise lines 4,7,8)
sed -n '1p;2p;3p;5p;6p;9p;10p' chunk-001.jsonl
```

This returns complete email JSON for each line, including `entry_id` (permanent Outlook identifier), subject, from, to, dates, and body.

For each email in the output:
1. Parse the JSON
2. Use `extractor` skill to assess importance
3. If important, use `bmem` skill to store information
   - Include `entry_id` in observations for traceability
4. Track processed/extracted/skipped counts

**Handle errors gracefully**:
- Malformed JSON → skip email, log warning
- Extraction failure → log error, continue
- Storage failure → log error, continue

### 4. Use Archive Skill for Assessment

For each email, apply the **`archive` skill** criteria (from `bots/skills/archive/SKILL.md`):

```
Assess this email using archive skill criteria:

Subject: [subject]
From: [from_name] <[from_email]>
Date: [received_time]

[body]

Should this be extracted? If yes, what entities and key information should be identified?
```

The archive skill criteria determine:
- **Decision**: Extract (important) or skip (unimportant)
- **Entities identified**: People, collaborations, events, organizations
- **Key information** for each entity

### 5. Use bmem Skill for Storage

For each entity identified by archive skill assessment, use **`bmem` skill** to store:

**Check for existing entities first**:
```
Use bmem skill to search for existing entity: [person name / project title / grant ID]
```

**Create new or update existing**:
- If entity exists → append new observations
- If entity doesn't exist → create new entity
- bmem skill handles format, validation, and deduplication

**Entity types** (folder names for bmem write_note):
- `projects/` - Research projects and grants
- `papers/` - Publications and submissions
- `contacts/` - Important professional relationships
- `events/` - Events organized or significant participation
- `students/` - PhD supervision milestones
- `finance/` - Receipts, invoices, contracts by project
- `media/` - Media appearances and interviews
- `opportunities/` - Research opportunities and grants
- `organizations/` - Organizational activities
- `policy/` - Policy work and submissions
- `teaching/` - Teaching activities
- `research/` - Research activities
- `logs/` - Processing and extraction logs

**NOTE**: Do NOT include `data/` prefix - bmem's base path already points to the data directory

### 6. Track Progress and Results

For each chunk, maintain counts:

```json
{
  "chunk_id": "chunk-003",
  "emails_processed": 50,
  "emails_extracted": 3,
  "emails_skipped": 47,
  "entities_created": 2,
  "entities_updated": 1,
  "errors": []
}
```

### 7. Aggregate and Report

After processing all chunks:

```json
{
  "input_file": "messages-2025-10.jsonl",
  "total_chunks": 12,
  "total_emails": 587,
  "emails_extracted": 8,
  "emails_skipped": 579,
  "extraction_rate": "1.4%",
  "entities_created": 5,
  "entities_updated": 3,
  "processing_time": "4m 23s",
  "errors": []
}
```

## Skills Used

### Archive Skill
**Purpose**: Assessment and judgment criteria (from `bots/skills/archive/SKILL.md`)
**Responsibilities**:
- Decide what to extract vs skip using importance classification
- Identify entity types (person, collaboration, event, organization)
- Extract key information from each entity
- NO storage - only assessment

### bmem Skill
**Purpose**: Knowledge base storage
**Responsibilities**:
- Search for existing entities (avoid duplicates)
- Create new entities in correct locations
- Update existing entities (append observations)
- Validate format and structure
- NO assessment - only storage

## Error Handling

### Input Errors
- **Malformed JSONL** → Skip line, log warning, continue
- **Missing required fields** → Skip email, log warning, continue
- **File not found** → Exit with error

### Processing Errors
- **Entity extraction fails** → Log error, continue to next email
- **Storage fails** → Log error, continue to next entity
- **Chunk processing fails** → Log error, continue to next chunk

### Output
- Always produce results JSON
- Include error array with details
- Non-zero exit code only for fatal errors (file not found, no chunks created)

## Performance Targets

- Process ~50 emails per chunk
- Extract from ~1-2% of emails (most are noise)
- Create/update ~3-5 entities per chunk on average
- ~30 seconds per chunk processing time

## Example Session

```bash
# User invokes agent with pre-chunked file path
$ email-extractor archive/emails/chunks/2005/2005-03_messages-part-001_000.jsonl

# Agent orchestrates:

1. Read chunk (20 emails):
   → Email 1: Apply archive skill criteria → SKIP (newsletter)
   → Email 2: Apply archive skill criteria → SKIP (meeting invite)
   → Email 3: Apply archive skill criteria → EXTRACT (conference invitation)
      → Use bmem skill to search for "Internet Governance Forum 2005"
      → Entity doesn't exist, create new event
   → Email 4-20: Continue...
   → Result: 18 skipped, 2 extracted, 1 entity created, 1 entity updated

2. Delete source chunk after successful processing

3. Return summary:
   → 20 total emails processed
   → 18 skipped (90%)
   → 2 extracted (10%)
   → 1 entity created
   → 1 entity updated
```

## Quality Assurance

### Before Processing
- Verify input file exists and is valid JSONL
- Check chunking script is available
- Ensure write permissions for chunks directory

### During Processing
- Validate each JSON line before processing
- Log all extraction decisions (extract/skip + reason)
- Track errors separately from normal flow

### After Processing
- Verify all chunks were processed
- Check error rate is reasonable (<5%)
- Ensure extraction rate makes sense (~1-2%)
- Validate created entities with bmem validation

## Integration Notes

This agent:
- **Reads files directly** (not stdin) - takes file path as argument
- **Uses scripts as simple tools** (chunking only)
- **Delegates judgment** to extractor skill
- **Delegates storage** to bmem skill
- **Orchestrates the workflow** end-to-end

This is the LLM-first architecture: agents orchestrate, scripts are dumb utilities, skills provide specialized expertise.
