# /trading_bot/news_gcs_integration.py - GCS News Data Integration

import os
import json
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from google.cloud import storage
import logging

class GCSNewsIntegration:
    def __init__(self, bucket_name="portfolio_reports_algo"):
        self.bucket_name = bucket_name
        self.local_news_dir = Path("news_data")
        self.local_news_dir.mkdir(exist_ok=True)
        
        # Setup GCS client
        try:
            self.storage_client = storage.Client.from_service_account_json('service-account-key.json')
        except:
            # Fallback to default credentials
            self.storage_client = storage.Client()
            
        self.bucket = self.storage_client.bucket(bucket_name)
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
    def get_cached_news_path(self, date: str) -> Path:
        """Get local cached news file path"""
        return self.local_news_dir / f"market_news_{date.replace('-', '')}.json"
    
    def is_news_cached(self, date: str) -> bool:
        """Check if news data is already cached locally"""
        cache_path = self.get_cached_news_path(date)
        return cache_path.exists()
    
    def download_news_from_gcs(self, date: str) -> Optional[Dict]:
        """Download news data from GCS for a specific date"""
        try:
            gcs_path = f"market_data/{date}/market_news.json"
            blob = self.bucket.blob(gcs_path)
            
            if blob.exists():
                self.logger.info(f"Downloading news data from GCS: {gcs_path}")
                content = blob.download_as_text()
                news_data = json.loads(content)
                
                # Cache locally
                cache_path = self.get_cached_news_path(date)
                with open(cache_path, 'w') as f:
                    json.dump(news_data, f, indent=2)
                
                self.logger.info(f"News data cached locally: {cache_path}")
                return news_data
            else:
                self.logger.warning(f"News data not found in GCS: {gcs_path}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error downloading news from GCS for {date}: {e}")
            return None
    
    def load_cached_news(self, date: str) -> Optional[Dict]:
        """Load news data from local cache"""
        try:
            cache_path = self.get_cached_news_path(date)
            if cache_path.exists():
                with open(cache_path, 'r') as f:
                    return json.load(f)
            return None
        except Exception as e:
            self.logger.error(f"Error loading cached news for {date}: {e}")
            return None
    
    def get_news_for_date(self, date: str) -> Optional[Dict]:
        """Get news data for a specific date (cache-first approach)"""
        # First check local cache
        if self.is_news_cached(date):
            self.logger.info(f"Loading news from cache for {date}")
            return self.load_cached_news(date)
        
        # If not cached, download from GCS
        return self.download_news_from_gcs(date)
    
    def download_recent_news(self, days_back: int = 7) -> List[Dict]:
        """Download news for the last N days"""
        downloaded_news = []
        
        for i in range(days_back):
            date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
            news_data = self.get_news_for_date(date)
            
            if news_data:
                news_data['analysis_date'] = date
                downloaded_news.append(news_data)
                self.logger.info(f"Downloaded news for {date}: {len(news_data.get('headlines', []))} articles")
            else:
                self.logger.info(f"No news data available for {date}")
        
        return downloaded_news
    
    def convert_to_trading_format(self, gcs_news_data: Dict, symbols: List[str]) -> Dict:
        """Convert GCS news format to trading bot expected format"""
        if not gcs_news_data:
            return {}
        
        # Get headlines from GCS format
        headlines = gcs_news_data.get('headlines', [])
        sentiment_summary = gcs_news_data.get('sentiment_summary', {})
        
        # Create trading format for each symbol
        trading_news = {}
        
        for symbol in symbols:
            # Filter headlines relevant to this symbol
            relevant_headlines = []
            
            for headline in headlines:
                title = headline.get('title', '').lower()
                description = headline.get('description', '').lower()
                
                # Simple symbol matching (you can enhance this)
                if (symbol.lower() in title or symbol.lower() in description or
                    any(company_name in title for company_name in self._get_company_names(symbol))):
                    relevant_headlines.append(headline)
            
            # If no specific headlines, use general market sentiment
            if not relevant_headlines:
                relevant_headlines = headlines[:3]  # Use top 3 general market headlines
            
            # Analyze sentiment for this symbol
            symbol_sentiment = self._analyze_symbol_sentiment(relevant_headlines)
            
            trading_news[symbol] = {
                'article_count': len(relevant_headlines),
                'sentiment_label': symbol_sentiment['label'],
                'sentiment_score': symbol_sentiment['score'],
                'sentiment_emoji': symbol_sentiment['emoji'],
                'latest_headlines': [h.get('title', '') for h in relevant_headlines[:3]],
                'has_news': len(relevant_headlines) > 0,
                'summary': f"{symbol_sentiment['label']} sentiment from {len(relevant_headlines)} articles",
                'source': 'GCS Market Data'
            }
        
        return trading_news
    
    def _get_company_names(self, symbol: str) -> List[str]:
        """Get company names for symbol matching"""
        company_map = {
            'AAPL': ['apple', 'iphone', 'ipad', 'mac'],
            'MSFT': ['microsoft', 'windows', 'azure', 'office'],
            'GOOGL': ['google', 'alphabet', 'search', 'youtube'],
            'GOOG': ['google', 'alphabet', 'search', 'youtube'],
            'META': ['meta', 'facebook', 'instagram', 'whatsapp'],
            'AMZN': ['amazon', 'aws', 'prime', 'alexa'],
            'TSLA': ['tesla', 'elon musk', 'electric vehicle'],
            'NVDA': ['nvidia', 'gpu', 'ai chip'],
            'NFLX': ['netflix', 'streaming'],
            'CRM': ['salesforce'],
            'ADBE': ['adobe', 'photoshop']
        }
        return company_map.get(symbol, [symbol.lower()])
    
    def _analyze_symbol_sentiment(self, headlines: List[Dict]) -> Dict:
        """Analyze sentiment for symbol-specific headlines"""
        if not headlines:
            return {
                'label': 'NO_DATA',
                'score': 0,
                'emoji': '❓'
            }
        
        positive_keywords = ['rally', 'surge', 'gains', 'up', 'bullish', 'optimistic', 'growth', 'strong', 'beat', 'exceed']
        negative_keywords = ['fall', 'drop', 'decline', 'down', 'bearish', 'pessimistic', 'weak', 'concern', 'miss', 'disappoint']
        
        sentiment_scores = []
        
        for headline in headlines:
            title = headline.get('title', '').lower()
            description = headline.get('description', '').lower()
            text = f"{title} {description}"
            
            pos_count = sum(1 for word in positive_keywords if word in text)
            neg_count = sum(1 for word in negative_keywords if word in text)
            
            # Score: positive words - negative words
            score = pos_count - neg_count
            sentiment_scores.append(score)
        
        # Average sentiment
        avg_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0
        
        # Classify sentiment
        if avg_sentiment > 0.3:
            return {'label': 'POSITIVE', 'score': avg_sentiment, 'emoji': '📈'}
        elif avg_sentiment < -0.3:
            return {'label': 'NEGATIVE', 'score': avg_sentiment, 'emoji': '📉'}
        else:
            return {'label': 'NEUTRAL', 'score': avg_sentiment, 'emoji': '⚖️'}
    
    def get_latest_available_news(self, symbols: List[str], max_days_back: int = 5) -> Dict:
        """Get the most recent available news data in trading format"""
        for i in range(max_days_back):
            date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
            gcs_news = self.get_news_for_date(date)
            
            if gcs_news and gcs_news.get('headlines'):
                self.logger.info(f"Using news data from {date} ({len(gcs_news['headlines'])} articles)")
                return self.convert_to_trading_format(gcs_news, symbols)
        
        self.logger.warning(f"No news data found in the last {max_days_back} days")
        return self._create_empty_news_response(symbols)
    
    def _create_empty_news_response(self, symbols: List[str]) -> Dict:
        """Create empty news response when no data is available"""
        empty_news = {}
        for symbol in symbols:
            empty_news[symbol] = {
                'article_count': 0,
                'sentiment_label': 'NO_DATA',
                'sentiment_score': 0,
                'sentiment_emoji': '❓',
                'latest_headlines': [],
                'has_news': False,
                'summary': 'No recent news data available',
                'source': 'GCS Market Data'
            }
        return empty_news

