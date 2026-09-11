"""
Modulo 7 - Reporte de cambios para el manual
base_ii_clearing_interchange_formats_tc_50_to_tc_92.

Ultimo eslabon del pipeline: toma la salida ya enriquecida del Modulo 5 y genera un reporte
en Markdown por cada par de ediciones consecutivas. Modulo 6 sigue tentativo/sin definir.

Mismo diseno que el Modulo 7 del 3er manual, su hermano directo -sin cambios, opera puramente
sobre la forma ya estable del output de Modulo 5 (identica en ambos manuales):
`field_became_defined`/`field_became_reserved` primero, cambios de negocio agrupados por
campo segundo, apendice de redaccion/ruido, altas/bajas estructurales, avisos de
confiabilidad al final. Misma deduplicacion fila/ficha para las transiciones Reserved<->
definido.

Diferencia real esperada en el output (no de diseno): dado que este manual no tuvo ninguna
transicion Reserved<->definido en los 8 pares (ver Modulo 3/4 en
[[open-questions-technical-manuals]]), esa seccion del reporte va a salir vacia
("_Ninguno en este par de ediciones._") en las 8 corridas -no es un bug del reporte, refleja
fielmente que el rango de capitulos TC 50-92 no tuvo ese tipo de cambio en esta ventana de
ediciones.
"""

import json
import sys
from pathlib import Path

MANUAL_SLUG = "base_ii_clearing_interchange_formats_tc_50_to_tc_92"
MANUAL_TITLE = "BASE II Clearing Interchange Formats, TC 50 to TC 92"
INPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "05_interpretacion_cambios_ia"
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "07_reporte_cambios"


def _fmt_date(edition: str) -> str:
    return f"{edition[6:8]}/{edition[4:6]}/{edition[0:4]}"


def _group_by_title(items: list, key: str = "title") -> dict:
    """Agrupa por `(titulo, signature)` -no solo titulo- para no mezclar 2 secciones que
    colisionan de titulo (item 10/[[pending-bug-fixes]], ej. las 2 "TC 57 - TCR 5 - Limited
    Use Data" de este manual) bajo el mismo encabezado ambiguo. La clave sigue siendo el
    titulo solo cuando no hay colision (`signature` vacio o unico por titulo) -ver
    `_heading_for_group` para como se decide el texto final del encabezado."""
    grouped = {}
    for item in items:
        grouped.setdefault((item[key], item.get("signature", "")), []).append(item)
    return dict(sorted(grouped.items()))


def _heading_for_group(groups: dict, title_key, position_by_signature: dict) -> str:
    """Texto de encabezado para un grupo `(titulo, signature)`: agrega un sufijo
    desambiguador SOLO si el mismo titulo aparece en mas de un grupo en este render (ver
    `_group_by_title`) -asi el caso comun (titulo unico) no se ensucia con una señal interna
    que no aporta nada quien lee un reporte donde nunca hubo colision. Incluye la posicion
    del campo (item 10/[[pending-bug-fixes]], residuo cerrado 2026-09-05) -el nombre solo
    alcanza para distinguir las 2 variantes, la posicion le permite a quien lee ubicar el
    campo en el layout de bytes sin tener que cruzar contra la tabla completa."""
    title, signature = title_key
    sibling_signatures = {sig for (t, sig) in groups if t == title}
    if len(sibling_signatures) > 1 and signature:
        position = position_by_signature.get(title_key, "")
        pos_suffix = f" @ {position}" if position else ""
        return f"{title} — variante con campo «{signature}{pos_suffix}»"
    return title


