---
name: pending-bug-fixes
description: "Consolidated, scannable TODO list of known-but-unfixed bugs/gaps in the interchange_change_monitor POC, to pick up later"
metadata: 
  node_type: memory
  type: project
  modified: 2026-09-10T16:33:15.117Z
---

Short, scannable index of bugs/gaps found but deliberately left unfixed (or, for most items,
already resolved — check each item's own status tag, this index isn't purely a TODO list
anymore). 24 items as of 2026-09-10 (items 21-22 added 2026-09-04, item 22 resolved 2026-09-05;
item 23 added 2026-09-09, a deferred feature idea rather than a bug; item 24 added 2026-09-10, a
completed one-off Qwen-vs-Gemini comparison test, not a bug either — see each entry).
Full
narrative/evidence for each lives in `local_memory/TODO.md` and `local_memory/NOTES.md` in the
repo — read those before acting, this memory is just the pointer/index so a future session doesn't
have to re-discover these from scratch. [[open-questions-technical-manuals]] has the fuller module-
by-module status if more context is needed.

1. **RESOLVED (2026-08-25).** Originally: glossary section not parsed as structured entries —
   `base_ii_clearing_data_codes`, Module 2 (user later asked to pick this up despite the earlier
   deprioritization, along with items 3b/4/5 below, all in the same session). Root cause: the
   glossary is geometrically the SAME 2-column pattern (bold term at X0=72 / regular definition at
   X0=216, both 9.0pt) Module 2 already reconstructs for code tables — it collapsed only because the
   "new row?" heuristic keyed 100% off `CODE_LIKE` (short code), which a glossary term never
   matches. No new block type needed. **Fixed**: added `bold` and `max_size` per-line fields in
   Module 1; Module 2 tracks an `in_glossary` state (activated on the real 26pt "Glossary" heading —
   `max_size` was needed because the table-of-contents has a same-text, same-bold, 12pt homonym
   entry that would otherwise false-trigger) and treats any bold cell as the "code cell" signal
   while active. A vertical-gap check (`GLOSSARY_TERM_WRAP_GAP_MAX`, calibrated on a full 9-edition
   scan: wrap gaps ≤0pt vs new-entry gaps ≥9.3pt) distinguishes a term wrapped across 2+ lines (e.g.
   "Account Screen Authorization File (ASAF)") from a genuine new entry. **Real collateral bug found
   validating Module 3**: it only recognizes a logical table when it sees an explicit
   `table_header` — a bare `table_row` with no active table falls into a generic "orphan row"
   bucket titled `"(sin titulo)"`, which would have silently merged the ~200 glossary rows with ANY
   other unrelated orphan row elsewhere in the document (via title-based coalescing). Fixed by
   emitting a synthetic `table_header` (`["Term","Definition"]`) once, right before the first real
   entry, without touching the generic orphan-row mechanism other tables rely on. **Verified**:
   Modules 1→4 re-run across all 9 editions, ~198-201 clean entries/edition (was 1-2 giant blobs),
   0 `"(sin titulo)"` tables, "Glossary" matches stably across all 8 consecutive pairs. Already
   surfacing real, previously-invisible changes (e.g. `OPTIONAL ISSUER FEE`'s full definition
   replaced by a cross-reference to another term). Not replicated in the 2nd manual's smaller
   glossary (not asked this session). Full detail in `local_memory/NOTES.md`, session 2026-08-25.
