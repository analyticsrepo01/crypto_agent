#!/usr/bin/env python3
"""
test_client.py - Simple test client for the API 
"""
import requests
import json
from datetime import datetime, timedelta

# API base URL
BASE_URL = "http://localhost:8085"


DB_HOST='localhost'
DB_PORT=5432
DB_NAME='trading_historical'
DB_USER='trading_bot'
DB_PASSWORD='your_secure_password'

# In server_backtest.py, update this section:
DATABASE_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'trading_historical',
    'user': 'trading_bot',
    'password': 'your_secure_password'  # ⚠️ CHANGE THIS
}

def test_health():
    """Test health endpoint"""
    try:
        response = requests.get(f"{BASE_URL}/health")
        print("Health Check:", response.json())
        return True
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to health endpoint")
        return False
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False

def test_root():
    """Test root endpoint"""
    try:
        response = requests.get(f"{BASE_URL}/")
        print("Root endpoint:", response.json())
        return True
    except Exception as e:
        print(f"❌ Root endpoint failed: {e}")
        return False

def test_available_symbols():
    """Test available symbols endpoint"""
    try:
        response = requests.get(f"{BASE_URL}/available_symbols")
        if response.status_code == 200:
            symbols = response.json()
            print(f"Available Symbols: Found {len(symbols)} symbols")
            for symbol in symbols[:5]:  # Show first 5
                print(f"  • {symbol}")
        else:
            print("Error getting symbols:", response.json())
    except Exception as e:
        print(f"❌ Available symbols failed: {e}")

def test_historical_data():
    """Test historical data endpoint"""
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        params = {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "timeframe": "5min"
        }
        
        response = requests.get(f"{BASE_URL}/historical_prices/AAPL", params=params)
        if response.status_code == 200:
            data = response.json()
            print(f"Historical Data: Found {len(data)} records for AAPL")
            if data:
                print("Sample record:", data[0])
        else:
            print("Historical data error:", response.json())
    except Exception as e:
        print(f"❌ Historical data test failed: {e}")

def test_stock_analysis():
    """Test comprehensive stock analysis"""
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        params = {
            "date_from": start_date.isoformat(),
            "date_to": end_date.isoformat(),
            "timeframe": "5min"
        }
        
        response = requests.get(f"{BASE_URL}/stock_analysis/AAPL", params=params)
        if response.status_code == 200:
            analysis = response.json()
            print("Stock Analysis for AAPL:")
            print(f"  • Valid: {analysis.get('valid')}")
            print(f"  • Current Price: ${analysis.get('current_price', 'N/A')}")
            print(f"  • RSI: {analysis.get('rsi', 'N/A')}")
            print(f"  • SMA 20: ${analysis.get('sma_20', 'N/A')}")
        else:
            print("Stock analysis error:", response.json())
    except Exception as e:
        print(f"❌ Stock analysis test failed: {e}")

def test_data_summary():
    """Test data summary endpoint"""
    try:
        response = requests.get(f"{BASE_URL}/data_summary")
        if response.status_code == 200:
            summary = response.json()
            print("Data Summary:")
            print(f"  • Price Records: {summary.get('price_data', {}).get('total_records', 'N/A')}")
            print(f"  • Unique Symbols: {summary.get('price_data', {}).get('unique_symbols', 'N/A')}")
            print(f"  • Date Range: {summary.get('price_data', {}).get('earliest_date', 'N/A')} to {summary.get('price_data', {}).get('latest_date', 'N/A')}")
        else:
            print("Data summary error:", response.json())
    except Exception as e:
        print(f"❌ Data summary test failed: {e}")

def main():
    print("🧪 Testing Backtesting API...")
    print("=" * 40)
    
    # Test basic connectivity first
    if not test_root():
        print("❌ Cannot connect to API. Make sure the server is running on port 8085")
        print("\n💡 To start the server, run in another terminal:")
        print("   python backtest_server.py")
        return
    
    print()
    
    # Test health
    if test_health():
        print()
        
        # Test data endpoints
        test_data_summary()
        print()
        
        test_available_symbols()
        print()
        
        test_historical_data()
        print()
        
        test_stock_analysis()
        
        print("\n✅ All tests completed!")
    else:
        print("❌ Health check failed - check database connection")

if __name__ == "__main__":  # Fixed syntax error here!
    main()