"""
Modulo 4 - Deteccion de cambios para el manual
base_ii_clearing_interchange_formats_tc_01_to_tc_49.

Toma la salida ya emparejada del Modulo 3 (secciones/filas de grilla/fichas matched/added/
removed) y la convierte en una lista plana de cambios tipados -mismo principio de
separacion de responsabilidades que los otros 2 manuales: Modulo 3 ya resolvio que fila/
ficha es la misma entidad; Modulo 4 solo decide si hubo cambio de contenido real y de que
categoria. Sigue siendo 100% deterministico, sin IA (eso es Modulo 5).

**Filas emparejadas por "chain-shift" (2026-08-26, ver Modulo 3 punto 5 para el diseno
completo)**: `_match_shifted_rows` en Modulo 3 empareja filas que cambiaron de POSICION pero
son el mismo campo (`matched_by: "position_shift"`, con `position_a`/`position_b`
explicitos en vez de un solo `position`). Para estas filas (y SOLO para estas -el resto
sigue sin diffear la celda 0, ya que normalmente es la clave del match, identica por
construccion), `_diff_row_cells` tambien diffea `Position` (`start_index=0`), para que el
cambio de rango de bytes -la senal central del chain-shift- quede reportado como parte del
mismo `row_content_changed`, en vez de perderse silenciosamente.

**Fichas emparejadas por "chain-shift" (2026-09-05, extension del mecanismo de arriba a
`match_cards`)**: mismo `matched_by: "position_shift"`, mismo tratamiento -`_diff_card_fields`
tambien diffea `positions` (normalmente excluido de `CARD_FIELDS` por ser la clave del match)
solo para estas fichas.

Diferencia de diseno respecto a los otros 2 manuales: esta manual tiene DOS listas
paralelas por seccion (filas de grilla + fichas, ver Modulo 3), asi que la deteccion de
cambios de contenido se hace 2 veces por seccion -una para filas (`row_content_changed`,
diff por indice de celda, mismo mecanismo que el manual 1) y otra para fichas
(`card_content_changed`, diff por nombre de campo, mismo mecanismo que el manual 2)- sin
intentar unificarlas (mismo criterio ya establecido en Modulo 3: no se linkea fila con
ficha, se tratan como 2 problemas independientes).

**Categoria nueva, especifica de este manual: `field_became_defined`.** Es el caso de uso
central del proyecto (ver project_overview en la memoria del asistente): un rango
`Reserved` se parte en un campo nuevo con nombre real + un `Reserved` mas chico. Detectado
deterministicamente (`_detect_reserved_splits`) buscando, dentro de los `rows_removed`/
`cards_removed` y `rows_added`/`cards_added` YA calculados por el Modulo 3 (no hace falta
re-emparejar nada), una fila/ficha removida cuyo contenido es literalmente "Reserved" cuyo
rango de posiciones CONTIENE el rango de una o mas filas/fichas agregadas, con al menos una
de ellas empezando en la MISMA posicion inicial que el Reserved removido y con contenido
que YA NO es "Reserved" -confirmado con datos reales (ver Modulo 3, NOTES.md) que el patron
real de Visa es tallar el campo nuevo del INICIO del rango Reserved existente, nunca del
medio o el final. Sin esta deteccion, cada caso de este tipo se veria como 2-3
`row_added`/`row_removed` sueltos sin ninguna relacion aparente entre si -perdiendo
exactamente la senal que el proyecto existe para capturar. Los added/removed consumidos por
un split detectado NO se reportan tambien como `row_added`/`row_removed` sueltos (se
consumen, no se duplican). Este es el `subtype` `"split"`.

**2do subtype de `field_became_defined`, mas simple: `"renamed_in_place"`.** Encontrado
leyendo contenido real del Modulo 4 (no en la exploracion previa): a veces el rango
`Reserved` completo se renombra a un campo real SIN partirse -mismo rango de posiciones en
ambas ediciones, solo cambia el `Contents`/`name` (ej. "TC 05 - TCR 2 Colombia", `5-16
Reserved` -> `5-16 Tip Amount`). Como el rango no cambia, Modulo 3 ya empareja la fila/
ficha por posicion exacta -esto se detecta directo en `rows_matched`/`cards_matched`
(`_reserved_transition`), no con el mismo mecanismo de added/removed que el subtype
`"split"`. Se chequea ANTES de caer en el diff generico de celda/campo, para que este caso
central del proyecto no quede escondido como un `row_content_changed`/`card_content_changed`
mas. Simetricamente, se agrega tambien `field_became_reserved` (el caso inverso: un campo
real se retira y su rango pasa a `Reserved`) -mismo mecanismo, mismo nivel de señal, aunque
no es el caso de uso central del proyecto.

Deteccion de `row_content_changed`/`card_content_changed`: mismo umbral de similitud 0.98
(`difflib.SequenceMatcher`) que los otros 2 manuales, para descartar diferencias de solo
formato/espaciado. Columnas de la grilla fijas (`Position`/`Field Length`/`Format`/
`Contents`, siempre en ese orden -confirmado en Modulo 2, `GRID_HEADER_OUTPUT_CELLS`); se
saltea la celda 0 (`Position`, ya es la clave del match). Campos de ficha:
`name`/`length`/`format`/`description`/`note`/`values`/`mapping` (se saltea `positions`,
tambien la clave del match).

Alcance: procesa todos los pares ya generados por el Modulo 3 en
`data/03_emparejamiento_bloques/`.
"""

