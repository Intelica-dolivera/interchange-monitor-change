"""
Modulo 7 - Reporte de cambios para el manual
visanet_settlement_service_vss_user_guide_volume_1_specifications.

Ultimo eslabon del pipeline: toma la salida ya clasificada del Modulo 5 y genera un reporte
en Markdown por cada par de ediciones consecutivas. Modulo 6 sigue tentativo/sin definir.

Diseno de reporte, extendiendo el del 6to manual con los pares Field Name/Description (ver
Modulo 2/3/4): cambios de negocio a revisar (parrafos Y pares con `ai_category ==
business_rule_change`, agrupados por seccion, distinguiendo tipo); secciones/parrafos/pares
agregados/eliminados; secciones posiblemente renombradas; apendice de redaccion/ruido; avisos
de confiabilidad (duplicados de parrafo/par, `safety_net_override`, `paragraph_reflowed`
-nunca tratado como cambio real, ver Modulo 4).
"""

import json
import sys
from pathlib import Path

MANUAL_SLUG = "visanet_settlement_service_vss_user_guide_volume_1_specifications"
MANUAL_TITLE = "VisaNet Settlement Service (VSS) User Guide, Volume 1, Specifications"
INPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "05_interpretacion_cambios_ia"
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "07_reporte_cambios"


def _fmt_date(edition: str) -> str:
    return f"{edition[6:8]}/{edition[4:6]}/{edition[0:4]}"


def _path_str(path) -> str:
    return " > ".join(path)


def _group_by_path(items: list) -> dict:
    grouped = {}
    for item in items:
        grouped.setdefault(_path_str(item["path"]), []).append(item)
    return dict(sorted(grouped.items()))


