## server_backtest.py

# test_client.py - Simple test client for the API 
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
    response = requests.get(f"{BASE_URL}/health")
    print("Health Check:", response.json())

def test_available_symbols():
    """Test available symbols endpoint"""
    response = requests.get(f"{BASE_URL}/available_symbols")
    print("Available Symbols:", response.json())

def test_historical_data():
    """Test historical data endpoint"""
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
        print("Error:", response.json())

def test_stock_analysis():
    """Test comprehensive stock analysis"""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    params = {
        "date_from": start_date.isoformat(),
        "date_to": end_date.isoformat(),
        "timeframe": "5min"
    }
    
    response = requests.get(f"{BASE_URL}/stock_analysis/AAPL", params=params)
    print("Stock Analysis:", response.json())

def test_data_summary():
    """Test data summary endpoint"""
    response = requests.get(f"{BASE_URL}/data_summary")
    print("Data Summary:", response.json())

if __name__ == "__main__":
    print("🧪 Testing Backtesting API...")
    print("=" * 40)
    
    try:
        test_health()
        print()
        
        test_data_summary()
        print()
        
        test_available_symbols()
        print()
        
        test_historical_data()
        print()
        
        test_stock_analysis()
        
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to API. Make sure the server is running on port 8085")
    except Exception as e:
        print(f"❌ Test failed: {e}")

