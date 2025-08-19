# /trading_bot/backtest_enhancements.py

"""
Enhanced backtesting functions and utilities for the trading agent.
This module provides advanced backtesting capabilities including:
- Historical data management
- Enhanced portfolio simulation
- Performance analytics
- Risk management
- Backtesting reports
"""

import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import sqlite3
import json
from pathlib import Path

from config import PORTFOLIO_STOCKS, TRADE_SIZE, MIN_CASH_RESERVE, TRADING_FEE_PER_TRADE

class BacktestPortfolio:
    """Enhanced portfolio simulation for backtesting"""
    
    def __init__(self, initial_cash: float = 10000.0, start_date: str = None):
        self.initial_cash = initial_cash
        self.cash = initial_cash
        self.positions = {symbol: 0 for symbol in PORTFOLIO_STOCKS}
        self.purchase_prices = {symbol: 0.0 for symbol in PORTFOLIO_STOCKS}
        self.trade_history = []
        self.portfolio_values = []
        self.start_date = start_date or datetime.now().isoformat()
        self.total_fees_paid = 0.0
        self.max_portfolio_value = initial_cash
        self.max_drawdown = 0.0
        
    def execute_trade(self, symbol: str, action: str, quantity: int, price: float, 
                     timestamp: str, reasoning: str = "") -> Dict:
        """Execute a simulated trade with enhanced tracking"""
        
        if action == 'BUY':
            cost = quantity * price + TRADING_FEE_PER_TRADE
            
            if self.cash >= cost:
                # Update portfolio
                old_position = self.positions[symbol]
                old_avg_price = self.purchase_prices[symbol]
                
                # Calculate new average cost
                if old_position > 0:
                    total_cost = (old_position * old_avg_price) + (quantity * price)
                    new_position = old_position + quantity
                    new_avg_price = total_cost / new_position
                else:
                    new_avg_price = price
                    new_position = quantity
                
                self.positions[symbol] = new_position
                self.purchase_prices[symbol] = new_avg_price
                self.cash -= cost
                self.total_fees_paid += TRADING_FEE_PER_TRADE
                
                # Record trade
                trade_record = {
                    'timestamp': timestamp,
                    'symbol': symbol,
                    'action': action,
                    'quantity': quantity,
                    'price': price,
                    'cost': cost,
                    'fee': TRADING_FEE_PER_TRADE,
                    'cash_after': self.cash,
                    'position_after': new_position,
                    'avg_cost_after': new_avg_price,
                    'reasoning': reasoning,
                    'success': True
                }
                
                self.trade_history.append(trade_record)
                return trade_record
            else:
                # Insufficient funds
                return {
                    'timestamp': timestamp,
                    'symbol': symbol,
                    'action': action,
                    'quantity': quantity,
                    'price': price,
                    'error': 'Insufficient funds',
                    'cash_available': self.cash,
                    'cost_required': cost,
                    'success': False
                }
                
        elif action == 'SELL':
            if self.positions[symbol] >= quantity:
                proceeds = quantity * price - TRADING_FEE_PER_TRADE
                
                # Update portfolio
                self.positions[symbol] -= quantity
                self.cash += proceeds
                self.total_fees_paid += TRADING_FEE_PER_TRADE
                
                # If position is now zero, reset average price
                if self.positions[symbol] == 0:
                    original_avg = self.purchase_prices[symbol]
                    self.purchase_prices[symbol] = 0.0
                    realized_pnl = quantity * (price - original_avg) - TRADING_FEE_PER_TRADE
                else:
                    realized_pnl = quantity * (price - self.purchase_prices[symbol]) - TRADING_FEE_PER_TRADE
                
                # Record trade
                trade_record = {
                    'timestamp': timestamp,
                    'symbol': symbol,
                    'action': action,
                    'quantity': quantity,
                    'price': price,
                    'proceeds': proceeds,
                    'fee': TRADING_FEE_PER_TRADE,
                    'realized_pnl': realized_pnl,
                    'cash_after': self.cash,
                    'position_after': self.positions[symbol],
                    'reasoning': reasoning,
                    'success': True
                }
                
                self.trade_history.append(trade_record)
                return trade_record
            else:
                # Insufficient shares
                return {
                    'timestamp': timestamp,
                    'symbol': symbol,
                    'action': action,
                    'quantity': quantity,
                    'price': price,
                    'error': 'Insufficient shares',
                    'shares_available': self.positions[symbol],
                    'shares_required': quantity,
                    'success': False
                }
    
    def update_portfolio_value(self, stock_prices: Dict[str, float], timestamp: str):
        """Update portfolio value with current market prices"""
        stock_value = sum(self.positions[symbol] * stock_prices.get(symbol, 0) 
                         for symbol in PORTFOLIO_STOCKS)
        total_value = stock_value + self.cash
        
        # Track maximum value for drawdown calculation
        if total_value > self.max_portfolio_value:
            self.max_portfolio_value = total_value
        
        # Calculate current drawdown
        current_drawdown = (self.max_portfolio_value - total_value) / self.max_portfolio_value * 100
        if current_drawdown > self.max_drawdown:
            self.max_drawdown = current_drawdown
        
        # Calculate P&L for each position
        position_pnls = {}
        for symbol in PORTFOLIO_STOCKS:
            if self.positions[symbol] > 0 and self.purchase_prices[symbol] > 0:
                current_price = stock_prices.get(symbol, 0)
                unrealized_pnl = self.positions[symbol] * (current_price - self.purchase_prices[symbol])
                position_pnls[symbol] = unrealized_pnl
            else:
                position_pnls[symbol] = 0.0
        
        portfolio_record = {
            'timestamp': timestamp,
            'cash': self.cash,
            'stock_value': stock_value,
            'total_value': total_value,
            'total_return_pct': ((total_value - self.initial_cash) / self.initial_cash) * 100,
            'total_fees_paid': self.total_fees_paid,
            'max_drawdown': self.max_drawdown,
            'positions': dict(self.positions),
            'position_pnls': position_pnls,
            'total_unrealized_pnl': sum(position_pnls.values())
        }
        
        self.portfolio_values.append(portfolio_record)
        return portfolio_record

    def get_performance_summary(self) -> Dict:
        """Generate comprehensive performance summary"""
        if not self.portfolio_values:
            return {"error": "No portfolio data available"}
        
        latest = self.portfolio_values[-1]
        total_trades = len([t for t in self.trade_history if t.get('success', False)])
        winning_trades = len([t for t in self.trade_history 
                            if t.get('success', False) and t.get('realized_pnl', 0) > 0])
        
        # Calculate returns over time
        returns = []
        for i, record in enumerate(self.portfolio_values):
            if i == 0:
                daily_return = 0
            else:
                prev_value = self.portfolio_values[i-1]['total_value']
                current_value = record['total_value']
                daily_return = (current_value - prev_value) / prev_value * 100 if prev_value > 0 else 0
            returns.append(daily_return)
        
        return {
            'initial_cash': self.initial_cash,
            'final_value': latest['total_value'],
            'total_return': latest['total_return_pct'],
            'total_return_dollars': latest['total_value'] - self.initial_cash,
            'max_drawdown': self.max_drawdown,
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'win_rate': (winning_trades / total_trades * 100) if total_trades > 0 else 0,
            'total_fees_paid': self.total_fees_paid,
            'sharpe_ratio': np.std(returns) != 0 and np.mean(returns) / np.std(returns) or 0,
            'volatility': np.std(returns),
            'final_cash': latest['cash'],
            'final_stock_value': latest['stock_value'],
            'active_positions': sum(1 for pos in latest['positions'].values() if pos > 0),
            'best_position': max(latest['position_pnls'].items(), key=lambda x: x[1]) if latest['position_pnls'] else None,
            'worst_position': min(latest['position_pnls'].items(), key=lambda x: x[1]) if latest['position_pnls'] else None
        }

