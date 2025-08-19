#!/usr/bin/env python3
"""
Test script for crypto trading functionality with Gemini exchange
"""

import asyncio
import sys
from datetime import datetime

# Test all critical imports
print("🧪 CRYPTO TRADING SYSTEM TEST")
print("=" * 50)

def test_imports():
    """Test all critical imports"""
    print("\n📦 Testing Imports...")
    
    try:
        from config import (
            PORTFOLIO_CRYPTOS, GEMINI_API_KEY, GEMINI_SANDBOX,
            TRADE_SIZE, MIN_USD_RESERVE
        )
        print("✅ Config imports successful")
        print(f"   Portfolio: {len(PORTFOLIO_CRYPTOS)} cryptos")
        print(f"   Trade size: {TRADE_SIZE}")
        print(f"   Sandbox mode: {GEMINI_SANDBOX}")
    except Exception as e:
        print(f"❌ Config imports failed: {e}")
        return False
    
    try:
        from crypto_market_data import (
            get_crypto_data_batch, get_crypto_portfolio_summary,
            test_gemini_connection, is_crypto_market_open
        )
        print("✅ Crypto market data imports successful")
    except Exception as e:
        print(f"❌ Crypto market data imports failed: {e}")
        return False
    
    try:
        from market_data import get_stock_data_batch, is_market_open
        print("✅ Market data compatibility layer successful")
    except Exception as e:
        print(f"❌ Market data compatibility failed: {e}")
        return False
    
    return True

async def test_gemini_connection_full():
    """Test Gemini API connection"""
    print("\n🔌 Testing Gemini Connection...")
    
    try:
        from crypto_market_data import test_gemini_connection
        connection_ok = await test_gemini_connection()
        if connection_ok:
            print("✅ Gemini connection test passed")
            return True
        else:
            print("❌ Gemini connection test failed")
            return False
    except Exception as e:
        print(f"❌ Connection test error: {e}")
        return False

async def test_data_fetching():
    """Test crypto data fetching"""
    print("\n📊 Testing Data Fetching...")
    
    try:
        from crypto_market_data import get_crypto_data_batch
        from config import PORTFOLIO_CRYPTOS
        
        # Test with first 3 cryptos to save time
        test_symbols = PORTFOLIO_CRYPTOS[:3]
        print(f"   Testing with symbols: {test_symbols}")
        
        data = await get_crypto_data_batch(test_symbols)
        
        success_count = 0
        for symbol, symbol_data in data.items():
            if symbol_data.get('valid'):
                success_count += 1
                price = symbol_data.get('current_price', 0)
                rsi = symbol_data.get('rsi', 0)
                print(f"   ✅ {symbol}: ${price:,.2f}, RSI {rsi:.1f}")
            else:
                print(f"   ❌ {symbol}: {symbol_data.get('reason', 'Unknown error')}")
        
        if success_count > 0:
            print(f"✅ Data fetching successful ({success_count}/{len(test_symbols)})")
            return True
        else:
            print("❌ No data fetching succeeded")
            return False
            
    except Exception as e:
        print(f"❌ Data fetching error: {e}")
        return False

async def test_portfolio_functions():
    """Test portfolio summary functions"""
    print("\n💰 Testing Portfolio Functions...")
    
    try:
        from crypto_market_data import get_crypto_portfolio_summary
        
        portfolio_value, usd_available, positions = await get_crypto_portfolio_summary()
        
        print(f"   Portfolio Value: ${portfolio_value:,.2f}")
        print(f"   USD Available: ${usd_available:,.2f}")
        print(f"   Positions: {len(positions)}")
        
        for symbol, amount in positions.items():
            if amount > 0:
                print(f"   📦 {symbol}: {amount:.6f}")
        
        print("✅ Portfolio functions working")
        return True
        
    except Exception as e:
        print(f"❌ Portfolio functions error: {e}")
        return False

def test_market_status():
    """Test market status functions"""
    print("\n🕐 Testing Market Status...")
    
    try:
        from crypto_market_data import is_crypto_market_open
        from market_data import is_market_open
        
        crypto_open = is_crypto_market_open()
        market_open = is_market_open()
        
        print(f"   Crypto market open: {crypto_open}")
        print(f"   Market open (compatibility): {market_open}")
        
        if crypto_open and market_open:
            print("✅ Market status functions working")
            return True
        else:
            print("⚠️ Markets appear closed")
            return True  # This is not an error for crypto
            
    except Exception as e:
        print(f"❌ Market status error: {e}")
        return False

async def test_main_compatibility():
    """Test compatibility with main trading components"""
    print("\n🔗 Testing Main Script Compatibility...")
    
    try:
        # Test key imports that main_trading.py will need
        from utils import ensure_connection
        from technical_analysis import calculate_rsi
        
        # Test connection
        connection = await ensure_connection()
        if connection:
            print("   ✅ Connection test passed")
        else:
            print("   ⚠️ Connection test returned None (may be expected)")
        
        # Test technical analysis
        import pandas as pd
        test_data = pd.Series([100, 101, 99, 102, 98, 103, 97])
        rsi = calculate_rsi(test_data)
        print(f"   ✅ Technical analysis working (test RSI: {rsi:.1f})")
        
        print("✅ Main script compatibility confirmed")
        return True
        
    except Exception as e:
        print(f"❌ Main compatibility error: {e}")
        return False

async def run_full_test():
    """Run all tests"""
    print(f"\n🚀 Starting Crypto Trading System Test at {datetime.now()}")
    
    results = []
    
    # Run tests
    results.append(test_imports())
    results.append(await test_gemini_connection_full())
    results.append(await test_data_fetching())
    results.append(await test_portfolio_functions())
    results.append(test_market_status())
    results.append(await test_main_compatibility())
    
    # Summary
    passed = sum(results)
    total = len(results)
    
    print(f"\n📋 TEST SUMMARY")
    print("=" * 30)
    print(f"Passed: {passed}/{total}")
    print(f"Success Rate: {passed/total*100:.1f}%")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! Crypto trading system is ready.")
        print("\n✅ You can now run main_trading.py with crypto functionality")
    elif passed >= total * 0.8:
        print(f"\n⚠️ Most tests passed. System is largely functional.")
        print("   Some minor issues may need attention.")
    else:
        print(f"\n❌ Multiple test failures. System needs fixes.")
    
    return passed == total

if __name__ == "__main__":
    success = asyncio.run(run_full_test())
    sys.exit(0 if success else 1)