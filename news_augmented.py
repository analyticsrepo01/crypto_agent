# /trading_bot/news_augmented.py - Augmented News System (IBKR + GCS + Gemini)

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from config import PORTFOLIO_STOCKS, gemini_model, USE_IBKR_NEWS, USE_GCS_NEWS, USE_GEMINI_ANALYSIS
from news_working import get_stock_news_working, analyze_news_sentiment_enhanced
from news_gcs_integration import GCSNewsIntegration, initialize_news_cache

class AugmentedNewsSystem:
    """
    Combines IBKR news, GCS market news, and Gemini AI summarization
    to provide comprehensive news analysis for each symbol
    
    Supports configuration switches to enable/disable each news source:
    - USE_IBKR_NEWS: Enable/disable IBKR real-time news
    - USE_GCS_NEWS: Enable/disable GCS market news from Cloud Run app
    - USE_GEMINI_ANALYSIS: Enable/disable AI-powered news analysis
    """
    
    def __init__(self):
        self.gcs_integration = GCSNewsIntegration() if USE_GCS_NEWS else None
        self.print_config_status()
    
    def print_config_status(self):
        """Print the current news configuration status"""
        print(f"📰 News Configuration:")
        print(f"   IBKR News: {'✅ ENABLED' if USE_IBKR_NEWS else '❌ DISABLED'}")
        print(f"   GCS News: {'✅ ENABLED' if USE_GCS_NEWS else '❌ DISABLED'}")
        print(f"   Gemini AI: {'✅ ENABLED' if USE_GEMINI_ANALYSIS else '❌ DISABLED'}")
        
        if not USE_IBKR_NEWS and not USE_GCS_NEWS:
            print(f"   ⚠️ WARNING: All news sources disabled - trading without news sentiment")
        elif not USE_GEMINI_ANALYSIS:
            print(f"   ⚠️ NOTE: AI analysis disabled - using basic sentiment only")
        
    async def get_comprehensive_news_for_symbol(self, symbol: str) -> Dict:
        """Get comprehensive news analysis for a single symbol using all sources"""
        try:
            print(f"📰 Getting comprehensive news for {symbol}...")
            
            # Source 1: IBKR News (your existing working system)
            ibkr_news = await self._get_ibkr_news_for_symbol(symbol)
            
            # Source 2: GCS Market News (from your Cloud Run app)
            gcs_news = await self._get_gcs_news_for_symbol(symbol)
            
            # Combine both sources
            combined_news = self._combine_news_sources(symbol, ibkr_news, gcs_news)
            
            # Source 3: Gemini AI Analysis (summarize and analyze all news)
            ai_analysis = await self._get_ai_news_analysis(symbol, combined_news)
            
            # Create final comprehensive response
            comprehensive_news = {
                'symbol': symbol,
                'has_news': combined_news['has_news'],
                'total_articles': combined_news['total_articles'],
                
                # Source breakdown
                'sources': {
                    'ibkr': ibkr_news,
                    'gcs_market': gcs_news,
                    'ai_analysis': ai_analysis
                },
                
                # Unified metrics for trading decisions
                'sentiment_label': ai_analysis.get('final_sentiment', 'NEUTRAL'),
                'sentiment_score': ai_analysis.get('sentiment_score', 0),
                'sentiment_emoji': ai_analysis.get('sentiment_emoji', '⚖️'),
                'confidence_level': ai_analysis.get('confidence', 'MEDIUM'),
                
                # Trading insights
                'key_themes': ai_analysis.get('key_themes', []),
                'trading_impact': ai_analysis.get('trading_impact', 'Neutral'),
                'risk_factors': ai_analysis.get('risk_factors', []),
                'catalysts': ai_analysis.get('catalysts', []),
                
                # Headlines from all sources
                'latest_headlines': combined_news['all_headlines'][:5],
                'summary': ai_analysis.get('executive_summary', 'No significant news impact detected'),
                
                'timestamp': datetime.now().isoformat()
            }
            
            print(f"✅ {symbol}: {comprehensive_news['sentiment_emoji']} {comprehensive_news['sentiment_label']} - {comprehensive_news['total_articles']} articles")
            
            return comprehensive_news
            
        except Exception as e:
            print(f"❌ Error getting comprehensive news for {symbol}: {e}")
            return self._create_error_response(symbol, str(e))
    
    async def _get_ibkr_news_for_symbol(self, symbol: str) -> Dict:
        """Get IBKR news for a specific symbol"""
        try:
            # Check if IBKR news is enabled
            if not USE_IBKR_NEWS:
                print(f"📰 IBKR news disabled for {symbol}")
                return {
                    'source': 'IBKR',
                    'article_count': 0,
                    'articles': [],
                    'sentiment': {'sentiment_label': 'DISABLED'},
                    'headlines': [],
                    'success': False,
                    'disabled': True
                }
            
            # Use your existing working IBKR news function
            news_data = await get_stock_news_working(symbol, days_back=2, max_articles=8)
            
            if news_data and news_data.get('articles'):
                sentiment = analyze_news_sentiment_enhanced(news_data['articles'])
                
                return {
                    'source': 'IBKR',
                    'article_count': news_data['articles_count'],
                    'articles': news_data['articles'],
                    'sentiment': sentiment,
                    'headlines': [a['headline'] for a in news_data['articles']],
                    'success': True
                }
            else:
                return {
                    'source': 'IBKR',
                    'article_count': 0,
                    'articles': [],
                    'sentiment': {'sentiment_label': 'NO_DATA'},
                    'headlines': [],
                    'success': False
                }
                
        except Exception as e:
            print(f"⚠️ IBKR news error for {symbol}: {e}")
            return {
                'source': 'IBKR',
                'article_count': 0,
                'articles': [],
                'sentiment': {'sentiment_label': 'ERROR'},
                'headlines': [],
                'success': False,
                'error': str(e)
            }
    
    async def _get_gcs_news_for_symbol(self, symbol: str) -> Dict:
        """Get GCS market news relevant to a specific symbol"""
        try:
            # Check if GCS news is enabled
            if not USE_GCS_NEWS:
                print(f"📰 GCS news disabled for {symbol}")
                return {
                    'source': 'GCS_Market',
                    'article_count': 0,
                    'sentiment_label': 'DISABLED',
                    'headlines': [],
                    'success': False,
                    'disabled': True
                }
            
            # Get latest GCS news data
            gcs_news_data = self.gcs_integration.get_latest_available_news([symbol])
            symbol_news = gcs_news_data.get(symbol, {})
            
            if symbol_news.get('has_news', False):
                return {
                    'source': 'GCS_Market',
                    'article_count': symbol_news.get('article_count', 0),
                    'sentiment_label': symbol_news.get('sentiment_label', 'NEUTRAL'),
                    'sentiment_score': symbol_news.get('sentiment_score', 0),
                    'headlines': symbol_news.get('latest_headlines', []),
                    'summary': symbol_news.get('summary', ''),
                    'success': True
                }
            else:
                return {
                    'source': 'GCS_Market',
                    'article_count': 0,
                    'sentiment_label': 'NO_DATA',
                    'headlines': [],
                    'success': False
                }
                
        except Exception as e:
            print(f"⚠️ GCS news error for {symbol}: {e}")
            return {
                'source': 'GCS_Market',
                'article_count': 0,
                'sentiment_label': 'ERROR',
                'headlines': [],
                'success': False,
                'error': str(e)
            }
    
    def _combine_news_sources(self, symbol: str, ibkr_news: Dict, gcs_news: Dict) -> Dict:
        """Combine news from both sources"""
        all_headlines = []
        total_articles = 0
        has_news = False
        
        # Combine IBKR headlines
        if ibkr_news.get('success', False):
            all_headlines.extend(ibkr_news.get('headlines', []))
            total_articles += ibkr_news.get('article_count', 0)
            has_news = True
        
        # Combine GCS headlines
        if gcs_news.get('success', False):
            all_headlines.extend(gcs_news.get('headlines', []))
            total_articles += gcs_news.get('article_count', 0)
            has_news = True
        
        return {
            'symbol': symbol,
            'has_news': has_news,
            'total_articles': total_articles,
            'all_headlines': all_headlines,
            'ibkr_count': ibkr_news.get('article_count', 0),
            'gcs_count': gcs_news.get('article_count', 0)
        }
    
    async def _get_ai_news_analysis(self, symbol: str, combined_news: Dict) -> Dict:
        """Use Gemini to analyze and summarize all news for the symbol"""
        try:
            # Check if Gemini analysis is enabled
            if not USE_GEMINI_ANALYSIS:
                print(f"🤖 Gemini analysis disabled for {symbol}")
                return {
                    'final_sentiment': 'DISABLED',
                    'sentiment_score': 0,
                    'sentiment_emoji': '⚙️',
                    'confidence': 'DISABLED',
                    'executive_summary': 'AI news analysis disabled by configuration',
                    'key_themes': [],
                    'trading_impact': 'Disabled',
                    'risk_factors': [],
                    'catalysts': [],
                    'disabled': True
                }
            
            if not combined_news.get('has_news', False):
                return {
                    'final_sentiment': 'NO_DATA',
                    'sentiment_score': 0,
                    'sentiment_emoji': '❓',
                    'confidence': 'LOW',
                    'executive_summary': 'No recent news data available for analysis',
                    'key_themes': [],
                    'trading_impact': 'Neutral',
                    'risk_factors': [],
                    'catalysts': []
                }
            
            # Prepare news content for Gemini
            headlines_text = "\n".join([f"- {headline}" for headline in combined_news['all_headlines']])
            
            prompt = f"""
            You are an expert financial news analyst. Analyze the following news headlines for {symbol} and provide a comprehensive trading-focused summary.

            NEWS HEADLINES FOR {symbol}:
            {headlines_text}

            ANALYSIS REQUIREMENTS:
            1. Determine overall sentiment impact on {symbol} stock price
            2. Identify key themes and market drivers
            3. Assess potential trading impact (bullish/bearish/neutral)
            4. Identify specific risk factors for traders
            5. Identify potential catalysts for price movement
            6. Provide confidence level in your analysis

            Respond in the following JSON format:
            {{
                "final_sentiment": "POSITIVE|NEGATIVE|NEUTRAL",
                "sentiment_score": -1.0 to 1.0,
                "sentiment_emoji": "📈|📉|⚖️",
                "confidence": "HIGH|MEDIUM|LOW",
                "executive_summary": "Brief 2-3 sentence summary of trading impact",
                "key_themes": ["theme1", "theme2", "theme3"],
                "trading_impact": "Strong Bullish|Bullish|Neutral|Bearish|Strong Bearish",
                "risk_factors": ["risk1", "risk2"],
                "catalysts": ["catalyst1", "catalyst2"]
            }}

            IMPORTANT: 
            - Focus on trading/investment implications
            - Be specific about {symbol}'s prospects
            - Consider both short-term and medium-term impacts
            - Provide actionable insights for algorithmic trading decisions
            """
            
            response = await gemini_model.generate_content_async(prompt)
            
            # Parse JSON response
            try:
                # Extract JSON from response
                response_text = response.text.strip()
                
                # Find JSON block
                start_idx = response_text.find('{')
                end_idx = response_text.rfind('}') + 1
                
                if start_idx != -1 and end_idx != -1:
                    json_text = response_text[start_idx:end_idx]
                    analysis = json.loads(json_text)
                    
                    # Validate and set defaults
                    analysis['sentiment_score'] = float(analysis.get('sentiment_score', 0))
                    analysis['final_sentiment'] = analysis.get('final_sentiment', 'NEUTRAL')
                    analysis['sentiment_emoji'] = analysis.get('sentiment_emoji', '⚖️')
                    analysis['confidence'] = analysis.get('confidence', 'MEDIUM')
                    
                    return analysis
                else:
                    raise ValueError("No valid JSON found in response")
                    
            except (json.JSONDecodeError, ValueError) as e:
                print(f"⚠️ Error parsing Gemini response for {symbol}: {e}")
                # Fallback to basic analysis
                return self._create_fallback_analysis(combined_news)
                
        except Exception as e:
            print(f"❌ Gemini analysis error for {symbol}: {e}")
            return self._create_fallback_analysis(combined_news)
    
    def _create_fallback_analysis(self, combined_news: Dict) -> Dict:
        """Create fallback analysis when Gemini fails"""
        return {
            'final_sentiment': 'NEUTRAL',
            'sentiment_score': 0,
            'sentiment_emoji': '⚖️',
            'confidence': 'LOW',
            'executive_summary': f"Basic analysis: {combined_news.get('total_articles', 0)} news articles found, AI analysis unavailable",
            'key_themes': ['News available', 'Analysis pending'],
            'trading_impact': 'Neutral',
            'risk_factors': ['AI analysis unavailable'],
            'catalysts': []
        }
    
    def _create_error_response(self, symbol: str, error_msg: str) -> Dict:
        """Create error response"""
        return {
            'symbol': symbol,
            'has_news': False,
            'total_articles': 0,
            'sentiment_label': 'ERROR',
            'sentiment_score': 0,
            'sentiment_emoji': '⚠️',
            'confidence_level': 'LOW',
            'key_themes': [],
            'trading_impact': 'Error',
            'risk_factors': [f'News system error: {error_msg}'],
            'catalysts': [],
            'latest_headlines': [],
            'summary': f'Error retrieving news: {error_msg}',
            'timestamp': datetime.now().isoformat()
        }

