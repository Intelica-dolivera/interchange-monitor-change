"""
Modulo 7 - Reporte de cambios para el manual base_ii_transactions_quick_reference.

Ultimo eslabon del pipeline: toma la salida ya "clasificada" del Modulo 5 (no-op para este
manual, ver docstring de `classify.py`) y genera un reporte en Markdown por cada par de
ediciones consecutivas. Modulo 6 sigue tentativo/sin definir, igual que en los otros 4
manuales.

**Diseno de reporte pedido explicitamente por el usuario (2026-08-19), distinto al de los
otros 4 manuales**: no hay `field_became_defined` (no aplica, ver Modulo 4) ni
`row_content_changed` (nunca ocurre, ver Modulo 3/5) que priorizar -en cambio, la vista
central es una tabla por TC mostrando cuantos TCR tenia antes, cuantos tiene ahora, el delta,
y el detalle de que filas se agregaron/quitaron especificamente. Discutido con el usuario:
un delta de TCR en cero NO significa "sin cambios" (puede ser 1 baja + 1 alta = un rename
que el diseno de Modulo 3 no puede confirmar como tal, ver docstring de `match.py`) -por eso
el reporte siempre lista el detalle de filas agregadas/quitadas debajo del conteo, nunca se
conforma con mostrar solo el numero.

**Fuente de los conteos "antes/despues" por TC**: Modulo 4/5 solo emiten EVENTOS de cambio
(`row_added`/`row_removed`), no el total de filas de una seccion que no cambio -no alcanza
para reconstruir "TC 33 tenia 17 TCR, ahora tiene 17" si nada cambio ahi. Este modulo relee
directo la salida ya validada del Modulo 3 (`data/03_emparejamiento_bloques/`) para esa
metadata de conteo -mismo patron ya establecido en los otros 4 manuales (Modulo 5 de esos
relee Modulo 3 para contexto -`_field_name_lookup`- que no esta en su propio input
inmediato), aplicado aca por la misma razon: no duplicar/inventar de nuevo un dato que una
etapa anterior ya calculo.

**Heuristica de "posible renombre" (agregada 2026-09-04, ver [[dev-phase-considerations]]
punto 3)**: como el Modulo 3 empareja filas por clave EXACTA (TCR+descripcion, ver su
docstring), un renombre real de TCR (misma fila, description distinta) siempre llega aca como
un `row_removed` + `row_added` sin relacion aparente entre si -nunca un `row_content_changed`
(no existe ese tipo de cambio para este manual). Ya habia una senal MUY cruda para esto (el
aviso "cantidad neta sin cambio, pero hay altas Y bajas" cuando `delta == 0`), pero esa senal
ni identifica CUALES filas podrian ser el mismo renombre ni dispara si el TC tambien tuvo
altas/bajas genuinas ademas del renombre (delta != 0 en ese caso, la vieja senal no disparaba
nunca). Fix, deliberadamente a nivel de REPORTE, no de matching (mismo principio ya aplicado
en el proyecto para no reintroducir el riesgo de falso positivo del fuzzy matching por
descripcion, ver docstring de `match.py` punto 2): dentro de cada TC, se agrupan
`rows_added`/`rows_removed` por su TCR (primera celda, normalizada) y, cuando el mismo TCR
aparece en AMBAS listas, se extrae ese par a una lista separada "posible renombre" (emparejado
por orden de aparicion si hay mas de 1 par con el mismo TCR, mismo criterio defensivo que
Modulo 3 usa para claves duplicadas) -se muestra el par junto, con ambas descripciones, en vez
de 2 bullets sueltos en Agregados/Eliminados. NUNCA se fusiona en el JSON ni se toca
Modulo 3/4/5 -es pura reagrupacion visual sobre datos que ya estaban ahi, el humano decide si
es un rename real o una coincidencia.

**Solo empareja cuando hay EXACTAMENTE 1 fila removida y 1 agregada con ese TCR en la
seccion -nunca por orden de aparicion cuando hay 2+ de cada lado.** Un primer intento
ingenuo que emparejaba por orden de aparicion (mismo criterio que Modulo 3 usa para claves
duplicadas) se probo real e INSEGURO antes de dejarlo asi: en el par `20250412_to_20260418`,
la seccion "05 Sales Draft" tiene 13 filas removidas y 13 agregadas compartiendo el TCR
generico `"TCR 2"` (uno por pais, ej. `"National Settlement, Uruguay"`, mencionado en
[[dev-phase-considerations]]) -la lista removida viene ordenada por nombre de pais y la
agregada por el nuevo prefijo de codigo (orden ALFABETICO DISTINTO), asi que emparejar por
posicion fabricaba parejas falsas (ej. `"National Settlement, Sweden"` emparejado con
`"(KR) National Settlement, South Korea"`, paises sin ninguna relacion real). Con la regla
estricta (1:1 inequivoco) esos 13 pares NO se muestran como hint -se quedan como 13 altas +
13 bajas honestas, igual que antes de este cambio- y el par completo termina con solo 2 hints
reales en todo el corpus (`"Promotion Data"` -> `"(PD) Promotion Data"`, 2 secciones
distintas, cada una con 1 sola fila removida y 1 sola agregada compartiendo `"TCR 4"`).
Perder los casos 2+:2+ (ej. un TCR con 2 filas ambiguas de cada lado) es el costo aceptado a
cambio de nunca mostrar una pareja fabricada -mismo principio de "preferir un remove+add
honesto antes que adivinar mal" ya aplicado en el proyecto (chain-shift del 3er manual,
fuzzy matching por descripcion en este mismo manual, ver Modulo 3).
"""

