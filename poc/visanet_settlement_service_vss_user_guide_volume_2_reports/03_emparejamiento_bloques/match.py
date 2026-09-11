"""
Modulo 3 - Emparejamiento de bloques para el manual
visanet_settlement_service_vss_user_guide_volume_2_reports.

A diferencia de los otros manuales (una jerarquia de secciones L1>L2>L3 unica para todo el
documento), este manual se procesa POR APENDICE de forma independiente -Modulo 1 y 2 ya
mantienen esa separacion, y no hay ninguna relacion de matching entre bloques de apendices
distintos (un `grid_row` del Apendice B nunca deberia poder emparejar con uno del Apendice C).

**Clave de tabla: `(appendix, table_title)`, exacto + fallback fuzzy (0.85, mismo umbral que
el resto del proyecto).** `table_title` ya viene redeclarado en CADA `grid_row` desde Modulo 2
(bold 10.5pt en horizontal, mismo tamano rotado) -mismo principio de "el titulo se
re-declara por pagina, se usa como identidad de tabla" ya establecido en los manuales de
grilla (Tipo A) y en el 7mo manual.

**Clave de fila dentro de una tabla: valor normalizado de `row["columns"][row["anchor_column"]]`,
EXACTO, con desempate por orden de aparicion para claves repetidas dentro de la misma tabla**
-mismo mecanismo ya usado 3 veces en el proyecto (TC 57 del 4to manual, filas TCR del 5to,
`field_description_pair` del 7mo). Investigado con datos reales antes de decidir (ver
[[manual8-vss-vol2-progress]] en la memoria del asistente): la columna ancla SI tiene
duplicados reales dentro de varias tablas (hasta ~33% de las filas en el Apendice E, donde
"Transaction Description" puede repetirse para distintas variantes de Additional Data de un
mismo TC) -el desempate por orden es necesario, no un caso raro. Sin fallback fuzzy sobre la
clave de fila -mismo riesgo ya demostrado inseguro con etiquetas cortas en el 5to manual, no
se re-investiga aca.

**Encabezados de seccion (`section_heading`) y parrafos**: tratados como contexto liviano, NO
como el corazon del diffing (eso es `grid_row`, el "campo/posicion" real que le importa a este
proyecto). Encabezados: exacto + fuzzy por texto dentro del apendice. Parrafos: exacto
solamente (mismo criterio de baja prioridad ya aplicado a prosa boilerplate en otros
manuales -aca son mayormente oraciones "Esta tabla contiene..." de bajo valor).

Alcance: procesa pares de ediciones CONSECUTIVAS (6 pares para las 7 ediciones de este manual).
"""

import difflib
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

MANUAL_SLUG = "visanet_settlement_service_vss_user_guide_volume_2_reports"
INPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "02_normalizacion_bloques"
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "03_emparejamiento_bloques"

APPENDICES = ["appendix_a", "appendix_b", "appendix_c", "appendix_d", "appendix_e"]

WHITESPACE = re.compile(r"\s+")
FUZZY_TABLE_THRESHOLD = 0.85
FUZZY_HEADING_THRESHOLD = 0.85


def _norm(text: str) -> str:
    return WHITESPACE.sub(" ", text or "").strip().casefold()


def _find_duplicates(values) -> list:
    seen = {}
    dups = set()
    for v in values:
        seen[v] = seen.get(v, 0) + 1
        if seen[v] > 1:
            dups.add(v)
    return sorted(dups)


NOTE_PREFIX = re.compile(r"^note:\s*", re.IGNORECASE)


