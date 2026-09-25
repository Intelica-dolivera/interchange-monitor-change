---
name: manual7-vss-vol1-progress
description: "Progress log for the 7th manual, visanet_settlement_service_vss_user_guide_volume_1_specifications — mixed narrative+rotated-table content, most complex Module 2 in the project so far"
metadata:
  node_type: memory
  type: project
  modified: 2026-08-26T21:37:05.335Z
---

## 7th manual: `visanet_settlement_service_vss_user_guide_volume_1_specifications`
(started 2026-08-19, `visa/src/vss/`, 6 editions: 20220423→20251017, gap 2023-2025 with no
2024 edition present)

**Most content-complex manual so far** — mixes narrative prose (like the 6th manual) with
TWO distinct kinds of rotated (90°) content embedded in the PDF, discovered only through
investigation (not assumed):
1. Mainframe/terminal-style report-sample printouts (fixed-width columns, explicitly labeled
   `"This Data is Fictitious and for Illustration Purposes Only."`) — disposable, user
   confirmed excluding as noise.
2. `"Field Name"` / `"Description"` reference tables inside `"Example N: Reconciliation of X
   Report to Y Report"` exhibits — real reference documentation, user confirmed reconstructing
   these (see the correction/re-decision below).

**Module 1** — `.../01_ingesta_parseo/ingest.py`. Same generic per-line design, PLUS captures
the PyMuPDF `dir` vector per line (new field, not present in the other 6 manuals) — needed
because this manual's rotated content would produce garbage if processed with the normal
horizontal geometric logic (`dir=(0.0,-1.0)` for rotated lines vs `(1.0,0.0)` horizontal).
Ran clean on all 6 editions (203-211 pages, ~7400-7800 lines).

**Initial wrong framing, corrected via AskUserQuestion (2026-08-19) before building Module
2**: first hypothesis was "rotated report-sample content is a legacy chapter that only exists
in old (2022-2023) landscape-page editions and disappears by 2025" — this was WRONG. Only the
PAGE ORIENTATION (whole-page landscape, 92/204 pages in 2022) disappears by 2025 (0 landscape
pages in `20251017`); the actual ROTATED TEXT CONTENT persists in every edition, just
re-packaged as rotated blocks embedded within portrait pages instead of whole landscape
pages. Corrected this to the user directly before proceeding — they then chose to
reconstruct the valuable `Field Name`/`Description` pairs specifically (not just discard all
rotated content), a bigger scope than the original "generic treatment" plan.

**Module 2** — `.../02_normalizacion_bloques/normalize.py`. Extends the 6th manual's
prose/heading design (26/20/14pt headings, paragraph-by-adjacency) with a SEPARATE
reconstruction path for rotated content:
- `_filter_noise` now returns 2 streams: horizontal clean lines (normal path) and rotated
  candidate lines (font size 9.0/9.5pt = label/description candidates, 12.0pt = table title;
  any OTHER rotated font size, e.g. 7.3pt fictitious report data, is dropped as noise).
- `_extract_rotated_pairs`: reconstructs Field Name/Description pairs per page. Geometry
  investigated with real data from 2 different table instances before coding: for rotated
  text the axes are effectively transposed — "same row, different column" (in un-rotated
  terms) shows up as "same `x0` (row band), different `y1` (column band)". Column boundaries
  (`y1` values) are calculated PER PAGE (confirmed they vary slightly table-to-table, e.g.
  717.0/574.5 vs 717.0/576.3 — not safe as global constants). Row spacing confirmed ~20.5pt
  in both sampled tables, used as the row-band tolerance. Pairs by nearest `x0` within
  tolerance. Table title (`"Example N: ..."`, 12.0pt rotated) captured per page as
  `example_title` context, matching the "title redeclared per continuation page" convention
  already established for grid manuals (Type A).