import difflib
import json
import re
import sys
from pathlib import Path

_SHARED_DIR = Path(__file__).resolve().parents[2] / "_shared"
if str(_SHARED_DIR) not in sys.path:
    sys.path.insert(0, str(_SHARED_DIR))
from stage_runners import run_detect_main


MANUAL_SLUG = "base_ii_clearing_interchange_formats_tc_01_to_tc_49"
INPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "03_emparejamiento_bloques"
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "04_deteccion_cambios"

CONTENT_SIMILARITY_THRESHOLD = 0.98
WHITESPACE = re.compile(r"\s+")

GRID_COLUMNS = ["Position", "Field Length", "Format", "Contents"]
CARD_FIELDS = ["name", "length", "format", "description", "note", "values", "mapping"]

RESERVED_PATTERN = re.compile(r"^reserved$", re.IGNORECASE)
POSITION_RANGE = re.compile(r"^(\d+)(?:-(\d+))?$")


def _normalize_text(text: str) -> str:
    return WHITESPACE.sub(" ", text).strip()


def _parse_range(position: str):
    m = POSITION_RANGE.match(position.strip())
    if not m:
        return None, None
    start = int(m.group(1))
    end = int(m.group(2)) if m.group(2) else start
    return start, end


def _detect_reserved_splits(removed_items: list, added_items: list, contents_key) -> tuple:
    """Busca el patron 'Reserved se parte en campo(s) nuevo(s) + Reserved mas chico'.
    `contents_key(item)` devuelve el texto de contenido/nombre del item (distinto para
    filas -cells[3]- y fichas -name-). Devuelve (splits, ids_de_added_consumidos)."""
    splits = []
    consumed_added_ids = set()

    for removed in removed_items:
        contents = _normalize_text(contents_key(removed))
        if not RESERVED_PATTERN.match(contents):
            continue
        start_r, end_r = _parse_range(removed["position"])
        if start_r is None:
            continue

        contained = []
        for added in added_items:
            start_a, end_a = _parse_range(added["position"])
            if start_a is None:
                continue
            if start_r <= start_a and end_a <= end_r:
                contained.append(added)

        new_fields = [
            a
            for a in contained
            if _parse_range(a["position"])[0] == start_r
            and not RESERVED_PATTERN.match(_normalize_text(contents_key(a)))
        ]
        if not new_fields:
            continue

        splits.append({"removed": removed, "new_fields": new_fields, "contained": contained})
        for a in contained:
            consumed_added_ids.add(id(a))

    return splits, consumed_added_ids


