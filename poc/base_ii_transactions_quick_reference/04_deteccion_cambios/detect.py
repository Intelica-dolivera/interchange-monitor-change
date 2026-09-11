"""
Modulo 4 - Deteccion de cambios para el manual base_ii_transactions_quick_reference.

Toma la salida ya emparejada del Modulo 3 (secciones/filas matched/added/removed) y la
convierte en una lista plana de cambios tipados. 100% deterministico (sin IA, eso es Modulo
5 -aunque para este manual en particular, ver mas abajo, puede no hacer falta).

**Mucho mas simple que los otros 4 manuales -consecuencia directa del diseno de Modulo 3, no
una simplificacion arbitraria**: como la clave de emparejamiento de filas (`TCR` + descripcion
normalizados) consume TODO el contenido mutable de una fila, una fila matcheada es SIEMPRE
identica en ambas ediciones por construccion (ver docstring de `match.py`). No existe una
categoria `row_content_changed` para este manual -no hay nada que diferir dentro de una fila
ya emparejada. Cualquier edicion real de una fila (renombre de descripcion, reasignacion de
TCR) ya aparece como `row_removed` + `row_added` separados, resueltos por Modulo 3.

**Este manual tampoco tiene el caso de uso central del proyecto (`field_became_defined`,
Reserved->definido)** -es un indice de codigos TC/TCR con nombre de mensaje, no una grilla de
bytes con campos "Reserved". No aplica aca, ni por analogia forzada: no hay ninguna nocion de
"campo reservado" en un listado de referencia rapida. El valor de este pipeline para este
manual especifico es distinto: rastrear cuando aparece/desaparece/se renombra un TIPO DE
MENSAJE completo (una fila TCR), util como diff de indice/tabla de contenidos de alto nivel,
complementario a (no sustituto de) el rastreo de campos de los otros 4 manuales.

Tipos de cambio emitidos: `section_added`/`section_removed`/`section_renamed` (identico a los
otros manuales), `row_added`/`row_removed` (sin distincion "grilla"/"ficha" -solo hay un tipo
de fila aca), `duplicate_key_warning` (mismo espiritu que `duplicate_position_warning` en los
otros manuales, aviso de confiabilidad si aparece un caso de clave repetida -0 casos reales en
las 8 ediciones disponibles, ver Modulo 3).

Alcance: procesa todos los pares ya generados por el Modulo 3 en
`data/03_emparejamiento_bloques/`.
"""

import json
import sys
from pathlib import Path

_SHARED_DIR = Path(__file__).resolve().parents[2] / "_shared"
if str(_SHARED_DIR) not in sys.path:
    sys.path.insert(0, str(_SHARED_DIR))
from stage_runners import run_detect_main


MANUAL_SLUG = "base_ii_transactions_quick_reference"
INPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "03_emparejamiento_bloques"
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "04_deteccion_cambios"


def detect_changes(match_result: dict) -> dict:
    changes = []

    for section in match_result["sections_added"]:
        changes.append(
            {"change_type": "section_added", "title": section["title"], "num_rows": section["num_rows"]}
        )
    for section in match_result["sections_removed"]:
        changes.append(
            {"change_type": "section_removed", "title": section["title"], "num_rows": section["num_rows"]}
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

        if section["duplicate_row_keys_a"] or section["duplicate_row_keys_b"]:
            changes.append(
                {
                    "change_type": "duplicate_key_warning",
                    "title": title,
                    "duplicate_keys_a": section["duplicate_row_keys_a"],
                    "duplicate_keys_b": section["duplicate_row_keys_b"],
                }
            )

        for row in section["rows_added"]:
            changes.append({"change_type": "row_added", "title": title, "cells": row["cells"]})
        for row in section["rows_removed"]:
            changes.append({"change_type": "row_removed", "title": title, "cells": row["cells"]})

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
