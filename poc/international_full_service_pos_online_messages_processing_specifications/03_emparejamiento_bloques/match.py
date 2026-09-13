"""
Modulo 3 - Emparejamiento de bloques para el manual
international_full_service_pos_online_messages_processing_specifications.

Toma el stream plano de bloques del Modulo 2 (`section_heading` con nivel 1/2/3 +
`paragraph`) y reconstruye la entidad real a comparar -una seccion identificada por su RUTA
JERARQUICA completa (titulo L1 + L2 + L3, no solo el titulo inmediato)- y empareja secciones
y, dentro de cada seccion emparejada, sus parrafos, entre 2 ediciones consecutivas.

**Clave de emparejamiento de secciones: RUTA jerarquica completa, no titulo suelto -decidido
con datos reales, no de antemano.** Confirmado que titulos de encabezado de nivel 2/3 se
REPITEN de forma sistematica bajo distintos padres (7 titulos L2 repetidos de 80, ej.
"Cardholder Transactions" aparece bajo el capitulo "Transaction Types" Y bajo "Standard
Processing" -son 2 secciones genuinamente distintas, no una ambiguedad rara como el caso
`TC 57` del 4to manual). A diferencia de ese caso (donde alcanzo con emparejar por orden de
aparicion, por ser una ambiguedad aislada), aca la repeticion es un patron ESTRUCTURAL
esperable en un documento bien organizado -la ruta completa (L1>L2>L3) resulta unica en
264/264 secciones de la edicion mas reciente (0 colisiones) y en 295/296 de la edicion mas
vieja disponible (1 colision residual, ver duplicados mas abajo).

**Emparejamiento de parrafos: exacto primero, fuzzy con salvaguardas especificas despues
-NO el mismo diseno "solo exacto" del 5to manual, decidido tras investigar el riesgo real**:
a diferencia de las filas cortas del 5to manual (donde CUALQUIER fuzzy matching demostro ser
inseguro), la prosa de este manual es mayormente mas larga y distintiva, y el usuario
explicitamente quiere que Modulo 5 (IA) tenga parrafos "reescritos" reales para clasificar
-un diseno solo-exacto dejaria a Modulo 5 sin nada que clasificar, igual que paso con el 5to
manual (no lo que el usuario pidio aca). Medido con datos reales (`difflib`, la seccion mas
grande con 485 "parrafos" -en realidad fragmentos de un diagrama de flujo de conversion de
moneda, ver Modulo 2): fuzzy matching SIN filtro es claramente inseguro (2052 pares
riesgosos >=0.85 solo en esa seccion). Filtrando por longitud minima (>=60 caracteres,
descarta fragmentos cortos tipo diagrama/tabla) y subiendo el umbral a 0.90, el riesgo cae
~20x pero NO llega a cero -quedan casos residuales de contenido genuinamente distinto con
alta similitud textual por ser formulaico/plantillado (ej. "Converting ... Response Code XA"
vs "...Response Code XD" vs "...Response Code 82", 3 filas de una tabla de conversion de
codigos escritas como parrafos, con un prefijo comun larguisimo). Se acepta ese riesgo
residual (~0.5-1% de los pares evaluados, medido) de la MISMA forma que el proyecto ya acepto
el 0.05% de chain-shift en el 3er manual: documentado, marcado explicitamente en el output
como `match_type="fuzzy"` con su `fuzzy_ratio` (nunca se presenta como un match confirmado),
para que Modulo 5/7 y cualquier revision humana vean el nivel de confianza real.

**Duplicados de clave (parrafos identicos repetidos dentro de la MISMA seccion, o rutas de
seccion duplicadas)**: se detectan y reportan (`duplicate_section_paths`/
`duplicate_paragraph_texts`, mismo patron que `duplicate_row_positions` en los otros
manuales) y se emparejan por ORDEN DE APARICION -mismo mecanismo ya usado para la seccion
`TC 57` del 4to manual y las claves de fila del 5to.

**Bug real encontrado y arreglado (2026-08-19), tras correr Modulo 5 y ver un
`safety_net_override` sospechosamente alto (18/124 en un par, 14.5%)**: el mismo parrafo
real puede quedar cortado DISTINTO entre 2 ediciones -una frase corta tipo "intro de lista"
(termina en `:`, antecede una lista) a veces queda FUSIONADA al parrafo anterior en una
edicion y SEPARADA en la otra- no por un cambio de contenido, sino porque el salto de pagina
cae en un lugar distinto entre ediciones (confirmado leyendo lineas crudas del Modulo 1:
"VMP accounts can be used for the following:" fluye sin corte de pagina en la edicion vieja
pero cae justo al tope de la pagina siguiente en la edicion nueva -probablemente una regla
de paginacion "keep with next" del generador de PDF de Visa para no dejar huerfana la intro
de una lista). El chequeo de "misma pagina" en Modulo 2 (deliberado, ver su docstring, evita
el bug de fusion de filas del 5to manual) es CORRECTO ahi pero tiene este efecto secundario
aca: sin el sin ningun tipo de reconciliacion, Modulo 3 fuzzy-matcheaba el parrafo fusionado
de una edicion contra la MITAD suelta de la otra, y la mitad restante (la frase intro)
aparecia como "contenido desaparecido" -activando el safety net de Modulo 5 y forzando
`business_rule_change` en algo que en realidad es ruido de re-corte, no un cambio real ni
siquiera editorial. Confirmado el mismo patron en 4/4 casos revisados en 2 pares distintos.

**Fix original (2026-08-19), a nivel de Modulo 3 (no de geometria en Modulo 2, que resulto
ser una senal poco confiable -el salto de pagina no siempre cae "cerca del margen inferior",
ver la investigacion en la memoria del asistente)**: version inicial, acotada a pares
ADYACENTES 2:1/1:2 (2 parrafos de un lado concatenados = 1 parrafo suelto del otro). Cubria
el patron real observado en los primeros 4 casos, pero dejaba sin resolver variantes N:M mas
generales (ver punto siguiente).

**Generalizado a N:M (2026-08-25), resolviendo el residuo logueado en
[[pending-bug-fixes]]/[[dev-phase-considerations]] item 13**: investigando el `safety_net_
override` de la seccion "Card Verification Value (CVV) Service" se confirmo un caso 2:2 real
que el fix 2:1 no cubria -en la edicion vieja, la oracion "Acquirers of all Visa card
products must provide..." vive pegada al final del parrafo largo de la ficha, Y una oracion
totalmente DISTINTA ("The CVV Service allows issuers to detect invalid cards...") es su
propio parrafo separado; en la edicion nueva, esas 2 oraciones se re-agrupan al reves (la
primera se separa del parrafo largo, la segunda se pega detras de ella) -A[0]+A[1]
concatenado es IDENTICO, normalizado, a B[0]+B[1] concatenado, pero ningun sub-par de 1
parrafo contra 2 (ni al reves) matchea por si solo. El diseno "solo pares adyacentes 2:1"
nunca podia encontrar este caso porque no es una simple fusion/division de 2 en 1 -es una
REDISTRIBUCION del mismo contenido entre 2 parrafos ya existentes en ambos lados.

**Rediseno de `match_paragraphs`**: en vez de emparejar por texto exacto con un dict +
buscar pares adyacentes por separado, se corre UN SOLO `difflib.SequenceMatcher` sobre las
listas de texto normalizado de parrafos de ambos lados (parrafo como unidad atomica de
comparacion, no palabra ni caracter -mismo principio que el diff a nivel de palabra que ya
usa Modulo 5 en varios manuales, aplicado aca a nivel de parrafo). Sus opcodes ya dan,
gratis, exactamente lo que se necesita:
- `"equal"`: parrafos identicos en el mismo orden relativo -reemplaza el emparejamiento
  exacto anterior (mas robusto ante duplicados intercalados que el dict+zip por orden de
  aparicion, porque el alineamiento LCS de `SequenceMatcher` ya resuelve eso).
- `"replace"` (bloque de N parrafos de un lado, M del otro): se concatena (normalizado) el
  texto de ambos bloques COMPLETOS -si son identicos, es reflow N:M puro (el caso CVV de
  arriba, y sigue cubriendo el 2:1 original como caso particular) y se emite en
  `paragraphs_reflowed` sin tocar `paragraphs_matched`; si no coinciden, los parrafos de
  ambos lados del bloque pasan al pool de fuzzy-matching de siempre (mismo comportamiento
  que antes para contenido que cambio de verdad, no una regresion).
- `"delete"`/`"insert"`: parrafos sin correspondencia directa -mismo pool de fuzzy que antes.

**Actualizacion 2026-09-13 (Bug I, ver NOTES.md)**: la "limitacion aceptada" de abajo dejo de
ser hipotetica -una revision manual del usuario encontro un caso real ("The following
parameters..." -> "These parameters...", mismo parrafo re-cortado por un salto de pagina
distinto entre ediciones, CON un cambio de wording minimo adentro). Bloque `"replace"` cuya
concatenacion normalizada NO es identica pero SI muy similar (`REFLOW_CONTENT_SIMILARITY_
THRESHOLD=0.95`, mas estricto que `FUZZY_PARAGRAPH_THRESHOLD` porque aca se fusionan 2+
parrafos completos) se reporta como UN solo `paragraph_content_changed` comparando los
bloques COMPLETOS concatenados -Modulo 5 ve la comparacion real, no el artefacto de re-corte
(1 parrafo viejo corto vs 1 parrafo nuevo mas largo, que antes daba una falsa impresion de
"contenido agregado"). Los bloques MIXTOS que NO llegan a 0.95 (cambio de contenido real y
sustancial junto con el re-corte, no solo una reescritura menor) siguen sin sub-dividirse -caen
al pool de fuzzy per-parrafo, mismo tratamiento que antes: resolver ese caso restante
necesitaria una busqueda recursiva de sub-alineamientos dentro de cada bloque, todavia no
justificada sin evidencia real de que ocurra.

Se expone en el output como `paragraphs_reflowed` (separado de `paragraphs_matched`, nunca
mezclado) para que quede visible que hubo una reconciliacion de re-corte, no una confirmacion
de "sin cambios" comun -mismo esquema de salida que la version anterior, sin cambios para
Modulo 4/5/7.

**Heuristica de "seccion movida" (agregada 2026-09-04, ver [[dev-phase-considerations]] punto
5)**: la clave de seccion es la RUTA jerarquica completa (ver arriba), asi que cuando Visa
promueve/reubica una seccion a otro padre, el path cambia entero y sale como seccion removida
+ seccion agregada, aunque el contenido interno sea el mismo -confirmado con datos reales:
`("VisaNet Systems", "Full Service Processing")` (L2, edicion vieja) -> `("Full Service
Processing",)` (L1, edicion nueva), mismo contenido con reflow menor.

**Metrica: reusa `match_paragraphs` entre la seccion removida y la agregada** (tratandolas
como si fueran "2 ediciones" de la misma seccion hipotetica) -aprovecha el mismo mecanismo ya
validado de exact+fuzzy+reflow en vez de inventar una metrica de similitud nueva. Cobertura =
(parrafos matched + parrafos de la removida reconciliados via reflow) / total parrafos de la
removida. El caso real de arriba da cobertura 0.8 (4 de 5 parrafos matchean, contando el
reflow de 2 parrafos en 1).

**Filtro de tamano (`SECTION_MOVE_MIN_SIZE_RATIO=0.5`) agregado tras medir contra el corpus
completo -sin el, la heuristica genera falsos positivos reales, no hipoteticos**: escaneando
TODAS las combinaciones removida x agregada del par mas grande (90x58=5220, ~34s), cobertura
alta sola no alcanza -varias secciones CHICAS (3-7 parrafos) tienen cobertura 0.6-1.0 contra
una seccion NUEVA GRANDE (22-75 parrafos) que en realidad es una consolidacion de VARIAS
secciones viejas distintas (ej. 4 secciones distintas de "Additional Considerations..." todas
con cobertura >=0.6 contra la MISMA seccion nueva "Considerations for Visa POS Issuers", 22
parrafos) -mostrar cualquiera de esas como "se movio a X" seria enganoso, es una fusion de
muchas-a-una, no un rename/reubicacion 1:1. El filtro de tamano (`min(n_removida,n_agregada)/
max(...) >= 0.5`) separa limpiamente ambos patrones: los 42 casos reales de reubicacion 1:1
tienen tamanos comparables (ratio 0.5-1.0, la mayoria 1.0), mientras que los casos de fusion
descartados tienen ratio 0.04-0.33. Umbral de cobertura `SECTION_MOVE_MIN_COVERAGE=0.8`
elegido porque el caso real conocido cae justo ahi (0.8) y separa limpio de los casos de
fusion multiple (que quedan en 0.15-0.75 pero con ratio de tamano bajo, ya excluidos por el
otro filtro de todas formas -ambos filtros juntos, no cualquiera solo).

**Unicidad 1:1 obligatoria**: si una seccion removida o agregada aparece en mas de 1 candidato
que pasa ambos filtros, NINGUNO de esos candidatos se reporta -no hay forma segura de saber
cual es el destino/origen real (mismo principio que la heuristica de rename del 5to manual, y
el mismo bug real que ese intento inicial tuvo: emparejar sin unicidad puede fabricar parejas
falsas). Encontrado con datos reales, no hipotetico: la seccion "Mobile Location Confirmation
Service" aparece duplicada (2 veces) tanto en removidas como en agregadas en la edicion
`20241021_to_20250414` -sin este chequeo, esos 2 pares se habrian mostrado igual (por
casualidad, en este caso serian correctos ya que es una duplicacion exacta), pero el mecanismo
de deteccion no puede distinguir ese caso benigno de uno genuinamente ambiguo, asi que se
excluyen ambos por seguridad.

Se expone en el output como `possible_section_moves` (campo nuevo, aditivo) -Modulo 3 NUNCA
fusiona `sections_removed`/`sections_added` entre si, solo agrega esta lista de candidatos
para que Modulo 4/7 decidan como mostrarla. Reporte-time hint, nunca auto-match -mismo
principio que la heuristica de rename del 5to manual y el punto 5 de
[[dev-phase-considerations]].

Alcance: procesa pares de ediciones CONSECUTIVAS (6 pares para las 7 ediciones de este
manual).
"""