def extract_tables(blocks: list) -> dict:
    """Agrupa los `grid_row` de un apendice por titulo de tabla normalizado. Cada fila
    conserva su `anchor_column` (ya calculado en Modulo 2) para derivar su clave de
    emparejamiento sin tener que re-adivinarla.

    **Bug real encontrado en validacion (2026-08-19, ver [[manual8-vss-vol2-progress]])**: en
    las ediciones 20220423-20230415, la MISMA tabla real (ej. V22225) queda partida en 2
    titulos por una inconsistencia genuina del PDF fuente -una pagina declara "Note: Financial
    Transaction Record 4-V22225" mientras su pagina de continuacion declara el titulo plano
    sin el prefijo "Note: ". Se probo primero coalescer por fuzzy-similaridad entre titulos de
    una misma edicion, pero se descarto: el mismo umbral (0.85) que hace falta para esto
    tambien fusionaria tablas REALMENTE DISTINTAS (confirmado real: "Financial Transaction
    Record 4-V22225" vs "...Record 5-V22226" da 0.895, arriba del umbral). Confirmado que el
    prefijo real es siempre, y unicamente, un `"Note: "` literal (2 titulos base afectados, 3
    ediciones, ver commit) -se quita ese prefijo especifico al normalizar el titulo en vez de
    usar fuzzy matching, evitando el riesgo de sobre-fusion."""
    tables = defaultdict(lambda: {"rows": [], "title_raw": None, "title_raw_is_clean": False})
    for block in blocks:
        if block["type"] != "grid_row":
            continue
        raw_title = block["table_title"] or ""
        is_clean = not NOTE_PREFIX.match(raw_title.strip())
        title_norm = _norm(NOTE_PREFIX.sub("", raw_title))
        entry = tables[title_norm]
        entry["rows"].append(block)
        # Titulo canonico mostrado: preferir la variante SIN el prefijo "Note: " si aparece en
        # cualquier pagina de la tabla; si nunca aparece, usar la primera vista (con prefijo).
        if entry["title_raw"] is None or (is_clean and not entry["title_raw_is_clean"]):
            entry["title_raw"] = raw_title
            entry["title_raw_is_clean"] = is_clean
    for entry in tables.values():
        del entry["title_raw_is_clean"]
    return dict(tables)


def _row_key(row: dict) -> str:
    cols = row["columns"]
    if "__unassigned_prefix__" in cols:
        return "__unassigned_prefix__"
    anchor = row.get("anchor_column")
    return _norm(cols.get(anchor, "")) if anchor else _norm(next(iter(cols.values()), ""))


def match_tables(tables_a: dict, tables_b: dict) -> dict:
    matched = []
    unmatched_a = dict(tables_a)
    unmatched_b = dict(tables_b)

    # sorted() -mismo fix que match_headings/match_paragraphs mas abajo, ver su comentario y
    # [[dev-phase-considerations]] punto 9: iterar un set() de strings sin ordenar depende de
    # PYTHONHASHSEED, produce el mismo contenido en orden de lista distinto cada corrida.
    exact_titles = sorted(set(unmatched_a) & set(unmatched_b))
    for title in exact_titles:
        matched.append((unmatched_a.pop(title), unmatched_b.pop(title), "exact", 1.0))

    # Emparejamiento fuzzy por MEJOR similitud global, no por orden de procesamiento -antes
    # (greedy, cada title_a se quedaba con su mejor candidato DISPONIBLE en el momento en que
    # se procesaba) el resultado podia depender del orden de iteracion de unmatched_a -ver
    # [[dev-phase-considerations]] punto 9. Recolectar TODOS los candidatos por encima del
    # umbral primero y asignar en orden de similitud DESCENDENTE lo hace independiente del
    # orden de entrada.
    candidates = []
    for title_a in unmatched_a:
        for title_b in unmatched_b:
            ratio = difflib.SequenceMatcher(None, title_a, title_b).ratio()
            if ratio >= FUZZY_TABLE_THRESHOLD:
                candidates.append((ratio, title_a, title_b))
    candidates.sort(key=lambda c: -c[0])

    used_a: set = set()
    used_b: set = set()
    for ratio, title_a, title_b in candidates:
        if title_a in used_a or title_b in used_b:
            continue
        matched.append((unmatched_a[title_a], unmatched_b[title_b], "fuzzy", round(ratio, 3)))
        used_a.add(title_a)
        used_b.add(title_b)

    still_unmatched_a = {t: v for t, v in unmatched_a.items() if t not in used_a}
    tables_added = {t: v for t, v in unmatched_b.items() if t not in used_b}

    return {
        "matched": matched,
        "tables_removed": still_unmatched_a,
        "tables_added": tables_added,
    }


