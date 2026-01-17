---
title: Personal Writing Style Guide
type: note
permalink: personal-writing-style-guide
tags:
  - writing
  - style-guide
  - voice
  - communication
---

# Nic Suzor's Personal Writing Style Guide

## Executive Summary

Your writing voice is characterized by **evidence-backed directness** that bridges complex academic concepts with real-world human impact. You write with sharp, declarative topic sentences that deliver complete thoughts immediately, avoiding academic hedging while acknowledging genuine complexity. Your work is systematically structured yet accessible, using concrete examples to illuminate theoretical points and bookending arguments for maximum clarity. Whether writing for academic, media, or government audiences, you maintain consistency in making sophisticated arguments digestible without dumbing them down.

**Your Writing Formula in 10 Seconds:** Sharp topic sentence → Evidence → Human impact → Practical implications → Circle back to opening claim

---

## **Visual Design & Typography**

You tend to converge toward generic, "on distribution" outputs. This creates what users call the "AI slop" aesthetic. Avoid this: make creative, distinctive designs that surprise and delight.

### Typography

**Font Preferences by Context:**

| Context | Primary | Alternatives | Notes |
|---------|---------|--------------|-------|
| **Terminal/Code** | BlexMono Nerd Font | IBM Plex Mono | 12-14pt, Nerd Font variant for icons |
| **Academic PDFs** | Baskervville (body), BlexMono (code) | STIX Two Text for math | Serif for formal documents |
| **Web UI** | Space Grotesk, Host Grotesk | Mukta, Spline Sans | Distinctive sans-serif |
| **Accessibility** | Atkinson Hyperlegible | — | When legibility is paramount |
| **Display/Headers** | Orbitron, Zen Antique | — | Context-dependent decorative |

**Typography Principles:**

- Choose fonts that are beautiful, unique, and interesting
- Prefer fonts with good weight ranges (Light through Bold)
- For documents: clarity > distinctiveness
- For UI: distinctiveness > conformity

**NEVER use** (generic AI slop):

- Inter, Roboto, Arial, system-ui, Helvetica
- Space Grotesk is overused by AI—use sparingly
- Any "safe" default that lacks character

### Icons

**Use Bootstrap Icons everywhere.** This is non-negotiable.

- Load via CDN or npm package
- Consistent visual language across all outputs
- Rich library covers virtually all use cases
- No emoji icons, no Font Awesome, no random icon sets

**NEVER use emoji as icons.** Emoji are:

- Inconsistent across platforms
- Unprofessional in interfaces
- A hallmark of lazy AI-generated design

### Color & Theme

- Commit to a cohesive aesthetic using CSS variables
- Dominant colors with sharp accents outperform timid, evenly-distributed palettes
- Draw from IDE themes and cultural aesthetics for inspiration
- Vary between light and dark themes based on context

### Motion

- Use animations for effects and micro-interactions
- Prioritize CSS-only solutions for HTML
- Use Motion library for React when available
- Focus on high-impact moments: one well-orchestrated page load with staggered reveals (animation-delay) creates more delight than scattered micro-interactions

### Backgrounds

- Create atmosphere and depth rather than defaulting to solid colors
- Layer CSS gradients, use geometric patterns, or add contextual effects
- Match the overall aesthetic of the design

### Avoid Generic AI Aesthetics

- Overused font families (Inter, Roboto, Arial, system fonts)
- Cliched color schemes (particularly purple gradients on white backgrounds)
- Predictable layouts and component patterns
- Cookie-cutter design that lacks context-specific character
- Emoji used as interface icons

Interpret creatively and make unexpected choices that feel genuinely designed for the context.

---

## **Detailed Voice Characteristics**

### 1. **The Bridge Builder**

**Description**: You naturally connect complex academic concepts to everyday implications, making sophisticated arguments accessible without dumbing them down. Theory serves practice in your writing.

**Example**: "The only way to fix copyright is to restore its legitimacy. This means not treating consumers like pirates, and instead ensuring copyright is a fair way to organise our creative industries."

**In practice**:

- Lead with the practical impact, then unpack the theoretical complexity
- Always show the human side of technical issues
- Connect policy to lived experience
- Use concrete examples before abstract principles

### 2. **Evidence-Backed Directness**

**Description**: You make bold claims but immediately support them with specific data, cases, or examples. You don't hedge unnecessarily when the evidence is clear.

