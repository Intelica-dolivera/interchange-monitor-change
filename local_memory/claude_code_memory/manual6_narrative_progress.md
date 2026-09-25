---
name: manual6-narrative-progress
description: "Progress log for the 6th manual, international_full_service_pos_online_messages_processing_specifications — the first narrative-prose manual (paragraph/section diff, not field tables)"
metadata:
  node_type: memory
  type: project
  modified: 2026-08-19T20:55:50.613Z
---

## 6th manual: `international_full_service_pos_online_messages_processing_specifications`
(started 2026-08-19, `visa/src/base_i/`, 7 editions: 20230415→20260420)

**Fundamentally different from the first 5 manuals** — confirmed by reading real PDF content
before committing to an approach (per [[project-overview]], this is the "narrative Processing
Specifications" manual explicitly set aside during original scoping for lacking field-layout
tables). 232 pages, only 7 mention `Position`/`TCR`/`Reserved` at all, and those are incidental
prose mentions (e.g. "positions 1 and 2 of the decimal positions indicator field"), not real
grid structure. No Position/Length/Format grid, no TCR concept, no Reserved-field use case.

**User explicitly chose the approach via AskUserQuestion (2026-08-19)**: diff at
paragraph/section level with AI classification (Module 5), rather than skip this manual or do
structural-only diffing. This is a genuinely new content-shape category for the project.

**Module 1** — `poc/international_full_service_pos_online_messages_processing_specifications/
01_ingesta_parseo/ingest.py`. Same generic per-line design as all 5 other manuals, unchanged.
Ran clean on all 7 editions (226-238 pages, ~9000-9300 lines each).

**Module 2** — `.../02_normalizacion_bloques/normalize.py`. New design for this manual:
- **3-level heading hierarchy confirmed real**: 26.0pt / 20.0pt / 14.0pt (levels 1/2/3),
  captured as `section_heading` blocks with a `level` field — flat stream, no real tree
  built (same "no over-design without demonstrated need" principle as the other manuals,
  which also never built true nesting despite multi-tier headings). Confirmed 0 collisions
  between these sizes and TOC/front-matter content (checked all pages before the first
  `Chapter 1` heading). `Chapter N` (40pt) and chapter title (30pt) deliberately NOT captured
  as their own headings — fall through to the generic paragraph mechanism, same treatment as
  chapter-start boilerplate in the other manuals.
- **Content below 9.0pt confirmed to be diagram/bullet-glyph noise, not prose** — verified by
  reading real samples: 8.3/7.3/6.4-6.9pt are flowchart/diagram label fragments ("Merchant",
  "(0100 or 0200)"), 8.0pt is EXCLUSIVELY the bullet marker glyph (698 occurrences, all "l" or
  "n" — the real bulleted sentence is a separate 10.5pt line). All filtered as noise.
- **Real content genuinely lives in the 9.0-9.7pt range too** (not just 10.5pt body text) —
  found a real "Transaction Type × Message Type" support matrix (Yes/No cells) and bulleted
  field-conversion rules ("Fld 49 = 392") at 9.5/9.7pt. **Known, accepted limitation**: this
  module does NOT reconstruct these as tables — they fall through to the same generic
  paragraph-by-geometric-adjacency mechanism as prose, since the user explicitly chose
  paragraph/section diffing over building table-extraction machinery for this manual. Checked
  the actual result: because table cells are spatially separated, they mostly fragment into
  many small individual `paragraph` blocks (one per cell/bullet) rather than merging into
  unreadable garbage — milder than initially feared, but still loses table/list structure.
- **Cross-page paragraph merging is structurally impossible by design** (the paragraph-
  continuation check requires the same page as its first condition) — this manual is immune
  by construction to the exact page-boundary row-merge bug found and fixed in the 5th manual
  (see [[dev-phase-considerations]] item 1), since there's no page-crossing continuation path
  at all here.

