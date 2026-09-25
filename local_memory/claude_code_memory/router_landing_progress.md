---
name: router-landing-progress
description: "poc/router/ — thin CLI orchestrator over the 8 existing pipelines, plus a landing/type-detection feature to auto-classify and onboard a new edition pair into the corpus"
metadata:
  type: project
  modified: 2026-09-05T17:11:33.552Z
---

Built and validated in one session (2026-09-03): the first version of the **production router**
the user raised on 2026-08-20 ("router delgado → 8 pipelines bespoke, infra compartida mínima"),
plus a follow-up feature the user asked for in the same session — automatic manual-type detection
for a "landing" folder. Both live under `poc/router/`, additive only — **zero changes to any of
the 8 existing bespoke pipeline scripts**.

## Scope negotiated before building (via AskUserQuestion, don't re-litigate without asking again)

1. Wrap the existing POC pipelines as-is, don't rewrite them.
2. Shared infra = orchestration/CLI only for this round — explicitly NOT the Ollama client
   (duplicated in 8 `classify.py`), NOT low-level extraction utilities (`_split_line_segments`
   and similar, today copied by hand between manuals — see [[pending-bug-fixes]] items 14/17),
   NOT a shared report layer. All three remain deliberately deferred to a later round.
3. Landing: filename-based detection first, PDF-content fallback second; on match, move the
   PDFs into the permanent corpus (`visa/src/...`) and run the full pipeline there (not an
   isolated/staging run); on mismatch or unidentifiable, alert only (console + persistent file),
   never process, never touch the input files.

## `poc/router/run.py` — orchestrator

Key finding that shaped the whole design: inspected `main()` across all 48 entry points (8
manuals × 6 stages) and found a **de-facto uniform contract already existed**, undesigned —
every stage script runs with zero positional args (except `classify.py`'s optional
`--limit=`/`--only=`), resolves all I/O via `Path(__file__).resolve()...` (CWD-independent), and
follows an identical `NN_<name>/` folder convention with exactly one `*.py` per stage dir. This
meant the router didn't need per-manual interface adapters — it just discovers stages by glob
(`poc/<slug>/[0-9][0-9]_*/`) and invokes them as subprocesses in order via `subprocess.run`
(stdout/stderr inherited live, not captured — matters for progress visibility; needed
`flush=True` on the router's own print statements, otherwise Python's stdout buffering when
piped reorders the router's own status lines after the subprocess's already-flushed output).

CLI: `python3 poc/router/run.py <manual_slug|all> [--from NN] [--to NN] [--skip-ai] [--only PAIR]
[--limit N] [--list]`. `--only`/`--limit` are passthrough to stage 05 only (documented as NOT a
blind passthrough — today only that stage accepts flags). On a manual's stage failure, the chain
for that manual stops; in `all` mode, other manuals still run, with a pass/fail summary at the
end. `MANUALS` dict (slug → display title, copied from each manual's `report.py` `MANUAL_TITLE`
constant) is the only per-manual registry — everything else (stage list, script names) is
discovered dynamically, not hardcoded, so an added/removed stage in any manual doesn't require a
router change.

**Verified end-to-end**: a byte-identical-output check for one manual's stages 01-02 vs. their
pre-existing output, and a full `all --skip-ai` run across all 8 manuals (2m32s, 8/8 OK, zero
`.py` files touched other than the new `poc/router/` ones).

The full contract is written up in **`poc/router/CONTRACT.md`** — read that (not this memory)
for the authoritative, current rule list; this memory is a narrative pointer, not the spec.

## `poc/router/land.py` + `detect_type.py` — landing / auto-detection

User's ask: a folder where a pair of PDFs (old + new edition) lands, the system figures out
which of the 8 known manuals they belong to, and refuses to process (alert-only) if they're
different types or unidentifiable. Two follow-up rounds of user pushback shaped the final
design — both are worth remembering because they changed real decisions, not just wording:

