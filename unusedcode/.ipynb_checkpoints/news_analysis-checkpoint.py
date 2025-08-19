# /trading_bot/news_analysis.py

import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from ib_insync import *

# Import your existing utilities
from utils import ensure_connection, log_portfolio_activity, setup_reporting_directory, upload_to_gcs
from config import PORTFOLIO_STOCKS

async def test_news_providers():
    """Test function to see what news providers are available through IBKR"""
    try:
        ib = await ensure_connection()
        if not ib:
            print("❌ Could not connect to IBKR")
            return None
        
        print("🔍 Fetching available news providers...")
        news_providers = ib.reqNewsProviders()
        
        print(f"📰 Found {len(news_providers)} news providers:")
        provider_list = []
        for provider in news_providers:
            print(f"   📡 {provider.code}: {provider.name}")
            provider_list.append({
                'code': provider.code,
                'name': provider.name
            })
        
        # Log this activity
        log_portfolio_activity("news_providers_check", {
            "providers_found": len(news_providers),
            "provider_codes": [p.code for p in news_providers]
        })
        
        return provider_list
        
    except Exception as e:
        print(f"❌ Error getting news providers: {e}")
        log_portfolio_activity("news_providers_error", {"error": str(e)})
        return None

async def get_stock_news(symbol: str, days_back: int = 7, max_articles: int = 10):
    """Get recent news for a specific stock using your existing connection"""
    try:
        ib = await ensure_connection()
        if not ib:
            print(f"❌ Could not connect to IBKR for {symbol}")
            return None
        
        print(f"\n📰 Getting news for {symbol} (last {days_back} days)...")
        
        # Try multiple approaches to get the contract
        qualified_contract = None
        contract_attempts = [
            Stock(symbol, 'SMART', 'USD'),
            Stock(symbol, 'NASDAQ', 'USD'),
            Stock(symbol, 'NYSE', 'USD'),
            Stock(symbol, 'ARCA', 'USD')
        ]
        
        for attempt, contract in enumerate(contract_attempts, 1):
            try:
                print(f"🔍 Attempt {attempt}: Trying contract {contract.symbol} on {contract.exchange}")
                qualified_contracts = await ib.qualifyContractsAsync(contract)
                
                if qualified_contracts and len(qualified_contracts) > 0:
                    qualified_contract = qualified_contracts[0]
                    print(f"✅ Contract qualified: {qualified_contract.symbol} (ConId: {qualified_contract.conId}) on {qualified_contract.exchange}")
                    break
                else:
                    print(f"⚠️  No qualified contracts returned for {contract.exchange}")
                    
            except Exception as e:
                print(f"⚠️  Contract qualification attempt {attempt} failed: {e}")
                continue
        
        if not qualified_contract:
            print(f"❌ Could not qualify contract for {symbol} on any exchange")
            
            # Try alternative approach using reqContractDetails
            try:
                print(f"🔄 Trying alternative approach with reqContractDetails...")
                contract_details = ib.reqContractDetails(Stock(symbol, 'SMART', 'USD'))
                
                if contract_details and len(contract_details) > 0:
                    qualified_contract = contract_details[0].contract
                    print(f"✅ Contract found via details: {qualified_contract.symbol} (ConId: {qualified_contract.conId})")
                else:
                    print(f"❌ No contract details found for {symbol}")
                    return None
                    
            except Exception as e:
                print(f"❌ Contract details lookup failed: {e}")
                return None
        
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        # Format dates for IBKR API (YYYYMMDD-HH:MM:SS)
        start_date_str = start_date.strftime('%Y%m%d-00:00:00')
        end_date_str = end_date.strftime('%Y%m%d-23:59:59')
        
        print(f"🔍 Searching news from {start_date_str} to {end_date_str}")
        print(f"📡 Using ConId: {qualified_contract.conId}")
        
        # Request historical news with error handling
        try:
            news_articles = ib.reqHistoricalNews(
                conId=qualified_contract.conId,
                providerCodes="BRFG+DJNL+FLY",  # Use available providers from your output
                startDateTime=start_date_str,
                endDateTime=end_date_str,
                totalResults=max_articles
            )
        except Exception as news_error:
            print(f"❌ Historical news request failed: {news_error}")
            
            # Try with different provider codes
            print("🔄 Trying with different news providers...")
            try:
                news_articles = ib.reqHistoricalNews(
                    conId=qualified_contract.conId,
                    providerCodes="BRFG",  # Try with just one provider
                    startDateTime=start_date_str,
                    endDateTime=end_date_str,
                    totalResults=max_articles
                )
            except Exception as retry_error:
                print(f"❌ Retry with single provider also failed: {retry_error}")
                return None
        
        print(f"📊 Found {len(news_articles)} articles for {symbol}")
        
        # Process and display articles
        processed_articles = []
        if news_articles:
            print(f"\n📋 Recent news for {symbol}:")
            for i, article in enumerate(news_articles[:5], 1):  # Show first 5
                print(f"\n   {i}. 📰 {article.headline}")
                print(f"      🕐 {article.time}")
                print(f"      📡 Provider: {article.providerCode}")
                print(f"      🆔 Article ID: {article.articleId}")
                
                article_data = {
                    'headline': article.headline,
                    'time': article.time,
                    'provider': article.providerCode,
                    'article_id': article.articleId
                }
                
                # Try to get article content (this may require additional permissions)
                try:
                    article_content = ib.reqNewsArticle(
                        providerCode=article.providerCode,
                        articleId=article.articleId
                    )
                    if article_content:
                        # Show first 200 characters of content
                        content_preview = article_content.articleText[:200] + "..." if len(article_content.articleText) > 200 else article_content.articleText
                        print(f"      📄 Preview: {content_preview}")
                        article_data['content_preview'] = content_preview
                        article_data['full_content'] = article_content.articleText
                except Exception as e:
                    print(f"      ⚠️  Could not fetch article content: {e}")
                    article_data['content_error'] = str(e)
                
                processed_articles.append(article_data)
        
        # Log this activity using your existing logging
        log_portfolio_activity("stock_news_fetch", {
            "symbol": symbol,
            "days_back": days_back,
            "articles_found": len(news_articles),
            "search_period": f"{start_date_str} to {end_date_str}"
        })
        
        return {
            'symbol': symbol,
            'articles_count': len(news_articles),
            'articles': processed_articles,
            'raw_articles': news_articles
        }
        
    except Exception as e:
        print(f"❌ Error getting news for {symbol}: {e}")
        log_portfolio_activity("stock_news_error", {
            "symbol": symbol,
            "error": str(e)
        })
        return None

