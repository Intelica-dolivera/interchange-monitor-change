---
name: dev-phase-considerations
description: "Architectural/design considerations surfaced during the POC that should be revisited when the project moves from POC to real development — distinct from the deferred-bug list"
metadata:
  node_type: memory
  type: project
  modified: 2026-09-05T22:48:00.786Z
---

Running list of forward-looking architectural notes surfaced while building the POC, kept
separate from [[pending-bug-fixes]] (which is per-manual defects) because these are cross-
cutting design/process observations relevant to a production build, not bugs in a specific
manual's pipeline. Requested by the user (2026-08-19, right after closing Module 3 for the
5th manual) as a companion to [[feedback-poc-vs-development]] — that memory is the POLICY
("keep findings, don't drop them"), this one is the actual accumulating content.

1. **RESOLVED for grid rows in manuals 3/4 (2026-09-03) — the cross-manual audit this item
   asked for.** Originally: found and fixed only in the 5th manual
   (`base_ii_transactions_quick_reference`) Module 2 — the Y-band/gap-based row-continuation
   logic (`group_into_rows`/`grid_row_buffer` pattern, shared code lineage) can silently merge
   unrelated rows across a page break, because a cross-page gap is a large NEGATIVE number that
   still satisfies a naive `<= GRID_ROW_GAP_MAX` check; flagged as needing the same audit across
   every manual before trusting "no bug observed yet" as proof of safety. **Audit result**: of
   the 4 manuals sharing this code lineage (grepped for `GRID_ROW_GAP_MAX`/`group_into_rows`),
   `base_ii_clearing_data_codes` (2nd) turned out structurally safe by a DIFFERENT mechanism —
   its `group_into_rows`/`build_blocks` are called per-page with all matching state reset every
   call (no `active_last_y1`/cells ever persists across a page boundary), and genuine
   cross-page row continuation is instead handled explicitly and safely by a separate
   `_merge_continued_rows` keyed on a literal `"(continued)"` code marker — not incidental
   safety, a real design choice. The 3rd (`..._tc_01_to_tc_49`) and 4th (`..._tc_50_to_tc_92`)
   manuals, however, WERE the genuinely exposed case: both process the whole document as one
   continuous stream (`grid_row_buffer` never reset per page) with no page-equality check
   before the `GRID_ROW_GAP_MAX` fallback — same latent risk as the 5th manual pre-fix, safe in
   practice only because their grid header happens to redeclare on every continuation page
   (confirmed by instrumenting a probe copy of each manual's `build_blocks` and running it
   against ALL 9 real editions of both manuals: 0 real trigger across all 18 edition-runs —
   this was never an active bug, purely a latent one). **Fixed**: ported the same explicit
   page-check pattern already proven in the 5th manual's fix — flush `grid_row_buffer` whenever
   its last line's page differs from the new line's page, before the geometry fallback ever
   runs — to both manuals' `build_blocks`. Also added a counter,
   `page_boundary_grid_guard_hits`, threaded into each edition's Module 2 JSON output and
   printed by `main()` with a `[!]` marker whenever nonzero — so if this condition is EVER hit
   by a future edition, it surfaces as a visible flag in the normal pipeline run instead of
   silently fusing rows (same observability principle as Module 5's `safety_net_override`).
   **Verified**: re-ran Module 2 for all 9 editions of both manuals — `blocks` output
   byte-identical to the pre-fix baseline (confirmed via direct dict comparison, not just
   count), 0 guard hits in current data (purely additive, zero regression), Module 3 re-run
   clean on top of the unchanged blocks. **Not touched**: manuals 6/7/8 don't share this
   `group_into_rows`/`GRID_ROW_GAP_MAX` code lineage at all (different block types —
   paragraph/ficha-based with their own reflow/matching mechanisms) — this item was scoped to
   the shared-lineage manuals only, confirmed by grep across the whole `poc/` tree before
   starting.

2. **Fuzzy-matching safety is NOT a manual-independent default — must be re-validated per
   manual, per matching level.** The same `difflib` 0.85-threshold fuzzy fallback that works
   safely for SECTION/TABLE TITLES in all 5 manuals (titles tend to be distinctive) turned out
   to be actively unsafe for ROW-level free text in the 5th manual (many genuinely-different
   rows measured ≥0.85 similarity in real data, e.g. `"Batch Disposition Code A"` vs `"...Code
   R"`). A production system should treat "is fuzzy matching safe here" as a question to
   re-answer per manual and per matching granularity, not a blanket assumption inherited from
   whichever manual was built first.

3. **Rename-detection sensitivity gap, 5th manual, deliberately accepted for the POC.** Because
   the 5th manual's row matching key consumes both mutable fields (TCR label + description, see
   [[open-questions-technical-manuals]] Module 3 section), a real rename always surfaces as a
   remove+add pair, never a `row_content_changed`-style diff — confirmed this happens for real,
   large edits (country-code prefixes added to ~10+ sections' worth of rows in one edition
   pair). A production report consumer will likely want a smarter, review-only heuristic
   eventually (e.g., flag "1 removed + 1 added row sharing the same TCR label in the same
   section" as a *possible* rename for a human to confirm, WITHOUT auto-matching them) — not
   implemented now because doing it at match-time reintroduces the false-positive risk from
   point 2. Worth designing properly once this stops being a POC.
   **DONE (2026-09-04)**: implemented exactly as scoped, at report time only
   (`base_ii_transactions_quick_reference/07_reporte_cambios/report.py`, `_extract_rename_hints`)
   — zero changes to Module 3/4/5, purely a display-level regrouping of `row_added`/`row_removed`
   that were already in the JSON. **A first implementation attempt was WRONG and caught before
   shipping, worth remembering as its own lesson**: it paired same-TCR removed/added rows by
   order-of-appearance when 2+ rows shared a TCR label (mirroring Module 3's duplicate-key
   pairing pattern) — looked fine on a small sample, but running it against the full corpus
   surfaced a real, serious false-positive: in "05 Sales Draft" (pair `20250412_to_20260418`),
   13 removed and 13 added rows all share the generic label `"TCR 2"` (one per country, e.g.
   `"National Settlement, Uruguay"`), but the removed list is sorted by country NAME and the
   added list by the NEW code prefix — two genuinely different sort orders — so order-based
   pairing fabricated nonsense matches like `"National Settlement, Sweden"` →
   `"(KR) National Settlement, South Korea"`, two unrelated countries. **Fixed by tightening to
   the literal spec**: only pair when there is EXACTLY 1 removed + 1 added row sharing that TCR
   in the section (matches the "1 removed + 1 added" wording this point already specified,
   which the first attempt had silently generalized to N:N without re-checking safety). Final
   verified scope against the real corpus: only 2 genuinely unambiguous hints across all 7
   pairs (`"Promotion Data"` → `"(PD) Promotion Data"`, 2 different sections, each a clean 1:1
   case) — the 13-country case and a handful of 2:2 cases (e.g. `"TCR 4"` appearing twice per
   section in the "..._Dispute" sections, `"Single Message System Interface (SMS Data)"` →
   `"Supplemental Financial Data"` and its "...and Promotion Data" sibling) correctly fall back
   to the existing generic "revisar a mano" warning instead of a fabricated pairing. Lesson
   reinforced: even an already-cautious, report-time-only, non-auto-matching heuristic needs
   validation against the FULL real corpus before trusting it, not just a plausible-looking
   design — the failure mode here would have been actively worse than the pre-existing gap
   (confidently wrong output, not just missing sensitivity).

4. **Architectural scaling question — bespoke per-manual parsers vs. a general extraction
   framework. Now backed by a real duplication inventory (2026-09-03), not just intuition.**
   Originally flagged (2026-08-19, all 5 manuals) as an undecided tradeoff: the project has
   needed genuinely different Module 2 content-shapes (Type B code-lookup tables, Type F
   validation-message fichas, Type A grid+ficha duality ×2, a simple 2-level list) and genuinely
   different Module 3 matching-key designs (position-based, code-based, composite-text-based) —
   each correctly derived from real data, the right call for a POC. All 8 manuals are now built;
   ran a real inventory across all 48 stage scripts (~13,144 LOC) with `diff`/`grep`, not
   assumption, to size the question properly. **3-tier result**:
   - **Tier 1 — 100% mechanical duplication, zero risk to extract**: Module 1's `main()` and
     Module 4's `main()` are BYTE-IDENTICAL across 7 of 8 manuals (only `vss_vol2` differs,
     ~8-20 lines, for its appendix-range logic); the Ollama HTTP client (`_ollama_classify`'s
     payload/request/response-parsing/invalid-category-fallback block) is near-verbatim
     identical across all 7 manuals that call an LLM (`base_ii_transactions_quick_reference`,
     the 5th, uses no LLM at all — `classify_pair` there is fully deterministic, no
     `_ollama_classify` present). Confirmed via literal diff, not eyeballing — one manual's
     `ingest.py` even has a comment admitting the copy: `"Igual que en
     base_ii_clearing_edit_package_messages"`.
   - **Tier 2 — the actual argument for consolidating, found as a live consequence, not a
     hypothetical**: `_find_disappeared_content` (Module 5's safety net) has the same skeleton
     copy-pasted into all 7 LLM-using manuals, but 2 real correctness fixes each landed in only
     ONE of the 7 copies and were never ported: the "replace opcode" fix
     ([[pending-bug-fixes]] item 7, originally fixed only in
     `base_ii_clearing_edit_package_messages`, explicitly flagged there as "likely applies to
     manual 1 too... not checked") and the bullet-glyph filter (item 4, fixed only in
     `base_ii_clearing_data_codes`). Verified live: `base_ii_clearing_data_codes` really was
     still missing the replace-opcode fix as of this inventory — ported it same session (see
     [[pending-bug-fixes]] item 7's resolution note), producing 10 real reclassifications
     confirmed against actual data, not simulated. This is the concrete cost of the "8 bespoke
     codebases" choice: a bug found and fixed once does not automatically reach its identical
     siblings, and nothing currently flags that it should.
     **CORRECTION (2026-09-04)**: the claim above that this fix "landed in only ONE of the 7
     copies" and was then "ported same session" turned out to only describe part of the story —
     re-verified against the actual current code (not re-trusting this memory) during Tier 1
     extraction prep and found the replace-opcode fix (`tag in ("delete","replace")` vs. the
     buggy `tag == "delete"` only) is present in just 2 of 7 LLM-using manuals
     (`base_ii_clearing_data_codes`, `base_ii_clearing_edit_package_messages`) — the other 5
     (`..._tc_01_to_tc_49`, `..._tc_50_to_tc_92`, `international_full_service_pos...`,
     `visanet...volume_1`, `visanet...volume_2`) still only match `tag == "delete"`, meaning a
     paragraph/row whose text is fully REPLACED by unrelated new text (not just deleted) is
     silently missed by the safety net in those 5 manuals right now. This is a live, active
     correctness bug, not a historical one already closed — do not trust the "ported" framing
     above without re-checking the code at the time of reading this.
   - **Tier 3 — genuinely bespoke, confirmed NOT to consolidate**: Module 2 ranges 102-727 lines
     and Module 3 197-417 lines across the 8 manuals, each a real structural fit to that
     manual's PDF (grid+ficha, linear single-block stream, rotated pairs, simple lists) — sizes
     alone confirm these aren't boilerplate wearing different clothes, forcing a shared
     abstraction here would repeat the anti-pattern this project has correctly avoided 8 times
     over.
   **Recommendation given this evidence**: extract a small shared module for Tier 1 (both
   `main()` wrappers + the Ollama client, parameterized only by the already-built prompt) and
   use that same pass to audit/port any other Tier-2-style single-copy fixes not yet checked
   across siblings; leave Tier 3 (Module 2/3) bespoke, unchanged.
   **DONE (2026-09-04)**: `poc/_shared/stage_runners.py` (Module 1/4 `main()` wrappers, 7 of 8
   manuals — vss_vol2 stays bespoke, its own result schema) and `poc/_shared/ollama_client.py`
   (`ollama_classify`, `ensure_ollama_running`, `find_disappeared_content`, all 7 LLM-using
   manuals) now exist — see [[router-landing-progress]] for the CONTRACT.md writeup. Doing this
   consolidation surfaced that the "replace opcode" fix's porting status recorded just above was
   ITSELF WRONG: re-verified against the actual current code (not trusted at face value) and
   found only 2 of 7 LLM-using manuals actually had it, not "ported to all" as this memory
   claimed — see the CORRECTION note attached to the Tier 2 paragraph above. Consolidating
   `_find_disappeared_content` into one shared copy closed that gap in the same change (measured
   impact before touching code: 14 concrete real cases across the 5 previously-buggy manuals
   that flip from "editorial_reword" to a forced "business_rule_change" override, one of them
   the exact V1209 case documented in Tier 2's original writeup). Verified: Modules 1/4 output
   byte-identical to pre-change for 6/8 manuals; a real (unrelated, pre-existing) list-ordering
   nondeterminism was found in `visanet...volume_1` and `volume_2`'s Module 3 (`match.py`) while
   diffing — see new point 9 below, not something this Tier 1 change introduced. Module 5
   re-verified with real Ollama (not `--skip-ai`) on a cheap pair per manual: all 7 ran clean,
   the new overrides that appeared are legitimate (report shows the ⚠️ marker, e.g. the exact
   historical V1209 case now flags again on a fresh classify). Not done in this pass, still
   deliberately deferred: report-layer consolidation (`report.py` per manual, Module 8
   adapters), low-level extraction utilities (`_split_line_segments` and siblings), and
   `classify.py`'s `main()` (confirmed structurally bespoke per manual, not Tier 1).
   **Low-level extraction utilities AUDITED (2026-09-06), verdict: nothing to consolidate or
   fix.** User asked to pick this deferred item up. Real duplicated surface turned out much
   smaller than the framing above implied: only 3 of the 8 manuals
   (`base_ii_clearing_data_codes`, `visanet...volume_1`, `visanet...volume_2`) have this
   "split a PyMuPDF line into segments by whitespace-only spans" helper at all — the other 5
   manuals' `extract_pdf_lines` never needed it. Found 1 real code difference between the 3
   copies: the original (`base_ii_clearing_data_codes`'s `_split_line_segments`) lacks the
   `or [spans]` defensive fallback that both later ports (`_split_rotated_line_segments`,
   `_split_whitespace_segments`) have — looked exactly like the same "fix landed in the port,
   never came back to the original" pattern already found twice elsewhere in this project.
   **Verified empirically it is NOT a real bug, in either direction**: ran each manual's actual
   function against its own full real corpus (all editions) — the missing-fallback case (all
   spans in a line being whitespace-only) never once occurs in `base_ii_clearing_data_codes`'s
   89,537 real lines (9 editions), so the fallback's absence there is provably inert. It DOES
   occur often in `visanet...volume_1`/`volume_2` (270 and 1,134 times respectively, out of
   15,360 and 165,865 lines) — but both manuals have a `if not text: continue` filter
   immediately downstream that discards an all-whitespace segment either way, so the fallback's
   presence there is ALSO provably inert — confirmed by reconstructing the no-fallback logic and
   diffing against the real output, 0 observable difference in final JSON in any of the 3
   manuals. **No changes made** — this is a legitimate "measured, not needed" outcome (same
   discipline as the router landing/Appendix D scope corrections earlier this session), not an
   oversight: the 3 existing copies also have genuine per-manual differences worth keeping
   bespoke (a TOC-dot-leader guard specific to `base_ii_clearing_data_codes`'s layout,
   rotated-only scoping in `visanet...volume_1`), so even setting the dead-code question aside,
   the shared surface was never going to be large enough to justify a new `poc/_shared/` module
   for this.

5. **Section-move detection gap, 6th manual (`international_full_service_pos_online_messages_
   processing_specifications`).** Module 3's section matching key is the full hierarchical
   heading path (L1>L2>L3, needed because sub-heading titles repeat systematically under
   different parents — e.g. "Cardholder Transactions" appears under both "Transaction Types"
   and "Standard Processing" as genuinely different sections). Confirmed real consequence with
   actual data: when Visa promotes a subsection to a standalone top-level chapter (e.g.
   `"VisaNet Systems > Full Service Processing"` (level 2) became `"Full Service Processing"`
   (level 1) between `20241021→20250414`), the path changes entirely even though the paragraph
   text inside is ~90% identical — it shows as a full section removed + full section added
   (296→264 sections, 90 removed/58 added in that one pair) rather than "moved, content mostly
   unchanged." A production report consumer would likely want a "this looks like the same
   content relocated" heuristic (e.g., compare paragraph-set similarity between a removed and
   an added section, independent of path) — not implemented now for the same reason as point 3
   (matching-time inference reintroduces false-positive risk); a report-time *hint*, never an
   auto-match, is the safer place for this if it's ever built.
   **DONE (2026-09-04)**: implemented in `match.py` (`find_possible_section_moves`), report-time
   hint only — `sections_removed`/`sections_added` in Module 3's output are completely
   untouched, the new `possible_section_moves` field is purely additive; Module 4 emits it as a
   `possible_section_move` change type alongside (not instead of) the existing `section_added`/
   `section_removed` events; Module 7 groups them together for display only. **Metric reuses
   existing code rather than inventing a new one**: treats the removed and added section as "2
   editions" of a hypothetical single section and runs the module's own `match_paragraphs`
   (already-validated exact+fuzzy+reflow paragraph matcher) between them — coverage = fraction
   of the removed section's paragraphs that found an equivalent in the added section.
   **A real false-positive pattern was found and filtered BEFORE shipping, by measuring against
   the full corpus first** (same discipline as the manual-5 rename heuristic): coverage alone is
   not enough — several small OLD sections (3-7 paragraphs) scored 0.6-1.0 coverage against ONE
   large NEW section (22-75 paragraphs) that was actually a many-to-one CONSOLIDATION of several
   old sections, not a 1:1 move (e.g. 4 different old "Additional Considerations..." subsections
   all partially overlapping the same new "Considerations for Visa POS Issuers"). Fixed by
   requiring BOTH high coverage (`SECTION_MOVE_MIN_COVERAGE=0.8`, exactly where the known real
   case scores) AND comparable section size (`SECTION_MOVE_MIN_SIZE_RATIO=0.5`, i.e.
   `min(paragraphs)/max(paragraphs) >= 0.5`) — the genuine 1:1 moves cluster at size-ratio
   0.5-1.0 while the consolidation false-positives sit at 0.04-0.33, a clean separation.
   **Mutual 1:1 uniqueness also enforced** (same principle, and the same real edge case
   category, as the manual-5 rename heuristic): if a removed or added section appears in more
   than one candidate pair passing both filters, none of those candidates are reported — found
   for real via a duplicated section path ("Mobile Location Confirmation Service" appearing
   twice in both the removed and added sets of one edition pair). **Verified end-to-end** against
   the real corpus: 42 candidates pass both filters before the uniqueness check, 40 survive it
   (2 dropped, the duplicate-path case); the known real case (`"VisaNet Systems > Full Service
   Processing"` → `"Full Service Processing"`) scores exactly 0.8 coverage as predicted and
   renders correctly in the generated report with real Ollama classification on top. Runtime is
   fine (~8.5s for the whole manual's Module 3, dominated by the one large 90×58-candidate pair)
   because the cheap size-ratio filter runs before the expensive paragraph-matching call, not
   after.

6. **Fuzzy-matching threshold tuning is itself manual-specific and needs its own evidence.**
   The 6th manual needed a THIRD fuzzy-matching profile, distinct from both the safe "section
   titles" default (0.85, unscoped) and the "unsafe, don't do it" row-level conclusion from the
   5th manual: paragraph-level fuzzy matching here is only acceptably safe with an ADDED length
   floor (≥60 chars) alongside a higher threshold (0.90) — even then a small residual risk
   remains (~0.5-1% of eligible pairs), from formulaic/templated prose (e.g. three near-
   identical "Converting ... Response Code X" sentences that are genuinely different table rows
   written as prose). Reinforces point 2 above with a concrete third data point: there is no
   single safe fuzzy-matching recipe across manuals or even within one manual's content types —
   each needs its own threshold AND its own risk-mitigating preconditions (length floor, scope),
   derived from real pairwise-similarity measurement, not assumed from what worked elsewhere.

7. **Page-boundary chunking instability is better reconciled at the matching layer (content-
   equivalence) than guessed at the extraction layer (geometry).** The 6th manual's Module 2
   correctly refuses to merge paragraphs across a page break (avoiding the 5th manual's row-
   merge bug), but this means the SAME real paragraph can get chunked into 1 block in one
   edition and 2 blocks in another purely from where a page break falls (confirmed: a "keep
   with next" PDF pagination rule can push a short list-intro sentence to the next page even
   when there's visible room left on the current page, so a geometric "near page-bottom" guard
   wouldn't even have caught it). The fix that worked was NOT at the geometry/extraction layer —
   it was checking, at match time, whether 2 adjacent paragraphs on one side concatenate to
   exactly equal one paragraph on the other side. General lesson for a production build: don't
   try to make block-boundary detection at extraction time perfectly stable across page reflow —
   it structurally can't be, since real pagination rules (widow/orphan control, keep-with-next)
   are invisible in the text/geometry alone. Reconcile equivalence downstream instead, where
   both sides' data is available to compare directly.

8. **The 6th manual's paragraph-reflow fix (item 7) is real but incomplete — needs a general
   N:M paragraph-realignment algorithm to fully close, deferred by explicit user choice
   (2026-08-19).** The bounded fix (`_reflow_matches` in the 6th manual's `match.py`) only
   handles the simple case of 2 adjacent paragraphs on one side concatenating to exactly equal 1
   paragraph on the other. Real residual cases found after the fix: (a) 2↔2 re-chunking (2
   paragraphs merge into a different 2-paragraph split, not reducible to a simple pair-to-single
   check); (b) PDF hyphen-wrap extraction noise (`"non-USD"` vs `"non- USD"` — an extra space
   after a hyphen inserted inconsistently between editions depending on where a compound word
   happens to line-wrap) breaking otherwise-exact reflow matches by a single character; (c) at
   least one case that may be genuine content removal masquerading as a chunking artifact,
   unconfirmed. Fixing this properly needs real sequence alignment across a whole section's
   paragraph list (diff-style, not pairwise) — offered to the user as an option, explicitly
   declined in favor of shipping the already-validated improvement (safety_net_override 29→14)
   and moving on. Revisit with a general realignment approach (and a hyphen-wrap-tolerant text
   normalizer) when this manual's pipeline gets hardened for production.
   **STALE as of 2026-09-04, corrected in place**: residual (a) — the general N:M
   realignment — was ALREADY DONE on 2026-08-25 ([[pending-bug-fixes]] item 13), this note just
   never got updated to reflect it. Discovered this re-reading `match.py`'s actual current
   docstring/code (not trusting this memory) while doing point 5's work, before starting on
   point 8 — same "verify before trusting" discipline as the item-7 correction. `match_paragraphs`
   already runs one `difflib.SequenceMatcher` over the whole section's paragraph list and treats
   any `"replace"` block (any N:M size, not just 2:1) as reflow when its full concatenation
   matches exactly. **Residuals (b) and (c) DONE (2026-09-04)**, and turned out to be one thing,
   not two, plus a genuinely new third finding:
   - Investigated by checking every remaining `safety_net_override` in the corpus (11 total,
     down from the original 29→14 baseline) against the WHOLE new section's other paragraphs
     before touching code: 9 of 11 were the SAME real pattern — content that looks
     "disappeared" from its specific fuzzy-matched pair is actually intact, verbatim, in some
     OTHER non-adjacent paragraph of the same new section. The existing block-based reflow
     detection structurally can't catch this (`SequenceMatcher`'s LCS alignment only groups
     CONTIGUOUS differences into one "replace" block; content redistributed to a distant
     paragraph doesn't land in the same block). This is what residual (b)'s "hyphen-wrap"
     framing was actually a symptom of — the real root cause is non-adjacent redistribution,
     not specifically hyphen noise. **Fix**: `detect.py` now attaches `section_new_paragraphs` (every new-edition paragraph
     text for that section) to each `paragraph_content_changed` change; `classify.py`
     (`_split_relocated`) checks each "disappeared" chunk against that full list before letting
     it drive an override — if found elsewhere in the section (exact substring, normalized), it
     doesn't count as disappeared for the override decision, but IS still recorded (as
     `content_relocated_within_section`) for transparency, same observability principle as
     `safety_net_override` itself. Report-time-adjacent (computed at Module 4/5, surfaced in
     Module 7's "Avisos de confiabilidad"), never silently drops evidence.
   - Residual (c) — investigated, not found reproducible in the current corpus: broadened the
     search to the WHOLE new edition (not just the matching section) for the 2 non-relocated
     cases; both are genuinely absent everywhere, confirming real content removal, not an
     unconfirmed ambiguous case. Whatever the original 2026-08-19 "may be genuine removal" case
     was, it either got resolved as a side effect of later fixes or isn't reproducible with
     today's corpus — not chased further.
   - **Investigated 2026-09-05, user asked to size the real scope before deciding whether to
     fix. Verdict: leave as-is, deliberately not fixed.** One of the 3 overrides remaining after
     the fix above (`"VSDC PIN Management Service"`, actually pair `20240415→20241021`, not
     `20230415→20231015` as this note originally said) is a paragraph truncated MID-WORD
     (`"...in Fie"` / `"ld 52 52—Personal..."`). **Confirmed NOT a Module 1/2 bug** — read the
     real source PDF's raw span data directly with `fitz`: the 2 fragments are genuinely 2
     separate spans in the PDF ITSELF, same Y-band, ~9pt gap, and the 2nd fragment's "52" is
     truly duplicated in the source — a real Visa-side PDF defect (plausibly a botched Word
     cross-reference field), not an extraction artifact. Nothing at the parsing layer can recover
     text that isn't there. **Real scope, measured by scanning all 8 editions for the same
     same-Y-band adjacent-line-split signature** (excluding TOC dot-leaders, numbered-list
     markers, and 2-column table-header pairs, which are the same geometric shape but benign):
     exactly ~5 genuine mid-word splits per edition (e.g. "wh"+"ich"="which", "ST"+"IP"="STIP",
     "Res"+"ults"="Results", "V.I."+"P."="V.I.P.", plus the Field/duplication case), but ONLY in
     the 3 oldest editions (`20230415`, `20231015`, `20240415`) — **zero in all 4 newer editions**
     (`20241021` onward), meaning Visa's PDF generation process changed and this defect stopped
     recurring. Impact is therefore confined to exactly 3 historical pairs, never current ones.
     **Why not worth fixing**: these change types (`paragraph_added`/`paragraph_removed`) never
     go through AI classification in this manual (structural, shown as-is) — so this never
     produces an incorrect business-change verdict, only extra cosmetic fragments in the report's
     "Párrafos agregados/eliminados" appendix section for 3 already-historical pairs. User agreed
     to leave it alone given the low remaining value (self-limited to old data, cosmetic only,
     source-side defect no parser fix could truly correct anyway).
   - **Verified end-to-end with real Ollama** (not `--skip-ai`) on the 3 pairs that had any
     overrides: total `safety_net_override` dropped 11→3 across the corpus (6 relocated-within-
     section suppressed in one pair, 2 in another, 0 change in the third which had none of that
     pattern); the 3 remaining are the 2 genuine removals above plus the newly-found truncation
     case. Report renders correctly: the 2 genuine cases keep their ⚠️ marker, the 8 relocated
     ones show up as a distinct, separate "Avisos de confiabilidad" note instead of a false
     `business_rule_change`.

9. **Real, previously-unknown nondeterminism found in Module 3 (`match.py`) for
   `visanet...volume_1` and `visanet...volume_2` (2026-09-04) — list ORDER only, not content,
   but worth fixing before production.** Discovered as a side effect of the Tier 1 extraction
   work (unrelated code, Module 3 wasn't touched): running the exact same unchanged `match.py`
   twice in a row on the same input produces JSON with matched-paragraph lists in a different
   order each time. Confirmed via a canonicalized (order-normalized, recursively sorted)
   comparison that the actual matched content is byte-identical between runs — this is pure
   ordering nondeterminism, almost certainly from a `set()`/dict-iteration-order dependency
   somewhere in the paragraph-matching logic that Python's per-process hash randomization
   (`PYTHONHASHSEED`) makes non-reproducible. Not investigated further or fixed this session
   (out of scope for the Tier 1 change that surfaced it) — but it means "re-run and diff for
   byte-identical output" as a verification technique does NOT work for these 2 manuals'
   Module 3 onward without first normalizing list order, and more importantly: any consumer
   that treats list position as meaningful (a diff tool, a human comparing 2 report runs, a
   future caching/incremental layer) could see spurious "changes" that are pure noise. Worth
   finding and fixing the actual `set()`-driven ordering before this manual's pipeline is
   considered production-hardened — likely a small, contained fix (sort by a stable key before
   returning) once located.
   **RESOLVED (2026-09-05).** Found by grepping every `set(` in both manuals' `match.py` and
   checking, for each, whether the set gets ITERATED for output order (unsafe) vs. only used
   for membership testing or already re-sorted before return (safe) — 4 unsafe occurrences
   total: `visanet...volume_1`'s `match_paragraphs` (1), `visanet...volume_2`'s `match_tables`,
   `match_headings`, and `match_paragraphs` (3). All 4 followed the same shape: `for x in
   set(by_key_a) | set(by_key_b):` feeding an output list with no final sort — unlike sibling
   functions in the same files (`match_rows`/`match_pairs`) that hit the identical pattern but
   already end with `sorted(matched, key=sort_key)`, which is why only SOME functions per file
   were affected, not all. **Fix**: sort the iteration source itself (`sorted(set(...) |
   set(...))`) rather than only sorting the final output — sorting only the end result would
   have fixed list order but NOT a subtler thing found while verifying (see below). **Verified
   real fix**: running `match.py` twice in a row on unchanged input now produces byte-identical
   output for both manuals (was different every time before). Content-regression check (run
   before the fix vs. after, order-normalized): `visanet...volume_2` — 0 differences across all
   6 pairs, confirming the bug really was pure ordering there. `visanet...volume_1` — 1 real
   content difference survived normalization, in 1 section of 1 pair (`20230415→20231013`,
   "Reporting Options Worksheet"): **a genuine finding, not a fix regression** — the fuzzy
   paragraph-matching stage is a GREEDY algorithm (each unmatched old paragraph, in whatever
   order it's processed, claims its best available match from the pool, removing it from
   contention for the next one). Two old and two new paragraph fragments here were genuinely
   near-tied candidates for each other (a reflow-like re-split between editions) — the random
   pre-fix processing order happened, in the one snapshot compared, to land on a
   tighter pairing (0.996 similarity) than the now-deterministic sorted order does (0.907, still
   safely above the 0.90 threshold). **This means the ORIGINAL bug wasn't purely cosmetic
   ordering — in rare greedy-contention cases it could also silently vary which specific
   pairing gets chosen, not just the list position.** Sorting the iteration source fixes
   reproducibility (same input → same output, always) but does NOT make the greedy fuzzy stage
   globally optimal — it's now a stable, arbitrary tie-break, not necessarily the best available
   pairing. Presented this tradeoff to the user directly (`AskUserQuestion`): fix determinism
   only (cheap, what was actually asked) vs. also replace the greedy per-paragraph assignment
   with a globally-optimal one (e.g., collect all candidate pairs above threshold, assign
   greedily in DESCENDING similarity order instead of arbitrary processing order — a real
   algorithm change, more invasive). **User chose determinism-only for now, asked to log the
   optimality gap here for later** — this paragraph is that log entry. Scope: only 1 instance
   found across the full 2-manual corpus (11 edition pairs total), both candidate pairings clear
   the safety threshold — same order of magnitude as other accepted residual risks in this
   project (e.g. manual 6's ~0.5-1% formulaic-prose fuzzy risk), not treated as urgent. **If
   revisited**: the fix would be in `match_paragraphs` (both manuals) and `match_headings`
   (`visanet...volume_2`) — replace the `for pa in unmatched_a: <find best pb, pop it>` greedy
   loop with: compute all `(pa, pb, ratio)` candidates above threshold up front, sort by ratio
   descending, then greedily assign in THAT order (highest-confidence pairs claim first) —
   removes the dependency on `unmatched_a`'s processing order entirely, not just makes it
   stable. Re-ran the specific pair after the determinism fix (`--only`, real Ollama) to keep
   on-disk data consistent with the corrected Module 3/4 output — nothing about this needed the
   optimality fix to be safe to ship.
   **RESOLVED (2026-09-06).** User asked to revisit this gap. Grepped both manuals' `match.py`
   for the same greedy shape (`best_ratio`/`best_idx` pattern) before assuming the 2 functions
   named above were the only ones affected — found 4 total, not 2: `visanet...volume_1`'s
   `match_sections` (fuzzy section-title matching) ALSO has the identical pattern, not just
   `match_paragraphs`; `visanet...volume_2`'s `match_tables` (fuzzy table-title matching) also
   has it, not just `match_headings`. Fixed all 4 with the exact design already logged above
   (collect all `(ratio, a, b)` candidates above threshold, sort descending, greedily assign in
   that order) — implementation differs slightly per function to match each one's existing data
   shape (index pairs for list-based `match_sections`/`match_paragraphs`/`match_headings`,
   string titles directly for dict-keyed `match_tables`, since titles are already unique and
   safe to use as set members without needing `id()`-based tracking). **Verified**: `match.py`
   still gives byte-identical output across repeated runs for both manuals (determinism from
   the original fix preserved). Order-normalized content diff (before this fix vs. after, across
   all 11 pairs in both manuals): only the ONE already-known case
   (`visanet...volume_1`, `20230415→20231013`, "Reporting Options Worksheet") changed, and it
   changed to the BETTER pairing — both fuzzy matches in that section now consistently score
   0.996 (previously arbitrary between 0.996 and 0.907 depending on run order; now always the
   higher-confidence one). All other 10 pairs across both manuals stayed byte-identical
   (order-normalized), confirming the fix is surgical — it only changes outcomes in genuine
   near-tie situations, never touches unambiguous matches. Re-ran the 1 affected pair's Module 5
   with real Ollama to keep on-disk data consistent. This closes the gap fully — the fuzzy
   matching in both manuals' Module 3 is now both deterministic AND globally optimal (within
   each function's own candidate pool), not just stable-but-arbitrary.

**Why:** the user wants this kind of cross-cutting insight preserved so it isn't rediscovered
from scratch (or, worse, silently missed) when scoping the production build — POC-phase
velocity means these are noted rather than acted on immediately.

**How to apply:** when the user signals the project is moving from POC to real development,
proactively surface this file's contents (alongside [[pending-bug-fixes]]) as input to
scoping/planning, rather than waiting to be asked. Keep adding to this list as new
cross-cutting patterns emerge in later manuals.
