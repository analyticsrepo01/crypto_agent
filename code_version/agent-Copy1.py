# /trading_bot/agent.py

from typing import Dict, List
from config import gemini_model, STOP_LOSS_PERCENTAGE, TAKE_PROFIT_PERCENTAGE, PORTFOLIO_STOP_LOSS, TRADE_SIZE, MIN_CASH_RESERVE, MAX_TOTAL_SHARES, MAX_SHARES_PER_STOCK, PORTFOLIO_STOCKS

# Define a type alias for state for clarity
PortfolioState = Dict 


def analyze_technical_strength(stock_data: Dict) -> Dict:
    """
    Analyzes the technical strength of a stock based on all available indicators.
    Returns a comprehensive technical score and breakdown.
    """
    if not stock_data.get('valid', False):
        return {'score': 0, 'signals': [], 'strength': 'WEAK', 'confidence': 'LOW'}
    
    signals = []
    bullish_signals = 0
    bearish_signals = 0
    
    # Price vs Moving Averages Analysis
    current_price = stock_data.get('current_price', 0)
    sma_20 = stock_data.get('sma_20', 0)
    sma_50 = stock_data.get('sma_50', 0)
    ema_12 = stock_data.get('ema_12', 0)
    ema_26 = stock_data.get('ema_26', 0)
    
    if current_price > sma_20 > sma_50:
        signals.append("BULLISH: Price above SMA20 > SMA50")
        bullish_signals += 2
    elif current_price < sma_20 < sma_50:
        signals.append("BEARISH: Price below SMA20 < SMA50")
        bearish_signals += 2
    
    if current_price > ema_12 > ema_26:
        signals.append("BULLISH: Price above EMA12 > EMA26")
        bullish_signals += 1
    elif current_price < ema_12 < ema_26:
        signals.append("BEARISH: Price below EMA12 < EMA26")
        bearish_signals += 1
    
    # RSI Analysis
    rsi = stock_data.get('rsi', 50)
    if rsi < 30:
        signals.append(f"BULLISH: RSI oversold ({rsi:.1f})")
        bullish_signals += 2
    elif rsi > 70:
        signals.append(f"BEARISH: RSI overbought ({rsi:.1f})")
        bearish_signals += 2
    elif 40 <= rsi <= 60:
        signals.append(f"NEUTRAL: RSI balanced ({rsi:.1f})")
    
    # MACD Analysis
    macd = stock_data.get('macd', 0)
    macd_signal = stock_data.get('macd_signal', 0)
    macd_hist = stock_data.get('macd_histogram', 0)
    
    if macd > macd_signal and macd_hist > 0:
        signals.append("BULLISH: MACD above signal line with positive histogram")
        bullish_signals += 2
    elif macd < macd_signal and macd_hist < 0:
        signals.append("BEARISH: MACD below signal line with negative histogram")
        bearish_signals += 2
    
    # Bollinger Bands Analysis
    bb_upper = stock_data.get('bb_upper', 0)
    bb_lower = stock_data.get('bb_lower', 0)
    bb_middle = stock_data.get('bb_middle', 0)
    
    if current_price > bb_upper:
        signals.append("BEARISH: Price above upper Bollinger Band (overbought)")
        bearish_signals += 1
    elif current_price < bb_lower:
        signals.append("BULLISH: Price below lower Bollinger Band (oversold)")
        bullish_signals += 1
    elif current_price > bb_middle:
        signals.append("BULLISH: Price above BB middle line")
        bullish_signals += 0.5
    
    # Stochastic Oscillator Analysis
    stoch_k = stock_data.get('stoch_k', 50)
    stoch_d = stock_data.get('stoch_d', 50)
    
    if stoch_k < 20 and stoch_d < 20:
        signals.append(f"BULLISH: Stochastic oversold (K:{stoch_k:.1f}, D:{stoch_d:.1f})")
        bullish_signals += 1
    elif stoch_k > 80 and stoch_d > 80:
        signals.append(f"BEARISH: Stochastic overbought (K:{stoch_k:.1f}, D:{stoch_d:.1f})")
        bearish_signals += 1
    
    # Williams %R Analysis
    williams_r = stock_data.get('williams_r', -50)
    if williams_r < -80:
        signals.append(f"BULLISH: Williams %R oversold ({williams_r:.1f})")
        bullish_signals += 1
    elif williams_r > -20:
        signals.append(f"BEARISH: Williams %R overbought ({williams_r:.1f})")
        bearish_signals += 1
    
    # Volume Analysis
    current_volume = stock_data.get('current_volume', 0)
    volume_ma = stock_data.get('volume_ma', 0)
    daily_change = stock_data.get('daily_change_pct', 0)
    
    if current_volume > volume_ma * 1.5 and daily_change > 0:
        signals.append("BULLISH: High volume with positive price movement")
        bullish_signals += 1
    elif current_volume > volume_ma * 1.5 and daily_change < 0:
        signals.append("BEARISH: High volume with negative price movement")
        bearish_signals += 1
    
    # Volatility Analysis
    atr = stock_data.get('atr', 0)
    volatility_20 = stock_data.get('volatility_20', 0)
    
    if volatility_20 > atr * 1.5:
        signals.append("CAUTION: High recent volatility detected")
        bearish_signals += 0.5
    
    # Calculate overall score and strength
    net_score = bullish_signals - bearish_signals
    max_possible = 10  # Approximate maximum possible signals
    
    if net_score >= 3:
        strength = 'STRONG_BULLISH'
        confidence = 'HIGH' if net_score >= 5 else 'MEDIUM'
    elif net_score >= 1:
        strength = 'WEAK_BULLISH'
        confidence = 'MEDIUM' if net_score >= 2 else 'LOW'
    elif net_score <= -3:
        strength = 'STRONG_BEARISH'
        confidence = 'HIGH' if net_score <= -5 else 'MEDIUM'
    elif net_score <= -1:
        strength = 'WEAK_BEARISH'
        confidence = 'MEDIUM' if net_score <= -2 else 'LOW'
    else:
        strength = 'NEUTRAL'
        confidence = 'LOW'
    
    score = max(0, min(10, 5 + net_score))  # Normalize to 0-10 scale
    
    return {
        'score': score,
        'signals': signals,
        'strength': strength,
        'confidence': confidence,
        'bullish_signals': bullish_signals,
        'bearish_signals': bearish_signals,
        'net_score': net_score
    }

