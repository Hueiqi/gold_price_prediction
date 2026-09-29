-- Gold Price Prediction System — database schema (PostgreSQL)

CREATE TABLE IF NOT EXISTS gold_prices (
    date DATE PRIMARY KEY,
    open NUMERIC,
    high NUMERIC,
    low NUMERIC,
    close NUMERIC,
    volume NUMERIC
);

CREATE TABLE IF NOT EXISTS macro_indicators (
    date DATE,
    indicator_name TEXT,
    value NUMERIC,
    PRIMARY KEY (date, indicator_name)
);

CREATE TABLE IF NOT EXISTS models (
    model_version TEXT PRIMARY KEY,
    algorithm TEXT,
    trained_at TIMESTAMP,
    rmse NUMERIC,
    mae NUMERIC,
    mape NUMERIC
);

CREATE TABLE IF NOT EXISTS predictions (
    id SERIAL PRIMARY KEY,
    model_version TEXT REFERENCES models(model_version),
    prediction_date DATE,
    target_date DATE,
    predicted_price NUMERIC,
    confidence_lower NUMERIC,
    confidence_upper NUMERIC,
    created_at TIMESTAMP DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_macro_date ON macro_indicators(date);
CREATE INDEX IF NOT EXISTS idx_predictions_target_date ON predictions(target_date);
