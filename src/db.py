"""SQLAlchemy engine/session setup, shared across ingestion, training, and API."""
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from src.config import DATABASE_URL

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, pool_pre_ping=True, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_session():
    """FastAPI-style dependency / context manager for a DB session."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def init_db():
    """Create tables if they don't exist. Uses raw SQL so it works for both
    Postgres and the SQLite fallback without needing an ORM model layer."""
    schema_sql = """
    CREATE TABLE IF NOT EXISTS gold_prices (
        date DATE PRIMARY KEY,
        open NUMERIC, high NUMERIC, low NUMERIC,
        close NUMERIC, volume NUMERIC
    );
    CREATE TABLE IF NOT EXISTS macro_indicators (
        date DATE, indicator_name TEXT, value NUMERIC,
        PRIMARY KEY (date, indicator_name)
    );
    CREATE TABLE IF NOT EXISTS models (
        model_version TEXT PRIMARY KEY, algorithm TEXT, trained_at TIMESTAMP,
        rmse NUMERIC, mae NUMERIC, mape NUMERIC
    );
    CREATE TABLE IF NOT EXISTS predictions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        model_version TEXT, prediction_date DATE, target_date DATE,
        predicted_price NUMERIC, confidence_lower NUMERIC,
        confidence_upper NUMERIC, created_at TIMESTAMP
    );
    """
    if not DATABASE_URL.startswith("sqlite"):
        schema_sql = schema_sql.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "SERIAL PRIMARY KEY")
    with engine.begin() as conn:
        for statement in schema_sql.strip().split(";"):
            if statement.strip():
                conn.execute(text(statement))


if __name__ == "__main__":
    init_db()
    print(f"Database initialized at: {DATABASE_URL}")
