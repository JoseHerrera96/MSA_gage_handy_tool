# Interpretación completa del dashboard de Paired T-Test

Este documento explica cada parte del dashboard generado por `Paired_T_Test_tool.py` y cómo interpretar los resultados de una comparación emparejada entre dos sistemas de medida.

## 1. Qué mide el análisis

El estudio compara dos sistemas de medición:

- `System A`: valores medidos por el primer sistema.
- `System B`: valores medidos por el segundo sistema.

Cada línea de los archivos de entrada corresponde a la misma observación en ambos sistemas. El objetivo es determinar si existe una diferencia estadísticamente significativa entre los valores emparejados.

## 2. Archivos generados

- `paired_data.txt`
  - Contiene los valores originales de ambos sistemas y la diferencia (`System_A - System_B`).
  - Es la base de datos usada para el cálculo estadístico.

- `Paired_T_Test_Summary.txt`
  - Reporte de texto con las métricas clave, hipótesis, estadísticos, valor T, p-value y conclusión.

- `Paired_T_Test_Dashboard.html`
  - Dashboard interactivo con gráficos y resumen visual.

## 3. Componentes del dashboard

### 3.1 Indicadores clave (KPIs)

- **Sample Size (N)**: número de pares de medición. Es el tamaño de la muestra.
- **Mean Difference**: promedio de las diferencias `A - B`. Indica la dirección y magnitud media de la discrepancia entre sistemas. Si es positivo, `A` tiende a ser mayor que `B`; si es negativo, `A` tiende a ser menor.
- **T-Statistic**: valor del estadístico T calculado para la muestra emparejada.
- **P-Value (two-sided)**: probabilidad asociada con el valor T en una prueba de dos colas.

### 3.2 Conclusión del test

Esta caja muestra la interpretación estadística con nivel de significancia α = 0.05.

- Si el p-value es menor a 0.05:
  - Rechaza la hipótesis nula.
  - Indica que los sistemas son significativamente diferentes.
- Si el p-value es mayor o igual a 0.05:
  - No se rechaza la hipótesis nula.
  - Indica que no se encontró evidencia suficiente de diferencia estadística.

### 3.3 Hipótesis

- **H₀**: `μ_A = μ_B` (las medias verdaderas son iguales).
- **H₁**: `μ_A ≠ μ_B` (las medias verdaderas son distintas).

Esta prueba es de dos colas.

## 4. Gráficos del dashboard

### 4.1 Summary Statistics

Este gráfico/tablero muestra las estadísticas principales de los datos:

- `N`
- `Mean`
- `StDev`
- `SE Mean`

Para cada sistema y para las diferencias.

### 4.2 Histogram of Differences

- Muestra la distribución de los valores `A - B`.
- La línea vertical en cero indica ausencia de diferencia.

Interpretación:

- Si la mayoría de los datos están cerca de cero, hay buena concordancia.
- Si la distribución está desplazada a la derecha o a la izquierda, existe sesgo sistemático.
- Si la distribución es amplia, hay más variabilidad entre los pares.

### 4.3 Individual Value Plot: System A vs System B

- Cada punto representa una observación emparejada.
- El eje X es el valor de `System A`.
- El eje Y es el valor de `System B`.
- La línea `Y = X` indica el lugar donde ambos sistemas coinciden exactamente.

Interpretación:

- Puntos cerca de la línea indican concordancia entre sistemas.
- Puntos por encima de la línea significan `A > B`.
- Puntos por debajo de la línea significan `A < B`.
- Cuanto más dispersos estén los puntos, mayor es la diferencia entre sistemas.

### 4.4 Boxplot of Differences

- Muestra la mediana, cuartiles y posible presencia de valores atípicos de las diferencias `A - B`.
- La línea horizontal en cero ayuda a ver si la mediana está centrada en cero.

Interpretación:

- Si la caja y la mediana están centradas cerca de cero, la diferencia es pequeña.
- Si la mediana está desplazada, hay sesgo sistemático.
- Las “bigotes” largos indican mayor variabilidad.

## 5. Cómo interpretar los resultados juntos

### 5.1 Coherencia entre gráficos y el valor p

- **Histograma centrado en cero + scatter cerca de la línea `A=B` + boxplot simétrico** → probable conclusión de **no diferencia significativa**.
- **Histograma desplazado + scatter sesgado + mediana de diferencias distinta de cero** → probable conclusión de **diferencia significativa**.

### 5.2 Contrastar con el resumen numérico

- Si el p-value < 0.05:
  - La diferencia media no es atribuible al azar.
  - Apoya el hallazgo de desajuste entre sistemas.

- Si el p-value ≥ 0.05:
  - No hay evidencia estadística de diferencia.
  - Puede haber pequeñas discrepancias, pero no suficientemente grandes para ser significativas.

### 5.3 Evaluar el intervalo de confianza

- El intervalo de confianza de 95% para la diferencia media se calcula como:
  - `media_diferencias ± t_critico * SE_d`
- Si el intervalo contiene cero:
  - Sugiere que la diferencia podría ser nula.
- Si el intervalo no contiene cero:
  - Sugiere que la diferencia es real.

## 6. Pasos prácticos después de la interpretación

1. Revisar si el sesgo observado es aceptable para la aplicación del proceso.
2. Verificar si la variabilidad entre pares es compatible con tolerancias de medición.
3. Si hay diferencia significativa, investigar:
   - calibración de instrumentos
   - condiciones de medición
   - definición de piezas/observaciones

## 7. Recomendaciones finales

- Usa el `Paired_T_Test_Summary.txt` para obtener los números exactos y la conclusión técnica.
- Usa el `Paired_T_Test_Dashboard.html` para ver visualmente el comportamiento y detectar patrones.
- Usa `paired_data.txt` si deseas revisar observación por observación.

---

Este reporte está diseñado para ayudarte a interpretar el dashboard completo del estudio de Paired T-Test y tomar decisiones fundamentadas en los resultados estadísticos.
