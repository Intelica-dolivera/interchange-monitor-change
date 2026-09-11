"""
Modulo 2 - Normalizacion de bloques para el manual base_ii_clearing_edit_package_messages.

Toma las lineas atomicas del Modulo 1 (cada una con su bbox, tamano/fuente de letra
maxima y lista de fuentes) y las reconstruye en bloques con sentido: el encabezado de
cada ficha de codigo (codigo + titulo), sus campos etiquetados (`Description:`/`Action:`),
su lista de tipos de transaccion (solo Capitulo 2), y parrafos narrativos para todo lo
demas (TOC, aviso legal, encabezados de capitulo/seccion, glosario).

Diferencias de diseno respecto al Modulo 2 de `base_ii_clearing_data_codes` (ver discusion
completa del porque en local_memory/NOTES.md, seccion "Cerrando Modulo 1" de este manual):

1. La deteccion de "esto es el comienzo de una ficha nueva" NO usa un patron de texto
   (`^[A-Z]{0,2}\\d{4,6}(-[A-Z])?$` tiene falsos positivos reales -una lista de MCCs
   envuelta en un parrafo produce una linea suelta "5969" que matchea sin ser un codigo-)
   sino la senal tipografica ya validada en Modulo 1: `max_font_size == 20.0`. Es
   inequivoca (952/952 lineas en ese tamano matchean un codigo real en la edicion de
   referencia, 0 falsos positivos/negativos) y estable en las 9 ediciones a pesar de que
   el NOMBRE de fuente cambio a mitad de camino (rebranding de Visa, `SegoeUI-Bold` ->
   `OpenSans-Bold`) -por eso se usa el tamano, no el nombre, como disparador.

2. El contenido de este manual es texto corrido de una sola columna (no una grilla
   multi-columna como el Tipo B del otro manual), asi que NO hace falta la reconstruccion
   geometrica de filas/celdas por solapamiento de banda Y que necesito el otro Modulo 2.
   El orden natural que entrega PyMuPDF por pagina ya coincide con el orden de lectura
   real, una vez filtrado el ruido de header/footer (verificado con datos reales: sin
   filtrar, el header/footer de cada pagina aparece al FINAL de esa pagina en el orden
   "order", no al principio -por eso hay que filtrarlo ANTES de confiar en el orden, no
   reordenar por (y0,x0) como en el otro manual).

3. **Se procesa el documento COMPLETO como un solo stream continuo, sin resetear estado
   por pagina** -aplicando directamente la leccion aprendida en `base_ii_clearing_data_codes`
   (el bug de continuidad `"H0 (continued)"`, que paso desapercibido hasta que se armo
   Modulo 3, causado justamente por resetear el estado en cada salto de pagina). Ese bug
   entero queda evitado de raiz aca: si el texto de `Description:`/`Action:` de una ficha
   se corta justo en un salto de pagina, las lineas siguientes se siguen acumulando en el
   mismo campo activo sin importar el numero de pagina, porque no hay ninguna frontera de
   estado en el salto de pagina.

Patron de una ficha (Capitulo 2 "Validation Messages", con `Transaction Types:`; Capitulo 3
"Log Messages" es identico pero SIN esa ultima seccion):
```
V0027                                                          <- codigo (size 20.0)
BUSINESS APPLICATION ID IS INVALID FOR ARGENTINA DOMESTIC ...  <- titulo (fuente CourierNewPS-BoldMT, mayusculas)
Description: AFT Original and Reversal transactions...         <- puede envolver 2+ lineas
Action: Enter the correct value for the field.
Transaction Types:
●  Account Funding — Originals and Reversals                   <- viñeta + texto (puede envolver 2+ lineas)
```

Limitacion aceptada (tabla chica, no arreglada a proposito): la tabla de 2 columnas "Message
Severity Levels" al principio del Capitulo 3 no tiene ninguna senal especial que la distinga
de texto narrativo -cae como bloque `paragraph` sin estructura. No es el contenido central del
proyecto (fichas de codigo de validacion/log), y son solo 6 filas -no se justifica un parser
dedicado.

**Glosario (ultimas paginas, encabezado "BASE II Glossary") -arreglado 2026-08-25, resolviendo
[[pending-bug-fixes]] item de este manual, mismo bug ya cerrado en `base_ii_clearing_data_codes`
(ver su Modulo 2, punto 8 del docstring).** Investigado con datos reales antes de tocar codigo:
es EXACTAMENTE el mismo glosario, mismo contenido, misma geometria de 2 columnas (termino en
`OpenSans-Bold` a X0=72 / definicion en `OpenSans-Regular` a X0=216, ambos 9.0pt) que ya se
resolvio en el otro manual -pero la arquitectura de ESTE Modulo 2 (stream de 1 sola columna,
sin reconstruccion de filas/celdas por banda Y) es fundamentalmente distinta, asi que el fix no
se pudo portar tal cual.

**Diseno elegido: reusar el vocabulario de bloques de FICHA (`card_header`+`field`) en vez de
crear un tipo de bloque nuevo**, para no tocar Modulos 3/4/5/7 (que ya saben diffear
`ficha_content_changed` por campo con nombre) -mismo principio de "reusar antes que inventar"
que ya goberno el fix del glosario del otro manual (ahi tambien se descarto un tipo de bloque
nuevo a favor de generalizar `table_row`). Cada entrada de glosario se emite como un
`card_header` sintetico (`code`=`title`=el termino completo, igual que un codigo real de
ficha) seguido de un `field` con `label="Description"` (la definicion) -Modulo 3 ya sabe
capturar ambos sin ningun cambio. El campo `label="Description"` es una eleccion deliberada
(no "Definition", que Modulo 3 ignoraria silenciosamente por no estar en su whitelist de
labels reconocidos) a costa de una etiqueta levemente imprecisa en el reporte final
("**Description**" en vez de "**Definición**") -tradeoff aceptado por lo poco que cuesta
corregirlo despues si se pide, contra el costo real de tocar 4 modulos ya cerrados y validados.

Mecanismo: se activa `in_glossary=True` al ver la fila de 1 linea "BASE II Glossary" (26pt,
mismo chequeo de tamano que ya existia para separar subtitulos de seccion). Mientras esta
activo, una linea en negrita `OpenSans-Bold` que arranca a X0<100 (el margen del termino, con
margen amplio respecto al X0=216 de la definicion) inicia una entrada nueva -salvo que el hueco
vertical hasta la ULTIMA linea de termino ya vista sea chico (`GLOSSARY_TERM_WRAP_GAP_MAX`,
misma calibracion validada en el otro manual: terminos envueltos en 2+ lineas quedan pegados
<=0pt, una entrada nueva arranca siempre a 17.3pt o mas -confirmado con un escaneo de este
mismo documento, mismo margen amplio), en cuyo caso se acumula como continuacion del MISMO
termino en vez de cerrar la entrada. La transicion de "termino acumulandose" a "definicion
acumulandose" ocurre en la 1ra linea que NO es una linea de termino -ahi se cierra el
`card_header` y arranca el `field` de `Description`, que de ahi en mas reusa sin cambios la
logica de acumulacion de campo ya existente en este modulo (linea "if active is not None and
active['type'] == 'field': ..."), incluidas las viñetas `"●"` dentro de una definicion (vienen
fusionadas en la misma linea de PyMuPDF que el texto que las sigue, no necesitan tratamiento
especial de `bullet_list` como si lo necesita `Transaction Types:`).
"""

