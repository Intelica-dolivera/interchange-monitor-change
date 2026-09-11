"""
Modulo 7 - Reporte de cambios para el manual
visanet_settlement_service_vss_user_guide_volume_2_reports.

Ultimo eslabon del pipeline: toma la salida ya clasificada del Modulo 5 y genera un reporte en
Markdown por cada par de ediciones consecutivas. Modulo 6 sigue tentativo/sin definir.

A diferencia de los otros manuales, este procesa 5 apendices INDEPENDIENTES (ver Modulo 1-4:
sin jerarquia de secciones unica para todo el documento) -por eso cada item se agrupa por
`(apendice, table_title)` en vez de por `path`, y el nombre legible del apendice (ver
`APPENDIX_LABELS`, mismo texto que separa las secciones en Modulo 1) se antepone a cada
encabezado de grupo para que el lector sepa de inmediato en que parte del documento esta.

Mismo principio de diseno que los demas manuales: cambios de negocio a revisar primero
(`row_content_changed` con `ai_category == business_rule_change`, agrupados); altas/bajas
estructurales (tabla, fila, encabezado, parrafo) en sus propias secciones; apendice de
redaccion/ruido; avisos de confiabilidad (`duplicate_row_key_warning`, `safety_net_override`)
al final. Este manual NO tiene deteccion dedicada de transiciones Reserved<->definido (Modulo 4
no emite ese change_type aca, a diferencia del 3er/4to manual) -las altas/bajas de fila ya
muestran el contenido completo de la fila, asi que un lector puede identificar una transicion
Reserved a simple vista sin una seccion dedicada.
"""

import json
import sys
from pathlib import Path

MANUAL_SLUG = "visanet_settlement_service_vss_user_guide_volume_2_reports"
MANUAL_TITLE = "VisaNet Settlement Service (VSS) User Guide, Volume 2, Reports"
INPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "05_interpretacion_cambios_ia"
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "07_reporte_cambios"

APPENDICES = ["appendix_a", "appendix_b", "appendix_c", "appendix_d", "appendix_e"]
APPENDIX_LABELS = {
    "appendix_a": "Apéndice A: VSS Reports-Print-Ready Formats",
    "appendix_b": "Apéndice B: VSS Reports-Machine-Readable Formats",
    "appendix_c": "Apéndice C: VSS Codes",
    "appendix_d": "Apéndice D: SMS Reports and Raw Data",
    "appendix_e": "Apéndice E: VSS Business Transaction Types Cross-Reference",
}


def _fmt_date(edition: str) -> str:
    return f"{edition[6:8]}/{edition[4:6]}/{edition[0:4]}"


def _flatten(result: dict) -> list:
    """Aplana `appendices` (dict de listas) en una sola lista, inyectando el apendice de
    origen en cada item (`_appendix`) -ningun item lo trae de por si, ver docstring del
    modulo."""
    flat = []
    for appendix in APPENDICES:
        for item in result["appendices"].get(appendix, []):
            item = dict(item)
            item["_appendix"] = appendix
            flat.append(item)
    return flat


def _group_key(item: dict) -> tuple:
    return (item["_appendix"], item.get("table_title", ""))


def _group_by_appendix_table(items: list) -> dict:
    grouped = {}
    for item in items:
        grouped.setdefault(_group_key(item), []).append(item)
    return dict(sorted(grouped.items(), key=lambda kv: (kv[0][0], kv[0][1])))


def _group_label(appendix: str, table_title: str) -> str:
    label = APPENDIX_LABELS[appendix]
    return f"{label} — {table_title}" if table_title else label


def _row_summary(columns: dict, anchor_column: str, max_len: int = 200) -> str:
    parts = [
        f"{name}: {value}"
        for name, value in columns.items()
        if name not in (anchor_column, "__unassigned_prefix__") and value
    ]
    text = "; ".join(parts)
    return text[:max_len] + ("…" if len(text) > max_len else "")


