---
name: reference-pipeline-vs-technical-manuals
description: "What the utils_example reference pipeline does stage-by-stage, and how its entities map (or don't) to the technical-manuals domain"
metadata: 
  node_type: memory
  type: project
  modified: 2026-08-11T16:58:39.913Z
---

## Reference pipeline (`utils_example/`, built by another team for Visa/Mastercard Interchange
Guides — fee-rate rule PDFs, NOT the same document type as this project's manuals)

1. **Stage 1 (script not shared)** — extracts PDF via **Docling** into `raw_guide.json`: a flat
   list of blocks, each with `page`, `bbox`, `type` (`text`|`table`), `text`. Table blocks are
   already rendered as **Markdown** at this stage — not the whole document, just tables.
2. **Stage 2 (`02_guide_parser.py`)** — sorts blocks by page/position, detects numbered section
   headings (builds `section_path` hierarchy), attaches `Table X-Y: Title` captions to their table,
   classifies block role (`section_heading`, `paragraph`, `business_table`, `navigation`,
   `summary_of_changes`), strips noise (page numbers, headers/footers, legal notices, TOC/List of
   Tables/Figures), and merges tables split across consecutive pages by comparing normalized
   headers (`_get_normalized_table_schema`, `_merge_table_continuations`).
3. **Stages 3-4 (not shared)** — presumed matching step: pairs "Program" and "Fee Descriptor"
   entities between old/new versions (exact + fuzzy name match — output consumed by stage 5 has
   `match_type`, `fuzzy_ratio`, `added_descriptors`, `removed_descriptors`, etc).
4. **Stage 5 (`05_diff_descriptors.py`)** — diffs matched entities: fee rate changes
   (`fee_rate_raw`), criteria text changes (`SequenceMatcher` ratio, threshold 0.98), program/
   descriptor renames (fuzzy), added/removed programs/descriptors. When criteria text references
   `Table X-Y`, resolves and attaches that table's actual content from both versions for downstream
   AI context (`enrich_criteria_change`).
5. **Stage 6 (`06_classify_changes.py`)** — sends only ambiguous free-text `criteria_changed` items
   to a local LLM (Ollama, `qwen3:4b`, forced JSON schema, temp 0) to label as
   `criteria_real_change` / `criteria_clarification` / `criteria_reword` / `extraction_noise`, with
   a deterministic safety net (`detect_disappeared_content`) that downgrades confidence if the LLM
   says "noise" but significant content actually vanished. Structural decisions (added/removed/
   renamed) stay fully deterministic — the LLM only judges free-text nuance.

## Domain mapping: Guides vs Technical Manuals (this project)

| Guides (reference team) | Technical manuals (this project) |
|---|---|
| Container entity: **Program** | Container entity: **Record / Message / TC** (e.g. TC 05, TC 15 in Base II; a Base I ISO message) |
| Detail entity: **Fee Descriptor** | Detail entity: **Field / Data Element** (position, length, name, format) |
| Matching key: entity **name** (exact/fuzzy) | Matching key should be **position / byte range / field number**, not name — far more stable across editions than fuzzy name matching |
| Change types: added/removed program/descriptor, rate change, criteria change, rename | Change types include those PLUS a domain-specific one: **reserved field becomes defined** (a position that existed but was unnamed/"Reserved" gets a real field name+definition in a later edition) — this is not a rename (no real old name to fuzzy-match) nor a pure "added" (the slot already existed) |

**Why:** [[project-overview]] — the core deliverable is detecting exactly this kind of
reserved→defined transition, plus ordinary field additions/removals/definition changes, edition
over edition.

**How to apply:** When designing the matching/diff stage for this project, don't port stage 3-4's
fuzzy-name matching as-is. Design matching primarily around stable positional/numeric keys
(byte position or field number within a given Record/TC), with name-based fuzzy matching as a
secondary signal only. Reuse stage 2's approach (block classification + noise filtering + table
continuation merging) as a strong pattern for stage 2 of this project too, since these are also
Visa PDFs with similar headers/footers/noise.