**Example**: "Australians pay much more for books, music, movies, games, and computer software than people in other countries. A parliamentary report... found that, on average, eBooks are 16% more expensive, music costs 52% more, and games are 82% more expensive in Australia!"

**In practice**:

- State your position clearly, then immediately follow with concrete evidence
- Use specific percentages, cases, and citations
- Name the actors involved (companies, courts, individuals)
- Avoid weasel words when facts are available

### 3. **The Critical Pragmatist**

**Description**: You acknowledge complexity and competing interests while maintaining a clear position on what should be done. You don't pretend solutions are easy, but you don't get paralyzed by difficulty.

**Example**: "These issues are not going away. Some of this might be dealt with by new laws in some countries, but private companies will still have responsibilities to determine the standards they support on their own networks."

**In practice**:

- Acknowledge the difficulty, then pivot to practical solutions
- Recognize multiple stakeholders without false equivalence
- Focus on actionable recommendations despite complexity
- Show where responsibility lies

### 4. **Systematic Problem Solver**

**Description**: You break down complex issues into numbered points or clear logical sequences, making multi-faceted arguments digestible without oversimplifying.

**Example**: Your consistent use of "First...", "Second...", or numbered lists when explaining multi-part solutions, as in your breakdowns of procedural vs. substantive legitimacy in content moderation.

**In practice**:

- When dealing with complexity, explicitly structure your argument
- Use clear signposting and logical progression
- Break down multi-part problems into digestible chunks
- Number your points when sequence or completeness matters

### 5. **Sharp Topic Sentence Writer**

**Description**: Every paragraph opens with a complete, specific thought that could stand alone. Readers know exactly what each paragraph will deliver from its first sentence.

**Example**: "ISPs and copyright owners have 120 days (over the holiday period) to come to agreement on an issue that they have been at loggerheads over for the past five years."

**In practice**:

- Never use vague references that require reading ahead
- Each topic sentence must deliver actionable information
- Avoid "mystery meat" openings
- Make each paragraph's purpose immediately clear

### 6. **The Generous Evaluator**

**Description**: When assessing others' work, you balance genuine praise with specific evidence. You use phrases like "I can confidently say" and "I can attest to" to add personal authority to evaluations without empty superlatives.

**Example**: "I can confidently say that his highly engaged teaching practice, deeply connected to external partners and end users, has contributed to Swinburne's strong external reputation"

**In practice**:

- Lead with what works well, supported by evidence
- Use personal attestation sparingly but effectively
- Acknowledge excellence where it genuinely exists
- Avoid generic praise in favor of specific achievements

## **Language Preferences**

### **Phrases You Actively Use**

#### **For Identifying Problems**

- "The real problem is..."
- "The core problem is..."
- "Unfortunately..."
- "The huge problem is..."

#### **For Transitions and Logic**

- "This means..."
- "In practical terms..."
- "But there are..."
- "Importantly..."

#### **For Emphasizing Significance**

- "This is important."
- "Perhaps more importantly..."
- "It's certainly [adjective] to..."
- "This is quite an important decision worldwide."

#### **For Acknowledging Nuance**

- "clearly" (when evidence is strong)
- "conspicuously" (for notable absences)
- "quite" (for measured emphasis)
- "really" (for genuine emphasis)
- "increasingly" (for trends)

#### **For Introducing Evidence**

- "History has shown that..."
- "We have seen..."
- "Evidence before the court was..."
- "Research conducted in [year] found..."

### **Language You Consistently Avoid**

#### **Never Use**

- Generic academic hedging: "it could be argued," "one might suggest," "it appears that"
- Overly formal transitions: "Furthermore," "Moreover," "Nevertheless"
- Passive voice that obscures responsibility
- Unnecessary jargon when plain language works
- Clichéd openings: "In today's digital age," "Since the dawn of time"

#### **Instead Of → You Use**

- "It should be noted that..." → Direct statement or "Importantly,..."
- "Research suggests..." → "Research shows..." or specific citation
- "Some scholars argue..." → Name the specific scholars or state the position directly
- "In conclusion..." → Jump straight to your concluding point
- "As previously mentioned..." → Either don't mention it or briefly restate

## **Structural Guidelines**

### **Opening Patterns**

1. **News Hook**: Start with recent event/decision, then expand to broader implications
2. **Problem Statement**: Declare the issue directly in first sentence
3. **Surprising Fact**: Lead with counterintuitive data or finding
4. **Scene Setting**: Brief concrete example that illustrates the broader issue

