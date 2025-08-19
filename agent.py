# /trading_bot/agent.py

from typing import Dict, List
from config import gemini_model, STOP_LOSS_PERCENTAGE, TAKE_PROFIT_PERCENTAGE, PORTFOLIO_STOP_LOSS, TRADE_SIZE, MIN_CASH_RESERVE, MAX_TOTAL_SHARES, MAX_SHARES_PER_STOCK, PORTFOLIO_STOCKS, TRADING_FEE_PER_TRADE
from market_data import calculate_portfolio_profitability

# Define a type alias for state for clarity
PortfolioState = Dict 


def analyze_technical_strength_dual_timeframe(stock_data_5m: Dict, stock_data_1h: Dict, profitability_data: Dict = None) -> Dict:
    """
    Analyzes the technical strength of a stock based on both 5-minute and 1-hour timeframes.
    Returns a comprehensive technical score considering multiple timeframes.
    """
    if not stock_data_5m.get('valid', False) or not stock_data_1h.get('valid', False):
        return {'score': 0, 'signals': [], 'strength': 'WEAK', 'confidence': 'LOW', 'timeframe_alignment': 'NO_DATA'}
    
    signals = []
    bullish_signals = 0
    bearish_signals = 0
    
    # 5-minute timeframe analysis (short-term)
    current_price_5m = stock_data_5m.get('current_price', 0)
    sma_20_5m = stock_data_5m.get('sma_20', 0)
    sma_50_5m = stock_data_5m.get('sma_50', 0)
    rsi_5m = stock_data_5m.get('rsi', 50)
    macd_5m = stock_data_5m.get('macd', 0)
    macd_signal_5m = stock_data_5m.get('macd_signal', 0)
    
    # 1-hour timeframe analysis (medium-term)
    current_price_1h = stock_data_1h.get('current_price', 0)
    sma_20_1h = stock_data_1h.get('sma_20', 0)
    sma_50_1h = stock_data_1h.get('sma_50', 0)
    rsi_1h = stock_data_1h.get('rsi', 50)
    macd_1h = stock_data_1h.get('macd', 0)
    macd_signal_1h = stock_data_1h.get('macd_signal', 0)
    
    # Moving Average Analysis - 5min timeframe
    if current_price_5m > sma_20_5m > sma_50_5m:
        signals.append("BULLISH 5M: Price above SMA20 > SMA50")
        bullish_signals += 1
    elif current_price_5m < sma_20_5m < sma_50_5m:
        signals.append("BEARISH 5M: Price below SMA20 < SMA50")
        bearish_signals += 1
    
    # Moving Average Analysis - 1hr timeframe
    if current_price_1h > sma_20_1h > sma_50_1h:
        signals.append("BULLISH 1H: Price above SMA20 > SMA50")
        bullish_signals += 2  # 1-hour signals weighted more heavily
    elif current_price_1h < sma_20_1h < sma_50_1h:
        signals.append("BEARISH 1H: Price below SMA20 < SMA50")
        bearish_signals += 2
    
    # RSI Analysis - Both timeframes
    if rsi_5m < 30:
        signals.append(f"BULLISH 5M: RSI oversold ({rsi_5m:.1f})")
        bullish_signals += 1
    elif rsi_5m > 70:
        signals.append(f"BEARISH 5M: RSI overbought ({rsi_5m:.1f})")
        bearish_signals += 1
    
    if rsi_1h < 30:
        signals.append(f"BULLISH 1H: RSI oversold ({rsi_1h:.1f})")
        bullish_signals += 2
    elif rsi_1h > 70:
        signals.append(f"BEARISH 1H: RSI overbought ({rsi_1h:.1f})")
        bearish_signals += 2
    
    # MACD Analysis - Both timeframes
    if macd_5m > macd_signal_5m:
        signals.append("BULLISH 5M: MACD above signal")
        bullish_signals += 1
    else:
        signals.append("BEARISH 5M: MACD below signal")
        bearish_signals += 1
    
    if macd_1h > macd_signal_1h:
        signals.append("BULLISH 1H: MACD above signal")
        bullish_signals += 2
    else:
        signals.append("BEARISH 1H: MACD below signal")
        bearish_signals += 2
    
    # Timeframe Alignment Analysis
    timeframe_alignment = "NEUTRAL"
    alignment_score = 0
    
    # Check if both timeframes agree on direction
    ma_trend_5m = 1 if current_price_5m > sma_20_5m else -1 if current_price_5m < sma_20_5m else 0
    ma_trend_1h = 1 if current_price_1h > sma_20_1h else -1 if current_price_1h < sma_20_1h else 0
    
    rsi_trend_5m = 1 if rsi_5m > 50 else -1 if rsi_5m < 50 else 0
    rsi_trend_1h = 1 if rsi_1h > 50 else -1 if rsi_1h < 50 else 0
    
    macd_trend_5m = 1 if macd_5m > macd_signal_5m else -1
    macd_trend_1h = 1 if macd_1h > macd_signal_1h else -1
    
    if (ma_trend_5m == ma_trend_1h == 1) and (rsi_trend_5m >= 0 and rsi_trend_1h >= 0):
        timeframe_alignment = "BULLISH_ALIGNED"
        alignment_score = 3
        bullish_signals += 3
    elif (ma_trend_5m == ma_trend_1h == -1) and (rsi_trend_5m <= 0 and rsi_trend_1h <= 0):
        timeframe_alignment = "BEARISH_ALIGNED"
        alignment_score = -3
        bearish_signals += 3
    elif ma_trend_5m != ma_trend_1h:
        timeframe_alignment = "CONFLICTED"
        signals.append("CAUTION: 5M and 1H timeframes showing conflicting signals")
        bearish_signals += 1  # Add uncertainty penalty
    
    # Add remaining indicators from the original function for 5-minute data
    # (keeping the existing comprehensive analysis for short-term)
    original_analysis = analyze_technical_strength(stock_data_5m, profitability_data)
    remaining_signals = [s for s in original_analysis.get('signals', []) if not any(x in s for x in ['SMA20', 'RSI', 'MACD above signal'])]
    signals.extend(remaining_signals)
    
    # Calculate enhanced score
    net_score = bullish_signals - bearish_signals + alignment_score
    max_possible = 20  # Adjusted for dual timeframe
    
    if net_score >= 4:
        strength = 'STRONG_BULLISH'
        confidence = 'HIGH' if net_score >= 6 else 'MEDIUM'
    elif net_score >= 2:
        strength = 'WEAK_BULLISH'
        confidence = 'MEDIUM' if net_score >= 3 else 'LOW'
    elif net_score <= -4:
        strength = 'STRONG_BEARISH'
        confidence = 'HIGH' if net_score <= -6 else 'MEDIUM'
    elif net_score <= -2:
        strength = 'WEAK_BEARISH'
        confidence = 'MEDIUM' if net_score <= -3 else 'LOW'
    else:
        strength = 'NEUTRAL'
        confidence = 'LOW'
    
    score = max(0, min(10, 5 + net_score))
    
    # Add profitability information if available
    profitability_info = {}
    if profitability_data:
        symbol = None
        for s in ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA', 'NFLX', 'CRM', 'ADBE']:
            if s in str(stock_data_5m):
                symbol = s
                break
        
        if symbol and symbol in profitability_data.get('individual_stocks', {}):
            stock_profit = profitability_data['individual_stocks'][symbol]
            profitability_info = {
                'current_position': stock_profit['position'],
                'avg_cost': stock_profit['avg_cost'],
                'unrealized_pnl': stock_profit['unrealized_pnl'],
                'unrealized_pnl_pct': stock_profit['unrealized_pnl_pct'],
                'profit_status': 'profitable' if stock_profit['unrealized_pnl'] > 0 else 'loss' if stock_profit['unrealized_pnl'] < 0 else 'breakeven'
            }
    
    return {
        'score': score,
        'signals': signals,
        'strength': strength,
        'confidence': confidence,
        'bullish_signals': bullish_signals,
        'bearish_signals': bearish_signals,
        'net_score': net_score,
        'timeframe_alignment': timeframe_alignment,
        'alignment_score': alignment_score,
        'profitability': profitability_info,
        'timeframes': {
            '5m': {
                'price': current_price_5m,
                'rsi': rsi_5m,
                'sma_20': sma_20_5m,
                'macd_signal': 'BULLISH' if macd_5m > macd_signal_5m else 'BEARISH'
            },
            '1h': {
                'price': current_price_1h,
                'rsi': rsi_1h,
                'sma_20': sma_20_1h,
                'macd_signal': 'BULLISH' if macd_1h > macd_signal_1h else 'BEARISH'
            }
        }
    }

