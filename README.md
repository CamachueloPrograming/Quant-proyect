# Quant Stock Screener — Stoxx Europe 600

🔗 **App en vivo**: https://quant-proyect.streamlit.app

## Descripción general

Este proyecto es un dashboard de análisis cuantitativo para las 600 empresas del índice
**Stoxx Europe 600**. El objetivo es construir un sistema de ranking que combine factores
técnicos y fundamentales, visualizar su comportamiento y complementar esa visión con
una simulación walk-forward histórica.

La aplicación está hecha con **Streamlit** y se apoya en datasets locales para:

- Mostrar un ranking interactivo por `score_ajustado`.
- Validar resultados por quintiles.
- Comparar top-quintil vs bottom-quintil vs universo completo.
- Ejecutar una simulación walk-forward anual con cortes históricos.

> Este proyecto es exploratorio y no constituye asesoría de inversión.

## Fases del proyecto

### 1. Recolección y preparación de datos

La fase inicial consistió en reunir los datos necesarios para el universo Stoxx 600:

- Factores técnicos y fundamentales por empresa.
- Precios históricos diarios para el universo completo.
- Histórico del índice real `^STOXX`.

Los datos se normalizaron y se exportaron a CSVs que el dashboard consume directamente.

### 2. Cálculo del score compuesto

El `score_ajustado` está construido a partir de 9 factores:

- Fundamentos:
  - P/E
  - ROE
  - Deuda / Equity
  - Crecimiento de ingresos
- Técnicos:
  - Momentum 3 meses
  - Momentum 6 meses
  - Momentum 12 meses
  - RSI 14
  - Distancia a la SMA200

Cada factor se transforma con `z-score` y se aplica un Winsorizing a ±3 desviaciones
estándar para reducir el impacto de valores extremos.

El z-score se calcula **dentro de cada sector** usando la categoría `sector` de
`factores_score_stoxx600.csv`. Esto significa que una petrolera noruega se compara
con otras empresas de energía, y una tecnológica alemana se compara con otras
tecnológicas. Con esta normalización sectorial se busca aislar el mérito relativo
intrínseco de una empresa frente a movimientos macro sectoriales.

Los factores con dirección negativa en valor (P/E y deuda/equity) se invierten para que
un mayor score siempre represente condición relativa mejor.

### 3. Validación del ranking

El dashboard valida el ranking con varias capas:

- Distribución de empresas por quintiles de score.
- Retorno medio a 12 meses por quintil.
- Métricas agregadas para top quintil vs bottom quintil.
- Modelo de regresión logística de soporte para comparar la capacidad de clasificación.

### 4. Walk-forward histórico

La fase más avanzada es la simulación walk-forward anual, que usa los precios diarios
contenidos en `precios_stoxx600_max.csv` y el índice real `stoxx600_index.csv`.

Para cada corte anual:

- se calcula el score usando solo datos históricos hasta esa fecha
- los factores técnicos se normalizan por sector antes de agregarse en el score
- se selecciona el quintil superior (Q5)
- se calcula el retorno en los siguientes 12 meses
- se compara con el rendimiento promedio del universo y con ^STOXX real

Al normalizar por sector, el ranking pone en primer plano a las empresas que
realmente destacan dentro de su categoría, en lugar de premiar sectores enteros
que se han comportado bien por razones macroeconómicas.

## Qué hace el dashboard

### Ranking por score ajustado

- Carga `factores_score_stoxx600.csv`.
- Permite filtrar por sector y país.
- Ordena las empresas por `score_ajustado`.
- Muestra tablas de resultados y métricas por quintil.

### Walk-forward histórico

- Carga `precios_stoxx600_max.csv` y `stoxx600_index.csv`.
- Genera cortes anuales desde 2001 hasta 2025.
- Calcula el score con datos previos a cada corte.
- Produce:
  - curva de capital acumulado ($100 iniciales)
  - curva logarítmica para analizar crecimiento relativo
  - gráfico de retornos anuales por corte
  - métricas CAGR y valor p long-short

- Carga `precios_stoxx600_max.csv` y `stoxx600_index.csv`.
- Genera cortes anuales desde 2001 hasta 2025.
- Calcula el score con datos previos a cada corte.
- Produce:
  - curva de capital acumulado ($100 iniciales)
  - curva logarítmica para analizar crecimiento relativo
  - gráfico de retornos anuales por corte
  - métricas CAGR y valor p long-short

## Interpretación de resultados

- Una **curva acumulada** más alta para Q5 que para el benchmark sugiere que el
  top quintil estuvo consistentemente por delante en los cortes analizados.