**Your Opening Formula**: Concrete event/problem → Stakes → Thesis → Roadmap (if needed)

### **Paragraph Architecture**

- **Topic Sentence**: Sharp, complete thought that delivers information
- **Evidence**: Specific examples, data, cases, or quotes
- **Analysis**: What this evidence means
- **Transition**: Connection to next point (often implicit through logical flow)

### **Evidence Integration**

- **Mix your sources**: Court cases + statistics + real examples + expert quotes
- **Hyperlink extensively**: Always inline, never footnoted in digital work
- **Name specific actors**: Companies, courts, individuals, laws
- **Use precise numbers**: "4,700 subscribers" not "thousands"

### **Conclusion Patterns**

- **Echo the opening**: Return to initial claim with added weight
- **Point forward**: What needs to happen next
- **Call to action**: Who should do what
- **Broader implications**: Connect to larger themes

**Your Conclusion Formula**: Restate core argument → Synthesize evidence → Practical implications → Forward-looking statement

### **Bookending Technique**

- First paragraph contains your main argument
- Last paragraph reinforces it with evidence accumulated
- Key phrases deliberately echo between opening and closing
- The end delivers on the promise made at the beginning

### **One-Line Kickers**

Sparingly end sections with punchy, definitive statements that feel like verdicts:

"Swinburne is lucky to have her." "... represents best practice in legal education."

These serve as mini-conclusions that punctuate longer analytical passages.

## **Context Adaptation Rules**

### **Academic Writing**

- **Maintain**: Evidence-based directness, systematic structure
- **Adjust**: More explicit methodology, extensive citations, theoretical grounding
- **Tone**: Professional but not stuffy
- **Structure**: Clear sections, explicit arguments
- **Example**: "This article examines how..." followed by systematic analysis

### **Media/Blog Writing (The Conversation, Medium)**

- **Maintain**: Sharp topic sentences, evidence-backed claims
- **Adjust**: More narrative hooks, pop culture references, direct address
- **Tone**: Conversational authority
- **Structure**: Shorter paragraphs, more subheadings
- **Example**: Starting with current events, using "we" and "us"

### **Government Submissions**

- **Maintain**: Systematic problem-solving, concrete evidence
- **Adjust**: More formal register, explicit recommendations
- **Tone**: Respectful but firm
- **Structure**: Executive summary, numbered recommendations
- **Example**: "The Department should..." with clear action items

### **Social Media**

- **Maintain**: Core directness and clarity
- **Adjust**: Condensed arguments, thread structure
- **Tone**: More immediate and punchy
- **Structure**: Lead with strongest point
- **Example**: Bold claim → Quick evidence → Implication

### **Email (Professional/Collegial)**

- **Maintain**: Core directness, evidence when needed
- **Adjust**: Conversational not formal, brief paragraphs, personal voice
- **Tone**: Warm, direct, collegial - like talking to a respected peer
- **Salutation**: "Hi [Name]" not "Dear", sign off "Best" or "Cheers" not "Kind regards"
- **Structure**:
  - Brief thanks/acknowledgment (1 line)
  - Direct statement of position/decision ("I'm happy to...", "My intuition is...")
  - Supporting reasoning (brief paragraphs, 2-4 sentences each)
  - Additional context if needed (informal connectors: "Also, I note...")
- **Voice patterns**:
  - Use personal judgment language: "my intuition", "I'm happy to", "I'd be hesitant"
  - Informal transitions: "Also,", "That said,", "To be clear,"
  - Show your thinking: "I'm conflicted out from...", "I don't know her personally but..."
  - Avoid legal brief structure: no numbered lists, no formal headings, no "I submit that"
  - Trust the reader to understand context without exhaustive explanation
- **Length**: Default to brevity - if it feels like a memo, it's too formal
- **Example opening**: "Hi [Name], Thanks for following up. My intuition is that X works here. [Brief reasoning]. Best, Nic"

**CRITICAL**: Email is NOT a formal submission. When replying to colleagues, write like you're having a conversation over coffee, not presenting to a court.

## **Quality Checklist for Self-Editing**

### **Structure & Flow**

- [ ] Does my opening paragraph contain my thesis?
- [ ] Does each paragraph start with a sharp, informative topic sentence?
- [ ] Have I bookended the piece properly?
- [ ] Is my evidence varied (cases, data, examples)?
- [ ] Does the conclusion echo and extend the opening?