def validate_ai_decisions(state: PortfolioState) -> Dict:
    """
    Enhanced validation that considers ALL technical indicators and their alignment.
    """
    recommendations = state.get('ai_recommendations', {})
    ai_trends = state.get('ai_trend_analysis', {})
    stock_data = state.get('stock_data', {})
    aggressive_mode = state.get('aggressive_mode', False)
    issues = []
    warnings = []
    
    if not recommendations:
        return {'decision': 'proceed', 'reason': 'No recommendations to validate.'}

    print("\n🔍 COMPREHENSIVE TECHNICAL VALIDATION")
    print("=" * 60)

    for symbol, rec in recommendations.items():
        action = rec.get('action', 'HOLD')
        priority = rec.get('priority', 'LOW')
        
        if action == 'HOLD':
            continue
            
        print(f"\n📊 VALIDATING {symbol} - {action} ({priority} priority)")
        
        # Get comprehensive technical analysis
        technical_analysis = analyze_technical_strength(stock_data.get(symbol, {}))
        trend_info = ai_trends.get(symbol, {})
        
        ai_trend = trend_info.get('trend', 'NEUTRAL')
        ai_confidence = trend_info.get('confidence', 'LOW')
        ai_risk = trend_info.get('risk_level', 'HIGH')
        
        technical_strength = technical_analysis.get('strength', 'NEUTRAL')
        technical_confidence = technical_analysis.get('confidence', 'LOW')
        technical_score = technical_analysis.get('score', 5)
        
        print(f"   🤖 AI Analysis: {ai_trend} ({ai_confidence} confidence, {ai_risk} risk)")
        print(f"   📈 Technical: {technical_strength} (Score: {technical_score}/10, {technical_confidence} confidence)")
        print(f"   📋 Signals: {len(technical_analysis.get('signals', []))} total")
        
        # Major contradiction checks
        if action == 'BUY':
            # Check for major bearish contradictions
            if (ai_trend == 'BEARISH' and ai_confidence in ['MEDIUM', 'HIGH']) or \
               (technical_strength in ['STRONG_BEARISH', 'WEAK_BEARISH'] and technical_confidence in ['MEDIUM', 'HIGH']):
                issues.append(f"{symbol}: Major contradiction - BUY recommendation conflicts with bearish analysis")
                print(f"   ❌ MAJOR ISSUE: BUY conflicts with bearish signals")
            
            # Check technical score alignment
            if technical_score < 3 and priority == 'HIGH':
                if aggressive_mode:
                    warnings.append(f"{symbol}: High-priority BUY with low technical score ({technical_score}/10) - risky in aggressive mode")
                    print(f"   ⚠️  WARNING: Low technical score for high-priority BUY")
                else:
                    issues.append(f"{symbol}: High-priority BUY with poor technical indicators (score: {technical_score}/10)")
                    print(f"   ❌ ISSUE: Poor technical score for high-priority BUY")
            
            # RSI overbought check
            rsi = stock_data.get(symbol, {}).get('rsi', 50)
            if rsi > 75 and priority in ['HIGH', 'MEDIUM']:
                warnings.append(f"{symbol}: BUY recommendation with very overbought RSI ({rsi:.1f})")
                print(f"   ⚠️  WARNING: Very overbought RSI ({rsi:.1f})")
        
        elif action == 'SELL':
            # Check for major bullish contradictions
            if (ai_trend == 'BULLISH' and ai_confidence in ['MEDIUM', 'HIGH']) or \
               (technical_strength in ['STRONG_BULLISH', 'WEAK_BULLISH'] and technical_confidence in ['MEDIUM', 'HIGH']):
                issues.append(f"{symbol}: Major contradiction - SELL recommendation conflicts with bullish analysis")
                print(f"   ❌ MAJOR ISSUE: SELL conflicts with bullish signals")
            
            # Check technical score alignment
            if technical_score > 7 and priority == 'HIGH':
                if not aggressive_mode:  # In aggressive mode, might sell for quick profits
                    issues.append(f"{symbol}: High-priority SELL with strong technical indicators (score: {technical_score}/10)")
                    print(f"   ❌ ISSUE: High technical score conflicts with high-priority SELL")
            
            # RSI oversold check
            rsi = stock_data.get(symbol, {}).get('rsi', 50)
            if rsi < 25 and priority in ['HIGH', 'MEDIUM']:
                warnings.append(f"{symbol}: SELL recommendation with very oversold RSI ({rsi:.1f})")
                print(f"   ⚠️  WARNING: Very oversold RSI ({rsi:.1f})")
        
        # Risk assessment checks
        if not aggressive_mode and action in ['BUY', 'SELL'] and priority == 'HIGH':
            volatility = stock_data.get(symbol, {}).get('volatility_20', 0)
            atr = stock_data.get(symbol, {}).get('atr', 0)
            
            if volatility > atr * 2:  # High volatility
                warnings.append(f"{symbol}: High-priority {action} on highly volatile stock")
                print(f"   ⚠️  WARNING: High volatility detected")
            
            if ai_risk == 'HIGH' and technical_confidence == 'LOW':
                issues.append(f"{symbol}: High-priority {action} with high AI risk and low technical confidence")
                print(f"   ❌ ISSUE: High risk + low confidence combination")

    # Portfolio-level validation
    buy_sell_actions = [rec.get('action') for rec in recommendations.values() if rec.get('action') in ['BUY', 'SELL']]
    churn_limit = 0.9 if aggressive_mode else 0.7 
    
    if len(buy_sell_actions) > (len(PORTFOLIO_STOCKS) * churn_limit):
        issues.append(f"Portfolio: Excessive trading activity - {len(buy_sell_actions)} actions suggested (limit: {int(len(PORTFOLIO_STOCKS) * churn_limit)})")
        print(f"\n   ❌ PORTFOLIO ISSUE: Excessive trading activity")

    # Market condition check
    bullish_count = sum(1 for rec in recommendations.values() if rec.get('action') == 'BUY')
    bearish_count = sum(1 for rec in recommendations.values() if rec.get('action') == 'SELL')
    
    if bullish_count > 0 and bearish_count > 0:
        ratio = bullish_count / (bullish_count + bearish_count)
        if 0.3 <= ratio <= 0.7:  # Mixed signals
            warnings.append(f"Portfolio: Mixed market signals - {bullish_count} BUY vs {bearish_count} SELL recommendations")
            print(f"\n   ⚠️  PORTFOLIO WARNING: Mixed signals detected")

    print(f"\n📋 VALIDATION SUMMARY:")
    print(f"   ✅ Clean validations: {len([s for s in PORTFOLIO_STOCKS if s in recommendations and recommendations[s].get('action') == 'HOLD']) + len(PORTFOLIO_STOCKS) - len(recommendations)}")
    print(f"   ⚠️  Warnings: {len(warnings)}")
    print(f"   ❌ Issues: {len(issues)}")

    if issues:
        all_problems = issues + ([f"WARNINGS: {'; '.join(warnings)}"] if warnings else [])
        return {
            'decision': 'rerun', 
            'reason': f"Validation failed. Critical issues: {'; '.join(issues)}. {f'Warnings: {len(warnings)}' if warnings else ''}"
        }
    
    reason = 'AI decisions are technically sound and consistent.'
    if warnings:
        reason += f" Note: {len(warnings)} minor warnings detected."
    
    return {'decision': 'proceed', 'reason': reason}

