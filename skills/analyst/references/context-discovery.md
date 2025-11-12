# Context Discovery Reference

Guide to discovering and reading project context before beginning analysis work.

## Why Context Discovery Matters

**CRITICAL FIRST STEP:** Before performing any analysis, understand the project's:

- Research questions and goals
- Data sources and access patterns
- Existing dbt models and analysis work
- Project-specific conventions and rules
- Testing strategy and quality expectations
- Tools and technologies in use

**Without context discovery, you risk:**

- Creating duplicate work
- Violating project conventions
- Misunderstanding research questions
- Querying wrong data sources
- Breaking existing pipelines

## Required Context Files

### 1. Project README Files

**What to read:**

- `README.md` in current working directory
- `README.md` in all parent directories up to project root
- Project root is typically: `papers/[project]/`, `projects/[project]/`, or repository root

**Example discovery path:**

If working in `papers/automod/analysis/`, read:

```
papers/automod/analysis/README.md       (if exists)
papers/automod/README.md                (project root - REQUIRED)
papers/README.md                        (if exists)
README.md                               (repository root)
```

**What to extract:**

- **Research questions**: What is this project investigating?
- **Methodology**: Experimental design, data collection approach
- **Conventions**: Naming patterns, file organization, coding standards
- **Dependencies**: Required tools, packages, external services
- **Project status**: Active development, data collection phase, analysis phase

**Commands:**

```bash
# Find README files in current path
find . -name "README.md" -maxdepth 1

# Find README in parent directories
find .. -name "README.md" -maxdepth 2

# Read project README
cat README.md
```

### 2. Data README

**What to read:**

- `data/README.md` in the project directory
- May also exist in subdirectories: `data/raw/README.md`, `data/processed/README.md`

**What to extract:**

- **Data sources**: Where does data come from? (BigQuery, API, files, manual collection)
- **Schema**: What tables/files exist? What fields do they contain?
- **Access patterns**: How to access data? (Through dbt models, direct queries, file reads)
- **Data dictionary**: Field definitions, value meanings, units
- **Known issues**: Data quality problems, missing data, limitations
- **Update frequency**: How often is data refreshed?

**Commands:**

```bash
# Find data README
ls -la data/README.md

# Read it
cat data/README.md

# List data files to understand structure
ls -lh data/
ls -lh data/raw/
```

### 3. Project Overview

**What to read:**

- `data/projects/[project-name].md` corresponding to current project
- Example: If in `papers/automod/`, read `data/projects/automod.md` or `data/projects/automod-demo.md`

**What to extract:**

- **Strategic context**: Why does this project exist? What's the big picture?
- **Goals and objectives**: What outcomes are expected?
- **Status**: What stage is project in? What's completed? What's in progress?
- **Decisions made**: Important choices about methodology, tools, approach
- **Blockers and issues**: Known problems or challenges
- **Timeline**: Deadlines, milestones

**Commands:**

```bash
# Find project overview files
ls -1 data/projects/*.md

# Search for project name
ls -1 data/projects/ | grep -i "project-keyword"

# Read overview
cat data/projects/project-name.md
```

### 4. Existing dbt Models

**What to read:**

- List all existing models in `dbt/models/`
- Understand staging, intermediate, and mart layers

**What to extract:**

- **Existing models**: What data is already available in dbt?
- **Model purposes**: What does each model do? (Read `dbt/schema.yml`)
- **Data lineage**: How do models depend on each other?
- **Naming patterns**: `stg_*`, `int_*`, `fct_*`, `dim_*` conventions
- **Reusable components**: Can existing models be extended instead of creating new ones?

**Commands:**

```bash
# List all dbt models
ls -1 dbt/models/staging/*.sql
ls -1 dbt/models/intermediate/*.sql
ls -1 dbt/models/marts/*.sql

# Count models by layer
echo "Staging: $(ls -1 dbt/models/staging/*.sql 2>/dev/null | wc -l)"
echo "Intermediate: $(ls -1 dbt/models/intermediate/*.sql 2>/dev/null | wc -l)"
echo "Marts: $(ls -1 dbt/models/marts/*.sql 2>/dev/null | wc -l)"

# Read schema documentation
cat dbt/schema.yml

# View model lineage
dbt docs generate
dbt docs serve  # Opens documentation in browser
```

### 5. Streamlit Apps

**What to read:**

- List existing Streamlit apps in `streamlit/` directory
- Understand what visualizations already exist

**What to extract:**

- **Existing visualizations**: What charts/dashboards exist?
- **Data models used**: Which dbt models do they query?
- **Interaction patterns**: What filters, controls, layouts are used?
- **Conventions**: Code style, organization patterns

**Commands:**

```bash
# List Streamlit apps
ls -1 streamlit/*.py

# Quick preview of what each app does
for file in streamlit/*.py; do
    echo "=== $file ==="
    head -20 "$file" | grep -E "(st.title|st.header|def load)"
done
```

## Context Extraction Process

### Step 1: Automated Discovery

Run these commands to gather context:

