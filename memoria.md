# Memoria del proyecto

> Archivo local de contexto para agentes de AI. No debe versionarse ni subirse al repositorio.
> Última actualización: 2026-10-11.

## Estado actual

- Repositorio: `MSA_gage_handy_tool`.
- Rama activa al documentar: `Repo-sort-priv` (implementación del plan de modernización arquitectónica).
- Progreso del plan (revalidado 2026-10-11): Fases 2–5 completadas; estructura de Fase 1 completada salvo dos documentos de UI/UX cuyas fuentes no están disponibles.
- Progreso general: flujos de implementación terminados; no se recrearon las dos especificaciones ausentes.
- Entorno Python: `.venv`, Python 3.13, paquetes principales pandas, numpy, scipy, matplotlib, streamlit y watchdog.
- Punto de entrada principal de UI: `MSA_app.py`, que carga `app.main`; el archivo anterior `streamlit_app.py` fue renombrado y eliminado.

## Progreso del Plan Arquitectónico

### Fase 1: Datos, Privacidad y Limpieza de Raíz ⚠️ MAYORMENTE COMPLETADA
- ✅ Estructura de datos unificada creada:
  - `data/examples/gage_rr/`, `data/examples/paired/`, `data/examples/type1/`
  - `data/private/` para datos confidenciales
  - `outputs/gage_rr/`, `outputs/paired/`, `outputs/type1/`
- ✅ Documentación reubicada:
  - `docs/references/minitab/`
  - `docs/specifications/`
  - `docs/workflows/`
- ✅ Raíz limpia sin carpetas de datos ni archivos HTML sueltos
- ✅ `.gitignore` actualizado protegiendo `data/private/*` y `outputs/*/*`
- ✅ Scripts CLI actualizados con rutas nuevas
- ✅ Salidas paired heredadas removidas del índice; los archivos locales se conservaron y siguen ignorados.
- ⚠️ Las especificaciones `1_resumen_ejecutivo_ui_ux.md` y `2_especificaci_n_t_cnica_css.md` no están presentes en el repositorio ni en `docs/specifications/`; no hay fuentes disponibles para reubicarlas.

### Fase 2: Empaquetado PEP 517/621 ✅ COMPLETADA
- ✅ Creado `pyproject.toml` con metadatos del proyecto
- ✅ Dependencias formales basadas en `requirements.txt`
- ✅ Configurado `package-dir = {"": "src"}`
- ✅ `pip install --no-deps -e .` funciona en `.venv`; `gage_tracer` y `app` importan desde fuera del repositorio.
- ✅ Los entry points `msa-app`, `msa-type1`, `msa-paired` y `msa-grr` se cargan desde fuera del repositorio.
- ✅ Los puntos de entrada principales ya no modifican `sys.path`.
- ℹ️ Los tres comandos analíticos heredados se conservan como compatibilidad con la CLI `msa`.

### Fase 3: Saneamiento de Pruebas ✅ COMPLETADA
- ✅ Scripts obsoletos eliminados:
  - `test_calculations.py` - eliminado (fallaba buscando archivos locales)
  - `test_tolerances.py` - eliminado (fallaba buscando archivos locales)
- ✅ `_runtests.py` eliminado; las pruebas se ejecutan mediante unittest discovery.
- ✅ `tests/fixtures/` creado y conectado a las pruebas:
  - `type1_sample_data.txt`
  - `paired_sample_a.txt`, `paired_sample_b.txt`
  - `gage_rr_sample.txt`
- ✅ Los tests paired y Gage R&R ahora son `unittest.TestCase` y se descubren automáticamente.
- ✅ `python -m unittest discover -s tests -p "test_*.py"` pasa con 38 tests.

### Fase 4: Modularización de UI ✅ COMPLETADA
- ✅ Aplicación reorganizada como paquete `src/app/`.
- ✅ `main.py` es un orquestador de 20 líneas (<100).
- ✅ Vistas aisladas en `views/type1_view.py`, `views/paired_view.py` y `views/grr_view.py`.
- ✅ Componentes compartidos en `components/sidebar.py`, `file_pills.py` y `alerts.py`.
- ✅ Tema extraído a `theme.py` y `assets/styles.css`, empaquetado como recurso.
- ✅ Streamlit inicia por `MSA_app.py`; ya no existe el antiguo archivo `streamlit_app.py`.

