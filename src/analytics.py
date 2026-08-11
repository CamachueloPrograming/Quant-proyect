import pandas as pd


def build_quintile_returns(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "momentum_12m" not in df.columns:
        return pd.DataFrame(columns=["quintil", "retorno_medio_12m"])

    df_with_quintiles = df.copy()
    df_with_quintiles["quintil"] = pd.qcut(
        df_with_quintiles["score_ajustado"],
        q=5,
        labels=[1, 2, 3, 4, 5],
        duplicates="drop",
    )

    return (
        df_with_quintiles.groupby("quintil", observed=True)["momentum_12m"]
        .mean()
        .reset_index()
        .rename(columns={"momentum_12m": "retorno_medio_12m"})
    )
