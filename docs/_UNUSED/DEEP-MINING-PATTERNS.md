# Deep Mining Patterns for Information Extraction

This guide trains agents to extract maximum value from conversations through deep contextual analysis.

## Core Principle: Every Word is Data

Treat conversations as rich data sources. Information exists at multiple levels:
1. **Explicit**: Direct statements and requests
2. **Implicit**: Context requiring inference
3. **Latent**: Patterns emerging across utterances

## Pattern Recognition Guide

### 1. People Extraction Pattern
**Trigger**: Any proper name mentioned
**Action**: Create stakeholder entry immediately

**Example**:
- Input: "maybe through Elliot?"
- Extract: Name=Elliot, Role=Unknown, Context=Mentioned in funding discussion
- Inference: Likely funding connection, needs exploration

**Example**:
- Input: "I need to get that to Jenni @ GLAAD soon"
- Extract: Name=Jenni, Organization=GLAAD, Urgency=High, Role=Recipient
- Inference: Critical stakeholder with deadline pressure

### 2. Timeline Mining Pattern
**Triggers**: Temporal markers like "next month", "second half of", "by [date]"
**Action**: Create timeline entry with inferred dates

**Example**:
- Input: "six months left on my fellowship"
- Extract: Fellowship end = Current date + 6 months
- Create: Timeline entry, funding deadline

**Example**:
- Input: "will we take long service leave in the second half of 2026?"
- Extract: Potential unavailability period H2 2026
- Inference: Affects project planning beyond that date

### 3. Assessment Extraction Pattern
**Triggers**: Evaluative language (good, bad, efficient, bureaucratic, etc.)
**Action**: Capture as strategic assessment

**Example**:
- Input: "too bureaucratic and ideologically deadlocked"
- Extract: Entity=Oversight Board, Assessment=Negative, Issues=[bureaucratic, deadlocked]
- Action: Update project file with strategic context

**Example**:
- Input: "highest reward/cost ratio"
- Extract: Project=DSA Tracking, Assessment=High efficiency
- Inference: Priority candidate for resource allocation

### 4. Resource Allocation Pattern
**Triggers**: Percentages, days/week, hours, FTE mentions
**Action**: Create or update resource allocation records

**Example**:
- Input: "maybe 30% of Sasha's time (= one day a week)"
- Extract: Person=Sasha, Allocation=30%, Time=1 day/week, Project=Inferred from context
- Create: Resource allocation entry

### 5. Uncertainty Capture Pattern
**Triggers**: "maybe", "might", "seems", "unclear", question marks
**Action**: Create entry with uncertainty flag

**Example**:
- Input: "am i eligible to apply for ANOTHER future fellowship? immediately?"
- Extract: Question about fellowship eligibility, Timeline=immediate
- Action: Create research task or question to resolve

### 6. Emotional/Cognitive State Pattern
**Triggers**: Stress indicators, energy mentions, cognitive load references
**Action**: Note in context for workload planning

**Example**:
- Input: "that's a big mush taking up space in my brain"
- Extract: Cognitive overload from undefined tasks
- Action: Flag need for structure/organization

**Example**:
- Input: "I feel like I might be behind"
- Extract: Anxiety about academic output
- Inference: May need timeline/milestone review

### 7. Dependency Discovery Pattern
**Triggers**: "needs", "requires", "depends on", "before", "after"
**Action**: Map relationships between entities

**Example**:
- Input: "it needs some scaffolding for me to really make it stand out"
- Extract: Project=Buttermilk, Dependency=Academic framing
- Action: Note requirement for academic wrapper

### 8. Implicit Task Pattern
**Triggers**: Future actions mentioned without "todo" language
**Action**: Create task entries

**Example**:
- Input: "keynote the DIGI misinformation event next month"
- Extract: Task=Prepare keynote, Event=DIGI, Date=Next month
- Create: Task with deadline

## Multi-Level Analysis Framework

### Level 1: Surface Extraction
- Direct quotes and explicit statements
- Named entities (people, organizations, projects)
- Dates and deadlines

### Level 2: Contextual Inference
- Relationships between entities
- Implicit priorities from discussion order/emphasis
- Unstated assumptions from context

### Level 3: Pattern Recognition
- Recurring themes across conversation
- Strategic tensions and trade-offs
- Emotional/energy patterns

## Quality Checks

### Completeness Test
After extraction, ask:
1. Do we know WHO is involved?
2. Do we know WHAT needs to happen?
3. Do we know WHEN it needs to happen?
4. Do we know WHY it matters?
5. Do we know HOW MUCH effort/resource it needs?

### Inference Validation
For each inference:
1. What evidence supports this?
2. What assumption am I making?
3. How confident am I? (High/Medium/Low)
4. What would confirm/refute this?

## Common Extraction Failures to Avoid

### 1. Name Dropping Without Context
**Bad**: Mentioned "Elliot"
**Good**: Elliot - potential funding connection through foundations

### 2. Ignoring Qualifiers
**Bad**: Will apply for fellowship
**Good**: Questioning eligibility for immediate fellowship reapplication

### 3. Missing Emotional Context
**Bad**: Multiple speaking engagements planned
**Good**: Speaking engagements creating cognitive overload ("mush in brain")

### 4. Isolated Facts Without Relationships
**Bad**: Sasha available 3 days/week
**Good**: Sasha 3 days/week, allocated 60% to Automod, 30% to DSA

## Implementation Checklist

When processing any conversation:
- [ ] Extract all named people with context
- [ ] Capture all temporal references
- [ ] Note all evaluative statements
- [ ] Record resource allocations
- [ ] Flag uncertainties for follow-up
- [ ] Map dependencies and relationships
- [ ] Identify implicit tasks
- [ ] Note emotional/energy states
- [ ] Create follow-up questions for gaps

## Success Metrics

Good extraction should:
1. Capture 90%+ of actionable information
2. Require zero "please save this" requests
3. Build complete context over time
4. Enable future agents to understand situation fully
5. Preserve strategic reasoning for future reference

## Remember

The goal is not just to capture what was said, but to understand:
- What it means
- Why it matters
- What should happen next
- What might block progress
- Who needs to know

Every conversation is a goldmine. Your job is to extract every nugget.