def analyze_technical_strength(stock_data: Dict, profitability_data: Dict = None) -> Dict:
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

    # ADX and Directional Movement Analysis
    adx = stock_data.get('adx', 0)
    plus_di = stock_data.get('plus_di', 0)
    minus_di = stock_data.get('minus_di', 0)
    
    if adx and adx > 25:  # Strong trend
        if plus_di > minus_di:
            signals.append(f"BULLISH: Strong uptrend (ADX: {adx:.1f}, +DI > -DI)")
            bullish_signals += 2
        elif minus_di > plus_di:
            signals.append(f"BEARISH: Strong downtrend (ADX: {adx:.1f}, -DI > +DI)")
            bearish_signals += 2
    elif adx and adx < 20:
        signals.append(f"NEUTRAL: Weak trend/sideways (ADX: {adx:.1f})")

    # Parabolic SAR Analysis
    sar = stock_data.get('parabolic_sar', 0)
    if sar and current_price:
        if current_price > sar:
            signals.append(f"BULLISH: Price above Parabolic SAR ({sar:.2f})")
            bullish_signals += 1
        else:
            signals.append(f"BEARISH: Price below Parabolic SAR ({sar:.2f})")
            bearish_signals += 1

    # DeMarker Analysis
    demarker = stock_data.get('demarker', 0)
    if demarker:
        if demarker > 0.7:
            signals.append(f"BEARISH: DeMarker overbought ({demarker:.2f})")
            bearish_signals += 1
        elif demarker < 0.3:
            signals.append(f"BULLISH: DeMarker oversold ({demarker:.2f})")
            bullish_signals += 1

    # Moving Average Envelopes Analysis
    ma_env_upper = stock_data.get('ma_env_upper', 0)
    ma_env_lower = stock_data.get('ma_env_lower', 0)
    
    if current_price and ma_env_upper and ma_env_lower:
        if current_price > ma_env_upper:
            signals.append("BEARISH: Price above MA envelope (overbought)")
            bearish_signals += 1
        elif current_price < ma_env_lower:
            signals.append("BULLISH: Price below MA envelope (oversold)")
            bullish_signals += 1

    # On Balance Volume (OBV) Analysis
    obv = stock_data.get('obv', 0)
    if obv and daily_change:
        if daily_change > 0 and obv > 0:
            signals.append("BULLISH: Positive price change with OBV support")
            bullish_signals += 0.5
        elif daily_change < 0 and obv < 0:
            signals.append("BEARISH: Negative price change with OBV confirmation")
            bearish_signals += 0.5

    # Accumulation/Distribution Line Analysis
    ad_line = stock_data.get('ad_line', 0)
    if ad_line and daily_change:
        # Compare A/D line direction with price direction
        if daily_change > 2 and ad_line > 0:  # Strong positive price movement
            signals.append("BULLISH: Strong buying pressure (A/D Line)")
            bullish_signals += 1
        elif daily_change < -2 and ad_line < 0:  # Strong negative price movement
            signals.append("BEARISH: Strong selling pressure (A/D Line)")
            bearish_signals += 1
    
    # Calculate overall score and strength
    net_score = bullish_signals - bearish_signals
    max_possible = 15  # Updated for additional technical indicators
    
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
    
    # Add profitability information if available
    profitability_info = {}
    if profitability_data:
        # Extract symbol from stock_data context (assuming it's passed in state)
        symbol = None
        for s in ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA', 'NFLX', 'CRM', 'ADBE']:
            if s in str(stock_data):
                symbol = s
                break
        
        if symbol and symbol in profitability_data.get('individual_stocks', {}):
            stock_profit = profitability_data['individual_stocks'][symbol]
            profitability_info = {
                'current_position': stock_profit['position'],
                'avg_cost': stock_profit['avg_cost'],
                'unrealized_pnl': stock_profit['unrealized_pnl'],
                'unrealized_pnl_pct': stock_profit['unrealized_pnl_pct'],
                'profit_status': 'profitable' if stock_profit['unrealized_pnl'] > 0 else 'loss' if stock_profit['unrealized_pnl'] < 0 else 'breakeven'
            }
    
    return {
        'score': score,
        'signals': signals,
        'strength': strength,
        'confidence': confidence,
        'bullish_signals': bullish_signals,
        'bearish_signals': bearish_signals,
        'net_score': net_score,
        'profitability': profitability_info
    }

def validate_ai_decisions(state: PortfolioState, profitability_data: Dict = None) -> Dict:
    """
    Enhanced validation that considers ALL technical indicators and their alignment.
    """
    recommendations = state.get('ai_recommendations', {})
    ai_trends = state.get('ai_trend_analysis', {})
    stock_data = state.get('stock_data', {})
    aggressive_mode = state.get('aggressive_mode', False)
    news_sentiment = state.get('news_sentiment', {})     
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

        news_data = news_sentiment.get(symbol, {})
        if news_data.get('has_news', False):
            sentiment = news_data.get('sentiment_label', 'NEUTRAL')
            sentiment_score = news_data.get('sentiment_score', 0)
            
            if action == 'BUY' and sentiment == 'NEGATIVE' and sentiment_score < -0.3:
                warnings.append(f"{symbol}: BUY recommendation conflicts with strong negative news sentiment ({sentiment_score:.2f})")
            elif action == 'SELL' and sentiment == 'POSITIVE' and sentiment_score > 0.3:
                warnings.append(f"{symbol}: SELL recommendation conflicts with strong positive news sentiment ({sentiment_score:.2f})")

        
        print(f"\n📊 VALIDATING {symbol} - {action} ({priority} priority)")
        
        # Get comprehensive technical analysis with profitability data
        technical_analysis = analyze_technical_strength(stock_data.get(symbol, {}), profitability_data)
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
        
        # Display profitability information if available
        profit_info = technical_analysis.get('profitability', {})
        if profit_info:
            position = profit_info.get('current_position', 0)
            unrealized_pnl = profit_info.get('unrealized_pnl', 0)
            unrealized_pnl_pct = profit_info.get('unrealized_pnl_pct', 0)
            profit_status = profit_info.get('profit_status', 'unknown')
            print(f"   💰 Position: {position} shares, P&L: ${unrealized_pnl:+.2f} ({unrealized_pnl_pct:+.1f}%) - {profit_status.upper()}")
        else:
            print(f"   💰 No current position")
        
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
            
            # CRITICAL: Check fee-aware profitability for SELL decisions
            position = state.get('positions', {}).get(symbol, 0)
            current_price = stock_data.get(symbol, {}).get('current_price', 0)
            purchase_price = state.get('purchase_prices', {}).get(symbol, 0)
            
            if position > 0 and current_price > 0 and purchase_price > 0:
                fee_info = calculate_fee_adjusted_pnl(current_price, purchase_price, position)
                net_pnl = fee_info['net_pnl']
                
                if net_pnl <= 0:  # Unprofitable after fees
                    # Check if it's a valid stop-loss scenario
                    loss_pct = ((current_price - purchase_price) / purchase_price) * 100
                    if loss_pct > STOP_LOSS_PERCENTAGE:  # Not a stop-loss trigger
                        issues.append(f"{symbol}: SELL recommendation would result in loss after fees (Net P&L: ${net_pnl:.2f})")
                        print(f"   ❌ CRITICAL FEE ISSUE: Unprofitable SELL - Net P&L: ${net_pnl:.2f}")
                    else:
                        print(f"   ✅ VALID STOP-LOSS: Selling at loss due to stop-loss trigger ({loss_pct:.1f}%)")
                else:
                    print(f"   ✅ PROFITABLE SELL: Net P&L after fees: ${net_pnl:.2f}")
            
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
    
    # Add portfolio profitability summary if available
    if profitability_data:
        portfolio_summary = profitability_data.get('portfolio_summary', {})
        total_pnl = portfolio_summary.get('total_pnl', 0)
        total_pnl_pct = portfolio_summary.get('total_pnl_pct', 0)
        total_investment = portfolio_summary.get('total_investment', 0)
        print(f"   💰 Portfolio P&L: ${total_pnl:+.2f} ({total_pnl_pct:+.1f}%) on ${total_investment:,.0f} invested")

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
    - Standard Deviation: {indicators.get('std_dev', 0):.3f}
    - OBV: {indicators.get('obv', 0):,.0f}

    ADVANCED INDICATORS:
    - ADX (Trend Strength): {indicators.get('adx', 0):.1f}
    - +DI: {indicators.get('plus_di', 0):.1f} | -DI: {indicators.get('minus_di', 0):.1f}
    - Parabolic SAR: ${indicators.get('parabolic_sar', 0):.2f}
    - DeMarker: {indicators.get('demarker', 0):.3f}
    - A/D Line: {indicators.get('ad_line', 0):,.0f}
    - PVT: {indicators.get('pvt', 0):,.0f}

    MOVING AVERAGE ENVELOPES:
    - Upper: ${indicators.get('ma_env_upper', 0):.2f}
    - Middle: ${indicators.get('ma_env_middle', 0):.2f}
    - Lower: ${indicators.get('ma_env_lower', 0):.2f}

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

