"""
Modulo 2 - Normalizacion de bloques para el manual
visanet_settlement_service_vss_user_guide_volume_1_specifications.

Mismo diseno que el 6to manual (narrativo, sin grillas Position/Length/Format): 3 niveles de
encabezado (26.0/20.0/14.0pt, `section_heading` con `level`), parrafos reconstruidos por
adyacencia geometrica (`paragraph`), filtrado de ruido por contenido+adyacencia (header/pie/
TOC). El usuario confirmo (2026-08-19) reusar este enfoque -incluyendo las tablas "Field
Name/Description" y los restos de contenido de ejemplos de reporte- sin construir un parser
de tablas dedicado para este manual.

**Correccion real, encontrada DESPUES de la primera version de este modulo (2026-08-19,
antes de reportarlo como listo -ver memoria del asistente)**: la hipotesis inicial ("el
contenido rotado es un capitulo de ejemplos de reporte que solo existe en ediciones viejas,
2022-2023, y desaparece en 2025+") resulto ser PARCIALMENTE incorrecta. Es verdad que las
paginas COMPLETAS en orientacion paisaje desaparecen (0 en la edicion 20251017), pero el
contenido ROTADO en si (`dir=(0.0,-1.0)` en vez de `(1.0,0.0)` horizontal) sigue presente en
TODAS las ediciones -solo que empaquetado distinto: en 2022 como paginas paisaje completas,
en ediciones nuevas como bloques rotados DENTRO de paginas retrato normales (mismo contenido,
distinta maquetacion). Ademas, ese contenido rotado mezcla 2 cosas de valor MUY distinto:

1. **Pares `Field Name`/`Description`** (9.0-9.5pt Bold, ej. "Business mode (designates
   whether the report is for the issuer, acquirer, or other)." emparejado con su nombre de
   campo) -documentacion de referencia real, presente en ~30 paginas por edicion (ej. pag.
   112-148 en la edicion 20251017). El usuario decidio (2026-08-19, tras la correccion)
   reconstruir ESTOS pares -son contenido real, no descartable.
2. **Datos de reporte ficticios** (7.3pt, ej. "This Data is Fictitious and for Illustration
   Purposes Only.", columnas tipo mainframe con valores de relleno) -se descartan como ruido,
   igual que el criterio original (el propio texto declara que es relleno, no contenido real
   a rastrear).

**Reconstruccion de los pares rotados** (`_extract_rotated_pairs`, geometria investigada con
datos reales de 2 tablas distintas antes de escribir el codigo -confirmado el mismo patron en
ambas): para texto rotado, los ejes quedan efectivamente transpuestos respecto al texto
horizontal -lo que en una tabla sin rotar seria "misma fila, distinta columna" se ve aca como
"mismo `x0` (banda de fila), distinto rango `y1`" (banda de columna). Confirmado en 2 tablas:
la columna `Field Name` tiene un `y1` mas alto (fijo por pagina, ej. 717.0) que la columna
`Description` (fijo por pagina, ej. 574.5-576.3, VARIA levemente de tabla en tabla -no es una
constante global, se calcula por pagina). Espaciado entre filas consistente (~20.5pt de
`x0` a `x0` en ambas tablas revisadas) -confirma que agrupar por `x0` (banda, no valor
exacto) es el equivalente rotado del agrupamiento por banda Y ya usado para filas
horizontales en otros manuales. El titulo "Example N: Reconciliation of ... Report" que
encabeza cada tabla TAMBIEN esta rotado (12.0pt, distinto de los 3 niveles de encabezado
normales 26/20/14pt) -se captura por separado y se asocia a los pares de esa pagina como
contexto (`example_title`), reusado el mismo criterio de "titulo re-declarado por pagina" ya
visto en los manuales de grilla (Tipo A).

**Bug real encontrado y arreglado en la 1ra validacion (2026-08-19)**: las mismas bandas de
tamano de fuente (9.0/9.5pt rotado) tambien las usa OTRA tabla, totalmente distinta y SI
descartable -el listado de jerarquia de ejemplo del capitulo de reportes (ej. p.61,
encabezado literal `"Field"` / `"Settlement Reporting Entity (SRE) SRE Name"`, mapeando ID de
SRE a nombre de banco/procesador de ejemplo). Sin filtro adicional, esto contaminaba los
pares extraidos (220/484 con descripcion vacia en la 1ra corrida -mucho mas alto de lo
esperable). Fix: solo se procesan paginas que tengan el literal EXACTO de 2 palabras
`"Field Name"` entre los candidatos rotados -confirmado que la tabla de referencia real
siempre redeclara ese literal exacto en cada pagina en la que continua, mientras que la tabla
descartable usa `"Field"` solo (1 palabra) -senal limpia y confiable para separar ambas
estructuras que comparten geometria y tamano de fuente pero no son la misma tabla.

**2do bug real encontrado (2026-08-19), al empezar a explorar el output para disenar Modulo
3**: los pares quedaban ordenados al PRINCIPIO del documento entero (antes del 1er
`section_heading`) en vez de en su pagina real. Causa: el `order` de cada par se calculaba
buscando la 1ra linea HORIZONTAL de su misma pagina (`order_by_page`), pero las paginas
dentro de una tabla "Example N" no tienen NINGUNA linea horizontal (todo el contenido de esa
pagina es texto rotado) -la busqueda caia al default `0`, ordenando todos los pares de esas
paginas antes que absolutamente todo lo demas. Fix: cada par usa el `order` de su propia
linea (`name_line["order"]`, ya presente en todo output de Modulo 1) en vez de un proxy
basado en lineas horizontales que puede no existir en esa pagina.
"""