2. **RESOLVED (2026-08-20).** Originally: `"Cook Islands (the) CK"` — PyMuPDF text-fusion quirk,
   thought to be 1 row, 1 edition. Real scope, found investigating: 3 editions (`20220423`-
   `20230415`, self-corrects from `20231014` on) for Cook Islands specifically, plus the SAME
   fusion pattern on ~6 more instances across the corpus (`Moroccan Dirham MAD`, `Canadian
   DollarS CAD`, `Zimbabwe Dollar ZWL`, `American Samoa AS`, plus 2 non-Country/Currency-table
   instances — a code-definition table on p.60 and a 2-column matrix on p.135/136). Root cause:
   PyMuPDF sometimes groups 2 logically different table cells (e.g. country name + alpha code)
   into ONE `line` object with an explicit whitespace-ONLY span between them, which Module 1
   simply concatenated. **Fixed**: `_split_line_segments()` in Module 1 (`ingest.py`) splits a
   PyMuPDF line into separate output lines at any standalone whitespace-only span, each with its
   own recomputed bbox — confirmed via a full-corpus scan (excluding TOC dot-leader lines, which
   use the same signal but are handled separately) that this pattern ALWAYS separates 2 distinct
   pieces of content, never appears within one real cell. **1 regression found and fixed
   immediately while validating**: naively splitting also broke the TOC's dot-leader filter in
   Module 2 (`is_noise`, which matches `(\. ){4,}` against a line's FULL text) — a split TOC line's
   first fragment (just the title) no longer contains the dot-leader pattern and would leak
   through as real content. Fixed by detecting the dot-leader pattern on the line's raw
   (unsplit) text BEFORE deciding to split, and skipping the split entirely for those lines.
   Verified end-to-end: Modules 1-4 re-run, 0 structural regressions (0 pages without blocks, 0
   empty cells, `table_row` counts identical to pre-fix baseline), TOC page confirmed clean of
   leaked dot-leader entries. **Modules 5 and 7 re-run too (2026-08-20, same session)**: Module 5
   batch (301 items, ~50min CPU) finished 0 errors, `safety_net_override` 10 total (close to the
   item-3 baseline); Module 7 regenerated all 8 reports — grepped for "cook island" across every
   report, 0 hits, confirming the fix removed the spurious diff noise entirely rather than just
   changing its shape. Full pipeline (Modules 1-5, 7) now clean for both item 2 and item 3 fixes
   together. Full detail in `local_memory/NOTES.md` (repo).
3. **RESOLVED (2026-08-20).** Originally: footnote-digit-superscript corruption of Croatia/Sierra
   Leone's currency codes in `base_ii_clearing_data_codes`'s `Country and Currency Codes` table,
   thought to be a single `20230415` instance. Full investigation (2026-08-20) found the REAL scope
   was much bigger: Croatia corrupted across 6 consecutive editions (`20221015`→`20250412`), Sierra
   Leone across 2 (`20221015`, `20230415`), via 2 distinct root causes — (a) Module 1 concatenated a
   footnote superscript digit (6.75pt) into the same PyMuPDF line as a real code (9.0pt) with no
   separator, e.g. `'HRK'+'1'`→`'HRK1'`; found via a full-corpus scan that this ALSO affected dozens
   of unrelated codes elsewhere in the document (e.g. `Merchant Mailing CRB Region Codes`, `'X'+'1'`
   colliding with the real, distinct code `'X1'`) — not scoped to just Croatia/Sierra Leone. (b)
   Module 2's row-grouping treated a country's "secondary/transitioning currency" sub-line (no
   country-name anchor, e.g. Sierra Leone's old `SLL/694` stacked with its new `SLE/925`) as an
   independent orphan row instead of merging it into the right country's row. **Both fixed**: (a) a
   `_line_text_or_none` filter in Module 1 (`ingest.py`) drops small-font pure-digit/comma spans
   before concatenation; (b) an anchor-column proximity check in Module 2 (`normalize.py`,
   `SECONDARY_ROW_ANCHOR_GAP_MIN`) reroutes off-anchor code-cell rows into the gap-based
   merge/`pending_prefix` path instead of always treating them as new rows. **2 regressions found
   and fixed while validating (b) against the full 9-edition corpus, not just Croatia/Sierra
   Leone** (same "don't trust a threshold calibrated against 1 table" lesson as
   [[manual8-vss-vol2-progress]]): the anchor-check first broke 2 unrelated tables where a header
   label or a `(continued)` marker legitimately sits ~20-30pt left of its own data rows (fixed by
   scoping the check to `table_row`→`table_row` transitions only, recalibrating the threshold to
   150.0 using a full-corpus gap scan — real false-positive gaps topped out at 78.1, real true
   positives started at 233.9, wide margin); then a "closer gap wins" heuristic misrouted Sierra
   Leone's secondary currency row into Singapore's (the next country alphabetically) because the
   numeric gap to Singapore happened to be smaller than to Sierra Leone even though neither
   genuinely overlapped — fixed by requiring real Y-band overlap with the next row before deferring
   to it, otherwise always merging into the active row. Verified end-to-end (Modules 1→5,7 re-run,
   0 structural regressions across 9 editions, Croatia/Sierra Leone/Singapore diffs all read
   correctly in the final report). Full detail in `local_memory/NOTES.md` (repo), session
   2026-08-20. **Zimbabwe has a related-but-distinct residual, NOT fixed** — see item 3b below.
3b. **PARTIALLY RESOLVED (2026-08-25), residual further reduced 2026-09-05.** Zimbabwe's
    country-name cell absorbing the trailing footnote block + next section's heading — same
    "footnote bleeds into table boundary" bug class as item 3, different mechanism. Root cause
    confirmed: the footnote block (and the next section's heading) starts at the exact same X0 as
    the table's anchor column, so the paragraph-start-by-left-shift heuristic never fires, and the
    vertical gap (~10.9pt) is too close to a normal row-to-row gap (~8.5pt) to use as a standalone
    signal. **Fixed for the numbered-footnote variant** (`"1 From 1 January 2023, acquirers can
    submit..."`): added `starts_with_footnote_marker` in Module 1 (small-font digit as the FIRST
    span of a line, followed by 15+ chars of prose — confirmed via full-corpus scan this pattern
    always marks a genuine footnote-paragraph start, 10 distinct instances, 0 false positives;
    distinct from item 3's already-fixed fusion pattern, where the digit is the LAST span, not the
    first). Module 2 treats this signal like the left-margin-shift check (flush + start a new
    paragraph). Verified clean in 5 of the 7 originally-affected editions (`20220423`-`20250412`).

    **2026-09-05 follow-up, user asked to size the remaining residual before fixing.**
    Investigated the actual data before touching anything and found the prior note's own claim
    was wrong: the `"Note:"` label from edition `20251018` on is **NOT bold** (checked the raw
    Module 1 span data directly — `bold: false`) — a stale assumption in this memory, now
    corrected. Also found the 2 affected editions' shape genuinely differs: `20260418` dropped
    the ZWG/ZWL note text entirely (Visa's transition note became obsolete), so Zimbabwe's cell
    there absorbs the NEXT section's 26pt heading + intro directly with no note in between;
    `20251018` still has the (non-bold) `"Note:"` paragraph fused in, unchanged from before.
    **Fixed the cheap, safe part**: added `MAJOR_HEADING_MIN_SIZE=20.0` (same threshold/tier as
    the already-validated `GLOSSARY_HEADING_MIN_SIZE`) — any bold line ≥20pt now forces a hard
    block break instead of fusing into an active table row, reusing a signal already proven safe
    project-wide (corpus-wide scan: 83-93 such lines per edition across all 9 editions, always
    genuine section/table titles, never real cell content). This fully closes `20260418`'s
    variant (Zimbabwe's cell is now just `"Zimbabwe"`, 8 chars, was 681) and meaningfully shrinks
    `20251018`'s (424→136 chars — no longer swallows "Canadian Province Codes" and its intro,
    only its own on-topic note remains fused). **Unexpected bonus scope, found validating against
    the full corpus, not assumed**: this same "major heading fused into the wrong active table"
    bug was NOT unique to Zimbabwe — 5 of 8 edition-pairs showed spurious `code_added`/
    `code_removed` counts drop after the fix (e.g. `20251018_to_20260418`: 31→20 removed, 27→16
    added, `code_content_changed` unchanged at 114 both times), plus a phantom
    `"Restricted Ticket Indicators"` table_added/removed pair vanished in 2 pairs, plus 1 currency
    row (`QATARI RIAL`) was mis-attributed to the wrong table (`"U.S. State Codes"` instead of
    `"Settlement Currencies"`) before the fix and is now correctly attributed. Verified end-to-end:
    Modules 2→4 re-run for all 9 editions/8 pairs, block counts rose 4-13 per edition (each a
    genuine split-off heading, none a regression — confirmed by diffing exactly which
    `code_added`/`code_removed`/`table_added` keys changed in every pair, all removals were
    fabricated noise, all keeps were untouched, `code_content_changed` byte-identical in every
    pair). Module 5 re-run with real Ollama (not `--skip-ai`) for the 5 pairs whose Module 4
    output changed — 0 errors, `safety_net_override` counts consistent with expectations. Module 7
    regenerated for all 8 pairs.

    **Follow-up RESOLVED (2026-09-05, same day, user asked to close it right after the first
    fix).** Closed the remaining piece: the `"Note:"` paragraph itself fusing into Zimbabwe's own
    cell in `20251018`. Measured the safety of a lookahead signal against the full corpus BEFORE
    implementing (same discipline as always) — `_note_precedes_major_heading` in `normalize.py`:
    a single-line row is treated as a footnote-block start (same as the numbered-marker signal)
    only when ALL 3 hold: (1) it is NOT itself a real code (`CODE_LIKE`) — without this, the
    genuine code `"X"` of a "Visa B2B Virtual Payments" row that happens to sit right before a
    section heading was a false positive; (2) it starts at the SAME anchor x0 as the active row
    — without this, ordinary multi-line description wraps that happen to end near a heading were
    false positives; (3) a `MAJOR_HEADING_MIN_SIZE` line appears within
    `NOTE_BEFORE_HEADING_LOOKAHEAD=5` rows with no real code row in between (K=5/10/20 all give
    the identical result, so not a fragile threshold). Measured against the real corpus: exactly
    8 matches in all 9 editions, 0 false positives. **Real finding, bigger than "just Zimbabwe"**:
    7 of the 8 are a DIFFERENT recurring case — the same "Type D (Dispute) stopped being valid"
    footnote fused into codes `04` and `7` of 2 separate dispute-code tables, in every edition —
    confirming this was never a Zimbabwe-specific bug, just the only instance anyone had noticed.
    **Verified end-to-end**: Modules 2→5,7 re-run; Zimbabwe's cell is now clean (`"Zimbabwe"`, 8
    chars) in ALL 9 editions (not just `20260418` as the first pass left it); Module 4's only
    changes were the exact contaminated `code_added`/`code_removed` pairs disappearing from BOTH
    sides with nothing new appearing (3 pairs in `20250412_to_20251018`, 1 pair in
    `20251018_to_20260418`) — confirms pure noise elimination, `code_content_changed` byte-
    identical (117 and 114) in both affected pairs; Module 5 re-run with real Ollama for those 2
    pairs reproduced identical classifications to the pre-fix run (confirms the fix never touched
    content already correctly classified, only structural add/remove noise). **Item 3b is now
    fully resolved — no residual left**, closing a bug that turned out both broader (affects
    other tables, not just Zimbabwe) and more fixable (2 additive signal checks, no risky
    restructuring) than originally assessed.
4. **RESOLVED (2026-08-25).** Originally logged as purely cosmetic: Module 5 safety net's evidence
   text was uninformative on bullet-heavy rows (`H0`/`HZ` codes, `"l l l l l l l l l"` bullet-glyph
   strings instead of substantive text in `_find_disappeared_content`). **Fixed**: bullet-glyph
   tokens (`"l"`, `"●"`, `"•"` — confirmed via corpus scan only `"l"` actually appears, `"-"` is
   real hyphenated content, not a bullet) are filtered from both old/new word lists before the
   word-level diff. **Turned out to matter more than cosmetically**: for H0/HZ specifically, the
   "disappeared content" that had been triggering `safety_net_override=True` (forcing
   `business_rule_change`) was PURE bullet-position noise — the underlying field list was byte-
   identical between editions, just with bullets shifted. Post-fix, both cases correctly revert to
   the LLM's original `editorial_reword` classification — 2 real false-positive overrides fixed,
   not just evidence cleanup.
5. **RESOLVED (2026-08-25).** LLM mistyping digits when restating large numbers in `ai_reason`
   prose. Fixed via a prompt instruction telling the model to refer to "el valor anterior"/"el
   valor nuevo" instead of retyping digit sequences for numeric changes — safe because Module 7's
   report always renders `Antes`/`Ahora` from source data (`c['old']`/`c['new']`), never from LLM
   text, so this change can only fix the typo risk, never hide a real value.
6. **RESOLVED (2026-08-13), not an issue after all.** Original note worried `CODE_LIKE` regex
   wouldn't match hyphenated position ranges once Module 2 got built for a Type A manual. Turned out
   moot: Module 2 for `base_ii_clearing_interchange_formats_tc_01_to_tc_49` ended up using a
   font-size/text-pattern-driven design (section headings, grid header words, card labels), not the
   `CODE_LIKE` regex approach at all — see [[open-questions-technical-manuals]] for the real design.
7. **PARTIALLY RESOLVED (2026-08-25), plus the glossary for this manual RESOLVED same session.**
   Originally: `base_ii_clearing_edit_package_messages` (2nd manual), Module 5, LLM misclassifies
   ficha `V0407`'s `title` field (pair `20221015→20230415`, "IND EQUALS B OR P"→"IND EQUAL TO P").
   **Real root cause found, more precise than originally logged**: not the 5-word threshold — the
   change is a `difflib` "replace" opcode (3 words), and `_find_disappeared_content` only ever
   checked "delete" opcodes, never "replace". **A prompt-engineering fix was tried and explicitly
   REJECTED**: instructing the LLM to watch for value-list removals fixed V0407 in isolation but,
   validated against 4 known-correct `editorial_reword` cases (fichas V1232/V1235/V1236/V1245,
   plain field-name shortenings with no value change), caused the model to misclassify those TOO
   as `business_rule_change` — a real, measured regression, not hypothetical. **Fixed instead at
   the deterministic safety-net level**: `_find_disappeared_content` now also counts "replace"
   opcodes (same unchanged 5-word threshold — lowering it was tested and rejected too, several
   real 3-4-word replaces in the corpus are harmless renames/abbreviations, e.g. "Interchange
   Transaction File"→"ITF"). This resolved 2 more significant real misclassifications found while
   scoping the fix: ficha `V1209` (7 words, "Fee Collection | Funds Disbursement" silently
   vanishes from `transaction_types`) and glossary entry `optional issuer fee` (41-word full
   definition replaced by a cross-reference — same fact already seen in manual 1's glossary,
   confirming both manuals share the same source glossary). **V0407 itself remains unfixed** (its
   replace is 3 words, still under the 5-word threshold) — same low-priority/cosmetic assessment
   as before, the fact stays correctly captured in the ficha's `description` field. **Likely
   applies to manual 1 too** (near-identical `classify.py` code) — not checked/touched this
   session, flagged as a follow-up candidate.

   **V0407 residual RESOLVED (2026-09-05).** User asked to close this specific low-effort
   residual. Measured before implementing (same discipline as every other fix this session):
   scanned all 9 editions for every "replace"/"delete" opcode under the 5-word threshold (104
   total across the corpus) and checked which ones remove a coordinating conjunction ("or"/"and")
   together with a short value-like token (1-3 chars, e.g. "B") — a signal specific enough to
   distinguish "an enumerated value stopped being valid" from an innocuous short rename/
   abbreviation (the exact reason lowering the general threshold was rejected before). Result:
   exactly 3 matches in the WHOLE corpus, all in the same edition pair (`20221015_to_20230415`):
   ficha `V0407` (`title`, `"EQUALS B OR"` removed), ficha `V1073` (`title`, `"B OR"` removed,
   same pattern, a second real gap found by the same investigation, not previously logged under
   this item), and ficha `V1089` (`description`) — this 3rd one turned out to already be
   correctly classified `business_rule_change` via a different, longer opcode in the same field,
   confirming 0 false positives and 0 redundant fixes. **Fix, scoped to this manual only (not the
   shared `poc/_shared/ollama_client.py`)**: new `_removes_enumerated_value()` in `classify.py`,
   its result unioned with the existing `_find_disappeared_content()` output rather than
   replacing the general threshold — deliberately NOT added to the shared module, since
   validating it as safe for the other 6 LLM-using manuals wasn't asked for and wasn't measured.
   **Verified**: simulated against existing Module 5 output first (2 predicted flips, V0407 and
   V1073, matching the measurement exactly, 0 surprises); confirmed the known-safe rename
   ("Interchange Transaction File"→"ITF") still does NOT trigger the new signal. Ran real Ollama
   scoped to the 1 affected pair (`--only`): `safety_net_override` 0→2 exactly as predicted, both
   fichas now correctly show `business_rule_change` with the ⚠️ marker in the regenerated report.
   Item 7 has no residual left in this manual — manual 1's own `_find_disappeared_content` was
   NOT touched (this signal was never logged as needed there, and manual 1's `title` field
   changes don't follow the same "IND EQUALS X OR Y" phrasing pattern that motivated it).

   **Follow-up RESOLVED (2026-09-03)**: ported to `base_ii_clearing_data_codes` (manual 1) as a
   direct consequence of the point-4 duplication inventory (see [[dev-phase-considerations]]) —
   confirmed via grep that manual 1's `_find_disappeared_content` still only checked `"delete"`
   opcodes, exactly the gap this note had flagged and left unchecked. Simulated the fix against
   the existing Module 5 output first (no Ollama calls needed, since the fix only changes the
   deterministic override logic, not the LLM call) to predict impact before spending the ~356-item
   Ollama re-run: 10 real reclassifications predicted. Then ran the actual `classify.py` end-to-end
   through Ollama (356 items, all 8 pairs) and diffed old vs new by (table, code, column) key:
   exactly the 10 predicted flips, 0 unexpected changes, 0 `ai_reason` drift on the other 346 items
   (confirms `qwen3:4b` at temperature 0 reproduces identically). Module 7 re-run confirms the
   flips render correctly with the `⚠️ (la IA lo clasifico distinto...)` marker — e.g. `AVS
   Response Codes` code `N`: `'Address and ZIP code do not match.'` was being silently accepted as
   an `editorial_reword` down to `'AVS non-match.'` before this fix.
   **CORRECTION (2026-09-04): the "Follow-up RESOLVED" claim above was itself wrong about scope.**
   Re-verified against the actual current code (not trusted at face value) while doing the Tier 1
   shared-module extraction ([[dev-phase-considerations]] point 4): the fix was ported to manual 1
   as this note says, but was NEVER ported to the other 5 LLM-using manuals
   (`base_ii_clearing_interchange_formats_tc_01_to_tc_49`,
   `..._tc_50_to_tc_92`, `international_full_service_pos...`, `visanet...volume_1`,
   `visanet...volume_2`) despite this manual's flagged-as-checked status implying the audit was
   complete. See item 21 below for the real fix (consolidation, not a 5x manual port).
   **Same session, this manual's own glossary (~181-183 entries/edition, was one collapsed
   `paragraph` blob) also got fixed** — same underlying bug as [[pending-bug-fixes]] item 1
   (manual 1), but this manual's Module 2 has a fundamentally different architecture (linear
   single-active-block stream, no row/cell reconstruction), so the fix reused the FICHA block
   vocabulary (`card_header`+`field`, `label="Description"`) instead of porting item 1's
   `table_row` approach — zero changes needed to Modules 3/4/5/7. 2 real bugs found validating
   against all 9 editions: the 3 oldest editions use `SegoeUI-Bold` (not `OpenSans-Bold`) for the
   glossary term font — same Visa rebrand this module already handles for code-line detection —
   so without accepting both font names those 3 editions got ZERO glossary entries; and those same
   3 editions render bullet glyphs as their own standalone line (not fused with following text
   like the 6 newer editions), leaking a stray "l" word into definition prose until filtered.
8. **RESOLVED for grid rows (2026-08-26) AND field cards (2026-09-05).** `base_ii_clearing_interchange_
   formats_tc_01_to_tc_49` (3rd manual), "chain-shift": a field's length change shifts every
   subsequent field's position within the same TCR; exact-position matching saw this as a chain of
   false remove+add pairs instead of one clean resize. Originally investigated empirically across
   all 8 edition pairs (2173 section comparisons) on 2026-08-13, found only 1 real occurrence
   (0.05%) — explicitly deferred with the user given the rarity (the much more common
   position-change pattern is `Reserved` splitting into a new field + smaller `Reserved`, which
   never shifts anything since the new field is carved from the START of the existing range).
   **User later asked to implement it anyway, confirming it was low-risk.** Fix (`match.py`,
   `_match_shifted_rows`): after exact-position matching, leftover unmatched rows on both sides of
   a section are aligned by NAME (`Contents` cell) via `difflib.SequenceMatcher` over each side's
   name sequence (same reflow-reconciliation mechanism already used for manual 6/7's paragraph
   matching) — takes "equal" name subsequences even with genuine adds/removes interleaved, more
   robust than requiring the leftover lists to have equal total length. **Critical exclusion,
   confirmed BEFORE implementing**: any row named exactly "Reserved" is excluded from this
   fallback — the Reserved-split pattern ALSO shifts the remaining Reserved's own start position
   and reuses the literal name "Reserved" on both sides, so without this exclusion the fallback
   would have stolen Reserved rows away from `_detect_reserved_splits` (Module 4's more specific,
   pre-existing mechanism for the project's central Reserved-split use case) before it ever got to
   see them in `rows_removed`/`rows_added` — a silent regression of the project's most important
   detection path. Matched rows carry `matched_by: "position_shift"` + explicit `position_a`/
   `position_b`; Module 4's `_diff_row_cells` now also diffs the `Position` cell for these specific
   rows (normally skipped, since it's the match key and always identical for exact matches) so the
   byte-range change itself gets reported, not just the resize's side effects. **Verified against
   the full corpus**: the originally-known case now reports as 2 clean `row_content_changed`
   pairs (Position+Length for the resized field, Position+Format for the shifted one) instead of
   fragmented remove+add. **Scope turned out bigger than the original 1-instance measurement**: 7
   real chain-shift instances found across the corpus once the mechanism could actually surface
   them (vs. the 1 originally measured) — including a substantial new case, `TC 05 - TCR 2
   Colombia`, 3 tax-amount fields all resized 8-9→12 bytes, previously invisible as 6 disconnected
   remove+add pairs. Confirmed 0 "Reserved" leakage into the fallback and 0 double-counting
   between shift-matched rows and the removed/added lists, across all 8 pairs. Full pipeline
   (Modules 3→5,7) re-run end-to-end across all 8 pairs: Module 5 (567 items, Ollama) classified
   the shift-matched Position/Length changes as `business_rule_change` sensibly; Module 7's final
   report shows the known case as ONE clean grouped entry ("Mastercard - Service Location Postal
   Code" with both Position and Field Length changes together, AI reason correctly explaining the
   position/length change) instead of scattered remove+add noise. **Deliberately NOT
   extended to field cards (`match_cards`)**: investigated first — the same real chain-shift case
   exists in card form too, but the card's `name` field is NOT always byte-identical between
   editions for the same field (e.g. `"character Mastercard - Service Location Postal Code"` →
   `"character Mastercard Service Location Postal Code"`, a dash drops) — exact-name matching
   (safe for grid rows, where `Contents` IS byte-identical in the real case) would fail here, and
   fuzzy matching would need its own threshold calibration/validation before being trusted — not
   investigated, out of scope this session. Cards remain unmitigated for chain-shift.

   **Field-card residual RESOLVED (2026-09-05).** User asked to close this after V0407 (item 7).
   Measured before implementing (same discipline as always): scanned all 8 pairs replaying the
   real `extract_sections`/`match_sections` leftover-card computation — found 6 leftover card
   pairs ALREADY exactly name-identical (recoverable with zero new logic, just the same
   `SequenceMatcher`-over-exact-names mechanism already proven safe for rows) plus exactly 1 more
   (the known real case) that only differs by a dropped dash. **Not genuine fuzzy/ratio matching**
   (the approach flagged as needing its own risky calibration) — a targeted text NORMALIZATION
   instead: strip a dash used as a word-separator (`NAME_SEPARATOR_DASH`, a NEW regex — the
   existing `DASH_CHARS` in this file only covers non-ASCII dash variants for position-range
   normalization and does NOT match the plain ASCII hyphen that actually appears in card names,
   a real bug caught mid-implementation via a `KeyError` and then a silent non-match before
   settling on the right regex) before feeding names into the SAME exact-match `SequenceMatcher`
   algorithm already used for rows — same safety profile as the row mechanism, not a new
   fuzzy-matching risk surface. **Fix** (`match.py`): `_card_name()`, `_match_shifted_cards()`
   (mirrors `_match_shifted_rows`, same `Reserved`-exclusion for the same reason — confirmed the
   accepted `"character Reserved"`→`"Reserved"` residual still isn't stolen), wired into
   `match_cards()`. `detect.py`: `_diff_card_fields()` gets an `include_positions` flag (mirrors
   `_diff_row_cells`'s `start_index`), so shift-matched cards' `positions` field gets diffed too,
   not just the already-included `length`/`format`/etc. **Verified end-to-end**: Modules 3→5,7
   re-run for all 8 pairs — exactly 7 shift-matches recovered corpus-wide (matching the
   measurement precisely), added/removed counts dropped by exactly that number in exactly the 3
   affected pairs, 0 change in the other 5 (confirmed programmatically, not eyeballed). The known
   real case now renders as ONE grouped report entry showing both "Grilla" and "Ficha" versions
   of the Position/Length change together (previously scattered card_added/card_removed noise);
   real Ollama classified the position/length/format changes as `business_rule_change` and the
   wording-only description change as `editorial_reword`, both sensible. Item 8 has no residual
   left in either grid or card form.
9. **`base_ii_clearing_interchange_formats_tc_01_to_tc_49` (3rd manual), edition `20260418` is
   missing ~57 `"Note:"` labels from its extracted text layer.** Low priority — doesn't affect the
   project's core Position/Length/Format/Contents data, only supplementary `Note:` prose. The bold
   span rendering "Note:" is genuinely absent from PyMuPDF's text extraction for that one edition
   (confirmed: 274/274/274/274/274/272/273/273 `"Note:"` occurrences across the first 8 editions,
   only 216 in `20260418`) — a source-PDF limitation, not a parser bug; would need OCR to recover,
   out of scope. Module 5's safety net already compensates in practice (flags the disappeared
   content for human review instead of losing it silently). **Logged 2026-09-05 as a future-
   improvement candidate, deliberately NOT picked up this round**: user explicitly deferred this
   one (unlike items 7/8 below, which were picked up the same session) specifically because it
   needs new infrastructure (an OCR step), not a targeted code fix — different category of effort
   than every other item on this list. Revisit if/when OCR becomes worth adding to the pipeline.

10. **RESOLVED (2026-08-25, residual closed 2026-09-05).** Originally: `base_ii_clearing_interchange_formats_
    tc_50_to_tc_92` (4th manual), 2 distinct record layouts ("TC 57 - TCR 5 - Limited Use Data")
    stacked under one identical section-heading text, with no way to know which is which or give
    them readable labels — data loss already mitigated on 2026-08-19 (order-of-appearance
    matching). **Fixed**: added `_section_signature()` in Module 3 — the name of the first grid
    field that isn't part of the 3-field preamble common to every section in this manual, or
    "Reserved" (confirmed the most generic possible field, almost never the real differentiator —
    e.g. variant 2 here starts with `Reserved`@5-15, but the real differentiator is the next field,
    `Banknet Settlement Number`@16-24). Confirmed stable across all 9 editions: variant 1 =
    `Local Tax`@5-13, variant 2 = `Banknet Settlement Number`@16-24, always in that order. When a
    title collides, both sides are now re-sorted by this content signature before pairing by
    position — replaces fragile appearance-order matching with content-anchored matching (no
    behavior change on current data, pure future-proofing). Module 4 propagates the signature to
    every change from that section; Module 7 uses `(title, signature)` as the grouping key and adds
    a `"— variante con campo «X»"` heading suffix only when a title actually has 2+ distinct
    signatures in that specific report (never clutters the non-colliding common case). **1 self-
    found bug caught by a synthetic test** (no real pair has a content change in this section to
    exercise the path with real data): the first version of the heading-disambiguation helper
    compared each group's title against itself instead of counting distinct signatures, so the
    suffix never fired — caught before considering the fix done.

    **Residual RESOLVED (2026-09-05), user asked to close the lowest-effort residual on the
    list.** The label was a real field name (e.g. `"Banknet Settlement Number"`) but gave no way
    to LOCATE the field without cross-referencing the full table — no attempt to fabricate a
    "business reason" the 2 layouts exist (that reason genuinely isn't in the source data), just
    make the existing disambiguator immediately actionable. **Fix, fully additive, no matching/
    detection logic touched**: `_section_signature()` in `match.py` now returns `(name, position)`
    instead of just `name`; the position flows through as a new `signature_position` field
    alongside the existing `signature` field at every propagation point (`extract_sections`,
    `sections_matched`/`sections_added`/`sections_removed` in Module 3, the `section_added`/
    `section_removed`/matched-section changes in Module 4 — same `setdefault` pattern already
    used for `signature`). `report.py`'s 2 suffix-rendering call sites now render
    `"— variante con campo «Banknet Settlement Number @ 16-24»"` instead of just the bare name.
    **Verified end-to-end**: Modules 3→4 re-run for all 8 pairs, diffed against the pre-change
    baseline after stripping the new field — byte-identical in every pair, confirming zero
    behavior change to matching/detection, purely additive. The real collision case
    ("TC 57 - TCR 5 - Limited Use Data") still doesn't appear in any of the 8 real pair reports
    (same as before — no real content change happens to land in that specific section in the
    current corpus), so the new format was verified with a synthetic `render_report()` call using
    the known real case's data, same technique already used to catch the original heading-suffix
    bug. Module 5 re-run with real Ollama for all 8 pairs to refresh the on-disk `signature_position`
    field (the field flows through classify.py's `enriched = dict(change)` untouched, confirmed by
    code read, no logic change there) — 7 of 8 pairs came back byte-identical (net of the new
    field); 1 pair (`20220423_to_20221015`) surfaced an unrelated, genuine, welcome correction:
    a `"note"` field's classification flipped `editorial_reword`→`business_rule_change` because
    `find_disappeared_content` (the shared, already-fixed "replace opcode" logic from item 21)
    had never actually been re-verified for this specific pair since the 2026-09-04 consolidation
    — that fix's own verification only re-ran ONE representative pair per manual, and this wasn't
    the one chosen for this manual. Confirmed via direct, repeated calls to the shared function
    with the exact real (byte-identical, unchanged by this session) old/new text that it
    deterministically returns the same non-empty result — a pre-existing stale on-disk artifact,
    not a regression introduced by this change. Item 10 has no residual left.

11. **RESOLVED (2026-08-25).** Originally: `base_ii_clearing_interchange_formats_tc_50_to_tc_92`
    (4th manual), ficha-table title text bleeding into the 1st field's `description` (3 of 9
    editions, ficha `Transaction Code`@1-2, "...Leg-Specific Edit Criteria This field must contain
    a 50."). **Real root cause, more precise than originally logged**: the title paragraph (10.5pt
    prose) occasionally gets extracted split into 2 PyMuPDF "line" fragments sharing the exact same
    Y-band (confirmed same `source_block`, a genuine PyMuPDF layout quirk with no recognizable
    splitting signal — no whitespace-only span, no font-size jump between the 2 fragments). The 2nd
    fragment then trips `same_row_as_next_name` — the mechanism this module uses, on ~1700 fichas
    across the document (18167 confirmed legitimate triggers in a full corpus scan), to capture a
    real field's `Description:` first line when it starts on the same row as the field's own name.
    Since nothing distinguished "this active paragraph is a title" from "this is a field name," the
    title fragment got buffered as if it were the next field's inline description. **Fixed**: field
    names are always 9.0pt in this manual, titles 10.5pt — confirmed via the same full-corpus scan
    (18167 legitimate hits at 9.0pt, exactly 7 at 10.5pt, all instances of this bug class, including
    1 additional unlogged instance). `same_row_as_next_name` now excludes 10.5pt paragraphs.
    Verified: 0 regressions across all 9 editions (0 fully-empty ficha content), `Transaction Code`
    clean in the 3 previously-affected editions.

12. **RESOLVED (2026-08-25).** Originally: `base_ii_clearing_interchange_formats_tc_50_to_tc_92`
    (4th manual), a ficha whose `Values:` enumeration spans multiple pages (`"BASE II Customized
    Delivery File Type"`@109-113, section `"TC 90 - TCR 0 - Incoming ITF"`, edition `20220423`,
    3 page fragments) fragmenting into several `field_card` blocks instead of merging into one —
    don't confuse with the sibling `"Outgoing ITF"` occurrence of the same field name, which is a
    genuine editorial change (Visa removed an enumerated list for a cross-reference), correctly
    caught by the Module 5 safety net, untouched by this fix. **Fixed**: in Module 2, when a new
    ficha's name carries the literal `"(continued)"` suffix AND its position matches the
    immediately-preceding emitted ficha exactly, that ficha is reopened (`blocks.pop()`) instead of
    creating a new one. **1 real bug found validating (not in the original design)**: this manual's
    2-column ficha layout means the continuation's own first right-column line ("Note: Values
    continued:") sorts BEFORE its own "Positions:" line by Y-coordinate (same reordering mechanism
    already documented for item 11) — it lands buffered in `pending_right`, and the first fix
    version discarded that buffer unconditionally when reopening the card, silently losing all of
    the continuation's content. Fixed by merging `pending_right` into the reopened card, mirroring
    what the "new ficha" path already does. Verified: 0 unmerged `"(continued)"` cards left across
    all 9 editions; the merged 20220423 ficha now carries its full ~70-value list (`note` field:
    1685 chars, was 224).

13. **RESOLVED for the 6th manual (2026-08-25), generalized from 2:1-only to true N:M.** 6th
    manual (`international_full_service_pos_online_messages_processing_specifications`),
    Module 3: paragraph-reflow reconciliation was previously limited to the simple
    2-paragraphs-on-one-side↔1-on-the-other case (`_reflow_matches`, cut `safety_net_override`
    29→14 on 2026-08-19), leaving 2↔2 and other N:M re-chunking variants unresolved. **Real
    2:2 case found and used to validate the fix**: section "Card Verification Value (CVV)
    Service" — in the old edition a sentence lives glued to the tail of a long paragraph AND a
    completely different sentence is its own separate paragraph; in the new edition those 2
    sentences get regrouped the opposite way (redistributed between 2 paragraphs that exist on
    both sides, not a simple merge/split) — no 1↔2 sub-pair alone could ever find it, but
    `A[0]+A[1]` concatenated is byte-identical to `B[0]+B[1]` concatenated. **Fixed**: rewrote
    `match_paragraphs` to run ONE `difflib.SequenceMatcher` over each side's list of
    paragraph-normalized-texts (paragraph as the atomic unit, not word/char) instead of a
    dict-based exact match + separate adjacent-pair search. Its opcodes give everything needed
    for free: `"equal"` = identical paragraphs (more robust to interleaved duplicates than the
    old dict+zip); `"replace"` (N paragraphs one side, M the other) = reflow candidate — if the
    2 blocks' full concatenated text matches exactly, it's pure N:M reflow (subsumes the
    original 2:1 case with no special-casing) and goes to `paragraphs_reflowed`; otherwise both
    sides fall to the same fuzzy-matching pool as before (no behavior change for genuine
    content changes). `"delete"`/`"insert"` also feed the same fuzzy pool. Deliberately not
    handling MIXED replace blocks (part reflow + part real change in the same stretch) — no
    real instance found validating against the full corpus. **Verified**: Modules 3→5,7 re-run
    across all 6 editions/7 pairs, 0 errors, 18 genuine N:M cases found beyond simple 2:1 (up
    to 5↔4 in one section), `safety_net_override` dropped further (14→10), the CVV case
    confirmed reconciled (was a false `business_rule_change`, now correctly
    `paragraph_reflowed`), and the already-validated "Exception File"→"ASAF" rename finding
    still renders identically (no regression). **7th manual's own variant of this same root
    cause (a `name`+`description` merge in one field of a `field_description_pair`) was NOT
    touched this session** — it needs its own investigation before deciding whether this same
    mechanism applies as-is or needs adapting.

    **Follow-up RESOLVED (2026-09-04)**: closed the remaining residual this item's own writeup
    left open (`[[dev-phase-considerations]]` point 8's "hyphen-wrap noise" + "1 unconfirmed
    ambiguous case"). Checked all 11 `safety_net_override`s still in the corpus against the
    real data before touching code: 9 were the SAME pattern — content flagged "disappeared"
    from its matched paragraph pair was actually intact in some OTHER non-adjacent paragraph of
    the same new section (the block-based reflow detection only catches CONTIGUOUS
    redistribution, not this). Fixed by having `detect.py` attach every new-section paragraph
    text to each `paragraph_content_changed` change, and `classify.py` excluding any
    "disappeared" chunk found there from the override decision (kept as
    `content_relocated_within_section` for transparency, not silently dropped). Verified with
    real Ollama: `safety_net_override` corpus-wide 11→3. The 2 remaining are confirmed genuine
    (checked against the WHOLE new edition, not just the section — truly absent). **Real new
    finding, separate bug, not fixed**: 1 of the 3 remaining overrides turned out to be neither
    reflow nor real removal — the new edition's paragraph is truncated MID-WORD
    (`"...in Fie"`), a PDF page-boundary word-splitting artifact in Module 1/2, unrelated to
    paragraph-level matching. Logged for its own investigation if pursued later.
    See [[dev-phase-considerations]] items 7-8 for
    the architectural framing.
14. **RESOLVED (2026-08-26, in 2 passes same day).** 7th manual
    (`visanet_settlement_service_vss_user_guide_volume_1_specifications`), Module 1/2: rotated
    Field Name/Description pair extraction had an imperfect residual — ~35-45% of reconstructed
    pairs with an empty description. **Sub-case fixed**: a real fraction of these were the SAME
    PyMuPDF line-fusion bug as item 2 (Cook Islands, manual 1) — 2 logically distinct cells
    (field name / description) merged into one `line` by PyMuPDF, separated only by a
    whitespace-only span, here in ROTATED text. Confirmed via a full 6-edition corpus scan
    before coding: 9-10 real instances/edition, always exactly 3 spans (name/space/
    description), always uniform 9.0pt. ~47 more instances/edition of the same pattern exist
    but all fall on pages Module 2 already discards entirely (no `"Field Name"` literal) —
    inert either way. The same pattern also appears in horizontal text (220-224 hits/edition)
    but confirmed ALL are TOC dot-leader lines (already filtered) or a "Report ID/Report Title"
    table whose fused content was an already-accepted residual from an earlier session —
    deliberately NOT extended to horizontal lines, to avoid reopening that closed scope. Fix:
    ported `_split_line_segments`/`_segment_bbox` from manual 1's `ingest.py`, scoped to
    rotated lines only. Verified end-to-end: empty descriptions 109→101 (old editions) / 82→73
    (new editions), 236 pairs unchanged, Module 3 236/236 matched all 5 pairs (0 regression),
    Module 4's 39→41 `pair_content_changed` increase in the big pair investigated and confirmed
    pre-existing/unrelated (not touched by the split fix), Module 5 `safety_net_override`=2
    (identical to pre-fix baseline), Module 7 same business-change counts as the validated
    baseline. **2nd sub-case, also FIXED same day (user asked directly whether it was safe
    before agreeing to proceed)**: a distinct, deeper geometry issue — a long description that
    wraps into a 2nd `x0` sub-band within the same rotated cell was being treated by
    `_extract_rotated_pairs` as 2 separate "row" bands instead of one continuous description,
    orphaning or misattributing the wrapped tail (e.g. "Example 5" table, pages 129/131 in
    `20231013`: `"CLEARING AMOUNT"`'s description truncated because its wrapped tail
    `"SMS600C report."` landed in a different, unrelated bracket-named pair like
    `"[CLEARING AMOUNT]"` instead). **Investigated with the same corpus-wide-evidence rigor as
    item 8's chain-shift before implementing**: scanned every consecutive desc-line gap (by
    `x0`) across all 6 editions/all real Field Name tables — genuine wrap-continuation gaps are
    ALWAYS exactly 12.0pt (87 instances, zero variance, each one completing a truncated
    sentence when read), while the minimum real gap between 2 different table rows' own
    descriptions is 17.0pt — a clean, non-overlapping boundary, even cleaner than item 8's.
    Fix: `_merge_wrapped_descriptions` (new function, threshold `DESC_WRAP_GAP_MAX=15.0`,
    midpoint) merges consecutive desc-lines below that gap into one description BEFORE the
    existing name↔desc nearest-match runs — keeps the first fragment's `x0` (already the one
    that correctly matches its real name today), so the existing matching mechanism needed no
    changes, purely additive. Verified: `CLEARING AMOUNT` now gets its full description; the
    bracket-named entries that were WRONGLY stealing the orphaned wrap tail (`"[CLEARING
    AMOUNT]"`, `"[CARDHOLDER BILLING AMT CUR]"`, `"[TOTAL ISSUER INTERCHANGE]"`) now correctly
    show an empty description instead — same legitimate "no description of its own" pattern
    already established for `"Row"`/`"Column"`. 236 pairs unchanged, Module 3 236/236 matched
    with 0 regression, Module 4's spurious `"SMS600C report."`-type truncation noise is
    completely gone from the diff (the previously-flagged 39→41 `pair_content_changed`
    increase dropped further to 21, all of them the already-accepted empty-old-description
    category, none of the truncation-noise kind). Module 5/7 re-run to confirm no downstream
    regression.

    **Remaining residual, legitimate, not a bug**: `"Row"`/`"Column"` structural sub-labels
    with no description of their own (~23 occurrences each) — same accepted pattern as always,
    nothing left to fix here.

15. **RESOLVED (2026-09-05) — real scope turned out MUCH smaller than originally estimated,
    both root-cause variants fixed.** 8th manual
    (`visanet_settlement_service_vss_user_guide_volume_2_reports`), Module 2: tight row-packing
    in some Appendix D grids misattributes a wrapped non-anchor cell's continuation line to a
    phantom following row. Found 2026-08-19, confirmed on `Financial Transaction Record 4 –
    V22225` (page 375). Originally estimated ~150-170 of ~1550 Appendix D `grid_row`s affected
    in the newest edition — **that estimate was stale**: it was very likely measured before item
    18's fix (2026-08-26, `ROTATED_ANCHOR_WRAP_GAP_MAX` recalibrated 4.0→6.8 for an unrelated
    Appendix A bug) incidentally shrank this item's impact too, without anyone re-measuring
    afterward. **Re-measured 2026-09-05 with a real corpus-wide scan (not another guess)**:
    the ORIGINAL cited example (V22225, "Message Type"/"Trace Number") doesn't reproduce in the
    latest edition — rendering the actual PDF page confirmed it's a LEGITIMATE compound
    bulleted row ("Original Data Elements" with 6 sub-fields) that IS correctly reconstructed
    there; the bug turned out to still be real, just confined (like everything else in this
    item) to the 3 oldest editions, where the same table's tighter geometry crosses the
    ambiguity threshold. A naive "Position+Attribute both empty" signal (tried first) is
    UNSAFE — 124 of 3939 Position+Attribute-schema rows in Appendix D match it, and ~119 of
    those are legitimate footnote rows (e.g. `"DX = Hexadecimal Display"`) that would have been
    corrupted by an auto-merge.

    **Variant 1, "– " (literal dash) sub-bullets — fixed first**: `_merge_dash_orphan_rows` in
    `normalize.py` — a row whose anchor-column value starts with "–"/"-" AND every other column
    is empty gets merged into the immediately preceding row. Signal validated safe against the
    full corpus (none of the 119 legitimate footnote rows start with a dash).

    **Variant 2, "•" (round bullet) sub-bullets — investigated further and ALSO fixed, same
    session**. Initially assessed as needing a Module 1 change (wrongly) — re-investigated by
    rendering the raw PyMuPDF span data directly: the bullet is NOT lost in Module 1 at all,
    it's captured as a real line (`text="l"`, `font="Wingdings-Regular"`, ~6.4pt — the classic
    Word-generated-PDF trick of mapping a bullet glyph onto a letter in a symbol font). Module 1
    passes it through untouched; Module 2 was the one silently dropping it as an unclassified
    "leftover" `paragraph` block (font size matches none of title/header/data), disconnected
    from the row it visually belongs to — so the real fix is entirely in `normalize.py`, same
    file as variant 1, no Module 1 change needed after all. **Geometry was counter-intuitive
    and needed real measurement, not assumption**: the bullet does NOT precede its associated
    text in the primary sort axis, it FOLLOWS it (~4-6.4pt after, confirmed on all 6 real
    instances) — the opposite of variant 1's literal "– " marker, which precedes as expected.
    A naive "anchor line followed by any Wingdings bullet within 10pt" signal is UNSAFE: found
    14 cases in Appendix A (same `_build_table_rows` code path) where a genuine large new-table
    gap (174.5-202.6pt) coincidentally has a Wingdings bullet nearby for an unrelated legitimate
    list item — blindly suppressing those would have caused a real regression. Fixed by ALSO
    requiring the gap to be small (`BULLET_SUPPRESS_GAP_MAX=10.0`) — validated against the full
    corpus: the real bug's gap is EXACTLY 7.0pt in all 18 instances (barely over the 6.8
    threshold), the Appendix A false-positive gaps are 174.5pt+, a huge clean separation with
    no values in between. Confirmed via `fitz`-rendered PDF pages that "– Original Trace"'s
    table (V22240) and V22420's table both had additional "•"-bulleted sub-items ("Reimbursement
    Attribute", "Local Date", "Contact Name") that variant 1 alone couldn't reach.

    **Combined result, verified end-to-end**: 0 dash-orphans and 0 bullet-caused misattributions
    remain in any of the 7 editions; 0 side effects in Appendix B/C/E (unaffected code path) and
    confirmed 0 change to Appendix A's own row/block counts across all 7 editions (the
    gap-size guard correctly excludes its legitimate large-gap bullet coincidences). Several
    tables now reconstruct as a single clean row where they used to fragment into 2-5 pieces
    (best case: V22420's whole "Supporting Information: Contact Name Contact Phone Copy
    Request: – Date Document Sent – Documentation Delivery – Method – Original Data" record
    fully unified). One residual remains in V22240 for the one pair crossing the bug boundary
    (`20230415→20231013`): `"Supporting Information: Reimbursement Attribute Original Data:"`
    and `"– Original Trace – Original Transmission Date – Original Transmission Time – Free
    Text"` are now each internally consistent (down from 5 total fragments to 2), but the 2
    pieces don't merge into each other because the transition between them isn't marked by
    either signal (no bullet, no leading dash on that specific boundary) — real, small,
    accepted residual, not chased further. Re-ran the affected pairs' Module 5 with real Ollama
    to keep on-disk data consistent with the fixes. Full detail in
    [[manual8-vss-vol2-progress]] (pre-2026-09-05 narrative; this entry is the authoritative
    current status).

