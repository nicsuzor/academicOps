# Structured Log Analysis Guide

This document provides techniques for structured log analysis.

## Finding Structured Logs

Structured logs are often written in JSONL format to a temporary directory.

```bash
# Get the most recent structured log file
ls -t /tmp/project_*.jsonl 2>/dev/null | head -1
```

## Recommended: Use Structured Log Tools

If the project provides a dedicated tool for parsing logs, prefer that. It may offer features like level filtering.

```bash
# Example of a dedicated log tool
my_log_tool logs -n 50 -l ERROR
```

## Manual Analysis (Advanced)

If a dedicated tool is not available, you can use standard command-line tools like `grep` and `jq`.

### 1. View Recent Structured Log Entries
```bash
# View last N lines of JSONL logs
tail -50 /tmp/project_*.jsonl

# Basic level filtering with jq (if available)
tail -100 /tmp/project_*.jsonl | jq 'select(.level == "ERROR")'
```

### 2. Filter by Log Level (Manual)
```bash
# Show only ERROR and CRITICAL messages
grep '"level":"ERROR"\|"level":"CRITICAL"' /tmp/project_*.jsonl | tail -50

# Show WARNING and above  
grep '"level":"WARNING"\|"level":"ERROR"\|"level":"CRITICAL"' /tmp/project_*.jsonl | tail -50
```

### 3. Search for Errors and Exceptions
```bash
# Find errors, exceptions, and tracebacks in any log file
grep -iE "error|exception|traceback|failed" /tmp/*.log | tail -50

# Find Python stack traces (multiline)
grep -A 10 "Traceback (most recent call last)" /tmp/*.log
```

## Building Custom Grep Commands

### Basic Structure
```bash
grep [OPTIONS] "PATTERN" /path/to/logs | tail -N
```

### Useful Options
- `-i`: Case-insensitive search
- `-E`: Extended regex (use `|` for OR, `()` for grouping)
- `-A N`: Show N lines after match
- `-B N`: Show N lines before match
- `-C N`: Show N lines before and after match
- `-n`: Show line numbers
- `-c`: Count matches instead of showing them

## Tips for Effective Log Analysis

1. **Start broad, then narrow**: Begin with general error searches, then focus on specific patterns.
2. **Use context lines**: Add `-C 5` to see surrounding context for errors.
3. **Combine filters**: Use pipes to chain grep commands for complex filtering.
4. **Check timestamps**: Correlate errors with specific user actions or time periods.
5. **Follow the flow**: Track a unique ID (like a `flow_id` or `message_id`) through the logs to understand the execution path.