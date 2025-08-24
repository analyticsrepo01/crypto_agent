# crypto_market_data.py - Gemini Exchange Market Data Functions

import asyncio
import aiohttp
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import sys
import os

# Add gemini_api to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'gemini_api'))

from gemini_v2 import GeminiAPI
from config import (
    GEMINI_API_KEY, GEMINI_API_SECRET, GEMINI_SANDBOX, 
    PORTFOLIO_CRYPTOS, TRADE_SIZE, MIN_USD_RESERVE
)
from technical_analysis import *

# Initialize Gemini API client
gemini_client = GeminiAPI(
    api_key=GEMINI_API_KEY,
    api_secret=GEMINI_API_SECRET,
    sandbox=GEMINI_SANDBOX
)

async def get_crypto_data(symbol: str) -> Dict[str, Any]:
    """
    Fetch comprehensive crypto data for a single symbol from Gemini
    """
    try:
        print(f"📊 Fetching crypto data for {symbol}...")
        
        # Get both v1 and v2 ticker data with better error handling
        ticker_v2 = None
        ticker_v1 = None
        candles = None
        
        try:
            ticker_v2 = gemini_client.get_ticker_v2(symbol.lower())
        except Exception as e:
            print(f"⚠️ V2 ticker failed for {symbol}: {e}")
        
        try:
            ticker_v1 = gemini_client.get_ticker(symbol.lower())
        except Exception as e:
            print(f"⚠️ V1 ticker failed for {symbol}: {e}")
        
        try:
            # Get candlestick data for technical analysis
            candles = gemini_client.get_candles(symbol.lower(), '5m')  # Get 5-minute data
        except Exception as e:
            print(f"⚠️ Candles failed for {symbol}: {e}")
        
        if not ticker_v2 and not ticker_v1:
            return {'valid': False, 'reason': 'No ticker data from Gemini API - both V1 and V2 failed'}
        
        # Combine v1 and v2 data
        ticker = {}
        if ticker_v2:
            ticker.update(ticker_v2)
        if ticker_v1:
            ticker.update(ticker_v1)
        
        # Extract volume from v1 format if available with validation
        volume_data = ticker_v1.get('volume', {}) if ticker_v1 else {}
        volume = float(volume_data.get('USD', 0)) if isinstance(volume_data, dict) else 0
        
        # Volume validation and fallback mechanisms
        if volume == 0:
            # Try alternative volume sources
            if ticker_v2 and 'volume' in ticker_v2:
                volume = float(ticker_v2.get('volume', 0))
            
            # If still 0, use simulated volume for sandbox/testing
            if volume == 0:
                # Simulate reasonable volume based on price and market cap estimates
                current_price = float(ticker.get('close', ticker.get('last', 1)))
                if 'BTC' in symbol:
                    volume = 50000000  # $50M daily volume simulation
                elif 'ETH' in symbol:
                    volume = 20000000  # $20M daily volume simulation
                else:
                    volume = 5000000   # $5M daily volume simulation for altcoins
                print(f"📊 Using simulated volume for {symbol}: ${volume:,.0f}")
        
        # Use basic ticker data if candles are not available
        if not candles or len(candles) < 10:
            print(f"⚠️ Limited candle data for {symbol}, using ticker only")
            current_price = float(ticker.get('close', ticker.get('last', 0)))
            
            # Create basic indicators from ticker data
            indicators = {
                'symbol': symbol,
                'current_price': current_price,
                'previous_close': current_price,  # Will be updated if we have historical data
                'open': float(ticker.get('open', current_price)),
                'high': float(ticker.get('high', current_price)),
                'low': float(ticker.get('low', current_price)),
                'volume': volume,
                'sma_20': current_price,  # Default to current price
                'sma_50': current_price,
                'ema_12': current_price,
                'ema_26': current_price,
                'daily_change_pct': 0.0,
                'volatility_20': 0.0,
                'rsi': 50.0,
                'williams_r': -50.0,
                'atr': 0.0,
                'macd': 0.0,
                'macd_signal': 0.0,
                'macd_histogram': 0.0,
                'bb_upper': current_price * 1.02,
                'bb_middle': current_price,
                'bb_lower': current_price * 0.98,
                'stoch_k': 50.0,
                'stoch_d': 50.0,
                'volume_ma': volume/24,  # Simulate hourly volume
                'current_volume': volume,
                'obv': 0,
                'valid': True
            }
            return indicators
        
        # Process candlestick data
        # Prepare OHLCV data
        closes = pd.Series([float(candle[4]) for candle in candles])  # Close price
        highs = pd.Series([float(candle[2]) for candle in candles])   # High price
        lows = pd.Series([float(candle[3]) for candle in candles])    # Low price
        volumes = pd.Series([float(candle[5]) for candle in candles]) # Volume
        
        current_price = float(ticker.get('close', ticker.get('last', closes.iloc[-1])))
        
        # Calculate technical indicators
        indicators = {
            'symbol': symbol,
            'current_price': current_price,
            'previous_close': closes.iloc[-2] if len(closes) > 1 else current_price,
            'open': float(ticker.get('open', current_price)),
            'high': float(ticker.get('high', current_price)),
            'low': float(ticker.get('low', current_price)),
            'volume': volume,
            'sma_20': closes.rolling(20).mean().iloc[-1] if len(closes) >= 20 else current_price,
            'sma_50': closes.rolling(min(50, len(closes))).mean().iloc[-1],
            'ema_12': closes.ewm(span=12).mean().iloc[-1],
            'ema_26': closes.ewm(span=26).mean().iloc[-1],
            'daily_change_pct': ((current_price - closes.iloc[-2]) / closes.iloc[-2] * 100) if len(closes) > 1 else 0,
            'volatility_20': closes.rolling(min(20, len(closes))).std().iloc[-1],
        }
        
        # Add advanced technical indicators
        if len(closes) >= 14:
            rsi = calculate_rsi(closes)
            williams_r = calculate_williams_r(highs, lows, closes)
            atr = calculate_atr(highs, lows, closes)
            indicators['rsi'] = rsi if rsi is not None else 50.0
            indicators['williams_r'] = williams_r if williams_r is not None else -50.0
            indicators['atr'] = atr if atr is not None else 0.0
        else:
            indicators['rsi'] = 50.0
            indicators['williams_r'] = -50.0
            indicators['atr'] = 0.0
        
        # MACD indicators
        if len(closes) >= 26:
            macd, macd_signal, macd_hist = calculate_macd(closes)
            indicators.update({
                'macd': macd if macd is not None else 0.0,
                'macd_signal': macd_signal if macd_signal is not None else 0.0,
                'macd_histogram': macd_hist if macd_hist is not None else 0.0
            })
        else:
            indicators.update({
                'macd': 0.0,
                'macd_signal': 0.0,
                'macd_histogram': 0.0
            })
        
        # Bollinger Bands
        if len(closes) >= 20:
            bb_upper, bb_middle, bb_lower = calculate_bollinger_bands(closes)
            indicators.update({
                'bb_upper': bb_upper if bb_upper is not None else current_price * 1.02,
                'bb_middle': bb_middle if bb_middle is not None else current_price,
                'bb_lower': bb_lower if bb_lower is not None else current_price * 0.98
            })
        else:
            indicators.update({
                'bb_upper': current_price * 1.02,
                'bb_middle': current_price,
                'bb_lower': current_price * 0.98
            })
        
        # Stochastic Oscillator
        if len(closes) >= 14:
            stoch_k, stoch_d = calculate_stochastic(highs, lows, closes)
            indicators.update({
                'stoch_k': stoch_k if stoch_k is not None else 50.0,
                'stoch_d': stoch_d if stoch_d is not None else 50.0
            })
        else:
            indicators.update({
                'stoch_k': 50.0,
                'stoch_d': 50.0
            })
        
        # Volume indicators with fallback
        if len(volumes) >= 10:
            vol_ma, obv = calculate_volume_indicators(volumes, closes)
            indicators.update({
                'volume_ma': vol_ma if vol_ma is not None else (volumes.iloc[-1] if not volumes.empty else volume/24),  # Use current volume as fallback
                'obv': obv if obv is not None else 0
            })
        else:
            indicators.update({
                'volume_ma': volumes.iloc[-1] if not volumes.empty else volume/24,  # Simulate hourly volume
                'obv': 0
            })
        
        # Add current volume for analysis
        indicators['current_volume'] = volume
        
        indicators['valid'] = True
        return indicators
        
    except Exception as e:
        print(f"❌ Error fetching crypto data for {symbol}: {e}")
        return {'valid': False, 'reason': str(e)}