17. **RESOLVED (2026-08-26).** 8th manual (`visanet_settlement_service_vss_user_guide_volume_2_
    reports`), Appendix B: Description's first sentence bled into the preceding `Field Name`
    column in specific rows/editions (e.g. `Net Amount Sign` in `20231013`). Same root cause as
    manual 1's Cook Islands (item 2) and manual 7's item 13/14: PyMuPDF fuses 2 logically
    distinct cells into one `line`, separated by a whitespace-only span. **New complication not
    present in the other 2 manuals**: the same symptom also innocuously separates every WORD of
    a legitimate single-cell title/legend elsewhere in this manual (a rotated matrix row-label,
    a legend, a narrow-no-break-space-joined sentence pair) — blind splitting would have
    corrupted those. **Fixed more surgically**: Module 1 exposes candidate segments (split only
    on whitespace-only spans, deciding nothing) via a new `segments` field; Module 2's
    `_resegment_by_column` (inside `_build_table_rows`, which already has the active table's
    column geometry) only splits when segments land in genuinely different column bands
    (`_nearest_band`) — same-column segments stay fused. Verified: 0 suspicious `Field Name`
    values left across all 7 editions, 0 regression on all 3 confirmed risk cases, `grid_row`
    totals unchanged (2601-2685, same baseline). Full detail in [[manual8-vss-vol2-progress]]
    (bug 10).
