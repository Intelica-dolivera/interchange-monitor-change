"""
Adaptador de Modulo 8 para base_ii_clearing_data_codes.

Espeja la logica de agrupamiento de su propio Modulo 7
(poc/base_ii_clearing_data_codes/07_reporte_cambios/report.py) -misma fuente de la verdad
para que headline/secondary coincidan con lo que ya muestra el index.md de ese manual.
"""

from . import _common


def summarize(data: dict, manual_dir, pair_filename: str) -> dict:
    changes = data["changes"]
    by_type: dict = {}
    for c in changes:
        by_type.setdefault(c["change_type"], []).append(c)

    content_changes = by_type.get("code_content_changed", [])
    business = [c for c in content_changes if c["ai_category"] == "business_rule_change"]

    by_table: dict = {}
    for c in business:
        by_table.setdefault(c["table"], []).append(c)

    groups = []
    for table in sorted(by_table, key=_common.short_name):
        items = [
            _common.make_item(
                location=f"Código `{c['code']}` — columna *{c['column']}*",
                before=c["old"],
                after=c["new"],
                reason=c["ai_reason"],
                flagged=c.get("safety_net_override", False),
            )
            for c in by_table[table]
        ]
        groups.append(_common.make_group(_common.short_name(table), items))

    added = len(by_type.get("table_added", [])) + len(by_type.get("code_added", []))
    removed = len(by_type.get("table_removed", [])) + len(by_type.get("code_removed", []))

    return {
        "edition_a": data["edition_a"],
        "edition_b": data["edition_b"],
        "headline": {"label": "Cambios de negocio a revisar", "value": len(business)},
        "secondary": [
            {"label": "Altas", "value": added},
            {"label": "Bajas", "value": removed},
            {"label": "Tablas agregadas", "value": len(by_type.get("table_added", []))},
            {"label": "Tablas eliminadas", "value": len(by_type.get("table_removed", []))},
        ],
        "groups": groups,
        "top_items": _common.top_items(groups),
    }