def render_report(result: dict) -> str:
    changes = result["changes"]
    by_type = {}
    for c in changes:
        by_type.setdefault(c["change_type"], []).append(c)

    para_changes = by_type.get("paragraph_content_changed", [])
    pair_changes = by_type.get("pair_content_changed", [])
    all_content_changes = para_changes + pair_changes
    business_changes = [c for c in all_content_changes if c["ai_category"] == "business_rule_change"]
    appendix_changes = [c for c in all_content_changes if c["ai_category"] != "business_rule_change"]
    num_overrides = sum(1 for c in all_content_changes if c.get("safety_net_override"))

    section_added = by_type.get("section_added", [])
    section_removed = by_type.get("section_removed", [])
    section_renamed = by_type.get("section_renamed", [])
    para_added = by_type.get("paragraph_added", [])
    para_removed = by_type.get("paragraph_removed", [])
    para_reflowed = by_type.get("paragraph_reflowed", [])
    pair_added = by_type.get("pair_added", [])
    pair_removed = by_type.get("pair_removed", [])
    duplicate_path = by_type.get("duplicate_path_warning", [])
    duplicate_para = by_type.get("duplicate_paragraph_warning", [])
    duplicate_pair = by_type.get("duplicate_pair_key_warning", [])

    lines = [
        f"# Reporte de cambios — {MANUAL_TITLE}",
        f"## Edición {_fmt_date(result['edition_a'])} → {_fmt_date(result['edition_b'])}",
        "",
        "## Resumen",
        "",
        f"- Secciones: {len(section_added)} agregadas, {len(section_removed)} eliminadas, "
        f"{len(section_renamed)} posiblemente renombradas/reubicadas",
        f"- Párrafos: {len(para_added)} agregados, {len(para_removed)} eliminados, "
        f"{len(para_reflowed)} re-cortados entre ediciones (no es un cambio)",
        f"- Pares Field Name/Description: {len(pair_added)} agregados, {len(pair_removed)} eliminados",
        f"- Cambios de contenido: {len(all_content_changes)} totales "
        f"({len(para_changes)} de párrafo, {len(pair_changes)} de descripción de campo) — "
        + ", ".join(f"{k}={v}" for k, v in sorted(result.get("ai_summary", {}).items())),
        "",
    ]

    lines.append(f"## Cambios de negocio a revisar ({len(business_changes)})")
    lines.append("")
    if not business_changes:
        lines.append("_Ninguno en este par de ediciones._")
        lines.append("")
    else:
        by_path = _group_by_path(business_changes)
        for path_str, items in by_path.items():
            lines.append(f"### {path_str}")
            lines.append("")
            for c in items:
                flag = " ⚠️ *(corregido por contenido desaparecido)*" if c.get("safety_net_override") else ""
                if c["change_type"] == "pair_content_changed":
                    lines.append(f"- **{c['name']}** ({c['example_title']}){flag}")
                else:
                    lines.append(f"- Párrafo cambiado{flag}")
                lines.append(f"  - Antes: {c['old']!r}")
                lines.append(f"  - Ahora: {c['new']!r}")
                lines.append(f"  - Razón (IA): {c['ai_reason']}")
            lines.append("")

    lines.append(f"## Secciones agregadas ({len(section_added)})")
    lines.append("")
    if section_added:
        for s in section_added:
            lines.append(f"- {_path_str(s['path'])} ({s['num_paragraphs']} párrafos, {s['num_pairs']} pares)")
    else:
        lines.append("_Ninguna._")
    lines.append("")

    lines.append(f"## Secciones eliminadas ({len(section_removed)})")
    lines.append("")
    if section_removed:
        for s in section_removed:
            lines.append(f"- {_path_str(s['path'])} ({s['num_paragraphs']} párrafos, {s['num_pairs']} pares)")
    else:
        lines.append("_Ninguna._")
    lines.append("")

    if section_renamed:
        lines.append(f"## Secciones posiblemente renombradas/reubicadas ({len(section_renamed)})")
        lines.append("")
        for s in section_renamed:
            lines.append(
                f"- {_path_str(s['path_a'])} → {_path_str(s['path_b'])} (similitud {s['fuzzy_ratio']:.2f})"
            )
        lines.append("")

    lines.append(f"## Párrafos agregados ({len(para_added)})")
    lines.append("")
    if para_added:
        by_path = _group_by_path(para_added)
        for path_str, items in by_path.items():
            lines.append(f"### {path_str}")
            lines.append("")
            for c in items:
                lines.append(f"- {c['text'][:200]!r}")
            lines.append("")
    else:
        lines.append("_Ninguno._")
        lines.append("")

    lines.append(f"## Párrafos eliminados ({len(para_removed)})")
    lines.append("")
    if para_removed:
        by_path = _group_by_path(para_removed)
        for path_str, items in by_path.items():
            lines.append(f"### {path_str}")
            lines.append("")
            for c in items:
                lines.append(f"- {c['text'][:200]!r}")
            lines.append("")
    else:
        lines.append("_Ninguno._")
        lines.append("")

    lines.append(f"## Pares Field Name/Description agregados ({len(pair_added)})")
    lines.append("")
    if pair_added:
        by_path = _group_by_path(pair_added)
        for path_str, items in by_path.items():
            lines.append(f"### {path_str}")
            lines.append("")
            for c in items:
                lines.append(f"- **{c['name']}** ({c['example_title']}): {c['description'][:150]!r}")
            lines.append("")
    else:
        lines.append("_Ninguno._")
        lines.append("")

    lines.append(f"## Pares Field Name/Description eliminados ({len(pair_removed)})")
    lines.append("")
    if pair_removed:
        by_path = _group_by_path(pair_removed)
        for path_str, items in by_path.items():
            lines.append(f"### {path_str}")
            lines.append("")
            for c in items:
                lines.append(f"- **{c['name']}** ({c['example_title']}): {c['description'][:150]!r}")
            lines.append("")
    else:
        lines.append("_Ninguno._")
        lines.append("")

    lines.append(f"## Apéndice: cambios de solo redacción / ruido de extracción ({len(appendix_changes)})")
    lines.append("")
    if appendix_changes:
        by_path = _group_by_path(appendix_changes)
        for path_str, items in by_path.items():
            lines.append(f"### {path_str}")
            lines.append("")
            for c in items:
                label = c["name"] if c["change_type"] == "pair_content_changed" else "párrafo"
                lines.append(f"- {label}: {c['ai_category']} (similitud {c['similarity_ratio']:.2f})")
            lines.append("")
    else:
        lines.append("_Ninguno._")
        lines.append("")

    if duplicate_path or duplicate_para or duplicate_pair or num_overrides or para_reflowed:
        lines.append("## Avisos de confiabilidad")
        lines.append("")
        if num_overrides:
            lines.append(
                f"- {num_overrides} cambio(s) de negocio fueron re-clasificados automáticamente "
                "porque la IA los marcó como redacción/ruido pero se detectó contenido real "
                "desaparecido sin reemplazo (ver marca ⚠️ arriba)."
            )
        if para_reflowed:
            lines.append(
                f"- {len(para_reflowed)} párrafo(s) se re-cortaron distinto entre ediciones "
                "(mismo contenido, reconciliado automáticamente, no es un cambio real)."
            )
        for w in duplicate_path:
            lines.append(
                f"- Ruta(s) de sección repetidas dentro de la misma edición: "
                f"`{w['duplicate_paths_a']}` en la edición vieja, `{w['duplicate_paths_b']}` en la nueva."
            )
        for w in duplicate_para:
            lines.append(
                f"- La sección **{_path_str(w['path'])}** tiene texto de párrafo repetido dentro "
                "de la misma edición — el emparejamiento en esos casos puntuales puede no ser "
                "1:1 confiable."
            )
        for w in duplicate_pair:
            lines.append(
                f"- La sección **{_path_str(w['path'])}** tiene claves de par (tabla+campo) "
                "repetidas dentro de la misma edición — el emparejamiento en esos casos "
                "puntuales puede no ser 1:1 confiable."
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

        by_type = {}
        for c in result["changes"]:
            by_type.setdefault(c["change_type"], []).append(c)
        business_changes = sum(
            1
            for c in by_type.get("paragraph_content_changed", []) + by_type.get("pair_content_changed", [])
            if c["ai_category"] == "business_rule_change"
        )
        index_lines.append(
            f"- [{_fmt_date(result['edition_a'])} → {_fmt_date(result['edition_b'])}]"
            f"({out_path.name}) — {business_changes} cambios de negocio a revisar"
        )
        print(f"{out_path.name}: {business_changes} cambios de negocio")

    (OUTPUT_DIR / "index.md").write_text("\n".join(index_lines) + "\n")


if __name__ == "__main__":
    main()
