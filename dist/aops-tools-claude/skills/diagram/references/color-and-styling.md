# Mermaid Flowchart: Color and Styling

## Color for Meaning, Not Decoration

- Limit to **4-5 color roles** max - fewer is better
- Use **contrast ≥ 4.5:1** for text on fills
- **One dominant color** (60%), **one accent** (30%), **one highlight** (10%)
- Avoid red-green pairs for accessibility

## Recommended Palettes

**Modern Dark (recommended for most uses)**:

```
classDef default fill:#2d3748,stroke:#4a5568,color:#e2e8f0
classDef start fill:#276749,stroke:#48bb78,color:#f0fff4,stroke-width:2px
classDef process fill:#2c5282,stroke:#4299e1,color:#ebf8ff
classDef decision fill:#6b46c1,stroke:#9f7aea,color:#faf5ff,stroke-width:2px
classDef error fill:#c53030,stroke:#fc8181,color:#fff5f5
```

**Clean Light** (for formal documents):

```
classDef default fill:#f7fafc,stroke:#a0aec0,color:#2d3748
classDef start fill:#c6f6d5,stroke:#38a169,color:#22543d,stroke-width:2px
classDef process fill:#e2e8f0,stroke:#718096,color:#2d3748
classDef decision fill:#e9d8fd,stroke:#805ad5,color:#44337a,stroke-width:2px
classDef error fill:#fed7d7,stroke:#e53e3e,color:#742a2a
```

**High Contrast** (accessibility-first):

```
classDef default fill:#ffffff,stroke:#000000,color:#000000,stroke-width:2px
classDef start fill:#000000,stroke:#000000,color:#ffffff,stroke-width:3px
classDef process fill:#ffffff,stroke:#000000,color:#000000,stroke-width:2px
classDef decision fill:#ffff00,stroke:#000000,color:#000000,stroke-width:3px
classDef error fill:#ff0000,stroke:#000000,color:#ffffff,stroke-width:2px
```

**Warm Professional** (modern, approachable):

```
classDef default fill:#f5f5f5,stroke:#d4a574,color:#333333
classDef start fill:#d4a574,stroke:#8b6f47,color:#ffffff,stroke-width:2px
classDef process fill:#e8d4c0,stroke:#a0826d,color:#333333
classDef decision fill:#c4a46f,stroke:#8b6f47,color:#f5f5f5,stroke-width:2px
classDef error fill:#a0534f,stroke:#6b3b38,color:#ffffff
```

**Ocean Blue** (calm, professional):

```
classDef default fill:#e8f4f8,stroke:#4a90a4,color:#1a3a42
classDef start fill:#2c5aa0,stroke:#1a3a6a,color:#e8f4f8,stroke-width:2px
classDef process fill:#d0e8f2,stroke:#4a90a4,color:#1a3a42
classDef decision fill:#5a7ab8,stroke:#3a5a88,color:#e8f4f8,stroke-width:2px
classDef error fill:#c44444,stroke:#8a2a2a,color:#f5f5f5
```

**Sunset** (warm, energetic):

```
classDef default fill:#fff8e8,stroke:#e8a85c,color:#3a2a1a
classDef start fill:#d97706,stroke:#a85a2a,color:#fff8e8,stroke-width:2px
classDef process fill:#ffe4c0,stroke:#d4915a,color:#3a2a1a
classDef decision fill:#f59e0b,stroke:#d97706,color:#1a1a1a,stroke-width:2px
classDef error fill:#dc2626,stroke:#991b1b,color:#f5f5f5
```

## Anti-Pattern: Pastel Soup

**Avoid** charts with 8+ similar pastel colors - they create visual noise without hierarchy:

```
❌ BAD: 10 different light fills (#e3f2fd, #fff3e0, #fce4ec, #e8f5e9...)
✅ GOOD: 3-4 distinct colors with clear semantic meaning
```

## Always Use Solid Backgrounds

**Never use `fill:transparent`** for subgraphs or nodes. Users view charts in different themes (light/dark mode, custom CSS). Transparent backgrounds inherit unpredictably.

```
❌ BAD: style HOOKS fill:transparent,stroke:#c62828
✅ GOOD: style HOOKS fill:#fff8e1,stroke:#f9a825,stroke-width:2px
```

Every visual element needs an explicit fill color for theme safety.

## Typography

- Font size **14-16px** for readability
- **Bold labels** for key nodes (entry/exit points)
- Consistent casing: Sentence case for labels, CAPS for subgraph titles
