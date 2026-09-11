"""
Modulo 3 - Emparejamiento de bloques para el manual
visanet_settlement_service_vss_user_guide_volume_1_specifications.

Mismo diseno que el 6to manual para secciones y parrafos (ruta jerarquica L1>L2>L3, exacto+
fuzzy para secciones; exacto+fuzzy con salvaguardas -longitud minima+umbral alto- y
reconciliacion de reflow para parrafos, ver docstring del 6to manual `match.py` para el
detalle completo de por que cada decision se tomo asi). Este manual agrega un 3er tipo de
bloque, `field_description_pair` (ver Modulo 2), que necesita su propio diseno de
emparejamiento.

**Clave de emparejamiento de pares: `(example_title, name)` normalizados, EXACTO -sin
fallback fuzzy.** Investigado con datos reales antes de decidir: `name` solo NO alcanza
(`"Row"`/`"Column"` se repiten decenas de veces en todo el documento, son sub-encabezados de
estructura, no identificadores unicos -mismo tipo de colision ya visto con `TCR` en el 5to
manual). `example_title` (el titulo rotado "Example N: Reconciliation of X Report to Y
Report", normalizado SIN su sufijo de pagina "(N of M)" -separado en Modulo 2, confirmado que
cambia por pagina pero el resto del titulo no) agrupa correctamente las 10 tablas reales de
la edicion de referencia (10-40 pares cada una). Pero incluso la clave compuesta tiene
duplicados residuales (52/236 en la edicion de referencia): una misma tabla "Example N" puede
tener SUB-estructuras repetidas (ej. "ISSUER TRANSACTION DETAIL" y "ACQUIRER TRANSACTION
DETAIL" como 2 bloques paralelos, cada uno con sus propios campos "Row"/"Proc Date"/"To CRS"/
etc.) -mismo patron ya resuelto en otros manuales (`TC 57` del 4to manual, claves de fila del
5to): se empareja por ORDEN DE APARICION dentro de la clave repetida, no un dict simple que
perderia una entrada por colision. Sin fallback fuzzy sobre `name` -mismo riesgo demostrado
inseguro que en el 5to manual (etiquetas cortas y genericas), no se re-investiga aca porque el
mecanismo y el riesgo ya estan validados en ese manual.

**Salto real de nivel de encabezado, encontrado corriendo este modulo por 1ra vez (2026-08-19)**:
a diferencia del 6to manual, aca la jerarquia L1>L2>L3 no siempre esta completa -"Related
Information" aparece como encabezado de NIVEL 3 directamente bajo un nivel 1, sin nivel 2
intermedio (confirmado el mismo patron exacto en las 6 ediciones, bajo 4 capitulos distintos:
"VSS Implementation Methods", "VSS Funds Transfer Point Identification", "VSS Testing", "VSS
Implementation Timelines"). `extract_sections` usa el ancestro que SI esta presente en vez de
asumir la secuencia 1..N completa (`tuple(p for p in path[:level] if p is not None)`).

Alcance: procesa pares de ediciones CONSECUTIVAS (5 pares para las 6 ediciones de este
manual).
"""

import difflib
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

MANUAL_SLUG = "visanet_settlement_service_vss_user_guide_volume_1_specifications"
INPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "02_normalizacion_bloques"
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "03_emparejamiento_bloques"

WHITESPACE = re.compile(r"\s+")

FUZZY_SECTION_THRESHOLD = 0.85
FUZZY_PARAGRAPH_THRESHOLD = 0.90
MIN_PARAGRAPH_LEN_FOR_FUZZY = 60


def _normalize_text(text: str) -> str:
    return WHITESPACE.sub(" ", text).strip().casefold()


def _find_duplicates(values) -> list:
    seen = {}
    dups = set()
    for v in values:
        seen[v] = seen.get(v, 0) + 1
        if seen[v] > 1:
            dups.add(v)
    return sorted(dups)