### Fase 5: Unificación CLI ✅ COMPLETADA
- ✅ `msa` ofrece los subcomandos `type1`, `grr` y `paired`.
- ✅ Los tres flujos aceptan rutas explícitas de entrada y salida; los ejemplos y `outputs/` son los defaults.
- ✅ Gage R&R conserva `--input-format` y `--report-order`.
- ✅ `python -m cli` y el entry point instalado `msa` funcionan; los scripts heredados se conservan por compatibilidad.
- ✅ Validación end-to-end de Type 1, Paired simple/multicaracterística y Gage R&R con outputs temporales.

## Cambios Recientes (2026-10-11)

### Empaquetado Formal (Fase 2)
- Creado `pyproject.toml` con configuración PEP 517/621
- Configurados metadatos del proyecto: nombre, versión, autores, licencia
- Dependencias formales declaradas basadas en `requirements.txt`
- Build system configurado con setuptools y `package-dir = {"": "src"}`
- Entry points de CLI configurados: `msa-type1`, `msa-paired`, `msa-grr`
- `pip install -e .` funciona correctamente, paquete instalado como `msa-gage-handy-tool==0.1.0`

### Limpieza de Suite de Pruebas (Fase 3)
- Eliminados `test_calculations.py` y `test_tolerances.py` (scripts de inspección, no tests unitarios)
- Actualizado `_runtests.py` para usar rutas dinámicas en lugar de rutas absolutas locales
- Creado directorio `tests/fixtures/` con datos sintéticos para pruebas independientes del sistema de archivos
- Arreglado `test_gage_rr_minitab_structure.py` con imports correctos usando sys.path dinámico
- Suite de pruebas ahora funcional: 35/35 tests pasando en `python -m unittest discover -s tests`

### Estructura de Fixtures de Pruebas
- `tests/fixtures/type1_sample_data.txt` - datos sintéticos Type 1
- `tests/fixtures/paired_sample_a.txt` - datos sintéticos Paired T-Test System A
- `tests/fixtures/paired_sample_b.txt` - datos sintéticos Paired T-Test System B
- `tests/fixtures/gage_rr_sample.txt` - datos sintéticos Gage R&R con bloques BEGIN/END

## Próximos Pasos Prioritarios

**Pendiente externo:** Obtener las fuentes originales `1_resumen_ejecutivo_ui_ux.md` y `2_especificaci_n_t_cnica_css.md` si aún deben incorporarse. No recrear su contenido sin las fuentes.

## Arquitectura

- `src/gage_tracer/data_parser.py`
  - Parser Type 1 y Gage R&R.
  - Type 1 mantiene comportamiento independiente; no mezclar cambios GRR sin validar Type 1.
  - Gage R&R soporta dos layouts:
    1. 90 bloques explícitos `BEGIN/END` o `:BEGIN/:END`.
    2. Un bloque o flujo continuo con 90 mediciones de una dimensión y tags `C20_A001...C20_A010`.
  - Streamlit también acepta layouts GRR agrupados: 10 archivos por pieza o 3 por operador; se normalizan a los mismos factores.
  - Type 1 ofrece formatos con bloques y reportes periódicos sin marcadores.
  - Los headers y footers son ignorados en filas no válidas.
  - El diseño GRR está fijo: 10 partes × 3 operadores × 3 repeticiones = 90 reportes.
  - Para reportes sin tags de parte, `report_order` define el mapeo secuencial: `part-major` (default, Parte → Operador → Ensayo) u `operator-major` (Operador → Parte → Ensayo).
  - Reparación de entradas fusionadas: separa `END"":BEGIN` en dos marcadores y elimina el prefijo ASCII `0x1A` antes de `:BEGIN`.

- `src/gage_tracer/calculations.py`
  - Funciones estadísticas puras.
  - Type 1 calcula Cg, Cgk, bias, t-test y %Var.
  - Gage R&R Crossed calcula ANOVA, componentes de varianza, %Contribution, %StudyVar, %Tolerance y NDC.
  - Cuando `Part × Operator` tiene p > 0.05, se agrupa con Error.
  - Hay dos tablas ANOVA:
    - `anova_table_with_interaction`
    - `anova_table` (final, con o sin interacción según pooling)

- `src/gage_tracer/study_config.py`
  - Reglas de dominio centralizadas:
    - `GRR_DESIGN`
    - `TYPE1_CAPABILITY_THRESHOLD = 1.33`
    - `GRR_MINIMUM_NDC = 5`
    - `classify_gage_rr`

