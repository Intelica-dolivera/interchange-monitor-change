"""
Modulo 7 - Reporte de cambios para el manual
international_full_service_pos_online_messages_processing_specifications.

Ultimo eslabon del pipeline: toma la salida ya clasificada del Modulo 5 y genera un reporte
en Markdown por cada par de ediciones consecutivas. Modulo 6 sigue tentativo/sin definir,
igual que en los otros 5 manuales.

Diseno de reporte, adaptado a este manual (sin grilla de campos, ver Modulo 2/3/4):
- Cambios de negocio a revisar (`paragraph_content_changed` con `ai_category ==
  business_rule_change`) van primero, agrupados por RUTA de seccion completa.
- Secciones/parrafos agregados/eliminados en sus propias secciones.
- Secciones posiblemente renombradas (fuzzy -en este manual puede ser un renombre real O una
  promocion de nivel jerarquico, ver Modulo 3/4).
- Secciones con posible reubicacion de contenido (agregado 2026-09-04, ver docstring de
  Modulo 3 -distinto del renombre fuzzy de arriba: aca la RUTA cambio demasiado para el fuzzy
  de titulo, pero el CONTENIDO de parrafos coincide). Los paths involucrados se excluyen de
  las listas planas de "Secciones agregadas/eliminadas" de abajo (se muestran una sola vez,
  aca) -pura reagrupacion visual, `section_added`/`section_removed` siguen intactos en el
  JSON de Modulo 4, el reporte decide como agruparlos.
- Apendice compacto de redaccion/ruido.
- Avisos de confiabilidad: duplicados, `safety_net_override`, Y `paragraph_reflowed` (parrafos
  re-cortados distinto entre ediciones por reflow de pagina, reconciliados automaticamente -no
  son un cambio real, se listan aca solo para trazabilidad completa, nunca como "cambio de
  negocio". Ver Modulo 3 docstring sobre el fix acotado del 2026-08-19: reduce pero no elimina
  el ruido de reflow -el residuo que sigue disparando `safety_net_override` queda visible via esa
  marca, no oculto).
"""

import json
import sys
from pathlib import Path

