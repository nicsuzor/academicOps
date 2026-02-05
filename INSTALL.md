# AcademicOps Plugin Installation

Distribution repository: https://github.com/nicsuzor/aops-dist

Claude Code

```bash
command claude plugin marketplace add nicsuzor/aops-dist
command claude plugin marketplace update aops
command claude plugin install aops-core@aops
```

Gemini CLI (warning: auto accept flag below, remove --consent if you're concerned)
```bash
command gemini extensions install git@github.com:nicsuzor/aops-dist.git --consent --auto-update --pre-release 
```
