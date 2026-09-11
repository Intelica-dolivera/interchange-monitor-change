"""Landing: aterriza uno o mas grupos de PDFs del inbox, cada grupo perteneciente a un manual.
Cada PDF se identifica a que uno de los 8 manuales conocidos pertenece (ver detect_type.py) y
se agrupa por tipo detectado. Un grupo puede tener:
  - 2 PDFs (par completo, edicion vieja + edicion nueva, 2 fechas distintas) -- modo clasico.
  - 1 PDF (edicion nueva sola) -- modo "edicion unica": la edicion vieja se resuelve
    automaticamente contra la mas reciente YA presente en el corpus para ese manual (ver
    `_latest_corpus_edition`). Requiere que el corpus ya tenga al menos 1 edicion de ese
    manual (la primera carga de un manual nuevo siempre necesita el par completo) y que la
    fecha de la edicion nueva sea estrictamente posterior a la ya presente.
Si CADA grupo resultante es valido bajo alguno de esos 2 modos, se incorporan todos los PDFs
al corpus permanente (visa/src/.../<slug>/) y se corre el pipeline completo de cada manual
(reusando run.py), acotando la etapa de IA solo al par resultante de cada uno (--only, ver
CONTRACT.md).

**Todo o nada sobre el LOTE completo, no por grupo**: si CUALQUIER PDF del inbox no se puede
identificar, o CUALQUIER grupo no forma un par valido bajo ninguno de los 2 modos (tamano de
grupo distinto de 1 o 2, 2 PDFs con la misma fecha, 1 PDF sin edicion previa en el corpus, o 1
PDF no mas nuevo que la ya presente), o CUALQUIER edicion ya existe en el corpus con contenido
distinto -- no se procesa NI SE MUEVE nada de ningun grupo, ni siquiera los que si estaban bien
formados. Decision explicita del usuario (2026-09-06): mismo principio "todo o nada" que ya usa
el resto del proyecto (ver conflictos de hash mas abajo), preferido sobre procesar los grupos
validos y alertar solo los problematicos por consistencia con el resto del pipeline, a costa de
menos comodidad operacional si un solo PDF de un lote grande esta mal.

Uso:
    python3 poc/router/land.py [carpeta_inbox] [--manual SLUG] [--skip-ai]

`--manual SLUG` fuerza el mismo slug para TODOS los PDFs del inbox (salta la deteccion
automatica) -- pensado para el caso de 1 solo par cuando la deteccion automatica falla o es
ambigua. Con 3+ PDFs en el inbox, forzar un slug unico para todos hace que agrupen en un solo
grupo de 3+, que la validacion de "exactamente 2 por grupo" rechaza igual -- no hace falta
logica especial para este caso, el mismo camino de validacion ya lo cubre.
"""
import argparse
import hashlib
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

from detect_type import DetectionResult, detect_manual
from run import MANUALS, run_manual

ROUTER_DIR = Path(__file__).resolve().parent
POC_DIR = ROUTER_DIR.parent
REPO_ROOT = ROUTER_DIR.parents[1]
DEFAULT_INBOX = ROUTER_DIR / "landing" / "inbox"
ALERTS_DIR = ROUTER_DIR / "landing" / "alertas"

EDITION_DATE_RE = re.compile(r"^\d{8}$")


def _write_alert(reason_lines: list[str]) -> Path:
    ALERTS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = ALERTS_DIR / f"{ts}_rechazado.txt"
    path.write_text(f"[{datetime.now().isoformat()}]\n" + "\n".join(reason_lines) + "\n")
    return path


def _alert_and_exit(reason_lines: list[str]) -> int:
    print("\n".join(reason_lines), file=sys.stderr)
    alert_path = _write_alert(reason_lines)
    print(f"\nAlerta guardada en: {alert_path}", file=sys.stderr)
    return 1


def _edition_date(pdf_path: Path) -> str | None:
    prefix = pdf_path.stem.split(" - ", 1)[0]
    return prefix if EDITION_DATE_RE.match(prefix) else None


def _describe(pdf_path: Path, result: DetectionResult) -> str:
    if result.slug:
        return f"{pdf_path.name}: {result.slug} (via {result.method})"
    if not result.candidates:
        return f"{pdf_path.name}: no coincide con ninguno de los 8 manuales conocidos"
    return f"{pdf_path.name}: ambiguo entre {', '.join(result.candidates)}"


