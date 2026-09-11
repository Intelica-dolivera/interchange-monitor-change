"""
Modulo 7 - Reporte de cambios para el manual base_ii_clearing_data_codes.

Ultimo eslabon del pipeline: toma la salida ya enriquecida del Modulo 5 (cambios
deterministicos del Modulo 4 + clasificacion IA de los `code_content_changed`) y genera un
reporte en Markdown, legible por una persona, por cada par de ediciones consecutivas.

Modulo 6 (Validacion con Plataforma STD) se salteo por ahora -sigue tentativo, sin definir,
segun el plan original del usuario- asi que este modulo consume directo la salida del
Modulo 5.

Principio de diseno: no todos los cambios pesan lo mismo para alguien revisando el reporte.
- `code_content_changed` con `ai_category == business_rule_change` es lo que de verdad
  importa revisar -va primero, con el texto viejo/nuevo completo y la razon que dio el LLM.
- `editorial_reword` / `extraction_noise` NO requieren revision (por definicion, no cambio
  nada de fondo) -se listan en una seccion aparte, compactos (solo codigo+columna+ratio de
  similitud, sin repetir el texto completo), para que el reporte principal no se llene de
  ruido pero la info siga disponible para quien la necesite.
- Altas/bajas de tabla y de codigo son siempre accionables (son eventos binarios, no hay
  "matiz" que juzgar) -van en secciones propias.
- `duplicate_code_warning` y los `safety_net_override` de Modulo 5 se listan como avisos de
  confiabilidad al final, no como cambios en si -le dicen al lector en que partes del
  reporte conviene desconfiar un poco mas de la deteccion automatica.

Los titulos de tabla anormalmente largos (>80 caracteres) son casi siempre el efecto ya
documentado del gap del glosario (ver local_memory/TODO.md item 1) -no se filtran (el dato
es real, se decidio no ocultar nada), pero se truncan visualmente para que no rompan el
formato del reporte.
"""

import json
import sys
from pathlib import Path

MANUAL_SLUG = "base_ii_clearing_data_codes"
MANUAL_TITLE = "BASE II Clearing Data Codes"
INPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "05_interpretacion_cambios_ia"
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "07_reporte_cambios"

MAX_TABLE_NAME_LEN = 80


def _short_table_name(name: str) -> str:
    flat = " ".join(name.split())
    if len(flat) <= MAX_TABLE_NAME_LEN:
        return flat
    return flat[: MAX_TABLE_NAME_LEN - 1].rstrip() + "…"


def _fmt_date(edition: str) -> str:
    return f"{edition[6:8]}/{edition[4:6]}/{edition[0:4]}"


def _group_by_table(items: list) -> dict:
    grouped = {}
    for item in items:
        grouped.setdefault(item["table"], []).append(item)
    return dict(sorted(grouped.items(), key=lambda kv: _short_table_name(kv[0])))


def _render_business_rule_changes(lines: list, changes: list) -> None:
    real_changes = [c for c in changes if c["ai_category"] == "business_rule_change"]
    lines.append(f"## Cambios de negocio a revisar ({len(real_changes)})")
    lines.append("")
    if not real_changes:
        lines.append("_Ninguno en este par de ediciones._")
        lines.append("")
        return

    for table, items in _group_by_table(real_changes).items():
        lines.append(f"### {_short_table_name(table)}")
        lines.append("")
        for c in items:
            flag = " ⚠️ *(la IA lo clasifico distinto; se corrigio por contenido desaparecido)*" if c.get("safety_net_override") else ""
            lines.append(f"- **Código `{c['code']}`** — columna *{c['column']}*{flag}")
            lines.append(f"  - Antes: {c['old']!r}")
            lines.append(f"  - Ahora: {c['new']!r}")
            lines.append(f"  - Razón (IA): {c['ai_reason']}")
        lines.append("")


def _render_table_structural_changes(lines: list, changes_added: list, changes_removed: list, changes_renamed: list) -> None:
    lines.append(f"## Tablas agregadas ({len(changes_added)})")
    lines.append("")
    if changes_added:
        for c in changes_added:
            lines.append(f"- {_short_table_name(c['table'])} ({c['num_rows']} filas)")
    else:
        lines.append("_Ninguna._")
    lines.append("")

    lines.append(f"## Tablas eliminadas ({len(changes_removed)})")
    lines.append("")
    if changes_removed:
        for c in changes_removed:
            lines.append(f"- {_short_table_name(c['table'])} ({c['num_rows']} filas)")
    else:
        lines.append("_Ninguna._")
    lines.append("")

    if changes_renamed:
        lines.append(f"## Tablas posiblemente renombradas ({len(changes_renamed)})")
        lines.append("")
        for c in changes_renamed:
            lines.append(
                f"- {_short_table_name(c['table_a'])} → {_short_table_name(c['table_b'])} "
                f"(similitud {c['fuzzy_ratio']:.2f})"
            )
        lines.append("")


