---
name: manual8-vss-vol2-progress
description: "Progress log for the 8th manual, visanet_settlement_service_vss_user_guide_volume_2_reports — 5 appendices with distinct content shapes, page-level PDF rotation, generic N-column table reconstructor"
metadata:
  node_type: memory
  type: project
  modified: 2026-08-26T15:52:41.832Z
---

## 8th manual: `visanet_settlement_service_vss_user_guide_volume_2_reports`
(started 2026-08-19, `visa/src/vss/`, 7 editions: 20220423→20251017, 428-444 pages)

**Companion to the 7th manual (Volume 1), but structurally different and more fragmented.**
5 appendices, each a distinct content shape, confirmed via real bbox/font exploration before
any code was written:
- **Appendix A** (`VSS Reports-Print-Ready Formats`): entirely landscape via real PDF page
  rotation (`page.rotation == 90`, a genuine `/Rotate 90` — NOT individually-rotated text
  lines embedded in portrait pages like Volume 1). Mixes disposable mainframe report samples
  with real "Field Name/Description" reference tables on the SAME page.
- **Appendix B** (`VSS Reports-Machine-Readable Formats`): classic Type A grid (Position/
  Field Length/Format/Field Name/Description), portrait, no rotation — same family as the
  `base_ii_clearing_interchange_formats` manuals but simpler (Description is a direct grid
  column here, no separate field-card structure needed).
- **Appendix C** (`VSS Codes`): simple Code/Description Type B tables, portrait — several
  sub-tables also have a 2-tier group/leaf header (e.g. "Fee Collection/Funds Disbursement"
  with codes grouped under a "VSS Business Transaction Code" umbrella).
- **Appendix D** (`SMS Reports and Raw Data`): same page-level rotation as Appendix A, but a
  DIFFERENT sub-shape mix — SMS report field-description tables (2 or 3 columns) AND the
  Release 2.2/2.3 raw record layouts (V22xxx/V23xxx, 5 columns: Field Name/Position/
  Attribute/Field Sources/Comments).
- **Appendix E** (`VSS Business Transaction Types Cross-Reference`): a 6-column matrix table
  with a genuine 2-tier header (row1 group labels spanning row2 leaf sub-columns), portrait.

**User's explicit scoping decisions (2026-08-19, via AskUserQuestion)**: Module 1 separated
by appendix from the start (unlike all 7 previous manuals, where Module 1 was always
appendix/shape-agnostic and differentiation was deferred to Module 2) — Module 1 output is
one JSON per edition with a `sections` dict keyed by `front_matter`/`appendix_a`..`appendix_e`,
boundaries computed per-edition from the PDF's own TOC bookmarks (`"Appendix A:".."Appendix
E:"`, level 2 — confirmed stable title/level across all 7 editions, only page numbers shift).
Module 2 covers all 5 appendices in one big pass (unlike the incremental per-appendix
checkpoints used elsewhere) — user picked this explicitly over doing Appendix B first alone.

**Real finding before Module 1 was written**: `page.rotation == 90` is a genuine PDF page
attribute here (confirmed via `page.rotation`), not per-line `dir` embedding like Volume 1.
PyMuPDF applies this rotation transparently in `page.get_text()` (plain text reads correctly)
but NOT in `page.get_text("dict")` bbox values — those stay in the UNROTATED mediabox
coordinate system. Module 1 captures both `page_rotation` and per-line `dir` (same field
Volume 1 used) so Module 2 can use whichever signal it needs.

**Module 1 implemented and validated** —
`poc/visanet_settlement_service_vss_user_guide_volume_2_reports/01_ingesta_parseo/ingest.py`.
0 lines land in an "unassigned" appendix bucket across all 7 editions (TOC-based boundary
detection is fully reliable here). Spot-checked: page 63 (Appendix A, rotation=90) and page
191 (Appendix B, rotation=0) both land in the correct section with the expected rotation flag.

**Module 2 implemented (2026-08-19)** —
`poc/visanet_settlement_service_vss_user_guide_volume_2_reports/02_normalizacion_bloques/normalize.py`.
Core design decision: ONE generic N-column table reconstructor (`_detect_columns` +
`_build_table_rows`) reused for all 5 appendices, driven by a typographic pattern that turned
out to be IDENTICAL across all 5 despite very different column counts/orientations: 26.0/20.0pt
Bold section titles, 10.5pt Bold table titles, 9.5pt Bold column headers (2-6 per table), 9.0pt
Regular row content — same 4-tier scheme rotated to 14.0/12.0/10.5/9.5/9.0pt for Appendix A/D.
Column bands are computed dynamically per page/table from the header row itself (never global
constants), and the "anchor" column (the one whose appearance triggers a new row) is
determined generically: smallest X0 for horizontal tables, largest Y1 for rotated tables (Y1
= "first in rotated reading order", same convention Volume 1 established). Disposable
mainframe report samples in Appendix A/D are filtered by font name alone (`CourierNewPSMT`,
monospace) — confirmed the only reliable signal, since the disposable content's font SIZE
varies (7.3pt or 10.5pt depending on the report) while the font NAME never does.

