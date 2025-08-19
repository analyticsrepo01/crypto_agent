# /trading_bot/agent.py

from typing import Dict, List
from config import gemini_model, STOP_LOSS_PERCENTAGE, TAKE_PROFIT_PERCENTAGE, PORTFOLIO_STOP_LOSS, TRADE_SIZE, MIN_CASH_RESERVE, MAX_TOTAL_SHARES, MAX_SHARES_PER_STOCK, PORTFOLIO_STOCKS

# Define a type alias for state for clarity
PortfolioState = Dict 


def validate_ai_decisions(state: PortfolioState) -> Dict:
    """
    Validates the AI's recommendations. Logic is adjusted based on the trading mode.
    """
    recommendations = state.get('ai_recommendations', {})
    ai_trends = state.get('ai_trend_analysis', {})
    aggressive_mode = state.get('aggressive_mode', False)
    issues = []
    
    if not recommendations:
        return {'decision': 'proceed', 'reason': 'No recommendations to validate.'}

    for symbol, rec in recommendations.items():
        action = rec.get('action', 'HOLD')
        trend_info = ai_trends.get(symbol, {})
        ai_trend = trend_info.get('trend', 'NEUTRAL')
        ai_confidence = trend_info.get('confidence', 'LOW')
        ai_risk = trend_info.get('risk_level', 'HIGH')
        
        if action == 'BUY' and ai_trend == 'BEARISH' and ai_confidence in ['MEDIUM', 'HIGH']:
            issues.append(f"{symbol}: Contradictory signal - Recommending BUY on a BEARISH trend.")
            
        if action == 'SELL' and ai_trend == 'BULLISH' and ai_confidence in ['MEDIUM', 'HIGH']:
            issues.append(f"{symbol}: Contradictory signal - Recommending SELL on a BULLISH trend.")

        # --- MODIFIED VALIDATION FOR AGGRESSIVE MODE ---
        # This check is skipped in aggressive mode to allow for higher-risk plays.
        if not aggressive_mode and action == 'BUY' and rec.get('priority') == 'HIGH' and ai_risk == 'HIGH':
            issues.append(f"{symbol}: High-risk action - High-priority BUY on a stock assessed with HIGH risk.")

    buy_sell_actions = [rec.get('action') for rec in recommendations.values() if rec.get('action') in ['BUY', 'SELL']]
    # In aggressive mode, allow trading up to 90% of the portfolio at once.
    churn_limit = 0.9 if aggressive_mode else 0.7 
    if len(buy_sell_actions) > (len(PORTFOLIO_STOCKS) * churn_limit):
        issues.append(f"Portfolio: Excessive activity suggested ({len(buy_sell_actions)} trades).")

    if issues:
        return {'decision': 'rerun', 'reason': "Validation failed. Issues found: " + ", ".join(issues)}
    
    return {'decision': 'proceed', 'reason': 'AI decisions are logically consistent.'}



def should_rerun_or_proceed(state: PortfolioState) -> str:
    """
    Checks the last validation result to decide the next step in the graph.
    """
    if not state.get('validation_history'):
        return "proceed_to_execute" # Should not happen, but as a safeguard
        
    last_validation = state['validation_history'][-1]
    if last_validation['decision'] == 'rerun':
        return "rerun_decision"
    return "proceed_to_execute"

