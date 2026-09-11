"""
Modulo 2 - Normalizacion de bloques para el manual
visanet_settlement_service_vss_user_guide_volume_2_reports.

Por decision explicita del usuario (2026-08-19), este modulo cubre los 5 apendices en un
solo paso grande (a diferencia del enfoque incremental usado en otros manuales). Exploracion
previa a escribir este modulo (bbox/font reales de al menos 1 pagina por apendice, ver
conversacion) encontro un patron tipografico SORPRENDENTEMENTE CONSISTENTE entre los 5
apendices pese a tener distinta cantidad de columnas y (en A/D) estar rotados:

- Titulo de pagina/seccion: 26.0pt Bold (Apendices C/E) o 20.0pt Bold (Apendice B) -> `section_heading`.
- Titulo de tabla especifico: 10.5pt Bold (ej. "Business Transaction Types", "TC 46, TCR 0
  (Report Subgroup 1) Client Settlement Data Record Layout") -> contexto de la tabla, NO su
  propio bloque.
- Encabezados de columna de la tabla: 9.5pt Bold, SIEMPRE en plural (2 a 6 por tabla).
- Contenido de fila: 9.0pt Regular.

Esto permitio construir UN SOLO reconstructor generico de tabla N-columnas
(`_build_table_rows`) reusado para los 5 apendices, en vez de un parser bespoke por apendice:
las bandas de columna (posicion X para tablas horizontales, banda Y1 para tablas rotadas -ver
mas abajo) se calculan dinamicamente leyendo la propia fila de encabezado de cada pagina/tabla
(igual principio ya usado en otros manuales: "el header se re-declara en cada pagina, no
asumir constantes globales"), y la columna "ancla" (la que dispara una fila nueva) es la de
menor X0 (horizontal) o mayor Y1 (rotado, orden de lectura).

**Apendices A y D estan ROTADOS A NIVEL DE PAGINA** (`page.rotation == 90`, un `/Rotate 90`
real del PDF -no lineas de texto rotadas individualmente dentro de paginas normales, como
paso en el Volume 1). PyMuPDF aplica esa rotacion en `page.get_text()` pero NO en los bbox de
`page.get_text("dict")` -Modulo 1 ya capturo esto (`page_rotation` + `dir` por linea). Para
texto rotado los ejes quedan transpuestos, igual que en el Volume 1: "misma fila" = mismo X0,
"misma columna" = misma banda Y1 -misma logica de `_extract_rotated_pairs` del Volume 1,
generalizada aqui a N columnas en vez de solo 2 (Field Name/Description).

**Contenido descartable en A/D**: capturas de reportes de mainframe de ejemplo (ej. "REPORT
ID: VSS-111 ... *** END OF VSS-111 REPORT ***", literalmente marcado "This Data is
Fictitious..."). Se identifican con una sola senal inequivoca y estable en TODA la
exploracion: fuente `CourierNewPSMT` (monoespaciada) -nunca usada para contenido real, sin
importar el tamano de fuente (que SI varia, 7.3pt o 10.5pt segun el reporte -Volume 1 uso
tamano de fuente para esto, pero aca el tamano no es estable, la fuente si).

Front matter (portada + indice, antes del Apendice A) se descarta enteramente -mismo
criterio que el TOC descartado en los otros 8 manuales.
"""

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

MANUAL_SLUG = "visanet_settlement_service_vss_user_guide_volume_2_reports"
INPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "01_ingesta_parseo"
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "02_normalizacion_bloques"

HORIZONTAL_DIR = (1.0, 0.0)
ROTATED_DIR = (0.0, -1.0)

# Encabezado/pie de pagina: estable independientemente de si la pagina esta rotada o no (el
# texto de "chrome" -titulo del documento, fecha, "Visa Confidential", numero de pagina- nunca
# esta rotado, ver docstring). Confirmado en Apendices A/B/C/D/E.
HEADER_Y1_MAX = 44.0
FOOTER_Y0_MIN = 755.0

DISPOSABLE_FONT = "CourierNewPSMT"

HEADING_FONT_SIZES = {26.0: 1, 20.0: 2}
TABLE_TITLE_FONT_SIZE = 10.5
HEADER_FONT_SIZE = 9.5
DATA_FONT_SIZE = 9.0

# Rotado: los mismos 4 niveles tipograficos existen, a otros tamanos (encabezados de
# seccion/subseccion 14.0/12.0pt en vez de 26.0/20.0pt -ver pagina "SMS608 Report Layout"/
# "Fee Collection and Funds Disbursement Detail (SMS608C)").
ROTATED_HEADING_FONT_SIZES = {14.0: 1, 12.0: 2}
ROTATED_TABLE_TITLE_FONT_SIZE = 10.5
ROTATED_HEADER_FONT_SIZE = 9.5
ROTATED_DATA_FONT_SIZE = 9.0

