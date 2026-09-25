# Interchange Change Monitor — README

Sistema que detecta y reporta cambios de negocio entre ediciones consecutivas de los manuales
técnicos de Visa/Mastercard (BASE II, VSS, BASE I). Por cada manual, un pipeline de 5-6 etapas
extrae el contenido de 2 PDFs (edición vieja + edición nueva), los compara, clasifica cada
cambio con un LLM local, y genera un reporte en Markdown. Un router orquesta los 8 pipelines,
detecta automáticamente a qué manual pertenece un PDF nuevo, y un módulo aparte consolida el
último estado de los 8 manuales en una sola página web.

---

## 1. Qué hace la aplicación

```
PDF viejo ┐
          ├─► 01 Ingesta ─► 02 Normalización ─► 03 Emparejamiento ─► 04 Detección ─► 05 IA ─► 07 Reporte
PDF nuevo ┘   (extrae      (reconstruye        (empareja filas/     (decide qué      (Ollama    (.md por
              texto crudo)  tablas/fichas)      fichas/secciones)    cambió)         clasifica)  par + index.md)
```

- **Etapas 01-04 y 07**: 100% determinísticas, sin IA, rápidas (segundos para todo el corpus).
- **Etapa 05**: la única que llama a un LLM local (Ollama), solo para clasificar los cambios de
  contenido ambiguos (¿es un cambio de negocio real, una reformulación editorial, o ruido de
  extracción del PDF?). Trae una red de seguridad determinística que corrige al LLM si detecta
  contenido real desaparecido sin reemplazo.
- **Etapa 06 no existe** (Validación con Plataforma STD) — fuera de alcance del proyecto desde
  el diseño original.

Encima de los 8 pipelines hay 2 capas:

- **`poc/router/`** — orquesta los pipelines (`run.py`) y aterriza PDFs nuevos al corpus
  detectando automáticamente a qué manual pertenecen (`land.py` + `detect_type.py`).
- **`poc/08_reporte_web_consolidado/`** — junta el último par comparado de cada uno de los 8
  manuales en una sola página HTML autocontenida (`build.py`), con una pestaña "Cambios
  recientes" que resalta qué manuales tuvieron una edición nueva desde la última vez que se
  generó el reporte. Los pills de conteo (altas, bajas, secciones, transiciones...) son
  clicables y despliegan el contenido de lo agregado/eliminado.

## 2. Los 8 manuales soportados

| Slug | Título |
|---|---|
| `base_ii_clearing_data_codes` | BASE II Clearing Data Codes |
| `base_ii_clearing_edit_package_messages` | BASE II Clearing Edit Package Messages |
| `base_ii_clearing_interchange_formats_tc_01_to_tc_49` | BASE II Clearing Interchange Formats, TC 01 to TC 49 |
| `base_ii_clearing_interchange_formats_tc_50_to_tc_92` | BASE II Clearing Interchange Formats, TC 50 to TC 92 |
| `base_ii_transactions_quick_reference` | BASE II Transactions (Quick Reference) |
| `international_full_service_pos_online_messages_processing_specifications` | Full Service POS Online Messages – Processing Specifications (International) |
| `visanet_settlement_service_vss_user_guide_volume_1_specifications` | VisaNet Settlement Service (VSS) User Guide, Volume 1, Specifications |
| `visanet_settlement_service_vss_user_guide_volume_2_reports` | VisaNet Settlement Service (VSS) User Guide, Volume 2, Reports |

`python3 poc/router/run.py --list` siempre muestra esta misma lista (es la fuente de verdad).

Cada manual tiene su propio Módulo 2 (normalización) y Módulo 3 (emparejamiento) hechos a
medida de la estructura real de su PDF (grillas, fichas, glosarios, texto narrativo) — eso es
intencional, no está pendiente de "unificar".

## 3. Requisitos previos

- **Python 3.10+**, con `pymupdf` (`fitz`) instalado.
- **Ollama corriendo en `localhost:11434`** con el modelo `qwen3:4b` descargado
  (`ollama pull qwen3:4b`) — solo hace falta para la etapa 05 (clasificación IA). El resto del
  pipeline no lo necesita.
- No hace falta git para que el pipeline funcione (aunque conviene tenerlo para tu propio
  control de versiones del código).

## 4. Escenarios de uso

### Escenario A — Aterrizar un par nuevo de un manual (caso más común)
Tenés 2 PDFs de un mismo manual (edición vieja + edición nueva) y querés incorporarlos al
corpus y generar su comparativa.
→ Poné los 2 PDFs en `poc/router/landing/inbox/` y corré `land.py` (ver paso a paso más abajo).

### Escenario B — Solo llegó una edición nueva (modo "edición única")
Ya tenés el manual en el corpus con al menos 1 edición previa, y solo te llegó la edición
nueva — no hace falta que busques la vieja a mano.
→ Poné solo 1 PDF en el inbox. `land.py` resuelve la edición vieja automáticamente contra la
más reciente que ya esté en el corpus, siempre que la fecha del PDF nuevo sea posterior.