## Additional detail from a parallel Claude Web design session (merged 2026-08-11)

Confirmed domain model with real names: `Manual (versión=fecha) → Transaction Code / sección
funcional (ej. "TC 33.A Capture Transactions (Acquirer)") → Component Record / grupo de campos
(ej. "TCR 0", "CP 02 TCR 0 EMV Data") → Campo (position_range, length, format, name, description,
valid_values, notes)`. Format codes seen at the foot of Record Layout tables: `AN`=Alphanumeric,
`ANS`=Alphanumeric Special, `DX`=Display Hexadecimal, `N`=Numeric, `UN`=Unpacked Numeric — this
legend should be parsed per-manual since it may vary.

**Two distinct content patterns per field, needing different extraction treatment:**
1. **"Record Layout" summary tables** — real grid (`Position | Field | Length | Format |
   Contents`), one row per field, compact. This is the structural source of truth — additions/
   removals/length/format/position changes are detected here. **Highest risk for silent extraction
   errors**: narrow one-row-per-line tables linearize fine even with raw `pdftotext`, but wide
   tables, wrapped cells, or side-by-side columns can silently interleave text from different
   columns when extracted without layout awareness.
2. **"Field ID cards"** — NOT a real PDF table, running text with a repeated pattern (`Field Name`
   → `Positions:` → `Length:` → `Format:` → `Description:` → optional `Values:` / `Note:`,
   sometimes with cross-system `Mapping:` lines). Source of business description, valid values,
   external mappings. Regex-parseable even from raw crude text extraction — doesn't need
   layout-aware tooling. Both patterns describe the same logical field and should be linked by
   name + position range when building the final structured block.

**Real example found** (from `20260418 - BASE II Clearing Interchange Formats, TC 01 to TC 49.pdf`,
section "TC 33.A - CP 02 TCR 0 EMV Data"): a Record Layout table ending in `151-168  18  AN
Reserved` — this exact row is the kind of thing the project needs to catch changing across
editions (e.g., splitting into a defined sub-range + a smaller Reserved remainder).

