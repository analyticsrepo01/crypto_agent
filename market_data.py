# /trading_bot/market_data.py

import asyncio
import pandas as pd
from typing import List, Dict
import sqlite3
from datetime import datetime, timedelta
import aiohttp

# Import crypto-specific functions
from crypto_market_data import (
    get_crypto_data_batch, get_crypto_portfolio_summary, 
    place_crypto_order, is_crypto_market_open,
    get_all_positions as get_crypto_positions,
    get_portfolio_summary as get_crypto_portfolio_summary
)

# Legacy imports for backward compatibility
try:
    from ib_insync import Stock, MarketOrder
    from utils import ensure_connection
    IBKR_AVAILABLE = True
except ImportError:
    print("⚠️ IBKR not available, using crypto-only mode")
    IBKR_AVAILABLE = False

from technical_analysis import *
from config import PORTFOLIO_STOCKS, PORTFOLIO_CRYPTOS

async def get_comprehensive_stock_data(symbol: str) -> Dict:
    """
    Fetches historical data for a single stock and calculates a comprehensive
    set of technical indicators using 5-minute data.
    """
    try:
        ib = await ensure_connection()
        if not ib:
            return {'valid': False, 'reason': 'No IB connection'}

        contract = Stock(symbol, 'SMART', 'USD')
        qualified_contracts = await ib.qualifyContractsAsync(contract)
        if not qualified_contracts:
            return {'valid': False, 'reason': 'Contract could not be qualified'}

        bars = await ib.reqHistoricalDataAsync(
            qualified_contracts[0], '', '3 D', '5 mins', 'MIDPOINT', True, 1
        )        
        if not bars or len(bars) < 50:
            return {'valid': False, 'reason': 'Insufficient historical data'}

        df = pd.DataFrame(bars)
        opens, highs, lows, closes, volumes = df['open'], df['high'], df['low'], df['close'], df['volume']
        current_price = closes.iloc[-1]

        indicators = {
            'current_price': current_price,
            'previous_close': closes.iloc[-2] if len(closes) > 1 else current_price,
            'sma_20': closes.rolling(20).mean().iloc[-1],
            'sma_50': closes.rolling(50).mean().iloc[-1],
            'ema_12': closes.ewm(span=12).mean().iloc[-1],
            'ema_26': closes.ewm(span=26).mean().iloc[-1],
            'rsi': calculate_rsi(closes),
            'williams_r': calculate_williams_r(highs, lows, closes),
            'atr': calculate_atr(highs, lows, closes),
            'current_volume': volumes.iloc[-1],
            'daily_change_pct': ((current_price - closes.iloc[-2]) / closes.iloc[-2] * 100) if len(closes) > 1 else 0,
            'volatility_20': closes.rolling(20).std().iloc[-1],
        }
        
        # MACD indicators
        macd, macd_signal, macd_hist = calculate_macd(closes)
        indicators.update({'macd': macd, 'macd_signal': macd_signal, 'macd_histogram': macd_hist})

        # Bollinger Bands
        bb_upper, bb_middle, bb_lower = calculate_bollinger_bands(closes)
        indicators.update({'bb_upper': bb_upper, 'bb_middle': bb_middle, 'bb_lower': bb_lower})

        # Stochastic Oscillator
        stoch_k, stoch_d = calculate_stochastic(highs, lows, closes)
        indicators.update({'stoch_k': stoch_k, 'stoch_d': stoch_d})
        
        # Volume indicators
        vol_ma, obv = calculate_volume_indicators(volumes, closes)
        indicators.update({'volume_ma': vol_ma, 'obv': obv})

        # Additional technical indicators
        indicators['std_dev'] = calculate_std_dev(closes)
        indicators['ad_line'] = calculate_ad_line(highs, lows, closes, volumes)
        indicators['pvt'] = calculate_pvt(closes, volumes)
        indicators['parabolic_sar'] = calculate_parabolic_sar(highs, lows)
        indicators['demarker'] = calculate_demarker(highs, lows)
        
        # ADX and Directional Movement
        adx, plus_di, minus_di = calculate_adx(highs, lows, closes)
        indicators.update({'adx': adx, 'plus_di': plus_di, 'minus_di': minus_di})
        
        # Moving Average Envelopes
        ma_upper, ma_middle, ma_lower = calculate_moving_average_envelopes(closes)
        indicators.update({'ma_env_upper': ma_upper, 'ma_env_middle': ma_middle, 'ma_env_lower': ma_lower})

        # Final validity check
        indicators['valid'] = len([v for v in indicators.values() if v is not None]) > 10
        return indicators

    except Exception as e:
        print(f"❌ Error getting comprehensive data for {symbol}: {e}")
        return {'valid': False, 'reason': str(e)}

