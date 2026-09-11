"""
Modulo 4 - Deteccion de cambios para el manual
international_full_service_pos_online_messages_processing_specifications.

Toma la salida ya emparejada del Modulo 3 (secciones/parrafos matched/added/removed) y la
convierte en una lista plana de cambios tipados. 100% deterministico (sin IA, eso es Modulo
5).

**Diferencia clave respecto a los otros manuales**: un parrafo no tiene sub-campos (a
diferencia de una ficha con `name`/`length`/`format`/`description`/etc.) -es un solo bloque de
texto libre, asi que no hace falta un diff campo-por-campo tipo `CARD_FIELDS`. La distincion
relevante ya la resolvio Modulo 3: parrafos con `match_type="exact"` son IDENTICOS por
construccion (nada que reportar como cambio de contenido); solo los `match_type="fuzzy"`
(emparejados por similitud, no por texto exacto) representan una posible reescritura real y se
emiten como `paragraph_content_changed` -estos son los que Modulo 5 va a clasificar
(business_rule_change/editorial_reword/extraction_noise), igual que `row_content_changed`/
`card_content_changed` en los otros manuales.

Tipos de cambio emitidos: `section_added`/`section_removed` (con conteo de parrafos),
`section_renamed` (match fuzzy a nivel de seccion -en este manual puede significar tanto un
renombre real de titulo COMO una promocion de nivel jerarquico, ver Modulo 3 docstring sobre
el caso `"Full Service Processing"` -Modulo 4 no distingue entre ambos, se reporta igual),
`paragraph_added`/`paragraph_removed`, `paragraph_content_changed` (solo para los fuzzy-
matched), `paragraph_reflowed` (parrafos re-cortados distinto entre ediciones por reflow de
pagina, mismo contenido -ver Modulo 3 docstring sobre el bug real encontrado y arreglado el
2026-08-19- se expone para que quede visible/trazable, pero NUNCA se cuenta como cambio real:
no participa de `ai_summary` en Modulo 5 ni de los conteos de "cambios de negocio" en Modulo
7), `duplicate_path_warning`/`duplicate_paragraph_warning` (avisos de confiabilidad, mismo
espiritu que `duplicate_position_warning` en los otros manuales), `possible_section_move`
(agregado 2026-09-04, ver docstring de Modulo 3 -pasa `possible_section_moves` de Modulo 3
como eventos tipados, NO reemplaza ni suprime los `section_added`/`section_removed` de esos
mismos paths -es un hint adicional, nunca un auto-match).

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


MANUAL_SLUG = "international_full_service_pos_online_messages_processing_specifications"
INPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "03_emparejamiento_bloques"
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "04_deteccion_cambios"


def _path_str(path) -> str:
    return " > ".join(path)


def detect_changes(match_result: dict) -> dict:
    changes = []

    for section in match_result["sections_added"]:
        changes.append(
            {
                "change_type": "section_added",
                "path": section["path"],
                "num_paragraphs": section["num_paragraphs"],
            }
        )
    for section in match_result["sections_removed"]:
        changes.append(
            {
                "change_type": "section_removed",
                "path": section["path"],
                "num_paragraphs": section["num_paragraphs"],
            }
        )

    for move in match_result.get("possible_section_moves", []):
        changes.append(
            {
                "change_type": "possible_section_move",
                "path_removed": move["path_removed"],
                "path_added": move["path_added"],
                "coverage": move["coverage"],
                "num_paragraphs_removed": move["num_paragraphs_removed"],
                "num_paragraphs_added": move["num_paragraphs_added"],
            }
        )

    if match_result["duplicate_section_paths_a"] or match_result["duplicate_section_paths_b"]:
        changes.append(
            {
                "change_type": "duplicate_path_warning",
                "duplicate_paths_a": match_result["duplicate_section_paths_a"],
                "duplicate_paths_b": match_result["duplicate_section_paths_b"],
            }
        )

    for section in match_result["sections_matched"]:
        path = section["path_b"]

        if section["match_type"] == "fuzzy":
            changes.append(
                {
                    "change_type": "section_renamed",
                    "path_a": section["path_a"],
                    "path_b": section["path_b"],
                    "fuzzy_ratio": section["fuzzy_ratio"],
                }
            )

        if section["duplicate_paragraph_texts_a"] or section["duplicate_paragraph_texts_b"]:
            changes.append(
                {
                    "change_type": "duplicate_paragraph_warning",
                    "path": path,
                    "duplicate_texts_a": section["duplicate_paragraph_texts_a"],
                    "duplicate_texts_b": section["duplicate_paragraph_texts_b"],
                }
            )

        for r in section.get("paragraphs_reflowed", []):
            changes.append(
                {
                    "change_type": "paragraph_reflowed",
                    "path": path,
                    "text_a": r["text_a"],
                    "text_b": r["text_b"],
                }
            )
        for text in section["paragraphs_added"]:
            changes.append({"change_type": "paragraph_added", "path": path, "text": text})
        for text in section["paragraphs_removed"]:
            changes.append({"change_type": "paragraph_removed", "path": path, "text": text})
        fuzzy_pairs = [p for p in section["paragraphs_matched"] if p["match_type"] == "fuzzy"]
        if fuzzy_pairs:
            # Todos los parrafos de la edicion NUEVA en esta seccion -contexto para que Modulo 5
            # pueda distinguir "contenido realmente desaparecido" de "contenido redistribuido a
            # un parrafo NO ADYACENTE de esta misma seccion" (ver docstring de Modulo 3 sobre el
            # residuo del item 13 -el reflow por bloque contiguo no cubre este caso).
            section_new_paragraphs = (
                [p["text_b"] for p in section["paragraphs_matched"]]
                + [t for r in section.get("paragraphs_reflowed", []) for t in r["text_b"]]
                + list(section["paragraphs_added"])
            )
            for p in fuzzy_pairs:
                changes.append(
                    {
                        "change_type": "paragraph_content_changed",
                        "path": path,
                        "old": p["text_a"],
                        "new": p["text_b"],
                        "similarity_ratio": p["similarity"],
                        "section_new_paragraphs": section_new_paragraphs,
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
