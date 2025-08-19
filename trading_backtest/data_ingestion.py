#!/usr/bin/env python3
"""
data_ingestion.py - Download historical data and store in PostgreSQL
Usage: python data_ingestion.py
"""

import yfinance as yf
import psycopg2
import pandas as pd
from datetime import datetime, timedelta
import numpy as np
import sys

# Database connection configuration
DB_CONFIG = {
    'host': 'localhost',
    'database': 'trading_historical',
    'user': 'trading_bot',
    'password': 'your_secure_password'  # ⚠️ CHANGE THIS PASSWORD
}

def get_db_connection():
    """Create database connection"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except psycopg2.Error as e:
        print(f"❌ Database connection error: {e}")
        sys.exit(1)

def test_connection():
    """Test database connection"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT version();")
        version = cur.fetchone()
        print(f"✅ Connected to PostgreSQL: {version[0]}")
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Connection test failed: {e}")
        return False

def calculate_rsi(prices, period=14):
    """Calculate RSI indicator"""
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_macd(prices, fast=12, slow=26, signal=9):
    """Calculate MACD indicator"""
    ema_fast = prices.ewm(span=fast).mean()
    ema_slow = prices.ewm(span=slow).mean()
    macd = ema_fast - ema_slow
    macd_signal = macd.ewm(span=signal).mean()
    macd_histogram = macd - macd_signal
    return macd, macd_signal, macd_histogram

def calculate_bollinger_bands(prices, period=20, std_dev=2):
    """Calculate Bollinger Bands"""
    sma = prices.rolling(window=period).mean()
    std = prices.rolling(window=period).std()
    upper_band = sma + (std * std_dev)
    lower_band = sma - (std * std_dev)
    return upper_band, sma, lower_band

