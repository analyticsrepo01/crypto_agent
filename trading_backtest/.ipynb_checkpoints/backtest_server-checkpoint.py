# Save this as backtest_server.py
# cat > backtest_server.py << 'EOF'
#!/usr/bin/env python3
"""
backtest_server.py - FastAPI server for historical trading data
"""

import asyncio
import asyncpg
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
from contextlib import asynccontextmanager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database configuration - UPDATE THE PASSWORD HERE!
DATABASE_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'trading_historical',
    'user': 'trading_bot',
    'password': 'your_secure_password'  # ⚠️ CHANGE THIS TO YOUR ACTUAL PASSWORD
}

# Global database pool
pg_pool = None

# Pydantic models
class PriceData(BaseModel):
    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    adjusted_close: float

class StockAnalysis(BaseModel):
    valid: bool
    symbol: str
    data_points: int
    current_price: Optional[float] = None
    sma_20: Optional[float] = None
    sma_50: Optional[float] = None
    rsi: Optional[float] = None
    reason: Optional[str] = None

# Database management
async def create_db_pool():
    """Create database connection pool"""
    try:
        pool = await asyncpg.create_pool(
            host=DATABASE_CONFIG['host'],
            port=DATABASE_CONFIG['port'],
            database=DATABASE_CONFIG['database'],
            user=DATABASE_CONFIG['user'],
            password=DATABASE_CONFIG['password'],
            min_size=5,
            max_size=20,
            command_timeout=60
        )
        logger.info("✅ Database connection pool created successfully")
        return pool
    except Exception as e:
        logger.error(f"❌ Failed to create database pool: {e}")
        raise

async def close_db_pool():
    """Close database connection pool"""
    global pg_pool
    if pg_pool:
        await pg_pool.close()
        logger.info("🔒 Database connection pool closed")

# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global pg_pool
    pg_pool = await create_db_pool()
    yield
    # Shutdown
    await close_db_pool()

# FastAPI app
app = FastAPI(
    title="Trading Backtesting API",
    description="API for accessing historical trading data",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency to get database connection
async def get_db():
    if not pg_pool:
        raise HTTPException(status_code=503, detail="Database connection not available")
    return pg_pool

# Routes
@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "message": "Trading Backtesting API is running",
        "version": "1.0.0",
        "timestamp": datetime.now()
    }

@app.get("/health")
async def health_check(db_pool = Depends(get_db)):
    """Comprehensive health check including database"""
    try:
        async with db_pool.acquire() as conn:
            result = await conn.fetchval("SELECT 1")
            return {
                "status": "healthy",
                "database": "connected",
                "timestamp": datetime.now()
            }
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "database": "disconnected",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        )

@app.get("/available_symbols")
async def get_available_symbols(db_pool = Depends(get_db)):
    """Get list of all available symbols"""
    query = """
    SELECT DISTINCT symbol, 
           COUNT(*) as record_count,
           MIN(timestamp) as earliest_date,
           MAX(timestamp) as latest_date
    FROM historical_prices
    GROUP BY symbol
    ORDER BY symbol;
    """
    
    try:
        async with db_pool.acquire() as conn:
            rows = await conn.fetch(query)
            return [
                {
                    "symbol": row['symbol'],
                    "record_count": row['record_count'],
                    "earliest_date": row['earliest_date'],
                    "latest_date": row['latest_date']
                }
                for row in rows
            ]
    except Exception as e:
        logger.error(f"Failed to fetch available symbols: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch available symbols")

@app.get("/historical_prices/{symbol}")
async def get_historical_prices(
    symbol: str,
    start_date: datetime = Query(..., description="Start date for data retrieval"),
    end_date: datetime = Query(..., description="End date for data retrieval"),
    timeframe: str = Query("5min", description="Data timeframe"),
    db_pool = Depends(get_db)
):
    """Fetch historical price data"""
    
    # Simple query - adapt based on your schema
    query = """
    SELECT symbol, timestamp, open, high, low, close, volume, adjusted_close
    FROM historical_prices
    WHERE symbol = $1 AND timestamp BETWEEN $2 AND $3
    ORDER BY timestamp ASC;
    """
    
    try:
        async with db_pool.acquire() as conn:
            rows = await conn.fetch(query, symbol.upper(), start_date, end_date)
            
            if not rows:
                raise HTTPException(
                    status_code=404, 
                    detail=f"No data found for {symbol.upper()}"
                )
                
            return [dict(row) for row in rows]
            
    except Exception as e:
        logger.error(f"Database query failed for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")

@app.get("/stock_analysis/{symbol}")
async def get_stock_analysis(
    symbol: str,
    date_from: datetime = Query(..., description="Analysis start date"),
    date_to: datetime = Query(..., description="Analysis end date"),
    db_pool = Depends(get_db)
):
    """Basic stock analysis"""
    
    query = """
    SELECT timestamp, close
    FROM historical_prices
    WHERE symbol = $1 AND timestamp BETWEEN $2 AND $3
    ORDER BY timestamp ASC;
    """
    
    try:
        async with db_pool.acquire() as conn:
            rows = await conn.fetch(query, symbol.upper(), date_from, date_to)
        
        if not rows:
            return StockAnalysis(
                valid=False,
                symbol=symbol.upper(),
                data_points=0,
                reason="No historical data found"
            )
        
        # Simple analysis
        df = pd.DataFrame(rows, columns=['timestamp', 'close'])
        closes = df['close']
        
        current_price = float(closes.iloc[-1])
        sma_20 = float(closes.rolling(20).mean().iloc[-1]) if len(closes) >= 20 else None
        sma_50 = float(closes.rolling(50).mean().iloc[-1]) if len(closes) >= 50 else None
        
        return StockAnalysis(
            valid=True,
            symbol=symbol.upper(),
            data_points=len(df),
            current_price=current_price,
            sma_20=sma_20,
            sma_50=sma_50
        )
        
    except Exception as e:
        logger.error(f"Analysis failed for {symbol}: {e}")
        return StockAnalysis(
            valid=False,
            symbol=symbol.upper(),
            data_points=0,
            reason=f"Analysis error: {str(e)}"
        )

@app.get("/data_summary")
async def get_data_summary(db_pool = Depends(get_db)):
    """Get database statistics"""
    try:
        async with db_pool.acquire() as conn:
            price_stats = await conn.fetchrow("""
                SELECT COUNT(*) as total_records,
                       COUNT(DISTINCT symbol) as unique_symbols,
                       MIN(timestamp) as earliest_date,
                       MAX(timestamp) as latest_date
                FROM historical_prices;
            """)
            
            return {
                "price_data": dict(price_stats) if price_stats else {},
                "database_status": "healthy",
                "last_updated": datetime.now()
            }
            
    except Exception as e:
        logger.error(f"Failed to get data summary: {e}")
        raise HTTPException(status_code=500, detail="Failed to get data summary")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backtest_server:app", 
        host="0.0.0.0", 
        port=8085, 
        reload=True,
        log_level="info"
    )
# EOF