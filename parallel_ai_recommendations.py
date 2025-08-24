# /trading_bot/parallel_ai_recommendations.py

import asyncio
from typing import Dict, List
import os
import json
from datetime import datetime
from config import gemini_model, PORTFOLIO_STOCKS, TRADE_SIZE, MIN_CASH_RESERVE, MAX_SHARES_PER_STOCK, MAX_TOTAL_SHARES, TRADING_FEE_PER_TRADE

def save_ai_prompt_log(symbol: str, prompt: str, response: str, recommendation: Dict, state: Dict):
    """Save AI prompt, response, and context to timestamped log file"""
    try:
        # Ensure logs directory exists
        os.makedirs("logs", exist_ok=True)
        
        # Create timestamp for filename and content
        timestamp = datetime.now()
        filename = f"logs/ai_analysis_{timestamp.strftime('%Y%m%d_%H%M%S')}_{symbol}.txt"
        
        # Extract key state information for context
        portfolio_summary = {
            'total_value': state.get('total_portfolio_value', 0),
            'cash_available': state.get('cash_available', 0),
            'total_pnl': state.get('total_unrealized_pnl', 0),
            'cycle_number': state.get('cycle_number', 0),
            'session_id': state.get('session_id', 'unknown'),
            'aggressive_mode': state.get('aggressive_mode', False)
        }
        
        # Get market data for this symbol
        stock_data = state.get('stock_data', {}).get(symbol, {})
        news_data = state.get('news_sentiment', {}).get(symbol, {})
        position = state.get('positions', {}).get(symbol, 0)
        
        # Create comprehensive log content
        log_content = f"""{'='*80}
AI TRADING ANALYSIS LOG
{'='*80}
Timestamp: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}
Symbol: {symbol}
Cycle: {state.get('cycle_number', 'N/A')}
Session: {state.get('session_id', 'N/A')}
Strategy Mode: {'AGGRESSIVE' if state.get('aggressive_mode', False) else 'BALANCED'}

{'='*80}
PORTFOLIO CONTEXT
{'='*80}
{json.dumps(portfolio_summary, indent=2)}

{'='*80}
CURRENT POSITION & MARKET DATA
{'='*80}
Position: {position} shares
Current Price: ${stock_data.get('current_price', 0):.2f}
Daily Change: {stock_data.get('daily_change_pct', 0):+.2f}%
RSI: {stock_data.get('rsi', 0):.1f}
News Sentiment: {news_data.get('sentiment_label', 'N/A')} ({news_data.get('sentiment_score', 0):+.2f})

{'='*80}
FULL AI PROMPT SENT
{'='*80}
{prompt}

{'='*80}
AI RESPONSE RECEIVED
{'='*80}
{response}

{'='*80}
PARSED RECOMMENDATION
{'='*80}
{json.dumps(recommendation, indent=2)}

{'='*80}
END OF LOG
{'='*80}
"""
        
        # Write to file
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(log_content)
        
        print(f"📝 AI analysis logged: {filename}")
        
    except Exception as e:
        print(f"⚠️ Failed to save AI log for {symbol}: {e}")