**5 real bugs found and fixed during first-pass validation** (all found by reading actual
reconstructed content against the source PDF, not just structural counts — same discipline
used throughout this project):
1. **2-line wrapped column headers landing in their own row-tier, breaking group/leaf
   detection.** Appendix E's "Transaction \nDescription" and "VSS Business \nTransaction
   Type" headers wrap to 2 lines with a ~12pt gap — the initial row-tier clustering (6pt
   tolerance) treated the wrap's 2nd line as a 3rd, separate header tier instead of merging it
   into its own header, causing both columns to silently disappear (their data fell through to
   the nearest OTHER column via nearest-band assignment). Fixed: widened the row-tier
   clustering tolerance to 15.0 (real wrap gap ~12pt, real distinct-tier gap ~20.5pt — safely
   between both) and fixed a separate flattening bug where only the LAST header tier's leaves
   were ever added to the final column set, silently dropping any earlier tier's legitimate
   leaf headers.
2. **Wrapped header's OWN 2 lines not merging due to a secondary-axis X-shift.** Even after
   fix 1, "VSS Business "/"Transaction Type" still didn't merge into one column — their 2nd
   line's X0 shifts ~10.3pt from the 1st line's (text alignment artifact), exceeding the
   6.0pt merge tolerance used for collapsing a wrapped header's own lines. Widened that
   tolerance to 20.0 (safe: real gap between 2 DIFFERENT headers in the same row is >90pt,
   confirmed empirically — no risk of over-merging).
3. **Wrong bbox axis used for the rotated "row gap" check.** `_build_table_rows`'s new-row
   trigger compared the WRONG bbox index for rotated tables (`bbox[1]`, i.e. Y0 — a completely
   unrelated axis — instead of `bbox[2]`, X1, the correct "end of line along the primary/row
   axis" for rotated content). This silently broke row-splitting for every rotated grid table
   (Appendix A/D), collapsing multiple real rows into one. Fixed by computing `prim_end`
   correctly per orientation (Y1 for horizontal, X1 for rotated).
4. **Sort-order tie-break processed non-anchor columns before the anchor at the same primary
   position, misattributing data to the previous still-open row.** For rotated tables the
   anchor column is the one with the LARGEST secondary position (Y1), but the row-processing
   sort ordered the secondary axis ascending (correct for horizontal, where the anchor has the
   SMALLEST secondary position) — so at a tied primary position, the anchor line sorted LAST,
   not first, letting other columns' data get appended to the previous row before the new-row
   trigger fired. Fixed by sorting the secondary axis descending specifically for rotated
   tables (`sec_sign = -1`).
5. **Rotated row-gap threshold recalibrated with real evidence.** After fix 3 exposed the real
   geometry, the rotated anchor-column threshold (originally a lazy `ANCHOR_WRAP_GAP_MAX * 4 =
   12.0`) was well ABOVE the real minimum row-to-row gap (7.5pt, confirmed on 2 different
   tables: Appendix D's V22200 record and Appendix A's VSS-111 field descriptions) — merging
   real distinct rows into one. Replaced with a dedicated, evidence-calibrated constant,
   `ROTATED_ANCHOR_WRAP_GAP_MAX = 4.0` (real wrap gap ~-1 to 0pt, real row gap >=7.5pt).
6. **`GROUP_HEADER_MIN_GAP` (2-tier header group-vs-leaf threshold) recalibrated.** Originally
   30.0, calibrated only against Appendix E. A real group header in Appendix C ("VSS Business
   Transaction Code", spanning "Fee Collection"/"Funds Disbursement") sits 48.4pt from its
   nearest leaf — ABOVE the old threshold — so it escaped group classification and became a
   spurious extra column that stole data from the real "Fee Collection" column via
   nearest-band assignment (its own real leaf column ended up empty). Recalibrated to 65.0
   using evidence from BOTH appendices (real group-to-leaf range 10.8-48.4pt, real
   leaf-to-leaf range >=90.8pt) — same "validate against the whole corpus, not just the first
   table found" lesson this project has hit repeatedly (see [[open-questions-technical-manuals]]
   2nd-manual Module 3 narrative for the earlier instance of this exact lesson).

**1 real residual found and NOT fixed (logged, matching [[feedback-bug-prioritization]] /
[[feedback-poc-vs-development]]): tight row-packing in some Appendix D grids causes a
non-anchor cell's wrapped 2nd line to be misattributed to the following row.** Confirmed on
Appendix D's `Financial Transaction Record 4 – V22225` (page 375): "Message Type"'s Field
Sources value "Field 90, Positions 5-10" is split — "Field 90, Positions" stays with Message
Type's row, but the wrapped continuation "5-10" lands on the FOLLOWING row ("Trace Number")
instead, because that continuation line's primary-axis position (X0=189.88) falls to the right
of where the NEXT row's own anchor already triggered (Trace Number's anchor X0=185.21). Root
cause: in this specific table the anchor-to-anchor row gap (~4-8pt) is close in magnitude to a
non-anchor cell's own wrap-continuation gap, so pure geometry can't always tell which row a
non-anchor continuation belongs to — genuinely ambiguous without a smarter same-row-detection
signal (e.g., checking if the previous row's same-column text looks sentence-incomplete).
Confirmed NOT a wholesale data-loss bug (content is captured, just occasionally attributed to
the row after the one it belongs to) — affects an estimated ~150-170 rows in Appendix D (out of
~1550 grid_rows there) in the newest edition, concentrated in the V22xxx/V23xxx raw-record
tables. Not chased further given the geometric ambiguity and the project's established
diminishing-returns precedent for POC-phase edge cases (see item 13/14 in
[[pending-bug-fixes]] for the same "accepted, real residual" pattern already used twice
before). **Also verified NOT a bug**: many of Appendix A's "empty first column" rows (e.g.
`"(National Net Specific)"` sub-note rows in the `Other Reports` report catalog on pages
14-17) are genuine sparse source content — a real annotation row with only its Report ID
populated, faithfully reproduced, not a reconstruction defect.

