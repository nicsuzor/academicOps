# AcademicOps Plugin Installation

Distribution repository: https://github.com/nicsuzor/aops

Claude Code

```bash
command claude plugin marketplace add nicsuzor/aops
command claude plugin marketplace update aops && command claude plugin install aops-core@aops
```

Gemini CLI (warning: auto accept flag below, remove --consent if you're concerned)

```bash
command gemini extensions install https://github.com/nicsuzor/aops.git --auto-update --pre-release --consent
```

Update both:

```bash
command claude plugin marketplace update aops && command claude plugin update aops-core@aops
command gemini extensions uninstall aops-core && command gemini extensions install https://github.com/nicsuzor/aops.git --auto-update --pre-release --consent
```

## Polecat Installation

Polecat is the ephemeral worker management system for academicOps. It is distributed as part of the `academicOps` package and provides a console script entry point.

From the repository root, install it as an editable package using `uv`:

```bash
uv pip install -e .
```

_(Note: If you are not in a virtual environment, you may need to use `--system` or install via `uv tool install -e .` depending on your environment setup)._

Once installed, the `polecat` command will be available on your system `PATH`:

```bash
polecat --help
```

You can also run Polecat using module invocation from anywhere on your PATH:

```bash
python -m polecat.cli --help
```