async def analyze_single_symbol(state: Dict, symbol: str) -> Dict:
    """
    Analyze a single symbol with full context and rich information
    """
    print(f"🔍 Analyzing {symbol} with full context...")
    
    # Extract all data for this specific symbol including dual timeframe data
    s_data = state['stock_data'].get(symbol, {})  # 5-minute data
    s_data_1h = state.get('stock_data_1h', {}).get(symbol, {})  # 1-hour data
    t_analysis = state['ai_trend_analysis'].get(symbol, {})
    pos = state['positions'].get(symbol, 0)
    news_sentiment = state.get('news_sentiment', {})
    news_data = news_sentiment.get(symbol, {})
    
    if not s_data.get('valid', False):
        return {
            'symbol': symbol,
            'action': 'HOLD',
            'priority': 'LOW',
            'reasoning': 'No valid market data available',
            'technical_score': 0,
            'confidence': 'LOW'
        }
    
    # Build comprehensive context for this ONE symbol
    strategy_instruction = ""
    if state.get('aggressive_mode', False):
        strategy_instruction = """
        AGGRESSIVE TRADING MODE ACTIVE:
        - MAXIMIZE PROFIT through decisive action
        - Accept higher risk for higher potential returns  
        - Consider technical scores 4+ as actionable for BUY
        - Consider technical scores 6- as actionable for SELL
        - Prioritize momentum and volume indicators
        - Be quick to enter/exit based on technical signals
        - Use positive news as strong confirmation for BUY signals
        - Use negative news as immediate trigger for SELL signals
        - News sentiment score +0.5 or higher = strong BUY boost
        - News sentiment score -0.5 or lower = immediate SELL consideration"""
    else:
        strategy_instruction = """
        BALANCED CRYPTO TRADING MODE ACTIVE:
        - Adapted for crypto's higher volatility (normal daily swings: 5-15%)
        - Require technical scores 5+ for high-priority BUY (lowered from 6+)
        - Require technical scores 5- for high-priority SELL (adjusted from 4-)
        - Accept 2-3 confirming indicators (reduced from multiple)
        - Allow trades during moderate volatility (crypto norm)
        - Only avoid trades during EXTREME volatility (>20% daily moves)
        - Focus on strong technical alignment with crypto-adjusted thresholds
        - Use news sentiment as critical risk assessment factor
        - Avoid BUY on negative news (sentiment < -0.2)
        - Avoid SELL on strongly positive news (sentiment > +0.5)
        - Allow trades with moderate technical+news alignment for crypto opportunities"""

    # Get memory context for this symbol specifically
    memory_context = state.get('memory_context', 'No trading history available')
    
    # CRITICAL: Calculate fee-aware profitability for current position
    fee_analysis_text = "No current position"
    if pos > 0:
        current_price = s_data.get('current_price', 0)
        purchase_price = state.get('purchase_prices', {}).get(symbol, 0)
        if current_price > 0 and purchase_price > 0:
            # Calculate fee-adjusted P&L
            gross_pnl = (current_price - purchase_price) * pos
            total_fees = TRADING_FEE_PER_TRADE * 2  # Buy + Sell fees
            net_pnl = gross_pnl - total_fees
            is_profitable = net_pnl > 0
            
            fee_analysis_text = f"""
            CURRENT POSITION PROFITABILITY ANALYSIS:
            - Position: {pos} shares @ ${purchase_price:.2f} → ${current_price:.2f}
            - Gross P&L: ${gross_pnl:+.2f}
            - Total Fees (Round-trip): ${total_fees:.2f}
            - Net P&L After Fees: ${net_pnl:+.2f}
            - Status: {'✅ PROFITABLE to sell' if is_profitable else '❌ UNPROFITABLE to sell'}
            """
    
    # Build news sentiment section for this symbol
    news_section = "No news data available"
    if news_data.get('has_news', False):
        sentiment_label = news_data.get('sentiment_label', 'NO_DATA')
        sentiment_score = news_data.get('sentiment_score', 0)
        article_count = news_data.get('article_count', 0)
        headlines = news_data.get('latest_headlines', [])
        
        news_section = f"""
        NEWS SENTIMENT FOR {symbol}:
        - Sentiment: {sentiment_label} (score: {sentiment_score:+.2f})
        - Articles analyzed: {article_count}
        - Key headline: {headlines[0] if headlines else 'No headlines available'}
        """
    
    # Comprehensive prompt for this ONE symbol
    prompt = f"""
    You are an expert quantitative trading analyst with deep technical analysis expertise and access to real-time news sentiment.
    
    {strategy_instruction}
    
    PORTFOLIO STATE:
    - Total Value: ${state['total_portfolio_value']:.2f}
    - Unrealized P&L: ${state['total_unrealized_pnl']:+.2f}
    - Available Cash: ${state['cash_available']:.2f}
    - Total Trades This Session: {state.get('total_trades', 0)}

    CONSTRAINTS:
    - Trade size: {TRADE_SIZE} shares per order
    - Max shares per stock: {MAX_SHARES_PER_STOCK}
    - Min cash reserve: ${MIN_CASH_RESERVE:,}
    - Max total shares: {MAX_TOTAL_SHARES}
    
    CRITICAL TRADING FEES & PROFITABILITY:
    - Trading fee per trade: ${TRADING_FEE_PER_TRADE:.2f} (both buy and sell)
    - Total fees per round trip: ${TRADING_FEE_PER_TRADE * 2:.2f}
    {fee_analysis_text}

    HISTORICAL TRADING CONTEXT:
    {memory_context}
    
    {news_section}
    
    COMPREHENSIVE DUAL TIMEFRAME ANALYSIS FOR {symbol}:
    
    CURRENT POSITION: {pos} shares
    
    === 5-MINUTE TIMEFRAME DATA (Short-term) ===
    PRICE DATA:
    - Current Price: ${s_data.get('current_price', 0):.2f}
    - Daily Change: {s_data.get('daily_change_pct', 0):+.2f}%
    - Previous Close: ${s_data.get('previous_close', 0):.2f}
    
    TECHNICAL INDICATORS (5M):
    - RSI (14): {s_data.get('rsi', 50):.1f}
    - MACD Histogram: {s_data.get('macd_histogram', 0):.3f}
    - MACD Line: {s_data.get('macd', 0):.3f}
    - MACD Signal: {s_data.get('macd_signal', 0):.3f}
    - SMA 20: ${s_data.get('sma_20', 0):.2f} | SMA 50: ${s_data.get('sma_50', 0):.2f}
    - Williams %R: {s_data.get('williams_r', -50):.1f}
    - Stochastic K: {s_data.get('stoch_k', 50):.1f}
    
    === 1-HOUR TIMEFRAME DATA (Medium-term) ===
    {"DATA AVAILABLE" if s_data_1h.get('valid', False) else "NO 1-HOUR DATA AVAILABLE"}
    {f'''PRICE DATA (1H):
    - Current Price: ${s_data_1h.get('current_price', 0):.2f}
    - Daily Change: {s_data_1h.get('daily_change_pct', 0):+.2f}%
    
    TECHNICAL INDICATORS (1H):
    - RSI (14): {s_data_1h.get('rsi', 50):.1f}
    - MACD Histogram: {s_data_1h.get('macd_histogram', 0):.3f}
    - SMA 20: ${s_data_1h.get('sma_20', 0):.2f} | SMA 50: ${s_data_1h.get('sma_50', 0):.2f}
    - Williams %R: {s_data_1h.get('williams_r', -50):.1f}
    - Stochastic K: {s_data_1h.get('stoch_k', 50):.1f}''' if s_data_1h.get('valid', False) else "Fallback to 5-minute analysis only"}
    
    === VOLUME & VOLATILITY ANALYSIS ===
    - Current Volume: {s_data.get('current_volume', 0):,.0f}
    - Volume MA: {s_data.get('volume_ma', 0):,.0f}
    - Volume Ratio: {(s_data.get('current_volume', 0) / max(s_data.get('volume_ma', 1), 1)):.2f}x average
    - ATR: {s_data.get('atr', 0):.3f}
    - 20-day Volatility: {s_data.get('volatility_20', 0):.3f}
    
    === AI TREND ANALYSIS ===
    - Trend: {t_analysis.get('trend', 'NEUTRAL')}
    - Confidence: {t_analysis.get('confidence', 'LOW')}
    - Risk Level: {t_analysis.get('risk_level', 'HIGH')}
    - Dual Timeframe: {t_analysis.get('dual_timeframe', False)}
    - Timeframe Alignment: {t_analysis.get('timeframe_alignment', 'N/A')}
    - Reasoning: {t_analysis.get('reasoning', 'No analysis available')}
    
    CRITICAL DUAL TIMEFRAME INSTRUCTION: 
    Based on ALL the above information for {symbol}, provide your recommendation.
    
    Consider:
    1. DUAL TIMEFRAME ANALYSIS: Weight 1-hour trends MORE heavily than 5-minute for direction
    2. Technical strength from multiple indicators across BOTH timeframes
    3. News sentiment impact (if available)
    4. Current position and portfolio constraints
    5. CRYPTO-ADJUSTED RISK MANAGEMENT:
       - Daily moves 5-15% are NORMAL for crypto (not high volatility)
       - Only moves >20% daily are considered EXTREME volatility
       - Volume of 0 is concerning but common in crypto sandbox/testing
       - RSI >80 or <20 are stronger signals in crypto than stocks
       - MACD crossovers are more reliable in crypto's trending markets
    6. Historical trading pattern for this symbol
    7. TIMEFRAME ALIGNMENT: Medium confidence acceptable if 1H data supports direction
    8. Use 5-minute data for precise entry/exit timing, 1-hour for trend confirmation
    
    DECISION INTEGRATION MATRIX:
    1. Strong Technical + Positive News = HIGH confidence BUY
    2. Strong Technical + Negative News = Reduce to MEDIUM priority or HOLD
    3. Weak Technical + Positive News = MEDIUM priority BUY consideration  
    4. Weak Technical + Negative News = AVOID BUY or consider SELL
    5. Strong Technical + No News = Proceed based on technical analysis
    6. Negative News + Any Technical = Seriously consider SELL or avoid BUY
    
    CRITICAL FEE-AWARE SELL RULES (MANDATORY):
    1. NEVER sell a position at a loss unless it's a stop-loss trigger (2%+ loss from purchase price)
    2. Only sell profitable positions (net P&L > $0 after accounting for ${TRADING_FEE_PER_TRADE * 2:.2f} round-trip fees)
    3. Prefer HOLD over unprofitable SELL - wait for price recovery or stop-loss trigger
    4. If current position shows "❌ UNPROFITABLE to sell" above, you MUST recommend HOLD unless it's an emergency stop-loss
    5. Management fee consideration: Minimum profit threshold = ${TRADING_FEE_PER_TRADE * 2:.2f} + small buffer
    
    Provide recommendation in EXACT format:
    STOCK: {symbol} | ACTION: [BUY/SELL/HOLD] | PRIORITY: [HIGH/MEDIUM/LOW] | REASONING: [Detailed technical reasons + specific news sentiment impact] | TECHNICAL_SCORE: [1-10] | CONFIDENCE: [HIGH/MEDIUM/LOW]
    """
    
    try:
        response = await gemini_model.generate_content_async(prompt)
        
        # Parse the response
        recommendation = parse_single_symbol_response(response.text, symbol)
        print(f"✅ {symbol}: {recommendation['action']} ({recommendation['priority']}) - Score: {recommendation['technical_score']}")
        
        # Log the full AI analysis details
        save_ai_prompt_log(symbol, prompt, response.text, recommendation, state)
        
        return recommendation
        
    except Exception as e:
        print(f"❌ Error analyzing {symbol}: {e}")
        return {
            'symbol': symbol,
            'action': 'HOLD',
            'priority': 'LOW',
            'reasoning': f'Analysis error: {str(e)}',
            'technical_score': 5.0,
            'confidence': 'LOW'
        }