# Tolerancia de "salto de linea dentro de la misma celda" (envoltura) vs "fila nueva" en
# tablas HORIZONTALES, calibrada con datos reales de Apendice B/E: envoltura ~0pt de
# separacion entre el fin de una linea y el inicio de la siguiente en la MISMA columna ancla;
# fila nueva real, >=7.5pt. Valor conservador por debajo del minimo real observado.
ANCHOR_WRAP_GAP_MAX = 3.0
# Misma idea para tablas ROTADAS (Apendice A/D) -eje distinto (X en vez de Y), calibrada por
# separado con datos reales de las tablas V22200/SMS608: envoltura real de un Field Name a 2
# lineas, ~-1 a 0pt (lineas se tocan); fila nueva real, minimo observado 7.5pt (con casos
# hasta 24.5pt). Un solo umbral global (antes derivado como ANCHOR_WRAP_GAP_MAX*4=12.0) era
# MAYOR que el gap real minimo entre filas (7.5pt) -fusionaba filas reales distintas en una
# sola, bug real encontrado en validacion (Apendice D pagina 366, V22200: 9 campos separados
# colapsando en 3 bloques).
#
# **Recalibrado (2026-08-26), resolviendo [[pending-bug-fixes]] item 16.** El valor original
# (4.0) se habia calibrado contra solo 2 tablas -mismo "no confiar en un umbral calibrado con
# 1-2 tablas" ya pagado varias veces en este proyecto. Un escaneo de TODOS los gaps reales
# entre lineas consecutivas de la columna ancla, en las 7 ediciones y los 2 apendices rotados
# (7200 gaps totales, reusando la logica real de zonas/columnas de este modulo, no una
# aproximacion), encontro un SEGUNDO modo de envoltura legitima invisible en la calibracion
# original: cuando un valor de la columna ancla envuelve a 3+ lineas (ej. "VSS-116 - SRE
# Settlement" + "Recap Report" + "(Fee by Jurisdiction)", el mismo campo, 3 fragmentos), el
# gap entre el 2do y 3er fragmento puede ser bastante mayor que el gap ~0pt tipico entre el
# 1ro y el 2do (confirmado real: 4.1-6.6pt, 674 instancias en el corpus) -por encima del
# umbral original de 4.0, disparando una fila nueva espuria que separaba el fragmento final
# del resto de su propio valor (sintoma original del item 16: "(Fee by Jurisdiction)" quedaba
# como su propia fila, con las demas columnas vacias). Confirmado un limite limpio y SIN
# superposicion en todo el corpus: maximo gap de envoltura real 6.6pt, minimo gap de fila
# nueva real 7.0pt (redondeado a 0.1pt) -umbral recalibrado a mitad de camino.
ROTATED_ANCHOR_WRAP_GAP_MAX = 6.8

# Tolerancia para agrupar las 2 lineas de UN MISMO encabezado envuelto (ej. "Transaction" +
# "Description") en la misma fila tipografica de encabezado. Calibrada con datos reales del
# Apendice E: separacion real entre las 2 lineas de un encabezado envuelto ~12pt, separacion
# real entre 2 NIVELES de encabezado distintos (grupo vs hoja) ~20.5pt -umbral a mitad de
# camino para no fusionar ambos casos.
HEADER_ROW_WRAP_TOLERANCE = 15.0

# Umbral para distinguir un encabezado "hoja" (tiene su propia columna de datos) de un
# encabezado "grupo" (una etiqueta que abarca 2+ encabezados hoja debajo, ej. "Business Mode"
# sobre "Outgoing"/"Incoming" en el Apendice E, o "VSS Business Transaction Code" sobre "Fee
# Collection"/"Funds Disbursement" en el Apendice C) -si el encabezado candidato tiene otro
# encabezado candidato a menos de este umbral en el eje perpendicular, se asume que es un
# grupo y se descarta (sus hijos ya cubren esa columna). Bug real encontrado en validacion: el
# valor original (30.0, calibrado solo contra el Apendice E) era MENOR que un caso real de
# grupo-a-hoja en el Apendice C (48.4pt, "VSS Business Transaction Code"), asi que ese
# encabezado grupo escapaba el filtro y quedaba como columna espuria que robaba datos de la
# columna vecina real ("Fee Collection"). Recalibrado con evidencia de ambos apendices:
# grupo-a-hoja real observado 10.8-48.4pt, hoja-a-hoja real observado >=90.8pt -umbral a
# mitad de camino entre ambos rangos.
GROUP_HEADER_MIN_GAP = 65.0

DATE_LINE = re.compile(r"^\d{1,2} [A-Za-z]+ 20\d{2}$")

# Bug real encontrado en validacion (2026-08-20, ver [[manual8-vss-vol2-progress]]): el PDF
# fuente codifica el espacio entre palabras de ALGUNOS encabezados de columna/titulos de tabla
# como NBSP (U+00A0) en vez de espacio normal (U+0020) -inconsistente incluso DENTRO de una
# misma edicion/tabla (confirmado: mezcla de filas limpias y con NBSP en la misma pagina). El
# texto de contenido (valores de fila) ya se compara con `\s+` (que matchea NBSP) en Modulo
# 3/4, asi que ahi no rompe nada -pero el NOMBRE de columna/titulo se usa tal cual como CLAVE
# de diccionario (`{nombre: posicion}` en este modulo, luego iterado directo por nombre en
# `Modulo4/detect.py`'s `_diff_row`, que NO normaliza las claves antes de comparar). Cuando la
# misma columna se extrae con NBSP en una edicion y con espacio normal en la otra, Modulo 4 las
# trata como 2 columnas DISTINTAS: reporta que el contenido "desaparecio" de una y "aparecio"
# en la otra -el primer caso lo atrapa el safety net de Modulo 5 (categoria final correcta,
# extraction_noise, pero por la razon equivocada), el segundo NO (no hay "disappeared_content"
# que perseguir) y el LLM lo clasifica como business_rule_change sin ninguna bandera de
# revision -falso positivo silencioso. Fix en la raiz: normalizar NBSP a espacio normal en el
# texto de cada linea ANTES de que se use como nombre de columna/titulo (ver `_clean_text`),
# para que nunca entre al pipeline como una clave inconsistente.
NBSP = "\xa0"

