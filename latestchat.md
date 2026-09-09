me:
creo que faltan graficos, ademas todo lo que se agregue al preview debe ir tambien al reporte html
Esta es la especificación técnica y funcional completa (Product Requirement Document - PRD) para replicar exactamente los 3 reportes del Asistente de Minitab para Prueba t Pareada (Paired t) en un dashboard interactivo.
________________________________________
ARCHITECTURA GENERAL DEL DASHBOARD
El dashboard debe estructurarse en 3 pestañas o secciones principales:
	Summary Report (Informe de Resumen): Enfocado en la toma de decisiones ejecutivas.
	Diagnostic Report (Informe Diagnóstico): Enfocado en la exploración gráfica y detección de patrones en los datos.
	Report Card (Tarjeta de Informe): Un motor de validación de supuestos y calidad del estudio.
________________________________________
I. MOTOR DE CÁLCULO Y DATA PIPELINE (BACKEND)
Antes de renderizar las vistas, el sistema debe procesar las dos columnas de entrada (X_1 y X_2) de tamaño n:
	Diferencias individuales:
d_i=X_1i-X_2i∀ i∈{1,…,n}
	Estadísticos descriptivos básicos:
	Medias: X ˉ_1, X ˉ_2, d ˉ=1/n∑d_i
	Desviaciones estándar: S_1, S_2, S_d=√((∑(d_i-d ˉ)^2)/(n-1))
	Error estándar de la media de la diferencia: SE_d=S_d/√n
	Prueba de Hipótesis:
	Grados de libertad: df=n-1
	Estadística t: t=d ˉ/(SE_d )
	p-valor: Calculado según la hipótesis alternativa elegida (μ_d≠0, μ_d>0, o μ_d<0) usando la distribución tde Student con dfgrados de libertad.
	Intervalo de Confianza (95% por defecto):
IC=[d ˉ-t_(α/2,df)⋅SE_d, d ˉ+t_(α/2,df)⋅SE_d ]
________________________________________
II. PANTALLA 1: SUMMARY REPORT (INFORME DE RESUMEN)
Esta vista debe organizarse en una cuadrícula de 2x2.
+------------------------------------+------------------------------------+
| [1.1] Gauge / Indicador p-valor    | [1.2] Gráfico de Intervalo (CI)    |
+------------------------------------+------------------------------------+
| [1.3] Tabla de Estadísticas        | [1.4] Tarjeta de Comentarios      |
+------------------------------------+------------------------------------+
	
	
	
	
Componente 1.1: Gauge / Indicador de Decisiones (p-valor)
	Tipo: Barra graduada horizontal con un indicador/flecha.
	Rango del eje: De 0.000 a 0.150 (o más).
	Zona crítica: Línea vertical roja discontinua en α=0.05.
	Etiquetas de zona:
	Izquierda (≤0.05): Fondo verde suave o rojo destacado según significancia. Texto: "Sí (p<0.05)".
	Derecha (>0.05): Fondo gris neutro. Texto: "No (p≥0.05)".
	Título del componente: "¿Es la diferencia entre las medias estadísticamente significativa? (α=0.05)"
	Lógica condicional de texto:
	Si p≤0.05: "La media de [Nombre_Muestra_1] es significativamente diferente de la media de [Nombre_Muestra_2] (p=[Valor_p])."
	Si p>0.05: "La diferencia entre las medias de [Nombre_Muestra_1] y [Nombre_Muestra_2] no es estadísticamente significativa (p=[Valor_p])."
Componente 1.2: Gráfico de Intervalo de la Diferencia
	Tipo: Interval Plot (Gráfico de línea con barra de error).
	Eje Y: Escala continua de la diferencia (Muestra_1-Muestra_2).
	Línea de referencia: Línea horizontal punteada en 0(Línea de No Diferencia).
	Elementos gráficos:
	Punto central: Media de las diferencias (d ˉ).
	Barras de error: Límite inferior (IC_low) y Límite superior (IC_high).
	Comportamiento visual:
	Si el intervalo no cruza la línea 0, las barras se pintan de un color contrastante (p. ej., Azul oscuro o Verde), indicando significancia.
	Si el intervalo cruza la línea 0, las barras se pintan de Gris neutro.
Componente 1.3: Tabla de Estadísticas Descriptivas
	Formato: Tabla limpia de 3 filas y 5 columnas.
Variable	Muestra (N)	Media (X ˉ)	Desv. Est. (S)	Error Est. Media (SE)
[Nombre_Muestra_1]	n	X ˉ_1	S_1	S_1/√n
[Nombre_Muestra_2]	n	X ˉ_2	S_2	S_2/√n
Diferencia (M_1-M_2)	n	d ˉ	S_d	SE_d
	Metadatos al pie de tabla: Mostrar la estadística t, los grados de libertad (df) y el p-valor exacto.