def parse_single_symbol_response(ai_response: str, symbol: str) -> Dict:
    """Parse AI response for a single symbol"""
    
    # Default recommendation
    recommendation = {
        'symbol': symbol,
        'action': 'HOLD',
        'priority': 'LOW',
        'reasoning': 'Could not parse AI response',
        'technical_score': 5.0,
        'confidence': 'LOW'
    }
    
    try:
        # Clean the response
        response_text = ai_response.strip()
        
        # Look for the formatted response
        import re
        
        # Try to find the STOCK: line
        stock_pattern = rf"STOCK:\s*{symbol}\s*\|(.*)"
        match = re.search(stock_pattern, response_text, re.IGNORECASE)
        
        if match:
            parts_text = match.group(1)
            parts = [part.strip() for part in parts_text.split('|')]
            
            for part in parts:
                if ':' in part:
                    key, value = part.split(':', 1)
                    key = key.strip().lower()
                    value = value.strip()
                    
                    if key == 'action':
                        recommendation['action'] = value.upper()
                    elif key == 'priority':
                        recommendation['priority'] = value.upper()
                    elif key == 'reasoning':
                        recommendation['reasoning'] = value
                    elif key == 'technical_score':
                        try:
                            recommendation['technical_score'] = float(value)
                        except:
                            recommendation['technical_score'] = 5.0
                    elif key == 'confidence':
                        recommendation['confidence'] = value.upper()
        
        # Validate action
        if recommendation['action'] not in ['BUY', 'SELL', 'HOLD']:
            recommendation['action'] = 'HOLD'
            
        # Validate priority
        if recommendation['priority'] not in ['HIGH', 'MEDIUM', 'LOW']:
            recommendation['priority'] = 'LOW'
            
        # Validate confidence
        if recommendation['confidence'] not in ['HIGH', 'MEDIUM', 'LOW']:
            recommendation['confidence'] = 'LOW'
            
    except Exception as e:
        print(f"⚠️ Error parsing response for {symbol}: {e}")
        # Keep default recommendation
    
    return recommendation

