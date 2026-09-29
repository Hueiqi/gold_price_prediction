"""FastAPI app serving gold price predictions, history, and model status.

Run with:  uvicorn src.api.main:app --reload --port 8000
Docs at:   http://localhost:8000/docs
"""
import datetime as dt
import asyncio
from contextlib import asynccontextmanager, suppress
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from src.db import engine, init_db
from src.market import market_feed
from src.models.predict import predict_next_price

@asynccontextmanager
async def lifespan(app):
    init_db()
    async def refresh_loop():
        while True:
            await asyncio.to_thread(market_feed.refresh)
            await asyncio.sleep(60)
    task = asyncio.create_task(refresh_loop())
    yield
    task.cancel()
    with suppress(asyncio.CancelledError):
        await task


app = FastAPI(
    lifespan=lifespan,
    title="Gold Price Prediction API",
    description="Forecasts gold prices using historical data and macro indicators.",
    version="1.0.0",
)
WEB_DIR = Path(__file__).resolve().parents[1] / "web"
app.mount("/assets", StaticFiles(directory=WEB_DIR), name="assets")


@app.get("/")
def root():
    return FileResponse(WEB_DIR / "index.html")


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "gold-price-prediction-api"}


@app.get("/api/market")
def market():
    data = market_feed.get()
    if data is None:
        raise HTTPException(503, "Connecting to the market data provider. Please retry shortly.")
    return data


@app.get("/api/prices/history")
def price_history(
    start: str | None = Query(None, description="YYYY-MM-DD"),
    end: str | None = Query(None, description="YYYY-MM-DD"),
    limit: int = Query(365, ge=1, le=5000),
):
    query = "SELECT date, open, high, low, close, volume FROM gold_prices"
    conditions, params = [], {}

    if start:
        conditions.append("date >= :start")
        params["start"] = start
    if end:
        conditions.append("date <= :end")
        params["end"] = end
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY date DESC LIMIT :limit"
    params["limit"] = limit

    with engine.connect() as conn:
        df = pd.read_sql(text(query), conn, params=params)

    if df.empty:
        raise HTTPException(status_code=404, detail="No price data found for the given range.")

    return df.sort_values("date").to_dict(orient="records")


@app.get("/api/predict")
def predict(days_ahead: int = Query(1, ge=1, le=30)):
    try:
        result = predict_next_price(target_horizon=days_ahead)
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    # Log the prediction for later accuracy tracking.
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO predictions "
                "(model_version, prediction_date, target_date, predicted_price, "
                "confidence_lower, confidence_upper, created_at) "
                "VALUES (:mv, :pd, :td, :pp, :cl, :cu, :ca)"
            ),
            {
                "mv": "latest",
                "pd": dt.date.today().isoformat(),
                "td": (dt.date.today() + dt.timedelta(days=days_ahead)).isoformat(),
                "pp": result["predicted_price"],
                "cl": result["confidence_lower"],
                "cu": result["confidence_upper"],
                "ca": dt.datetime.utcnow(),
            },
        )

    return result


@app.get("/api/model/status")
def model_status():
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT * FROM models ORDER BY trained_at DESC LIMIT 1")
        ).mappings().first()

    if not row:
        raise HTTPException(status_code=404, detail="No trained model found yet.")
    return dict(row)
