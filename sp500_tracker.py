# /trading_bot/sp500_tracker.py

import asyncio
import yfinance as yf
from datetime import datetime, timedelta
from typing import Dict, Optional
import sqlite3
import json

class SP500Tracker:
    """Track S&P 500 performance for portfolio comparison"""
    
    def __init__(self, db_path="trading_data.db"):
        self.db_path = db_path
        self.sp500_symbol = "^GSPC"  # S&P 500 index symbol
        self.init_sp500_table()
    
    def init_sp500_table(self):
        """Initialize S&P 500 tracking table"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sp500_tracking (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                trading_date TEXT,
                cycle_number INTEGER,
                session_id TEXT,
                sp500_price REAL,
                sp500_change_pct REAL,
                sp500_open REAL,
                sp500_high REAL,
                sp500_low REAL,
                sp500_volume INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Add benchmark tracking table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS benchmark_comparison (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trading_date TEXT,
                session_id TEXT,
                portfolio_start_value REAL,
                portfolio_current_value REAL,
                portfolio_return_pct REAL,
                sp500_start_price REAL,
                sp500_current_price REAL,
                sp500_return_pct REAL,
                alpha REAL,
                outperformance REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    async def get_sp500_data(self) -> Dict:
        """Fetch current S&P 500 data"""
        try:
            # Get S&P 500 data
            sp500 = yf.Ticker(self.sp500_symbol)
            
            # Get current data
            info = sp500.info
            hist = sp500.history(period="2d")  # Get 2 days to calculate change
            
            if len(hist) >= 2:
                current_price = hist['Close'].iloc[-1]
                previous_close = hist['Close'].iloc[-2]
                change_pct = ((current_price - previous_close) / previous_close) * 100
                
                return {
                    'success': True,
                    'price': current_price,
                    'change_pct': change_pct,
                    'open': hist['Open'].iloc[-1],
                    'high': hist['High'].iloc[-1],
                    'low': hist['Low'].iloc[-1],
                    'volume': hist['Volume'].iloc[-1],
                    'previous_close': previous_close,
                    'timestamp': datetime.now().isoformat()
                }
            else:
                return {'success': False, 'error': 'Insufficient historical data'}
                
        except Exception as e:
            print(f"⚠️ Failed to fetch S&P 500 data: {e}")
            return {'success': False, 'error': str(e)}
    
    def log_sp500_data(self, state: Dict, sp500_data: Dict):
        """Log S&P 500 data to database"""
        if not sp500_data.get('success'):
            return
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO sp500_tracking 
            (timestamp, trading_date, cycle_number, session_id, sp500_price, 
             sp500_change_pct, sp500_open, sp500_high, sp500_low, sp500_volume)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            datetime.now().isoformat(),
            datetime.now().strftime('%Y-%m-%d'),
            state.get('cycle_number', 0),
            state.get('session_id', ''),
            sp500_data['price'],
            sp500_data['change_pct'],
            sp500_data['open'],
            sp500_data['high'],
            sp500_data['low'],
            sp500_data['volume']
        ))
        
        conn.commit()
        conn.close()
    
    def calculate_benchmark_comparison(self, state: Dict) -> Dict:
        """Calculate portfolio performance vs S&P 500"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            session_id = state.get('session_id', '')
            current_portfolio_value = state.get('total_portfolio_value', 0)
            
            # Get first portfolio value from this session
            cursor.execute('''
                SELECT portfolio_value FROM trading_decisions 
                WHERE session_id = ? 
                ORDER BY timestamp ASC LIMIT 1
            ''', (session_id,))
            portfolio_start = cursor.fetchone()
            portfolio_start_value = portfolio_start[0] if portfolio_start else current_portfolio_value
            
            # Get first S&P 500 price from this session
            cursor.execute('''
                SELECT sp500_price FROM sp500_tracking 
                WHERE session_id = ? 
                ORDER BY timestamp ASC LIMIT 1
            ''', (session_id,))
            sp500_start = cursor.fetchone()
            
            # Get current S&P 500 price
            cursor.execute('''
                SELECT sp500_price FROM sp500_tracking 
                WHERE session_id = ? 
                ORDER BY timestamp DESC LIMIT 1
            ''', (session_id,))
            sp500_current = cursor.fetchone()
            
            conn.close()
            
            if sp500_start and sp500_current and portfolio_start_value > 0:
                sp500_start_price = sp500_start[0]
                sp500_current_price = sp500_current[0]
                
                # Calculate returns
                portfolio_return_pct = ((current_portfolio_value - portfolio_start_value) / portfolio_start_value) * 100
                sp500_return_pct = ((sp500_current_price - sp500_start_price) / sp500_start_price) * 100
                
                # Calculate alpha (outperformance)
                alpha = portfolio_return_pct - sp500_return_pct
                
                comparison_data = {
                    'portfolio_start_value': portfolio_start_value,
                    'portfolio_current_value': current_portfolio_value,
                    'portfolio_return_pct': portfolio_return_pct,
                    'sp500_start_price': sp500_start_price,
                    'sp500_current_price': sp500_current_price,
                    'sp500_return_pct': sp500_return_pct,
                    'alpha': alpha,
                    'outperformance': alpha,
                    'outperforming': alpha > 0
                }
                
                # Log the comparison
                self.log_benchmark_comparison(state, comparison_data)
                
                return comparison_data
            else:
                return {'error': 'Insufficient data for comparison'}
                
        except Exception as e:
            print(f"⚠️ Error calculating benchmark comparison: {e}")
            return {'error': str(e)}
    
    def log_benchmark_comparison(self, state: Dict, comparison_data: Dict):
        """Log benchmark comparison to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO benchmark_comparison 
            (trading_date, session_id, portfolio_start_value, portfolio_current_value, 
             portfolio_return_pct, sp500_start_price, sp500_current_price, 
             sp500_return_pct, alpha, outperformance)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            datetime.now().strftime('%Y-%m-%d'),
            state.get('session_id', ''),
            comparison_data['portfolio_start_value'],
            comparison_data['portfolio_current_value'],
            comparison_data['portfolio_return_pct'],
            comparison_data['sp500_start_price'],
            comparison_data['sp500_current_price'],
            comparison_data['sp500_return_pct'],
            comparison_data['alpha'],
            comparison_data['outperformance']
        ))
        
        conn.commit()
        conn.close()
    
    def get_session_benchmark_data(self, session_id: str) -> Dict:
        """Get benchmark comparison data for a session"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM benchmark_comparison 
                WHERE session_id = ? 
                ORDER BY created_at DESC LIMIT 1
            ''', (session_id,))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                columns = ['id', 'trading_date', 'session_id', 'portfolio_start_value', 
                          'portfolio_current_value', 'portfolio_return_pct', 'sp500_start_price',
                          'sp500_current_price', 'sp500_return_pct', 'alpha', 'outperformance', 'created_at']
                return dict(zip(columns, result))
            return {}
            
        except Exception as e:
            print(f"⚠️ Error getting session benchmark data: {e}")
            return {}

# Global SP500 tracker instance
sp500_tracker = SP500Tracker()