# Bug real encontrado en validacion (2026-08-26, resolviendo [[pending-bug-fixes]] item 17):
# una malformacion DISTINTA a la del NBSP -"TCR" se extrae partido en 2 palabras reales
# ("TC R", espacio normal U+0020, no NBSP) en el titulo de tabla (10.5pt) del Apendice B,
# SOLO en el titulo de la 1ra pagina de cada tabla "TC 46, TCR N (Report Subgroup X)" -las
# redeclaraciones en paginas siguientes de la MISMA tabla extraen "TCR" correctamente (con
# NBSP). Confirmado con un escaneo completo del corpus (7 ediciones, las 5 apendices): el
# patron literal "TC R" (con limite de palabra) aparece SOLO en 3 ediciones consecutivas
# (`20230415`-`20240413`, se autocorrige desde `20250412`), SIEMPRE las mismas 9 instancias
# (1 por cada tabla "Report Subgroup" de este apendice), CERO apariciones legitimas de "TC R"
# en cualquier otro lugar del corpus -senal perfectamente segura para una sustitucion de texto
# literal. Sin este fix, la 1ra pagina de cada tabla queda con un `table_title` DISTINTO al
# de sus paginas de continuacion, fragmentando la tabla en 2 entradas para Modulo 3 (la
# fragmentada, de 1 sola pagina, no encuentra match exacto en la otra edicion -> `table_
# removed`/`table_renamed` espurios, ya logueado como el sintoma de este item).
TCR_SPLIT = re.compile(r"\bTC R\b")


def _clean_text(text: str) -> str:
    if not text:
        return text
    return TCR_SPLIT.sub("TCR", text.replace(NBSP, " "))


def _is_bold(line: dict) -> bool:
    return any("Bold" in f for f in line["fonts"])


def _split_noise(lines: list) -> tuple:
    """Separa lineas de chrome (encabezado/pie de pagina, siempre horizontales) del resto.
    Devuelve (contenido_relevante, ). El resto se clasifica luego por orientacion."""
    kept = []
    for line in lines:
        is_rotated = tuple(line["dir"]) == ROTATED_DIR
        y0, y1 = line["bbox"][1], line["bbox"][3]
        if not is_rotated:
            if y1 <= HEADER_Y1_MAX or y0 >= FOOTER_Y0_MIN:
                continue
            if DATE_LINE.match(line["text"].strip()) or line["text"].strip() == "Visa Confidential":
                continue
        kept.append(line)
    return kept


def _cluster_bands(values: list, tolerance: float) -> list:
    clusters = []
    for v in sorted(values):
        if clusters and (v - clusters[-1][-1]) <= tolerance:
            clusters[-1].append(v)
        else:
            clusters.append([v])
    return clusters


def _nearest_band(value: float, bands: dict) -> str:
    return min(bands, key=lambda name: abs(bands[name] - value))


def _cluster_header_tiers(header_lines: list, primary_axis: str) -> list:
    """Agrupa lineas candidatas a encabezado (9.5pt bold) en 'filas tipograficas' (tiers) por
    su posicion primaria (Y0 horizontal, X0 rotado), fusionando las 2 lineas de un mismo
    header envuelto (ver HEADER_ROW_WRAP_TOLERANCE/tolerancia de 20.0 mas abajo). Devuelve una
    lista de tiers en orden de aparicion, cada uno una lista de
    {"text","sec_pos","prim_pos"} -sec_pos = posicion secundaria (columna), prim_pos = donde
    arranca el tier en el eje primario (necesario para asignar filas de datos a su tabla/zona
    correcta cuando 2 tablas comparten una pagina, ver `_split_into_zones`)."""
    if not header_lines:
        return []
    prim_key = "y0" if primary_axis == "y0" else "x0"
    idx = {"y0": 1, "x0": 0}[prim_key]
    sec_idx = {"y0": 0, "x0": 3}[prim_key]

    by_row = {}
    for line in header_lines:
        prim = line["bbox"][idx]
        placed = False
        for row_key in by_row:
            if abs(prim - row_key) <= HEADER_ROW_WRAP_TOLERANCE:
                by_row[row_key].append(line)
                placed = True
                break
        if not placed:
            by_row[prim] = [line]

    tiers = []
    for row_key in sorted(by_row):
        row_lines = by_row[row_key]
        sec_clusters = _cluster_bands(sorted({l["bbox"][sec_idx] for l in row_lines}), 20.0)
        merged = []
        for cluster in sec_clusters:
            members = [l for l in row_lines if l["bbox"][sec_idx] in cluster]
            members.sort(key=lambda l: l["bbox"][idx])
            text = " ".join(m["text"].strip() for m in members)
            sec_pos = members[0]["bbox"][sec_idx]
            merged.append(
                {
                    "text": text,
                    "sec_pos": sec_pos,
                    "prim_pos": row_key,
                    # `text` ya viene recortado desde Modulo 1 -para saber si el fragmento
                    # CRUDO empezaba con un espacio real en el PDF fuente (ej. ' and Codes')
                    # hace falta el booleano `starts_with_space` que Modulo 1 guarda
                    # especificamente para esto (ver su docstring). Solo lo usa
                    # `_merge_phantom_columns`, para decidir si insertar un espacio al unir 2
                    # fragmentos de UN MISMO encabezado partido en 2 tiers separados por una
                    # rareza de renderizado -sin esto se pierde la distincion entre una fusion
                    # que necesita espacio ("Messages"+"and Codes") y una que no (mitad de
                    # palabra, "Business Tran"+"saction Type").
                    "starts_with_space": members[0].get("starts_with_space", False),
                }
            )
        tiers.append(merged)
    return tiers


