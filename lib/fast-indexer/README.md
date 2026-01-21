# Fast Graph Indexer for Markdown Links

This is a high-performance Rust tool to generate a graph index JSON file for the Markdown Links VS Code extension.

## Usage

```bash
fast-indexer /path/to/markdown/notes --output graph.json
```

Arguments:
- `ROOT`: The root directory to scan (default: current directory).
- `--output`: The path to the output JSON file (default: `graph.json`).

## Installation

The binary is located in `../bin/fast-indexer` relative to this directory.
You can copy it to your path:

```bash
cp ../bin/fast-indexer ~/.local/bin/
```

## Pre-commit Hook Integration

To ensure your graph index is always up-to-date in your repository, you can use this tool in a Git pre-commit hook.

1. Copy the binary to your repository (e.g., in `scripts/bin/`) or ensure it is installed in your system path.
2. Create `.git/hooks/pre-commit` (or append to it) with the following content:

```bash
#!/bin/bash
# Update graph index before commit

# Adjust path to where you installed the binary
INDEXER="fast-indexer"
OUTPUT="graph.json"

echo "Generating graph index..."
if $INDEXER . --output "$OUTPUT"; then
    echo "Graph index updated."
    git add "$OUTPUT"
else
    echo "Error generating graph index."
    exit 1
fi
```

3. Make the hook executable: `chmod +x .git/hooks/pre-commit`

## VS Code Configuration

In VS Code, configure the Markdown Links extension to use this index:

```json
"markdown-links.indexFile": "/absolute/path/to/your/repo/graph.json"
```

This will bypass the slow startup parsing and load the graph instantly from the index.