import json
import re
import sys
from pathlib import Path

MANUAL_SLUG = "base_ii_clearing_edit_package_messages"
INPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "01_ingesta_parseo"
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "02_normalizacion_bloques"

# Bandas de header/footer, calibradas con datos reales de este manual (distintas a las de
# base_ii_clearing_data_codes -no reusar esas constantes, ver NOTES.md).
# Bug real encontrado en Modulo 3 (2026-08-13), misma categoria que el de FOOTER_Y_MIN mas
# abajo: la 2da linea del header (el titulo de seccion corriente, "Validation Messages" o
# "Log Messages") tiene y1=40.6 en las 3 primeras ediciones y en la mas nueva (41.0), pero
# y1=42.5 en las 5 ediciones del medio (20231014-20251018) -otro cambio de formato tipo
# "rebrand" no capturado la primera vez que se calibro esta banda (esa calibracion solo se
# habia hecho contra la edicion de referencia, la mas nueva). Con el viejo umbral de 41, esa
# linea se colaba como texto normal en 5 de 9 ediciones y se pegaba al final del bloque
# activo en ese momento -confirmado con datos reales: el ultimo item de la lista de
# `Transaction Types` de la ficha V0002 en la edicion 20251018 terminaba en "...Original
# Credit — Originals and Reversals Validation Messages". Recalibrado contra las 9 ediciones:
# el header real nunca pasa de y1=42.5 y el contenido real de pagina nunca empieza antes de
# y0=45.9 -44.0 tiene margen en las 2 direcciones sin arriesgar filtrar contenido real.
HEADER_Y_MAX = 44.0
# Bug real encontrado en Modulo 3 (2026-08-13): con 758.9, las lineas de footer (fecha +
# "Visa Confidential" + numero de pagina) tienen y0 tan bajo como 758.8 en varias ediciones
# -0.1pt por debajo del umbral- asi que la fecha y el numero de pagina se colaban como texto
# normal y se pegaban al final del campo `field`/`bullet_list` activo en ese momento
# (confirmado con datos reales: "...return message YYYY. 23 April 2022 259" en la ficha
# 000001-I, edicion 20220423). Recalibrado contra las 9 ediciones: el contenido real de
# pagina nunca pasa de y0=709.2 y el footer real nunca baja de y0=758.8 -hay una banda vacia
# de ~50pt entre ambos- asi que 750.0 tiene margen de sobra en las 2 direcciones sin
# arriesgar filtrar contenido real.
FOOTER_Y_MIN = 750.0