import difflib
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

MANUAL_SLUG = "international_full_service_pos_online_messages_processing_specifications"
INPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "02_normalizacion_bloques"
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "03_emparejamiento_bloques"

WHITESPACE = re.compile(r"\s+")

FUZZY_SECTION_THRESHOLD = 0.85
FUZZY_PARAGRAPH_THRESHOLD = 0.90
MIN_PARAGRAPH_LEN_FOR_FUZZY = 60
# Bug I (ver NOTES.md, 2026-09-13): umbral para el caso "replace" MIXTO -reflow de
# pagina + cambio real de contenido en el mismo tramo- que la "limitacion aceptada" del
# docstring del modulo dejaba caer entero al pool de fuzzy per-parrafo (comparando 1 parrafo
# viejo corto contra 1 parrafo nuevo mas largo, mostrando una falsa impresion de "contenido
# agregado" cuando en realidad es el mismo contenido re-cortado con una reescritura minima
# adentro). Mas estricto que `FUZZY_PARAGRAPH_THRESHOLD` (0.90, calibrado para reescrituras
# genuinas de UN parrafo) porque aca se estan fusionando 2+ parrafos completos en una sola
# comparacion -confirmado con el caso real ("The following parameters..." -> "These
# parameters...", mismo parrafo re-cortado por reflow con salto de pagina distinto entre
# ediciones) que el ratio de la concatenacion normalizada da 0.989.
REFLOW_CONTENT_SIMILARITY_THRESHOLD = 0.95