18. **RESOLVED (2026-08-26), root cause turned out DIFFERENT and much bigger in scope than
    logged.** 8th manual, Appendix A: `Available VSS Reports` catalog rows fragmenting (e.g.
    `VSS-116`/`(Fee by Jurisdiction)` in `20240413`). Originally assumed a genuine page-boundary
    issue (Module 2 never carries rows across pages) — investigating the concrete case found
    this was WRONG, both fragments are on the SAME page. **Real cause**:
    `ROTATED_ANCHOR_WRAP_GAP_MAX=4.0` (calibrated 2026-08-19 against only 2 tables) missed a
    2nd legitimate wrap-gap mode — when the anchor column's value wraps across 3+ lines, the
    gap between the 2nd and 3rd fragment can be larger (4.1-6.6pt) than the tight ~0pt gap
    between the 1st and 2nd, spuriously triggering a new row. Recalibrated with full-corpus
    evidence (7200 real gaps, 7 editions, both rotated appendices): clean non-overlapping
    boundary, max real wrap gap 6.6pt, min real new-row gap 7.0pt — set to 6.8. **Scope much
    bigger than logged**: the 3 oldest editions had the SAME bug affecting 35 of 79 rows (44%)
    of this catalog, with an unrelated-looking symptom (missing `"VSS-100-W —"` ID prefix) that
    turned out to be the identical root cause. Post-fix: 0 affected rows across all 7 editions
    (was 35 in 3 editions). Verified: `grid_row` totals dropped 2601-2685→2509-2582 manual-wide
    (fragments merging back, no data loss), the ORIGINAL case that motivated the 4.0 threshold
    (Appendix D p.366, V22200) still correctly stays split (10 rows). Full detail in
    [[manual8-vss-vol2-progress]] (bug 11).
