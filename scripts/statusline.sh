#!/bin/bash

# Read JSON from stdin (required by Claude Code)
read -r json_input

# Get basic info
user=$(whoami)
host=$(hostname -s)
dir=$(pwd)
dir=${dir/#$HOME/\~}

# Git info
git_info=''
if git rev-parse --git-dir >/dev/null 2>&1; then
    branch=$(git --no-optional-locks symbolic-ref --short HEAD 2>/dev/null || git --no-optional-locks rev-parse --short HEAD 2>/dev/null)
    if ! git --no-optional-locks diff --quiet 2>/dev/null || ! git --no-optional-locks diff --cached --quiet 2>/dev/null; then
        dirty='*'
    else
        dirty=''
    fi
    [ -n "$branch" ] && git_info=$(printf ' \033[38;5;99mon \033[38;5;141m%s%s' "$branch" "$dirty")
fi

# Virtual env info
venv_info=''
[ -n "$VIRTUAL_ENV" ] && venv_info=$(printf ' \033[38;5;45mvia \033[38;5;51m%s' "$(basename "$VIRTUAL_ENV")")

# Output status line (only first line is used)
printf '\033[38;5;244m%s\033[38;5;214m@%s \033[38;5;75min \033[38;5;81m%s%s%s' "$user" "$host" "$dir" "$git_info" "$venv_info"