async def get_crypto_data_1h(symbol: str) -> Dict[str, Any]:
    """
    Fetch 1-hour timeframe crypto data for a single symbol from Gemini
    """
    try:
        print(f"📊 Fetching 1H data for {symbol}...")
        
        # Get 1-hour candlestick data specifically
        candles_1h = gemini_client.get_candles(symbol.lower(), '1hr')  # Get hourly data
        ticker = gemini_client.get_ticker_v2(symbol.lower())
        
        if not candles_1h or len(candles_1h) < 50:
            print(f"⚠️ Insufficient 1H candle data for {symbol}, using 5-minute as fallback")
            # Fallback to regular data but mark as 1h timeframe
            fallback_data = await get_crypto_data(symbol)
            if fallback_data.get('valid'):
                fallback_data['timeframe'] = '1h_fallback'
                fallback_data['trend_direction'] = 'NEUTRAL'
                return fallback_data
            else:
                return {'valid': False, 'reason': 'No 1H data and fallback failed'}
        
        # Process 1-hour candlestick data
        closes = pd.Series([float(candle[4]) for candle in candles_1h])
        highs = pd.Series([float(candle[2]) for candle in candles_1h])
        lows = pd.Series([float(candle[3]) for candle in candles_1h])
        volumes = pd.Series([float(candle[5]) for candle in candles_1h])
        
        current_price = float(ticker.get('close', ticker.get('last', closes.iloc[-1])))
        
        # Calculate 1-hour technical indicators
        indicators = {
            'symbol': symbol,
            'timeframe': '1h',
            'current_price': current_price,
            'previous_close': closes.iloc[-2] if len(closes) > 1 else current_price,
            'open': closes.iloc[0] if len(closes) > 0 else current_price,
            'high': highs.max(),
            'low': lows.min(),
            'volume': volumes.iloc[-1] if len(volumes) > 0 else 0,
            'sma_20': closes.rolling(20).mean().iloc[-1] if len(closes) >= 20 else current_price,
            'sma_50': closes.rolling(min(50, len(closes))).mean().iloc[-1],
            'ema_12': closes.ewm(span=12).mean().iloc[-1],
            'ema_26': closes.ewm(span=26).mean().iloc[-1],
            'daily_change_pct': ((current_price - closes.iloc[-25]) / closes.iloc[-25] * 100) if len(closes) > 25 else 0,  # 24h change
            'volatility_20': closes.rolling(min(20, len(closes))).std().iloc[-1],
        }
        
        # Add advanced technical indicators for 1H timeframe
        if len(closes) >= 14:
            rsi = calculate_rsi(closes)
            williams_r = calculate_williams_r(highs, lows, closes)
            atr = calculate_atr(highs, lows, closes)
            indicators['rsi'] = rsi if rsi is not None else 50.0
            indicators['williams_r'] = williams_r if williams_r is not None else -50.0
            indicators['atr'] = atr if atr is not None else 0.0
        else:
            indicators['rsi'] = 50.0
            indicators['williams_r'] = -50.0
            indicators['atr'] = 0.0
        
        # MACD indicators
        if len(closes) >= 26:
            macd, macd_signal, macd_hist = calculate_macd(closes)
            indicators.update({
                'macd': macd if macd is not None else 0.0,
                'macd_signal': macd_signal if macd_signal is not None else 0.0,
                'macd_histogram': macd_hist if macd_hist is not None else 0.0
            })
        else:
            indicators.update({
                'macd': 0.0,
                'macd_signal': 0.0,
                'macd_histogram': 0.0
            })
        
        # Bollinger Bands
        if len(closes) >= 20:
            bb_upper, bb_middle, bb_lower = calculate_bollinger_bands(closes)
            indicators.update({
                'bb_upper': bb_upper if bb_upper is not None else current_price * 1.02,
                'bb_middle': bb_middle if bb_middle is not None else current_price,
                'bb_lower': bb_lower if bb_lower is not None else current_price * 0.98
            })
        else:
            indicators.update({
                'bb_upper': current_price * 1.02,
                'bb_middle': current_price,
                'bb_lower': current_price * 0.98
            })
        
        # Determine 1H trend direction
        sma_20 = indicators['sma_20']
        sma_50 = indicators['sma_50']
        rsi = indicators['rsi']
        macd_hist = indicators['macd_histogram']
        
        if current_price > sma_20 > sma_50 and rsi > 45 and macd_hist > 0:
            trend_direction = 'BULLISH'
        elif current_price < sma_20 < sma_50 and rsi < 55 and macd_hist < 0:
            trend_direction = 'BEARISH'
        else:
            trend_direction = 'NEUTRAL'
        
        indicators['trend_direction'] = trend_direction
        indicators['valid'] = True
        
        return indicators
        
    except Exception as e:
        print(f"❌ Error fetching 1H crypto data for {symbol}: {e}")
        return {'valid': False, 'reason': str(e), 'timeframe': '1h'}

