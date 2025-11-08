# The Complete Guide to Structuring Claude Skill Prompts

**Claude Skills are specialized instruction folders that extend Claude's capabilities through progressive disclosure, not executable code**. The description field determines skill invocation through pure LLM reasoning, while SKILL.md provides procedural knowledge that transforms Claude from generalist to specialist. Success hinges on understanding this is prompt engineering at scale, not traditional programming.

Skills operate through a three-level loading system: metadata consumes just 30-50 tokens at startup, full SKILL.md loads only when invoked (500-5,000 tokens), and bundled resources load on-demand. This architecture enables hundreds of skills without context bloat. The difference between a skill that works reliably versus one that never triggers comes down to mastering these seven core principles.

## 1. Essential information for skill prompts

Every skill requires two components: YAML frontmatter for discovery and markdown content for execution. The frontmatter serves as Claude's decision mechanism—if this metadata fails, your skill becomes invisible regardless of content quality.

**Required frontmatter fields** establish identity and invocation criteria. The name field must use lowercase hyphen-case (analyzing-spreadsheets not spreadsheet_analyzer), limited to 64 characters. Choose gerund forms (verb + -ing) for clarity about function. The description field, limited to 1024 characters, represents your most critical decision—this single field determines whether Claude ever loads your skill. Write in third person only, combining what the skill does with explicit when-to-use triggers. Invalid example: "You can use this to process Excel files." Valid example: "Analyze Excel spreadsheets, create pivot tables, generate charts. Use when analyzing Excel files, spreadsheets, tabular data, or .xlsx files."

**Optional frontmatter enhances control** over execution environment. The allowed-tools field pre-approves specific tools, eliminating user permission prompts during skill execution. Use comma-separated strings with optional wildcards: "Read,Write,Bash(git:*)" grants file operations and scoped git commands. The model field specifies which Claude version to use, either explicit like "claude-opus-4-20250514" or "inherit" for the session's current model. The version field enables tracking iterations, while license references external licensing terms.

**SKILL.md content structure** should follow a consistent pattern optimized for Claude's consumption. Begin with a brief one-to-two sentence purpose statement, followed by an Overview section explaining what the skill provides and when to use it. Include Prerequisites for required tools, files, or context. The Instructions section forms the core, breaking workflows into numbered steps with imperative language. Add sections for Output Format, Error Handling, concrete Examples, and Resources that reference bundled files. This structure creates scannable, logical flow that Claude parses efficiently.

**Progressive disclosure governs information architecture**. Keep SKILL.md under 500 lines (approximately 5,000 words) by moving detailed content to the references directory. Core procedural instructions belong in SKILL.md; comprehensive API documentation, detailed examples, and domain-specific guides move to separate reference files. This separation prevents context window bloat while maintaining discoverability. Reference files should stay one level deep—avoid chains where SKILL.md references main.md which references advanced.md which references detailed.md.

**The frontmatter example** from Anthropic's skill-creator demonstrates best practices:

```yaml
---
name: skill-creator
description: Guide for creating effective skills. This skill should be used when users want to create a new skill (or update an existing skill) that extends Claude's capabilities with specialized knowledge, workflows, or tool integrations.
allowed-tools: "Read,Write,Bash,Glob,Grep,Edit"
version: 1.0.0
---
```

## 2. Ensuring proper skill invocation

**The description field uses pure LLM reasoning, not algorithmic matching**. When Claude receives a request, all skill descriptions appear in the Skill tool's context as formatted text. Claude reads these descriptions and uses natural language understanding to match user intent against available skills. No embeddings, no classifiers, no pattern matching—just the model's forward pass through the transformer deciding "this user request matches that skill description."

**Effective descriptions combine action and context** using a proven formula: [What it does]. Use when [specific trigger 1], [trigger 2], or when user mentions [keywords]. The PDF skill demonstrates this: "Comprehensive PDF manipulation toolkit for extracting text and tables, creating new PDFs, merging/splitting documents, and handling forms. When Claude needs to fill in a PDF form or programmatically process, generate, or analyze PDF documents at scale." This pattern gives Claude clear matching criteria across multiple phrasings.

