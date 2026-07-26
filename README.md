# Quant Stock Screener — Stoxx Europe 600

🔗 **App en vivo**: https://tu-url-aqui.streamlit.app
*(sustituye por la URL real que te dio Streamlit Community Cloud)*

## Qué es esto

Una herramienta que rankea las 600 empresas del índice **Stoxx Europe 600** combinando
factores fundamentales y técnicos en un score compuesto, validado estadísticamente y
comparado contra un modelo de machine learning (regresión logística con train/test split).

No es una recomendación de inversión — es un proyecto de ingeniería de datos y análisis
cuantitativo aplicado a mercados financieros, construido para demostrar manejo de todo el
ciclo: obtención de datos reales, limpieza, diseño metodológico, validación y despliegue.

## Stack técnico

`Python` · `pandas` · `yfinance` · `scikit-learn` · `Streamlit` · `Google Colab` (desarrollo) · `Streamlit Community Cloud` (deploy)

## Metodología

### 1. Universo
600 empresas del Stoxx Europe 600, obtenidas de los holdings públicos del ETF
iShares STOXX Europe 600 UCITS, con tickers mapeados al formato de Yahoo Finance
según su bolsa de cotización (Xetra, Euronext, LSE, SIX, Nasdaq Nórdico, etc.).

### 2. Factores (9 en total)
- **Fundamentales**: P/E, ROE, deuda/equity, crecimiento de ingresos
- **Técnicos**: momentum a 3/6/12 meses, RSI, distancia a la SMA200

Todos los factores se normalizan por **z-score** dentro del universo, y se aplica
**winsorizing** (tope en ±3 desviaciones estándar) para evitar que valores atípicos
extremos dominen el score.

### 3. Score compuesto
Promedio ponderado de los 9 factores (con P/E y deuda invertidos, ya que "bajo" es
mejor en ambos). Las empresas con factores faltantes reciben una pequeña penalización
proporcional a cuántos datos les faltan, en vez de ser excluidas o tratadas como neutras.

### 4. Validación
- **Por quintiles**: se divide el universo en 5 grupos según el score y se compara su
  retorno medio a 12 meses. Resultado: progresión monótona de -12.3% (peor quintil) a
  +63.9% (mejor quintil).
- **Modelo logit**: regresión logística sobre los factores fundamentales, con
  train/test split (75/25), para predecir si una empresa superó la mediana de retorno.
  Accuracy en test: 56.3% (línea base: 50%).

## Limitaciones (leídas y documentadas, no ignoradas)

- **Circularidad en la validación por quintiles**: `momentum_12m` es uno de los propios
  factores del score, así que esta validación confirma consistencia interna, no poder
  predictivo real fuera de muestra. Un backtest walk-forward genuino requeriría datos
  fundamentales y técnicos point-in-time históricos, no disponibles en fuentes gratuitas.
- **Cobertura de datos**: ~90 empresas (15%) no tienen P/E utilizable, principalmente
  porque Yahoo Finance omite el campo cuando la empresa no tiene beneficio neto positivo,
  en vez de reportar un valor negativo.
- **Sector financiero**: los bancos y aseguradoras suelen carecer de un ratio
  deuda/equity comparable al del resto de sectores, por la naturaleza de su balance.
- **Sesgo hacia momentum**: tal como está ponderado, el score favorece a empresas con
  fuerte tendencia de precio incluso cuando su valoración es cara — no es un score
  "value" puro.
- **~9% del universo** (54 empresas) quedó con factores técnicos parcial o totalmente
  incompletos por inconsistencias de formato de ticker entre proveedores de datos
  (notación de clases de acciones en bolsas nórdicas, puntuación propia de tickers
  británicos).

## Estructura del repositorio
-  **app.py** # App de Streamlit
-  **requirements.txt # Dependencias**
-  **factores_score_stoxx600.csv # Dataset final: factores, z-scores y score**
-  **README.md**

## Cómo ejecutarlo en local

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Posibles mejoras futuras

- Datos fundamentales point-in-time para permitir un backtest walk-forward real
- Ampliar el modelo predictivo con más algoritmos (random forest, gradient boosting)
- Programar actualización automática de datos (ej. semanal, vía GitHub Actions)
- Separar un factor de calidad/rentabilidad que no dependa únicamente de P/E, para
  reducir el sesgo hacia momentum

---

*Proyecto desarrollado como parte de un plan de aprendizaje autodirigido en quant
finance, combinando Python, estadística aplicada y buenas prácticas de ingeniería de
datos con fuentes gratuitas.*