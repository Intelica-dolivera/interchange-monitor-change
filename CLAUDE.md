# CLAUDE.md — Interchange Change Monitor

> Este archivo lo carga Claude Code automáticamente al abrir el repo. Resume todo el contexto
> necesario para continuar el proyecto, empezando por la **próxima fase: Mastercard**.
> Última actualización: 2026-09-25. Responder al usuario en **español**.

## 1. Qué es el proyecto

Sistema que compara **dos ediciones consecutivas de un manual técnico (PDF)** de una marca de
tarjetas y detecta qué cambió, para que un Data Engineer sepa si tiene que actualizar la
configuración de la plataforma de procesamiento de transacciones.

Caso de uso central (el que motiva todo el diseño): un campo `Reserved` que en la edición
siguiente pasa a tener una definición de negocio real, por ejemplo:

```
Edición N:    151-168  18  AN  Reserved
Edición N+1:  151-160  10  AN  Reserved
              161-168   8  AN  Merchant Category Code Extension
```

También: campos agregados/eliminados, cambios de longitud/formato/posición, cambios en
descripciones o valores válidos, códigos nuevos o retirados, etc.

## 2. Estado actual (fase Visa: COMPLETA)

- **8 manuales de Visa** con pipeline completo y validado de punta a punta (BASE I, BASE II x5,
  VSS x2). Todos pasaron revisión manual contra el PDF real (2026-09-12/13).
- **Router** (`poc/router/`): orquesta los 8 pipelines y aterriza PDFs nuevos detectando solo a
  qué manual pertenecen.
- **Módulo 8** (`poc/08_reporte_web_consolidado/`): página HTML única con el último par de los 8
  manuales, pestaña "Cambios recientes" y pills clicables con detalle.
- Único pendiente abierto (diferido a propósito, no bloquea): etiquetas "Note:" faltantes en una
  edición del manual 3, requiere OCR.
- **Mastercard no empezó**: la carpeta `mastercard/` está vacía (Git no la versiona, crearla al empezar). Ver sección 6.

## 3. Orden de lectura para entender todo

1. **`poc/README.md`** — cómo funciona la aplicación, escenarios de uso A-I, parámetros, flujo
   diario. Es la documentación operativa principal.
2. **`poc/router/CONTRACT.md`** — reglas autoritativas del router y del landing (y cómo agregar
   un manual nuevo).
3. **`local_memory/Claude_web_PROJECT_MEMORY.md`** — diseño original (2026-08-10): dominio,
   modelo de entidades, categorías de cambio.
4. **`local_memory/claude_code_memory/INDEX.md`** — memoria exportada de las sesiones de Claude
   Code (en inglés). Las más útiles:
   - `reference_pipeline.md` — hallazgos de extracción de PDF (**leer antes de Mastercard**).
   - `dev_phase_considerations.md` — lecciones de arquitectura.
   - `pending_bug_fixes.md` — índice de todos los bugs encontrados y su estado.
   - `feedback_*.md` — cómo prefiere trabajar el usuario.
5. **`local_memory/TODO.md`** (índice de bugs/pendientes) y **`local_memory/NOTES.md`**
   (bitácora narrativa completa por fecha, ~4200 líneas: buscar por fecha o tema, no leer
   entero).

Las notas de memoria reflejan lo que era cierto cuando se escribieron: verificar contra el código
antes de afirmar algo.

## 4. Arquitectura en 30 segundos

```
PDF viejo ┐
          ├─► 01 Ingesta ─► 02 Normalización ─► 03 Emparejamiento ─► 04 Detección ─► 05 IA ─► 07 Reporte
PDF nuevo ┘
```

- Un pipeline por manual en `poc/<slug>/NN_<etapa>/<script>.py`; salidas en
  `poc/<slug>/data/NN_<etapa>/*.json` y reportes en `poc/<slug>/data/07_reporte_cambios/*.md`.
- Etapas 01-04 y 07: determinísticas. Etapa 05: LLM local (Ollama `qwen3:4b`) solo para cambios
  de texto ambiguos, con red de seguridad determinística. Etapa 06 no existe (fuera de alcance).
- **Módulos 2 y 3 son bespoke por manual a propósito**: cada PDF tiene una estructura distinta
  (grillas posición/longitud, fichas de campo, tablas de códigos, texto narrativo, reportes de
  ancho fijo). No es deuda técnica: no intentar "unificarlos".
- Código compartido mínimo: `poc/_shared/stage_runners.py` (main de etapas 01/04) y
  `poc/_shared/ollama_client.py` (cliente LLM + `find_disappeared_content`).
- `utils_example/` = 3 scripts de referencia de OTRO equipo (Guías de Interchange, otro tipo de
  documento). Solo como inspiración, no se reutiliza 1:1.

## 5. Setup en una máquina nueva

1. **PDFs fuente (no están en git).** Los PDFs están excluidos por `.gitignore` (`*.pdf`,
   `visa/src.zip`). Pedir `src.zip` al dueño del repo y descomprimirlo **dentro de `visa/`**
   para que quede `visa/src/{base_i,base_ii,vss}/<slug>/<YYYYMMDD> - <Título>.pdf`.
2. Python 3.10+ con `pymupdf` (`pip install pymupdf`).
3. Ollama en `localhost:11434` con `ollama pull qwen3:4b` (solo para la etapa 05; sin Ollama usar
   `--skip-ai`).
