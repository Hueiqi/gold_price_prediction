"""Build the model-ready feature table from raw price + macro data."""
import pandas as pd
from sqlalchemy import text

from src.db import engine

LAG_DAYS = [1, 3, 7, 14]
ROLLING_WINDOW = 7


def load_raw_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    with engine.connect() as conn:
        prices = pd.read_sql(text("SELECT * FROM gold_prices ORDER BY date"), conn)
        macro = pd.read_sql(text("SELECT * FROM macro_indicators ORDER BY date"), conn)

    prices["date"] = pd.to_datetime(prices["date"])
    macro["date"] = pd.to_datetime(macro["date"])
    return prices, macro


def add_price_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values("date").copy()
    for lag in LAG_DAYS:
        df[f"close_lag_{lag}"] = df["close"].shift(lag)

    df["rolling_mean_7"] = df["close"].rolling(ROLLING_WINDOW).mean()
    df["rolling_std_7"] = df["close"].rolling(ROLLING_WINDOW).std()
    df["daily_return"] = df["close"].pct_change()
    return df


def merge_macro_features(prices: pd.DataFrame, macro: pd.DataFrame) -> pd.DataFrame:
    if macro.empty:
        return prices

    macro_wide = macro.pivot(index="date", columns="indicator_name", values="value")
    macro_wide = macro_wide.sort_index().ffill()  # macro data is often lower frequency

    merged = prices.merge(macro_wide, on="date", how="left")
    macro_cols = list(macro_wide.columns)
    merged[macro_cols] = merged[macro_cols].ffill()
    return merged


def build_feature_table(target_horizon: int = 1) -> pd.DataFrame:
    """Returns a feature table with a `target` column = close price N days ahead."""
    prices, macro = load_raw_data()
    if prices.empty:
        raise RuntimeError("No price data found — run src/ingestion/fetch_prices.py first.")

    df = add_price_features(prices)
    df = merge_macro_features(df, macro)

    df["target"] = df["close"].shift(-target_horizon)
    df = df.dropna()  # drop rows without full lag history or a known target
    return df


if __name__ == "__main__":
    table = build_feature_table()
    print(table.tail())
    print(f"\nFeature table shape: {table.shape}")
