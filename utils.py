# /trading_bot/utils.py

import os
import json
import random
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from config import storage_client, GCS_BUCKET_NAME, MARKET_TIMEZONE

# Import crypto connection
from crypto_market_data import test_gemini_connection

# Legacy IBKR imports (optional)
try:
    from ib_insync import IB
    IBKR_AVAILABLE = True
    # Suppress verbose IB connection logs
    logging.getLogger('ib_insync').setLevel(logging.WARNING)
except ImportError:
    print("⚠️ IBKR not available, using crypto-only mode")
    IBKR_AVAILABLE = False

from typing import Dict, List, Optional

# Global variable for the Interactive Brokers connection (legacy)
ib_connection = None

async def ensure_connection():
    """
    For crypto trading, test Gemini connection instead of IBKR
    """
    try:
        print("🔍 Testing Gemini Exchange connection...")
        connection_ok = await test_gemini_connection()
        if connection_ok:
            print("✅ Gemini connection verified")
            return True
        else:
            print("❌ Gemini connection failed")
            return None
    except Exception as e:
        print(f"❌ Error testing Gemini connection: {e}")
        return None

def upload_to_gcs(source_file_path, destination_blob_name):
    """
    Uploads a local file to a specified Google Cloud Storage bucket.
    """
    try:
        if not os.path.exists(source_file_path):
            print(f"❌ GCS Upload Error: Source file not found at {source_file_path}")
            return None

        bucket = storage_client.bucket(GCS_BUCKET_NAME)
        blob = bucket.blob(destination_blob_name)
        blob.upload_from_filename(source_file_path)

        gcs_uri = f"gs://{GCS_BUCKET_NAME}/{destination_blob_name}"
        print(f"📄 File uploaded to GCS: {gcs_uri}")
        return gcs_uri
    except Exception as e:
        print(f"❌ GCS Upload Failed: {e}")
        return None

def log_portfolio_activity(action, details=None):
    """
    Logs a JSON line entry for a given portfolio activity to Google Cloud Storage.
    """
    try:
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "details": details or {},
            "session_id": "portfolio_trading" # This could be made dynamic
        }

        log_file_path = "portfolio_logs/activity.jsonl"
        bucket = storage_client.bucket(GCS_BUCKET_NAME)
        log_blob = bucket.blob(log_file_path)

        # Append to the log file
        try:
            existing_logs = log_blob.download_as_text()
        except Exception:
            existing_logs = ""
        
        new_content = existing_logs + json.dumps(log_entry) + "\n"
        log_blob.upload_from_string(new_content, content_type='application/jsonl')
        
        print(f"📝 Logged activity to GCS: {action}")
    except Exception as e:
        print(f"❌ Failed to log activity to GCS: {e}")

def is_market_open(backtest_mode=False):
    """
    Checks if the US stock market is currently open.
    In backtest mode, always returns True to allow trading simulation.
    """
    # In backtest mode, always return True to allow continuous trading
    if backtest_mode:
        return True
        
    try:
        now = datetime.now(MARKET_TIMEZONE)
        current_time = now.time()
        weekday = now.weekday()

        if weekday >= 5:  # Saturday or Sunday
            return False
            
        market_open = datetime.strptime("09:30", "%H:%M").time()
        market_close = datetime.strptime("16:00", "%H:%M").time()
        
        return market_open <= current_time <= market_close
    except Exception as e:
        print(f"⚠️  Could not verify market hours, assuming open. Error: {e}")
        return True # Fail-safe to assume it's open

def setup_reporting_directory():
    """
    Creates the 'portfolio_reports' directory if it doesn't already exist.
    """
    reports_dir = Path("portfolio_reports")
    reports_dir.mkdir(exist_ok=True)
    return reports_dir

def generate_session_id():
    """
    Generates a unique ID for a trading session.
    """
    return f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{random.randint(1000, 9999)}"



# Add these functions to the end of your existing utils.py file:

def log_news_activity(symbol: str, action: str, details: Dict = None):
    """
    Specialized logging function for news-related activities
    """
    try:
        news_details = {
            "symbol": symbol,
            "news_action": action,
            **(details or {})
        }
        log_portfolio_activity(f"news_{action}", news_details)
    except Exception as e:
        print(f"❌ Failed to log news activity: {e}")