- La **curva logarítmica** hace que los cambios porcentuales similares mantengan
  distancias visuales similares, lo que facilita comparar el comportamiento en
  etapas distintas del tiempo.
- Si la gráfica de **retornos anuales por corte** muestra barras muy dispersas,
  eso indica mayor volatilidad de resultados entre años.
- El **valor p long-short Q5-Q1** ayuda a distinguir si la diferencia de retornos
  podría ser aleatoria. Un valor p bajo indica una señal más sólida estadísticamente.

## Detalles técnicos importantes

### Preprocesamiento de precios

`load_close_prices()` lee un CSV de precios con encabezados de dos niveles y extrae
la columna `Close` para cada ticker.

### Manejo del índice ^STOXX

`load_stoxx_index()` lee `stoxx600_index.csv` saltando las primeras dos filas del archivo,
coerciendo la columna de fecha, y descartando filas con fechas inválidas.

### Cálculo de factores en un corte

`compute_factors_at_cutoff()` calcula momentum, RSI y distancia a SMA200 usando solo el
histórico anterior al corte, respetando el principio de no mirar datos futuros.

### Walk-forward anual

`simulate_walkforward()`:

- construye cortes anuales con `get_annual_cutoffs()`
- calcula scores y quintiles solo con datos anteriores al corte
- evalúa retornos de Q5, Q1, universo y ^STOXX
- genera curvas de capital acumulado y métricas comparativas

## Problemas y desafíos que resolvimos

### 1. Calidad y cobertura de datos

- Muchos tickers del Stoxx 600 no tienen datos completos en Yahoo Finance.
- Aproximadamente 15% de las empresas carecen de P/E usable.
- Hay inconsistencias de ticker por clases de acciones europeas y notación local.

### 2. Validación circular por momentum

- El factor `momentum_12m` forma parte del score.
- Esto significa que el análisis de quintiles muestra consistencia interna más que
  probabilidad de predicción absoluta.
- Lo documentamos claramente en el dashboard y en el README.

### 3. Estructura compleja de CSVs de precios

- `precios_stoxx600_max.csv` tiene encabezados multi-nivel.
- `stoxx600_index.csv` no es un CSV estándar: requiere saltar filas y convertir fechas.
- Estas necesidades se resolvieron con parsing específico en `app.py`.

### 4. Presentación visual y explicación de la escala logarítmica

- Añadimos texto explicativo en el dashboard para que el usuario entienda que la
  curva logarítmica no altera resultados, solo mejora la comparabilidad relativa.
- También mostramos unidades claras en todas las gráficas de walk-forward.

## Limitaciones actuales

- Los resultados son históricos y no garantizan rendimientos futuros.
- La simulación walk-forward se basa en un solo camino histórico del mercado.
- El dataset no incluye datos fundamentales point-in-time reales.
- El long-short Q5-Q1 sirve como diagnóstico interno, no como estrategia final.

## Walk-forward ampliado: validación del score técnico (2001-2025)

### Resumen ejecutivo

Se amplió la validación walk-forward original (3 cortes) a **25 cortes anuales
no solapados (2001-2025)**, usando solo los 5 factores técnicos (momentum
3/6/12m, RSI14, distancia a SMA200) — los fundamentales se excluyeron de
esta fase porque yfinance no ofrece histórico point-in-time de ellos, y
usarlos habría introducido fuga de información.

**Resultado principal:** el score técnico puro **no muestra poder
predictivo estadísticamente significativo** en ningún horizonte probado
(3, 6 o 12 meses). Sin embargo, una simulación de cartera basada en ese
mismo score sí bate a un benchmark equal-weight en el acumulado de 25 años
— una aparente contradicción que se explica más abajo.

---

### 1. De 3 a 25 cortes: por qué importa el tamaño de muestra

Con solo 3 observaciones, un resultado favorable por casualidad es
indistinguible de una señal real. Al escalar a 25 años independientes
(fechas de corte espaciadas exactamente el horizonte de evaluación, para
que ninguna ventana se solape con otra), esa señal aparente se diluyó
hasta quedar dentro del rango esperable por azar.

**Lección del proyecto:** una validación con pocas observaciones puede
sugerir que un modelo "funciona" cuando en realidad el ruido de mercado
se ha confundido con señal. Ampliar la muestra no es un paso opcional —
es lo que separa una validación real de una ilusión estadística.

### 2. Resultados por horizonte

En la muestra ampliada (25 cortes) las métricas principales fueron:

- 3 meses: Accuracy 49.0% (p=0.33), long-short medio anual -0.08% (p=0.96)
- 6 meses: Accuracy 50.4% (p=0.72), long-short medio anual +0.16% (p=0.96)
- 12 meses: Accuracy 50.8% (p=0.54), long-short medio anual +0.94% (p=0.86)

