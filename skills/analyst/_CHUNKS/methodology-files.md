# METHODOLOGY.md Files

## What is a Methodology?

**Methodology** (singular) is the overarching research design and epistemological approach for your entire project. It answers:

- **What is your research question?**
- **Why is this question important?**
- **What is your theoretical framework?**
- **What type of research design are you using?** (experimental, observational, mixed-methods, etc.)
- **What are your dependent and independent variables?**
- **What is your unit of analysis?**
- **How will you measure outcomes?**
- **What are the limitations of your approach?**
- **What alternative approaches did you consider and why did you reject them?**

Methodology is about **research design and justification**, not technical implementation.

## METHODOLOGY.md Structure

Every research project MUST have a `METHODOLOGY.md` file at project root with this structure:

```markdown
# Methodology: [Project Name]

## Research Questions

[Primary research question and sub-questions]

## Theoretical Framework

[What existing literature/theory informs this work?]

## Research Design

[Experimental, observational, mixed-methods, etc.]

### Variables

**Dependent variable(s)**: [What you're measuring]

**Independent variable(s)**: [What you're manipulating or examining]

**Control variables**: [What you're holding constant or controlling for]

### Unit of Analysis

[What is being studied? Cases, users, time periods, etc.]

## Data Sources

[Overview of data sources - details go in data/README.md]

## Measurement Strategy

[How you operationalize your theoretical constructs]

### Example:
If studying "content moderation effectiveness":
- **Construct**: Effectiveness
- **Operationalization**: Time to resolution, accuracy of decisions, appeal rates
- **Measurement**: See `methods/effectiveness_scoring.md` for technical details

## Analysis Approach

[Statistical methods, qualitative analysis, computational approaches]

### Example:
- Descriptive statistics for overview
- Regression analysis for relationships
- Time series analysis for trends
- See `methods/` directory for implementation details

## Validity and Limitations

### Internal Validity
[Can you draw causal inferences? What threatens this?]

### External Validity
[Can findings generalize? To what populations?]

### Construct Validity
[Do your measures actually capture what you claim?]

### Limitations
[Be honest about constraints, biases, and weaknesses]

## Alternative Approaches Considered

[What other methodologies did you consider? Why did you choose this one?]

## Ethical Considerations

[IRB approval, data privacy, potential harms, etc.]
```

## When to Update METHODOLOGY.md

Update METHODOLOGY.md when:

✅ **Research question changes or refines**
✅ **Research design changes** (e.g., switching from experimental to observational)
✅ **Variables added or redefined**
✅ **Unit of analysis changes**
✅ **Major analytical approach shifts**
✅ **New limitations discovered**

Do NOT update METHODOLOGY.md for:

❌ Technical implementation details (those go in `methods/`)
❌ Code changes (those go in code comments and git commits)
❌ Data source specifics (those go in `data/README.md`)
❌ Experimental results (those go in `experiments/`)

## Examples: What Goes in METHODOLOGY.md

### ✅ CORRECT - Belongs in METHODOLOGY.md

> We use a quasi-experimental design with a difference-in-differences approach to examine the effect of policy change X on outcome Y. Our treatment group consists of cases filed after the policy change (n=1,247), and our control group consists of cases filed in the same calendar months one year prior (n=1,189). We control for case type, complexity, and submission month to account for seasonal variation.

**Why it belongs**: This describes research design, not technical implementation.

### ❌ INCORRECT - Does NOT belong in METHODOLOGY.md

> We implement the difference-in-differences estimator using the `did` package in Python. The model specification is:
> ```python
> model = PanelOLS(Y, X, entity_effects=True, time_effects=True)
> ```
> We use robust standard errors clustered at the case level.

**Why it doesn't belong**: This is technical implementation. Goes in `methods/diff_in_diff.md` instead.

## Methodology vs. Methods

**See `_CHUNKS/methods-vs-methodology.md` for detailed distinction.**