import json
import sys
from pathlib import Path

MANUAL_SLUG = "base_ii_transactions_quick_reference"
MANUAL_TITLE = "BASE II Transactions (Quick Reference)"
INPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "05_interpretacion_cambios_ia"
MATCH_DIR = Path(__file__).resolve().parents[1] / "data" / "03_emparejamiento_bloques"
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "07_reporte_cambios"


def _fmt_date(edition: str) -> str:
    return f"{edition[6:8]}/{edition[4:6]}/{edition[0:4]}"


def _row_line(cells: list) -> str:
    if len(cells) == 2:
        return f"`{cells[0]}` — {cells[1]}"
    return f"`{cells[0]}` — _(sin descripción)_"


def _tcr_label(cells: list) -> str:
    return cells[0].strip().casefold()


def _extract_rename_hints(added: list, removed: list) -> tuple:
    """Separa de added/removed los pares INEQUIVOCOS que comparten el mismo TCR (posible
    renombre, ver docstring del modulo) y devuelve (hints, added_restante, removed_restante).

    Solo empareja cuando hay EXACTAMENTE 1 fila removida y 1 agregada con ese TCR en la
    seccion -nunca por orden de aparicion cuando hay 2+ de cada lado. Confirmado con datos
    reales por que esto ultimo es inseguro: en TCs donde el mismo TCR se reusa para muchas
    filas distintas (ej. "TCR 2" = "National Settlement, <pais>" para 13 paises en "05 Sales
    Draft"), la lista removida viene ordenada por nombre de pais y la agregada por el nuevo
    prefijo de codigo -ordenes DISTINTOS- asi que emparejar por posicion producia parejas
    fabricadas y falsas (ej. "Sweden" emparejado con "(KR) South Korea"). Con 2+ candidatos
    de cada lado no hay forma segura de saber cual va con cual desde el TCR solo -se quedan
    como altas/bajas honestas sin agrupar, mismo principio de "preferir un remove+add honesto
    antes que adivinar mal" ya aplicado en el proyecto."""
    by_label_added = {}
    for cells in added:
        by_label_added.setdefault(_tcr_label(cells), []).append(cells)
    by_label_removed = {}
    for cells in removed:
        by_label_removed.setdefault(_tcr_label(cells), []).append(cells)

    hints = []
    paired_added_ids = set()
    paired_removed_ids = set()
    for label in sorted(set(by_label_added) & set(by_label_removed)):
        added_list = by_label_added[label]
        removed_list = by_label_removed[label]
        if len(added_list) != 1 or len(removed_list) != 1:
            continue
        cells_added, cells_removed = added_list[0], removed_list[0]
        hints.append({"cells_removed": cells_removed, "cells_added": cells_added})
        paired_added_ids.add(id(cells_added))
        paired_removed_ids.add(id(cells_removed))

    remaining_added = [c for c in added if id(c) not in paired_added_ids]
    remaining_removed = [c for c in removed if id(c) not in paired_removed_ids]
    return hints, remaining_added, remaining_removed


