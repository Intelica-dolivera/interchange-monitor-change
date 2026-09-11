# Contrato de interfaz entre etapas (poc/router)

Este router (`run.py`) orquesta los pipelines bespoke de cada manual, pero no conoce nada de
su lógica interna (esquema de los JSON, reglas de matching, prompts de IA, etc). Solo conoce
la forma en que cada etapa se invoca y se encadena. Esa forma es hoy un contrato *de facto*
que los 8 manuales ya cumplen sin haber sido diseñado a propósito — este documento lo deja
explícito para que:

- Un manual nuevo (9°, 10°...) sepa qué debe cumplir para ser router-compatible sin tener que
  inferirlo leyendo los 8 pipelines existentes.
- Quede claro qué SÍ es parte del contrato (y por lo tanto no se puede romper sin avisar al
  router) y qué NO lo es (y por lo tanto puede seguir siendo bespoke por manual sin problema).

## Qué exige el contrato

1. **Estructura de carpetas**: `poc/<manual_slug>/NN_<nombre>/` — una carpeta por etapa, con
   prefijo numérico de 2 dígitos. El router descubre las etapas de un manual con un glob
   (`poc/<slug>/[0-9][0-9]_*/`), en orden ascendente por nombre de carpeta. Hoy siempre son
   `01, 02, 03, 04, 05, 07` (`06` no existe en ningún manual, está fuera de alcance del
   proyecto — Validación con Plataforma STD).
2. **Un solo entry-point por etapa**: cada carpeta `NN_*/` tiene exactamente un archivo `*.py`
   (aparte de `__pycache__/`). El router lo descubre por glob, no lo hardcodea por nombre — así
   que `ingest.py`, `normalize.py`, `match.py`, etc. pueden llamarse como quieran, siempre que
   sean el único `.py` de su carpeta.
3. **Invocación sin argumentos posicionales**: cada script corre como
   `python3 <script>.py` y hace su trabajo completo (todas las ediciones/pares disponibles) sin
   necesitar flags. Hoy solo `05_interpretacion_cambios_ia` acepta flags **opcionales**
   (`--limit=N`, `--only=<par>`) — el router los reenvía únicamente a esa etapa, no es un
   passthrough ciego. Una etapa nueva puede agregar sus propios flags opcionales sin romper el
   contrato, siempre que funcione igual sin ellos.
4. **Rutas independientes del CWD**: cada script resuelve sus directorios de entrada/salida vía
   `Path(__file__).resolve()...`, nunca asumiendo que se ejecuta desde una carpeta específica.
   Esto es lo que permite al router invocar los scripts por ruta absoluta desde cualquier lado.
5. **Convención de entrada/salida por etapa**:
   - Etapa `01`: lee PDFs de `visa/src/.../<manual_slug>/`, escribe un `.json` por edición en
     `data/01_.../`.
   - Etapas `02`–`05`: leen los `.json` de `data/<etapa anterior>/`, escriben `.json` (incluso
     con el mismo nombre de archivo en la mayoría de los casos) en `data/<esta etapa>/`.
   - Etapa `07`: lee de `data/05_.../`, escribe un `.md` por par en `data/07_.../` + un
     `index.md`.
6. **Exit code + progreso en stdout/stderr**: éxito = exit code 0, con una línea de progreso
   por ítem procesado en stdout. Falla = exit code distinto de cero, con el motivo en stderr
   (ej. `classify.py` valida que Ollama esté corriendo antes de arrancar y aborta con un
   mensaje claro si no). El router corta la cadena de ese manual en la primera etapa que falle.

## Landing (`land.py` + `detect_type.py`): incorporación de un par nuevo al corpus

Además de orquestar manuales ya presentes en el corpus, el router tiene una puerta de entrada
para incorporar un par de ediciones nuevo (`poc/router/landing/inbox/` → `land.py`). Esta capa
NO forma parte del contrato de las etapas 01-07 de arriba — es un paso previo, específico del
router, que decide a qué manual pertenece un PDF y si corresponde correr su pipeline.

