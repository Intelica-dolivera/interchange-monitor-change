"""
Modulo 3 - Emparejamiento de bloques para el manual
base_ii_clearing_interchange_formats_tc_01_to_tc_49.

Toma el stream plano de bloques del Modulo 2 (`section_heading`/`paragraph`/`table_header`/
`table_row`/`field_card`) y reconstruye la entidad real a comparar -una "seccion" TC/TCR,
delimitada por `section_heading`, que contiene DOS listas paralelas de campos: las filas de
la grilla (`table_row`, compactas) y las fichas de detalle (`field_card`). Luego empareja
secciones y, dentro de cada seccion emparejada, sus filas y sus fichas, entre 2 ediciones
consecutivas.

Diseno (ver discusion completa y evidencia empirica en local_memory/NOTES.md):

1. **Reconstruccion de secciones** (`extract_sections`): cada `section_heading` cierra la
   seccion activa y arranca una nueva; los `table_row`/`field_card` que siguen se acumulan
   en sus listas respectivas hasta el proximo `section_heading`. A diferencia del Modulo 3
   del primer manual (donde el TITULO de tabla, un `paragraph`, era la senal de
   continuidad), aca la seccion ya viene delimitada explicitamente por el Modulo 2
   (`section_heading` es su propio tipo de bloque, no un `paragraph` generico) -no hace
   falta re-declarar/coalescer titulos como alli. Confirmado con datos reales: 0 titulos de
   seccion duplicados dentro de una misma edicion, en las 9 ediciones.

2. **NO se enlazan filas de grilla con fichas dentro de este modulo** -deliberado. Ambas
   describen los mismos campos (la grilla es el resumen compacto, las fichas la
   elaboracion), pero encontramos con datos reales que la relacion no siempre es 1:1 -un
   campo compuesto en la grilla (ej. "Acquirer Reference Number", 1 fila, posiciones
   27-49) puede tener una ficha "padre" MAS varias fichas "hijas" por sub-componente (ej.
   "Acquirer Reference Number— Format Code" en la posicion 27 sola, etc.), y no siempre el
   nombre coincide exactamente entre ambas representaciones. Enlazarlas requeriria logica
   adicional no justificada todavia por el objetivo del proyecto (diffear campos, no
   unificar 2 vistas del mismo campo) -mismo criterio de "no sobre-disenar" ya aplicado en
   el proyecto. Se emparejan como DOS problemas paralelos independientes: filas de grilla
   contra filas de grilla, fichas contra fichas -mismo patron ya usado (fila por codigo en
   el manual 1, ficha por codigo en el manual 2), aplicado 2 veces en este modulo en vez de
   una.

3. **Clave de emparejamiento: `Position` (grilla) / `Positions` (ficha), normalizada** -no
   nombre. Mismo principio ya establecido en el proyecto (matchear por clave estable, no
   por nombre fuzzy). La normalizacion solo unifica el caracter de guion/en-dash (`-`/`–`/
   `—` -el PDF fuente mezcla ambos de forma inconsistente ENTRE campos, aunque se confirmo
   empiricamente que el mismo campo nunca cambia de caracter entre ediciones consecutivas
   en las 8 ediciones disponibles -0 matches adicionales al normalizar- se normaliza de
   todas formas como seguro barato, no por necesidad demostrada) y espacios en blanco.

4. **Emparejamiento de secciones (`match_sections`)**: primero exacto por titulo
   normalizado; lo que no matchea exacto se intenta por similitud de texto (`difflib`,
   umbral 0.85), mismo patron que el emparejamiento de tablas del manual 1.

5. **Problema de "chain-shift" (campo que cambia de longitud corre la posicion de todos
   los campos siguientes en el mismo TCR) -RESUELTO (2026-08-26) para filas de grilla.**
   Investigado empiricamente ANTES de decidir el diseno original (no se asumio): comparando
   las 9 ediciones completas (8 pares, 2173 secciones comunes), aparece un chain-shift real
   en 1 sola seccion (`TC 33.A - CP 12 TCR 4 Gateway Data, continuation`, par
   `20240413→20241019` -un campo crecio de 9 a 10 bytes y corrio 2 campos siguientes). El
   otro patron de cambio de posicion, mucho mas comun, NO es chain-shift real: un rango
   `Reserved` (siempre al final del registro) se parte en un campo nuevo + un `Reserved` mas
   chico, sin correr nada antes -confirmado en las 3 secciones no identicas del primer par
   de ediciones. Dada la frecuencia real (0.05% de las secciones), se decidio inicialmente
   (con el usuario, 2026-08-13) NO implementar la mitigacion de ancla ordinal propuesta en el
   diseno original -documentado como TODO de baja prioridad.

   **Implementado despues, a pedido explicito del usuario, confirmando que era bajo riesgo**
   (`_match_shifted_rows`): despues del emparejamiento exacto por posicion, las filas que
   quedan sin matchear en ambos lados de la seccion se intentan alinear por NOMBRE
   (`cells[3]`, "Contents") usando `difflib.SequenceMatcher` sobre la secuencia de nombres de
   cada lado -mismo mecanismo de reconciliacion ya usado en el 6to/7mo manual para el reflow
   de parrafos: toma los tramos "equal" (nombres identicos en el mismo orden relativo en
   ambos lados), aunque haya altas/bajas genuinas intercaladas, en vez de exigir que ambas
   listas de sobrantes tengan la misma longitud total -mas robusto que un simple emparejamiento
   por indice ordinal. **Exclusion critica, confirmada ANTES de implementar (no despues)**:
   cualquier fila cuyo nombre normalizado sea exactamente "Reserved" queda FUERA de este
   emparejamiento -el patron "Reserved se parte en campo nuevo + Reserved mas chico" tambien
   corre la posicion del `Reserved` restante (su propio inicio se mueve, igual que en un
   chain-shift real), y el nombre "Reserved" se repite tal cual en ambos lados -sin esta
   exclusion, este mecanismo hubiera emparejado el `Reserved` viejo con el `Reserved` nuevo del
   split ANTES de que Modulo 4 pudiera verlos en `rows_removed`/`rows_added`, rompiendo
   silenciosamente `_detect_reserved_splits` (el mecanismo, mas especifico, que Modulo 4 ya usa
   para este caso de uso central del proyecto -ver docstring de `detect.py`). Confirmado con el
   caso real: de los 3 campos afectados en `TC 33.A - CP 12 TCR 4 Gateway Data, continuation`,
   los 2 con nombre real (`Mastercard - Service Location Postal Code`,
   `Mastercard Transaction Link Identifier/...`) se re-emparejan correctamente como 1 fila
   "movida" cada uno (con `position_a`/`position_b` distintos); el 3er campo (`Reserved`, que
   tambien se corrio y encogio 1 byte como consecuencia) queda EXCLUIDO deliberadamente y sigue
   viendose como `row_removed`+`row_added` separado, igual que antes -residuo aceptado, de bajo
   valor informativo (nadie necesita saber que `Reserved` perdio 1 byte, ya se infiere del
   resize del campo anterior). Filas emparejadas por este mecanismo llevan `matched_by:
   "position_shift"` + `position_a`/`position_b` explicitos (a diferencia de un match exacto,
   que solo tiene `position`) -Modulo 4 usa esto para tambien diffear la celda `Position`
   (normalmente saltatada porque es la clave del match, ver docstring de `detect.py`).

   **Alcance de este fix: solo filas de grilla (`match_rows`), NO fichas (`match_cards`).**
   Investigado si aplicaba igual a fichas antes de decidir: el caso real de chain-shift
   tambien aparece en las fichas de esta misma seccion, pero el campo `name` de la ficha NO
   es siempre byte-identico entre ediciones para el mismo campo (ej. `"character Mastercard -
   Service Location Postal Code"` -> `"character Mastercard Service Location Postal Code"`,
   el guion se cae) -un emparejamiento EXACTO por nombre (el mismo usado para filas, seguro
   porque `Contents` en la grilla SI es byte-identico en el caso real) fallaria aca, y uno
   FUZZY necesitaria su propia calibracion/validacion de umbral antes de confiar en el -no
   investigado, fuera de alcance de esta sesion. Fichas siguen sin mitigacion para chain-shift
   (mismo comportamiento que antes).

   **Extendido a fichas (2026-09-05), sin fuzzy-matching genuino.** Medido antes de implementar
   (misma disciplina de siempre): escaneando los 8 pares completos, ya habia 6 pares de fichas
   sobrantes con nombre EXACTAMENTE identico (serian recuperables solo con el mismo mecanismo
   `SequenceMatcher` de `_match_shifted_rows`, sin tocar nada mas) mas exactamente 1 caso donde
   solo difieren por un guion (`"character Mastercard - Service Location Postal Code"` vs
   `"character Mastercard Service Location Postal Code"` -el caso ya conocido). **En vez de
   fuzzy-matching por ratio (el enfoque descartado antes, que necesitaria su propia calibracion
   de umbral y arriesga el mismo problema de "texto libre a nivel de fila" ya documentado como
   inseguro en [[dev-phase-considerations]] punto 2)**, la solucion resulto ser una NORMALIZACION
   de texto especifica y ya segura en este mismo archivo: `DASH_CHARS` (ya usado en
   `_normalize_position` para unificar variantes de guion) aplicado al nombre de la ficha antes
   de comparar por IGUALDAD EXACTA -mismo mecanismo `SequenceMatcher` que ya usan las filas, solo
   alimentado con nombres normalizados en vez de crudos. Confirmado que esto NO genera ninguna
   colision nueva: de los 7 pares recuperados en todo el corpus (6 exactos + 1 solo-diferia-por-
   guion), 0 son falsos positivos -es la MISMA seguridad que ya tiene el mecanismo de filas,
   simplemente aplicada a un campo cuyo unico patron real de variacion (un guion que a veces cae)
   ya se conocia y ya estaba resuelto en otro lugar del mismo archivo. Fichas emparejadas asi
   llevan `matched_by: "position_shift"` + `position_a`/`position_b`, igual que filas.

6. **Codigos duplicados**: se detectan y reportan por separado (`duplicate_row_positions`/
   `duplicate_card_positions`), mismo patron que los otros 2 manuales -no se sobreescriben
   silenciosamente. Encontrado un caso real de duplicacion LEGITIMA (no bug): la seccion
   `TC 39 - TCR 4 VDAS Forms Data, Exhibit Y or Exhibit 3C` tiene filas con `Format="Group"`
   que introducen sub-estructuras ALTERNATIVAS (ej. "Lodging Merchant" vs "Vehicle Leasing
   Merchant", ambas ocupando las mismas posiciones 12-68 porque son interpretaciones
   mutuamente excluyentes del mismo rango de bytes segun el tipo de formulario) -confirmado
   real leyendo el PDF, no arreglado (no hay nada que arreglar, es la aviso de
   confiabilidad haciendo su trabajo).

Alcance: procesa pares de ediciones CONSECUTIVAS (8 pares para las 9 ediciones de este
manual).
"""