async def get_ai_trend_analysis(stock_data: Dict, symbol: str) -> Dict:
    """
    Enhanced AI trend analysis using ALL available technical indicators.
    """
    indicators = stock_data.get(symbol, {})
    if not indicators.get('valid', False):
        return {'trend': 'NEUTRAL', 'confidence': 'LOW', 'reasoning': 'Insufficient data', 'risk_level': 'HIGH'}

    # Get comprehensive technical analysis
    technical_analysis = analyze_technical_strength(indicators)
    
    # Create enhanced prompt with ALL indicators
    context = f"""
    Perform comprehensive technical analysis for {symbol} using ALL available indicators:

    PRICE DATA:
    - Current Price: ${indicators.get('current_price', 0):.2f}
    - Previous Close: ${indicators.get('previous_close', 0):.2f}
    - Daily Change: {indicators.get('daily_change_pct', 0):.2f}%

    MOVING AVERAGES:
    - SMA 20: ${indicators.get('sma_20', 0):.2f}
    - SMA 50: ${indicators.get('sma_50', 0):.2f}
    - EMA 12: ${indicators.get('ema_12', 0):.2f}
    - EMA 26: ${indicators.get('ema_26', 0):.2f}

    MOMENTUM INDICATORS:
    - RSI (14): {indicators.get('rsi', 50):.1f}
    - Williams %R: {indicators.get('williams_r', -50):.1f}
    - Stochastic K: {indicators.get('stoch_k', 50):.1f}
    - Stochastic D: {indicators.get('stoch_d', 50):.1f}

    MACD ANALYSIS:
    - MACD Line: {indicators.get('macd', 0):.3f}
    - Signal Line: {indicators.get('macd_signal', 0):.3f}
    - Histogram: {indicators.get('macd_histogram', 0):.3f}

    BOLLINGER BANDS:
    - Upper: ${indicators.get('bb_upper', 0):.2f}
    - Middle: ${indicators.get('bb_middle', 0):.2f}
    - Lower: ${indicators.get('bb_lower', 0):.2f}
    - Position: {"Above Upper" if indicators.get('current_price', 0) > indicators.get('bb_upper', 0) else "Below Lower" if indicators.get('current_price', 0) < indicators.get('bb_lower', 0) else "Within Bands"}

    VOLUME & VOLATILITY:
    - Current Volume: {indicators.get('current_volume', 0):,.0f}
    - Volume MA: {indicators.get('volume_ma', 0):,.0f}
    - Volume Ratio: {(indicators.get('current_volume', 0) / max(indicators.get('volume_ma', 1), 1)):.2f}x
    - ATR: {indicators.get('atr', 0):.3f}
    - 20-day Volatility: {indicators.get('volatility_20', 0):.3f}
    - OBV: {indicators.get('obv', 0):,.0f}

    TECHNICAL SCORE BREAKDOWN:
    - Overall Score: {technical_analysis.get('score', 5)}/10
    - Strength: {technical_analysis.get('strength', 'NEUTRAL')}
    - Bullish Signals: {technical_analysis.get('bullish_signals', 0)}
    - Bearish Signals: {technical_analysis.get('bearish_signals', 0)}

    KEY SIGNALS DETECTED:
    {chr(10).join(['- ' + signal for signal in technical_analysis.get('signals', [])[:8]])}

    Based on this comprehensive analysis, provide your assessment in EXACT format:
    TREND: [BULLISH/BEARISH/NEUTRAL]
    CONFIDENCE: [HIGH/MEDIUM/LOW]
    REASONING: [Brief 1-2 sentence summary considering multiple indicators]
    RISK_LEVEL: [LOW/MEDIUM/HIGH]
    """
    
    try:
        response = await gemini_model.generate_content_async(context)
        ai_response = response.text
        
        analysis = {}
        for line in ai_response.split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                analysis[key.strip().lower()] = value.strip()
        
        # Add technical analysis data
        analysis['technical_score'] = technical_analysis.get('score', 5)
        analysis['technical_strength'] = technical_analysis.get('strength', 'NEUTRAL')
        analysis['signal_count'] = len(technical_analysis.get('signals', []))
        
        return analysis
    except Exception as e:
        print(f"❌ Enhanced AI trend analysis error for {symbol}: {e}")
        return {
            'trend': 'NEUTRAL', 
            'confidence': 'LOW', 
            'reasoning': f'AI error: {e}', 
            'risk_level': 'HIGH',
            'technical_score': technical_analysis.get('score', 5),
            'technical_strength': technical_analysis.get('strength', 'NEUTRAL')
        }