def extract_sections(blocks: list) -> list:
    """Reconstruye secciones por RUTA jerarquica completa (L1>L2>L3). Cada `section_heading`
    (de cualquier nivel) arranca una seccion nueva; los `paragraph`/`field_description_pair`
    que siguen se acumulan ahi hasta el proximo `section_heading`."""
    sections = []
    current = None
    path = [None, None, None]

    for block in blocks:
        if block["type"] == "section_heading":
            if current is not None:
                sections.append(current)
            level = block["level"]
            path[level - 1] = block["text"]
            for i in range(level, 3):
                path[i] = None
            # Salto real de nivel confirmado con datos reales (ej. "Related Information" a
            # nivel 3 sin nivel 2 intermedio, mismo patron en las 6 ediciones) -se usa el
            # ancestro que SI esta presente, sin asumir la secuencia 1..nivel completa.
            effective_path = tuple(p for p in path[:level] if p is not None)
            path_norm = tuple(_normalize_text(p) for p in effective_path)
            current = {
                "path": effective_path,
                "path_norm": path_norm,
                "paragraphs": [],
                "pairs": [],
            }
            continue
        if current is None:
            continue
        if block["type"] == "paragraph":
            current["paragraphs"].append(
                {"text": block["text"], "text_norm": _normalize_text(block["text"])}
            )
        elif block["type"] == "field_description_pair":
            key = (_normalize_text(block["example_title"]), _normalize_text(block["name"]))
            current["pairs"].append({"key": key, "block": block})

    if current is not None:
        sections.append(current)

    for section in sections:
        section["duplicate_paragraph_texts"] = _find_duplicates(
            p["text_norm"] for p in section["paragraphs"]
        )
        section["duplicate_pair_keys"] = _find_duplicates(p["key"] for p in section["pairs"])

    return sections


def match_sections(sections_a: list, sections_b: list) -> dict:
    by_path_a = defaultdict(list)
    for s in sections_a:
        by_path_a[s["path_norm"]].append(s)
    by_path_b = defaultdict(list)
    for s in sections_b:
        by_path_b[s["path_norm"]].append(s)

    matched = []
    unmatched_a = {}
    unmatched_b = {p: list(lst) for p, lst in by_path_b.items()}

    for path_norm, list_a in by_path_a.items():
        list_b = unmatched_b.get(path_norm, [])
        n = min(len(list_a), len(list_b))
        for sec_a, sec_b in zip(list_a[:n], list_b[:n]):
            matched.append((sec_a, sec_b, "exact", 1.0))
        if list_a[n:]:
            unmatched_a.setdefault(path_norm, []).extend(list_a[n:])
        if list_b[n:]:
            unmatched_b[path_norm] = list_b[n:]
        else:
            unmatched_b.pop(path_norm, None)

    flat_unmatched_a = [(p, sec) for p, lst in unmatched_a.items() for sec in lst]
    remaining_b = [(p, sec) for p, lst in unmatched_b.items() for sec in lst]

    # Emparejamiento fuzzy por MEJOR similitud global, no por orden de procesamiento -ver
    # [[dev-phase-considerations]] punto 9 (2026-09-06): la version anterior (greedy, cada
    # sec_a se queda con su mejor candidato DISPONIBLE en el momento en que se procesa) podia
    # dar un resultado distinto segun el orden de flat_unmatched_a -confirmado real con datos
    # reales del propio Modulo 3 de este manual (par "Reporting Options Worksheet", 2 pares
    # de secciones casi-empatadas donde el orden de procesamiento decidia cual quedaba con la
    # mejor similitud, 0.996 vs 0.907). Recolectar TODOS los candidatos por encima del umbral
    # primero y asignar en orden de similitud DESCENDENTE hace que el resultado ya no dependa
    # del orden de entrada -los pares mas confiables se reservan primero, siempre.
    candidates = []
    for i, (path_norm_a, _sec_a) in enumerate(flat_unmatched_a):
        text_a = " > ".join(path_norm_a)
        for j, (path_norm_b, _sec_b) in enumerate(remaining_b):
            text_b = " > ".join(path_norm_b)
            ratio = difflib.SequenceMatcher(None, text_a, text_b).ratio()
            if ratio >= FUZZY_SECTION_THRESHOLD:
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
    for i, (_path_norm_a, sec_a) in enumerate(flat_unmatched_a):
        if i in fuzzy_match_for_a:
            j, ratio = fuzzy_match_for_a[i]
            _, sec_b = remaining_b[j]
            matched.append((sec_a, sec_b, "fuzzy", round(ratio, 3)))
        else:
            still_unmatched_a.append(sec_a)

    return {
        "matched": matched,
        "sections_removed": still_unmatched_a,
        "sections_added": [sec for j, (_, sec) in enumerate(remaining_b) if j not in used_b],
    }