import difflib
import json
import re
import sys
from pathlib import Path

MANUAL_SLUG = "base_ii_clearing_interchange_formats_tc_01_to_tc_49"
INPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "02_normalizacion_bloques"
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "03_emparejamiento_bloques"

FUZZY_TITLE_THRESHOLD = 0.85
WHITESPACE = re.compile(r"\s+")
DASH_CHARS = re.compile(r"[‐-―]")

# Guion usado como separador de palabras en el nombre de una ficha (ej. "Mastercard -
# Service Location Postal Code"), distinto de `DASH_CHARS` de arriba -ese cubre variantes
# Unicode de guion (para normalizar rangos de posicion), este cubre el guion ASCII comun
# ("-", U+002D) que SI aparece en nombres de ficha reales y que `DASH_CHARS` (rango
# U+2010-U+2015) nunca matchea. Ver `_card_name`, punto 5 del docstring del modulo.
NAME_SEPARATOR_DASH = re.compile(r"\s*[-‐-―]\s*")
RESERVED_NAME = re.compile(r"^reserved$", re.IGNORECASE)


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
    return sorted(dups, key=_position_sort_key)


def extract_sections(blocks: list) -> list:
    """Reconstruye secciones TC/TCR (titulo + filas de grilla + fichas) a partir de los
    bloques planos del Modulo 2."""
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
            # Contenido antes de la 1ra seccion (portada, aviso legal, indice, intro de
            # capitulo) -no pertenece a ninguna seccion, se ignora a proposito.
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

    return sections