def save_news_report(report_data: Dict, report_type: str = "general"):
    """
    Save news analysis report using existing infrastructure
    """
    try:
        reports_dir = setup_reporting_directory()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Create filename based on report type
        filename = f"news_{report_type}_{timestamp}.json"
        filepath = reports_dir / filename
        
        # Save locally
        import json
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, default=str)
        
        print(f"📰 News report saved: {filepath}")
        
        # Upload to GCS
        gcs_path = f"news_reports/{datetime.now().strftime('%Y/%m/%d')}/{filename}"
        upload_result = upload_to_gcs(str(filepath), gcs_path)
        
        # Log the activity
        log_news_activity("portfolio", "report_saved", {
            "report_type": report_type,
            "filepath": str(filepath),
            "gcs_path": gcs_path,
            "upload_success": upload_result is not None
        })
        
        return str(filepath)
        
    except Exception as e:
        print(f"❌ Error saving news report: {e}")
        return None

def get_news_cache_path(symbol: str, days_back: int = 1):
    """
    Generate cache path for news data to avoid excessive API calls
    """
    cache_dir = Path("news_cache")
    cache_dir.mkdir(exist_ok=True)
    
    today = datetime.now().strftime('%Y%m%d')
    cache_filename = f"{symbol}_{days_back}days_{today}.json"
    return cache_dir / cache_filename

def cache_news_data(symbol: str, news_data: Dict, days_back: int = 1):
    """
    Cache news data locally to reduce API calls
    """
    try:
        cache_path = get_news_cache_path(symbol, days_back)
        
        cache_entry = {
            "timestamp": datetime.now().isoformat(),
            "symbol": symbol,
            "days_back": days_back,
            "data": news_data
        }
        
        import json
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(cache_entry, f, indent=2, default=str)
        
        print(f"💾 Cached news data for {symbol}: {cache_path}")
        return True
        
    except Exception as e:
        print(f"❌ Error caching news data for {symbol}: {e}")
        return False

def load_cached_news_data(symbol: str, days_back: int = 1, max_age_hours: int = 2):
    """
    Load cached news data if it's still fresh
    """
    try:
        cache_path = get_news_cache_path(symbol, days_back)
        
        if not cache_path.exists():
            return None
        
        import json
        with open(cache_path, 'r', encoding='utf-8') as f:
            cache_entry = json.load(f)
        
        # Check if cache is still fresh
        cache_time = datetime.fromisoformat(cache_entry["timestamp"])
        age_hours = (datetime.now() - cache_time).total_seconds() / 3600
        
        if age_hours <= max_age_hours:
            print(f"📥 Using cached news data for {symbol} (age: {age_hours:.1f}h)")
            return cache_entry["data"]
        else:
            print(f"⏰ Cache expired for {symbol} (age: {age_hours:.1f}h)")
            return None
            
    except Exception as e:
        print(f"❌ Error loading cached news data for {symbol}: {e}")
        return None

def clean_news_cache(max_age_days: int = 7):
    """
    Clean old news cache files
    """
    try:
        cache_dir = Path("news_cache")
        if not cache_dir.exists():
            return
        
        cutoff_time = datetime.now() - timedelta(days=max_age_days)
        cleaned_count = 0
        
        for cache_file in cache_dir.glob("*.json"):
            try:
                # Check file modification time
                file_time = datetime.fromtimestamp(cache_file.stat().st_mtime)
                if file_time < cutoff_time:
                    cache_file.unlink()
                    cleaned_count += 1
            except Exception as e:
                print(f"⚠️ Error cleaning cache file {cache_file}: {e}")
        
        if cleaned_count > 0:
            print(f"🧹 Cleaned {cleaned_count} old news cache files")
            
    except Exception as e:
        print(f"❌ Error cleaning news cache: {e}")

def is_news_market_hours():
    """
    Check if it's appropriate time to fetch news (avoid excessive API calls)
    Returns True during extended hours when news is most relevant
    """
    try:
        now = datetime.now(MARKET_TIMEZONE)
        current_time = now.time()
        weekday = now.weekday()

        # Allow news fetching on weekdays from 6 AM to 8 PM ET
        if weekday < 5:  # Monday to Friday
            news_start = datetime.strptime("06:00", "%H:%M").time()
            news_end = datetime.strptime("20:00", "%H:%M").time()
            return news_start <= current_time <= news_end
        
        # Limited news fetching on weekends (only morning)
        else:
            weekend_start = datetime.strptime("08:00", "%H:%M").time()
            weekend_end = datetime.strptime("12:00", "%H:%M").time()
            return weekend_start <= current_time <= weekend_end
            
    except Exception as e:
        print(f"⚠️ Could not verify news hours, allowing fetch. Error: {e}")
        return True

# Add this import at the top if not already present
from datetime import timedelta

# Example of how to integrate news checking into your existing market check
def should_fetch_news():
    """
    Determine if news should be fetched based on market status and timing
    """
    market_open = is_market_open()
    news_hours = is_news_market_hours()
    
    # Fetch news if market is open OR during extended news hours
    return market_open or news_hours