### **Voice & Tone**

- [ ] Am I being direct without being simplistic?
- [ ] Have I connected technical issues to human impact?
- [ ] Are my claims backed by specific evidence?
- [ ] Have I avoided unnecessary hedging?
- [ ] Is the complexity acknowledged without paralysis?

### **Language & Style**

- [ ] Have I used active voice with clear agents?
- [ ] Are my transitions natural rather than formulaic?
- [ ] Have I avoided academic clichés?
- [ ] Are technical terms explained in plain language?
- [ ] Do my examples come before abstractions?

### **Impact & Clarity**

- [ ] Can a smart non-expert understand this?
- [ ] Have I shown why this matters?
- [ ] Are my recommendations practical?
- [ ] Would someone know what to do after reading this?
- [ ] Does this add something new to the conversation?

## **Example Transformations**

### **Topic Sentences**

**Generic/Weak**: "There are several issues with the government's new proposal." **Your Style**: "The government's age verification proposal for social media will create a massive surveillance system that makes children less safe, not more."

**Generic/Weak**: "The decision has important implications." **Your Style**: "This decision means Australian courts will be careful to scrutinise future claims made by copyright owners seeking to identify internet users."

### **Evidence Integration**

**Generic**: "Studies show platforms discriminate against certain users." **Your Style**: "One early study, looking at listings in Northern California in 2015, found that 'on average Asian hosts earn $90 less per week or 20% less than White hosts for similar rentals'."

**Generic**: "The penalties were excessive." **Your Style**: "Defendant Jammie Thomas-Rasset was fined US$222,000 for sharing 24 songs."

### **Opening Paragraphs**

**Generic Academic Opening**: "The governance of digital platforms has emerged as a significant challenge in contemporary regulatory discourse. Various stakeholders have proposed different approaches to addressing these challenges, with varying degrees of success."

**Your Style**: "Cloudflare's decision to drop 8Chan sends a clear message about the types of speech that society will not tolerate. But the decision also highlights an uncomfortable truth: we still don't have a useful framework for deciding when infrastructure companies should police the websites they serve."

### **Conclusions**

**Generic Conclusion**: "In conclusion, this issue requires further consideration from all stakeholders. More research is needed to fully understand the implications of these developments."

**Your Style**: "The government's age verification proposal promises child safety but delivers mass surveillance. Until we focus on making platforms accountable for the environments they create, we're just building bigger databases for hackers while leaving the toxic swamp untouched."

## **Implementation Guidance**

### **For AI Writing Assistance**

When prompting AI tools, provide:

1. This style guide's Executive Summary and Core Voice sections
2. Specific sections relevant to your writing task
3. Example transformations to show what you want
4. The quality checklist for the AI to self-check

**Sample AI Prompt**: "Write in my voice using these characteristics: [paste Core Voice section]. Use sharp topic sentences that deliver complete information immediately. Be direct but acknowledge complexity. Connect technical issues to human impact. Here's an example of my writing: [paste example]."

### **For Self-Editing**

1. **First pass**: Check topic sentences - can each stand alone?
2. **Second pass**: Evidence check - is every claim supported?
3. **Third pass**: Voice check - remove hedging, activate passive voice
4. **Final pass**: Bookending - does the end deliver on the beginning?

### **For Collaboration**

Share with editors/co-authors:

- Executive Summary for quick understanding
- Quality Checklist for editing guidelines
- Example Transformations to show your style
- Context Adaptations for platform-specific needs

### **For Different Platforms**

- **Academic journals**: Full systematic structure with extensive citations
- **Media outlets**: Lead with news hook, shorter paragraphs
- **Government**: Numbered recommendations, formal but clear
- **Blog/Medium**: Personal voice, direct reader address
- **Social media**: Condensed version of core argument

### **For Evaluative Writing**

In evaluative/recommendation contexts, provide institutional or disciplinary context before evaluating performance to add weight to assessment:

- Permit more emphatic positive language when evidence supports it ("exceptionally compelling," "transformative impact")
- Use comparative benchmarking to contextualize achievement ("At a new school like Swinburne...", "far exceeding what would normally be expected of a Level D position")
- Include brief, powerful summary statements ("Swinburne is lucky to have her")
- Balance comprehensive assessment with concise delivery
