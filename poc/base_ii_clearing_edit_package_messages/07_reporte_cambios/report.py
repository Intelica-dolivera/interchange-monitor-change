"""
Modulo 7 - Reporte de cambios para el manual base_ii_clearing_edit_package_messages.

Ultimo eslabon del pipeline: toma la salida ya enriquecida del Modulo 5 (cambios
deterministicos del Modulo 4 + clasificacion IA de los `ficha_content_changed`) y genera un
reporte en Markdown, legible por una persona, por cada par de ediciones consecutivas. Mismo
principio de diseno que el Modulo 7 del manual 1 (no todos los cambios pesan lo mismo:
`business_rule_change` primero con texto completo, `editorial_reword`/`extraction_noise` en
un apendice compacto, altas/bajas en sus propias secciones, avisos de confiabilidad al
final) -Modulo 6 (Validacion con Plataforma STD) se salteo, sigue tentativo, este modulo
consume directo la salida del Modulo 5.

Diferencias de diseno respecto al Modulo 7 del manual 1 (ver reference_pipeline-vs-
technical-manuals en la memoria del asistente si hace falta mas contexto):

1. No hay nivel "tabla" en este manual -se agrupa por FICHA (codigo) en vez de por tabla.
   Una ficha puede tener varios campos cambiados a la vez (`title`/`description`/`action`/
   `transaction_types`); agruparlos bajo un mismo encabezado de ficha es mas legible que
   listarlos sueltos, porque casi siempre son la MISMA historia de negocio contada en mas
   de un campo (ej. ficha `V0173`: `title`+`description`+`transaction_types` cambiaron
   juntos por el mismo motivo).

2. Los cambios (`ficha_content_changed`) no traen el titulo de la ficha -Modulo 4/5 no lo
   necesitaban para su trabajo. El reporte SI lo necesita para dar contexto legible, asi que
   se carga aparte desde la salida ya emparejada del Modulo 3 (mismo patron que el Modulo 5
   ya usa para el prompt del LLM -`title_by_code`, ver `classify.py`- reutilizado aca; no es
   nuevo en el proyecto). Fichas agregadas/eliminadas SI traen su titulo directo en el
   cambio (Modulo 4 ya lo incluye), no hace falta el lookup para esas secciones.

3. No hay `table_added`/`table_removed`/`table_renamed` (no existe ese nivel) -solo
   `ficha_added`/`ficha_removed`. `duplicate_code_warning` tampoco es por tabla: es UN aviso
   por par de ediciones (a nivel de todo el documento), no una lista de tablas afectadas.

Los titulos de ficha son cortos por naturaleza (son "MENSAJE EN MAYUSCULAS", no nombres de
tabla largos como el otro manual) -no hace falta la logica de truncado del Modulo 7 del
manual 1.
"""

import json
import sys
from pathlib import Path

MANUAL_SLUG = "base_ii_clearing_edit_package_messages"
MANUAL_TITLE = "BASE II Clearing Edit Package Messages"
INPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "05_interpretacion_cambios_ia"
MATCH_DIR = Path(__file__).resolve().parents[1] / "data" / "03_emparejamiento_bloques"
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "07_reporte_cambios"

FIELD_LABELS = {
    "title": "Título",
    "description": "Description",
    "action": "Action",
    "transaction_types": "Transaction Types",
}


def _title_by_code(edition_pair_name: str) -> dict:
    match_path = MATCH_DIR / edition_pair_name
    match_result = json.loads(match_path.read_text())
    return {f["code"]: f["title_b"] for f in match_result.get("fichas_matched", [])}


def _fmt_date(edition: str) -> str:
    return f"{edition[6:8]}/{edition[4:6]}/{edition[0:4]}"


def _group_by_code(items: list) -> dict:
    grouped = {}
    for item in items:
        grouped.setdefault(item["code"], []).append(item)
    return dict(sorted(grouped.items()))


def _render_business_rule_changes(lines: list, changes: list, title_by_code: dict) -> None:
    real_changes = [c for c in changes if c["ai_category"] == "business_rule_change"]
    lines.append(f"## Cambios de negocio a revisar ({len(real_changes)})")
    lines.append("")
    if not real_changes:
        lines.append("_Ninguno en este par de ediciones._")
        lines.append("")
        return

    for code, items in _group_by_code(real_changes).items():
        title = title_by_code.get(code, "")
        lines.append(f"### `{code}` — {title}")
        lines.append("")
        for c in items:
            flag = " ⚠️ *(la IA lo clasifico distinto; se corrigio por contenido desaparecido)*" if c.get("safety_net_override") else ""
            lines.append(f"- **{FIELD_LABELS.get(c['field'], c['field'])}**{flag}")
            lines.append(f"  - Antes: {c['old']!r}")
            lines.append(f"  - Ahora: {c['new']!r}")
            lines.append(f"  - Razón (IA): {c['ai_reason']}")
        lines.append("")