def _dedupe_field_transitions(items: list) -> dict:
    """Une las entradas kind=row/kind=card del mismo evento (misma seccion+posicion) en
    una sola, prefiriendo la de la grilla. Devuelve {(title, signature, position_key):
    entry_preferida, con "confirmed_in_card"/"confirmed_in_row" agregado}. Incluye
    `signature` en la clave (item 10/[[pending-bug-fixes]]) para no mezclar el mismo
    `position` de 2 secciones que colisionan de titulo como si fuera 1 solo evento."""
    by_key = {}
    for item in items:
        pos_key = item.get("position") or item.get("removed_position")
        key = (item["title"], item.get("signature", ""), pos_key)
        by_key.setdefault(key, {})[item["kind"]] = item

    result = {}
    for key, kinds in by_key.items():
        preferred = kinds.get("row") or kinds.get("card")
        preferred = dict(preferred)
        preferred["confirmed_in_row"] = "row" in kinds
        preferred["confirmed_in_card"] = "card" in kinds
        result[key] = preferred
    return result


def _field_display_name(field_item: dict) -> str:
    if "cells" in field_item:
        return field_item["cells"][3]
    return field_item["card"]["name"]


def _render_field_transitions(lines: list, heading: str, items: list) -> None:
    deduped = _dedupe_field_transitions(items)
    lines.append(f"## {heading} ({len(deduped)})")
    lines.append("")
    if not deduped:
        lines.append("_Ninguno en este par de ediciones._")
        lines.append("")
        return

    by_title = {}
    position_by_signature = {}
    for (title, signature, _pos), entry in deduped.items():
        key = (title, signature)
        by_title.setdefault(key, []).append(entry)
        position_by_signature.setdefault(key, entry.get("signature_position", ""))

    for title_key, entries in sorted(by_title.items()):
        lines.append(f"### {_heading_for_group(by_title, title_key, position_by_signature)}")
        lines.append("")
        for e in sorted(entries, key=lambda x: x.get("position") or x.get("removed_position")):
            confirmed = []
            if e["confirmed_in_row"]:
                confirmed.append("grilla")
            if e["confirmed_in_card"]:
                confirmed.append("ficha")
            confirmed_str = " y ".join(confirmed)
            if e.get("subtype") == "split":
                new_names = ", ".join(
                    f"**{f['position']}** {_field_display_name(f)}" for f in e["new_fields"]
                )
                remaining = e.get("remaining_reserved") or []
                remaining_str = (
                    ", ".join(f"{r['position']} Reserved" for r in remaining)
                    if remaining
                    else "ninguno (el rango completo se redefinio)"
                )
                lines.append(
                    f"- Posición `{e['removed_position']}` (Reserved) se partió en: {new_names}. "
                    f"Reserved restante: {remaining_str}. _(confirmado en {confirmed_str})_"
                )
            else:
                if e["kind"] == "row":
                    old_name, new_name = e["cells_a"][3], e["cells_b"][3]
                else:
                    old_name, new_name = e["card_a"]["name"], e["card_b"]["name"]
                lines.append(
                    f"- Posición `{e['position']}`: **{old_name}** → **{new_name}**. "
                    f"_(confirmado en {confirmed_str})_"
                )
        lines.append("")


def _render_content_changes(lines: list, changes: list, category_filter, heading: str, compact: bool) -> None:
    filtered = [c for c in changes if category_filter(c)]
    lines.append(f"## {heading} ({len(filtered)})")
    lines.append("")
    if not filtered:
        lines.append("_Ninguno en este par de ediciones._")
        lines.append("")
        return

    by_section = _group_by_title(filtered)
    position_by_signature = {
        title_key: next((i.get("signature_position", "") for i in items), "")
        for title_key, items in by_section.items()
    }
    for title_key, items in by_section.items():
        lines.append(f"### {_heading_for_group(by_section, title_key, position_by_signature)}")
        lines.append("")
        by_position = {}
        for item in items:
            by_position.setdefault(item["position"], []).append(item)
        for position, entries in sorted(by_position.items()):
            field_name = next((e.get("field_name") for e in entries if e.get("field_name")), "")
            lines.append(f"- **`{position}`**{f' — {field_name}' if field_name else ''}")
            for e in entries:
                is_row = e["change_type"] == "row_content_changed"
                label = f"Grilla ({e['column']})" if is_row else f"Ficha ({e['field']})"
                if compact:
                    lines.append(f"  - {label} — {e['ai_category']} (similitud {e['similarity_ratio']:.2f})")
                else:
                    flag = " ⚠️ *(corregido por contenido desaparecido)*" if e.get("safety_net_override") else ""
                    lines.append(f"  - {label}{flag}")
                    lines.append(f"    - Antes: {e['old']!r}")
                    lines.append(f"    - Ahora: {e['new']!r}")
                    lines.append(f"    - Razón (IA): {e['ai_reason']}")
        lines.append("")


