"""
Adaptador de Modulo 8 para visanet_settlement_service_vss_user_guide_volume_2_reports.

Este manual tiene 5 apendices independientes, sin jerarquia de secciones unica para todo el
documento (ver Modulo 1-4) -se agrupa por (apendice, tabla), igual que su propio Modulo 7
(`_group_by_appendix_table`).
"""

from . import _common

APPENDICES = ["appendix_a", "appendix_b", "appendix_c", "appendix_d", "appendix_e"]
APPENDIX_LABELS = {
    "appendix_a": "Apéndice A: VSS Reports-Print-Ready Formats",
    "appendix_b": "Apéndice B: VSS Reports-Machine-Readable Formats",
    "appendix_c": "Apéndice C: VSS Codes",
    "appendix_d": "Apéndice D: SMS Reports and Raw Data",
    "appendix_e": "Apéndice E: VSS Business Transaction Types Cross-Reference",
}


def _flatten(data: dict) -> list:
    flat = []
    for appendix in APPENDICES:
        for item in data["appendices"].get(appendix, []):
            item = dict(item)
            item["_appendix"] = appendix
            flat.append(item)
    return flat


def _group_label(appendix: str, table_title: str) -> str:
    label = APPENDIX_LABELS[appendix]
    return f"{label} — {table_title}" if table_title else label


def _table_details(changes: list, change_type: str) -> list:
    return [
        _common.make_detail(APPENDIX_LABELS[c["_appendix"]], f"{c['table_title']} ({c['num_rows']} filas)")
        for c in changes
        if c["change_type"] == change_type
    ]


def _row_details(changes: list, change_type: str) -> list:
    """La fila completa (columna: valor, sin las vacias), agrupada por (apendice, tabla)
    en el mismo orden que los grupos de cambios de negocio."""
    rows = [c for c in changes if c["change_type"] == change_type]
    rows.sort(key=lambda c: (c["_appendix"], c.get("table_title", "")))
    return [
        _common.make_detail(
            _group_label(c["_appendix"], c.get("table_title", "")),
            " | ".join(f"{col}: {val}" for col, val in c["row"]["columns"].items() if val) or f"Fila {c['key']}",
        )
        for c in rows
    ]


def summarize(data: dict, manual_dir, pair_filename: str) -> dict:
    changes = _flatten(data)

    business = [
        c
        for c in changes
        if c["change_type"] == "row_content_changed" and c["ai_category"] == "business_rule_change"
    ]

    by_key: dict = {}
    for c in business:
        by_key.setdefault((c["_appendix"], c.get("table_title", "")), []).append(c)

    groups = []
    for key in sorted(by_key, key=lambda k: (k[0], k[1])):
        items = [
            _common.make_item(
                location=f"Fila **{c['key']}** — columna {c['column']}",
                before=c["old"],
                after=c["new"],
                reason=c["ai_reason"],
                flagged=c.get("safety_net_override", False),
            )
            for c in by_key[key]
        ]
        groups.append(_common.make_group(_group_label(*key), items))

    return {
        "edition_a": data["edition_a"],
        "edition_b": data["edition_b"],
        "headline": {"label": "Cambios de negocio a revisar", "value": len(business)},
        "secondary": [
            _common.make_pill("Tablas agregadas", _table_details(changes, "table_added")),
            _common.make_pill("Tablas eliminadas", _table_details(changes, "table_removed")),
            _common.make_pill("Filas agregadas", _row_details(changes, "row_added")),
            _common.make_pill("Filas eliminadas", _row_details(changes, "row_removed")),
        ],
        "groups": groups,
        "top_items": _common.top_items(groups),
    }