Componente 1.4: Tarjeta de Comentarios Ejecutivos (Text Generator)
Bloque de texto dinámico estructurado en viñetas:
	Interpretación del resultado: "Usted puede concluir que las medias poblacionales son diferentes con un nivel de confianza del 95%." (o lo opuesto si p>0.05).
	Estimación puntual: "La diferencia promedio estimada entre las dos muestras es de [d ˉ]."
	Intervalo de confianza: "Con un 95% de confianza, la verdadera diferencia promedio entre las poblaciones se encuentra entre [IC_low] y [IC_high]."
________________________________________
III. PANTALLA 2: DIAGNOSTIC REPORT (INFORME DIAGNÓSTICO)
Esta vista permite auditar la calidad de los datos recopilados a través de 3 gráficos independientes y un panel de alertas.
+------------------------------------+------------------------------------+
| [2.1] Gráfico de Datos Pareados   | [2.2] Histograma de Diferencias    |
+------------------------------------+------------------------------------+
| [2.3] Gráfico de Orden Cronológico| [2.4] Panel de Valores Atípicos    |
+------------------------------------+------------------------------------+
	
	
	
	
Componente 2.1: Gráfico de Datos Pareados (Slopegraph / Connected Dot Plot)
	Tipo: Gráfico de puntos conectados por segmentos de línea.
	Eje X (Categorías): Dos posiciones verticales: Muestra 1 y Muestra 2.
	Eje Y (Continuo): Escala de valores de medición.
	Mapeo de datos: Para cada sujeto/pieza i, dibuja un punto en (Muestra_1ⓜ,X_1i )y otro en (Muestra_2ⓜ,X_2i ), unidos por una línea fina.
	Propósito: Mostrar si la tendencia general de cambio (subida o bajada) es consistente en casi todas las piezas o si hay comportamientos cruzados.
Componente 2.2: Histograma de las Diferencias
	Tipo: Histograma con curva de distribución normal superpuesta.
	Eje X: Escala de las diferencias (d_i).
	Eje Y: Frecuencia absoluta (conteo).
	Elementos superpuestos:
	Línea vertical continua para la Media (d ˉ).
	Línea vertical punteada en 0.
	Curva Gaussiana calculada con N(d ˉ,S_d).
	Resaltado de outliers: Si existen barras correspondientes a datos fuera de límites (±3S_d), se pintan en color Rojo / Alerta.
Componente 2.3: Gráfico de Diferencias vs. Orden de Observación (Run Chart)
	Tipo: Gráfico de dispersión con líneas de conexión cronológica.
	Eje X: Número de observación u orden de recolección (1,2,…,n).
	Eje Y: Valor de la diferencia (d_i).
	Líneas de referencia:
	Línea central (d ˉ).
	Línea de cero (0).
	Propósito: Detectar patrones temporales (tendencias de desgaste, cambios de turno, deriva del instrumento).
Componente 2.4: Tabla / Panel de Valores Atípicos (Outlier Panel)
	Lógica de detección: Identifica cualquier índice idonde ∣d_i-d ˉ∣>3⋅S_d.
	Visualización:
	Si la lista está vacía: Muestra un mensaje en verde: "No se detectaron valores atípicos severos (>3σ)."
	Si hay valores: Muestra una tabla con: # Fila / ID de Pieza, Valor Muestra 1, Valor Muestra 2, Diferencia ($d_i$).
________________________________________
IV. PANTALLA 3: REPORT CARD (TARJETA DE INFORME)
Esta pantalla consiste en una matriz de validación con 3 tarjetas cualitativas. Cada tarjeta contiene un icono de estado, un título y un texto explicativo dinámico.
Estados posibles de los iconos:
	🟢 Check Verde (Pasa): El supuesto se cumple sin problemas.
	🟡 Triángulo Amarillo (Advertencia): El supuesto no se cumple totalmente, pero la prueba es relativamente robusta.
	🔴 Círculo Rojo (Alerta): El incumplimiento compromete la validez de la prueba.
