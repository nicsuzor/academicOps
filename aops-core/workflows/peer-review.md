---
id: peer-review
category: academic
description: Structured peer review for grant/fellowship applications with scaffolding and human composition
triggers:
  - "review grant"
  - "peer review"
  - "fellowship review"
  - "review submission"
  - "assess application"
bases: [base-task-tracking, base-handover]
---

# Peer Review

Structured review for grant/fellowship applications and academic work.

## Routing Signals

- Assessment packages
- Scheme reviews (ARC FT, etc.)
- Multiple applications to evaluate
- Conference/journal submissions

## Phases

1. **Setup**: Create workspace, get criteria, generate template
2. **Scaffold**: Create bot tasks per application (transcribe, draft, observe)
3. **Execute**: Workers process using templates
4. **Compose**: Human drafts, agent assists with voice/tone

## Composition Principles

### Core Values

- **Tone**: Professional positive, measured not effusive
- **Voice**: Evaluate claims, don't restate
- **Evidence**: Concrete examples over generalizations
- **Structure**: Lead with strengths, concerns at end

### Detailed Guidance (Updated 2026-02-27)

These principles emerged from systematic analysis of effective peer review practices.

#### 1. Frame Volume of Feedback Positively

When providing detailed feedback, explicitly contextualize the volume upfront to prevent misinterpretation.

**Why**: Volume of comments ≠ negative assessment. Without framing, authors may interpret many comments as harsh criticism.

**How**:
- State overall quality assessment first (positive)
- Explain why there are many comments (requested, detail-oriented, etc.)
- Clarify the nature of comments (minor, stylistic, etc.)

**Example**: "This is strong work. My detailed comments below are mostly about strengthening an already solid argument, not fundamental issues."

**When to use**:
- More than 5-7 comments
- Work is fundamentally sound but has improvable elements
- Feedback was requested in detail
- Author might be sensitive to criticism

#### 2. Teach Principles, Not Just Fixes

Explain the general pattern, why it matters, and how to recognize similar issues in future.

**Why**: Builds transferable skills rather than just correcting one instance. Shows investment in author's development.

**How**:
1. Identify the general pattern/principle
2. Explain why it matters (consequences)
3. Provide the specific fix
4. Teach how to recognize similar issues

**Example**: "This is the type of claim that needs methodological support: any statement about what 'always' or 'never' happens. Without data, soften to 'often' or 'typically'."

**When to use**:
- Issue represents a broader pattern
- Author would benefit from understanding the principle
- Pattern appears multiple times in the work
- Teaching moment is clear

#### 3. Frame Revisions as Strategic Strengthening

Position feedback in terms of strategic advantage, risk reduction, and economy of effort rather than error correction.

**Why**: Positions reviewer as author's advocate. Treats revision as strategic choice rather than fixing mistakes.

**How**:
- Frame in terms of what author gains
- Emphasize criticism avoided
- Note effort saved on defending claims
- Avoid "this is wrong" when it's "this is strategically suboptimal"

**Example**: "You could defend this stronger claim, but it would take significant space. Since it's not central to your argument, a softer version saves you effort and reduces potential critique."

**When to use**:
- Current text isn't wrong but invites unnecessary criticism
- Softer claim is easier to defend
- Strong version isn't central to argument
- Suggesting defensive revisions

#### 4. Provide Multiple Concrete Solutions

Present two or more specific solutions with brief rationales, then leave the choice to the author.

**Why**: Respects author agency. Shows multiple valid approaches. Teaches strategic thinking.

**How**:
1. Clear diagnosis of issue
2. Two or more specific solutions
3. Brief rationale for each option
4. Leave choice to author (avoid "you must")

**Example**: "To address this, you could either: (a) cite literature to support this claim, or (b) reframe it explicitly as an illustrative example rather than a verified finding. Option (a) strengthens the empirical base; option (b) clarifies epistemic status without requiring additional evidence."

**When to use**:
- Multiple valid approaches exist
- Author should make strategic choice
- Options have different trade-offs
- Want to teach decision-making

#### 5. Explain Reader Experience

Frame feedback in terms of what will confuse, slow, or frustrate readers rather than citing abstract rules.

**Why**: Teaches empathetic writing. Helps author understand the "why" behind conventions. Transfers to understanding different audiences.

**How**:
- Start with reader experience: "This will make readers..."
- Explain what happens in reader's mind
- Connect to specific issue
- Show how fix improves reader experience

**Example**: "Readers will stumble here because they're expecting evidence after this claim. Without it, they'll either doubt you or stop to wonder if they missed something. That pause disrupts the flow of your argument."

**When to use**:
- Clarity issues
- Flow problems
- Missing context or explanation
- Audience-specific considerations

#### 6. Identify Fundamentals vs. Refinements

Help the author understand which issues are fundamental (affect argument/structure) and which are refinements (improve already-sound work).

**Why**: Prevents paralysis. Helps author triage. Shows understanding of hierarchy of concerns.