class BacktestDataManager:
    """Manages historical data for backtesting"""
    
    def __init__(self, data_source: str = "yfinance"):
        self.data_source = data_source
        self.data_cache = {}
        
    async def fetch_historical_data(self, symbols: List[str], 
                                  start_date: datetime, 
                                  end_date: datetime,
                                  interval: str = "5m") -> Dict[str, pd.DataFrame]:
        """Fetch historical data for backtesting"""
        
        if self.data_source == "yfinance":
            return await self._fetch_yfinance_data(symbols, start_date, end_date, interval)
        elif self.data_source == "local_api":
            return await self._fetch_local_api_data(symbols, start_date, end_date, interval)
        else:
            raise ValueError(f"Unsupported data source: {self.data_source}")
    
    async def _fetch_yfinance_data(self, symbols: List[str], 
                                 start_date: datetime, 
                                 end_date: datetime,
                                 interval: str = "5m") -> Dict[str, pd.DataFrame]:
        """Fetch data from Yahoo Finance"""
        import yfinance as yf
        
        print(f"📊 Fetching historical data from Yahoo Finance...")
        print(f"   📅 Period: {start_date.date()} to {end_date.date()}")
        print(f"   📈 Symbols: {symbols}")
        print(f"   ⏰ Interval: {interval}")
        
        data_dict = {}
        
        for symbol in symbols:
            try:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(
                    start=start_date.date(),
                    end=end_date.date(),
                    interval=interval,
                    auto_adjust=True,
                    prepost=True
                )
                
                if not hist.empty:
                    # Standardize column names
                    hist.columns = [col.lower() for col in hist.columns]
                    data_dict[symbol] = hist
                    print(f"   ✅ {symbol}: {len(hist)} data points")
                else:
                    print(f"   ❌ {symbol}: No data available")
                    data_dict[symbol] = pd.DataFrame()
                    
            except Exception as e:
                print(f"   ❌ {symbol}: Error - {e}")
                data_dict[symbol] = pd.DataFrame()
                
        return data_dict
    
    async def _fetch_local_api_data(self, symbols: List[str], 
                                  start_date: datetime, 
                                  end_date: datetime,
                                  interval: str = "5m") -> Dict[str, pd.DataFrame]:
        """Fetch data from local API server"""
        import aiohttp
        
        print(f"📊 Fetching historical data from local API...")
        data_dict = {}
        
        async with aiohttp.ClientSession() as session:
            for symbol in symbols:
                try:
                    url = f"http://127.0.0.1:8085/historical_prices/{symbol}"
                    params = {
                        "start_date": start_date.isoformat(),
                        "end_date": end_date.isoformat(),
                        "timeframe": interval
                    }
                    
                    async with session.get(url, params=params) as response:
                        if response.status == 200:
                            data = await response.json()
                            if data:
                                df = pd.DataFrame(data)
                                if not df.empty:
                                    # Convert timestamp to datetime index
                                    if 'timestamp' in df.columns:
                                        df['timestamp'] = pd.to_datetime(df['timestamp'])
                                        df.set_index('timestamp', inplace=True)
                                    data_dict[symbol] = df
                                    print(f"   ✅ {symbol}: {len(df)} data points")
                                else:
                                    print(f"   ❌ {symbol}: Empty response")
                                    data_dict[symbol] = pd.DataFrame()
                            else:
                                print(f"   ❌ {symbol}: No data in response")
                                data_dict[symbol] = pd.DataFrame()
                        else:
                            print(f"   ❌ {symbol}: HTTP {response.status}")
                            data_dict[symbol] = pd.DataFrame()
                            
                except Exception as e:
                    print(f"   ❌ {symbol}: Error - {e}")
                    data_dict[symbol] = pd.DataFrame()
                    
        return data_dict