async def get_ai_trend_analysis_dual(stock_data_5m: Dict, stock_data_1h: Dict, symbol: str) -> Dict:
    """
    Enhanced AI trend analysis using DUAL timeframes (5-minute and 1-hour data).
    """
    if not stock_data_5m.get('valid', False) or not stock_data_1h.get('valid', False):
        # Fallback to single timeframe if dual data isn't available
        return await get_ai_trend_analysis({'symbol': stock_data_5m}, symbol)

    # Get dual timeframe technical analysis
    dual_technical_analysis = analyze_technical_strength_dual_timeframe(stock_data_5m, stock_data_1h)
    
    # Create enhanced prompt with DUAL timeframe indicators
    context = f"""
    Perform DUAL TIMEFRAME technical analysis for {symbol} using BOTH 5-minute and 1-hour data:

    === 5-MINUTE TIMEFRAME (Short-term) ===
    PRICE DATA:
    - Current Price: ${stock_data_5m.get('current_price', 0):.2f}
    - Previous Close: ${stock_data_5m.get('previous_close', 0):.2f}
    - Daily Change: {stock_data_5m.get('daily_change_pct', 0):.2f}%

    MOVING AVERAGES (5M):
    - SMA 20: ${stock_data_5m.get('sma_20', 0):.2f}
    - SMA 50: ${stock_data_5m.get('sma_50', 0):.2f}
    - EMA 12: ${stock_data_5m.get('ema_12', 0):.2f}
    - EMA 26: ${stock_data_5m.get('ema_26', 0):.2f}

    MOMENTUM INDICATORS (5M):
    - RSI (14): {stock_data_5m.get('rsi', 50):.1f}
    - Williams %R: {stock_data_5m.get('williams_r', -50):.1f}
    - Stochastic K: {stock_data_5m.get('stoch_k', 50):.1f}
    - MACD: {stock_data_5m.get('macd', 0):.3f} | Signal: {stock_data_5m.get('macd_signal', 0):.3f}

    === 1-HOUR TIMEFRAME (Medium-term) ===
    PRICE DATA:
    - Current Price: ${stock_data_1h.get('current_price', 0):.2f}
    - Previous Close: ${stock_data_1h.get('previous_close', 0):.2f}
    - Daily Change: {stock_data_1h.get('daily_change_pct', 0):.2f}%

    MOVING AVERAGES (1H):
    - SMA 20: ${stock_data_1h.get('sma_20', 0):.2f}
    - SMA 50: ${stock_data_1h.get('sma_50', 0):.2f}
    - EMA 12: ${stock_data_1h.get('ema_12', 0):.2f}
    - EMA 26: ${stock_data_1h.get('ema_26', 0):.2f}

    MOMENTUM INDICATORS (1H):
    - RSI (14): {stock_data_1h.get('rsi', 50):.1f}
    - Williams %R: {stock_data_1h.get('williams_r', -50):.1f}
    - Stochastic K: {stock_data_1h.get('stoch_k', 50):.1f}
    - MACD: {stock_data_1h.get('macd', 0):.3f} | Signal: {stock_data_1h.get('macd_signal', 0):.3f}

    === DUAL TIMEFRAME ANALYSIS RESULTS ===
    Overall Technical Score: {dual_technical_analysis.get('score', 5)}/10
    Strength Assessment: {dual_technical_analysis.get('strength', 'NEUTRAL')}
    Timeframe Alignment: {dual_technical_analysis.get('timeframe_alignment', 'NEUTRAL')}
    Bullish Signals: {dual_technical_analysis.get('bullish_signals', 0)}
    Bearish Signals: {dual_technical_analysis.get('bearish_signals', 0)}

    KEY SIGNALS DETECTED:
    {chr(10).join(['- ' + signal for signal in dual_technical_analysis.get('signals', [])[:6]])}

    TIMEFRAME COMPARISON:
    5M Trends: Price ${dual_technical_analysis.get('timeframes', {}).get('5m', {}).get('price', 0):.2f}, RSI {dual_technical_analysis.get('timeframes', {}).get('5m', {}).get('rsi', 50):.1f}
    1H Trends: Price ${dual_technical_analysis.get('timeframes', {}).get('1h', {}).get('price', 0):.2f}, RSI {dual_technical_analysis.get('timeframes', {}).get('1h', {}).get('rsi', 50):.1f}

    CRITICAL ANALYSIS INSTRUCTIONS:
    1. Weight 1-hour timeframe MORE HEAVILY than 5-minute for trend direction
    2. Use 5-minute data for entry/exit timing precision
    3. Require timeframe alignment for HIGH confidence signals
    4. Flag conflicting timeframes as MEDIUM or LOW confidence
    5. Consider both short-term momentum (5M) and medium-term trend (1H)

    Based on this DUAL TIMEFRAME analysis, provide your assessment in EXACT format:
    TREND: [BULLISH/BEARISH/NEUTRAL]
    CONFIDENCE: [HIGH/MEDIUM/LOW]
    REASONING: [Brief summary considering BOTH timeframes and their alignment]
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
        
        # Add dual timeframe technical analysis data
        analysis['technical_score'] = dual_technical_analysis.get('score', 5)
        analysis['technical_strength'] = dual_technical_analysis.get('strength', 'NEUTRAL')
        analysis['timeframe_alignment'] = dual_technical_analysis.get('timeframe_alignment', 'NEUTRAL')
        analysis['signal_count'] = len(dual_technical_analysis.get('signals', []))
        analysis['dual_timeframe'] = True
        
        return analysis
    except Exception as e:
        print(f"❌ Dual timeframe AI trend analysis error for {symbol}: {e}")
        # Fallback to single timeframe
        return await get_ai_trend_analysis({'symbol': stock_data_5m}, symbol)

import re
from typing import Dict, Any

def parse_ai_recommendations_enhanced(ai_response: str, portfolio_stocks: list) -> Dict[str, Dict[str, Any]]:
    """
    Enhanced parsing function to handle various AI response formats including markdown.
    """
    recommendations = {}
    
    # Clean the response text
    cleaned_response = ai_response.strip()
    
    # Method 1: Enhanced line-by-line parsing with markdown handling
    for line in cleaned_response.split('\n'):
        line = line.strip()
        if not line:
            continue
            
        # Remove markdown formatting
        clean_line = re.sub(r'\*\*', '', line)  # Remove ** bold markers
        clean_line = re.sub(r'\*', '', clean_line)   # Remove * markers
        clean_line = clean_line.strip()
        
        # Check if this line contains a stock recommendation
        if ('STOCK:' in clean_line.upper() or 
            any(stock in clean_line.upper() for stock in portfolio_stocks)):
            
            try:
                rec = parse_recommendation_line(clean_line, portfolio_stocks)
                if rec and 'symbol' in rec:
                    symbol = rec.pop('symbol')
                    recommendations[symbol] = rec
                    print(f"✅ Parsed {symbol}: {rec.get('action', 'HOLD')} ({rec.get('priority', 'LOW')})")
            except Exception as e:
                print(f"⚠️  Error parsing line: {clean_line[:50]}... - {e}")
    
    # Method 2: Regex-based extraction as fallback
    if len(recommendations) < len(portfolio_stocks):
        print("🔄 Using regex fallback parsing...")
        regex_recommendations = parse_with_regex(cleaned_response, portfolio_stocks)
        
        # Merge results, preferring Method 1
        for symbol, rec in regex_recommendations.items():
            if symbol not in recommendations:
                recommendations[symbol] = rec
                print(f"✅ Regex parsed {symbol}: {rec.get('action', 'HOLD')}")
    
    # Method 3: Simple keyword extraction as last resort
    if len(recommendations) < len(portfolio_stocks):
        print("🔄 Using keyword extraction...")
        keyword_recommendations = parse_with_keywords(cleaned_response, portfolio_stocks)
        
        for symbol, rec in keyword_recommendations.items():
            if symbol not in recommendations:
                recommendations[symbol] = rec
                print(f"✅ Keyword parsed {symbol}: {rec.get('action', 'HOLD')}")
    
    # Ensure all portfolio stocks have recommendations
    for symbol in portfolio_stocks:
        if symbol not in recommendations:
            print(f"⚠️  Missing recommendation for {symbol}, defaulting to HOLD")
            recommendations[symbol] = {
                'action': 'HOLD',
                'priority': 'LOW',
                'reasoning': 'No clear signal from analysis',
                'technical_score': 5.0,
                'confidence': 'LOW'
            }
    
    return recommendations


def parse_recommendation_line(line: str, portfolio_stocks: list) -> Dict[str, Any]:
    """Parse a single recommendation line."""
    rec = {}
    symbol = None
    
    # Split by pipe and process each part
    parts = [p.strip() for p in line.split('|')]
    
    for part in parts:
        if ':' not in part:
            continue
            
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
    
    # Try to find symbol in first part if not found
    if not symbol:
        first_part = parts[0].replace('STOCK:', '').strip()
        if first_part in portfolio_stocks:
            symbol = first_part
        else:
            # Look for any portfolio stock in the first part
            for stock in portfolio_stocks:
                if stock in first_part.upper():
                    symbol = stock
                    break
    
    if symbol:
        rec['symbol'] = symbol
        # Set defaults
        rec.setdefault('action', 'HOLD')
        rec.setdefault('priority', 'LOW')
        rec.setdefault('reasoning', 'AI recommendation')
        rec.setdefault('technical_score', 5.0)
        rec.setdefault('confidence', 'MEDIUM')
    
    return rec


def parse_with_regex(text: str, portfolio_stocks: list) -> Dict[str, Dict[str, Any]]:
    """Use regex to extract recommendations."""
    recommendations = {}
    
    # Pattern to match the recommendation format
    pattern = r'(?:STOCK:\s*)?([A-Z]+)(?:\s*\||\s+)(?:ACTION:\s*)?(BUY|SELL|HOLD)(?:\s*\||\s+)(?:PRIORITY:\s*)?(HIGH|MEDIUM|LOW)?'
    
    matches = re.finditer(pattern, text.upper(), re.IGNORECASE)
    
    for match in matches:
        symbol = match.group(1)
        action = match.group(2) if match.group(2) else 'HOLD'
        priority = match.group(3) if match.group(3) else 'LOW'
        
        if symbol in portfolio_stocks:
            # Try to extract more details from the surrounding text
            start = max(0, match.start() - 100)
            end = min(len(text), match.end() + 200)
            context = text[start:end]
            
            # Extract technical score if present
            score_match = re.search(r'(?:TECHNICAL[_\s]*SCORE|Score)[\s:]*([0-9\.]+)', context, re.IGNORECASE)
            technical_score = float(score_match.group(1)) if score_match else 5.0
            
            # Extract confidence if present
            conf_match = re.search(r'CONFIDENCE[\s:]*([A-Z]+)', context, re.IGNORECASE)
            confidence = conf_match.group(1) if conf_match else 'MEDIUM'
            
            recommendations[symbol] = {
                'action': action,
                'priority': priority,
                'reasoning': 'Extracted from AI response',
                'technical_score': technical_score,
                'confidence': confidence
            }
    
    return recommendations


def parse_with_keywords(text: str, portfolio_stocks: list) -> Dict[str, Dict[str, Any]]:
    """Extract recommendations using keyword proximity."""
    recommendations = {}
    text_upper = text.upper()
    
    for symbol in portfolio_stocks:
        # Find the symbol in text
        symbol_pos = text_upper.find(symbol)
        if symbol_pos == -1:
            continue
            
        # Extract surrounding context (500 chars around symbol)
        start = max(0, symbol_pos - 250)
        end = min(len(text), symbol_pos + 250)
        context = text[start:end].upper()
        
        # Determine action based on keywords
        action = 'HOLD'  # default
        if any(word in context for word in ['BUY', 'PURCHASE', 'ACQUIRE']):
            action = 'BUY'
        elif any(word in context for word in ['SELL', 'DISPOSE', 'EXIT']):
            action = 'SELL'
        
        # Determine priority
        priority = 'LOW'  # default
        if any(word in context for word in ['HIGH PRIORITY', 'URGENT', 'CRITICAL']):
            priority = 'HIGH'
        elif any(word in context for word in ['MEDIUM PRIORITY', 'MODERATE']):
            priority = 'MEDIUM'
        
        # Extract technical score
        score_match = re.search(r'(?:SCORE|TECHNICAL)[\s:]*([0-9\.]+)', context)
        technical_score = float(score_match.group(1)) if score_match else 5.0
        
        recommendations[symbol] = {
            'action': action,
            'priority': priority,
            'reasoning': 'Extracted via keyword analysis',
            'technical_score': technical_score,
            'confidence': 'LOW'
        }
    
    return recommendations


# Complete function with context building:
# async def get_ai_portfolio_recommendations(state: PortfolioState):
#     """
#     Enhanced AI recommendations using comprehensive technical analysis for ALL indicators.
#     """
#     print("\n🧠 GENERATING AI RECOMMENDATIONS WITH FULL TECHNICAL ANALYSIS")
#     print("=" * 70)
    
