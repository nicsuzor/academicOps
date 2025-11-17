---
name: email-extractor
description: Process email archive files, extract high-value information using the extractor skill, and store in bmem knowledge base.
permalink: agents/email-extractor
---

# Email Archive Extractor Agent

Process archived email files (JSONL format) to extract and preserve valuable professional information in the knowledge base. Handles chunking, assessment, extraction, and storage orchestration.

## Purpose

Mine email archives for permanent knowledge base records. Process large JSONL files by:
1. Chunking them into manageable pieces
2. Assessing each email using the `extractor` skill
3. Storing valuable information using the `bmem` skill

**Most emails have NO long-term value** - the extractor skill provides rigorous filtering criteria.

## Workflow

### 1. Read Input File

Accept JSONL file path as input (not stdin). JSONL format:

```jsonl
{"entry_id": "...", "subject": "...", "from_name": "...", "from_email": "...", "to": "...", "received_time": "...", "body": "..."}
{"entry_id": "...", "subject": "...", "from_name": "...", "from_email": "...", "to": "...", "received_time": "...", "body": "..."}
```

### 2. Chunk the File

Use the chunking script to split large files:

```bash
python ~/src/writing-archive/scripts/chunk_emails.py <input.jsonl> <chunks_dir>
```

This creates size-based chunks (~200KB, ~50 emails each) in `chunks_dir/chunk-NNN.json` format.

**Script does ONLY mechanical splitting** - no filtering, no logic.

### 3. Process Each Chunk

For each chunk file:

1. **Read chunk file** (JSON object with email array)
2. **Process each email line-by-line**:
   - Parse JSON
   - Use `extractor` skill to assess importance
   - If important, use `bmem` skill to store information
   - Track processed/extracted/skipped counts

3. **Handle errors gracefully**:
   - Malformed JSON → skip email, log warning
   - Extraction failure → log error, continue
   - Storage failure → log error, continue

### 4. Use Extractor Skill for Assessment

For each email, invoke the **`extractor` skill** with email content:

```
Use the extractor skill to assess this email:

Subject: [subject]
From: [from_name] <[from_email]>
Date: [received_time]

[body]

Should this be extracted? If yes, what entities and key information should be identified?
```

The extractor skill returns:
- **Decision**: Extract or skip
- **Entities identified**: People, projects, events, contacts, financial records
- **Key information** for each entity

### 5. Use bmem Skill for Storage

For each entity identified by extractor skill, use **`bmem` skill** to store:

**Check for existing entities first**:
```
Use bmem skill to search for existing entity: [person name / project title / grant ID]
```

**Create new or update existing**:
- If entity exists → append new observations
- If entity doesn't exist → create new entity
- bmem skill handles format, validation, and deduplication

**Entity types**:
- `data/projects/` - Research projects and grants
- `data/papers/` - Publications and submissions
- `data/contacts/` - Important professional relationships
- `data/events/` - Events organized or significant participation
- `data/students/` - PhD supervision milestones
- `data/finance/` - Receipts, invoices, contracts by project

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

### Extractor Skill
**Purpose**: Assessment and judgment criteria
**Responsibilities**:
- Decide what to extract vs skip
- Identify entity types (person, project, event, etc.)
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
# User invokes agent with file path
$ email-extractor messages-2025-10.jsonl

# Agent orchestrates:

1. Chunk file:
   → python chunk_emails.py messages-2025-10.jsonl chunks/
   → Created 12 chunks

2. Process chunk-001.json (50 emails):
   → Email 1: Use extractor skill → SKIP (newsletter)
   → Email 2: Use extractor skill → SKIP (meeting invite)
   → Email 3: Use extractor skill → EXTRACT (paper acceptance)
      → Use bmem skill to search "Platform Governance paper"
      → Entity exists, update with new observation
   → Email 4-50: Continue...
   → Result: 48 skipped, 2 extracted, 1 created, 1 updated

3. Process chunk-002.json (50 emails):
   → Similar process...

...

12. Aggregate results:
   → 587 total emails
   → 579 skipped (98.6%)
   → 8 extracted (1.4%)
   → 5 entities created
   → 3 entities updated
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