async def analyze_portfolio_news_sentiment():
    """Get news sentiment for all portfolio stocks and save report"""
    print("🔍 ANALYZING NEWS SENTIMENT FOR PORTFOLIO")
    print("=" * 50)
    
    # Setup reporting directory using your existing function
    reports_dir = setup_reporting_directory()
    
    # First, check available providers
    providers = await test_news_providers()
    
    portfolio_news = {}
    sentiment_summary = {
        'positive_stocks': [],
        'negative_stocks': [],
        'neutral_stocks': [],
        'total_articles': 0
    }
    
    # Get news for each stock in portfolio
    for symbol in PORTFOLIO_STOCKS[:5]:  # Test with first 5 stocks to avoid rate limits
        print(f"\n{'='*20} {symbol} {'='*20}")
        
        # Get news
        news_data = await get_stock_news(symbol, days_back=3, max_articles=10)
        
        if news_data and news_data['articles']:
            # Analyze sentiment
            sentiment_result = analyze_news_sentiment(news_data['articles'])
            
            portfolio_news[symbol] = {
                **news_data,
                'sentiment': sentiment_result
            }
            
            # Update summary
            sentiment_summary['total_articles'] += news_data['articles_count']
            sentiment_label = sentiment_result['sentiment_label']
            
            if sentiment_label == 'POSITIVE':
                sentiment_summary['positive_stocks'].append(symbol)
            elif sentiment_label == 'NEGATIVE':
                sentiment_summary['negative_stocks'].append(symbol)
            else:
                sentiment_summary['neutral_stocks'].append(symbol)
        
        # Rate limiting to avoid overwhelming the API
        await asyncio.sleep(2)
    
    # Generate and save report
    report_data = {
        'timestamp': datetime.now().isoformat(),
        'portfolio_stocks': PORTFOLIO_STOCKS,
        'news_providers': providers,
        'sentiment_summary': sentiment_summary,
        'detailed_analysis': portfolio_news
    }
    
    # Save JSON report using your existing directory structure
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    json_filename = f"portfolio_news_sentiment_{timestamp}.json"
    json_filepath = reports_dir / json_filename
    
    import json
    with open(json_filepath, 'w', encoding='utf-8') as f:
        json.dump(report_data, f, indent=2, default=str)
    
    print(f"\n📊 News sentiment report saved: {json_filepath}")
    
    # Upload to GCS using your existing function
    gcs_path = f"news_analysis/{datetime.now().strftime('%Y/%m/%d')}/{json_filename}"
    upload_to_gcs(str(json_filepath), gcs_path)
    
    # Log the overall activity
    log_portfolio_activity("portfolio_news_sentiment_analysis", {
        "stocks_analyzed": len(portfolio_news),
        "total_articles": sentiment_summary['total_articles'],
        "positive_stocks": len(sentiment_summary['positive_stocks']),
        "negative_stocks": len(sentiment_summary['negative_stocks']),
        "neutral_stocks": len(sentiment_summary['neutral_stocks'])
    })
    
    # Print summary
    print(f"\n📊 PORTFOLIO NEWS SENTIMENT SUMMARY")
    print("=" * 40)
    print(f"📈 Positive: {sentiment_summary['positive_stocks']}")
    print(f"📉 Negative: {sentiment_summary['negative_stocks']}")
    print(f"⚖️  Neutral: {sentiment_summary['neutral_stocks']}")
    print(f"📰 Total articles analyzed: {sentiment_summary['total_articles']}")
    
    return report_data