1. **First pushback**: worried the design implied some manual "couldn't" be identified. Root
   cause was under-communicated validation scope, not a real gap — content-based detection was
   tested against the real cover-page text of the **newest edition of all 8 manuals** (not a
   partial sample), including deliberately the 2 near-duplicate title pairs (TC 01-49 vs TC
   50-92, VSS Volume 1 vs Volume 2) that carry the most collision risk. All 8 pass. Clarified
   the real distinction: "not one of our 8 manuals" (expected, correct to alert) vs. "looks like
   one of the 8 but ambiguous" (should be rare, is the actual risk surface).
2. **Second ask**: user wanted it explicit that a future unrecognized edition isn't a dead end —
   confirmed the fix path is NOT touching the router or any pipeline, it's either (a)
   `--manual SLUG` to bypass detection immediately with zero code change, or (b) adding a new
   accepted title string to that manual's entry in `TITLE_VARIANTS` (a list, not a single
   string, specifically designed as the low-friction extension point for this exact scenario).

**Detection algorithm, validated against real data before committing to it (found and fixed 2
real edge cases empirically, not assumed)**:
- Real PDF filenames and cover-page text do NOT reliably preserve the exact word order or
  punctuation of each manual's registered `MANUAL_TITLE`. Found 2 concrete counter-examples
  while sampling real PDFs with `fitz`: the international base_i manual's real filename has
  "International" moved to the FRONT (`"...International - Full Service POS Online Messages
  Processing Specifications.pdf"`) while `MANUAL_TITLE` has it at the end in parens; the edit
  package messages manual's real filename carries an extra unregistered suffix
  (`"...(Reference Guide - Release 4).pdf"`). A naive substring/exact-order match would have
  failed both.
- Fix: normalize both sides to a **set of words** (lowercase, non-alphanumeric → space, split)
  and require **subset containment** (`normalize(title) <= normalize(candidate)`), not equality
  or ordered substring. This tolerates reordering, extra surrounding words, and line-wrap
  newlines in cover-page text, while staying safe against the near-duplicate title pairs — a
  subset check requires every distinguishing token (`01`/`49` vs `50`/`92`, `1`/`specifications`
  vs `2`/`reports`) to be literally present, so cross-matching between siblings can't happen by
  partial-credit fuzziness the way a similarity-score approach could have.
- If filename-based matching gives 0 or >1 candidates, fall back to scanning the first 3 pages'
  text the same way; if still 0 or >1, `slug=None` (unidentified) — ambiguity is never resolved
  by picking arbitrarily.

**Flow**: exactly 2 PDFs required in the inbox; each must parse an 8-digit `edition_date` from
its filename (same convention `ingest.py` already relies on — `stem.split(" - ")[0]`); same-date
pair rejected; on a same-slug match, PDFs are moved (not copied) into the corpus dir (resolved by
glob over `visa/src/*/<slug>/`, not hardcoded per-family path, since the family — base_i/base_ii/
vss — differs per manual) under the normalized name `<date> - <MANUAL_TITLE>.pdf`; an
already-present same-hash edition is skipped (no duplication), a same-date-different-content
conflict aborts the whole landing with nothing moved (all-or-nothing, never partially onboard a
pair); then `run_manual()` from `run.py` is reused as-is (no orchestration logic duplicated)
for the full pipeline; finally the specific `{old}_to_{new}.md` report is located and pointed to,
or — if an existing corpus edition already sat between old and new, so no direct pair exists —
the real chain of intermediate pair-reports is listed instead of pretending a direct one exists.