**Quick rule of thumb:**
- **METHODOLOGY.md**: "We will measure X by looking at Y because Z theoretical reason"
- **methods/**: "Here's the exact code and algorithm that measures Y"

## METHODOLOGY.md Maintenance

### Critical Rule: Keep It Current

**METHODOLOGY.md must always reflect your CURRENT research design.**

If you discover during analysis that:
- Your research question has evolved
- Your measurement strategy has changed
- Your data sources have shifted
- New limitations have emerged

**STOP. Update METHODOLOGY.md immediately. Then continue.**

### Version Control

METHODOLOGY.md is version-controlled like code:

```bash
git add METHODOLOGY.md
git commit -m "refine: Research question to focus on X instead of Y

After preliminary analysis, we realized Y was not measurable
with available data. Refocused on X which better captures the
theoretical construct of interest."
```

### Review Frequency

Review METHODOLOGY.md:
- ✅ **Before starting major analysis** - Confirm design is still correct
- ✅ **After discovering unexpected patterns** - Update limitations
- ✅ **When research question evolves** - Document the evolution
- ✅ **Before writing papers** - Ensure methodology section matches file

## Integration with Other Documentation

METHODOLOGY.md should reference (not duplicate):

```markdown
## Data Sources

We use three primary data sources (see `data/README.md` for details):
1. Administrative case records
2. Public decisions database
3. Appeal records

## Analysis Approach

We employ three main analytical methods:
1. Descriptive statistics (see `methods/descriptive_analysis.md`)
2. Difference-in-differences estimation (see `methods/diff_in_diff.md`)
3. Qualitative coding of decisions (see `methods/qualitative_coding.md`)
```

## Common Mistakes

### Mistake 1: Methodology is aspirational, not actual

❌ **WRONG**: "We will conduct interviews with stakeholders..."
✅ **CORRECT**: "We conducted interviews..." OR "We plan to conduct..."

Keep methodology file in sync with reality. If plans change, update the file.

### Mistake 2: Too much technical detail

❌ **WRONG**: Including SQL queries, Python code, specific package versions
✅ **CORRECT**: Describing analytical approach conceptually, referencing methods/ for implementation

### Mistake 3: Duplicating information from other files

❌ **WRONG**: Copying entire data schema from data/README.md
✅ **CORRECT**: Brief overview with reference: "See data/README.md for schema details"

### Mistake 4: Not updating when design changes

❌ **WRONG**: Leaving old research question in file when focus has shifted
✅ **CORRECT**: Updating immediately when research design evolves

### Mistake 5: Confusing methods with methodology

❌ **WRONG**: "We use Python 3.11 with pandas for data analysis"
✅ **CORRECT**: "We use descriptive statistics and regression analysis" (implementation details go in methods/)

## METHODOLOGY.md Quality Checklist

Before considering METHODOLOGY.md complete, verify:

- [ ] Research question is clearly stated
- [ ] Theoretical framework is explained
- [ ] Research design type is identified
- [ ] Variables (DV, IV, controls) are defined
- [ ] Unit of analysis is specified
- [ ] Data sources are listed (with reference to data/README.md)
- [ ] Measurement strategy is explained
- [ ] Analysis approach is described
- [ ] Validity threats are discussed
- [ ] Limitations are honestly acknowledged
- [ ] Alternative approaches are mentioned
- [ ] Ethical considerations are addressed (if applicable)
- [ ] File is current (not aspirational or outdated)
- [ ] Technical details are in methods/, not here
- [ ] No duplication of content from other files

## When METHODOLOGY.md Is Complete

A complete METHODOLOGY.md means a peer reviewer could:

1. **Understand your research design** without reading code
2. **Evaluate validity** of your approach
3. **Assess generalizability** of findings
4. **Identify limitations** and threats to inference
5. **Locate technical details** via references to methods/

If a reviewer would need to read code to understand your research design, your METHODOLOGY.md is incomplete.
