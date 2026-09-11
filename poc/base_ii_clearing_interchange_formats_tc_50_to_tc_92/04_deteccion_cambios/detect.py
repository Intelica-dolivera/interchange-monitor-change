"""
Modulo 4 - Deteccion de cambios para el manual
base_ii_clearing_interchange_formats_tc_50_to_tc_92.

Mismo diseno que el Modulo 4 del 3er manual, su hermano directo: toma la salida ya
emparejada del Modulo 3 (secciones/filas/fichas matched/added/removed) y la convierte en una
lista plana de cambios tipados, 100% deterministico (sin IA, eso es Modulo 5). Dos listas
paralelas por seccion (filas de grilla + fichas) -> deteccion de contenido 2 veces por
seccion (`row_content_changed` por indice de celda, `card_content_changed` por nombre de
campo `CARD_FIELDS`), sin unificarlas (mismo criterio ya establecido en Modulo 2/3: no se
linkea fila con ficha).

Este modulo no necesito ningun cambio de diseno respecto al 3er manual -opera puramente
sobre la forma ya estable del output de Modulo 3 (identica en los 2 manuales), sin tocar
texto/tipografia especifica del PDF. `field_became_defined`/`field_became_reserved` (subtypes
`"split"` y `"renamed_in_place"`) se detectan con el mismo mecanismo determinista sobre
`rows_removed`/`rows_added`/`rows_matched` y su equivalente de fichas, ya calculados por
Modulo 3 -incluyendo el fix de Modulo 3 para las 2 secciones `"TC 57 - TCR 5 - Limited Use
Data"` (ver docstring de `match.py`): como esa seccion ahora se matchea 2 veces por separado
(1ra copia con 1ra copia, 2da con 2da), este modulo la procesa como 2 secciones normales sin
ningun caso especial.

**Resultado real esperado, confirmado explorando el output de Modulo 3 antes de escribir
este modulo (ver [[open-questions-technical-manuals]] en la memoria del asistente)**: a
diferencia del 3er manual, este manual (capitulos TC 50-92) no tuvo NINGUNA transicion
`Reserved<->definido` -ni por split ni por renamed-in-place, ni en filas ni en fichas- en
ninguno de los 8 pares de ediciones disponibles. `field_became_defined`/`field_became_reserved`
deberian salir en 0 en el summary de las 8 corridas -no es un bug de este modulo, es una
propiedad real de los datos de este rango de capitulos en esta ventana de ediciones.

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


MANUAL_SLUG = "base_ii_clearing_interchange_formats_tc_50_to_tc_92"
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
    posicion (sin split de rango). Devuelve "became_defined", "became_reserved" o None."""
    was_reserved = bool(RESERVED_PATTERN.match(_normalize_text(contents_a)))
    is_reserved = bool(RESERVED_PATTERN.match(_normalize_text(contents_b)))
    if was_reserved and not is_reserved:
        return "became_defined"
    if not was_reserved and is_reserved:
        return "became_reserved"
    return None


def _diff_row_cells(position: str, cells_a: list, cells_b: list) -> list:
    changes = []
    shared_len = min(len(cells_a), len(cells_b), len(GRID_COLUMNS))
    for i in range(1, shared_len):
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


def _diff_card_fields(position: str, card_a: dict, card_b: dict) -> list:
    changes = []
    for field in CARD_FIELDS:
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
                "signature": section["signature"],
                "signature_position": section["signature_position"],
                "num_rows": section["num_rows"],
                "num_cards": section["num_cards"],
            }
        )
    for section in match_result["sections_removed"]:
        changes.append(
            {
                "change_type": "section_removed",
                "title": section["title"],
                "signature": section["signature"],
                "signature_position": section["signature_position"],
                "num_rows": section["num_rows"],
                "num_cards": section["num_cards"],
            }
        )

    for section in match_result["sections_matched"]:
        title = section["title_b"]
        # Item 10/[[pending-bug-fixes]] (resuelto parcialmente 2026-08-25): cuando 2+
        # secciones comparten `title` (ej. las 2 "TC 57 - TCR 5 - Limited Use Data"), sus
        # cambios se verian mezclados bajo el mismo encabezado ambiguo en el reporte. Se
        # etiqueta cada cambio con la `signature` de contenido de su seccion (ver Modulo 3,
        # `_section_signature`) para que Modulo 7 pueda separarlos con una etiqueta legible.
        signature = section.get("signature_b", "")
        signature_position = section.get("signature_position_b", "")
        section_changes_start = len(changes)

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
            row_changes = _diff_row_cells(row["position"], row["cells_a"], row["cells_b"])
            for change in row_changes:
                change["title"] = title
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
            card_changes = _diff_card_fields(card["position"], card["card_a"], card["card_b"])
            for change in card_changes:
                change["title"] = title
            changes.extend(card_changes)

        for change in changes[section_changes_start:]:
            change.setdefault("signature", signature)
            change.setdefault("signature_position", signature_position)

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