**How**:
- Explicitly label major vs. minor issues
- Group similar issues together
- Explain why fundamental issues are fundamental
- Consider priority or sequence of revisions

**Example**: "Two fundamental issues: (1) reorganize so your argument leads; (2) clarify your methodological approach. The rest of my comments are refinements to strengthen already-solid sections."

**When to use**:
- Many comments of varying importance
- Work has structural issues alongside minor points
- Want to help author prioritize
- Prevent overwhelm

#### 7. Offer Strategic Identity Choices

When work has unclear identity or framing, surface the choice, present distinct options with requirements, and let author decide.

**Why**: Surfaces hidden assumptions. Helps author see implications of framing choices. Respects that this is the author's work to shape.

**How**:
1. Identify the choice needing to be made
2. Present distinct options clearly
3. Explain what each option requires
4. Let author decide

**Example**: "You need to decide if this is a theoretical contribution or an empirical study. If theoretical, strengthen the conceptual framework and use examples illustratively. If empirical, develop your methodology section and ensure data supports claims."

**When to use**:
- Work seems to straddle two approaches
- Disciplinary identity is unclear
- Scope/ambition mismatched with method
- Fundamental framing question exists

#### 8. Provide Concrete Language for Reorganization

When suggesting structural changes, provide actual transition language or example text.

**Why**: Makes implementation easy. Shows you've thought it through. Models good writing.

**How**:
- Suggest the reorganization
- Provide actual transition language/text
- Offer as suggestion ("something like") not prescription

**Example**: "Consider moving this paragraph to open the section, perhaps starting with: 'Three distinct regulatory frameworks fail to address representational harm...' This frames what follows and helps readers understand the structure of your argument."

**When to use**:
- Suggesting moves/reorganization
- Transitions would be unclear
- You can see the better framing clearly
- Example would help implementation

#### 9. Teach Self-Review Techniques

Combine specific feedback with teaching the technique that would help author catch similar issues themselves.

**Why**: Builds author independence. Teaches transferable practice. Helps with all future work.

**How**:
- Identify technique that would catch this issue
- Be explicit: "Here's how to catch this type of issue..."
- Combine with the specific fix

**Example**: "These types of logical gaps often become visible when you read your work aloud - the missing step will feel like a jump to your ear. In this case, you need to add [specific content]."

**When to use**:
- Issue that self-review technique would catch
- Teaching opportunity is clear
- Want to build author capacity
- Technique is broadly applicable

#### 10. Frame as Developing Habits

Use forward-looking language about practices to cultivate rather than backward-looking correction.

**Why**: Positions author as developing scholar. Implies practice will serve beyond this paper. More encouraging than "you didn't do X."

**How**:
- Use "get into the habit of" language
- Frame as practice to cultivate
- Especially useful for early-career scholars
- Combine with explanation of why habit matters

**Example**: "Get into the habit of explicitly articulating your contribution in the introduction - readers shouldn't have to infer what's new. In this paper, state clearly [specific contribution] so readers know what to look for."

**When to use**:
- Practices that benefit author long-term
- Developing craft/skill
- Early-career scholars
- Want to be forward-looking

## Common Error Types to Watch For

Based on analysis of peer review feedback patterns.

### 1. Undefended Strong Claims

**Pattern**: Absolute language ("always", "never", "completely", "revolutionized") without evidence to support it.

**Example**: "AI has completely transformed content creation" (overstated)
**Better**: "AI has significantly changed content creation practices" (defensible)

**Why it matters**: Strong claims invite criticism and require substantial defense. If not central to argument, they weaken rather than strengthen.

**Feedback approach**: Point out that strong value judgments attract objections. Suggest softer alternatives that are easier to defend and note what author gains (reduced criticism, less defense needed).

### 2. Implicit Arguments Needing Explicit Articulation

**Pattern**: Connections between claims are implied but not stated. Reader must infer the logical steps.

**Example**: Introduction discusses power in tech generally, then shifts to specific context without explaining connection.

**Why it matters**: Readers slow down when connections are unclear. Some will question the logic; others will assume they missed something. Disrupts argument flow.

**Feedback approach**: Ask specific questions that expose the gap ("What's the connection between X and Y?"). Explain reader experience (confusion, slowing down). Suggest how to make connection explicit.

### 3. Methodology-Evidence Mismatch

**Pattern**: Presenting examples or preliminary tests as if they're verified findings without methodological support.

**Example**: "When prompted with X, systems consistently do Y" - based on informal testing, presented as established fact.

**Why it matters**: Academic audience expects clear distinction between verified claims (with method) and illustrations. Conflating them undermines credibility.

**Feedback approach**: Explain epistemic standards. Provide options: either strengthen methodology to support the claim, OR reframe as illustrative example with appropriate caveats.

### 4. Missing Context for Specialized Audience

**Pattern**: Assumptions about shared knowledge that audience doesn't share. Jurisdiction-specific language, field-specific terms without definition.

**Example**: "Constitutional protections..." (which constitution?) or field jargon without introduction.