19. **RESOLVED (2026-08-26).** 8th manual, Appendix B: `"TC 46, TCR N ..."` title occasionally
    extracted with "TCR" split into 2 words (`"TC R"`) on 1 of ~6 page re-declarations of the
    same title — a different malformation from the NBSP bug (bug 9, already fixed). Full-corpus
    scan of the literal substring `"TC R"` confirmed it appears ONLY in 3 consecutive editions
    (`20230415`-`20240413`, self-corrects from `20250412`), ALWAYS the same 9 instances, ZERO
    legitimate occurrences elsewhere — a fully safe signal. Fixed by adding `TCR_SPLIT =
    re.compile(r"\bTC R\b")` to `_clean_text`, alongside the existing NBSP normalization.
    Verified: Appendix B for pair `20240413→20250412` went from `30->22 tablas (+0/-8)` to
    `22->22 tablas (+0/-0)` — the spurious `table_removed`/`table_renamed` are gone. Full detail
    in [[manual8-vss-vol2-progress]] (bug 12).
20. **RESOLVED (2026-08-20).** 8th manual, Appendix E, Module 4: NBSP (U+00A0) vs regular
    space in column header text broke column-name-keyed diffing, producing 15 of 31
    `safety_net_override` false positives (plus an unknown number of silently-miscategorized
    `business_rule_change` false positives that never hit the override list at all — the
    "column appeared" counterpart of the same bug). Fixed at the root in
    `Modulo2/normalize.py` (`_clean_text`, replaces NBSP before it can become a column/table
    name). Verified end-to-end: Modules 2→5 re-run for all 7 editions, `safety_net_override`
    31→18, `row_content_changed` 506→445, all genuine cases preserved. Full detail in
    [[manual8-vss-vol2-progress]] (bug 9).