async def run_enhanced_backtest(symbols: List[str], 
                              start_date: datetime,
                              end_date: datetime,
                              initial_cash: float = 10000.0,
                              strategy_function = None,
                              data_source: str = "yfinance",
                              interval: str = "5m") -> Dict:
    """
    Run an enhanced backtest with comprehensive analytics
    
    Args:
        symbols: List of stock symbols to trade
        start_date: Backtest start date
        end_date: Backtest end date
        initial_cash: Starting cash amount
        strategy_function: Trading strategy function (optional)
        data_source: Data source ("yfinance" or "local_api")
        interval: Data interval
    
    Returns:
        Comprehensive backtest results
    """
    
    print(f"🚀 Starting Enhanced Backtest")
    print(f"   📅 Period: {start_date.date()} to {end_date.date()}")
    print(f"   💰 Initial Cash: ${initial_cash:,.2f}")
    print(f"   📊 Symbols: {symbols}")
    print(f"   📈 Data Source: {data_source}")
    
    # Initialize components
    portfolio = BacktestPortfolio(initial_cash, start_date.isoformat())
    data_manager = BacktestDataManager(data_source)
    
    # Fetch historical data
    historical_data = await data_manager.fetch_historical_data(
        symbols, start_date, end_date, interval
    )
    
    # Validate data availability
    valid_symbols = [symbol for symbol, df in historical_data.items() 
                    if not df.empty and len(df) > 20]
    
    if not valid_symbols:
        return {
            "error": "No valid historical data available for any symbols",
            "symbols_requested": symbols,
            "data_availability": {symbol: len(df) for symbol, df in historical_data.items()}
        }
    
    print(f"   ✅ Valid data for {len(valid_symbols)}/{len(symbols)} symbols")
    
    # Determine date range from available data
    min_dates = []
    max_dates = []
    for symbol in valid_symbols:
        df = historical_data[symbol]
        min_dates.append(df.index.min())
        max_dates.append(df.index.max())
    
    actual_start = max(min_dates) if min_dates else start_date
    actual_end = min(max_dates) if max_dates else end_date
    
    print(f"   📅 Actual backtest period: {actual_start.date()} to {actual_end.date()}")
    
    # Run backtest simulation
    backtest_results = {
        'config': {
            'symbols': symbols,
            'valid_symbols': valid_symbols,
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'actual_start': actual_start.isoformat(),
            'actual_end': actual_end.isoformat(),
            'initial_cash': initial_cash,
            'data_source': data_source,
            'interval': interval
        },
        'portfolio': portfolio,
        'historical_data': historical_data,
        'data_summary': {
            symbol: {
                'data_points': len(df),
                'start_date': df.index.min().isoformat() if not df.empty else None,
                'end_date': df.index.max().isoformat() if not df.empty else None,
                'has_data': not df.empty
            } for symbol, df in historical_data.items()
        }
    }
    
    print(f"✅ Enhanced backtest setup complete")
    return backtest_results

