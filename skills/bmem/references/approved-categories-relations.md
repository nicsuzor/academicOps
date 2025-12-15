---
title: Approved bmem Categories and Relations
type: reference
permalink: approved-categories-relations
tags:
  - bmem
  - reference
  - validation
---

# Approved bmem Categories and Relations

**CRITICAL**: bmem files MUST use only these approved values. Using unapproved categories or relations will cause validation failures.

**Source of truth**: `~/writing/scripts/bmem_tools.py` (VALID_CATEGORIES and VALID_RELATIONS)

## Approved Observation Categories

Use ONLY these categories in observations (`- [category] statement`):

- `fact` - Objective information
- `idea` - Thoughts and concepts
- `decision` - Choices made with rationale
- `technique` - Methods and approaches
- `requirement` - Needs and constraints
- `question` - Open questions
- `insight` - Key realizations
- `problem` - Issues identified
- `solution` - Resolutions
- `action` - Tasks to complete
- `goal` - Objectives and targets
- `strategy` - High-level approaches
- `challenge` - Difficulties and obstacles
- `task` - Task-related observations
- `classification` - Categorization
- `recommendation` - Suggested actions
- `feature` - Feature descriptions
- `plan` - Planning information
- `lesson-learned` - Lessons from experience
- `risk` - Risk factors
- `principle` - Guiding principles
- `audience` - Audience information
- `message` - Key messages
- `focus` - Areas of focus
- `priority` - Priority information
- `outcome` - Results and outcomes
- `metric` - Measurable indicators
- `deadline` - Time constraints
- `constraint` - Limitations
- `approach` - Methodological approaches
- `architecture` - System architecture
- `framework` - Framework information
- `design` - Design decisions
- `tool` - Tool information
- `benefit` - Benefits and advantages
- `blocker` - Blocking issues
- `concern` - Concerns and worries
- `consideration` - Factors to consider
- `opportunity` - Opportunities identified
- `milestone` - Milestones and checkpoints
- `timeline` - Timing information
- `allocation` - Resource allocation
- `strategic` - Strategic information
- `assessment` - Evaluations and assessments
- `purpose` - Purpose and intent
- `philosophy` - Philosophical approach
- `pattern` - Patterns identified
- `structure` - Structural information
- `relationship` - Relationship information
- `value` - Value propositions
- `capability` - Capabilities
- `collaboration` - Collaboration details
- `competitive-advantage` - Competitive advantages
- `deliverable` - Deliverables
- `event` - Event information
- `format` - Format specifications
- `need` - Needs identified
- `positioning` - Positioning information
- `topic` - Topic information
- `transition` - Transitions
- `urgent` - Urgent items
- `advantage` - Advantages
- `categorization` - Categorization schemes
- `category` - Category information
- `contact` - Contact information
- `metrics` - Metrics (plural)
- `mitigations` - Risk mitigations
- `risks` - Risks (plural)
- `completed` - Completed items
- `audience-tailoring` - Audience-specific tailoring

## Approved Relation Types

Use ONLY these relation types in relations (`- relation_type [[Target]]`):

- `relates_to` - General connection
- `implements` - Implementation of spec/design
- `requires` - Dependency relationship
- `extends` - Extension or enhancement
- `part_of` - Hierarchical membership
- `supports` - Supporting relationship
- `contrasts_with` - Opposite or alternative
- `caused_by` - Causal relationship
- `leads_to` - Sequential relationship
- `similar_to` - Similarity relationship
- `incorporates_lessons_from` - Learning transfer
- `underpins` - Foundational support
- `defines_allocation_for` - Resource allocation
- `builds_on` - Builds upon
- `references` - Reference relationship
- `follows_up` - Follow-up relationship
- `affects` - Affects relationship
- `replaces` - Replacement relationship
- `depends_on` - Dependency
- `includes` - Inclusion relationship
- `monitored_by` - Monitoring relationship
- `deployed_to` - Deployment relationship
- `integrates_with` - Integration relationship
- `blocked_by` - Blocking relationship
- `built_on` - Built on foundation
- `built_with` - Built using tools/tech
- `continuation_of` - Continuation
- `continues` - Continues from
- `enabled_by` - Enablement relationship
- `enables` - Enables other entity
- `informed` - Was informed by
- `informs` - Informs other entity
- `shares_architecture_with` - Shared architecture
- `supported_by` - Support source
- `tracks_progress_for` - Progress tracking
- `uses_architecture_from` - Architecture source
- `visualizes` - Visualization relationship

## Format Rules

**Permalinks**:
- MUST be simple slugs: `my-project-name`
- NO forward slashes: `projects/my-project` ❌
- Lowercase alphanumeric with hyphens only: `^[a-z0-9-]+$`

**Relations syntax**:
- MUST use double brackets: `- relates_to [[Entity Title]]`
- NO plain text: `- relates_to Entity Title` ❌
- NO parenthetical notes: `- relates_to Entity (details)` ❌

**Title consistency**:
- H1 heading MUST exactly match frontmatter title
- Including punctuation, capitalization, everything

## Common Mistakes

❌ **Invalid category**: `- [email] Sent to user@example.com`
✅ **Correct**: `- [fact] Sent to user@example.com #email`

❌ **Invalid relation**: `- led_by [[Person Name]]`
✅ **Correct**: `- part_of [[Person Name]]` or `- relates_to [[Person Name]]`

❌ **Invalid permalink**: `permalink: projects/my-project`
✅ **Correct**: `permalink: my-project`

❌ **Missing brackets**: `- relates_to My Project`
✅ **Correct**: `- relates_to [[My Project]]`

## Mapping Common Needs to Approved Values

### General Mappings

If you need to express:
- **Email-related info**: Use `[fact]` with `#email` tag
- **Grant information**: Use `[fact]` with `#grant` tag
- **Metadata**: Use `[fact]` with `#metadata` tag
- **Leadership**: Use `part_of` relation or `[fact]` with description
- **Collaboration**: Use `[collaboration]` category or `relates_to` relation
- **Involvement**: Use `part_of` or `relates_to` relation

**Pattern**: Use approved categories/relations, supplement with tags in frontmatter for specificity.

### Email Extraction Specific Mappings

When extracting from email archives, map invalid categories to approved ones:

| ❌ Invalid Category | ✅ Use Instead |
|---------------------|----------------|
| `[email]` | `[fact]` + `#email` tag |
| `[project]` | `[fact]` + `#project` tag, OR use `type: project` in frontmatter |
| `[coordinator]` | `[fact]` with role description, OR `[contact]` |
| `[duration]` | `[timeline]` or `[constraint]` |
| `[content-focus]` | `[focus]` |
| `[target-audience]` | `[audience]` |
| `[team]` | `[collaboration]` or `[fact]` |
| `[production-approach]` | `[approach]` |
| `[status]` | `[fact]` + `#status` tag, OR `[outcome]` |

**Relations for people/roles**:

| ❌ Invalid Relation | ✅ Use Instead |
|---------------------|----------------|
| `coordinator` | `relates_to` (generic), or use `[contact]` observation |
| `content_creator` | `relates_to` with `[fact]` describing role |
| `proposed_filmmaker` | `relates_to` with `[fact]` describing proposed role |
| `led_by` | `part_of` (person is part of project) |
| `team_member` | `relates_to` |
| `collaborator` | `relates_to` with `[collaboration]` observation |

**Pattern for roles**: Use `relates_to [[Person Name]]` relation + `[fact]` or `[contact]` observation describing the person's role, rather than inventing role-specific relation types.
