"""
Utilities for managing historical data
"""

import asyncio
import pandas as pd
from datetime import datetime, timedelta
from typing import List
import yfinance as yf

from backtesting_system import DatabaseManager, HistoricalDataIngester

class DataManager:
    """Manage historical data updates and maintenance"""
    
    def __init__(self):
        self.db_manager = None
        self.ingester = None
    
    async def initialize(self):
        self.db_manager = DatabaseManager()
        await self.db_manager.initialize()
        self.ingester = HistoricalDataIngester(self.db_manager)
    
    async def update_historical_data(self, symbols: List[str], days_back: int = 7):
        """Update historical data with recent market data"""
        
        print(f"🔄 Updating historical data for last {days_back} days...")
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        for symbol in symbols:
            try:
                # Download recent data
                ticker = yf.Ticker(symbol)
                recent_data = ticker.history(
                    start=start_date.strftime('%Y-%m-%d'),
                    end=end_date.strftime('%Y-%m-%d'),
                    interval='1d'
                )
                
                if not recent_data.empty:
                    await self.ingester._store_price_data(symbol, recent_data, '1d')
                    await self.ingester._calculate_and_store_indicators(symbol, recent_data, '1d')
                    print(f"✅ Updated {symbol}")
                else:
                    print(f"⚠️ No recent data for {symbol}")
                    
            except Exception as e:
                print(f"❌ Error updating {symbol}: {e}")
    
    async def data_quality_check(self, symbols: List[str]):
        """Check data quality and identify gaps"""
        
        print("🔍 Running data quality check...")
        
        query = """
        SELECT symbol, DATE(timestamp) as date, COUNT(*) as records
        FROM historical_prices 
        WHERE symbol = ANY($1)
        AND DATE(timestamp) >= CURRENT_DATE - INTERVAL '30 days'
        GROUP BY symbol, DATE(timestamp)
        ORDER BY symbol, date;
        """
        
        async with self.db_manager.pg_pool.acquire() as conn:
            rows = await conn.fetch(query, symbols)
        
        # Analyze data gaps
        data_by_symbol = {}
        for row in rows:
            symbol = row['symbol']
            if symbol not in data_by_symbol:
                data_by_symbol[symbol] = []
            data_by_symbol[symbol].append(row['date'])
        
        for symbol in symbols:
            dates = data_by_symbol.get(symbol, [])
            if dates:
                date_range = (max(dates) - min(dates)).days
                expected_days = date_range * 5 / 7  # Approximate trading days
                actual_days = len(dates)
                coverage = actual_days / expected_days if expected_days > 0 else 0
                
                print(f"📊 {symbol}: {actual_days} days of data, {coverage:.1%} coverage")
                
                if coverage < 0.9:
                    print(f"⚠️  {symbol} may have data gaps")
            else:
                print(f"❌ {symbol}: No recent data found")

# CLI utility
async def main():
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python data_manager.py [update|check] [symbols...]")
        sys.exit(1)
    
    command = sys.argv[1]
    symbols = sys.argv[2:] if len(sys.argv) > 2 else ['AAPL', 'MSFT', 'GOOGL']
    
    manager = DataManager()
    await manager.initialize()
    
    if command == 'update':
        await manager.update_historical_data(symbols)
    elif command == 'check':
        await manager.data_quality_check(symbols)
    else:
        print(f"Unknown command: {command}")

if __name__ == "__main__":
    asyncio.run(main())