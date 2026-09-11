"""
Modulo 3 - Emparejamiento de bloques para el manual
base_ii_clearing_interchange_formats_tc_50_to_tc_92.

Mismo diseno que el Modulo 3 del 3er manual, su hermano directo: reconstruye secciones
TC/TCR delimitadas por `section_heading`, cada una con DOS listas paralelas (filas de grilla
`table_row` y fichas `field_card`, sin enlazarlas entre si -mismo criterio de no unificar 2
vistas del mismo campo sin necesidad demostrada), y empareja secciones/filas/fichas entre 2
ediciones consecutivas. Clave de emparejamiento de filas/fichas: `Position`/`Positions`
normalizado (unifica guion/en-dash y espacios), no nombre.

**Diferencia real respecto al 3er manual, encontrada validando el Modulo 2 de ESTE manual
(no antes)**: el 3er manual documento "0 titulos de seccion duplicados dentro de una misma
edicion, en las 9 ediciones" y por eso `match_sections` ahi arma sin mas un dict
`{titulo_normalizado: seccion}`. ESTE manual rompe esa asuncion: la seccion
`"TC 57 - TCR 5 - Limited Use Data"` aparece 2 VECES seguidas en el stream de bloques, con
titulo Y parrafo introductorio IDENTICOS, pero con 2 layouts de campos completamente
distintos (confirmado en las 9 ediciones, siempre exactamente 1 ocurrencia, siempre esta
misma seccion -ver [[pending-bug-fixes]] item 10 en la memoria del asistente). Un dict simple
pisaria silenciosamente la 1ra ocurrencia con la 2da al construir `by_title`, perdiendo un
layout completo del diffing en las 8 comparaciones -exactamente el tipo de perdida silenciosa
que este proyecto evita en todos los demas modulos (duplicados de Position/Values, filas con
cell count incorrecto, etc. siempre se DETECTAN y reportan, nunca se pisan en silencio).

Fix minimo aplicado (no resuelve la ambiguedad semantica de "cual layout es cual" -eso sigue
pendiente, ver feedback del usuario 2026-08-19 en memoria: revisitar cuando el proyecto pase
de POC a desarrollo real): `by_title` ahora mapea titulo -> LISTA de secciones (no una sola),
preservando el orden en que aparecen en el stream. El emparejamiento "exacto" empareja
secciones del mismo titulo POR ORDEN DE APARICION (1ra con 1ra, 2da con 2da, etc.) -mismo
principio de "clave estable" ya usado en el resto del proyecto, aplicado aca al orden
posicional del documento (estable dentro de una edicion) en vez de al texto del titulo
(ambiguo cuando se repite). Si un lado tiene mas ocurrencias que el otro del mismo titulo, el
sobrante cae a la logica de matching por similitud (`difflib`) igual que cualquier seccion sin
match exacto -no se pierde, se reporta como removed/added si no encuentra pareja.
`duplicate_section_titles` se agrega al resultado (mismo patron que `duplicate_row_positions`/
`duplicate_card_positions`) para que quede visible en el output cuando esto ocurre, en vez de
quedar oculto en la logica interna.

Alcance: procesa pares de ediciones CONSECUTIVAS (8 pares para las 9 ediciones de este
manual).
"""

import difflib
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

MANUAL_SLUG = "base_ii_clearing_interchange_formats_tc_50_to_tc_92"
INPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "02_normalizacion_bloques"
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "03_emparejamiento_bloques"

FUZZY_TITLE_THRESHOLD = 0.85
WHITESPACE = re.compile(r"\s+")
DASH_CHARS = re.compile(r"[‐-―]")

