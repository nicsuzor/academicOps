# Manifest for aops-core and aops-tools generation

MANIFEST = [
    # ── aops-core agents ───────────────────────────────────────────────
    {
        "src_glob": "aops-core/agents/*.md",
        "transforms": ["claude_agent_schema", "translate_tool_calls_claude"],
        "runtimes": ["claude"],
    },
    {
        "src_glob": "aops-core/agents/*.md",
        "transforms": ["gemini_agent_schema", "translate_tool_calls_gemini"],
        "runtimes": ["gemini"],
    },
    # ── aops-tools agents ──────────────────────────────────────────────
    {
        "src_glob": "aops-tools/agents/*.md",
        "transforms": ["claude_agent_schema", "translate_tool_calls_claude"],
        "runtimes": ["claude"],
    },
    {
        "src_glob": "aops-tools/agents/*.md",
        "transforms": ["gemini_agent_schema", "translate_tool_calls_gemini"],
        "runtimes": ["gemini"],
    },
    # ── general markdown translation for Gemini ────────────────────────
    # Claude gets these unchanged
    {
        "src_glob": "aops-core/**/*.md",
        "exclude": ["aops-core/agents/*.md", "aops-core/PATHS.md"],
        "transforms": ["translate_tool_calls_gemini"],
        "runtimes": ["gemini"],
    },
    {
        "src_glob": "aops-tools/**/*.md",
        "exclude": ["aops-tools/agents/*.md", "aops-tools/PATHS.md"],
        "transforms": ["translate_tool_calls_gemini"],
        "runtimes": ["gemini"],
    },
    # ── Hooks ──────────────────────────────────────────────────────────
    {
        "src_glob": "aops-core/hooks/hooks.json",
        "transforms": ["gemini_hooks"],
        "runtimes": ["gemini"],
    },
    {
        "src_glob": "aops-core/hooks/hooks.json",
        "transforms": [],
        "runtimes": ["claude"],
    },
    # ── Catch-all copy for everything else ─────────────────────────────
    {
        "src_glob": "aops-core/**/*",
        "exclude": [
            "aops-core/agents/*.md",
            "aops-core/**/*.md",
            "aops-core/hooks/hooks.json",
            "aops-core/**/__pycache__/*",
            "aops-core/pyproject.toml",
            "aops-core/indices/*",
            "aops-core/.*", # .mcp.json etc
        ],
        "transforms": [],
        "runtimes": ["gemini", "claude"],
    },
    {
        "src_glob": "aops-tools/**/*",
        "exclude": [
            "aops-tools/agents/*.md",
            "aops-tools/**/*.md",
            "aops-tools/**/__pycache__/*",
            "aops-tools/pyproject.toml",
            "aops-tools/indices/*",
            "aops-tools/.*",
        ],
        "transforms": [],
        "runtimes": ["gemini", "claude"],
    },
]

# Additional metadata generated at build time (e.g., pyproject.toml) is handled
# by specific metadata steps in the generator engine.