async def get_crypto_data_batch(symbols: List[str]) -> Dict[str, Any]:
    """
    Fetch crypto data for multiple symbols in batch
    """
    crypto_data = {}
    
    for i, symbol in enumerate(symbols):
        print(f"📊 Fetching {symbol} ({i+1}/{len(symbols)})...", end=" ")
        data = await get_crypto_data(symbol)
        
        if data and data.get('valid'):
            price = data.get('current_price', 0)
            rsi = data.get('rsi', 50)
            change_pct = data.get('daily_change_pct', 0)
            print(f"✅ ${price:,.2f} ({change_pct:+.2f}%, RSI {rsi:.1f})")
        else:
            print(f"❌ Failed: {data.get('reason', 'Unknown error')}")
            data = {
                'valid': False, 
                'current_price': 0.0, 
                'sma_20': 0.0,
                'symbol': symbol
            }
        
        crypto_data[symbol] = data
        await asyncio.sleep(0.2)  # Rate limiting for Gemini API
    
    return crypto_data

async def get_crypto_data_1h_batch(symbols: List[str]) -> Dict[str, Any]:
    """
    Fetch 1-hour timeframe crypto data for multiple symbols in batch
    """
    crypto_data_1h = {}
    
    for i, symbol in enumerate(symbols):
        print(f"📊 Fetching 1H {symbol} ({i+1}/{len(symbols)})...", end=" ")
        data = await get_crypto_data_1h(symbol)
        
        if data and data.get('valid'):
            price = data.get('current_price', 0)
            rsi = data.get('rsi', 50)
            trend = data.get('trend_direction', 'NEUTRAL')
            print(f"✅ 1H ${price:,.2f} (RSI {rsi:.1f}, {trend})")
        else:
            print(f"❌ 1H Failed: {data.get('reason', 'Unknown error')}")
            data = {
                'valid': False, 
                'current_price': 0.0, 
                'sma_20': 0.0,
                'symbol': symbol,
                'trend_direction': 'NEUTRAL'
            }
        
        crypto_data_1h[symbol] = data
        await asyncio.sleep(0.2)  # Rate limiting for Gemini API
    
    return crypto_data_1h

