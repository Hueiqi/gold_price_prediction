"""Pull historical gold price data from Yahoo Finance and upsert into the DB."""
import pandas as pd
import yfinance as yf
from sqlalchemy import text

from src.config import GOLD_TICKER
from src.db import engine, init_db


def fetch_gold_prices(start: str = "2010-01-01", end: str | None = None) -> pd.DataFrame:
    """Download daily OHLCV gold futures data and return a clean dataframe."""
    raw = yf.download(GOLD_TICKER, start=start, end=end, progress=False)
    if raw.empty:
        raise RuntimeError(f"No data returned for ticker {GOLD_TICKER}")

    raw = raw.reset_index()
    # yfinance sometimes returns MultiIndex columns for a single ticker; flatten if so.
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = [c[0] for c in raw.columns]

    df = raw.rename(columns={
        "Date": "date", "Open": "open", "High": "high",
        "Low": "low", "Close": "close", "Volume": "volume",
    })
    df = df.dropna(subset=["close"])
    return df[["date", "open", "high", "low", "close", "volume"]]


def upsert_prices(df: pd.DataFrame) -> int:
    """Insert rows, skipping dates already present. Returns rows written."""
    with engine.begin() as conn:
        existing_dates = {
            row[0] for row in conn.execute(text("SELECT date FROM gold_prices"))
        }
        new_rows = df[~df["date"].astype(str).isin({str(d) for d in existing_dates})]

        if new_rows.empty:
            return 0

        new_rows.to_sql("gold_prices", conn, if_exists="append", index=False)
        return len(new_rows)


def main():
    init_db()
    df = fetch_gold_prices()
    written = upsert_prices(df)
    print(f"Fetched {len(df)} rows total; wrote {written} new rows to gold_prices.")


if __name__ == "__main__":
    main()
