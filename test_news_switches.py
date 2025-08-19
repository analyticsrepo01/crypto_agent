#!/usr/bin/env python3
"""
Test script to demonstrate news configuration switches
Shows how to run the trading bot with different news configurations
"""

import asyncio

async def test_news_configuration():
    """Test different news configurations"""
    
    print("🧪 Testing News Configuration Switches")
    print("="*50)
    
    # Test 1: Check current configuration
    print("1️⃣ Current Configuration:")
    from config import USE_IBKR_NEWS, USE_GCS_NEWS, USE_GEMINI_ANALYSIS
    print(f"   USE_IBKR_NEWS: {USE_IBKR_NEWS}")
    print(f"   USE_GCS_NEWS: {USE_GCS_NEWS}")
    print(f"   USE_GEMINI_ANALYSIS: {USE_GEMINI_ANALYSIS}")
    
    # Test 2: Test import behavior
    print("\n2️⃣ Testing Import Behavior:")
    try:
        if USE_IBKR_NEWS or USE_GCS_NEWS:
            print("   📰 Attempting to import augmented news system...")
            from news_augmented import get_news_summary_for_trading
            print("   ✅ Augmented news system imported successfully")
            news_system = "AUGMENTED"
        else:
            print("   📰 All news disabled - importing fallback system...")
            from news_working import get_news_summary_for_trading
            print("   ✅ IBKR-only news system imported as fallback")
            news_system = "IBKR_ONLY"
            
    except ImportError as e:
        print(f"   ⚠️ Import failed: {e}")
        print("   🔄 Falling back to basic news system...")
        from news_working import get_news_summary_for_trading
        news_system = "FALLBACK"
    
    # Test 3: Test news data retrieval
    print(f"\n3️⃣ Testing News Data Retrieval ({news_system}):")
    test_symbols = ['AAPL', 'MSFT']
    
    try:
        news_data = await get_news_summary_for_trading()
        
        print(f"   📊 Retrieved news for {len(news_data)} symbols")
        
        for symbol in test_symbols:
            if symbol in news_data:
                data = news_data[symbol]
                has_news = data.get('has_news', False)
                sentiment = data.get('sentiment_label', 'UNKNOWN')
                emoji = data.get('sentiment_emoji', '❓')
                disabled = data.get('disabled', False)
                
                if disabled:
                    print(f"   ⚙️ {symbol}: News disabled")
                elif has_news:
                    print(f"   {emoji} {symbol}: {sentiment}")
                else:
                    print(f"   ❓ {symbol}: No news data")
            else:
                print(f"   ❌ {symbol}: Not in results")
                
    except Exception as e:
        print(f"   ❌ News retrieval failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 4: Configuration recommendations
    print(f"\n4️⃣ Configuration Guide:")
    print("   To disable all news (trade without news sentiment):")
    print("   - Set USE_IBKR_NEWS = False")
    print("   - Set USE_GCS_NEWS = False")
    print("   - Set USE_GEMINI_ANALYSIS = False")
    print()
    print("   To use only IBKR news:")
    print("   - Set USE_IBKR_NEWS = True")
    print("   - Set USE_GCS_NEWS = False")
    print("   - Set USE_GEMINI_ANALYSIS = False")
    print()
    print("   To use only GCS news:")
    print("   - Set USE_IBKR_NEWS = False")
    print("   - Set USE_GCS_NEWS = True")
    print("   - Set USE_GEMINI_ANALYSIS = True (for analysis)")
    print()
    print("   To use full augmented system:")
    print("   - Set USE_IBKR_NEWS = True")
    print("   - Set USE_GCS_NEWS = True")
    print("   - Set USE_GEMINI_ANALYSIS = True")

if __name__ == "__main__":
    asyncio.run(test_news_configuration())