**Flujo**: el inbox puede tener uno o más pares mezclados de manuales distintos (agregado
2026-09-06, ver más abajo). `land.py`:
1. Valida que cada nombre de archivo siga `YYYYMMDD - <lo que sea>.pdf` (misma convención que ya
   usa `ingest.py` para extraer `edition_date`, ver punto 5 arriba).
2. Detecta a qué uno de los 8 manuales conocidos pertenece CADA PDF (`detect_type.py`), salvo
   que se fuerce con `--manual SLUG` (fuerza el MISMO slug para todos los PDFs del inbox —
   pensado para el caso de 1 solo par).
3. Agrupa los PDFs por slug detectado. Cada grupo debe tener **1 o 2 PDFs**:
   - **2 PDFs con 2 fechas distintas** (modo clásico, par completo) — sigue firme, ahora
     aplicado por grupo en vez de al inbox entero.
   - **1 PDF solo** (modo "edición única", agregado 2026-09-05): la edición vieja se resuelve
     automáticamente contra la más reciente YA presente en el corpus para ese manual
     (`_latest_corpus_edition`, misma convención de nombre `<fecha> - <título>.pdf` que ya usa
     el corpus). Requiere que el corpus tenga al menos 1 edición previa de ese manual (la
     primera carga siempre necesita el par completo) y que la fecha del PDF sea estrictamente
     posterior a esa edición — si no, se rechaza como cualquier otro problema del lote.
   - Cualquier otro tamaño de grupo (0, 3+) se rechaza.
4. **Todo o nada sobre el LOTE completo, no por grupo**: si cualquier PDF no se identifica, o
   cualquier grupo no forma un par válido bajo ninguno de los 2 modos de arriba, o cualquier
   edición ya existe en el corpus con contenido DISTINTO — no se mueve ni procesa NADA de ningún
   grupo, ni siquiera los que sí estaban bien formados. Solo alerta — mensaje en consola + exit
   code ≠0 + archivo persistente en `poc/router/landing/alertas/<timestamp>_rechazado.txt`,
   listando cuál(es) grupo(s) tuvo el problema — y deja TODOS los PDFs intactos en el inbox para
   que se corrijan a mano. Un lote puede mezclar libremente grupos en modo par y en modo
   edición-única para manuales distintos — cada grupo se valida y resuelve de forma
   independiente.
5. Si todo valida: mueve TODOS los PDFs de TODOS los grupos a sus carpetas de corpus
   respectivas (`visa/src/<familia>/<slug>/`, resuelta por glob por cada slug — no hardcodeada)
   con el nombre normalizado `<edition_date> - <MANUAL_TITLE>.pdf`, y corre el pipeline completo
   de CADA manual afectado (uno por uno, reusando `run_manual()` de `run.py`, sin duplicar
   lógica de orquestación). Si el pipeline de un manual falla, NO detiene el procesamiento de
   los demás manuales del lote (mismo criterio que `run.py all`) — los PDFs de todos ya quedaron
   incorporados al corpus de todas formas, solo se reporta el fallo puntual al final.

**Etapa 05 (IA) se acota al par aterrizado de CADA manual, no se re-clasifican los pares
históricos** (con varios manuales en el mismo lote, esto aplica independientemente a cada uno —
cada `run_manual()` recibe el `only` de SU propio par, no el de otros manuales del lote): al
llamar a `run_manual()`, `land.py` pasa `only=f"{fecha_vieja}_to_{fecha_nueva}"` (el mismo
`--only` de la sección "Qué exige el contrato" arriba). Las etapas 01-04 (deterministas, sin
IA, rápidas) igual corren sobre el corpus completo cada vez — no tienen modo incremental, y no
hace falta que lo tengan porque no llaman a Ollama. La etapa 07 tampoco filtra: regenera el
`.md` de todos los pares para los que exista `.json` de la etapa 05, pero como esos otros
`.json` no fueron tocados, sus reportes salen idénticos. El costo real (llamadas a Ollama) queda
acotado al par que efectivamente llegó nuevo.

