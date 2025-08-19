# /trading_bot/memory_store.py

import json
import sqlite3
from datetime import datetime, date, timedelta
from typing import Dict, List, Any, Optional, Tuple
import os
import traceback

# Import your config (with fallback if not available)
try:
    from config import PORTFOLIO_STOCKS
except ImportError:
    PORTFOLIO_STOCKS = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA']  # fallback

class SimpleTradingMemoryStore:
    """Simplified memory store using only SQLite for reliability"""
    
    def __init__(self, db_path="trading_memory.db", backtest_mode=False):
        # Use different database file for backtest mode
        if backtest_mode:
            if db_path == "trading_memory.db":  # Default path
                self.db_path = "trading_memory_backtest.db"
            else:
                # Add _backtest suffix to custom path
                path_parts = db_path.split('.')
                if len(path_parts) > 1:
                    self.db_path = '.'.join(path_parts[:-1]) + '_backtest.' + path_parts[-1]
                else:
                    self.db_path = db_path + '_backtest'
        else:
            self.db_path = db_path
            
        self.backtest_mode = backtest_mode
        self.current_trading_day = None
        self.daily_orders = []
        self.daily_stats = {}
        
        mode_text = "BACKTEST" if backtest_mode else "LIVE"
        print(f"🧠 Initializing Trading Memory Store ({mode_text} MODE) with: {self.db_path}")
        
        # Initialize the database
        try:
            self.init_database()
            self.start_new_trading_day()
            print(f"✅ Trading Memory Store ({mode_text} MODE) initialized successfully")
        except Exception as e:
            print(f"❌ Error initializing memory store: {e}")
            traceback.print_exc()
    
    def init_database(self):
        """Create all necessary tables and migrate existing ones"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Trading memories table (main storage)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS trading_memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    trading_date TEXT,
                    cycle_number INTEGER,
                    session_id TEXT,
                    order_id TEXT,
                    symbol TEXT,
                    action TEXT,
                    quantity INTEGER,
                    price REAL,
                    reasoning TEXT,
                    technical_score REAL,
                    news_sentiment TEXT,
                    portfolio_value REAL,
                    cash_available REAL,
                    market_context TEXT,
                    ai_confidence TEXT,
                    priority TEXT,
                    execution_status TEXT,
                    pnl_impact REAL,
                    strategy_mode TEXT,
                    sp500_price REAL DEFAULT 0,
                    sp500_change_pct REAL DEFAULT 0,
                    portfolio_vs_sp500 REAL DEFAULT 0,
                    benchmark_alpha REAL DEFAULT 0,
                    searchable_content TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Add new forecast columns if they don't exist (migration)
            self._migrate_database_schema(cursor)
            
            # Commit migration changes
            conn.commit()
            
            # Daily summaries table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS daily_summaries (
                    trading_date TEXT PRIMARY KEY,
                    total_trades INTEGER,
                    total_buys INTEGER,
                    total_sells INTEGER,
                    total_volume INTEGER,
                    avg_technical_score REAL,
                    dominant_sentiment TEXT,
                    strategy_mode TEXT,
                    portfolio_value REAL,
                    total_pnl REAL,
                    cash_available REAL,
                    positions_json TEXT,
                    stats_json TEXT,
                    session_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create indexes for better performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_trading_date ON trading_memories(trading_date)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_symbol ON trading_memories(symbol)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_action ON trading_memories(action)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON trading_memories(timestamp)')
            
            conn.commit()
            conn.close()
            print("✅ Database tables created successfully")
            
        except Exception as e:
            print(f"❌ Error creating database: {e}")
            traceback.print_exc()
            raise
    
    def _migrate_database_schema(self, cursor):
        """Add new forecast columns to existing tables if they don't exist"""
        try:
            # Check which columns exist
            cursor.execute("PRAGMA table_info(trading_memories)")
            existing_columns = [column[1] for column in cursor.fetchall()]
            print(f"🔍 Found {len(existing_columns)} existing columns in trading_memories")
            
            # List of new forecast columns to add
            new_columns = [
                ('target_price', 'REAL DEFAULT NULL'),
                ('stop_loss', 'REAL DEFAULT NULL'),
                ('risk_reward_ratio', 'REAL DEFAULT NULL'),
                ('forecast_confidence', 'REAL DEFAULT NULL'),
                ('technical_target', 'REAL DEFAULT NULL'),
                ('ai_target', 'REAL DEFAULT NULL'),
                ('combined_target', 'REAL DEFAULT NULL'),
                ('expected_timeline_days', 'INTEGER DEFAULT NULL'),
                ('forecast_method', 'TEXT DEFAULT NULL'),
                ('forecast_data', 'TEXT DEFAULT NULL')
            ]
            
            # Add missing columns one by one with individual commits
            columns_added = 0
            for column_name, column_def in new_columns:
                if column_name not in existing_columns:
                    try:
                        print(f"🔧 Adding column: {column_name}")
                        cursor.execute(f'ALTER TABLE trading_memories ADD COLUMN {column_name} {column_def}')
                        # Verify the column was added
                        cursor.execute("PRAGMA table_info(trading_memories)")
                        updated_columns = [col[1] for col in cursor.fetchall()]
                        if column_name in updated_columns:
                            columns_added += 1
                            print(f"✅ Successfully added column: {column_name}")
                        else:
                            print(f"❌ Failed to verify column addition: {column_name}")
                    except Exception as e:
                        print(f"⚠️ Could not add column {column_name}: {e}")
                        # If this is a "duplicate column" error, that's actually OK
                        if "duplicate column name" in str(e).lower():
                            print(f"ℹ️ Column {column_name} already exists")
                        else:
                            print(f"❌ Real error adding {column_name}: {e}")
            
            if columns_added > 0:
                print(f"✅ Database migration complete: {columns_added} new forecast columns added")
            else:
                print("✅ Database schema up to date - all forecast columns already exist")
                
        except Exception as e:
            print(f"⚠️ Error during database migration: {e}")
            traceback.print_exc()
            # Continue anyway - the database will still work for basic operations
    
    def get_trading_day(self) -> str:
        """Get current trading day string"""
        return datetime.now().strftime('%Y-%m-%d')
    
    def start_new_trading_day(self) -> bool:
        """Check if we need to start a new trading day"""
        current_day = self.get_trading_day()
        
        if self.current_trading_day != current_day:
            if self.current_trading_day:
                print(f"📅 Trading day transition: {self.current_trading_day} → {current_day}")
                self._store_daily_summary()
            
            self.current_trading_day = current_day
            self.daily_orders = []
            self.daily_stats = {
                'total_trades': 0,
                'total_buys': 0,
                'total_sells': 0,
                'total_volume': 0,
                'avg_technical_score': 0,
                'dominant_sentiment': 'NEUTRAL',
                'strategy_mode': 'BALANCED'
            }
            
            print(f"🌅 Started new trading day: {current_day}")
            return True
        
        return False
    
    def store_trading_decision(self, state: Dict, executed_trades: List[Dict]):
        """Store trading decisions in SQLite database"""
        if not executed_trades:
            print("ℹ️ No executed trades to store")
            return
        
        self.start_new_trading_day()
        trading_date = self.get_trading_day()
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            stored_count = 0
            
            for trade in executed_trades:
                # Get data safely with defaults
                timestamp = datetime.now().isoformat()
                cycle_number = state.get('cycle_number', 0)
                session_id = state.get('session_id', 'unknown')
                order_id = trade.get('order_id', 'N/A')
                symbol = trade.get('symbol', '')
                action = trade.get('action', 'HOLD')
                quantity = trade.get('quantity', 0)
                price = trade.get('price', 0)
                reasoning = trade.get('reasoning', '')
                technical_score = trade.get('technical_score', 0)
                news_sentiment = self._get_symbol_sentiment(state, symbol)
                portfolio_value = state.get('total_portfolio_value', 0)
                cash_available = state.get('cash_available', 0)
                market_context = self._create_market_context(state)
                ai_confidence = trade.get('confidence', 'MEDIUM')
                priority = trade.get('priority', 'LOW')
                execution_status = trade.get('status', 'Unknown')
                pnl_impact = trade.get('estimated_cost', 0) * (-1 if action == 'BUY' else 1)
                strategy_mode = 'AGGRESSIVE' if state.get('aggressive_mode', False) else 'BALANCED'
                sp500_price = state.get('sp500_data', {}).get('price', 0)
                sp500_change_pct = state.get('sp500_data', {}).get('change_pct', 0)
                portfolio_vs_sp500 = state.get('benchmark_comparison', {}).get('alpha', 0)
                benchmark_alpha = state.get('benchmark_comparison', {}).get('alpha', 0)
                
                # Extract forecast data for BUY orders
                forecast_data = trade.get('forecast', {})
                target_price = forecast_data.get('target_price') if action == 'BUY' else None
                stop_loss = forecast_data.get('stop_loss') if action == 'BUY' else None
                risk_reward_ratio = forecast_data.get('risk_reward_ratio') if action == 'BUY' else None
                forecast_confidence = forecast_data.get('confidence') if action == 'BUY' else None
                technical_target = forecast_data.get('technical_target') if action == 'BUY' else None
                ai_target = forecast_data.get('ai_target') if action == 'BUY' else None
                combined_target = forecast_data.get('combined_target') if action == 'BUY' else None
                expected_timeline = forecast_data.get('expected_timeline_days') if action == 'BUY' else None
                forecast_method = forecast_data.get('method') if action == 'BUY' else None
                forecast_data_json = json.dumps(forecast_data) if forecast_data and action == 'BUY' else None
                
                # Create searchable content including forecast info
                searchable_content = f"{action} {quantity} {symbol} at ${price:.2f} - {reasoning} - Score: {technical_score} - Sentiment: {news_sentiment}"
                if target_price:
                    searchable_content += f" - Target: ${target_price:.2f}"
                
                # Insert into database
                cursor.execute('''
                    INSERT INTO trading_memories 
                    (timestamp, trading_date, cycle_number, session_id, order_id, symbol, action,
                     quantity, price, reasoning, technical_score, news_sentiment, portfolio_value,
                     cash_available, market_context, ai_confidence, priority, execution_status,
                     pnl_impact, strategy_mode, sp500_price, sp500_change_pct, portfolio_vs_sp500,
                     benchmark_alpha, searchable_content, target_price, stop_loss, risk_reward_ratio,
                     forecast_confidence, technical_target, ai_target, combined_target, 
                     expected_timeline_days, forecast_method, forecast_data)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    timestamp, trading_date, cycle_number, session_id,
                    order_id, symbol, action, quantity, price,
                    reasoning, technical_score, news_sentiment,
                    portfolio_value, cash_available, market_context,
                    ai_confidence, priority, execution_status,
                    pnl_impact, strategy_mode, sp500_price,
                    sp500_change_pct, portfolio_vs_sp500, benchmark_alpha,
                    searchable_content, target_price, stop_loss, risk_reward_ratio,
                    forecast_confidence, technical_target, ai_target, combined_target,
                    expected_timeline, forecast_method, forecast_data_json
                ))
                
                stored_count += 1
                print(f"✅ Stored: {action} {quantity} {symbol} @ ${price:.2f}")
            
            conn.commit()
            print(f"🧠 Successfully stored {stored_count} trading decisions for {trading_date}")
            
        except Exception as e:
            print(f"❌ Error storing trading decisions: {e}")
            traceback.print_exc()
            if 'conn' in locals():
                conn.rollback()
        finally:
            if 'conn' in locals():
                conn.close()
    
    def get_daily_context(self, trading_date: str = None) -> Dict:
        """Get context for current or specified trading day"""
        if trading_date is None:
            trading_date = self.get_trading_day()
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get all trades for the day
            cursor.execute('''
                SELECT * FROM trading_memories WHERE trading_date = ? ORDER BY timestamp
            ''', (trading_date,))
            trades = cursor.fetchall()
            
            # Convert to dictionaries
            if trades:
                columns = [desc[0] for desc in cursor.description]
                trades_dict = [dict(zip(columns, trade)) for trade in trades]
            else:
                trades_dict = []
            
            conn.close()
            
            return {
                'trading_date': trading_date,
                'total_trades': len(trades_dict),
                'trades': trades_dict
            }
            
        except Exception as e:
            print(f"⚠️ Error getting daily context for {trading_date}: {e}")
            return {'trading_date': trading_date, 'trades': [], 'total_trades': 0}
    
    def search_similar_situations(self, query: str, symbol: str = None, days_back: int = 7) -> List[Dict]:
        """Search for similar trading situations using text matching"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Build search query
            search_conditions = []
            params = []
            
            # Date range
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=days_back)
            search_conditions.append("trading_date BETWEEN ? AND ?")
            params.extend([start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')])
            
            # Symbol filter
            if symbol:
                search_conditions.append("symbol = ?")
                params.append(symbol)
            
            # Text search in searchable content
            if query:
                search_conditions.append("searchable_content LIKE ?")
                params.append(f"%{query}%")
            
            where_clause = " AND ".join(search_conditions)
            
            cursor.execute(f'''
                SELECT * FROM trading_memories 
                WHERE {where_clause}
                ORDER BY timestamp DESC
                LIMIT 20
            ''', params)
            
            trades = cursor.fetchall()
            
            results = []
            if trades:
                columns = [desc[0] for desc in cursor.description]
                for trade in trades:
                    trade_dict = dict(zip(columns, trade))
                    results.append({
                        'trading_date': trade_dict['trading_date'],
                        'similarity_score': 1.0,
                        'memory': trade_dict
                    })
            
            conn.close()
            return results
            
        except Exception as e:
            print(f"⚠️ Error searching similar situations: {e}")
            return []
    
    def get_symbol_trading_history(self, symbol: str, days_back: int = 7) -> List[Dict]:
        """Get all trading history for a specific symbol"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Date range
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=days_back)
            
            cursor.execute('''
                SELECT * FROM trading_memories 
                WHERE symbol = ? AND trading_date BETWEEN ? AND ?
                ORDER BY timestamp DESC
                LIMIT 50
            ''', (symbol, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')))
            
            trades = cursor.fetchall()
            
            if trades:
                columns = [desc[0] for desc in cursor.description]
                history = [dict(zip(columns, trade)) for trade in trades]
            else:
                history = []
            
            conn.close()
            return history
            
        except Exception as e:
            print(f"⚠️ Error getting symbol history for {symbol}: {e}")
            return []
    
    def get_buy_targets_for_symbol(self, symbol: str, days_back: int = 30) -> List[Dict]:
        """Get all BUY orders with target prices for a specific symbol"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Date range
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=days_back)
            
            cursor.execute('''
                SELECT timestamp, trading_date, price, target_price, stop_loss, 
                       risk_reward_ratio, forecast_confidence, technical_target, 
                       ai_target, combined_target, expected_timeline_days, 
                       forecast_method, forecast_data, quantity, reasoning
                FROM trading_memories 
                WHERE symbol = ? AND action = 'BUY' AND target_price IS NOT NULL
                AND trading_date BETWEEN ? AND ?
                ORDER BY timestamp DESC
                LIMIT 20
            ''', (symbol, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')))
            
            targets = cursor.fetchall()
            
            if targets:
                columns = [desc[0] for desc in cursor.description]
                target_history = [dict(zip(columns, target)) for target in targets]
            else:
                target_history = []
            
            conn.close()
            return target_history
            
        except Exception as e:
            print(f"⚠️ Error getting buy targets for {symbol}: {e}")
            return []
    
    def get_ai_context_for_decision(self, state: Dict) -> str:
        """Generate AI context based on memory for better decision making"""
        try:
            current_day_context = self.get_daily_context()
            
            context_parts = [
                f"📅 Current Trading Day: {self.get_trading_day()}",
                f"🔢 Today's Trades: {current_day_context['total_trades']}",
            ]
            
            # Add today's trading summary
            if current_day_context['total_trades'] > 0:
                trades = current_day_context['trades']
                buy_count = len([t for t in trades if t['action'] == 'BUY'])
                sell_count = len([t for t in trades if t['action'] == 'SELL'])
                
                context_parts.extend([
                    f"📊 Today's Activity:",
                    f"  • Buys: {buy_count}, Sells: {sell_count}",
                ])
                
                # Show recent trades
                recent_trades = trades[-3:]  # Last 3 trades
                context_parts.append(f"📈 Recent Trades:")
                for trade in recent_trades:
                    context_parts.append(f"  • {trade['action']} {trade['quantity']} {trade['symbol']} @ ${trade['price']:.2f}")
            
            # Add symbol-specific recent activity with target info
            symbol_activity = []
            for symbol in PORTFOLIO_STOCKS[:5]:  # Check recent activity for first 5 symbols
                history = self.get_symbol_trading_history(symbol, days_back=3)
                targets = self.get_buy_targets_for_symbol(symbol, days_back=7)
                
                if history or targets:
                    recent_trades = len(history)
                    last_action = history[0].get('action', 'N/A') if history else 'N/A'
                    active_targets = len([t for t in targets if t.get('target_price')])
                    
                    activity_text = f"{symbol}: {recent_trades} trades (last: {last_action})"
                    if active_targets > 0:
                        latest_target = targets[0]
                        target_price = latest_target.get('target_price')
                        buy_price = latest_target.get('price')
                        if target_price and buy_price:
                            potential_gain = ((target_price - buy_price) / buy_price) * 100
                            activity_text += f", Target: ${target_price:.2f} (+{potential_gain:.1f}%)"
                    
                    symbol_activity.append(activity_text)
            
            if symbol_activity:
                context_parts.append(f"📊 Recent Symbol Activity (3 days):")
                for activity in symbol_activity[:3]:  # Limit to avoid too much text
                    context_parts.append(f"  • {activity}")
            
            return "\n".join(context_parts)
            
        except Exception as e:
            print(f"⚠️ Error generating AI context: {e}")
            return f"📅 Current Trading Day: {self.get_trading_day()}\n🔢 Today's Trades: 0\n⚠️ Error accessing trading history"
    
    def _get_symbol_sentiment(self, state: Dict, symbol: str) -> str:
        """Get news sentiment for symbol from state"""
        try:
            news_sentiment = state.get('news_sentiment', {})
            symbol_news = news_sentiment.get(symbol, {})
            return symbol_news.get('sentiment_label', 'NO_DATA')
        except:
            return 'NO_DATA'
    
    def _create_market_context(self, state: Dict) -> str:
        """Create market context string"""
        try:
            portfolio_value = state.get('total_portfolio_value', 0)
            pnl = state.get('total_unrealized_pnl', 0)
            pnl_pct = (pnl / portfolio_value * 100) if portfolio_value > 0 else 0
            return f"Portfolio: ${portfolio_value:,.0f} (P&L: {pnl_pct:+.1f}%)"
        except:
            return "Portfolio: Unknown"
    
    def _store_daily_summary(self):
        """Store daily summary at the end of trading day"""
        # Simple implementation - just print for now
        if self.current_trading_day:
            print(f"📦 End of trading day: {self.current_trading_day}")
    
    def get_memory_stats(self) -> Dict:
        """Get statistics about stored memories"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Total memories
            cursor.execute("SELECT COUNT(*) FROM trading_memories")
            total_memories = cursor.fetchone()[0]
            
            # Memories by trading date
            cursor.execute('''
                SELECT trading_date, COUNT(*) 
                FROM trading_memories 
                GROUP BY trading_date 
                ORDER BY trading_date DESC 
                LIMIT 7
            ''')
            daily_counts = cursor.fetchall()
            
            # Action distribution
            cursor.execute('''
                SELECT action, COUNT(*) 
                FROM trading_memories 
                GROUP BY action
            ''')
            action_counts = dict(cursor.fetchall())
            
            conn.close()
            
            return {
                'total_memories': total_memories,
                'daily_counts': dict(daily_counts),
                'action_distribution': action_counts,
                'database_path': self.db_path,
                'database_size_mb': os.path.getsize(self.db_path) / (1024 * 1024) if os.path.exists(self.db_path) else 0
            }
            
        except Exception as e:
            print(f"⚠️ Error getting memory stats: {e}")
            return {'error': str(e)}

# Create global instances - will be initialized based on mode
print("🚀 Trading memory instances will be created based on trading mode...")
trading_memory = None
trading_memory_backtest = None

def get_memory_store(backtest_mode=False):
    """Get the appropriate memory store based on trading mode"""
    global trading_memory, trading_memory_backtest
    
    if backtest_mode:
        if trading_memory_backtest is None:
            print("🚀 Creating backtest trading memory instance...")
            trading_memory_backtest = SimpleTradingMemoryStore(backtest_mode=True)
        return trading_memory_backtest
    else:
        if trading_memory is None:
            print("🚀 Creating live trading memory instance...")
            trading_memory = SimpleTradingMemoryStore(backtest_mode=False)
        return trading_memory

# Integration functions for your trading bot
def store_cycle_memory(state: Dict, backtest_mode=False) -> Dict:
    """Store current cycle's trading decisions in memory"""
    try:
        # Get the appropriate memory store
        memory_store = get_memory_store(backtest_mode)
        
        executed_trades = state.get('executed_trades', [])
        
        if executed_trades:
            mode_text = "BACKTEST" if backtest_mode else "LIVE"
            print(f"🧠 Storing {len(executed_trades)} executed trades in {mode_text} memory...")
            memory_store.store_trading_decision(state, executed_trades)
            
            # Verify storage worked
            daily_context = memory_store.get_daily_context()
            print(f"✅ {mode_text} Memory verification: {daily_context['total_trades']} total trades stored today")
        else:
            print("ℹ️ No executed trades to store in memory")
        
        # Add memory context to state for AI to use
        memory_context = memory_store.get_ai_context_for_decision(state)
        state['memory_context'] = memory_context
        
        return state
        
    except Exception as e:
        print(f"❌ Error in store_cycle_memory: {e}")
        traceback.print_exc()
        # Return state with basic memory context even if storage failed
        state['memory_context'] = f"📅 Current Trading Day: {datetime.now().strftime('%Y-%m-%d')}\n⚠️ Memory storage error"
        return state

def get_memory_enhanced_prompt_context(state: Dict, backtest_mode=False) -> str:
    """Get enhanced prompt context with memory for AI decision making"""
    try:
        memory_store = get_memory_store(backtest_mode)
        return memory_store.get_ai_context_for_decision(state)
    except Exception as e:
        print(f"⚠️ Error getting memory context: {e}")
        return f"📅 Current Trading Day: {datetime.now().strftime('%Y-%m-%d')}\n⚠️ Memory context error"

def get_memory_stats(backtest_mode=False) -> Dict:
    """Get memory storage statistics for debugging"""
    try:
        memory_store = get_memory_store(backtest_mode)
        return memory_store.get_memory_stats()
    except Exception as e:
        print(f"⚠️ Error getting memory stats: {e}")
        return {'error': str(e)}

# Test function
def manually_migrate_database(db_path=None, backtest_mode=False):
    """Manually migrate database to add forecast columns"""
    if db_path is None:
        if backtest_mode:
            db_path = "trading_memory_backtest.db"
        else:
            db_path = "trading_memory.db"
    
    print(f"\n🔧 MANUALLY MIGRATING DATABASE: {db_path}")
    print("=" * 50)
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check current schema
        cursor.execute("PRAGMA table_info(trading_memories)")
        existing_columns = [column[1] for column in cursor.fetchall()]
        print(f"🔍 Current columns ({len(existing_columns)}): {', '.join(existing_columns[:10])}...")
        
        # List of new forecast columns to add
        new_columns = [
            ('target_price', 'REAL DEFAULT NULL'),
            ('stop_loss', 'REAL DEFAULT NULL'),
            ('risk_reward_ratio', 'REAL DEFAULT NULL'),
            ('forecast_confidence', 'REAL DEFAULT NULL'),
            ('technical_target', 'REAL DEFAULT NULL'),
            ('ai_target', 'REAL DEFAULT NULL'),
            ('combined_target', 'REAL DEFAULT NULL'),
            ('expected_timeline_days', 'INTEGER DEFAULT NULL'),
            ('forecast_method', 'TEXT DEFAULT NULL'),
            ('forecast_data', 'TEXT DEFAULT NULL')
        ]
        
        columns_added = 0
        for column_name, column_def in new_columns:
            if column_name not in existing_columns:
                try:
                    print(f"🔧 Adding column: {column_name}")
                    cursor.execute(f'ALTER TABLE trading_memories ADD COLUMN {column_name} {column_def}')
                    conn.commit()  # Commit each column addition immediately
                    columns_added += 1
                    print(f"✅ Added: {column_name}")
                except Exception as e:
                    if "duplicate column" in str(e).lower():
                        print(f"ℹ️ Column {column_name} already exists")
                    else:
                        print(f"❌ Error adding {column_name}: {e}")
            else:
                print(f"ℹ️ Column {column_name} already exists")
        
        # Verify final schema
        cursor.execute("PRAGMA table_info(trading_memories)")
        final_columns = [column[1] for column in cursor.fetchall()]
        print(f"\n✅ Final schema ({len(final_columns)} columns):")
        
        # Check if all forecast columns are now present
        forecast_columns = [col[0] for col in new_columns]
        missing_columns = [col for col in forecast_columns if col not in final_columns]
        
        if missing_columns:
            print(f"❌ Still missing columns: {missing_columns}")
        else:
            print(f"✅ All forecast columns are present!")
        
        conn.close()
        print(f"\n🎉 Migration complete! Added {columns_added} new columns to {db_path}")
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        traceback.print_exc()
        return False

def test_memory_storage():
    """Test function to verify memory storage is working"""
    print("\n🧪 Testing Memory Storage System...")
    
    # First, try to manually migrate the database
    print("🔧 Ensuring database schema is up to date...")
    manually_migrate_database(backtest_mode=False)
    manually_migrate_database(backtest_mode=True)
    
    # Test state
    test_state = {
        'cycle_number': 1,
        'session_id': 'test_session',
        'total_portfolio_value': 100000,
        'cash_available': 50000,
        'total_unrealized_pnl': 1000,
        'aggressive_mode': False,
        'sp500_data': {'price': 4500, 'change_pct': 0.5},
        'benchmark_comparison': {'alpha': 0.2},
        'news_sentiment': {
            'AAPL': {'sentiment_label': 'POSITIVE', 'has_news': True},
            'MSFT': {'sentiment_label': 'NEUTRAL', 'has_news': False}
        },
        'executed_trades': [
            {
                'symbol': 'AAPL',
                'action': 'BUY',
                'quantity': 10,
                'price': 150.00,
                'reasoning': 'Strong technical signals',
                'technical_score': 8.5,
                'confidence': 'HIGH',
                'priority': 'HIGH',
                'order_id': 'TEST_001',
                'status': 'Filled',
                'forecast': {
                    'target_price': 165.00,
                    'stop_loss': 142.50,
                    'risk_reward_ratio': 2.0,
                    'confidence': 0.75,
                    'technical_target': 162.00,
                    'ai_target': 168.00,
                    'combined_target': 165.00,
                    'expected_timeline_days': 30,
                    'method': 'combined_analysis'
                }
            }
        ]
    }
    
    # Store in memory
    result_state = store_cycle_memory(test_state)
    
    # Test retrieval
    memory_store = get_memory_store(backtest_mode=False)
    daily_context = memory_store.get_daily_context()
    print(f"📊 Daily context retrieved: {daily_context['total_trades']} trades")
    
    # Test stats
    stats = get_memory_stats()
    print(f"📊 Memory stats: {stats}")
    
    print("✅ Memory storage test completed!")
    return result_state

if __name__ == "__main__":
    # Run test if file is executed directly
    test_memory_storage()