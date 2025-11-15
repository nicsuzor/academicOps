# aOps Installation Guide for New Machines/Repositories

This guide shows you how to install the aOps framework deployment package on a new machine or into a new repository.

## Quick Install (Global Installation)

Install aOps globally so it's available in all Claude Code sessions:

```bash
# 1. Download the latest beta release
cd /tmp
wget https://github.com/nicsuzor/academicOps/releases/download/v1.0.0-beta.20251115.2f3030e/aops-v1.0.0-beta.20251115.2f3030e.tar.gz

# 2. Extract the archive
tar -xzf aops-v1.0.0-beta.20251115.2f3030e.tar.gz
cd aops-v1.0.0-beta.20251115.2f3030e

# 3. Run the setup script (creates global symlinks in ~/.claude/)
bash scripts/setup.sh

# 4. Verify installation
ls -la ~/.claude/
# You should see symlinks to: settings.json, hooks/, skills/, commands/, agents/, CLAUDE.md
```

**What this does:**
- Creates `~/.claude/` directory with symlinks to aOps framework files
- Makes aOps available globally to Claude Code from ANY directory
- Uses symlinks so you can update by re-extracting and re-running setup.sh

---

## Installation Options

### Option 1: Global Installation (Recommended)

**Use case:** You want aOps available everywhere on this machine.

**Location:** Extracts files anywhere (e.g., `~/aops/` or `/opt/aops/`), symlinks from `~/.claude/`

```bash
# Extract to a permanent location
mkdir -p ~/aops
cd ~/aops
tar -xzf /path/to/aops-VERSION.tar.gz
cd aops-VERSION

# Run setup (creates ~/.claude/ symlinks)
bash scripts/setup.sh
```

**Advantages:**
- Available in all repositories and directories
- Single source of truth for aOps configuration
- Easy to update (re-extract and re-run setup.sh)

---

### Option 2: Repository-Specific Installation

**Use case:** You want aOps only for a specific project repository.

**Location:** Extract into your project repository

```bash
# From inside your project repository
cd /path/to/your/project

# Extract aOps
tar -xzf /path/to/aops-VERSION.tar.gz

# Run setup (creates both ~/.claude/ and .claude/ symlinks)
cd aops-VERSION
bash scripts/setup.sh

# The script creates:
# - ~/.claude/ (global symlinks)
# - /path/to/your/project/.claude/ (local symlinks)
```

**Advantages:**
- Keeps aOps with your project
- Can version-control which aOps version your project uses
- Setup script still creates global symlinks as well

---

## Verification

After installation, verify everything is set up correctly:

### Check Global Installation

```bash
# Verify ~/.claude/ directory exists
ls -la ~/.claude/

# Should see symlinks like:
# lrwxrwxrwx  1 user group   XX Nov 16 06:35 settings.json -> /path/to/aops/config/settings.json
# lrwxrwxrwx  1 user group   XX Nov 16 06:35 hooks -> /path/to/aops/hooks
# lrwxrwxrwx  1 user group   XX Nov 16 06:35 skills -> /path/to/aops/skills
# lrwxrwxrwx  1 user group   XX Nov 16 06:35 commands -> /path/to/aops/commands
# lrwxrwxrwx  1 user group   XX Nov 16 06:35 agents -> /path/to/aops/agents
# lrwxrwxrwx  1 user group   XX Nov 16 06:35 CLAUDE.md -> /path/to/aops/CLAUDE.md
```

### Check Repository Installation (if applicable)

```bash
# From inside your project
ls -la .claude/

# Should see relative symlinks like:
# lrwxrwxrwx  1 user group   XX Nov 16 06:35 settings.json -> ../aops-VERSION/config/settings.json
# lrwxrwxrwx  1 user group   XX Nov 16 06:35 hooks -> ../aops-VERSION/hooks
# ... etc
```

### Test in Claude Code

Launch Claude Code from any directory and ask:

```
What aOps skills are available?
```

Claude should respond with information about the available skills (aops, analyst, tasks, etc.)

---

## Downloading Releases

### Latest Beta Release

```bash
# Get the download URL
curl -s https://api.github.com/repos/nicsuzor/academicOps/releases | \
  python3 -c "import sys, json; r = json.load(sys.stdin); print([rel for rel in r if rel['prerelease']][0]['assets'][0]['browser_download_url'])"

# Or manually browse to:
https://github.com/nicsuzor/academicOps/releases
```

### Specific Version

```bash
# Download a specific version
VERSION="v1.0.0-beta.20251115.2f3030e"
wget https://github.com/nicsuzor/academicOps/releases/download/${VERSION}/aops-${VERSION}.tar.gz
```

### Latest Stable Release (when available)

