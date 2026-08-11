import numpy as np
import pandas as pd
import streamlit as st
from pathlib import Path

from analytics import build_quintile_returns
from data_loader import load_data

try:
    from scipy import stats
except ImportError:
    stats = None

@st.cache_data
def load_close_prices(path: str) -> pd.DataFrame:
    raw = pd.read_csv(path, header=[0, 1], index_col=0, parse_dates=True)
    close = raw.xs("Close", axis=1, level=1)
    return close.sort_index()

@st.cache_data
def load_stoxx_index(path: str) -> pd.Series:
    df = pd.read_csv(
        path,
        skiprows=2,
        names=["Date", "Close", "High", "Low", "Open", "Volume"],
        engine="python",
    )
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.dropna(subset=["Date"]).set_index("Date")
    return df["Close"].sort_index()


def compute_rsi(price_series: pd.Series, period: int = 14) -> pd.Series:
    delta = price_series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(period, min_periods=period).mean()
    avg_loss = loss.rolling(period, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def zscore_winsorize(s: pd.Series, cap: float = 3.0) -> pd.Series:
    mu, sd = s.mean(), s.std()
    if sd == 0 or np.isnan(sd):
        return s * 0
    return ((s - mu) / sd).clip(-cap, cap)


def group_zscore_winsorize(factors: pd.DataFrame, sector_map: pd.Series | None = None, cap: float = 3.0) -> pd.DataFrame:
    """Compute z-scores within each sector group.

    If sector_map is provided, each company is compared only against its sector
    peers. If no sector map is available, fallback to universe-level z-scores.
    """
    if sector_map is None:
        return factors.apply(zscore_winsorize)

    sector_series = sector_map.reindex(factors.index).fillna("Unknown")
    z_groups = []
    for _, group in factors.groupby(sector_series, sort=False):
        z_groups.append(group.apply(zscore_winsorize))

    if z_groups:
        return pd.concat(z_groups).reindex(factors.index)
    return factors.apply(zscore_winsorize)


@st.cache_data
def load_sector_map(path: str = "data/stoxx600_factor_scores.csv") -> pd.Series:
    """Load ticker-to-sector mapping for sector-level normalization."""
    try:
        metadata = pd.read_csv(path, usecols=["yahoo_ticker", "sector"], dtype={"yahoo_ticker": str, "sector": str})
        metadata = metadata.dropna(subset=["yahoo_ticker"])
        return metadata.set_index("yahoo_ticker")["sector"]
    except Exception:
        return pd.Series(dtype="object")


def compute_factors_at_cutoff(df: pd.DataFrame, cutoff_pos: int, min_history: int = 252) -> pd.DataFrame:
    window_raw = df.iloc[:cutoff_pos + 1]
    window = window_raw.ffill()
    last = window.iloc[-1]

    def px_back(n: int) -> pd.Series:
        if len(window) <= n:
            return pd.Series(np.nan, index=window.columns)
        return window.iloc[-1 - n]

    mom_3m = last / px_back(63) - 1
    mom_6m = last / px_back(126) - 1
    mom_12m = last / px_back(252) - 1
    sma200 = window.iloc[-200:].mean() if len(window) >= 200 else pd.Series(np.nan, index=window.columns)
    dist_sma200 = last / sma200 - 1
    rsi_last = window.apply(compute_rsi, period=14).iloc[-1]

    factors = pd.DataFrame(
        {
            "mom_3m": mom_3m,
            "mom_6m": mom_6m,
            "mom_12m": mom_12m,
            "rsi14": rsi_last,
            "dist_sma200": dist_sma200,
        }
    )
    valid_history = window_raw.notna().sum() >= min_history
    factors = factors[valid_history].dropna(how="any")
    return factors


def get_annual_cutoffs(index: pd.DatetimeIndex, start_year: int = 2001, end_year: int = 2025) -> list[pd.Timestamp]:
    cutoffs = []
    for year in range(start_year, end_year + 1):
        target = pd.Timestamp(f"{year}-01-01")
        candidates = index[index >= target]
        if len(candidates):
            cutoffs.append(candidates[0])
    return cutoffs


def simulate_walkforward(
    close: pd.DataFrame,
    stoxx_index: pd.Series | None = None,
    start_year: int = 2001,
    end_year: int = 2025,
    min_history: int = 252,
    horizon: int = 252,
) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    idx = close.index
    cutoffs = get_annual_cutoffs(idx, start_year, end_year)
    results = []
    sector_map = load_sector_map()

    # In the walk-forward simulation, the technical score uses sector-normalized z-scores.
    # This prevents the ranking from simply favoring entire sectors with strong momentum
    # instead of companies that stand out within their sector.
    for cutoff in cutoffs:
        cpos = idx.get_loc(cutoff)
        fpos = cpos + horizon
        if fpos >= len(idx):
            continue

        factors = compute_factors_at_cutoff(close, cpos, min_history=min_history)
        if len(factors) < 50:
            continue

        z = group_zscore_winsorize(factors, sector_map=sector_map)
        score = z.mean(axis=1)

        p0 = close.iloc[: cpos + 1].ffill().iloc[-1][score.index]
        p1 = close.iloc[: fpos + 1].ffill().iloc[-1][score.index]
        fwd_ret = p1 / p0 - 1
        valid = fwd_ret.notna() & p0.notna()
        score, fwd_ret = score[valid], fwd_ret[valid]
        if len(score) < 50:
            continue

        quintile = pd.qcut(score, 5, labels=[1, 2, 3, 4, 5], duplicates="drop")
        q5_ret = fwd_ret[quintile == 5].mean()
        q1_ret = fwd_ret[quintile == 1].mean()

        results.append(
            {
                "cutoff": cutoff,
                "fwd_date": idx[fpos],
                "num_companies": len(score),
                "q1_ret": q1_ret,
                "q5_ret": q5_ret,
                "long_short": q5_ret - q1_ret,
                "universe_avg_ret": fwd_ret.mean(),
            }
        )

    df_res = pd.DataFrame(results)
    if df_res.empty:
        return df_res, pd.DataFrame(), {}

    if stoxx_index is not None and not stoxx_index.empty:
        def get_idx_price(date: pd.Timestamp) -> float:
            if date < stoxx_index.index.min():
                return np.nan
            return stoxx_index.asof(date)

        df_res["stoxx600_ret"] = [
            get_idx_price(row["fwd_date"]) / get_idx_price(row["cutoff"]) - 1
            for _, row in df_res.iterrows()
        ]
    else:
        df_res["stoxx600_ret"] = np.nan

    equity_strategy = [100.0]
    equity_benchmark = [100.0]
    equity_long_short = [100.0]
    for _, row in df_res.iterrows():
        equity_strategy.append(equity_strategy[-1] * (1 + row["q5_ret"]))
        equity_benchmark.append(equity_benchmark[-1] * (1 + row["universe_avg_ret"]))
        equity_long_short.append(equity_long_short[-1] * (1 + row["long_short"]))

    equity_stoxx600 = [np.nan] * (len(df_res) + 1)
    primer_valido = df_res["stoxx600_ret"].first_valid_index()
    if primer_valido is not None:
        equity_stoxx600[primer_valido] = 100.0
        for i in range(primer_valido, len(df_res)):
            ret = df_res["stoxx600_ret"].iloc[i]
            equity_stoxx600[i + 1] = equity_stoxx600[i] * (1 + ret) if pd.notna(ret) else equity_stoxx600[i]

    dates = [df_res["cutoff"].iloc[0] - pd.DateOffset(years=1)] + list(df_res["cutoff"])
    curve = pd.DataFrame(
        {
            "date": dates,
            "strategy_long_only_Q5": equity_strategy,
            "benchmark_universe_equalweight": equity_benchmark,
            "benchmark_stoxx600_real": equity_stoxx600,
            "long_short_experiment": equity_long_short,
        }
    )

    n_years = len(df_res)
    cagr_estrategia = (equity_strategy[-1] / 100) ** (1 / n_years) - 1
    cagr_bench = (equity_benchmark[-1] / 100) ** (1 / n_years) - 1
    cagr_stoxx600 = (
        (equity_stoxx600[-1] / 100) ** (1 / (len(df_res) - primer_valido)) - 1
        if primer_valido is not None
        else float("nan")
    )

    p_ls = None
    if stats is not None and len(df_res) > 1:
        _, p_ls = stats.ttest_1samp(df_res["long_short"].values, 0.0)

    metrics = {
        "cagr_estrategia": cagr_estrategia,
        "cagr_bench": cagr_bench,
        "cagr_stoxx600": cagr_stoxx600,
        "final_capital_strategy": equity_strategy[-1],
        "final_capital_benchmark": equity_benchmark[-1],
        "final_capital_stoxx600": equity_stoxx600[-1] if primer_valido is not None else np.nan,
        "final_capital_long_short": equity_long_short[-1],
        "p_value_long_short": p_ls,
        "cutoffs": len(df_res),
    }

    return df_res, curva, metrics

st.set_page_config(page_title="Sector-Neutral Stoxx Europe 600 Screener", layout="wide", page_icon="📊")

st.title("Sector-Neutral Stoxx Europe 600 Screener")
with st.expander("Methodology"):
    st.write(
        "The `score_ajustado` combines 9 technical and fundamental factors normalized by z-score. "
        "The quintile chart is an approximate validation and not a point-in-time backtest, "
        "because `momentum_12m` is one of the factors used in the score. "
        "Around 90 companies have at least one incomplete factor due to free Yahoo Finance data limitations."
    )

st.markdown("Interactive ranking view for companies by adjusted score.")

csv_path = "data/stoxx600_factor_scores.csv"

try:
    df = load_data(csv_path)
except FileNotFoundError:
    st.error(f"Data file not found: {csv_path}")
    st.stop()

if "score_ajustado" not in df.columns:
    st.error("The CSV does not contain the required 'score_ajustado' column.")
    st.stop()

# Sidebar filters
st.sidebar.header("Filters")

has_sector = "sector" in df.columns
has_country = "pais" in df.columns

sector_options = sorted(df["sector"].dropna().unique()) if has_sector else []
country_options = sorted(df["pais"].dropna().unique()) if has_country else []

if has_sector:
    selected_sectors = st.sidebar.multiselect("Sector", sector_options, default=sector_options)
else:
    st.sidebar.info("The CSV does not contain a 'sector' column.")
    selected_sectors = None

if has_country:
    selected_countries = st.sidebar.multiselect("Country", country_options, default=country_options)
else:
    st.sidebar.info("The CSV does not contain a country ('pais') column.")
    selected_countries = None

min_score = float(df["score_ajustado"].min())
max_score = float(df["score_ajustado"].max())
selected_score = st.sidebar.slider(
    "Adjusted score range",
    min_value=min_score,
    max_value=max_score,
    value=(min_score, max_score),
    step=(max_score - min_score) / 100 if max_score > min_score else 0.01,
)

filtered = df.copy()
if has_sector and selected_sectors:
    filtered = filtered[filtered["sector"].isin(selected_sectors)]
if has_country and selected_countries:
    filtered = filtered[filtered["pais"].isin(selected_countries)]
filtered = filtered[filtered["score_ajustado"].between(selected_score[0], selected_score[1])]
filtered = filtered.sort_values(by="score_ajustado", ascending=False)

if not filtered.empty:
    quintile_summary = build_quintile_returns(filtered)

    best_row = filtered.iloc[0]
    best_name = (
        best_row["nombre"]
        if "nombre" in best_row.index and pd.notna(best_row["nombre"])
        else best_row["yahoo_ticker"]
    )
    quintile_5_return = None
    if not quintile_summary.empty and 5 in quintile_summary["quintile"].values:
        quintile_5_return = float(
            quintile_summary.loc[quintile_summary["quintile"] == 5, "avg_return_12m"].iloc[0]
        )

    col1, col2, col3 = st.columns(3)
    col1.metric("Total companies", len(filtered))
    col2.metric("Best score", f"{best_name} ({best_row['score_ajustado']:.3f})")
    col3.metric("Average Q5 return", f"{quintile_5_return:.3f}" if quintile_5_return is not None else "N/A")
else:
    st.info("No companies match the selected filters.")

st.markdown("---")
st.subheader("Adjusted score ranking")

if not filtered.empty:
    display_df = filtered.copy()
    if "nombre" not in display_df.columns and "yahoo_ticker" in display_df.columns:
        display_df["nombre"] = display_df["yahoo_ticker"]

    key_columns = [col for col in ["yahoo_ticker", "nombre", "sector", "pais", "score_ajustado"] if col in display_df.columns]
    technical_columns = [
        col for col in display_df.columns
        if col.startswith("z_") or col in {"pe_ratio", "roe", "debt_to_equity", "revenue_growth", "momentum_3m", "momentum_6m", "momentum_12m", "rsi", "dist_sma200"}
    ]
    display_df = display_df.rename(columns={"nombre": "name", "pais": "country", "score_ajustado": "adjusted_score"})
    key_columns = [col for col in ["yahoo_ticker", "name", "sector", "country", "adjusted_score"] if col in display_df.columns]
    other_columns = [col for col in display_df.columns if col not in key_columns + technical_columns]
    ordered_columns = key_columns + other_columns + technical_columns
    display_df = display_df[ordered_columns].reset_index(drop=True)

    for col in display_df.columns:
        if pd.api.types.is_numeric_dtype(display_df[col]):
            display_df[col] = display_df[col].round(3)

    st.dataframe(display_df, use_container_width=True, hide_index=True)

    with st.expander("Technical details (z-scores and factors)"):
        technical_display = display_df[key_columns + technical_columns].copy()
        st.dataframe(technical_display, use_container_width=True, hide_index=True)
else:
    st.info("No data available to display the table.")

if not filtered.empty and "momentum_12m" in filtered.columns:
    quintile_summary = build_quintile_returns(filtered)
    st.subheader("Score quintile returns")
    st.bar_chart(
        quintile_summary.set_index("quintile")["avg_return_12m"],
        use_container_width=True,
    )

st.subheader("Historic walk-forward 2001-2025: top quintile strategy vs benchmarks")
st.write(
    "This dashboard section has two clearly separated parts:\n"
    "1) The initial validation uses recent historical data (~3 years) from the `stoxx600_factor_scores.csv` dataset. "
    "It computes adjusted scores per company using only the available technical and fundamental factors: "
    "momentum 3/6/12m, RSI14, and distance to SMA200, together with the available fundamental factors. "
    "This shows the current universe ranking behavior, but it is not a full point-in-time walk-forward backtest.\n"
    "2) The annual walk-forward simulation uses daily price history from 2001 through 2025. "
    "Each yearly cutoff computes the score using data available up to that date and then simulates the next 12 months' return for the top quintile (Q5), "
    "comparing it against the equal-weight universe and the real ^STOXX index."
)

price_path = Path("data/stoxx600_prices_max.csv")
index_path = Path("data/stoxx600_real_index.csv")

if price_path.exists():
    try:
        close = load_close_prices(str(price_path))
        stoxx600_index = load_stoxx_index(str(index_path)) if index_path.exists() else pd.Series(dtype="float64")
        df_walk, curva_walk, walk_metrics = simulate_walkforward(close, stoxx600_index)
    except Exception as exc:
        st.error(f"Could not run walk-forward simulation: {exc}")
        df_walk = pd.DataFrame()
        curva_walk = pd.DataFrame()
        walk_metrics = {}
else:
    st.warning("The price history file for walk-forward was not found: data/stoxx600_prices_max.csv")
    df_walk = pd.DataFrame()
    curva_walk = pd.DataFrame()
    walk_metrics = {}

if not df_walk.empty:
    col1, col2, col3 = st.columns(3)
    col1.metric("Valid cutoffs", walk_metrics.get("cutoffs", 0))
    col2.metric("CAGR Q5 long-only", f"{walk_metrics['cagr_estrategia']:.2%}")
    col3.metric("CAGR equal-weight benchmark", f"{walk_metrics['cagr_bench']:.2%}")

    if pd.notna(walk_metrics.get("cagr_stoxx600")):
        st.metric("CAGR real ^STOXX", f"{walk_metrics['cagr_stoxx600']:.2%}")
    if walk_metrics.get("p_value_long_short") is not None:
        st.caption(
            f"Long-short Q5-Q1 p-value: {walk_metrics['p_value_long_short']:.3f}. "
            "A high p-value indicates that the average annual edge is not statistically significant."
        )

    st.markdown(
        "**Chart 1: Cumulative equity curve**  \n"
        "Unit: relative capital ($100 starting value). "
        "Each series shows how $100 would evolve under the strategy, the equal-weight benchmark, and the real ^STOXX index."
    )
    curve_display = curva_walk.set_index("date")[
        ["strategy_long_only_Q5", "benchmark_universe_equalweight", "benchmark_stoxx600_real", "long_short_experiment"]
    ]
    st.line_chart(curve_display, use_container_width=True)

    st.markdown(
        "**Chart 2: Logarithmic equity curve**  \n"
        "Unit: log(capital). This scale makes relative growth and similar percentage moves easier to compare across the series.\n"
        "A 20% rise anywhere on the curve occupies the same vertical distance, which helps visualize compound return consistency."
    )
    log_curve = np.log(curve_display.replace({0: np.nan})).replace([np.inf, -np.inf], np.nan)
    st.line_chart(log_curve, use_container_width=True)

    st.markdown(
        "**Note**: the logarithmic chart does not change financial outcomes; it only makes compound returns more comparable visually."
    )

    st.markdown(
        "**Chart 3: Annual returns by cutoff**  \n"
        "Unit: annual percentage (%). Each bar shows the 12-month return from each annual cutoff for the top quintile, the bottom quintile, the equal-weight universe, the real ^STOXX index, and the long-short difference."
    )
    returns_display = df_walk.set_index("cutoff")[
        ["q5_ret", "q1_ret", "universo_ret_medio", "stoxx600_ret", "long_short"]
    ].copy()
    returns_display = returns_display.rename(
        columns={
            "q5_ret": "Q5",
            "q1_ret": "Q1",
            "universo_ret_medio": "Universe",
            "stoxx600_ret": "^STOXX",
            "long_short": "Q5 - Q1",
        }
    )
    st.bar_chart(returns_display * 100, use_container_width=True)

    st.subheader("Annual cutoff results")
    display_walk = df_walk.copy()
    display_walk["cutoff"] = pd.to_datetime(display_walk["cutoff"]).dt.date
    display_walk["fwd_date"] = pd.to_datetime(display_walk["fwd_date"]).dt.date
    display_walk = display_walk.rename(
        columns={
            "cutoff": "Cutoff",
            "fwd_date": "Final date",
            "q1_ret": "Q1 return",
            "q5_ret": "Q5 return",
            "long_short": "Long-short",
            "universe_avg_ret": "Universe return",
            "stoxx600_ret": "^STOXX return",
            "num_companies": "Companies",
        }
    )
    st.dataframe(display_walk, use_container_width=True, hide_index=True)

    st.markdown(
        """
        ### Extended walk-forward: technical score validation (2001-2025)

        The analysis used 25 non-overlapping annual cutoffs (2001-2025) with **only technical factors**: momentum 3/6/12m, RSI14, and distance to SMA200. Fundamentals were excluded because point-in-time historical fundamental data is not available via yfinance, and including them would introduce lookahead bias.

        **Summary result:** the pure technical score did not show statistically significant predictive power across the evaluated horizons (3, 6, and 12 months). Still, the long-only Q5 simulation accumulated more capital than the equal-weight benchmark over 2001-2025; this apparent discrepancy arises from the difference between annual significance tests and compound returns along a historical path.

        A notable event is also documented: at the 2009 cutoff, the long-short experiment suffered a "momentum crash" where Q1 rebounded more strongly than Q5 during the post-crisis recovery (a pattern consistent with momentum crash literature).

        Note: all observations are presented with warnings about survival bias, absent transaction costs, and missing point-in-time fundamental data.
        """
    )
else:
    st.info("The walk-forward simulation is not available because data is missing or there are no valid cutoffs.")

st.markdown("---")
st.caption("Developed by [Camachuelo](https://github.com/CamachueloPrograming)")