**Include specific trigger keywords** that match natural user language. For Excel skills, embed terms like "Excel," "spreadsheets," "tabular data," ".xlsx files." For git skills, include "commit messages," "git diffs," "staged changes." These keywords create multiple entry points for skill invocation. Technology-specific triggers work particularly well: "Use when using React Router and handling authentication redirects" versus the vague "Use for routing."

**Avoid mega-skills by maintaining narrow scope**. Creating one presentation skill that handles "presentations, brand guidelines, design templates, and data visualization" creates router confusion. Instead, split into focused skills: one for pitch deck presentations with narrative structure, another for brand guideline application, a third for data-heavy slides with charts. Claude automatically composes multiple skills when needed, but each must have distinctive trigger language to avoid overlap.

**Test invocation systematically** using the Claude A/B method. Claude A helps design the skill, capturing successful approaches into SKILL.md. Claude B tests the skill in fresh sessions on similar tasks, revealing whether descriptions provide sufficient routing signal. Watch Claude's thinking trace for skill loading confirmation: you should see "The 'skill-name' skill is loading" messages. If these don't appear when expected, the description lacks sufficient trigger specificity.

**Common invocation failures** stem from predictable causes. Code execution not being enabled represents the most common silent failure—the skill uploads successfully and appears in the library but never triggers. Description vagueness, overlapping skills with similar domain language, point-of-view inconsistencies (using "I" or "you"), and missing "when to use" context all prevent reliable invocation. The debugging checklist starts with verifying code execution is enabled in Settings → Capabilities, then validates description specificity, third-person point of view, trigger keyword presence, and YAML frontmatter validity.

**Negative examples prevent false positives** when multiple skills share adjacent domains. For a financial Excel skill, specify: "Process Excel files for financial analysis. Use for financial models, accounting data, budgets. Do not use for sales reports, CRM data, or general spreadsheet creation." This explicit boundary helps the router distinguish between similar skills.

## 3. Linking references within and outside skill directories

**The three-directory structure** organizes bundled resources by function. The scripts directory contains executable code (Python, Bash, JavaScript) for deterministic operations. The references directory holds documentation intended for loading into Claude's context. The assets directory stores templates and binary files referenced by path but never loaded into context. This distinction matters for token efficiency—references consume context tokens when read, assets do not.

**Path references use the baseDir variable** for portability across environments. Always write `{baseDir}/references/advanced.md` never `/home/user/.claude/skills/my-skill/references/advanced.md`. When the skill invokes, Claude receives access to tools specified in allowed-tools, and the base directory path resolves automatically. This makes skills portable across user configurations, project directories, and different installations.

**Direct reference patterns** provide clear signposting from SKILL.md to supporting files. Use explicit instructions: "For advanced PDF features, see {baseDir}/references/advanced.md" or "For form filling specifically, read {baseDir}/references/forms.md." When Claude encounters these instructions, it uses the Read tool to load referenced content into context, accessing detailed information only when the workflow requires it.

**Conditional loading patterns** prevent unnecessary context consumption. Structure SKILL.md with basic instructions followed by conditional references: "If you need advanced features like image manipulation, custom rendering, or JavaScript-based PDFs, read {baseDir}/references/advanced.md for detailed documentation." This approach keeps common use cases lean while making advanced features discoverable.

**Domain-specific organization** works well for skills with multiple specializations. A database query skill might organize as: "For sales metrics queries: Read {baseDir}/references/sales_schema.md. For finance data: Read {baseDir}/references/finance_schema.md. For product analytics: Read {baseDir}/references/product_schema.md." This prevents loading irrelevant schemas into context while maintaining clear navigation.

**Reference file best practices** maintain usability as files grow. Keep references one level deep from SKILL.md—no nested reference chains. Include table of contents for files exceeding 100 lines. Use descriptive filenames like form_validation_rules.md not doc2.md. Organize by domain or feature for large skills. The PDF skill demonstrates this with SKILL.md for core operations, forms.md for form-filling workflows, and reference.md for advanced features and JavaScript libraries.