16. **RESOLVED (2026-08-19), same day it was logged.** Originally: 8th manual, Module 3, a
    table's tail rows spilling onto a continuation page without a header redeclaration got
    glued into the next table's title (2 residual cross-record fuzzy-match mismatches out of
    51). Turned out to share its root cause with a separate bug found while validating Module
    4 (title lines routed with the wrong direction — see [[manual8-vss-vol2-progress]] bug
    write-up "1 more real bug found while validating Module 4"): fixing the title-routing
    direction resolved this residual as a side effect. Re-checked: 0 cross-record mismatches
    left out of 52 total fuzzy matches. No longer an open item.

21. **RESOLVED (2026-09-04).** The item-7 "replace opcode" fix's REAL scope: only 2 of 7
    LLM-using manuals (`base_ii_clearing_data_codes`, `base_ii_clearing_edit_package_messages`)
    actually had it, despite item 7's own "Follow-up RESOLVED" note claiming a full port. Found
    doing the Tier 1 shared-module extraction ([[dev-phase-considerations]] point 4) — a fresh
    grep against the live code, not trusting the prior note. **Fixed properly this time**: instead
    of porting the fix by hand a 3rd/4th/5th/6th/7th time (the exact failure mode that let it go
    unnoticed twice already), consolidated `_find_disappeared_content` into
    `poc/_shared/ollama_client.py::find_disappeared_content` — one copy, used by all 7 manuals via
    a thin per-manual wrapper. Measured impact against the existing corpus BEFORE touching code
    (no Ollama needed, pure text diff): 14 concrete real cases across the 5 previously-buggy
    manuals that flip from `editorial_reword` to a forced `business_rule_change` override (e.g.
    tc_01_to_tc_49: "This field contains the Senders Foreign Exchange fee..." replaced by an
    unrelated "This field contains the money transfer foreign exchange fee." was being silently
    accepted as a reword). Verified with real Ollama on a representative pair per manual: all 7
    classify cleanly, overrides render with the `⚠️` marker in the generated report, non-buggy
    manuals' behavior unchanged. See [[router-landing-progress]] for the CONTRACT.md writeup.
