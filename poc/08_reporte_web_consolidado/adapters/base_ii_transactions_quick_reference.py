"""
Adaptador de Modulo 8 para base_ii_transactions_quick_reference.

Este manual no tiene `ai_category` -Modulo 5 es un no-op a proposito (ver su propio
`classify.py`: `row_content_changed` nunca ocurre por diseno de la clave de emparejamiento
de Modulo 3). Espeja el diseno de su propio Modulo 7: la metrica central es altas/bajas de
fila TCR por TC, no "cambios de negocio" -ese concepto no existe aca, no se lo inventa. Los
conteos antes/despues por TC se releen del Modulo 3 (`sections_matched`), igual que ya hace
`report.py`.
"""

import json

from . import _common


def _row_counts_by_title(manual_dir, pair_filename: str) -> dict:
    match_path = manual_dir / "data" / "03_emparejamiento_bloques" / pair_filename
    match_result = json.loads(match_path.read_text())
    counts = {}
    for section in match_result.get("sections_matched", []):
        before = len(section["rows_matched"]) + len(section["rows_removed"])
        after = len(section["rows_matched"]) + len(section["rows_added"])
        counts[section["title_b"]] = {"before": before, "after": after}
    return counts


def _row_line(cells: list) -> str:
    if len(cells) == 2:
        return f"`{cells[0]}` — {cells[1]}"
    return f"`{cells[0]}` — (sin descripción)"


def _tc_details(changes: list) -> list:
    return [_common.make_detail("", f"{c['title']} ({c['num_rows']} TCR)") for c in changes]


def summarize(data: dict, manual_dir, pair_filename: str) -> dict:
    row_counts = _row_counts_by_title(manual_dir, pair_filename)

    changes = data["changes"]
    by_type: dict = {}
    for c in changes:
        by_type.setdefault(c["change_type"], []).append(c)

    row_added = by_type.get("row_added", [])
    row_removed = by_type.get("row_removed", [])

    added_by_title: dict = {}
    removed_by_title: dict = {}
    for c in row_added:
        added_by_title.setdefault(c["title"], []).append(c["cells"])
    for c in row_removed:
        removed_by_title.setdefault(c["title"], []).append(c["cells"])

    changed_titles = sorted(set(added_by_title) | set(removed_by_title))

    groups = []
    for title in changed_titles:
        counts = row_counts.get(title, {"before": "?", "after": "?"})
        added = added_by_title.get(title, [])
        removed = removed_by_title.get(title, [])
        delta = (
            counts["after"] - counts["before"]
            if isinstance(counts["before"], int) and isinstance(counts["after"], int)
            else None
        )
        reason_parts = []
        if added:
            reason_parts.append("Agregados: " + "; ".join(_row_line(c) for c in added[:3]))
        if removed:
            reason_parts.append("Eliminados: " + "; ".join(_row_line(c) for c in removed[:3]))
        possible_rename = bool(delta == 0 and added and removed)
        if possible_rename:
            reason_parts.append(
                "Cantidad neta sin cambio pero hay altas Y bajas — posible renombre no detectado."
            )
        item = _common.make_item(
            location="TCR agregados/eliminados",
            before=f"{counts['before']} TCR",
            after=f"{counts['after']} TCR",
            reason=" | ".join(reason_parts),
            flagged=possible_rename,
        )
        groups.append(_common.make_group(title, [item]))

    return {
        "edition_a": data["edition_a"],
        "edition_b": data["edition_b"],
        "headline": {"label": "Cambios de TCR", "value": len(row_added) + len(row_removed)},
        "secondary": [
            _common.make_pill("TC agregados", _tc_details(by_type.get("section_added", []))),
            _common.make_pill("TC eliminados", _tc_details(by_type.get("section_removed", []))),
            _common.make_pill(
                "TC afectados",
                [
                    _common.make_detail(
                        "",
                        f"{title}: +{len(added_by_title.get(title, []))} / "
                        f"-{len(removed_by_title.get(title, []))} TCR",
                    )
                    for title in changed_titles
                ],
            ),
        ],
        "groups": groups,
        "top_items": _common.top_items(groups),
    }