```bash
# Get latest non-beta release
gh release download --repo nicsuzor/academicOps --pattern "aops-*.tar.gz"
```

---

## Package Contents

Each aOps release package contains:

```
aops-VERSION/
├── CLAUDE.md              # Core instructions for Claude
├── README.md              # Framework documentation
├── INSTALL.md             # Installation guide (auto-generated)
├── MANIFEST.json          # Package metadata
│
├── skills/                # Agent skills
│   ├── aops/              # Framework maintenance
│   ├── analyst/           # Data analysis
│   ├── tasks/             # Task management
│   ├── python-dev/        # Python development
│   └── ...
│
├── hooks/                 # Lifecycle automation
│   ├── load_instructions.py
│   ├── validate_tool.py
│   ├── autocommit_tasks.py
│   └── ...
│
├── scripts/               # Utility scripts
│   ├── setup.sh           # Installation script
│   ├── task_add.py
│   └── ...
│
├── config/                # Configuration
│   ├── settings.json      # Claude Code settings
│   └── mcp.json           # MCP server config
│
├── commands/              # Slash commands
│   ├── ttd.md
│   └── err.md
│
├── agents/                # Agent definitions
│   └── DEVELOPER.md
│
└── docs/                  # Documentation
    ├── AXIOMS.md
    └── chunks/
```

---

## Updating to a New Version

To update to a new aOps version:

```bash
# 1. Download new version
cd /tmp
wget https://github.com/nicsuzor/academicOps/releases/download/NEW_VERSION/aops-NEW_VERSION.tar.gz

# 2. Extract to a new location (or same location)
tar -xzf aops-NEW_VERSION.tar.gz
cd aops-NEW_VERSION

# 3. Re-run setup (updates symlinks)
bash scripts/setup.sh

# 4. Old version can be deleted (symlinks now point to new version)
```

**Note:** The setup script automatically updates symlinks, so no manual cleanup is needed.

---

## Uninstallation

To completely remove aOps:

```bash
# Remove global symlinks
rm -rf ~/.claude/settings.json
rm -rf ~/.claude/hooks
rm -rf ~/.claude/skills
rm -rf ~/.claude/commands
rm -rf ~/.claude/agents
rm -rf ~/.claude/CLAUDE.md

# Remove the directory (if you want)
rm -rf ~/.claude

# Remove repository-specific installation (if applicable)
rm -rf /path/to/your/project/.claude

# Remove extracted files
rm -rf ~/aops/aops-VERSION  # or wherever you extracted
```

---

## Troubleshooting

### Problem: Symlinks are broken

**Symptoms:** `ls -la ~/.claude/` shows red/broken symlinks

**Solution:**
```bash
# Re-run setup from the extracted directory
cd /path/to/aops-VERSION
bash scripts/setup.sh
```

### Problem: Skills not loading in Claude Code

**Symptoms:** Claude doesn't recognize aOps skills

**Solution:**
1. Verify symlinks exist: `ls -la ~/.claude/skills`
2. Check Claude Code settings enable skills
3. Restart Claude Code
4. Ask Claude: "List available skills"

### Problem: Hooks not running

**Symptoms:** Automation doesn't work (e.g., no session logging)

**Solution:**
1. Verify hooks symlink: `ls -la ~/.claude/hooks`
2. Check settings.json: `cat ~/.claude/settings.json`
3. Verify hooks are enabled in Claude Code settings
4. Check hook permissions: `ls -la ~/.claude/hooks/*.py`

### Problem: Wrong aOps version active

**Symptoms:** Old version still running after update

**Solution:**
```bash
# Check where symlinks point
readlink -f ~/.claude/skills
readlink -f ~/.claude/hooks

# Re-run setup from new version
cd /path/to/new/aops-VERSION
bash scripts/setup.sh
```

---

## Advanced: Multiple Versions

You can keep multiple aOps versions installed and switch between them:

```bash
# Install multiple versions
~/aops/
├── aops-v1.0.0/
├── aops-v1.1.0/
└── aops-v2.0.0-beta/

# Switch to v1.1.0
cd ~/aops/aops-v1.1.0
bash scripts/setup.sh

# Switch to v2.0.0-beta
cd ~/aops/aops-v2.0.0-beta
bash scripts/setup.sh
```

The setup script updates symlinks to point to whichever version you ran it from.

---

## Support & Issues

- **Repository:** https://github.com/nicsuzor/academicOps
- **Releases:** https://github.com/nicsuzor/academicOps/releases
- **Documentation:** See `docs/` directory in extracted package
- **Core Principles:** See `docs/AXIOMS.md`

---

**Last Updated:** 2025-11-16
**Package Version:** v1.0.0-beta.20251115.2f3030e