def generate_backtest_report(backtest_results: Dict, output_dir: str = "backtest_reports") -> str:
    """Generate comprehensive backtest report"""
    
    if 'error' in backtest_results:
        return f"Backtest failed: {backtest_results['error']}"
    
    portfolio = backtest_results['portfolio']
    config = backtest_results['config']
    performance = portfolio.get_performance_summary()
    
    # Create output directory
    Path(output_dir).mkdir(exist_ok=True)
    
    # Generate timestamp for report
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_filename = f"{output_dir}/backtest_report_{timestamp}.html"
    
    # HTML report content
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Enhanced Backtest Report - {timestamp}</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            .header {{ background: #f4f4f4; padding: 20px; border-radius: 5px; }}
            .section {{ margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }}
            .metric {{ display: inline-block; margin: 10px; padding: 10px; background: #f9f9f9; border-radius: 3px; }}
            .positive {{ color: green; }}
            .negative {{ color: red; }}
            table {{ border-collapse: collapse; width: 100%; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #f2f2f2; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🚀 Enhanced Backtest Report</h1>
            <p><strong>Generated:</strong> {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
            <p><strong>Period:</strong> {config['actual_start'][:10]} to {config['actual_end'][:10]}</p>
            <p><strong>Symbols:</strong> {', '.join(config['valid_symbols'])}</p>
        </div>

        <div class="section">
            <h2>📊 Performance Summary</h2>
            <div class="metric">
                <strong>Initial Cash:</strong> ${performance['initial_cash']:,.2f}
            </div>
            <div class="metric">
                <strong>Final Value:</strong> ${performance['final_value']:,.2f}
            </div>
            <div class="metric">
                <strong>Total Return:</strong> 
                <span class="{'positive' if performance['total_return'] > 0 else 'negative'}">
                    {performance['total_return']:+.2f}%
                </span>
            </div>
            <div class="metric">
                <strong>Total Return ($):</strong>
                <span class="{'positive' if performance['total_return_dollars'] > 0 else 'negative'}">
                    ${performance['total_return_dollars']:+,.2f}
                </span>
            </div>
            <div class="metric">
                <strong>Max Drawdown:</strong> 
                <span class="negative">{performance['max_drawdown']:.2f}%</span>
            </div>
            <div class="metric">
                <strong>Total Trades:</strong> {performance['total_trades']}
            </div>
            <div class="metric">
                <strong>Win Rate:</strong> {performance['win_rate']:.1f}%
            </div>
            <div class="metric">
                <strong>Total Fees:</strong> ${performance['total_fees_paid']:.2f}
            </div>
        </div>

        <div class="section">
            <h2>📈 Risk Metrics</h2>
            <div class="metric">
                <strong>Sharpe Ratio:</strong> {performance['sharpe_ratio']:.3f}
            </div>
            <div class="metric">
                <strong>Volatility:</strong> {performance['volatility']:.2f}%
            </div>
            <div class="metric">
                <strong>Active Positions:</strong> {performance['active_positions']}
            </div>
        </div>

        <div class="section">
            <h2>🎯 Best/Worst Positions</h2>
            <p><strong>Best Position:</strong> {performance['best_position'][0] if performance['best_position'] else 'N/A'} 
               (${performance['best_position'][1]:+,.2f} P&L) if performance['best_position'] else ''</p>
            <p><strong>Worst Position:</strong> {performance['worst_position'][0] if performance['worst_position'] else 'N/A'} 
               (${performance['worst_position'][1]:+,.2f} P&L) if performance['worst_position'] else ''</p>
        </div>

        <div class="section">
            <h2>📋 Recent Trades</h2>
            <table>
                <tr>
                    <th>Timestamp</th>
                    <th>Symbol</th>
                    <th>Action</th>
                    <th>Quantity</th>
                    <th>Price</th>
                    <th>P&L</th>
                </tr>
    """
    
    # Add recent trades to table
    recent_trades = portfolio.trade_history[-10:] if len(portfolio.trade_history) > 10 else portfolio.trade_history
    for trade in recent_trades:
        if trade.get('success', False):
            pnl = trade.get('realized_pnl', 0)
            pnl_class = 'positive' if pnl > 0 else 'negative' if pnl < 0 else ''
            html_content += f"""
                <tr>
                    <td>{trade['timestamp'][:19]}</td>
                    <td>{trade['symbol']}</td>
                    <td>{trade['action']}</td>
                    <td>{trade['quantity']}</td>
                    <td>${trade['price']:.2f}</td>
                    <td class="{pnl_class}">${pnl:+.2f}</td>
                </tr>
            """
    
    html_content += """
            </table>
        </div>
    </body>
    </html>
    """
    
    # Write report to file
    with open(report_filename, 'w') as f:
        f.write(html_content)
    
    print(f"📝 Backtest report generated: {report_filename}")
    return report_filename

# Enhanced backtest-specific helper functions for use in the main notebook

async def get_enhanced_backtest_data_batch(symbols: List[str], 
                                         interval: str = '5min',
                                         days_back: int = 5) -> Dict:
    """
    Enhanced version of get_backtest_data_batch with better error handling and caching
    """
    if not BACKTEST_MODE:
        print("⚠️ Enhanced backtest data should only be used in BACKTEST_MODE=True")
        return {}
    
    print(f"📊 Fetching enhanced backtest data for {len(symbols)} symbols...")
    
    # Use the existing data manager but with better error handling
    data_manager = BacktestDataManager("local_api")  # Try local API first
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back)
    
    try:
        historical_data = await data_manager.fetch_historical_data(
            symbols, start_date, end_date, interval
        )
        
        # Transform to expected format
        stock_data = {}
        for symbol in symbols:
            df = historical_data.get(symbol, pd.DataFrame())
            
            if not df.empty and len(df) > 10:
                # Calculate technical indicators
                closes = df['close'] if 'close' in df.columns else df.get('Close', pd.Series())
                
                if not closes.empty:
                    current_price = closes.iloc[-1]
                    
                    stock_data[symbol] = {
                        'valid': True,
                        'current_price': current_price,
                        'previous_close': closes.iloc[-2] if len(closes) > 1 else current_price,
                        'sma_20': closes.rolling(min(20, len(closes))).mean().iloc[-1],
                        'sma_50': closes.rolling(min(50, len(closes))).mean().iloc[-1],
                        'volume': df['volume'].iloc[-1] if 'volume' in df.columns else 1000,
                        'data_points': len(df),
                        'source': 'enhanced_backtest'
                    }
                    print(f"   ✅ {symbol}: ${current_price:.2f} ({len(df)} data points)")
                else:
                    stock_data[symbol] = {'valid': False, 'reason': f'No price data available'}
                    print(f"   ❌ {symbol}: No price data")
            else:
                stock_data[symbol] = {'valid': False, 'reason': f'Insufficient data ({len(df)} points)'}
                print(f"   ❌ {symbol}: Insufficient data")
        
        return stock_data
        
    except Exception as e:
        print(f"❌ Enhanced backtest data fetch failed: {e}")
        print("🔄 Falling back to yfinance...")
        
        # Fallback to yfinance
        try:
            data_manager = BacktestDataManager("yfinance")
            historical_data = await data_manager.fetch_historical_data(
                symbols, start_date, end_date, "5m"
            )
            
            stock_data = {}
            for symbol in symbols:
                df = historical_data.get(symbol, pd.DataFrame())
                
                if not df.empty:
                    closes = df['close']
                    current_price = closes.iloc[-1]
                    
                    stock_data[symbol] = {
                        'valid': True,
                        'current_price': current_price,
                        'previous_close': closes.iloc[-2] if len(closes) > 1 else current_price,
                        'sma_20': closes.rolling(min(20, len(closes))).mean().iloc[-1],
                        'volume': df['volume'].iloc[-1] if 'volume' in df.columns else 1000,
                        'source': 'yfinance_fallback'
                    }
                else:
                    stock_data[symbol] = {'valid': False, 'reason': 'No data from yfinance'}
            
            return stock_data
            
        except Exception as fallback_error:
            print(f"❌ Yfinance fallback also failed: {fallback_error}")
            return {symbol: {'valid': False, 'reason': 'All data sources failed'} for symbol in symbols}

# Global BACKTEST_MODE flag for this module
BACKTEST_MODE = True

print("✅ Enhanced backtesting module loaded successfully!")