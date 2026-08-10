# Quant Stock Screener — Stoxx Europe 600

🔗 **App en vivo**: https://quant-proyect-r9vs32bsy287xrcqy9tpvq.streamlit.app

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
- Curvas de rendimiento y métricas resumen para comparación rápida.

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

Los factores con dirección negativa en valor (P/E y deuda/equity) se invierten para que
un mayor score siempre represente condición relativa mejor.

### 3. Validación del ranking

El dashboard valida el ranking con varias capas:

- Distribución de empresas por quintiles de score.
- Retorno medio a 12 meses por quintil.
- Métricas agregadas para top quintil vs bottom quintil.
- Modelo de regresión logística de soporte para comparar la capacidad de clasificación.

### 4. Simulación de cartera reciente

Se incorporó una sección adicional que usa los archivos:

- `curvas_rendimiento.csv`
- `metricas_rendimiento.csv`

Esta sección compara de forma directa:

- cartera long-only del top quintil
- cartera del bottom quintil
- universo equal-weight

### 5. Walk-forward histórico

La fase más avanzada es la simulación walk-forward anual, que usa los precios diarios
contenidos en `precios_stoxx600_max.csv` y el índice real `stoxx600_index.csv`.

Para cada corte anual:

- se calcula el score usando solo datos históricos hasta esa fecha
- se selecciona el quintil superior (Q5)
- se calcula el retorno en los siguientes 12 meses
- se compara con el rendimiento promedio del universo y con ^STOXX real

## Qué hace el dashboard

### Ranking por score ajustado

- Carga `factores_score_stoxx600.csv`.
- Permite filtrar por sector y país.
- Ordena las empresas por `score_ajustado`.
- Muestra tablas de resultados y métricas por quintil.

### Simulación reciente de cartera

- Carga `curvas_rendimiento.csv` y `metricas_rendimiento.csv`.
- Muestra una gráfica de rendimiento para top, bottom y benchmark.
- Presenta una tabla con métricas clave: retorno total, volatilidad, Sharpe y drawdown.

### Walk-forward histórico

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
streamlit run app.py
```

## Estructura del repositorio

- `app.py` — aplicación principal de Streamlit.
- `requirements.txt` — dependencias.
- `factores_score_stoxx600.csv` — dataset con factores y score.
- `curvas_rendimiento.csv` — curvas de rendimiento del top/bottom y benchmark.
- `metricas_rendimiento.csv` — métricas de rendimiento resumidas.
- `precios_stoxx600_max.csv` — precios diarios para la simulación walk-forward.
- `stoxx600_index.csv` — benchmark real ^STOXX.
- `analytics.py` — funciones para calcular retornos por quintil.
- `data_loader.py` — carga de datos y utilidades de lectura.
- `inspect_csv.py` — script auxiliar para inspeccionar archivos CSV.

## Posibles mejoras futuras

- Conseguir datos fundamentales point-in-time para un backtest walk-forward real.
- Añadir más modelos predictivos: random forest, gradient boosting, redes neuronales.
- Incluir métricas de riesgo adicionales: drawdown por periodo, beta, correlación con mercado.
- Automatizar descarga y actualización de datos con GitHub Actions.
- Separar un factor de calidad independiente de momentum y valoración.

---

*Proyecto desarrollado como ejercicio práctico de finanzas cuantitativas, ingeniería de datos
y visualización de resultados para el universo Stoxx 600.*
