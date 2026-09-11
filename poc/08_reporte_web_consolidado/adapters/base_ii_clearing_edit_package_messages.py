"""
Adaptador de Modulo 8 para base_ii_clearing_edit_package_messages.

Espeja su propio Modulo 7 -agrupa por ficha (codigo), no por tabla (este manual no tiene ese
nivel). El titulo de cada ficha no viene en el cambio (Modulo 4/5 no lo necesitaban para su
trabajo), asi que se relee del Modulo 3 igual que ya hace `07_reporte_cambios/report.py`
(`_title_by_code`).
"""

import json

from . import _common

FIELD_LABELS = {
    "title": "Título",
    "description": "Description",
    "action": "Action",
    "transaction_types": "Transaction Types",
}


def _title_by_code(manual_dir, pair_filename: str) -> dict:
    match_path = manual_dir / "data" / "03_emparejamiento_bloques" / pair_filename
    match_result = json.loads(match_path.read_text())
    return {f["code"]: f["title_b"] for f in match_result.get("fichas_matched", [])}


def summarize(data: dict, manual_dir, pair_filename: str) -> dict:
    title_by_code = _title_by_code(manual_dir, pair_filename)

    changes = data["changes"]
    by_type: dict = {}
    for c in changes:
        by_type.setdefault(c["change_type"], []).append(c)

    content_changes = by_type.get("ficha_content_changed", [])
    business = [c for c in content_changes if c["ai_category"] == "business_rule_change"]

    by_code: dict = {}
    for c in business:
        by_code.setdefault(c["code"], []).append(c)

    groups = []
    for code in sorted(by_code):
        title = title_by_code.get(code, "")
        items = [
            _common.make_item(
                location=FIELD_LABELS.get(c["field"], c["field"]),
                before=c["old"],
                after=c["new"],
                reason=c["ai_reason"],
                flagged=c.get("safety_net_override", False),
            )
            for c in by_code[code]
        ]
        groups.append(_common.make_group(f"`{code}` — {title}", items))

    added = len(by_type.get("ficha_added", []))
    removed = len(by_type.get("ficha_removed", []))

    return {
        "edition_a": data["edition_a"],
        "edition_b": data["edition_b"],
        "headline": {"label": "Cambios de negocio a revisar", "value": len(business)},
        "secondary": [
            {"label": "Fichas agregadas", "value": added},
            {"label": "Fichas eliminadas", "value": removed},
        ],
        "groups": groups,
        "top_items": _common.top_items(groups),
    }
