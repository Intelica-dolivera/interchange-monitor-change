"""
Adaptador de Modulo 8 compartido por base_ii_clearing_interchange_formats_tc_01_to_tc_49 y
_tc_50_to_tc_92 -los unicos 2 manuales cuya forma de Modulo 5 es realmente identica (el
segundo solo agrega `signature` para desambiguar titulos de seccion colisionantes, ver
item 10/pending-bug-fixes; este adaptador ya lo maneja via `.get("signature", "")`, que da
"" para el primer manual y listo). Espeja la logica de sus propios Modulo 7:
`field_became_defined`/`field_became_reserved` -el caso de uso central del proyecto- van
primero, agrupados por seccion; `row_content_changed`/`card_content_changed` con
`ai_category == business_rule_change` van despues, agrupados por (titulo, signature).
"""

from . import _common


def _dedupe_field_transitions(items: list) -> dict:
    """Une las entradas kind=row/kind=card del mismo evento (misma seccion+signature+
    posicion) en una sola, prefiriendo la de la grilla -mismo mecanismo que el Modulo 7 de
    ambos manuales (`_dedupe_field_transitions`)."""
    by_key: dict = {}
    for item in items:
        pos_key = item.get("position") or item.get("removed_position")
        key = (item["title"], item.get("signature", ""), pos_key)
        by_key.setdefault(key, {})[item["kind"]] = item

    result = {}
    for key, kinds in by_key.items():
        preferred = dict(kinds.get("row") or kinds.get("card"))
        preferred["confirmed_in_row"] = "row" in kinds
        preferred["confirmed_in_card"] = "card" in kinds
        result[key] = preferred
    return result


def _field_display_name(field_item: dict) -> str:
    if "cells" in field_item:
        return field_item["cells"][3]
    return field_item["card"]["name"]


def _transition_item(entry: dict) -> dict:
    confirmed = []
    if entry["confirmed_in_row"]:
        confirmed.append("grilla")
    if entry["confirmed_in_card"]:
        confirmed.append("ficha")
    confirmed_str = " y ".join(confirmed)

    if entry.get("subtype") == "split":
        new_names = ", ".join(
            f"`{f['position']}` {_field_display_name(f)}" for f in entry["new_fields"]
        )
        remaining = entry.get("remaining_reserved") or []
        remaining_str = (
            ", ".join(f"{r['position']} Reserved" for r in remaining)
            if remaining
            else "ninguno (rango completo redefinido)"
        )
        return _common.make_item(
            location=f"Posición `{entry['removed_position']}` (Reserved) se partió",
            before=f"`{entry['removed_position']}` Reserved",
            after=f"{new_names}. Reserved restante: {remaining_str}",
            reason=f"Confirmado en {confirmed_str}.",
        )

    if entry.get("subtype") == "shifted":
        removed = {"cells": entry["removed_cells"]} if entry["kind"] == "row" else {"card": entry["removed_card"]}
        old_name = _field_display_name(removed)
        reserved_str = ", ".join(f"`{r['position']}` Reserved" for r in entry["new_reserved"])
        return _common.make_item(
            location=f"Posición `{entry['removed_position']}` pasó a Reserved (límite corrido por campo vecino)",
            before=f"`{entry['removed_position']}` {old_name}",
            after=reserved_str,
            reason=f"Confirmado en {confirmed_str}.",
        )

    if entry["kind"] == "row":
        old_name, new_name = entry["cells_a"][3], entry["cells_b"][3]
    else:
        old_name, new_name = entry["card_a"]["name"], entry["card_b"]["name"]
    return _common.make_item(
        location=f"Posición `{entry['position']}`",
        before=old_name,
        after=new_name,
        reason=f"Confirmado en {confirmed_str}.",
    )


def _transition_groups(by_type: dict, heading: str, change_type: str) -> list:
    deduped = _dedupe_field_transitions(by_type.get(change_type, []))

    by_title: dict = {}
    for (title, _sig, _pos), entry in deduped.items():
        by_title.setdefault(title, []).append(entry)

    groups = []
    for title in sorted(by_title):
        entries = sorted(by_title[title], key=lambda e: e.get("position") or e.get("removed_position"))
        groups.append(_common.make_group(f"{heading} — {title}", [_transition_item(e) for e in entries]))
    return groups


def _heading_for_group(sibling_signatures_by_title: dict, title: str, signature: str) -> str:
    if len(sibling_signatures_by_title.get(title, set())) > 1 and signature:
        return f"{title} — variante con campo «{signature}»"
    return title


def _business_groups(content_changes: list) -> list:
    business = [c for c in content_changes if c["ai_category"] == "business_rule_change"]

    by_key: dict = {}
    for c in business:
        by_key.setdefault((c["title"], c.get("signature", "")), []).append(c)

    siblings: dict = {}
    for title, signature in by_key:
        siblings.setdefault(title, set()).add(signature)

    groups = []
    for title, signature in sorted(by_key):
        by_position: dict = {}
        for c in by_key[(title, signature)]:
            by_position.setdefault(c["position"], []).append(c)

        items = []
        for position in sorted(by_position):
            entries = by_position[position]
            field_name = next((e.get("field_name") for e in entries if e.get("field_name")), "")
            for e in entries:
                is_row = e["change_type"] == "row_content_changed"
                label = f"Grilla ({e['column']})" if is_row else f"Ficha ({e['field']})"
                loc = f"`{position}`" + (f" — {field_name}" if field_name else "") + f" · {label}"
                items.append(
                    _common.make_item(
                        location=loc,
                        before=e["old"],
                        after=e["new"],
                        reason=e["ai_reason"],
                        flagged=e.get("safety_net_override", False),
                    )
                )
        heading = _heading_for_group(siblings, title, signature)
        groups.append(_common.make_group(heading, items))
    return groups


def _section_details(changes: list) -> list:
    details = []
    for c in sorted(changes, key=lambda c: (c["title"], c.get("signature", ""))):
        variant = f" — variante con campo «{c['signature']}»" if c.get("signature") else ""
        details.append(
            _common.make_detail("", f"{c['title']}{variant} ({c['num_rows']} filas de grilla, {c['num_cards']} fichas)")
        )
    return details


def summarize(data: dict, manual_dir, pair_filename: str, title: str) -> dict:
    changes = data["changes"]
    by_type: dict = {}
    for c in changes:
        by_type.setdefault(c["change_type"], []).append(c)

    content_changes = by_type.get("row_content_changed", []) + by_type.get("card_content_changed", [])
    business = [c for c in content_changes if c["ai_category"] == "business_rule_change"]

    transition_groups = _transition_groups(
        by_type, "Reserved → definido", "field_became_defined"
    ) + _transition_groups(by_type, "Definido → Reserved", "field_became_reserved")
    transition_details = [
        _common.make_detail(g["group_title"], f"{i['location']}: {i['before']} → {i['after']}")
        for g in transition_groups
        for i in g["items"]
    ]

    groups = transition_groups + _business_groups(content_changes)

    return {
        "edition_a": data["edition_a"],
        "edition_b": data["edition_b"],
        "headline": {"label": "Cambios de negocio a revisar", "value": len(business)},
        "secondary": [
            _common.make_pill("Transiciones Reserved↔definido", transition_details),
            _common.make_pill("Secciones agregadas", _section_details(by_type.get("section_added", []))),
            _common.make_pill("Secciones eliminadas", _section_details(by_type.get("section_removed", []))),
        ],
        "groups": groups,
        "top_items": _common.top_items(groups),
    }