TOC_DOT_LEADER = re.compile(r"(\. ){4,}")
CODE_FONT_SIZE = 20.0
# Encontrado validando contra el indice (TOC) de la edicion de referencia: exactamente 1
# codigo de 952 (`V9003`) usa tamano 26.0 en vez de 20.0 -el mismo tamano que los subtitulos
# de seccion ("Problem Resolution", "Log Reports", etc.), asi que NO se puede aceptar 26.0
# sin mas: se exige ademas que el texto matchee el patron de codigo (una seccion nunca lo
# hace, cero riesgo de colision real).
CODE_FONT_SIZE_FALLBACK = 26.0
CODE_PATTERN = re.compile(r"^[vV]\d{4}$|^\d{6}-[A-Z]$")
# La fuente monoespaciada del titulo tiene 3 variantes reales en el documento (Bold,
# BoldItalic, Italic -esta ultima usada, ej., para resaltar un placeholder "XXXX" dentro
# del titulo), por eso se matchea por prefijo en vez de por nombre exacto.
TITLE_FONT_PREFIX = "CourierNewPS"
# "Transaction Type:" (singular) aparece al menos una vez en la edicion de referencia junto
# a la forma plural habitual "Transaction Types:" -se acepta cualquiera de las dos.
LABEL_PATTERN = re.compile(r"^(Description|Action|Transaction Types?):\s*(.*)$")
# Bug real encontrado en Modulo 3 (2026-08-13): "●"/"■" solo cubren el glifo de viñeta de la
# edicion de referencia (la mas nueva, 20260418). Las otras 8 de 9 ediciones usan un glifo
# distinto que PyMuPDF extrae como la letra "l" (fuente/tamano de simbolo, no la letra "l"
# real) -confirmado con datos reales: 1400+ lineas de texto "l" por edicion, siempre a
# tamano 8.0pt (o 6.4pt para unas pocas, viñetas anidadas), nunca al tamano de cuerpo normal
# (10.5pt), asi que no hay riesgo real de confundir una "l" de texto real con esto. Sin este
# fix, cada viñeta de `Transaction Types` en esas 8 ediciones se fusionaba con la siguiente
# en un solo item gigante en vez de separarse (la deteccion de "esto es un glifo de viñeta"
# fallaba, asi que el codigo caia en la rama de "continuar el item activo").
BULLET_GLYPHS = {"●", "■", "l"}
# Bug real encontrado en Modulo 5 (2026-08-13, via la red de seguridad de contenido
# desaparecido): la ficha `V0545` tiene, en 8 de las 9 ediciones (arreglado recien en la
# mas nueva, `20260418`, donde ya aparece en su propia linea), la etiqueta `Action:`
# pegada al FINAL de la linea de `Description:` en vez de en su propia linea -layout
# ajustado del PDF fuente- sin texto despues en esa misma linea fisica (el valor real de
# `Action` arranca en la linea siguiente). Sin este split, `LABEL_PATTERN` matcheaba
# normalmente contra la etiqueta del PRINCIPIO de la linea (`Description:`) pero el
# `rest` capturado se tragaba el `Action:` colgado como si fuera parte del texto de
# Description. Es el UNICO caso real en las 9 ediciones completas (verificado
# programaticamente, 0 ocurrencias fuera de esta ficha), pero se resuelve con una regla
# general -una etiqueta nueva sin texto despues en el resto de la linea- en vez de
# hardcodear el codigo de esta ficha puntual.
TRAILING_LABEL_PATTERN = re.compile(r"^(.*\S)\s+(Description|Action|Transaction Types?):\s*$")

