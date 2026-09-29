"""Shared, bounded market-data cache. Failed refreshes never become fresh quotes."""
from copy import deepcopy
from datetime import datetime, timezone
import logging
import threading
import time

import pandas as pd
import yfinance as yf

from src.config import GOLD_TICKER

log = logging.getLogger(__name__)


class MarketFeed:
    def __init__(self):
        self.lock = threading.Lock()
        self.snapshot = None
        self.last_attempt = 0.0
        self.daily = None
        self.daily_at = 0.0
        self.error = False

    def refresh(self):
        with self.lock:
            if time.monotonic() - self.last_attempt < 55:
                return
            self.last_attempt = time.monotonic()
            try:
                ticker = yf.Ticker(GOLD_TICKER)
                if self.daily is None or time.monotonic() - self.daily_at > 3600:
                    daily = ticker.history(period="2y", interval="1d", auto_adjust=False, timeout=15)
                    if daily.empty:
                        raise RuntimeError("Empty daily data")
                    self.daily = daily.dropna(subset=["Close"])
                    self.daily_at = time.monotonic()
                intraday = ticker.history(period="5d", interval="5m", auto_adjust=False, timeout=15)
                if intraday.empty:
                    raise RuntimeError("Empty intraday data")
                intraday = intraday.dropna(subset=["Close"])
                stamp = intraday.index[-1]
                session = intraday[intraday.index.date == stamp.date()]
                previous = self.daily[self.daily.index.date < stamp.date()]
                if previous.empty:
                    raise RuntimeError("No previous close")
                price = float(intraday.iloc[-1]["Close"])
                prev = float(previous.iloc[-1]["Close"])
                now = datetime.now(timezone.utc).isoformat()
                self.snapshot = {
                    "symbol": GOLD_TICKER, "instrument": "Gold futures", "currency": "USD",
                    "unit": "troy ounce", "source": "Yahoo Finance", "interval": "5 minutes",
                    "price": price, "previous_close": prev, "change": price - prev,
                    "change_percent": (price / prev - 1) * 100,
                    "open": float(session.iloc[0]["Open"]),
                    "high": float(session["High"].max()), "low": float(session["Low"].min()),
                    "quote_time": stamp.isoformat(), "fetched_at": now,
                    "history_fetched_at": datetime.fromtimestamp(time.time() - (time.monotonic() - self.daily_at), timezone.utc).isoformat(),
                    "intraday": self.records(session), "history": self.records(self.daily),
                    "notice": "Gold futures, not a retail gold or spot quote. Provider data may be delayed. Auto-checks every 60 seconds.",
                }
                self.error = False
            except Exception:
                self.error = True
                log.exception("Market refresh failed; retaining last successful quote")

    @staticmethod
    def records(frame):
        return [{"date": idx.isoformat(), "open": float(row.Open), "high": float(row.High),
                 "low": float(row.Low), "close": float(row.Close)}
                for idx, row in frame.iterrows()]

    def get(self):
        # Assignment of a complete snapshot is atomic; reads never wait on the provider.
        data = deepcopy(self.snapshot)
        if data is None:
            return None
        age = (datetime.now(timezone.utc) - datetime.fromisoformat(data["quote_time"])).total_seconds()
        fetched_age = (datetime.now(timezone.utc) - datetime.fromisoformat(data["fetched_at"])).total_seconds()
        data["quote_age_seconds"] = max(0, round(age))
        data["stale"] = self.error or fetched_age > 180 or age > 1200
        data["feed_status"] = "refresh_failed" if self.error else ("older_quote" if data["stale"] else "connected")
        return data


market_feed = MarketFeed()
