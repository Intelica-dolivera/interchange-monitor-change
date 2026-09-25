---
name: feedback-bug-prioritization
description: "How the user wants Module-2-style parsing bugs triaged — fix data-loss bugs in real tables now, defer cosmetic/out-of-scope ones as low-priority TODOs"
metadata: 
  node_type: memory
  type: feedback
  modified: 2026-08-12T15:37:20.153Z
---

When multiple parsing bugs are found in the same pass, the user wants them triaged by relevance to
the project's actual goal (field/position diffing across manual editions), not fixed uniformly.

Concrete instance (2026-08-12): two bugs surfaced in the same validation pass over
`base_ii_clearing_data_codes` Module 2 — (1) the manual's glossary section collapsing into one big
block per page (prose term→definition, not a code table — [[open-questions-technical-manuals]]),
and (2) a cross-page table continuation bug losing a real code-table row (`H0 (continued)`,
`Return/Reclassification Reason Codes`). The user explicitly said: turn (1) into a low-priority TODO
in memory ("prioridad 0", not blocking anything), but fix (2) now.

**Why:** the glossary is definitional prose, not something the reserved-field/position diffing use
case needs to touch; the continuation bug loses real structured data from a code table, which is
exactly the kind of data loss the project's parser must not have.

**How to apply:** when a validation pass turns up several rough edges at once, don't fix everything
by default and don't ask "fix all of these?" as one bundled question — separate them by whether they
touch data the core use case (field/position/code diffing) depends on. Bugs affecting real
code/field tables are worth proposing a fix for immediately; bugs in narrative/prose sections
(glossaries, legal notices, general descriptions) should default to being logged as low-priority
TODOs in memory rather than fixed, unless the user says otherwise.