def render_report(result: dict, match_pair: dict) -> str:
    changes = result["changes"]
    by_type = {}
    for c in changes:
        by_type.setdefault(c["change_type"], []).append(c)

    row_added = by_type.get("row_added", [])
    row_removed = by_type.get("row_removed", [])
    section_added = by_type.get("section_added", [])
    section_removed = by_type.get("section_removed", [])
    section_renamed = by_type.get("section_renamed", [])
    duplicate_warnings = by_type.get("duplicate_key_warning", [])

    # Conteo antes/despues por TC, releido del Modulo 3 (ver docstring) -incluye TODAS las
    # secciones matched, no solo las que tuvieron cambios, para poder mostrar "sin cambios"
    # con la misma vista uniforme.
    row_counts_by_title = {}
    for section in match_pair.get("sections_matched", []):
        before = len(section["rows_matched"]) + len(section["rows_removed"])
        after = len(section["rows_matched"]) + len(section["rows_added"])
        row_counts_by_title[section["title_b"]] = {"before": before, "after": after}

    rows_added_by_title = {}
    for c in row_added:
        rows_added_by_title.setdefault(c["title"], []).append(c["cells"])
    rows_removed_by_title = {}
    for c in row_removed:
        rows_removed_by_title.setdefault(c["title"], []).append(c["cells"])

    # Extraer pares "posible renombre" (mismo TCR en added y removed del mismo TC) ANTES de
    # armar la vista por titulo -ver docstring del modulo. Purely a display-level regrouping,
    # no toca row_added/row_removed en el JSON ni los conteos del resumen de arriba.
    rename_hints_by_title = {}
    for title in set(rows_added_by_title) | set(rows_removed_by_title):
        hints, remaining_added, remaining_removed = _extract_rename_hints(
            rows_added_by_title.get(title, []), rows_removed_by_title.get(title, [])
        )
        if hints:
            rename_hints_by_title[title] = hints
        if remaining_added:
            rows_added_by_title[title] = remaining_added
        else:
            rows_added_by_title.pop(title, None)
        if remaining_removed:
            rows_removed_by_title[title] = remaining_removed
        else:
            rows_removed_by_title.pop(title, None)

    changed_titles = sorted(set(rows_added_by_title) | set(rows_removed_by_title) | set(rename_hints_by_title))

    lines = [
        f"# Reporte de cambios — {MANUAL_TITLE}",
        f"## Edición {_fmt_date(result['edition_a'])} → {_fmt_date(result['edition_b'])}",
        "",
        "## Resumen",
        "",
        f"- TC: {len(section_added)} agregados, {len(section_removed)} eliminados, "
        f"{len(section_renamed)} posiblemente renombrados",
        f"- TCR: {len(row_added)} agregados, {len(row_removed)} eliminados "
        f"(en {len(changed_titles)} TC afectados de {len(row_counts_by_title)} matcheados)",
    ]
    total_rename_hints = sum(len(h) for h in rename_hints_by_title.values())
    if total_rename_hints:
        lines.append(
            f"- Posibles renombres de TCR detectados: {total_rename_hints} (mismo TCR con baja "
            "y alta en el mismo TC — revisar, ver detalle abajo)"
        )
    lines.append("")

    lines.append(f"## TC agregados ({len(section_added)})")
    lines.append("")
    if section_added:
        for s in section_added:
            lines.append(f"- **{s['title']}** ({s['num_rows']} TCR)")
    else:
        lines.append("_Ninguno._")
    lines.append("")

    lines.append(f"## TC eliminados ({len(section_removed)})")
    lines.append("")
    if section_removed:
        for s in section_removed:
            lines.append(f"- **{s['title']}** ({s['num_rows']} TCR)")
    else:
        lines.append("_Ninguno._")
    lines.append("")

    if section_renamed:
        lines.append(f"## TC posiblemente renombrados ({len(section_renamed)})")
        lines.append("")
        for s in section_renamed:
            lines.append(f"- {s['title_a']} → {s['title_b']} (similitud {s['fuzzy_ratio']:.2f})")
        lines.append("")

    lines.append(f"## Detalle de TCR por TC afectado ({len(changed_titles)})")
    lines.append("")
    if not changed_titles:
        lines.append("_Ningún TC matcheado tuvo altas/bajas de TCR en este par de ediciones._")
        lines.append("")
    else:
        for title in changed_titles:
            counts = row_counts_by_title.get(title, {"before": "?", "after": "?"})
            delta = (
                counts["after"] - counts["before"]
                if isinstance(counts["before"], int) and isinstance(counts["after"], int)
                else None
            )
            delta_str = f"{delta:+d}" if delta is not None else "?"
            lines.append(f"### {title}")
            lines.append("")
            lines.append(f"TCR: {counts['before']} → {counts['after']} (delta {delta_str})")
            lines.append("")
            hints = rename_hints_by_title.get(title, [])
            added = rows_added_by_title.get(title, [])
            removed = rows_removed_by_title.get(title, [])
            if hints:
                lines.append(f"- ⚠️ Posibles renombres de TCR ({len(hints)}, revisar):")
                for hint in hints:
                    old_cells = hint["cells_removed"]
                    new_cells = hint["cells_added"]
                    tcr = old_cells[0]
                    old_desc = old_cells[1] if len(old_cells) > 1 else "_(sin descripción)_"
                    new_desc = new_cells[1] if len(new_cells) > 1 else "_(sin descripción)_"
                    lines.append(f"  - `{tcr}`: '{old_desc}' → '{new_desc}'")
            if added:
                lines.append(f"- Agregados ({len(added)}):")
                for cells in added:
                    lines.append(f"  - {_row_line(cells)}")
            if removed:
                lines.append(f"- Eliminados ({len(removed)}):")
                for cells in removed:
                    lines.append(f"  - {_row_line(cells)}")
            if delta == 0 and added and removed:
                lines.append(
                    "  - ⚠️ _Cantidad neta de TCR sin cambio, pero hay altas Y bajas sin TCR en "
                    "común — revisar a mano, no se pudo emparejar por TCR._"
                )
            lines.append("")

    if duplicate_warnings:
        lines.append("## Avisos de confiabilidad")
        lines.append("")
        for w in duplicate_warnings:
            lines.append(
                f"- El TC **{w['title']}** tiene claves TCR+descripción repetidas dentro de "
                f"la misma edición (`{w['duplicate_keys_a']}` en la edición vieja, "
                f"`{w['duplicate_keys_b']}` en la nueva) — el emparejamiento por clave en esos "
                "casos puntuales puede no ser 1:1 confiable."
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
        match_pair = json.loads((MATCH_DIR / input_path.name).read_text())
        report_md = render_report(result, match_pair)

        out_path = OUTPUT_DIR / (input_path.stem + ".md")
        out_path.write_text(report_md)

        by_type = {}
        for c in result["changes"]:
            by_type.setdefault(c["change_type"], []).append(c)
        tc_changes = len(by_type.get("section_added", [])) + len(by_type.get("section_removed", []))
        tcr_changes = len(by_type.get("row_added", [])) + len(by_type.get("row_removed", []))
        index_lines.append(
            f"- [{_fmt_date(result['edition_a'])} → {_fmt_date(result['edition_b'])}]"
            f"({out_path.name}) — {tc_changes} cambios de TC, {tcr_changes} cambios de TCR"
        )
        print(f"{out_path.name}: {tc_changes} cambios de TC, {tcr_changes} cambios de TCR")

    (OUTPUT_DIR / "index.md").write_text("\n".join(index_lines) + "\n")


if __name__ == "__main__":
    main()