def match_sections(sections_a: list, sections_b: list) -> dict:
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


def _row_name(row: dict) -> str:
    cells = row["cells"]
    return _normalize_title(cells[3]) if len(cells) > 3 else ""


def _match_shifted_rows(removed_leftover: list, added_leftover: list) -> tuple:
    """Empareja filas que cambiaron de POSICION pero son el mismo campo logico -mitigacion
    de "chain-shift" (ver punto 5 del docstring del modulo para el analisis completo).
    Devuelve (pares_matched, ids_consumidos_de_a, ids_consumidos_de_b)."""
    candidates_a = [r for r in removed_leftover if not RESERVED_NAME.match(_row_name(r))]
    candidates_b = [r for r in added_leftover if not RESERVED_NAME.match(_row_name(r))]
    if not candidates_a or not candidates_b:
        return [], set(), set()

    names_a = [_row_name(r) for r in candidates_a]
    names_b = [_row_name(r) for r in candidates_b]
    sm = difflib.SequenceMatcher(None, names_a, names_b, autojunk=False)

    matched = []
    consumed_a, consumed_b = set(), set()
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag != "equal":
            continue
        for k in range(i2 - i1):
            row_a = candidates_a[i1 + k]
            row_b = candidates_b[j1 + k]
            matched.append(
                {
                    "position": row_b["position"],
                    "position_a": row_a["position"],
                    "position_b": row_b["position"],
                    "matched_by": "position_shift",
                    "cells_a": row_a["cells"],
                    "cells_b": row_b["cells"],
                }
            )
            consumed_a.add(id(row_a))
            consumed_b.add(id(row_b))
    return matched, consumed_a, consumed_b


