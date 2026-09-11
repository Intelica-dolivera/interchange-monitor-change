"""
Modulo 4 - Deteccion de cambios para el manual
visanet_settlement_service_vss_user_guide_volume_2_reports.

Puramente deterministico (sin IA todavia -eso es Modulo 5, que consume la salida de este
modulo). Decisiones estructurales (tabla/fila/encabezado agregado, quitado, renombrado) ya
las resolvio Modulo 3 -este modulo solo las convierte en eventos tipados, sin volver a
decidir nada. Solo evalua si el CONTENIDO de un par ya emparejado cambio de verdad.

**Diff de fila: por NOMBRE de columna (no por indice), excluyendo la columna ancla.** Igual
principio que el 2do manual (fichas sin estructura de grilla fija) en vez del 1er/3er/4to
manual (diff por indice de columna, valido solo cuando la grilla es homogenea) -aca cada
`table_title` puede tener un set de columnas DISTINTO (2 a 6, ver Modulo 2), asi que diffear
por indice seria incorrecto en cuanto 2 tablas no comparten el mismo esquema. La columna ancla
(`anchor_column`, ya expuesta por Modulo 2/3) nunca se diffea -es la clave de identidad de la
fila, no contenido a comparar.

Mismo umbral de similitud 0.98 (`difflib.SequenceMatcher`) que el resto del proyecto, para
descartar diferencias de solo formato/espaciado y quedarse con cambios de contenido real.

Los `duplicate_row_keys_a/b` que Modulo 3 ya detecto (colisiones de clave ancla dentro de una
tabla) se pasan como advertencias de confiabilidad, no como cambios -mismo tratamiento que
`duplicate_code_warning` en otros manuales.
"""

import difflib
import json
import re
import sys
from pathlib import Path

MANUAL_SLUG = "visanet_settlement_service_vss_user_guide_volume_2_reports"
INPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "03_emparejamiento_bloques"
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "04_deteccion_cambios"

APPENDICES = ["appendix_a", "appendix_b", "appendix_c", "appendix_d", "appendix_e"]
CONTENT_SIMILARITY_THRESHOLD = 0.98
WHITESPACE = re.compile(r"\s+")


def _normalize_text(text: str) -> str:
    return WHITESPACE.sub(" ", text or "").strip()


def _diff_row(row_a: dict, row_b: dict, anchor_column: str) -> list:
    cols_a, cols_b = row_a["columns"], row_b["columns"]
    changes = []
    for col in sorted(set(cols_a) | set(cols_b)):
        if col == anchor_column or col == "__unassigned_prefix__":
            continue
        norm_a, norm_b = _normalize_text(cols_a.get(col, "")), _normalize_text(cols_b.get(col, ""))
        if norm_a == norm_b:
            continue
        ratio = difflib.SequenceMatcher(None, norm_a, norm_b).ratio()
        if ratio >= CONTENT_SIMILARITY_THRESHOLD:
            continue
        changes.append(
            {
                "change_type": "row_content_changed",
                "column": col,
                "old": norm_a,
                "new": norm_b,
                "similarity_ratio": round(ratio, 3),
            }
        )
    return changes


def detect_appendix_changes(appendix_match: dict) -> list:
    changes = []

    for t in appendix_match["tables_added"]:
        changes.append({"change_type": "table_added", "table_title": t["table_title"], "num_rows": t["num_rows"]})
    for t in appendix_match["tables_removed"]:
        changes.append({"change_type": "table_removed", "table_title": t["table_title"], "num_rows": t["num_rows"]})

    for table in appendix_match["tables_matched"]:
        title = table["table_title_b"]

        if table["match_type"] == "fuzzy":
            changes.append(
                {
                    "change_type": "table_renamed",
                    "table_title_old": table["table_title"],
                    "table_title_new": title,
                    "similarity_ratio": table["fuzzy_ratio"],
                }
            )

        for entry in table["rows_added"]:
            changes.append({"change_type": "row_added", "table_title": title, "key": entry["key"], "row": entry["row"]})
        for entry in table["rows_removed"]:
            changes.append({"change_type": "row_removed", "table_title": title, "key": entry["key"], "row": entry["row"]})

        for entry in table["rows_matched"]:
            row_a, row_b = entry["row_a"], entry["row_b"]
            anchor_column = row_b.get("anchor_column") or row_a.get("anchor_column")
            row_changes = _diff_row(row_a, row_b, anchor_column)
            for rc in row_changes:
                rc["table_title"] = title
                rc["key"] = entry["key"]
                changes.append(rc)

        if table["duplicate_row_keys_a"] or table["duplicate_row_keys_b"]:
            changes.append(
                {
                    "change_type": "duplicate_row_key_warning",
                    "table_title": title,
                    "duplicate_keys_a": table["duplicate_row_keys_a"],
                    "duplicate_keys_b": table["duplicate_row_keys_b"],
                }
            )

    for h in appendix_match["headings_added"]:
        changes.append({"change_type": "heading_added", "text": h})
    for h in appendix_match["headings_removed"]:
        changes.append({"change_type": "heading_removed", "text": h})
    for h in appendix_match["headings_matched"]:
        if h["match_type"] == "fuzzy":
            changes.append(
                {
                    "change_type": "heading_renamed",
                    "text_old": h["text_a"],
                    "text_new": h["text_b"],
                    "similarity_ratio": h["similarity"],
                }
            )

    for p in appendix_match["paragraphs_added"]:
        changes.append({"change_type": "paragraph_added", "text": p})
    for p in appendix_match["paragraphs_removed"]:
        changes.append({"change_type": "paragraph_removed", "text": p})

    return changes


def detect_changes(match_result: dict) -> dict:
    appendices_out = {}
    for appendix in APPENDICES:
        appendix_match = match_result["appendices"].get(appendix)
        appendices_out[appendix] = detect_appendix_changes(appendix_match) if appendix_match else []

    return {
        "manual": MANUAL_SLUG,
        "edition_a": match_result["edition_a"],
        "edition_b": match_result["edition_b"],
        "appendices": appendices_out,
    }


def main():
    input_paths = sorted(INPUT_DIR.glob("*.json"))
    if not input_paths:
        print(f"No se encontraron JSON de entrada en {INPUT_DIR}", file=sys.stderr)
        sys.exit(1)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for input_path in input_paths:
        match_result = json.loads(input_path.read_text())
        result = detect_changes(match_result)
        out_path = OUTPUT_DIR / input_path.name
        out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2))

        summary_parts = []
        for appendix in APPENDICES:
            changes = result["appendices"][appendix]
            by_type = {}
            for c in changes:
                by_type[c["change_type"]] = by_type.get(c["change_type"], 0) + 1
            summary_parts.append(f"{appendix}: {dict(sorted(by_type.items()))}")
        print(f"{input_path.name}:")
        for part in summary_parts:
            print(f"  {part}")


if __name__ == "__main__":
    main()
