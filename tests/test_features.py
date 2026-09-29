import pandas as pd

from src.features.engineering import add_price_features, merge_macro_features


def test_add_price_features_creates_lag_columns():
    df = pd.DataFrame({
        "date": pd.date_range("2024-01-01", periods=20, freq="D"),
        "close": range(100, 120),
    })
    result = add_price_features(df)

    assert "close_lag_1" in result.columns
    assert "rolling_mean_7" in result.columns
    # lag_1 at row index 1 should equal close at row index 0
    assert result.iloc[1]["close_lag_1"] == df.iloc[0]["close"]


def test_merge_macro_features_forward_fills():
    prices = pd.DataFrame({
        "date": pd.date_range("2024-01-01", periods=5, freq="D"),
        "close": [100, 101, 102, 103, 104],
    })
    macro = pd.DataFrame({
        "date": pd.to_datetime(["2024-01-01", "2024-01-03"]),
        "indicator_name": ["usd_index", "usd_index"],
        "value": [100.0, 102.0],
    })
    merged = merge_macro_features(prices, macro)

    assert "usd_index" in merged.columns
    # 2024-01-02 has no direct macro value, should forward-fill from 01-01
    assert merged.loc[merged["date"] == "2024-01-02", "usd_index"].iloc[0] == 100.0


def test_merge_macro_features_handles_empty_macro():
    prices = pd.DataFrame({"date": pd.date_range("2024-01-01", periods=3), "close": [1, 2, 3]})
    result = merge_macro_features(prices, pd.DataFrame())
    assert result.equals(prices)
