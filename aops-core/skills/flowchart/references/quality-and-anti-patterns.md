# Quality Checklist and Anti-Patterns

## Quality Checklist

Before considering a flowchart complete:

**Structure**:

- [ ] One clear message and audience defined
- [ ] Happy path is straight, exceptions branch clearly
- [ ] Decision nodes use diamond shape `{}`
- [ ] Each subgraph has ≤9 nodes

**Visual**:

- [ ] 4-6 color roles max; color-blind-safe
- [ ] Labels convey meaning (not just color)
- [ ] Font 14px, consistent casing, short verb labels
- [ ] Node and rank spacing adjusted; minimal edge crossings

**Technical**:

- [ ] Legend included if color meanings aren't obvious
- [ ] Interactive links for deep detail where appropriate
- [ ] Tested rendering in target environment

## Anti-Patterns to Avoid

**Layout Sins**:

- **Tall narrow tower**: Using `TD` for everything creates scroll-heavy charts. Use `LR` or mixed directions
- **Stacked subgraphs**: Placing all subgraphs vertically. Arrange phases horizontally instead
- **Tight spacing**: Default `nodeSpacing: 30` is cramped. Use 60+ minimum
- **No breathing room**: Nodes touching edges. Add `padding: 20` to init block

**Visual Sins**:

- **Pastel soup**: 8+ similar light colors with no visual hierarchy
- **Rainbow explosion**: Every node a different color
- **No focal point**: All nodes same size/weight (use stroke-width for emphasis)
- **Text walls**: Paragraphs in shapes (move to notes or split charts)

**Structural Sins**:

- **No clear message**: Chart tries to show everything
- **Spaghetti links**: Internal nodes linking to external nodes (breaks subgraph direction)
- **Backwards arrows**: Crossing the main flow spine
- **Mixed logic**: TD subgraphs in LR chart with cross-links (pick one strategy)

**Maintenance Sins**:

- Many individual `style` lines instead of `classDef`
- Hardcoded colors without semantic meaning
- IDs with spaces or special characters