def _finalize_zone_leaves(zone_tiers: list) -> tuple:
    """Dado el grupo de tiers de UNA tabla/zona (ya separados de otras tablas que compartan
    pagina, ver `_split_into_zones`), resuelve grupo-vs-hoja igual que antes: la ULTIMA fila
    son siempre hojas; de las anteriores, solo se conservan como hoja las que NO tengan una
    hoja de la ultima fila cerca (ver GROUP_HEADER_MIN_GAP). Devuelve (columnas, banderas de
    espacio inicial) -la 2da solo la usa `_merge_phantom_columns`, ver docstring."""
    if len(zone_tiers) == 1:
        leaves = zone_tiers[0]
    else:
        leaf_rows = zone_tiers[1:]
        all_leaf_secs = [h["sec_pos"] for row in leaf_rows for h in row]
        leaves = [h for row in leaf_rows for h in row]
        for h in zone_tiers[0]:
            nearest_leaf_dist = min((abs(h["sec_pos"] - s) for s in all_leaf_secs), default=None)
            if nearest_leaf_dist is None or nearest_leaf_dist > GROUP_HEADER_MIN_GAP:
                leaves.append(h)
    return (
        {h["text"]: h["sec_pos"] for h in leaves},
        {h["text"]: h["starts_with_space"] for h in leaves},
    )


def _split_into_zones(tiers: list) -> list:
    """Separa los tiers de encabezado de una pagina en 1+ 'zonas' (tablas independientes).
    Bug real encontrado en validacion (2026-08-19, ver [[manual8-vss-vol2-progress]]): cuando
    2 tablas REALMENTE DISTINTAS (ej. 2 registros V22xxx consecutivos, cada uno con su propio
    grid de 5 columnas Field Name/Position/Attribute/Field Sources/Comments) comparten una
    pagina rotada, sus encabezados generaban 2 tiers con los MISMOS 5 nombres de columna -el
    diccionario final `{nombre: posicion}` los colapsaba en 1 solo (colision de clave),
    perdiendo la posicion real de una de las 2 tablas y mezclando sus filas.

    Senal usada para separar: un tier que comparte ALGUN nombre de columna con un tier YA
    pendiente en la zona actual es, por definicion, una tabla NUEVA con el mismo esquema (no
    puede ser una fila "grupo" legitima de la MISMA tabla -un grupo real, ej. "Business Mode"
    sobre "Outgoing"/"Incoming" en el Apendice E, usa nombres DISTINTOS a los de su hoja, nunca
    el mismo nombre repetido). Se cierra la zona pendiente y arranca una nueva en ese tier."""
    zones = []
    pending = []
    pending_names = set()
    for tier in tiers:
        tier_names = {h["text"] for h in tier}
        if pending and (tier_names & pending_names):
            zones.append(pending)
            pending = [tier]
            pending_names = set(tier_names)
        else:
            pending.append(tier)
            pending_names |= tier_names
    if pending:
        zones.append(pending)

    zone_dicts = []
    for zone_tiers in zones:
        columns, leading_space = _finalize_zone_leaves(zone_tiers)
        zone_dicts.append(
            {"columns": columns, "leading_space": leading_space, "prim_start": zone_tiers[0][0]["prim_pos"]}
        )
    return zone_dicts


def _assign_zone(prim_pos: float, zones: list) -> int:
    """Devuelve el indice de la zona a la que pertenece una linea de DATOS, segun cual es la
    zona mas reciente cuyo encabezado ya aparecio antes de esa posicion (los datos de una
    tabla siempre vienen DESPUES de su propio encabezado de columnas). Si la linea cae ANTES
    del primer encabezado de tabla de la pagina, se asigna a la zona 0 (mejor asignar a la
    tabla mas cercana que descartar silenciosamente)."""
    best = 0
    for i, zone in enumerate(zones):
        if zone["prim_start"] <= prim_pos:
            best = i
    return best


def _assign_title_zone(prim_pos: float, zones: list) -> int:
    """Devuelve el indice de la zona para una linea de TITULO. A diferencia de los datos, el
    titulo de una tabla aparece ANTES de su propio encabezado de columnas (orden de lectura
    normal: titulo, luego headers, luego filas) -bug real encontrado en validacion
    (2026-08-19, Apendice C, ver [[manual8-vss-vol2-progress]]): cuando 2 tablas comparten
    pagina, el titulo de la 2da tabla ("Transaction Dispositions") cae geometricamente DESPUES
    del encabezado de columnas de la 1ra tabla pero ANTES del propio -`_assign_zone` (pensada
    para datos) lo asignaba a la zona 1ra por error, pegando ambos titulos. Se busca la zona
    MAS CERCANA CUYO ENCABEZADO VIENE DESPUES (no antes) de esta linea; si ninguna zona
    empieza despues (titulo tras el ultimo encabezado de la pagina, caso raro), cae en la
    ultima zona."""
    for i, zone in enumerate(zones):
        if zone["prim_start"] >= prim_pos:
            return i
    return len(zones) - 1


def _resegment_by_column(data_lines: list, columns: dict, idx_sec: int) -> list:
    """Divide una linea de datos en sus segmentos de Modulo 1 (`segments`, cortados en cada
    span de puro espacio en blanco) SOLO cuando la division revela una fusion REAL de 2
    celdas -bug real encontrado en validacion (2026-08-26, ver [[pending-bug-fixes]] item 15):
    PyMuPDF a veces fusiona el `Field Name` y el inicio de `Description` en una sola linea
    separados por un span de espacio (ej. Apendice B, "Net Amount Sign" + "This field
    contains..."). El mismo sintoma geometrico (span de espacio interno) tambien separa cada
    PALABRA de un titulo/leyenda de una sola celda legitima en otras partes de este manual
    (ej. Apendice A, "Settlement Warehouse Returned CRS Deferred", un unico row-label) -dividir
    siempre romperia ese caso. Senal usada para distinguir: se calcula a que columna mapea cada
    segmento (`_nearest_band` sobre su propio bbox, misma logica ya usada para lineas
    completas) -si TODOS los segmentos mapean a la MISMA columna, es una sola celda con
    espacios internos (no se divide, se usa la linea completa sin cambios); si mapean a 2+
    columnas DISTINTAS, es una fusion real (se divide, cada segmento pasa a ser su propia
    linea de datos). No aplica a lineas de encabezado (`header_lines`, otro camino de codigo
    enteramente separado -`_cluster_header_tiers`- nunca pasa por aca)."""
    if not columns:
        return data_lines
    result = []
    for line in data_lines:
        segments = line.get("segments")
        if not segments or len(segments) < 2:
            result.append(line)
            continue
        nearest = [_nearest_band(seg["bbox"][idx_sec], columns) for seg in segments]
        if len(set(nearest)) < 2:
            result.append(line)
            continue
        for seg in segments:
            result.append({**line, "text": seg["text"], "bbox": seg["bbox"]})
    return result


