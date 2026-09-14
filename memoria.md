# Memoria del proyecto

> Archivo local de contexto para agentes de AI. No debe versionarse ni subirse al repositorio.
> Última actualización: 2026-09-14.

## Estado actual

- Repositorio: `Type_1_gage_handy_tool`.
- Rama activa al documentar: `improving-paired-preview`.
- Último commit visible: `eac74f4 debug GRR tool`.
- Commit modular anterior: `0aafd70 feat: modularize MSA workflows and improve crossed Gage R&R parsing`.
- Entorno Python: `.venv`, Python 3.14, paquetes principales pandas, numpy, scipy, matplotlib, streamlit y watchdog.
- Punto de entrada principal de UI: `streamlit_app.py`, que carga `src/app.py`.

## Arquitectura

- `src/gage_tracer/data_parser.py`
  - Parser Type 1 y Gage R&R.
  - Type 1 mantiene comportamiento independiente; no mezclar cambios GRR sin validar Type 1.
  - Gage R&R soporta dos layouts:
    1. 90 bloques explícitos `BEGIN/END` o `:BEGIN/:END`.
    2. Un bloque o flujo continuo con 90 mediciones de una dimensión y tags `C20_A001...C20_A010`.
  - Los headers y footers son ignorados en filas no válidas.
  - El diseño GRR está fijo: 10 partes × 3 operadores × 3 repeticiones = 90 reportes.

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

- `src/gage_tracer/paired_ttest.py`
  - Parser de dos archivos numéricos.
  - Cálculo de paired t-test, IC 95%, dashboard.
  - Diagnósticos Minitab-like: normalidad, outliers > 3σ, tamaño de muestra y potencia/diferencias detectables.
  - Exportación HTML con Summary Report, Diagnostic Report y Report Card.
  - Advertencia pendiente: descarta líneas no numéricas silenciosamente.

- `src/gage_tracer/paired_visualization.py`
  - Gráficos Paired T alineados con Minitab Assistant.
  - Gauge de p-value, tablas de estadísticas, histograma con IC, worksheet order,
    slopegraph, run chart y power/detectable difference.
  - Usa paleta dark compartida: fondo carbón, texto claro, naranja `#FF8C00`,
    azul visible para System B, verde y rojo semánticos.

- `src/app.py`
  - Orquestación Streamlit.
  - UI con modo dark/light.
  - Acentos de botones: `#FF8C00`.
  - Superficies de carga/tablas/alertas usan grises definidos por variables CSS.

## Reglas Gage R&R importantes

- Estudio fijo:
  - 10 partes
  - 3 operadores
  - 3 repeticiones
  - 90 reportes/mediciones
- Streamlit usa siempre `input_format="auto"`; no pedir selección manual al usuario.
- CLI conserva `--input-format` como respaldo: `auto`, `blocks`, `continuous`.
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

## Riesgos y pendientes

- El parser Type 1 sigue siendo sensible a archivos sin tolerancias completas.
- El parser Type 1 usa `.replace("_OUT1", "")`, que puede fusionar nombres si aparece dentro del nombre y no solo como sufijo.
- `RAW DATA.txt` local contiene una primera línea anómala `s"C1"` y filas de dos columnas; no es una referencia fiable de Type 1.
- Los gráficos R Chart usan constantes fijas para tamaño de subgrupo 3; correcto porque el diseño quedó fijo en 3 repeticiones.
- Los gráficos “Measurement by Part” y “Part × Operator Interaction” son muy similares; si se quiere paridad visual exacta con Minitab, revisar el primero.
- Los tests existentes `test_calculations.py` y `test_tolerances.py` son scripts de inspección, no pruebas unitarias robustas.
- `pytest` no está instalado en `.venv`; las pruebas principales actuales usan `unittest`.
- El HTML generado previamente puede contener resultados antiguos; regenerar dashboards después de cambios.

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
- `paired_ttest/docs/paired_t_summary.png`
  - Referencia visual del Summary Report de Minitab Assistant.
- `paired_ttest/docs/Paired_t_diagnostic.png`
  - Referencia visual del Diagnostic Report, worksheet order y power.
- `paired_ttest/docs/paired_t_eval.png`
  - Referencia visual del Report Card.

## Preferencias del usuario observadas

- Prefiere respuestas claras, orientadas a ingeniería y validación.
- Se preocupa por:
  - Robustez del parser.
  - Paridad con Minitab.
  - Diseño fijo del estudio GRR.
  - UI adaptada a modo claro/oscuro.
  - Ingeniería modular y estándares de software.
- Pidió explícitamente que `memoria.md` no se suba al repositorio.