- `src/gage_tracer/presentation.py`
  - Adaptadores puros para presentación de resultados.
  - Formatea tablas Type 1 y Paired T-Test sin depender de Streamlit.

- `src/gage_tracer/visualization.py`
  - Dashboards HTML y matplotlib.
  - Gage R&R genera seis paneles:
    1. Components of Variation
    2. Measurement by Part
    3. R Chart by Operator
    4. Measurement by Operator
    5. Xbar Chart by Operator
    6. Part × Operator Interaction
  - El boxplot usa `positions` + `set_xticks` por compatibilidad de matplotlib; no volver a usar `labels=`.
  - `create_gage_rr_html_zip` crea un ZIP con un HTML independiente por característica y nombres de archivo seguros.

- `src/gage_tracer/paired_ttest.py`
  - Paired T acepta archivos numéricos, bloques multi-característica y texto no estructurado de una medición por línea.
  - El modo no estructurado rechaza líneas ambiguas y muestra en la vista previa las líneas fuente de cada par.
  - `_read_text_lines` elimina un BOM UTF-8 inicial; necesario para `PAIRED DATA SYSTEM A.txt`.
  - Cálculo de paired t-test, IC 95%, dashboard.
  - Diagnósticos Minitab-like: normalidad, outliers > 3σ, tamaño de muestra y potencia/diferencias detectables.
  - Exportación HTML con Summary Report, Diagnostic Report y Report Card.
  - Los parsers numérico y no estructurado rechazan texto no clasificado entre mediciones en lugar de desplazar pares silenciosamente.

- `src/gage_tracer/paired_visualization.py`
  - Gráficos Paired T alineados con Minitab Assistant.
  - Gauge de p-value, tablas de estadísticas, histograma con IC, worksheet order,
    slopegraph, run chart y power/detectable difference.
  - Usa paleta dark compartida: fondo carbón, texto claro, naranja `#FF8C00`,
    azul visible para System B, verde y rojo semánticos.

- `src/app/`
  - `main.py` orquesta Streamlit; `views/` contiene un flujo por estudio.
  - `components/` comparte navegación, file pills y alertas.
  - `theme.py` carga los estilos del recurso `assets/styles.css`.
  - Sistema de Design Tokens en `:root` para Dark Mode (`--bg-main: #121212`, `--bg-sidebar: #1E1E1E`, `--surface-card: #2D2D2D`, `--brand-orange: #F58220`, `--text-primary: #F9FAFB`, `--border-color: #3F3F46`, etc.) y Light Mode dinámico.
  - Navegación lateral en el Sidebar:
    - Estado activo diferenciado (`type="primary"`, fondo `--brand-orange` y tipografía `#121212` con cumplimiento WCAG AAA).
    - Estados inactivos (`type="secondary"`, fondo transparente, borde neutro de 1px y hover sutil).
    - Alineación izquierda (`justify-content: flex-start`).
    - Tipografía refinada `Study Selection` en Title Case (`1.15rem`, `font-weight: 600`, stack del sistema).
    - Eliminación de listas informativas redundantes (`.sidebar-help`).
  - Dropzones de carga (`st.file_uploader`): tarjeta de arrastre con borde discontinuo (`1px dashed var(--border-color)`), fondo `--surface-card` y soporte para *File Pill*.
  - Divisores `st.divider` nítidos con opacidad completa y borde sólido.
  - Banners semánticos de alerta (`st.info`, `st.warning`, `st.error`, `st.success`) con acento lateral sólido de 4px (`border-left`) y formato monoespacio para bloques `code` en cadenas técnicas.
  - Gage R&R permite seleccionar el orden de reportes sin tags y descargar todos los dashboards HTML en un ZIP; el ZIP se crea bajo demanda.

## Reglas Gage R&R importantes

- Estudio fijo:
  - 10 partes
  - 3 operadores
  - 3 repeticiones
  - 90 reportes/mediciones
- Streamlit usa siempre `input_format="auto"`; no pedir selección manual al usuario.
- Para bloques sin etiquetas de parte, el orden real debe conocerse: default `part-major`; la UI y CLI permiten `operator-major` si corresponde a la secuencia de captura.
- CLI conserva `--input-format` como respaldo: `auto`, `blocks`, `continuous`; también acepta `--report-order part-major|operator-major`.
- Archivos como `C20_RAW.txt`:
  - Un solo `BEGIN/END`.
  - 90 filas.
  - Tags `C20_A001` hasta `C20_A010`.
  - Deben interpretarse como una dimensión `C20`.
  - `_A###` identifica parte, no característica distinta.
  - Resultado validado contra Minitab:
    - NDC = 6
    - % Total Gage R&R = 21.0094%
    - Repeatability ≈ 20.6178%
    - Reproducibility ≈ 4.0380%
    - Part-to-Part ≈ 97.7681%