WINGDINGS_BULLET_FONT = "Wingdings"
# Ventana de distancia (en el eje primario) entre una linea de columna ancla y un marcador
# de vineta Wingdings que la sigue -calibrada con datos reales (ver docstring de
# _build_table_rows abajo): distancia real siempre 4.0-6.4pt en los 6 casos confirmados,
# nunca mas.
BULLET_FOLLOW_MAX_DIST = 10.0
# Tope superior del GAP para considerar la senal de vineta -separa el caso real (gap SIEMPRE
# exactamente 7.0pt, justo pasando el umbral de ROTATED_ANCHOR_WRAP_GAP_MAX=6.8) de disparos
# de fila nueva genuinos que tambien resultan tener una vineta cerca por coincidencia (ej.
# Apendice A, gaps de 174.5-202.6pt -un cambio de tabla real, nada ambiguo). Confirmado con un
# escaneo completo del corpus (ambos apendices rotados, las 7 ediciones): separacion limpia y
# enorme entre ambas poblaciones (7.0 vs 174.5+), CUALQUIER valor entre esos 2 numeros separa
# bien -elegido 10.0 con margen comodo de ambos lados.
BULLET_SUPPRESS_GAP_MAX = 10.0


def _build_table_rows(
    data_lines: list, columns: dict, primary_axis: str, leading_space: dict = None, bullet_lines: list = None
) -> list:
    """Reconstruye filas desde lineas de datos ya clasificadas en una tabla, dado el mapa de
    columnas {nombre: posicion_secundaria}. La columna ancla (dispara fila nueva) es la de
    menor posicion secundaria en horizontal (X0 mas a la izquierda) o mayor en rotado (Y1 mas
    alto = primera en orden de lectura, ver docstring). Devuelve (lista de dicts
    columna->texto, nombre de la columna ancla) -el nombre de ancla se expone para que Modulo
    3 sepa que columna usar como clave de emparejamiento sin tener que re-derivarla.

    **Senal de vineta Wingdings (agregada 2026-09-05, ver [[pending-bug-fixes]] item 15
    residuo (b))**: `bullet_lines` -opcional, solo lo pasa `build_rotated_blocks`- son las
    lineas de fuente "Wingdings*" de la pagina (el glifo "•" de sub-vineta en este manual se
    renderea como la letra "l" en Wingdings, ~6.4pt -PyMuPDF SI la captura en Modulo 1, nunca
    se pierde ahi; el bug real es que Modulo 2 la descartaba a "leftover" por no matchear
    ningun tamano de fuente esperado, desconectada de la fila). Confirmado con datos reales,
    contra-intuitivo: el marcador NO precede a su texto en el eje primario, lo SIGUE (~4-6.4pt
    despues, no antes) -la geometria real del glifo Wingdings no se comporta como el guion "–"
    literal (ver `_merge_dash_orphan_rows`, que si usa "precede"). Por eso esta senal se
    consulta hacia ADELANTE (bullet_dist = bullet.x0 - esta_linea.x0, buscado en
    BULLET_FOLLOW_MAX_DIST) para decidir si SUPRIMIR un `is_new_row` que de otra forma
    dispararia -nunca para forzar una fila nueva que no dispararia sola."""
    if not columns:
        return [], None
    if primary_axis == "y0":
        anchor_col = min(columns, key=lambda c: columns[c])
        idx_prim, idx_sec = 1, 0
        sec_sign = 1
    else:
        anchor_col = max(columns, key=lambda c: columns[c])
        idx_prim, idx_sec = 0, 3
        sec_sign = -1

    data_lines = _resegment_by_column(data_lines, columns, idx_sec)
    bullet_lines = bullet_lines or []

    rows = []
    active = None
    active_anchor_last_y = None
    unassigned_prefix = []

    # Empates en el eje primario (misma fila real) deben procesar PRIMERO la linea de la
    # columna ancla, para que dispare "fila nueva" antes de que otras columnas de esa misma
    # fila intenten sumarse a la fila (todavia activa) anterior -bug real encontrado en
    # validacion: en rotado el ancla es la banda secundaria MAS ALTA, asi que ordenar el eje
    # secundario ascendente (como en horizontal) la procesaba de ULTIMA, no de primera.
    for line in sorted(data_lines, key=lambda l: (l["bbox"][idx_prim], sec_sign * l["bbox"][idx_sec])):
        col = _nearest_band(line["bbox"][idx_sec], columns)
        prim = line["bbox"][idx_prim]
        # Fin de la linea en el EJE PRIMARIO (no el secundario/columna): Y1 en horizontal,
        # X1 en rotado -bug real encontrado en validacion: usar bbox[1] (Y0) en rotado
        # comparaba x0 contra y0, 2 ejes sin relacion, rompiendo la deteccion de fila nueva.
        prim_end = line["bbox"][3] if primary_axis == "y0" else line["bbox"][2]

        if col == anchor_col:
            gap = None if active is None else prim - active_anchor_last_y
            gap_max = ANCHOR_WRAP_GAP_MAX if primary_axis == "y0" else ROTATED_ANCHOR_WRAP_GAP_MAX
            is_new_row = active is None or gap > gap_max
            if (
                is_new_row
                and active is not None
                and gap <= BULLET_SUPPRESS_GAP_MAX
                and any(
                    0 < (b["bbox"][idx_prim] - prim) < BULLET_FOLLOW_MAX_DIST
                    and WINGDINGS_BULLET_FONT in " ".join(b.get("fonts", []))
                    for b in bullet_lines
                )
            ):
                is_new_row = False
            if is_new_row:
                if active:
                    rows.append(active)
                active = {c: [] for c in columns}
            active[col].append(line["text"])
            active_anchor_last_y = prim_end
        else:
            if active is None:
                unassigned_prefix.append(line["text"])
                continue
            active[col].append(line["text"])

    if active:
        rows.append(active)

    result = [{c: " ".join(v).strip() for c, v in row.items()} for row in rows]
    result = _merge_phantom_columns(result, columns, primary_axis, leading_space or {})
    result = _merge_dash_orphan_rows(result, anchor_col)
    if unassigned_prefix:
        # Deberia ser raro (Modulo 3 lo puede investigar si aparece con frecuencia): datos
        # cayendo al inicio de la tabla antes de que la columna ancla dispare ninguna fila.
        result.insert(0, {"__unassigned_prefix__": " ".join(unassigned_prefix)})
    return result, anchor_col


