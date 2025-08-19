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
        
        # Get both v1 and v2 ticker data
        ticker_v2 = gemini_client.get_ticker_v2(symbol.lower())
        ticker_v1 = gemini_client.get_ticker(symbol.lower())
        
        # Get candlestick data for technical analysis
        candles = gemini_client.get_candles(symbol.lower(), '1hr')
        
        if not ticker_v2 and not ticker_v1:
            return {'valid': False, 'reason': 'No ticker data from Gemini API'}
        
        # Combine v1 and v2 data
        ticker = {}
        if ticker_v2:
            ticker.update(ticker_v2)
        if ticker_v1:
            ticker.update(ticker_v1)
        
        # Extract volume from v1 format if available
        volume_data = ticker_v1.get('volume', {}) if ticker_v1 else {}
        volume = float(volume_data.get('USD', 0)) if isinstance(volume_data, dict) else 0
        
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
                'volume_ma': volume,
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
            indicators['rsi'] = calculate_rsi(closes)
            indicators['williams_r'] = calculate_williams_r(highs, lows, closes)
            indicators['atr'] = calculate_atr(highs, lows, closes)
        else:
            indicators['rsi'] = 50.0
            indicators['williams_r'] = -50.0
            indicators['atr'] = 0.0
        
        # MACD indicators
        if len(closes) >= 26:
            macd, macd_signal, macd_hist = calculate_macd(closes)
            indicators.update({
                'macd': macd,
                'macd_signal': macd_signal,
                'macd_histogram': macd_hist
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
                'bb_upper': bb_upper,
                'bb_middle': bb_middle,
                'bb_lower': bb_lower
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
                'stoch_k': stoch_k,
                'stoch_d': stoch_d
            })
        else:
            indicators.update({
                'stoch_k': 50.0,
                'stoch_d': 50.0
            })
        
        # Volume indicators
        if len(volumes) >= 10:
            vol_ma, obv = calculate_volume_indicators(volumes, closes)
            indicators.update({
                'volume_ma': vol_ma,
                'obv': obv
            })
        else:
            indicators.update({
                'volume_ma': volumes.iloc[-1] if not volumes.empty else 1000,
                'obv': 0
            })
        
        indicators['valid'] = True
        return indicators
        
    except Exception as e:
        print(f"❌ Error fetching crypto data for {symbol}: {e}")
        return {'valid': False, 'reason': str(e)}

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

async def get_crypto_portfolio_summary():
    """
    Get portfolio summary from Gemini exchange
    """
    try:
        balances = gemini_client.get_account_balance()
        
        portfolio_value = 0.0
        usd_available = 0.0
        positions = {}
        
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
        
        return portfolio_value, usd_available, positions
        
    except Exception as e:
        print(f"❌ Error getting crypto portfolio summary: {e}")
        return 0.0, 0.0, {}

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

async def get_all_positions():
    """Legacy compatibility function"""
    try:
        portfolio_value, usd_available, positions = await get_crypto_portfolio_summary()
        
        # Convert to expected format
        position_dict = {symbol: 0.0 for symbol in PORTFOLIO_CRYPTOS}
        pnl_dict = {symbol: 0.0 for symbol in PORTFOLIO_CRYPTOS}
        purchase_prices_dict = {symbol: 0.0 for symbol in PORTFOLIO_CRYPTOS}
        
        for symbol, amount in positions.items():
            if symbol in position_dict:
                position_dict[symbol] = amount
                # P&L calculation would need historical cost basis
                # For now, set to 0
                pnl_dict[symbol] = 0.0
                purchase_prices_dict[symbol] = 0.0
        
        return position_dict, pnl_dict, purchase_prices_dict
        
    except Exception as e:
        print(f"❌ Error getting crypto positions: {e}")
        empty_dict = {symbol: 0.0 for symbol in PORTFOLIO_CRYPTOS}
        return empty_dict, empty_dict, empty_dict

async def get_portfolio_summary():
    """Legacy compatibility function"""
    portfolio_value, usd_available, _ = await get_crypto_portfolio_summary()
    return portfolio_value, usd_available

def is_market_open():
    """Legacy compatibility function"""
    return is_crypto_market_open()