## Problemas ya resueltos

- Parser GRR no reconocía bloques sin `:END` exacto; ahora acepta `END`, `:END`, comillas o sin comillas.
- El formato C20 producía NDC=1 por mapear incorrectamente `A001...A010` como repeticiones agrupadas; ahora conserva la parte por tag.
- ANOVA inicial usaba denominadores equivocados en ciertos casos; ahora coincide con las tablas de Minitab.
- Dashboard GRR fallaba en despliegue por `ax.boxplot(labels=...)`; se reemplazó por posiciones y `set_xticks`.
- Streamlit light mode:
  - Fondo y superficies pasaron a grises claros.
  - Textos de tablas/uploader en negro.
  - Botones y uploader en naranja oscuro.
  - Alertas informativas eliminaron el fondo azul.
- Paired T:
  - Preview organizado en tres pestañas: Summary Report, Diagnostic Report y Report Card.
  - El HTML descargable mantiene paridad con el preview y embebe siete gráficos.
  - Las tablas y textos de los gráficos Paired T fueron ajustados para dark mode.
  - La tabla Difference/Power usa texto `#F2F2F2` para contraste.
- Comparación Minitab vs. código para `merged.txt` / `C20_A001`:
  - La secuencia real es part-major. El mapeo anterior operator-major generaba 79.9031% GRR Study Var y NDC=1; con part-major coincide con Minitab: GRR Study Var=19.6114%, NDC=7, Parte F=226.006 y Operador F=0.713 (P=0.494).
  - `merged.txt` tenía 90 reportes, pero dos inicios no eran reconocidos por marcadores fusionados/ASCII `0x1A`; el parser ahora recupera los 90 sin editar el archivo original.
  - El HTML comparativo `Gage_RR_C20_A001_Dashboard (1).html` fue regenerado con el orden correcto.
- Exportación de todos los reportes GRR: botón Streamlit `Download all reports (.zip)`; probado con ZIP válido y HTML embebido.
- Rediseño y consistencia de UI/UX (2026-10-11):
  - Inconsistencia de botones en sidebar: antes todos los botones aparecían con fondo naranja simultáneamente; ahora el botón activo (`type="primary"`) se distingue claramente con fondo `--brand-orange`, mientras los inactivos (`type="secondary"`) usan fondo transparente y borde neutro sutil.
  - Fallo de contraste WCAG en botón activo: Streamlit inyectaba texto blanco sobre fondo naranja (contraste deficiente 2.8:1); se corrigió forzando herencia de color `#121212` en todos los descendientes internos del botón activo, cumpliendo el estándar WCAG AAA (>7:1).
  - Ruido visual en panel lateral: se removió la lista estática de viñetas de ayuda (`sidebar-help`) que competía con la navegación.
  - Tipografía agresiva de navegación: se reemplazó el estilo tosco `STUDY SELECTION` (800 uppercase de 24px) por `Study Selection` en Title Case natural (`1.15rem`, `font-weight: 600`, stack del sistema), armonizando con el título principal.
  - Alineación de navegación: botones del sidebar alineados a la izquierda (`justify-content: flex-start`).
  - Dropzones de carga: se eliminó el botón flotante `+` desalineado; la tarjeta de carga adopta borde discontinuo (`1px dashed var(--border-color)`), fondo `--surface-card`, botón Browse redondeado y contenedor de archivo cargado (*File Pill*).
  - Divisores difuminados: `st.divider` corregido con `opacity: 1`, `height: 1px` y color sólido de token de borde.
  - Banners de alerta genéricos: transformados en banners semánticos con acento lateral izquierdo sólido de 4px (`border-left`) y soporte estilizado para bloques `code` en mensajes técnicos de error.
  - Especificación técnica `2_especificaci_n_t_cnica_css.md`: se removió el texto residual `eof` y se agregó una tabla formal de mapeo de selectores DOM de Streamlit (`[data-testid="..."]`).

## Validaciones actuales

- Compilación completa:
  - `python -m compileall -q src cli streamlit_app.py tests`
- Tests estándar:
  - `python -m unittest discover -s tests -p "test_*.py" -v`
  - Requiere `PYTHONPATH=src` en algunos comandos.