Validated: ran clean on all 7 editions (3027-3188 blocks each). 0 suspiciously-short/empty
headings or paragraphs across all 7. Read real section content end-to-end (`"Full Service
Participation Requirements"` → `"General Requirements"`/`"Acquirer System Requirements"`) —
prose paragraphs coalesce correctly across multiple physical lines into one coherent block.
Noted (not yet investigated): heading count drops from ~296-297 (2023-2024 editions) to 264
(2025 editions onward) — a real structural consolidation, to be explored when Module 3/4 are
built, not now.

**Module 3 implemented and validated (2026-08-19)** —
`.../03_emparejamiento_bloques/match.py`. Two real design questions resolved with data before
writing code:

1. **Section matching key = full hierarchical path (L1>L2>L3), not the immediate title.**
   Confirmed level-2 titles repeat SYSTEMATICALLY under different level-1 parents (7 of 80,
   e.g. `"Cardholder Transactions"` under both `"Transaction Types"` and `"Standard
   Processing"` — genuinely different sections, not a rare oddity like the 4th manual's `TC
   57`). Full path is unique in 264/264 sections (newest edition) and 295/296 (1 residual
   duplicate, `"V.I.P. Services > Online Request Services > Mobile Location Confirmation
   Service"` — detected and order-tiebroken, same mechanism as `TC 57`).
2. **Paragraph matching: exact first, THEN fuzzy with real safeguards — not exact-only like the
   5th manual.** The user wants Module 5 to have real reworded-paragraph pairs to classify (an
   exact-only design would make Module 5 a no-op again, defeating their explicit choice).
   Measured real risk before tuning: unscoped fuzzy matching on all paragraphs is clearly unsafe
   (2052 risky pairs ≥0.85 in the single largest section alone — mostly short diagram-fragment
   "paragraphs", see Module 2). Restricting to paragraphs ≥60 chars AND raising the threshold to
   0.90 cuts the risk ~20x but doesn't zero it out — a small residual (~0.5-1%) remains from
   formulaic/templated prose (e.g. 3 near-identical "Converting ... Response Code X" sentences
   that are really 3 different table rows written as prose). Accepted this residual the same way
   the project already accepted the 3rd manual's 0.05% chain-shift rate — documented, and every
   fuzzy paragraph match is tagged `match_type="fuzzy"` with its `similarity` ratio in the
   output, never presented as a confirmed match. Logged as [[dev-phase-considerations]] item 6
   (a 3rd distinct fuzzy-matching risk profile, reinforcing that this needs re-deriving per
   manual, never assumed).

Validated: reconciliation exact across all 6 pairs; duplicate-path detection fires correctly and
consistently (present in all 4 early pairs, gone after the `20250414` restructuring below);
spot-checked 7 real fuzzy paragraph matches (`20231015→20240415`) — all genuine small wording
edits (e.g. `"0120 and 0322"` → `"0120 or 0322"`), no false positives found.

**Investigated a real structural anomaly, confirmed genuine, not a Module 2 regression**: pair
`20241021→20250414` shows 296→264 sections with only 206 matched (90 removed, 58 added) — traced
to a real document reorganization, not a bug: Visa promoted `"VisaNet Systems > Full Service
Processing"` (a level-2 subsection) to a standalone top-level chapter `"Full Service Processing"`
— confirmed by reading both sides' paragraph text directly (4 of 5 paragraphs byte-identical,
1 genuinely new paragraph inserted). Because the matching key is the full path, this shows as a
full section removed + full section added rather than "moved" — a real, accepted design gap, now
logged as [[dev-phase-considerations]] item 5 (a report-time "possible move" hint would be the
right place to address this later, not a matching-time auto-link).