# Main function to replace your current get_news_summary_for_trading()
async def get_augmented_news_summary_for_trading(symbols: List[str] = None) -> Dict:
    """
    Get comprehensive news summary using IBKR + GCS + Gemini AI
    This augments your existing news system with additional sources and AI analysis
    Respects configuration switches for each news source
    """
    try:
        if symbols is None:
            symbols = PORTFOLIO_STOCKS
        
        # Check if all news sources are disabled
        if not USE_IBKR_NEWS and not USE_GCS_NEWS:
            print(f"📰 All news sources disabled - returning empty news data for {len(symbols)} symbols")
            return {symbol: {
                'symbol': symbol,
                'has_news': False,
                'total_articles': 0,
                'sentiment_label': 'DISABLED',
                'sentiment_score': 0,
                'sentiment_emoji': '⚙️',
                'confidence_level': 'DISABLED',
                'key_themes': [],
                'trading_impact': 'News Disabled',
                'risk_factors': [],
                'catalysts': [],
                'latest_headlines': [],
                'summary': 'All news sources disabled by configuration',
                'sources_used': 0,
                'timestamp': datetime.now().isoformat(),
                'disabled': True
            } for symbol in symbols}
        
        print(f"🤖 Getting augmented news analysis for {len(symbols)} symbols...")
        
        # Initialize augmented news system
        news_system = AugmentedNewsSystem()
        
        # Process symbols in parallel for better performance
        async def process_symbol(symbol):
            return symbol, await news_system.get_comprehensive_news_for_symbol(symbol)
        
        # Create tasks for parallel processing
        tasks = [process_symbol(symbol) for symbol in symbols]
        
        # Execute in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        augmented_news = {}
        total_articles = 0
        symbols_with_news = 0
        
        for result in results:
            if isinstance(result, Exception):
                print(f"❌ Task failed: {result}")
                continue
                
            symbol, news_data = result
            augmented_news[symbol] = news_data
            
            total_articles += news_data.get('total_articles', 0)
            if news_data.get('has_news', False):
                symbols_with_news += 1
        
        print(f"✅ Augmented News Complete: {total_articles} articles, {symbols_with_news}/{len(symbols)} symbols with news")
        
        return augmented_news
        
    except Exception as e:
        print(f"❌ Error in augmented news system: {e}")
        import traceback
        traceback.print_exc()
        
        # Return basic fallback
        return {symbol: {
            'symbol': symbol,
            'has_news': False,
            'sentiment_label': 'ERROR',
            'sentiment_score': 0,
            'sentiment_emoji': '⚠️',
            'summary': f'News system error: {str(e)}',
            'latest_headlines': [],
            'total_articles': 0
        } for symbol in symbols or PORTFOLIO_STOCKS}