**External references** outside the skill directory require different handling. Skills cannot directly reference files outside their directory structure. For external data sources, documentation, or APIs, use two strategies. First, include documentation URLs in SKILL.md instructions: "Use WebFetch to load the Python SDK documentation from https://raw.githubusercontent.com/modelcontextprotocol/python-sdk/main/README.md." Second, for frequently-accessed external resources, copy relevant documentation into the references directory during skill packaging, ensuring all required information bundles with the skill.

**Asset references for templates** use path-only notation since assets never load into context. In SKILL.md: "Use the template at {baseDir}/assets/report-template.html as the report structure" or "Copy boilerplate from {baseDir}/assets/frontend-template/." Claude sees the file path and manipulates assets by copying, filling placeholders, or referencing in generated output, but never reads content into its context window.

## 4. When to create scripts for skills

**Scripts offload deterministic operations** where precision matters more than flexibility. Create scripts for complex multi-step operations requiring specific logic better expressed in code than natural language, for repeated operations that would otherwise require Claude to regenerate code each time, and for error-prone tasks needing explicit error handling. The PDF skill demonstrates this pattern with scripts for checking fillable fields, filling PDF form fields, converting PDFs to images, and extracting form field metadata—operations requiring reliable binary format handling.

**Use instructions for judgment, code for precision**. Workflow guidance, decision-making frameworks, analysis approaches, and creative tasks belong in SKILL.md instructions where Claude applies reasoning. Data transformations with specific algorithms, validation logic with precise rules, API interactions with exact parameter requirements, and operations with strict output formatting belong in scripts. The XLSX skill includes a recalculation script for Excel formulas using LibreOffice—deterministic math better handled by executable code than natural language generation.

**Script integration patterns** connect SKILL.md instructions to executable code through clear conventions. Direct execution pattern: "Run the validation script: python {baseDir}/scripts/validate.py \u003cinput_file\u003e." Conditional execution: "First check if PDF has fillable fields: python scripts/check_fillable_fields.py \u003cfile.pdf\u003e. If fillable fields exist, use fill_fillable_fields.py. Otherwise, follow the non-fillable workflow." Pipeline execution chains scripts sequentially: "Convert PDF to images, extract field info, validate bounding boxes, fill form with validated data."

**Programming language selection** depends on task requirements and environment constraints. Python dominates document skills (pdf, docx, xlsx, pptx) due to rich libraries for binary format handling. Bash suits system operations and command chaining. JavaScript with Node.js enables web-based operations, demonstrated in the algorithmic-art skill using p5.js and the webapp-testing skill using Playwright. All three languages work across Claude.ai, Claude Code, and API implementations, though package installation differs by environment.

**Package dependency handling** varies by deployment context. Claude.ai and Claude Code can install packages from npm and PyPI, pulling from GitHub repositories as needed. The Anthropic API has no network access and no runtime package installation—all dependencies must pre-package in the container. Document this clearly in SKILL.md: list required packages in a Dependencies section, specify minimum versions, and note any environment-specific limitations.

**Script best practices** ensure reliability and maintainability. Handle errors explicitly rather than delegating to Claude—scripts should return clear error messages with actionable guidance. Use the {baseDir} variable for all skill-relative paths, never hardcode absolute paths that break portability. Create verifiable intermediate outputs like plan.json files before execution, enabling validation steps. Provide clear documentation in script docstrings explaining purpose, parameters, return values, and error conditions. Avoid "voodoo constants"—magic numbers need justification in comments.

**The init_skill.py example** from skill-creator demonstrates proper error handling:

```python
def init_skill(skill_name, path):
    """Initialize a new skill directory with template SKILL.md."""
    skill_dir = Path(path).resolve() / skill_name

    if skill_dir.exists():
        print(f"❌ Error: Skill directory already exists: {skill_dir}")
        return None

    try:
        skill_dir.mkdir(parents=True, exist_ok=False)
        print(f"✅ Created skill directory: {skill_dir}")
    except Exception as e:
        print(f"❌ Error creating directory: {e}")
        return None
```

**Avoid scripts for simple operations** that Claude handles naturally. Don't create a script for basic file concatenation, simple text transformations, or standard API calls with minimal logic. Reserve scripts for operations where code precision demonstrably outperforms natural language generation or where reliability requirements exceed LLM consistency.

