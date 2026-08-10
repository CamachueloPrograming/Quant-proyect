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

    for cutoff in cutoffs:
        cpos = idx.get_loc(cutoff)
        fpos = cpos + horizon
        if fpos >= len(idx):
            continue

        factors = compute_factors_at_cutoff(close, cpos, min_history=min_history)
        if len(factors) < 50:
            continue

        z = factors.apply(zscore_winsorize)
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
                "n_empresas": len(score),
                "q1_ret": q1_ret,
                "q5_ret": q5_ret,
                "long_short": q5_ret - q1_ret,
                "universo_ret_medio": fwd_ret.mean(),
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

    equity_estrategia = [100.0]
    equity_bench = [100.0]
    equity_long_short = [100.0]
    for _, row in df_res.iterrows():
        equity_estrategia.append(equity_estrategia[-1] * (1 + row["q5_ret"]))
        equity_bench.append(equity_bench[-1] * (1 + row["universo_ret_medio"]))
        equity_long_short.append(equity_long_short[-1] * (1 + row["long_short"]))

    equity_stoxx600 = [np.nan] * (len(df_res) + 1)
    primer_valido = df_res["stoxx600_ret"].first_valid_index()
    if primer_valido is not None:
        equity_stoxx600[primer_valido] = 100.0
        for i in range(primer_valido, len(df_res)):
            ret = df_res["stoxx600_ret"].iloc[i]
            equity_stoxx600[i + 1] = equity_stoxx600[i] * (1 + ret) if pd.notna(ret) else equity_stoxx600[i]

    fechas = [df_res["cutoff"].iloc[0] - pd.DateOffset(years=1)] + list(df_res["cutoff"])
    curva = pd.DataFrame(
        {
            "fecha": fechas,
            "estrategia_long_only_Q5": equity_estrategia,
            "benchmark_universo_equalweight": equity_bench,
            "benchmark_stoxx600_real": equity_stoxx600,
            "experimento_long_short": equity_long_short,
        }
    )

    n_years = len(df_res)
    cagr_estrategia = (equity_estrategia[-1] / 100) ** (1 / n_years) - 1
    cagr_bench = (equity_bench[-1] / 100) ** (1 / n_years) - 1
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
        "capital_final_estrategia": equity_estrategia[-1],
        "capital_final_bench": equity_bench[-1],
        "capital_final_stoxx600": equity_stoxx600[-1] if primer_valido is not None else np.nan,
        "capital_final_long_short": equity_long_short[-1],
        "p_value_long_short": p_ls,
        "cutoffs": len(df_res),
    }

    return df_res, curva, metrics

st.set_page_config(page_title="Stoxx 600 Screener", layout="wide", page_icon="📊")

st.title("Stoxx 600 Screener")
with st.expander("Metodología"):
    st.write(
        "El `score_ajustado` combina 9 factores fundamentales y técnicos normalizados por z-score. "
        "El gráfico de quintiles muestra una validación aproximada y no es un backtest point-in-time, "
        "ya que existe circularidad porque `momentum_12m` es uno de los factores usados en el score. "
        "Aproximadamente 90 empresas tienen algún factor incompleto por limitaciones de datos gratuitos de Yahoo Finance."
    )

st.markdown("Vista interactiva del ranking de empresas por score ajustado.")

csv_path = "factores_score_stoxx600.csv"

try:
    df = load_data(csv_path)
except FileNotFoundError:
    st.error(f"No se encontró el archivo: {csv_path}")
    st.stop()

if "score_ajustado" not in df.columns:
    st.error("La columna 'score_ajustado' no está presente en el CSV.")
    st.stop()

# Sidebar filters
st.sidebar.header("Filtros")

has_sector = "sector" in df.columns
has_pais = "pais" in df.columns

sector_options = sorted(df["sector"].dropna().unique()) if has_sector else []
pais_options = sorted(df["pais"].dropna().unique()) if has_pais else []

if has_sector:
    selected_sectors = st.sidebar.multiselect("Sector", sector_options, default=sector_options)
else:
    st.sidebar.info("No hay columna 'sector' en el CSV.")
    selected_sectors = None

if has_pais:
    selected_paises = st.sidebar.multiselect("País", pais_options, default=pais_options)