def analyze_news_sentiment(articles: List[Dict]) -> Dict:
    """Analyze sentiment of news articles using keyword matching"""
    
    # Enhanced sentiment keywords
    positive_keywords = [
        'growth', 'profit', 'beat', 'strong', 'positive', 'upgrade', 'bullish', 
        'surge', 'gain', 'rally', 'outperform', 'exceed', 'robust', 'optimistic',
        'breakthrough', 'expansion', 'success', 'milestone', 'record', 'soar'
    ]
    
    negative_keywords = [
        'loss', 'decline', 'weak', 'negative', 'downgrade', 'bearish', 'fall', 
        'drop', 'crash', 'concern', 'warning', 'risk', 'plunge', 'disappointing',
        'underperform', 'struggle', 'challenge', 'pressure', 'volatility', 'uncertainty'
    ]
    
    sentiment_scores = []
    article_sentiments = []
    
    for article in articles:
        headline_lower = article['headline'].lower()
        
        # Count positive and negative words
        positive_count = sum(1 for word in positive_keywords if word in headline_lower)
        negative_count = sum(1 for word in negative_keywords if word in headline_lower)
        
        # Calculate sentiment score for this article
        article_sentiment = positive_count - negative_count
        sentiment_scores.append(article_sentiment)
        
        # Classify individual article
        if article_sentiment > 0:
            article_label = 'POSITIVE'
        elif article_sentiment < 0:
            article_label = 'NEGATIVE'
        else:
            article_label = 'NEUTRAL'
        
        article_sentiments.append({
            'headline': article['headline'],
            'sentiment_score': article_sentiment,
            'sentiment_label': article_label,
            'positive_words': positive_count,
            'negative_words': negative_count
        })
    
    # Calculate overall sentiment
    if sentiment_scores:
        avg_sentiment = sum(sentiment_scores) / len(sentiment_scores)
        total_articles = len(articles)
        
        # Determine overall sentiment label
        if avg_sentiment > 0.2:
            sentiment_label = 'POSITIVE'
        elif avg_sentiment < -0.2:
            sentiment_label = 'NEGATIVE'
        else:
            sentiment_label = 'NEUTRAL'
        
        print(f"📊 NEWS SENTIMENT ANALYSIS:")
        print(f"   📰 Total Articles: {total_articles}")
        print(f"   📈 Average Sentiment: {avg_sentiment:.2f}")
        print(f"   🎯 Overall Sentiment: {sentiment_label}")
        
        return {
            'total_articles': total_articles,
            'avg_sentiment': avg_sentiment,
            'sentiment_label': sentiment_label,
            'individual_articles': article_sentiments,
            'positive_articles': len([s for s in sentiment_scores if s > 0]),
            'negative_articles': len([s for s in sentiment_scores if s < 0]),
            'neutral_articles': len([s for s in sentiment_scores if s == 0])
        }
    
    return {
        'total_articles': 0,
        'avg_sentiment': 0,
        'sentiment_label': 'NEUTRAL',
        'individual_articles': [],
        'positive_articles': 0,
        'negative_articles': 0,
        'neutral_articles': 0
    }

