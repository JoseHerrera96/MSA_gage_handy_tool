# Plan: opciones de entrega de datos por estudio
## 1. Objetivo
Permitir que la persona seleccione primero el estudio y luego la forma de
entregar sus datos, viendo solo las opciones compatibles con ese estudio. Cada
opción debe explicar cuántos archivos preparar, qué representa cada uno, el
orden esperado, las validaciones y un ejemplo.
Se deben conservar los formatos actuales y los resultados estadísticos. Los
nuevos formatos se normalizarán a las estructuras que ya consumen los análisis;
no se duplicarán las fórmulas.
## 2. Flujo de interfaz

1. Seleccionar estudio: Type 1, Gage R&R o Paired T-Test.
2. Seleccionar una modalidad de entrada específica para ese estudio.
3. Mostrar instrucciones de formato, cantidad de archivos, orden, ejemplo y
	errores frecuentes.
4. Presentar cargas etiquetadas claramente, por ejemplo `Part 1` u
	`Operator 1`.
5. Validar los datos y mostrar una vista previa antes de calcular.

Al cambiar de estudio o modalidad, la aplicación no debe reutilizar cargas
anteriores que tengan otro significado.
## 3. Modalidades por estudio

### 3.1 Type 1 Gage Study

| Modalidad | Archivos | Formato esperado |
| --- | --- | --- |
| Reportes con separadores (actual) | 1 | Reportes delimitados por `BEGIN`/`END`, con características, mediciones y especificaciones. |
| Reportes consecutivos sin separadores (nueva) | 1 | Reportes contiguos; puede haber encabezados u otras líneas que no sean mediciones. El parser identifica ciclos mediante una secuencia periódica de características y columnas/especificaciones. |

Instrucciones de la interfaz: un archivo con todas las mediciones de la misma
pieza o estándar; explicar las columnas de característica, medición, referencia
y tolerancias usando los nombres reales admitidos; informar qué encabezados se
pueden ignorar; y mostrar cuántos ciclos fueron detectados.

**Regla por confirmar:** el parser actual inicia ciclos cuando vuelve a aparecer
una característica y omite algunas filas no medibles. Antes de ampliar esa
heurística, hay que fijar con ejemplos qué secuencia representa un ciclo
completo. No se deben descartar silenciosamente mediciones mal formadas ni
adivinar límites cuando haya más de una interpretación posible. En caso de
ambigüedad, mostrar un error accionable y sugerir el formato con separadores.

Resumen visible: `1 archivo · varias mediciones/reportes · una pieza o estándar`.

### 3.2 Gage R&R (Crossed)

El diseño actual es **10 piezas × 3 operadores × 3 pruebas = 90 reportes**.
Cada reporte puede tener varias características.

| Modalidad | Archivos | Contenido y orden |
| --- | --- | --- |
| Archivo único (actual) | 1 | 90 reportes. Si no llevan etiquetas de pieza u operador, se elige el orden global de la secuencia. |
| Un archivo por pieza (nueva) | 10 (`Part 1` a `Part 10`) | 9 reportes por archivo: tres pruebas del Operator 1, luego tres del Operator 2 y tres del Operator 3. |
| Un archivo por operador (nueva) | 3 (`Operator 1` a `Operator 3`) | 30 reportes por archivo: tres pruebas de Part 1, después tres de Part 2, hasta Part 10. |

#### Explicación de las secuencias actuales

`Part → Operator → Trial` y `Operator → Part → Trial` no representan estudios
diferentes. Definen cómo asignar etiquetas a los 90 reportes de un archivo que
no identifica la pieza y el operador. En ambos casos, `Trial` es el nivel más
interno y cada combinación pieza-operador tiene tres pruebas.

- **Part → Operator → Trial (part-major):** se agrupa primero por pieza. Los
	reportes 1–9 son Part 1: 1–3 Operator 1, 4–6 Operator 2 y 7–9 Operator 3.
	Los siguientes nueve son Part 2, y así hasta Part 10.
- **Operator → Part → Trial (operator-major):** se agrupa primero por operador.
	Los reportes 1–30 son Operator 1; cada grupo de tres avanza por las piezas 1
	a 10. Los reportes 31–60 son Operator 2 y 61–90 Operator 3.