### Escenario C — Llegaron varios manuales el mismo día
→ Poné todos los pares (o ediciones sueltas, ver Escenario B) mezclados en el mismo inbox y
corré `land.py` una sola vez — agrupa por manual detectado y corre cada pipeline por separado.

### Escenario D — La detección automática falla o es ambigua
→ Usá `--manual SLUG` para forzar el tipo de manual de todos los PDFs del inbox en esa corrida,
sin tocar código.

### Escenario E — Re-procesar un manual que ya está en el corpus (sin landing)
Por ejemplo, después de arreglar un bug en el pipeline de un manual y querer regenerar todo su
historial.
→ Corré `run.py <slug>` directo (no pasa por el inbox, usa los PDFs que ya están en
`visa/src/.../<slug>/`).

### Escenario F — Generar/actualizar el reporte web consolidado
→ Corré `build.py` (ver sección 6) después de la última corrida de `land.py`/`run.py` del día.

### Escenario G — Probar el pipeline sin gastar tiempo/cómputo de IA
→ Agregá `--skip-ai` a `run.py` o `land.py` — corre las etapas 01-04 y 07, salta la 05 (no
necesita Ollama corriendo). Los reportes no tendrán clasificación de negocio para los cambios
de contenido nuevos, pero sirve para validar que el resto del pipeline funciona.

### Escenario H — Acotar la IA a un par o una cantidad de ítems (pruebas/depuración)
→ `run.py <slug> --only 20250412_to_20251018` (un par específico) o `--limit 5` (los primeros
5 ítems). Solo aplica a la etapa 05.

### Escenario I — Un PDF no se identifica como ninguno de los 8 manuales
Comportamiento esperado, no un bug: `land.py` alerta, no mueve ni procesa nada, y dice qué
manuales candidatos consideró. Se soluciona con `--manual SLUG` (Escenario D) o, si el formato
de portada/nombre de archivo cambió de forma permanente, agregando la variante nueva a
`TITLE_VARIANTS` en `poc/router/detect_type.py` (una línea, sin tocar lógica).

## 5. Parámetros disponibles (`--help`)

### `poc/router/run.py` — orquestador

```
usage: run.py [-h] [--list] [--from NN] [--to NN] [--skip-ai] [--only PAR] [--limit N] [manual]

positional arguments:
  manual       slug de manual (ver --list) o 'all' para correr los 8 en orden

options:
  -h, --help   muestra esta ayuda
  --list       lista los 8 manuales y sale, sin correr nada
  --from NN    arranca desde la etapa NN (ej. --from 03 salta 01 y 02)
  --to NN      termina en la etapa NN (ej. --to 04 no llega al reporte)
  --skip-ai    salta la etapa 05 (no requiere Ollama corriendo)
  --only PAR   pasa el par a la etapa 05 unicamente (ej. --only 20250412_to_20251018)
  --limit N    pasa el límite de ítems a la etapa 05 únicamente
```

Ejemplos:
```bash
python3 poc/router/run.py --list
python3 poc/router/run.py base_ii_clearing_data_codes
python3 poc/router/run.py all --skip-ai
python3 poc/router/run.py base_ii_clearing_data_codes --only 20250412_to_20251018
python3 poc/router/run.py base_ii_clearing_data_codes --from 03 --to 04
```

### `poc/router/land.py` — aterrizaje de PDFs nuevos

```
usage: land.py [-h] [--manual MANUAL] [--skip-ai] [inbox]

positional arguments:
  inbox            carpeta con uno o más PDFs (default: poc/router/landing/inbox)

options:
  -h, --help       muestra esta ayuda
  --manual MANUAL  fuerza el mismo slug para TODOS los PDFs del inbox, salta la detección automática
  --skip-ai        salta la etapa 05 para todos los manuales del lote
```

Ejemplos:
```bash
python3 poc/router/land.py                              # usa el inbox por defecto
python3 poc/router/land.py /ruta/a/otra/carpeta
python3 poc/router/land.py --manual base_ii_clearing_data_codes
python3 poc/router/land.py --skip-ai
```

### `poc/08_reporte_web_consolidado/build.py` — reporte web

Sin parámetros — siempre toma el último par ya comparado de cada uno de los 8 manuales:
```bash
python3 poc/08_reporte_web_consolidado/build.py
```

### Convención de nombre de archivo (obligatoria para `land.py`)

```
YYYYMMDD - <lo que sea>.pdf
```
La fecha (8 dígitos) es la única parte que `land.py`/`ingest.py` necesitan parsear — el resto
del nombre no importa para la detección (se usa el contenido de portada como respaldo).

## 6. Paso a paso — flujo operacional del día a día

1. **Juntar los PDFs del día.** Uno o más pares (o ediciones sueltas, ver Escenario B) de
   cualquiera de los 8 manuales, nombrados `YYYYMMDD - Título.pdf`.
2. **Copiarlos todos juntos a `poc/router/landing/inbox/`** (se pueden mezclar manuales
   distintos sin problema).