## 5. Permissions and capabilities in skills

**The allowed-tools field pre-approves specific tools** without requiring user permission prompts during skill execution. When Claude invokes a skill with allowed-tools specified, the system modifies the execution context by adding those tools to the always-allow rules. This modification remains scoped to the skill's execution—once the skill completes, permissions revert to normal. This temporary privilege escalation enables seamless workflows while maintaining security boundaries.

**Common tool types** cover file operations, execution, and specialized capabilities. File operations include Read (read file contents), Write (create/overwrite files), Edit (modify existing files), Glob (find files by pattern), and Grep (search within files). Execution tools include Bash for shell commands and scoped variants like Bash(command:*) restricting to specific command families. Other capabilities include WebSearch for internet queries, Task for creating subtasks, and Agent for spawning sub-agents, though these require careful justification.

**Permission scoping patterns** balance capability against security risk. Basic file operations use "Read,Write" for skills that only need to read and write files. File operations plus search expand to "Read,Write,Grep,Glob" for skills requiring codebase search or file pattern matching. Scoped Bash commands use "Bash(git:_),Read,Grep" to allow only git operations, or "Bash(npm:_)" for npm commands. Very specific patterns like "Bash(git status:_),Bash(git diff:_),Read" restrict to individual git subcommands. Comprehensive access like "Read,Write,Bash,Glob,Grep,Edit" suits meta-skills like skill-creator that require broad capabilities for their core function.

**Security considerations follow the principle of least privilege**. Start with minimal permissions, adding only as required by actual skill functionality. Use wildcards carefully—"Bash(git:*)" scopes to git commands while bare "Bash" grants unrestricted shell access. Validate scripts before giving execution permission, auditing code for security vulnerabilities or unintended side effects. Document rationale for each tool, explaining why the skill needs specific permissions.

**Real examples** from Anthropic's skills repository demonstrate appropriate scoping. The skill-creator uses "Read,Write,Bash,Glob,Grep,Edit" because creating skills requires reading templates, writing SKILL.md files, executing validation scripts, searching for files, and editing existing skills. Code reviewer skills use "Read,Grep,Glob" for read-only access ensuring safe analysis without modification capability. Safe file reader skills explicitly restrict to "Read,Grep,Glob" for security-conscious environments.

**Permission behavior** creates different user experiences. With allowed-tools specified, Claude uses approved tools immediately without prompting. Without allowed-tools, the system prompts "Claude wants to use Bash tool. Allow?" before each tool use, requiring manual approval. This difference profoundly impacts skill usability—workflows requiring multiple tool invocations become tedious without pre-approval, while unnecessary permissions create security exposure.

**Model overrides** extend permissions to computational resources. Skills can specify model selection in frontmatter: "model: claude-opus-4-20250514" requests a specific model regardless of session default, while "model: inherit" uses the current session model. This enables skills with complex reasoning requirements to request more capable models, or skills optimizing for speed to request faster variants. The model override applies only during skill execution, reverting afterward.

**The execution context modification** happens programmatically when skills load. The system injects allowed tools into the permission context, adding them to always-allow rules that bypass normal permission checks. This modification creates a temporary elevated privilege environment scoped to skill execution. Understanding this mechanism clarifies why allowed-tools must be chosen carefully—these permissions grant Claude direct capability to execute operations within the skill's scope.

## 6. Phrasing instructions in skills

**Imperative language creates the clearest instructions**. Use verb-first commands: "Analyze code for security vulnerabilities," "Extract text from PDF files," "Generate descriptive commit messages." Avoid second-person constructions: not "You should analyze code" but "Analyze code." This imperative form matches how Claude processes procedural instructions, creating direct, actionable guidance without conversational overhead.

**Consistent terminology prevents confusion**. Throughout a skill, use identical terms for identical concepts. If you call something "extract" in one section, don't switch to "pull," "get," or "retrieve" in other sections. The PDF skill consistently uses "extract" for text retrieval, "fill" for form field population, "merge" for document combination. This consistency helps Claude maintain coherent mental models of skill capabilities.