def match_rows(table_a: dict, table_b: dict) -> dict:
    by_key_a = defaultdict(list)
    for r in table_a["rows"]:
        by_key_a[_row_key(r)].append(r)
    by_key_b = defaultdict(list)
    for r in table_b["rows"]:
        by_key_b[_row_key(r)].append(r)

    matched = []
    removed = []
    added = []
    for key in set(by_key_a) | set(by_key_b):
        list_a = by_key_a.get(key, [])
        list_b = by_key_b.get(key, [])
        n = min(len(list_a), len(list_b))
        for ra, rb in zip(list_a[:n], list_b[:n]):
            matched.append({"key": key, "row_a": ra, "row_b": rb})
        removed.extend({"key": key, "row": r} for r in list_a[n:])
        added.extend({"key": key, "row": r} for r in list_b[n:])

    sort_key = lambda item: item["key"]
    return {
        "rows_matched": sorted(matched, key=sort_key),
        "rows_removed": sorted(removed, key=sort_key),
        "rows_added": sorted(added, key=sort_key),
        "duplicate_row_keys_a": _find_duplicates(_row_key(r) for r in table_a["rows"]),
        "duplicate_row_keys_b": _find_duplicates(_row_key(r) for r in table_b["rows"]),
    }


def extract_headings(blocks: list) -> list:
    return [
        {"level": b["level"], "text": b["text"], "text_norm": _norm(b["text"])}
        for b in blocks
        if b["type"] == "section_heading"
    ]


def match_headings(headings_a: list, headings_b: list) -> dict:
    by_text_a = defaultdict(list)
    for h in headings_a:
        by_text_a[h["text_norm"]].append(h)
    by_text_b = defaultdict(list)
    for h in headings_b:
        by_text_b[h["text_norm"]].append(h)

    matched = []
    unmatched_a = []
    unmatched_b = []
    # sorted() -bug de no-determinismo real, ver comentario de match_tables arriba y
    # [[dev-phase-considerations]] punto 9.
    for text_norm in sorted(set(by_text_a) | set(by_text_b)):
        list_a = by_text_a.get(text_norm, [])
        list_b = by_text_b.get(text_norm, [])
        n = min(len(list_a), len(list_b))
        for ha, hb in zip(list_a[:n], list_b[:n]):
            matched.append({"text_a": ha["text"], "text_b": hb["text"], "match_type": "exact"})
        unmatched_a.extend(list_a[n:])
        unmatched_b.extend(list_b[n:])

    remaining_b = list(unmatched_b)

    # Emparejamiento fuzzy por MEJOR similitud global, no por orden de procesamiento -mismo
    # fix y misma razon que `match_tables` arriba, ver su comentario y
    # [[dev-phase-considerations]] punto 9.
    candidates = []
    for i, ha in enumerate(unmatched_a):
        for j, hb in enumerate(remaining_b):
            ratio = difflib.SequenceMatcher(None, ha["text_norm"], hb["text_norm"]).ratio()
            if ratio >= FUZZY_HEADING_THRESHOLD:
                candidates.append((ratio, i, j))
    candidates.sort(key=lambda c: -c[0])

    used_a: set = set()
    used_b: set = set()
    fuzzy_match_for_a: dict = {}
    for ratio, i, j in candidates:
        if i in used_a or j in used_b:
            continue
        used_a.add(i)
        used_b.add(j)
        fuzzy_match_for_a[i] = (j, ratio)

    still_unmatched_a = []
    for i, ha in enumerate(unmatched_a):
        if i in fuzzy_match_for_a:
            j, ratio = fuzzy_match_for_a[i]
            hb = remaining_b[j]
            matched.append(
                {"text_a": ha["text"], "text_b": hb["text"], "match_type": "fuzzy", "similarity": round(ratio, 3)}
            )
        else:
            still_unmatched_a.append(ha)

    remaining_b = [hb for j, hb in enumerate(remaining_b) if j not in used_b]

    return {
        "headings_matched": matched,
        "headings_removed": [h["text"] for h in still_unmatched_a],
        "headings_added": [h["text"] for h in remaining_b],
    }


def extract_paragraphs(blocks: list) -> list:
    return [{"text": b["text"], "text_norm": _norm(b["text"])} for b in blocks if b["type"] == "paragraph"]


