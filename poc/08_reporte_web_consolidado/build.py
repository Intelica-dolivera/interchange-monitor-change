"""
Modulo 8 - Reporte web consolidado.

Lee el JSON mas reciente de Modulo 5 (05_interpretacion_cambios_ia) de cada uno de los 8
manuales, lo normaliza con un adaptador bespoke por manual (los 8 manuales NO comparten un
esquema real -confirmado investigando los 8 report.py de Modulo 7 antes de escribir esto,
ver adapters/), y arma una unica pagina HTML autocontenida (datos embebidos inline en base64,
sin fetch/servidor) con una pestana "Resumen general" + una pestana por manual mostrando el
detalle completo del ULTIMO par de ediciones.

Modulo 6 sigue tentativo/sin definir en los 8 manuales, igual que en el resto del pipeline;
este modulo consume Modulo 5 igual que cada Modulo 7 ya hace -es un consumidor hermano de
Modulo 7 (mismo input, output distinto), no algo que dependa de el.

Ademas de "Resumen general" + pestana por manual, la pagina trae una pestana "Cambios
recientes" que muestra solo el/los manual(es) cuyo par de ediciones (edition_a, edition_b)
cambio desde la ultima vez que se genero este reporte (cada corrida de build.py ES el evento
de "publicacion" - no hay un paso de publicar separado). El estado de la publicacion anterior
se persiste en data/estado_publicacion/<slug>.json, un archivo por manual (no uno solo
compartido) para poder resetear la "memoria" de un unico manual -por ejemplo para simular una
prueba end-to-end de una edicion nueva- sin afectar a los otros 7 (borrar solo su archivo).
Si no existe ninguno (primera corrida), todos los manuales cuentan como recientes. Compatible
con el formato viejo de un unico estado_publicacion.json (pre-migracion): si existe y todavia
no se corrio nunca con el formato nuevo, se usa como fallback para la primera comparacion y
despues se reemplaza por los archivos por manual.

Se corre sin argumentos: `python3 build.py`.
"""

import base64
import json
from datetime import datetime, timezone
from pathlib import Path

from adapters import (
    base_ii_clearing_data_codes,
    base_ii_clearing_edit_package_messages,
    base_ii_transactions_quick_reference,
    interchange_formats_grid,
    international_full_service_pos_online_messages_processing_specifications as pos_online,
    visanet_vss_volume_1,
    visanet_vss_volume_2,
)

POC_ROOT = Path(__file__).resolve().parents[1]
MODULE_DIR = Path(__file__).resolve().parent
OUT_DIR = MODULE_DIR / "data"
STATE_DIR = OUT_DIR / "estado_publicacion"
LEGACY_STATE_PATH = OUT_DIR / "estado_publicacion.json"  # formato viejo, pre-migracion a por-manual

# (slug de la carpeta en poc/, titulo para mostrar, funcion adaptadora)
MANUALS = [
    (
        "base_ii_clearing_data_codes",
        "BASE II Clearing Data Codes",
        base_ii_clearing_data_codes.summarize,
    ),
    (
        "base_ii_clearing_edit_package_messages",
        "BASE II Clearing Edit Package Messages",
        base_ii_clearing_edit_package_messages.summarize,
    ),
    (
        "base_ii_clearing_interchange_formats_tc_01_to_tc_49",
        "BASE II Clearing Interchange Formats, TC 01 to TC 49",
        lambda data, manual_dir, pair_name: interchange_formats_grid.summarize(
            data, manual_dir, pair_name, "BASE II Clearing Interchange Formats, TC 01 to TC 49"
        ),
    ),
    (
        "base_ii_clearing_interchange_formats_tc_50_to_tc_92",
        "BASE II Clearing Interchange Formats, TC 50 to TC 92",
        lambda data, manual_dir, pair_name: interchange_formats_grid.summarize(
            data, manual_dir, pair_name, "BASE II Clearing Interchange Formats, TC 50 to TC 92"
        ),
    ),
    (
        "base_ii_transactions_quick_reference",
        "BASE II Transactions (Quick Reference)",
        base_ii_transactions_quick_reference.summarize,
    ),
    (
        "international_full_service_pos_online_messages_processing_specifications",
        "Full Service POS Online Messages – Processing Specifications (International)",
        pos_online.summarize,
    ),
    (
        "visanet_settlement_service_vss_user_guide_volume_1_specifications",
        "VisaNet Settlement Service (VSS) User Guide, Volume 1, Specifications",
        visanet_vss_volume_1.summarize,
    ),
    (
        "visanet_settlement_service_vss_user_guide_volume_2_reports",
        "VisaNet Settlement Service (VSS) User Guide, Volume 2, Reports",
        visanet_vss_volume_2.summarize,
    ),
]