#     portfolio_summary = []
#     for symbol in PORTFOLIO_STOCKS:
#         s_data = state['stock_data'].get(symbol, {})
#         t_analysis = state['ai_trend_analysis'].get(symbol, {})
#         pos = state['positions'].get(symbol, 0)
        
#         if s_data.get('valid', False):
#             # Get comprehensive technical analysis
#             tech_analysis = analyze_technical_strength(s_data)
            
#             portfolio_summary.append(
#                 f"""{symbol} (Position: {pos} shares):
#    Price: ${s_data.get('current_price', 0):.2f} (Change: {s_data.get('daily_change_pct', 0):+.2f}%)
#    Technical Score: {tech_analysis.get('score', 5)}/10 ({tech_analysis.get('strength', 'NEUTRAL')})
#    RSI: {s_data.get('rsi', 50):.1f} | Williams %R: {s_data.get('williams_r', -50):.1f}
#    MACD Hist: {s_data.get('macd_histogram', 0):.3f} | ADX: {s_data.get('adx', 0):.1f}
#    Volume: {(s_data.get('current_volume', 0) / max(s_data.get('volume_ma', 1), 1)):.1f}x avg | ATR: {s_data.get('atr', 0):.3f}
#    Bollinger: {"Upper" if s_data.get('current_price', 0) > s_data.get('bb_upper', 0) else "Lower" if s_data.get('current_price', 0) < s_data.get('bb_lower', 0) else "Middle"} band
#    Parabolic SAR: ${s_data.get('parabolic_sar', 0):.2f} | DeMarker: {s_data.get('demarker', 0):.2f}
#    AI Trend: {t_analysis.get('trend', 'N/A')} ({t_analysis.get('confidence', 'N/A')} conf, {t_analysis.get('risk_level', 'N/A')} risk)
#    Key Signals: {tech_analysis.get('bullish_signals', 0)} bullish, {tech_analysis.get('bearish_signals', 0)} bearish"""
#             )
            
#             print(f"📊 {symbol}: Tech Score {tech_analysis.get('score', 5)}/10, RSI {s_data.get('rsi', 50):.1f}, Trend {t_analysis.get('trend', 'N/A')}")
    
#     # Enhanced strategy instruction based on mode
#     strategy_instruction = ""
#     if state.get('aggressive_mode', False):
#         strategy_instruction = """
#         AGGRESSIVE TRADING MODE ACTIVE:
#         - MAXIMIZE PROFIT through decisive action
#         - Accept higher risk for higher potential returns  
#         - Consider technical scores 4+ as actionable for BUY
#         - Consider technical scores 6- as actionable for SELL
#         - Prioritize momentum and volume indicators
#         - Be quick to enter/exit based on technical signals"""
#     else:
#         strategy_instruction = """
#         BALANCED TRADING MODE ACTIVE:
#         - Prioritize capital preservation with steady growth
#         - Require technical scores 6+ for high-priority BUY
#         - Require technical scores 4- for high-priority SELL  
#         - Demand multiple confirming indicators
#         - Avoid trades during high volatility periods
#         - Focus on strong technical alignment"""