- Smoke tests realizados:
  - Type 1 con `RAW DATA.txt`
  - Paired T-Test con datos simples
  - Gage R&R con `C20_RAW.txt` y simulación de 90 bloques
  - `tests/test_modular_domain.py`: 35 pruebas pasan, incluyendo opciones de formato, normalización GRR, trazabilidad de líneas Paired T y BOM UTF-8.
  - `python -m compileall -q src cli streamlit_app.py tests` pasa.
  - Prueba directa de `merged.txt`: 90 reportes y métricas de `C20_A001` coinciden con Minitab.
  - ZIP real de `C20_A001` abre y contiene el dashboard HTML esperado.
  - La suite `unittest discover` completa no es limpia: `test_calculations.py` y `test_tolerances.py` buscan `gage data.txt`, que no existe. `test_gage_rr_minitab_structure.py` y `test_paired_ttest_example.py` son funciones pytest-style y se validaron invocándolas directamente.

## Riesgos y pendientes

- El parser Type 1 sigue siendo sensible a archivos sin tolerancias completas.
- El parser Type 1 usa `.replace("_OUT1", "")`, que puede fusionar nombres si aparece dentro del nombre y no solo como sufijo.
- `gage_type1/raw/RAW DATA.txt` contiene 120 reportes completos de 8 filas y un reporte final truncado con solo `C5` (121 `BEGIN`, 120 `END`). Los modos `blocks` y `periodic` rechazan el archivo completo; el prefijo de 120 reportes se procesa en ambos modos.
- Los gráficos R Chart usan constantes fijas para tamaño de subgrupo 3; correcto porque el diseño quedó fijo en 3 repeticiones.
- Los gráficos “Measurement by Part” y “Part × Operator Interaction” son muy similares; si se quiere paridad visual exacta con Minitab, revisar el primero.
- Los tests existentes `test_calculations.py` y `test_tolerances.py` son scripts de inspección, no pruebas unitarias robustas.
- `pytest` no está instalado en `.venv`; las pruebas principales actuales usan `unittest`.
- El HTML generado previamente puede contener resultados antiguos; regenerar dashboards después de cambios.
- No se puede inferir el orden de factores para reportes sin tags solo a partir de sus mediciones; seleccionar el orden de recolección correcto es requisito estadístico.

## Datos y archivos relevantes

- `gage_rr/raw/GAGE RR DATA.txt`
  - Fixture simulado completado a 90 bloques.
  - 3 características por bloque: `Measurement1`, `Measurement2`, `Measurement3`.
  - 720 líneas estructurales, 270 mediciones.
- `C20_RAW.txt`
  - Fuera del workspace, en `C:\Users\16917\Downloads\C20_RAW.txt`.
  - Referencia crítica para formato de una dimensión.
- `Gage_RR_C20_minitab.htm`
  - Referencia externa de Minitab para comparar resultados.
- `merged.txt` y `minitab GRR prueba C20_A001.pdf`
  - Fixture de comparación GRR. No editar `merged.txt` para corregir sus marcadores: el parser los normaliza en memoria.
- `paired_ttest/docs/paired_t_summary.png`
  - Referencia visual del Summary Report de Minitab Assistant.
- `paired_ttest/docs/Paired_t_diagnostic.png`
  - Referencia visual del Diagnostic Report, worksheet order y power.
- `paired_ttest/docs/paired_t_eval.png`
  - Referencia visual del Report Card.

## Auditoría de datos raw (2026-10-10)

- Los tags cambian entre fuentes; validar estructura y consistencia dentro del estudio, no depender de nombres de característica fijos.
- `gage_rr/raw/GAGE RR DATA.txt`: 90 reportes, 3 características (`Measurement1`–`Measurement3`); el parser acepta 270 filas.
- `gage_rr/raw/merged.txt`: 90 reportes, 63 tags de característica; el parser acepta 5,670 filas y asigna 10 piezas × 3 operadores × 3 pruebas.
- `gage_rr/raw/GAGE RR DATA_backup.txt`: 42 reportes con tres filas que repiten el tag `Measurement`; el parser rechaza duplicados por reporte. No cumple el diseño actual de 90 reportes.
- `gage_type1/raw/RAW DATA.txt`: 120 reportes completos con las mismas 8 características y un reporte final con solo `C5`. Los parsers no deben completar ni descartar ese reporte silenciosamente.
- `paired_ttest/raw/OGP DATA _A.txt` y `_b.txt`: 10 reportes por sistema, 8 características; los tags y su orden dentro de cada reporte coinciden. Se procesan como 8 series de 10 pares.
- `paired_ttest/raw/PAIRED DATA SYSTEM A.txt` y `SYSTEM B.txt`: 30 valores por sistema. System A empieza con BOM UTF-8; tras normalizarlo, ambos archivos producen 30 pares.
- Verificación: 35 pruebas de `test_modular_domain.py` pasan. El ejemplo Paired T y la aserción de estructura GRR también pasan; compilación, diagnósticos y `git diff --check` limpios.
- Limitaciones de tests: `tests/_runtests.py` conserva una ruta absoluta de otra máquina; `test_tolerances.py` requiere el archivo ausente `gage data.txt`.