def _reserved_transition(contents_a: str, contents_b: str) -> str:
    """Detecta la transicion Reserved<->definido para una fila/ficha ya emparejada por
    posicion (sin split de rango, ver docstring del modulo -esto es el sub-caso mas
    simple: el mismo rango de posiciones, solo cambia el contenido). Devuelve
    "became_defined", "became_reserved" o None."""
    was_reserved = bool(RESERVED_PATTERN.match(_normalize_text(contents_a)))
    is_reserved = bool(RESERVED_PATTERN.match(_normalize_text(contents_b)))
    if was_reserved and not is_reserved:
        return "became_defined"
    if not was_reserved and is_reserved:
        return "became_reserved"
    return None


def _diff_row_cells(position: str, cells_a: list, cells_b: list, start_index: int = 1) -> list:
    """`start_index=1` salta la celda 0 (`Position`) porque normalmente ES la clave del
    match -identica por construccion. Las filas emparejadas por `_match_shifted_rows`
    (Modulo 3, mitigacion de "chain-shift") son la excepcion: su posicion SI cambio (esa es
    la senal que se quiere reportar), asi que Modulo 4 les pasa `start_index=0` para
    diffear tambien esa celda -ver `detect_changes`, chequeo de `matched_by`."""
    changes = []
    shared_len = min(len(cells_a), len(cells_b), len(GRID_COLUMNS))
    for i in range(start_index, shared_len):
        norm_a, norm_b = _normalize_text(cells_a[i]), _normalize_text(cells_b[i])
        if norm_a == norm_b:
            continue
        ratio = difflib.SequenceMatcher(None, norm_a, norm_b).ratio()
        if ratio >= CONTENT_SIMILARITY_THRESHOLD:
            continue
        changes.append(
            {
                "change_type": "row_content_changed",
                "position": position,
                "column": GRID_COLUMNS[i],
                "old": cells_a[i],
                "new": cells_b[i],
                "similarity_ratio": round(ratio, 3),
            }
        )
    return changes


def _diff_card_fields(position: str, card_a: dict, card_b: dict, include_positions: bool = False) -> list:
    changes = []
    fields = ["positions"] + CARD_FIELDS if include_positions else CARD_FIELDS
    for field in fields:
        norm_a, norm_b = _normalize_text(card_a.get(field, "")), _normalize_text(card_b.get(field, ""))
        if norm_a == norm_b:
            continue
        ratio = difflib.SequenceMatcher(None, norm_a, norm_b).ratio()
        if ratio >= CONTENT_SIMILARITY_THRESHOLD:
            continue
        changes.append(
            {
                "change_type": "card_content_changed",
                "position": position,
                "field": field,
                "old": norm_a,
                "new": norm_b,
                "similarity_ratio": round(ratio, 3),
            }
        )
    return changes