async def get_ai_trend_analysis(stock_data: Dict, symbol: str) -> Dict:
    """
    Get AI-powered trend analysis for a single stock based on all technical indicators.
    """
    indicators = stock_data.get(symbol, {})
    if not indicators.get('valid', False):
        return {'trend': 'NEUTRAL', 'confidence': 'LOW', 'reasoning': 'Insufficient data', 'risk_level': 'HIGH'}

    # Create a detailed prompt for the AI
    context = f"""
    Analyze the technical indicators for {symbol} to determine the trend, strength, confidence, and risk.
    - Current Price: ${indicators.get('current_price', 0):.2f}
    - SMA 20/50: ${indicators.get('sma_20', 0):.2f} / ${indicators.get('sma_50', 0):.2f}
    - RSI (14): {indicators.get('rsi', 50):.1f}
    - MACD Histogram: {indicators.get('macd_histogram', 0):.3f}
    - Bollinger Bands: Price is near {'Upper' if indicators.get('current_price', 0) > indicators.get('bb_upper', 0) else 'Lower' if indicators.get('current_price', 0) < indicators.get('bb_lower', 0) else 'Middle'} band.
    - Volume vs MA: {'Above' if indicators.get('current_volume', 0) > indicators.get('volume_ma', 0) else 'Below'} average.

    Respond in this EXACT format:
    TREND: [BULLISH/BEARISH/NEUTRAL]
    CONFIDENCE: [HIGH/MEDIUM/LOW]
    REASONING: [Brief explanation]
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
        return analysis
    except Exception as e:
        print(f"❌ AI trend analysis error for {symbol}: {e}")
        return {'trend': 'NEUTRAL', 'confidence': 'LOW', 'reasoning': f'AI error: {e}', 'risk_level': 'HIGH'}



async def get_ai_portfolio_recommendations(state: PortfolioState):
    """
    Gets AI recommendations. The prompt is adjusted based on the trading mode.
    """
    portfolio_summary = []
    for symbol in PORTFOLIO_STOCKS:
        s_data = state['stock_data'].get(symbol, {})
        t_analysis = state['ai_trend_analysis'].get(symbol, {})
        pos = state['positions'].get(symbol, 0)
        if s_data.get('valid', False):
            portfolio_summary.append(
                f"{symbol} (Position: {pos} shares): "
                f"Price ${s_data.get('current_price', 0):.2f}, "
                f"RSI {s_data.get('rsi', 50):.1f}, "
                f"AI Trend: {t_analysis.get('trend', 'N/A')} ({t_analysis.get('confidence', 'N/A')})"
            )
    
    # --- DYNAMIC PROMPT BASED ON TRADING STRATEGY ---
    strategy_instruction = ""
    if state.get('aggressive_mode', False):
        strategy_instruction = "Your primary goal is to MAXIMIZE PROFIT. You should prioritize high-conviction trades, even if they carry higher risk. Be more decisive in entering and exiting positions to capture short-term gains."
    else:
        strategy_instruction = "Your primary goal is balanced growth. Prioritize capital preservation and make trades based on strong technical signals with moderate to high confidence."

    context = f"""
    You are an expert quantitative trading analyst. {strategy_instruction}
    
    Portfolio State:
    - Total Value: ${state['total_portfolio_value']:.2f}
    - P&L: ${state['total_unrealized_pnl']:+.2f}
    - Cash: ${state['cash_available']:.2f}

    Stock Analysis Summary:
    {'; '.join(portfolio_summary)}

    Constraints:
    - Trade size: {TRADE_SIZE} shares.
    - Max shares per stock: {MAX_SHARES_PER_STOCK}.

    For each stock, provide a recommendation in this EXACT format, one per line:
    STOCK: [SYMBOL] | ACTION: [BUY/SELL/HOLD] | PRIORITY: [HIGH/MEDIUM/LOW] | REASONING: [Brief reason] | TECHNICAL_SCORE: [1-10]
    """
    
    feedback = state.get("validation_feedback")
    if feedback:
        context += f"""
        CRITICAL REVISION REQUEST: Your previous recommendations were rejected. Address these issues: "{feedback}"
        Provide a new set of recommendations that resolves these contradictions.
        """
    
    try:
        response = await gemini_model.generate_content_async(context)
        ai_response = response.text
        
        print("\n--- RAW AI RESPONSE ---")
        print(ai_response)
        print("-----------------------\n")

        recommendations = {}
        # ... (robust parsing logic remains the same) ...
        for line in ai_response.split('\n'):
            line = line.strip()
            if not line or '|' not in line:
                continue

            rec = {}
            symbol = None
            
            if line.startswith("STOCK:"):
                parts = [p.strip() for p in line.split('|')]
                for part in parts:
                    if ':' in part:
                        key, value = part.split(':', 1)
                        clean_key = key.strip().lower().replace(' ', '_')
                        if clean_key == 'stock':
                            symbol = value.strip()
                        else:
                            rec[clean_key] = value.strip()
            else:
                try:
                    first_part = line.split('|')[0].strip()
                    if first_part in PORTFOLIO_STOCKS:
                        symbol = first_part
                        parts = [p.strip() for p in line.split('|')]
                        for part in parts[1:]:
                             if ':' in part:
                                key, value = part.split(':', 1)
                                clean_key = key.strip().lower().replace(' ', '_')
                                rec[clean_key] = value.strip()
                    else:
                        potential_symbol = line.split(':')[0].strip()
                        if potential_symbol in PORTFOLIO_STOCKS:
                            symbol = potential_symbol
                            parts = [p.strip() for p in line.split('|')]
                            for part in parts:
                                if ':' in part:
                                    key, value = part.split(':', 1)
                                    clean_key = key.strip().lower().replace(' ', '_')
                                    if clean_key != symbol.lower():
                                        rec[clean_key] = value.strip()
                except:
                    continue

            if symbol and symbol in PORTFOLIO_STOCKS:
                if 'technical_score' in rec:
                    try:
                        rec['technical_score'] = float(rec['technical_score'])
                    except (ValueError, TypeError):
                        rec['technical_score'] = 5.0
                recommendations[symbol] = rec

        return recommendations

    except Exception as e:
        print(f"❌ AI portfolio recommendation error: {e}")
        return {s: {'action': 'HOLD', 'priority': 'LOW', 'reasoning': 'AI Error'} for s in PORTFOLIO_STOCKS}
        
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
    value = state.get('total_portfolio_value', 1) # Avoid division by zero
    if pnl < 0 and value > 0:
        loss_pct = (pnl / value) * 100
        if loss_pct <= PORTFOLIO_STOP_LOSS:
            print(f"🚨 EMERGENCY PORTFOLIO STOP: Total loss at {loss_pct:.2f}%")
            return True
    return False