# Glosario (ver docstring del modulo, seccion agregada 2026-08-25). Mismo texto de encabezado
# y misma calibracion de hueco vertical ya validada en `base_ii_clearing_data_codes`.
GLOSSARY_HEADING_TEXT = "BASE II Glossary"
# El termino usa negrita, pero el NOMBRE de fuente cambia a mitad de camino por el mismo
# rebrand ya documentado arriba (punto 1 del docstring, `SegoeUI-Bold` -> `OpenSans-Bold`):
# confirmado en las 9 ediciones, las 3 mas viejas (20220423-20230415) usan `SegoeUI-Bold`,
# las 6 mas nuevas `OpenSans-Bold` -se aceptan ambas, nunca coexisten en la misma edicion.
GLOSSARY_TERM_FONTS = {"OpenSans-Bold", "SegoeUI-Bold"}
GLOSSARY_TERM_X_MAX = 100.0
GLOSSARY_TERM_WRAP_GAP_MAX = 8.0


def _new_field_or_bullet(label: str, rest: str, page: int) -> dict:
    if label.startswith("Transaction Type"):
        items = [rest] if rest else []
        return {"type": "bullet_list", "page": page, "items": items, "_awaiting_item": False}
    return {"type": "field", "page": page, "label": label, "text": rest}


def is_noise(line: dict) -> bool:
    y0, y1 = line["bbox"][1], line["bbox"][3]
    if y1 <= HEADER_Y_MAX or y0 >= FOOTER_Y_MIN:
        return True
    if TOC_DOT_LEADER.search(line["text"]):
        return True
    return False


def _is_code_line(line: dict) -> bool:
    if line["max_font_size"] == CODE_FONT_SIZE:
        return True
    return line["max_font_size"] == CODE_FONT_SIZE_FALLBACK and bool(CODE_PATTERN.match(line["text"]))


