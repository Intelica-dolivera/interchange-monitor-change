---
name: project-overview
description: Purpose of interchange_change_monitor and how it maps to the reference guides pipeline in utils_example
metadata: 
  node_type: memory
  type: project
  modified: 2026-08-13T21:56:54.755Z
---

The project's goal is to analyze VISA (and eventually Mastercard) technical manuals in PDF —
`base_i`, `base_ii`, `vss` — to detect version-to-version differences in file/message field
definitions. Concretely: if a manual edition says a file has 20 fields (18 defined + 2 reserved),
and the next edition shows 19 defined fields, the system must detect that one reserved field
became a newly-defined field (not just treat it as a generic "added field"). Other change types:
new fields, changed field values/definitions, fields that stop being defined (become reserved/removed).

Manuals live under `visa/src/{base_i,base_ii,vss}/<manual_name>/<YYYYMMDD> - <Title>.pdf`, multiple
dated editions per manual (date in filename = version). `mastercard/` exists but is currently empty
(future scope, not yet started).

Final manual inventory (9 folders, as of 2026-08-11, after `base_i` gaps were resolved — see
[[open-questions-technical-manuals]] for how): `base_i` has 2 folders — a narrative "Processing
Specifications" manual (no field-layout tables, process/message-flow prose only) and a technical
folder containing 2 manuals with the real field/byte-layout content (`VisaNet Authorization-Only
Online Messages Technical Specifications`, 1 edition, and `Full Service POS Online Messages
Technical Specifications`, 8 editions). `base_ii` has 5 folders (clearing_data_codes,
clearing_edit_package_messages, clearing_interchange_formats_tc_01_to_tc_49,
clearing_interchange_formats_tc_50_to_tc_92, transactions_quick_reference). `vss` has 2 folders
(volume_1_specifications, volume_2_reports). A wrong/incomplete `base_i` manual
(`authorization_only_online_messages_processing_specifications_International`) was deleted from the
repo after this was confirmed.

**Why:** A separate team already built a working proof-of-concept pipeline for a related but
different document type — "Interchange Guides" (Visa/Mastercard fee-rate rule documents) — shared
in `utils_example/` (`02_guide_parser.py`, `05_diff_descriptors.py`, `06_classify_changes.py`; stages
01/03/04 were not shared but are inferable from the input/output filenames referenced).

**How to apply:** Use the reference pipeline as an architectural starting point, but do not assume
a 1:1 code reuse — the domain entities are different (see [[reference-pipeline-vs-technical-manuals]]).
When resuming this project, start by re-reading [[open-questions-technical-manuals]] for exactly
where the conversation left off.

**Status (2026-08-13):** the core reserved→defined use case described above is no longer
theoretical — it's been validated end-to-end with real data in
`base_ii_clearing_interchange_formats_tc_01_to_tc_49` (Type A), the manual with real byte-level
Position/Length/Format/Contents grids. 3 manuals now have a full validated POC pipeline (Modules
1-5, 7): `base_ii_clearing_data_codes` (Type B, code lookup tables), `base_ii_clearing_edit_package_
messages` (Type F, validation/log message fichas), and this Type A one. See
[[open-questions-technical-manuals]] for full module-by-module detail on all 3.