async def get_ai_portfolio_recommendations(state: PortfolioState):
    """
    Enhanced AI recommendations using comprehensive technical analysis for ALL indicators.
    """
    print("\n🧠 GENERATING AI RECOMMENDATIONS WITH FULL TECHNICAL ANALYSIS")
    print("=" * 70)
    
    portfolio_summary = []
    for symbol in PORTFOLIO_STOCKS:
        s_data = state['stock_data'].get(symbol, {})
        t_analysis = state['ai_trend_analysis'].get(symbol, {})
        pos = state['positions'].get(symbol, 0)
        
        if s_data.get('valid', False):
            # Get comprehensive technical analysis
            tech_analysis = analyze_technical_strength(s_data)
            
            portfolio_summary.append(
                f"""{symbol} (Position: {pos} shares):
   Price: ${s_data.get('current_price', 0):.2f} (Change: {s_data.get('daily_change_pct', 0):+.2f}%)
   Technical Score: {tech_analysis.get('score', 5)}/10 ({tech_analysis.get('strength', 'NEUTRAL')})
   RSI: {s_data.get('rsi', 50):.1f} | MACD Hist: {s_data.get('macd_histogram', 0):.3f}
   Volume: {(s_data.get('current_volume', 0) / max(s_data.get('volume_ma', 1), 1)):.1f}x avg
   Bollinger: {"Upper" if s_data.get('current_price', 0) > s_data.get('bb_upper', 0) else "Lower" if s_data.get('current_price', 0) < s_data.get('bb_lower', 0) else "Middle"} band
   AI Trend: {t_analysis.get('trend', 'N/A')} ({t_analysis.get('confidence', 'N/A')} conf, {t_analysis.get('risk_level', 'N/A')} risk)
   Key Signals: {tech_analysis.get('bullish_signals', 0)} bullish, {tech_analysis.get('bearish_signals', 0)} bearish"""
            )
            
            print(f"📊 {symbol}: Tech Score {tech_analysis.get('score', 5)}/10, RSI {s_data.get('rsi', 50):.1f}, Trend {t_analysis.get('trend', 'N/A')}")
    
    # Enhanced strategy instruction based on mode
    strategy_instruction = ""
    if state.get('aggressive_mode', False):
        strategy_instruction = """
        AGGRESSIVE TRADING MODE ACTIVE:
        - MAXIMIZE PROFIT through decisive action
        - Accept higher risk for higher potential returns  
        - Consider technical scores 4+ as actionable for BUY
        - Consider technical scores 6- as actionable for SELL
        - Prioritize momentum and volume indicators
        - Be quick to enter/exit based on technical signals"""
    else:
        strategy_instruction = """
        BALANCED TRADING MODE ACTIVE:
        - Prioritize capital preservation with steady growth
        - Require technical scores 6+ for high-priority BUY
        - Require technical scores 4- for high-priority SELL  
        - Demand multiple confirming indicators
        - Avoid trades during high volatility periods
        - Focus on strong technical alignment"""

    context = f"""
    You are an expert quantitative trading analyst with deep technical analysis expertise.
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

    COMPREHENSIVE STOCK ANALYSIS:
    {chr(10).join(portfolio_summary)}

    CRITICAL INSTRUCTION: Consider ALL technical indicators in your analysis:
    - Price vs Moving Averages (SMA20, SMA50, EMA12, EMA26)
    - Momentum indicators (RSI, Williams %R, Stochastic)
    - MACD system (line, signal, histogram)
    - Bollinger Band position and squeeze
    - Volume analysis vs moving average
    - Volatility measurements (ATR, 20-day vol)
    
    For each stock, provide recommendation in EXACT format:
    STOCK: [SYMBOL] | ACTION: [BUY/SELL/HOLD] | PRIORITY: [HIGH/MEDIUM/LOW] | REASONING: [Specific technical reasons citing 2-3 indicators] | TECHNICAL_SCORE: [1-10] | CONFIDENCE: [HIGH/MEDIUM/LOW]
    """
    
    feedback = state.get("validation_feedback")
    if feedback:
        context += f"""
        
        CRITICAL REVISION REQUEST: 
        Your previous recommendations were rejected for these reasons: "{feedback}"
        
        MANDATORY FIXES:
        - Address all identified contradictions
        - Ensure technical indicators align with recommended actions
        - Provide stronger reasoning based on multiple confirming signals
        - Adjust priorities based on technical strength scores
        """
    
    try:
        print("🤖 Sending comprehensive analysis to AI...")
        response = await gemini_model.generate_content_async(context)
        ai_response = response.text
        
        print("\n--- FULL AI RESPONSE ---")
        print(ai_response)
        print("------------------------\n")

        recommendations = {}
        
        # Enhanced parsing to capture all fields
        for line in ai_response.split('\n'):
            line = line.strip()
            if not line or '|' not in line:
                continue

            try:
                rec = {}
                symbol = None
                
                # Parse the structured response
                if line.startswith("STOCK:") or any(stock in line.split('|')[0] for stock in PORTFOLIO_STOCKS):
                    parts = [p.strip() for p in line.split('|')]
                    
                    for part in parts:
                        if ':' in part:
                            key, value = part.split(':', 1)
                            clean_key = key.strip().lower().replace(' ', '_')
                            clean_value = value.strip()
                            
                            if clean_key == 'stock':
                                symbol = clean_value
                            elif clean_key in ['action', 'priority', 'reasoning', 'confidence']:
                                rec[clean_key] = clean_value
                            elif clean_key == 'technical_score':
                                try:
                                    rec[clean_key] = float(clean_value)
                                except:
                                    rec[clean_key] = 5.0
                    
                    # Try alternative parsing if symbol not found
                    if not symbol:
                        first_part = parts[0].replace('STOCK:', '').strip()
                        if first_part in PORTFOLIO_STOCKS:
                            symbol = first_part
                    
                    if symbol and symbol in PORTFOLIO_STOCKS:
                        # Set defaults for missing fields
                        rec.setdefault('action', 'HOLD')
                        rec.setdefault('priority', 'LOW')
                        rec.setdefault('reasoning', 'AI recommendation')
                        rec.setdefault('technical_score', 5.0)
                        rec.setdefault('confidence', 'MEDIUM')
                        
                        recommendations[symbol] = rec
                        print(f"✅ Parsed {symbol}: {rec['action']} ({rec['priority']}) - Score: {rec['technical_score']}")
                        
            except Exception as e:
                print(f"⚠️  Error parsing line: {line[:50]}... - {e}")
                continue

        # Ensure all portfolio stocks have recommendations
        for symbol in PORTFOLIO_STOCKS:
            if symbol not in recommendations:
                print(f"⚠️  Missing recommendation for {symbol}, defaulting to HOLD")
                recommendations[symbol] = {
                    'action': 'HOLD',
                    'priority': 'LOW', 
                    'reasoning': 'No clear signal from analysis',
                    'technical_score': 5.0,
                    'confidence': 'LOW'
                }

        print(f"\n✅ Generated recommendations for {len(recommendations)}/{len(PORTFOLIO_STOCKS)} stocks")
        return recommendations

    except Exception as e:
        print(f"❌ AI portfolio recommendation error: {e}")
        return {s: {
            'action': 'HOLD', 
            'priority': 'LOW', 
            'reasoning': f'AI Error: {e}',
            'technical_score': 5.0,
            'confidence': 'LOW'
        } for s in PORTFOLIO_STOCKS}





