#!/bin/bash
################################################################################
# Git Hooks Installer for academicOps
################################################################################
#
# PURPOSE:
#   Installs git pre-commit hooks that enforce the documentation philosophy:
#   - Documentation should be self-contained in templates, issues, and code
#   - Prevents creating new .md files except for actual research/project content
#   - Promotes self-documenting code with --help flags and inline comments
#
# USAGE:
#   ./scripts/git-hooks/install-hooks.sh [OPTIONS]
#
#   From bot directory:
#     ./scripts/git-hooks/install-hooks.sh
#
#   From parent repo:
#     bot/scripts/git-hooks/install-hooks.sh
#
# OPTIONS:
#   -h, --help       Show this help message and exit
#   -f, --force      Overwrite existing hooks without backup
#
# WHAT IT DOES:
#   1. Detects if running in git repo or submodule
#   2. Finds the correct .git/hooks directory
#   3. Creates pre-commit.d/ directory for hook delegation
#   4. Preserves existing pre-commit hook by moving to pre-commit.d/10-existing.sh
#   5. Installs academicOps hook as pre-commit.d/00-academicops.sh
#   6. Installs delegating pre-commit hook that runs all hooks in order
#
# THE PRE-COMMIT HOOK PREVENTS:
#   - README.md files for scripts (use --help instead)
#   - HOWTO.md files (use issue templates instead)
#   - GUIDE.md files (use code comments instead)
#   - Any system documentation .md files
#
# THE PRE-COMMIT HOOK ALLOWS:
#   - Research papers and manuscripts (papers/ directory)
#   - Project deliverables (actual work product)
#   - Agent instruction files (bot/agents/*.md are executable code)
#
# EXAMPLES:
#   # Standard installation with backup
#   ./scripts/git-hooks/install-hooks.sh
#
#   # Force installation without backup
#   ./scripts/git-hooks/install-hooks.sh --force
#
#   # Show help
#   ./scripts/git-hooks/install-hooks.sh --help
#
# NOTES:
#   - Works with both regular repos and git submodules
#   - Preserves existing hooks by moving to pre-commit.d/ (keeps them functional)
#   - Uses delegation pattern - hooks in pre-commit.d/ run in lexical order
#   - Existing project hooks continue to work alongside academicOps hook
#   - To add more hooks: create executable script in .git/hooks/pre-commit.d/
#
################################################################################

set -e

# Parse command-line arguments
FORCE=false
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            # Extract and display the header comment as help text
            sed -n '2,/^################################################################################$/p' "$0" | sed 's/^# //; s/^#//'
            exit 0
            ;;
        -f|--force)
            FORCE=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Run with --help for usage information"
            exit 1
            ;;
    esac
done

# Detect git directory (handles both regular repos and submodules)
# In submodules, .git is a FILE containing "gitdir: ../../../.git/modules/bot"
# In regular repos, .git is a DIRECTORY
if [ -f .git ]; then
    # Submodule: .git is a file pointing to the real git directory
    GIT_DIR=$(cat .git | sed 's/gitdir: //')
else
    # Regular repo: .git is a directory
    GIT_DIR=".git"
fi

# Construct paths
HOOKS_DIR="$(dirname "$GIT_DIR")/$(basename "$GIT_DIR")/hooks"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Installing git hooks..."
echo "  Hooks directory: $HOOKS_DIR"
echo "  Source directory: $SCRIPT_DIR"

# Create hooks directory if it doesn't exist
mkdir -p "$HOOKS_DIR"

# Create hooks.d directory for hook delegation
HOOKS_D_DIR="$HOOKS_DIR/pre-commit.d"
mkdir -p "$HOOKS_D_DIR"

# Install pre-commit hook using delegation pattern
if [ -f "$HOOKS_DIR/pre-commit" ]; then
    if [ "$FORCE" = true ]; then
        echo "  🔄 Overwriting existing pre-commit hook (--force mode)"
        rm "$HOOKS_DIR/pre-commit"
    else
        # Check if it's already our delegating hook
        if grep -q "Delegating Pre-commit Hook" "$HOOKS_DIR/pre-commit" 2>/dev/null; then
            echo "  ✅ Delegating pre-commit hook already installed"
        else
            # Preserve existing hook by moving to hooks.d
            echo "  ⚠️  Existing pre-commit hook found. Moving to pre-commit.d/10-existing.sh"
            mv "$HOOKS_DIR/pre-commit" "$HOOKS_D_DIR/10-existing.sh"
            chmod +x "$HOOKS_D_DIR/10-existing.sh"
        fi
    fi
fi

# Install academicOps hook in hooks.d directory
echo "  📝 Installing academicOps hook to pre-commit.d/00-academicops.sh"
cp "$SCRIPT_DIR/pre-commit" "$HOOKS_D_DIR/00-academicops.sh"
chmod +x "$HOOKS_D_DIR/00-academicops.sh"

# Install delegating pre-commit hook
if [ ! -f "$HOOKS_DIR/pre-commit" ]; then
    echo "  📝 Installing delegating pre-commit hook"
    cp "$SCRIPT_DIR/pre-commit-delegating" "$HOOKS_DIR/pre-commit"
    chmod +x "$HOOKS_DIR/pre-commit"
fi

echo "  ✅ Pre-commit hook delegation system installed"
echo ""
echo "Git hooks installed successfully!"
echo ""
echo "Hook delegation system:"
echo "  - Main hook: $HOOKS_DIR/pre-commit (delegating script)"
echo "  - Hook directory: $HOOKS_D_DIR/"
echo "  - Hooks run in lexical order (00-, 10-, 20-, etc.)"
echo "  - Existing hooks preserved in pre-commit.d/"
echo ""
echo "The academicOps hook (00-academicops.sh) will:"
echo "  - Detect new .md files being added (except research/project deliverables)"
echo "  - Require explicit confirmation before allowing the commit"
echo "  - Remind you to use self-documenting approaches instead:"
echo "    • Scripts should have --help output"
echo "    • Code should have thorough inline comments"
echo "    • Processes should use issue templates"
echo "    • README files are generally forbidden"
echo ""
echo "To add custom hooks:"
echo "  - Create executable script in $HOOKS_D_DIR/"
echo "  - Use numeric prefix for order (e.g., 20-my-hook.sh)"
echo "  - Exit 0 for success, non-zero for failure"