**Cómo detecta el tipo (`detect_type.py`)**: compara el nombre de archivo (y, si eso no alcanza,
el texto de las primeras páginas del PDF) contra `TITLE_VARIANTS` — una lista de títulos
aceptados por manual (arranca con 1 sola variante, el `MANUAL_TITLE` de cada `report.py`) — por
**contención de subconjunto de palabras normalizadas**, no igualdad exacta ni substring
ordenado. Esto importa porque, validado contra PDFs reales, ni el nombre de archivo ni el texto
de portada preservan siempre el orden/puntuación exacta del título registrado (ej. una edición
real trae "International" al principio del nombre de archivo aunque el título registrado lo
tiene al final). La contención de subconjunto tolera eso sin perder precisión entre los pares de
títulos casi-idénticos del corpus (TC 01-49 vs TC 50-92, VSS Volumen 1 vs Volumen 2), porque
exige que **todos** los tokens distintivos del título estén presentes.

**Qué pasa si una edición futura no se reconoce** (portada rediseñada, nombre de archivo
atípico): cae a "no identificado" — alerta, no procesa nada, comportamiento correcto y esperado,
no un bug. La corrección no es tocar el router ni ningún pipeline: `--manual SLUG` desbloquea al
toque sin código, y si el cambio de formato se vuelve la norma, agregar esa variante de título a
la entrada del manual en `TITLE_VARIANTS` (un string a una lista) la cubre para siempre. El mismo
mecanismo cubre agregar un 9° manual: slug + variante(s) de título nuevas, sin tocar lógica.

## Flujo operacional recomendado: varios manuales nuevos el mismo día + reporte web

**Actualizado 2026-09-06**: `land.py` ya soporta varios pares mezclados en el mismo inbox en
una sola corrida (ver "Flujo" arriba) — se puede dejar el par del manual A y el par del manual
B juntos, y el router los agrupa, valida y procesa a cada uno con su propio pipeline. Sigue
existiendo la restricción de "exactamente 2 PDFs por grupo/manual", ahora aplicada por grupo,
y sigue siendo todo-o-nada sobre el lote completo (ver arriba) — si un solo grupo del lote está
mal formado, no se procesa nada de ningún grupo, ni siquiera los que estaban bien.

El flujo real, con varios manuales nuevos el mismo día:

1. Poner en el inbox los pares (vieja + nueva edición) de TODOS los manuales que llegaron ese
   día, mezclados sin problema → correr `python3 poc/router/land.py` una sola vez → corre el
   pipeline completo de CADA manual detectado hasta el reporte de cambios (etapa 07).
2. **Recién cuando ya no hay más manuales nuevos por aterrizar ese día**, correr una sola vez
   `python3 poc/08_reporte_web_consolidado/build.py` para refrescar el reporte web consolidado
   (`poc/08_reporte_web_consolidado/data/index.html`), que agrega el último par ya procesado de
   cada uno de los 8 manuales.

Si en cambio los manuales van llegando en momentos distintos del día (no todos disponibles de
una), sigue siendo válido aterrizarlos de a uno por separado (poner el par, correr `land.py`,
vaciar el inbox, repetir) — el flujo de un solo par sigue funcionando igual que antes, es
simplemente el caso particular de un lote con 1 solo grupo.

**Por qué `build.py` no se dispara automáticamente al final de cada `land.py` exitoso**:
`build.py` no tiene modo incremental — siempre reconstruye el consolidado leyendo el último par
de los 8 manuales desde cero (barato, sin IA, pero igual redundante). Correrlo una sola vez al
final del día (después del último `land.py` del día, sea de 1 o varios manuales a la vez) evita
reconstrucciones redundantes. Esto es una decisión operacional, no una limitación técnica: nada
impide llamarlo más seguido si en algún momento hiciera falta ver el consolidado actualizado
entre aterrizajes del mismo día.

## Qué NO es parte del contrato (sigue siendo bespoke, a propósito)