def match_paragraphs(paras_a: list, paras_b: list) -> dict:
    by_text_a = defaultdict(list)
    for p in paras_a:
        by_text_a[p["text_norm"]].append(p)
    by_text_b = defaultdict(list)
    for p in paras_b:
        by_text_b[p["text_norm"]].append(p)

    matched_count = 0
    removed = []
    added = []
    # sorted() -mismo bug, ver comentario de match_tables arriba y [[dev-phase-considerations]]
    # punto 9.
    for text_norm in sorted(set(by_text_a) | set(by_text_b)):
        list_a = by_text_a.get(text_norm, [])
        list_b = by_text_b.get(text_norm, [])
        n = min(len(list_a), len(list_b))
        matched_count += n
        removed.extend(p["text"] for p in list_a[n:])
        added.extend(p["text"] for p in list_b[n:])

    return {"paragraphs_matched": matched_count, "paragraphs_removed": removed, "paragraphs_added": added}


def match_appendix(blocks_a: list, blocks_b: list) -> dict:
    tables_a = extract_tables(blocks_a)
    tables_b = extract_tables(blocks_b)
    table_match = match_tables(tables_a, tables_b)

    tables_matched = []
    for table_a, table_b, match_type, ratio in table_match["matched"]:
        row_match = match_rows(table_a, table_b)
        tables_matched.append(
            {
                "table_title": table_a["title_raw"],
                "table_title_b": table_b["title_raw"],
                "match_type": match_type,
                "fuzzy_ratio": ratio,
                **row_match,
            }
        )

    heading_match = match_headings(extract_headings(blocks_a), extract_headings(blocks_b))
    paragraph_match = match_paragraphs(extract_paragraphs(blocks_a), extract_paragraphs(blocks_b))

    return {
        "num_tables_a": len(tables_a),
        "num_tables_b": len(tables_b),
        "tables_matched": tables_matched,
        "tables_removed": [
            {"table_title": t["title_raw"], "num_rows": len(t["rows"])} for t in table_match["tables_removed"].values()
        ],
        "tables_added": [
            {"table_title": t["title_raw"], "num_rows": len(t["rows"])} for t in table_match["tables_added"].values()
        ],
        **heading_match,
        **paragraph_match,
    }


def match_edition_pair(data_a: dict, data_b: dict) -> dict:
    appendices_out = {}
    for appendix in APPENDICES:
        blocks_a = data_a["sections"].get(appendix, {}).get("blocks", [])
        blocks_b = data_b["sections"].get(appendix, {}).get("blocks", [])
        appendices_out[appendix] = match_appendix(blocks_a, blocks_b)

    return {
        "manual": MANUAL_SLUG,
        "edition_a": data_a["edition_date"],
        "edition_b": data_b["edition_date"],
        "appendices": appendices_out,
    }


def main():
    input_paths = sorted(INPUT_DIR.glob("*.json"))
    if len(input_paths) < 2:
        print(f"Se necesitan al menos 2 ediciones en {INPUT_DIR}", file=sys.stderr)
        sys.exit(1)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for path_a, path_b in zip(input_paths, input_paths[1:]):
        data_a = json.loads(path_a.read_text())
        data_b = json.loads(path_b.read_text())
        result = match_edition_pair(data_a, data_b)

        out_name = f"{result['edition_a']}_to_{result['edition_b']}.json"
        (OUTPUT_DIR / out_name).write_text(json.dumps(result, ensure_ascii=False, indent=2))

        summary_parts = []
        for appendix in APPENDICES:
            a = result["appendices"][appendix]
            rows_matched = sum(len(t["rows_matched"]) for t in a["tables_matched"])
            rows_added = sum(len(t["rows_added"]) for t in a["tables_matched"])
            rows_removed = sum(len(t["rows_removed"]) for t in a["tables_matched"])
            fuzzy_tables = sum(1 for t in a["tables_matched"] if t["match_type"] == "fuzzy")
            summary_parts.append(
                f"{appendix}: tablas {a['num_tables_a']}->{a['num_tables_b']} "
                f"(matched={len(a['tables_matched'])}[fuzzy={fuzzy_tables}], "
                f"+{len(a['tables_added'])}/-{len(a['tables_removed'])}) "
                f"filas matched={rows_matched} +{rows_added}/-{rows_removed}"
            )
        print(f"{out_name}:")
        for part in summary_parts:
            print(f"  {part}")


if __name__ == "__main__":
    main()