def _reflow_matches(paras_side: list, other_norm_index: dict, other_consumed: set) -> tuple:
    """Busca pares de parrafos ADYACENTES de un lado que, concatenados, matchean EXACTO
    (normalizado) a un parrafo TODAVIA no consumido del otro lado -mismo contenido, solo
    re-cortado distinto por reflow de pagina/layout entre ediciones, no un cambio real (ver
    docstring del 6to manual)."""
    reflow = []
    consumed_side = set()
    for i in range(len(paras_side) - 1):
        if i in consumed_side or (i + 1) in consumed_side:
            continue
        combined_norm = _normalize_text(paras_side[i]["text"] + " " + paras_side[i + 1]["text"])
        for idx in other_norm_index.get(combined_norm, []):
            if idx in other_consumed:
                continue
            reflow.append({"pair_idx": (i, i + 1), "other_idx": idx})
            consumed_side.add(i)
            consumed_side.add(i + 1)
            other_consumed.add(idx)
            break
    return reflow, consumed_side


def match_paragraphs(section_a: dict, section_b: dict) -> dict:
    """Empareja parrafos en 3 pasadas: re-corte por reflow, exacto, fuzzy con salvaguardas
    -identico al 6to manual, ver su docstring para el detalle completo."""
    paras_a = section_a["paragraphs"]
    paras_b = section_b["paragraphs"]

    norm_index_a = defaultdict(list)
    for i, p in enumerate(paras_a):
        norm_index_a[p["text_norm"]].append(i)
    norm_index_b = defaultdict(list)
    for i, p in enumerate(paras_b):
        norm_index_b[p["text_norm"]].append(i)

    consumed_a = set()
    consumed_b = set()
    reflowed = []

    reflow_a, pair_idx_a = _reflow_matches(paras_a, norm_index_b, consumed_b)
    for r in reflow_a:
        i, j = r["pair_idx"]
        reflowed.append(
            {
                "text_a": [paras_a[i]["text"], paras_a[j]["text"]],
                "text_b": [paras_b[r["other_idx"]]["text"]],
            }
        )
    consumed_a |= pair_idx_a

    remaining_a_norm_index = defaultdict(list)
    for i, p in enumerate(paras_a):
        if i not in consumed_a:
            remaining_a_norm_index[p["text_norm"]].append(i)
    reflow_b, pair_idx_b = _reflow_matches(paras_b, remaining_a_norm_index, consumed_a)
    for r in reflow_b:
        i, j = r["pair_idx"]
        reflowed.append(
            {
                "text_a": [paras_a[r["other_idx"]]["text"]],
                "text_b": [paras_b[i]["text"], paras_b[j]["text"]],
            }
        )
    consumed_b |= pair_idx_b

    by_text_a = defaultdict(list)
    for i, p in enumerate(paras_a):
        if i not in consumed_a:
            by_text_a[p["text_norm"]].append(p)
    by_text_b = defaultdict(list)
    for i, p in enumerate(paras_b):
        if i not in consumed_b:
            by_text_b[p["text_norm"]].append(p)

    matched = []
    unmatched_a = []
    unmatched_b = []

    # sorted() -no iterar el set crudo- para que el orden de salida sea deterministico entre
    # corridas: la iteracion de un set() de strings depende de PYTHONHASHSEED (randomizado por
    # proceso en Python 3), asi que sin este sort el mismo input produce el mismo CONTENIDO
    # pero en un orden de lista distinto cada vez (bug real encontrado 2026-09-05, ver
    # [[dev-phase-considerations]] punto 9).
    all_texts = sorted(set(by_text_a) | set(by_text_b))
    for text_norm in all_texts:
        list_a = by_text_a.get(text_norm, [])
        list_b = by_text_b.get(text_norm, [])
        n = min(len(list_a), len(list_b))
        for pa, pb in zip(list_a[:n], list_b[:n]):
            matched.append({"text_a": pa["text"], "text_b": pb["text"], "match_type": "exact", "similarity": 1.0})
        unmatched_a.extend(list_a[n:])
        unmatched_b.extend(list_b[n:])

    remaining_b = list(unmatched_b)

    # Emparejamiento fuzzy por MEJOR similitud global, no por orden de procesamiento -mismo
    # fix y misma razon que `match_sections` arriba, ver su comentario y
    # [[dev-phase-considerations]] punto 9. Este es el caso REAL confirmado (par "Reporting
    # Options Worksheet": antes daba 0.996 o 0.907 segun el orden aleatorio pre-punto-9, ahora
    # siempre 0.996 -el mejor de los dos- sin importar el orden de entrada.
    eligible_a = [pa for pa in unmatched_a if len(pa["text"]) >= MIN_PARAGRAPH_LEN_FOR_FUZZY]
    short_a = [pa for pa in unmatched_a if len(pa["text"]) < MIN_PARAGRAPH_LEN_FOR_FUZZY]
    eligible_b_idx = [idx for idx, pb in enumerate(remaining_b) if len(pb["text"]) >= MIN_PARAGRAPH_LEN_FOR_FUZZY]

    candidates = []
    for i, pa in enumerate(eligible_a):
        for j in eligible_b_idx:
            pb = remaining_b[j]
            ratio = difflib.SequenceMatcher(None, pa["text_norm"], pb["text_norm"]).ratio()
            if ratio >= FUZZY_PARAGRAPH_THRESHOLD:
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

    still_unmatched_a = list(short_a)
    for i, pa in enumerate(eligible_a):
        if i in fuzzy_match_for_a:
            j, ratio = fuzzy_match_for_a[i]
            pb = remaining_b[j]
            matched.append(
                {
                    "text_a": pa["text"],
                    "text_b": pb["text"],
                    "match_type": "fuzzy",
                    "similarity": round(ratio, 3),
                }
            )
        else:
            still_unmatched_a.append(pa)

    remaining_b = [pb for j, pb in enumerate(remaining_b) if j not in used_b]

    return {
        "paragraphs_matched": matched,
        "paragraphs_removed": [p["text"] for p in still_unmatched_a],
        "paragraphs_added": [p["text"] for p in remaining_b],
        "paragraphs_reflowed": reflowed,
    }