# Add this to your main trading notebook after imports

import time
from functools import wraps
from typing import Dict, List
from datetime import datetime

class TradingTimer:
    """Timer system for tracking trading bot performance"""
    
    def __init__(self):
        self.timings: Dict[str, List[float]] = {}
        self.current_cycle_timings: Dict[str, float] = {}
        self.cycle_start_time = None
        self.session_start_time = None
    
    def start_session(self):
        """Start timing a new trading session"""
        self.session_start_time = time.time()
        self.timings.clear()
        print("⏱️ Started session timing")
    
    def start_cycle(self, cycle_number: int):
        """Start timing a new cycle"""
        self.cycle_start_time = time.time()
        self.current_cycle_timings.clear()
        print(f"\n⏱️ Started timing Cycle {cycle_number}")
    
    def record_time(self, step_name: str, duration: float):
        """Record timing for a step"""
        if step_name not in self.timings:
            self.timings[step_name] = []
        self.timings[step_name].append(duration)
        self.current_cycle_timings[step_name] = duration
    
    def end_cycle(self, cycle_number: int):
        """End cycle and print summary"""
        if self.cycle_start_time:
            total_cycle_time = time.time() - self.cycle_start_time
            print(f"\n📊 Cycle {cycle_number} Timing Summary:")
            print(f"   🕐 Total Cycle Time: {total_cycle_time:.2f}s")
            
            # Sort by time taken
            sorted_timings = sorted(self.current_cycle_timings.items(), key=lambda x: x[1], reverse=True)
            
            for step, duration in sorted_timings:
                percentage = (duration / total_cycle_time) * 100
                print(f"   📈 {step}: {duration:.2f}s ({percentage:.1f}%)")
    
    def end_session(self):
        """End session and print comprehensive report"""
        if self.session_start_time:
            total_session_time = time.time() - self.session_start_time
            print(f"\n" + "="*60)
            print(f"📊 SESSION TIMING REPORT")
            print(f"="*60)
            print(f"🕐 Total Session Time: {total_session_time:.2f}s")
            print(f"📈 Steps Performance Analysis:")
            
            step_stats = {}
            for step, times in self.timings.items():
                total_time = sum(times)
                avg_time = total_time / len(times)
                max_time = max(times)
                min_time = min(times)
                count = len(times)
                
                step_stats[step] = {
                    'total': total_time,
                    'average': avg_time,
                    'max': max_time,
                    'min': min_time,
                    'count': count
                }
            
            # Sort by total time
            sorted_stats = sorted(step_stats.items(), key=lambda x: x[1]['total'], reverse=True)
            
            print(f"\n{'Step':<20} {'Total(s)':<10} {'Avg(s)':<8} {'Max(s)':<8} {'Min(s)':<8} {'Count':<6}")
            print("-" * 70)
            
            for step, stats in sorted_stats:
                print(f"{step:<20} {stats['total']:<10.2f} {stats['average']:<8.2f} {stats['max']:<8.2f} {stats['min']:<8.2f} {stats['count']:<6}")
            
            print("="*60)

# Global timer instance
trading_timer = TradingTimer()

def time_function(step_name: str):
    """Decorator to time function execution"""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            print(f"⏱️ Starting: {step_name}")
            
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                trading_timer.record_time(step_name, duration)
                print(f"✅ Completed: {step_name} ({duration:.2f}s)")
                return result
            except Exception as e:
                duration = time.time() - start_time
                trading_timer.record_time(f"{step_name}_ERROR", duration)
                print(f"❌ Failed: {step_name} ({duration:.2f}s) - {e}")
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            print(f"⏱️ Starting: {step_name}")
            
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                trading_timer.record_time(step_name, duration)
                print(f"✅ Completed: {step_name} ({duration:.2f}s)")
                return result
            except Exception as e:
                duration = time.time() - start_time
                trading_timer.record_time(f"{step_name}_ERROR", duration)
                print(f"❌ Failed: {step_name} ({duration:.2f}s) - {e}")
                raise
        
        # Return async wrapper if function is async
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator

def time_code_block(step_name: str):
    """Context manager for timing code blocks"""
    class TimeContext:
        def __init__(self, name):
            self.name = name
            self.start_time = None
        
        def __enter__(self):
            self.start_time = time.time()
            print(f"⏱️ Starting: {self.name}")
            return self
        
        def __exit__(self, exc_type, exc_val, exc_tb):
            duration = time.time() - self.start_time
            if exc_type is None:
                trading_timer.record_time(self.name, duration)
                print(f"✅ Completed: {self.name} ({duration:.2f}s)")
            else:
                trading_timer.record_time(f"{self.name}_ERROR", duration)
                print(f"❌ Failed: {self.name} ({duration:.2f}s)")
    
    return TimeContext(step_name)


