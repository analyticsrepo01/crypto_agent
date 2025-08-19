\c trading_historical

CREATE EXTENSION IF NOT EXISTS timescaledb;

CREATE TABLE IF NOT EXISTS historical_prices (
    symbol VARCHAR(10) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    timeframe VARCHAR(10) NOT NULL DEFAULT '1d',
    open REAL NOT NULL,
    high REAL NOT NULL,
    low REAL NOT NULL,
    close REAL NOT NULL,
    volume BIGINT NOT NULL,
    adjusted_close REAL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(symbol, timestamp, timeframe)
);

SELECT create_hypertable('historical_prices', 'timestamp', if_not_exists => TRUE, chunk_time_interval => INTERVAL '1 month');

CREATE TABLE IF NOT EXISTS historical_indicators (
    symbol VARCHAR(10) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    timeframe VARCHAR(10) NOT NULL DEFAULT '1d',
    sma_20 REAL, sma_50 REAL, ema_12 REAL, ema_26 REAL, rsi REAL,
    macd REAL, macd_signal REAL, macd_histogram REAL,
    bb_upper REAL, bb_middle REAL, bb_lower REAL,
    stoch_k REAL, stoch_d REAL, williams_r REAL,
    atr REAL, volatility_20 REAL, volume_ma REAL, obv REAL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(symbol, timestamp, timeframe)
);

SELECT create_hypertable('historical_indicators', 'timestamp', if_not_exists => TRUE, chunk_time_interval => INTERVAL '1 month');

CREATE TABLE IF NOT EXISTS historical_news_sentiment (
    symbol VARCHAR(10) NOT NULL,
    date DATE NOT NULL,
    sentiment_label VARCHAR(20),
    sentiment_score REAL,
    sentiment_emoji VARCHAR(10),
    article_count INTEGER DEFAULT 0,
    headlines TEXT[],
    summary TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(symbol, date)
);

CREATE INDEX IF NOT EXISTS idx_prices_symbol_time ON historical_prices (symbol, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_indicators_symbol_time ON historical_indicators (symbol, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_news_symbol_date ON historical_news_sentiment (symbol, date DESC);

GRANT ALL ON ALL TABLES IN SCHEMA public TO trading_bot;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO trading_bot;