Ninguno de estos resultados es estadísticamente significativo.

### 3. Momentum crash de 2009

El experimento de long-short (comprar Q5, vender en corto Q1 — diagnóstico de
validación, no una estrategia recomendada) se desplomó un 82% en el corte de
2009: las empresas más castigadas del año anterior (Q1) rebotaron con más
fuerza que las de mejor score (Q5) en la recuperación post-crisis financiera.
Este patrón de reversión brusca del momentum tras caídas severas está
documentado en la literatura académica y su presencia valida que el motor
captura dinámicas reales, aunque no suficientes para predecir con fiabilidad.

### 4. Simulación de cartera: long-only Q5 vs benchmarks

Estrategia propuesta: 100% larga, comprar a partes iguales el quintil top (Q5)
cada año, rebalanceo anual. Resultados (2001-2025, $100 iniciales):

- Long-only Q5: CAGR ≈ 12.8% → Capital final ≈ $2,020
- Benchmark equal-weight: CAGR ≈ 10.9% → Capital final ≈ $1,336
- Índice real ^STOXX (desde 2004/2005 en datos de Yahoo): CAGR ≈ 3.6% → $209
- Experimento long-short Q5-Q1 (no recomendado): capital final ≈ $29

Esta diferencia acumulada no contradice la falta de predictividad anual:
un edge medio pequeño y no significativo puede dar lugar a grandes diferencias
por composición a lo largo de 25 años; son preguntas distintas (fiabilidad
anual vs camino histórico observado).

### 5. Efecto tamaño y construcción de benchmark

La mayor parte de la brecha entre la estrategia y el índice real se explica
por la construcción cap-weighted del índice, que concentra peso en mega-caps.
Un benchmark equal-weight (y la propia estrategia Q5) reparte capital
más uniformemente y se beneficia del rebalanceo, que tiende a comprar
relativamente companies más pequeñas que, históricamente, han rendido
mejor a largo plazo (efecto tamaño).

### 6. Sesgo de supervivencia

El universo usado se construyó a partir de la composición actual (2026) con
histórico hacia atrás; por tanto, empresas que desaparecieron en el camino
no están incluidas en los cortes históricos. Esto infla los resultados en
relación a un índice que sí refleja entradas y salidas históricas. Una
comprobación parcial (2021-2025) muestra reducción de la ventaja de la
estrategia (de +1.9 a +0.9 p.p. de CAGR), consistente con que el sesgo de
supervivencia puede estar influyendo.

### 7. Conclusión y presentación en la app

El score técnico puro (momentum + RSI + distancia a SMA200) **no tiene
poder predictivo demostrado de forma robusta**. En la app se presenta este
resultado junto con advertencias explícitas (fuga de información potencial,
sesgo de supervivencia, ausencia de costes de transacción) y la diferencia
entre significancia estadística anual y efecto acumulado en el camino histórico.

## Requisitos

- Python 3.12+
- `streamlit`
- `pandas`
- `numpy`
- `scipy`

Instala dependencias con:

```bash
pip install -r requirements.txt
```

## Cómo ejecutar

```bash
streamlit run src/app.py
```

## Estructura del repositorio

- `src/` — código Python de la aplicación.
  - `src/app.py` — aplicación principal de Streamlit.
  - `src/analytics.py` — funciones para calcular retornos por quintil.
  - `src/data_loader.py` — carga de datos y utilidades de lectura.
  - `src/inspect_csv.py` — script auxiliar para inspeccionar archivos CSV.
- `data/` — datasets del proyecto.
  - `data/factores_score_stoxx600.csv` — dataset con factores y score.
  - `data/precios_stoxx600_max.csv` — precios diarios para la simulación walk-forward.
  - `data/stoxx600_index.csv` — benchmark real ^STOXX.
  - `data/precios_stoxx600.csv` — precios adicionales de historial.
  - `data/tecnicos_stoxx600.csv` — factores técnicos para el universo.
  - `data/fundamentales_stoxx600.csv` — factores fundamentales del universo.

## Posibles mejoras futuras

- Conseguir datos fundamentales point-in-time para un backtest walk-forward real.
- Añadir más modelos predictivos: random forest, gradient boosting, redes neuronales.
- Incluir métricas de riesgo adicionales: drawdown por periodo, beta, correlación con mercado.
- Automatizar descarga y actualización de datos con GitHub Actions.
- Separar un factor de calidad independiente de momentum y valoración.

---

*Proyecto desarrollado como ejercicio práctico de finanzas cuantitativas, ingeniería de datos
y visualización de resultados para el universo Stoxx 600.*
