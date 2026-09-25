---
name: open-questions-technical-manuals
description: Pending questions and next step to resume the interchange_change_monitor design conversation
metadata: 
  node_type: memory
  type: project
  modified: 2026-08-19T17:12:59.994Z
---

Design dialogue, no production code written yet. Status as of 2026-08-11: **the PDF-tooling and
table-homogeneity questions that used to be open here are now CLOSED** (see
[[reference-pipeline-vs-technical-manuals]] for full detail — this file only tracks what's still
open).

## Closed questions (don't re-investigate these)

- **Which extraction tool to use** → closed. `fitz.get_text()` (raw PyMuPDF text) is sufficient as
  the sole extraction tool across all 9 manual folders / 8 content shapes found. `pymupdf4llm`
  table reconstruction has 2 confirmed data-integrity defects (dropped row; fragmented-row-into-
  fake-rows) on 2 different manuals. `pdfplumber.extract_tables()` fails on the borderless tables
  these manuals use. Docling was never justified by evidence and wasn't installed.
- **Are field tables homogeneous across manuals?** → closed, answer is NO. 8 distinct content
  shapes catalogued (A/A'/A''/B/C/D/F/H) across the 9 manual folders — each family needs its own
  regex parsing pattern, but all use the same extraction tool.
- **Does the parsing pattern change edition-to-edition within a family?** → closed, answer is NO.
  Verified via regex signature counts (oldest vs. newest edition) across all 9 families — pattern
  presence/absence never flips between editions, only content values change. One parser per
  family/content-shape applies unchanged across all its editions; no need to re-verify per version.
- **base_i scope gap (no field-layout tables in the narrative manual)** → closed. User located and
  added the correct technical-spec manuals (`visanet-authorization_only_online_messages_technical_
  specifications/`), confirmed via exact text-quote match. The wrong manual
  (`authorization_only_online_messages_processing_specifications_International`) was deleted from
  the repo by explicit user request (irreversible, no git in this project — confirmed before
  deleting).

## Still open / not started

1. **Design the Stage 1/2 parser — IN PROGRESS (started 2026-08-11).** User chose to build this as
   a proof-of-concept per manual before generalizing to a pipeline. Project structure:
   `poc/<manual>/<NN_modulo_name>/` for code, `poc/<manual>/data/<NN_modulo_name>/` for per-edition
   intermediate outputs. User's 7-module plan (Ingesta y Parseo → Normalización de bloques →
   Emparejamiento de bloques → Detección de cambios → Interpretación de cambios (IA) → Validación
   con Plataforma STD (tentative) → Reporte de cambios) is the structure being followed — kept
   unchanged, no extra module needed.
   - **Module 1 (Ingesta y Parseo) DONE** for `base_ii_clearing_data_codes`:
     `poc/base_ii_clearing_data_codes/01_ingesta_parseo/ingest.py`, output at
     `poc/base_ii_clearing_data_codes/data/01_ingesta_parseo/<edition>.json`, all 9 editions
     generated. Key design decision made during schema review: extract at **line level** via
     `page.get_text("dict")`, NOT block level via `page.get_text("blocks")` — PyMuPDF's block
     grouping can silently merge text from different table columns into one unit when they're
     spatially close (confirmed real example: `82`/`All`/`Duplicate Processing` — 3 different
     columns fused into one block by PyMuPDF), and once merged the per-line bbox is unrecoverable.
     At line level, same-Y/different-X means different columns of one row; consecutive-Y/similar-X
     means a wrapped paragraph — this geometric signal is what Module 2 will use to reconstruct
     rows/cells correctly instead of trusting PyMuPDF's generic heuristic. Full schema and rationale
     in `local_memory/NOTES.md` in the repo.
   - **Module 2 (Normalización de bloques) DONE** for this manual:
     `poc/base_ii_clearing_data_codes/02_normalizacion_bloques/normalize.py`, output at
     `poc/base_ii_clearing_data_codes/data/02_normalizacion_bloques/<edition>.json`, all 9 editions
     generated. Filters header/footer/page-number noise (Y-band thresholds) and TOC lines (dot-
     leader regex) first, then reconstructs rows by Y-overlap (>50% of smaller line's height) and
     assigns multi-line rows to `table_row` (if first cell looks like a short code,
     `^[A-Z0-9]{1,6}$`) vs `table_header` (otherwise, merged into any active header), with solo
     lines assigned to the nearest-X active column (this is how a wide wrapped cell like
     "Chargeback Reason Rules" accumulates many bullet lines under one row). **Real bug found and
     fixed**: PyMuPDF's `get_text("dict")` line order is NOT always row-by-row — for this manual's
     table headers it emitted column-by-column (all of column 1's wrapped lines, then column 2's,
     etc.), which silently broke row-grouping until lines were explicitly re-sorted by `(y0, x0)`
     per page before grouping. Validated against 2 different tables (3-col and 2-col) — both
     reconstruct correctly, and the TOC pages produce zero false-positive table blocks. Known
     accepted limitation: the "looks like a short code" heuristic wouldn't recognize a table whose
     key column is normal words instead of short codes — not seen yet in this manual, flagged as a
     risk to watch, not fixed pre-emptively. Full design rationale, calibration data, and the bug
     writeup are in `local_memory/NOTES.md`.
   - **Module 2 heuristic risk CONFIRMED as a real bug and FIXED (2026-08-12).** Scanned all 158
     pages of edition `20260418` programmatically (not just spot-checks) — found the accepted risk
     ("key column isn't a short code") was real, in `Country and Currency Codes` (p.119-131, ~180
     country rows), `U.S. State Codes` (p.133-135, 50 rows), and a bonus Type-H usage matrix
     (`Retained and Returned Data Elements`, p.138-140) — all 3 were collapsing into one giant
     `table_header` block per page instead of one `table_row` per entry. Fixed in
     `normalize.py`'s `build_blocks()`: classification signal changed from "does the FIRST cell
     look like a short code" to "does ANY cell in the row look like a short code" (works because
     sibling columns, e.g. `AF`/`004`/`AFN`/`971` next to `Afghanistan`, almost always carry a code
     even when the key column doesn't), plus a new branch so a codeless row while
     `active_kind=="table_row"` is treated as a wrap-continuation of the active data row instead of
     reopening a header. Verified against all 9 editions post-fix: 0 pages without blocks, 0
     empty-cell blocks, no regression on the originally-validated tables (p.31, p.101) or
     `Product ID Values` (p.65-67). Full trace/design rationale in `local_memory/NOTES.md`
     ("2026-08-12 — Riesgo aceptado del Módulo 2 confirmado como bug real, y arreglado").
   - **Two items surfaced by the full-editions validation:**
     1. **TODO, priority 0 (explicit user call, 2026-08-12) — not blocking anything right now.** The
        manual's final glossary section (~14-22 pages, always at the end, e.g. p.141-157 in
        `20260418`) is alphabetical term→prose-definition, has no code-like column at all, and
        still collapses into one `table_header` blob per page in all 9 editions. Not the same fix
        applies (no code signal exists to key off). Low priority for this project's goal (field/
        position diffing, not glossary diffing) — would need a new block type (e.g.
        `definition_list`) if ever tackled. Don't pick this up unless the user asks.
     2. **FIXED same day (2026-08-12), explicitly requested by user.** Cross-page table continuation
        bug: a row like `H0 (continued)` (error code `H0`'s definition continuing from the previous
        page, table `Return/Reclassification Reason Codes`) was being lost/swallowed into the
        page's re-declared header because `build_blocks()` runs per-page and resets
        `active_kind`/`active_cells` on every page boundary. Confirmed present in 5 of 9 editions
        (`20240413` onward — older editions' `H0` entry was short enough to fit on one page).
        Fixed with 2 additions in `normalize.py`: a `CONTINUED_CODE` regex
        (`^([A-Z0-9]{1,6})\s*\(continued\)$`) recognized as a code-cell trigger inside
        `build_blocks()` (so the row closes as its own `table_row` instead of merging into the
        header), plus a document-wide (not per-page) post-pass `_merge_continued_rows()` that
        finds the original row with the same code within a 50-block lookback window and merges the
        continuation's cells into it column-wise. Verified: exactly 1 unified `H0` `table_row` per
        affected edition (was 0 before — the content lived scattered inside a `table_header`), 0
        residual "(continued)"-tainted header blocks across all 9 editions, no regression
        (`pages_without_blocks=[]`, `empty_cell_blocks=0` in all 9). Full before/after detail in
        `local_memory/NOTES.md`.
   - **Cross-manual mapping done (2026-08-12, lightweight text scan, not full Module 1/2):** the
     same "word-keyed column, not short code" pattern was found in all 10 manuals in the repo. Most
     notably, both `base_i` technical manuals (VisaNet Auth-Only, Full Service POS) embed their own
     copy of the same `Country and Currency Codes` appendix (p.1114-1121 and p.1420-1427
     respectively) — same table, same bug, just a different manual. Reassuring finding for the
     project's central target: inspected a real Type A "Record Layout" grid
     (`base_ii_clearing_interchange_formats_tc_01_to_tc_49` p.371, e.g. `41  1  AN  Unattended
     Acceptance Terminal Indicator`) and confirmed its `Format` column (`AN`/`N`/`ANS`/`DX`/`UN`) is
     present in virtually every row and always matches the short-code pattern — so the
     any-cell-matches-code fix should generalize to Type A without further changes. One deferred
     design note: position ranges like `"45-69"` don't match `CODE_LIKE` (the hyphen breaks it) —
     not blocking today since `Format` covers the row, but would need the regex widened if position
     itself is ever used as the anchor. Full per-manual hit counts in `local_memory/NOTES.md`.
   - **Module 3 (Emparejamiento de bloques) implemented and validated (2026-08-12).**
     `poc/base_ii_clearing_data_codes/03_emparejamiento_bloques/match.py`. Reconstructs logical
     tables from Module 2's flat block stream (title = preceding `paragraph`, continuity detected
     via title re-declaration on each page a table spans), then matches tables across 2 consecutive
     editions (exact title match, `difflib` fuzzy fallback for renames) and rows within matched
     tables (exact code match — the same "match by stable key, not fuzzy name" principle already
     established for this project). Runs across all 8 consecutive edition pairs by default; output
     at `data/03_emparejamiento_bloques/<edition_a>_to_<edition_b>.json`.
     Found + fixed 2 real bugs during validation (not after): (a) 0-row "ghost tables" from the
     known bullet-paragraph-misclassified-as-table_header false positive were polluting
     added/removed/fuzzy counts — filtered out, dropped table count per edition from ~148-154 to a
     believable ~74-85 and fuzzy noise from 29-50/pair to 0-4/pair; (b) a dict-collision bug in
     `match_tables` silently discarded 194 of 198 rows of `Country and Currency Codes` in edition
     `20230415` because that edition's table got split into 4 same-titled segments (a long wrapped
     country name breaking Module 2's row-grouping) and the naive `{title: table}` dict kept only
     the last one — fixed via `_coalesce_same_title()` merging same-titled tables within an edition
     before matching. Validated for plausibility, not just structure: `Product ID Values` shows a
     believable progression of real product-code additions edition to edition (`F2`, `F3`, `G2`,
     `I3`, `L1`, `W1`...); the `H0`/`H0 (continued)` code from the cross-page-continuation fix above
     confirmed as a single stable `matched-ok` row across all 8 pairs.
     **FIXED same day (2026-08-12), explicitly requested by user (unlike the glossary gap, this one
     touched real code-table data so it wasn't auto-deprioritized).** Root cause found by pulling
     real bbox coordinates from Module 1's raw JSON, not guessed: in `20230415`'s `Country and
     Currency Codes`/`U.S. State Codes`, when the key column (country/state name) wraps to 2-3
     lines, this PDF vertically CENTERS the row's single-line sibling cells (code, currency, etc.)
     against the wrapped name — so the wrap's first and last lines each overlap the data row's
     Y-band at exactly 50%, sitting right on `group_into_rows()`'s `SAME_ROW_MIN_OVERLAP_RATIO=0.5`
     boundary. The old single-line continuation logic in `build_blocks()` blindly assumed "belongs
     to the currently active row" with no gap check — correct for the wrap's suffix (last line) but
     wrong for its prefix (first line, which is actually the START of the next row). A second,
     harder sub-case: two DIFFERENT columns wrapping simultaneously in the same Y-band (e.g. country
     "Cayman Islands" and its currency "Cayman Islands Dollar" both wrapping at once) get grouped by
     `group_into_rows()` into one code-less multi-cell row-group, bypassing the single-line-only fix
     entirely.
     Fixed in `normalize.py`: `build_blocks()` now gets a `rows[i+1]` lookahead; when a
     single-line OR code-less multi-cell row-group is about to merge into the active block but the
     gap to that active block exceeds `TABLE_ROW_GAP_MAX` (4.0, calibrated: same-cell wrap lines are
     ~0pt apart, distinct rows ~8.5pt apart in this manual), the gap to the NEXT row-group is also
     checked — if smaller, the line(s) are buffered (`pending_prefix`) and prepended to the next row
     instead of merged now. `_new_cells()` was updated to merge lines with near-identical x0
     (`CELL_X_MERGE_TOLERANCE=3.0`) into one cell so a prepended prefix joins correctly instead of
     becoming a spurious extra column. A safety net emits any unresolved `pending_prefix` as a loose
     paragraph at page-end instead of silently dropping it.
     Validated by hand-tracing real Y/X coordinates for all 4 known-broken cases in this edition
     BEFORE implementing (Bolivia 2-line, Bonaire/Sint Eustatius/Saba 3-line, Bosnia/Herzegovina
     2-line, Cayman Islands simultaneous 2-column wrap) — confirmed correct in the actual output
     after the fix, not just "should work" reasoning. End-to-end impact: the `20230415→20231014`
     Module 3 pair that motivated this investigation dropped from 292 added/24 removed to 30
     added/19 removed (now in line with the other 7 pairs); isolating just `Country and Currency
     Codes`, from 105 added/51 removed to 3 added/5 removed. No structural regression across all 9
     editions (0 pages without blocks, 0 empty-cell blocks, `H0` still matches as 1 stable row).
     **2 small residuals left unfixed (different root cause each, not chased further — diminishing
     returns)**: (a) `"Cook Islands (the) CK"` — PyMuPDF itself fused the country name and its ISO
     code into ONE raw text line at the Module 1 extraction level (confirmed in the raw JSON), not
     a Module 2 grouping bug; (b) ~4 rows come from numbered-footnote text (Croatian Kuna→Euro and
     Sierra Leone SLL currency-transition notes) bleeding into the table right at its boundary with
     the next table — a different problem category (narrative footnote at a table edge, not a
     wrapped key-column name). Full coordinate-level trace and reasoning in `local_memory/NOTES.md`.
   - **Module 4 (Detección de cambios) implemented and validated (2026-08-12).**
     `poc/base_ii_clearing_data_codes/04_deteccion_cambios/detect.py`. Purely deterministic (no AI
     yet — that's Module 5, which will consume this module's output). Turns Module 3's
     already-matched tables/rows into a flat typed change list: table-level `table_added`/
     `table_removed`/`table_renamed`; row-level `code_added`/`code_removed`/`code_content_changed`
     (cell-by-cell diff, skipping the code column, using `difflib.SequenceMatcher` with the same
     0.98 similarity threshold the reference pipeline's Stage 5 uses to discard pure
     reformatting/whitespace noise — genuine differences pass through un-classified, since
     real-change-vs-reword judgment is explicitly deferred to Module 5); plus a
     `duplicate_code_warning` passthrough from Module 3's already-detected duplicate codes.
     Required a small Module 3 addition: `header_a`/`header_b` added to each matched table's output
     (wasn't there before) so Module 4 can label which column changed by name.
     Validated by reading actual diff content, not just counts: confirmed genuine, meaningful
     business changes surfaced correctly — e.g. `Business Application IDs` code `MI` description
     changed from "Merchant Initiated Money Transfer" to "Merchant Initiated Faster Refund", and
     `Maximum Credit and Debit... POS Transaction Limits` codes A-D show real limit increases (e.g.
     `USD$249,999.99`→`USD$749,999.99`). All `table_renamed` fuzzy matches across every pair are
     the already-known glossary-gap noise, not new findings. Output at
     `data/04_deteccion_cambios/<edition_a>_to_<edition_b>.json` for all 8 pairs.
   - **Ollama set up (2026-08-12)** for Module 5: installed via the official Linux script inside
     WSL2 Ubuntu (no NVIDIA GPU detected, systemd already enabled in `/etc/wsl.conf` so it runs as a
     normal systemd service on `127.0.0.1:11434`). Model `qwen3:4b` pulled (2.5GB, matches the
     reference pipeline). ~10-11s per generate call on CPU once warm. **Gotcha**: `qwen3:4b` has
     "thinking" mode on by default — with `format:"json"` but without `"think": false`, the JSON
     lands in the response's `thinking` field instead of `response`, breaking any parser expecting
     `response`. Fix is passing `"think": false` in the `/api/generate` payload.
   - **Module 5 (Interpretación de cambios con IA) implemented (2026-08-12).**
     `poc/base_ii_clearing_data_codes/05_interpretacion_cambios_ia/classify.py`. Only
     `code_content_changed` entries from Module 4 go to the LLM — structural decisions
     (added/removed/renamed) stay fully deterministic and pass through untouched, same
     separation-of-concerns principle as the reference pipeline's Stage 6. Uses 3 categories
     (`business_rule_change`, `editorial_reword`, `extraction_noise`), deliberately dropping the
     `structural_change` 4th category proposed earlier in this file's history — reasoning: at the
     row level of a code-lookup table, anything "structural" (code added/removed, table renamed) is
     already deterministic and never reaches this classifier, so a 4th category here would be
     ambiguous with no real case to use it; revisit if Module 5 gets built for a Type A manual where
     a field-length change is genuinely "structural" in a way a code-table row change isn't.
     Ported the reference pipeline's `detect_disappeared_content` safety net as
     `_find_disappeared_content`: if the LLM says `editorial_reword`/`extraction_noise` but a 5+
     word chunk of the old text has no match in the new text (via word-level
     `difflib.SequenceMatcher` delete-opcodes), the LLM's label is overridden to
     `business_rule_change` and logged (`safety_net_override`/`ai_original_category`).
     Validated on a small batch (6 items) before running the full 312: the LLM correctly classified
     real Visa naming changes (`China`→`Mainland China`, `Taiwan (Province of China)`→`Taiwan` as
     `business_rule_change`) but got 2 cases wrong — `CROATIA`'s currency code `'191'`→`'1911'` and
     `SIERRA LEONE`'s `'SLL'`/`'694'`→`'3'` were misclassified as `business_rule_change` when they're
     actually data corrupted by the already-known footnote-bleed issue (see
     [[pending-bug-fixes]] item 3, priority raised because of this finding — it corrupts real
     matched-row content, not just spurious row counts). Full batch (8 pairs × ~312 items, ~50min on
     CPU) launched in the background — check `local_memory/NOTES.md` for the outcome once it lands,
     since this entry was written before that run finished.

     **UPDATE — full batch completed (8 pairs, 312 items).** Final distribution:
     `business_rule_change`=193 (62%), `editorial_reword`=105 (34%), `extraction_noise`=14 (4.5%);
     safety net fired 11 times (~3.5%). Spot-checked quality post-run: correctly told apart pure
     bullet-glyph formatting changes (old "l" bullets vs new round-bullet glyph, same content) from
     real content changes across multiple `Retired Chargeback Reason Codes` rows. ~7 of the 11
     safety-net overrides caught genuinely substantive disappeared content; ~4 (recurring `H0`/`HZ`
     codes) fire on bullet-list rows where the "disappeared content" evidence is just repeated
     bullet glyphs with no real text — final classification still reasonable in practice, but the
     saved evidence isn't useful for a human report. Logged as a new very-low-priority cosmetic item
     in [[pending-bug-fixes]] (item 4). Output at
     `data/05_interpretacion_cambios_ia/<edition_a>_to_<edition_b>.json` for all 8 pairs.
   - **Module 7 (Reporte de cambios) implemented (2026-08-12) — Module 6 (Validación con
     Plataforma STD) skipped for now**, per explicit user direction; it stays tentative/undefined
     from the original plan. Module 7 consumes Module 5's output directly.
     `poc/base_ii_clearing_data_codes/07_reporte_cambios/report.py` generates one Markdown report
     per edition pair + an `index.md`. Design principle: not all changes deserve equal weight in a
     human-facing report — `code_content_changed` with `ai_category == business_rule_change` leads
     with full old/new text + the AI's reason; `editorial_reword`/`extraction_noise` go in a
     compact appendix (code+column+ratio only, no repeated text); table/code added/removed get
     their own sections; `duplicate_code_warning` and `safety_net_override` counts become a
     "reliability caveats" section at the end. Abnormally long table titles (>80 chars, almost
     always the known glossary-gap artifact) are visually truncated, not hidden.
     Validated by reading the actual generated report for the highest-volume pair
     (`20250412→20251018`): confirmed genuine, externally-verifiable business changes — Sierra
     Leone's currency code changed `SLL`→`SLE` (the real 2022 leone redenomination), Curaçao/Sint
     Maarten changed `ANG`→`XCG` (the real 2025 Caribbean guilder replacement) — both correctly
     surfaced and explained by the LLM from the text diff alone, no historical context given.
     **2 new data observations surfaced while reading the report (not code bugs, not fixed)**: (a)
     `CROATIA`'s currency code is corrupted (`'9782'` instead of `'978'`) as late as edition
     `20250412`, only resolving in `20251018` — suggests the footnote-bleed corruption
     ([[pending-bug-fixes]] item 3) may span more editions than the single `20230415` occurrence
     originally scoped; not investigated further, noted as an extension of that same item. (b) the
     LLM occasionally mistypes a digit when restating a large number inside its Spanish `ai_reason`
     prose (e.g. "USD$749,9.99" instead of "USD$749,999.99") — the actual `old`/`new` values shown
     in the report always come from source data, never regenerated by the LLM, so the diff itself is
     always accurate; only the explanatory sentence can have a stray digit typo. Cosmetic, very low
     impact, logged as [[pending-bug-fixes]] item 6.
     Output: `data/07_reporte_cambios/<edition_a>_to_<edition_b>.md` (8 files) + `index.md`.
     **This completes an end-to-end validated pipeline (Modules 1-5, 7) for
     `base_ii_clearing_data_codes`** — raw PDF to a human-readable change report.
   - Start with Type A (the project's central target: field Position/Length/Format grids, e.g.
     `base_ii_clearing_interchange_formats_tc_01_to_tc_49`'s `151-168 Reserved`) once this first
     manual's POC (`base_ii_clearing_data_codes`, Type B) is far enough along to validate the
     module boundaries generalize.
2. **Sub-structure numbering patterns (TC, TCR, CP, etc.) per manual family** — not formally
   catalogued as a standalone deliverable yet, though largely surfaced as a side effect of the
   content-shape sampling. Should get finalized once the Stage 2 block classifier is designed.
3. **The "chain-shift" matching problem** (a field's length change shifts every subsequent field's
   position within the same TCR) — proposed mitigation (ordinal position within TCR as a secondary
   anchor) still untested against real consecutive editions. Needs design work once matching
   (Stage 3-4) is tackled — not before Stage 1/2 parsing exists.
4. **Type H change category missing from the 8 proposed diff categories** — field-usage-by-message-
   type matrices (M/C/O/C+/C- per message) found in `base_i`'s technical manual imply a change type
   not yet in the list (e.g. `field_usage_requirement_changed`). Needs to be added when Stage 5
   (diff) categories are finalized.

**How to apply:** Don't re-derive the closed items above — read
[[reference-pipeline-vs-technical-manuals]] for the full catalogue and evidence if detail is
needed, and `local_memory/NOTES.md` in the repo for the complete session-by-session narrative. As of
2026-08-12, the FULL pipeline (Modules 1-5, 7) is implemented and validated end-to-end for
`base_ii_clearing_data_codes` — raw PDF through a human-readable Markdown change report. Module 6
(Validación con Plataforma STD) was explicitly skipped/deferred, still tentative/undefined. Don't
re-run any of the module 1-5/7 investigations or rebuild what already exists. Known open items, all
low priority, tracked in [[pending-bug-fixes]] (full detail in repo's `local_memory/TODO.md`): the
deprioritized glossary gap, a Module-1 PDF text-fusion quirk on 1 row, the footnote-bleed
data-corruption issue (now suspected to span more than the single `20230415` edition originally
scoped), a Module 5 safety-net evidence-text cosmetic issue, and an LLM digit-typo quirk in
`ai_reason` prose.

**Second manual chosen and started (2026-08-12): `base_ii_clearing_edit_package_messages`.** User
picked it explicitly and asked to go **module by module with a pause/check-in at each step**, not
repeat the run-1-through-7-in-a-row approach used for the first manual. This is Type F content
(already catalogued: "fichas" of validation/error codes, same repeated-label pattern as Type A's
Field ID cards but different vocabulary — `CÓDIGO` → `TÍTULO` → `Description:` → `Action:` →
`Transaction Types:` with `●` bullets) — NOT a multi-column grid like `base_ii_clearing_data_codes`'s
Type B, so it likely won't need the same geometric row/cell reconstruction Module 2 needed there;
probably closer to direct regex-over-text parsing, but that's a Module 2 decision, not made yet.
**Module 1 done**: `poc/base_ii_clearing_edit_package_messages/01_ingesta_parseo/ingest.py`, nearly
identical to the first manual's (raw extraction doesn't depend on content shape — same
line-level-not-block-level `page.get_text("dict")` approach, same reasoning). Ran cleanly across all
9 editions (333-347 pages, ~12,100-12,630 lines each — notably bigger than the first manual's
~150-158 pages). Verified against a real page (p.50, `20260418`) that the Type F pattern holds
exactly as catalogued. Header/footer bands are different from the first manual's and NOT calibrated
yet (needed before Module 2's noise filter). Full detail in `local_memory/NOTES.md`.
**Module 1 now fully closed (2026-08-12), all the "not done yet" items below resolved.** Document
structure catalogued (346 pages, edition `20260418`): TOC is huge (p.5-38, every code gets a TOC
line); Chapter 1 (p.39-40) narrative overview; **Chapter 2 "Validation Messages"** (p.41-269) has
the `V####` fichas with a `Transaction Types:` bullet section; **Chapter 3 "Log Messages"**
(p.270-346) has `######-X` fichas (X = severity letter I/W/C/E/S/A, confirmed against a small
embedded 2-col "Message Severity Levels" table) — same ficha shape as Chapter 2 but WITHOUT
`Transaction Types:`; last ~3 pages are a small glossary (same low-priority category as
[[pending-bug-fixes]] item 1, much smaller here).
**Key design finding**: the real "is this a code line" signal is NOT text-content regex — it's
**typography**. Code lines use font size exactly 20.0pt (body text is 9-10.5pt, chapter/section
headings are 26/30/40pt — zero collision), ficha title lines use the monospace font
`CourierNewPS-BoldMT` (unique to titles, nowhere else in the doc). Validated with 0 false
positives/negatives across a full edition (952/952 lines at `max_font_size==20.0` matched a
case-insensitive code pattern) — a naive content regex has real false positives (a wrapped MCC list
produces a standalone `"5969"` line matching a naive code pattern) and a real false negative
(`"v0720"` uses a lowercase `v`, a genuine source typo, still caught by the font signal). **Font
name is NOT stable across editions** — code-line font changed from `SegoeUI-Bold`
(`20220423`-`20230415`) to `OpenSans-Bold` (`20231014` onward, a Visa rebrand mid-series) while
staying at size 20.0pt throughout; the ficha-title font (`CourierNewPS-BoldMT`) never changed. So
Module 2's parser must key off font SIZE, not font name.
Header/footer bands calibrated (different from the first manual, don't reuse those constants):
header `y1<=41` (2 lines, second one is a variable running section title, unlike the first manual's
fixed one), footer `y0>=758.9`. Chapter-first pages lack the running header (the big chapter title
occupies that space) but it starts below y0=41 anyway so the Y-band filter still works.
**Module 1 code fix**: added `max_font_size` (max across the line's spans, not average — a line can
mix a bold "Description:" label at one size with regular body text) and `fonts` (sorted distinct
font names) per line to `ingest.py` — this manual's Module 1 needed it, the first manual's didn't
(its signal was purely geometric), so this is a deliberate per-manual difference, not copy-paste.
Regenerated all 9 editions with the new schema.
**Module 2 also implemented and closed (2026-08-12).**
`poc/base_ii_clearing_edit_package_messages/02_normalizacion_bloques/normalize.py`. Design:
since this manual is single-column running text (not a multi-column grid like the first manual),
no Y-band geometric row reconstruction is needed — PyMuPDF's natural per-page order already matches
reading order once header/footer noise is filtered (verified: unfiltered, header/footer lines land
at the END of each page's `order` sequence, not the start — filter before trusting order, don't
re-sort by (y0,x0) like the first manual needed). **The whole document is processed as ONE
continuous stream with no per-page state reset** — deliberately applying the lesson from the first
manual's `"H0 (continued)"` cross-page bug: if `Description:`/`Action:` text is cut by a page break,
it just keeps accumulating regardless of page number, because there's no state boundary at a page
break at all. Avoids that whole bug class by construction instead of hitting it and fixing it later.
Block types: `card_header` (code+title), `field` (Description/Action), `bullet_list` (Transaction
Types items), `paragraph` (catch-all: TOC leftovers, legal notice, chapter/section headings,
glossary, the small embedded "Message Severity Levels" table).
**5 real edge cases found and fixed, each validated against real data before moving on** (full
detail in `local_memory/NOTES.md`): (1) `Transaction Types:` sometimes has its value INLINE on the
same line (`"...: All Financial Drafts"`, `"...: n/a"`, 195 real cases) instead of bullets — was
being discarded, now captured as the first item. (2) Titles can wrap to 2+ lines — was truncating to
just the first line. (3) 2 of 952 codes have their title in `OpenSans-Bold` instead of the monospace
title font (real source-PDF inconsistency) — fixed by treating the line immediately after a code as
always the title regardless of font, using the monospace font only to detect continuation. (4) the
monospace title font has 3 real variants (Bold/BoldItalic/Italic, the italic one used to emphasize a
placeholder like "XXXX" inside a title) — fixed by prefix-matching `"CourierNewPS"` instead of exact
name. (5) 1 of 952 codes (`V9003`) uses font size 26.0 instead of 20.0 — the SAME size used by
section subheadings ("Data Entry Messages", etc.) — found by cross-checking every captured code
against the edition's full TOC listing (the only way this systematic check would have caught it, not
manual sampling). Fixed narrowly: accept size 26.0 as a code ONLY if the text also matches the code
content pattern (a heading never does, zero real collision risk); also added a general rule that any
line with `max_font_size > 15` that isn't a code always closes out whatever block is active (body
text is always 9-10.5pt) — without it, "Data Entry Messages" was silently merging into the previous
bullet item's text. Also fixed a 6th, smaller case: `"Transaction Type:"` (singular) alongside the
usual plural, one real occurrence.
**Not a bug, left as-is**: code `V0545` has a literally duplicated `Action:` field in the source PDF
itself (verified in raw text) — captured faithfully as 2 separate `field` blocks, which is correct;
Module 2 shouldn't silently deduplicate real (if sloppy) source content.
**Final validation, all 9 editions, checked against each edition's full TOC listing (not a sample)**:
0 TOC codes missing from capture, 0 missing titles, 0 empty fields, 0 empty bullet_lists, 0 duplicate
codes. Module 2 for this manual is now considered closed and solid.

**Module 3 (Emparejamiento de bloques) implemented and validated (2026-08-13)** for this manual —
`poc/base_ii_clearing_edit_package_messages/03_emparejamiento_bloques/match.py`. Simpler than the
first manual's Module 3: no "table" level here, just a flat list of ~933-953 code fichas per
edition, matched by exact code only (no fuzzy title-matching needed — the code IS the ficha's full
identity, unlike a table title that can get renamed). `action` stored as a list (not a string) on
purpose, to preserve the known real duplicate-`Action:` case (`V0545`) instead of silently losing it.
**3 real Module 2 bugs found and fixed while validating Module 3's output against real content**
(not just structural counts) — same pattern as the first manual, where Module 3 was the point that
exposed Module 2 calibration bugs because it's the first place 2 editions' real content gets
compared: (1) `FOOTER_Y_MIN=758.9` was 0.1pt too tight — real footer lines (date/page-number) sit as
low as `y0=758.8` in several editions and were leaking into whatever field was active, corrupting
text (confirmed real example: `"...return message YYYY. 23 April 2022 259"`). Recalibrated to 750.0
after confirming real body content never exceeds `y0=709.2` and real footer never drops below 758.8
across all 9 editions. (2) `HEADER_Y_MAX=41` had only been calibrated against the newest edition —
the running section-title header line (`y1=42.5` in 5 of 9 editions, `20231014`-`20251018`) leaked
through and corrupted content at page boundaries (e.g. `"...Reversals Validation Messages"`).
Recalibrated to 44.0. (3) `BULLET_GLYPHS={"●","■"}` had only been validated against the newest
edition too — the other 8 of 9 editions use a different bullet glyph that PyMuPDF extracts as a bare
`"l"` (symbol font, size 8.0/6.4pt, never body size 10.5pt — zero real collision risk), which wasn't
recognized, so `Transaction Types` items fused into one giant string instead of staying separate
list items. Fixed by adding `"l"` to `BULLET_GLYPHS`. This one was the highest-volume: 383 of 428
"changed" fichas in the first edition pair had only this problem. All 3 fixes live in Module 2's
`normalize.py`, not Module 3 — same as the first manual's `"H0 (continued)"` bug, Module 3 is where
this project's Module-2 calibration bugs keep surfacing, not where they live.
Post-fix validation across all 9 editions: 0 footer/header-tainted fields, same ficha counts per
edition (fixes don't touch code/title identity), 0 duplicates. Re-ran Module 3: add/remove counts
unchanged as expected; "changed" matched-ficha counts dropped sharply and became believable (428→4
on the first pair, 539→23 on the last pair which straddles the glyph-format transition). Read the
actual output (not just counts): what's left is a believable mix of (a) known cosmetic noise — bullet
sub-lists embedded *inside* `Description`/`Action` field text (not the dedicated `Transaction Types`
`bullet_list` block) still carry the edition's literal glyph inline, consistently across all 9
editions including the newest — not a bug, Module 2 never structures those; deferred to Module 4's
similarity-threshold filter, same role as the first manual's Module 4 — and (b) genuine content
changes (e.g. `V0173`: "less than" → "less than or equal to" with its transaction-types list and
title updated to match; `V0180`: real typo fix "Credti"→"Credit"). Output at
`data/03_emparejamiento_bloques/<edition_a>_to_<edition_b>.json` for all 8 pairs. Full narrative in
`local_memory/NOTES.md` ("2026-08-13 — Módulo 3... y 2 bugs reales de Módulo 2" — despite the title
saying 2, it's 3 fixes, see the entry).

**Module 4 (Detección de cambios) implemented and validated (2026-08-13)** for this manual —
`poc/base_ii_clearing_edit_package_messages/04_deteccion_cambios/detect.py`. Same separation-of-
concerns principle as the first manual's Module 4 (structural add/removed already resolved by
Module 3, pass through untouched; Module 4 only decides whether a matched ficha's content actually
changed, still 100% deterministic, no AI yet). Key design difference: the first manual's Module 4
diffs table cells by column INDEX (variable per table); this manual has no tables/columns — every
ficha has the same fixed 4 named fields (`title`, `description`, `action`, `transaction_types`), so
Module 4 diffs by field NAME instead. Each field collapses to one canonical string (lists joined with
a space; `transaction_types` — a list of lists, one per `bullet_list` block — flattened to one list
of items first, then joined with `" | "`), then compared with the same mechanism and same threshold
as the first manual (`difflib.SequenceMatcher`, 0.98) to separate formatting noise from real content
changes — validated against 4 known real cases from this manual before trusting the threshold:
whitespace-only diffs (ratio ~0.99) correctly discarded, genuine changes (`V0173` "less than"→"less
than or equal to", ratio 0.948; `V0180` typo fix inside a transaction_types item, ratio 0.927)
correctly kept.
Ran cleanly across all 8 pairs, believable summary, no new bugs surfaced (unlike Module 3, which
found 3 real Module 2 bugs — this validation pass came up clean, a good signal the earlier fixes
were complete). Verified by reading real content, not just counts: the highest-volume pair
(`20221015→20230415`, 33 field-level changes across 15 fichas) turned out to be mostly ONE real
business rename ("Installment Payment Indicator" → "Payment Indicator") propagated consistently
across ~9 related Argentina-NNSS fichas (`V1232`-`V1245`), plus a spelling normalization
("zeroes"→"zeros") riding along — exactly the kind of coherent, cross-ficha-consistent real change a
human reviewer would want surfaced clearly. Also correctly caught `V1008` (title+description almost
fully rewritten, ratio ~0.5) and `V0313` (transaction_types entirely different, ratio 0.137) as
genuine substantial changes, not filtered as noise. Zero footer/header/glossary contamination in any
reported `old`/`new` value (checked programmatically across all 8 files). Output at
`data/04_deteccion_cambios/<edition_a>_to_<edition_b>.json` for all 8 pairs.

**Module 5 (Interpretación de cambios con IA) implemented and validated (2026-08-13)** for this
manual — `poc/base_ii_clearing_edit_package_messages/05_interpretacion_cambios_ia/classify.py`. Same
design as the first manual's Module 5 (Ollama local, `qwen3:4b`, forced JSON, `think:false`, temp 0;
same 3 categories; same `_find_disappeared_content` safety net, 5+ word threshold). Only real design
difference: no "table" level in the prompt — gives the LLM the ficha's title as fixed context
(from `title_b`) plus which named field changed, instead of table+column.

Smoke test (6 items) surfaced one low-priority LLM quirk: ficha `V0407` has the same real business
change reflected in both `title` and `description` fields ("IND EQUALS B OR P"→"IND EQUAL TO P" —
value B stops being accepted); `description` classified correctly (`business_rule_change`), `title`
classified wrong (`editorial_reword`, with a reason that describes the change accurately but reaches
the opposite conclusion) — safety net didn't catch it since only ~3 words disappeared (below the 5-
word threshold). Not fixed (known small-model limitation, same category as the first manual's digit-
typo quirk) — logged as [[pending-bug-fixes]] item 7, no info actually lost since the same fact is
captured correctly in the ficha's other field.

**A 4th real Module 2 bug found via the full-batch run (not the smoke test)**: ficha `V0545`
triggered the safety net (`safety_net_override=true`) with disappeared content
`"Action: Enter the correct numeric value for this field."` in its `description` field. Root cause
(confirmed via raw Module 1 bbox): in 8 of 9 editions (all but the newest, `20260418`, where the PDF
layout already puts it on its own line), the `Action:` label sits glued to the END of the
`Description:` line in the source PDF (tight layout, no line break between them) with no text after
it on that physical line — `LABEL_PATTERN.match()` only checks the label is at the START of a line,
so it matched `Description:` correctly but swallowed the trailing `Action:` into Description's own
text. Confirmed as the ONLY real occurrence across all 9 full editions (0 second-label occurrences
anywhere else). Fixed generally (not hardcoded to this ficha's code): new `TRAILING_LABEL_PATTERN`
splits off a dangling second label at the end of a matched label's captured remainder, starting a
second block instead of absorbing it as content.
Re-ran Modules 2→3→4→5 end to end after the fix: Module 2 gained exactly 1 block per affected
edition (+8 total), 0 duplicates/empty fields; Module 4's `ficha_content_changed` count for the pair
crossing the corrupted→clean transition (`20251018→20260418`) dropped from 11 to 9 (the spurious
`V0545` diff disappeared); Module 5 re-run on the corrected 59 items (down from 61) came back with
`safety_net_override=0` across all 8 pairs — confirms `V0545` was the only real corruption the
safety net was compensating for.

**Final result, all 8 runs**: `business_rule_change`=39, `editorial_reword`=20, `extraction_noise`=0
(unlike the first manual's ~4.5% `extraction_noise` — makes sense, this manual's known Module 2 bugs
are now fixed, so there's no residual extraction noise reaching the classifier the way the first
manual's still-unfixed footnote-bleed issue does). Validated by reading real content from the
highest-volume pair post-fix (`20251018→20260418`): a coherent real business change ("cashback amount
must be less than" → "...less than or equal to...") correctly identified and consistently classified
across 3 related fichas (`V0173`, `V0188`, `V1098`) through their `title`/`description`/`action`
fields; known embedded-glyph cosmetic noise (`V1180`, `"l"` vs `"●"` bullets inside an `action` field,
ratio 0.972) correctly classified as `editorial_reword` with an accurate reason. Output at
`data/05_interpretacion_cambios_ia/<edition_a>_to_<edition_b>.json` for all 8 pairs.

**Module 7 (Reporte de cambios) implemented and validated (2026-08-13)** for this manual —
`poc/base_ii_clearing_edit_package_messages/07_reporte_cambios/report.py`. Same design principle as
the first manual's Module 7 (business_rule_change leads with full text, editorial_reword/
extraction_noise in a compact appendix, structural add/remove in their own sections, reliability
caveats at the end) — Module 6 stays skipped/tentative for both manuals. 3 design differences, all
from this manual having no "table" level: (1) groups by ficha code, not table — a ficha can have
several fields changed at once and it's almost always the same business story told across multiple
fields (e.g. `V0173`: title+description+transaction_types changed together), so grouping under one
ficha heading reads better than listing them loose; (2) Module 4/5's changes don't carry the ficha's
title (wasn't needed for their work) — the report loads it separately from Module 3's output, reusing
the same `title_by_code` pattern Module 5 already uses for its LLM prompt; (3) no
table_added/removed/renamed — only ficha_added/ficha_removed — and duplicate_code_warning is one
document-wide notice, not a per-table list.
Ran cleanly across all 8 pairs including the known 0-change edge case (`20250412→20251018`) —
empty sections render cleanly. Validated by reading the highest-volume report in full
(`20221015→20230415`, 19 business changes): coherent end to end — the real "Installment Payment
Indicator"→"Payment Indicator" rename reads consistently across its ~9 related fichas, each grouping
its affected fields under one heading; the already-documented `V0407` quirk (same fact correctly
classified in `Description`, wrongly in `Título`) shows up in the real report exactly as predicted —
not a new surprise. Output at `data/07_reporte_cambios/<edition_a>_to_<edition_b>.md` (8 files) +
`index.md`.

**This completes the full pipeline (Modules 1-5, 7) for `base_ii_clearing_edit_package_messages`**,
same milestone already reached for the first manual. Module 6 (Validación con Plataforma STD) stays
deliberately skipped/tentative for both manuals, undefined. Across this manual's Modules 3-5, 4 real
Module 2 bugs were found and fixed (footer/header bands calibrated only against the reference
edition, the pre-rebrand `"l"` bullet glyph never recognized, and a trailing `"Action:"` label glued
to the end of a `Description:` line) — recurring pattern worth remembering for any future manual:
each bug hid in a calibration/heuristic validated against only ONE edition (usually the newest),
never against the full 9-edition corpus — validate extraction/normalization signals against the whole
corpus before trusting them, not just the reference edition.

**3rd manual chosen and started (2026-08-13): `base_ii_clearing_interchange_formats_tc_01_to_tc_49`**
— the project's original Type A target (Position/Field/Length/Format grids, the "Reserved" field use
case). Source at `visa/src/base_ii/base_ii_clearing_interchange_formats_tc_01_to_tc_49/`, 9 editions,
same filename pattern as the other 2 manuals.

**Module 1 implemented and validated** —
`poc/base_ii_clearing_interchange_formats_tc_01_to_tc_49/01_ingesta_parseo/ingest.py`, a deliberate
copy of the first manual's Module 1 (line-level extraction via `page.get_text("dict")`, bbox+text
only, no `max_font_size`/`fonts`) — same principle already applied for the second manual: don't
speculate what Module 2 will need, start minimal, add fields only when real Module 2 design work
demands it. There's a hint (not a decision) that this manual may get away with pure geometry like the
first manual rather than needing a typographic signal like the second: the earlier cross-manual
mapping ([[pending-bug-fixes]] item 6) already confirmed this table type's `Format` column
(`AN`/`N`/`ANS`/`DX`/`UN`) matches the `CODE_LIKE` pattern already used in the first manual — to be
confirmed only once Module 2 is actually built.
Ran cleanly across all 9 editions: 883-940 pages (noticeably bigger than the other 2 manuals — first
was ~150-158 pages, second ~333-346), 54,591-57,960 lines, consistent page size (612×792pt, US
Letter) throughout, no mixed-size warnings.
Validated against real content already known from an earlier investigation (before any code existed
for this manual): the row `41 1 AN Unattended Acceptance Terminal Indicator` at p.371 of edition
`20260418` extracts correctly line-by-line, one line per CELL (header cells `Position`/`Field`/
`Length`/`Format`/`Contents` as separate lines; then `41`/`1`/`AN`/`Unattended Acceptance Terminal
Indicator` as 4 separate lines of that row, each with its own bbox) — exactly the granularity Module
2 will need to reconstruct rows via Y-band overlap, same approach that already worked for the first
manual.
Skimmed the TOC (p.5-6) to understand the macro-structure before designing Module 2: confirms the
sub-structure numbering already anticipated in the roadmap (chapters by Transaction Code — TC 01/02/
03, TC 04, TC 05... — each with TCR sub-sections, e.g. "TC 05 - TCR 0", "TC 05 - TCR 1 Additional
Data", "TC 05 - TCR 2 Argentina"). Minor TOC-only quirk noted, not a bug: some TOC lines have a
truncated/split-off trailing page number — same category of TOC noise the other 2 manuals already
discard via their dot-leader filter in Module 2, not investigated further since TOC content gets
fully discarded anyway.

**Module 2 implemented and validated (2026-08-13)** — the most complex Module 2 of the 3 manuals so
far. Went back and added `max_font_size`/`fonts` to Module 1 first (same as the second manual — only
decided once real Module 2 design work showed 5 distinct typographic tiers were needed to separate
chapter/section/table/card/body). Real finding: every TC/TCR section mixes TWO content shapes, not
one — a "Record Layout" grid (Position/Field Length/Format/Contents, same Type B geometric Y-band
reconstruction as the first manual) followed by "Edit Criteria" field cards (name +
Positions:/Length:/Format: on the left, Description:/Note:/Values:/Mapping: on the right — a 2-column
form, NOT a grid; row-grouping by Y-band there produces arbitrary pairings, confirmed with real data,
so it's handled by a sequential state machine instead). Both describe the same fields in different
detail; Module 2 keeps them as separate block types (`table_row` / `field_card`), linking deferred to
Module 3 per the project's established Module 2/3 responsibility split.

**8 real bugs found and fixed** while validating against real data (not during upfront exploration):
(1) grid header column order — `Field`+`Length` are ONE column (2-line wrapped header), not two, each
data row only ever has one number between Position and Format; (2) page-number noise detection
assumed it's always the page's last line in reading order — false, `Visa Confidential` sometimes sorts
after it due to a 0.1-1.1pt higher y0, so detection was recalibrated to content+position instead of
list position; (3) the table title re-declared at the top of each continuation page was leaking into
the grid's row buffer since grid mode never explicitly closed until the next header — fixed by exiting
grid mode on any line that isn't the real data-row font size (9.0pt); (4) a field's Description shares
a Y-row with its own NAME line, so it arrives in the stream BEFORE that field's own `Positions:`
trigger — needed a `pending_right` buffer to hold it until the field card is created; (5) symmetric bug
— field N+1's Description (sharing a row with N+1's name) was gluing onto field N's still-open card
(N doesn't close until ITS OWN next `Positions:`) — fixed with a `same_row_as_next_name` check
redirecting to `pending_right`, needed for both labeled lines AND their unlabeled continuation
wraps (a second, separate fix once the first one only covered the labeled case); (6) `Description`
sometimes has NO colon after it in the source PDF (confirmed real via character codes, 9 cases,
clustered on one page) — loosened the right-side-only regex to accept a colon OR whitespace as
separator, deliberately NOT loosened on the left side (`Positions:`/`Length:`/`Format:`) since a real
field is literally named `"Format Code"` there and loosening would misread it as the `Format:` label;
(7) Description sometimes has NO label at all, just bare text in the right column — detected via the
same same-row-as-next-name signal, treated as an implicit description; (8) a wrapped `Contents` cell's
second line sometimes doesn't Y-overlap its row (same quirk already solved in the first manual's
Module 2) — added a small-gap fallback (~0pt for a wrap vs ~8.3pt for a real new row in this manual).
Recurring pattern across bugs 2,3,4,5,7,8: two content types sharing an ambiguous geometric signal
(same Y-band, same small gap) needing an ADDITIONAL signal (font size, or "what's currently in the
other buffer") to disambiguate — no single simple geometric heuristic was ever enough alone.

Final validation across all 9 full editions (not a sample): 0 `table_row` blocks with a wrong cell
count, 0 unexpected `table_header` cells, 0 `field_card` with empty name, 0 with empty positions, 0
grid Position cells failing the position/range pattern (hyphen or en-dash). Only 2 residual anomalies
— both confirmed genuine dirty source content via raw PDF text, not bugs: a duplicated label
`"Positions: Position: 122–123"` and a stray trailing hyphen `"Positions: 24-27-"`, both single
occurrences, left as-is (same precedent as other "faithfully preserve real if sloppy source content"
cases in this project, e.g. manual 2's duplicated `V0545` Action field). Also validated by reading
real content across several distinct areas (TC 33.A CP01 TCR0/TCR1, TC 05 TCR2 Chile/Brazil —
confirmed the project's central `Reserved`-field use case reads correctly, chapters near the end of
the document TC 48/TC 49) — all coherent with the source PDF in each case.

**Chain-shift investigated empirically (2026-08-13), before designing Module 3.** User asked to
clarify what chain-shift meant and whether it had already shown up in the first manual — it hadn't:
it was flagged during the original design conversation (2026-08-11, before any code existed) as a
problem anticipated specifically for Type A manuals with chained positional fields; neither the first
manual (Type B, rows keyed by business code) nor the second (Type F, no positional layout at all)
could ever hit it. Compared row positions across common sections in all 8 consecutive edition pairs
(2173 section comparisons): 2172 of 2173 showed zero shift — most position changes are actually the
"`Reserved` (always at the record's end) splits into a new field + a smaller `Reserved`" pattern,
which never shifts anything because the new field is carved from the START of the existing Reserved
range. Found exactly ONE real chain-shift in the entire available edition history (`TC 33.A - CP 12
TCR 4 Gateway Data, continuation`, pair `20240413→20241019`: a field grew from 9 to 10 bytes and
shifted the next 2 fields). Presented this evidence to the user via AskUserQuestion — given 0.05%
real-world frequency, mitigate now with the originally-proposed ordinal-position secondary anchor, or
match by exact position with no mitigation? **User picked the recommended option: no mitigation** —
same stable-key-matching principle already used in the other 2 manuals; the rare case is logged as a
low-priority TODO ([[pending-bug-fixes]] item 8) instead of adding complexity now.

**Module 3 implemented and validated (2026-08-13)** —
`poc/base_ii_clearing_interchange_formats_tc_01_to_tc_49/03_emparejamiento_bloques/match.py`.
Reconstructs TC/TCR sections (delimited by `section_heading`, already explicit from Module 2 — unlike
the first manual, no need to re-declare/coalesce titles via `paragraph` here) holding two PARALLEL
lists: grid rows and field cards. Deliberate design choice: does NOT link rows to cards within this
module — confirmed with real data that the relationship isn't always 1:1 (a composite grid field, e.g.
"Acquirer Reference Number" as one row spanning positions 27-49, can have one "parent" card plus 5
"child" cards for its sub-components, each with their own narrower position range) and linking them
would need extra logic not yet justified by the project's actual goal. Matched as two independent
parallel problems (rows vs rows, cards vs cards) — same pattern already used twice in the project (row
by code in the first manual, ficha by code in the second), now applied twice within one module.
Matching key: `Position`/`Positions`, normalized (unifies hyphen vs en-dash — confirmed empirically
zero real difference across all 8 editions, normalized anyway as cheap insurance). Sections matched by
exact title then fuzzy fallback (0.85 threshold, same as the first manual).

**One real Module 2 bug found while exploring data to design Module 3** (before writing any Module 3
code): found a section with massive position duplication (7 rows with `Position="1-2"`, etc.) during
an exploratory duplicate check. Root cause: a 3rd, smaller heading tier (20.0pt) existed alongside the
already-calibrated 26.0pt tier, used when one large section actually contains several independent
nested sub-records each with their own complete field layout and independent Position numbering (e.g.
"TC 33 - TCR 0 BASE II Dispute Financial Status Advice" nested inside "TC 33 - TCR 0 Commercial Choice
Select Reference Data Record"). Only 6 occurrences in the reference edition, confined to this one
section. Fixed in `normalize.py`: `SECTION_HEADING_FONT_MIN` (single value) replaced with
`SECTION_HEADING_FONT_SIZES = {20.0, 26.0}` (a set), with wrapped-title continuation now compared
against the exact size of the currently active heading instance rather than one global constant.
Re-ran Module 2: `section_heading` count went from 269 to 275 (269+6, exact), the massive duplication
disappeared. One legitimate (non-bug) duplication remains: `TC 39 - TCR 4 VDAS Forms Data, Exhibit Y
or Exhibit 3C` has rows with `Format="Group"` introducing mutually-exclusive alternative
sub-structures (e.g. "Lodging Merchant" vs "Vehicle Leasing Merchant", both at positions 12-68 since
they're different interpretations of the same byte range depending on form type) — confirmed genuine
by reading the source PDF, not fixed (the duplicate-detection warning is doing exactly its job, not
something to "fix away").

Ran cleanly across all 8 pairs: ~97-99% of sections matched by exact title per pair, 1-3 fuzzy matches
per pair (checked by hand, all believable real renames, e.g. adding "E" to a TCR range list, "TC
33"→"TC 33.B"). Validated by reading real content, not just counts: the project's central use case
(`Reserved` 150-168 in TC33.A CP02 TCR0 splitting into `Tap-to-Phone Indicator` at 150 + a smaller
`Reserved` 151-168) shows up correctly in both `rows_added`/`rows_removed` AND
`cards_added`/`cards_removed` in parallel, full field description captured intact. Duplicate detection
found the same stable set of 7 sections across all 8 pairs (doesn't vary by edition — confirms it's a
real structural feature of the source, not a variable extraction artifact). Output at
`data/03_emparejamiento_bloques/<edition_a>_to_<edition_b>.json` for all 8 pairs.

**Module 4 implemented and validated (2026-08-13)** —
`poc/base_ii_clearing_interchange_formats_tc_01_to_tc_49/04_deteccion_cambios/detect.py`. Same
separation-of-concerns principle as the other 2 manuals; diffs the two parallel lists (grid rows,
cards) per section independently, without unifying them (same principle as Module 3).

**New category `field_became_defined` — the project's central use case — implemented with 2
subtypes**, the second one found only after reading real Module 4 output, not during design: (1)
`subtype="split"` — a `Reserved` range splits into a new field + a smaller `Reserved`, positions
differ before/after (the case already seen in Module 3); detected deterministically from Module 3's
already-computed rows_removed/rows_added by finding a removed `Reserved` row whose range CONTAINS one
or more added rows, at least one starting at the same initial position with non-Reserved content. (2)
`subtype="renamed_in_place"` — sometimes the WHOLE `Reserved` range gets renamed to a real field
WITHOUT splitting (same position range in both editions, e.g. "TC 05 - TCR 2 Colombia": `5-16
Reserved` → `5-16 Tip Amount`) — Module 3 already matches this by exact position, so without this fix
it would've been buried as a generic `row_content_changed`/`card_content_changed`, losing exactly the
signal the project exists to catch. Detected directly on `rows_matched`/`cards_matched`
(`_reserved_transition`), checked BEFORE falling through to generic cell/field diffing. Added the
symmetric `field_became_reserved` too (a real field gets retired, its range becomes `Reserved`) — same
mechanism, though not the project's central use case.

Validated integrity across all 8 pairs (not a sample): for each pair, loose `row_added`/`row_removed`
counts PLUS the fields consumed by each `field_became_defined` (`subtype="split"`) reconciled EXACTLY
against Module 3's raw `rows_added`/`rows_removed` totals — same check for cards — confirming no
double-counting or dropped items from the split-consumption logic. Fixed 2 small things caught while
reviewing the code before running: an equality-based (`not in`) instead of identity-based check for
`remaining_reserved` (theoretical risk of wrongly excluding an item if two added rows had identical
cells by coincidence — switched to `is` comparison, no real case found affected but fixed as a
precaution), and a dead unused variable left over from an earlier draft.

Also validated by reading real content: the two known Module 3 examples
("renamed_in_place" for "TC 05 - TCR 2 Colombia" and "TC 33 - TCR 1 BASE II Clearing and Settlement
Advice") show up correctly classified, with the row AND card representations agreeing on exactly which
positions had a Reserved↔defined transition — a strong cross-validation signal since rows and cards
are matched by completely independent processes. Spot-checked 6 `card_content_changed` entries by
hand: all believable real business changes (e.g. genuine field rename "Token Assurance Level"→"Token
Assurance Method", "Deferred OCT Request Type"→"Service Processing Type" with matching description
rewrite). Output at `data/04_deteccion_cambios/<edition_a>_to_<edition_b>.json` for all 8 pairs.

**Module 5 implemented and validated (2026-08-13)** —
`poc/base_ii_clearing_interchange_formats_tc_01_to_tc_49/05_interpretacion_cambios_ia/classify.py`.
Same design as the other 2 manuals; field-name context resolved by reaching back into Module 3's
output (`_field_name_lookup`, same pattern as the second manual's `title_by_code`) rather than
touching Module 4's already-closed schema. Full run: 554 items across 8 pairs,
`business_rule_change`=301, `editorial_reword`=241, `extraction_noise`=12.

`safety_net_override` came back much higher than normal in 2 of the 8 pairs (19 and 33, vs the usual
0-1 seen in every prior run across the other 2 manuals) — investigated fully before closing the
module (same discipline as the rest of this session: an unusual signal doesn't get waved off just
because the mechanism is already validated elsewhere). Neither turned out to be a code bug: (1) pair
`20230415→20231014` — a genuine editorial change: several "Fleet Service" (`TC 05 - TCR 3`) fields
lost their enumerated `Values:` list, replaced by a cross-reference to another manual ("See BASE II
Clearing Data Codes for a listing of valid codes.") — confirmed in the raw source PDF, Visa really did
rewrite this section to stop duplicating the inline enumeration. (2) pair `20251018→20260418` — a
genuine source-PDF limitation confined to that one edition: the bold span rendering the word "Note:"
is flatly absent from the text layer PyMuPDF extracts for many cards in `20260418` specifically (the
rest of that note's text — italic/regular — extracts fine, just missing the label itself), so Module 2
has no trigger to capture it as a separate `note` field and it merges into `description` as plain
continuation instead. Quantified across all 9 full editions by counting literal `"Note:"`
occurrences: 274/274/274/274/274/272/273/273 across the first 8 editions, **216 in `20260418`** — a
~57-instance (~21%) drop unique to that edition. Not fixable in the pipeline (would need OCR, out of
scope) — logged as [[pending-bug-fixes]] item 9. In both cases, the safety net did exactly its job:
flagged real disappeared content for human review instead of letting it slip through silently. Output
at `data/05_interpretacion_cambios_ia/<edition_a>_to_<edition_b>.json` for all 8 pairs.

**Module 7 implemented and validated (2026-08-13)** —
`poc/base_ii_clearing_interchange_formats_tc_01_to_tc_49/07_reporte_cambios/report.py`. Same design
principle as the other 2 manuals, with one new priority: `field_became_defined`/
`field_became_reserved` come FIRST in the report, ahead of generic business changes — it's the
project's central use case, so it gets its own prominent section instead of being mixed in.
Content changes (`row_content_changed`/`card_content_changed`) with `ai_category ==
business_rule_change` are grouped by FIELD (section + position, using the `field_name` Module 5
already resolved), not by row and card separately, so the reader sees at a glance that the grid and
the card describe the same change. Deduplicates the row/card pair Module 4 emits for the same
`field_became_defined`/`field_became_reserved` event (by title+position, preferring the grid version,
noting when both confirm it) so the same event doesn't show up twice.

Ran cleanly across all 8 pairs. Read the full first-pair report end to end: the 3 Reserved→defined
transitions show up with full detail (split position, new field, remaining Reserved, confirmed in
both representations); the business-changes section surfaced a genuinely new finding not seen during
earlier module validation — Visa modernized terminology consistently across dozens of unrelated
fields, replacing "chargeback or representment" with "dispute or dispute response" in field
descriptions (spanning `TC 38`, `TC 39`, multiple TCRs) — correctly classified as
`business_rule_change` in every instance. The 2 `safety_net_override` cases in that pair (`TC 42, 43
- TCR 0 Record 1/2`) are genuine editorial cleanups (a cross-reference to another manual got
dropped), correctly re-classified. Sections added/removed/renamed, the reword/noise appendix, and the
reliability warnings (duplicates) all read coherently. Output at
`data/07_reporte_cambios/<edition_a>_to_<edition_b>.md` (8 files) + `index.md`.

**This completes the full pipeline (Modules 1-5, 7) for `base_ii_clearing_interchange_formats_tc_01_to_tc_49`**
— same milestone already reached for the other 2 manuals. Module 6 stays deliberately
skipped/tentative across all 3 manuals, undefined.

**All 3 chosen manuals (Type B, Type F, Type A) now have a fully validated end-to-end pipeline.**
Bug tally for this 3rd manual specifically: 8 real bugs in Module 2 (the most complex module of the
3 manuals — mixes 2 content shapes per section), 1 more Module 2 bug found while exploring data for
Module 3 (missing 20pt nested section headings), 2 minor fixes in Module 4 (identity vs equality
comparison, a dead variable) — plus 2 deep investigations of unusual signals that turned out NOT to
be bugs (chain-shift, confirmed real but very rare, user explicitly chose not to mitigate; and
Module 5's elevated `safety_net_override`, resolved as one genuine editorial change plus one genuine
source-PDF limitation confined to a single edition).

**No concrete next step decided yet — ask the user** whether to pick a 4th manual or return to
something still open across the 3 already-closed ones (see [[pending-bug-fixes]] items 1-9).

## 4th manual: `base_ii_clearing_interchange_formats_tc_50_to_tc_92` (started 2026-08-19)

User picked this as the 4th manual — direct sibling of the 3rd (`..._tc_01_to_tc_49`), same
document series "BASE II Clearing Interchange Formats", same 9 editions/8 pairs, just covers
chapters TC 50-92 instead of TC 01-49 (confirmed chapters present: TC 50, 52, 54-59, 90, 91/92).

**Module 1** — `poc/base_ii_clearing_interchange_formats_tc_50_to_tc_92/01_ingesta_parseo/ingest.py`.
Identical design to the 3rd manual's Module 1 (raw per-line extraction via `page.get_text("dict")`,
captures `max_font_size`/`fonts`). Ran clean on all 9 editions (376-389 pages, ~23000-23700 lines
each). Confirmed the SAME font-size tiers as the 3rd manual (40/30/26/10.5/9.5/9.0pt) before
committing to reusing the Module 2 design — not assumed just because it's the sibling manual.

**Module 2** — `poc/base_ii_clearing_interchange_formats_tc_50_to_tc_92/02_normalizacion_bloques/normalize.py`.
Same 2-content-shape design as the 3rd manual (grid `Record Layout` + `Edit Criteria` field
cards). Validated 0 errors across all 9 editions (bad row cell counts, unexpected header cells,
empty card name/positions, malformed position patterns — same integrity bar as the 3rd manual).
Confirmed via real data, not assumed:
- **No 20pt nested-section-heading quirk in this manual** — searched `^TC \d` @ 20.0pt across
  all 9 editions, 0 matches in all 9 (unlike the 3rd manual, which had 6 real occurrences).
  `SECTION_HEADING_FONT_SIZES = {26.0}` only (dropped the 20.0 the 3rd manual needed).
- An illustrative example figure ("Field Edit Criteria Example", p.18 intro, 8.1pt) that could
  in theory leak into `pending_right` — traced the full stream and confirmed the next real
  26pt section heading flushes it before any real card exists, so no actual contamination.
- `"Values are:"` variant (vs `"Values:"`) — same cosmetic quirk already accepted in the 3rd
  manual (12 occurrences there too), unchanged behavior, not fixed.

**Real bug found: `"TC 57 - TCR 5 - Limited Use Data"` appears twice in a row with identical
heading text AND identical intro paragraph, but 2 completely different record layouts
underneath** (position 168 is `Reserved` in the 1st copy, `Reimbursement Attribute` in the 2nd).
Confirmed in all 9 editions, always exactly 1 occurrence, always this section. No typographic or
textual differentiator exists between the two copies — unlike the 3rd manual's 20pt-nested fix,
there's no signal to key off yet. **User explicitly deferred fixing/investigating this further**
(2026-08-19) — logged as [[pending-bug-fixes]] item 10, to revisit when the project moves from
POC to real development (see [[feedback-poc-vs-development]], a new memory saved from this
exchange).

**Module 3** — `poc/base_ii_clearing_interchange_formats_tc_50_to_tc_92/03_emparejamiento_bloques/match.py`.
Same section/row/card matching design as the 3rd manual (Position-keyed, section by title exact
then fuzzy 0.85 threshold). **One real design fix required, applied during the port, as a direct
consequence of the TC 57 duplicate-heading bug**: the 3rd manual's `match_sections` builds a
plain `{title: section}` dict, which would silently drop one of the two `TC 57 - TCR 5` layouts
via key collision (Python dict keeps only the last write) — a real, previously-undetected
category of data loss the project's design otherwise never allows (duplicates are always
detected/reported elsewhere, never silently overwritten). Fixed by matching same-titled sections
by ORDER OF APPEARANCE within each edition (1st↔1st, 2nd↔2nd) instead of by title alone; added
`duplicate_section_titles_a/b` to the output so it's visible, not hidden. This does NOT resolve
the semantic ambiguity of "which physical layout is which" (still deferred per user's decision
above) — it only guarantees no data is silently lost.

Validated: reconciliation (`matched+removed=total_a`, `matched+added=total_b`) exact across all 8
pairs; `duplicate_section_titles` correctly flags `"tc 57 - tcr 5 - limited use data"` in all 8
pairs (both sides); confirmed the fix actually works by reading real output — position 168
matches `Reserved↔Reserved` in the 1st TC 57 copy and `Reimbursement Attribute↔Reimbursement
Attribute` in the 2nd, across editions, correctly kept separate. Found one real section rename
(`TC 54 - TCR 0` split into 2 more specific titles between `20241019→20250412`, correctly falls
to removed+added since it's below the fuzzy threshold). Sanity-checked (not a bug, just my own
ad hoc verification script being naive) that 1064 "changed" cards in one pair were ALL just page-
number drift from the TC 54 restructuring reflowing the document — confirmed Module 4's design
(not yet ported for this manual) already excludes `page` from its `CARD_FIELDS` comparison list,
so this will be handled correctly once built.

**Notable finding, not a bug**: unlike the 3rd manual (which had multiple `Reserved→defined`
transitions), this 4th manual shows **zero** such transitions (row-level or card-level) across
all 8 available edition pairs. The matching mechanism itself is proven to work (see TC 57 case
above) — the TC 50-92 chapter range just didn't happen to have this kind of change during this
edition window. Worth keeping in mind when writing the final report/summary for this manual —
don't expect the same "central use case" narrative highlight the 3rd manual's report had.

**Module 4 implemented and validated (2026-08-19)** —
`poc/base_ii_clearing_interchange_formats_tc_50_to_tc_92/04_deteccion_cambios/detect.py`. Ported
unchanged from the 3rd manual (no design changes needed — operates purely on Module 3's already-
stable output shape, identical in both manuals). Ran clean across all 8 pairs: 39 total changes
(`card_content_changed`=26, `duplicate_position_warning`=8, `section_added`=4,
`section_removed`=1) — much smaller volume than the 3rd manual's 554, confirming this chapter
range (TC 50-92) is more content-stable in this edition window. Confirmed 0
`field_became_defined`/`field_became_reserved` across all 8 pairs, consistent with the Module 3
finding already logged above.

Read real `card_content_changed` output (same discipline as the manual-1/manual-3 deep dives) and
found 2 new real Module 2 bugs, both narrow in scope, both logged as [[pending-bug-fixes]] items
11-12 rather than fixed (per [[feedback-poc-vs-development]]):
- Item 11: a ficha table's own title paragraph bleeds into the 1st field's `description` when the
  title happens to line-wrap unusually — confined to 1 field (`Transaction Code` @ 1-2 in the
  "Passenger Itinerary Data - Leg-Specific" section), 3 of 9 editions.
- Item 12: a ficha whose `Values:` list spans multiple pages fragments into several `field_card`
  blocks (source PDF literally re-declares `"(continued)"` fichas per page) instead of merging —
  confined to 1 field (`"BASE II Customized Delivery File Type"` @ 109-113), 1 edition
  (`20220423`). Causes edition-dependent spurious `card_content_changed` noise via the same
  accepted dict-collision mechanism already used for the manual-3 `Format="Group"` case — but here
  the duplicate isn't a legitimate alternative, it's fragmented single-field content.

Verified `duplicate_position_warning` for `TC 54 - TCR 0` (recurring in every pair) IS the
legitimate Format="Group" pattern already accepted in the 3rd manual (`"File Replacement Data"` @
30-169 has 2 mutually-exclusive sub-structure interpretations) — traced back to real PDF content,
confirmed not a bug, consistent with precedent.

Also confirmed (ad hoc sanity check, not a bug): 1064 `card_content_changed` items in one pair
(`20241019→20250412`) were ALL page-number-only artifacts from the `TC 54` section restructuring
reflowing the document — Module 4's `CARD_FIELDS` list already correctly excludes `page` from the
comparison, so this never actually surfaced as a false change in the real output; only my own ad
hoc verification script (which naively compared full card dicts including `page`) needed the
`page`-exclusion check to confirm this wasn't a design gap.

**Module 5 implemented and validated (2026-08-19)** —
`poc/base_ii_clearing_interchange_formats_tc_50_to_tc_92/05_interpretacion_cambios_ia/classify.py`.
Ported unchanged (only the manual title in the prompt template changed). Ran via Ollama
(`qwen3:4b`, local) across all 8 pairs — took ~7 minutes wall-clock for only 26 items (CPU-bound
inference, no GPU), much slower per-item than expected but not a design issue. Full run: 26
items, `business_rule_change`=9, `editorial_reword`=17, `extraction_noise`=0,
`safety_net_override`=1.

Investigated the 1 `safety_net_override` (same discipline as the other 3 manuals — never wave off
an unusual signal just because the mechanism is validated elsewhere): `"TC 90 - TCR 0 - Outgoing
ITF"`, field `"BASE II Customized Delivery File Type"` @ 109-113, `values` field went from a long
enumerated list (593 chars) in `20220423` to empty in `20221015`. Confirmed via raw Module 1/2
data this is a GENUINE editorial change, not a bug: Visa removed the inline enumerated `Values:`
list and added a cross-reference note ("Please refer to the 'Custom Delivery and Split Routing
File Types' table in Chapter 5 of the BASE II Clearing Services manual for the values.") instead —
same exact pattern already documented for the 3rd manual's "Fleet Service" fields. The LLM
initially said `extraction_noise` (wrong), the safety net correctly overrode it to
`business_rule_change` (right) — a true-positive catch, good validation of the safety net working
as designed. **Correction to [[pending-bug-fixes]] item 12** made after this investigation: item
12's real bug (the `"(continued)"` fragmentation) is scoped ONLY to the sibling section `"TC 90 -
TCR 0 - Incoming ITF"` — don't conflate the two `"BASE II Customized Delivery File Type"`
occurrences, only one of them is an actual bug.

**Module 7 implemented and validated (2026-08-19)** —
`poc/base_ii_clearing_interchange_formats_tc_50_to_tc_92/07_reporte_cambios/report.py`. Ported
unchanged (only `MANUAL_SLUG`/`MANUAL_TITLE` changed). Ran cleanly across all 8 pairs, confirmed 0
Reserved↔defined transitions in all 8 (expected, matches Module 3/4 findings). Read the fullest
report end to end (`20251018_to_20260418.md`, 5 business changes): found a real, coherent
cross-section finding — field `"Transaction Component Sequence Number"` @ position 4 changed
`Format` from `unpacked numeric` to `alphanumeric` simultaneously across 5 different TC 50 OCT-
related sections (TCR 0/1/2 variants) — reads as a genuine, consistent business rule change, not
noise. The `TC 54` `Format="Group"` reliability warning (see Module 4 above) correctly resurfaces
in the report's "Avisos de confiabilidad" section. Output at
`data/07_reporte_cambios/<edition_a>_to_<edition_b>.md` (8 files) + `index.md`.

**This completes the full pipeline (Modules 1-5, 7) for
`base_ii_clearing_interchange_formats_tc_50_to_tc_92`** — same milestone as the other 3 manuals.
Module 6 stays deliberately skipped/tentative, same as the other 3.

**All 4 manuals now have a fully validated end-to-end pipeline.** Bug tally for this 4th manual
specifically: 1 real Module 2 bug with a required Module 3 fix (TC 57 duplicate-heading — the fix
was necessary to prevent silent data loss, not optional polish); 2 more real Module 2 bugs found
reading real output (ficha-title bleed into a description, multi-page ficha fragmentation) —
logged as [[pending-bug-fixes]] items 10-12, all deferred per [[feedback-poc-vs-development]]; 1
deep investigation of an unusual Module 5 signal that turned out NOT to be a bug (the
`safety_net_override`, a genuine editorial change correctly caught, same pattern as the 3rd
manual). Distinguishing feature of this manual vs. the other 3: much lower change volume overall
(39 Module 4 changes / 26 AI-classified items vs. the 3rd manual's hundreds) and zero occurrences
of the project's central use case (Reserved→defined) in the available edition history — still a
valid, fully-working pipeline, just less eventful data for this particular chapter range/window.

**No concrete next step decided yet — ask the user** whether to pick a 5th manual or return to
something still open across the 4 already-closed ones (see [[pending-bug-fixes]] items 1-12).

## 5th manual: `base_ii_transactions_quick_reference` (started 2026-08-19)

User picked this as the 5th manual — a genuinely NEW source (not a sibling of an existing one
like the 4th was), much smaller (128KB-466KB PDFs vs. multi-MB for the other 4; 20-24 pages,
~1000-1300 lines per edition). Only 8 editions available (no `20251018` edition exists for this
manual, unlike the other 4 which have 9).

**Module 1** — `poc/base_ii_transactions_quick_reference/01_ingesta_parseo/ingest.py`. Identical
generic design (raw per-line extraction, `max_font_size`/`fonts` captured) — ran clean on all 8
editions.

**Content shape investigated before writing Module 2 (2026-08-19), confirmed genuinely different
from the other 4 manuals**: this is a simple 2-level quick-reference LIST, not a Position/Length/
Format grid — no grid+ficha duality at all.
1. **TC entry** (12.0pt, x0=72, text `"NN Name"` e.g. `"33 Multipurpose Message"`) — exactly 45 in
   all 8 editions (the 45 TC/TCR codes), stable count across the whole edition history.
2. **TCR row** (10.5pt, 2 fixed columns: TCR label @ x0=90, description @ x0=144, description
   sometimes entirely absent — e.g. `"40 Fraud Advice"` has 5 TCR rows with no description at
   all).
Font-size separation confirmed clean (12.0/10.5pt used ONLY by real content, 0 collisions with
front-matter/header/footer in any of the 8 editions) — simpler than the other 4 manuals, no
per-page table-title redeclaration needed for TC entries.

**Real Module 2 bug found and fixed during the FIRST validation pass (2026-08-19), before
reporting the module as done** — same "fix data-loss bugs in real tables immediately" rule as
always ([[feedback-bug-prioritization]]): the row-grouping wrap-fallback (`group_into_rows`,
ported unchanged from the other 3 Type-A-style manuals) didn't check that the 2 compared lines
were on the SAME page. Crossing a page boundary, the new page's `y0` starts small (~50-70pt)
while the previous page's last row `y1` is near the bottom (~700-750pt) — the resulting gap is
very NEGATIVE, which still passed the `<= GRID_ROW_GAP_MAX` threshold by accident, merging ALL
subsequent rows of a section into one unreadable blob until the next TC heading. Confirmed real:
9 real TCR rows of `"33 Multipurpose Message"` (crossing pages 15→16) collapsed into 1 block.
Root cause of why this bug is NEW here despite reusing proven code: the other 3 manuals get this
page-crossing protection for FREE via their table-title redeclaration-per-page convention (a
different-sized line always breaks the row buffer before any cross-page geometry check runs) —
this manual has no such redeclaration, so the protection had to be made explicit. Fix: `row_buffer`
flushes unconditionally on a page change, before the gap-based wrap fallback ever runs. **Caught
an over-correction while fixing**: an initial attempt added a `0 <=` lower bound on the gap check
as a "belt and suspenders" second safeguard — this broke a LEGITIMATE same-page wrap case (a
description wrapping to a 2nd line can have a slightly NEGATIVE gap from tight line-spacing,
confirmed real on `"39 VCRFS/VDAS Message"` TCR 3 — `"...Optional Representment/Second"` wrapping
to `"Chargeback"`), splitting it into 2 spurious separate rows. Removed the lower bound — the
page-check alone is sufficient and correct.

Validated after the fix: 0 rows with cell count outside {1,2}, 0 suspicious multiline TCR-label
merges, across all 8 editions — table_row counts now match the raw TCR-label line counts exactly.
Spot-checked both fixed cases (TC 33's 9 rows now separate and correct; TC 39's wrap still merges
correctly) plus TC 40's no-description rows (still correctly 1-cell).

**Open design question for Module 3 (not yet built)**: this manual has NO position/byte-offset
column at all (unlike the other 4), so there's no natural stable matching key. Worse, the TCR
label itself is NOT unique within a TC entry — confirmed real: `"33 Multipurpose Message"` has
`"TCR 0"` repeated 9 times with 9 completely different descriptions (9 different message subtypes
sharing the same TCR number). Will need a different Module 3 matching-key design than the
Position-based one used in the other 4 manuals — to be figured out with real data when Module 3
is actually built, not speculated now.

**Module 3 implemented and validated (2026-08-19)** —
`poc/base_ii_transactions_quick_reference/03_emparejamiento_bloques/match.py`. Matching-key
design resolved with real data BEFORE writing the module (per the open question logged above):
- **Sections (TC entries)**: exact-title + fuzzy 0.85 fallback, unchanged from the other 4
  manuals — safe here because the 2-digit code prefix guarantees title uniqueness by
  construction, no observed collision risk.
- **TCR rows**: composite EXACT key `(TCR label normalized, description normalized)`, deliberately
  WITHOUT a fuzzy fallback on the description text. Confirmed empirically before deciding: pairwise
  `difflib` similarity between ALL description pairs within the same section in the reference
  edition turned up dozens of genuinely-different-row pairs at ≥0.85 similarity (e.g. `"Batch
  Disposition Code A"` vs `"Batch Disposition Code R"` = 0.958; `"...Part 1"` vs `"...Part 2"` =
  0.971; country pairs like Russia vs Uruguay = 0.862) — a fuzzy fallback here would risk
  mismatching a real removed+added pair as one "renamed" row, hiding the exact kind of structural
  change the project exists to expose. Also confirmed description-alone (without TCR) isn't a safe
  key either: `"BASE II Clearing and Settlement Advice"` appears twice in `"33 Multipurpose
  Message"` under different TCR labels. The full composite key has 0 collisions across all 8
  editions (verified before committing to the design). **Consequence accepted deliberately**:
  since the key consumes both mutable fields, a matched row is always byte-identical between
  editions by construction — there's no `row_content_changed` category for this manual, any real
  edit surfaces as remove+add instead of a content diff. Same "honest add/remove over a risky
  guess" principle already used for the 3rd manual's chain-shift decision.

Added a duplicate-key safety net (`duplicate_row_keys`, same pattern as `duplicate_row_positions`
elsewhere) plus order-of-appearance matching for any future collision (same mechanism proven for
the 4th manual's `TC 57` fix) — 0 actual collisions in all 8 editions, purely defensive.

Validated: reconciliation exact across all 7 pairs; 0 `duplicate_row_keys` triggered (as
expected). Investigated 3 real, large, non-obvious diffs to confirm the remove+add design
correctly surfaces genuine changes rather than masking a bug:
1. Pair `20220423→20221015`: 6 sections removed + 6 added — confirmed a real, consistent Visa
   terminology shift ("Chargeback" → "Dispute", e.g. `"15 Sales Draft Chargeback"` →
   `"15 Sales Draft Dispute"`) across 6 TC codes — same "chargeback→dispute" modernization already
   documented in the 3rd manual's Module 7 report.
2. Pair `20240413→20241019`: 18 rows added + 18 removed — confirmed a real, consistent rename
   ("Single Message System Interface (SMS...)" → "Supplemental Financial...") across 9 sections (2
   rows each).
3. Pair `20250412→20260418` (the pair spanning the missing `20251018` edition, so a bigger gap):
   matched dropped from 471 to 243 (274 added, 228 removed) — confirmed a real, document-wide
   editorial change: Visa added 2-letter country-code prefixes to `"National Settlement, X"`
   descriptions (e.g. `"National Settlement, Argentina"` → `"(AR) National Settlement,
   Argentina"`) across ~10+ sections. Not a normalization bug (double-checked, since the other 4
   manuals needed a dash-character unification this manual's `_normalize_text` doesn't have — but
   the actual diff here has nothing to do with dashes).

**Module 4 implemented and validated (2026-08-19)** —
`poc/base_ii_transactions_quick_reference/04_deteccion_cambios/detect.py`. Simpler than the other
4 manuals exactly as anticipated: no `row_content_changed` category exists for this manual (a
matched row is always identical by construction, see Module 3 above), and no
`field_became_defined`/`field_became_reserved` either — this manual has no "Reserved field"
concept at all (it's a TC/TCR code index with message names, not a byte-layout grid), so the
project's central use case doesn't apply here even by analogy. This manual's actual value is
different: tracking when a whole message TYPE (a TCR row) appears/disappears/gets renamed — a
high-level index diff, complementary to (not a substitute for) the other 4 manuals' field-level
tracking. Emits `section_added`/`section_removed`/`section_renamed`, `row_added`/`row_removed`
(no grid/ficha distinction, only one row shape here), `duplicate_key_warning`.

Ran cleanly across all 7 pairs, numbers reconcile exactly against Module 3's already-validated
output (0 `duplicate_key_warning`, 0 `section_renamed` — confirms the "Chargeback→Dispute" case
correctly fell to remove+add as designed, not a fuzzy match). Totals: 20220423→20221015 (21
changes), 20221015→20230415 (0), 20230415→20231014 (9), 20231014→20240413 (0), 20240413→20241019
(36), 20241019→20250412 (0), 20250412→20260418 (502 — the big country-code-prefix rewrite already
investigated and confirmed genuine in Module 3).

**Module 5 resolved as a deliberate no-op (2026-08-19), confirmed with the user via discussion,
not just assumed** — `poc/base_ii_transactions_quick_reference/05_interpretacion_cambios_ia/
classify.py`. User initially pushed back on the "no row_content_changed" claim ("¿no habrá una
línea que se parezca en algo entre versiones?") — resolved by walking through why matched rows
exist (471+ per pair) but are always identical by construction, and why the SMS-interface rename
case specifically shows as remove+add rather than a content diff (no independent anchor like
Position to say "same entity, different text" — TCR alone isn't unique, description alone isn't
unique, only the composite is, and the composite consuming both fields is exactly why nothing
partial can be classified). User proposed an alternative validation angle (count TCR per TC,
compare counts across editions, flag new TC codes) — confirmed this is ALREADY fully available
from Module 3/4's existing output with no new mechanism needed, demonstrated with real data
(computed a live TCR-count delta for the `20240413→20241019` pair, showed it nets to exactly 0
per affected section despite 2 real renames underneath — proving count-alone hides content
detail, motivating the Module 7 design below). User agreed: keep Module 5 as an empty/pass-
through file for pipeline-folder consistency (same as Module 6's tentative status across all 5
manuals) rather than skip the file entirely — it copies Module 4's output unchanged, adds an
empty `ai_summary`, and includes a defensive stderr warning if `row_content_changed` ever
appears (would mean Module 3's design assumption broke and needs re-checking).

**Module 7 implemented and validated (2026-08-19)** —
`poc/base_ii_transactions_quick_reference/07_reporte_cambios/report.py`. Report structure
designed around the user's count-delta idea, done properly: per affected TC, shows TCR count
before → after with the delta, AND always lists the specific added/removed rows underneath (never
just the number) — explicitly flags with ⚠️ when delta is 0 but both additions AND removals
exist in the same TC (the "possible undetected rename" signal). Re-reads Module 3's output
directly for the before/after row-count metadata (Module 4/5 only emit change EVENTS, not
per-section totals for unchanged sections) — same "reach back to an earlier stage for context"
pattern already established by the other 4 manuals' Module 5 (`_field_name_lookup`).

Validated by reading 2 full reports end to end: (1) the `20220423→20221015` pair shows the 6
Chargeback→Dispute TC renames correctly as TC-level added/removed pairs, PLUS a real `05 Sales
Draft` TCR growth (+5, no removals — genuine new content, no rename ambiguity) alongside the SMS-
interface-style rename-with-warning case in the same report, reading coherently side by side; (2)
the `20240413→20241019` pair shows all 9 SMS-interface rename cases with the ⚠️ marker correctly
triggered in each. Output at `data/07_reporte_cambios/<edition_a>_to_<edition_b>.md` (7 files) +
`index.md`.

**This completes the full pipeline (Modules 1-5 [5 as deliberate no-op], 7) for
`base_ii_transactions_quick_reference`** — 5th manual done. Module 6 stays tentative, same as the
other 4. Real bug tally for this manual: 1 real Module 2 bug (page-boundary row-merge, found and
fixed in the first validation pass, see Module 2 section above) — logged in
[[dev-phase-considerations]] as a cross-manual audit item, not [[pending-bug-fixes]] (already
fixed, not deferred). Distinguishing feature of this manual: fundamentally different Module 3
matching-key design (exact composite key, no position, no fuzzy row-level matching) forced by
real evidence that fuzzy text matching is unsafe at this granularity — and Module 5 genuinely not
needed, confirmed through actual back-and-forth with the user rather than assumed upfront.

**No concrete next step decided yet — ask the user** whether to pick a 6th manual or return to
something still open (see [[pending-bug-fixes]] items 1-12, [[dev-phase-considerations]]).