SECTION_MOVE_MIN_COVERAGE = 0.8
SECTION_MOVE_MIN_SIZE_RATIO = 0.5


def _normalize_text(text: str) -> str:
    return WHITESPACE.sub(" ", text).strip().casefold()


def _find_duplicates(values) -> list:
    seen = {}
    dups = set()
    for v in values:
        seen[v] = seen.get(v, 0) + 1
        if seen[v] > 1:
            dups.add(v)
    return sorted(dups)


def extract_sections(blocks: list) -> list:
    """Reconstruye secciones por RUTA jerarquica completa (L1>L2>L3, ver docstring). Cada
    `section_heading` (de cualquier nivel) arranca una seccion nueva; los `paragraph` que
    siguen se acumulan ahi hasta el proximo `section_heading`."""
    sections = []
    current = None
    path = [None, None, None]

    for block in blocks:
        if block["type"] == "section_heading":
            if current is not None:
                sections.append(current)
            level = block["level"]
            path[level - 1] = block["text"]
            for i in range(level, 3):
                path[i] = None
            path_norm = tuple(_normalize_text(p) for p in path[:level])
            current = {
                "path": tuple(path[:level]),
                "path_norm": path_norm,
                "level": level,
                "paragraphs": [],
            }
            continue
        if current is None:
            continue
        if block["type"] == "paragraph":
            current["paragraphs"].append(
                {"text": block["text"], "text_norm": _normalize_text(block["text"])}
            )

    if current is not None:
        sections.append(current)

    for section in sections:
        section["duplicate_paragraph_texts"] = _find_duplicates(
            p["text_norm"] for p in section["paragraphs"]
        )

    return sections


