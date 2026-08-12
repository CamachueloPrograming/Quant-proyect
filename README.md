# Stoxx 600 Quant Screener

This repository contains a Streamlit dashboard for quantitative analysis of the
**Stoxx Europe 600** universe. It is designed to show a sector-neutral ranking
framework, validate the ranking by quintile, and support the process with an
annual walk-forward simulation.

https://stoxx600-quant-screener.streamlit.app

The app uses local datasets to:

- Display an interactive ranking based on an adjusted score.
- Validate the score with quintile performance metrics.
- Compare the top quintile to the overall universe and the real ^STOXX benchmark.
- Run a historical walk-forward simulation using annual cutoffs.

> This project is exploratory and is not investment advice.

## Core concepts

### Sector-neutral z-score normalization

Scores are computed from technical and fundamental factors, and the z-scores are
calculated within each sector. This means each company is compared against its
sector peers instead of the full universe, so the ranking highlights relative
strength within a sector rather than sector-level momentum.

### Adjusted score

The adjusted score is built from several factor inputs, including:

- P/E ratio
- ROE
- Debt / Equity
- Revenue growth
- 3-month momentum
- 6-month momentum
- 12-month momentum
- RSI 14
- Distance to SMA 200

Negative directional factors such as P/E and Debt/Equity are inverted so that a
higher score always reflects stronger relative fundamentals or momentum.

### Walk-forward simulation

The annual walk-forward simulation uses the historical price dataset in
`data/stoxx600_prices_max.csv` and the real ^STOXX index in
`data/stoxx600_real_index.csv`.

For each annual cutoff:

- factors are computed using only data available before the cutoff
- technical factors are normalized by sector
- the top quintile (Q5) is selected
- the next 12-month return is measured
- the Q5 performance is compared to the equal-weight universe and ^STOXX

## What the dashboard shows

### Ranking section

- Loads `data/stoxx600_factor_scores.csv`
- Supports sector and country filtering
- Sorts companies by `score_ajustado`
- Displays the universe table and technical factor details
- Shows average Q5 returns across the current filtered universe

### Walk-forward section

- Loads `data/stoxx600_prices_max.csv` and `data/stoxx600_real_index.csv`
- Builds yearly cutoffs from 2001 through 2025
- Computes a sector-neutral technical score using only prior data
- Produces:
  - cumulative equity curves for the strategy, the universe benchmark, and ^STOXX
  - logarithmic equity curves for relative comparison
  - annual return bars by cutoff
  - CAGR metrics and a long-short p-value

## Important notes

- `score_ajustado` is the dataset column used by the current CSV inputs.
- The ranking validation chart is approximate and not a true point-in-time backtest.
- Momentum-based factors are part of the score, so the validation reflects internal
  consistency rather than a fully independent predictive test.
- Many Stoxx 600 companies have incomplete factor coverage due to data limitations.

## Technical details

### Price preprocessing

`load_close_prices()` reads the multi-level CSV `data/stoxx600_prices_max.csv`
and extracts the `Close` price series for each ticker.

### STOXX index handling

`load_stoxx_index()` reads `data/stoxx600_real_index.csv`, skips the first two rows,
parses dates, and drops invalid entries.

### Annual cutoff simulation

`simulate_walkforward()`:

- creates yearly cutoffs with `get_annual_cutoffs()`
- computes factor z-scores by sector via `group_zscore_winsorize()`
- assigns quintiles and evaluates returns for Q5, Q1, and the universe
- calculates cumulative curves and summary metrics

## Limitations

- Historical results do not guarantee future outcomes.
- The simulation uses a single historical path and a fixed current universe.
- The dataset does not include point-in-time historical fundamentals.
- The long-short Q5-Q1 result is a diagnostic, not a recommended trading strategy.

## Requirements

- Python 3.12+
- `streamlit`
- `pandas`
- `numpy`
- `scipy`

Install dependencies with:

```bash
pip install -r requirements.txt
```

## Run the dashboard

From the repository root:

```bash
streamlit run app.py
```

## Repository structure

- `app.py` — root wrapper that launches `src/app.py`
- `src/` — Python application code
  - `src/app.py` — main Streamlit dashboard
  - `src/analytics.py` — quintile return helper
  - `src/data_loader.py` — CSV loading utility
  - `src/inspect_csv.py` — helper for inspecting CSV files
- `data/` — project datasets
  - `data/stoxx600_factor_scores.csv`
  - `data/stoxx600_prices_max.csv`
  - `data/stoxx600_real_index.csv`
  - `data/stoxx600_prices.csv`
  - `data/stoxx600_technical.csv`
  - `data/stoxx600_fundamentals.csv`

## Future improvements

- Capture point-in-time fundamentals for a true backtest.
- Add alternative signal models such as random forest and gradient boosting.
- Include additional risk metrics: drawdown, beta, and correlation.
- Automate dataset refresh using GitHub Actions.
- Separate valuation and momentum signals more clearly.

## Notes

This project is a quantitative finance exercise for the Stoxx Europe 600 universe.
It is not investment advice.