**Final validation across all 7 editions**: 0 disposable-content leakage (`CourierNewPSMT`
text never appears in any `grid_row`/`paragraph` value, confirmed programmatically), 0 rows
with every column empty, `__unassigned_prefix__` (data landing before any row's anchor has
fired) down to 1-3 occurrences per edition out of ~2600-2700 total `grid_row` blocks — very
low, not investigated further (same category as the small residuals accepted elsewhere in the
project, e.g. manual 1's `pending_prefix` safety net). Spot-checked real content across all 5
appendices against the source PDF by hand before/after each fix (Appendix B's TC46 record
layout, Appendix C's Business Transaction Types/Charge Types/Fee Collection tables, Appendix
D's V22200/SMS608 tables, Appendix E's BASE II cross-reference matrix, Appendix A's VSS-111
field descriptions) — all confirmed byte-for-byte correct against the PDF after fixes.

**Module 3 implemented (2026-08-19)** —
`poc/visanet_settlement_service_vss_user_guide_volume_2_reports/03_emparejamiento_bloques/match.py`.
Processes each of the 5 appendices independently (no shared cross-appendix section
hierarchy, unlike every other manual). Table identity key: `(appendix, table_title)`, exact
then fuzzy fallback (0.85). Row identity key within a matched table: the row's own
`anchor_column` value (now carried per `grid_row` since a small Module 2 addition made
specifically to support this — `_build_table_rows` returns `(rows, anchor_col)` and both
`build_horizontal_blocks`/`build_rotated_blocks` attach it), normalized, EXACT only, with
order-of-appearance tiebreak for duplicate keys within one table (duplicates confirmed real
and non-trivial — up to ~33% of rows in some Appendix E tables, where "Transaction
Description" repeats across TC variants — same mechanism already used 3x elsewhere in this
project, not re-investigated). `section_heading`/`paragraph` blocks matched lightly (exact +
fuzzy for headings, exact-only for paragraphs) as low-priority structural context, not the
core deliverable.

**2 more real bugs found and fixed while validating Module 3's first run** (same discipline:
investigate an elevated/suspicious signal before accepting it):

7. **A genuine PDF-source inconsistency split one real table into 2 titles, which then
   cascaded into a WRONG cross-edition table match for a completely different table.**
   Editions 20220423-20230415: the V22225 record's continuation page (364) declares the plain
   title "Financial Transaction Record 4—V22225", but its FIRST page (363) declares "Note:
   Financial Transaction Record 4—V22225" (a literal "Note: " prefix in the source PDF itself,
   confirmed real — not an extraction artifact). Splitting the table in 2 wasn't just a cosmetic
   miscount: because the fuzzy-matching pool for Appendix D was large (many similarly-named
   V22xxx tables), the spurious "Note: ..." title stole the CORRECT cross-edition match target
   away from the real "Financial Transaction Record 4" title, cascading into that one getting
   fuzzy-matched against "Financial Transaction Record 5" instead (a genuinely different
   record) — would have produced garbage diffs comparing 2 unrelated records' fields.
   **First fix attempt (coalescing same-edition titles whenever their fuzzy ratio clears
   0.85) was tried and explicitly REJECTED before committing**: the same threshold needed to
   catch "Note: X" vs "X" would ALSO merge genuinely different tables (confirmed real:
   "...Record 4—V22225" vs "...Record 5—V22226" scores 0.895, above threshold) — a strictly
   worse bug (silent cross-record merging) than the one being fixed. Replaced with a precise,
   narrow fix: strip a literal `"Note: "` prefix (regex, case-insensitive) when computing a
   table's normalized identity, confirmed as the ONLY real prefix variant across the whole
   corpus (2 base titles affected, 3 editions, self-corrects by 20231013).