def download_and_store_data(symbols, start_date, end_date, interval='5m'):
    """Download historical data and store in PostgreSQL using start/end dates"""
    
    print(f"📥 Starting data download for {len(symbols)} symbols...")
    print(f"📅 Start: {start_date}, End: {end_date}")
    print(f"⏱️  Interval: {interval}")
    print("=" * 50)
    
    if not test_connection():
        return False
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    successful_symbols = []
    failed_symbols = []
    
    for i, symbol in enumerate(symbols, 1):
        print(f"\n📊 [{i}/{len(symbols)}] Processing {symbol}...")
        
        try:
            # Download data using start and end dates
            ticker = yf.Ticker(symbol)
            
            # For 5-minute data, yfinance has limitations - try different approaches
            if interval in ['5m', '1m', '2m', '15m', '30m', '60m', '90m']:
                # For intraday data, use period instead of start/end for better reliability
                data = ticker.history(period='60d', interval=interval, auto_adjust=True)
            else:
                # For daily data and above, use start/end dates
                data = ticker.history(start=start_date, end=end_date, interval=interval, auto_adjust=True)
            
            if data.empty:
                print(f"   ❌ No data available for {symbol}")
                failed_symbols.append(symbol)
                continue
            
            print(f"   📈 Downloaded {len(data)} records")
            
            # Determine timeframe for database storage
            timeframe_map = {
                '1m': '1min', '2m': '2min', '5m': '5min', '15m': '15min',
                '30m': '30min', '60m': '1hour', '90m': '90min',
                '1d': 'daily', '5d': '5daily', '1wk': 'weekly',
                '1mo': 'monthly', '3mo': 'quarterly'
            }
            timeframe = timeframe_map.get(interval, interval)
            
            # Insert price data with proper timeframe
            price_rows = 0
            for timestamp, row in data.iterrows():
                try:
                    # Check if timeframe column exists in your schema
                    cur.execute("""
                        INSERT INTO historical_prices 
                        (symbol, timestamp, timeframe, open, high, low, close, volume, adjusted_close)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (symbol, timestamp, timeframe) DO UPDATE SET
                        open = EXCLUDED.open,
                        high = EXCLUDED.high,
                        low = EXCLUDED.low,
                        close = EXCLUDED.close,
                        volume = EXCLUDED.volume,
                        adjusted_close = EXCLUDED.adjusted_close
                    """, (
                        symbol,
                        timestamp,
                        timeframe,
                        float(row['Open']),
                        float(row['High']),
                        float(row['Low']),
                        float(row['Close']),
                        int(row['Volume']),
                        float(row['Close'])
                    ))
                    price_rows += 1
                except psycopg2.Error as e:
                    if "column \"timeframe\" of relation \"historical_prices\" does not exist" in str(e):
                        # Fallback: try without timeframe column
                        conn.rollback()
                        cur.execute("""
                            INSERT INTO historical_prices 
                            (symbol, timestamp, open, high, low, close, volume, adjusted_close)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (symbol, timestamp) DO UPDATE SET
                            open = EXCLUDED.open,
                            high = EXCLUDED.high,
                            low = EXCLUDED.low,
                            close = EXCLUDED.close,
                            volume = EXCLUDED.volume,
                            adjusted_close = EXCLUDED.adjusted_close
                        """, (
                            symbol,
                            timestamp,
                            float(row['Open']),
                            float(row['High']),
                            float(row['Low']),
                            float(row['Close']),
                            int(row['Volume']),
                            float(row['Close'])
                        ))
                        price_rows += 1
                    else:
                        print(f"   ⚠️ Error inserting price data for {timestamp}: {e}")
                        conn.rollback()
                        break
            
            # Calculate and insert technical indicators (optional for 5min data)
            if len(data) > 50:  # Only if we have enough data points
                print(f"   🔧 Calculating technical indicators...")
                
                # Calculate indicators
                data['SMA_20'] = data['Close'].rolling(20).mean()
                data['SMA_50'] = data['Close'].rolling(50).mean()
                data['EMA_12'] = data['Close'].ewm(span=12).mean()
                data['EMA_26'] = data['Close'].ewm(span=26).mean()
                data['RSI'] = calculate_rsi(data['Close'])
                data['MACD'], data['MACD_Signal'], data['MACD_Histogram'] = calculate_macd(data['Close'])
                data['BB_Upper'], data['BB_Middle'], data['BB_Lower'] = calculate_bollinger_bands(data['Close'])
                data['Volume_MA'] = data['Volume'].rolling(20).mean()
                
                # Calculate ATR (Average True Range)
                data['High_Low'] = data['High'] - data['Low']
                data['High_Close'] = np.abs(data['High'] - data['Close'].shift())
                data['Low_Close'] = np.abs(data['Low'] - data['Close'].shift())
                data['True_Range'] = data[['High_Low', 'High_Close', 'Low_Close']].max(axis=1)
                data['ATR'] = data['True_Range'].rolling(14).mean()
                
                # Calculate volatility
                data['Volatility_20'] = data['Close'].pct_change().rolling(20).std() * np.sqrt(252)
                
                # Insert indicator data
                indicator_rows = 0
                for timestamp, row in data.iterrows():
                    # Only insert if we have valid indicator data
                    if pd.notna(row.get('SMA_20')):
                        try:
                            cur.execute("""
                                INSERT INTO historical_indicators 
                                (symbol, timestamp, timeframe, sma_20, sma_50, ema_12, ema_26, rsi,
                                 macd, macd_signal, macd_histogram, bb_upper, bb_middle, bb_lower,
                                 atr, volatility_20, volume_ma)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                ON CONFLICT (symbol, timestamp, timeframe) DO UPDATE SET
                                sma_20 = EXCLUDED.sma_20,
                                sma_50 = EXCLUDED.sma_50,
                                ema_12 = EXCLUDED.ema_12,
                                ema_26 = EXCLUDED.ema_26,
                                rsi = EXCLUDED.rsi,
                                macd = EXCLUDED.macd,
                                macd_signal = EXCLUDED.macd_signal,
                                macd_histogram = EXCLUDED.macd_histogram,
                                bb_upper = EXCLUDED.bb_upper,
                                bb_middle = EXCLUDED.bb_middle,
                                bb_lower = EXCLUDED.bb_lower,
                                atr = EXCLUDED.atr,
                                volatility_20 = EXCLUDED.volatility_20,
                                volume_ma = EXCLUDED.volume_ma
                            """, (
                                symbol,
                                timestamp,
                                timeframe,
                                float(row.get('SMA_20', 0)) if pd.notna(row.get('SMA_20')) else None,
                                float(row.get('SMA_50', 0)) if pd.notna(row.get('SMA_50')) else None,
                                float(row.get('EMA_12', 0)) if pd.notna(row.get('EMA_12')) else None,
                                float(row.get('EMA_26', 0)) if pd.notna(row.get('EMA_26')) else None,
                                float(row.get('RSI', 50)) if pd.notna(row.get('RSI')) else None,
                                float(row.get('MACD', 0)) if pd.notna(row.get('MACD')) else None,
                                float(row.get('MACD_Signal', 0)) if pd.notna(row.get('MACD_Signal')) else None,
                                float(row.get('MACD_Histogram', 0)) if pd.notna(row.get('MACD_Histogram')) else None,
                                float(row.get('BB_Upper', 0)) if pd.notna(row.get('BB_Upper')) else None,
                                float(row.get('BB_Middle', 0)) if pd.notna(row.get('BB_Middle')) else None,
                                float(row.get('BB_Lower', 0)) if pd.notna(row.get('BB_Lower')) else None,
                                float(row.get('ATR', 0)) if pd.notna(row.get('ATR')) else None,
                                float(row.get('Volatility_20', 0)) if pd.notna(row.get('Volatility_20')) else None,
                                float(row.get('Volume_MA', 0)) if pd.notna(row.get('Volume_MA')) else None
                            ))
                            indicator_rows += 1
                        except psycopg2.Error as e:
                            if "column \"timeframe\" of relation \"historical_indicators\" does not exist" in str(e):
                                # Skip indicators if timeframe column doesn't exist
                                print(f"   ⚠️ Skipping indicators - timeframe column missing")
                                break
                            else:
                                print(f"   ⚠️ Error inserting indicator data for {timestamp}: {e}")
                
                print(f"      📊 Stored {indicator_rows} indicator records")

            conn.commit()
            successful_symbols.append(symbol)
            
            print(f"   ✅ {symbol} completed!")
            print(f"      💾 Stored {price_rows} price records")
            
        except Exception as e:
            print(f"   ❌ Error processing {symbol}: {e}")
            print(f"       Error details: {type(e).__name__}")
            failed_symbols.append(symbol)
            conn.rollback()
    
    # Close database connection
    cur.close()
    conn.close()
    
    # Summary
    print("=" * 50)
    print("📋 DATA INGESTION SUMMARY")
    print("=" * 50)
    print(f"✅ Successful: {len(successful_symbols)} symbols")
    for symbol in successful_symbols:
        print(f"   • {symbol}")
    
    if failed_symbols:
        print(f"\n❌ Failed: {len(failed_symbols)} symbols")
        for symbol in failed_symbols:
            print(f"   • {symbol}")
    
    print(f"\n🎉 Data ingestion completed!")
    print(f"📊 Total symbols processed: {len(symbols)}")
    print(f"✅ Success rate: {len(successful_symbols)/len(symbols)*100:.1f}%")
    
    return len(successful_symbols) > 0

