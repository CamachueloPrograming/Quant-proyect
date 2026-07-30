import pandas as pd
import streamlit as st

from analytics import build_quintile_returns
from data_loader import load_data

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
st.caption("Desarrollado por [Camachuelo](https://github.com/CamachueloPrograming)")
