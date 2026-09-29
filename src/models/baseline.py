"""Naive persistence baseline: tomorrow's price = today's price.

Any real model should beat this on a walk-forward backtest before being trusted.
"""
import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error

from src.features.engineering import build_feature_table


def evaluate_baseline(target_horizon: int = 1) -> dict:
    df = build_feature_table(target_horizon=target_horizon)
    y_true = df["target"].values
    y_pred = df["close"].values  # naive: predict no change

    rmse = mean_squared_error(y_true, y_pred, squared=False)
    mae = mean_absolute_error(y_true, y_pred)
    mape = float(np.mean(np.abs((y_true - y_pred) / y_true)) * 100)

    return {"rmse": rmse, "mae": mae, "mape": mape}


if __name__ == "__main__":
    metrics = evaluate_baseline()
    print("Naive baseline performance:", metrics)
