import streamlit as st
import pandas as pd

st.set_page_config(page_title="Stoxx 600 Screener", layout="wide")

st.title("Stoxx 600 Screener")
with st.expander("Metodología"):
    st.write(
        "El `score_ajustado` combina 9 factores fundamentales y técnicos normalizados por z-score. "
        "El gráfico de quintiles muestra una validación aproximada y no es un backtest point-in-time, "
        "ya que existe circularidad porque `momentum_12m` es uno de los factores usados en el score. "
        "Aproximadamente 90 empresas tienen algún factor incompleto por limitaciones de datos gratuitos de Yahoo Finance."
    )

st.markdown("App básica para filtrar y ordenar el ranking de empresas por score ajustado.")

@st.cache_data
def load_data(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    return df

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

st.subheader("Ranking ordenado por score ajustado")
st.write(f"Empresas mostradas: {len(filtered)}")
st.data_editor(filtered.reset_index(drop=True))

if not filtered.empty and "momentum_12m" in filtered.columns:
    quintil_labels = [1, 2, 3, 4, 5]
    filtered = filtered.copy()
    filtered["quintil"] = pd.qcut(
        filtered["score_ajustado"],
        q=5,
        labels=quintil_labels,
        duplicates="drop",
    )
    quintil_summary = (
        filtered.groupby("quintil", observed=True)["momentum_12m"]
        .mean()
        .reset_index()
        .rename(columns={"momentum_12m": "retorno_medio_12m"})
    )

    st.subheader("Retorno por quintil de score")
    st.bar_chart(
        quintil_summary.set_index("quintil")["retorno_medio_12m"],
        use_container_width=True,
    )
else:
    st.info("No hay datos disponibles para generar el gráfico de retorno por quintil.")
