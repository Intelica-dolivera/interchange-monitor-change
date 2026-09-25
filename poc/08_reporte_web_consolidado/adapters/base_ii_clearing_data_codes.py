"""
Adaptador de Modulo 8 para base_ii_clearing_data_codes.

Espeja la logica de agrupamiento de su propio Modulo 7
(poc/base_ii_clearing_data_codes/07_reporte_cambios/report.py) -misma fuente de la verdad
para que headline/secondary coincidan con lo que ya muestra el index.md de ese manual.
"""

from . import _common

TABLES_GROUP = "Tablas completas"


def _table_details(changes: list) -> list:
    return [
        _common.make_detail(TABLES_GROUP, f"{_common.short_name(c['table'])} ({c['num_rows']} filas)")
        for c in changes
    ]


def _code_details(changes: list) -> list:
    """Codigos sueltos dentro de una tabla que sigue existiendo, agrupados por tabla."""
    return [
        _common.make_detail(_common.short_name(c["table"]), f"`{c['code']}` — {' | '.join(c['cells'][1:])}")
        for c in sorted(changes, key=lambda c: _common.short_name(c["table"]))
    ]


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

    tables_added = _table_details(by_type.get("table_added", []))
    tables_removed = _table_details(by_type.get("table_removed", []))

    return {
        "edition_a": data["edition_a"],
        "edition_b": data["edition_b"],
        "headline": {"label": "Cambios de negocio a revisar", "value": len(business)},
        "secondary": [
            _common.make_pill("Altas", tables_added + _code_details(by_type.get("code_added", []))),
            _common.make_pill("Bajas", tables_removed + _code_details(by_type.get("code_removed", []))),
            _common.make_pill("Tablas agregadas", tables_added),
            _common.make_pill("Tablas eliminadas", tables_removed),
        ],
        "groups": groups,
        "top_items": _common.top_items(groups),
    }