def _render_business_changes(lines: list, changes: list) -> None:
    business = [c for c in changes if c["change_type"] == "row_content_changed" and c["ai_category"] == "business_rule_change"]
    lines.append(f"## Cambios de negocio a revisar ({len(business)})")
    lines.append("")
    if not business:
        lines.append("_Ninguno en este par de ediciones._")
        lines.append("")
        return
    for group_key, items in _group_by_appendix_table(business).items():
        lines.append(f"### {_group_label(*group_key)}")
        lines.append("")
        by_row = {}
        for item in items:
            by_row.setdefault(item["key"], []).append(item)
        for row_key, entries in sorted(by_row.items()):
            lines.append(f"- **{row_key}**")
            for e in entries:
                flag = " ⚠️ *(corregido por contenido desaparecido)*" if e.get("safety_net_override") else ""
                lines.append(f"  - Columna **{e['column']}**{flag}")
                lines.append(f"    - Antes: {e['old']!r}")
                lines.append(f"    - Ahora: {e['new']!r}")
                lines.append(f"    - Razón (IA): {e['ai_reason']}")
        lines.append("")


def _render_row_structural(lines: list, changes: list, change_type: str, heading: str) -> None:
    filtered = [c for c in changes if c["change_type"] == change_type]
    lines.append(f"## {heading} ({len(filtered)})")
    lines.append("")
    if not filtered:
        lines.append("_Ninguna._")
        lines.append("")
        return
    for group_key, items in _group_by_appendix_table(filtered).items():
        lines.append(f"### {_group_label(*group_key)}")
        lines.append("")
        for c in items:
            row = c["row"]
            summary = _row_summary(row["columns"], row["anchor_column"])
            lines.append(f"- **{c['key']}**{f': {summary}' if summary else ''}")
        lines.append("")


def _render_table_structural(lines: list, changes: list) -> None:
    added = [c for c in changes if c["change_type"] == "table_added"]
    removed = [c for c in changes if c["change_type"] == "table_removed"]
    renamed = [c for c in changes if c["change_type"] == "table_renamed"]

    lines.append(f"## Tablas agregadas ({len(added)})")
    lines.append("")
    if added:
        for group_key, items in _group_by_appendix_table(added).items():
            for c in items:
                lines.append(f"- {APPENDIX_LABELS[group_key[0]]} — **{c['table_title']}** ({c['num_rows']} filas)")
    else:
        lines.append("_Ninguna._")
    lines.append("")

    lines.append(f"## Tablas eliminadas ({len(removed)})")
    lines.append("")
    if removed:
        for group_key, items in _group_by_appendix_table(removed).items():
            for c in items:
                lines.append(f"- {APPENDIX_LABELS[group_key[0]]} — **{c['table_title']}** ({c['num_rows']} filas)")
    else:
        lines.append("_Ninguna._")
    lines.append("")

    if renamed:
        lines.append(f"## Tablas posiblemente renombradas/reubicadas ({len(renamed)})")
        lines.append("")
        for c in renamed:
            lines.append(
                f"- {APPENDIX_LABELS[c['_appendix']]} — **{c['table_title_old']}** → "
                f"**{c['table_title_new']}** (similitud {c['similarity_ratio']:.3f})"
            )
        lines.append("")


def _render_heading_structural(lines: list, changes: list) -> None:
    added = [c for c in changes if c["change_type"] == "heading_added"]
    removed = [c for c in changes if c["change_type"] == "heading_removed"]
    renamed = [c for c in changes if c["change_type"] == "heading_renamed"]
    if not (added or removed or renamed):
        return

    lines.append(f"## Encabezados de sección agregados ({len(added)})")
    lines.append("")
    if added:
        for c in added:
            lines.append(f"- {APPENDIX_LABELS[c['_appendix']]} — {c['text']}")
    else:
        lines.append("_Ninguno._")
    lines.append("")

    lines.append(f"## Encabezados de sección eliminados ({len(removed)})")
    lines.append("")
    if removed:
        for c in removed:
            lines.append(f"- {APPENDIX_LABELS[c['_appendix']]} — {c['text']}")
    else:
        lines.append("_Ninguno._")
    lines.append("")

    if renamed:
        lines.append(f"## Encabezados de sección posiblemente renombrados ({len(renamed)})")
        lines.append("")
        for c in renamed:
            lines.append(
                f"- {APPENDIX_LABELS[c['_appendix']]} — {c['text_old']} → {c['text_new']} "
                f"(similitud {c['similarity_ratio']:.3f})"
            )
        lines.append("")