async def get_comprehensive_stock_data_1h(symbol: str) -> Dict:
    """
    Fetches historical data for a single stock and calculates a comprehensive
    set of technical indicators using 1-hour data for longer-term perspective.
    """
    try:
        ib = await ensure_connection()
        if not ib:
            return {'valid': False, 'reason': 'No IB connection'}

        contract = Stock(symbol, 'SMART', 'USD')
        qualified_contracts = await ib.qualifyContractsAsync(contract)
        if not qualified_contracts:
            return {'valid': False, 'reason': 'Contract could not be qualified'}

        bars = await ib.reqHistoricalDataAsync(
            qualified_contracts[0], '', '3 D', '1 hour', 'MIDPOINT', True, 1
        )        
        if not bars or len(bars) < 20:
            return {'valid': False, 'reason': 'Insufficient historical data'}

        df = pd.DataFrame(bars)
        opens, highs, lows, closes, volumes = df['open'], df['high'], df['low'], df['close'], df['volume']
        current_price = closes.iloc[-1]

        indicators = {
            'current_price': current_price,
            'previous_close': closes.iloc[-2] if len(closes) > 1 else current_price,
            'sma_20': closes.rolling(20).mean().iloc[-1] if len(closes) >= 20 else closes.rolling(len(closes)).mean().iloc[-1],
            'sma_50': closes.rolling(min(50, len(closes))).mean().iloc[-1],
            'ema_12': closes.ewm(span=12).mean().iloc[-1],
            'ema_26': closes.ewm(span=26).mean().iloc[-1],
            'rsi': calculate_rsi(closes),
            'williams_r': calculate_williams_r(highs, lows, closes),
            'atr': calculate_atr(highs, lows, closes),
            'current_volume': volumes.iloc[-1],
            'daily_change_pct': ((current_price - closes.iloc[-2]) / closes.iloc[-2] * 100) if len(closes) > 1 else 0,
            'volatility_20': closes.rolling(min(20, len(closes))).std().iloc[-1],
        }
        
        # MACD indicators
        macd, macd_signal, macd_hist = calculate_macd(closes)
        indicators.update({'macd': macd, 'macd_signal': macd_signal, 'macd_histogram': macd_hist})

        # Bollinger Bands
        bb_upper, bb_middle, bb_lower = calculate_bollinger_bands(closes)
        indicators.update({'bb_upper': bb_upper, 'bb_middle': bb_middle, 'bb_lower': bb_lower})

        # Stochastic Oscillator
        stoch_k, stoch_d = calculate_stochastic(highs, lows, closes)
        indicators.update({'stoch_k': stoch_k, 'stoch_d': stoch_d})
        
        # Volume indicators
        vol_ma, obv = calculate_volume_indicators(volumes, closes)
        indicators.update({'volume_ma': vol_ma, 'obv': obv})

        # Additional technical indicators
        indicators['std_dev'] = calculate_std_dev(closes)
        indicators['ad_line'] = calculate_ad_line(highs, lows, closes, volumes)
        indicators['pvt'] = calculate_pvt(closes, volumes)
        indicators['parabolic_sar'] = calculate_parabolic_sar(highs, lows)
        indicators['demarker'] = calculate_demarker(highs, lows)
        
        # ADX and Directional Movement
        adx, plus_di, minus_di = calculate_adx(highs, lows, closes)
        indicators.update({'adx': adx, 'plus_di': plus_di, 'minus_di': minus_di})
        
        # Moving Average Envelopes
        ma_upper, ma_middle, ma_lower = calculate_moving_average_envelopes(closes)
        indicators.update({'ma_env_upper': ma_upper, 'ma_env_middle': ma_middle, 'ma_env_lower': ma_lower})

        # Final validity check
        indicators['valid'] = len([v for v in indicators.values() if v is not None]) > 10
        return indicators

    except Exception as e:
        print(f"❌ Error getting 1-hour data for {symbol}: {e}")
        return {'valid': False, 'reason': str(e)}

