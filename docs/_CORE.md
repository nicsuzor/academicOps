## User Context

- **Nic**: Law professor with ADHD researching tech fairness
- **Needs**: Zero-friction capture, clean task separation, efficient design, concise communication
- **Work Style**: Commitment to highest quality, academic rigor, professional standards
- Name: Nicolas Suzor
- Email: n.suzor@qut.edu.au, nic@suzor.com, nic@suzor.net, nsuzor@osbmember.com
- Affiliations:
  - Professor, Queensland University of Technology (QUT) School of Law and Digital Media Research Centre (DMRC)
  - Chief Investigator, Australian Research Councile (ARC) Centre of Excellence for Automated Decision-Making + Society (ADM+S)
  - Member, Oversight Board (OSB)

## Repository Information

**Owner**: nicsuzor **Primary Repos**:

- Parent repo: `/home/nic/src/writing/` (PRIVATE)
- Agent framework: `nicsuzor/academicOps` (PUBLIC, submodule at `bot/`)
- GitHub issues tracked centrally in `nicsuzor/academicOps`

## Polyrepo Structure

```
/home/nic/src/writing/
├── bot/                    # academicOps (nicsuzor/academicOps)
├── projects/
│   ├── buttermilk/        # Core infrastructure (4 dependents)
│   ├── zotmcp/            # Zotero MCP server
│   ├── osbchatmcp/        # Oversight Board MCP
│   ├── automod/tja        # Trans Journalists Association research project
│   ├── automod/tox        # Toxicity research project
│   ├── dbr/               # Digital Bills of Rights research project
│   ├── mediamarkets/      # Research project
│   └── wikijuris/         # Open textbooks project
└── data/
    ├── goals/
    ├── projects/
    └── tasks/
```

## Cross-Cutting Concerns

**buttermilk**: Shared by 4 projects

- Changes require testing ALL dependents
- Breaking changes require user approval

## Writing Style

When drafting in author's voice:

- Quick reference: `docs/STYLE-QUICK.md`
- Comprehensive: `docs/STYLE.md`