# Add this alternative news function for testing
async def test_news_without_contract(symbol: str = "AAPL"):
    """Alternative news test that doesn't rely on contract qualification"""
    try:
        ib = await ensure_connection()
        if not ib:
            print(f"❌ Could not connect to IBKR")
            return None
        
        print(f"\n🔍 Testing alternative news approach for {symbol}...")
        
        # Try getting news without specific contract - using general news
        try:
            # Method 1: Try to get general news that might include our symbol
            print("📰 Attempting to fetch general market news...")
            
            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=3)
            start_date_str = start_date.strftime('%Y%m%d-00:00:00')
            end_date_str = end_date.strftime('%Y%m%d-23:59:59')
            
            # Try general news request (without specific contract)
            general_news = ib.reqHistoricalNews(
                conId=0,  # Use 0 for general news
                providerCodes="BRFG",
                startDateTime=start_date_str,
                endDateTime=end_date_str,
                totalResults=20
            )
            
            if general_news:
                print(f"✅ Found {len(general_news)} general market articles")
                
                # Filter for articles that mention our symbol
                relevant_articles = []
                for article in general_news:
                    if symbol.upper() in article.headline.upper():
                        relevant_articles.append(article)
                        print(f"📰 Relevant: {article.headline}")
                
                print(f"🎯 Found {len(relevant_articles)} articles mentioning {symbol}")
                return relevant_articles
            
        except Exception as e:
            print(f"⚠️  General news approach failed: {e}")
        
        # Method 2: Try with a known working ConId (if available)
        print("🔄 Trying manual ConId lookup...")
        
        # Common ConIds for major stocks (these are examples - may change)
        known_conids = {
            'AAPL': 265598,  # Apple
            'MSFT': 272093,  # Microsoft  
            'GOOGL': 208813720,  # Google
            'TSLA': 76792991,  # Tesla
            'AMZN': 3691937,  # Amazon
        }
        
        if symbol.upper() in known_conids:
            try:
                test_conid = known_conids[symbol.upper()]
                print(f"🧪 Testing with known ConId {test_conid} for {symbol}")
                
                news_articles = ib.reqHistoricalNews(
                    conId=test_conid,
                    providerCodes="BRFG",
                    startDateTime=start_date_str,
                    endDateTime=end_date_str,
                    totalResults=10
                )
                
                if news_articles:
                    print(f"✅ Success! Found {len(news_articles)} articles for {symbol}")
                    for i, article in enumerate(news_articles[:3], 1):
                        print(f"   {i}. {article.headline}")
                    return news_articles
                
            except Exception as e:
                print(f"⚠️  Known ConId approach failed: {e}")
        
        print(f"❌ All alternative approaches failed for {symbol}")
        return None
        
    except Exception as e:
        print(f"❌ Alternative news test failed: {e}")
        return None

