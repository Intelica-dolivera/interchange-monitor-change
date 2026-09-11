"""
Modulo 3 - Emparejamiento de bloques para el manual base_ii_transactions_quick_reference.

Toma el stream plano de bloques del Modulo 2 (`section_heading`/`table_row`/`paragraph`) y
reconstruye la entidad real a comparar -una entrada TC, delimitada por `section_heading`, que
contiene una lista de filas TCR- y empareja secciones y, dentro de cada seccion emparejada,
sus filas, entre 2 ediciones consecutivas.

**Diseno de clave de emparejamiento, DISTINTO al de los otros 4 manuales -decidido con datos
reales, no de antemano** (ver [[open-questions-technical-manuals]] en la memoria del
asistente para el contexto completo de por que este manual no tiene columna de posicion/
byte-offset):

1. **Secciones (entradas TC)**: emparejadas por titulo exacto normalizado, con fallback
   fuzzy (`difflib`, umbral 0.85) para las no exactas -mismo mecanismo ya usado en los otros
   4 manuales, sin cambios: el titulo `"NN Nombre"` es unico por construccion (el prefijo de
   2 digitos garantiza unicidad), no hace falta el emparejamiento por orden de aparicion que
   si hizo falta para las filas (ver mas abajo) ni para el 4to manual (seccion `TC 57`
   duplicada).

2. **Filas TCR: clave compuesta `(TCR normalizado, descripcion normalizada)`, SIN fallback
   fuzzy sobre el texto -decision tomada tras confirmar EMPIRICAMENTE que el fuzzy matching
   por descripcion sola (el mismo mecanismo que si funciona bien para titulos de seccion en
   los otros 4 manuales) NO es seguro aca**: calculando similitud `difflib` par a par entre
   TODAS las descripciones de una misma seccion en la edicion de referencia, aparecen decenas
   de pares de filas GENUINAMENTE DISTINTAS con similitud >= 0.85 -ej. `"Batch Disposition
   Code A"` vs `"Batch Disposition Code R"` (0.958), `"American Express Insurance, Part 1"`
   vs `"Part 2"` (0.971), codigos de pais como `"(RU) National Settlement, Russia"` vs
   `"(UY) National Settlement, Uruguay"` (0.862). Un umbral fuzzy aca arriesgaria emparejar
   por error 2 filas que en realidad son entidades distintas (ej. tratar la baja de "Code A"
   + el alta de "Code R" como si fuera 1 sola fila "renombrada"), escondiendo exactamente el
   tipo de cambio estructural que el proyecto existe para exponer. Tampoco alcanza usar el
   TCR solo como contexto para acotar el fuzzy: el caso `"Batch Disposition Code A/R/X"`
   completo comparte el MISMO TCR (`TCR 0`), asi que acotar por TCR no evita la colision.
   Tampoco alcanza usar la descripcion sola como clave exacta (sin TCR): confirmado real que
   `"BASE II Clearing and Settlement Advice"` aparece 2 veces en `"33 Multipurpose Message"`
   con el MISMO texto exacto pero bajo TCR distinto (`TCR 0` y `TCR 1`) -la clave necesita
   ambos campos juntos. Confirmado empiricamente que la clave compuesta completa (TCR
   normalizado + descripcion normalizada) no tiene NINGUNA colision en ninguna de las 8
   ediciones disponibles (0 pares con la misma clave dentro de una misma seccion).
   **Consecuencia de este diseno**: como la clave consume TANTO el TCR como la descripcion,
   una fila matcheada por clave exacta es SIEMPRE identica en ambas ediciones por
   construccion -no hay una fase de "diff de contenido" separada como `row_content_changed`/
   `card_content_changed` en los otros manuales; cualquier cambio real (renombre de
   descripcion, reasignacion de TCR) se ve como una baja + un alta, no como un cambio de
   contenido de la misma entidad. Es una perdida de sensibilidad real (un rename se reporta
   como 2 eventos en vez de 1), aceptada deliberadamente en vez de arriesgar falsos positivos
   -mismo principio de "preferir un remove+add honesto antes que adivinar mal" ya aplicado en
   el proyecto (ver la decision de no mitigar el "chain-shift" en el 3er manual).

**Duplicados de clave**: 0 casos reales en las 8 ediciones disponibles, pero se detectan y
reportan igual (`duplicate_row_keys`, mismo patron que `duplicate_row_positions` en los otros
manuales) por si aparecen en una edicion futura -y se emparejan por ORDEN DE APARICION dentro
de la clave repetida (mismo mecanismo ya usado para la seccion `TC 57` duplicada del 4to
manual) en vez de un dict simple que perderia una entrada por colision -defensivo, sin costo
extra para el caso normal (0 duplicados).

Alcance: procesa pares de ediciones CONSECUTIVAS (7 pares para las 8 ediciones de este
manual).
"""

import difflib
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

MANUAL_SLUG = "base_ii_transactions_quick_reference"
INPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "02_normalizacion_bloques"
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "03_emparejamiento_bloques"

FUZZY_TITLE_THRESHOLD = 0.85
WHITESPACE = re.compile(r"\s+")


def _normalize_text(text: str) -> str:
    return WHITESPACE.sub(" ", text).strip().casefold()


def _row_key(cells: list) -> tuple:
    label = _normalize_text(cells[0])
    description = _normalize_text(cells[1]) if len(cells) > 1 else ""
    return (label, description)