3. **Correr `python3 poc/router/land.py`** (con Ollama corriendo, sin `--skip-ai`, salvo que
   sea una prueba). Esto:
   - detecta a qué manual pertenece cada PDF,
   - agrupa y valida cada grupo (todo-o-nada sobre el lote completo — si un grupo está mal
     formado, no se mueve ni procesa nada de ningún grupo),
   - mueve los PDFs válidos al corpus permanente (`visa/src/<familia>/<slug>/`),
   - corre el pipeline completo (01→07) de cada manual afectado, acotando la IA solo al par
     recién llegado.
4. **Revisar la salida en consola** — por cada manual, indica dónde quedó el reporte de ese
   par (`poc/<slug>/data/07_reporte_cambios/<viejo>_to_<nuevo>.md`) o, si había ediciones
   intermedias en el corpus, la cadena real de reportes generados.
5. **Si el inbox tenía algo mal formado**, corregir según lo que diga el archivo de alerta en
   `poc/router/landing/alertas/<timestamp>_rechazado.txt`, y volver a correr `land.py`.
6. **Repetir 1-5** cada vez que lleguen más manuales nuevos ese mismo día.
7. **Al final del día** (cuando ya no van a llegar más manuales), correr una sola vez
   `python3 poc/08_reporte_web_consolidado/build.py` para refrescar el reporte web
   (`poc/08_reporte_web_consolidado/data/index.html`) — muestra los 8 manuales con su último
   par, más la pestaña "Cambios recientes" con los que cambiaron desde la última vez que se
   generó esta página.

## 7. Dónde queda cada cosa

- **Corpus de PDFs**: `visa/src/<familia>/<slug>/<fecha> - <Título>.pdf` (familia = `base_i`,
  `base_ii` o `vss`, resuelta automáticamente por `land.py`, no hace falta saberla de memoria).
- **Salida intermedia de cada etapa**: `poc/<slug>/data/<NN>_<etapa>/*.json` (un archivo por
  edición en la etapa 01, uno por par en las etapas 02-05).
- **Reportes en Markdown**: `poc/<slug>/data/07_reporte_cambios/<viejo>_to_<nuevo>.md` +
  `index.md` (índice de todos los pares del manual).
- **Reporte web consolidado**: `poc/08_reporte_web_consolidado/data/index.html` (autocontenido,
  se abre con doble clic, no necesita servidor) + `reporte_consolidado.json`.
- **Estado de la última publicación web**: `poc/08_reporte_web_consolidado/data/estado_publicacion/<slug>.json`
  (un archivo por manual — lo usa `build.py` para saber qué manuales mostrar en "Cambios
  recientes"). Se puede borrar el archivo de un solo manual para forzar que aparezca como
  "nuevo" en la próxima corrida (útil para probar el flujo de punta a punta) sin afectar el
  estado de los otros 7. Compatible con el formato viejo de un único `estado_publicacion.json`
  compartido (se migra solo a la carpeta por manual la primera vez que corre `build.py` con
  esta versión).
- **Alertas de landing rechazado**: `poc/router/landing/alertas/*.txt`.
- **Documentación técnica completa del contrato del router**: `poc/router/CONTRACT.md` — es la
  referencia autoritativa y más detallada que este README para todo lo relacionado a
  `run.py`/`land.py`.

## 8. Puntos importantes a tener en cuenta

- **`land.py` es todo-o-nada sobre el lote completo.** Si tirás 3 pares y 1 está mal formado
  (PDFs sin fecha, manual no identificado, edición duplicada con contenido distinto), **no se
  mueve ni procesa nada de ningún par**, ni siquiera los que estaban bien. Es una decisión de
  diseño explícita (consistencia con el resto del pipeline), no un límite técnico.
- **El modo "edición única" necesita al menos 1 edición previa en el corpus.** La primera carga
  de un manual nuevo siempre necesita el par completo (2 PDFs).
- **`build.py` no es incremental** — siempre reconstruye el consolidado desde cero leyendo el
  último par de los 8 manuales. Por eso se recomienda correrlo una sola vez al final del día,
  no después de cada `land.py`.
- **La etapa 05 (IA) es la única que necesita Ollama corriendo.** Si Ollama no está disponible,
  usá `--skip-ai` — el resto del pipeline (extracción, matching, detección, reporte estructural)
  funciona igual, solo faltará la clasificación de negocio para los cambios de contenido.
- **El esquema interno de cada manual es bespoke a propósito** — no es deuda técnica pendiente.
  Cada manual tiene una estructura de PDF genuinamente distinta (grillas de posición/longitud,
  fichas de campo, glosarios, texto narrativo), y forzar un esquema único sería más frágil que
  mantener 8 parsers especializados.
- **No hay modo de "deshacer" un landing.** Los PDFs se *mueven* (no se copian) al corpus. Si
  aterrizaste algo por error, hay que corregirlo a mano (mover el PDF de vuelta, borrar los
  `.json`/`.md` generados para ese par).
- **Agregar un 9° manual no requiere tocar el router.** Solo necesita seguir la convención de
  carpetas (`poc/<slug>/NN_<etapa>/`, un único `.py` por etapa, sin argumentos posicionales
  obligatorios) y agregar su slug/título a `run.py` y sus variantes de título a
  `detect_type.py`. El detalle completo está en `CONTRACT.md`.
