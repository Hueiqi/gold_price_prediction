"""Central configuration loaded from environment variables (.env)."""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

# Fall back to local SQLite if no Postgres URL is configured — keeps the
# project runnable without any external database setup.
DATABASE_URL = os.getenv("DATABASE_URL") or f"sqlite:///{DATA_DIR / 'gold.db'}"

FRED_API_KEY = os.getenv("FRED_API_KEY", "")
GOLD_TICKER = os.getenv("GOLD_TICKER", "GC=F")

MODEL_DIR = Path(os.getenv("MODEL_DIR", DATA_DIR / "models"))
MODEL_DIR.mkdir(parents=True, exist_ok=True)

# Macro series pulled from FRED (series_id: friendly_name)
FRED_SERIES = {
    "DTWEXBGS": "usd_index",       # Trade-weighted US Dollar Index
    "DGS10": "treasury_10y",       # 10-Year Treasury yield
    "CPIAUCSL": "cpi",             # Consumer Price Index
}
