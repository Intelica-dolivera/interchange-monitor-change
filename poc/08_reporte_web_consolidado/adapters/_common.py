"""
Utilidades minimas compartidas por los adaptadores de Modulo 8.

Deliberadamente chico: cada adaptador sigue siendo bespoke por manual (ver docstring de
build.py) -esto solo evita repetir 3 helpers realmente identicos en los 8 archivos (formato
de fecha, truncado de nombres largos, y la forma comun de "item"/"grupo"/"top items").
"""


def fmt_date(edition: str) -> str:
    return f"{edition[6:8]}/{edition[4:6]}/{edition[0:4]}"


def short_name(name: str, max_len: int = 80) -> str:
    flat = " ".join(name.split())
    if len(flat) <= max_len:
        return flat
    return flat[: max_len - 1].rstrip() + "…"


def make_item(location: str, before=None, after=None, reason=None, flagged: bool = False) -> dict:
    return {
        "location": location,
        "before": before,
        "after": after,
        "reason": reason,
        "flagged": bool(flagged),
    }


def make_group(group_title: str, items: list) -> dict:
    return {"group_title": group_title, "items": items}


def top_items(groups: list, n: int = 3) -> list:
    """Primeros N items en orden de aparicion (ver decision de diseno en el plan: no se
    inventa un score de "importancia" sin datos que lo justifiquen). El `location` se
    antepone con el titulo del grupo para que tenga sentido fuera de contexto, en la
    pestana "Resumen general"."""
    picked = []
    for group in groups:
        for item in group["items"]:
            copy = dict(item)
            copy["location"] = (
                f"{group['group_title']} — {item['location']}" if item["location"] else group["group_title"]
            )
            picked.append(copy)
            if len(picked) >= n:
                return picked
    return picked