- El esquema interno de cada `.json` intermedio — cada manual tiene su propio Módulo 2/3/4
  diseñado desde los datos reales de ese manual (grillas, fichas, glosarios, etc.), y así debe
  seguir. El router nunca abre ni interpreta estos archivos, solo los deja pasar de una etapa a
  la siguiente.
- **Actualizado 2026-09-04**: el cliente de Ollama YA NO está duplicado — ver
  `poc/_shared/ollama_client.py` abajo. Lo que sigue bespoke a propósito: utilidades de bajo
  nivel de extracción (`_split_line_segments` y similares, hoy copiadas a mano entre manuales
  cuando aparece el mismo bug), la capa de reporte (cada manual tiene su propio `report.py`, más
  el Módulo 8 web con adaptadores bespoke), y `main()` de cada `classify.py` (diverge
  estructuralmente entre manuales — manejo de `--limit`, lookups adicionales como
  `field_name_lookup`, el set de `change_type` filtrado por manual — no es Tier 1).

## `poc/_shared/`: código 100%-duplicado extraído (no reemplaza nada bespoke)

Directorio hermano de `poc/router/` y de cada `poc/<slug>/`, con la lógica que un inventario de
duplicación (2026-09-03, re-verificado contra el código real 2026-09-04) confirmó byte-idéntica
entre manuales — nunca el Módulo 2/3 de cada uno, que sigue 100% bespoke.

- **`stage_runners.py`**: `run_ingest_main()` y `run_detect_main()`, el cuerpo de `main()` de
  las etapas 01 y 04 en 7 de los 8 manuales (todos menos
  `visanet_settlement_service_vss_user_guide_volume_2_reports`, que tiene su propio schema de
  resultado por apéndice y sigue con `main()` bespoke). Cada `ingest.py`/`detect.py` de esos 7
  queda en un `main()` de una sola línea que delega, pasando su `extract_pdf_lines`/
  `detect_changes` propios — la lógica de extracción/detección de cada manual no se tocó.
- **`ollama_client.py`**: `ollama_classify()` (payload/request/parsing/fallback de categoría
  inválida), `ensure_ollama_running()` (chequeo de conectividad) y `find_disappeared_content()`
  (la red de seguridad determinística de la etapa 05), usados por los 7 manuales con IA
  (`base_ii_transactions_quick_reference` es 100% determinístico, sin IA, no lo importa). Cada
  `classify.py` sigue armando su propio prompt (`PROMPT_TEMPLATE` + argumentos distintos por
  manual) — eso sigue bespoke.
  **Fix incluido en esta consolidación**: `find_disappeared_content()` cuenta operaciones
  `tag in ("delete", "replace")`, no solo `"delete"`. Verificado contra el código real el
  2026-09-04 que 5 de los 7 manuales con IA (`..._tc_01_to_tc_49`, `..._tc_50_to_tc_92`,
  `international_full_service_pos...`, `visanet...volume_1`, `visanet...volume_2`) NO tenían
  este fix pese a que la memoria del proyecto afirmaba (incorrectamente) que ya estaba portado a
  todos desde 2026-09-03 — solo `base_ii_clearing_data_codes` y
  `base_ii_clearing_edit_package_messages` lo tenían de verdad. Medido contra el corpus real
  antes de tocar código: 14 casos concretos que pasan de "editorial_reword" (sin cambio real) a
  "business_rule_change" forzado bajo la lógica corregida — ver [[dev-phase-considerations]]
  punto 4 para el detalle completo.
- **Import**: cada script agrega `sys.path.insert(0, str(Path(__file__).resolve().parents[2] /
  "_shared"))` antes de importar — sigue cumpliendo el punto 4 del contrato de arriba (rutas
  resueltas vía `Path(__file__)`, nunca CWD).
- El Módulo 8 (`poc/08_reporte_web_consolidado/`) no es una etapa de manual — es una agregación
  cross-manual sobre las salidas de la etapa 07 de los 8 pipelines. Se invoca por separado
  (`python3 poc/08_reporte_web_consolidado/build.py`), no forma parte de la cadena por-manual
  del router.