def _file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _corpus_dir(slug: str) -> Path:
    matches = sorted((REPO_ROOT / "visa" / "src").glob(f"*/{slug}"))
    if len(matches) != 1:
        raise RuntimeError(
            f"se esperaba exactamente 1 carpeta de corpus para {slug!r} bajo visa/src/*/, "
            f"se encontraron {len(matches)}: {matches}"
        )
    return matches[0]


def _latest_corpus_edition(corpus_dir: Path) -> str | None:
    """Fecha (YYYYMMDD) de la edicion mas reciente ya presente en el corpus de un manual, o
    None si el corpus todavia no tiene ninguna. Misma convencion de nombre que `_edition_date`
    (el corpus ya normaliza todo a `<fecha> - <MANUAL_TITLE>.pdf` al aterrizar, ver mas abajo)."""
    dates = [d for pdf in corpus_dir.glob("*.pdf") if (d := _edition_date(pdf)) is not None]
    return max(dates) if dates else None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "inbox", nargs="?", default=None,
        help="carpeta con uno o mas pares de PDFs (default: poc/router/landing/inbox)",
    )
    parser.add_argument(
        "--manual", default=None,
        help="fuerza el mismo slug para TODOS los PDFs del inbox, salta la deteccion automatica",
    )
    parser.add_argument("--skip-ai", action="store_true")
    args = parser.parse_args()

    if args.manual and args.manual not in MANUALS:
        print(f"manual desconocido: {args.manual!r} -- usa run.py --list", file=sys.stderr)
        return 2

    inbox = Path(args.inbox).resolve() if args.inbox else DEFAULT_INBOX
    inbox.mkdir(parents=True, exist_ok=True)

    pdfs = sorted(inbox.glob("*.pdf"))
    if not pdfs:
        return _alert_and_exit([f"No se encontraron PDFs en {inbox}."])

    dates: dict[Path, str] = {}
    bad_dates = [pdf for pdf in pdfs if _edition_date(pdf) is None]
    if bad_dates:
        return _alert_and_exit([
            "Los siguientes PDFs no cumplen la convencion 'YYYYMMDD - Titulo.pdf', no se pudo "
            "extraer la fecha de edicion -- no se procesa nada del lote:",
            *[f"  - {p.name}" for p in bad_dates],
        ])
    for pdf in pdfs:
        dates[pdf] = _edition_date(pdf)

    if args.manual:
        results = {pdf: DetectionResult(args.manual, "forzado (--manual)", [args.manual]) for pdf in pdfs}
    else:
        results = {pdf: detect_manual(pdf) for pdf in pdfs}

    unresolved = [pdf for pdf in pdfs if results[pdf].slug is None]
    if unresolved:
        return _alert_and_exit([
            "No se pudo identificar el tipo de manual de al menos 1 PDF -- no se procesa nada "
            "del lote:",
            *[f"  - {_describe(pdf, results[pdf])}" for pdf in pdfs],
        ])

    groups: dict[str, list[Path]] = {}
    for pdf in pdfs:
        groups.setdefault(results[pdf].slug, []).append(pdf)

    corpus_dirs = {slug: _corpus_dir(slug) for slug in groups}

    problems = []
    old_date_by_slug: dict[str, str] = {}  # solo para grupos de 1 PDF (modo edicion unica)
    for slug, group_pdfs in groups.items():
        if len(group_pdfs) == 2:
            d0, d1 = dates[group_pdfs[0]], dates[group_pdfs[1]]
            if d0 == d1:
                problems.append(
                    f"  - {slug} ({MANUALS[slug]}): ambos PDFs tienen la misma fecha de "
                    f"edicion ({d0}) -- se esperaba una edicion vieja y una nueva"
                )
            continue
        if len(group_pdfs) == 1:
            latest = _latest_corpus_edition(corpus_dirs[slug])
            new_date = dates[group_pdfs[0]]
            if latest is None:
                problems.append(
                    f"  - {slug} ({MANUALS[slug]}): 1 solo PDF y el corpus todavia no tiene "
                    "ninguna edicion previa de este manual -- la primera carga necesita el "
                    "par completo (2 PDFs)"
                )
            elif new_date <= latest:
                problems.append(
                    f"  - {slug} ({MANUALS[slug]}): la edicion {new_date} no es mas nueva que "
                    f"la ya presente en el corpus ({latest}) -- se esperaba una edicion "
                    "posterior"
                )
            else:
                old_date_by_slug[slug] = latest
            continue
        problems.append(
            f"  - {slug} ({MANUALS[slug]}): se esperaban 1 o 2 PDFs, se encontraron "
            f"{len(group_pdfs)} ({', '.join(p.name for p in group_pdfs)})"
        )
    if problems:
        return _alert_and_exit([
            "Al menos un grupo del lote no forma un par valido -- todo o nada, no se procesa "
            "NADA del lote (ni siquiera los grupos que si estaban bien):",
            *problems,
        ])

    print(f"Lote identificado: {len(groups)} grupo(s), {len(pdfs)} PDF(s) total.")
    for slug, group_pdfs in groups.items():
        print(f"  {slug} ({MANUALS[slug]}):")
        for pdf in group_pdfs:
            print(f"    {_describe(pdf, results[pdf])}")
        if slug in old_date_by_slug:
            print(
                f"    modo edicion unica: se compara contra la edicion "
                f"{old_date_by_slug[slug]} ya presente en el corpus"
            )

    targets: dict[Path, Path] = {}
    for slug, group_pdfs in groups.items():
        for pdf in group_pdfs:
            targets[pdf] = corpus_dirs[slug] / f"{dates[pdf]} - {MANUALS[slug]}.pdf"

    conflicts = [
        pdf for pdf in pdfs
        if targets[pdf].exists() and _file_hash(targets[pdf]) != _file_hash(pdf)
    ]
    if conflicts:
        return _alert_and_exit([
            "Al menos una edicion ya existe en el corpus con contenido DISTINTO al PDF "
            "aterrizado -- todo o nada, no se mueve NADA del lote:",
            *[f"  - {pdf.name} -> {targets[pdf].name}" for pdf in conflicts],
        ])

    print()
    for pdf in pdfs:
        target = targets[pdf]
        if target.exists():
            print(f"  {target.name} ya esta en el corpus (contenido identico), no se mueve.")
            continue
        shutil.move(str(pdf), str(target))
        print(f"  {pdf.name} -> {target}")

    pipeline_ok: dict[str, bool] = {}
    pair_dates: dict[str, tuple[str, str]] = {}
    for slug, group_pdfs in groups.items():
        if slug in old_date_by_slug:
            old_date, new_date = old_date_by_slug[slug], dates[group_pdfs[0]]
        else:
            old_pdf, new_pdf = sorted(group_pdfs, key=lambda p: dates[p])
            old_date, new_date = dates[old_pdf], dates[new_pdf]
        pair_dates[slug] = (old_date, new_date)
        only = f"{old_date}_to_{new_date}"
        print(f"\n=== Pipeline: {slug} ({MANUALS[slug]}) ===")
        pipeline_ok[slug] = run_manual(slug, None, None, args.skip_ai, only, None)

    print()
    any_fail = False
    for slug in groups:
        old_date, new_date = pair_dates[slug]
        slug_dir = POC_DIR / slug
        if not pipeline_ok[slug]:
            any_fail = True
            print(
                f"[{slug}] el pipeline termino con errores -- revisa la salida de arriba. "
                "Las ediciones ya quedaron incorporadas al corpus de todas formas.",
                file=sys.stderr,
            )
            continue

        pair_report = slug_dir / "data" / "07_reporte_cambios" / f"{old_date}_to_{new_date}.md"
        if pair_report.exists():
            print(f"[{slug}] reporte del par aterrizado: {pair_report}")
            continue

        editions_dir = slug_dir / "data" / "01_ingesta_parseo"
        reports_dir = slug_dir / "data" / "07_reporte_cambios"
        all_dates = sorted(p.stem for p in editions_dir.glob("*.json"))
        chain = [d for d in all_dates if old_date <= d <= new_date]
        print(
            f"[{slug}] no hay una comparacion directa {old_date}->{new_date}: ya habia "
            "edicion(es) intermedia(s) en el corpus. Cadena real de reportes generados:"
        )
        for a, b in zip(chain, chain[1:]):
            report = reports_dir / f"{a}_to_{b}.md"
            marker = "" if report.exists() else " (no encontrado)"
            print(f"  - {report}{marker}")

    return 1 if any_fail else 0


if __name__ == "__main__":
    sys.exit(main())