def _render_code_changes(lines: list, title: str, changes: list) -> None:
    lines.append(f"## {title} ({len(changes)})")
    lines.append("")
    if not changes:
        lines.append("_Ninguno._")
        lines.append("")
        return
    for table, items in _group_by_table(changes).items():
        lines.append(f"### {_short_table_name(table)}")
        lines.append("")
        for c in items:
            preview = " | ".join(cell.replace("\n", " ")[:60] for cell in c["cells"])
            lines.append(f"- `{c['code']}`: {preview}")
        lines.append("")


def _render_minor_content_changes(lines: list, changes: list) -> None:
    minor = [c for c in changes if c["ai_category"] != "business_rule_change"]
    lines.append(f"## Apéndice: cambios de solo redacción / ruido de extracción ({len(minor)})")
    lines.append("")
    lines.append("No requieren revisión — el significado no cambió (o el cambio es un artefacto")
    lines.append("de extracción del PDF), según la clasificación automática.")
    lines.append("")
    if not minor:
        lines.append("_Ninguno._")
        lines.append("")
        return
    for table, items in _group_by_table(minor).items():
        lines.append(f"### {_short_table_name(table)}")
        lines.append("")
        for c in items:
            lines.append(
                f"- `{c['code']}` / *{c['column']}* — {c['ai_category']} "
                f"(similitud texto {c['similarity_ratio']:.2f})"
            )
        lines.append("")


def _render_caveats(lines: list, duplicate_warnings: list, num_overrides: int) -> None:
    if not duplicate_warnings and not num_overrides:
        return
    lines.append("## Avisos de confiabilidad")
    lines.append("")
    if num_overrides:
        lines.append(
            f"- {num_overrides} cambio(s) de negocio fueron re-clasificados automáticamente "
            "porque la IA los marcó como redacción/ruido pero se detectó contenido real "
            "desaparecido sin reemplazo (ver marca ⚠️ arriba)."
        )
    for c in duplicate_warnings:
        lines.append(
            f"- La tabla **{_short_table_name(c['table'])}** tiene códigos repetidos dentro de "
            f"la misma edición (`{c['duplicate_codes_a']}` en la edición vieja, "
            f"`{c['duplicate_codes_b']}` en la nueva) — el emparejamiento código-a-código en "
            "esta tabla puede no ser 1:1 confiable."
        )
    lines.append("")


def render_report(result: dict) -> str:
    changes = result["changes"]
    by_type = {}
    for c in changes:
        by_type.setdefault(c["change_type"], []).append(c)

    content_changes = by_type.get("code_content_changed", [])
    num_overrides = sum(1 for c in content_changes if c.get("safety_net_override"))

    lines = [
        f"# Reporte de cambios — {MANUAL_TITLE}",
        f"## Edición {_fmt_date(result['edition_a'])} → {_fmt_date(result['edition_b'])}",
        "",
        "## Resumen",
        "",
        f"- Tablas: {len(by_type.get('table_added', []))} agregadas, "
        f"{len(by_type.get('table_removed', []))} eliminadas, "
        f"{len(by_type.get('table_renamed', []))} renombradas",
        f"- Códigos: {len(by_type.get('code_added', []))} agregados, "
        f"{len(by_type.get('code_removed', []))} eliminados",
        f"- Cambios de contenido: {len(content_changes)} totales — "
        + ", ".join(f"{k}={v}" for k, v in sorted(result.get("ai_summary", {}).items())),
        "",
    ]

    _render_business_rule_changes(lines, content_changes)
    _render_table_structural_changes(
        lines,
        by_type.get("table_added", []),
        by_type.get("table_removed", []),
        by_type.get("table_renamed", []),
    )
    _render_code_changes(lines, "Códigos agregados", by_type.get("code_added", []))
    _render_code_changes(lines, "Códigos eliminados", by_type.get("code_removed", []))
    _render_minor_content_changes(lines, content_changes)
    _render_caveats(lines, by_type.get("duplicate_code_warning", []), num_overrides)

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

        real_changes = sum(
            1
            for c in result["changes"]
            if c["change_type"] == "code_content_changed" and c["ai_category"] == "business_rule_change"
        )
        added = len(
            [c for c in result["changes"] if c["change_type"] in ("table_added", "code_added")]
        )
        removed = len(
            [c for c in result["changes"] if c["change_type"] in ("table_removed", "code_removed")]
        )
        index_lines.append(
            f"- [{_fmt_date(result['edition_a'])} → {_fmt_date(result['edition_b'])}]"
            f"({out_path.name}) — {real_changes} cambios de negocio a revisar, "
            f"{added} altas, {removed} bajas"
        )
        print(f"{out_path.name}: {real_changes} cambios de negocio, {added} altas, {removed} bajas")

    (OUTPUT_DIR / "index.md").write_text("\n".join(index_lines) + "\n")


if __name__ == "__main__":
    main()