async def diagnose_news_issue():
    """Diagnose what's wrong with news API access"""
    try:
        ib = await ensure_connection()
        if not ib:
            print("❌ Cannot diagnose - no IB connection")
            return
        
        print("🔍 DIAGNOSING NEWS API ISSUES")
        print("=" * 40)
        
        # Test 1: Check account capabilities
        print("\n1️⃣ Checking account information...")
        try:
            account_summary = ib.accountSummary()
            print(f"✅ Account summary retrieved: {len(account_summary)} items")
        except Exception as e:
            print(f"❌ Account summary failed: {e}")
        
        # Test 2: Check news providers again
        print("\n2️⃣ Checking news providers...")
        try:
            providers = ib.reqNewsProviders()
            print(f"✅ Found {len(providers)} news providers")
            for p in providers[:3]:  # Show first 3
                print(f"   📡 {p.code}: {p.name}")
        except Exception as e:
            print(f"❌ News providers failed: {e}")
        
        # Test 3: Test basic contract lookup
        print("\n3️⃣ Testing basic contract lookup...")
        test_symbols = ['AAPL', 'MSFT', 'SPY']
        
        for symbol in test_symbols:
            try:
                print(f"\n   Testing {symbol}:")
                
                # Try reqContractDetails first
                contract = Stock(symbol, 'SMART', 'USD')
                details = ib.reqContractDetails(contract)
                
                if details:
                    detail = details[0]
                    print(f"   ✅ {symbol}: ConId={detail.contract.conId}, Exchange={detail.contract.exchange}")
                    
                    # Try a simple news request with this ConId
                    try:
                        end_date = datetime.now()
                        start_date = end_date - timedelta(days=1)
                        start_str = start_date.strftime('%Y%m%d-00:00:00')
                        end_str = end_date.strftime('%Y%m%d-23:59:59')
                        
                        test_news = ib.reqHistoricalNews(
                            conId=detail.contract.conId,
                            providerCodes="BRFG",
                            startDateTime=start_str,
                            endDateTime=end_str,
                            totalResults=1
                        )
                        
                        print(f"   📰 News test: {'✅ SUCCESS' if test_news else '❌ NO ARTICLES'}")
                        
                    except Exception as news_err:
                        print(f"   📰 News test failed: {news_err}")
                else:
                    print(f"   ❌ {symbol}: No contract details found")
                    
            except Exception as e:
                print(f"   ❌ {symbol}: Contract lookup failed: {e}")
        
        # Test 4: Check permissions/subscriptions
        print("\n4️⃣ Checking for common issues...")
        print("   💡 Common reasons for news API failures:")
        print("      • News data subscription not active")
        print("      • Account permissions don't include news")
        print("      • Paper trading account (may have limited news)")
        print("      • Need to enable news data in TWS/Gateway")
        print("      • Market data permissions issue")
        
        print("\n📋 RECOMMENDATIONS:")
        print("   1. Check TWS/Gateway: Configuration → Data Subscriptions → News")
        print("   2. Verify account has news data permissions")
        print("   3. Try with live trading account if using paper trading")
        print("   4. Contact IBKR support about news data access")
        
    except Exception as e:
        print(f"❌ Diagnosis failed: {e}")

