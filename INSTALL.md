# AcademicOps Plugin Installation

Distribution repository: https://github.com/qut-dmrc/aops-dist

Claude Code

```bash
command claude plugin marketplace add qut-dmrc/aops-dist
command claude plugin marketplace update aops && command claude plugin install aops-core@aops
```

Gemini CLI (warning: auto accept flag below, remove --consent if you're concerned)

```bash
command gemini extensions install https://github.com/qut-dmrc/aops-dist.git --auto-update --pre-release --consent
```

Update both:

```bash
command claude plugin marketplace update aops && command claude plugin update aops-core@aops
command gemini extensions uninstall aops-core && command gemini extensions install https://github.com/qut-dmrc/aops-dist.git --auto-update --pre-release --consent
```