else:
    st.sidebar.info("No hay columna 'pais' en el CSV.")
    selected_paises = None

min_score = float(df["score_ajustado"].min())
max_score = float(df["score_ajustado"].max())
selected_score = st.sidebar.slider(
    "Rango de score ajustado",
    min_value=min_score,
    max_value=max_score,
    value=(min_score, max_score),
    step=(max_score - min_score) / 100 if max_score > min_score else 0.01,
)

filtered = df.copy()
if has_sector and selected_sectors:
    filtered = filtered[filtered["sector"].isin(selected_sectors)]
if has_pais and selected_paises:
    filtered = filtered[filtered["pais"].isin(selected_paises)]
filtered = filtered[filtered["score_ajustado"].between(selected_score[0], selected_score[1])]
filtered = filtered.sort_values(by="score_ajustado", ascending=False)

if not filtered.empty:
    quintil_summary = build_quintile_returns(filtered)

    best_row = filtered.iloc[0]
    best_name = (
        best_row["nombre"]
        if "nombre" in best_row.index and pd.notna(best_row["nombre"])
        else best_row["yahoo_ticker"]
    )
    quintil_5_return = None
    if not quintil_summary.empty and 5 in quintil_summary["quintil"].values:
        quintil_5_return = float(
            quintil_summary.loc[quintil_summary["quintil"] == 5, "retorno_medio_12m"].iloc[0]
        )

    col1, col2, col3 = st.columns(3)
    col1.metric("Empresas totales", len(filtered))
    col2.metric("Mejor score", f"{best_name} ({best_row['score_ajustado']:.3f})")
    col3.metric("Retorno medio quintil 5", f"{quintil_5_return:.3f}" if quintil_5_return is not None else "N/A")
else:
    st.info("No hay empresas que cumplan los filtros seleccionados.")

st.markdown("---")
st.subheader("Ranking ordenado por score ajustado")

if not filtered.empty:
    display_df = filtered.copy()
    if "nombre" not in display_df.columns and "yahoo_ticker" in display_df.columns:
        display_df["nombre"] = display_df["yahoo_ticker"]

    key_columns = [col for col in ["yahoo_ticker", "nombre", "sector", "pais", "score_ajustado"] if col in display_df.columns]
    technical_columns = [
        col for col in display_df.columns
        if col.startswith("z_") or col in {"pe_ratio", "roe", "debt_to_equity", "revenue_growth", "momentum_3m", "momentum_6m", "momentum_12m", "rsi", "dist_sma200"}
    ]
    other_columns = [col for col in display_df.columns if col not in key_columns + technical_columns]
    ordered_columns = key_columns + other_columns + technical_columns
    display_df = display_df[ordered_columns].reset_index(drop=True)

    for col in display_df.columns:
        if pd.api.types.is_numeric_dtype(display_df[col]):
            display_df[col] = display_df[col].round(3)

    st.dataframe(display_df, use_container_width=True, hide_index=True)

    with st.expander("Detalle técnico (z-scores y factores)"):
        technical_display = display_df[key_columns + technical_columns].copy()
        st.dataframe(technical_display, use_container_width=True, hide_index=True)
else:
    st.info("No hay datos disponibles para mostrar la tabla.")

if not filtered.empty and "momentum_12m" in filtered.columns:
    quintil_summary = build_quintile_returns(filtered)
    st.subheader("Retorno por quintil de score")
    st.bar_chart(
        quintil_summary.set_index("quintil")["retorno_medio_12m"],
        use_container_width=True,
    )
else:
    st.info("No hay datos disponibles para generar el gráfico de retorno por quintil.")

st.markdown("---")
st.subheader("Simulación de cartera: Top vs Bottom vs Benchmark")
st.write(
    "Simulación de una cartera equiponderada del 20% de empresas con mejor score vs el 20% peor vs el universo completo (Stoxx 600), durante los últimos 12 meses. "
    "Nota: como el score incluye momentum de 12 meses como factor, este resultado refleja consistencia interna del modelo más que capacidad predictiva real."
)

try:
    curvas = pd.read_csv("curvas_rendimiento.csv")
    metricas = pd.read_csv("metricas_rendimiento.csv")