def match_pairs(section_a: dict, section_b: dict) -> dict:
    """Empareja pares Field Name/Description por clave EXACTA `(example_title, name)`, con
    desempate por orden de aparicion dentro de una clave repetida (ver docstring del modulo)."""
    by_key_a = defaultdict(list)
    for p in section_a["pairs"]:
        by_key_a[p["key"]].append(p["block"])
    by_key_b = defaultdict(list)
    for p in section_b["pairs"]:
        by_key_b[p["key"]].append(p["block"])

    matched = []
    removed = []
    added = []

    for key in set(by_key_a) | set(by_key_b):
        list_a = by_key_a.get(key, [])
        list_b = by_key_b.get(key, [])
        n = min(len(list_a), len(list_b))
        for pa, pb in zip(list_a[:n], list_b[:n]):
            matched.append({"key": key, "pair_a": pa, "pair_b": pb})
        removed.extend({"key": key, "pair": p} for p in list_a[n:])
        added.extend({"key": key, "pair": p} for p in list_b[n:])

    sort_key = lambda item: item["key"]
    return {
        "pairs_matched": sorted(matched, key=sort_key),
        "pairs_removed": sorted(removed, key=sort_key),
        "pairs_added": sorted(added, key=sort_key),
    }


def match_edition_pair(data_a: dict, data_b: dict) -> dict:
    sections_a = extract_sections(data_a["blocks"])
    sections_b = extract_sections(data_b["blocks"])

    section_match = match_sections(sections_a, sections_b)

    sections_matched = []
    for sec_a, sec_b, match_type, ratio in section_match["matched"]:
        para_match = match_paragraphs(sec_a, sec_b)
        pair_match = match_pairs(sec_a, sec_b)
        sections_matched.append(
            {
                "path_a": sec_a["path"],
                "path_b": sec_b["path"],
                "match_type": match_type,
                "fuzzy_ratio": ratio,
                "duplicate_paragraph_texts_a": sec_a["duplicate_paragraph_texts"],
                "duplicate_paragraph_texts_b": sec_b["duplicate_paragraph_texts"],
                "duplicate_pair_keys_a": sec_a["duplicate_pair_keys"],
                "duplicate_pair_keys_b": sec_b["duplicate_pair_keys"],
                **para_match,
                **pair_match,
            }
        )

    return {
        "manual": MANUAL_SLUG,
        "edition_a": data_a["edition_date"],
        "edition_b": data_b["edition_date"],
        "num_sections_a": len(sections_a),
        "num_sections_b": len(sections_b),
        "sections_matched": sections_matched,
        "sections_removed": [
            {
                "path": s["path"],
                "num_paragraphs": len(s["paragraphs"]),
                "num_pairs": len(s["pairs"]),
            }
            for s in section_match["sections_removed"]
        ],
        "sections_added": [
            {
                "path": s["path"],
                "num_paragraphs": len(s["paragraphs"]),
                "num_pairs": len(s["pairs"]),
            }
            for s in section_match["sections_added"]
        ],
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

        paras_matched = sum(len(s["paragraphs_matched"]) for s in result["sections_matched"])
        paras_added = sum(len(s["paragraphs_added"]) for s in result["sections_matched"])
        paras_removed = sum(len(s["paragraphs_removed"]) for s in result["sections_matched"])
        paras_reflowed = sum(len(s["paragraphs_reflowed"]) for s in result["sections_matched"])
        pairs_matched = sum(len(s["pairs_matched"]) for s in result["sections_matched"])
        pairs_added = sum(len(s["pairs_added"]) for s in result["sections_matched"])
        pairs_removed = sum(len(s["pairs_removed"]) for s in result["sections_matched"])
        fuzzy_secs = sum(1 for s in result["sections_matched"] if s["match_type"] == "fuzzy")
        fuzzy_paras = sum(
            1 for s in result["sections_matched"] for p in s["paragraphs_matched"] if p["match_type"] == "fuzzy"
        )
        print(
            f"{out_name}: secciones {result['num_sections_a']}->{result['num_sections_b']} "
            f"(matched={len(result['sections_matched'])} [fuzzy={fuzzy_secs}], "
            f"added={len(result['sections_added'])}, removed={len(result['sections_removed'])}) | "
            f"parrafos matched={paras_matched} [fuzzy={fuzzy_paras}] reflowed={paras_reflowed} "
            f"added={paras_added} removed={paras_removed} | "
            f"pares matched={pairs_matched} added={pairs_added} removed={pairs_removed}"
        )


if __name__ == "__main__":
    main()