En la modalidad de 10 archivos, el archivo determina la pieza y los nueve
reportes internos siguen Operator → Trial. En la modalidad de 3 archivos, el
archivo determina el operador y sus treinta reportes siguen Part → Trial. Esta
explicación debe mostrarse junto a las opciones, no solo en un tooltip.

**Validaciones:**

- Exactamente 90 reportes en total, diseño balanceado 10 × 3 × 3.
- Modalidad por pieza: exactamente 9 reportes válidos en cada archivo.
- Modalidad por operador: exactamente 30 reportes válidos en cada archivo.
- Cada reporte contiene las características necesarias con mediciones y
	tolerancias válidas; el conjunto de características debe ser consistente.
- Las etiquetas explícitas de pieza/operador no pueden contradecir la identidad
	determinada por el archivo sin generar un error.
- Los errores identifican archivo y número de reporte.

Resumen visible:

- `1 archivo · 90 reportes · elegir orden de la secuencia`.
- `10 archivos · 9 reportes por pieza · 3 operadores × 3 pruebas`.
- `3 archivos · 30 reportes por operador · 10 piezas × 3 pruebas`.

### 3.3 Paired T-Test

Se comparan dos sistemas medidos sobre las mismas observaciones. Hay un archivo
para System A y otro para System B. Por defecto, las mediciones se emparejan por
orden de reporte.

| Modalidad | Archivos | Formato esperado |
| --- | --- | --- |
| Archivos estructurados (actual) | 2 | Valores numéricos por línea o bloques `BEGIN`/`END` para varias características. Ambos sistemas deben tener igual cantidad y estructura compatible. |
| Texto sin estructura fija (nueva) | 2 | Puede no tener encabezados ni marcadores, o tener marcadores incompletos. Las mediciones se extraen con reglas explícitas del modo elegido; el orden determina el pareo. |

Para texto sin estructura, el MVP debería aceptar solo patrones inequívocos:

- Una medición numérica reconocible por observación, aunque haya texto no
	medible alrededor.
- Varias características solo si cada medición puede asociarse a una etiqueta.
- Igual número de observaciones y las mismas características por observación en
	ambos sistemas.

Los marcadores presentes pueden ayudar a identificar reportes, pero no serán
requisito en esta modalidad. Un marcador aislado, anidado o incompleto no debe
provocar pérdida o desplazamiento de mediciones. Si no se puede reconstruir el
pareo con seguridad, se debe indicar la línea u observación que requiere
corrección.

**Validaciones:** ambos archivos asignados a sus sistemas; al menos dos pares;
igual cantidad de observaciones; mediciones numéricas finitas; etiquetas
consistentes si hay varias características; y vista previa del pareo A/B antes
de mostrar conclusiones.

Resumen visible: `2 archivos · System A y System B · misma cantidad y orden de
observaciones`. Ejemplo: `10 observaciones por sistema · 10 pares`.

## 4. Arquitectura propuesta

- `src/app.py`: organiza el flujo estudio → modalidad → instrucciones → cargas,
	separando el estado de cada modalidad.
- `src/gage_tracer/data_parser.py`: implementa o extiende parsers por modalidad,
	valida entradas y las convierte a estructuras normalizadas. No contiene UI ni
	cálculos estadísticos.
- `src/gage_tracer/study_config.py`: concentra reglas compartidas del diseño
	GRR y cantidades, evitando repetir constantes entre UI, parser y pruebas.
- `src/gage_tracer/calculations.py` y `paired_ttest.py`: consumen datos
	normalizados. Solo se modifican si un contrato nuevo lo requiere.
- `cli/`: mantiene compatibilidad con sus flujos actuales. La primera entrega
	puede ampliar Streamlit sin rediseñar las opciones de línea de comandos.
- `tests/`: cubre parsers y la integración normalización → cálculo.

La interfaz debe indicar el modo seleccionado al parser. La autodetección se
puede conservar para compatibilidad, pero no debe elegir silenciosamente entre
formatos nuevos ambiguos.

## 5. Fases de implementación

### Fase 1: cerrar contratos de datos

