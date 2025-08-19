# /trading_bot/diagnostics.py

import asyncio
from utils import ensure_connection, setup_reporting_directory
from market_data import get_stock_data_batch
from agent import validate_ai_decisions
from config import gemini_model, PORTFOLIO_STOCKS

async def test_ib_connection():
    """Test Interactive Brokers connection."""
    print("🔍 Testing Interactive Brokers Connection...")
    ib = await ensure_connection()
    if ib and ib.isConnected():
        print("✅ IB Connection: PASSED")
        return True
    print("❌ IB Connection: FAILED")
    return False

async def test_ai_connection():
    """Test Gemini AI connection."""
    print("🤖 Testing Gemini AI Connection...")
    try:
        response = await gemini_model.generate_content_async("test")
        if response.text:
            print("✅ Gemini AI Connection: PASSED")
            return True
    except Exception as e:
        print(f"❌ Gemini AI Connection: FAILED - {e}")
    return False

async def test_market_data():
    """Test market data retrieval for a sample of stocks."""
    print("📊 Testing Market Data Retrieval...")
    try:
        data = await get_stock_data_batch(PORTFOLIO_STOCKS[:2])
        if data and all(d['valid'] for d in data.values()):
            print("✅ Market Data Retrieval: PASSED")
            return True
    except Exception as e:
        print(f"❌ Market Data Retrieval: FAILED - {e}")
    return False

async def test_validation_system():
    """Test the validation system with mock data."""
    print("🕵️  Testing Validation System...")
    # Mock state with a clear contradiction
    mock_state_fail = {
        'ai_recommendations': {'AAPL': {'action': 'BUY', 'priority': 'HIGH'}},
        'ai_trend_analysis': {'AAPL': {'trend': 'BEARISH', 'confidence': 'HIGH'}}
    }
    result_fail = validate_ai_decisions(mock_state_fail)
    if result_fail['decision'] == 'rerun':
        print("✅ Validation System (Failure Case): PASSED")
    else:
        print("❌ Validation System (Failure Case): FAILED")

    # Mock state with consistent data
    mock_state_pass = {
        'ai_recommendations': {'GOOGL': {'action': 'BUY', 'priority': 'HIGH'}},
        'ai_trend_analysis': {'GOOGL': {'trend': 'BULLISH', 'confidence': 'HIGH'}}
    }
    result_pass = validate_ai_decisions(mock_state_pass)
    if result_pass['decision'] == 'proceed':
        print("✅ Validation System (Success Case): PASSED")
    else:
        print("❌ Validation System (Success Case): FAILED")

async def run_full_system_diagnostics():
    """Run a comprehensive check of all system components."""
    print("\n" + "="*50)
    print("🔧 RUNNING FULL SYSTEM DIAGNOSTICS")
    print("="*50)
    
    results = {
        "IB Connection": await test_ib_connection(),
        "AI Connection": await test_ai_connection(),
        "Market Data": await test_market_data(),
        "Reporting Directory": bool(setup_reporting_directory()),
    }
    await test_validation_system()

    print("\n----- DIAGNOSTIC SUMMARY -----")
    all_passed = all(results.values())
    for component, status in results.items():
        print(f"{'✅' if status else '❌'} {component}: {'PASSED' if status else 'FAILED'}")

    if all_passed:
        print("\n🎉 All systems operational!")
    else:
        print("\n⚠️  One or more systems failed. Please check the logs.")
    print("="*50 + "\n")
