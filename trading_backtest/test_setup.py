#!/usr/bin/env python3
"""
Fixed test_setup.py - Corrected SQL query issue
"""
#!/usr/bin/env python3
"""
Step-by-step testing and first backtest
"""

import psycopg2
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt

# Database configuration (update password)
DB_CONFIG = {
    'host': 'localhost',
    'database': 'trading_historical',
    'user': 'trading_bot',
    'password': 'your_secure_password'  # ⚠️ UPDATE THIS
}


def test_data_quality():
    """Test that data was ingested correctly - FIXED VERSION"""
    print("🔍 STEP 1: VERIFYING DATA QUALITY")
    print("=" * 40)
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        # Check price data coverage
        cur.execute("""
            SELECT 
                symbol,
                COUNT(*) as total_records,
                MIN(timestamp) as earliest_date,
                MAX(timestamp) as latest_date,
                COUNT(DISTINCT DATE(timestamp)) as trading_days
            FROM historical_prices 
            GROUP BY symbol 
            ORDER BY symbol;
        """)
        
        price_data = cur.fetchall()
        
        print("📈 PRICE DATA SUMMARY:")
        for symbol, records, earliest, latest, days in price_data:
            print(f"   {symbol}: {records} records, {days} trading days ({earliest.date()} to {latest.date()})")
        
        # Check indicator data
        cur.execute("""
            SELECT 
                symbol,
                COUNT(*) as indicator_records,
                COUNT(CASE WHEN rsi IS NOT NULL THEN 1 END) as rsi_count,
                COUNT(CASE WHEN sma_20 IS NOT NULL THEN 1 END) as sma_count
            FROM historical_indicators 
            GROUP BY symbol 
            ORDER BY symbol;
        """)
        
        indicator_data = cur.fetchall()
        
        print("\n📊 INDICATOR DATA SUMMARY:")
        for symbol, total, rsi_count, sma_count in indicator_data:
            print(f"   {symbol}: {total} total, {rsi_count} RSI, {sma_count} SMA")
        
        # Sample data check - FIXED QUERY
        print("\n📋 SAMPLE DATA CHECK:")
        cur.execute("""
            SELECT p.symbol, p.timestamp, p.close, i.rsi, i.sma_20 
            FROM historical_prices p
            LEFT JOIN historical_indicators i ON 
                p.symbol = i.symbol AND p.timestamp = i.timestamp
            WHERE p.symbol = 'AAPL' 
            ORDER BY p.timestamp DESC 
            LIMIT 5;
        """)
        
        sample_data = cur.fetchall()
        print("   Recent AAPL data:")
        for symbol, timestamp, close, rsi, sma20 in sample_data:
            print(f"   {timestamp.date()}: Close=${close:.2f}, RSI={rsi:.1f if rsi else 'N/A'}, SMA20=${sma20:.2f if sma20 else 'N/A'}")
        
        cur.close()
        conn.close()
        
        print("\n✅ Data quality check completed!")
        return True
        
    except Exception as e:
        print(f"❌ Data quality check failed: {e}")
        return False

def create_backtrader_data_feed():
    """Create a data feed for Backtrader from PostgreSQL"""
    print("\n🔌 STEP 2: CREATING BACKTRADER DATA FEED")
    print("=" * 40)
    
    try:
        # Install backtrader if not already installed
        try:
            import backtrader as bt
            print("✅ Backtrader is installed")
        except ImportError:
            print("❌ Backtrader not installed. Installing...")
            import subprocess
            subprocess.check_call(['pip', 'install', 'backtrader[plotting]'])
            import backtrader as bt
            print("✅ Backtrader installed successfully")
        
        # Test data retrieval for backtrader
        conn = psycopg2.connect(**DB_CONFIG)
        
        # Get data for AAPL as test - FIXED QUERY
        query = """
        SELECT 
            p.timestamp,
            p.open, p.high, p.low, p.close, p.volume,
            COALESCE(i.rsi, 50) as rsi,
            COALESCE(i.sma_20, p.close) as sma_20,
            COALESCE(i.macd_histogram, 0) as macd_histogram
        FROM historical_prices p
        LEFT JOIN historical_indicators i ON 
            p.symbol = i.symbol AND p.timestamp = i.timestamp
        WHERE p.symbol = 'AAPL'
        AND p.timestamp >= '2023-01-01'
        ORDER BY p.timestamp;
        """
        
        df = pd.read_sql(query, conn, parse_dates=['timestamp'])
        df.set_index('timestamp', inplace=True)
        
        conn.close()
        
        print(f"✅ Retrieved {len(df)} records for AAPL")
        print(f"   Date range: {df.index.min().date()} to {df.index.max().date()}")
        print(f"   Columns: {list(df.columns)}")
        print(f"   Sample RSI values: {df['rsi'].tail(3).values}")
        print(f"   Sample SMA values: {df['sma_20'].tail(3).values}")
        
        # Save sample data for testing
        df.to_csv('test_data_aapl.csv')
        print("📄 Sample data saved to 'test_data_aapl.csv'")
        
        return True
        
    except Exception as e:
        print(f"❌ Data feed creation failed: {e}")
        return False