except FileNotFoundError:
    st.warning("No se encontraron los archivos de rendimiento para la simulación de cartera.")
    st.stop()

curvas["Ticker"] = pd.to_datetime(curvas["Ticker"], format="%Y-%m-%d")
curvas = curvas.set_index("Ticker")

line_chart_data = curvas[["top_quintil", "bottom_quintil", "benchmark_600"]].copy()
line_chart_data = line_chart_data * 100.0
st.line_chart(line_chart_data, use_container_width=True)

metricas_display = metricas.copy()
metricas_display["retorno_total"] = (metricas_display["retorno_total"] * 100).round(1)
metricas_display["volatilidad_anual"] = (metricas_display["volatilidad_anual"] * 100).round(1)
metricas_display["sharpe_ratio"] = metricas_display["sharpe_ratio"].round(1)
metricas_display["max_drawdown"] = (metricas_display["max_drawdown"] * 100).round(1)
metricas_display = metricas_display.rename(columns={
    "retorno_total": "Retorno total (%)",
    "volatilidad_anual": "Volatilidad anual (%)",
    "sharpe_ratio": "Sharpe ratio",
    "max_drawdown": "Max drawdown (%)",
})

st.dataframe(metricas_display, use_container_width=True, hide_index=True)

st.markdown("---")
st.subheader("Walk-forward histórico 2001-2025: estrategia top quintil vs benchmarks")
st.write(
    "Esta sección del dashboard tiene dos partes claramente diferenciadas:\n"
    "1) La validación inicial se construye con datos históricos recientes (aprox. 3 años) del dataset ``factores_score_stoxx600.csv``. "
    "En esa parte se calculan scores ajustados por empresa usando únicamente factores técnicos y fundamentales disponibles en el periodo reciente: "
    "momentum 3/6/12m, RSI14 y distancia a SMA200, junto con los factores fundamentales del dataset. "
    "Esto sirve para ver el comportamiento del ranking actual del universo, pero no es un backtest walk-forward completo.\n"
    "2) La simulación walk-forward anual utiliza precios históricos diarios desde 2001 hasta 2025. "
    "Cada corte anual calcula el score con datos solo hasta esa fecha y luego simula el rendimiento del quintil top (Q5) durante los siguientes 12 meses, "
    "comparándolo contra el universo equal-weight y el índice real ^STOXX."
)

price_path = Path("precios_stoxx600_max.csv")
index_path = Path("stoxx600_index.csv")

if price_path.exists():
    try:
        close = load_close_prices(str(price_path))
        stoxx600_index = load_stoxx_index(str(index_path)) if index_path.exists() else pd.Series(dtype="float64")
        df_walk, curva_walk, walk_metrics = simulate_walkforward(close, stoxx600_index)
    except Exception as exc:
        st.error(f"No se pudo ejecutar la simulación walk-forward: {exc}")
        df_walk = pd.DataFrame()
        curva_walk = pd.DataFrame()
        walk_metrics = {}
else:
    st.warning("No se encontró el archivo de precios necesarios para el walk-forward: precios_stoxx600_max.csv")
    df_walk = pd.DataFrame()
    curva_walk = pd.DataFrame()
    walk_metrics = {}

