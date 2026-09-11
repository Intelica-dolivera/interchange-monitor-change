"""Router delgado que orquesta los 6 scripts de cada uno de los 8 pipelines del POC
(01_ingesta_parseo -> 02_normalizacion_bloques -> 03_emparejamiento_bloques ->
04_deteccion_cambios -> 05_interpretacion_cambios_ia -> 07_reporte_cambios; el Modulo 6
no existe en ningun manual, queda fuera de alcance).

No reemplaza ni modifica ningun script bespoke de cada manual -- solo los invoca en orden
como subprocesos, aprovechando que los 8 pipelines ya comparten un contrato de facto (ver
CONTRACT.md en este mismo directorio): cada script corre sin argumentos posicionales, resuelve
sus rutas de entrada/salida via Path(__file__), y usa exit code 0/no-cero para exito/falla.

Uso:
    python3 poc/router/run.py --list
    python3 poc/router/run.py <manual_slug> [--from NN] [--to NN] [--skip-ai]
                                             [--only PAR] [--limit N]
    python3 poc/router/run.py all [--skip-ai]
"""
import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
POC_DIR = REPO_ROOT / "poc"

# slug (nombre de carpeta bajo poc/) -> titulo legible (copiado de la constante MANUAL_TITLE
# de cada manual's 07_reporte_cambios/report.py -- se duplica aca a proposito, es solo texto
# para logging/resumen, no logica; el router no importa codigo de ningun modulo bespoke).
MANUALS = {
    "base_ii_clearing_data_codes": "BASE II Clearing Data Codes",
    "base_ii_clearing_edit_package_messages": "BASE II Clearing Edit Package Messages",
    "base_ii_clearing_interchange_formats_tc_01_to_tc_49":
        "BASE II Clearing Interchange Formats, TC 01 to TC 49",
    "base_ii_clearing_interchange_formats_tc_50_to_tc_92":
        "BASE II Clearing Interchange Formats, TC 50 to TC 92",
    "base_ii_transactions_quick_reference": "BASE II Transactions (Quick Reference)",
    "international_full_service_pos_online_messages_processing_specifications":
        "Full Service POS Online Messages – Processing Specifications (International)",
    "visanet_settlement_service_vss_user_guide_volume_1_specifications":
        "VisaNet Settlement Service (VSS) User Guide, Volume 1, Specifications",
    "visanet_settlement_service_vss_user_guide_volume_2_reports":
        "VisaNet Settlement Service (VSS) User Guide, Volume 2, Reports",
}

AI_STAGE_PREFIX = "05"


def discover_stages(slug: str) -> list[tuple[str, Path]]:
    """Etapas de un manual: carpetas 'NN_*' bajo poc/<slug>/, cada una con exactamente un
    *.py (aparte de __pycache__). No hardcodea nombres de script ni de carpeta -- confia en
    que el contrato (ver CONTRACT.md) se cumple, y falla ruidosamente si no."""
    manual_dir = POC_DIR / slug
    stage_dirs = sorted(
        p for p in manual_dir.glob("[0-9][0-9]_*") if p.is_dir()
    )
    stages = []
    for stage_dir in stage_dirs:
        scripts = [p for p in stage_dir.glob("*.py")]
        if len(scripts) != 1:
            raise RuntimeError(
                f"{stage_dir}: se esperaba exactamente 1 script .py, se encontraron "
                f"{len(scripts)} ({[p.name for p in scripts]}) -- viola el contrato del "
                f"router (ver CONTRACT.md)"
            )
        prefix = stage_dir.name.split("_", 1)[0]
        stages.append((prefix, scripts[0]))
    return stages


def run_manual(
    slug: str,
    from_stage: str | None,
    to_stage: str | None,
    skip_ai: bool,
    only: str | None,
    limit: str | None,
) -> bool:
    stages = discover_stages(slug)
    stages = [
        (prefix, script)
        for prefix, script in stages
        if (from_stage is None or prefix >= from_stage)
        and (to_stage is None or prefix <= to_stage)
    ]
    if skip_ai:
        stages = [(p, s) for p, s in stages if p != AI_STAGE_PREFIX]

    if not stages:
        print(f"[{slug}] ninguna etapa seleccionada (revisa --from/--to)", file=sys.stderr)
        return False

    print(f"\n=== {slug} ({MANUALS.get(slug, slug)}) ===", flush=True)
    for prefix, script in stages:
        extra_args = []
        if prefix == AI_STAGE_PREFIX:
            if only:
                extra_args.append(f"--only={only}")
            if limit:
                extra_args.append(f"--limit={limit}")

        print(f"--- [{slug}] etapa {prefix}: {script.parent.name}/{script.name} ---", flush=True)
        result = subprocess.run([sys.executable, str(script), *extra_args])
        if result.returncode != 0:
            print(
                f"[{slug}] etapa {prefix} ({script.name}) fallo con exit code "
                f"{result.returncode} -- se corta la cadena de este manual",
                file=sys.stderr,
                flush=True,
            )
            return False

    return True


def print_list() -> None:
    for slug, title in MANUALS.items():
        print(f"{slug}\n    {title}")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Router delgado para los 8 pipelines del POC (orquestacion, no reescribe "
        "ninguna etapa bespoke)."
    )
    parser.add_argument(
        "manual",
        nargs="?",
        help="slug de manual (ver --list) o 'all' para correr los 8 en orden",
    )
    parser.add_argument("--list", action="store_true", help="lista los manuales y sale")
    parser.add_argument("--from", dest="from_stage", metavar="NN", default=None)
    parser.add_argument("--to", dest="to_stage", metavar="NN", default=None)
    parser.add_argument(
        "--skip-ai",
        action="store_true",
        help="salta la etapa 05_interpretacion_cambios_ia (no requiere Ollama corriendo)",
    )
    parser.add_argument(
        "--only",
        metavar="PAR",
        default=None,
        help="passthrough a la etapa 05 unicamente (ej. 20250412_to_20251018)",
    )
    parser.add_argument(
        "--limit", metavar="N", default=None, help="passthrough a la etapa 05 unicamente"
    )
    return parser.parse_args(argv)


def main() -> int:
    args = parse_args(sys.argv[1:])

    if args.list:
        print_list()
        return 0

    if not args.manual:
        print("falta el manual (slug o 'all') -- usa --list para ver los slugs", file=sys.stderr)
        return 2

    if args.manual != "all" and args.manual not in MANUALS:
        print(f"manual desconocido: {args.manual!r} -- usa --list para ver los slugs", file=sys.stderr)
        return 2

    slugs = list(MANUALS) if args.manual == "all" else [args.manual]

    results = {}
    for slug in slugs:
        results[slug] = run_manual(
            slug,
            args.from_stage,
            args.to_stage,
            args.skip_ai,
            args.only,
            args.limit,
        )

    if len(slugs) > 1:
        print("\n=== resumen ===")
        for slug, ok in results.items():
            print(f"{'OK  ' if ok else 'FALLO'} {slug}")

    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