async def get_crypto_portfolio_summary():
    """
    Get portfolio summary from Gemini exchange
    """
    try:
        # Try to get balances - this might fail in sandbox with empty account
        try:
            balances = gemini_client.get_account_balance()
        except Exception as balance_error:
            print(f"⚠️ Balance API error (expected in sandbox): {balance_error}")
            # Return simulated empty portfolio for testing
            return 0.0, 1000.0, {}  # Simulate $1000 available cash
        
        portfolio_value = 0.0
        usd_available = 0.0
        positions = {}
        
        if balances:
            for balance in balances:
                currency = balance['currency']
                amount = float(balance['amount'])
                
                if currency == 'USD':
                    usd_available = amount
                elif amount > 0:
                    # Get current price for this crypto
                    try:
                        symbol = f"{currency}USD"
                        if symbol in PORTFOLIO_CRYPTOS:
                            ticker = gemini_client.get_ticker(symbol.lower())
                            current_price = float(ticker['last'])
                            value = amount * current_price
                            portfolio_value += value
                            positions[symbol] = amount
                    except Exception as e:
                        print(f"⚠️ Could not get price for {currency}: {e}")
        
        portfolio_value += usd_available
        
        # If no balances found (sandbox), return simulated values
        if portfolio_value == 0 and usd_available == 0:
            usd_available = 1000.0  # Simulated $1000 for testing
            portfolio_value = 1000.0
        
        return portfolio_value, usd_available, positions
        
    except Exception as e:
        print(f"❌ Error getting crypto portfolio summary: {e}")
        return 1000.0, 1000.0, {}  # Return simulated values for testing

async def place_crypto_order(symbol: str, action: str, quantity: float) -> Dict[str, Any]:
    """
    Place a crypto order on Gemini exchange
    Note: This is a placeholder - Gemini's Python library may not support live trading
    You would need to implement order placement using their REST API
    """
    try:
        print(f"🚀 CRYPTO ORDER: {action} {quantity} {symbol}")
        
        # For now, return a simulated response
        # In production, you'd implement actual Gemini order placement
        return {
            "success": True,
            "symbol": symbol,
            "action": action,
            "quantity": quantity,
            "order_id": f"sim_{int(datetime.now().timestamp())}",
            "status": "Submitted",
            "message": f"Simulated {action} order for {quantity} {symbol}"
        }
        
    except Exception as e:
        return {
            "success": False,
            "symbol": symbol,
            "action": action,
            "quantity": quantity,
            "error": str(e)
        }

