---
name: module8-web-report
description: "Module 8 consolidated web report (poc/08_reporte_web_consolidado) — design, adapter pattern, how to regenerate"
metadata: 
  node_type: memory
  type: project
  modified: 2026-09-10T02:27:08.680Z
---

Built 2026-08-27, at the user's request: a new **Módulo 8** (`poc/08_reporte_web_consolidado/`)
that consolidates the LATEST edition-pair of all 8 manuals into one self-contained local HTML
page with tabs (a "Resumen general" tab with counts + top-3 highlighted business changes per
manual, plus one detail tab per manual with the full grouped business-change list) — so the
user doesn't have to open 8 separate `.md` files from each manual's own Módulo 7 to see current
state.

**Key finding that shaped the design** (confirmed via a full read of all 8 manuals' `07_reporte_
cambios/report.py` before writing any adapter code): the 8 manuals' Módulo 5 JSON schemas are
genuinely NOT uniform — different `change_type` names, different identifier fields (`code`/
`position`/`key`/none), different grouping keys (`table`/`path`/`(title,signature)`/
`(appendix,table_title)`), and one manual (`base_ii_transactions_quick_reference`) has no
`ai_category` concept at all (Módulo 5 is a deliberate no-op there). This directly echoes
[[dev-phase-considerations]]'s "bespoke-parsers-vs-framework" note. **Design consequence**:
Módulo 8 is NOT a generic parser — it's 7 small per-manual adapter files under `adapters/`
(the 2 grid manuals, TC 01-49 and TC 50-92, share one `interchange_formats_grid.py` since
their schema really is identical) each exposing `summarize(data, manual_dir, pair_filename) ->
dict`, normalizing to a common shape: `{edition_a, edition_b, headline, secondary, groups,
top_items}`. `headline`/`secondary` deliberately use each manual's OWN native vocabulary
("Cambios de negocio a revisar" vs. `quick_reference`'s "Cambios de TCR") rather than forcing a
fake uniform label. `top_items` = first 3 items in existing grouping order — no invented
importance score, documented as a POC simplification.

**Output**: `poc/08_reporte_web_consolidado/data/index.html` — fully self-contained (no
`fetch()`, JSON data embedded as base64 in an inline `<script>`, decoded via
`TextDecoder`/`atob` to survive Unicode/accents safely) so it opens with a plain double-click,
no local server needed. Also writes `data/reporte_consolidado.json` (the normalized
intermediate, useful for debugging/reuse). Regenerate anytime with
`python3 poc/08_reporte_web_consolidado/build.py` (stdlib only, no new dependencies) — it always
picks each manual's latest `data/05_interpretacion_cambios_ia/*.json` by filename sort.

Verified against known cases before considering it done: `base_ii_clearing_data_codes`'s
Bulgaria/Croatia business changes render with full old/new text; `base_ii_transactions_quick_
reference` (no `ai_category`) correctly shows its own TCR-count metric instead of a broken/empty
"cambios de negocio" section, including its existing rename-suspicion flag; the grid manuals'
"Reserved → definido" transitions group renders first, ahead of generic business changes, as the
project's central use case; all 8 headline counts matched their existing `07_reporte_cambios/
index.md` numbers exactly.

**Scope not covered** (explicitly out per the plan approved with the user): no historical-pair
selector per manual (latest pair only, per user's explicit choice when asked); no production
router — this is POC tooling for Módulo 7's output, unrelated to the router/interface-contract
design mentioned in [[pending-bug-fixes]]'s "not yet started" line.

**DONE (2026-09-05): "Cambios recientes" tab, closing the two-phase landing/publish idea.**
User proposed a two-phase model (Phase 1 = land PDF pairs via the router, as many times as
needed; Phase 2 = generate this web report as an "announcement"). Phase 1 already worked as
described (each manual's `05_interpretacion_cambios_ia/` latest-pair-by-filename logic already
means Módulo 8 only ever shows the most recent comparison per manual, no historical pile-up).
For Phase 2, considered reordering "Resumen general" to surface recent changes first, but the
user preferred (after discussion) a **dedicated new tab** so the existing Resumen/per-manual tabs
stay untouched. Implemented: `build.py` persists `data/estado_publicacion.json` (per-manual
`edition_a`/`edition_b` of the last-published pair) and tags each manual's summary with
`is_new_since_last_publish`; **each `build.py` run IS the publish event** — it compares against
the state left by the previous run, then overwrites the state with the current pairs. First-ever
run (no state file) treats all 8 manuals as new. `template.html` gets a new "Cambios recientes
(N)" tab, now the default landing tab, showing full detail (not just compact cards) for only the
flagged manuals, with a "ningún manual nuevo" empty state. Resumen general and the 8 per-manual
tabs are byte-for-byte unchanged. Verified end-to-end: first run flagged 8/8 new, an identical
re-run flagged 0/8, and a simulated stale-state test correctly isolated exactly 1/8 as new before
self-healing the state back to a clean baseline on the next run.

**DONE (2026-09-09): per-manual state files, replacing the single shared `estado_publicacion.json`.**
Came up while walking the user through the README's usage scenarios: they wanted to simulate a
fresh landing of one manual's latest edition (as if it had never arrived) to rehearse the
production flow, and asked how to reset just that manual's "recent changes" flag. Found that the
single shared file meant `previous_state.get(slug)` returned `None` for ALL 8 slugs if the file
was simply deleted — resetting one manual's memory forced all 8 to show as new. User asked how
hard a per-manual split would be (assessed as small/contained — grep confirmed nothing else in
the repo depends on the file's path/shape) and asked to implement it. **Change**: `build.py` now
persists `data/estado_publicacion/<slug>.json` (one file per manual) instead of one shared
`data/estado_publicacion.json`. `_load_previous_state()` reads the new directory if present;
if not, falls back to the old single file (so upgrading doesn't force all 8 manuals to appear
"new" at once). `_write_state()` writes the 8 new files and deletes the legacy file if still
present — migration is automatic and happens on the first run with the new code. **Verified**
against the real corpus: (1) a run with the legacy file still present migrated cleanly, 0/8 new
(nothing had actually changed) and deleted the legacy file; (2) an identical re-run gave 0/8
(idempotent); (3) manually deleting only `base_ii_transactions_quick_reference.json` caused
exactly that 1/8 to show `[NUEVO]` on the next run, the other 7 untouched. `poc/README.md`
section 7 updated with the new path and the "delete one manual's file to force-test it" use case.
Full narrative in `local_memory/NOTES.md`, 2026-09-09 entry.

**DONE (2026-09-24): clickable pills with detail.** Every secondary pill in all 8 adapters is now
built via `_common.make_pill(label, details)` (value = len(details)); `template.html` renders
non-zero pills as buttons opening a grouped detail panel. Verified counts/headline/groups
unchanged vs. prior JSON. Not browser-tested (no headless browser in env). Grid manuals'
loose `row/card_added/removed` still have no pill of their own — possible follow-up.
Full note in `local_memory/NOTES.md`, 2026-09-24 entry.
