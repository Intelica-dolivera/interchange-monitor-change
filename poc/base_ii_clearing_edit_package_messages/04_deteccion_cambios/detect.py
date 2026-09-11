"""
Modulo 4 - Deteccion de cambios para el manual base_ii_clearing_edit_package_messages.

Toma la salida ya emparejada del Modulo 3 (fichas matched/added/removed entre 2 ediciones
consecutivas) y la convierte en una lista plana de "cambios" tipados. Modulo 3 ya resolvio
el trabajo dificil (que ficha es la misma ficha, por codigo exacto); Modulo 4 solo decide,
para cada ficha ya emparejada, SI hubo un cambio real de contenido y en que campo -sigue
siendo trabajo 100% deterministico, sin IA todavia (eso es Modulo 5, que consume la salida
de este modulo). Mismo principio de separacion de responsabilidades que el Modulo 4 del
otro manual.

Diferencia de diseno respecto al Modulo 4 de `base_ii_clearing_data_codes`: ese manual
tiene tablas con columnas posicionales (celda 0 = codigo, celdas 1..N = contenido variable
segun la tabla); este manual no tiene tablas ni columnas -cada ficha tiene siempre el mismo
conjunto FIJO de 4 campos con nombre (`title`, `description`, `action`,
`transaction_types`), asi que ac치 se diffea por nombre de campo en vez de por indice de
celda. Los 3 primeros son texto libre; `transaction_types` es una lista de items (viene como
lista de listas del Modulo 3 -uno por bloque `bullet_list`, casi siempre 0 o 1- y se aplana
a una sola lista antes de comparar).

Deteccion de `ficha_content_changed` (`_diff_ficha_fields`): cada campo se reduce a un
string canonico (listas -> join con espacio) y se compara con `difflib.SequenceMatcher`,
mismo mecanismo y mismo umbral (0.98) que el Modulo 4 del otro manual usa para descartar
ruido de formato/espaciado vs. cambios reales -validado con datos reales de este manual
antes de fijar el umbral: diffs conocidos de solo espaciado (ej. `"1- character"` ->
`"1-character"`, ratio 0.995) quedan por encima del umbral y se descartan, mientras que
cambios de contenido genuino conocidos (ej. ficha `V0173`, "less than" -> "less than or
equal to", ratio 0.948; ficha `V0180`, typo "Credti"->"Credit" dentro de un item de
`transaction_types`, ratio 0.927) quedan por debajo y se reportan. Deliberadamente NO se
intenta distinguir aca que change reformulacion editorial vs. cambio de regla de negocio
-esa es la frontera de responsabilidad con el Modulo 5, que recibe `similarity_ratio` como
señal de entrada, igual que en el otro manual.

No hay categorias de nivel "tabla" (`table_added`/`table_removed`/`table_renamed`) porque
no existe ese nivel intermedio en este manual -solo `ficha_added`/`ficha_removed`/
`ficha_content_changed`. `duplicate_code_warning` se mantiene igual en espiritu pero a nivel
de EDICION completa (Modulo 3 ya lo calcula asi, `duplicate_codes_a`/`duplicate_codes_b`
sobre todas las fichas, no por tabla, porque no hay tablas) en vez de por tabla.

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


MANUAL_SLUG = "base_ii_clearing_edit_package_messages"
INPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "03_emparejamiento_bloques"
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "04_deteccion_cambios"

# Mismo umbral que el Modulo 4 de base_ii_clearing_data_codes (y que el pipeline de
# referencia, utils_example/05_diff_descriptors.py) para decidir si un cambio de texto es
# ruido de formato/espaciado vs. un cambio real. Validado contra datos reales de este
# manual (ver docstring del modulo).
CONTENT_SIMILARITY_THRESHOLD = 0.98

WHITESPACE = re.compile(r"\s+")

FIELDS = ["title", "description", "action", "transaction_types"]


def _normalize_text(text: str) -> str:
    return WHITESPACE.sub(" ", text).strip()


def _flatten_field(value, field: str) -> str:
    if field == "title":
        return _normalize_text(value or "")
    if field == "transaction_types":
        # value es lista de listas (una por bloque bullet_list, casi siempre 0 o 1) -se
        # aplana a una sola lista de items antes de unir en un string comparable.
        items = [item for group in value for item in group]
        return _normalize_text(" | ".join(items))
    # description / action: lista de strings (mas de 1 elemento solo en el caso conocido
    # de un campo duplicado en la fuente, ej. V0545 -se preserva la duplicacion en el
    # string canonico, no se deduplica).
    return _normalize_text(" ".join(value))


def _diff_ficha_fields(ficha: dict) -> list:
    changes = []
    for field in FIELDS:
        text_a = _flatten_field(ficha[f"{field}_a"], field)
        text_b = _flatten_field(ficha[f"{field}_b"], field)
        if text_a == text_b:
            continue
        ratio = difflib.SequenceMatcher(None, text_a, text_b).ratio()
        if ratio >= CONTENT_SIMILARITY_THRESHOLD:
            continue
        changes.append(
            {
                "change_type": "ficha_content_changed",
                "code": ficha["code"],
                "field": field,
                "old": text_a,
                "new": text_b,
                "similarity_ratio": round(ratio, 3),
            }
        )
    return changes


def detect_changes(match_result: dict) -> dict:
    changes = []

    for ficha in match_result["fichas_added"]:
        changes.append(
            {"change_type": "ficha_added", "code": ficha["code"], "title": ficha["title"]}
        )

    for ficha in match_result["fichas_removed"]:
        changes.append(
            {"change_type": "ficha_removed", "code": ficha["code"], "title": ficha["title"]}
        )

    for ficha in match_result["fichas_matched"]:
        changes.extend(_diff_ficha_fields(ficha))

    if match_result["duplicate_codes_a"] or match_result["duplicate_codes_b"]:
        changes.append(
            {
                "change_type": "duplicate_code_warning",
                "duplicate_codes_a": match_result["duplicate_codes_a"],
                "duplicate_codes_b": match_result["duplicate_codes_b"],
            }
        )

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