- Reunir ejemplos válidos e inválidos, anonimizados, para cada modalidad.
- Documentar columnas, etiquetas, tolerancias y líneas ignorables.
- Acordar cómo detectar ciclos Type 1 y extraer mediciones Paired T sin
	estructura.
- Definir qué hacer si etiquetas de GRR contradicen el archivo o la secuencia.

**Entrega:** especificación y ejemplos que puedan convertirse en pruebas.

### Fase 2: opciones de interfaz

- Implementar el flujo estudio → formato → instrucciones → cargas.
- Crear controles GRR etiquetados para 1, 10 o 3 archivos.
- Mostrar diagramas o tablas de orden, cantidades, ejemplo y preview.

**Entrega:** interfaz comprensible con modos explícitos.

### Fase 3: parsers y normalización

- Adaptar Type 1 sin separadores al modelo actual de ciclos.
- Convertir cargas GRR por pieza/operador a registros comunes con
	`Part`, `Operator`, `Trial`, característica, medición y tolerancias.
- Implementar extracción Paired T sin estructura conservando índices/orden de
	origen para auditar el pareo.
- Generar errores específicos por archivo, bloque, línea, característica y
	cantidad esperada/recibida.

**Entrega:** todas las modalidades alimentan las mismas estructuras de análisis.

### Fase 4: pruebas y regresión

- Probar cada parser con entradas válidas, encabezados, ruido, separadores
	parciales, valores no finitos, duplicados, datos faltantes y orden incorrecto.
- Comprobar que el mismo estudio sintético en modalidades equivalentes produce
	las mismas filas normalizadas y resultados.
- Probar cambio de estudio/modalidad, número de archivos, preview, errores y
	descargas en Streamlit.
- Ejecutar la suite actual y preservar los formatos existentes.

**Entrega:** cobertura automatizada y regresiones detectables.

### Fase 5: documentación y entrega

- Actualizar README y guías de cada estudio con cantidades y ejemplos por modo.
- Añadir plantillas sintéticas, sin datos de producción.
- Probar ejemplos completos en Streamlit y los flujos actuales compatibles en
	CLI.

**Entrega:** instrucciones coherentes con interfaz y parser.

## 6. Criterios de aceptación

- Primero se elige el estudio; después se muestran únicamente sus modalidades.
- Cada modalidad explica cantidad de archivos, contenido y orden en lenguaje
	claro.
- Las cargas múltiples quedan asociadas inequívocamente a pieza u operador.
- Los formatos existentes siguen funcionando y mantienen sus resultados.
- Datos ambiguos o incompletos se rechazan con mensajes útiles; nunca se omiten
	mediciones ni se desplazan pares silenciosamente.
- Modalidades equivalentes producen los mismos datos normalizados y resultados.
- Cada modalidad tiene ejemplo, preview y pruebas automatizadas.

## 7. Decisiones pendientes

1. **Type 1:** ¿qué secuencia exacta de filas define un ciclo completo sin
	 separadores? ¿Siempre hay varias características y especificaciones?
2. **Paired T sin estructura:** ¿la primera versión acepta solo una medición por
	 observación o también varias características etiquetadas? ¿Qué texto cuenta
	 como ruido ignorable?
3. **Emparejamiento Paired T:** ¿siempre por posición o habrá identificador de
	 muestra para alinear observaciones?
4. **GRR:** en cargas por pieza/operador, ¿se mantienen bloques `BEGIN`/`END` o
	 pueden ser reportes separados únicamente por su patrón de filas?
5. Si etiquetas explícitas de pieza/operador contradicen el modo elegido,
	 ¿prevalecen las etiquetas o se rechaza el archivo?
6. ¿La primera entrega amplía solo Streamlit o también añade argumentos CLI
	 para los modos de varios archivos?

## 8. Orden recomendado

1. Gage R&R con 10 archivos por pieza y 3 por operador: los archivos determinan
	 una dimensión y las secuencias internas ya están definidas.
2. Type 1 sin separadores: comenzar después de acordar y probar el patrón
	 periódico real.
3. Paired T sin estructura fija: implementar una vez acordados los criterios
	 para distinguir ruido de mediciones y preservar el pareo.
