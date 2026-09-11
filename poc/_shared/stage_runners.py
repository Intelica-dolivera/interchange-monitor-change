"""Cuerpo compartido de main() para las etapas 01 (ingesta/parseo) y 04 (deteccion de cambios),
extraido tras confirmar que es byte-identico en 7 de los 8 manuales (todos menos
visanet_settlement_service_vss_user_guide_volume_2_reports, que tiene su propio schema de
resultado por apendice y sigue con su main() bespoke).

No reemplaza la logica de extraccion/deteccion de cada manual (extract_pdf_lines,
detect_changes siguen siendo bespoke) -- solo el loop de "leer entradas, escribir un .json de
salida por entrada, imprimir una linea de progreso" que rodea a esa logica.
"""
import json
import sys
from pathlib import Path
from typing import Callable, Optional


def run_ingest_main(
    source_dir: Path,
    output_dir: Path,
    extract_pdf_lines: Callable[[Path], dict],
    describe: Optional[Callable[[Path, Path, dict], str]] = None,
) -> None:
    pdf_paths = sorted(source_dir.glob("*.pdf"))
    if not pdf_paths:
        print(f"No se encontraron PDFs en {source_dir}", file=sys.stderr)
        sys.exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)
    for pdf_path in pdf_paths:
        result = extract_pdf_lines(pdf_path)
        out_path = output_dir / f"{result['edition_date']}.json"
        out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2))
        if describe:
            print(describe(pdf_path, out_path, result))
        else:
            print(
                f"{pdf_path.name} -> {out_path.name} "
                f"({result['num_pages']} paginas, {result['num_lines']} lineas)"
            )


def run_detect_main(
    input_dir: Path,
    output_dir: Path,
    detect_changes: Callable[[dict], dict],
    describe: Optional[Callable[[Path, Path, dict], str]] = None,
    empty_msg: Optional[str] = None,
) -> None:
    input_paths = sorted(input_dir.glob("*.json"))
    if not input_paths:
        print(
            empty_msg or f"No se encontraron pares emparejados en {input_dir}",
            file=sys.stderr,
        )
        sys.exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)
    for input_path in input_paths:
        match_result = json.loads(input_path.read_text())
        result = detect_changes(match_result)

        out_path = output_dir / input_path.name
        out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2))

        if describe:
            print(describe(input_path, out_path, result))
        else:
            summary_str = ", ".join(f"{k}={v}" for k, v in sorted(result["summary"].items()))
            print(f"{input_path.name}: {len(result['changes'])} cambios ({summary_str})")