DASH_ORPHAN_PREFIX = re.compile(r"^[–‒-]\s")


def _merge_dash_orphan_rows(rows: list, anchor_col: str) -> list:
    """Fusiona filas 'huerfanas' que en realidad son la CONTINUACION envuelta de una fila
    compuesta con sub-vinetas (ver [[pending-bug-fixes]] item 15, residuo real re-medido y
    corregido 2026-09-05).

    **Root cause**: en filas compuestas con sub-items en guion "– " (ej. "Original Data:" con
    "– Original Trace" / "– Original Transmission Date" / "– Original Transmission Time" /
    "– Free Text" debajo, tabla V22240), cuando la columna `Field Sources` de esa fila envuelve
    a 3+ lineas, la posicion primaria de la linea final de envoltura puede caer DESPUES de
    donde el proximo sub-item (tambien en la columna ancla) ya disparo "fila nueva" en
    `_build_table_rows` -el mismo tramo de codigo procesa lineas en UN SOLO pase ordenado por
    posicion, asi que una vez que el ancla del siguiente sub-item dispara, todo lo que llega
    despues (aunque semanticamente pertenezca al sub-item anterior) se atribuye a la fila
    equivocada. Confirmado geometricamente ambiguo sin una senal de contenido (ver docstring
    de ROTATED_ANCHOR_WRAP_GAP_MAX arriba y [[dev-phase-considerations]]).

    **Senal usada, validada contra las 3939 filas de Apendice D con schema Position+Attribute
    antes de implementar (0 falsos positivos)**: una fila cuyo valor de columna ancla empieza
    con guion/en-dash ("– " o "- ") Y todas las demas columnas estan vacias. Las notas al pie
    legitimas (~119 casos reales en el corpus, ej. "1Amount fields are signed with two implied
    decimal positions.", "DX = Hexadecimal Display") tambien tienen todas las demas columnas
    vacias, pero NINGUNA empieza con guion -confirmado que las 2 primeras condiciones juntas
    (no cada una por separado) son las que dan la senal segura.

    **Alcance real medido, mucho menor al ~150-170 filas originalmente estimado en
    [[pending-bug-fixes]] item 15** (esa cifra parece haber sido medida antes de que el fix
    del item 18 -recalibracion de ROTATED_ANCHOR_WRAP_GAP_MAX, 2026-08-26, hecho por otro bug
    de Apendice A- redujera el impacto de este item como efecto secundario, sin que se
    re-midiera despues): solo 2 ubicaciones reales en todo el corpus (tabla V22240, filas
    "– Original Transmission Date" y "– Original Transmission Time – Free Text"), confinadas a
    las 3 ediciones mas viejas (`20220423`, `20221014`, `20230415`) -desde `20231013` en
    adelante el mismo layout no dispara la ambiguedad, nada que fusionar ahi.

    **Deliberadamente NO arreglado aca**: el mismo patron con vinetas "•" en vez de guion (ej.
    "ZIP Five ZIP Four", tabla V22220) no tiene senal de contenido -PyMuPDF no conserva el
    glifo "•" en estas celdas, a diferencia del guion "–" que si sobrevive en el texto
    extraido. Arreglarlo necesitaria un cambio en Modulo 1 (dejar de descartar ese glifo ahi),
    fuera de alcance de este fix -decision explicita del usuario tras evaluar el tradeoff."""
    merged = []
    for row in rows:
        anchor_val = (row.get(anchor_col) or "").strip()
        other_cols_empty = all(
            not (v or "").strip() for c, v in row.items() if c != anchor_col
        )
        if merged and other_cols_empty and DASH_ORPHAN_PREFIX.match(anchor_val):
            prev = merged[-1]
            prev[anchor_col] = f"{prev.get(anchor_col, '')} {anchor_val}".strip()
            continue
        merged.append(row)
    return merged


MIN_ROWS_FOR_PHANTOM_CHECK = 2


