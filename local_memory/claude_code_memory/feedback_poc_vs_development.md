---
name: feedback-poc-vs-development
description: "User wants meticulous Module 2-style validation findings kept as a running record during the POC phase, to revisit when the project moves from POC to real development"
metadata:
  node_type: memory
  type: feedback
  modified: 2026-08-19T15:47:00.852Z
---

The user explicitly asked (2026-08-19, while building Module 2 for the 4th manual,
`base_ii_clearing_interchange_formats_tc_50_to_tc_92`) to keep the kind of meticulous
validation review just done — reading real block output, cross-checking duplicate positions,
tracing root causes through the raw PDF text — in mind for later, when the project stops
being a proof of concept and moves into real development. Confirmed this applies specifically
to the finding just surfaced: `"TC 57 - TCR 5 - Limited Use Data"` (this 4th manual) contains
TWO genuinely different record layouts stacked under one identical section-heading text with
no textual differentiator (see [[pending-bug-fixes]] for the concrete data). The user did not
ask to fix it now, only to not lose track of it.

**Why:** during the POC phase, the goal is breadth (validate the pipeline design across
manuals) more than exhaustively fixing every parsing edge case immediately — but the
meticulous investigative work that surfaces these edge cases is valuable and shouldn't be
thrown away just because it isn't acted on right now.

**How to apply:** keep logging findings like this into [[pending-bug-fixes]] (or a similar
running index) even when the immediate answer to "should I fix this now?" is no — don't
silently drop a finding just because it's deferred. When the project transitions from POC to
real development (a milestone the user will announce explicitly), proactively surface the
accumulated list of deferred findings for reprioritization, rather than assuming they're
still low-priority by default. This is a different axis from [[feedback-bug-prioritization]]
(which triages "fix now vs. defer" by data-relevance within the POC) — this one is about not
losing the deferred list across the POC→development boundary.