**Verified end-to-end** (see this session's transcript for exact runs, not re-detailed here):
happy path with 2 real adjacent editions (identical-hash skip correctly prevented corpus
duplication, full pipeline ran, correct pair report located); mismatched-manual pair (alert
written, both files left untouched, zero processing); genuinely unidentifiable pair (garbage
PDF content, fast alert, no pipeline triggered). One self-caught mistake during testing: ran
`land.py` once without `--skip-ai` on a test pair already satisfied by the identical-hash-skip
path, accidentally kicking off a real (redundant, slow) Ollama classification run — killed it
once noticed; harmless (classify.py's writes are whole-file, no partial corruption) but a
reminder to default test invocations to `--skip-ai` unless the AI stage itself is what's being
tested.

**Deliberately out of scope this round** (not asked for, not built): a "single new edition vs.
already-in-corpus history" landing mode (user specifically asked for the pair-at-a-time flow);
touching `run.py` or any bespoke pipeline script (both new files are purely additive); content-
shape/structural signatures as a detection signal (rejected during design — doesn't discriminate
within a manual family, e.g. the 2 TC manuals share the exact same table shape, only title text
differs).

Full rule-list documentation lives in **`poc/router/CONTRACT.md`** (section "Landing") —
authoritative and current; this memory explains the reasoning/history behind it.

**Why this file exists separately from [[dev-phase-considerations]]**: that memory is
forward-looking architectural *notes* not yet acted on; this one is a completed, verified,
in-repo deliverable — the first real progress on the "next major undertaking" line that memory
file used to end with. Update or remove this memory if `poc/router/` gets substantially
redesigned rather than incrementally extended.

**How to apply**: before extending `poc/router/`, read `CONTRACT.md` first (current source of
truth for the rules), and check the "out of scope this round" list above before assuming a
feature (Ollama consolidation, single-edition landing, etc.) doesn't exist yet — it was a
deliberate deferral, not an oversight.

## PENDING (as of 2026-09-03, not done yet)

**Still needs a full real end-to-end run through the router/landing flow, start to finish, with
real editions** — not done this session, user had to leave. What exists so far was verified
piecemeal (byte-identical-output checks, `all --skip-ai` across all 8 manuals, landing tested
with copies of already-in-corpus editions to stay non-destructive, one deliberately garbage/
unidentifiable pair, one deliberately mismatched pair). None of that is the same as actually
landing a genuinely new pair start-to-finish (including the AI classification stage, not
skipped) and confirming the whole thing end-to-end the way a real future use would. Do this next
session before considering `poc/router/` done — pick a manual with a due/plausible next edition,
or otherwise construct a realistic (non-synthetic) full run, including stage 05 with Ollama
actually up.

## RESOLVED 2026-09-04: real end-to-end run done, found and fixed a real `land.py` bug

Did the pending run above for real: temporarily pulled the 2 newest real editions of **VSS
Volume 2** (`visanet_settlement_service_vss_user_guide_volume_2_reports`, chosen for having the
fewest Módulo 5 items among the 8 manuals) out of the corpus into `poc/router/landing/inbox/`
(actual `mv`, not copies — backed up both the PDFs and the manual's whole `data/` dir first,
since this repo has no git), then ran `python3 poc/router/land.py` for real, Ollama (`qwen3:4b`)
actually up, no `--skip-ai`.

**Bug found by the user mid-run, not by me**: the user asked "how does this actually work" while
it was churning through the *oldest* pair (`20220423_to_20221014`) with real AI calls, and
pointed out the intent was always "land 2 new editions → run their pipeline → AI contrasts only
those two JSONs" — not "recompute the AI classification for the manual's entire pair history
every time a new edition lands." That's exactly what was happening: `land.py` called
`run_manual(slug, None, None, args.skip_ai, None, None)` — the 5th arg (`only`) was hardcoded
`None`, so stage 05 reprocessed all 6 historical pairs (put it at 174 AI items into pair 1 of 6
before being killed) instead of just the newly-landed one. This was a real bug in `land.py`, not
a misunderstanding of intended scope — `run.py`'s `--only` passthrough to stage 05 already
existed and was already documented in `CONTRACT.md` for exactly this use case, `land.py` just
never used it.

**Fix** (`poc/router/land.py`, in `main()`): compute
`only = f"{dates[old_pdf]}_to_{dates[new_pdf]}"` and pass it as the 5th arg to `run_manual()`
instead of `None`. One line. Confirmed before fixing that stages 01-04 are cheap/deterministic
(no Ollama, a few seconds for the whole corpus) so leaving them un-scoped is fine and not worth
touching — only stage 05 (the expensive, AI one) needed the fix, and `--only` was designed
specifically for this.

**Re-verified after the fix**, same real PDFs, restored `data/` from backup first to discard the
killed run's partial recompute: stage 05 now only printed progress for
`[20250412_to_20251017] 1/13` .. `13/13` (the actual landed pair), left the other 5 pairs'
`05_interpretacion_cambios_ia/*.json` byte-identical to the pre-experiment backup (`diff -rq`
confirmed), stage 07 regenerated all 6 `.md` reports but only the landed pair's content actually
changed. Diffed that pair's report against the pre-experiment version: same 9 "cambios de
negocio", same finding set — the only deltas were one AI-phrasing variation of an identical
finding (LLM wording nondeterminism, same underlying business-rule change) and a reordering
(not a content change) of the extraction-noise warning bullets. Confirms the scoped-down run is
functionally equivalent to the old full-recompute one, just fast. Corpus and inbox both back to
clean state after (7 PDFs in corpus, empty inbox, no alerts written). `CONTRACT.md` updated with
a new paragraph under the Landing section documenting this behavior.

**Why this matters for [[dev-phase-considerations]]**: this was a real, load-bearing bug (10-100x
more Ollama calls than necessary on every future landing, for a POC where each pipeline is
manually re-run rarely, but would matter a lot at any real cadence) that had shipped as
"verified end-to-end" the previous session — the piecemeal verification (byte-identical checks,
`--skip-ai` runs) never exercised the with-AI code path enough to catch it. Reinforces: a
component that calls an LLM needs at least one real, un-skipped run before calling it done, not
just a dry run plus code review.

**`poc/router/` is now genuinely done** for this round's scope (see "out of scope this round" list
above, unchanged — Ollama client consolidation, single-edition landing mode, etc. still
deliberately deferred).

## 2026-09-04, continued: clarified operational flow + confirmed a real gap (multi-pair landing)

User asked, reasonably, whether dropping 2 *pairs* (4 PDFs, potentially 2 different manual
types) in the inbox at once would get auto-detected and routed to 2 pipelines. Checked
`land.py`: no — it hard-requires `len(pdfs) == 2` in the inbox, so 4 files triggers the
"wrong count" alert path, not per-type grouping. This is a real, confirmed gap (not built), not
a misunderstanding — `detect_type.py` itself would generalize fine to N loose PDFs, but `land.py`
has no grouping logic before the count check. Deliberately not fixed this session (not asked to
build it, just to document the boundary).

Also clarified with the user: Módulo 8 (`poc/08_reporte_web_consolidado/build.py`) is NOT
triggered by `land.py`/`run.py` — stays a fully separate, manually-invoked step (per
`CONTRACT.md`'s pre-existing "Qué NO es parte del contrato" section). Recommended workflow when
several manuals land the same day: call `land.py` once per pair (draining/refilling the inbox
each time), and only call `build.py` once, after the last landing of the day — not after every
single `land.py`, since `build.py` has no incremental mode (always rebuilds the consolidated
view from scratch off the 8 manuals' latest pair) and would just redo the same rebuild N times
for N same-day landings. User agreed with this framing.

**Both now documented in `poc/router/CONTRACT.md`** under a new "Flujo operacional recomendado"
section: the exactly-2-PDFs-per-run constraint and what NOT to do (dumping multiple pairs at
once), the recommended per-day sequence (land each pair → drain inbox → repeat → `build.py` once
at the end), the reasoning for not auto-triggering `build.py`, and a short forward-looking note
on what multi-pair-at-once landing would need if ever built (grouping by detected type before
the count check, one `run_manual()` call per resulting group).

## RESOLVED 2026-09-06: multi-pair landing built, closing the gap above

User asked to build exactly what the 2026-09-04 note above sketched as the extension path.
Before implementing, one real design decision wasn't already settled by prior negotiation and
needed asking: if the inbox has several groups and ONE of them is malformed (wrong PDF count,
same-date pair, unidentified PDF), should the well-formed groups still process, or does the
whole batch get rejected together? Asked directly (`AskUserQuestion`) — user chose **todo o
nada sobre el lote completo**, explicitly for consistency with the rest of the project's
established all-or-nothing pattern (same principle already used for the same-hash-conflict
check), over the more operationally convenient "process the valid ones, alert only the bad
one."

**Implementation** (`poc/router/land.py`, full rewrite of `main()`, ~230 lines): no longer
requires exactly 2 PDFs in the inbox — detects every PDF's type (or applies `--manual` to all
of them uniformly, which naturally degrades to the old single-pair behavior when there are only
2), groups by detected slug, then validates that EVERY group has exactly 2 PDFs with 2 distinct
dates. Any single violation (bad group size, same-date pair within a group, an unidentified
PDF, or — checked before moving anything — a same-date-different-content corpus conflict in any
group) aborts the ENTIRE batch with one alert listing every group that had a problem; nothing
moves, not even the groups that were fine. Only if everything validates does it move all PDFs
of all groups (atomic for the whole batch, not per group) and then run each affected manual's
pipeline one at a time, scoped to its own new pair via `--only` (reusing the 2026-09-04 fix,
now applied per-group) — one manual's pipeline failure doesn't stop the others in the same
batch (same "other manuals still run" precedent as `run.py all`), reported per-manual at the
end. The `--manual SLUG` flag intentionally needed no special-casing for the multi-pair case:
forcing one slug onto 3+ PDFs just makes them one oversized group, which the existing
"exactly 2 per group" check rejects on its own — no new logic needed for that path.

**Verified with real (non-destructive) tests** — copies of already-in-corpus PDFs, so a
same-hash match means nothing actually gets moved, but the whole detection/grouping/validation/
pipeline-invocation path runs for real: (1) happy path, 2 valid pairs from 2 different manuals
(`base_ii_transactions_quick_reference` + `visanet_settlement_service_vss_user_guide_volume_2_
reports`) in the same inbox in one `land.py` call — both correctly grouped, both pipelines ran,
both pair reports located. (2) todo-o-nada rejection — same 2 manuals, but one group given 3
PDFs instead of 2 — confirmed the WHOLE batch rejected (including the otherwise-valid pair),
alert correctly named which group had the problem, 0 files moved from the inbox. (3) the
classic 2-different-manuals-in-1-pair case (the original single-pair mismatch scenario) still
alerts correctly, now phrased as "2 groups of size 1" rather than "manuales distintos" — still
clear, slightly different wording than before.

`CONTRACT.md`'s Landing section and "Flujo operacional recomendado" section both rewritten to
match — the old "land one at a time, drain the inbox between each" recommendation is gone,
replaced with "drop everything for the day in the inbox together, one `land.py` call handles
it all," while noting the true single-pair-at-a-time flow still works unchanged as the
degenerate 1-group case.

**`poc/router/` multi-pair landing gap is now closed.** (Low-level extraction utilities were
investigated 2026-09-06 — see the audit note there, turned out to need no changes.)

## DONE 2026-09-05: "single new edition vs. corpus history" landing mode

User asked to build the previously-out-of-scope mode: drop just 1 new PDF (not a pair) into the
inbox and have the system resolve the "old" side automatically against the corpus, instead of
requiring the user to supply both editions by hand every time.

**Implementation** (`poc/router/land.py`): a detected group can now have 1 OR 2 PDFs (was
strictly 2). New helper `_latest_corpus_edition(corpus_dir)` scans the manual's corpus directory
for existing `<date> - <title>.pdf` files and returns the max date, or `None` if the corpus has
no editions yet for that manual. Group-size-1 validation (same loop as the existing size-2 same-
date check, extended not replaced): reject if the corpus has zero prior editions ("primera carga
necesita el par completo") or if the new PDF's date isn't strictly newer than the latest corpus
edition ("no es mas nueva que la ya presente"); otherwise resolve `old_date` from the corpus and
proceed exactly like the pair flow from there (move the 1 PDF in, run the pipeline scoped via
`--only {old_date}_to_{new_date}`). The all-or-nothing batch principle (2026-09-06) is preserved
unchanged — a batch can freely mix pair-mode and single-edition-mode groups for different
manuals, each validated/resolved independently, but any single violation still rejects the whole
batch.

**Verified end-to-end, non-destructively** (VSS Volume 2, chosen for having the fewest Module 5
items among the 8 manuals — same manual used for the original router end-to-end test): backed up
the manual's `data/` dir and corpus dir to scratchpad first (no git in this repo). (1) Rejection
path: copied the corpus's newest real PDF (`20251017`) alone into the inbox unchanged — correctly
rejected with "la edicion 20251017 no es mas nueva que la ya presente en el corpus (20251017)",
0 files moved. (2) Happy path: copied that same PDF renamed to a fake future date (`20260419`,
same bytes so a real Ollama run would be pointless — ran with `--skip-ai`) — correctly detected
as a 1-group batch, printed "modo edicion unica: se compara contra la edicion 20251017 ya
presente en el corpus", moved the file into the corpus, ran the full pipeline (`--only
20251017_to_20260419`) across all 8 real editions plus the fake one, stages 03/04 showed 0 real
content diffs for that specific pair (expected — identical bytes under a different filename,
confirms the pipeline correctly treated it as a legitimate but unchanged edition). Cleaned up
after: removed the fake corpus PDF, restored `data/` from the backup, `diff -rq` confirmed both
corpus and data dirs are byte-identical to the pre-test state, removed the test's own alert file.

**Known pre-existing quirk surfaced by testing, NOT part of this change, not fixed**: with
`--skip-ai`, stage 07's report never gets generated for the landed pair (since it reads stage
05's output, which `--skip-ai` skips) — `land.py`'s final "no hay comparación directa" message
then fires and misleadingly suggests missing intermediate editions, when the real reason is
just that AI was skipped. This would happen identically for the classic 2-PDF pair flow under
`--skip-ai` too — unrelated to single-edition mode, not something this change introduced or was
asked to fix.

`CONTRACT.md`'s Landing section (point 3) rewritten to document both modes and that they can be
freely mixed within one batch. **This closes the last item that was explicitly logged as
"deliberately out of scope this round" — `poc/router/` has no more known deferred landing
features.**

## AUDITED 2026-09-05: report-layer consolidation (Módulo 7 + Módulo 8) — verdict: nothing worth
extracting

User asked to pick up the deferred "report-layer consolidation" item. **Módulo 8
(`poc/08_reporte_web_consolidado/adapters/`) turned out to already be consolidated** — built
2026-08-27 with a shared `_common.py` (`make_item`/`make_group`/`top_items`/`short_name`) used by
all 7 adapters, plus the 2 grid manuals already sharing one `interchange_formats_grid.py`. The
"not yet audited" framing in the pending-item note was itself stale — this had already been done
at build time, just never explicitly logged as "audited and confirmed."

**Módulo 7** (`poc/<manual>/07_reporte_cambios/report.py`, 8 manuals, 228-333 lines each):
measured real duplication before proposing any change (same discipline as the Módulo 1/4/5 Tier 1
work). Found 3 byte-identical (hash-confirmed) fragments across all 8: `_fmt_date()`, the
`input_paths = glob(...); exit if empty` block, and the `index.md` header+write block — combined
~60-70 of ~2300 total lines (~3%). Everything else — `main()`'s per-pair summary-line computation
and every `_render_*` function — is genuinely bespoke: different grouping key per manual
(table/code/hierarchical-path/appendix+table), different vocabulary ("cambios de negocio" vs.
"cambios de TCR"), some needing a side lookup others don't (`_title_by_code` in manual 2). Same
shape-but-genuinely-different-content pattern already established for `classify.py`'s `main()`
(never extracted, for the identical reason). **Key difference from the Módulo 1/4/5 round**: that
extraction was justified by TWO things together — real duplication AND a live bug hiding in it
(the un-ported "replace opcode" fix). Here there's no divergent-fix bug in the 3 duplicated
fragments — pure mechanical duplication, zero correctness payoff. One cosmetic-only finding
(not a bug): the `safety_net_override` ⚠️ flag's wording has 2 variants — 2 manuals say "la IA lo
clasifico distinto; se corrigio por contenido desaparecido", the other 5 just "corregido por
contenido desaparecido" — no behavior difference.

**User's call, presented with the tradeoff via `AskUserQuestion`: leave Módulo 7 as-is.**
Explicitly declined the extraction given the weak cost/benefit (churn across 8 files for ~3% LOC
reduction, no bug prevented) — this closes the "report-layer consolidation" line item as
*audited and deliberately left alone*, not as an oversight or a "still to do."