# Item 10/[[pending-bug-fixes]] (resuelto parcialmente 2026-08-25): campos que encabezan
# CUALQUIER seccion de este manual (confirmado en las 9 ediciones) -no sirven para distinguir
# 2 secciones que colisionan de titulo, asi que se saltean al buscar una "firma" de contenido.
# "Reserved" tambien se salta: es el campo mas generico posible, casi nunca es el que
# distingue semanticamente 2 layouts (confirmado en el caso real: la 2da ocurrencia de
# "TC 57 - TCR 5 - Limited Use Data" arranca con `Reserved` @ 5-15, pero el campo realmente
# distintivo es el siguiente, `Banknet Settlement Number` @ 16-24).
BORING_FIELD_NAMES = {
    "transaction code",
    "transaction code qualifier",
    "transaction component sequence number",
    "reserved",
}


def _section_signature(rows: list) -> tuple[str, str]:
    """Nombre (y su posicion) del primer campo 'distintivo' de una seccion (ver comentario de
    `BORING_FIELD_NAMES`), usado SOLO para desambiguar secciones que colisionan de titulo
    -nunca para el emparejamiento normal (eso sigue siendo por `title_norm` exacto/fuzzy).
    Ordena por posicion para que el resultado no dependa del orden de aparicion en el
    stream. La posicion se agrega (item 10/[[pending-bug-fixes]], residuo cerrado
    2026-09-05) para que el sufijo desambiguador del reporte ubique el campo en el layout de
    bytes sin tener que cruzar contra la tabla completa -el nombre solo alcanza para
    distinguir, no para ubicar."""
    for row in sorted(rows, key=lambda r: _position_sort_key(r["position"])):
        name = row["cells"][-1].strip()
        if name.casefold() not in BORING_FIELD_NAMES:
            return name, row["position"]
    if rows:
        return rows[0]["cells"][-1].strip(), rows[0]["position"]
    return "", ""


def _normalize_title(text: str) -> str:
    return WHITESPACE.sub(" ", text).strip().casefold()


def _normalize_position(text: str) -> str:
    text = DASH_CHARS.sub("-", text)
    return WHITESPACE.sub(" ", text).strip()


def _position_sort_key(position: str):
    m = re.match(r"\d+", position)
    return (int(m.group()) if m else 0, position)


def _find_duplicates(values) -> list:
    seen = {}
    dups = set()
    for v in values:
        seen[v] = seen.get(v, 0) + 1
        if seen[v] > 1:
            dups.add(v)
    return sorted(dups)


def extract_sections(blocks: list) -> list:
    """Reconstruye secciones TC/TCR (titulo + filas de grilla + fichas) a partir de los
    bloques planos del Modulo 2. Cada `section_heading` en el stream arranca una seccion
    nueva -incluso si su titulo repite el de una seccion anterior (ver docstring del
    modulo): la segmentacion es por POSICION en el stream, no por texto de titulo, asi que
    los 2 layouts de "TC 57 - TCR 5 - Limited Use Data" ya quedan separados en 2 objetos de
    seccion distintos en esta funcion -el riesgo de colision esta en `match_sections`, no
    aca."""
    sections = []
    current = None

    for block in blocks:
        if block["type"] == "section_heading":
            if current is not None:
                sections.append(current)
            current = {
                "title": block["text"],
                "title_norm": _normalize_title(block["text"]),
                "rows": [],
                "cards": [],
            }
            continue
        if current is None:
            continue
        if block["type"] == "table_row":
            current["rows"].append(
                {"position": _normalize_position(block["cells"][0]), "cells": block["cells"]}
            )
        elif block["type"] == "field_card":
            current["cards"].append(
                {"position": _normalize_position(block["positions"]), "card": block}
            )

    if current is not None:
        sections.append(current)

    for section in sections:
        section["duplicate_row_positions"] = _find_duplicates(r["position"] for r in section["rows"])
        section["duplicate_card_positions"] = _find_duplicates(c["position"] for c in section["cards"])
        section["signature"], section["signature_position"] = _section_signature(section["rows"])

    return sections