________________________________________
Tarjeta 1: Normalidad (Normality Check)
[Icono Estado] Normalidad de las Diferencias
	
	
	
	
	Regla de decisión (Algoritmo):
	Si n≥20"  "⟹"  " 🟢 VERDE.
	Texto: "Debido a que el tamaño de la muestra es de al menos 20, la normalidad no es un problema crítico. El Teorema del Límite Central garantiza que la prueba t es robusta a desviaciones moderadas de la normalidad."
	Si n<20: Ejecutar la prueba de normalidad de Anderson-Darling sobre las diferencias d_i:
	Si p_AD≥0.05"  "⟹"  " 🟢 VERDE.
	Texto: "Las diferencias siguen una distribución normal (p>0.05), por lo que los cálculos de la prueba t son precisos."
	Si p_AD<0.05"  "⟹"  " 🟡 AMARILLO.
	Texto: "Debido a que el tamaño de la muestra es menor que 20 y los datos no siguen una distribución normal, el p-valor podría no ser exacto. Considere usar una prueba no paramétrica (como la prueba de Signos o Wilcoxon) si los datos son fuertemente asimétricos."
________________________________________
Tarjeta 2: Valores Atípicos (Outliers Check)
[Icono Estado] Valores Atípicos
	
	
	
	
	Regla de decisión (Algoritmo):
	Contar observaciones donde ∣d_i-d ˉ∣>3⋅S_d.
	Si Conteo=0"  "⟹"  " 🟢 VERDE.
	Texto: "No hay valores atípicos inusuales en las diferencias que afecten sustancialmente los resultados."
	Si Conteo≥1"  "⟹"  " 🟡 AMARILLO.
	Texto: "Se encontraron [Conteo] valores atípicos en los datos de las diferencias. Los valores atípicos pueden distorsionar la media y la desviación estándar, aumentando la probabilidad de obtener resultados engañosos. Evalúe estos puntos en el Informe Diagnóstico para determinar si se deben a errores de medición o a causas especiales."
________________________________________
Tarjeta 3: Tamaño de la Muestra / Potencia (Sample Size & Power Check)
[Icono Estado] Tamaño de la Muestra
	
	
	
	
	Regla de decisión (Algoritmo):
	Si n≥15"  "⟹"  " 🟢 VERDE.
	Texto: "El tamaño de la muestra (n=[n]) es lo suficientemente grande como para detectar diferencias de interés práctico con una potencia adecuada."
	Si n<15"  "⟹"  " 🟡 AMARILLO.
	Texto: "El tamaño de la muestra es pequeño (n=[n]). Las muestras pequeñas reducen la potencia estadística de la prueba, lo que aumenta la probabilidad de no detectar una diferencia real cuando esta existe (Error Tipo II)."
________________________________________
RESUMEN DE ENTREGA PARA EL PROGRAMADOR / AGENTE
Para construir este dashboard, dile al agente que implemente:
	Entradas: Dos arreglos numéricos de igual longitud sample1 y sample2.
	Estructura visual: Dashboard de 3 pestañas (Summary, Diagnostics, ReportCard).
	Lógica gráfica:
	Recharts / D3.js / Plotly: Para crear el gauge de p-valor, la barra de error de IC, el slopegraph de líneas conectadas, el histograma con curva Gaussiana y el gráfico de dispersión por orden.
	Text Engine: Un generador de cadenas dinámicas basado en las condicionales descritas en la Sección IV.

AI:
You’re right: the web preview now has the requested five charts, but the downloaded HTML still uses the older four-chart layout and does not include the three Minitab-like sections. I’ll upgrade the HTML generator to consume the same summary figures, diagnostic figures, tables, and report-card diagnostics as the Streamlit preview.

Read , lines 500 to 980

Read 

Read 

The gap is confirmed: the exported HTML is still an older, separate implementation. I’ll replace that generator with a self-contained three-tab HTML report that embeds the exact same five figures and renders the same summary, diagnostics, report-card findings, and data-preview tables.

Read , lines 900 to 960

Read , lines 960 to 993

Generating patch (492 lines) in 


```

```
The exported HTML now mirrors the preview instead of maintaining a second, older report model: it has the same three tabs, five charts, descriptive/quality tables, outlier panel, and report-card checks. I’ll generate it with reference data and verify the expected sections and embedded figures.

Ran terminal command: & .\.venv\Scripts\python.exe -c "import sys; sys.path.insert(0,'src'); import pandas as pd; from gage_tracer.paired_ttest import calculate_paired_ttest_metrics, create_paired_ttest_dashboard; df=pd.DataFrame({'Observation':[1,2,3,4,5],'System_A':[10.1,10.3,10.2,10.4,10.0],'System_B':[10.0,10.1,10.3,10.2,10.1]}); df['Difference']=df['System_A']-df['System_B']; metrics=calculate_paired_ttest_metrics(df['System_A'].tolist(),df['System_B'].tolist()); html=create_paired_ttest_dashboard(df,metrics); required=['Summary Report','Diagnostic Report','Report Card','P-value decision gauge','Confidence interval plot','Paired measurements plot','Histogram of differences','Differences by observation order','Normality of differences']; print('missing=',[item for item in required if item not in html]); print('images=',html.count('data:image/png;base64,'))"