# Backwards compatibility function - this preserves your existing interface
async def get_news_summary_for_trading():
    """
    Enhanced version of your original function with augmented news sources
    Maintains the same interface but provides richer data
    """
    augmented_data = await get_augmented_news_summary_for_trading()
    
    # Convert to original format for backwards compatibility
    compatible_format = {}
    
    for symbol, data in augmented_data.items():
        compatible_format[symbol] = {
            'article_count': data.get('total_articles', 0),
            'sentiment_label': data.get('sentiment_label', 'NO_DATA'),
            'sentiment_score': data.get('sentiment_score', 0),
            'sentiment_emoji': data.get('sentiment_emoji', '❓'),
            'latest_headlines': data.get('latest_headlines', []),
            'has_news': data.get('has_news', False),
            'summary': data.get('summary', 'No news available'),
            
            # Enhanced fields (new)
            'confidence_level': data.get('confidence_level', 'MEDIUM'),
            'trading_impact': data.get('trading_impact', 'Neutral'),
            'key_themes': data.get('key_themes', []),
            'risk_factors': data.get('risk_factors', []),
            'catalysts': data.get('catalysts', []),
            'sources_used': len([s for s in data.get('sources', {}).values() if s.get('success', False)])
        }
    
    return compatible_format

# Test function
async def test_augmented_news():
    """Test the augmented news system"""
    print("🧪 Testing Augmented News System")
    print("=" * 50)
    
    # Test with a few symbols
    test_symbols = ['AAPL', 'MSFT']
    
    news_data = await get_augmented_news_summary_for_trading(test_symbols)
    
    for symbol, data in news_data.items():
        print(f"\n📊 {symbol} Analysis:")
        print(f"   {data['sentiment_emoji']} Sentiment: {data['sentiment_label']} (Score: {data['sentiment_score']:.2f})")
        print(f"   📰 Total Articles: {data['total_articles']}")
        print(f"   🎯 Trading Impact: {data['trading_impact']}")
        print(f"   📈 Key Themes: {', '.join(data.get('key_themes', [])[:3])}")
        if data.get('latest_headlines'):
            print(f"   📰 Latest: {data['latest_headlines'][0]}")

if __name__ == "__main__":
    # Run test
    asyncio.run(test_augmented_news())