**Why it matters**: International/interdisciplinary audiences slow down when encountering unfamiliar terms. Pauses disrupt flow and may cause readers to question author's awareness of audience.

**Feedback approach**: Frame in terms of reader experience ("This will slow your international readers down"). Identify specific audience knowledge gaps. Suggest brief explanatory phrases.

### 5. Examples Not Integrated with Text

**Pattern**: Figures, quotes, or examples presented without explicit interpretation. Reader left to infer what they should notice.

**Example**: Figure showing data, caption only, no body text saying "Notice that..." or "This demonstrates..."

**Why it matters**: Readers may not see what author wants them to see. Even if they do, separable examples feel like interruptions rather than integrated evidence.

**Feedback approach**: Teach practice of explicitly directing reader attention ("You want to get into the habit of saying something explicitly about examples"). Explain that examples must be woven in, not separable.

### 6. Delayed Thesis Statement

**Pattern**: Paper's purpose or argument doesn't appear until well into introduction or later.

**Example**: Background information for two paragraphs before "This paper examines..."

**Why it matters**: Readers don't know what to look for. They can't evaluate relevance of background without knowing the purpose. Reduces clarity and impact.

**Feedback approach**: Direct and clear ("You need this at the top"). Explain structural logic (readers need frame before details). If helpful, provide suggested opening language.

### 7. Unclear Paper Identity

**Pattern**: Work seems to be both empirical study and theoretical contribution, or both law paper and policy paper, without committing to either.

**Example**: Uses theoretical framing but makes empirical claims; or makes legal arguments but focuses on industry practice.

**Why it matters**: Different identities require different structures, evidence types, and argumentative approaches. Straddling weakens both.

**Feedback approach**: Surface the choice explicitly. Present the distinct options (empirical vs. theoretical, legal vs. policy). Explain what each requires. Let author decide which better serves their goals.

### 8. Insufficient Audience Awareness

**Pattern**: Writing for one audience (e.g., legal scholars) while submitting to another (e.g., interdisciplinary conference).

**Example**: Assuming familiarity with case law, regulatory frameworks, or field-specific methodology.

**Why it matters**: Mismatched audience awareness causes readers to struggle. Work seems inaccessible or poorly targeted.

**Feedback approach**: Remind author of specific audience. Point out assumptions that audience won't share. Suggest what audience needs to understand the argument.

### 9. Precision Issues in Causal Claims

**Pattern**: Imprecise verbs suggesting stronger causal relationships than evidence supports.

**Example**: "This gap amplifies discrimination" (hard to prove) vs. "This gap means discrimination isn't addressed" (more defensible).

**Why it matters**: Causal claims require strong evidence. Overstating makes the claim vulnerable to critique and harder to defend.

**Feedback approach**: Check whether statements are literally true. Explain why current claim is difficult to prove. Provide alternative formulations that are easier to defend.

### 10. Duplicate Content

**Pattern**: Same quote, paragraph, or example appears multiple times.

**Example**: Quote repeated on p. 2 and p. 14.

**Why it matters**: Looks like editing error. Wastes precious word count. May confuse readers about whether it's intentional.

**Feedback approach**: Simple, direct ("This is repeated on pages X and Y"). No need for extensive explanation unless it's part of a pattern.

## Using These Principles

### Application Sequence

When reviewing, consider applying principles in this order:
1. Start with positive framing (Principle 1)
2. Identify fundamentals vs. refinements (Principle 6)
3. For each issue:
   - Teach the principle (Principle 2)
   - Frame strategically (Principle 3)
   - Provide options when applicable (Principle 4)
   - Explain reader experience (Principle 5)

### Combination

Principles often work together:
- Principle 2 (teach principles) + Principle 9 (teach self-review) = comprehensive skill building
- Principle 3 (strategic framing) + Principle 4 (multiple solutions) = empowering feedback
- Principle 5 (reader experience) + Principle 10 (developing habits) = sustainable improvement

### Adaptation

Adapt based on:
- **Work quality**: Fundamentally sound work needs different approach than deeply flawed work
- **Author career stage**: Early-career scholars benefit more from habit-formation language
- **Relationship**: Peer review differs from supervision differs from editorial feedback
- **Context**: Time constraints, stakes, audience expectations

### Limitations

These principles work best when:
- Work is fundamentally sound (needs refinement not major revision)
- Author is receptive to feedback
- You have time for detailed engagement
- Relationship is collegial/supportive

Not recommended for:
- Severely flawed work requiring major overhaul (need different approach)
- Time-constrained quick reviews
- Adversarial contexts
- Work outside your expertise

## Data Sources

These principles extracted from systematic analysis of peer review feedback (2026-02-27).

**Process**: Review documents with inline comments analyzed for patterns → generalized to transferable principles → validated for cross-context applicability.

**Sensitive data** (actual reviews with identifying information): Stored in `$ACA_DATA/processed/review_training/`

**Public framework** (this document): Contains only depersonalized, generalized principles with constructed examples.

See `aops-core/skills/extract/workflows/review-inline-comments.md` for extraction methodology.
