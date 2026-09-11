"""
Modulo 4 - Deteccion de cambios para el manual
visanet_settlement_service_vss_user_guide_volume_1_specifications.

Toma la salida ya emparejada del Modulo 3 y la convierte en una lista plana de cambios
tipados. 100% deterministico (sin IA, eso es Modulo 5).

Parrafos: identico al 6to manual -`match_type="exact"` es identico por construccion (nada
que reportar), solo `match_type="fuzzy"` se emite como `paragraph_content_changed`.

**Pares Field Name/Description: DISTINTO a parrafos/filas de otros manuales** -la clave de
emparejamiento (`example_title`+`name`, ver Modulo 3) NO consume el campo `description`, asi
que un par matcheado por clave puede tener description DISTINTA entre ediciones -eso SI es un
cambio de contenido real a detectar, no una imposibilidad logica como en el 5to/6to manual.
Se compara `description_a` vs `description_b` normalizado con el mismo umbral de similitud
0.98 (`difflib`) ya usado en los manuales de grilla (Tipo A) para descartar diferencias de
solo espaciado/formato, emitido como `pair_content_changed` -este es el que Modulo 5 va a
clasificar, ademas de `paragraph_content_changed`.

Tipos de cambio: `section_added`/`removed`/`renamed`, `paragraph_added`/`removed`/
`content_changed`/`reflowed` (igual al 6to manual), `pair_added`/`removed`/`content_changed`,
`duplicate_path_warning`/`duplicate_paragraph_warning`/`duplicate_pair_key_warning`.

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


MANUAL_SLUG = "visanet_settlement_service_vss_user_guide_volume_1_specifications"
INPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "03_emparejamiento_bloques"
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "04_deteccion_cambios"

CONTENT_SIMILARITY_THRESHOLD = 0.98
WHITESPACE = re.compile(r"\s+")


def _normalize_text(text: str) -> str:
    return WHITESPACE.sub(" ", text).strip()


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
                "num_pairs": section["num_pairs"],
            }
        )
    for section in match_result["sections_removed"]:
        changes.append(
            {
                "change_type": "section_removed",
                "path": section["path"],
                "num_paragraphs": section["num_paragraphs"],
                "num_pairs": section["num_pairs"],
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
        if section["duplicate_pair_keys_a"] or section["duplicate_pair_keys_b"]:
            changes.append(
                {
                    "change_type": "duplicate_pair_key_warning",
                    "path": path,
                    "duplicate_keys_a": section["duplicate_pair_keys_a"],
                    "duplicate_keys_b": section["duplicate_pair_keys_b"],
                }
            )

        for r in section.get("paragraphs_reflowed", []):
            changes.append(
                {"change_type": "paragraph_reflowed", "path": path, "text_a": r["text_a"], "text_b": r["text_b"]}
            )
        for text in section["paragraphs_added"]:
            changes.append({"change_type": "paragraph_added", "path": path, "text": text})
        for text in section["paragraphs_removed"]:
            changes.append({"change_type": "paragraph_removed", "path": path, "text": text})
        for p in section["paragraphs_matched"]:
            if p["match_type"] == "fuzzy":
                changes.append(
                    {
                        "change_type": "paragraph_content_changed",
                        "path": path,
                        "old": p["text_a"],
                        "new": p["text_b"],
                        "similarity_ratio": p["similarity"],
                    }
                )

        for item in section["pairs_added"]:
            b = item["pair"]
            changes.append(
                {
                    "change_type": "pair_added",
                    "path": path,
                    "example_title": b["example_title"],
                    "name": b["name"],
                    "description": b["description"],
                }
            )
        for item in section["pairs_removed"]:
            b = item["pair"]
            changes.append(
                {
                    "change_type": "pair_removed",
                    "path": path,
                    "example_title": b["example_title"],
                    "name": b["name"],
                    "description": b["description"],
                }
            )
        for item in section["pairs_matched"]:
            pa, pb = item["pair_a"], item["pair_b"]
            desc_a, desc_b = _normalize_text(pa["description"]), _normalize_text(pb["description"])
            if desc_a == desc_b:
                continue
            ratio = difflib.SequenceMatcher(None, desc_a, desc_b).ratio()
            if ratio >= CONTENT_SIMILARITY_THRESHOLD:
                continue
            changes.append(
                {
                    "change_type": "pair_content_changed",
                    "path": path,
                    "example_title": pb["example_title"],
                    "name": pb["name"],
                    "old": pa["description"],
                    "new": pb["description"],
                    "similarity_ratio": round(ratio, 3),
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