import json
import re
import sys
from pathlib import Path

MANUAL_SLUG = "visanet_settlement_service_vss_user_guide_volume_1_specifications"
INPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "01_ingesta_parseo"
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "02_normalizacion_bloques"

HEADER_LINE1 = "VisaNet Settlement Service (VSS) – User Guide, Volume 1, Specifications"
TOC_DOT_LEADER = re.compile(r"(\. ){4,}")
DATE_LINE = re.compile(r"^\d{1,2} [A-Za-z]+ 20\d{2}$")
PAGE_NUMBER_X_MIN = 500.0

HEADING_LEVELS = {26.0: 1, 20.0: 2, 14.0: 3}
HEADING_FONT_SIZES = set(HEADING_LEVELS)
MIN_CONTENT_FONT_SIZE = 9.0  # por debajo: ruido de vineta/diagrama/dato ficticio, ver docstring
HORIZONTAL_DIR = (1.0, 0.0)
ROTATED_DIR = (0.0, -1.0)

# Texto rotado a estos tamanos: pares Field Name/Description (9.0/9.5pt) y el titulo
# "Example N: ..." que encabeza cada tabla (12.0pt) -ver docstring del modulo. Cualquier otro
# texto rotado (tipicamente 7.3pt, datos de reporte ficticios) se descarta como ruido.
ROTATED_LABEL_FONT_SIZES = {9.0, 9.5}
ROTATED_TITLE_FONT_SIZE = 12.0

# Espaciado real entre filas de la tabla rotada (banda de `x0`), confirmado ~20.5pt en 2
# tablas distintas -tolerancia generosa para variacion real entre tablas/paginas.
ROTATED_ROW_BAND_TOLERANCE = 6.0
# Los 2 valores de `y1` (columna "Field Name" vs "Description") se calculan POR PAGINA, no
# como constante global -confirmado que varian levemente de tabla en tabla (717.0/574.5 en
# una, 717.0/576.3 en otra).
ROTATED_MIN_COLUMN_GAP = 30.0
# El titulo rotado trae un sufijo de posicion, ej. "... (2 of 3)" -se separa para que la
# identidad de la tabla ("Example N: Reconciliation of X to Y") quede estable entre sus
# paginas de continuacion, confirmado real (el sufijo cambia por pagina, el resto no).
ROTATED_TITLE_PAGE_SUFFIX = re.compile(r"\s*\(\d+ of \d+\)\s*$")