**Objective instructional language** works better than conversational tone. Write "To accomplish X, do Y" rather than "If you need to do X, try doing Y." Omit hedging words like "possibly," "perhaps," "maybe" unless genuine uncertainty exists. State procedures directly: "Read the input file using the Read tool. Parse content according to the JSON schema. Transform data following specifications. Write output using the Write tool."

**Structured workflows with numbered steps** create scannable, sequential procedures. Break complex operations into discrete steps with clear boundaries:

```markdown
### Step 1: Validate Input

Check that input file exists and matches expected format.

### Step 2: Extract Data

Parse input according to schema, handling edge cases.

### Step 3: Transform

Apply business logic transformations to extracted data.

### Step 4: Write Output

Generate output file with transformed data.
```

**Templates for strict requirements** ensure consistent outputs. When specific formatting matters, provide exact templates:

```markdown
ALWAYS use this exact structure:

# [Analysis Title]

## Executive Summary

[One-paragraph overview]

## Key Findings

- Finding 1 with supporting data
- Finding 2 with supporting data
```

For flexible guidance, preface templates with: "Here is a sensible default format, but use your best judgment to adapt based on context."

**Assume Claude's intelligence** to avoid bloating instructions with common knowledge. Don't explain that JSON stands for JavaScript Object Notation or that Excel uses .xlsx extensions. Write "Validate input JSON before processing" not "You need to validate that the input is a valid JSON file. JSON stands for JavaScript Object Notation and is a data interchange format..." The skill-creator documentation emphasizes: "Every token in your skill's definition competes for space with system prompt, chat history, and other skills. Assume Claude's intelligence."

**Concrete examples** clarify abstract instructions. After explaining a workflow step, provide specific instances:

```markdown
## Workflow Step

Extract form field values from the PDF structure.

Example: Given a form with fields "firstName", "lastName", "email", extract each field's value and data type: { "firstName": {"value": "John", "type": "text"}, "lastName": {"value": "Doe", "type": "text"}, "email": {"value": "john@example.com", "type": "text"} }
```

**Error handling instructions** prevent Claude from getting stuck on failures. Specify what to do when operations fail:

```markdown
## Error Handling

If PDF has no fillable fields:

- Inform user that form filling isn't possible
- Offer text extraction as alternative
- Provide instructions for creating fillable PDF

If PDF is encrypted:

- Request password from user
- Attempt decryption with provided password
- Exit gracefully if decryption fails
```

**Avoid overwhelming with options**. Present sensible defaults rather than exhaustive lists of every possible parameter. Make validation scripts verbose with specific error messages, but keep main instructions focused on the primary workflow. If advanced options exist, link to references: "For advanced rendering options, see {baseDir}/references/advanced_rendering.md."

## 7. Optimal detail levels in skill prompts

**The 500-line guideline** provides practical boundaries for SKILL.md length. Approximately 500 lines (roughly 5,000 words) represents the practical upper limit before skill prompts overwhelm context windows and dilute focus. Content approaching this threshold signals the need to extract material into references directory files. The PDF skill demonstrates effective splitting: core operations in SKILL.md stay lean at around 300 lines, while forms.md and reference.md handle specialized topics.

**Progressive disclosure architecture** governs detail distribution across the three-level system. Level 1 metadata (name plus description in frontmatter) consumes 50-100 tokens per skill, always loaded at startup across all available skills. Level 2 SKILL.md content uses 500-5,000 tokens, loading only when Claude invokes the skill. Level 3 bundled resources (references, scripts, assets) consume tokens only when explicitly accessed. This architecture allows a skill library of 100+ skills while maintaining responsive performance.

**Balance detail against focus**. Too little detail creates skills that require excessive user guidance, defeating the purpose of packaging expertise. Too much detail bloats context, slows processing, and buries critical information in noise. The optimal balance provides just enough procedural guidance for Claude to execute workflows independently while using references for deep dives into complex scenarios.

**When to split content** follows clear patterns. Keep core workflow instructions, essential prerequisites, primary tool usage, and common examples in SKILL.md. Move comprehensive API documentation, detailed examples for edge cases, domain-specific deep dives, and troubleshooting guides to reference files. The mcp-creator skill demonstrates this: SKILL.md covers the creation workflow in 400 lines, while references/mcp_best_practices.md, references/python_mcp_server.md, and references/node_mcp_server.md provide language-specific implementation details accessed only when relevant.