def verify_data(symbols):
    """Verify that data was stored correctly"""
    print("\n🔍 Verifying stored data...")
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # Check if timeframe column exists
        cur.execute("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = 'historical_prices' AND column_name = 'timeframe'
        """)
        has_timeframe = cur.fetchone() is not None
        
        if has_timeframe:
            # Check price data with timeframe
            cur.execute("""
                SELECT symbol, timeframe, COUNT(*) as records, 
                       MIN(timestamp) as earliest, 
                       MAX(timestamp) as latest
                FROM historical_prices 
                WHERE symbol = ANY(%s)
                GROUP BY symbol, timeframe
                ORDER BY symbol, timeframe
            """, (symbols,))
        else:
            # Check price data without timeframe
            cur.execute("""
                SELECT symbol, COUNT(*) as records, 
                       MIN(timestamp) as earliest, 
                       MAX(timestamp) as latest
                FROM historical_prices 
                WHERE symbol = ANY(%s)
                GROUP BY symbol
                ORDER BY symbol
            """, (symbols,))
        
        price_results = cur.fetchall()
        
        print("\n📈 PRICE DATA:")
        for result in price_results:
            if has_timeframe:
                symbol, timeframe, count, earliest, latest = result
                print(f"   {symbol} ({timeframe}): {count} records ({earliest} to {latest})")
            else:
                symbol, count, earliest, latest = result
                print(f"   {symbol}: {count} records ({earliest} to {latest})")
        
        # Check indicator data if table exists
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'historical_indicators'
            )
        """)
        
        if cur.fetchone()[0]:
            if has_timeframe:
                cur.execute("""
                    SELECT symbol, timeframe, COUNT(*) as records
                    FROM historical_indicators 
                    WHERE symbol = ANY(%s)
                    GROUP BY symbol, timeframe
                    ORDER BY symbol, timeframe
                """, (symbols,))
            else:
                cur.execute("""
                    SELECT symbol, COUNT(*) as records
                    FROM historical_indicators 
                    WHERE symbol = ANY(%s)
                    GROUP BY symbol
                    ORDER BY symbol
                """, (symbols,))
            
            indicator_results = cur.fetchall()
            
            print("\n📊 INDICATOR DATA:")
            for result in indicator_results:
                if has_timeframe:
                    symbol, timeframe, count = result
                    print(f"   {symbol} ({timeframe}): {count} indicator records")
                else:
                    symbol, count = result
                    print(f"   {symbol}: {count} indicator records")
            
    except Exception as e:
        print(f"❌ Verification error: {e}")
    finally:
        cur.close()
        conn.close()

def main():
    """Main function"""
    print("🚀 HISTORICAL DATA INGESTION")
    print("=" * 40)
    
    if DB_CONFIG['password'] == 'your_secure_password_here':
        print("❌ Please update the database password in DB_CONFIG before running!")
        sys.exit(1)
    
    symbols = [
        'AAPL', 'XOM', 'META', 'AMZN', 'NFLX', 'MSFT', 'NVDA',
        'TSLA', 'JPM', 'ADBE'
    ]    
    
    # Calculate a 60-day date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=60)
    
    # Download and store 5-minute data for the last 60 days
    success = download_and_store_data(symbols, start_date=start_date, end_date=end_date, interval='5m')
    
    if success:
        verify_data(symbols)
        print("\n✅ All done! Your historical database is ready for backtesting.")
    else:
        print("\n❌ Data ingestion failed. Please check the errors above.")

if __name__ == "__main__":
    main()