# Umbral para distinguir un wrap de descripcion (misma descripcion, envuelve a una 2da
# sub-banda de `x0`) de una fila nueva real -resolviendo [[pending-bug-fixes]] item 14
# (2026-08-26). Calibrado con un escaneo del corpus completo (6 ediciones, todas las tablas
# con el literal "Field Name"): el gap real entre 2 lineas de descripcion consecutivas
# (ordenadas por `x0`) que son el MISMO wrap es SIEMPRE exactamente 12.0pt (87 instancias,
# 0 variacion) -confirmado leyendo el texto real, cada caso completa una oracion truncada
# (ej. "...Total Cardholder Billing Amount on the" + "SMS600C report."). El gap minimo real
# entre 2 filas DISTINTAS (medido entre nombres consecutivos, senal independiente) es 17.0pt
# -limite limpio, SIN superposicion (0 gaps en el rango [12.0, 17.0)). Umbral puesto a mitad
# de camino. Antes de este fix, un wrap quedaba huerfano (sin nombre a menos de
# `ROTATED_ROW_BAND_TOLERANCE`) o, peor, se lo robaba el nombre INCORRECTO mas cercano que
# por casualidad geometrica cayera dentro de esa tolerancia (ver docstring del modulo,
# ejemplo real "SMS600C report." robado por "[CLEARING AMOUNT]" en vez de completar la
# descripcion real de "CLEARING AMOUNT").
DESC_WRAP_GAP_MAX = 15.0

PARAGRAPH_MAX_GAP = 10.0
PARAGRAPH_MAX_X_SHIFT = 20.0


def _filter_noise(lines_by_page: dict) -> tuple:
    """Filtra header/pie/TOC por contenido+adyacencia. Devuelve (lineas_horizontales_limpias,
    lineas_rotadas_candidatas) -separadas porque requieren mecanismos de reconstruccion
    totalmente distintos (ver docstring del modulo)."""
    clean = []
    rotated = []
    for page in sorted(lines_by_page):
        page_lines = sorted(lines_by_page[page], key=lambda l: (l["bbox"][1], l["bbox"][0]))
        noise_idx = set()

        for i, line in enumerate(page_lines):
            text = line["text"].strip()
            x0, y0 = line["bbox"][0], line["bbox"][1]
            is_rotated = tuple(line.get("dir", HORIZONTAL_DIR)) == ROTATED_DIR
            if is_rotated:
                noise_idx.add(i)
                size = line["max_font_size"]
                if size in ROTATED_LABEL_FONT_SIZES or size == ROTATED_TITLE_FONT_SIZE:
                    rotated.append(line)
            elif text == HEADER_LINE1:
                noise_idx.add(i)
                if i + 1 < len(page_lines) and page_lines[i + 1]["bbox"][3] < 50:
                    noise_idx.add(i + 1)
            elif text == "Visa Confidential" or DATE_LINE.match(text):
                noise_idx.add(i)
            elif TOC_DOT_LEADER.search(text):
                noise_idx.add(i)
            elif y0 > 700 and x0 >= PAGE_NUMBER_X_MIN and re.match(r"^\d{1,4}$", text):
                noise_idx.add(i)
            elif line["max_font_size"] < MIN_CONTENT_FONT_SIZE:
                noise_idx.add(i)

        clean.extend(page_lines[i] for i in range(len(page_lines)) if i not in noise_idx)
    return clean, rotated


def _band_cluster(values: list, tolerance: float) -> list:
    """Agrupa valores numericos en bandas -mismo principio que el agrupamiento por banda Y
    de filas horizontales en otros manuales, aca aplicado al eje que corresponda (x0 para
    bandas de fila, y1 para bandas de columna del texto rotado)."""
    clusters = []
    for v in sorted(values):
        if clusters and (v - clusters[-1][-1]) <= tolerance:
            clusters[-1].append(v)
        else:
            clusters.append([v])
    return clusters


def _merge_wrapped_descriptions(descs: list) -> list:
    """Fusiona lineas de descripcion consecutivas (ya ordenadas por `x0`) que son
    continuacion de WRAP de la misma descripcion (gap al fragmento anterior <
    `DESC_WRAP_GAP_MAX`, ver constante) en una sola entrada -conserva el `x0` del PRIMER
    fragmento (el que ya matchea bien con su nombre real hoy) para no tocar el mecanismo de
    emparejamiento nombre<->descripcion, solo completar el texto truncado."""
    if not descs:
        return []
    merged = [dict(descs[0])]
    texts = [descs[0]["text"]]
    prev = descs[0]
    for line in descs[1:]:
        if (line["bbox"][0] - prev["bbox"][0]) < DESC_WRAP_GAP_MAX:
            texts[-1] = f"{texts[-1]} {line['text']}"
            merged[-1]["text"] = texts[-1]
        else:
            merged.append(dict(line))
            texts.append(line["text"])
        prev = line
    return merged