```bash
# 1. Find and read project READMEs
echo "=== Project README ==="
cat README.md 2>/dev/null || echo "No README in current dir"

# 2. Find and read data README
echo -e "\n=== Data README ==="
cat data/README.md 2>/dev/null || echo "No data README"

# 3. List existing dbt models
echo -e "\n=== Existing dbt Models ==="
echo "Staging: $(ls -1 dbt/models/staging/*.sql 2>/dev/null | wc -l)"
echo "Intermediate: $(ls -1 dbt/models/intermediate/*.sql 2>/dev/null | wc -l)"
echo "Marts: $(ls -1 dbt/models/marts/*.sql 2>/dev/null | wc -l)"
ls -1 dbt/models/**/*.sql 2>/dev/null | head -20

# 4. List Streamlit apps
echo -e "\n=== Streamlit Apps ==="
ls -1 streamlit/*.py 2>/dev/null || echo "No Streamlit apps"

# 5. Check for project overview
echo -e "\n=== Project Overview ==="
ls -1 data/projects/*.md 2>/dev/null || echo "No project overviews"
```

### Step 2: Manual Review

After gathering files, read them carefully and extract:

1. **Research questions** - What is being studied?
2. **Data sources** - Where does data come from?
3. **Existing models** - What dbt models exist? Can they be reused?
4. **Conventions** - Naming, coding standards, project-specific rules
5. **Tools** - DuckDB? PostgreSQL? Specific packages?
6. **Quality expectations** - What tests exist? What's the testing strategy?

### Step 3: Summarize to User

After context discovery, provide a concise summary:

**Template:**

```
I've reviewed the project context:

**Project:** [Project name and purpose]
**Research Questions:** [1-2 key questions being investigated]
**Data Sources:** [Where data comes from]
**Existing Work:**
  - [N] staging models
  - [M] mart models
  - [K] Streamlit dashboards

**Key Conventions:**
  - [Convention 1]
  - [Convention 2]

**Tools:** [Database, packages, frameworks]

What would you like me to help with?
```

**Example:**

```
I've reviewed the project context:

**Project:** Automod Analysis - Studying automated content moderation patterns
**Research Questions:** How do different platforms handle automated content removal? What factors predict automated takedowns?
**Data Sources:** BigQuery (platform API exports), accessed through dbt models
**Existing Work:**
  - 12 staging models (stg_youtube_videos, stg_twitter_tweets, etc.)
  - 5 mart models (fct_content_removals, dim_platforms, etc.)
  - 2 Streamlit dashboards (overview.py, trends.py)

**Key Conventions:**
  - All data access through dbt models (no direct BigQuery queries)
  - Tests required for all new models
  - Use DuckDB for local analysis

**Tools:** DuckDB, dbt, Streamlit, Plotly

What would you like me to help with?
```

## Common Context Discovery Patterns

### Pattern 1: New Project (No Existing Infrastructure)

**Indicators:**

- No `dbt/` directory
- No `README.md` in current directory
- Empty or minimal `data/` directory

**Action:**

1. Ask user: "This appears to be a new project. Should I help set up the dbt infrastructure?"
2. If yes, create basic structure:
   - `dbt/models/staging/`
   - `dbt/models/marts/`
   - `dbt/schema.yml`
   - `README.md` template
3. Document decisions as you go

### Pattern 2: Established Project (Mature Infrastructure)

**Indicators:**

- Many dbt models exist
- Comprehensive `README.md`
- Multiple Streamlit apps
- Extensive tests

**Action:**

1. Thoroughly review existing models to avoid duplication
2. Understand established conventions
3. Extend existing work rather than creating new
4. Follow existing patterns for new additions

### Pattern 3: In-Transition Project (Partially Migrated)

**Indicators:**

- Mix of old scripts and new dbt models
- Some data access through dbt, some direct queries
- Documentation incomplete

**Action:**

1. Identify which patterns are "old" vs "new"
2. Ask user: "I see both old and new patterns. Should I follow the newer dbt-based approach?"
3. Help migrate old patterns to new infrastructure if requested
4. Document the migration for clarity

## Context Discovery Anti-Patterns

**❌ Don't:**

- Skip context discovery and jump straight to analysis
- Assume project structure without checking
- Create new models without checking for duplicates
- Ignore existing conventions and impose your own
- Query upstream data sources without checking dbt models first

**✅ Do:**

- Always start with context discovery
- Read all required context files
- Check for existing work before creating new
- Follow project conventions
- Ask user for clarification when context is unclear

## Quick Reference Commands

```bash
# Full context discovery in one script
cat << 'DISCOVERY_SCRIPT' > /tmp/discover_context.sh
#!/bin/bash
echo "=== PROJECT CONTEXT DISCOVERY ==="
echo ""
echo "1. Project README:"
cat README.md 2>/dev/null || echo "  (not found)"
echo ""
echo "2. Data README:"
cat data/README.md 2>/dev/null || echo "  (not found)"
echo ""
echo "3. DBT Models:"
echo "  Staging: $(ls -1 dbt/models/staging/*.sql 2>/dev/null | wc -l)"
echo "  Intermediate: $(ls -1 dbt/models/intermediate/*.sql 2>/dev/null | wc -l)"
echo "  Marts: $(ls -1 dbt/models/marts/*.sql 2>/dev/null | wc -l)"
echo ""
echo "4. Streamlit Apps:"
ls -1 streamlit/*.py 2>/dev/null || echo "  (none)"
echo ""
echo "5. Project Overviews:"
ls -1 data/projects/*.md 2>/dev/null || echo "  (none)"
DISCOVERY_SCRIPT

chmod +x /tmp/discover_context.sh
/tmp/discover_context.sh
```

## References

- academicOps methodology: Focus on reproducible, self-documenting research
- dbt documentation patterns: See `references/dbt-workflow.md`
- Project structure standards: See main project `README.md`