def _render_structural(lines: list, title: str, added: list, removed: list, key_fmt) -> None:
    lines.append(f"## {title} agregadas ({len(added)})")
    lines.append("")
    if added:
        for c in added:
            lines.append(f"- {key_fmt(c)}")
    else:
        lines.append("_Ninguna._")
    lines.append("")

    lines.append(f"## {title} eliminadas ({len(removed)})")
    lines.append("")
    if removed:
        for c in removed:
            lines.append(f"- {key_fmt(c)}")
    else:
        lines.append("_Ninguna._")
    lines.append("")


def render_report(result: dict) -> str:
    changes = result["changes"]
    by_type = {}
    for c in changes:
        by_type.setdefault(c["change_type"], []).append(c)

    content_changes = by_type.get("row_content_changed", []) + by_type.get("card_content_changed", [])
    num_overrides = sum(1 for c in content_changes if c.get("safety_net_override"))
    field_transitions = by_type.get("field_became_defined", []) + by_type.get("field_became_reserved", [])
    num_transitions = len(_dedupe_field_transitions(field_transitions))

    lines = [
        f"# Reporte de cambios — {MANUAL_TITLE}",
        f"## Edición {_fmt_date(result['edition_a'])} → {_fmt_date(result['edition_b'])}",
        "",
        "## Resumen",
        "",
        f"- Secciones: {len(by_type.get('section_added', []))} agregadas, "
        f"{len(by_type.get('section_removed', []))} eliminadas, "
        f"{len(by_type.get('section_renamed', []))} renombradas",
        f"- Transiciones Reserved↔definido: {num_transitions}",
        f"- Filas de grilla: {len(by_type.get('row_added', []))} agregadas, "
        f"{len(by_type.get('row_removed', []))} eliminadas",
        f"- Fichas: {len(by_type.get('card_added', []))} agregadas, "
        f"{len(by_type.get('card_removed', []))} eliminadas",
        f"- Cambios de contenido: {len(content_changes)} totales — "
        + ", ".join(f"{k}={v}" for k, v in sorted(result.get("ai_summary", {}).items())),
        "",
    ]

    _render_field_transitions(
        lines,
        "Campos que pasaron de Reserved a definidos",
        by_type.get("field_became_defined", []),
    )
    _render_field_transitions(
        lines,
        "Campos que pasaron a Reserved",
        by_type.get("field_became_reserved", []),
    )
    _render_content_changes(
        lines, content_changes, lambda c: c["ai_category"] == "business_rule_change",
        "Cambios de negocio a revisar", compact=False,
    )
    sections_added_removed = by_type.get("section_added", []) + by_type.get("section_removed", [])
    section_title_counts = {}
    for s in sections_added_removed:
        section_title_counts[s["title"]] = section_title_counts.get(s["title"], 0) + 1

    def _section_label(s: dict) -> str:
        # Item 10/[[pending-bug-fixes]]: mismo criterio que `_heading_for_group` -el sufijo
        # desambiguador solo aparece si el titulo realmente colisiona en esta lista, e
        # incluye la posicion del campo por la misma razon (residuo cerrado 2026-09-05).
        if section_title_counts.get(s["title"], 0) > 1 and s.get("signature"):
            position = s.get("signature_position", "")
            pos_suffix = f" @ {position}" if position else ""
            suffix = f" — variante con campo «{s['signature']}{pos_suffix}»"
        else:
            suffix = ""
        return f"{s['title']}{suffix} ({s['num_rows']} filas, {s['num_cards']} fichas)"

    _render_structural(
        lines, "Secciones", by_type.get("section_added", []), by_type.get("section_removed", []),
        _section_label,
    )
    if by_type.get("section_renamed"):
        lines.append(f"## Secciones posiblemente renombradas ({len(by_type['section_renamed'])})")
        lines.append("")
        for s in by_type["section_renamed"]:
            lines.append(f"- {s['title_a']} → {s['title_b']} (similitud {s['fuzzy_ratio']:.2f})")
        lines.append("")
    _render_structural(
        lines, "Filas de grilla", by_type.get("row_added", []), by_type.get("row_removed", []),
        lambda r: f"`{r['position']}` {r['cells'][3]} ({r['title']})",
    )
    _render_structural(
        lines, "Fichas", by_type.get("card_added", []), by_type.get("card_removed", []),
        lambda c: f"`{c['position']}` {c['card']['name']} ({c['title']})",
    )
    _render_content_changes(
        lines, content_changes, lambda c: c["ai_category"] != "business_rule_change",
        "Apéndice: cambios de solo redacción / ruido de extracción", compact=True,
    )

    duplicate_warnings = by_type.get("duplicate_position_warning", [])
    if duplicate_warnings or num_overrides:
        lines.append("## Avisos de confiabilidad")
        lines.append("")
        if num_overrides:
            lines.append(
                f"- {num_overrides} cambio(s) de negocio fueron re-clasificados automáticamente "
                "porque la IA los marcó como redacción/ruido pero se detectó contenido real "
                "desaparecido sin reemplazo (ver marca ⚠️ arriba)."
            )
        for w in duplicate_warnings:
            lines.append(
                f"- La sección **{w['title']}** tiene posiciones repetidas dentro de la misma "
                f"edición ({w['kind']}: `{w['duplicate_positions_a']}` en la edición vieja, "
                f"`{w['duplicate_positions_b']}` en la nueva) — el emparejamiento por posición "
                "en esos casos puntuales puede no ser 1:1 confiable."
            )
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def main():
    input_paths = sorted(INPUT_DIR.glob("*.json"))
    if not input_paths:
        print(f"No se encontraron cambios clasificados en {INPUT_DIR}", file=sys.stderr)
        sys.exit(1)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    index_lines = [f"# Índice de reportes — {MANUAL_TITLE}", ""]

    for input_path in input_paths:
        result = json.loads(input_path.read_text())
        report_md = render_report(result)

        out_path = OUTPUT_DIR / (input_path.stem + ".md")
        out_path.write_text(report_md)

        changes = result["changes"]
        by_type = {}
        for c in changes:
            by_type.setdefault(c["change_type"], []).append(c)
        real_changes = sum(
            1
            for c in changes
            if c["change_type"] in ("row_content_changed", "card_content_changed")
            and c["ai_category"] == "business_rule_change"
        )
        transitions = len(
            _dedupe_field_transitions(
                by_type.get("field_became_defined", []) + by_type.get("field_became_reserved", [])
            )
        )
        index_lines.append(
            f"- [{_fmt_date(result['edition_a'])} → {_fmt_date(result['edition_b'])}]"
            f"({out_path.name}) — {transitions} transiciones Reserved↔definido, "
            f"{real_changes} cambios de negocio a revisar"
        )
        print(f"{out_path.name}: {transitions} transiciones, {real_changes} cambios de negocio")

    (OUTPUT_DIR / "index.md").write_text("\n".join(index_lines) + "\n")


if __name__ == "__main__":
    main()