def _render_ficha_structural_changes(lines: list, added: list, removed: list) -> None:
    lines.append(f"## Fichas agregadas ({len(added)})")
    lines.append("")
    if added:
        for c in added:
            lines.append(f"- `{c['code']}` — {c['title']}")
    else:
        lines.append("_Ninguna._")
    lines.append("")

    lines.append(f"## Fichas eliminadas ({len(removed)})")
    lines.append("")
    if removed:
        for c in removed:
            lines.append(f"- `{c['code']}` — {c['title']}")
    else:
        lines.append("_Ninguna._")
    lines.append("")


def _render_minor_content_changes(lines: list, changes: list, title_by_code: dict) -> None:
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
    for code, items in _group_by_code(minor).items():
        title = title_by_code.get(code, "")
        lines.append(f"### `{code}` — {title}")
        lines.append("")
        for c in items:
            lines.append(
                f"- *{FIELD_LABELS.get(c['field'], c['field'])}* — {c['ai_category']} "
                f"(similitud texto {c['similarity_ratio']:.2f})"
            )
        lines.append("")


def _render_caveats(lines: list, duplicate_warning: dict | None, num_overrides: int) -> None:
    if not duplicate_warning and not num_overrides:
        return
    lines.append("## Avisos de confiabilidad")
    lines.append("")
    if num_overrides:
        lines.append(
            f"- {num_overrides} cambio(s) de negocio fueron re-clasificados automáticamente "
            "porque la IA los marcó como redacción/ruido pero se detectó contenido real "
            "desaparecido sin reemplazo (ver marca ⚠️ arriba)."
        )
    if duplicate_warning:
        lines.append(
            "- Hay códigos de ficha repetidos dentro de la misma edición "
            f"(`{duplicate_warning['duplicate_codes_a']}` en la edición vieja, "
            f"`{duplicate_warning['duplicate_codes_b']}` en la nueva) — el emparejamiento "
            "código-a-código puede no ser 1:1 confiable para esos códigos puntuales."
        )
    lines.append("")


def render_report(result: dict, title_by_code: dict) -> str:
    changes = result["changes"]
    by_type = {}
    for c in changes:
        by_type.setdefault(c["change_type"], []).append(c)

    content_changes = by_type.get("ficha_content_changed", [])
    num_overrides = sum(1 for c in content_changes if c.get("safety_net_override"))
    duplicate_warning = (by_type.get("duplicate_code_warning") or [None])[0]

    lines = [
        f"# Reporte de cambios — {MANUAL_TITLE}",
        f"## Edición {_fmt_date(result['edition_a'])} → {_fmt_date(result['edition_b'])}",
        "",
        "## Resumen",
        "",
        f"- Fichas: {len(by_type.get('ficha_added', []))} agregadas, "
        f"{len(by_type.get('ficha_removed', []))} eliminadas",
        f"- Cambios de contenido: {len(content_changes)} totales — "
        + ", ".join(f"{k}={v}" for k, v in sorted(result.get("ai_summary", {}).items())),
        "",
    ]

    _render_business_rule_changes(lines, content_changes, title_by_code)
    _render_ficha_structural_changes(
        lines, by_type.get("ficha_added", []), by_type.get("ficha_removed", [])
    )
    _render_minor_content_changes(lines, content_changes, title_by_code)
    _render_caveats(lines, duplicate_warning, num_overrides)

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
        title_by_code = _title_by_code(input_path.name)
        report_md = render_report(result, title_by_code)

        out_path = OUTPUT_DIR / (input_path.stem + ".md")
        out_path.write_text(report_md)

        real_changes = sum(
            1
            for c in result["changes"]
            if c["change_type"] == "ficha_content_changed" and c["ai_category"] == "business_rule_change"
        )
        added = len([c for c in result["changes"] if c["change_type"] == "ficha_added"])
        removed = len([c for c in result["changes"] if c["change_type"] == "ficha_removed"])
        index_lines.append(
            f"- [{_fmt_date(result['edition_a'])} → {_fmt_date(result['edition_b'])}]"
            f"({out_path.name}) — {real_changes} cambios de negocio a revisar, "
            f"{added} altas, {removed} bajas"
        )
        print(f"{out_path.name}: {real_changes} cambios de negocio, {added} altas, {removed} bajas")

    (OUTPUT_DIR / "index.md").write_text("\n".join(index_lines) + "\n")


if __name__ == "__main__":
    main()