##########################################################################################################################################################
##########################################################################################################################################################
################################################## MEMORY 
##########################################################################################################################################################
##########################################################################################################################################################

def show_memory_status(backtest_mode=False):
    """Display current memory system status"""
    from memory_store import get_memory_stats, get_memory_store
    
    mode_text = "BACKTEST" if backtest_mode else "LIVE"
    print(f"🧠 MEMORY SYSTEM STATUS ({mode_text} MODE)")
    print("=" * 40)
    
    # Get memory stats
    stats = get_memory_stats(backtest_mode)
    memory_store = get_memory_store(backtest_mode)
    
    print(f"📊 Total memories stored: {stats.get('total_memories', 0)}")
    print(f"💾 Database size: {stats.get('database_size_mb', 0):.2f} MB")
    print(f"📁 Database location: {stats.get('database_path', 'Unknown')}")
    
    # Show today's activity
    daily_context = memory_store.get_daily_context()
    print(f"📅 Today's trades: {daily_context['total_trades']}")
    
    # Show recent trades
    if daily_context['total_trades'] > 0:
        print(f"\n📈 Recent trades today:")
        for trade in daily_context['trades'][-3:]:  # Last 3 trades
            print(f"   • {trade['action']} {trade['quantity']} {trade['symbol']} @ ${trade['price']:.2f}")
    
    # Show daily distribution
    if 'daily_counts' in stats and stats['daily_counts']:
        print(f"\n📊 Trading days with stored memories:")
        for date, count in list(stats['daily_counts'].items())[:5]:  # Last 5 days
            print(f"   • {date}: {count} trades")

def test_memory_with_portfolio(backtest_mode=False):
    """Test memory system with your actual portfolio stocks"""
    from memory_store import get_memory_store
    from config import PORTFOLIO_STOCKS
    
    mode_text = "BACKTEST" if backtest_mode else "LIVE"
    print(f"🧪 TESTING MEMORY WITH YOUR PORTFOLIO ({mode_text} MODE)")
    print("=" * 55)
    
    memory_store = get_memory_store(backtest_mode)
    
    # Test symbol history for your actual stocks
    for symbol in PORTFOLIO_STOCKS[:3]:  # Test first 3 stocks
        history = memory_store.get_symbol_trading_history(symbol, days_back=7)
        print(f"📊 {symbol}: {len(history)} trades in last 7 days")
        
        if history:
            latest = history[0]
            print(f"   Latest: {latest['action']} {latest['quantity']} @ ${latest['price']:.2f}")

# Add this to your reporting node or run manually to check memory
def add_memory_info_to_reports(state, backtest_mode=False):
    """Add memory information to your trading reports"""
    try:
        from memory_store import get_memory_stats, get_memory_store
        
        # Get memory stats
        stats = get_memory_stats(backtest_mode)
        memory_store = get_memory_store(backtest_mode)
        daily_context = memory_store.get_daily_context()
        
        # Add to state for reporting
        state['memory_stats'] = {
            'total_memories': stats.get('total_memories', 0),
            'database_size_mb': stats.get('database_size_mb', 0),
            'todays_trades': daily_context['total_trades'],
            'database_path': stats.get('database_path', 'Unknown'),
            'backtest_mode': backtest_mode
        }
        
        mode_text = "BACKTEST" if backtest_mode else "LIVE"
        print(f"📊 {mode_text} Memory: {stats.get('total_memories', 0)} total, {daily_context['total_trades']} today")
        
    except Exception as e:
        print(f"⚠️ Error adding memory info: {e}")
        state['memory_stats'] = {'error': str(e)}
    
    return state

# Example: Add this to your cycle loop
def enhanced_cycle_with_memory(backtest_mode=False):
    """Example of how to integrate memory monitoring in your trading cycle"""
    from memory_store import get_memory_store
    
    mode_text = "BACKTEST" if backtest_mode else "LIVE"
    
    # At the start of each cycle, show memory status
    print("\n" + "="*50)
    print(f"🔄 STARTING TRADING CYCLE ({mode_text} MODE)")
    show_memory_status(backtest_mode)
    
    # Your existing trading cycle code goes here...
    # result_state = await trading_graph.ainvoke(current_state)
    
    # At the end of each cycle, verify memory storage
    print(f"\n🧠 {mode_text} MEMORY VERIFICATION:")
    memory_store = get_memory_store(backtest_mode)
    daily_context = memory_store.get_daily_context()
    print(f"📊 Total trades stored today: {daily_context['total_trades']}")
    
    print("="*50)