def match_rows(section_a: dict, section_b: dict) -> dict:
    rows_a = {r["position"]: r for r in section_a["rows"]}
    rows_b = {r["position"]: r for r in section_b["rows"]}

    matched_positions = set(rows_a) & set(rows_b)
    removed_leftover = [r for r in section_a["rows"] if r["position"] not in matched_positions]
    added_leftover = [r for r in section_b["rows"] if r["position"] not in matched_positions]

    shift_matched, consumed_a, consumed_b = _match_shifted_rows(removed_leftover, added_leftover)

    matched = sorted(matched_positions, key=_position_sort_key)
    removed = sorted(
        (r["position"] for r in removed_leftover if id(r) not in consumed_a),
        key=_position_sort_key,
    )
    added = sorted(
        (r["position"] for r in added_leftover if id(r) not in consumed_b),
        key=_position_sort_key,
    )

    rows_matched = [
        {"position": p, "cells_a": rows_a[p]["cells"], "cells_b": rows_b[p]["cells"]}
        for p in matched
    ]
    rows_matched.extend(shift_matched)

    return {
        "rows_matched": rows_matched,
        "rows_removed": [{"position": p, "cells": rows_a[p]["cells"]} for p in removed],
        "rows_added": [{"position": p, "cells": rows_b[p]["cells"]} for p in added],
    }


