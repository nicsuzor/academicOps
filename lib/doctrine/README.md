# doctrine

Composable agent-instruction fragments. An agent file pulls one in with
`@include doctrine/<name>.md`. Fragments use `##` headings so they slot in as
sections of the including file.

| Fragment             | Covers                                                                           | Included by                    |
| -------------------- | -------------------------------------------------------------------------------- | ------------------------------ |
| `bar.md`             | Excellence is the standard; compliance is the floor; block correct-but-wrong     | ida, james, marsha, pauli      |
| `launder.md`         | Every message is a synthesis, never a relay; density; cold-reader; lede          | ida, james                     |
| `epistemics.md`      | Observed vs reported; verify at assertion; absence claims; challenged claims     | ida, james, marsha, rbg, pauli |
| `delegation.md`      | The head never implements; cheapest surface; explicit model; brief thin          | ida, james, pauli              |
| `halt.md`            | Fail fast; detecting the halt condition is the halt signal; no workarounds       | ida, james, marsha, rbg, pauli |
| `probe.md`           | Empirical / process-determined / taste; cheapest discriminating experiment       | ida, james, pauli              |
| `governing-rules.md` | Obey the rules governing any artifact you change; binds delegation end to end    | ida, james, marsha, rbg, pauli |
| `memory.md`          | Capture knowledge not verdicts; update don't duplicate; only persistence surface | ida, james, marsha, pauli      |
