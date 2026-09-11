"""
Modulo 5 - Interpretacion de cambios (IA) para el manual base_ii_transactions_quick_reference.

**No-op deliberado, decidido con el usuario (2026-08-19) tras confirmar con datos reales que
no hace falta.** En los otros 4 manuales, este modulo clasifica con un LLM local los cambios
`row_content_changed`/`card_content_changed` -filas/fichas que MATCHEARON entre ediciones por
una clave estable (Position) pero cuyo texto libre cambio, donde hace falta criterio humano/IA
para distinguir cambio de negocio real vs. solo redaccion vs. ruido de extraccion.

Para ESTE manual esa categoria de cambio no existe nunca, por diseno (ver docstring de
`match.py`, Modulo 3): la clave de emparejamiento de filas (`TCR` + descripcion) consume TODO
el contenido mutable de la fila, asi que una fila matcheada es SIEMPRE identica en ambas
ediciones -si algo del texto cambio, la fila no matcheo, aparecio como baja+alta (`row_added`/
`row_removed`), ya resuelto de forma 100% determinista por Modulo 3/4. Confirmado corriendo el
Modulo 4 en los 7 pares disponibles: `row_content_changed` aparece 0 veces en las 8 ediciones.
No hay nada que un LLM podria clasificar aca -no es que el LLM no sirva, es que nunca llega
ningun caso a su bandeja de entrada.

Este archivo existe solo por consistencia de estructura del pipeline (mismos 7 modulos en las
5 carpetas de manuales, aunque Modulo 5 y 6 queden vacios/no aplicables en distintos casos -
Modulo 6 sigue tentativo/sin definir en los 5 manuales, y ahora Modulo 5 se suma como
"definido pero no aplicable" especificamente para este manual). Copia la salida del Modulo 4
sin tocarla, agregando un `ai_summary` vacio para que el Modulo 7 pueda seguir leyendo el mismo
esquema de entrada que en los otros manuales sin necesitar un branch especial.
"""

import json
import sys
from pathlib import Path

MANUAL_SLUG = "base_ii_transactions_quick_reference"
INPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "04_deteccion_cambios"
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "05_interpretacion_cambios_ia"


def classify_pair(match_result: dict) -> dict:
    num_content_changes = sum(1 for c in match_result["changes"] if c["change_type"] == "row_content_changed")
    if num_content_changes:
        # Nunca deberia pasar (ver docstring) -si pasa, es una senal de que el diseno de
        # Modulo 3 para este manual cambio y este no-op ya no es valido sin revisarlo.
        print(
            f"AVISO: se esperaba 0 row_content_changed para {MANUAL_SLUG}, se encontraron "
            f"{num_content_changes} -revisar si Modulo 5 sigue siendo un no-op valido.",
            file=sys.stderr,
        )

    result = dict(match_result)
    result["ai_summary"] = {}
    return result


def main():
    input_paths = sorted(INPUT_DIR.glob("*.json"))
    if not input_paths:
        print(f"No se encontraron cambios detectados en {INPUT_DIR}", file=sys.stderr)
        sys.exit(1)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for input_path in input_paths:
        match_result = json.loads(input_path.read_text())
        result = classify_pair(match_result)

        out_path = OUTPUT_DIR / input_path.name
        out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2))
        print(f"{input_path.name}: {len(result['changes'])} cambios (sin clasificacion IA, no aplica)")


if __name__ == "__main__":
    main()