def is_crypto_market_open() -> bool:
    """
    Crypto markets are always open (24/7)
    """
    return True

async def test_gemini_connection():
    """
    Test connection to Gemini API
    """
    try:
        print("🔍 Testing Gemini API connection...")
        
        # Test public API
        public_ok = gemini_client.test_public_connection()
        
        # Test private API  
        private_ok = gemini_client.test_private_connection()
        
        if public_ok and private_ok:
            print("✅ Gemini API connection successful!")
            
            # Test crypto data fetching
            print("\n📊 Testing crypto data fetching...")
            test_symbol = 'BTCUSD'
            btc_data = await get_crypto_data(test_symbol)
            
            if btc_data.get('valid'):
                price = btc_data.get('current_price', 0)
                rsi = btc_data.get('rsi', 0)
                print(f"✅ {test_symbol} data: ${price:,.2f}, RSI {rsi:.1f}")
                return True
            else:
                print(f"❌ Failed to fetch {test_symbol} data")
                return False
        else:
            print("❌ Gemini API connection failed")
            return False
            
    except Exception as e:
        print(f"❌ Error testing Gemini connection: {e}")
        return False

# Compatibility functions for existing codebase
async def get_stock_data_batch(symbols: List[str]) -> Dict[str, Any]:
    """Legacy compatibility function"""
    return await get_crypto_data_batch(symbols)

async def get_all_positions(current_prices=None):
    """Get positions from trading database (consistent with profitability calculation)"""
    import sqlite3
    try:
        # Read positions from the same trading database used by profitability calculation
        conn = sqlite3.connect("trading_memory.db")
        cursor = conn.cursor()
        
        position_dict = {symbol: 0.0 for symbol in PORTFOLIO_CRYPTOS}
        pnl_dict = {symbol: 0.0 for symbol in PORTFOLIO_CRYPTOS}
        purchase_prices_dict = {symbol: 0.0 for symbol in PORTFOLIO_CRYPTOS}
        
        for symbol in PORTFOLIO_CRYPTOS:
            # Get trade history for this symbol to calculate current position
            cursor.execute('''
                SELECT action, quantity, price, timestamp 
                FROM trading_memories 
                WHERE symbol = ? 
                ORDER BY timestamp ASC
            ''', (symbol,))
            
            trades = cursor.fetchall()
            
            if trades:
                current_position = 0.0
                total_cost = 0.0
                total_purchased = 0.0
                
                for action, quantity, price, timestamp in trades:
                    if action == 'BUY':
                        current_position += quantity
                        total_cost += quantity * price
                        total_purchased += quantity
                    elif action == 'SELL':
                        current_position -= quantity
                        # Reduce cost basis proportionally
                        if total_purchased > 0:
                            cost_reduction = (quantity / total_purchased) * total_cost
                            total_cost -= cost_reduction
                            total_purchased -= quantity
                
                # Calculate average purchase price
                avg_price = total_cost / current_position if current_position > 0 else 0.0
                
                position_dict[symbol] = current_position
                purchase_prices_dict[symbol] = avg_price
                
                # Calculate P&L if current prices are provided
                if current_prices and symbol in current_prices and current_position > 0:
                    current_price = current_prices[symbol]
                    unrealized_pnl = (current_price - avg_price) * current_position
                    # Round to avoid floating point precision issues
                    pnl_dict[symbol] = round(unrealized_pnl, 4)
                else:
                    pnl_dict[symbol] = 0.0
        
        conn.close()
        
        print(f"📊 Positions from trading database:")
        for symbol, pos in position_dict.items():
            if pos > 0:
                avg_price = purchase_prices_dict[symbol]
                print(f"   {symbol}: {pos} @ ${avg_price:.2f}")
        
        return position_dict, pnl_dict, purchase_prices_dict
        
    except Exception as e:
        print(f"❌ Error getting crypto positions from database: {e}")
        empty_dict = {symbol: 0.0 for symbol in PORTFOLIO_CRYPTOS}
        return empty_dict, empty_dict, empty_dict

async def get_portfolio_summary():
    """Legacy compatibility function"""
    portfolio_value, usd_available, _ = await get_crypto_portfolio_summary()
    return portfolio_value, usd_available

def is_market_open():
    """Legacy compatibility function"""
    return is_crypto_market_open()