async def get_stock_data_batch(symbols: List[str]) -> Dict:
    """
    Route to crypto data fetching for Gemini exchange
    """
    return await get_crypto_data_batch(symbols)

async def get_stock_data_batch_1h(symbols: List[str]) -> Dict:
    """
    Fetches comprehensive technical data for a list of stock symbols in a batch using 1-hour data.
    """
    stock_data = {}
    for i, symbol in enumerate(symbols):
        print(f"📊 Fetching 1hr data for {symbol} ({i+1}/{len(symbols)})...", end=" ")
        data = await get_comprehensive_stock_data_1h(symbol)
        if data and data['valid']:
            price = data.get('current_price', 0)
            rsi = data.get('rsi', 50)
            print(f"✅ Success: Price ${price:.2f}, RSI {rsi:.1f}")
        else:
            print(f"❌ Failed: {data.get('reason', 'Unknown error')}")
            data = {'valid': False, 'current_price': 0.0, 'sma_20': 0.0} # Default empty data
        stock_data[symbol] = data
        await asyncio.sleep(0.5) # Rate limit to avoid overwhelming the API
    return stock_data


# In market_data.py
async def get_all_positions():
    """
    Route to crypto positions from Gemini exchange
    """
    return await get_crypto_positions()
        

async def get_portfolio_summary():
    """
    Route to crypto portfolio summary from Gemini exchange
    """
    return await get_crypto_portfolio_summary()

async def place_smart_order(symbol: str, action: str, quantity: float):
    """
    Route to crypto order placement on Gemini exchange
    """
    return await place_crypto_order(symbol, action, quantity)


# In market_data.py