# 2. ENHANCED AI RECOMMENDATION FUNCTION WITH MEMORY (COMPLETE VERSION)
async def get_ai_portfolio_recommendations_with_memory(state: PortfolioState):
    """
    Enhanced AI recommendations using comprehensive technical analysis for ALL indicators WITH MEMORY CONTEXT.
    """
    print("\n🧠 GENERATING AI RECOMMENDATIONS WITH FULL TECHNICAL ANALYSIS + MEMORY")
    print("=" * 75)
    
    portfolio_summary = []
    for symbol in PORTFOLIO_STOCKS:
        s_data = state['stock_data'].get(symbol, {})
        t_analysis = state['ai_trend_analysis'].get(symbol, {})
        pos = state['positions'].get(symbol, 0)
        
        if s_data.get('valid', False):
            # Get comprehensive technical analysis (your existing logic)
            tech_analysis = analyze_technical_strength(s_data)
            
            portfolio_summary.append(
                f"""{symbol} (Position: {pos} shares):
   Price: ${s_data.get('current_price', 0):.2f} (Change: {s_data.get('daily_change_pct', 0):+.2f}%)
   Technical Score: {tech_analysis.get('score', 5)}/10 ({tech_analysis.get('strength', 'NEUTRAL')})
   RSI: {s_data.get('rsi', 50):.1f} | MACD Hist: {s_data.get('macd_histogram', 0):.3f}
   Volume: {(s_data.get('current_volume', 0) / max(s_data.get('volume_ma', 1), 1)):.1f}x avg
   Bollinger: {"Upper" if s_data.get('current_price', 0) > s_data.get('bb_upper', 0) else "Lower" if s_data.get('current_price', 0) < s_data.get('bb_lower', 0) else "Middle"} band
   AI Trend: {t_analysis.get('trend', 'N/A')} ({t_analysis.get('confidence', 'N/A')} conf, {t_analysis.get('risk_level', 'N/A')} risk)
   Key Signals: {tech_analysis.get('bullish_signals', 0)} bullish, {tech_analysis.get('bearish_signals', 0)} bearish"""
            )
            
            print(f"📊 {symbol}: Tech Score {tech_analysis.get('score', 5)}/10, RSI {s_data.get('rsi', 50):.1f}, Trend {t_analysis.get('trend', 'N/A')}")

    # Enhanced strategy instruction based on mode (your existing logic)
    strategy_instruction = ""
    if state.get('aggressive_mode', False):
        strategy_instruction = """
        AGGRESSIVE TRADING MODE ACTIVE:
        - MAXIMIZE PROFIT through decisive action
        - Accept higher risk for higher potential returns  
        - Consider technical scores 4+ as actionable for BUY
        - Consider technical scores 6- as actionable for SELL
        - Prioritize momentum and volume indicators
        - Be quick to enter/exit based on technical signals"""
    else:
        strategy_instruction = """
        BALANCED TRADING MODE ACTIVE:
        - Prioritize capital preservation with steady growth
        - Require technical scores 6+ for high-priority BUY
        - Require technical scores 4- for high-priority SELL  
        - Demand multiple confirming indicators
        - Avoid trades during high volatility periods
        - Focus on strong technical alignment"""

    # GET MEMORY CONTEXT (NEW ADDITION)
    memory_context = state.get('memory_context', 'No previous trading context available for this session.')
    
    # Get symbol-specific memory insights (NEW ADDITION)
    symbol_memory_insights = []
    try:
        from memory_store import trading_memory
        for symbol in PORTFOLIO_STOCKS[:5]:  # Limit to avoid too much context
            history = trading_memory.get_symbol_trading_history(symbol, days_back=3)
            if history:
                recent_trades = len(history)
                last_action = history[0]['memory']['action'] if history else 'NONE'
                avg_score = sum(h['memory']['technical_score'] for h in history) / len(history) if history else 0
                symbol_memory_insights.append(f"   {symbol}: {recent_trades} recent trades, last action: {last_action}, avg tech score: {avg_score:.1f}")
    except Exception as e:
        print(f"⚠️ Could not load symbol memory: {e}")

    # ENHANCED CONTEXT WITH MEMORY (PRESERVING ALL YOUR EXISTING ANALYSIS)
    context = f"""
    You are an expert quantitative trading analyst with deep technical analysis expertise and access to historical trading patterns.
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

    HISTORICAL TRADING CONTEXT & MEMORY:
    {memory_context}

    SYMBOL-SPECIFIC TRADING MEMORY:
    {chr(10).join(symbol_memory_insights) if symbol_memory_insights else "   No recent symbol-specific trading history available"}

    COMPREHENSIVE STOCK ANALYSIS:
    {chr(10).join(portfolio_summary)}

    CRITICAL INSTRUCTION: Consider ALL technical indicators AND historical trading patterns in your analysis:
    - Price vs Moving Averages (SMA20, SMA50, EMA12, EMA26)
    - Momentum indicators (RSI, Williams %R, Stochastic)
    - MACD system (line, signal, histogram)
    - Bollinger Band position and squeeze
    - Volume analysis vs moving average
    - Volatility measurements (ATR, 20-day vol)
    - Historical trading patterns and outcomes from memory
    - Recent trading decisions and their effectiveness
    - Daily trading bias and sentiment trends
    
    MEMORY-BASED DECISION ENHANCEMENT:
    - Learn from previous similar market conditions shown in memory context
    - Avoid repeating failed strategies from today's trading history
    - Consider the day's trading pattern and sentiment trends
    - Factor in previous decisions and their technical score effectiveness
    - Use historical context to validate current technical signals
    
    For each stock, provide recommendation in EXACT format:
    STOCK: [SYMBOL] | ACTION: [BUY/SELL/HOLD] | PRIORITY: [HIGH/MEDIUM/LOW] | REASONING: [Specific technical reasons citing 2-3 indicators AND relevant memory context] | TECHNICAL_SCORE: [1-10] | CONFIDENCE: [HIGH/MEDIUM/LOW]
    """
    
    feedback = state.get("validation_feedback")
    if feedback:
        context += f"""
        
        CRITICAL REVISION REQUEST: 
        Your previous recommendations were rejected for these reasons: "{feedback}"
        
        MANDATORY FIXES:
        - Address all identified contradictions
        - Ensure technical indicators align with recommended actions
        - Provide stronger reasoning based on multiple confirming signals
        - Adjust priorities based on technical strength scores
        - Use memory context to avoid repeating the same mistakes
        - Learn from historical patterns to improve decision quality
        """
    
    try:
        print("🤖 Sending comprehensive analysis with memory context to AI...")
        response = await gemini_model.generate_content_async(context)
        ai_response = response.text
        
        print("\n--- FULL AI RESPONSE WITH MEMORY CONTEXT ---")
        print(ai_response)
        print("---------------------------------------------\n")

        recommendations = {}
        
        # Enhanced parsing to capture all fields (your existing parsing logic)
        for line in ai_response.split('\n'):
            line = line.strip()
            if not line or '|' not in line:
                continue

            try:
                rec = {}
                symbol = None
                
                # Parse the structured response (your existing logic)
                if line.startswith("STOCK:") or any(stock in line.split('|')[0] for stock in PORTFOLIO_STOCKS):
                    parts = [p.strip() for p in line.split('|')]
                    
                    for part in parts:
                        if ':' in part:
                            key, value = part.split(':', 1)
                            clean_key = key.strip().lower().replace(' ', '_')
                            clean_value = value.strip()
                            
                            if clean_key == 'stock':
                                symbol = clean_value
                            elif clean_key in ['action', 'priority', 'reasoning', 'confidence']:
                                rec[clean_key] = clean_value
                            elif clean_key == 'technical_score':
                                try:
                                    rec[clean_key] = float(clean_value)
                                except:
                                    rec[clean_key] = 5.0
                    
                    # Try alternative parsing if symbol not found (your existing logic)
                    if not symbol:
                        first_part = parts[0].replace('STOCK:', '').strip()
                        if first_part in PORTFOLIO_STOCKS:
                            symbol = first_part
                    
                    if symbol and symbol in PORTFOLIO_STOCKS:
                        # Set defaults for missing fields (your existing logic)
                        rec.setdefault('action', 'HOLD')
                        rec.setdefault('priority', 'LOW')
                        rec.setdefault('reasoning', 'AI recommendation')
                        rec.setdefault('technical_score', 5.0)
                        rec.setdefault('confidence', 'MEDIUM')
                        
                        recommendations[symbol] = rec
                        print(f"✅ Parsed {symbol}: {rec['action']} ({rec['priority']}) - Score: {rec['technical_score']}")
                        
            except Exception as e:
                print(f"⚠️  Error parsing line: {line[:50]}... - {e}")
                continue

        # Ensure all portfolio stocks have recommendations (your existing logic)
        for symbol in PORTFOLIO_STOCKS:
            if symbol not in recommendations:
                print(f"⚠️  Missing recommendation for {symbol}, defaulting to HOLD")
                recommendations[symbol] = {
                    'action': 'HOLD',
                    'priority': 'LOW', 
                    'reasoning': 'No clear signal from analysis',
                    'technical_score': 5.0,
                    'confidence': 'LOW'
                }

        print(f"\n✅ Generated recommendations with memory context for {len(recommendations)}/{len(PORTFOLIO_STOCKS)} stocks")
        return recommendations

    except Exception as e:
        print(f"❌ AI portfolio recommendation with memory error: {e}")
        return {s: {
            'action': 'HOLD', 
            'priority': 'LOW', 
            'reasoning': f'AI Error: {e}',
            'technical_score': 5.0,
            'confidence': 'LOW'
        } for s in PORTFOLIO_STOCKS}