#     context = f"""
#     You are an expert quantitative trading analyst with deep technical analysis expertise.
#     {strategy_instruction}
    
#     PORTFOLIO STATE:
#     - Total Value: ${state['total_portfolio_value']:.2f}
#     - Unrealized P&L: ${state['total_unrealized_pnl']:+.2f}
#     - Available Cash: ${state['cash_available']:.2f}
#     - Total Trades This Session: {state.get('total_trades', 0)}

#     CONSTRAINTS:
#     - Trade size: {TRADE_SIZE} shares per order
#     - Max shares per stock: {MAX_SHARES_PER_STOCK}
#     - Min cash reserve: ${MIN_CASH_RESERVE:,}
#     - Max total shares: {MAX_TOTAL_SHARES}

#     COMPREHENSIVE STOCK ANALYSIS:
#     {chr(10).join(portfolio_summary)}

#     CRITICAL INSTRUCTION: Consider ALL technical indicators in your analysis:
#     - Price vs Moving Averages (SMA20, SMA50, EMA12, EMA26)
#     - Momentum indicators (RSI, Williams %R, Stochastic, DeMarker)
#     - MACD system (line, signal, histogram)
#     - Bollinger Bands and Moving Average Envelopes
#     - Volume analysis (OBV, A/D Line, PVT, Volume MA)
#     - Volatility measurements (ATR, Standard Deviation, 20-day vol)
#     - Trend strength indicators (ADX, +DI, -DI)
#     - Support/Resistance indicators (Parabolic SAR)
    
#     For each stock, provide recommendation in EXACT format:
#     STOCK: [SYMBOL] | ACTION: [BUY/SELL/HOLD] | PRIORITY: [HIGH/MEDIUM/LOW] | REASONING: [Specific technical reasons citing 2-3 indicators] | TECHNICAL_SCORE: [1-10] | CONFIDENCE: [HIGH/MEDIUM/LOW]
#     """
    
#     feedback = state.get("validation_feedback")
#     if feedback:
#         context += f"""
        
#         CRITICAL REVISION REQUEST: 
#         Your previous recommendations were rejected for these reasons: "{feedback}"
        
#         MANDATORY FIXES:
#         - Address all identified contradictions
#         - Ensure technical indicators align with recommended actions
#         - Provide stronger reasoning based on multiple confirming signals
#         - Adjust priorities based on technical strength scores
#         """
    
#     try:
#         print("🤖 Sending comprehensive analysis to AI...")
#         response = await gemini_model.generate_content_async(context)
#         ai_response = response.text
        
#         print("\n--- FULL AI RESPONSE ---")
#         print(ai_response)
#         print("------------------------\n")

#         # Use the enhanced parsing function
#         recommendations = parse_ai_recommendations_enhanced(ai_response, PORTFOLIO_STOCKS)
        
#         print(f"\n✅ Generated recommendations for {len(recommendations)}/{len(PORTFOLIO_STOCKS)} stocks")
#         return recommendations

#     except Exception as e:
#         print(f"❌ AI portfolio recommendation error: {e}")
#         return {s: {
#             'action': 'HOLD', 
#             'priority': 'LOW', 
#             'reasoning': f'AI Error: {e}',
#             'technical_score': 5.0,
#             'confidence': 'LOW'
#         } for s in PORTFOLIO_STOCKS}

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

def calculate_fee_adjusted_pnl(current_price: float, purchase_price: float, shares: int) -> Dict[str, float]:
    """
    Calculate profit/loss considering trading fees.
    Returns dict with gross P&L, fees, and net P&L.
    """
    if shares <= 0 or purchase_price <= 0:
        return {'gross_pnl': 0, 'buy_fees': 0, 'sell_fees': 0, 'net_pnl': 0}
    
    gross_value_change = (current_price - purchase_price) * shares
    buy_fees = TRADING_FEE_PER_TRADE  # Fee paid when buying
    sell_fees = TRADING_FEE_PER_TRADE  # Fee that would be paid when selling
    total_fees = buy_fees + sell_fees
    net_pnl = gross_value_change - total_fees
    
    return {
        'gross_pnl': gross_value_change,
        'buy_fees': buy_fees,
        'sell_fees': sell_fees,
        'total_fees': total_fees,
        'net_pnl': net_pnl
    }

def is_profitable_to_sell(current_price: float, purchase_price: float, shares: int) -> bool:
    """
    Check if selling would be profitable after accounting for fees.
    """
    fee_analysis = calculate_fee_adjusted_pnl(current_price, purchase_price, shares)
    return fee_analysis['net_pnl'] > 0

def should_apply_trailing_stop(symbol: str, current_price: float, state: PortfolioState) -> bool:
    """
    Check if trailing stop should trigger (3% down from peak, but only if still profitable).
    """
    # Get position info
    position = state.get('positions', {}).get(symbol, 0)
    if position <= 0:
        return False
    
    # Get purchase price
    purchase_price = state.get('purchase_prices', {}).get(symbol, 0)
    if purchase_price <= 0:
        return False
    
    # Get peak price from state (we'll add this tracking)
    peaks = state.get('price_peaks', {})
    peak_price = peaks.get(symbol, purchase_price)
    
    # Update peak if current price is higher
    if current_price > peak_price:
        peak_price = current_price
        if 'price_peaks' not in state:
            state['price_peaks'] = {}
        state['price_peaks'][symbol] = peak_price
    
    # Check if current price is 3% below peak
    drawdown_pct = ((peak_price - current_price) / peak_price) * 100
    
    # Only trigger if drawdown >= 3% AND still profitable after fees
    if drawdown_pct >= 3.0:
        if is_profitable_to_sell(current_price, purchase_price, position):
            print(f"🎯 TRAILING STOP TRIGGER: {symbol} down {drawdown_pct:.1f}% from peak ${peak_price:.2f}, still profitable")
            return True
        else:
            print(f"⚠️ {symbol} trailing stop would trigger but sale wouldn't be profitable after fees")
    
    return False

def get_enhanced_sell_conditions(state: PortfolioState) -> Dict[str, str]:
    """
    Enhanced sell conditions considering fees and trailing stops.
    """
    actions = {}
    
    for symbol in PORTFOLIO_STOCKS:
        position = state.get('positions', {}).get(symbol, 0)
        if position <= 0:
            continue
            
        current_price = state.get('stock_prices', {}).get(symbol, 0)
        purchase_price = state.get('purchase_prices', {}).get(symbol, 0)
        
        if purchase_price > 0 and current_price > 0:
            # Check regular stop loss (2% loss from purchase price)
            change_pct = ((current_price - purchase_price) / purchase_price) * 100
            
            if change_pct <= STOP_LOSS_PERCENTAGE:
                actions[symbol] = 'SELL'
                print(f"🚨 STOP-LOSS TRIGGER: {symbol} at {change_pct:.2f}% loss")
                continue
            
            # Check trailing stop
            if should_apply_trailing_stop(symbol, current_price, state):
                actions[symbol] = 'SELL'
                continue
            
            # Check take profit (only if profitable after fees)
            if change_pct >= TAKE_PROFIT_PERCENTAGE:
                if is_profitable_to_sell(current_price, purchase_price, position):
                    actions[symbol] = 'SELL'
                    print(f"💰 TAKE-PROFIT TRIGGER: {symbol} at {change_pct:.2f}% gain (profitable after fees)")
                else:
                    print(f"⚠️ {symbol} take-profit delayed: not profitable after fees")
    
    return actions