22. **RESOLVED (2026-09-05).** `visanet_settlement_service_vss_user_guide_volume_1_
    specifications` and `..._volume_2_reports`, Module 3 (`match.py`): real list-ordering
    nondeterminism, unrelated to any change made 2026-09-04 — found as a side effect while
    diffing Module 4 output for the Tier 1 extraction. Running the exact same unchanged
    `match.py` twice on the same input produced different ORDER of matched-paragraph entries
    each time; a canonical (recursively sorted) comparison confirmed the actual matched content
    was byte-identical, pointing at pure ordering noise from a `set()`/dict-iteration-order
    dependency exposed by Python's per-process hash randomization (`PYTHONHASHSEED`). **Root
    cause confirmed and fixed**: 4 functions across the 2 manuals' `match.py` iterate
    `set(dict_a) | set(dict_b)` directly to build an output list with no final sort —
    `volume_1`'s `match_paragraphs` (1 spot), `volume_2`'s `match_tables`/`match_headings`/
    `match_paragraphs` (3 spots). Sibling functions in the same files hit the identical pattern
    but already end with `sorted(matched, key=sort_key)`, explaining why only some functions per
    file were affected. Fix: sort the iteration source (`sorted(set(...) | set(...))`), not just
    the final list. **Verified**: both manuals now give byte-identical output across repeated
    runs. Order-normalized content diff (before vs. after the fix): `volume_2` 0 differences
    across 6 pairs; `volume_1` had 1 real difference in 1 section of 1 pair — a genuine finding,
    not a fix regression, logged in detail in [[dev-phase-considerations]] point 9: the fuzzy
    stage is greedy (order-sensitive in rare near-tied-candidate cases), so the bug could
    silently affect WHICH pairing gets picked, not just list order. Both candidate pairings
    clear the safety threshold; user chose to ship the determinism fix and defer the
    greedy-optimality gap. Re-ran the 1 affected pair's Module 5 with real Ollama to keep
    on-disk data consistent with the corrected Module 3/4 output. See [[dev-phase-considerations]]
    point 9 for the full writeup.