async def get_parallel_ai_portfolio_recommendations(state: Dict) -> Dict:
    """
    Get AI recommendations for all symbols in parallel - ONE symbol per Gemini call
    """
    print("\n🚀 GENERATING PARALLEL AI RECOMMENDATIONS (One Symbol Per Call)")
    print("=" * 70)
    
    # Create tasks for all symbols
    tasks = []
    for symbol in PORTFOLIO_STOCKS:
        task = analyze_single_symbol(state, symbol)
        tasks.append(task)
    
    print(f"🔄 Running {len(tasks)} parallel analysis tasks...")
    
    # Execute all tasks in parallel
    start_time = asyncio.get_event_loop().time()
    results = await asyncio.gather(*tasks, return_exceptions=True)
    end_time = asyncio.get_event_loop().time()
    
    print(f"⚡ Parallel analysis completed in {end_time - start_time:.2f} seconds")
    
    # Process results
    recommendations = {}
    for result in results:
        if isinstance(result, Exception):
            print(f"❌ Task failed: {result}")
            continue
            
        if isinstance(result, dict) and 'symbol' in result:
            symbol = result.pop('symbol')  # Remove symbol from dict
            recommendations[symbol] = result
    
    # Ensure all symbols have recommendations
    for symbol in PORTFOLIO_STOCKS:
        if symbol not in recommendations:
            print(f"⚠️ Missing recommendation for {symbol}, defaulting to HOLD")
            recommendations[symbol] = {
                'action': 'HOLD',
                'priority': 'LOW',
                'reasoning': 'No recommendation generated',
                'technical_score': 5.0,
                'confidence': 'LOW'
            }
    
    print(f"✅ Generated {len(recommendations)}/{len(PORTFOLIO_STOCKS)} parallel recommendations")
    return recommendations

# Integration function - REPLACE your existing AI recommendations call
async def get_ai_portfolio_recommendations_with_news_parallel(state: Dict):
    """
    Drop-in replacement for your existing AI recommendations with parallel processing
    """
    try:
        return await get_parallel_ai_portfolio_recommendations(state)
    except Exception as e:
        print(f"❌ Parallel AI recommendations failed: {e}")
        
        # Fallback to simple recommendations
        fallback_recommendations = {}
        for symbol in PORTFOLIO_STOCKS:
            fallback_recommendations[symbol] = {
                'action': 'HOLD',
                'priority': 'LOW',
                'reasoning': f'Fallback due to error: {str(e)}',
                'technical_score': 5.0,
                'confidence': 'LOW'
            }
        return fallback_recommendations