def _latest_pair_json(manual_dir: Path) -> Path:
    input_dir = manual_dir / "data" / "05_interpretacion_cambios_ia"
    paths = sorted(input_dir.glob("*.json"))
    if not paths:
        raise FileNotFoundError(f"No hay JSON de Modulo 5 en {input_dir}")
    return paths[-1]


def _load_previous_state() -> dict:
    """Estado de la ultima publicacion, un archivo por manual bajo estado_publicacion/<slug>.json
    -asi se puede resetear la "memoria" de un solo manual (ej. para probar el flujo de una
    edicion nueva de punta a punta) borrando solo su archivo, sin afectar a los otros 7.
    Si la carpeta todavia no existe pero si el archivo unico del formato viejo, lo usa como
    fallback (no fuerza a los 8 manuales a aparecer como "nuevos" de golpe tras la migracion)."""
    if STATE_DIR.exists():
        state = {}
        for slug, _, _ in MANUALS:
            path = STATE_DIR / f"{slug}.json"
            if path.exists():
                state[slug] = json.loads(path.read_text(encoding="utf-8"))
        return state
    if LEGACY_STATE_PATH.exists():
        return json.loads(LEGACY_STATE_PATH.read_text(encoding="utf-8"))
    return {}


def _write_state(manuals_out: list) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    for m in manuals_out:
        path = STATE_DIR / f"{m['slug']}.json"
        path.write_text(
            json.dumps(
                {"edition_a": m["edition_a"], "edition_b": m["edition_b"]},
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
    if LEGACY_STATE_PATH.exists():
        LEGACY_STATE_PATH.unlink()


def build(previous_state: dict | None = None) -> dict:
    previous_state = previous_state if previous_state is not None else {}
    manuals_out = []
    for slug, title, summarize_fn in MANUALS:
        manual_dir = POC_ROOT / slug
        pair_path = _latest_pair_json(manual_dir)
        data = json.loads(pair_path.read_text())

        summary = summarize_fn(data, manual_dir, pair_path.name)
        summary["slug"] = slug
        summary["title"] = title

        prev = previous_state.get(slug)
        summary["is_new_since_last_publish"] = (
            prev is None
            or prev.get("edition_a") != summary["edition_a"]
            or prev.get("edition_b") != summary["edition_b"]
        )

        manuals_out.append(summary)

        marker = " [NUEVO]" if summary["is_new_since_last_publish"] else ""
        print(
            f"{slug}: {summary['headline']['value']} "
            f"{summary['headline']['label'].lower()} ({pair_path.stem}){marker}"
        )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "manuals": manuals_out,
    }


def render_html(report: dict, template_path: Path) -> str:
    template = template_path.read_text(encoding="utf-8")
    data_json = json.dumps(report, ensure_ascii=False)
    data_b64 = base64.b64encode(data_json.encode("utf-8")).decode("ascii")
    return template.replace("__DATA_B64__", data_b64)


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    previous_state = _load_previous_state()
    report = build(previous_state)

    (OUT_DIR / "reporte_consolidado.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    html = render_html(report, MODULE_DIR / "template.html")
    out_html = OUT_DIR / "index.html"
    out_html.write_text(html, encoding="utf-8")

    _write_state(report["manuals"])

    n_new = sum(1 for m in report["manuals"] if m["is_new_since_last_publish"])
    print(f"\nListo: {out_html} ({n_new}/{len(report['manuals'])} manuales nuevos desde la ultima publicacion)")


if __name__ == "__main__":
    main()