def should_rerun_or_proceed(state: PortfolioState) -> str:
    """
    Checks the last validation result to decide the next step in the graph.
    """
    if not state.get('validation_history'):
        return "proceed_to_execute"
        
    last_validation = state['validation_history'][-1]
    if last_validation['decision'] == 'rerun':
        return "rerun_decision"
    return "proceed_to_execute"

def check_stop_loss_conditions(state: PortfolioState) -> Dict:
    """
    Checks for individual stock stop-loss or take-profit triggers.
    """
    actions = {}
    for symbol in PORTFOLIO_STOCKS:
        position = state.get('positions', {}).get(symbol, 0)
        if position <= 0:
            continue
            
        current_price = state.get('stock_prices', {}).get(symbol, 0)
        purchase_price = state.get('purchase_prices', {}).get(symbol, 0)
        
        if purchase_price > 0 and current_price > 0:
            change_pct = ((current_price - purchase_price) / purchase_price) * 100
            if change_pct <= STOP_LOSS_PERCENTAGE:
                actions[symbol] = 'SELL'
                print(f"🚨 STOP-LOSS TRIGGER: {symbol} at {change_pct:.2f}%")
            elif change_pct >= TAKE_PROFIT_PERCENTAGE:
                actions[symbol] = 'SELL'
                print(f"💰 TAKE-PROFIT TRIGGER: {symbol} at {change_pct:.2f}%")
    return actions

def check_emergency_stop_loss(state: PortfolioState) -> bool:
    """
    Checks if the entire portfolio has hit the emergency stop-loss threshold.
    """
    pnl = state.get('total_unrealized_pnl', 0)
    value = state.get('total_portfolio_value', 1)
    if pnl < 0 and value > 0:
        loss_pct = (pnl / value) * 100
        if loss_pct <= PORTFOLIO_STOP_LOSS:
            print(f"🚨 EMERGENCY PORTFOLIO STOP: Total loss at {loss_pct:.2f}%")
            return True
    return False