def _render_paragraph_structural(lines: list, changes: list) -> None:
    added = [c for c in changes if c["change_type"] == "paragraph_added"]
    removed = [c for c in changes if c["change_type"] == "paragraph_removed"]

    lines.append(f"## Párrafos agregados ({len(added)})")
    lines.append("")
    if added:
        for c in added:
            lines.append(f"- {APPENDIX_LABELS[c['_appendix']]} — {c['text'][:200]!r}")
    else:
        lines.append("_Ninguno._")
    lines.append("")

    lines.append(f"## Párrafos eliminados ({len(removed)})")
    lines.append("")
    if removed:
        for c in removed:
            lines.append(f"- {APPENDIX_LABELS[c['_appendix']]} — {c['text'][:200]!r}")
    else:
        lines.append("_Ninguno._")
    lines.append("")


def _render_noise_appendix(lines: list, changes: list) -> None:
    noise = [c for c in changes if c["change_type"] == "row_content_changed" and c["ai_category"] != "business_rule_change"]
    lines.append(f"## Apéndice: cambios de solo redacción / ruido de extracción ({len(noise)})")
    lines.append("")
    if not noise:
        lines.append("_Ninguno._")
        lines.append("")
        return
    for group_key, items in _group_by_appendix_table(noise).items():
        lines.append(f"### {_group_label(*group_key)}")
        lines.append("")
        for c in items:
            lines.append(f"- **{c['key']}** / {c['column']}: {c['ai_category']} (similitud {c['similarity_ratio']:.2f})")
        lines.append("")


def render_report(result: dict) -> str:
    changes = _flatten(result)
    row_content_changed = [c for c in changes if c["change_type"] == "row_content_changed"]
    num_overrides = sum(1 for c in row_content_changed if c.get("safety_net_override"))
    duplicate_warnings = [c for c in changes if c["change_type"] == "duplicate_row_key_warning"]

    lines = [
        f"# Reporte de cambios — {MANUAL_TITLE}",
        f"## Edición {_fmt_date(result['edition_a'])} → {_fmt_date(result['edition_b'])}",
        "",
        "## Resumen",
        "",
        f"- Tablas: {sum(1 for c in changes if c['change_type']=='table_added')} agregadas, "
        f"{sum(1 for c in changes if c['change_type']=='table_removed')} eliminadas, "
        f"{sum(1 for c in changes if c['change_type']=='table_renamed')} posiblemente renombradas/reubicadas",
        f"- Filas: {sum(1 for c in changes if c['change_type']=='row_added')} agregadas, "
        f"{sum(1 for c in changes if c['change_type']=='row_removed')} eliminadas",
        f"- Encabezados de sección: {sum(1 for c in changes if c['change_type']=='heading_added')} agregados, "
        f"{sum(1 for c in changes if c['change_type']=='heading_removed')} eliminados, "
        f"{sum(1 for c in changes if c['change_type']=='heading_renamed')} posiblemente renombrados",
        f"- Párrafos: {sum(1 for c in changes if c['change_type']=='paragraph_added')} agregados, "
        f"{sum(1 for c in changes if c['change_type']=='paragraph_removed')} eliminados",
        f"- Cambios de contenido: {len(row_content_changed)} totales — "
        + ", ".join(f"{k}={v}" for k, v in sorted(result.get("ai_summary", {}).items())),
        "",
    ]

    _render_business_changes(lines, changes)
    _render_row_structural(lines, changes, "row_added", "Filas agregadas")
    _render_row_structural(lines, changes, "row_removed", "Filas eliminadas")
    _render_table_structural(lines, changes)
    _render_heading_structural(lines, changes)
    _render_paragraph_structural(lines, changes)
    _render_noise_appendix(lines, changes)

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
                f"- {APPENDIX_LABELS[w['_appendix']]} — la tabla **{w['table_title']}** tiene "
                f"claves de fila repetidas dentro de la misma edición (`{w['duplicate_keys_a']}` "
                f"en la edición vieja, `{w['duplicate_keys_b']}` en la nueva) — el emparejamiento "
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

        changes = _flatten(result)
        business_changes = sum(
            1
            for c in changes
            if c["change_type"] == "row_content_changed" and c["ai_category"] == "business_rule_change"
        )
        index_lines.append(
            f"- [{_fmt_date(result['edition_a'])} → {_fmt_date(result['edition_b'])}]"
            f"({out_path.name}) — {business_changes} cambios de negocio a revisar"
        )
        print(f"{out_path.name}: {business_changes} cambios de negocio")

    (OUTPUT_DIR / "index.md").write_text("\n".join(index_lines) + "\n")


if __name__ == "__main__":
    main()