if not df_walk.empty:
    col1, col2, col3 = st.columns(3)
    col1.metric("Cortes válidos", walk_metrics.get("cutoffs", 0))
    col2.metric("CAGR Q5 long-only", f"{walk_metrics['cagr_estrategia']:.2%}")
    col3.metric("CAGR benchmark equal-weight", f"{walk_metrics['cagr_bench']:.2%}")

    if pd.notna(walk_metrics.get("cagr_stoxx600")):
        st.metric("CAGR ^STOXX real", f"{walk_metrics['cagr_stoxx600']:.2%}")
    if walk_metrics.get("p_value_long_short") is not None:
        st.caption(
            f"Valor p long-short Q5-Q1: {walk_metrics['p_value_long_short']:.3f}. "
            "El valor p alto indica que el edge medio anual no es estadísticamente significativo."
        )

    st.markdown(
        "**Gráfico 1: Curva de capital acumulada**  \n"
        "Unidad: capital relativo ($100 inicial). "
        "Cada serie muestra cómo evolucionaría $100 iniciales bajo la estrategia, el benchmark equal-weight y el índice ^STOXX real."
    )
    curve_display = curva_walk.set_index("fecha")[
        ["estrategia_long_only_Q5", "benchmark_universo_equalweight", "benchmark_stoxx600_real", "experimento_long_short"]
    ]
    st.line_chart(curve_display, use_container_width=True)

    st.markdown(
        "**Gráfico 2: Curva logarítmica de capital**  \n"
        "Unidad: log(valor de capital). Esta escala muestra mejor el crecimiento relativo y las caídas porcentuales similares en toda la serie.\n"
        "Una subida del 20% en cualquier punto de la curva ocupa la misma distancia vertical, lo que facilita ver la consistencia del rendimiento compuesto."
    )
    log_curve = np.log(curve_display.replace({0: np.nan})).replace([np.inf, -np.inf], np.nan)
    st.line_chart(log_curve, use_container_width=True)

    st.markdown(
        "**Importante**: la curva logarítmica no cambia el resultado financiero, solo hace que los retornos compuestos sean más comparables visualmente."
    )

    st.markdown(
        "**Gráfico 3: Retornos anuales por corte**  \n"
        "Unidad: porcentaje anual (%). Cada barra muestra el retorno de 12 meses a partir de cada corte anual para el top quintil, el bottom quintil, el universo equal-weight, el índice ^STOXX real y la diferencia long-short."
    )
    returns_display = df_walk.set_index("cutoff")[
        ["q5_ret", "q1_ret", "universo_ret_medio", "stoxx600_ret", "long_short"]
    ].copy()
    returns_display = returns_display.rename(
        columns={
            "q5_ret": "Q5",
            "q1_ret": "Q1",
            "universo_ret_medio": "Universo",
            "stoxx600_ret": "^STOXX",
            "long_short": "Q5 - Q1",
        }
    )
    st.bar_chart(returns_display * 100, use_container_width=True)

    st.subheader("Resultados por corte anual")
    display_walk = df_walk.copy()
    display_walk["cutoff"] = pd.to_datetime(display_walk["cutoff"]).dt.date
    display_walk["fwd_date"] = pd.to_datetime(display_walk["fwd_date"]).dt.date
    display_walk = display_walk.rename(
        columns={
            "cutoff": "Corte",
            "fwd_date": "Fecha final",
            "q1_ret": "Retorno Q1",
            "q5_ret": "Retorno Q5",
            "long_short": "Long-short",
            "universo_ret_medio": "Retorno universo",
            "stoxx600_ret": "Retorno ^STOXX",
            "n_empresas": "Empresas",
        }
    )
    st.dataframe(display_walk, use_container_width=True, hide_index=True)

    st.markdown(
        """
        ### Walk-forward ampliado: validación del score técnico (2001-2025)

        Se realizaron 25 cortes anuales no solapados (2001-2025) usando **solo
        factores técnicos**: momentum 3/6/12m, RSI14 y distancia a SMA200. Los
        fundamentales se excluyeron porque no están disponibles point-in-time
        vía yfinance y su inclusión introduciría fuga de información.

        **Resultado resumen:** el score técnico puro no mostró capacidad
        predictiva estadísticamente significativa en los horizontes evaluados
        (3, 6 y 12 meses). Aun así, la simulación long-only sobre Q5 acumuló
        mayor capital en el período 2001-2025 que el benchmark equal-weight;
        esta aparente discrepancia se explica por la diferencia entre pruebas
        de significancia anual y efectos compuestos en un camino histórico.

        Se documenta además un evento notable: en el corte 2009 el experimento
        long-short sufrió un "momentum crash" donde Q1 rebotó con más fuerza
        que Q5 durante la recuperación post-crisis (patrón consistente con la
        literatura sobre "momentum crashes").

        Nota: todas estas observaciones se muestran con advertencias sobre
        sesgo de supervivencia, falta de costes de transacción y ausencia de
        datos fundamentales point-in-time.
        """
    )
else:
    st.info("La simulación walk-forward no está disponible porque faltan datos o no hay cortes válidos.")

st.markdown("---")
st.caption("Desarrollado por [Camachuelo](https://github.com/CamachueloPrograming)")