Ran terminal command: & .\.venv\Scripts\python.exe -m compileall -q src cli streamlit_app.py tests; if ($LASTEXITCODE -eq 0) { 'Compilation OK' }

Checked , , , no problems found

The exported report validation passed: all three tab labels are present and it embeds exactly five charts. I’ll add a regression test for that parity contract so future changes cannot add a preview-only chart or silently drop an HTML report section.

Generating patch (33 lines) in 


```

```


Ran terminal command: $env:PYTHONPATH='src'; & .\.venv\Scripts\python.exe -m unittest tests.test_modular_domain -v

Ran terminal command: git diff --stat

Checked , no problems found

The parity test passes: the downloadable HTML now contains all three reports and exactly five embedded charts. I also noticed existing changes in the paired raw input files that were not made by this work, so I’m leaving them untouched and will report them separately rather than folding them into the dashboard change.

Ran terminal command: git status --short

Ran terminal command: & .\.venv\Scripts\python.exe -m compileall -q src cli streamlit_app.py tests; if ($LASTEXITCODE -eq 0) { 'Compilation OK' }

Implemented preview-to-HTML parity for Paired T.

The downloadable HTML now includes the same Minitab-like structure as the Streamlit preview:

- `Summary Report`
  - P-value decision gauge
  - 95% confidence interval chart
  - 3-row descriptive table
  - Executive comments

- `Diagnostic Report`
  - Paired-measurement slopegraph
  - Histogram with fitted normal curve
  - Difference run chart
  - Severe $3\sigma$ outlier panel

- `Report Card`
  - Normality assessment
  - Outlier assessment
  - Sample-size assessment
  - Uploaded-data preview and input-quality table

Validation passed:

```text
9 focused tests: OK
Compilation: OK
HTML report: 3 sections and 5 embedded charts
```

Note: `paired_ttest/raw/PAIRED DATA SYSTEM A.txt` and `paired_ttest/raw/PAIRED DATA SYSTEM B.txt` were already modified in the worktree; I did not alter them.


me:
aun le falta un monton con respecto a los que emerge del estudio en minitab 'Minitab Assistant Summary Report for a Paired t-test", te pego imagenes de los graficos que vienen en minitab
AI:
The screenshots clarify the gap: the current implementation follows the earlier PRD, but it still misses two prominent Minitab Assistant surfaces: the worksheet-order paired-data chart and the power/detectable-difference analysis. I’ll add those to the shared Paired T diagnostic model and render them in both Streamlit and the downloadable HTML; this keeps the two reports aligned.
Reviewed 3 files
The screenshots add two concrete Minitab Assistant components that were not in our current implementation: Paired Data in Worksheet Order and the power/detectable-difference panel. I’ll add both as shared diagnostics and include them in both outputs, so the preview and downloaded HTML remain identical in coverage.
Finished with 2 steps+97-1
The calculation and chart additions are now in place: a two-sided noncentral-t power model drives the new power panel, and the worksheet-order chart uses the original measurement order. I’ll run a focused smoke test now before wiring the extra figures into the two report surfaces.
Executed command and checked paired_ttest.py and paired_visualization.py
The first validation found a numerical edge case in SciPy’s noncentral-t tail calculation at an unnecessarily large search bound. The target powers are below 1, so I’ll limit the root search to a stable noncentrality range that still brackets 90% power, then rerun the same smoke test.
Updated paired_ttest.py and ran command+3-1
The deployed SciPy build returns NaN for noncentral-t evaluations even at moderate bounds, so this is a library numerical limitation rather than a chart problem. I’ll replace the unstable tail computation with a normal approximation for the power panel; it is robust for the intended planning display and prevents the report from failing on small samples.
Updated paired_ttest.py and ran command+2-4
The stable power model and the two additional figures now render correctly. I’ll place them in the Diagnostic tab and update the HTML generator from five to seven embedded charts, so both report surfaces carry the same full set.
Updated app.py and reviewed paired_ttest.py+8-0
The first HTML patch hit a context mismatch around the docstring, so no HTML changes were applied. I’ll apply the same update in small targeted pieces, starting with figure generation, then the diagnostics section, and immediately validate the resulting seven-image report.
Finished with 2 steps+8-2
The HTML now uses the same additional diagnostics as Streamlit. I’ll validate the preview and export together: both should produce seven figures, with the power table derived from the shared diagnostic data rather than separate calculations.
Executed commands and checked 3 files
The live parity check passed with seven embedded charts. I found one necessary follow-up: the existing regression test still expects five images, so I’ll update it to enforce the expanded Minitab-like report contract and add a direct power-planning assertion.

