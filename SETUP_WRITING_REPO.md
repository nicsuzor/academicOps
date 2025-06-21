# Setting Up Your Private Writing Repository

## Repository Structure Overview

You now have:
- ✅ **`academicOps`** (Public Framework) - Current repository
- ✅ **`@nicsuzor/writing`** (Private Personal Workspace) - Created at https://github.com/nicsuzor/writing

## Setting Up the Writing Repository

### 1. Clone and Initialize Your Writing Repository

```bash
# Clone your private writing repository
git clone git@github.com:nicsuzor/writing.git
cd writing

# Create the recommended directory structure
mkdir -p config projects tools workspace

# Create initial files
touch .env
touch README.md
```

### 2. Add AcademicOps Framework as Submodule

```bash
# Add the academicOps framework as a submodule
git submodule add git@github.com:nicsuzor/academicOps.git framework

# Initialize and update the submodule
git submodule update --init --recursive
```

### 3. Create Your First Research Project

```bash
# Create a new private repository for your first research project
gh repo create nicsuzor/research-project-1 --private --description "Private research project using AcademicOps framework"

# Add it as a submodule to your writing workspace
git submodule add git@github.com:nicsuzor/research-project-1.git projects/research-project-1

# Initialize the project using the framework template
cd projects/research-project-1
../../framework/tools/new-project.sh "Your Research Project Title"
```

### 4. Set Up Your Personal Configuration

Create `config/personal.yml`:

```yaml
# Personal AcademicOps Configuration
author:
  name: "Your Name"
  email: "your.email@university.edu"
  orcid: "0000-0000-0000-0000"
  affiliation: "Your Institution"

# Zotero Integration (via Buttermilk MCP)
zotero:
  library_id: "your_library_id"
  api_key: "stored_in_env"

# Default project settings
defaults:
  citation_style: "apa"
  target_journals: ["Nature", "Science"]
  chunk_size_limit: 1000
  
# AI Assistant Settings
ai:
  model: "claude-sonnet-4"
  integrity_checks: true
  attribution_required: true
```

Create `.env` (NEVER commit this file):

```bash
# Zotero API Key
ZOTERO_API_KEY=your_actual_api_key_here

# Claude API Key (if using direct API)
ANTHROPIC_API_KEY=your_api_key_here

# Other sensitive credentials
ORCID_CLIENT_ID=your_orcid_client_id
ORCID_CLIENT_SECRET=your_orcid_client_secret
```

### 5. Create Personal Automation Scripts

Create `tools/setup-new-project.sh`:

```bash
#!/bin/bash
# Personal script to set up a new research project

PROJECT_NAME="$1"
if [[ -z "$PROJECT_NAME" ]]; then
    echo "Usage: $0 <project-name>"
    exit 1
fi

# Create private repository
gh repo create "nicsuzor/$PROJECT_NAME" --private --description "Research project: $PROJECT_NAME"

# Add as submodule
git submodule add "git@github.com:nicsuzor/$PROJECT_NAME.git" "projects/$PROJECT_NAME"

# Initialize with framework template
cd "projects/$PROJECT_NAME"
"../../framework/tools/new-project.sh" "$PROJECT_NAME"

echo "✅ New project '$PROJECT_NAME' created and configured!"
```

### 6. Commit and Push Initial Setup

```bash
# Add all files
git add .

# Commit initial setup
git commit -m "Initial writing workspace setup with AcademicOps framework

- Add academicOps framework as submodule
- Configure personal settings and credentials
- Set up project automation scripts
- Create secure .env template

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>"

# Push to your private repository
git push -u origin main
```

## Recommended `.gitignore` for Writing Repository

Create `.gitignore`:

```gitignore
# Credentials and secrets
.env
.env.local
.env.production
config/secrets.yml

# Temporary files
*.tmp
*.temp
workspace/drafts/
workspace/temp/

# Personal notes (if you want to keep them private)
notes/personal/
ideas/private/

# OS files
.DS_Store
Thumbs.db

# Editor files
.vscode/settings.json
.idea/
*.swp
*.swo

# Build artifacts
*.pdf
*.docx
*.aux
*.log
*.out
*.toc
```

## Next Steps

1. **Complete GitHub Project Setup**: 
   - Refresh GitHub CLI auth: `gh auth refresh -s project,read:project --hostname github.com`
   - Create project board: `gh project create --title "AcademicOps Development" --owner "@me"`

2. **Configure MCP Integration**:
   - Install Buttermilk MCP connector
   - Set up Zotero integration
   - Test citation retrieval

3. **Start Your First Project**:
   - Use the setup script to create your first research project
   - Follow the CLAUDE.md guidelines for integrity-first writing
   - Begin with small chunks and build iteratively

## Repository Relationships

```
@nicsuzor/writing (Private Personal Workspace)
├── framework/ → academicOps (Public Framework)
├── projects/
│   ├── research-project-1/ → @nicsuzor/research-project-1 (Private)
│   ├── collaborative-paper/ → @shared/collaborative-paper (Shared Private)
│   └── conference-paper/ → @nicsuzor/conference-paper (Private)
├── config/ (Personal configurations)
├── tools/ (Personal automation)
└── workspace/ (Temporary work area)
```

This structure gives you:
- ✅ Secure credential management
- ✅ Flexible project organization  
- ✅ Easy collaboration when needed
- ✅ Clean separation of public framework and private work
- ✅ Version control for everything
- ✅ Scalable for multiple projects

## Security Best Practices

1. **Never commit credentials** to any repository
2. **Use private repositories** for all research content
3. **Share selectively** via collaboration permissions
4. **Regular security audits** of access permissions
5. **Backup strategies** for critical research data

Remember: Your academic integrity and intellectual property are paramount. This structure protects both while leveraging modern development workflows.