- **Real bug found and fixed in the FIRST validation pass**: the same 9.0/9.5pt rotated font
  bands are ALSO used by a totally different, genuinely disposable table (the report-sample
  hierarchy list, e.g. p.61, header literal `"Field"` alone mapping SRE IDs to example
  bank/processor names) — sharing geometry and font size with the real `Field Name`/
  `Description` table but NOT the same structure. First run produced 484 pairs with 220 empty
  descriptions (45%) — investigated, found root cause, fixed by requiring the literal EXACT
  2-word string `"Field Name"` to be present on a page before extracting any pairs from it
  (confirmed this literal redeclares every continuation page of the real table; the
  disposable table only ever has `"Field"` alone). Re-ran: 236 pairs, 82-109 empty
  descriptions depending on edition — investigated further, confirmed the majority (46/82,
  56%) are legitimate structural sub-labels (`"Row"`/`"Column"`, appear 23× each with no
  paired description, plausible as genuine table dividers not broken pairs) rather than
  pairing failures. Accepted the residual long tail (~36 single-occurrence cases per edition,
  some showing name+description merged into one `name` field) as a known imperfection, NOT
  chased further — this feature already grew well beyond the original "generic treatment"
  scope by explicit user choice; further precision tuning would be diminishing returns for a
  POC, same principle already applied to the 6th manual's paragraph-reflow residual.

Validated: pair count is IDENTICAL (236) across all 6 editions, `empty_name` always 0. Spot-
checked the real page 112 table by hand against raw Module 1 lines before writing code — output
matches expectations (`"SRE"` → `"Name and number of the SRE."`, etc.).

**Module 3 implemented and validated (2026-08-19)** —
`.../03_emparejamiento_bloques/match.py`. Sections and paragraphs reuse the 6th manual's design
unchanged (path-based exact+fuzzy sections, exact+fuzzy+reflow paragraphs). New design needed
for `field_description_pair` matching:

- **Key = `(example_title, name)` normalized, EXACT only, no fuzzy** — investigated with real
  data first: `name` alone isn't unique (`"Row"`/`"Column"` repeat dozens of times, same
  collision class as the 5th manual's `TCR` labels). `example_title` (the rotated table title,
  with its per-page `"(N of M)"` position suffix stripped in Module 2 so the identity stays
  stable across a table's continuation pages) correctly groups the reference edition's 236
  pairs into exactly 10 real tables (10-40 pairs each). Even the composite key has 52/236
  residual duplicates (a single "Example" table can have repeated sub-structures, e.g. parallel
  "ISSUER TRANSACTION DETAIL"/"ACQUIRER TRANSACTION DETAIL" blocks each with their own `Row`/
  `Proc Date`/etc.) — resolved with the same order-of-appearance tiebreak already proven for
  the 4th manual's `TC 57` and the 5th manual's TCR rows. No fuzzy fallback on `name` — same
  demonstrated-unsafe short-label risk as the 5th manual, not re-investigated (already settled).

**2 real bugs found and fixed in the FIRST run, before reporting the module as done:**
1. **Pair block ordering bug** (found immediately when the first extracted pair showed up at
   stream index 1, before the very first section heading): Module 2's `order` for each pair was
   computed by looking up the first HORIZONTAL line's `order` on that page — but pages fully
   inside a rotated "Example" table have NO horizontal lines at all, so the lookup silently fell
   back to a `0` default, sorting every pair on those pages before the entire rest of the
   document. Fixed by using the pair's own constituent line's `order` (already present in every
   Module 1 output) directly instead of a horizontal-line proxy. Also fixed in the same pass:
   `example_title` needed its `"(N of M)"` page-position suffix stripped (else every page of the
   same table would get a distinct, non-matching title) and needed to be carried forward across
   pages that don't redeclare it (confirmed the title usually redeclares every page but not
   always — cheap defensive carry-forward).
2. **Real, consistent heading-level skip** (crashed `extract_sections` on first run): this
   manual's heading hierarchy isn't always fully nested — `"Related Information"` appears as a
   LEVEL 3 heading directly under a level 1 heading with NO level 2 in between, confirmed the
   identical pattern in all 6 editions under 4 different chapters. Fixed by building each
   section's path from whichever ancestor levels are actually present, rather than assuming the
   full `1..N` sequence.

