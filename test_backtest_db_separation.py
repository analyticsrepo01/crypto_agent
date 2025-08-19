#!/usr/bin/env python3
"""
Test script to verify that BACKTEST_MODE creates separate trading logs databases
"""

import os
import sys
from datetime import datetime

# Add the current directory to path to import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from memory_store import store_cycle_memory, get_memory_stats, get_memory_store

def test_database_separation():
    """Test that backtest and live modes use separate databases"""
    
    print("🧪 TESTING BACKTEST DATABASE SEPARATION")
    print("=" * 50)
    
    # Test data for live trading
    live_test_state = {
        'cycle_number': 1,
        'session_id': 'test_live_session',
        'total_portfolio_value': 50000,
        'cash_available': 25000,
        'total_unrealized_pnl': 500,
        'executed_trades': [
            {
                'symbol': 'AAPL',
                'action': 'BUY',
                'quantity': 10,
                'price': 150.00,
                'reasoning': 'Live trading test - strong technical signals',
                'technical_score': 8.0,
                'confidence': 'HIGH',
                'priority': 'HIGH',
                'order_id': 'LIVE_TEST_001',
                'status': 'Filled'
            }
        ]
    }
    
    # Test data for backtest trading
    backtest_test_state = {
        'cycle_number': 1,
        'session_id': 'test_backtest_session',
        'total_portfolio_value': 100000,
        'cash_available': 50000,
        'total_unrealized_pnl': 1000,
        'executed_trades': [
            {
                'symbol': 'MSFT',
                'action': 'BUY',
                'quantity': 5,
                'price': 300.00,
                'reasoning': 'Backtest trading test - momentum indicators positive',
                'technical_score': 7.5,
                'confidence': 'HIGH',
                'priority': 'MEDIUM',
                'order_id': 'BACKTEST_TEST_001',
                'status': 'Filled'
            }
        ]
    }
    
    print("\n📊 Step 1: Testing LIVE trading memory storage...")
    # Store live trading data
    live_result = store_cycle_memory(live_test_state, backtest_mode=False)
    print(f"   ✅ Live trading data stored successfully")
    
    print("\n📊 Step 2: Testing BACKTEST trading memory storage...")
    # Store backtest trading data
    backtest_result = store_cycle_memory(backtest_test_state, backtest_mode=True)
    print(f"   ✅ Backtest trading data stored successfully")
    
    print("\n📊 Step 3: Verifying separate database files exist...")
    # Check that both database files exist
    live_db_exists = os.path.exists("trading_memory.db")
    backtest_db_exists = os.path.exists("trading_memory_backtest.db")
    
    print(f"   📁 Live database (trading_memory.db): {'✅ EXISTS' if live_db_exists else '❌ MISSING'}")
    print(f"   📁 Backtest database (trading_memory_backtest.db): {'✅ EXISTS' if backtest_db_exists else '❌ MISSING'}")
    
    print("\n📊 Step 4: Checking database contents...")
    # Get stats for both databases
    live_stats = get_memory_stats(backtest_mode=False)
    backtest_stats = get_memory_stats(backtest_mode=True)
    
    print(f"   🧠 Live database stats:")
    print(f"      - Total memories: {live_stats.get('total_memories', 0)}")
    print(f"      - Database path: {live_stats.get('database_path', 'Unknown')}")
    print(f"      - Database size: {live_stats.get('database_size_mb', 0):.2f} MB")
    
    print(f"   🧠 Backtest database stats:")
    print(f"      - Total memories: {backtest_stats.get('total_memories', 0)}")
    print(f"      - Database path: {backtest_stats.get('database_path', 'Unknown')}")
    print(f"      - Database size: {backtest_stats.get('database_size_mb', 0):.2f} MB")
    
    print("\n📊 Step 5: Verifying data isolation...")
    # Get memory stores directly to check today's context
    live_memory = get_memory_store(backtest_mode=False)
    backtest_memory = get_memory_store(backtest_mode=True)
    
    live_context = live_memory.get_daily_context()
    backtest_context = backtest_memory.get_daily_context()
    
    print(f"   📅 Live trades today: {live_context['total_trades']}")
    print(f"   📅 Backtest trades today: {backtest_context['total_trades']}")
    
    # Check that trades are in the correct databases
    live_trades = live_context.get('trades', [])
    backtest_trades = backtest_context.get('trades', [])
    
    if live_trades:
        latest_live = live_trades[-1]
        print(f"   📈 Latest live trade: {latest_live['action']} {latest_live['quantity']} {latest_live['symbol']} @ ${latest_live['price']:.2f}")
    
    if backtest_trades:
        latest_backtest = backtest_trades[-1]
        print(f"   📈 Latest backtest trade: {latest_backtest['action']} {latest_backtest['quantity']} {latest_backtest['symbol']} @ ${latest_backtest['price']:.2f}")
    
    print("\n🎯 RESULTS SUMMARY:")
    print("=" * 30)
    
    # Validation checks
    checks_passed = 0
    total_checks = 5
    
    if live_db_exists:
        print("   ✅ Live database file created")
        checks_passed += 1
    else:
        print("   ❌ Live database file missing")
    
    if backtest_db_exists:
        print("   ✅ Backtest database file created")
        checks_passed += 1
    else:
        print("   ❌ Backtest database file missing")
    
    if live_stats.get('database_path', '').endswith('trading_memory.db'):
        print("   ✅ Live database uses correct path")
        checks_passed += 1
    else:
        print("   ❌ Live database path incorrect")
    
    if backtest_stats.get('database_path', '').endswith('trading_memory_backtest.db'):
        print("   ✅ Backtest database uses correct path")
        checks_passed += 1
    else:
        print("   ❌ Backtest database path incorrect")
    
    if live_context['total_trades'] > 0 and backtest_context['total_trades'] > 0:
        print("   ✅ Both databases have trade data")
        checks_passed += 1
    else:
        print("   ❌ Missing trade data in one or both databases")
    
    print(f"\n🏆 TEST RESULT: {checks_passed}/{total_checks} checks passed")
    
    if checks_passed == total_checks:
        print("   🎉 SUCCESS: Database separation working correctly!")
        return True
    else:
        print("   ⚠️ ISSUES DETECTED: Some checks failed")
        return False

if __name__ == "__main__":
    try:
        success = test_database_separation()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)