## Preferencias del usuario observadas

- Prefiere respuestas claras, orientadas a ingeniería y validación.
- Se preocupa por:
  - Robustez del parser.
  - Paridad con Minitab.
  - Diseño fijo del estudio GRR.
  - UI adaptada a modo claro/oscuro.
  - Ingeniería modular y estándares de software.
- Pidió explícitamente que `memoria.md` no se suba al repositorio.

## Sesión de desarrollo

- Ramas de trabajo actuales: `Repo-sort-priv` (clasificación/ordenamiento) y `UI-New-improve` (rediseño UI/UX completado).
- Streamlit probado y ejecutándose localmente con recarga en vivo de estilos.
- Mantener `memoria.md` local y fuera de commits.

## Cierre de paso: Fase 2 (2026-10-11)

- Se configuró setuptools para instalar `gage_tracer`, la aplicación Streamlit y el paquete `cli`.
- Se agregó el entry point `msa-app`; los cuatro scripts instalados (`msa-app`, `msa-type1`, `msa-paired`, `msa-grr`) cargan fuera de la raíz del repositorio.
- Se eliminaron los hacks `sys.path.insert` de `src/app.py`, `streamlit_app.py` y los tres CLI.
- Validación: reinstalación editable exitosa; imports/entry points externos verificados; `unittest discover` (35 tests) y `compileall` pasan.
- README actualizado para la estructura real `data/examples/`, `data/private/`, `outputs/` y la instalación editable.

## Cierre de paso: Fase 3 (2026-10-11)

- Se eliminó `tests/_runtests.py`; `test_calculations.py` y `test_tolerances.py` ya estaban retirados.
- Se conectaron fixtures sintéticos para Type 1, Gage R&R y Paired T-Test con pruebas unittest.
- Se convirtió el ejemplo Paired y la prueba GRR a `unittest.TestCase`; se quitaron hacks `sys.path` de los tests.
- Validación: `python -m unittest discover -s tests -p "test_*.py"` pasa con 38 tests; compileall y `git diff --check` pasan.

## Cierre de paso: Fase 4 (2026-10-11)

- La aplicación pasó de `src/app.py` monolítico a paquete `src/app/`: tema/estilos, sidebar y componentes reutilizables, y vistas Type 1, Paired y GRR.
- `src/app/main.py` queda en 20 líneas; los entry points instalados se actualizaron para localizar el nuevo módulo.
- README actualizado con la nueva arquitectura.
- Validación: 38 tests pasan; compileall y `git diff --check` pasan; paquete editable y recurso CSS se cargan desde fuera del repo; Streamlit arrancó y respondió HTTP 200.

## Cierre de paso: Fase 5 (2026-10-11)

- Se añadió la CLI `msa` con `type1`, `grr` y `paired`, rutas explícitas y defaults hacia `data/examples/` y `outputs/`.
- Los flujos se refactorizaron para recibir rutas por parámetro; los scripts heredados permanecen como compatibilidad.
- README actualizado con la interfaz unificada y la estructura vigente.
- Los docstrings de los tres entry points heredados ahora apuntan a `msa` y a las rutas actuales.
- Validación: `msa --help` desde fuera del repositorio; 41 tests; compileall y `git diff --check`; ejecución end-to-end Type 1, Paired numérico y multicaracterística (8 características) y Gage R&R (3 características). Outputs temporales verificados y limpiados.

## Renombrado del launcher Streamlit (2026-10-11)

- `MSA_app.py` es el único launcher raíz; se eliminó `streamlit_app.py` en vez de mantener un alias.
- README actualizado para documentar solamente el nombre nuevo.
- Antes de eliminar el alias, ambos launchers respondieron HTTP 200; los 41 tests, compileall y `git diff --check` pasaron.