# Main integration function for your trading system
async def get_gcs_news_summary_for_trading(symbols: List[str] = None) -> Dict:
    """
    Main function to get news summary from GCS for trading decisions
    This replaces your current get_news_summary_for_trading() function
    """
    try:
        if symbols is None:
            from config import PORTFOLIO_STOCKS
            symbols = PORTFOLIO_STOCKS
        
        # Initialize GCS integration
        gcs_news = GCSNewsIntegration()
        
        print(f"📰 Getting GCS news data for {len(symbols)} symbols...")
        
        # Get latest available news
        news_summary = gcs_news.get_latest_available_news(symbols)
        
        # Log summary
        total_articles = sum(data.get('article_count', 0) for data in news_summary.values())
        symbols_with_news = sum(1 for data in news_summary.values() if data.get('has_news', False))
        
        print(f"✅ GCS News Summary: {total_articles} total articles for {symbols_with_news}/{len(symbols)} symbols")
        
        return news_summary
        
    except Exception as e:
        print(f"❌ Error in GCS news integration: {e}")
        import traceback
        traceback.print_exc()
        
        # Return empty response on error
        return {symbol: {
            'article_count': 0,
            'sentiment_label': 'ERROR',
            'sentiment_score': 0,
            'sentiment_emoji': '⚠️',
            'latest_headlines': [],
            'has_news': False,
            'summary': f'Error loading news: {str(e)}',
            'source': 'GCS Market Data'
        } for symbol in symbols or []}

# Startup function to download recent news
async def initialize_news_cache(days_back: int = 3):
    """Initialize news cache by downloading recent data from GCS"""
    try:
        print(f"🔄 Initializing news cache for last {days_back} days...")
        
        gcs_news = GCSNewsIntegration()
        downloaded_news = gcs_news.download_recent_news(days_back)
        
        print(f"✅ News cache initialized: {len(downloaded_news)} days of data downloaded")
        
        # Show summary
        for news_data in downloaded_news:
            date = news_data.get('analysis_date', 'Unknown')
            headlines_count = len(news_data.get('headlines', []))
            sentiment = news_data.get('sentiment_summary', {}).get('overall_sentiment', 'Unknown')
            print(f"   📅 {date}: {headlines_count} articles, {sentiment} sentiment")
        
        return True
        
    except Exception as e:
        print(f"❌ Error initializing news cache: {e}")
        return False

# Test function
async def test_gcs_news_integration():
    """Test the GCS news integration"""
    print("🧪 Testing GCS News Integration")
    print("=" * 40)
    
    # Test symbols
    test_symbols = ['AAPL', 'MSFT', 'GOOGL']
    
    # Test getting news
    news_data = await get_gcs_news_summary_for_trading(test_symbols)
    
    print(f"\n📊 Test Results:")
    for symbol, data in news_data.items():
        print(f"{data['sentiment_emoji']} {symbol}: {data['sentiment_label']} ({data['article_count']} articles)")
        if data['latest_headlines']:
            print(f"   📰 Latest: {data['latest_headlines'][0]}")
    
    return len(news_data) > 0

if __name__ == "__main__":
    # Run test
    asyncio.run(test_gcs_news_integration())