8. **2 genuinely distinct tables sharing one rotated page collapsed into one via a header
   dict-key collision — the bigger, more consequential bug of the two.** When 2 unrelated
   V22xxx/V23xxx records happen to fit on the same rotated page (common — these records are
   short), each declares its OWN "Field Name/Position/Attribute/Field Sources/Comments"
   header — SAME 5 column names, different physical position. `_detect_columns`'s final
   `{name: position}` dict silently kept only whichever table's header was processed last,
   losing the other's real column positions and gluing both tables' title lines into one
   string (`" ".join` over ALL title lines on the page, no per-table separation). Confirmed
   broad impact BEFORE fixing (not assumed): 13-21 glued titles per edition just in Appendix
   D, ~20-30% of its ~66-69 tables — this is real V22xxx/V23xxx record-layout data, the
   project's core "position/field" use case, not a low-priority residual. Fixed with a real
   architectural addition: `_cluster_header_tiers` (extracted from the old `_detect_columns`)
   + `_split_into_zones`, which detects "2 header tiers share a column NAME" as the signal
   that they're 2 SEPARATE same-schema tables (not a legitimate group/leaf 2-tier header,
   which never repeats a name between tiers — confirmed by re-checking Appendix E/C's already-
   validated 2-tier tables use entirely disjoint name sets between group and leaf rows) —
   splits the page into independent "zones," each with its own column-position dict and its
   own primary-axis start boundary; title lines and data lines are then routed to whichever
   zone's header most recently precedes them (`_assign_zone`), instead of being pooled
   page-wide. `build_horizontal_blocks`/`build_rotated_blocks` rewritten to loop over zones
   per page rather than assuming exactly one table per page. Verified no regression on every
   previously-validated single-zone table (Appendix B's TC46 grid, Appendix C's code tables,
   Appendix E's cross-reference matrix — byte-identical output before/after) plus confirmed
   fix on the concrete case (`Financial Transaction Record 4 – V22225` now its own clean
   15-row table, previously glued with V22226).
   **Residual, narrower than before, not chased further**: when a table's LAST few rows
   spill onto a continuation page that does NOT redeclare that table's own header (confirmed:
   unlike Appendix B, these V22xxx/V23xxx tables do NOT always redeclare their header on every
   page — only when a NEW table's header appears on that page), those orphan rows have no
   zone of their own to route into and fall back to zone 0 (whichever header IS present on
   that page, i.e. the NEXT table's), still producing a glued title for just that small tail.
   Quantified after the fix (not guessed): 2 residual cross-record fuzzy-match mismatches
   left out of 51 total fuzzy table matches across all 6 edition pairs (down from a much
   larger, unquantified-but-clearly-broader problem before finding item 8) — logged as
   [[pending-bug-fixes]] item 16, same "continuation without header redeclaration" bug class
   already seen in other manuals (e.g. manual 1's `H0 (continued)`), just not chased to full
   resolution here given the scope already invested this session.

Final validation across all 7 editions after both fixes: total `grid_row` counts unchanged
(2601-2685 per edition, confirms the fixes only re-grouped existing rows under correct
titles, never created/destroyed data), `__unassigned_prefix__` still 1-3 per edition,
disposable-content leakage still 0. Table counts per appendix increased as expected (more
granular, correctly-split tables) — e.g. Appendix D 66→69 tables in the newest edition.

**Module 4 implemented (2026-08-19)** —
`poc/visanet_settlement_service_vss_user_guide_volume_2_reports/04_deteccion_cambios/detect.py`.
Purely deterministic, same separation-of-concerns as every other manual (structural
add/remove/rename already resolved by Module 3, passed through untouched; only decides
whether a matched row's content really changed). Diffs by column NAME (not index, like the
2nd manual — each `table_title` can have a different column set here), excluding the anchor
column, same 0.98 `difflib` threshold as the rest of the project. `duplicate_row_keys_a/b`
from Module 3 passed through as a `duplicate_row_key_warning` reliability caveat, same
treatment as `duplicate_code_warning` elsewhere.

**1 more real bug found while validating Module 4's first output** (elevated/suspicious
`row_added`/`row_removed` counts in Appendix C prompted the investigation, same "elevated
signal → investigate before trusting" discipline used throughout this project): confirmed
Appendix C ALSO has the multi-table-per-page phenomenon from bug 8 (e.g. "Settlement
Services" and "Transaction Dispositions" share page 270) — the zone-SPLITTING logic (bug 8's
fix) worked correctly, but the TITLE-ROUTING logic didn't: `_assign_zone` was written for
DATA lines, which always come AFTER their own table's header — but a table's TITLE line
comes BEFORE its own header (normal reading order: title → header → rows). For the 2nd table
on a shared page, `_assign_zone` picked the "most recent header that already appeared before
this line," landing the 2nd title on the 1ST table's zone (its header was already visible,
the 2nd table's wasn't yet) — gluing both titles together, exactly the same visible symptom
as bug 8 but from a different root cause. Fixed with a dedicated `_assign_title_zone`
(searches FORWARD for the nearest zone whose header comes AFTER the title, not backward) used
only for title-line routing; `_assign_zone` unchanged for data-line routing. **Turned out to
also fully resolve item 16** (the "continuation tail without header redeclaration" residual
logged after Module 3) — re-checked after this fix: 0 record-number cross-mismatches left
out of 52 total fuzzy table matches across all 6 pairs (down from 2). Item 16 can be marked
resolved.

Final validation across all 7 editions: `grid_row` counts unchanged (same re-grouping-only
guarantee as bug 8's fix), 0 rows with an empty `table_title` (was nonzero before this fix),
0 disposable-content leakage, `__unassigned_prefix__` still 1-3 per edition, no regression on
any previously-validated table (Appendix B/C/E spot-checks byte-identical). Read real
generated diffs before accepting Module 4 as done (not just counts): Appendix E's
`row_content_changed` entries are plausible genuine business updates (e.g. `Usage Code = 1` →
`Usage Code = 9` for several cash-disbursement/dispute-financial cross-reference rows).
Appendix C's `Charge Types` table shows an ALL-CAPS↔Title-Case reformatting between
`20220423`→`20221014` (e.g. `"Other"`→`"OTHER"`) — flagged as `row_content_changed` with a
LOW similarity ratio (case-sensitive `SequenceMatcher`, as low as 0.18) despite being purely
cosmetic. **Deliberately NOT case-folded in Module 4** — same design boundary already
established across the whole project: Module 4 stays a dumb, case-sensitive threshold: it's
Module 5's job (AI classification) to recognize this as `editorial_reword`, not Module 4's.
Not a bug, a reminder of where this manual's Module 5 will need to earn its keep.

**Module 5 implemented (2026-08-19)** —
`poc/visanet_settlement_service_vss_user_guide_volume_2_reports/05_interpretacion_cambios_ia/classify.py`.
Same design as every other manual (Ollama local, `qwen3:4b`, forced JSON, `think:false`, temp
0, same 3 categories, same `_find_disappeared_content` safety net with a 5-word threshold).
One generic prompt for all 5 appendices (unlike the 7th manual, which needed 2) — every
`row_content_changed` already carries the same shape (appendix + table + row key + column +
old/new), so one template covers it. 487-item smoke-tested-then-full batch, ~85 min on CPU.

**Smoke test (6 items) surfaced a known-category, low-priority LLM quirk, not a new one**:
Appendix D, `Financial Transaction Record 2`, row "reserved" — the SAME real fact (a Reserved
field shrinking from 2 bytes to 1, position `79–80`→`80`, matching this project's central use
case) is correctly classified as `business_rule_change` in the `Attribute` column (`2 N`→`1
N`) but wrongly as `extraction_noise` in the `Position` column. Not fixed — same
"small-model-misses-a-short-value-swap" category already logged twice before (manual 1's
digit-typo quirk, manual 2's `V0407`); the safety net doesn't fire here because a 1-word
value swap isn't a 5+-word "disappeared chunk". No information lost (same fact captured
correctly in `Attribute`).

**1 more real Module 2 bug found while validating the FULL batch's `safety_net_override` rate
(37/487 ≈ 7.6%, elevated vs. other manuals' typical ~3.5% — investigated before accepting,
same discipline as always)**: 14 of 15 overrides in the `20221014→20230415` pair all pointed
at the SAME table (`SMS (Including Interlink) Transactions to VSS Business Transaction
Types`), with `Messages and Codes`/`Business Transaction Type` going from real content to
empty. Checked the real source PDF directly (not assumed) — confirmed the content genuinely
EXISTS in the newer edition's PDF, so this was NOT a real business change nor a real
editorial removal: in 3 of 7 editions (`20230415`, `20231013`, `20240413`, self-correcting
after), this specific table's 2-word column headers get extracted by PyMuPDF as 2 SEPARATE
same-Y0 text spans with a horizontal gap between them (`"Messages"` + `" and Codes"`,
`"Business Tran"` + `"saction Type"`) instead of one clean span — confirmed via exact bbox
comparison against the clean `20221014` edition, where the same headers extract as one span.
Not a wrap (same Y0 exactly, not a 2-line vertical stack) — a genuine PDF-rendering quirk
specific to those 3 editions.

**A geometric-threshold fix was tried first and explicitly rejected**: the real "spurious
split" gap (span-end to next-span-start) measured 19.4–31.8pt, but Appendix B's own
genuinely-different adjacent headers (`Field Length`→`Format`) measured as close as 19.9pt —
the ranges overlap, so no single threshold can separate "same header split" from "really 2
different headers" using gap size alone. **Fixed instead with a data-informed signal**: after
building a table's rows, any column that is 100% empty across every row (minimum 2 rows,
`MIN_ROWS_FOR_PHANTOM_CHECK`) AND sits immediately next to a column that's NOT empty is, with
very high confidence, a phantom fragment (confirmed real: the 2 phantom columns scored 0/6
non-empty rows while their neighbors scored 6/6) — merged into the preceding column, both
name and content (`_merge_phantom_columns`, called after `_build_table_rows` in both
`build_horizontal_blocks`/`build_rotated_blocks`).

**A 2nd, smaller bug surfaced while fixing the first**: the merged column NAME needed the
right spacing (`"Messages"+"and Codes"` → `"Messages and Codes"` needs a space;
`"Business Tran"+"saction Type"` → `"Business Transaction Type"` needs none — a genuine
mid-word split) so it would match the clean editions' column name for correct cross-edition
diffing — but Module 1 already `.strip()`s every line's text before Module 2 ever sees it,
destroying the leading-space signal needed to tell the 2 cases apart. Fixed with a small,
additive Module 1 change: capture a `starts_with_space` boolean per line (from the
UNSTRIPPED text) alongside the already-stripped `text` field, instead of duplicating the
full raw text — Module 1 re-run, propagated through `_cluster_header_tiers` →
`_finalize_zone_leaves` → `_merge_phantom_columns`. Verified: merged names now read
`"Messages and Codes"` / `"Business Transaction Type"`, matching the clean editions exactly.

Full pipeline (Modules 1-4) re-run after both fixes: 0 regressions on any previously-validated
table, `grid_row` counts unchanged in every appendix except `appendix_e` (phantom-column
merges reduce the row-fragment count slightly, as expected), Appendix E's
`row_content_changed` count in the affected pair dropped 64→40 (fewer spurious "content
vanished" diffs, the real signature of this bug).

**Module 5's classification batch completed (2026-08-20)** — `classify.py` re-run from scratch
(no arguments), all 506 `row_content_changed` items across the 6 edition pairs, ~1h38m on CPU,
0 errors. Aggregate `ai_summary` per pair (business_rule_change / editorial_reword /
extraction_noise, safety_net_override count):
- `20220423→20221014`: 90 / 69 / 17 (override=0)
- `20221014→20230415`: 30 / 0 / 15 (override=9)
- `20230415→20231013`: 47 / 111 / 52 (override=7)
- `20231013→20240413`: 11 / 0 / 4 (override=6)
- `20240413→20250412`: 27 / 3 / 17 (override=9)
- `20250412→20251017`: 9 / 0 / 4 (override=0)

Not yet spot-checked against the source PDF (that validation pass, same discipline as every
other module in this manual, is still pending — do it before declaring Module 5 fully done and
moving to Module 7). Modules 1-4's data files were untouched and did not need re-running.

**Module 5 output validation pass done (2026-08-20, later same day)** — read all 31
`safety_net_override` cases across the 4 affected pairs plus a sample of each normal category.
Found 3 more real bugs (2 fixed, 1 logged):

9. **FIXED. NBSP (U+00A0) vs regular space in column/title header text breaks Module 4's
   column-name-keyed diffing — the single biggest override-yield bug found this session
   (15 of 31 override cases, all in Appendix E's `SMS (Including Interlink) Transactions
   Cross-Reference to VSS Business Transaction Types`).** Root cause: the source PDF encodes
   the space between words in some header/title spans as NBSP instead of a regular space,
   inconsistently — even WITHIN one edition/table (confirmed real: 6 clean-keyed rows + 8
   NBSP-keyed rows in the SAME table in `20240413`, split across pages). `Modulo3/match.py`
   already normalizes whitespace (including NBSP, confirmed Python's `\s` matches U+00A0) for
   table/row identity keys via `_norm()`, but `Modulo4/detect.py`'s `_diff_row` iterated the
   raw `set(cols_a) | set(cols_b)` dict keys with NO normalization — so `"Messages and Codes"`
   and `"Messages\xa0and\xa0Codes"` were treated as 2 different columns. Every mismatch
   produced a PAIR of spurious diffs: a "column vanished" (caught by the Module 5 safety net,
   correctly downgraded to `extraction_noise` but for the wrong reason) AND a "column
   appeared" (NOT caught by anything — no `disappeared_content` to find — silently
   misclassified as `business_rule_change`, a worse, unflagged false positive; confirmed
   several real instances, e.g. `old:"" -> new:"POS Balance Inquiry"`, in the pre-fix output).
   **Fixed at the true root, not at the comparison site**: added `_clean_text()` to
   `Modulo2/normalize.py`, replacing NBSP with a regular space on every line's `text` field at
   the very start of `normalize_edition`, before that text is ever used to build a column name
   or table title — so the inconsistent key can never enter the pipeline. Did not touch
   `match.py`/`detect.py` (root cause fix made their behavior correct without changes).
   **Verified end-to-end**: re-ran Modules 2→5 for all 7 editions/6 pairs. All the false
   `"empty"`-pattern override cases in Appendix E vanished; the genuine ones (the
   `preauthorization`/`preauthorization reversal` "63.0 is set to 1)" trims) survived
   unchanged. `safety_net_override` count dropped exactly as predicted: `20221014→20230415`
   9→3, `20240413→20250412` 9→2 (the other 2 affected pairs, `20230415→20231013` and
   `20231013→20240413`, were untouched at 7 and 6 — those overrides are bugs 10/11 below, a
   different root cause, correctly unaffected by this fix). Total `row_content_changed` across
   the manual: 506→445 (61 fewer, all confirmed spurious). Total `safety_net_override`:
   31→18. Module 5 batch re-run, 0 errors.

10. **Not fixed, logged. Appendix B: Description's first sentence bleeds into the preceding
    `Field Name` column in specific rows/editions (Module 2 column-boundary bug).** Found
    validating the 5 overrides in `20230415→20231013`. Confirmed real: e.g. edition
    `20231013`'s `TC 46, TCR 0 (Report Subgroup 7)` table has `Field Name: "Net Amount Sign
    This field contains the sign for the"` / `Description: "net amount; DB for debit and CR
    for credit."` — the same row is clean in `20230415` (`Field Name: "Net Amount Sign"` /
    `Description: "This field contains the sign for..."`). 5 rows affected in this pair, same
    table family, not investigated further this session (out of scope of the NBSP fix, no user
    request yet to fix it).

11. **Not fixed, logged. Appendix A: `Available VSS Reports` catalog rows split into 2
    unmerged `grid_row` fragments at a page break, truncating content mid-sentence.** Found
    validating the 6 overrides in `20231013→20240413`. Confirmed real on edition `20240413`,
    page 25/26: the `VSS-116`/`VSS-116-M` rows each produce 2 separate `grid_row` blocks — the
    first ends mid-sentence (e.g. `"...the interchange value, reimbursement fees, and Visa"`),
    the second (missing its own anchor value, `Report ID and Report Title` empty) continues
    (`"charges for the Reporting for SRE..."`). Module 3 only matches the first (truncated)
    fragment against the prior edition's full text, producing a false "content vanished
    mid-word" diff. Same architectural class as items 13/14 in [[pending-bug-fixes]]
    (page/chunk reflow not fully reconciled), just a new instance in a new appendix. Not
    fixed this session.

12. **New finding, not fixed, logged (lower priority, narrow).** Appendix B: some `TC 46, TCR
    N (Report Subgroup X)` table titles extract from Module 1 with "TCR" split into 2 words
    (`"TC R"`) AND a regular space instead of NBSP, on ONE occurrence out of ~6 re-declarations
    of the same title (confirmed on raw Module 1 output for `20240413`, `Report Subgroup 2`:
    1 line reads `"TC 46, TC R 0 (Report Subgroup 2)..."`, the other 5 read `"TC\xa046,
    TCR\xa00 (Report Subgroup 2)..."`). This is a SEPARATE malformation from bug 9 above (an
    actual space between "C" and "R", not a NBSP-vs-space difference — whitespace
    normalization can't fix it) and predates/is independent of the Module 2 NBSP fix (confirmed
    present in raw Module 1 JSON, before Module 2 ever runs). Causes 8 `table_removed` +
    1 wrong `table_renamed` (fuzzy-matched to an unrelated Report Subgroup) in Appendix B for
    pair `20240413→20250412` — not chased further this session, logged as a new pending item.

Output files: `data/05_interpretacion_cambios_ia/*.json` (6 files, one per edition pair) in
`poc/visanet_settlement_service_vss_user_guide_volume_2_reports/`. Source PDFs in
`visa/src/vss/`. Module 7 (report generation) not started yet — do that next, OR pick up bugs
10/11/12 first if the user wants more of Appendix A/B cleaned up before generating reports.

**Why:** this manual pushed the project's "generic reconstructor over bespoke per-shape
parser" approach further than any prior manual — 5 distinct content shapes handled by ONE
column-detection/row-reconstruction pair instead of 5 separate implementations, validated by
finding and fixing 6 real bugs through the SAME discipline used throughout the project (real
bbox/font investigation before coding, validation against actual reconstructed content, not
just counts).

**How to apply:** before resuming Module 3+ for this manual, re-read the 6 real-bug writeups
above if touching `_detect_columns`/`_build_table_rows` — several of the calibration constants
(`HEADER_ROW_WRAP_TOLERANCE`, `GROUP_HEADER_MIN_GAP`, `ROTATED_ANCHOR_WRAP_GAP_MAX`) are
evidence-derived from specific real tables, not defaults; re-validate against the whole corpus
(not just 1 table) before changing any of them, same lesson this project has already paid for
twice. The tight-row-packing residual in Appendix D is a known, accepted gap — don't
re-investigate it unless the user asks, and don't confuse it with the (confirmed legitimate)
sparse "(National Net Specific)" rows in Appendix A.

**2026-08-26 session: all 3 remaining items (bugs 10/11/12, [[pending-bug-fixes]] items
15/16/17) RESOLVED.**

**Item 15 (bug 10, Appendix B description-bleed) — same root cause as manual 1's Cook
Islands (item 2) and manual 7's item 13/14: PyMuPDF fuses 2 logically distinct cells into one
`line`, separated by a whitespace-only span** (e.g. edition `20231013`, "Net Amount Sign" +
space + "This field contains the sign for the"). **New complication not present in the other
2 manuals**: the SAME geometric symptom (internal whitespace-only span) also innocuously
separates every WORD of a legitimate single-cell title/legend elsewhere in this manual (e.g.
Appendix A rotated matrix row-label "Settlement Warehouse Returned CRS Deferred", a single
value not 5; a legend "n = Numeric x = Alphanumeric..."; a Comments cell with 2 sentences
joined by a narrow-no-break-space U+202F) — blind splitting (the manual 1/7 approach) would
have corrupted these. **Fix, more surgical than the other 2 manuals**: Module 1 now exposes
candidate segments (split only on whitespace-only spans, deciding nothing) via a new
`segments` field. Module 2's `_resegment_by_column` (called from `_build_table_rows`, which
already has the active table's column geometry) only applies the split when segments land in
GENUINELY different column bands (`_nearest_band`) — same-column segments stay fused exactly
as before. Verified: 0 suspicious `Field Name` values left across all 7 editions (scanned for
>6-word values with punctuation), 0 regression on all 3 risk cases confirmed by hand, `grid_row`
totals unchanged (2601-2685, same as baseline), 0 empty rows, 0 disposable-content leakage.

**Item 17 (bug 12, Appendix B "TC R" title split) — narrow, safe text-normalization fix.**
Full-corpus scan of the literal substring `"TC R"` (word-boundary) across all 7 editions/5
appendices: appears ONLY in 3 consecutive editions (`20230415`-`20240413`, self-corrects from
`20250412`), ALWAYS the same 9 instances (1 per "Report Subgroup" table, always the table's
own 10.5pt title, always page 1 of that table), ZERO legitimate occurrences anywhere else in
the corpus — a fully safe signal for a blanket text substitution. Added `TCR_SPLIT =
re.compile(r"\bTC R\b")` to `_clean_text` (alongside the existing NBSP normalization).
Verified: Appendix B for pair `20240413→20250412` went from `30->22 tablas (+0/-8)` to
`22->22 tablas (+0/-0)` — the 8 spurious `table_removed` + 1 `table_renamed` are gone.

**Item 16 (bug 11, Appendix A page-split) — real root cause turned out DIFFERENT from what was
originally logged, and MUCH bigger in scope.** Originally assumed to be a genuine page-boundary
issue (Module 2 never carries a row across pages). Investigating the concrete case
(`VSS-116`/`(Fee by Jurisdiction)`) found this was WRONG — both fragments are on the SAME page
25, not different pages. **Real cause**: `ROTATED_ANCHOR_WRAP_GAP_MAX=4.0` (calibrated
2026-08-19 against only 2 tables) missed a SECOND legitimate wrap-gap mode: when the anchor
column's value wraps across 3+ lines, the gap between the 2nd and 3rd fragment can be
noticeably larger (4.1-6.6pt) than the tight ~0pt gap between the 1st and 2nd — above the old
threshold, spuriously triggering a new row that split the last fragment off from its own
value. **Recalibrated with full-corpus evidence** (7200 real gaps, 7 editions, both rotated
appendices, computed via the actual zone/column logic, not an approximation): a clean,
non-overlapping boundary — max real wrap gap 6.6pt, min real new-row gap 7.0pt. Recalibrated
to 6.8 (midpoint). **Scope much bigger than logged**: originally logged as "2 confirmed
instances" but investigating found the 3 oldest editions (`20220423`-`20230415`) had the SAME
bug affecting 35 of 79 rows (44%) of the `Available VSS Reports` catalog — the symptom there
looked unrelated (the `"VSS-100-W —"` ID prefix missing from the start of each title) but
turned out to be the identical root cause, just with more wrap fragments per row in those
editions. Post-fix: 0 rows with a missing ID prefix across all 7 editions (was 35 in 3
editions). **Verified end-to-end**: `grid_row` totals dropped 2601-2685 → 2509-2582
manual-wide (spurious fragments merging back into their real row, no data loss),
`unassigned_prefix` unchanged (1-3, same baseline), 0 empty rows. Re-confirmed the ORIGINAL
case that motivated the 4.0 threshold (Appendix D p.366, V22200, 9 distinct fields) still
correctly stays split (10 rows, not over-merged). Modules 3/4 re-run: table counts unchanged
(only row counts changed, as expected), total `row_content_changed` dropped 419→383 on top of
the 445→419 already gained from items 15/17.

**Full pipeline (Modules 1→5,7) re-run together after all 3 fixes, across all 7 editions/6
pairs.** `row_content_changed` 445→383 total (62 fewer, all confirmed spurious extraction
noise, not real content). Module 5 (LLM classification, 383 items, Ollama) completed: total
`safety_net_override` dropped 18→9 — the pair `20231013→20240413` (originally logged with "6
overrides" caused by item 16) went from 6 to 0, confirming the fix's real-world impact per
edition:
- `20220423→20221014`: business_rule_change=86, editorial_reword=69, extraction_noise=19
  (override=0)
- `20221014→20230415`: business_rule_change=12, extraction_noise=2 (override=3)
- `20230415→20231013`: business_rule_change=29, editorial_reword=100, extraction_noise=31
  (override=4)
- `20231013→20240413`: business_rule_change=6, extraction_noise=8 (override=0, was 6)
- `20240413→20250412`: business_rule_change=7, editorial_reword=1 (override=2)
- `20250412→20251017`: business_rule_change=9, extraction_noise=4 (override=0)

Module 7 (report regeneration) completed: business changes per pair 86/12/29/6/7/9 (was
90/12/47/11/8/9 before these 3 fixes — big drops in pairs 3 and 4 specifically, `47→29` and
`11→6`, exactly the pairs most affected by items 15/16/17's spurious extraction noise
cascading into false `business_rule_change` classifications). Spot-checked the VSS-116/
VSS-116-M case directly in the final reports: both editions now extract their full titles
cleanly (`20231013`: `"VSS-116 – SRE Settlement Recap Report"`; `20240413`: same + `" (Fee by
Jurisdiction)"`) — confirmed this suffix is a REAL title change between editions, not a
residual extraction bug, correctly captured as a genuine business-relevant rename now that
both sides parse without fragmentation.

**With this, all 3 items logged for this manual (15/16/17) are resolved and verified
end-to-end** — manual 8 has no unexplored TODO items left, matching manual 7's status from the
same session. Both manuals 7 and 8 (the explicit user-requested order for this session) are
now fully closed.