async def get_backtest_data_batch(symbols: List[str], interval: str = '5min') -> Dict:
    """
    Fetches backtest data from the local API server for a list of stock symbols.
    Uses the correct API endpoints and transforms data to match expected structure.
    """
    print(f"📡 Fetching {interval} backtest data from local API...")
    stock_data = {}
    
    # Define a reasonable date range for backtesting (using known good dates)
    # Use fixed recent dates that we know have data in the system
    end_date = datetime(2025, 8, 15, 20, 0, 0)
    start_date = datetime(2025, 8, 15, 4, 0, 0)
    
    async def fetch_single_symbol(symbol):
        try:
            # Use the correct API endpoint for historical prices
            url = f"http://127.0.0.1:8085/historical_prices/{symbol}"
            params = {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "timeframe": interval
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    response.raise_for_status()
                    api_data = await response.json()
                    
                    # Transform API response to match expected structure
                    if api_data and len(api_data) > 0:
                        # Convert to pandas DataFrame for technical analysis
                        df = pd.DataFrame(api_data)
                        
                        # Ensure we have the required columns
                        if 'close' in df.columns and len(df) > 10:
                            closes = df['close']
                            highs = df['high'] if 'high' in df.columns else closes
                            lows = df['low'] if 'low' in df.columns else closes
                            volumes = df['volume'] if 'volume' in df.columns else pd.Series([1000] * len(df))
                            
                            current_price = closes.iloc[-1]
                            
                            # Calculate basic technical indicators to match expected structure
                            transformed_data = {
                                'valid': True,
                                'current_price': current_price,
                                'previous_close': closes.iloc[-2] if len(closes) > 1 else current_price,
                                'sma_20': closes.rolling(min(20, len(closes))).mean().iloc[-1],
                                'sma_50': closes.rolling(min(50, len(closes))).mean().iloc[-1],
                                'ema_12': closes.ewm(span=12).mean().iloc[-1],
                                'ema_26': closes.ewm(span=26).mean().iloc[-1],
                                'rsi': calculate_rsi(closes) if len(closes) >= 14 else 50.0,
                                'williams_r': calculate_williams_r(highs, lows, closes) if len(closes) >= 14 else -50.0,
                                'atr': calculate_atr(highs, lows, closes) if len(closes) >= 14 else 0.0,
                                'current_volume': volumes.iloc[-1],
                                'daily_change_pct': ((current_price - closes.iloc[-2]) / closes.iloc[-2] * 100) if len(closes) > 1 else 0,
                                'volatility_20': closes.rolling(min(20, len(closes))).std().iloc[-1],
                            }
                            
                            # Add MACD indicators if we have enough data
                            if len(closes) >= 26:
                                macd, macd_signal, macd_hist = calculate_macd(closes)
                                transformed_data.update({
                                    'macd': macd,
                                    'macd_signal': macd_signal,
                                    'macd_histogram': macd_hist
                                })
                            else:
                                transformed_data.update({
                                    'macd': 0.0,
                                    'macd_signal': 0.0,
                                    'macd_histogram': 0.0
                                })
                            
                            # Add Bollinger Bands if we have enough data
                            if len(closes) >= 20:
                                bb_upper, bb_middle, bb_lower = calculate_bollinger_bands(closes)
                                transformed_data.update({
                                    'bb_upper': bb_upper,
                                    'bb_middle': bb_middle,
                                    'bb_lower': bb_lower
                                })
                            else:
                                transformed_data.update({
                                    'bb_upper': current_price * 1.02,
                                    'bb_middle': current_price,
                                    'bb_lower': current_price * 0.98
                                })
                            
                            # Add Stochastic if we have enough data
                            if len(closes) >= 14:
                                stoch_k, stoch_d = calculate_stochastic(highs, lows, closes)
                                transformed_data.update({
                                    'stoch_k': stoch_k,
                                    'stoch_d': stoch_d
                                })
                            else:
                                transformed_data.update({
                                    'stoch_k': 50.0,
                                    'stoch_d': 50.0
                                })
                            
                            return symbol, transformed_data
                        else:
                            return symbol, {'valid': False, 'reason': 'Insufficient data columns or length'}
                    else:
                        return symbol, {'valid': False, 'reason': 'No data returned from API'}
                        
        except Exception as e:
            print(f"❌ Error fetching backtest data for {symbol}: {e}")
            return symbol, {'valid': False, 'reason': str(e)}

    # Fetch data for all symbols in parallel
    tasks = [fetch_single_symbol(symbol) for symbol in symbols]
    results = await asyncio.gather(*tasks)

    for symbol, data in results:
        if data and data.get('valid'):
            price = data.get('current_price', 0)
            rsi = data.get('rsi', 50)
            print(f"✅ {symbol}: Price ${price:.2f}, RSI {rsi:.1f}")
        else:
            print(f"❌ Failed for {symbol}: {data.get('reason', 'Unknown error')}")
            data = {'valid': False, 'current_price': 0.0, 'sma_20': 0.0}
        stock_data[symbol] = data

    return stock_data

async def get_backtest_data_batch_1h(symbols: List[str]) -> Dict:
    """
    Fetches 1-hour backtest data from the local API server for a list of stock symbols.
    """
    return await get_backtest_data_batch(symbols, interval='1h')

def is_market_open():
    """
    Route to crypto market status (always open)
    """
    return is_crypto_market_open()

def calculate_portfolio_profitability(current_stock_data: Dict, db_path: str = "trading_memory.db", backtest_mode: bool = False) -> Dict:
    """
    Calculate current profitability based on stored trades and current market prices.
    
    Args:
        current_stock_data: Dict containing current stock data with 'current_price' for each symbol
        db_path: Path to the SQLite database containing trade history
        backtest_mode: Whether to use backtest database (adds _backtest suffix to db_path)
    
    Returns:
        Dict containing profitability metrics for the portfolio
    """
    try:
        # Use backtest database if in backtest mode
        if backtest_mode:
            if db_path == "trading_memory.db":  # Default path
                actual_db_path = "trading_memory_backtest.db"
            else:
                # Add _backtest suffix to custom path
                path_parts = db_path.split('.')
                if len(path_parts) > 1:
                    actual_db_path = '.'.join(path_parts[:-1]) + '_backtest.' + path_parts[-1]
                else:
                    actual_db_path = db_path + '_backtest'
        else:
            actual_db_path = db_path
            
        conn = sqlite3.connect(actual_db_path)
        cursor = conn.cursor()
        
        # Get all trades for each symbol
        profitability_data = {}
        total_realized_pnl = 0
        total_unrealized_pnl = 0
        total_investment = 0
        
        for symbol in PORTFOLIO_STOCKS:
            # Get trade history for this symbol
            cursor.execute('''
                SELECT action, quantity, price, timestamp 
                FROM trading_memories 
                WHERE symbol = ? 
                ORDER BY timestamp ASC
            ''', (symbol,))
            
            trades = cursor.fetchall()
            
            if not trades:
                profitability_data[symbol] = {
                    'position': 0,
                    'avg_cost': 0,
                    'total_invested': 0,
                    'current_value': 0,
                    'unrealized_pnl': 0,
                    'unrealized_pnl_pct': 0,
                    'realized_pnl': 0
                }
                continue
            
            # Calculate position and average cost
            current_position = 0
            total_cost = 0
            realized_pnl = 0
            
            for action, quantity, price, timestamp in trades:
                if action == 'BUY':
                    current_position += quantity
                    total_cost += quantity * price
                elif action == 'SELL':
                    if current_position > 0:
                        # Calculate realized P&L for sold shares
                        avg_cost_per_share = total_cost / current_position if current_position > 0 else 0
                        realized_pnl += quantity * (price - avg_cost_per_share)
                        
                        # Reduce position and cost basis proportionally
                        position_reduction_ratio = quantity / current_position
                        total_cost -= total_cost * position_reduction_ratio
                        current_position -= quantity
            
            # Calculate unrealized P&L based on current market price
            # First try to get from stock data, then fall back to direct price if available
            stock_info = current_stock_data.get(symbol, {})
            current_price = stock_info.get('current_price', 0)
            
            # If price is 0 or missing, skip this symbol in P&L calculation but include in data
            if current_price == 0:
                print(f"⚠️ No current price data for {symbol} in profitability calculation")
            avg_cost_per_share = total_cost / current_position if current_position > 0 else 0
            current_value = current_position * current_price
            unrealized_pnl = current_value - total_cost
            unrealized_pnl_pct = (unrealized_pnl / total_cost * 100) if total_cost > 0 else 0
            
            profitability_data[symbol] = {
                'position': current_position,
                'avg_cost': avg_cost_per_share,
                'total_invested': total_cost,
                'current_value': current_value,
                'unrealized_pnl': unrealized_pnl,
                'unrealized_pnl_pct': unrealized_pnl_pct,
                'realized_pnl': realized_pnl,
                'current_price': current_price
            }
            
            # Add to totals
            total_realized_pnl += realized_pnl
            total_unrealized_pnl += unrealized_pnl
            total_investment += total_cost
        
        conn.close()
        
        # Calculate portfolio-level metrics
        total_current_value = sum(data['current_value'] for data in profitability_data.values())
        
        # Add manual realized profit adjustment (e.g., for missing historical profits)
        manual_realized_profit = 7.22  # Previously realized profit not captured in trading_memories
        total_realized_pnl += manual_realized_profit
        
        total_pnl = total_realized_pnl + total_unrealized_pnl
        total_pnl_pct = (total_pnl / total_investment * 100) if total_investment > 0 else 0
        
        return {
            'individual_stocks': profitability_data,
            'portfolio_summary': {
                'total_investment': total_investment,
                'total_current_value': total_current_value,
                'total_realized_pnl': total_realized_pnl,
                'total_unrealized_pnl': total_unrealized_pnl,
                'total_pnl': total_pnl,
                'total_pnl_pct': total_pnl_pct,
                'calculation_timestamp': datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        print(f"❌ Error calculating portfolio profitability: {e}")
        return {
            'individual_stocks': {symbol: {
                'position': 0, 'avg_cost': 0, 'total_invested': 0,
                'current_value': 0, 'unrealized_pnl': 0, 'unrealized_pnl_pct': 0,
                'realized_pnl': 0, 'current_price': 0
            } for symbol in PORTFOLIO_STOCKS},
            'portfolio_summary': {
                'total_investment': 0, 'total_current_value': 0,
                'total_realized_pnl': 0, 'total_unrealized_pnl': 0,
                'total_pnl': 0, 'total_pnl_pct': 0,
                'calculation_timestamp': datetime.now().isoformat(),
                'error': str(e)
            }
        }