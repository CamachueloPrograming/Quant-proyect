# Quant Stock Screener — Stoxx Europe 600

🔗 **App en vivo**: https://quant-proyect-r9vs32bsy287xrcqy9tpvq.streamlit.app
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
-  **app.py** App de Streamlit
-  **requirements.txt** Dependencias
-  **factores_score_stoxx600.csv** Dataset final: factores, z-scores y score
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

# Quant Stock Screener — Stoxx Europe 600

🔗 **Live app**: https://quant-proyect-r9vs32bsy287xrcqy9tpvq.streamlit.app
*(replace with the real URL Streamlit Community Cloud gave you)*

## What this is

A tool that ranks the 600 companies in the **Stoxx Europe 600** index by combining
fundamental and technical factors into a composite score, statistically validated and
compared against a machine learning model (logistic regression with train/test split).

This is not investment advice — it's a data engineering and quantitative analysis
project applied to financial markets, built to demonstrate the full cycle: real data
acquisition, cleaning, methodological design, validation, and deployment.

## Tech stack

`Python` · `pandas` · `yfinance` · `scikit-learn` · `Streamlit` · `Google Colab` (development) · `Streamlit Community Cloud` (deploy)

## Methodology

### 1. Universe
600 companies from the Stoxx Europe 600, sourced from the public holdings of the
iShares STOXX Europe 600 UCITS ETF, with tickers mapped to Yahoo Finance format
according to their listing exchange (Xetra, Euronext, LSE, SIX, Nasdaq Nordic, etc.).

### 2. Factors (9 total)
- **Fundamental**: P/E, ROE, debt/equity, revenue growth
- **Technical**: 3/6/12-month momentum, RSI, distance to SMA200

All factors are normalized via **z-score** within the universe, with **winsorizing**
applied (capped at ±3 standard deviations) to prevent extreme outliers from
dominating the score.

### 3. Composite score
Weighted average of the 9 factors (with P/E and debt inverted, since "lower" is
better for both). Companies with missing factors receive a small penalty
proportional to how much data is missing, rather than being excluded or treated
as neutral.

### 4. Validation
- **Quintile analysis**: the universe is split into 5 groups by score and their
  average 12-month return is compared. Result: monotonic progression from -12.3%
  (worst quintile) to +63.9% (best quintile).
- **Logit model**: logistic regression on fundamental factors, with a train/test
  split (75/25), predicting whether a company beat the median return.
  Test accuracy: 56.3% (baseline: 50%).

## Limitations (acknowledged and documented, not hidden)

- **Circularity in quintile validation**: `momentum_12m` is itself one of the
  score's factors, so this validation confirms internal consistency rather than
  genuine out-of-sample predictive power. A true walk-forward backtest would
  require historical point-in-time fundamental and technical data, unavailable
  through free sources.
- **Data coverage**: ~90 companies (15%) lack a usable P/E, mainly because Yahoo
  Finance omits the field when a company has no positive net income, rather than
  reporting a negative value.
- **Financial sector**: banks and insurers typically lack a debt/equity ratio
  comparable to other sectors, due to the nature of their balance sheets.
- **Momentum bias**: as currently weighted, the score favors companies with
  strong price trends even when their valuation is expensive — it is not a pure
  "value" score.
- **~9% of the universe** (54 companies) ended up with partially or fully
  incomplete technical factors due to ticker format inconsistencies across data
  providers (share class notation on Nordic exchanges, UK tickers with their own
  built-in punctuation).

## Repository structure
-  **app.py** Streamlit app
-  **requirements.txt** Dependencies
-  **factores_score_stoxx600.csv** Final dataset: factors, z-scores, and score
-  **README.md**

## Running it locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Possible future improvements

- Point-in-time fundamental data to enable a genuine walk-forward backtest
- Expand the predictive model with additional algorithms (random forest, gradient boosting)
- Schedule automatic data refreshes (e.g. weekly, via GitHub Actions)
- Separate out a quality/profitability factor not solely dependent on P/E, to
  reduce the momentum bias

---

*Project developed as part of a self-directed quant finance learning plan,
combining Python, applied statistics, and data engineering best practices using
free data sources.*