def match_sections(sections_a: list, sections_b: list) -> dict:
    # Lista (no un solo valor) por titulo -preserva orden de aparicion; ver docstring del
    # modulo sobre por que un dict simple perderia una de las 2 secciones "TC 57 - TCR 5".
    by_title_a = defaultdict(list)
    for s in sections_a:
        by_title_a[s["title_norm"]].append(s)
    by_title_b = defaultdict(list)
    for s in sections_b:
        by_title_b[s["title_norm"]].append(s)

    # Item 10/[[pending-bug-fixes]] (resuelto parcialmente 2026-08-25): cuando un titulo
    # colisiona (2+ secciones), emparejar por orden de aparicion es fragil -si una edicion
    # futura reordenara las 2 ocurrencias, se emparejarian mal en silencio. Se reordena cada
    # grupo colisionado por `signature` (contenido real, ver `_section_signature`) ANTES de
    # emparejar por posicion -asi el emparejamiento queda anclado al contenido, no al orden
    # del documento. No cambia nada en las 9 ediciones actuales (el orden ya era estable),
    # es una salvaguarda a futuro sin costo ni riesgo medido.
    for by_title in (by_title_a, by_title_b):
        for title_norm, group in by_title.items():
            if len(group) > 1:
                group.sort(key=lambda s: s["signature"])

    matched = []
    unmatched_a = {}
    unmatched_b = {t: list(lst) for t, lst in by_title_b.items()}

    for title_norm, list_a in by_title_a.items():
        list_b = unmatched_b.get(title_norm, [])
        n = min(len(list_a), len(list_b))
        for sec_a, sec_b in zip(list_a[:n], list_b[:n]):
            matched.append((sec_a, sec_b, "exact", 1.0))
        leftover_a = list_a[n:]
        leftover_b = list_b[n:]
        if leftover_a:
            unmatched_a.setdefault(title_norm, []).extend(leftover_a)
        if leftover_b:
            unmatched_b[title_norm] = leftover_b
        else:
            unmatched_b.pop(title_norm, None)

    # Aplana los sobrantes a listas simples para el fallback fuzzy (que empareja seccion a
    # seccion, no titulo a titulo -a esta altura ya no importa el titulo compartido).
    flat_unmatched_a = [(t, sec) for t, lst in unmatched_a.items() for sec in lst]
    flat_unmatched_b = [(t, sec) for t, lst in unmatched_b.items() for sec in lst]

    remaining_b = list(flat_unmatched_b)
    still_unmatched_a = []
    for title_norm_a, sec_a in flat_unmatched_a:
        best_ratio = 0.0
        best_idx = None
        for idx, (title_norm_b, sec_b) in enumerate(remaining_b):
            ratio = difflib.SequenceMatcher(None, title_norm_a, title_norm_b).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_idx = idx
        if best_idx is not None and best_ratio >= FUZZY_TITLE_THRESHOLD:
            _, sec_b = remaining_b.pop(best_idx)
            matched.append((sec_a, sec_b, "fuzzy", round(best_ratio, 3)))
        else:
            still_unmatched_a.append(sec_a)

    return {
        "matched": matched,
        "sections_removed": still_unmatched_a,
        "sections_added": [sec_b for _, sec_b in remaining_b],
    }


def match_rows(section_a: dict, section_b: dict) -> dict:
    rows_a = {r["position"]: r for r in section_a["rows"]}
    rows_b = {r["position"]: r for r in section_b["rows"]}

    matched = sorted(set(rows_a) & set(rows_b), key=_position_sort_key)
    removed = sorted(set(rows_a) - set(rows_b), key=_position_sort_key)
    added = sorted(set(rows_b) - set(rows_a), key=_position_sort_key)

    return {
        "rows_matched": [
            {"position": p, "cells_a": rows_a[p]["cells"], "cells_b": rows_b[p]["cells"]}
            for p in matched
        ],
        "rows_removed": [{"position": p, "cells": rows_a[p]["cells"]} for p in removed],
        "rows_added": [{"position": p, "cells": rows_b[p]["cells"]} for p in added],
    }