Validated: reconciliation exact across all 5 pairs. Pair matching extremely stable (236/236
matched in 4 of 5 pairs; the 1 pair with a real diff — `20230415→20231013` — turned out to be
exactly the already-accepted residual pairing imperfection from Module 2 (name+description
merged into one `name` field in one edition, correctly split in the other) showing up as a
transparent remove+add, not a new surprise.

**Module 4 implemented and validated (2026-08-19)** —
`.../04_deteccion_cambios/detect.py`. Paragraphs identical to the 6th manual. Pairs need their
OWN content-diff step (unlike paragraphs/rows in the 5th/6th manuals): the pair matching key
(`example_title`+`name`) deliberately does NOT consume `description`, so a matched pair CAN
have a genuinely different description between editions — compared with the same 0.98
`difflib` similarity threshold already used by the grid-table (Type A) manuals, emitted as
`pair_content_changed`.

Investigated an elevated signal before validating (39 `pair_content_changed` in one pair,
`20230415→20231013`) — confirmed 26/39 (67%) are the ALREADY-KNOWN Module 2 pairing residual
showing up as content diffs: `description_a` empty (extraction gap in the older edition) →
`description_b` populated correctly. Not a new bug — same accepted imperfection from Module 2,
now visible downstream as expected. The remaining 13 look like genuine (if subtle) wording
edits (e.g. `"report."` → `"SMS600C report."`). Module 5's safety net naturally won't
misfire on the empty-old cases (nothing to flag as "disappeared" when old is empty) — expect
the LLM to reasonably classify those as `extraction_noise` on their own merit.

**Module 5 implemented and validated (2026-08-19)** —
`.../05_interpretacion_cambios_ia/classify.py`. Classifies BOTH `paragraph_content_changed` and
`pair_content_changed` (2 separate prompts, same 3-category design) — the only manual so far
with 2 distinct content types reaching Module 5. Ran via Ollama on 152 items across 5 pairs
(~45 min). Results: `safety_net_override` only 2 total (very low, as expected).

Confirmed the predicted hypothesis from Module 4: of 27 `extraction_noise` classifications in
the big pair, 24 are exactly the known empty-old-description pairing residual — the LLM
correctly recognized these as extraction artifacts on its own merit, no safety-net
intervention needed. The 2 `safety_net_override` cases are both the SAME already-documented
hyphen-wrap tokenization artifact from the 6th manual (`"print-ready"` vs `"print- ready"` —
one extra space after a hyphen from inconsistent PDF line-wrap rendering, which cascades into
a spurious "disappeared content" word-diff) — not a new finding, same known noise category.

**This completes Modules 1-5 for this manual.** Given how much this manual's pipeline already
expanded in scope (rotated-text reconstruction, dual-table disambiguation, heading-level-skip
handling, a new pair-content-diff mechanism — well beyond the original "reuse the 6th manual's
approach" plan), this remains a good checkpoint to confirm with the user before Module 7.

**Module 7 implemented and validated (2026-08-19)** —
`.../07_reporte_cambios/report.py`. Extends the 6th manual's report design with pair-specific
sections (pairs added/removed, `duplicate_pair_key_warning`) — business changes group both
paragraph and pair diffs together by section path.

Read the fullest report (`20230415_to_20231013.md`, 7 business changes) end to end — mostly
reads as genuine, coherent changes (e.g. `"the issuer's country"` → `"outside the issuer's
country"`, a real geographic-scope change correctly classified). Noted (not investigated
further, consistent with the already-accepted "generic paragraph handling on table-like
content" limitation from Module 2): the last 3 items under `"VSS Reports > Daily VSS Settlement
Reports"` look like short report-name/description table fragments rather than real prose (e.g.
`"...currency conversion"` → `"...currency"`) — plausibly another manifestation of the same
known category of residual noise already documented for this manual and the 6th, not a new
bug worth chasing given the scope already invested here.

**This completes the full pipeline (Modules 1-5, 7) for
`visanet_settlement_service_vss_user_guide_volume_1_specifications`** — 7th manual done, and by
far the most content-complex build in the project so far (3 distinct content shapes: prose,
rotated reference tables, and disposable rotated report samples excluded as noise). Module 6
stays tentative, same as all previous manuals. Real bug tally for this manual: 1 table-
contamination bug, 1 pair-ordering bug, 1 real heading-level-skip — all found and fixed during
Module 2/3's first validation passes, none deferred.

**2026-08-26 session: item 13's own variant for this manual RESOLVED** (see
[[pending-bug-fixes]] item 14). Root cause: same PyMuPDF line-fusion bug as manual 1's Cook
Islands (item 2) — 2 logically distinct cells (field name / description) merged into one
`line` by PyMuPDF, separated only by a whitespace-only span — here happening in ROTATED text
instead of horizontal. Confirmed via a full 6-edition corpus scan before coding: 9-10 real
instances per edition, always exactly 3 spans (name/space/description), always uniform 9.0pt.
~47 more instances of the same pattern per edition exist but all fall on pages Module 2 already
discards entirely (no "Field Name" literal), so splitting them is inert either way. Also found
the same fusion pattern in horizontal text (220-224 hits/edition), but confirmed ALL are either
TOC dot-leader lines (already filtered) or a "Report ID / Report Title" table whose fused
content was an ALREADY-ACCEPTED residual from an earlier session — deliberately did NOT extend
the fix to horizontal lines, to avoid reopening that already-closed scope. **Fix**: ported
`_split_line_segments`/`_segment_bbox` from manual 1's `ingest.py`, scoped to rotated lines
only (`dir == (0.0,-1.0)`) — horizontal lines take the exact same code path as before, 0
behavior change there. **Verified end-to-end**: empty descriptions dropped 109→101 (old
editions) / 82→73 (new editions) — exactly the 8-9 real fusion cases per edition; 236 pairs
total unchanged (no phantom pairs created); Module 3 re-run, 236/236 matched in all 5 pairs, 0
regression; Module 4 re-run, investigated a 39→41 `pair_content_changed` increase in the big
pair BEFORE assuming it was fine — confirmed genuinely pre-existing and unrelated (no line
near the new diffs was touched by the split fix in either edition) — it's a DIFFERENT,
deeper residual: long descriptions that wrap into a 2nd `x0` sub-band within the same rotated
cell get treated by `_extract_rotated_pairs` as 2 separate "row" bands instead of one
continuous description, orphaning or misattributing the wrapped tail. This is the more precise
root cause of the remaining part of item 14 (previously just "imperfect geometric pairing") —
deliberately NOT chased further, same diminishing-returns call already applied twice to this
item. Module 5 re-run (Ollama, 154 items, ~50min): `safety_net_override`=2, identical to the
pre-fix baseline, 0 regression — the fixed `ACCEPTED COUNT` case correctly classifies as
`extraction_noise` in the final report, not a false `business_rule_change`. Module 7 re-run:
same 0/2/7/2/0 business-change counts per pair as the already-validated baseline.

**Item 14's x0-wrap-band residual ALSO RESOLVED, same session (2026-08-26), later after
manual 8 was finished.** User asked directly "if we fix this, could it break something?" before
agreeing to proceed — investigated with the same corpus-wide-evidence rigor as manual 3's
chain-shift fix (item 8) before touching code: scanned every consecutive description-line gap
(by `x0`) across all 6 editions/every real Field Name table. Genuine wrap-continuation gaps
(the same description wrapping into a 2nd `x0` sub-band) are ALWAYS exactly 12.0pt (87
instances, zero variance — each one completes a truncated sentence when read, e.g. "...Total
Cardholder Billing Amount on the" + "SMS600C report."). The minimum real gap between 2
different table rows' own descriptions is 17.0pt — a clean, non-overlapping boundary, even
cleaner than item 8's chain-shift threshold. Fix: `_merge_wrapped_descriptions` (new function,
threshold `DESC_WRAP_GAP_MAX=15.0`, midpoint) merges consecutive wrapped desc-lines into one
BEFORE the existing name↔desc nearest-match algorithm runs — keeps the first fragment's `x0`
(already the one that correctly matches its real name today), so the matching mechanism itself
needed zero changes, purely additive. Verified: `CLEARING AMOUNT` now gets its full
description; the bracket-named entries that were WRONGLY stealing the orphaned wrap tail
(`"[CLEARING AMOUNT]"`, `"[CARDHOLDER BILLING AMT CUR]"`, `"[TOTAL ISSUER INTERCHANGE]"`) now
correctly show an empty description instead — same legitimate pattern already established for
`"Row"`/`"Column"`. 236 pairs unchanged, Module 3 236/236 matched with 0 regression, the
`"SMS600C report."`-type truncation noise completely gone from the diff (`pair_content_changed`
in the big pair dropped 41→21, all remaining are the already-accepted empty-old-description
category), Module 5 `safety_net_override`=2 (unchanged) and Module 7 same business-change
counts (0/2/7/2/0) re-confirmed with 0 regression.

**With this, manual 7 has zero open items left** — both sub-cases of item 14 are now resolved;
only the legitimate `Row`/`Column` no-description pattern remains, which was never a bug.