def _card_name(entry: dict) -> str:
    # NAME_SEPARATOR_DASH (no DASH_CHARS -ese solo cubre variantes Unicode de guion, nunca el
    # guion ASCII comun que realmente aparece en el caso real, "Mastercard - Service...") quita
    # un guion usado como separador de palabras (con espacio de por medio), no cualquier guion.
    return _normalize_title(NAME_SEPARATOR_DASH.sub(" ", entry["card"].get("name", "")))


def _match_shifted_cards(removed_leftover: list, added_leftover: list) -> tuple:
    """Version para fichas de `_match_shifted_rows` (ver punto 5 del docstring del modulo,
    "Extendido a fichas"): mismo mecanismo `SequenceMatcher` sobre nombres exactos, alimentado
    con `_card_name` (normaliza guiones) en vez de nombre crudo. `removed_leftover`/
    `added_leftover` son entradas `{"position": ..., "card": ...}` (mismo formato que
    `section["cards"]`). Devuelve (pares_matched, ids_consumidos_de_a, ids_consumidos_de_b)."""
    candidates_a = [e for e in removed_leftover if not RESERVED_NAME.match(_card_name(e))]
    candidates_b = [e for e in added_leftover if not RESERVED_NAME.match(_card_name(e))]
    if not candidates_a or not candidates_b:
        return [], set(), set()

    names_a = [_card_name(e) for e in candidates_a]
    names_b = [_card_name(e) for e in candidates_b]
    sm = difflib.SequenceMatcher(None, names_a, names_b, autojunk=False)

    matched = []
    consumed_a, consumed_b = set(), set()
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag != "equal":
            continue
        for k in range(i2 - i1):
            entry_a = candidates_a[i1 + k]
            entry_b = candidates_b[j1 + k]
            matched.append(
                {
                    "position": entry_b["position"],
                    "position_a": entry_a["position"],
                    "position_b": entry_b["position"],
                    "matched_by": "position_shift",
                    "card_a": entry_a["card"],
                    "card_b": entry_b["card"],
                }
            )
            consumed_a.add(id(entry_a))
            consumed_b.add(id(entry_b))
    return matched, consumed_a, consumed_b


def match_cards(section_a: dict, section_b: dict) -> dict:
    cards_a = {c["position"]: c["card"] for c in section_a["cards"]}
    cards_b = {c["position"]: c["card"] for c in section_b["cards"]}

    matched_positions = set(cards_a) & set(cards_b)
    removed_leftover = [
        {"position": p, "card": cards_a[p]} for p in cards_a if p not in matched_positions
    ]
    added_leftover = [
        {"position": p, "card": cards_b[p]} for p in cards_b if p not in matched_positions
    ]

    shift_matched, consumed_a, consumed_b = _match_shifted_cards(removed_leftover, added_leftover)

    matched = sorted(matched_positions, key=_position_sort_key)
    removed = sorted(
        (e["position"] for e in removed_leftover if id(e) not in consumed_a),
        key=_position_sort_key,
    )
    added = sorted(
        (e["position"] for e in added_leftover if id(e) not in consumed_b),
        key=_position_sort_key,
    )

    cards_matched = [
        {"position": p, "card_a": cards_a[p], "card_b": cards_b[p]} for p in matched
    ]
    cards_matched.extend(shift_matched)

    return {
        "cards_matched": cards_matched,
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

    return {
        "manual": MANUAL_SLUG,
        "edition_a": data_a["edition_date"],
        "edition_b": data_b["edition_date"],
        "num_sections_a": len(sections_a),
        "num_sections_b": len(sections_b),
        "sections_matched": sections_matched,
        "sections_removed": [
            {"title": s["title"], "num_rows": len(s["rows"]), "num_cards": len(s["cards"])}
            for s in section_match["sections_removed"]
        ],
        "sections_added": [
            {"title": s["title"], "num_rows": len(s["rows"]), "num_cards": len(s["cards"])}
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