def create_simple_test_strategy():
    """Create a simple test strategy file"""
    print("\n🎯 STEP 3: CREATING SIMPLE TEST STRATEGY")
    print("=" * 40)
    
    strategy_code = '''#!/usr/bin/env python3
"""
Simple Test Strategy - RSI + SMA crossover with PostgreSQL data
"""

import backtrader as bt
import pandas as pd
import psycopg2

class SimpleTestStrategy(bt.Strategy):
    """Simple strategy for testing - RSI + SMA crossover"""
    
    params = (
        ('rsi_low', 30),
        ('rsi_high', 70),
        ('printlog', True),
    )
    
    def __init__(self):
        # Add indicators
        self.rsi = bt.indicators.RSI(self.data.close, period=14)
        self.sma20 = bt.indicators.SMA(self.data.close, period=20)
        self.sma50 = bt.indicators.SMA(self.data.close, period=50)
        
        # Track signals
        self.crossover = bt.indicators.CrossOver(self.sma20, self.sma50)
        
        # Track orders
        self.order = None
        
    def next(self):
        # Skip if order pending
        if self.order:
            return
            
        # Current values
        current_rsi = self.rsi[0]
        current_price = self.data.close[0]
        
        if not self.position:  # Not in the market
            # Buy signal: RSI oversold + SMA20 > SMA50
            if current_rsi < self.params.rsi_low and self.crossover > 0:
                self.order = self.buy()
                if self.params.printlog:
                    self.log(f'BUY CREATE: Price={current_price:.2f}, RSI={current_rsi:.1f}')
                    
        else:  # In the market
            # Sell signal: RSI overbought OR SMA20 < SMA50
            if current_rsi > self.params.rsi_high or self.crossover < 0:
                self.order = self.sell()
                if self.params.printlog:
                    self.log(f'SELL CREATE: Price={current_price:.2f}, RSI={current_rsi:.1f}')
    
    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return
            
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'BUY EXECUTED: Price={order.executed.price:.2f}, Cost={order.executed.value:.2f}')
            elif order.issell():
                self.log(f'SELL EXECUTED: Price={order.executed.price:.2f}, Value={order.executed.value:.2f}')
                
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')
            
        self.order = None
    
    def log(self, txt, dt=None):
        """Logging function"""
        dt = dt or self.datas[0].datetime.date(0)
        print(f'{dt.isoformat()}: {txt}')

def get_data_from_db(symbol='AAPL', start_date='2023-01-01', end_date='2024-06-01'):
    """Get data from PostgreSQL for backtesting"""
    
    DB_CONFIG = {
        'host': 'localhost',
        'database': 'trading_historical',
        'user': 'trading_bot',
        'password': 'your_secure_password_here'  # ⚠️ UPDATE THIS
    }
    
    conn = psycopg2.connect(**DB_CONFIG)
    
    # Fixed query with table aliases
    query = """
    SELECT 
        p.timestamp as datetime,
        p.open, p.high, p.low, p.close, p.volume
    FROM historical_prices p
    WHERE p.symbol = %s
    AND p.timestamp >= %s
    AND p.timestamp <= %s
    ORDER BY p.timestamp;
    """
    
    df = pd.read_sql(query, conn, params=[symbol, start_date, end_date])
    df['datetime'] = pd.to_datetime(df['datetime'])
    df.set_index('datetime', inplace=True)
    
    conn.close()
    return df

def run_simple_backtest():
    """Run a simple backtest"""
    print("🚀 Running simple backtest...")
    print("=" * 40)
    
    # Create Cerebro engine
    cerebro = bt.Cerebro()
    
    # Add strategy
    cerebro.addstrategy(SimpleTestStrategy)
    
    # Get data
    print("📊 Loading data from database...")
    data = get_data_from_db('AAPL', '2023-01-01', '2024-06-01')
    print(f"   Loaded {len(data)} records for AAPL")
    
    # Create Backtrader data feed
    bt_data = bt.feeds.PandasData(dataname=data)
    cerebro.adddata(bt_data)
    
    # Set initial cash and commission
    cerebro.broker.setcash(100000.0)
    cerebro.broker.setcommission(commission=0.001)  # 0.1%
    
    # Add analyzers
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
    
    print(f'💰 Starting Portfolio Value: ${cerebro.broker.getvalue():,.2f}')
    print("")
    
    # Run backtest
    results = cerebro.run()
    
    print("")
    print(f'💰 Final Portfolio Value: ${cerebro.broker.getvalue():,.2f}')
    
    # Print performance metrics
    strat = results[0]
    
    print("\\n📊 PERFORMANCE METRICS:")
    print("=" * 30)
    
    try:
        sharpe = strat.analyzers.sharpe.get_analysis()['sharperatio']
        print(f"   📈 Sharpe Ratio: {sharpe:.3f}")
    except:
        print("   📈 Sharpe Ratio: N/A")
    
    try:
        returns = strat.analyzers.returns.get_analysis()
        total_return = returns['rtot']
        print(f"   💹 Total Return: {total_return:.2%}")
    except:
        print("   💹 Total Return: N/A")
    
    try:
        drawdown = strat.analyzers.drawdown.get_analysis()
        max_dd = drawdown['max']['drawdown']
        print(f"   📉 Max Drawdown: {max_dd:.2%}")
    except:
        print("   📉 Max Drawdown: N/A")
    
    try:
        trades = strat.analyzers.trades.get_analysis()
        total_trades = trades['total']['total']
        won_trades = trades['won']['total']
        win_rate = won_trades / total_trades if total_trades > 0 else 0
        print(f"   🎯 Total Trades: {total_trades}")
        print(f"   ✅ Win Rate: {win_rate:.1%}")
    except:
        print("   🎯 Trade Analysis: N/A")
    
    # Calculate profit
    initial_value = 100000.0
    final_value = cerebro.broker.getvalue()
    profit = final_value - initial_value
    print(f"   💰 Profit/Loss: ${profit:,.2f}")
    
    # Plot results (optional - may require GUI)
    try:
        cerebro.plot(style='candlestick')
        print("   📊 Chart displayed")
    except:
        print("   📊 Chart not available (no GUI)")
    
    return True

if __name__ == "__main__":
    print("🧪 SIMPLE BACKTEST STRATEGY TEST")
    print("=" * 50)
    run_simple_backtest()
'''
    
    # Save the strategy file
    with open('simple_test_strategy.py', 'w') as f:
        f.write(strategy_code)
    
    print("✅ Test strategy saved to 'simple_test_strategy.py'")
    return True

