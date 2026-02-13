#!/bin/bash
cp scripts/hooks/post-commit .git/hooks/post-commit
chmod +x .git/hooks/post-commit
echo "Post-commit hook installed."
