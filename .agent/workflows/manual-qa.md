# Manual QA Workflow

Test that the framework works with different AI CLI tools.

## Claude Test

```bash
command claude --permission-mode bypassPermissions --output-format json --print "What time is it?"
```

## Gemini Test

```bash
command gemini --approval-mode yolo --output-format stream-json --p "What time is it?"
```

## Generate Transcripts

After both runs, create transcript files:

```bash
uv run python $AOPS/aops-core/scripts/transcript.py --recent
```

## Find New Transcripts

Find transcripts created in the last 10 minutes:

```bash
fd -l --newer 10m -e md . ~/writing/sessions/
```

Or search for specific content in recent transcripts:

```bash
fd --newer 60m -e md . ~/writing/sessions | xargs rg "what time is it"
```

## Assessment

Review the abridged transcript for each session and assess the conversation, looking for markers of features from our framework.