def run_complete_test():
    """Run all tests in sequence"""
    print("🧪 RUNNING COMPLETE TESTING SEQUENCE")
    print("=" * 50)
    
    # Step 1: Verify data quality
    if not test_data_quality():
        print("❌ Data quality test failed. Please check your data ingestion.")
        return False
    
    # Step 2: Test Backtrader data feed
    if not create_backtrader_data_feed():
        print("❌ Backtrader data feed test failed.")
        return False
    
    # Step 3: Create test strategy
    if not create_simple_test_strategy():
        print("❌ Test strategy creation failed.")
        return False
    
    # Step 4: Install dependencies
    print("\n📦 STEP 4: INSTALLING DEPENDENCIES")
    print("=" * 40)
    
    try:
        import subprocess
        import sys
        
        packages = ['backtrader[plotting]', 'matplotlib']
        for package in packages:
            try:
                print(f"Installing {package}...")
                subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])
                print(f"✅ {package} installed")
            except Exception as e:
                print(f"⚠️ Warning installing {package}: {e}")
        
    except Exception as e:
        print(f"⚠️ Dependency installation warning: {e}")
    
    print("\n🎉 ALL TESTS COMPLETED SUCCESSFULLY!")
    print("\n🚀 NEXT STEPS:")
    print("1. Update password in 'simple_test_strategy.py'")
    print("2. Run: python simple_test_strategy.py")
    print("3. Check the backtest results!")
    
    return True

if __name__ == "__main__":
    print("🔧 TRADING BACKTEST SYSTEM - TESTING SUITE (FIXED)")
    print("=" * 55)
    
    # Check if password is updated
    if DB_CONFIG['password'] == 'your_secure_password_here':
        print("❌ Please update the database password in this script first!")
        print("   Edit DB_CONFIG['password'] and try again.")
        exit(1)
    
    # Run complete test
    success = run_complete_test()
    
    if success:
        print("\n✅ Your backtesting system is ready!")
        print("📊 Database: ✅ Working")
        print("🐍 Backtrader: ✅ Ready") 
        print("📈 Data: ✅ Available")
        print("\n🎯 Ready to create more advanced strategies!")
    else:
        print("\n❌ Some tests failed. Please check the errors above.")