def _merge_phantom_columns(rows: list, columns: dict, primary_axis: str, leading_space: dict) -> list:
    """Fusiona columnas 'fantasma': encabezados que en realidad son el FRAGMENTO DERECHO de
    OTRO encabezado partido en 2 spans de texto sobre la MISMA linea por una rareza de
    renderizado del PDF fuente -bug real encontrado en validacion (2026-08-19, Apendice E,
    ver [[manual8-vss-vol2-progress]]): en 3 de las 7 ediciones, encabezados como "Messages and
    Codes" se extraen como 2 lineas separadas por un hueco horizontal ("Messages" / " and
    Codes"), NO por un salto de linea real (mismo Y0 exacto en ambas, confirmado con bbox
    reales) -y el mismo problema con "Business Transaction Type" -> "Business Tran"/"saction
    Type". Se probo primero un umbral geometrico (separacion entre el fin de un encabezado y
    el inicio del siguiente) pero se descarto: el gap espurio real (19.4-31.8pt) se superpone
    con el gap real minimo entre columnas GENUINAMENTE distintas en otras tablas ya validadas
    (Apendice B, "Field Length"->"Format" = 19.9pt) -ningun umbral unico separa ambos casos.

    Senal usada en cambio: una columna 100% vacia en TODAS las filas de esta tabla/zona,
    inmediatamente adyacente (en orden de lectura) a una columna que SI tiene contenido, es
    con altisima confianza un fragmento fantasma (confirmado real: "and Codes"/"saction Type"
    dan 0/6 filas no vacias en la tabla afectada, mientras sus vecinas dan 6/6) -se fusiona su
    texto de encabezado a la columna anterior y se descarta como columna propia. Requiere un
    minimo de filas (`MIN_ROWS_FOR_PHANTOM_CHECK`) para evitar un falso positivo por una unica
    fila donde ese campo simplemente este vacio de verdad."""
    if len(rows) < MIN_ROWS_FOR_PHANTOM_CHECK or not columns:
        return rows

    reading_order = sorted(columns, key=lambda c: columns[c], reverse=(primary_axis != "y0"))
    always_empty = {
        c for c in reading_order if all(not r.get(c, "").strip() for r in rows if "__unassigned_prefix__" not in r)
    }
    if not always_empty or len(always_empty) == len(reading_order):
        return rows

    for i, col in enumerate(reading_order):
        if col in always_empty and i > 0 and reading_order[i - 1] not in always_empty:
            prev_col = reading_order[i - 1]
            # Renombra la columna anterior con el texto de encabezado completo (ej.
            # "Messages" + " and Codes" -> "Messages and Codes") -no solo fusiona los
            # valores- para que su nombre coincida con el de las ediciones donde este
            # encabezado SI se extrajo limpio en una sola linea, y Modulo 4 pueda diffear
            # por nombre de columna correctamente entre ediciones.
            separator = " " if leading_space.get(col) else ""
            merged_name = f"{prev_col}{separator}{col}".strip()
            for r in rows:
                if "__unassigned_prefix__" in r:
                    continue
                value = f"{r.pop(prev_col)}{r.pop(col)}".strip()
                r[merged_name] = value

    return rows


def _flush_paragraph(buf: list) -> str:
    return " ".join(buf).strip()


def build_horizontal_blocks(lines_by_page: dict) -> list:
    blocks = []
    for page in sorted(lines_by_page):
        page_lines = sorted(lines_by_page[page], key=lambda l: (l["bbox"][1], l["bbox"][0]))

        heading_lines = [l for l in page_lines if l["max_font_size"] in HEADING_FONT_SIZES]
        for hl in heading_lines:
            blocks.append(
                {
                    "order": hl["order"],
                    "type": "section_heading",
                    "page": page,
                    "level": HEADING_FONT_SIZES[hl["max_font_size"]],
                    "text": hl["text"].strip(),
                }
            )

        title_lines = [
            l for l in page_lines if l["max_font_size"] == TABLE_TITLE_FONT_SIZE and _is_bold(l)
        ]
        header_lines = [
            l for l in page_lines if l["max_font_size"] == HEADER_FONT_SIZE and _is_bold(l)
        ]
        data_lines = [l for l in page_lines if l["max_font_size"] == DATA_FONT_SIZE]

        tiers = _cluster_header_tiers(header_lines, primary_axis="y0")
        zones = _split_into_zones(tiers)

        # Titulos y datos se enrutan a la zona (tabla) mas cercana que ya los precede -ver
        # docstring de `_split_into_zones`: 2 tablas distintas pueden compartir una pagina.
        titles_by_zone = defaultdict(list)
        for t in title_lines:
            titles_by_zone[_assign_title_zone(t["bbox"][1], zones)].append(t)
        data_by_zone = defaultdict(list)
        for d in data_lines:
            data_by_zone[_assign_zone(d["bbox"][1], zones)].append(d)

        for zone_idx, zone in enumerate(zones):
            zone_titles = titles_by_zone.get(zone_idx, [])
            table_title = " ".join(t["text"].strip() for t in zone_titles) if zone_titles else ""
            title_order = zone_titles[0]["order"] if zone_titles else None

            zone_data = data_by_zone.get(zone_idx, [])
            rows, anchor_col = _build_table_rows(
                zone_data, zone["columns"], primary_axis="y0", leading_space=zone["leading_space"]
            )

            first_data_order = min((l["order"] for l in zone_data), default=None)
            row_order = first_data_order if first_data_order is not None else title_order
            for row in rows:
                blocks.append(
                    {
                        "order": row_order if row_order is not None else 0,
                        "type": "grid_row",
                        "page": page,
                        "table_title": table_title,
                        "anchor_column": anchor_col,
                        "columns": row,
                    }
                )

        # Parrafo residual: texto 10.5 Regular que no es titulo de tabla (intro/nota), y
        # cualquier otro texto de tamano no cubierto arriba -se conserva, no se descarta.
        leftover = [
            l
            for l in page_lines
            if l["max_font_size"] not in HEADING_FONT_SIZES
            and not (l["max_font_size"] == TABLE_TITLE_FONT_SIZE and _is_bold(l))
            and not (l["max_font_size"] == HEADER_FONT_SIZE and _is_bold(l))
            and l["max_font_size"] != DATA_FONT_SIZE
        ]
        if leftover:
            leftover.sort(key=lambda l: l["order"])
            blocks.append(
                {
                    "order": leftover[0]["order"],
                    "type": "paragraph",
                    "page": page,
                    "text": _flush_paragraph([l["text"] for l in leftover]),
                }
            )

    return blocks