**Module 4 implemented and validated (2026-08-19)** —
`.../04_deteccion_cambios/detect.py`. Simpler than the field-based manuals: a paragraph has no
sub-fields (unlike a ficha's `name`/`length`/`format`/etc.), so no `CARD_FIELDS`-style per-field
diff is needed — Module 3 already resolved the only distinction that matters (`match_type`):
`"exact"` paragraph matches are identical by construction (nothing to report), only `"fuzzy"`
matches become `paragraph_content_changed` (the actual target for Module 5's classification).
Emits `section_added`/`removed`/`renamed`, `paragraph_added`/`removed`/`content_changed`,
`duplicate_path_warning`/`duplicate_paragraph_warning`.

Ran cleanly across all 6 pairs (95-818 changes per pair — high volume, consistent with a 232-page
narrative document with real editorial churn plus diagram-fragment noise). Spot-checked the
recurring `duplicate_paragraph_warning` (46 instances, stable across the first 4 pairs, drops to
43 after the `20250414` restructuring) — confirmed genuine: short table/matrix cell fragments
("visa", "x", "options", "r1") that legitimately repeat within one section, same root cause as
the `"Multicurrency Field Flows"` diagram-fragment section already identified in Module 2/3. Not
a bug, safety net working as designed.

**Module 5 built, then a real bug found and fixed in Module 3 as a direct result of running it
(2026-08-19)** — `.../05_interpretacion_cambios_ia/classify.py`. Same 3-category design as the
field-based manuals, prompt adapted for prose/section-path context instead of a byte-layout
field. First run (304 items across 6 pairs, ~90 min via local Ollama) produced a suspiciously
high `safety_net_override` rate — 18/124 (14.5%) in the first pair alone, vs. the usual 0-2 seen
in every other manual's Module 5 run. Investigated per the project's standing rule (never wave
off an unusual signal) instead of accepting the run as validated.

**Root cause confirmed real, not noise**: the SAME logical paragraph can get chunked
differently between 2 editions — specifically, a short "list-intro" sentence (ends in `:`,
precedes a bullet list) sometimes stays MERGED into the preceding paragraph in one edition but
lands as its own separate paragraph in another, purely because a page break falls in a different
place — confirmed by reading raw Module 1 lines: `"VMP accounts can be used for the following:"`
flows mid-page with no break in one edition, but sits at the very top of the next page in the
other (likely a "keep with next" PDF pagination rule protecting the list-intro from being
orphaned at a page bottom). Module 2's same-page-only paragraph-continuation check (deliberately
added to avoid the 5th manual's row-merge bug) is correct in isolation but has this side effect.
Confirmed the SAME pattern in 4/4 sampled cases across 2 different edition pairs — systematic,
not a one-off.

**User chose to fix it now** (not defer) via AskUserQuestion. Investigated whether a Module-2
geometric fix (e.g. "near page-bottom + near page-top") would work FIRST — rejected: the
"keep with next" pagination means the page break can happen well before the actual page bottom
(the observed case broke at y1=671.7 on a page where content could still fit to ~750+), so
Y-position isn't a reliable signal for this. **Fixed at Module 3 instead**
(`_reflow_matches` in `match.py`): before normal exact/fuzzy paragraph matching, checks whether
2 ADJACENT paragraphs on one side, concatenated, exactly match (normalized) a single loose
paragraph on the other side — if so, it's pure re-chunking, not a real change. Only handles the
2-way-split case (the actual observed pattern); a hypothetical 3-way split would fall through
unresolved but still visible (not silently dropped). Exposed as a new `paragraphs_reflowed`
list in Module 3's output (never merged into `paragraphs_matched`) and a new `paragraph_reflowed`
change type in Module 4 (explicitly excluded from `ai_summary` and Module 7's "real change"
counts, same as it being genuinely not a change).

**Fix validated real impact**: re-ran Module 3/4 — first pair alone: 60 of 124 previously
fuzzy/added/removed paragraphs reconciled as pure reflow (`paragraphs_reflowed=60`), fuzzy count
dropped 124→103, added 294→223, removed 324→257. `paragraph_content_changed` total across all 6
pairs dropped from 304 to 267 (37 fewer misleading "content changed" events sent to Module 5).
Re-running Module 5 on the corrected input now (in progress as of this note).

**Re-run validated (2026-08-19)**: `safety_net_override` dropped 29→14 total across the 6 pairs
(first pair specifically: 18→7). Real, meaningful improvement, but investigated the remaining 7
in the first pair to check whether they're genuine changes or more reflow noise — found the fix
is INCOMPLETE, not wrong: the residual cases are more complex re-chunking variants than the
simple 2-adjacent-paragraphs-on-one-side↔1-paragraph-on-the-other pattern the fix handles.
Confirmed with a concrete example (`"Card Verification Value (CVV) Service"`): OLD had 2
paragraphs (`P1`, `P2`); NEW merged `P1+P2` into one bigger paragraph, then split OFF a
DIFFERENT trailing sentence into its own new paragraph — a genuine 2↔2 re-chunking, not the 2↔1
pattern `_reflow_matches` checks for. Each of the 7 residual cases sampled turned out to be a
DIFFERENT structural variant (2↔1 that also has a stray-whitespace mismatch from PDF hyphen-wrap
extraction noise — e.g. `"non-USD"` becomes `"non- USD"` between editions, breaking exact-match
by one character; 2↔2; and at least one, `"Merchandise Return and Merchandise Credit"`, that
looks like genuinely real content removal, not a chunking artifact at all — not fully confirmed).

**Presented this to the user with a recommendation; they chose NOT to keep extending the fix.**
A fully general fix would need real N:M paragraph-sequence realignment per section (diff-style
alignment across the whole section's paragraph list, not just adjacent pairs) — meaningfully more
engineering than the "acotado" (bounded) fix originally requested. **Decision: accept the
current improvement (29→14, real and validated) and move to Module 7**; the residual N:M
re-chunking cases are logged here as a genuine, deeper limitation for real development, not
solved further in the POC. Also logged in [[dev-phase-considerations]].

**Module 7 implemented and validated (2026-08-19)** —
`.../07_reporte_cambios/report.py`. Report grouped by full section path; business changes first;
`paragraph_reflowed` count surfaced in the summary and reliability-warnings section explicitly
labeled "not a real change" (transparency for the accepted residual noise, never hidden).

Read the fullest report (`20230415_to_20231015.md`, 26 business changes) end to end — strong
validation: found a genuine, coherent, document-wide finding despite the residual reflow noise —
**8 paragraphs across 5 different sections** ("Split Routing", "Assigning a Response Code",
"Issuer STIP Options" ×2, "STIP Authorization Processing" ×2, plus others) all show the same real
system rename: `"Exception File"` → `"Account Screen Authorization File (ASAF)"` — correctly
classified as `business_rule_change` in every instance, none of them flagged by the safety net
(clean matches, not reflow-affected). The `safety_net_override`-flagged items sit clearly
separated with their ⚠️ marker, exactly as designed. Output at
`data/07_reporte_cambios/<edition_a>_to_<edition_b>.md` (6 files) + `index.md`.

**This completes the full pipeline (Modules 1-5, 7) for
`international_full_service_pos_online_messages_processing_specifications`** — 6th manual done,
and the first of a genuinely new content-shape category (narrative prose, not field tables).
Module 6 stays tentative, same as the other 5. Real bug tally for this manual: 1 significant
Module 3 finding (paragraph reflow across page breaks misclassified as content changes) with a
bounded, user-approved fix that materially improved output quality (safety_net_override 29→14)
but was explicitly left incomplete by user choice — residual N:M re-chunking cases logged in
[[dev-phase-considerations]] items 7-8 for real development, not solved further here.

**No concrete next step decided yet — ask the user** whether to pick a 7th manual or return to
something still open (see [[pending-bug-fixes]] items 1-12, [[dev-phase-considerations]]).