**8 proposed diff change-categories** (analogous to the Guides pipeline's rate/criteria/rename/
added/removed, but domain-specific): `field_added`, `field_removed`, `field_redefined` (same
position, name/meaning changes), `field_resized` (length changes — see chain-shift problem below),
`field_position_shifted` (same field, position range changed — typically a downstream consequence
of an earlier field's `field_resized`), `field_format_changed`, `field_description_changed` /
`field_values_changed`, plus structural top-level ones (`tc_added`/`tc_removed`/`tcr_added`/
`tcr_removed`).

**Unresolved design problem — "chain-shift" matching:** when a field changes length, every
subsequent field in the same TCR shifts position even though it didn't itself change. Matching by
absolute byte range alone would misread this as a chain of false `field_removed`+`field_added`
pairs. Proposed mitigation (untested): use **ordinal position within the TCR** (e.g., "5th field
of TCR 0") as a secondary anchor alongside the byte range, so a pure shift is recognized as the
same field moved, not a different field. Needs validation against real consecutive editions.

**Proposed Stage 6 labels** (in place of Guides' `criteria_real_change`/`criteria_clarification`/
`criteria_reword`/`extraction_noise`): `structural_change`, `business_rule_change`,
`editorial_reword`, `extraction_noise`. The Guides pipeline's `detect_disappeared_content` safety
net (downgrade LLM confidence if content vanished without an equivalent even when the LLM says
nothing changed) is directly reusable as-is for this project too.

## Empirical extraction-tool findings (2026-08-11, tested on real PDFs in this environment)

Installed `pdfplumber` + `pymupdf4llm`, tested against 3 real pages across 3 manual families.
Result **reversed the original hypothesis**: raw PyMuPDF text extraction (`fitz.get_text()`, no
table tooling) reconstructed every row correctly in all cases, including a wide 3-column table
with wrapped bullet-list cells (`base_ii_clearing_data_codes` p.31, "Retired Chargeback Reason
Codes"). `pymupdf4llm`'s markdown table reconstruction **silently dropped a whole row** on that
same table (reason code "82"). `pdfplumber.extract_tables()` failed badly on the borderless
"Record Layout" grid tables (no ruling lines → garbled columns). Conclusion: use raw
page-ordered PyMuPDF text (with page+bbox provenance) as the extraction source of truth, parsed
via pattern-specific regex per content shape — not generic ML table reconstruction. Docling is
not justified by evidence so far. Full test details in `local_memory/NOTES.md` in the repo.

**3 distinct content shapes catalogued so far** (confirms table layout is NOT homogeneous across
manual families — answers the open question in [[open-questions-technical-manuals]]):
- **Type A — "Record Layout" grid + "Field ID card" prose**: seen in
  `base_ii_clearing_interchange_formats_tc_01_to_tc_49` (likely also `tc_50_to_tc_92` and BASE I
  manuals — not yet checked).
- **Type B — code/rule lookup tables**: 2-3 columns, wrapped text + bullet lists, no position/
  length columns. Seen in `base_ii_clearing_data_codes`.
- **Type C — fixed-width report layouts**: pre-formatted text simulating a printed report
  (`REPORT ID:`, `PAGE:`, manually space-aligned columns), not a real PDF table at all. Seen in
  `vss_user_guide_volume_1_specifications`.

Still unsampled: `base_i` (ISO messaging), `vss` volume 2 reports, `base_ii_transactions_quick_reference`,
`base_ii_clearing_edit_package_messages`.

## Full 7-family catalogue completed (2026-08-11) — final tool verdict

Sampled the remaining 5 manual families. **Final conclusion: `fitz.get_text()` (raw PyMuPDF text)
works as the single extraction tool across all 7 families** — it reconstructed content correctly
in every test, including a new stress case (VSS's wide 5-column field-layout table with wrapped
bulleted comments — `pymupdf4llm` didn't drop a row there like it did on the Type B table, but it
DID fragment one wrapped-comment row into two bogus Markdown rows, a second distinct data-integrity
defect). What varies per manual family is not the extraction tool but the **downstream regex
parsing pattern**, because each family has its own text "grammar." Full catalogue (6 content
shapes: A/A'/B/C/D/F) and the per-family tool-fit table live in `local_memory/NOTES.md` in the
repo — don't duplicate the table here, read that file for the full breakdown.

**Important scope finding:** `base_i`
(`international_full_service_pos_online_messages_processing_specifications`, 232 pages) contains
NO byte-level Record Layout tables anywhere (verified exhaustively — no "Positions:"/"Field
Definitions"/"Data Element"/Length+Format table headers in any of its 232 pages). It's business-
process narrative that references field numbers in prose but explicitly defers the actual field
layout to an external manual not present in this repo ("V.I.P. System technical specifications").
This means the core reserved→defined use case may not be directly applicable to `base_i` with the
files currently in the repo — worth confirming with the user whether a field-spec manual for BASE I
is missing or whether BASE I is intentionally out of scope for the binary-layout diff.

**Update:** user added a second `base_i` manual (`authorization_only_online_messages_processing_
specifications_International`, 197 pages) hoping it was the missing field-spec manual. Verified
exhaustively (regex grep across all 197 pages) — it is NOT: same narrative Type E content as the
other `base_i` manual, no Record Layout grids anywhere. Found a 7th content shape (Type G) on
p.158: file-schema tables that list field NAMES per CDB file (Activity File, Address Verification
File, ASAF) with no position/length data — tells you what fields exist but not their byte layout.

**RESOLVED (2026-08-11):** user then added
`visa/src/base_i/visanet-authorization_only_online_messages_technical_specifications/` with 9 files:
`VisaNet Authorization-Only Online Messages Technical Specifications` (1242p, single 2022-06-10
edition only) + `Full Service POS Online Messages Technical Specifications` (8 editions,
2022-06-10 → 2025-10-15, 1593-1673 pages). These are two DISTINCT manuals (not one renamed —
they coexist at the same 2022-06-10 date with different page counts), each the technical/byte-level
counterpart to one of the two narrative "Processing Specifications" manuals already in `base_i`.
Confirmed via exact text match: the narrative Full Service manual literally says "...Formats
chapter of Full Service POS Online Messages Technical Specifications, for information..." (p.35) —
matches the found manual's title exactly. Verified the Full Service technical manual (2025-10-15
edition) has 258 pages of `Field N – Attributes/Description/Usage/Field Edits/Reject Codes` cards
(Type A'' — same family as the Field ID card, different label vocabulary) and 19 pages of real
`Field Name | Position | Attributes | Description` grids (Type A'), 4 of which contain `Reserved`
rows — confirms the core reserved→defined use case DOES apply to `base_i` via this manual, and it
has enough editions (8) for real version-over-version diffing. The single-edition
Authorization-Only technical manual is useful as a structural reference but not for diffing yet
(no second edition available).

**New content shape found in this manual — Type H, field-usage-by-message-type matrix**: rows =
field number+name, columns = message types/flow steps (0100/0110/0120, Acqr→VIC→Issr...), cells =
usage code (M=Mandatory/C=Conditional/O=Optional/C+/C-, with `→` arrows meaning "passed through
unchanged"). E.g. "Table 237: Manual Cash or Quasi-Cash...", "Table 275: VSDC ATM Account Transfer
Reversal". This isn't a field-definition diff target — it's a distinct kind of change worth adding
to the proposed change-categories: something like `field_usage_requirement_changed` (e.g. field 42
went from Conditional to Mandatory in message 0100), not covered by the original 8 categories in
this file.

Full detail (all 8 content shapes A/A'/A''/B/C/D/F/H, per-manual breakdown, the base_i resolution
narrative) lives in `local_memory/NOTES.md` in the repo — read that file rather than duplicating it
here.

## CATALOGUE CLOSED (2026-08-11): final tool verdict + version-stability check across all 9 manual folders

Redid the sampling systematically across the full, now-final inventory of 9 manual folders (base_i
x2, base_ii x5, vss x2), explicitly comparing oldest vs. newest edition per family via regex
signature counts (field-card pattern, position-grid pattern, fixed-width-report pattern) to answer
two questions: does the content-shape pattern hold stable across editions within a family (so it
doesn't need to be re-verified per version), and does extraction need one tool or two across all
families.

**Stability result:** in every one of the 9 families, the pattern signature counts stay in the same
order of magnitude between the oldest and newest edition (growing roughly proportionally with total
page count, never appearing/disappearing). **Conclusion: the parsing pattern is a property of the
manual family, not of the specific version** — no need to check every edition individually, one
parser per family/content-shape applies unchanged across all its editions.

**Final tool verdict:** `fitz.get_text()` (raw PyMuPDF text) is sufficient as the SOLE extraction
tool across all 9 manual folders / 8 content shapes (A/A'/A''/B/C/D/F/H). No second tool, no
Docling needed. This is now the closed, final recommendation — supported by: `pymupdf4llm` table
reconstruction confirmed to have 2 distinct data-integrity defects on 2 different manuals (dropped
row on Type B, fragmented-row-into-two-fake-rows on Type A'); `pdfplumber.extract_tables()` fails on
every borderless table tested (both "lines" and "text" strategies produce broken/merged columns);
`fitz.get_text()` had zero failures across every content type tested (A, A', B, D confirmed
directly; C and F inferred low-risk since they're not gridded tables). What varies per manual is
only the downstream regex parsing pattern per content shape, never the extraction tool.

**Next step (not started):** design the Stage 1/2 parser — uniform extraction via
`fitz.get_text()` (ideally `page.get_text("blocks")` to retain page+bbox per block for
provenance/cross-page-table-merging later), then a block classifier by content shape
(A/A'/A''/B/C/D/F/H), then a shape-specific regex parser per type — starting with Type A (the
project's central target), using the real `151-168 Reserved` example from
`base_ii_clearing_interchange_formats_tc_01_to_tc_49` as the reference test case.

Full detail (per-family stability table, final 9-manual catalogue table) lives in
`local_memory/NOTES.md` in the repo.