def build_rotated_blocks(lines_by_page: dict) -> list:
    blocks = []
    for page in sorted(lines_by_page):
        page_lines = [l for l in lines_by_page[page] if tuple(l["dir"]) == ROTATED_DIR]
        # Descarta contenido de mainframe de ejemplo (ficticio, autodeclarado) por fuente,
        # nunca por tamano (que varia real y confirmadamente entre tablas, ver docstring).
        page_lines = [l for l in page_lines if DISPOSABLE_FONT not in l["fonts"]]
        if not page_lines:
            continue
        page_lines.sort(key=lambda l: (l["bbox"][0], l["bbox"][3]))

        heading_lines = [l for l in page_lines if l["max_font_size"] in ROTATED_HEADING_FONT_SIZES]
        for hl in heading_lines:
            blocks.append(
                {
                    "order": hl["order"],
                    "type": "section_heading",
                    "page": page,
                    "level": ROTATED_HEADING_FONT_SIZES[hl["max_font_size"]],
                    "text": hl["text"].strip(),
                }
            )

        title_lines = [
            l for l in page_lines if l["max_font_size"] == ROTATED_TABLE_TITLE_FONT_SIZE and _is_bold(l)
        ]
        header_lines = [
            l for l in page_lines if l["max_font_size"] == ROTATED_HEADER_FONT_SIZE and _is_bold(l)
        ]
        data_lines = [l for l in page_lines if l["max_font_size"] == ROTATED_DATA_FONT_SIZE]
        bullet_lines = [l for l in page_lines if WINGDINGS_BULLET_FONT in " ".join(l.get("fonts", []))]

        tiers = _cluster_header_tiers(header_lines, primary_axis="x0")
        zones = _split_into_zones(tiers)

        titles_by_zone = defaultdict(list)
        for t in title_lines:
            titles_by_zone[_assign_title_zone(t["bbox"][0], zones)].append(t)
        data_by_zone = defaultdict(list)
        for d in data_lines:
            data_by_zone[_assign_zone(d["bbox"][0], zones)].append(d)

        for zone_idx, zone in enumerate(zones):
            zone_titles = titles_by_zone.get(zone_idx, [])
            table_title = " ".join(t["text"].strip() for t in zone_titles) if zone_titles else ""
            title_order = zone_titles[0]["order"] if zone_titles else None

            zone_data = data_by_zone.get(zone_idx, [])
            rows, anchor_col = _build_table_rows(
                zone_data,
                zone["columns"],
                primary_axis="x0",
                leading_space=zone["leading_space"],
                bullet_lines=bullet_lines,
            )

            first_data_order = min((l["order"] for l in zone_data), default=None)
            row_order = first_data_order if first_data_order is not None else title_order
            for row in rows:
                blocks.append(
                    {
                        "order": row_order if row_order is not None else 0,
                        "type": "grid_row",
                        "page": page,
                        "table_title": table_title,
                        "anchor_column": anchor_col,
                        "columns": row,
                    }
                )

        leftover = [
            l
            for l in page_lines
            if l["max_font_size"] not in ROTATED_HEADING_FONT_SIZES
            and not (l["max_font_size"] == ROTATED_TABLE_TITLE_FONT_SIZE and _is_bold(l))
            and not (l["max_font_size"] == ROTATED_HEADER_FONT_SIZE and _is_bold(l))
            and l["max_font_size"] != ROTATED_DATA_FONT_SIZE
        ]
        for l in leftover:
            blocks.append(
                {
                    "order": l["order"],
                    "type": "paragraph",
                    "page": page,
                    "text": l["text"].strip(),
                }
            )

    return blocks


def normalize_edition(edition_json_path: Path) -> dict:
    data = json.loads(edition_json_path.read_text())
    sections_out = {}

    for appendix, section in data["sections"].items():
        if appendix == "front_matter":
            sections_out[appendix] = {"num_blocks": 0, "blocks": []}
            continue

        for line in section["lines"]:
            line["text"] = _clean_text(line["text"])
        clean_lines = _split_noise(section["lines"])
        lines_by_page = {}
        for line in clean_lines:
            lines_by_page.setdefault(line["page"], []).append(line)

        rotated_appendix = appendix in ("appendix_a", "appendix_d")
        blocks = build_rotated_blocks(lines_by_page) if rotated_appendix else build_horizontal_blocks(lines_by_page)
        blocks.sort(key=lambda b: b["order"])
        for b in blocks:
            del b["order"]
        sections_out[appendix] = {"num_blocks": len(blocks), "blocks": blocks}

    return {
        "manual": data["manual"],
        "edition_date": data["edition_date"],
        "source_file": data["source_file"],
        "sections": sections_out,
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
        summary = ", ".join(f"{k}={v['num_blocks']}" for k, v in result["sections"].items())
        print(f"{input_path.name}: [{summary}]")


if __name__ == "__main__":
    main()