def match_cards(section_a: dict, section_b: dict) -> dict:
    cards_a = {c["position"]: c["card"] for c in section_a["cards"]}
    cards_b = {c["position"]: c["card"] for c in section_b["cards"]}

    matched = sorted(set(cards_a) & set(cards_b), key=_position_sort_key)
    removed = sorted(set(cards_a) - set(cards_b), key=_position_sort_key)
    added = sorted(set(cards_b) - set(cards_a), key=_position_sort_key)

    return {
        "cards_matched": [
            {"position": p, "card_a": cards_a[p], "card_b": cards_b[p]} for p in matched
        ],
        "cards_removed": [{"position": p, "card": cards_a[p]} for p in removed],
        "cards_added": [{"position": p, "card": cards_b[p]} for p in added],
    }


def match_edition_pair(data_a: dict, data_b: dict) -> dict:
    sections_a = extract_sections(data_a["blocks"])
    sections_b = extract_sections(data_b["blocks"])

    section_match = match_sections(sections_a, sections_b)

    sections_matched = []
    for sec_a, sec_b, match_type, ratio in section_match["matched"]:
        row_match = match_rows(sec_a, sec_b)
        card_match = match_cards(sec_a, sec_b)
        sections_matched.append(
            {
                "title_a": sec_a["title"],
                "title_b": sec_b["title"],
                "signature_a": sec_a["signature"],
                "signature_b": sec_b["signature"],
                "signature_position_a": sec_a["signature_position"],
                "signature_position_b": sec_b["signature_position"],
                "match_type": match_type,
                "fuzzy_ratio": ratio,
                "duplicate_row_positions_a": sec_a["duplicate_row_positions"],
                "duplicate_row_positions_b": sec_b["duplicate_row_positions"],
                "duplicate_card_positions_a": sec_a["duplicate_card_positions"],
                "duplicate_card_positions_b": sec_b["duplicate_card_positions"],
                **row_match,
                **card_match,
            }
        )

    duplicate_titles_a = _find_duplicates(s["title_norm"] for s in sections_a)
    duplicate_titles_b = _find_duplicates(s["title_norm"] for s in sections_b)

    return {
        "manual": MANUAL_SLUG,
        "edition_a": data_a["edition_date"],
        "edition_b": data_b["edition_date"],
        "num_sections_a": len(sections_a),
        "num_sections_b": len(sections_b),
        "duplicate_section_titles_a": duplicate_titles_a,
        "duplicate_section_titles_b": duplicate_titles_b,
        "sections_matched": sections_matched,
        "sections_removed": [
            {
                "title": s["title"],
                "signature": s["signature"],
                "signature_position": s["signature_position"],
                "num_rows": len(s["rows"]),
                "num_cards": len(s["cards"]),
            }
            for s in section_match["sections_removed"]
        ],
        "sections_added": [
            {
                "title": s["title"],
                "signature": s["signature"],
                "signature_position": s["signature_position"],
                "num_rows": len(s["rows"]),
                "num_cards": len(s["cards"]),
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

        rows_matched = sum(len(s["rows_matched"]) for s in result["sections_matched"])
        rows_added = sum(len(s["rows_added"]) for s in result["sections_matched"])
        rows_removed = sum(len(s["rows_removed"]) for s in result["sections_matched"])
        cards_matched = sum(len(s["cards_matched"]) for s in result["sections_matched"])
        cards_added = sum(len(s["cards_added"]) for s in result["sections_matched"])
        cards_removed = sum(len(s["cards_removed"]) for s in result["sections_matched"])
        fuzzy = sum(1 for s in result["sections_matched"] if s["match_type"] == "fuzzy")
        print(
            f"{out_name}: secciones {result['num_sections_a']}->{result['num_sections_b']} "
            f"(matched={len(result['sections_matched'])} [fuzzy={fuzzy}], "
            f"added={len(result['sections_added'])}, removed={len(result['sections_removed'])}) | "
            f"filas matched={rows_matched} added={rows_added} removed={rows_removed} | "
            f"fichas matched={cards_matched} added={cards_added} removed={cards_removed}"
        )


if __name__ == "__main__":
    main()