**Table of contents patterns** help Claude navigate large reference files. For any reference file exceeding 100 lines, include a structured table of contents at the top:

```markdown
# Advanced PDF Processing Reference

## Contents

1. [Image Manipulation](#image-manipulation)
2. [pypdfium2 Library](#pypdfium2)
3. [JavaScript Libraries](#javascript-libraries)
4. [Custom Rendering](#custom-rendering)

## Image Manipulation

[Detailed content...]
```

**Duplication wastes tokens**. Information should exist in exactly one location within the skill. If basic PDF extraction appears in SKILL.md, don't repeat it in reference.md. Instead, SKILL.md provides the procedure while reference.md expands on advanced cases not covered in the basic workflow. Maintaining this separation requires discipline during skill authoring but pays dividends in context efficiency.

**Domain expertise density** varies by skill purpose. A brand guidelines skill might contain substantial detail about exact color values (#FF6B35 Coral, #004E89 Navy Blue), typography specifications (Montserrat Bold for headers, 32pt H1), and logo usage rules (0.5 inch minimum spacing). This dense specification provides value because consistency requirements demand precision. Conversely, a code review skill might include lightweight heuristics about what to look for, trusting Claude's reasoning to analyze specific code patterns.

**Examples balance comprehensiveness with conciseness**. Include 2-3 concrete examples demonstrating typical usage patterns, not 20 variations covering every edge case. The goal is establishing pattern recognition, not exhaustive documentation:

```markdown
## Examples

### Example 1: Simple Text Extraction

Input: Extract text from report.pdf Output: All text content from all pages

### Example 2: Form Filling

Input: Fill form.pdf with data from data.json Output: Completed form saved as output.pdf
```

**Avoid time-sensitive information** in skills meant for long-term use. Don't include "as of October 2024" or "the latest version is 3.2.1" in SKILL.md. These details create maintenance burden and become outdated quickly. Instead reference current documentation: "Check the official pandas documentation for current API details" or make version-agnostic statements: "Use the latest stable pandas version."

**Testing reveals optimal detail levels**. The Claude A/B testing method provides empirical feedback. If Claude B (fresh instance) repeatedly requests information that should be in the skill, add more detail. If Claude B ignores sections of the skill or never accesses certain reference files, remove excess detail. Iterate toward the minimum sufficient detail level where Claude executes workflows successfully without excessive guidance.

**Context management strategy** treats token budget as a shared resource. Your skill competes with system prompts, chat history, and other skills for context window space. A skill consuming 6,000 tokens for comprehensive coverage might work in isolation but fails when Claude loads three skills simultaneously. Keeping individual skills under 500 lines ensures multiple skills can compose effectively without context exhaustion.

## Validation and packaging

Skills require validation before distribution to ensure they meet structural requirements and function as expected. Anthropic provides validation scripts in the skill-creator that check for SKILL.md existence, valid YAML frontmatter format, required name and description fields, proper naming conventions, and absence of prohibited characters in descriptions.

The packaging process automatically validates skills before creating distributable ZIP files. Use scripts/package_skill.py \u003cpath/to/skill-folder\u003e to generate properly structured archives. The script validates structure, packages all files maintaining directory hierarchy, names the ZIP after the skill, and reports validation errors requiring fixes before successful packaging.

Testing methodology follows the systematic Claude A/B pattern. Work with Claude A to develop the skill, capturing successful approaches into SKILL.md. Test with Claude B in fresh sessions using multiple prompt phrasings to verify invocation triggers reliably. Review Claude's thinking traces to confirm skill loading when expected. Iterate on description if invocation fails, focusing on trigger specificity and keyword inclusion.

The official Anthropic skills repository at github.com/anthropics/skills provides reference implementations demonstrating these principles in practice. Study the document skills (pdf, docx, xlsx, pptx) for script integration patterns, skill-creator for meta-skill workflows, algorithmic-art for template-based generation, and brand-guidelines for specification-heavy skills. These examples provide concrete models for structuring your own skills following proven patterns.