def match_sections(sections_a: list, sections_b: list) -> dict:
    by_path_a = defaultdict(list)
    for s in sections_a:
        by_path_a[s["path_norm"]].append(s)
    by_path_b = defaultdict(list)
    for s in sections_b:
        by_path_b[s["path_norm"]].append(s)

    matched = []
    unmatched_a = {}
    unmatched_b = {p: list(lst) for p, lst in by_path_b.items()}

    for path_norm, list_a in by_path_a.items():
        list_b = unmatched_b.get(path_norm, [])
        n = min(len(list_a), len(list_b))
        for sec_a, sec_b in zip(list_a[:n], list_b[:n]):
            matched.append((sec_a, sec_b, "exact", 1.0))
        if list_a[n:]:
            unmatched_a.setdefault(path_norm, []).extend(list_a[n:])
        if list_b[n:]:
            unmatched_b[path_norm] = list_b[n:]
        else:
            unmatched_b.pop(path_norm, None)

    flat_unmatched_a = [(p, sec) for p, lst in unmatched_a.items() for sec in lst]
    remaining_b = [(p, sec) for p, lst in unmatched_b.items() for sec in lst]
    still_unmatched_a = []

    for path_norm_a, sec_a in flat_unmatched_a:
        text_a = " > ".join(path_norm_a)
        best_ratio = 0.0
        best_idx = None
        for idx, (path_norm_b, sec_b) in enumerate(remaining_b):
            text_b = " > ".join(path_norm_b)
            ratio = difflib.SequenceMatcher(None, text_a, text_b).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_idx = idx
        if best_idx is not None and best_ratio >= FUZZY_SECTION_THRESHOLD:
            _, sec_b = remaining_b.pop(best_idx)
            matched.append((sec_a, sec_b, "fuzzy", round(best_ratio, 3)))
        else:
            still_unmatched_a.append(sec_a)

    return {
        "matched": matched,
        "sections_removed": still_unmatched_a,
        "sections_added": [sec for _, sec in remaining_b],
    }