# Add this to the test integration function
async def test_news_integration_enhanced():
    """Enhanced news integration test with better diagnostics"""
    print("🚀 ENHANCED NEWS INTEGRATION TEST")
    print("=" * 40)
    
    # Test 1: Basic diagnostics
    print("\n🔍 Running diagnostics...")
    await diagnose_news_issue()
    
    # Test 2: Alternative news approach
    print("\n🔍 Testing alternative news methods...")
    await test_news_without_contract('AAPL')
    
    # Test 3: Try manual approach
    print("\n🔍 Testing manual news lookup...")
    try:
        ib = await ensure_connection()
        if ib:
            # Try to get any recent news at all
            print("📰 Attempting to get any recent market news...")
            
            end_date = datetime.now()
            start_date = end_date - timedelta(days=1)
            start_str = start_date.strftime('%Y%m%d-00:00:00')
            end_str = end_date.strftime('%Y%m%d-23:59:59')
            
            try:
                any_news = ib.reqHistoricalNews(
                    conId=0,  # General news
                    providerCodes="BRFG",
                    startDateTime=start_str,
                    endDateTime=end_str,
                    totalResults=5
                )
                
                if any_news:
                    print(f"✅ Successfully retrieved {len(any_news)} general market articles!")
                    for i, article in enumerate(any_news[:2], 1):
                        print(f"   {i}. {article.headline}")
                else:
                    print("❌ No general news articles retrieved")
                    
            except Exception as e:
                print(f"❌ General news request failed: {e}")
    
    except Exception as e:
        print(f"❌ Manual test failed: {e}")

# Update the main test function
async def test_news_integration():
    """Test news integration with your existing trading system"""
    print("🚀 TESTING NEWS INTEGRATION WITH EXISTING SYSTEM")
    print("=" * 50)
    
    # Run enhanced diagnostics instead
    await test_news_integration_enhanced()

# Easy-to-use function for integration into your main trading loop
async def get_portfolio_news_summary(days_back: int = 3, max_articles_per_stock: int = 5):
    """Get news summary for portfolio stocks - ready for integration"""
    try:
        news_summary = {}
        
        for symbol in PORTFOLIO_STOCKS[:3]:  # Limit to avoid rate limits
            news_data = await get_stock_news(symbol, days_back, max_articles_per_stock)
            
            if news_data and news_data['articles']:
                sentiment = analyze_news_sentiment(news_data['articles'])
                news_summary[symbol] = {
                    'article_count': news_data['articles_count'],
                    'sentiment_label': sentiment['sentiment_label'],
                    'avg_sentiment': sentiment['avg_sentiment'],
                    'latest_headlines': [a['headline'] for a in news_data['articles'][:3]]
                }
            else:
                news_summary[symbol] = {
                    'article_count': 0,
                    'sentiment_label': 'NO_DATA',
                    'avg_sentiment': 0,
                    'latest_headlines': []
                }
            
            await asyncio.sleep(1)  # Rate limiting
        
        return news_summary
        
    except Exception as e:
        print(f"❌ Error in portfolio news summary: {e}")
        log_portfolio_activity("portfolio_news_error", {"error": str(e)})
        return {}

# QUICK TEST RUNNER FOR IMMEDIATE TESTING
async def run_enhanced_news_test():
    """Quick test runner to diagnose and test news functionality"""
    print("🔍 ENHANCED NEWS API TESTING")
    print("=" * 30)
    
    # Step 1: Run diagnostics
    await diagnose_news_issue()
    
    # Step 2: Try alternative approaches
    print(f"\n{'='*50}")
    print("🧪 TESTING ALTERNATIVE NEWS APPROACHES")
    print(f"{'='*50}")
    
    # Test alternative approach
    await test_news_without_contract('AAPL')
    
    return True

# TO RUN THIS TEST IMMEDIATELY:
# import asyncio
# await run_enhanced_news_test()

# Example usage in your main trading system:
# news_summary = await get_portfolio_news_summary()
# for symbol, news_data in news_summary.items():
#     print(f"{symbol}: {news_data['sentiment_label']} ({news_data['article_count']} articles)")