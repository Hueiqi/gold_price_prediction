"""Load the latest trained model and produce a prediction from the most recent data."""
import joblib

from src.config import MODEL_DIR
from src.features.engineering import build_feature_table


def load_latest_model():
    path = MODEL_DIR / "latest_model.pkl"
    if not path.exists():
        raise FileNotFoundError(
            "No trained model found. Run `python -m src.models.train` first."
        )
    artifact = joblib.load(path)
    return artifact["model"], artifact["feature_cols"]


def predict_next_price(target_horizon: int = 1) -> dict:
    model, feature_cols = load_latest_model()

    # Rebuild the feature table and take the most recent complete row as
    # the basis for the next prediction.
    df = build_feature_table(target_horizon=target_horizon)
    latest_row = df.iloc[[-1]][feature_cols]

    predicted_price = float(model.predict(latest_row)[0])

    # Simple symmetric confidence band based on training RMSE would be more
    # rigorous; here we use a placeholder +/-2% band for illustration.
    lower = predicted_price * 0.98
    upper = predicted_price * 1.02

    return {
        "predicted_price": round(predicted_price, 2),
        "confidence_lower": round(lower, 2),
        "confidence_upper": round(upper, 2),
        "days_ahead": target_horizon,
        "based_on_date": str(df.iloc[-1]["date"].date()),
    }


if __name__ == "__main__":
    print(predict_next_price())
