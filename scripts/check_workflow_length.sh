#!/usr/bin/env bash
# Pre-commit hook: workflow files must be <= 100 lines (C1 in brain/CONSTRAINTS.md)
MAX=100
rc=0
for f in "$@"; do
  lines=$(wc -l < "$f")
  if [ "$lines" -gt "$MAX" ]; then
    echo "FAIL: $f has $lines lines (max $MAX)"
    rc=1
  fi
done
exit $rc