23. **DEFERRED IDEA (logged 2026-09-09), not a bug — a future-improvement candidate.** Token-usage
    instrumentation for the AI stage (`poc/_shared/ollama_client.py`). While walking the user
    through the README's usage scenarios and estimating how long a fresh landing would take, the
    question came up of whether token consumption could be tracked (relevant both for a future
    project-presentation data point and for costing out a possible move to a paid cloud LLM,
    raised in the same session — see the GPU/cloud discussion below). Confirmed Ollama's
    `/api/generate` response already includes `prompt_eval_count` (input tokens) and `eval_count`
    (output tokens) per call — `ollama_client.py:56-58` currently reads only `body["response"]`
    and discards the rest. Measured live against one real pending item (manual
    `base_ii_clearing_interchange_formats_tc_01_to_tc_49`, pair `20251018_to_20260418`,
    `row_content_changed`/`card_content_changed` type): **306 prompt tokens + 49 response tokens
    = 355 tokens for that one item**. Projected for a typical ~193-item pair (this manual's
    actual pending pair): **roughly 65,000-70,000 tokens total** (will vary with how much
    old/new text each item carries). User explicitly asked to log the idea and the measured
    baseline WITHOUT implementing yet. If picked up later: add the 2 counters to
    `ollama_classify()`'s return dict in `ollama_client.py` (contained change, same file already
    identified for the `estado_publicacion` split precedent below), have each `classify.py`
    accumulate and report a per-pair total (console line and/or a `token_usage` field in the
    05-stage JSON).

24. **DONE, one-off test, not a migration (2026-09-10).** Real Qwen-vs-Gemini comparison, following
    directly from item 23's "possible move to a paid cloud LLM" thread. User wanted to test Gemini
    (via OpenRouter) on the etapa 05 classifier and be able to trivially revert to Qwen. Implemented
    a `LLM_BACKEND` env var toggle in `poc/_shared/ollama_client.py` (default `"ollama"` — unset
    behaves exactly as before; `LLM_BACKEND=openrouter` + `OPENROUTER_API_KEY` dispatches
    `ensure_ollama_running`/`ollama_classify` to `google/gemini-2.5-flash-lite` via OpenRouter
    instead). Zero changes needed in any of the 7 manuals' `classify.py` — they only import the 2
    functions by name. **Bug hit and fixed during the test**: first real run failed at item 16/193
    with `JSONDecodeError: Unterminated string` — OpenRouter/Gemini truncated a response mid-JSON on
    a long-text item. Reproducing the same prompt manually succeeded cleanly, so likely transient
    network-layer truncation rather than a content-length-driven ceiling. Fixed by adding an
    explicit `max_tokens` (600) and 3-attempt retry-with-backoff to `_openrouter_classify` only
    (Ollama's local path doesn't need this — a cloud API can fail transiently, a local call
    essentially doesn't). Second run completed clean, 0 errors.
    **Real comparison run**: full pair `20251018_to_20260418` of
    `base_ii_clearing_interchange_formats_tc_01_to_tc_49` (193 content-change items), same prompt,
    both backends. **84.5% agreement (163/193)**. Confusion breakdown: 87 both-editorial, 72
    both-business, 4 both-noise agree; disagreements: 18 Qwen=business_rule_change→Gemini=
    editorial_reword (the risk-relevant direction — Gemini under-flagging real business changes),
    7 the reverse, 3 editorial→noise, 1 noise→editorial, 1 business→noise. `safety_net_override`
    count: Qwen 38, Gemini 43 (Gemini's own first-pass judgment needed the deterministic safety net
    more often). Concrete example found and verified from the raw JSON: ficha `TC 05 - TCR 0`
    position `133-136` (Merchant Category Code), `note` field — old text is a real business note
    that got deleted with nothing replacing it; Gemini's own first-pass category was
    `extraction_noise` (reasoned the empty new text meant the old text "must have been a PDF
    extraction artifact" — wrong), corrected to `business_rule_change` by
    `find_disappeared_content`'s safety net (`ai_original_category` field confirms this). Qwen got
    the same item right on its own, no override needed (`safety_net_override: false`). **Project
    state restored to Qwen and verified byte-identical** (`md5sum` match on both the 05 JSON and the
    07 `.md` report for the test pair) before ending the session — the toggle exists in code but is
    inert unless someone explicitly sets `LLM_BACKEND=openrouter`. **Security note**: the user pasted
    their real OpenRouter API key directly into chat instead of running the command themselves —
    flagged immediately, user was told to revoke/rotate it at openrouter.ai/keys (assistant has no
    way to revoke it directly — that needs dashboard access or a separate provisioning key). **Not a
    production decision** — this was purely a comparison test; confidentiality (proprietary
    Visa/Mastercard content going to a cloud API) and per-token cost (real, unlike free local Ollama)
    remain the open considerations from item 23 if a real migration is considered later.

**Why:** these are the residue left after fixing every bug that touched real code-table data during
the 2026-08-12 Module 1-3 validation pass for `base_ii_clearing_data_codes` — see
[[feedback-bug-prioritization]] for the triage rule that decided what got fixed immediately vs.
deferred here. Item 10 is a different kind of deferral — POC-phase logging per
[[feedback-poc-vs-development]], not a data-relevance triage call. Items 13-14 are the same
"accepted, real, deliberately deferred residual" category, confirmed and re-confirmed with real
data before being left as-is rather than assumed acceptable.

**Status as of 2026-09-05**: for `base_ii_clearing_data_codes` specifically, EVERY item the user
had flagged is now fully resolved — items 1/2/3/3b/4/5 all resolved (item 3b closed in 2 passes
2026-09-05, see its own entry for the lookahead-signal design and the bonus "Type D" finding).
Nothing in this manual is open anymore; only items 7-20 (other manuals) remain as genuinely open,
low-priority items.

**How to apply:** before starting new work on `base_ii_clearing_data_codes` (or copying its Module
1/2/3 patterns to another manual), check this list first — items 7-20 belong to other manuals,
check relevance before assuming any applies.
