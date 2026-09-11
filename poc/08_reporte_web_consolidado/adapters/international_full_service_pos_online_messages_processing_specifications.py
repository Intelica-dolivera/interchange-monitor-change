"""
Adaptador de Modulo 8 para
international_full_service_pos_online_messages_processing_specifications.

Espeja su propio Modulo 7: sin grilla de campos en este manual, los cambios de negocio son
parrafos completos (`paragraph_content_changed`), agrupados por ruta de seccion completa.
"""

from . import _common


def _path_str(path) -> str:
    return " > ".join(path)


def summarize(data: dict, manual_dir, pair_filename: str) -> dict:
    changes = data["changes"]
    by_type: dict = {}
    for c in changes:
        by_type.setdefault(c["change_type"], []).append(c)

    content_changes = by_type.get("paragraph_content_changed", [])
    business = [c for c in content_changes if c["ai_category"] == "business_rule_change"]

    by_path: dict = {}
    for c in business:
        by_path.setdefault(_path_str(c["path"]), []).append(c)

    groups = []
    for path_str in sorted(by_path):
        items = [
            _common.make_item(
                location="Párrafo cambiado",
                before=c["old"],
                after=c["new"],
                reason=c["ai_reason"],
                flagged=c.get("safety_net_override", False),
            )
            for c in by_path[path_str]
        ]
        groups.append(_common.make_group(path_str, items))

    return {
        "edition_a": data["edition_a"],
        "edition_b": data["edition_b"],
        "headline": {"label": "Cambios de negocio a revisar", "value": len(business)},
        "secondary": [
            {"label": "Secciones agregadas", "value": len(by_type.get("section_added", []))},
            {"label": "Secciones eliminadas", "value": len(by_type.get("section_removed", []))},
            {"label": "Párrafos agregados", "value": len(by_type.get("paragraph_added", []))},
            {"label": "Párrafos eliminados", "value": len(by_type.get("paragraph_removed", []))},
        ],
        "groups": groups,
        "top_items": _common.top_items(groups),
    }
