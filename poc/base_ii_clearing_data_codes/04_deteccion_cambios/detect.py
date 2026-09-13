"""
Modulo 4 - Deteccion de cambios para el manual base_ii_clearing_data_codes.

Toma la salida ya emparejada del Modulo 3 (tablas/filas matched/added/removed entre 2
ediciones consecutivas) y la convierte en una lista plana de "cambios" tipados. Modulo 3
ya resolvio el trabajo dificil (que tabla es la misma tabla, que fila es la misma fila);
Modulo 4 solo decide, para cada par ya emparejado, SI hubo un cambio real de contenido y
de que categoria es -sigue siendo trabajo 100% deterministico, sin IA todavia (eso es
Modulo 5, que consume la salida de este modulo).

Categorias de cambio (adaptadas del pipeline de referencia -ver reference_pipeline-vs-
technical-manuals en la memoria del asistente- a este manual, que es de tablas de
codigo/regla, NO de grids posicion/longitud/formato como el Tipo A):

- Nivel tabla: `table_added`, `table_removed`, `table_renamed` (match fuzzy de titulo,
  Modulo 3 ya calculo el ratio).
- Nivel fila (dentro de una tabla ya emparejada): `code_added`, `code_removed`,
  `code_content_changed` (el codigo existe en ambas ediciones pero alguna celda de
  contenido cambio).
- `duplicate_code_warning`: aviso de que una tabla tiene un codigo repetido en alguna de
  las 2 ediciones (Modulo 3 ya lo detecta via `duplicate_codes_a/b`); no es un cambio en
  si, pero indica que el emparejamiento de esa tabla puntual puede no ser 1:1 confiable.

Deteccion de `code_content_changed` (`_diff_row_cells`): compara celda a celda (saltando
la celda 0, el codigo, que por definicion es igual -es la clave del match). Se normaliza
espacios en blanco antes de comparar (los saltos de linea de wraps no deberian contar como
cambio real). Si el texto normalizado es identico, no hay cambio. Si difiere, se calcula
`difflib.SequenceMatcher.ratio()` -mismo mecanismo que el pipeline de referencia usa en su
Stage 5 (`05_diff_descriptors.py`) para decidir si un cambio de texto es "ruido de
extraccion" o real- con el mismo umbral que ese pipeline (0.98): por debajo del umbral se
reporta como `code_content_changed`; por encima se descarta (probablemente reformateo/
espaciado sin cambio real). Deliberadamente NO se intenta clasificar el cambio en "cambio
real de negocio" vs. "solo reescritura editorial" aca -esa es exactamente la frontera de
responsabilidad con el Modulo 5 (interpretacion con IA), que recibe el `similarity_ratio`
como señal de entrada. Si una fila tiene distinta cantidad de celdas entre ediciones (no
deberia pasar dado que Modulo 3 ya filtro tablas fantasma, pero se maneja por las dudas),
se compara solo hasta la cantidad de celdas mas corta y se marca la fila igual.

Alcance: procesa todos los archivos de `data/03_emparejamiento_bloques/` (uno por cada par
de ediciones consecutivas ya generado por el Modulo 3).
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


MANUAL_SLUG = "base_ii_clearing_data_codes"
INPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "03_emparejamiento_bloques"
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "04_deteccion_cambios"

# Mismo umbral que el pipeline de referencia (utils_example/05_diff_descriptors.py) usa
# para decidir si un cambio de texto es ruido de extraccion/reformateo vs. un cambio real.
CONTENT_SIMILARITY_THRESHOLD = 0.98

WHITESPACE = re.compile(r"\s+")
# Mismo patron que ya usa `tc_01_to_tc_49` (ver NOTES.md, 2026-09-13, "fix no portado"): la
# edicion vieja extrae el glifo de vineta de las listas de "Chargeback Reason Rules"/"Error
# Condition"/etc. como la letra "l" suelta, la nueva usa "●" -mismo contenido de negocio,
# glifo distinto. Sin neutralizarlo antes de medir similitud, el glifo (mas el reordenamiento
# de renglones que el fix de Modulo 2 ya corrige en el origen) sigue bajando el ratio lo
# suficiente como para disparar un `code_content_changed` que no es un cambio real.
BULLET_TOKEN_PATTERN = re.compile(r"(?<!\S)[l●](?!\S)")


def _normalize_cell(text: str) -> str:
    return WHITESPACE.sub(" ", text).strip()


def _similarity_text(text: str) -> str:
    return WHITESPACE.sub(" ", BULLET_TOKEN_PATTERN.sub(" ", text)).strip()


def _column_label(header: list, index: int) -> str:
    if header and index < len(header):
        return _normalize_cell(header[index])
    return f"columna {index}"


def _diff_row_cells(code: str, cells_a: list, cells_b: list, header_a: list, header_b: list) -> list:
    changes = []
    shared_len = min(len(cells_a), len(cells_b))
    for i in range(1, shared_len):
        norm_a, norm_b = _normalize_cell(cells_a[i]), _normalize_cell(cells_b[i])
        if norm_a == norm_b:
            continue
        ratio = difflib.SequenceMatcher(None, _similarity_text(norm_a), _similarity_text(norm_b)).ratio()
        if ratio >= CONTENT_SIMILARITY_THRESHOLD:
            continue
        changes.append(
            {
                "change_type": "code_content_changed",
                "code": code,
                "column": _column_label(header_b, i),
                "column_index": i,
                "old": cells_a[i],
                "new": cells_b[i],
                "similarity_ratio": round(ratio, 3),
            }
        )
    return changes


def detect_changes(match_result: dict) -> dict:
    changes = []

    for table in match_result["tables_added"]:
        changes.append(
            {"change_type": "table_added", "table": table["title"], "num_rows": table["num_rows"]}
        )

    for table in match_result["tables_removed"]:
        changes.append(
            {"change_type": "table_removed", "table": table["title"], "num_rows": table["num_rows"]}
        )

    for table in match_result["tables_matched"]:
        table_name = table["title_b"]

        if table["match_type"] == "fuzzy":
            changes.append(
                {
                    "change_type": "table_renamed",
                    "table_a": table["title_a"],
                    "table_b": table["title_b"],
                    "fuzzy_ratio": table["fuzzy_ratio"],
                }
            )

        if table["duplicate_codes_a"] or table["duplicate_codes_b"]:
            changes.append(
                {
                    "change_type": "duplicate_code_warning",
                    "table": table_name,
                    "duplicate_codes_a": table["duplicate_codes_a"],
                    "duplicate_codes_b": table["duplicate_codes_b"],
                }
            )

        for row in table["rows_added"]:
            changes.append(
                {
                    "change_type": "code_added",
                    "table": table_name,
                    "code": row["code"],
                    "cells": row["cells"],
                }
            )

        for row in table["rows_removed"]:
            changes.append(
                {
                    "change_type": "code_removed",
                    "table": table_name,
                    "code": row["code"],
                    "cells": row["cells"],
                }
            )

        for row in table["rows_matched"]:
            row_changes = _diff_row_cells(
                row["code"], row["cells_a"], row["cells_b"], table["header_a"], table["header_b"]
            )
            for change in row_changes:
                change["table"] = table_name
            changes.extend(row_changes)

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