async def get_ai_portfolio_recommendations_with_news(state: PortfolioState):
    """
    Enhanced AI recommendations using comprehensive technical analysis AND news sentiment.
    """
    print("\n🧠 GENERATING AI RECOMMENDATIONS WITH TECHNICAL ANALYSIS + NEWS SENTIMENT")
    print("=" * 80)
    
    portfolio_summary = []
    news_sentiment = state.get('news_sentiment', {})
    
    for symbol in PORTFOLIO_STOCKS:
        s_data = state['stock_data'].get(symbol, {})
        t_analysis = state['ai_trend_analysis'].get(symbol, {})
        news_data = news_sentiment.get(symbol, {})
        pos = state['positions'].get(symbol, 0)
        
        if s_data.get('valid', False):
            # Get comprehensive technical analysis
            tech_analysis = analyze_technical_strength(s_data)
            
            # Add news sentiment to summary
            news_info = "No news"
            if news_data.get('has_news', False):
                news_info = f"{news_data.get('sentiment_emoji', '📰')} {news_data.get('sentiment_label', 'NEUTRAL')} sentiment"
                news_score = news_data.get('sentiment_score', 0)
                news_info += f" (score: {news_score:.2f})"
                
                # Add latest headline if available
                headlines = news_data.get('latest_headlines', [])
                if headlines:
                    news_info += f" | Latest: {headlines[0][:50]}..."
            
            portfolio_summary.append(
                f"""{symbol} (Position: {pos} shares):
   Price: ${s_data.get('current_price', 0):.2f} (Change: {s_data.get('daily_change_pct', 0):+.2f}%)
   Technical Score: {tech_analysis.get('score', 5)}/10 ({tech_analysis.get('strength', 'NEUTRAL')})
   RSI: {s_data.get('rsi', 50):.1f} | Williams %R: {s_data.get('williams_r', -50):.1f}
   MACD Hist: {s_data.get('macd_histogram', 0):.3f} | ADX: {s_data.get('adx', 0):.1f}
   Volume: {(s_data.get('current_volume', 0) / max(s_data.get('volume_ma', 1), 1)):.1f}x avg | ATR: {s_data.get('atr', 0):.3f}
   Bollinger: {"Upper" if s_data.get('current_price', 0) > s_data.get('bb_upper', 0) else "Lower" if s_data.get('current_price', 0) < s_data.get('bb_lower', 0) else "Middle"} band
   Parabolic SAR: ${s_data.get('parabolic_sar', 0):.2f} | DeMarker: {s_data.get('demarker', 0):.2f}
   AI Trend: {t_analysis.get('trend', 'N/A')} ({t_analysis.get('confidence', 'N/A')} conf, {t_analysis.get('risk_level', 'N/A')} risk)
   NEWS SENTIMENT: {news_info}
   Key Signals: {tech_analysis.get('bullish_signals', 0)} bullish, {tech_analysis.get('bearish_signals', 0)} bearish"""
            )
            
            print(f"📊 {symbol}: Tech {tech_analysis.get('score', 5)}/10, RSI {s_data.get('rsi', 50):.1f}, News: {news_info}")
    
    # Build comprehensive news summary section
    news_summary_section = "\n    REAL-TIME NEWS SENTIMENT ANALYSIS:\n"
    if news_sentiment:
        for symbol, news in news_sentiment.items():
            if news.get('has_news', False):
                score = news.get('sentiment_score', 0)
                articles = news.get('article_count', 0)
                news_summary_section += f"    - {symbol}: {news.get('sentiment_emoji', '📰')} {news.get('sentiment_label', 'NEUTRAL')} sentiment (score: {score:.2f}, {articles} articles)\n"
                
                # Add key headlines
                headlines = news.get('latest_headlines', [])
                if headlines:
                    news_summary_section += f"      Key headline: {headlines[0]}\n"
        
        if "Key headline:" not in news_summary_section:
            news_summary_section += "    - No significant news detected for any portfolio stocks\n"
    else:
        news_summary_section += "    - News analysis not available\n"

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
        - Be quick to enter/exit based on technical signals
        - Use positive news as strong confirmation for BUY signals
        - Use negative news as immediate trigger for SELL signals
        - News sentiment score +0.5 or higher = strong BUY boost
        - News sentiment score -0.5 or lower = immediate SELL consideration"""
    else:
        strategy_instruction = """
        BALANCED TRADING MODE ACTIVE:
        - Prioritize capital preservation with aim to maximize profit
        - Require technical scores 6+ for high-priority BUY
        - Require technical scores 4- for high-priority SELL  
        - Demand multiple confirming indicators
        - Avoid trades during high volatility periods
        - Focus on strong technical alignment
        - Use news sentiment as critical risk assessment factor
        - Avoid BUY on negative news (sentiment < -0.2)
        - Avoid SELL on strongly positive news (sentiment > +0.5)
        - Require news alignment with technical signals for high-priority trades"""

    # Get memory context if available
    memory_context = state.get('memory_context', 'No previous trading context available for this session.')

    # Generate fee-aware position analysis for the prompt
    fee_analysis_summary = []
    for symbol in PORTFOLIO_STOCKS:
        position = state['positions'].get(symbol, 0)
        if position > 0:
            current_price = state['stock_prices'].get(symbol, 0)
            purchase_price = state['purchase_prices'].get(symbol, 0)
            if current_price > 0 and purchase_price > 0:
                fee_info = calculate_fee_adjusted_pnl(current_price, purchase_price, position)
                net_pnl = fee_info['net_pnl']
                total_fees = fee_info['total_fees']
                is_profitable = net_pnl > 0
                
                fee_analysis_summary.append(
                    f"   {symbol}: {position} shares @ ${purchase_price:.2f} → ${current_price:.2f} | "
                    f"Net P&L: ${net_pnl:+.2f} (after ${total_fees:.2f} fees) | "
                    f"{'✅ PROFITABLE' if is_profitable else '❌ UNPROFITABLE'} to sell"
                )
    
    fee_analysis_text = "\n".join(fee_analysis_summary) if fee_analysis_summary else "   No current positions to analyze"

    context = f"""
    You are an expert quantitative trading analyst with deep technical analysis expertise and access to real-time news sentiment from IBKR.
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
    
    CRITICAL TRADING FEES & PROFITABILITY ANALYSIS:
    - Trading fee per trade: ${TRADING_FEE_PER_TRADE:.2f} (both buy and sell)
    - Total fees per round trip: ${TRADING_FEE_PER_TRADE * 2:.2f}
    - Current Position Profitability (after fees):
{fee_analysis_text}

    HISTORICAL TRADING CONTEXT:
    {memory_context}
    {news_summary_section}
    
    COMPREHENSIVE STOCK ANALYSIS:
    {chr(10).join(portfolio_summary)}

    CRITICAL INSTRUCTION: Integrate technical indicators AND news sentiment in your analysis:
    
    TECHNICAL FACTORS (Primary):
    - Price vs Moving Averages (SMA20, SMA50, EMA12, EMA26)
    - Momentum indicators (RSI, Williams %R, Stochastic, DeMarker)  
    - MACD system (line, signal, histogram)
    - Bollinger Bands and Moving Average Envelopes
    - Volume analysis (OBV, A/D Line, PVT, Volume MA)
    - Volatility measurements (ATR, Standard Deviation, 20-day vol)
    - Trend strength indicators (ADX, +DI, -DI)
    - Support/Resistance indicators (Parabolic SAR)
    
    NEWS SENTIMENT FACTORS (Secondary but Important):
    - Positive news sentiment (POSITIVE, score > 0) should support BUY decisions when technical indicators align
    - Negative news sentiment (NEGATIVE, score < 0) should support SELL decisions or block BUY decisions
    - Neutral news (NEUTRAL, score ≈ 0) should not override strong technical signals
    - NO_DATA means rely purely on technical analysis
    - Consider news sentiment score magnitude: higher absolute values = stronger signal
    - Recent headlines provide context for sentiment direction
    
    DECISION INTEGRATION MATRIX:
    1. Strong Technical + Positive News = HIGH confidence BUY
    2. Strong Technical + Negative News = Reduce to MEDIUM priority or HOLD
    3. Weak Technical + Positive News = MEDIUM priority BUY consideration  
    4. Weak Technical + Negative News = AVOID BUY or consider SELL
    5. Strong Technical + No News = Proceed based on technical analysis
    6. Negative News + Any Technical = Seriously consider SELL or avoid BUY
    
    CRITICAL FEE-AWARE SELL RULES:
    1. NEVER sell a position at a loss unless it's a stop-loss trigger (2%+ loss from purchase price)
    2. Only sell profitable positions (net P&L > $0 after accounting for ${TRADING_FEE_PER_TRADE * 2:.2f} round-trip fees)
    3. Prefer HOLD over unprofitable SELL - wait for price recovery or stop-loss trigger
    4. Trailing stop: Consider selling when price drops 3%+ from peak BUT only if still profitable after fees
    5. Management fee consideration: Minimum profit threshold = ${TRADING_FEE_PER_TRADE * 2:.2f} + small buffer
    
    For each stock, provide recommendation in EXACT format:
    STOCK: [SYMBOL] | ACTION: [BUY/SELL/HOLD] | PRIORITY: [HIGH/MEDIUM/LOW] | REASONING: [Technical reasons + specific news sentiment impact] | TECHNICAL_SCORE: [1-10] | CONFIDENCE: [HIGH/MEDIUM/LOW]
    """
    
    feedback = state.get("validation_feedback")
    if feedback:
        context += f"""
        
        CRITICAL REVISION REQUEST: 
        Your previous recommendations were rejected for these reasons: "{feedback}"
        
        MANDATORY FIXES:
        - Address all identified contradictions
        - Ensure technical indicators AND news sentiment align with recommended actions
        - Provide stronger reasoning based on multiple confirming signals including news
        - Adjust priorities based on technical strength scores AND news sentiment alignment
        - Explicitly mention how news sentiment influenced each decision
        """

    # ==============================================================================
    # --- START: FULL PROMPT BEING SENT TO AI ---
    print("\n" + "#"*25 + " PROMPT SENT TO GEMINI " + "#"*25)
    print(context)
    print("#"*75 + "\n")
    # --- END: FULL PROMPT BEING SENT TO AI ---
    # ==============================================================================

    try:
        print("🤖 Sending comprehensive analysis with news sentiment to AI...")
        response = await gemini_model.generate_content_async(context)
        ai_response = response.text
        
        print("\n--- FULL AI RESPONSE WITH NEWS + TECHNICAL ---")
        print(ai_response)
        print("----------------------------------------------\n")

        # Use your existing enhanced parsing function
        recommendations = parse_ai_recommendations_enhanced(ai_response, PORTFOLIO_STOCKS)
        
        print(f"\n✅ Generated recommendations with news + technical analysis for {len(recommendations)}/{len(PORTFOLIO_STOCKS)} stocks")
        return recommendations

    except Exception as e:
        print(f"❌ AI portfolio recommendation with news error: {e}")
        return {s: {
            'action': 'HOLD', 
            'priority': 'LOW', 
            'reasoning': f'AI Error: {e}',
            'technical_score': 5.0,
            'confidence': 'LOW'
        } for s in PORTFOLIO_STOCKS}


# ===================================================================
# === PRICE TARGET FORECASTING SYSTEM ===
# ===================================================================

def calculate_technical_price_targets(stock_data: Dict, current_price: float, symbol: str) -> Dict[str, Any]:
    """
    Calculate multiple price targets based on technical indicators.
    Returns conservative, moderate, and aggressive targets.
    """
    targets = {
        'conservative': current_price * 1.05,  # Default 5% gain
        'moderate': current_price * 1.10,      # Default 10% gain  
        'aggressive': current_price * 1.15,    # Default 15% gain
        'method': 'percentage_based',
        'confidence': 'LOW',
        'timeframe_days': 30
    }
    
    try:
        # Method 1: Bollinger Bands targets
        bb_upper = stock_data.get('bb_upper', 0)
        bb_middle = stock_data.get('bb_middle', 0)
        bb_lower = stock_data.get('bb_lower', 0)
        
        if bb_upper > current_price > 0:
            bb_target = bb_upper
            bb_gain_pct = ((bb_target - current_price) / current_price) * 100
            
            if 3 <= bb_gain_pct <= 25:  # Reasonable target range
                targets['conservative'] = current_price + (bb_target - current_price) * 0.7
                targets['moderate'] = bb_target
                targets['aggressive'] = bb_target * 1.05
                targets['method'] = 'bollinger_bands'
                targets['confidence'] = 'MEDIUM'
                
        # Method 2: Resistance level targets
        # Use 20-day high as resistance approximation
        resistance_level = stock_data.get('high_20d', current_price * 1.1)
        if resistance_level > current_price:
            resistance_gain_pct = ((resistance_level - current_price) / current_price) * 100
            
            if 2 <= resistance_gain_pct <= 20:
                targets['conservative'] = current_price + (resistance_level - current_price) * 0.6
                targets['moderate'] = resistance_level
                targets['aggressive'] = resistance_level * 1.08
                targets['method'] = 'resistance_level'
                targets['confidence'] = 'HIGH'
                
        # Method 3: Moving average targets
        sma_20 = stock_data.get('sma_20', 0)
        sma_50 = stock_data.get('sma_50', 0)
        
        if sma_20 > current_price and sma_50 > 0:
            # Target is return to moving average + premium
            ma_target = max(sma_20, sma_50) * 1.03
            if ma_target > current_price:
                ma_gain_pct = ((ma_target - current_price) / current_price) * 100
                if 1 <= ma_gain_pct <= 15:
                    targets['conservative'] = ma_target
                    targets['moderate'] = ma_target * 1.05
                    targets['aggressive'] = ma_target * 1.10
                    targets['method'] = 'moving_average_reversion'
                    targets['confidence'] = 'MEDIUM'
        
        # Method 4: Volume-weighted targets (if volume spike)
        volume_ratio = stock_data.get('current_volume', 0) / max(stock_data.get('volume_ma', 1), 1)
        if volume_ratio > 1.5:  # High volume day
            # Assume momentum continuation
            daily_change_pct = stock_data.get('daily_change_pct', 0)
            if daily_change_pct > 1:  # Positive momentum
                momentum_target = current_price * (1 + daily_change_pct/100 * 1.5)  # 1.5x momentum
                targets['aggressive'] = min(momentum_target, current_price * 1.20)  # Cap at 20%
                targets['method'] = 'volume_momentum'
                targets['confidence'] = 'LOW'  # Momentum is risky
                
        # Adjust timeframe based on volatility
        atr = stock_data.get('atr', 0)
        if atr > 0:
            volatility_pct = (atr / current_price) * 100
            if volatility_pct > 3:  # High volatility
                targets['timeframe_days'] = 45  # Longer timeframe
            elif volatility_pct < 1:  # Low volatility
                targets['timeframe_days'] = 21  # Shorter timeframe
                
        # Sanity checks
        max_reasonable_gain = current_price * 1.25  # 25% max
        min_reasonable_gain = current_price * 1.02  # 2% min
        
        for target_type in ['conservative', 'moderate', 'aggressive']:
            targets[target_type] = max(min_reasonable_gain, 
                                     min(targets[target_type], max_reasonable_gain))
        
        # Ensure proper ordering
        if targets['conservative'] > targets['moderate']:
            targets['conservative'] = targets['moderate'] * 0.95
        if targets['moderate'] > targets['aggressive']:
            targets['aggressive'] = targets['moderate'] * 1.05
            
        print(f"📊 {symbol} Targets: Conservative ${targets['conservative']:.2f}, "
              f"Moderate ${targets['moderate']:.2f}, Aggressive ${targets['aggressive']:.2f} "
              f"({targets['method']}, {targets['confidence']} confidence)")
              
    except Exception as e:
        print(f"⚠️ Error calculating targets for {symbol}: {e}")
        
    return targets

async def get_ai_price_forecast(stock_data: Dict, symbol: str, current_price: float, 
                              ai_trend_analysis: Dict, news_sentiment: Dict) -> Dict[str, Any]:
    """
    Get AI-powered price forecast combining technical and fundamental analysis.
    """
    try:
        # Build context for AI forecasting
        technical_analysis = analyze_technical_strength(stock_data)
        
        # Get news context
        news_data = news_sentiment.get(symbol, {})
        news_context = ""
        if news_data.get('has_news', False):
            sentiment = news_data.get('sentiment_label', 'NEUTRAL')
            news_context = f"Recent news sentiment: {sentiment}"
            if news_data.get('key_themes'):
                news_context += f" (themes: {', '.join(news_data['key_themes'][:2])})"
        
        forecast_prompt = f"""
        Provide a price forecast for {symbol} currently at ${current_price:.2f}.
        
        TECHNICAL ANALYSIS:
        - Technical Score: {technical_analysis.get('score', 5)}/10
        - Strength: {technical_analysis.get('strength', 'NEUTRAL')}
        - RSI: {stock_data.get('rsi', 50):.1f}
        - MACD Histogram: {stock_data.get('macd_histogram', 0):.3f}
        - Daily Change: {stock_data.get('daily_change_pct', 0):+.2f}%
        - Volume Ratio: {(stock_data.get('current_volume', 0) / max(stock_data.get('volume_ma', 1), 1)):.1f}x
        - Bollinger Bands: Upper ${stock_data.get('bb_upper', 0):.2f}, Lower ${stock_data.get('bb_lower', 0):.2f}
        
        AI TREND ANALYSIS:
        - Trend: {ai_trend_analysis.get('trend', 'NEUTRAL')}
        - Confidence: {ai_trend_analysis.get('confidence', 'LOW')}
        - Risk Level: {ai_trend_analysis.get('risk_level', 'MEDIUM')}
        
        {news_context}
        
        Based on this analysis, provide:
        1. Conservative target price (high probability, 2-4 weeks)
        2. Moderate target price (medium probability, 4-6 weeks)  
        3. Aggressive target price (lower probability, 6-8 weeks)
        4. Overall confidence (HIGH/MEDIUM/LOW)
        5. Key reasoning (2-3 sentences)
        
        Respond EXACTLY in this format:
        CONSERVATIVE: $X.XX
        MODERATE: $X.XX  
        AGGRESSIVE: $X.XX
        CONFIDENCE: [HIGH/MEDIUM/LOW]
        REASONING: [Brief explanation]
        """
        
        print(f"🤖 Getting AI price forecast for {symbol}...")
        response = await gemini_model.generate_content_async(forecast_prompt)
        ai_response = response.text.strip()
        
        # Parse AI response
        forecast = {
            'conservative': current_price * 1.05,
            'moderate': current_price * 1.08,
            'aggressive': current_price * 1.12,
            'confidence': 'LOW',
            'reasoning': 'AI parsing failed, using defaults',
            'method': 'ai_forecast'
        }
        
        try:
            lines = ai_response.split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith('CONSERVATIVE:'):
                    price_str = line.split('$')[1].strip()
                    forecast['conservative'] = float(price_str)
                elif line.startswith('MODERATE:'):
                    price_str = line.split('$')[1].strip()
                    forecast['moderate'] = float(price_str)
                elif line.startswith('AGGRESSIVE:'):
                    price_str = line.split('$')[1].strip()
                    forecast['aggressive'] = float(price_str)
                elif line.startswith('CONFIDENCE:'):
                    forecast['confidence'] = line.split(':')[1].strip()
                elif line.startswith('REASONING:'):
                    forecast['reasoning'] = line.split(':', 1)[1].strip()
                    
            print(f"✅ AI forecast for {symbol}: ${forecast['conservative']:.2f} / "
                  f"${forecast['moderate']:.2f} / ${forecast['aggressive']:.2f}")
                  
        except Exception as parse_error:
            print(f"⚠️ Could not parse AI forecast for {symbol}: {parse_error}")
            
        return forecast
        
    except Exception as e:
        print(f"❌ AI forecast error for {symbol}: {e}")
        return {
            'conservative': current_price * 1.03,
            'moderate': current_price * 1.06,
            'aggressive': current_price * 1.09,
            'confidence': 'LOW',
            'reasoning': f'AI forecast failed: {e}',
            'method': 'ai_forecast_error'
        }

def combine_price_forecasts(technical_targets: Dict, ai_forecast: Dict, symbol: str) -> Dict[str, Any]:
    """
    Combine technical and AI forecasts into final price targets.
    """
    try:
        # Weight the forecasts based on confidence
        tech_weight = 0.7 if technical_targets['confidence'] == 'HIGH' else 0.5 if technical_targets['confidence'] == 'MEDIUM' else 0.3
        ai_weight = 0.7 if ai_forecast['confidence'] == 'HIGH' else 0.5 if ai_forecast['confidence'] == 'MEDIUM' else 0.3
        
        # Normalize weights
        total_weight = tech_weight + ai_weight
        tech_weight = tech_weight / total_weight
        ai_weight = ai_weight / total_weight
        
        combined_forecast = {
            'conservative_target': (technical_targets['conservative'] * tech_weight + 
                                  ai_forecast['conservative'] * ai_weight),
            'moderate_target': (technical_targets['moderate'] * tech_weight + 
                              ai_forecast['moderate'] * ai_weight),
            'aggressive_target': (technical_targets['aggressive'] * tech_weight + 
                                ai_forecast['aggressive'] * ai_weight),
            'primary_target': 0,  # Will be set below
            'target_method': f"{technical_targets['method']} + {ai_forecast['method']}",
            'target_confidence': 'MEDIUM',  # Combined confidence
            'timeframe_days': technical_targets.get('timeframe_days', 30),
            'technical_reasoning': f"Technical: {technical_targets['method']} ({technical_targets['confidence']})",
            'ai_reasoning': ai_forecast.get('reasoning', 'AI analysis'),
            'stop_loss': 0,  # Will be calculated
            'risk_reward_ratio': 0  # Will be calculated
        }
        
        # Set primary target (moderate by default)
        combined_forecast['primary_target'] = combined_forecast['moderate_target']
        
        # Set combined confidence
        if technical_targets['confidence'] == 'HIGH' and ai_forecast['confidence'] == 'HIGH':
            combined_forecast['target_confidence'] = 'HIGH'
        elif technical_targets['confidence'] == 'LOW' and ai_forecast['confidence'] == 'LOW':
            combined_forecast['target_confidence'] = 'LOW'
        
        print(f"🎯 {symbol} Combined Target: ${combined_forecast['primary_target']:.2f} "
              f"({combined_forecast['target_confidence']} confidence)")
              
        return combined_forecast
        
    except Exception as e:
        print(f"❌ Error combining forecasts for {symbol}: {e}")
        return {
            'conservative_target': technical_targets['conservative'],
            'moderate_target': technical_targets['moderate'], 
            'aggressive_target': technical_targets['aggressive'],
            'primary_target': technical_targets['moderate'],
            'target_method': 'technical_only',
            'target_confidence': 'LOW',
            'timeframe_days': 30,
            'technical_reasoning': 'Forecast combination failed',
            'ai_reasoning': 'N/A',
            'stop_loss': 0,
            'risk_reward_ratio': 0
        }

async def generate_buy_forecast(symbol: str, current_price: float, stock_data: Dict, 
                              ai_trend_analysis: Dict, news_sentiment: Dict) -> Dict[str, Any]:
    """
    Main function to generate comprehensive buy forecast with price targets.
    """
    print(f"\n🎯 Generating price forecast for {symbol} at ${current_price:.2f}")
    
    try:
        # Get technical targets
        technical_targets = calculate_technical_price_targets(stock_data, current_price, symbol)
        
        # Get AI forecast
        ai_forecast = await get_ai_price_forecast(stock_data, symbol, current_price, 
                                                ai_trend_analysis, news_sentiment)
        
        # Combine forecasts
        combined_forecast = combine_price_forecasts(technical_targets, ai_forecast, symbol)
        
        # Calculate stop loss (2% below current price, or based on ATR)
        atr = stock_data.get('atr', current_price * 0.02)
        stop_loss_atr = current_price - (atr * 2)  # 2x ATR stop
        stop_loss_pct = current_price * 0.98  # 2% stop
        combined_forecast['stop_loss'] = max(stop_loss_atr, stop_loss_pct)  # Use more conservative
        
        # Calculate risk-reward ratio
        potential_gain = combined_forecast['primary_target'] - current_price
        potential_loss = current_price - combined_forecast['stop_loss']
        if potential_loss > 0:
            combined_forecast['risk_reward_ratio'] = potential_gain / potential_loss
        else:
            combined_forecast['risk_reward_ratio'] = 0
            
        # Add metadata
        combined_forecast.update({
            'symbol': symbol,
            'buy_price': current_price,
            'forecast_date': datetime.now().isoformat(),
            'status': 'active'
        })
        
        print(f"✅ {symbol} Forecast Complete:")
        print(f"   🎯 Target: ${combined_forecast['primary_target']:.2f}")
        print(f"   🛑 Stop Loss: ${combined_forecast['stop_loss']:.2f}")
        print(f"   ⚖️ Risk/Reward: {combined_forecast['risk_reward_ratio']:.2f}")
        print(f"   📅 Timeframe: {combined_forecast['timeframe_days']} days")
        
        return combined_forecast
        
    except Exception as e:
        print(f"❌ Error generating forecast for {symbol}: {e}")
        return {
            'symbol': symbol,
            'buy_price': current_price,
            'conservative_target': current_price * 1.05,
            'moderate_target': current_price * 1.08,
            'aggressive_target': current_price * 1.12,
            'primary_target': current_price * 1.08,
            'stop_loss': current_price * 0.98,
            'target_method': 'error_fallback',
            'target_confidence': 'LOW',
            'timeframe_days': 30,
            'risk_reward_ratio': 4.0,  # Default 8% gain / 2% loss
            'forecast_date': datetime.now().isoformat(),
            'status': 'active',
            'technical_reasoning': f'Error in forecast: {e}',
            'ai_reasoning': 'N/A'
        }