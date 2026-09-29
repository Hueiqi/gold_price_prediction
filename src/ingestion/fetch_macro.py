"""Pull macroeconomic indicators (USD index, 10Y yield, CPI) from the FRED API."""
import pandas as pd
import requests
from sqlalchemy import text

from src.config import FRED_API_KEY, FRED_SERIES
from src.db import engine, init_db

FRED_URL = "https://api.stlouisfed.org/fred/series/observations"


def fetch_series(series_id: str, friendly_name: str) -> pd.DataFrame:
    if not FRED_API_KEY:
        raise RuntimeError(
            "FRED_API_KEY is not set. Get a free key at "
            "https://fred.stlouisfed.org/docs/api/api_key.html and add it to .env"
        )
    resp = requests.get(FRED_URL, params={
        "series_id": series_id,
        "api_key": FRED_API_KEY,
        "file_type": "json",
    }, timeout=30)
    resp.raise_for_status()
    obs = resp.json()["observations"]

    df = pd.DataFrame(obs)[["date", "value"]]
    df = df[df["value"] != "."]  # FRED uses "." for missing values
    df["value"] = df["value"].astype(float)
    df["indicator_name"] = friendly_name
    return df[["date", "indicator_name", "value"]]


def upsert_macro(df: pd.DataFrame) -> int:
    with engine.begin() as conn:
        existing = {
            (row[0], row[1])
            for row in conn.execute(text("SELECT date, indicator_name FROM macro_indicators"))
        }
        key = list(zip(df["date"].astype(str), df["indicator_name"]))
        mask = [k not in existing for k in key]
        new_rows = df[mask]

        if new_rows.empty:
            return 0

        new_rows.to_sql("macro_indicators", conn, if_exists="append", index=False)
        return len(new_rows)


def main():
    init_db()
    total_written = 0
    for series_id, friendly_name in FRED_SERIES.items():
        df = fetch_series(series_id, friendly_name)
        written = upsert_macro(df)
        total_written += written
        print(f"{friendly_name} ({series_id}): fetched {len(df)}, wrote {written} new rows.")
    print(f"Done. Total new rows written: {total_written}")


if __name__ == "__main__":
    main()
