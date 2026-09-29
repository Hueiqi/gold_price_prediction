"""Train an XGBoost model on the engineered feature table, evaluate with a
time-ordered split (never shuffle time-series data), and persist the model
artifact + metrics.
"""
import datetime as dt

import joblib
import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sqlalchemy import text
from xgboost import XGBRegressor

from src.config import MODEL_DIR
from src.db import engine, init_db
from src.features.engineering import build_feature_table

NON_FEATURE_COLS = {"date", "target"}


def time_ordered_split(df, test_frac: float = 0.2):
    split_idx = int(len(df) * (1 - test_frac))
    return df.iloc[:split_idx], df.iloc[split_idx:]


def train_model(target_horizon: int = 1):
    df = build_feature_table(target_horizon=target_horizon)
    train_df, test_df = time_ordered_split(df)

    feature_cols = [c for c in df.columns if c not in NON_FEATURE_COLS]
    X_train, y_train = train_df[feature_cols], train_df["target"]
    X_test, y_test = test_df[feature_cols], test_df["target"]

    model = XGBRegressor(
        n_estimators=300,
        max_depth=5,
        learning_rate=0.05,
        subsample=0.9,
        colsample_bytree=0.9,
        random_state=42,
    )
    model.fit(X_train, y_train)

    preds = model.predict(X_test)
    rmse = float(np.sqrt(mean_squared_error(y_test, preds)))
    mae = mean_absolute_error(y_test, preds)
    mape = float(np.mean(np.abs((y_test.values - preds) / y_test.values)) * 100)

    return model, feature_cols, {"rmse": rmse, "mae": mae, "mape": mape}


def save_model(model, feature_cols, metrics: dict) -> str:
    version = f"v{dt.datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    artifact_path = MODEL_DIR / f"{version}.pkl"
    joblib.dump({"model": model, "feature_cols": feature_cols}, artifact_path)

    # also save as "latest" for easy loading by the API
    joblib.dump({"model": model, "feature_cols": feature_cols}, MODEL_DIR / "latest_model.pkl")

    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO models (model_version, algorithm, trained_at, rmse, mae, mape) "
                "VALUES (:v, :a, :t, :r, :m, :p)"
            ),
            {
                "v": version, "a": "XGBRegressor",
                "t": dt.datetime.utcnow(),
                "r": metrics["rmse"], "m": metrics["mae"], "p": metrics["mape"],
            },
        )
    return version


def main():
    init_db()
    model, feature_cols, metrics = train_model()
    version = save_model(model, feature_cols, metrics)
    print(f"Trained model {version}")
    print(f"Metrics: {metrics}")
    print(f"Artifact saved to: {MODEL_DIR / (version + '.pkl')}")


if __name__ == "__main__":
    main()