def match_paragraphs(section_a: dict, section_b: dict) -> dict:
    """Empareja parrafos en 2 pasadas: (1) un solo `difflib.SequenceMatcher` a nivel de
    PARRAFO (cada parrafo, ya normalizado, como unidad atomica de comparacion) separa
    parrafos identicos (`"equal"`), bloques reflow N:M cuya concatenacion coincide exacto
    (`"replace"` con concatenacion igual -ver docstring del modulo) y todo lo demas
    (`"replace"` con concatenacion distinta + `"delete"`/`"insert"`) como candidatos a
    fuzzy; (2) fuzzy con salvaguardas (longitud minima + umbral alto, ver docstring del
    modulo) sobre esos candidatos."""
    paras_a = section_a["paragraphs"]
    paras_b = section_b["paragraphs"]

    texts_a_norm = [p["text_norm"] for p in paras_a]
    texts_b_norm = [p["text_norm"] for p in paras_b]
    sm = difflib.SequenceMatcher(None, texts_a_norm, texts_b_norm, autojunk=False)

    matched = []
    reflowed = []
    fuzzy_candidates_a = []
    fuzzy_candidates_b = []

    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1):
                matched.append(
                    {
                        "text_a": paras_a[i1 + k]["text"],
                        "text_b": paras_b[j1 + k]["text"],
                        "match_type": "exact",
                        "similarity": 1.0,
                    }
                )
        elif tag == "replace":
            block_a = paras_a[i1:i2]
            block_b = paras_b[j1:j2]
            combined_a = _normalize_text(" ".join(p["text"] for p in block_a))
            combined_b = _normalize_text(" ".join(p["text"] for p in block_b))
            if combined_a == combined_b:
                reflowed.append(
                    {
                        "text_a": [p["text"] for p in block_a],
                        "text_b": [p["text"] for p in block_b],
                    }
                )
            else:
                block_ratio = difflib.SequenceMatcher(None, combined_a, combined_b).ratio()
                if block_ratio >= REFLOW_CONTENT_SIMILARITY_THRESHOLD:
                    # Bug I: reflow con cambio real de contenido en el mismo tramo -en vez
                    # de dejar que el pool de fuzzy per-parrafo empareje 1 parrafo viejo
                    # corto contra 1 parrafo nuevo mas largo (mostrando una falsa impresion
                    # de "contenido agregado"), se reporta UN solo `paragraph_content_changed`
                    # comparando los bloques COMPLETOS concatenados de cada lado -asi Modulo 5
                    # ve la comparacion real (el cambio de wording puntual), no el artefacto
                    # de re-corte.
                    matched.append(
                        {
                            "text_a": " ".join(p["text"] for p in block_a),
                            "text_b": " ".join(p["text"] for p in block_b),
                            "match_type": "fuzzy",
                            "similarity": round(block_ratio, 3),
                        }
                    )
                else:
                    fuzzy_candidates_a.extend(block_a)
                    fuzzy_candidates_b.extend(block_b)
        elif tag == "delete":
            fuzzy_candidates_a.extend(paras_a[i1:i2])
        elif tag == "insert":
            fuzzy_candidates_b.extend(paras_b[j1:j2])

    unmatched_a = fuzzy_candidates_a
    remaining_b = list(fuzzy_candidates_b)
    still_unmatched_a = []
    for pa in unmatched_a:
        if len(pa["text"]) < MIN_PARAGRAPH_LEN_FOR_FUZZY:
            still_unmatched_a.append(pa)
            continue
        best_ratio = 0.0
        best_idx = None
        for idx, pb in enumerate(remaining_b):
            if len(pb["text"]) < MIN_PARAGRAPH_LEN_FOR_FUZZY:
                continue
            ratio = difflib.SequenceMatcher(None, pa["text_norm"], pb["text_norm"]).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_idx = idx
        if best_idx is not None and best_ratio >= FUZZY_PARAGRAPH_THRESHOLD:
            pb = remaining_b.pop(best_idx)
            matched.append(
                {
                    "text_a": pa["text"],
                    "text_b": pb["text"],
                    "match_type": "fuzzy",
                    "similarity": round(best_ratio, 3),
                }
            )
        else:
            still_unmatched_a.append(pa)

    return {
        "paragraphs_matched": matched,
        "paragraphs_removed": [p["text"] for p in still_unmatched_a],
        "paragraphs_added": [p["text"] for p in remaining_b],
        "paragraphs_reflowed": reflowed,
    }