def detect_changes(match_result: dict) -> dict:
    changes = []

    for section in match_result["sections_added"]:
        changes.append(
            {
                "change_type": "section_added",
                "title": section["title"],
                "num_rows": section["num_rows"],
                "num_cards": section["num_cards"],
            }
        )
    for section in match_result["sections_removed"]:
        changes.append(
            {
                "change_type": "section_removed",
                "title": section["title"],
                "num_rows": section["num_rows"],
                "num_cards": section["num_cards"],
            }
        )

    for section in match_result["sections_matched"]:
        title = section["title_b"]

        if section["match_type"] == "fuzzy":
            changes.append(
                {
                    "change_type": "section_renamed",
                    "title_a": section["title_a"],
                    "title_b": section["title_b"],
                    "fuzzy_ratio": section["fuzzy_ratio"],
                }
            )

        if section["duplicate_row_positions_a"] or section["duplicate_row_positions_b"]:
            changes.append(
                {
                    "change_type": "duplicate_position_warning",
                    "title": title,
                    "kind": "row",
                    "duplicate_positions_a": section["duplicate_row_positions_a"],
                    "duplicate_positions_b": section["duplicate_row_positions_b"],
                }
            )
        if section["duplicate_card_positions_a"] or section["duplicate_card_positions_b"]:
            changes.append(
                {
                    "change_type": "duplicate_position_warning",
                    "title": title,
                    "kind": "card",
                    "duplicate_positions_a": section["duplicate_card_positions_a"],
                    "duplicate_positions_b": section["duplicate_card_positions_b"],
                }
            )

        row_splits, row_consumed = _detect_reserved_splits(
            section["rows_removed"], section["rows_added"], lambda r: r["cells"][3]
        )
        for split in row_splits:
            changes.append(
                {
                    "change_type": "field_became_defined",
                    "kind": "row",
                    "subtype": "split",
                    "title": title,
                    "removed_position": split["removed"]["position"],
                    "removed_cells": split["removed"]["cells"],
                    "new_fields": [
                        {"position": f["position"], "cells": f["cells"]} for f in split["new_fields"]
                    ],
                    "remaining_reserved": [
                        {"position": c["position"], "cells": c["cells"]}
                        for c in split["contained"]
                        if not any(c is nf for nf in split["new_fields"])
                    ],
                }
            )

        card_splits, card_consumed = _detect_reserved_splits(
            section["cards_removed"], section["cards_added"], lambda c: c["card"]["name"]
        )
        for split in card_splits:
            changes.append(
                {
                    "change_type": "field_became_defined",
                    "kind": "card",
                    "subtype": "split",
                    "title": title,
                    "removed_position": split["removed"]["position"],
                    "removed_card": split["removed"]["card"],
                    "new_fields": [{"position": f["position"], "card": f["card"]} for f in split["new_fields"]],
                    "remaining_reserved": [
                        {"position": c["position"], "card": c["card"]}
                        for c in split["contained"]
                        if not any(c is nf for nf in split["new_fields"])
                    ],
                }
            )

        for row in section["rows_added"]:
            if id(row) in row_consumed:
                continue
            changes.append({"change_type": "row_added", "title": title, "position": row["position"], "cells": row["cells"]})
        for row in section["rows_removed"]:
            if any(row is split["removed"] for split in row_splits):
                continue
            changes.append({"change_type": "row_removed", "title": title, "position": row["position"], "cells": row["cells"]})
        for row in section["rows_matched"]:
            transition = _reserved_transition(row["cells_a"][3], row["cells_b"][3])
            if transition:
                changes.append(
                    {
                        "change_type": f"field_{transition}",
                        "kind": "row",
                        "subtype": "renamed_in_place",
                        "title": title,
                        "position": row["position"],
                        "cells_a": row["cells_a"],
                        "cells_b": row["cells_b"],
                    }
                )
                continue
            is_shift = row.get("matched_by") == "position_shift"
            row_changes = _diff_row_cells(
                row["position"], row["cells_a"], row["cells_b"], start_index=0 if is_shift else 1
            )
            for change in row_changes:
                change["title"] = title
                if is_shift:
                    change["matched_by"] = "position_shift"
            changes.extend(row_changes)

        for card in section["cards_added"]:
            if id(card) in card_consumed:
                continue
            changes.append(
                {"change_type": "card_added", "title": title, "position": card["position"], "card": card["card"]}
            )
        for card in section["cards_removed"]:
            if any(card is split["removed"] for split in card_splits):
                continue
            changes.append(
                {"change_type": "card_removed", "title": title, "position": card["position"], "card": card["card"]}
            )
        for card in section["cards_matched"]:
            transition = _reserved_transition(card["card_a"]["name"], card["card_b"]["name"])
            if transition:
                changes.append(
                    {
                        "change_type": f"field_{transition}",
                        "kind": "card",
                        "subtype": "renamed_in_place",
                        "title": title,
                        "position": card["position"],
                        "card_a": card["card_a"],
                        "card_b": card["card_b"],
                    }
                )
                continue
            is_shift = card.get("matched_by") == "position_shift"
            card_changes = _diff_card_fields(
                card["position"], card["card_a"], card["card_b"], include_positions=is_shift
            )
            for change in card_changes:
                change["title"] = title
                if is_shift:
                    change["matched_by"] = "position_shift"
            changes.extend(card_changes)

    summary = {}
    for change in changes:
        summary[change["change_type"]] = summary.get(change["change_type"], 0) + 1

    return {
        "manual": MANUAL_SLUG,
        "edition_a": match_result["edition_a"],
        "edition_b": match_result["edition_b"],
        "summary": summary,
        "changes": changes,
    }


def main():
    run_detect_main(INPUT_DIR, OUTPUT_DIR, detect_changes)


if __name__ == "__main__":
    main()