MANUAL_SLUG = "international_full_service_pos_online_messages_processing_specifications"
MANUAL_TITLE = "Full Service POS Online Messages – Processing Specifications (International)"
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

    content_changes = by_type.get("paragraph_content_changed", [])
    business_changes = [c for c in content_changes if c["ai_category"] == "business_rule_change"]
    appendix_changes = [c for c in content_changes if c["ai_category"] != "business_rule_change"]
    num_overrides = sum(1 for c in content_changes if c.get("safety_net_override"))

    section_added = by_type.get("section_added", [])
    section_removed = by_type.get("section_removed", [])
    section_renamed = by_type.get("section_renamed", [])
    section_moved = by_type.get("possible_section_move", [])
    moved_removed_paths = {tuple(m["path_removed"]) for m in section_moved}
    moved_added_paths = {tuple(m["path_added"]) for m in section_moved}
    section_added = [s for s in section_added if tuple(s["path"]) not in moved_added_paths]
    section_removed = [s for s in section_removed if tuple(s["path"]) not in moved_removed_paths]
    para_added = by_type.get("paragraph_added", [])
    para_removed = by_type.get("paragraph_removed", [])
    para_reflowed = by_type.get("paragraph_reflowed", [])
    duplicate_path = by_type.get("duplicate_path_warning", [])
    duplicate_para = by_type.get("duplicate_paragraph_warning", [])
    relocated_within_section = [c for c in content_changes if c.get("content_relocated_within_section")]

    lines = [
        f"# Reporte de cambios — {MANUAL_TITLE}",
        f"## Edición {_fmt_date(result['edition_a'])} → {_fmt_date(result['edition_b'])}",
        "",
        "## Resumen",
        "",
        f"- Secciones: {len(section_added)} agregadas, {len(section_removed)} eliminadas, "
        f"{len(section_renamed)} posiblemente renombradas, {len(section_moved)} con posible "
        "reubicación de contenido",
        f"- Párrafos: {len(para_added)} agregados, {len(para_removed)} eliminados, "
        f"{len(para_reflowed)} re-cortados entre ediciones (mismo contenido, no es un cambio)",
        f"- Cambios de contenido: {len(content_changes)} totales — "
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
                lines.append(f"- Párrafo cambiado{flag}")
                lines.append(f"  - Antes: {c['old']!r}")
                lines.append(f"  - Ahora: {c['new']!r}")
                lines.append(f"  - Razón (IA): {c['ai_reason']}")
            lines.append("")

    lines.append(f"## Secciones agregadas ({len(section_added)})")
    lines.append("")
    if section_added:
        for s in section_added:
            lines.append(f"- {_path_str(s['path'])} ({s['num_paragraphs']} párrafos)")
    else:
        lines.append("_Ninguna._")
    lines.append("")

    lines.append(f"## Secciones eliminadas ({len(section_removed)})")
    lines.append("")
    if section_removed:
        for s in section_removed:
            lines.append(f"- {_path_str(s['path'])} ({s['num_paragraphs']} párrafos)")
    else:
        lines.append("_Ninguna._")
    lines.append("")

    if section_renamed:
        lines.append(f"## Secciones posiblemente renombradas ({len(section_renamed)})")
        lines.append("")
        for s in section_renamed:
            lines.append(
                f"- {_path_str(s['path_a'])} → {_path_str(s['path_b'])} (similitud {s['fuzzy_ratio']:.2f})"
            )
        lines.append("")

    if section_moved:
        lines.append(f"## Secciones con posible reubicación de contenido ({len(section_moved)})")
        lines.append("")
        lines.append(
            "_El título/ruta cambió demasiado para el emparejamiento fuzzy de arriba, pero el "
            "contenido de los párrafos coincide en buena parte — revisar si es una reubicación "
            "real o una coincidencia (ver diseño en Módulo 3)._"
        )
        lines.append("")
        for m in section_moved:
            lines.append(
                f"- ⚠️ {_path_str(m['path_removed'])} ({m['num_paragraphs_removed']} párrafos) → "
                f"{_path_str(m['path_added'])} ({m['num_paragraphs_added']} párrafos) "
                f"— cobertura {m['coverage']:.0%}"
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

    lines.append(f"## Apéndice: cambios de solo redacción / ruido de extracción ({len(appendix_changes)})")
    lines.append("")
    if appendix_changes:
        by_path = _group_by_path(appendix_changes)
        for path_str, items in by_path.items():
            lines.append(f"### {path_str}")
            lines.append("")
            for c in items:
                lines.append(f"- {c['ai_category']} (similitud {c['similarity_ratio']:.2f})")
            lines.append("")
    else:
        lines.append("_Ninguno._")
        lines.append("")

    if duplicate_path or duplicate_para or num_overrides or para_reflowed or relocated_within_section:
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
                "(mismo contenido, solo el punto de corte del bloque cambió — reconciliado "
                "automáticamente, no aparece arriba como cambio)."
            )
        if relocated_within_section:
            lines.append(
                f"- {len(relocated_within_section)} párrafo(s) tenían un tramo que parecía "
                "desaparecer, pero se encontró intacto en OTRO párrafo de la misma sección "
                "(redistribución no adyacente, no una remoción real — no forzó reclasificación):"
            )
            for c in relocated_within_section:
                for chunk in c["content_relocated_within_section"]:
                    lines.append(f"  - **{_path_str(c['path'])}**: {chunk[:150]!r}")
        for w in duplicate_path:
            lines.append(
                f"- Ruta(s) de sección repetidas dentro de la misma edición: "
                f"`{w['duplicate_paths_a']}` en la edición vieja, `{w['duplicate_paths_b']}` en la nueva."
            )
        for w in duplicate_para:
            lines.append(
                f"- La sección **{_path_str(w['path'])}** tiene texto de párrafo repetido dentro "
                f"de la misma edición — el emparejamiento en esos casos puntuales puede no ser "
                "1:1 confiable."
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
            for c in by_type.get("paragraph_content_changed", [])
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
