"""
Adaptador de Modulo 8 para visanet_settlement_service_vss_user_guide_volume_1_specifications.

Espeja su propio Modulo 7: los cambios de negocio pueden venir de parrafos O de pares Field
Name/Description (`paragraph_content_changed` / `pair_content_changed`), agrupados por ruta
de seccion completa.
"""

from . import _common


def _path_str(path) -> str:
    return " > ".join(path)


def summarize(data: dict, manual_dir, pair_filename: str) -> dict:
    changes = data["changes"]
    by_type: dict = {}
    for c in changes:
        by_type.setdefault(c["change_type"], []).append(c)

    all_content_changes = by_type.get("paragraph_content_changed", []) + by_type.get("pair_content_changed", [])
    business = [c for c in all_content_changes if c["ai_category"] == "business_rule_change"]

    by_path: dict = {}
    for c in business:
        by_path.setdefault(_path_str(c["path"]), []).append(c)

    groups = []
    for path_str in sorted(by_path):
        items = []
        for c in by_path[path_str]:
            if c["change_type"] == "pair_content_changed":
                location = f"{c['name']} ({c['example_title']})"
            else:
                location = "Párrafo cambiado"
            items.append(
                _common.make_item(
                    location=location,
                    before=c["old"],
                    after=c["new"],
                    reason=c["ai_reason"],
                    flagged=c.get("safety_net_override", False),
                )
            )
        groups.append(_common.make_group(path_str, items))

    return {
        "edition_a": data["edition_a"],
        "edition_b": data["edition_b"],
        "headline": {"label": "Cambios de negocio a revisar", "value": len(business)},
        "secondary": [
            {"label": "Secciones agregadas", "value": len(by_type.get("section_added", []))},
            {"label": "Secciones eliminadas", "value": len(by_type.get("section_removed", []))},
            {"label": "Pares agregados", "value": len(by_type.get("pair_added", []))},
            {"label": "Pares eliminados", "value": len(by_type.get("pair_removed", []))},
        ],
        "groups": groups,
        "top_items": _common.top_items(groups),
    }