def _extract_rotated_pairs(rotated_lines: list) -> list:
    """Reconstruye pares Field Name/Description desde texto rotado, pagina por pagina (la
    tabla re-declara su propio titulo y encabezados en cada pagina en la que continua, mismo
    patron ya visto en los manuales de grilla Tipo A -ver docstring del modulo)."""
    by_page = {}
    for line in rotated_lines:
        by_page.setdefault(line["page"], []).append(line)

    pairs = []
    last_title = ""
    for page in sorted(by_page):
        page_lines = by_page[page]
        titles = [l for l in page_lines if l["max_font_size"] == ROTATED_TITLE_FONT_SIZE]
        if titles:
            raw_title = " ".join(t["text"] for t in titles)
            example_title = ROTATED_TITLE_PAGE_SUFFIX.sub("", raw_title)
            last_title = example_title
        else:
            # El titulo se redeclara en casi todas las paginas (con sufijo "(N of M)",
            # confirmado real) pero puede faltar en algun hueco puntual (ej. una pagina
            # intermedia sin ninguna fila Field Name/Description real) -se hereda el ultimo
            # visto en vez de dejarlo vacio, salvaguarda barata.
            example_title = last_title

        labels = [l for l in page_lines if l["max_font_size"] in ROTATED_LABEL_FONT_SIZES]
        if not labels:
            continue
        # Filtro real, encontrado validando este modulo (2026-08-19): estas mismas 2 bandas
        # de tamano (9.0/9.5pt) tambien las usa OTRA tabla rotada totalmente distinta -el
        # listado de jerarquia de ejemplo del capitulo de reportes descartable (ej. p.61,
        # encabezado literal "Field" / "Settlement Reporting Entity (SRE) SRE Name",
        # mapeando ID de SRE a nombre de banco/procesador -contenido de ejemplo, no
        # documentacion de referencia). Se distingue por el encabezado exacto: la tabla de
        # referencia real SIEMPRE redeclara el literal de 2 palabras "Field Name" en cada
        # pagina en la que continua (confirmado real en 3 paginas consecutivas) -si no esta
        # presente, se descarta la pagina entera en vez de arriesgar mezclar 2 estructuras
        # distintas bajo la misma banda geometrica.
        if not any(l["text"].strip() == "Field Name" for l in labels):
            continue

        # Banda de columna: agrupa por `y1` (confirmado 2 bandas reales por pagina -"Field
        # Name" con `y1` mas alto, "Description" con `y1` mas bajo- pero se calcula por
        # pagina, no con una constante global, ver docstring).
        y1_clusters = _band_cluster([l["bbox"][3] for l in labels], ROTATED_ROW_BAND_TOLERANCE)
        # Colapsa clusters muy cercanos (jitter) y descarta el caso degenerado de una sola
        # columna (no hay pares que reconstruir, se ignora la pagina).
        col_bands = [c for c in y1_clusters if True]
        if len(col_bands) < 2:
            continue
        col_bands.sort(key=lambda c: -c[-1])  # banda "Field Name" (y1 mas alto) primero
        name_band = (min(col_bands[0]), max(col_bands[0]))
        desc_band = (min(col_bands[-1]), max(col_bands[-1]))
        if desc_band[1] + ROTATED_MIN_COLUMN_GAP > name_band[0]:
            # Las 2 bandas quedaron demasiado cerca -no hay separacion de columna real,
            # descarta la pagina en vez de arriesgar un emparejamiento erroneo.
            continue

        def in_band(y1, band):
            return band[0] - ROTATED_ROW_BAND_TOLERANCE <= y1 <= band[1] + ROTATED_ROW_BAND_TOLERANCE

        names = sorted((l for l in labels if in_band(l["bbox"][3], name_band)), key=lambda l: l["bbox"][0])
        descs = sorted((l for l in labels if in_band(l["bbox"][3], desc_band)), key=lambda l: l["bbox"][0])

        # Filtra el propio header de columna ("Field Name"/"Description" literal) -es texto
        # de encabezado, no un par de datos real.
        names = [l for l in names if l["text"].strip() != "Field Name"]
        descs = [l for l in descs if l["text"].strip() != "Description"]
        descs = _merge_wrapped_descriptions(descs)

        used_desc = set()
        for name_line in names:
            x0 = name_line["bbox"][0]
            best_idx, best_dist = None, None
            for idx, desc_line in enumerate(descs):
                if idx in used_desc:
                    continue
                dist = abs(desc_line["bbox"][0] - x0)
                if dist <= ROTATED_ROW_BAND_TOLERANCE and (best_dist is None or dist < best_dist):
                    best_idx, best_dist = idx, dist
            description = ""
            if best_idx is not None:
                used_desc.add(best_idx)
                description = descs[best_idx]["text"]
            pairs.append(
                {
                    "type": "field_description_pair",
                    "page": page,
                    "order": name_line["order"],
                    "example_title": example_title,
                    "name": name_line["text"],
                    "description": description,
                }
            )
    return pairs