def build_blocks(lines: list) -> list:
    blocks = []
    active = None
    in_glossary = False
    last_glossary_line_y1 = None

    def flush():
        nonlocal active
        if active:
            active.pop("_awaiting_item", None)
            blocks.append(active)
        active = None

    for line in lines:
        text = line["text"]
        page = line["page"]
        x0, y0, y1 = line["bbox"][0], line["bbox"][1], line["bbox"][3]

        if _is_code_line(line):
            flush()
            active = {"type": "card_header", "page": page, "code": text, "title": None}
            continue

        # La 1ra linea despues de un codigo SIEMPRE es el titulo, sea cual sea su fuente
        # -encontrado con datos reales: 2 de 952 codigos en la edicion de referencia usan
        # `OpenSans-Bold` en vez de la fuente monoespaciada `CourierNewPS-BoldMT` para el
        # titulo (inconsistencia real del PDF fuente, no un artefacto de extraccion), asi
        # que exigir esa fuente para la 1ra linea los perdia. El titulo puede envolver en
        # 2+ lineas para titulos largos (ej. "CARD ACCEPTOR ID MUST NOT EQUAL SPACES FOR US
        # EIRF ORIGINAL PURCHASE AND" / "REVERSAL TRANSACTION") -para esas continuaciones SI
        # se exige la fuente monoespaciada, porque ahi ya no hay ambiguedad posicional (algo
        # tiene que distinguir "esto sigue siendo titulo" de "esto ya es Description:").
        if active is not None and active["type"] == "card_header" and active["title"] is None:
            active["title"] = text
            continue
        if active is not None and active["type"] == "card_header" and any(
            f.startswith(TITLE_FONT_PREFIX) for f in line["fonts"]
        ):
            active["title"] = f"{active['title']} {text}"
            continue

        # Termino de glosario (ver docstring del modulo, seccion agregada 2026-08-25):
        # negrita OpenSans a la columna izquierda, solo mientras `in_glossary` esta activo
        # (evita falsos positivos con otro texto en negrita del resto del documento, ej. si
        # alguna etiqueta de campo tambien fuera bold).
        if (
            in_glossary
            and any(f in GLOSSARY_TERM_FONTS for f in line["fonts"])
            and x0 < GLOSSARY_TERM_X_MAX
        ):
            is_wrap = (
                active is not None
                and active["type"] == "glossary_term"
                and last_glossary_line_y1 is not None
                and y0 - last_glossary_line_y1 < GLOSSARY_TERM_WRAP_GAP_MAX
            )
            if is_wrap:
                active["term"] = f"{active['term']} {text}".strip()
            else:
                flush()
                active = {"type": "glossary_term", "page": page, "term": text}
            last_glossary_line_y1 = y1
            continue

        # Subtitulo de capitulo/seccion (26/30/40pt, ej. "Data Entry Messages", "Problem
        # Resolution") que no es un codigo (ya se descarto en _is_code_line arriba). El
        # cuerpo normal de una ficha (Description/Action/viñetas) siempre es 9-10.5pt, asi
        # que cualquier cosa mas grande es, por definicion, un limite de seccion -no debe
        # fusionarse como si fuera continuacion del campo o la viñeta activa. Encontrado con
        # datos reales: sin este corte, "Data Entry Messages" se pegaba al final del ultimo
        # item de un `bullet_list` ("n/a Data Entry Messages") en vez de cortarlo.
        if line["max_font_size"] > 15:
            flush()
            active = {"type": "paragraph", "page": page, "text": text}
            if text == GLOSSARY_HEADING_TEXT:
                in_glossary = True
            continue

        # 1ra linea que NO es termino, justo despues de 1+ lineas de termino acumuladas:
        # cierra el termino y arranca su definicion. Se emite el `card_header` sintetico
        # DIRECTO a `blocks` (no via `active`) porque `active` pasa a representar la
        # definicion en curso -mismo vocabulario de bloques (`card_header`+`field`) que una
        # ficha real, para que Modulos 3/4/5/7 lo procesen sin ningun cambio (ver docstring).
        if active is not None and active["type"] == "glossary_term":
            term = active["term"]
            blocks.append({"type": "card_header", "page": page, "code": term, "title": term})
            active = {"type": "field", "page": page, "label": "Description", "text": text}
            continue

        m = LABEL_PATTERN.match(text)
        if m:
            flush()
            label, rest = m.group(1), m.group(2)
            # Caso real (ver TRAILING_LABEL_PATTERN mas arriba): la propia "rest" de esta
            # etiqueta puede terminar en OTRA etiqueta colgada, sin texto despues, si el
            # PDF puso 2 etiquetas en la misma linea fisica -hay que cortar ahi y arrancar
            # un 2do bloque en vez de tragarse la 2da etiqueta como contenido de la 1ra.
            trailing = TRAILING_LABEL_PATTERN.match(rest) if rest else None
            if trailing:
                real_rest, trailing_label = trailing.group(1), trailing.group(2)
                active = _new_field_or_bullet(label, real_rest, page)
                flush()
                active = _new_field_or_bullet(trailing_label, "", page)
            else:
                # A veces el valor va inline en la misma linea ("Transaction Types: All
                # Financial Drafts", "Transaction Types: n/a") en vez de una lista con
                # viñetas -195 casos confirmados en la edicion de referencia. Si hay texto
                # despues de los dos puntos, es el primer (y a veces unico) item.
                active = _new_field_or_bullet(label, rest, page)
            continue

        if text in BULLET_GLYPHS and active is not None and active["type"] == "bullet_list":
            active["_awaiting_item"] = True
            continue

        # Vinieta suelta en su propia linea dentro de una definicion de glosario (solo en
        # las 3 ediciones mas viejas -`SegoeUI`/`Wingdings`-, confirmado con datos reales:
        # en las 6 mas nuevas la vinieta viene fusionada en la MISMA linea que el texto que
        # la sigue, ver docstring). Sin este filtro, el glifo se cuela como una palabra
        # suelta ("l") dentro del texto de la definicion -acotado a `in_glossary` para no
        # tocar el comportamiento ya validado de campos `Description`/`Action` reales.
        if in_glossary and text in BULLET_GLYPHS and active is not None and active["type"] == "field":
            continue

        if active is not None and active["type"] == "field":
            active["text"] = f"{active['text']} {text}".strip()
            continue

        if active is not None and active["type"] == "bullet_list":
            if active["_awaiting_item"] or not active["items"]:
                active["items"].append(text)
                active["_awaiting_item"] = False
            else:
                active["items"][-1] = f"{active['items'][-1]} {text}".strip()
            continue

        if active is not None and active["type"] == "paragraph":
            active["text"] = f"{active['text']} {text}".strip()
            continue

        flush()
        active = {"type": "paragraph", "page": page, "text": text}

    flush()
    return blocks


def normalize_edition(edition_json_path: Path) -> dict:
    data = json.loads(edition_json_path.read_text())
    clean_lines = [line for line in data["lines"] if not is_noise(line)]
    clean_lines.sort(key=lambda l: l["order"])

    blocks = build_blocks(clean_lines)

    return {
        "manual": data["manual"],
        "edition_date": data["edition_date"],
        "source_file": data["source_file"],
        "num_lines_in": data["num_lines"],
        "num_lines_kept": len(clean_lines),
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
