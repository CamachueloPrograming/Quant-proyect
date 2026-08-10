# Quant Stock Screener — Stoxx Europe 600

🔗 **App en vivo**: https://quant-proyect-r9vs32bsy287xrcqy9tpvq.streamlit.app

## Qué es esto

Aplicación de Streamlit que analiza las 600 empresas del índice **Stoxx Europe 600**.
Esta herramienta combina factores fundamentales y técnicos en un `score_ajustado`, muestra
un ranking interactivo y ofrece una simulación walk-forward histórica del quintil superior.

**No es asesoría financiera.** Es un proyecto de ingeniería de datos y análisis cuantitativo.

## Secciones del dashboard

- **Ranking por score ajustado**
  - Filtros por sector y país.
  - Tabla ordenada por score con columnas clave y métricas técnicas.
  - Análisis de quintiles para comparar rendimiento medio.
- **Simulación de cartera reciente**
  - Basada en `curvas_rendimiento.csv` y `metricas_rendimiento.csv`.
  - Compara top quintil, bottom quintil y benchmark equal-weight.
- **Walk-forward histórico 2001-2025**
  - Cada corte anual calcula el score con datos solo disponibles hasta esa fecha.
  - Estrategia long-only sobre el quintil superior (Q5).
  - Compara con benchmark equal-weight y el índice real **^STOXX**.
  - Incluye gráficas de capital acumulado, capital en escala logarítmica y retornos anuales.

## Datos usados

- `factores_score_stoxx600.csv`: dataset principal con factores, z-scores y score.
- `curvas_rendimiento.csv`: curvas de rendimiento para top y bottom quintiles más benchmark.
- `metricas_rendimiento.csv`: métricas resumen de retorno, volatilidad, Sharpe y drawdown.
- `precios_stoxx600_max.csv`: precios diarios para la simulación walk-forward.
- `stoxx600_index.csv`: histórico del índice real ^STOXX.

## Metodología resumida

### Score compuesto

- Combina 9 factores: 4 fundamentales y 5 técnicos.
- Normaliza los factores con **z-score** y aplica **winsorizing**.
- Invierte P/E y deuda/equity porque valores menores son mejores.
- Penaliza datos faltantes en lugar de excluir empresas.

### Validación

- **Análisis de quintiles**: compara el retorno medio por grupo de score.
- **Modelo logit**: regresión logística para evaluar la capacidad de clasificación.
- **Walk-forward anual**: cortes desde 2001 a 2025 usando solo datos históricos
  disponibles hasta cada corte.

## Explicación de los gráficos walk-forward

- **Curva acumulada**: capital relativo con $100 iniciales.
- **Curva logarítmica**: usa `log(valor de capital)` para que los cambios porcentuales
  sean más comparables a lo largo del tiempo.
- **Retornos anuales por corte**: porcentaje de rendimiento de 12 meses por cada corte.

## Limitaciones

- `momentum_12m` forma parte del score, por lo que la validación de quintiles refleja
  consistencia interna más que predictibilidad absoluta.
- El walk-forward histórico no garantiza resultados futuros.
- El long-short Q5-Q1 se muestra solo como diagnóstico interno.
- Los datos de Yahoo Finance limitan algunos campos, especialmente P/E.

## Requisitos

- Python 3.12+
- `streamlit`
- `pandas`
- `numpy`
- `scipy`

## Cómo ejecutar

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Estructura del repositorio

- `app.py` — aplicación principal de Streamlit.
- `requirements.txt` — dependencias.
- `factores_score_stoxx600.csv` — dataset con factores y score.
- `curvas_rendimiento.csv` — curvas de rendimiento.
- `metricas_rendimiento.csv` — métricas resumen.
- `precios_stoxx600_max.csv` — precios diarios para walk-forward.
- `stoxx600_index.csv` — benchmark real ^STOXX.
- `inspect_csv.py` — script auxiliar para inspeccionar CSVs de resultados.

## Mejoras futuras

- Obtener datos point-in-time para un walk-forward real.
- Añadir más modelos predictivos (random forest, gradient boosting).
- Automatizar la actualización de datos con GitHub Actions.
- Añadir un factor de calidad independiente de momentum.

---

*Proyecto desarrollado como parte de un aprendizaje autodirigido en finanzas cuantitativas.*