def _find_duplicates(values) -> list:
    seen = {}
    dups = set()
    for v in values:
        seen[v] = seen.get(v, 0) + 1
        if seen[v] > 1:
            dups.add(v)
    return sorted(dups)


def extract_sections(blocks: list) -> list:
    """Reconstruye entradas TC (titulo + filas TCR) a partir de los bloques planos del
    Modulo 2. Contenido antes de la 1ra seccion (portada, aviso legal) se ignora a
    proposito, mismo criterio que los otros 4 manuales."""
    sections = []
    current = None

    for block in blocks:
        if block["type"] == "section_heading":
            if current is not None:
                sections.append(current)
            current = {
                "title": block["text"],
                "title_norm": _normalize_text(block["text"]),
                "rows": [],
            }
            continue
        if current is None:
            continue
        if block["type"] == "table_row":
            current["rows"].append({"key": _row_key(block["cells"]), "cells": block["cells"]})

    if current is not None:
        sections.append(current)

    for section in sections:
        section["duplicate_row_keys"] = _find_duplicates(r["key"] for r in section["rows"])

    return sections


def match_sections(sections_a: list, sections_b: list) -> dict:
    # Titulo de seccion unico por construccion (prefijo de 2 digitos) -dict simple alcanza,
    # a diferencia del emparejamiento de filas mas abajo.
    by_title_a = {s["title_norm"]: s for s in sections_a}
    by_title_b = {s["title_norm"]: s for s in sections_b}

    matched = []
    unmatched_a = dict(by_title_a)
    unmatched_b = dict(by_title_b)

    for title_norm, sec_a in by_title_a.items():
        sec_b = by_title_b.get(title_norm)
        if sec_b is not None:
            matched.append((sec_a, sec_b, "exact", 1.0))
            unmatched_a.pop(title_norm, None)
            unmatched_b.pop(title_norm, None)

    for title_norm_a, sec_a in list(unmatched_a.items()):
        best_ratio = 0.0
        best_title_norm_b = None
        for title_norm_b in unmatched_b:
            ratio = difflib.SequenceMatcher(None, title_norm_a, title_norm_b).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_title_norm_b = title_norm_b
        if best_title_norm_b is not None and best_ratio >= FUZZY_TITLE_THRESHOLD:
            sec_b = unmatched_b.pop(best_title_norm_b)
            matched.append((sec_a, sec_b, "fuzzy", round(best_ratio, 3)))
            unmatched_a.pop(title_norm_a, None)

    return {
        "matched": matched,
        "sections_removed": list(unmatched_a.values()),
        "sections_added": list(unmatched_b.values()),
    }


def match_rows(section_a: dict, section_b: dict) -> dict:
    """Empareja filas TCR por clave EXACTA (TCR+descripcion), sin fallback fuzzy (ver
    docstring del modulo -demostrado inseguro con datos reales). Emparejamiento por orden de
    aparicion dentro de una clave repetida (defensivo, ver docstring)."""
    by_key_a = defaultdict(list)
    for r in section_a["rows"]:
        by_key_a[r["key"]].append(r)
    by_key_b = defaultdict(list)
    for r in section_b["rows"]:
        by_key_b[r["key"]].append(r)

    matched = []
    removed = []
    added = []

    for key in set(by_key_a) | set(by_key_b):
        list_a = by_key_a.get(key, [])
        list_b = by_key_b.get(key, [])
        n = min(len(list_a), len(list_b))
        for ra, rb in zip(list_a[:n], list_b[:n]):
            matched.append({"key": key, "cells_a": ra["cells"], "cells_b": rb["cells"]})
        removed.extend({"key": key, "cells": r["cells"]} for r in list_a[n:])
        added.extend({"key": key, "cells": r["cells"]} for r in list_b[n:])

    sort_key = lambda item: item["key"]
    return {
        "rows_matched": sorted(matched, key=sort_key),
        "rows_removed": sorted(removed, key=sort_key),
        "rows_added": sorted(added, key=sort_key),
    }


def match_edition_pair(data_a: dict, data_b: dict) -> dict:
    sections_a = extract_sections(data_a["blocks"])
    sections_b = extract_sections(data_b["blocks"])

    section_match = match_sections(sections_a, sections_b)

    sections_matched = []
    for sec_a, sec_b, match_type, ratio in section_match["matched"]:
        row_match = match_rows(sec_a, sec_b)
        sections_matched.append(
            {
                "title_a": sec_a["title"],
                "title_b": sec_b["title"],
                "match_type": match_type,
                "fuzzy_ratio": ratio,
                "duplicate_row_keys_a": sec_a["duplicate_row_keys"],
                "duplicate_row_keys_b": sec_b["duplicate_row_keys"],
                **row_match,
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
            {"title": s["title"], "num_rows": len(s["rows"])} for s in section_match["sections_removed"]
        ],
        "sections_added": [
            {"title": s["title"], "num_rows": len(s["rows"])} for s in section_match["sections_added"]
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
        fuzzy = sum(1 for s in result["sections_matched"] if s["match_type"] == "fuzzy")
        print(
            f"{out_name}: secciones {result['num_sections_a']}->{result['num_sections_b']} "
            f"(matched={len(result['sections_matched'])} [fuzzy={fuzzy}], "
            f"added={len(result['sections_added'])}, removed={len(result['sections_removed'])}) | "
            f"filas matched={rows_matched} added={rows_added} removed={rows_removed}"
        )


if __name__ == "__main__":
    main()