def _section_move_coverage(sec_removed: dict, sec_added: dict) -> float:
    """Fraccion de los parrafos de sec_removed que encuentran equivalente (exacto, fuzzy o
    reflow) en sec_added -reusa match_paragraphs tratando ambas secciones como si fueran '2
    ediciones' de una misma seccion hipotetica (ver docstring del modulo)."""
    n_removed = len(sec_removed["paragraphs"])
    if n_removed == 0:
        return 0.0
    result = match_paragraphs(sec_removed, sec_added)
    matched = len(result["paragraphs_matched"])
    reflowed_from_removed = sum(len(r["text_a"]) for r in result["paragraphs_reflowed"])
    return (matched + reflowed_from_removed) / n_removed


def find_possible_section_moves(sections_removed: list, sections_added: list) -> list:
    """Detecta secciones removidas cuyo contenido parece haberse REUBICADO (no editado) bajo
    una ruta distinta -ver docstring del modulo para la investigacion completa (por que hace
    falta el filtro de tamano ademas de cobertura, y por que se exige unicidad 1:1)."""
    candidates = []
    for sec_r in sections_removed:
        n_r = len(sec_r["paragraphs"])
        if n_r == 0:
            continue
        for sec_a in sections_added:
            n_a = len(sec_a["paragraphs"])
            if n_a == 0:
                continue
            size_ratio = min(n_r, n_a) / max(n_r, n_a)
            if size_ratio < SECTION_MOVE_MIN_SIZE_RATIO:
                continue
            coverage = _section_move_coverage(sec_r, sec_a)
            if coverage >= SECTION_MOVE_MIN_COVERAGE:
                candidates.append((sec_r, sec_a, coverage, size_ratio))

    removed_ids = [id(c[0]) for c in candidates]
    added_ids = [id(c[1]) for c in candidates]
    removed_counts = {i: removed_ids.count(i) for i in set(removed_ids)}
    added_counts = {i: added_ids.count(i) for i in set(added_ids)}

    moves = []
    for sec_r, sec_a, coverage, size_ratio in candidates:
        if removed_counts[id(sec_r)] > 1 or added_counts[id(sec_a)] > 1:
            continue
        moves.append(
            {
                "path_removed": sec_r["path"],
                "path_added": sec_a["path"],
                "coverage": round(coverage, 3),
                "num_paragraphs_removed": len(sec_r["paragraphs"]),
                "num_paragraphs_added": len(sec_a["paragraphs"]),
            }
        )
    return moves