def build_blocks(lines: list) -> list:
    blocks = []
    active_heading = None
    active_paragraph = None

    def flush_heading():
        nonlocal active_heading
        if active_heading:
            blocks.append(
                {
                    "order": active_heading["order"],
                    "type": "section_heading",
                    "page": active_heading["page"],
                    "level": HEADING_LEVELS[active_heading["size"]],
                    "text": active_heading["text"],
                }
            )
        active_heading = None

    def flush_paragraph():
        nonlocal active_paragraph
        if active_paragraph:
            blocks.append(
                {
                    "order": active_paragraph["order"],
                    "type": "paragraph",
                    "page": active_paragraph["page"],
                    "text": " ".join(active_paragraph["text"]).strip(),
                }
            )
        active_paragraph = None

    for line in lines:
        text = line["text"].strip()
        page = line["page"]
        size = line["max_font_size"]
        x0, y0, y1 = line["bbox"][0], line["bbox"][1], line["bbox"][3]

        if size in HEADING_FONT_SIZES:
            if active_heading is not None and size == active_heading["size"] and page == active_heading["page"]:
                active_heading["text"] += " " + text
                continue
            flush_heading()
            flush_paragraph()
            active_heading = {"page": page, "size": size, "text": text, "order": line["order"]}
            continue

        if active_heading is not None:
            flush_heading()

        if (
            active_paragraph is not None
            and page == active_paragraph["page"]
            and abs(x0 - active_paragraph["x0"]) <= PARAGRAPH_MAX_X_SHIFT
            and (y0 - active_paragraph["last_y1"]) <= PARAGRAPH_MAX_GAP
        ):
            active_paragraph["text"].append(text)
            active_paragraph["last_y1"] = y1
        else:
            flush_paragraph()
            active_paragraph = {"page": page, "x0": x0, "last_y1": y1, "text": [text], "order": line["order"]}

    flush_heading()
    flush_paragraph()
    return blocks


def normalize_edition(edition_json_path: Path) -> dict:
    data = json.loads(edition_json_path.read_text())
    lines_by_page = {}
    for line in data["lines"]:
        lines_by_page.setdefault(line["page"], []).append(line)

    clean_lines, rotated_lines = _filter_noise(lines_by_page)
    blocks = build_blocks(clean_lines)

    pairs = _extract_rotated_pairs(rotated_lines)

    blocks.extend(pairs)
    blocks.sort(key=lambda b: b["order"])
    for b in blocks:
        del b["order"]

    return {
        "manual": data["manual"],
        "edition_date": data["edition_date"],
        "source_file": data["source_file"],
        "num_lines_in": data["num_lines"],
        "num_lines_kept": len(clean_lines) + len(rotated_lines),
        "num_blocks": len(blocks),
        "blocks": blocks,
    }


def main():
    input_paths = sorted(INPUT_DIR.glob("*.json"))
    if not input_paths:
        print(f"No se encontraron JSON de entrada en {INPUT_DIR}", file=sys.stderr)
        sys.exit(1)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for input_path in input_paths:
        result = normalize_edition(input_path)
        out_path = OUTPUT_DIR / input_path.name
        out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2))
        print(
            f"{input_path.name}: {result['num_lines_in']} lineas -> "
            f"{result['num_lines_kept']} utiles -> {result['num_blocks']} bloques"
        )


if __name__ == "__main__":
    main()
