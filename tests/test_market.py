from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

import pandas as pd
from fastapi.testclient import TestClient

from src.api.main import app
from src.market import MarketFeed


def frames():
    now = pd.Timestamp.now(tz="UTC").floor("5min")
    daily = pd.DataFrame({"Open": [99., 100.], "High": [102., 105.],
                          "Low": [98., 99.], "Close": [100., 103.]},
                         index=[now - pd.Timedelta(days=1), now])
    intraday = daily.iloc[[-1]].copy()
    return daily, intraday


def test_feed_coalesces_requests_and_calculates_change():
    feed = MarketFeed()
    ticker = Mock()
    ticker.history.side_effect = frames()
    with patch("src.market.yf.Ticker", return_value=ticker):
        feed.refresh()
        feed.refresh()
    result = feed.get()
    assert ticker.history.call_count == 2
    assert result["price"] == 103
    assert result["previous_close"] == 100
    assert abs(result["change_percent"] - 3) < 1e-10
    assert result["stale"] is False
    result["history"].clear()
    assert feed.get()["history"]  # clients cannot modify the shared cache


def test_failed_refresh_retains_quote_and_original_timestamp():
    feed = MarketFeed()
    ticker = Mock()
    ticker.history.side_effect = frames()
    with patch("src.market.yf.Ticker", return_value=ticker):
        feed.refresh()
    before = feed.get()
    feed.last_attempt = 0
    with patch("src.market.yf.Ticker", side_effect=RuntimeError("provider offline")):
        feed.refresh()
    after = feed.get()
    assert after["price"] == before["price"]
    assert after["fetched_at"] == before["fetched_at"]
    assert after["stale"] is True
    assert after["feed_status"] == "refresh_failed"


def test_old_quote_is_not_labelled_current_even_if_just_fetched():
    feed = MarketFeed()
    feed.snapshot = {"quote_time": (datetime.now(timezone.utc)-timedelta(days=2)).isoformat(),
                     "fetched_at": datetime.now(timezone.utc).isoformat()}
    assert feed.get()["stale"] is True
    assert feed.get()["feed_status"] == "older_quote"


def test_market_unavailable_has_honest_503():
    with patch("src.api.main.market_feed.get", return_value=None):
        response = TestClient(app).get("/api/market")
    assert response.status_code == 503
    assert "retry" in response.json()["detail"]


def test_static_assets_and_history_validation():
    client = TestClient(app)
    assert client.get("/assets/style.css").status_code == 200
    assert client.get("/assets/app.js").status_code == 200
    assert client.get("/api/prices/history?limit=-1").status_code == 422
    assert client.get("/assets/../../.env").status_code == 404