4. Chequeo rápido: `python3 poc/router/run.py --list` y `python3 poc/router/run.py all --skip-ai`.
5. Reporte web: `python3 poc/08_reporte_web_consolidado/build.py` → abrir
   `poc/08_reporte_web_consolidado/data/index.html`.

## 6. PRÓXIMA FASE: Mastercard

Nada construido todavía (la carpeta `mastercard/` hay que crearla). Aún no hay PDFs de Mastercard en el repo:
**el primer paso es pedirlos al usuario** (idealmente varias ediciones fechadas por manual, para
poder comparar pares consecutivos).

### Enfoque recomendado (el mismo que funcionó con Visa)

1. **Organizar el corpus** igual que Visa: `mastercard/src/<familia>/<slug>/<YYYYMMDD> - <Título>.pdf`
   (la fecha en el nombre es la versión; es lo único que parsean `ingest.py`/`land.py`).
2. **Catalogar antes de programar.** Por cada manual, muestrear páginas reales con PyMuPDF y
   clasificar su "forma de contenido" (grilla posición/longitud, ficha de campo, tabla de
   códigos, narrativo, reporte de ancho fijo, matriz de uso por mensaje...). Comparar edición más
   vieja vs. más nueva para confirmar que la forma es estable. Así se hizo con Visa el
   2026-08-11 (ver `reference_pipeline.md` y `NOTES.md`).
3. **Herramienta de extracción:** usar texto crudo de PyMuPDF (`page.get_text("dict")` con
   página+bbox) y regex por forma de contenido. Con Visa, `pymupdf4llm` **perdió filas en
   silencio** y `pdfplumber` falló con grillas sin bordes. Docling no se justificó. Re-verificar
   con los PDFs de Mastercard, no asumirlo.
4. **Un pipeline por manual** en `poc/<slug>/`, copiando la estructura del manual de Visa más
   parecido en forma (p. ej. los de grillas: `base_ii_clearing_interchange_formats_tc_01_to_tc_49`).
   Respetar el contrato: un único `.py` por carpeta `NN_<etapa>/`, sin argumentos posicionales
   obligatorios, rutas resueltas con `Path(__file__)`.
5. **Emparejar por clave estable** (posición de bytes, número de campo/Data Element, código), no
   por nombre difuso. El fuzzy-matching debe re-validarse por manual y por nivel: con Visa fue
   seguro para títulos de sección pero peligroso para filas.
6. **Integrar al router y al reporte web:**
   - `poc/router/run.py`: agregar slug → título al dict `MANUALS`.
   - `poc/router/detect_type.py`: variantes de título en `TITLE_VARIANTS` si hace falta.
   - **Rutas hardcodeadas a Visa que habrá que generalizar:** `ingest.py` de cada manual usa
     `REPO_ROOT / "visa" / "src" / <familia>` y `poc/router/land.py` (línea ~87) busca el corpus
     con `(REPO_ROOT / "visa" / "src").glob(f"*/{slug}")`. Para Mastercard, `land.py` debe
     buscar también en `mastercard/src/`.
   - Módulo 8: un adaptador nuevo en `poc/08_reporte_web_consolidado/adapters/` que exponga
     `summarize(data, manual_dir, pair_filename)` con la forma común
     (`edition_a, edition_b, headline, secondary, groups, top_items`), con pills vía
     `_common.make_pill`.
7. **Validar con datos reales** en todas las ediciones (no solo una muestra), revisar el reporte
   generado contra el PDF y registrar hallazgos en `local_memory/TODO.md`/`NOTES.md`.

Decisión a consultar con el usuario al empezar: si Mastercard vive como manuales adicionales en
`poc/` (junto a los 8 de Visa) o en una carpeta separada por marca. El README y el router hoy
asumen una sola lista plana de manuales.

## 7. Cómo prefiere trabajar el usuario

- **Priorizar bugs por impacto en datos reales.** Pérdida de datos en tablas de campos/códigos se
  arregla ya. Problemas en prosa, glosarios o avisos legales se anotan como TODO de baja
  prioridad, salvo que el usuario diga otra cosa.
- **No descartar hallazgos diferidos.** Todo lo que se investiga y no se arregla se registra en
  `local_memory/TODO.md` (índice) y `NOTES.md` (detalle con evidencia).
- **Verificar contra el corpus completo**, no contra una muestra. Varias "soluciones" que se
  veían bien en una muestra fallaron con todas las ediciones.
- **Probar con `--skip-ai`** salvo que se esté probando la etapa 05 (Ollama es lento).
- Documentar cada sesión en `local_memory/NOTES.md` con fecha y actualizar `TODO.md` si cambia el
  estado de algo.
- Commits en español, descriptivos. **Hacer commit/push solo cuando el usuario lo pida.**

## 8. Git

- Remoto: `https://github.com/Intelica-dolivera/interchange-monitor-change` (público).
- GitHub no acepta contraseña para `git push` por HTTPS: usar un Personal Access Token o la sesión
  de GitHub de VS Code. Antes del primer push, confirmar con qué cuenta se autentica.
- **Nunca subir PDFs ni `visa/src.zip`**: son manuales licenciados de Visa y el zip supera el
  límite de 100 MB de GitHub. Lo mismo aplicará a los PDFs de Mastercard.