def match_edition_pair(data_a: dict, data_b: dict) -> dict:
    sections_a = extract_sections(data_a["blocks"])
    sections_b = extract_sections(data_b["blocks"])

    section_match = match_sections(sections_a, sections_b)

    sections_matched = []
    for sec_a, sec_b, match_type, ratio in section_match["matched"]:
        para_match = match_paragraphs(sec_a, sec_b)
        sections_matched.append(
            {
                "path_a": sec_a["path"],
                "path_b": sec_b["path"],
                "match_type": match_type,
                "fuzzy_ratio": ratio,
                "duplicate_paragraph_texts_a": sec_a["duplicate_paragraph_texts"],
                "duplicate_paragraph_texts_b": sec_b["duplicate_paragraph_texts"],
                **para_match,
            }
        )

    duplicate_paths_a = _find_duplicates(s["path_norm"] for s in sections_a)
    duplicate_paths_b = _find_duplicates(s["path_norm"] for s in sections_b)

    possible_section_moves = find_possible_section_moves(
        section_match["sections_removed"], section_match["sections_added"]
    )

    return {
        "manual": MANUAL_SLUG,
        "edition_a": data_a["edition_date"],
        "edition_b": data_b["edition_date"],
        "num_sections_a": len(sections_a),
        "num_sections_b": len(sections_b),
        "duplicate_section_paths_a": duplicate_paths_a,
        "duplicate_section_paths_b": duplicate_paths_b,
        "sections_matched": sections_matched,
        "sections_removed": [
            {"path": s["path"], "num_paragraphs": len(s["paragraphs"])} for s in section_match["sections_removed"]
        ],
        "sections_added": [
            {"path": s["path"], "num_paragraphs": len(s["paragraphs"])} for s in section_match["sections_added"]
        ],
        "possible_section_moves": possible_section_moves,
    }


def main():
    input_paths = sorted(INPUT_DIR.glob("*.json"))
    if len(input_paths) < 2:
        print(f"Se necesitan al menos 2 ediciones en {INPUT_DIR}", file=sys.stderr)
        sys.exit(1)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for path_a, path_b in zip(input_paths, input_paths[1:]):
        data_a = json.loads(path_a.read_text())
        data_b = json.loads(path_b.read_text())
        result = match_edition_pair(data_a, data_b)

        out_name = f"{result['edition_a']}_to_{result['edition_b']}.json"
        (OUTPUT_DIR / out_name).write_text(json.dumps(result, ensure_ascii=False, indent=2))

        paras_matched = sum(len(s["paragraphs_matched"]) for s in result["sections_matched"])
        paras_added = sum(len(s["paragraphs_added"]) for s in result["sections_matched"])
        paras_removed = sum(len(s["paragraphs_removed"]) for s in result["sections_matched"])
        paras_reflowed = sum(len(s["paragraphs_reflowed"]) for s in result["sections_matched"])
        fuzzy_secs = sum(1 for s in result["sections_matched"] if s["match_type"] == "fuzzy")
        fuzzy_paras = sum(
            1 for s in result["sections_matched"] for p in s["paragraphs_matched"] if p["match_type"] == "fuzzy"
        )
        print(
            f"{out_name}: secciones {result['num_sections_a']}->{result['num_sections_b']} "
            f"(matched={len(result['sections_matched'])} [fuzzy={fuzzy_secs}], "
            f"added={len(result['sections_added'])}, removed={len(result['sections_removed'])}, "
            f"posibles reubicaciones={len(result['possible_section_moves'])}) | "
            f"parrafos matched={paras_matched} [fuzzy={fuzzy_paras}] reflowed={paras_reflowed} "
            f"added={paras_added} removed={paras_removed}"
        )


if __name__ == "__main__":
    main()
