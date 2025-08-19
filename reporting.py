# /trading_bot/reporting.py

import json
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from utils import setup_reporting_directory, upload_to_gcs,  ensure_connection, log_portfolio_activity
from config import PORTFOLIO_STOCKS
from market_data import calculate_portfolio_profitability

# Define a type alias for state for clarity
PortfolioState = Dict[str, Any]

# Add these helper functions to your existing reporting.py file

# ADD THIS IMPORT for memory store access:
from memory_store import trading_memory, get_memory_stats

# ADD these helper functions to your reporting.py:

def generate_trading_history_section_html(state: PortfolioState) -> str:
    """Generate comprehensive trading history HTML section"""
    
    try:
        # Get memory statistics
        memory_stats = get_memory_stats()
        
        # Get recent trading history (last 7 days)
        historical_trades = []
        for days_back in range(7):  # Last 7 days
            from datetime import datetime, timedelta
            target_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
            daily_context = trading_memory.get_daily_context(target_date)
            
            if daily_context.get('trades'):
                for trade in daily_context['trades']:
                    trade['trading_date'] = target_date  # Ensure date is set
                    historical_trades.append(trade)
        
        # Sort by timestamp (most recent first)
        historical_trades.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        # Calculate trading statistics
        total_historical_trades = len(historical_trades)
        buy_trades = [t for t in historical_trades if t.get('action') == 'BUY']
        sell_trades = [t for t in historical_trades if t.get('action') == 'SELL']
        total_volume = sum(t.get('quantity', 0) for t in historical_trades)
        
        # Calculate average technical scores
        scored_trades = [t for t in historical_trades if t.get('technical_score', 0) > 0]
        avg_technical_score = sum(t.get('technical_score', 0) for t in scored_trades) / len(scored_trades) if scored_trades else 0
        
        # Group by symbol for symbol breakdown
        symbol_breakdown = {}
        for trade in historical_trades:
            symbol = trade.get('symbol', 'UNKNOWN')
            if symbol not in symbol_breakdown:
                symbol_breakdown[symbol] = {'count': 0, 'total_quantity': 0, 'actions': []}
            symbol_breakdown[symbol]['count'] += 1
            symbol_breakdown[symbol]['total_quantity'] += trade.get('quantity', 0)
            symbol_breakdown[symbol]['actions'].append(trade.get('action', 'UNKNOWN'))
        
        # Build HTML
        html = f"""
        <div class="section trading-history-section">
            <h2>📊 Trading History & Performance Analytics</h2>
            
            <!-- Trading Statistics Summary -->
            <div class="trading-stats-grid">
                <div class="stat-card">
                    <div class="stat-value">{total_historical_trades}</div>
                    <div class="stat-label">Total Historical Trades</div>
                    <div class="stat-sublabel">Last 7 Days</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{len(buy_trades)}</div>
                    <div class="stat-label">Buy Orders</div>
                    <div class="stat-sublabel">{(len(buy_trades)/max(total_historical_trades,1)*100):.1f}% of trades</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{len(sell_trades)}</div>
                    <div class="stat-label">Sell Orders</div>
                    <div class="stat-sublabel">{(len(sell_trades)/max(total_historical_trades,1)*100):.1f}% of trades</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{total_volume:,}</div>
                    <div class="stat-label">Total Volume</div>
                    <div class="stat-sublabel">Shares Traded</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{avg_technical_score:.1f}/10</div>
                    <div class="stat-label">Avg Technical Score</div>
                    <div class="stat-sublabel">AI Confidence Level</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{memory_stats.get('database_size_mb', 0):.1f} MB</div>
                    <div class="stat-label">Memory Database</div>
                    <div class="stat-sublabel">{memory_stats.get('total_memories', 0)} total records</div>
                </div>
            </div>
            
            <!-- Symbol Trading Breakdown -->
            <div class="symbol-breakdown">
                <h3>🎯 Trading Activity by Symbol</h3>
                <div class="symbol-grid">
        """
        
        # Add symbol breakdown cards
        for symbol, data in sorted(symbol_breakdown.items(), key=lambda x: x[1]['count'], reverse=True):
            buy_count = data['actions'].count('BUY')
            sell_count = data['actions'].count('SELL')
            
            html += f"""
                    <div class="symbol-card">
                        <h4>{symbol}</h4>
                        <p><strong>{data['count']}</strong> trades</p>
                        <p><strong>{data['total_quantity']:,}</strong> shares</p>
                        <div class="symbol-actions">
                            <span class="buy-indicator">🟢 {buy_count} BUY</span>
                            <span class="sell-indicator">🔴 {sell_count} SELL</span>
                        </div>
                    </div>
            """
        
        html += """
                </div>
            </div>
            
            <!-- Recent Trading History Table -->
            <div class="recent-trades">
                <h3>📈 Recent Trading History (Last 20 Trades)</h3>
                <div class="table-container">
                    <table class="trading-history-table">
                        <thead>
                            <tr>
                                <th>Date & Time</th>
                                <th>Symbol</th>
                                <th>Action</th>
                                <th>Quantity</th>
                                <th>Price</th>
                                <th>Technical Score</th>
                                <th>News Sentiment</th>
                                <th>Strategy</th>
                                <th>Priority</th>
                                <th>Status</th>
                            </tr>
                        </thead>
                        <tbody>
        """
        
        # Add recent trades (limit to last 20)
        for trade in historical_trades[:20]:
            timestamp = trade.get('timestamp', '')
            try:
                formatted_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00')).strftime('%m/%d %H:%M')
            except:
                formatted_time = timestamp[:16] if timestamp else 'N/A'
            
            symbol = trade.get('symbol', 'N/A')
            action = trade.get('action', 'N/A')
            quantity = trade.get('quantity', 0)
            price = trade.get('price', 0)
            technical_score = trade.get('technical_score', 0)
            news_sentiment = trade.get('news_sentiment', 'NO_DATA')
            strategy_mode = trade.get('strategy_mode', 'BALANCED')
            priority = trade.get('priority', 'LOW')
            status = trade.get('execution_status', 'Unknown')
            
            # CSS classes for styling
            action_class = 'trade-buy' if action == 'BUY' else 'trade-sell' if action == 'SELL' else 'trade-hold'
            sentiment_class = 'sentiment-positive' if news_sentiment == 'POSITIVE' else 'sentiment-negative' if news_sentiment == 'NEGATIVE' else 'sentiment-neutral'
            score_class = 'score-high' if technical_score >= 7 else 'score-medium' if technical_score >= 4 else 'score-low'
            priority_class = f'priority-{priority.lower()}'
            
            html += f"""
                            <tr>
                                <td class="timestamp">{formatted_time}</td>
                                <td class="symbol"><strong>{symbol}</strong></td>
                                <td class="{action_class}"><strong>{action}</strong></td>
                                <td class="quantity">{quantity}</td>
                                <td class="price">${price:.2f}</td>
                                <td class="{score_class}">{technical_score:.1f}/10</td>
                                <td class="{sentiment_class}">{news_sentiment}</td>
                                <td class="strategy">{strategy_mode}</td>
                                <td class="{priority_class}">{priority}</td>
                                <td class="status">{status}</td>
                            </tr>
            """
        
        html += """
                        </tbody>
                    </table>
                </div>
            </div>
            
            <!-- Memory System Status -->
            <div class="memory-status">
                <h3>🧠 Trading Memory System Status</h3>
                <div class="memory-info">
                    <p><strong>Database Location:</strong> {database_path}</p>
                    <p><strong>Total Records:</strong> {total_memories} trading decisions stored</p>
                    <p><strong>Database Size:</strong> {database_size_mb:.2f} MB</p>
                    <p><strong>Daily Distribution:</strong> {daily_count} trading days with data</p>
                </div>
            </div>
        </div>
        """.format(
            database_path=memory_stats.get('database_path', 'N/A'),
            total_memories=memory_stats.get('total_memories', 0),
            database_size_mb=memory_stats.get('database_size_mb', 0),
            daily_count=len(memory_stats.get('daily_counts', {}))
        )
        
        return html
        
    except Exception as e:
        print(f"⚠️ Error generating trading history section: {e}")
        return f"""
        <div class="section">
            <h2>📊 Trading History</h2>
            <p class="error">⚠️ Unable to load trading history: {str(e)}</p>
            <p>This may be because the memory system is not yet initialized or no trades have been stored.</p>
        </div>
        """

def generate_css_for_trading_history() -> str:
    """Generate additional CSS for trading history section"""
    return """
        /* Trading History Section Styles */
        .trading-history-section {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-radius: 12px;
            padding: 25px;
            margin-top: 30px;
        }
        
        .trading-stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }
        
        .stat-card {
            background: rgba(255,255,255,0.1);
            padding: 15px;
            border-radius: 8px;
            text-align: center;
            backdrop-filter: blur(10px);
        }
        
        .stat-value {
            font-size: 2em;
            font-weight: bold;
            color: #fff;
        }
        
        .stat-label {
            font-size: 0.9em;
            margin-top: 5px;
            color: #ecf0f1;
        }
        
        .stat-sublabel {
            font-size: 0.7em;
            color: #bdc3c7;
            margin-top: 3px;
        }
        
        .symbol-breakdown {
            margin: 25px 0;
        }
        
        .symbol-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 15px;
        }
        
        .symbol-card {
            background: rgba(255,255,255,0.08);
            padding: 15px;
            border-radius: 8px;
            border-left: 4px solid #3498db;
        }
        
        .symbol-card h4 {
            margin: 0 0 10px 0;
            font-size: 1.2em;
        }
        
        .symbol-actions {
            margin-top: 10px;
            display: flex;
            justify-content: space-between;
            font-size: 0.8em;
        }
        
        .buy-indicator { color: #2ecc71; }
        .sell-indicator { color: #e74c3c; }
        
        .recent-trades {
            margin: 25px 0;
        }
        
        .table-container {
            background: rgba(255,255,255,0.05);
            border-radius: 8px;
            padding: 15px;
            overflow-x: auto;
        }
        
        .trading-history-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.9em;
        }
        
        .trading-history-table th {
            background: rgba(255,255,255,0.1);
            padding: 12px 8px;
            text-align: left;
            border-bottom: 2px solid rgba(255,255,255,0.2);
            font-weight: bold;
        }
        
        .trading-history-table td {
            padding: 10px 8px;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }
        
        .trading-history-table tr:hover {
            background: rgba(255,255,255,0.05);
        }
        
        /* Action styling */
        .trade-buy { color: #2ecc71; font-weight: bold; }
        .trade-sell { color: #e74c3c; font-weight: bold; }
        .trade-hold { color: #95a5a6; }
        
        /* Sentiment styling */
        .sentiment-positive { color: #2ecc71; }
        .sentiment-negative { color: #e74c3c; }
        .sentiment-neutral { color: #95a5a6; }
        
        /* Technical score styling */
        .score-high { color: #2ecc71; font-weight: bold; }
        .score-medium { color: #f39c12; }
        .score-low { color: #e74c3c; }
        
        /* Priority styling */
        .priority-high { background-color: rgba(231, 76, 60, 0.2); padding: 2px 6px; border-radius: 3px; }
        .priority-medium { background-color: rgba(243, 156, 18, 0.2); padding: 2px 6px; border-radius: 3px; }
        .priority-low { background-color: rgba(149, 165, 166, 0.2); padding: 2px 6px; border-radius: 3px; }
        
        .memory-status {
            background: rgba(255,255,255,0.08);
            padding: 15px;
            border-radius: 8px;
            margin-top: 20px;
        }
        
        .memory-info p {
            margin: 5px 0;
            font-size: 0.9em;
        }
        
        .timestamp { font-family: monospace; font-size: 0.8em; }
        .symbol { font-weight: bold; }
        .quantity { text-align: right; }
        .price { text-align: right; font-family: monospace; }
        .status { font-size: 0.8em; }
        .strategy { font-size: 0.8em; }
    """

def generate_news_section_html(state: PortfolioState) -> str:
    """Generate HTML for the news sentiment analysis section"""
    
    news_sentiment = state.get('news_sentiment', {})
    
    if not news_sentiment:
        return """
        <div class="news-section">
            <div class="news-header">
                <h2>📰 News Sentiment Analysis</h2>
                <p class="no-news">No news data available for this cycle</p>
            </div>
        </div>
        """
    
    # Calculate overall portfolio sentiment
    total_articles = 0
    sentiment_counts = {'POSITIVE': 0, 'NEGATIVE': 0, 'NEUTRAL': 0, 'NO_DATA': 0}
    portfolio_sentiment_score = 0
    stocks_with_news = 0
    
    for symbol, news_data in news_sentiment.items():
        if news_data.get('has_news', False):
            total_articles += news_data.get('article_count', 0)
            sentiment_label = news_data.get('sentiment_label', 'NO_DATA')
            sentiment_counts[sentiment_label] += 1
            
            if sentiment_label != 'NO_DATA':
                portfolio_sentiment_score += news_data.get('sentiment_score', 0)
                stocks_with_news += 1
    
    # Calculate overall portfolio news sentiment
    if stocks_with_news > 0:
        avg_portfolio_sentiment = portfolio_sentiment_score / stocks_with_news
        if avg_portfolio_sentiment > 0.2:
            portfolio_sentiment_label = 'POSITIVE'
            portfolio_sentiment_color = 'sentiment-positive-bg'
            portfolio_emoji = '📈'
        elif avg_portfolio_sentiment < -0.2:
            portfolio_sentiment_label = 'NEGATIVE'
            portfolio_sentiment_color = 'sentiment-negative-bg'
            portfolio_emoji = '📉'
        else:
            portfolio_sentiment_label = 'NEUTRAL'
            portfolio_sentiment_color = 'sentiment-neutral-bg'
            portfolio_emoji = '⚖️'
    else:
        portfolio_sentiment_label = 'NO_DATA'
        portfolio_sentiment_color = 'sentiment-neutral-bg'
        portfolio_emoji = '❓'
        avg_portfolio_sentiment = 0
    
    # Start building the news section HTML
    html = f"""
    <div class="news-section">
        <div class="news-header">
            <h2>📰 News Sentiment Analysis</h2>
            <div class="news-summary">
                <h3>{portfolio_emoji} Portfolio News Overview</h3>
                <p><strong>Overall Sentiment:</strong> 
                   <span class="sentiment-indicator {portfolio_sentiment_color}">{portfolio_sentiment_label}</span>
                   (Score: {avg_portfolio_sentiment:+.2f})</p>
                <p><strong>Total Articles:</strong> {total_articles} across {stocks_with_news} stocks</p>
                <p><strong>Sentiment Breakdown:</strong> 
                   📈 {sentiment_counts['POSITIVE']} Positive | 
                   📉 {sentiment_counts['NEGATIVE']} Negative | 
                   ⚖️ {sentiment_counts['NEUTRAL']} Neutral | 
                   ❓ {sentiment_counts['NO_DATA']} No Data</p>
            </div>
        </div>
        
        <div class="news-grid">
    """
    
    # Add individual stock news cards
    for symbol in PORTFOLIO_STOCKS:
        news_data = news_sentiment.get(symbol, {})
        
        if not news_data:
            # No news data for this symbol
            html += f"""
            <div class="news-card">
                <div class="news-symbol">{symbol}</div>
                <p class="no-news">No news data available</p>
            </div>
            """
            continue
        
        sentiment_label = news_data.get('sentiment_label', 'NO_DATA')
        sentiment_emoji = news_data.get('sentiment_emoji', '❓')
        sentiment_score = news_data.get('sentiment_score', 0)
        article_count = news_data.get('article_count', 0)
        headlines = news_data.get('latest_headlines', [])
        
        # Determine sentiment class for styling
        if sentiment_label == 'POSITIVE':
            sentiment_class = 'sentiment-positive'
        elif sentiment_label == 'NEGATIVE':
            sentiment_class = 'sentiment-negative'
        else:
            sentiment_class = 'sentiment-neutral'
        
        html += f"""
        <div class="news-card">
            <div class="news-symbol">{symbol} {sentiment_emoji}</div>
            <p class="{sentiment_class}">
                <strong>{sentiment_label}</strong> 
                {f"(Score: {sentiment_score:+.2f})" if sentiment_score != 0 else ""}
            </p>
            <div class="news-stats">
                📰 {article_count} articles analyzed
            </div>
        """
        
        # Add headlines if available
        if headlines:
            html += "<div style='margin-top: 10px;'><strong>Recent Headlines:</strong></div>"
            for headline in headlines[:3]:  # Show up to 3 headlines
                # Truncate long headlines
                display_headline = headline[:80] + "..." if len(headline) > 80 else headline
                html += f'<div class="news-headline">{display_headline}</div>'
        else:
            html += '<div class="news-headline">No recent headlines available</div>'
        
        html += "</div>"
    
    # Close the news section
    html += """
        </div>
        
        <div style="text-align: center; margin-top: 20px; color: #ecf0f1; font-size: 0.9em;">
            <p>📊 News sentiment analysis helps inform trading decisions by analyzing market sentiment from recent headlines.</p>
            <p>🔄 Data refreshed automatically during market hours | ⏰ Last updated: """ + datetime.now().strftime('%H:%M:%S') + """</p>
        </div>
    </div>
    """
    
    return html

def add_news_to_state(state: PortfolioState, news_summary: dict) -> PortfolioState:
    """Add news sentiment data to the trading state for reporting"""
    state['news_sentiment'] = news_summary
    
    # Log news activity
    total_articles = sum(data.get('article_count', 0) for data in news_summary.values() if data.get('has_news', False))
    positive_stocks = [symbol for symbol, data in news_summary.items() if data.get('sentiment_label') == 'POSITIVE']
    negative_stocks = [symbol for symbol, data in news_summary.items() if data.get('sentiment_label') == 'NEGATIVE']
    
    log_portfolio_activity("news_sentiment_added_to_state", {
        "total_articles": total_articles,
        "stocks_analyzed": len(news_summary),
        "positive_stocks": len(positive_stocks),
        "negative_stocks": len(negative_stocks),
        "positive_symbols": positive_stocks,
        "negative_symbols": negative_stocks
    })
    
    print(f"📰 News sentiment added to state: {total_articles} articles across {len(news_summary)} stocks")
    return state

# REPLACE your existing generate_html_report function with this enhanced version:

def generate_profitability_section_html(state: PortfolioState) -> str:
    """Generate HTML for the portfolio profitability analysis section"""
    
    # Get current stock data for profitability calculation
    stock_data = state.get('stock_data', {})
    
    # Calculate profitability data
    try:
        profitability_data = calculate_portfolio_profitability(stock_data)
    except Exception as e:
        print(f"⚠️ Error calculating profitability: {e}")
        return """
        <div class="profitability-section">
            <div class="profitability-header">
                <h2>💰 Portfolio Profitability Analysis</h2>
                <p class="no-news">Profitability data unavailable - calculation error</p>
            </div>
        </div>
        """
    
    portfolio_summary = profitability_data.get('portfolio_summary', {})
    individual_stocks = profitability_data.get('individual_stocks', {})
    
    # Extract portfolio-level metrics
    total_investment = portfolio_summary.get('total_investment', 0)
    total_current_value = portfolio_summary.get('total_current_value', 0)
    total_realized_pnl = portfolio_summary.get('total_realized_pnl', 0)
    total_unrealized_pnl = portfolio_summary.get('total_unrealized_pnl', 0)
    total_pnl = portfolio_summary.get('total_pnl', 0)
    total_pnl_pct = portfolio_summary.get('total_pnl_pct', 0)
    calculation_timestamp = portfolio_summary.get('calculation_timestamp', 'N/A')
    
    # Determine overall profit status
    overall_status = 'profit-positive' if total_pnl > 0 else 'profit-negative' if total_pnl < 0 else 'profit-neutral'
    status_emoji = '📈' if total_pnl > 0 else '📉' if total_pnl < 0 else '⚖️'
    status_text = 'PROFITABLE' if total_pnl > 0 else 'LOSS' if total_pnl < 0 else 'BREAKEVEN'
    
    # Start building the profitability section HTML
    html = f"""
    <div class="profitability-section">
        <div class="profitability-header">
            <h2>💰 Portfolio Profitability Analysis</h2>
        </div>
        
        <div class="profitability-summary">
            <h3>{status_emoji} Overall Status: <span class="{overall_status}">{status_text}</span></h3>
            <p><strong>Total P&L:</strong> <span class="{overall_status}">${total_pnl:+,.2f} ({total_pnl_pct:+.2f}%)</span></p>
        </div>
        
        <div class="profitability-grid">
            <div class="profit-metric">
                <h4>💵 Total Investment</h4>
                <p>${total_investment:,.2f}</p>
            </div>
            <div class="profit-metric">
                <h4>💎 Current Value</h4>
                <p>${total_current_value:,.2f}</p>
            </div>
            <div class="profit-metric">
                <h4>✅ Realized P&L</h4>
                <p class="{'profit-positive' if total_realized_pnl > 0 else 'profit-negative' if total_realized_pnl < 0 else 'profit-neutral'}">${total_realized_pnl:+,.2f}</p>
            </div>
            <div class="profit-metric">
                <h4>📊 Unrealized P&L</h4>
                <p class="{'profit-positive' if total_unrealized_pnl > 0 else 'profit-negative' if total_unrealized_pnl < 0 else 'profit-neutral'}">${total_unrealized_pnl:+,.2f}</p>
            </div>
            <div class="profit-metric">
                <h4>🎯 Total Return</h4>
                <p class="{overall_status}">{total_pnl_pct:+.2f}%</p>
            </div>
        </div>
        
        <div class="profitability-table">
            <table>
                <tr>
                    <th>Stock</th>
                    <th>Position</th>
                    <th>Avg Cost</th>
                    <th>Current Price</th>
                    <th>Total Invested</th>
                    <th>Current Value</th>
                    <th>Unrealized P&L</th>
                    <th>Return %</th>
                    <th>Status</th>
                </tr>
    """
    
    # Add individual stock rows
    for symbol in PORTFOLIO_STOCKS:
        stock_profit = individual_stocks.get(symbol, {})
        position = stock_profit.get('position', 0)
        avg_cost = stock_profit.get('avg_cost', 0)
        current_price = stock_profit.get('current_price', 0)
        total_invested = stock_profit.get('total_invested', 0)
        current_value = stock_profit.get('current_value', 0)
        unrealized_pnl = stock_profit.get('unrealized_pnl', 0)
        unrealized_pnl_pct = stock_profit.get('unrealized_pnl_pct', 0)
        
        # Determine profit class and status
        profit_class = 'profit-positive' if unrealized_pnl > 0 else 'profit-negative' if unrealized_pnl < 0 else 'profit-neutral'
        status_symbol = '📈' if unrealized_pnl > 0 else '📉' if unrealized_pnl < 0 else '⚖️'
        
        # Only show rows for stocks with positions or recent activity
        if position > 0 or total_invested > 0:
            html += f"""
                <tr>
                    <td><strong>{symbol}</strong></td>
                    <td class="position-size">{position:,}</td>
                    <td class="avg-cost">${avg_cost:.2f}</td>
                    <td class="current-price">${current_price:.2f}</td>
                    <td>${total_invested:,.2f}</td>
                    <td>${current_value:,.2f}</td>
                    <td class="{profit_class}">${unrealized_pnl:+,.2f}</td>
                    <td class="{profit_class}">{unrealized_pnl_pct:+.1f}%</td>
                    <td>{status_symbol}</td>
                </tr>
            """
        else:
            html += f"""
                <tr>
                    <td><strong>{symbol}</strong></td>
                    <td class="position-size">0</td>
                    <td class="avg-cost">-</td>
                    <td class="current-price">${current_price:.2f}</td>
                    <td>$0.00</td>
                    <td>$0.00</td>
                    <td class="profit-neutral">$0.00</td>
                    <td class="profit-neutral">0.0%</td>
                    <td>-</td>
                </tr>
            """
    
    # Close the profitability section
    html += f"""
            </table>
        </div>
        
        <div style="text-align: center; margin-top: 20px; color: #ecf0f1; font-size: 0.9em;">
            <p>💡 Profitability calculated from trade history • Last updated: {calculation_timestamp[:19].replace('T', ' ')}</p>
        </div>
    </div>
    """
    
    return html

def generate_html_report(state: PortfolioState):
    """Generate comprehensive HTML report with ENHANCED validation, trade, and NEWS information"""
    reports_dir = setup_reporting_directory()
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"portfolio_report_{timestamp}.html"
    filepath = reports_dir / filename

    # Basic state data
    portfolio_value = state.get('total_portfolio_value', 0)
    total_pnl = state.get('total_unrealized_pnl', 0)
    
    # CSS classes for positive/negative values
    pnl_class = 'positive' if total_pnl > 0 else 'negative' if total_pnl < 0 else 'neutral'

    # Start building HTML string with enhanced styling INCLUDING NEWS STYLES
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>AI Trading Report - {timestamp}</title>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 20px; background-color: #f9f9f9; }}
            .header {{ background: #4a69bd; color: white; padding: 20px; border-radius: 8px; text-align: center; }}
            .metric-card {{ background: white; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); text-align: center; }}
            .metrics {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; margin: 20px 0; }}
            .positive {{ color: #2ecc71; }} .negative {{ color: #e74c3c; }} .neutral {{ color: #7f8c8d; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
            th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
            th {{ background-color: #f2f2f2; }}
            .section {{ background: white; padding: 20px; border-radius: 8px; margin-top: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
            .trade-card {{ background: #f8f9fa; border-left: 4px solid #007bff; padding: 15px; margin: 10px 0; border-radius: 4px; }}
            .trade-buy {{ border-left-color: #28a745; }}
            .trade-sell {{ border-left-color: #dc3545; }}
            .trade-details {{ font-size: 0.9em; color: #666; margin-top: 8px; }}
            .priority-high {{ background-color: #fff3cd; }}
            .priority-medium {{ background-color: #d1ecf1; }}
            .priority-low {{ background-color: #d4edda; }}
            .validation-step {{ padding: 10px; margin: 5px 0; border-radius: 4px; }}
            .validation-proceed {{ background-color: #d4edda; border-left: 4px solid #28a745; }}
            .validation-rerun {{ background-color: #f8d7da; border-left: 4px solid #dc3545; }}
            .reasoning {{ font-style: italic; color: #495057; }}
            .order-status {{ font-weight: bold; }}
            .execution-time {{ color: #6c757d; font-size: 0.8em; }}
            
            /* NEWS SECTION STYLES */
            .news-section {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 8px; margin-top: 20px; }}
            .news-header {{ text-align: center; margin-bottom: 20px; }}
            .news-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }}
            .news-card {{ background: rgba(255,255,255,0.1); border-radius: 8px; padding: 15px; backdrop-filter: blur(10px); }}
            .news-symbol {{ font-size: 1.2em; font-weight: bold; margin-bottom: 10px; }}
            .sentiment-positive {{ color: #2ecc71; font-weight: bold; }}
            .sentiment-negative {{ color: #e74c3c; font-weight: bold; }}
            .sentiment-neutral {{ color: #95a5a6; font-weight: bold; }}
            .news-headline {{ background: rgba(255,255,255,0.05); padding: 8px; margin: 5px 0; border-radius: 4px; font-size: 0.9em; }}
            .news-stats {{ font-size: 0.8em; color: #ecf0f1; margin-top: 10px; }}
            .no-news {{ text-align: center; color: #bdc3c7; font-style: italic; }}
            .news-summary {{ background: rgba(255,255,255,0.15); padding: 15px; border-radius: 8px; margin-bottom: 20px; }}
            .sentiment-indicator {{ display: inline-block; padding: 4px 8px; border-radius: 12px; font-size: 0.8em; margin-left: 8px; }}
            .sentiment-positive-bg {{ background-color: #2ecc71; color: white; }}
            .sentiment-negative-bg {{ background-color: #e74c3c; color: white; }}
            .sentiment-neutral-bg {{ background-color: #95a5a6; color: white; }}
            
            /* PROFITABILITY SECTION STYLES */
            .profitability-section {{ background: linear-gradient(135deg, #26a69a 0%, #4caf50 100%); color: white; padding: 20px; border-radius: 8px; margin-top: 20px; }}
            .profitability-header {{ text-align: center; margin-bottom: 20px; }}
            .profitability-summary {{ background: rgba(255,255,255,0.15); padding: 15px; border-radius: 8px; margin-bottom: 20px; text-align: center; }}
            .profitability-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 15px; margin-bottom: 20px; }}
            .profit-metric {{ background: rgba(255,255,255,0.1); padding: 12px; border-radius: 6px; text-align: center; }}
            .profit-metric h4 {{ margin: 0 0 8px 0; font-size: 0.9em; opacity: 0.8; }}
            .profit-metric p {{ margin: 0; font-size: 1.1em; font-weight: bold; }}
            .profitability-table {{ background: rgba(255,255,255,0.95); color: #333; border-radius: 8px; overflow: hidden; }}
            .profitability-table table {{ margin: 0; }}
            .profitability-table th {{ background-color: rgba(76, 175, 80, 0.1); color: #2e7d32; }}
            .profit-positive {{ color: #2ecc71; font-weight: bold; }}
            .profit-negative {{ color: #e74c3c; font-weight: bold; }}
            .profit-neutral {{ color: #95a5a6; font-weight: bold; }}
            .position-size {{ font-weight: bold; color: #34495e; }}
            .avg-cost {{ color: #5d6d7e; }}
            .current-price {{ color: #2c3e50; font-weight: bold; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🤖 AI Portfolio Trading Report</h1>
            <p>Session: {state.get('session_id', 'N/A')} | Cycle: {state.get('cycle_number', 'N/A')} | Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p>Strategy Mode: {"🔥 AGGRESSIVE" if state.get('aggressive_mode') else "⚖️ BALANCED"}</p>
        </div>

        <div class="metrics">
            <div class="metric-card"><h3>Portfolio Value</h3><p class="neutral">${portfolio_value:,.2f}</p></div>
            <div class="metric-card"><h3>Total P&L</h3><p class="{pnl_class}">${total_pnl:+,.2f}</p></div>
            <div class="metric-card"><h3>Total Trades</h3><p class="neutral">{state.get('total_trades', 0)}</p></div>
            <div class="metric-card"><h3>Cash Available</h3><p class="neutral">${state.get('cash_available', 0):,.2f}</p></div>
            <div class="metric-card"><h3>Validation Attempts</h3><p class="neutral">{state.get('validation_attempts', 0)}</p></div>
            """
    
    # Add S&P 500 metrics to the metrics div
    sp500_data = state.get('sp500_data', {})
    benchmark_data = state.get('benchmark_comparison', {})
    
    if sp500_data.get('success'):
        sp500_price = sp500_data.get('price', 0)
        sp500_change = sp500_data.get('change_pct', 0)
        sp500_class = 'positive' if sp500_change > 0 else 'negative' if sp500_change < 0 else 'neutral'
        
        html += f"""
            <div class="metric-card"><h3>📈 S&P 500</h3><p class="neutral">${sp500_price:.2f}</p></div>
            <div class="metric-card"><h3>S&P Change</h3><p class="{sp500_class}">{sp500_change:+.2f}%</p></div>
        """
        
        if 'error' not in benchmark_data:
            alpha = benchmark_data.get('alpha', 0)
            portfolio_return = benchmark_data.get('portfolio_return_pct', 0)
            alpha_class = 'positive' if alpha > 0 else 'negative' if alpha < 0 else 'neutral'
            portfolio_return_class = 'positive' if portfolio_return > 0 else 'negative' if portfolio_return < 0 else 'neutral'
            status_text = "OUTPERFORMING" if alpha > 0 else "UNDERPERFORMING" if alpha < 0 else "MATCHING"
            
            html += f"""
            <div class="metric-card"><h3>Portfolio Return</h3><p class="{portfolio_return_class}">{portfolio_return:+.2f}%</p></div>
            <div class="metric-card"><h3>⚖️ Alpha</h3><p class="{alpha_class}">{alpha:+.2f}%</p></div>
            <div class="metric-card"><h3>🏆 Status</h3><p class="{alpha_class}">{status_text}</p></div>
            """
    else:
        html += """
            <div class="metric-card"><h3>📈 S&P 500</h3><p class="neutral">Unavailable</p></div>
        """
    
    html += """
        </div>
        
        <div class="section">
            <h2>📊 Current Holdings</h2>
            <table>
                <tr><th>Stock</th><th>Position</th><th>Price</th><th>P&L</th><th>Allocation</th><th>AI Action</th><th>Technical Score</th><th>News Sentiment</th></tr>
    """

    # Enhanced holdings table with news sentiment column
    news_sentiment = state.get('news_sentiment', {})
    for symbol in PORTFOLIO_STOCKS:
        pos = state.get('positions', {}).get(symbol, 0)
        price = state.get('stock_prices', {}).get(symbol, 0)
        pnl = state.get('stock_pnls', {}).get(symbol, 0)
        alloc = state.get('portfolio_allocation', {}).get(symbol, 0)
        rec = state.get('ai_recommendations', {}).get(symbol, {})
        action = rec.get('action', 'N/A')
        tech_score = rec.get('technical_score', 'N/A')
        pnl_class_row = 'positive' if pnl > 0 else 'negative' if pnl < 0 else 'neutral'
        
        # Get news sentiment for this symbol
        news_data = news_sentiment.get(symbol, {})
        sentiment_label = news_data.get('sentiment_label', 'NO_DATA')
        sentiment_emoji = news_data.get('sentiment_emoji', '❓')
        sentiment_class = 'sentiment-positive' if sentiment_label == 'POSITIVE' else 'sentiment-negative' if sentiment_label == 'NEGATIVE' else 'sentiment-neutral'
        
        html += f"""<tr>
            <td><strong>{symbol}</strong></td>
            <td>{pos}</td>
            <td>${price:.2f}</td>
            <td class='{pnl_class_row}'>${pnl:+.2f}</td>
            <td>{alloc:.1f}%</td>
            <td>{action}</td>
            <td>{tech_score if isinstance(tech_score, str) else f'{tech_score:.1f}/10'}</td>
            <td class='{sentiment_class}'>{sentiment_emoji} {sentiment_label}</td>
        </tr>"""

    html += "</table></div>"

    # ENHANCED Executed Trades Section (keeping your existing code)
    html += "<div class='section'><h2>⚡ Executed Trades in This Cycle</h2>"
    executed_trades = state.get('executed_trades', [])
    if executed_trades:
        for i, trade in enumerate(executed_trades, 1):
            action = trade.get('action', 'UNKNOWN')
            symbol = trade.get('symbol', 'N/A')
            quantity = trade.get('quantity', 0)
            price = trade.get('price', 0)
            priority = trade.get('priority', 'LOW')
            reasoning = trade.get('reasoning', 'No reasoning provided')
            order_id = trade.get('order_id', 'N/A')
            status = trade.get('status', 'Unknown')
            filled = trade.get('filled', 0)
            remaining = trade.get('remaining', 0)
            avg_fill_price = trade.get('avg_fill_price', 0)
            execution_time = trade.get('execution_time', 0)
            estimated_cost = trade.get('estimated_cost', 0)
            estimated_proceeds = trade.get('estimated_proceeds', 0)
            
            trade_class = 'trade-buy' if action == 'BUY' else 'trade-sell'
            priority_class = f'priority-{priority.lower()}'
            action_emoji = '🟢' if action == 'BUY' else '🔴'
            
            html += f"""
            <div class="trade-card {trade_class} {priority_class}">
                <h4>{action_emoji} Trade #{i}: {action} {quantity} {symbol}</h4>
                <div class="trade-details">
                    <p><strong>Price:</strong> ${price:.2f} | <strong>Priority:</strong> {priority} | <strong>Order ID:</strong> {order_id}</p>
                    <p><strong>Status:</strong> <span class="order-status">{status}</span> | <strong>Filled:</strong> {filled}/{quantity} shares</p>
                    {f'<p><strong>Avg Fill Price:</strong> ${avg_fill_price:.2f}</p>' if avg_fill_price > 0 else ''}
                    <p><strong>Estimated {"Cost" if action == "BUY" else "Proceeds"}:</strong> ${estimated_cost if action == "BUY" else estimated_proceeds:,.2f}</p>
                    <p class="reasoning"><strong>AI Reasoning:</strong> {reasoning}</p>
                    <p class="execution-time">Execution Time: {execution_time:.2f}s | Timestamp: {trade.get('timestamp', 'N/A')}</p>
                </div>
            </div>
            """
    else:
        html += "<p>No trades executed in this cycle.</p>"
    html += "</div>"

    # ENHANCED Validation Log Section (keeping your existing code)
    html += "<div class='section'><h2>🕵️ Decision Validation Process</h2>"
    validation_history = state.get('validation_history', [])
    if validation_history:
        for attempt in validation_history:
            decision = attempt.get('decision', 'unknown')
            reason = attempt.get('reason', 'No reason provided')
            attempt_num = attempt.get('attempt', 0)
            timestamp = attempt.get('timestamp', 'N/A')
            
            if decision == 'proceed':
                status_class = 'validation-proceed'
                status_icon = '✅'
                status_text = 'VALIDATION PASSED'
            else:
                status_class = 'validation-rerun'
                status_icon = '🔄'
                status_text = 'VALIDATION FAILED - RERUN REQUIRED'
            
            html += f"""
            <div class="validation-step {status_class}">
                <h4>{status_icon} Attempt #{attempt_num}: {status_text}</h4>
                <p><strong>Timestamp:</strong> {timestamp}</p>
                <p><strong>Reason:</strong> {reason}</p>
            </div>
            """
        
        # Add final decision logic
        final_logic = state.get('final_decision_logic', 'N/A')
        html += f"""
        <div class="validation-step" style="background-color: #e9ecef; border-left: 4px solid #6c757d;">
            <h4>🎯 Final Decision Logic</h4>
            <p>{final_logic}</p>
        </div>
        """
    else:
        html += "<p>No validation performed in this cycle.</p>"
    html += "</div>"

    # AI Recommendations Analysis Section (keeping your existing code)
    html += "<div class='section'><h2>🧠 AI Recommendations Analysis</h2>"
    ai_recommendations = state.get('ai_recommendations', {})
    if ai_recommendations:
        html += "<table><tr><th>Symbol</th><th>Action</th><th>Priority</th><th>Technical Score</th><th>Reasoning</th><th>Confidence</th></tr>"
        for symbol, rec in ai_recommendations.items():
            action = rec.get('action', 'HOLD')
            priority = rec.get('priority', 'LOW')
            tech_score = rec.get('technical_score', 'N/A')
            reasoning = rec.get('reasoning', 'No reasoning provided')
            confidence = rec.get('confidence', 'N/A')
            
            action_color = 'positive' if action == 'BUY' else 'negative' if action == 'SELL' else 'neutral'
            
            html += f"""<tr>
                <td><strong>{symbol}</strong></td>
                <td class="{action_color}">{action}</td>
                <td>{priority}</td>
                <td>{tech_score if isinstance(tech_score, str) else f'{tech_score:.1f}/10'}</td>
                <td class="reasoning">{reasoning}</td>
                <td>{confidence}</td>
            </tr>"""
        html += "</table>"
    else:
        html += "<p>No AI recommendations generated in this cycle.</p>"
    html += "</div>"

    # AI Trend Analysis Section (keeping your existing code)
    html += "<div class='section'><h2>📈 AI Trend Analysis</h2>"
    ai_trends = state.get('ai_trend_analysis', {})
    if ai_trends:
        html += "<table><tr><th>Symbol</th><th>Trend</th><th>Confidence</th><th>Risk Level</th><th>Technical Strength</th><th>Reasoning</th></tr>"
        for symbol, trend in ai_trends.items():
            trend_direction = trend.get('trend', 'NEUTRAL')
            confidence = trend.get('confidence', 'LOW')
            risk = trend.get('risk_level', 'HIGH')
            tech_strength = trend.get('technical_strength', 'N/A')
            reasoning = trend.get('reasoning', 'No analysis provided')
            
            trend_color = 'positive' if trend_direction == 'BULLISH' else 'negative' if trend_direction == 'BEARISH' else 'neutral'
            
            html += f"""<tr>
                <td><strong>{symbol}</strong></td>
                <td class="{trend_color}">{trend_direction}</td>
                <td>{confidence}</td>
                <td>{risk}</td>
                <td>{tech_strength}</td>
                <td class="reasoning">{reasoning}</td>
            </tr>"""
        html += "</table>"
    else:
        html += "<p>No AI trend analysis available.</p>"
    html += "</div>"

    # ADD THE NEW TRADING HISTORY SECTION
    html += generate_trading_history_section_html(state)
    
    # NEW: ADD PROFITABILITY SECTION BEFORE NEWS
    html += generate_profitability_section_html(state)
    
    # NEW: ADD NEWS SECTION AT THE BOTTOM
    html += generate_news_section_html(state)

    html += "</body></html>"

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"📄 Enhanced HTML Report with News saved: {filepath}")
    gcs_path = f"{datetime.now().strftime('%Y/%m/%d')}/{filename}"
    upload_to_gcs(str(filepath), gcs_path)
    return str(filepath)

# Helper function to easily add news to your trading cycle
async def add_news_to_current_cycle(state: PortfolioState) -> PortfolioState:
    """Simple function to add news to any existing cycle"""
    try:
        from news_working import get_news_summary_for_trading
        
        print("📰 Adding news sentiment to current cycle...")
        news_summary = await get_news_summary_for_trading()
        
        if news_summary:
            state = add_news_to_state(state, news_summary)
            print(f"✅ News added! {sum(d.get('article_count', 0) for d in news_summary.values())} total articles")
        else:
            state['news_sentiment'] = {}
            print("⚠️ No news data retrieved")
        
        return state
    
    except Exception as e:
        print(f"❌ Error adding news: {e}")
        state['news_sentiment'] = {}
        return state

def generate_json_report(state: PortfolioState):
    """Generate detailed JSON report with ENHANCED trade and validation capture"""
    reports_dir = setup_reporting_directory()
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"portfolio_data_{timestamp}.json"
    filepath = reports_dir / filename

    # Create enhanced report structure
    enhanced_report = {
        'report_metadata': {
            'generated_at': datetime.now().isoformat(),
            'session_id': state.get('session_id', 'N/A'),
            'cycle_number': state.get('cycle_number', 0),
            'strategy_mode': 'AGGRESSIVE' if state.get('aggressive_mode') else 'BALANCED',
            'report_version': '2.0_enhanced'
        },
        'portfolio_summary': {
            'total_portfolio_value': state.get('total_portfolio_value', 0),
            'total_unrealized_pnl': state.get('total_unrealized_pnl', 0),
            'cash_available': state.get('cash_available', 0),
            'total_trades': state.get('total_trades', 0),
            'validation_attempts': state.get('validation_attempts', 0)
        },
        'positions': state.get('positions', {}),
        'stock_prices': state.get('stock_prices', {}),
        'stock_pnls': state.get('stock_pnls', {}),
        'portfolio_allocation': state.get('portfolio_allocation', {}),
        'ai_recommendations': state.get('ai_recommendations', {}),
        'ai_trend_analysis': state.get('ai_trend_analysis', {}),
        'executed_trades_detailed': state.get('executed_trades', []),
        'validation_process': {
            'validation_history': state.get('validation_history', []),
            'final_decision_logic': state.get('final_decision_logic', 'N/A'),
            'validation_feedback': state.get('validation_feedback', ''),
            'total_attempts': state.get('validation_attempts', 0)
        },
        'technical_analysis_summary': {},
        'execution_performance': {
            'total_execution_time': 0,
            'successful_trades': len([t for t in state.get('executed_trades', []) if t.get('status') in ['Filled', 'Submitted']]),
            'failed_trades': len([t for t in state.get('executed_trades', []) if t.get('status') not in ['Filled', 'Submitted', 'Unknown']]),
            'avg_execution_time': 0
        },
        'raw_state_data': state  # Keep complete state for debugging
    }

    # Calculate execution performance metrics
    executed_trades = state.get('executed_trades', [])
    if executed_trades:
        total_exec_time = sum(t.get('execution_time', 0) for t in executed_trades)
        enhanced_report['execution_performance']['total_execution_time'] = total_exec_time
        enhanced_report['execution_performance']['avg_execution_time'] = total_exec_time / len(executed_trades)

    # Add technical analysis summary
    for symbol in PORTFOLIO_STOCKS:
        stock_data = state.get('stock_data', {}).get(symbol, {})
        if stock_data.get('valid', False):
            enhanced_report['technical_analysis_summary'][symbol] = {
                'current_price': stock_data.get('current_price', 0),
                'rsi': stock_data.get('rsi', 50),
                'sma_20': stock_data.get('sma_20', 0),
                'sma_50': stock_data.get('sma_50', 0),
                'macd_histogram': stock_data.get('macd_histogram', 0),
                'volume_ratio': stock_data.get('current_volume', 0) / max(stock_data.get('volume_ma', 1), 1),
                'daily_change_pct': stock_data.get('daily_change_pct', 0),
                'volatility_20': stock_data.get('volatility_20', 0)
            }

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(enhanced_report, f, indent=2, default=str)
        
    print(f"📊 Enhanced JSON Report saved: {filepath}")
    return str(filepath)

def generate_csv_report(state: PortfolioState):
    """Generate ENHANCED CSV reports for portfolio summary and detailed trades"""
    reports_dir = setup_reporting_directory()
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Enhanced Portfolio Summary CSV
    summary_filename = f"portfolio_summary_{timestamp}.csv"
    summary_filepath = reports_dir / summary_filename
    
    summary_data = []
    for symbol in PORTFOLIO_STOCKS:
        rec = state.get('ai_recommendations', {}).get(symbol, {})
        trend = state.get('ai_trend_analysis', {}).get(symbol, {})
        stock_data = state.get('stock_data', {}).get(symbol, {})
        
        summary_data.append({
            'Timestamp': datetime.now().isoformat(),
            'Session_ID': state.get('session_id', 'N/A'),
            'Cycle_Number': state.get('cycle_number', 0),
            'Symbol': symbol,
            'Current_Price': state.get('stock_prices', {}).get(symbol, 0),
            'Position': state.get('positions', {}).get(symbol, 0),
            'Unrealized_PnL': state.get('stock_pnls', {}).get(symbol, 0),
            'Portfolio_Allocation_Pct': state.get('portfolio_allocation', {}).get(symbol, 0),
            'AI_Action': rec.get('action', 'N/A'),
            'AI_Priority': rec.get('priority', 'N/A'),
            'AI_Reasoning': rec.get('reasoning', 'N/A'),
            'Technical_Score': rec.get('technical_score', 0),
            'AI_Confidence': rec.get('confidence', 'N/A'),
            'AI_Trend': trend.get('trend', 'N/A'),
            'Trend_Confidence': trend.get('confidence', 'N/A'),
            'Risk_Level': trend.get('risk_level', 'N/A'),
            'RSI': stock_data.get('rsi', 50),
            'SMA_20': stock_data.get('sma_20', 0),
            'SMA_50': stock_data.get('sma_50', 0),
            'MACD_Histogram': stock_data.get('macd_histogram', 0),
            'Daily_Change_Pct': stock_data.get('daily_change_pct', 0),
            'Volume_Ratio': stock_data.get('current_volume', 0) / max(stock_data.get('volume_ma', 1), 1),
            'Strategy_Mode': 'AGGRESSIVE' if state.get('aggressive_mode') else 'BALANCED'
        })
    
    pd.DataFrame(summary_data).to_csv(summary_filepath, index=False)
    print(f"📋 Enhanced Summary CSV saved: {summary_filepath}")

    # Enhanced Detailed Trades CSV
    executed_trades = state.get('executed_trades', [])
    if executed_trades:
        trades_filename = f"executed_trades_{timestamp}.csv"
        trades_filepath = reports_dir / trades_filename
        
        # Enhance trade data with additional context
        enhanced_trades_data = []
        for trade in executed_trades:
            enhanced_trade = {
                'Session_ID': state.get('session_id', 'N/A'),
                'Cycle_Number': state.get('cycle_number', 0),
                'Strategy_Mode': 'AGGRESSIVE' if state.get('aggressive_mode') else 'BALANCED',
                **trade,  # Include all original trade fields
                'Portfolio_Value_At_Trade': state.get('total_portfolio_value', 0),
                'Cash_Available_At_Trade': state.get('cash_available', 0),
                'Total_Trades_So_Far': state.get('total_trades', 0)
            }
            enhanced_trades_data.append(enhanced_trade)
        
        pd.DataFrame(enhanced_trades_data).to_csv(trades_filepath, index=False)
        print(f"📈 Enhanced Trades CSV saved: {trades_filepath}")

    # Validation History CSV
    validation_history = state.get('validation_history', [])
    if validation_history:
        validation_filename = f"validation_history_{timestamp}.csv"
        validation_filepath = reports_dir / validation_filename
        
        validation_data = []
        for validation in validation_history:
            validation_data.append({
                'Session_ID': state.get('session_id', 'N/A'),
                'Cycle_Number': state.get('cycle_number', 0),
                'Strategy_Mode': 'AGGRESSIVE' if state.get('aggressive_mode') else 'BALANCED',
                **validation
            })
        
        pd.DataFrame(validation_data).to_csv(validation_filepath, index=False)
        print(f"🕵️ Validation History CSV saved: {validation_filepath}")

    return str(summary_filepath)




# === ENHANCED PERFORMANCE SUMMARY REPORT (REVISED) ===
def generate_performance_summary_report(state: PortfolioState):
    """Generate performance summary report with advanced metrics"""
    reports_dir = setup_reporting_directory()
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"performance_summary_{timestamp}.html"
    filepath = reports_dir / filename

    cycle_history = state.get('cycle_history', [])
    if len(cycle_history) < 2:
        print("Not enough cycle history to generate a performance report.")
        return

    # --- 1. METRIC CALCULATIONS ---
    # Basic Performance
    initial_value = cycle_history[0].get('total_portfolio_value', 0)
    current_value = cycle_history[-1].get('total_portfolio_value', 0)
    total_return = current_value - initial_value
    return_pct = (total_return / initial_value * 100) if initial_value > 0 else 0
    total_trades = cycle_history[-1].get('total_trades', 0)
    avg_trades_per_cycle = total_trades / len(cycle_history)

    # Trade Analysis
    executed_trades = state.get('executed_trades', [])
    sell_trades = [t for t in executed_trades if t.get('action') == 'SELL' and 'net_profit' in t]
    win_count = len([t for t in sell_trades if t['net_profit'] > 0])
    loss_count = len([t for t in sell_trades if t['net_profit'] <= 0])
    total_win_loss_trades = win_count + loss_count
    win_rate_pct = (win_count / total_win_loss_trades * 100) if total_win_loss_trades > 0 else 0
    win_loss_ratio = win_count / loss_count if loss_count > 0 else float(win_count > 0)

    total_wins = sum(t['net_profit'] for t in sell_trades if t['net_profit'] > 0)
    total_losses = sum(t['net_profit'] for t in sell_trades if t['net_profit'] <= 0)
    profit_factor = total_wins / abs(total_losses) if total_losses < 0 else float('inf') if total_wins > 0 else 0

    # Advanced Metrics
    portfolio_returns = pd.Series([c.get('total_portfolio_value', 0) for c in cycle_history]).pct_change().dropna()
    sharpe_ratio = (portfolio_returns.mean() / portfolio_returns.std()) * (252**0.5) if portfolio_returns.std() > 0 else 0.0
    pnl_by_cycle = [cycle.get('total_unrealized_pnl', 0) for cycle in cycle_history]
    best_pnl = max(pnl_by_cycle) if pnl_by_cycle else 0
    worst_pnl = min(pnl_by_cycle) if pnl_by_cycle else 0

    # System Diagnostics
    connected_cycles = sum(1 for c in cycle_history if c.get('connection_status', False))
    connection_rate = (connected_cycles / len(cycle_history) * 100)
    avg_data_quality = sum(c.get('data_quality', 0) for c in cycle_history) / len(cycle_history)

    # Validation System
    total_validation_attempts = sum(c.get('validation_attempts', 0) for c in cycle_history)
    cycles_with_validation = sum(1 for c in cycle_history if c.get('validation_attempts', 0) > 0)
    avg_validation_per_cycle = total_validation_attempts / len(cycle_history)

    # --- 2. DYNAMIC CONTENT PRE-CALCULATION ---
    # CSS Classes for Metric Cards
    return_pct_class = 'positive' if return_pct > 0 else 'negative' if return_pct < 0 else 'neutral'
    total_return_class = 'positive' if total_return > 0 else 'negative' if total_return < 0 else 'neutral'
    sharpe_ratio_class = 'positive' if sharpe_ratio >= 1 else 'negative' if sharpe_ratio < 0 else 'neutral'
    win_loss_ratio_class = 'positive' if win_loss_ratio >= 1 else 'negative'
    profit_factor_class = 'positive' if profit_factor >= 1.5 else 'negative' if profit_factor < 1 else 'neutral'

    # Descriptive Text for Insights
    sharpe_interpretation = 'excellent' if sharpe_ratio > 2 else 'good' if sharpe_ratio > 1 else 'moderate' if sharpe_ratio > 0 else 'poor'
    validation_engagement = 'Actively engaged' if cycles_with_validation > len(cycle_history) * 0.1 else 'Minimal engagement'

    # --- 3. HTML STRING CONSTRUCTION ---
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Enhanced Performance Summary Report - {timestamp}</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; background-color: #f5f5f5; }}
            .header {{ background: linear-gradient(135deg, #4854c7 0%, #3a3897 100%); color: white; padding: 30px; border-radius: 10px; text-align: center; }}
            .metrics {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin: 20px 0; }}
            .metric-card {{ background: white; padding: 25px; border-radius: 10px; text-align: center; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
            .metric-value {{ font-size: 2.5em; font-weight: bold; color: #333; }}
            .metric-label {{ color: #666; margin-top: 10px; font-size: 1.1em; }}
            .positive {{ color: #28a745; }}
            .negative {{ color: #dc3545; }}
            .neutral {{ color: #6c757d; }}
            .performance-chart {{ background: white; padding: 25px; margin: 20px 0; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
            .cycle-table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
            .cycle-table th, .cycle-table td {{ padding: 12px; text-align: center; border-bottom: 1px solid #ddd; }}
            .cycle-table th {{ background-color: #f8f9fa; font-weight: bold; }}
            .insights, .validation-insights, .diagnostic {{ padding: 25px; margin: 20px 0; border-radius: 10px; }}
            .insights {{ background-color: #e8f4fd; border-left: 5px solid #007bff; }}
            .validation-insights {{ background-color: #e9f5e9; border-left: 5px solid #28a745; }}
            .diagnostic {{ background-color: #fff3cd; border-left: 5px solid #ffc107; }}
            .footer {{ text-align: center; color: #666; margin-top: 40px; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>📈 Enhanced Performance Summary</h1>
            <h2>Session: {state.get('session_id', 'N/A')}</h2>
            <p>Cycles Analyzed: {len(cycle_history)} | Period: {cycle_history[0].get('timestamp', 'N/A')} - {cycle_history[-1].get('timestamp', 'N/A')}</p>
        </div>

        <div class="metrics">
            <div class="metric-card">
                <div class="metric-value {return_pct_class}">{return_pct:+.2f}%</div>
                <div class="metric-label">Total Return</div>
            </div>
            <div class="metric-card">
                <div class="metric-value {sharpe_ratio_class}">{sharpe_ratio:.2f}</div>
                <div class="metric-label">Sharpe Ratio</div>
            </div>
            <div class="metric-card">
                <div class="metric-value {profit_factor_class}">{profit_factor:.2f}</div>
                <div class="metric-label">Profit Factor</div>
            </div>
            <div class="metric-card">
                <div class="metric-value {win_loss_ratio_class}">{win_loss_ratio:.2f}</div>
                <div class="metric-label">Win/Loss Ratio</div>
            </div>
            <div class="metric-card">
                <div class="metric-value positive">${best_pnl:+,.2f}</div>
                <div class="metric-label">Best Cycle P&L</div>
            </div>
            <div class="metric-card">
                <div class="metric-value negative">${worst_pnl:+,.2f}</div>
                <div class="metric-label">Worst Cycle P&L</div>
            </div>
        </div>

        <div class="insights">
            <h2>💡 Performance Insights</h2>
            <ul>
                <li><strong>Portfolio Growth:</strong> Achieved a total return of <strong>{return_pct:+.2f}%</strong> (${total_return:+,.2f}).</li>
                <li><strong>Risk-Adjusted Return:</strong> The Sharpe Ratio of <strong>{sharpe_ratio:.2f}</strong> indicates <strong>{sharpe_interpretation}</strong> performance.</li>
                <li><strong>Profitability:</strong> A Profit Factor of <strong>{profit_factor:.2f}</strong> shows that for every dollar lost, <strong>${profit_factor:.2f}</strong> was gained.</li>
                <li><strong>Win Rate:</strong> Of {total_win_loss_trades} completed trades, <strong>{win_count} were winners</strong> ({win_rate_pct:.1f}% win rate).</li>
                <li><strong>Trading Activity:</strong> Averaged <strong>{avg_trades_per_cycle:.1f} trades per cycle</strong>, incurring <strong>${state.get('total_fees_paid', 0):.2f}</strong> in total fees.</li>
            </ul>
        </div>
        
        <div class="diagnostic">
            <h3>🔧 System Diagnostics</h3>
            <p><strong>Connection Stability:</strong> {connection_rate:.1f}% ({connected_cycles}/{len(cycle_history)} cycles) | <strong>Data Quality:</strong> {avg_data_quality:.1f}/{len(PORTFOLIO_STOCKS)} stocks/cycle</p>
        </div>
        
        <div class="validation-insights">
            <h3>🕵️ Validation System</h3>
            <p><strong>Engagement:</strong> {validation_engagement}, with an average of {avg_validation_per_cycle:.2f} checks per cycle.</p>
        </div>

        <div class="performance-chart">
            <h2>📊 Recent Cycle Performance (Last 10)</h2>
            <table class="cycle-table">
                <thead>
                    <tr>
                        <th>Cycle</th>
                        <th>Portfolio Value</th>
                        <th>P&L</th>
                        <th>Trades</th>
                        <th>Shares Held</th>
                        <th>Connection</th>
                        <th>Validations</th>
                    </tr>
                </thead>
                <tbody>
    """

    for cycle in cycle_history[-10:]:
        pnl = cycle.get('total_unrealized_pnl', 0)
        pnl_class = 'positive' if pnl > 0 else 'negative' if pnl < 0 else 'neutral'
        connection_status = "✅" if cycle.get('connection_status', False) else "❌"
        validations = cycle.get('validation_attempts', 0)
        
        html_content += f"""
                    <tr>
                        <td>{cycle.get('cycle_number', 'N/A')}</td>
                        <td>${cycle.get('total_portfolio_value', 0):,.2f}</td>
                        <td class="{pnl_class}">${pnl:+.2f}</td>
                        <td>{cycle.get('executed_trades_count', 0)}</td>
                        <td>{cycle.get('total_shares', 0)}</td>
                        <td>{connection_status}</td>
                        <td>{validations}</td>
                    </tr>
        """

    html_content += f"""
                </tbody>
            </table>
        </div>
        
        <div class="footer">
            <p>Generated by Enhanced AI Portfolio Trading Agent | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
    </body>
    </html>
    """

    with open(filepath, 'w', encoding='utf-8', errors='replace') as f:
        f.write(html_content)
    
    print(f"📈 Enhanced Performance Summary saved: {filepath}")

    # Upload to GCS
    try:
        gcs_bucket_name = "portfolio_reports_algo"
        now = datetime.now()
        gcs_destination_path = f"{now.strftime('%Y/%m/%d')}/{filename}"

        # gcs_path = f"{datetime.now().strftime('%Y/%m/%d')}/{filename}"
        # upload_to_gcs(str(filepath), gcs_path)
    
        upload_result = upload_to_gcs(str(filepath), gcs_destination_path)
        if upload_result:
            print(f"✅ Performance summary uploaded to GCS: {upload_result}")
    except Exception as e:
        print(f"❌ GCS upload error: {e}")

    return str(filepath)

def generate_portfolio_status_report(state: PortfolioState):
    """
    Generates a portfolio status report with current metrics and a historical P&L trend chart.
    """
    reports_dir = setup_reporting_directory()
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"status_report_{timestamp}.html"
    filepath = reports_dir / filename

    # --- 1. Read Historical Data ---
    historical_pnl = []
    report_files = sorted(reports_dir.glob("portfolio_data_*.json"))

    for report_file in report_files:
        try:
            with open(report_file, 'r') as f:
                data = json.load(f)
                # Extract timestamp and P&L from the JSON structure
                ts = data.get('report_metadata', {}).get('generated_at', '')
                pnl = data.get('portfolio_summary', {}).get('total_unrealized_pnl', 0)
                if ts and pnl is not None:
                    # Format timestamp for chart labels
                    chart_ts = datetime.fromisoformat(ts).strftime('%H:%M:%S')
                    historical_pnl.append({'timestamp': chart_ts, 'pnl': pnl})
        except Exception as e:
            print(f"⚠️ Could not parse historical report {report_file}: {e}")

    # Add the current state's P&L to the trend
    current_ts = datetime.now().strftime('%H:%M:%S')
    current_pnl = state.get('total_unrealized_pnl', 0)
    historical_pnl.append({'timestamp': current_ts, 'pnl': current_pnl})

    # Prepare data for Chart.js
    chart_labels = json.dumps([item['timestamp'] for item in historical_pnl])
    chart_data = json.dumps([item['pnl'] for item in historical_pnl])

    # --- 2. Extract Current Data ---
    total_equity = state.get('total_portfolio_value', 0)
    cash_available = state.get('cash_available', 0)
    unrealized_pnl = state.get('total_unrealized_pnl', 0)
    pnl_class = 'positive' if unrealized_pnl > 0 else 'negative' if unrealized_pnl < 0 else 'neutral'
    
    # --- 3. Build HTML Content ---
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Portfolio Status Report - {timestamp}</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif; margin: 20px; background-color: #f7f9fc; color: #333; }}
            .header {{ background: #2c3e50; color: white; padding: 25px; border-radius: 12px; text-align: center; margin-bottom: 20px; }}
            .metrics {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 20px; }}
            .metric-card {{ background: white; padding: 20px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.08); text-align: center; }}
            .metric-value {{ font-size: 2.2em; font-weight: 600; }}
            .metric-label {{ color: #555; margin-top: 8px; font-size: 1em; }}
            .positive {{ color: #27ae60; }} .negative {{ color: #c0392b; }} .neutral {{ color: #7f8c8d; }}
            .section {{ background: white; padding: 25px; border-radius: 12px; margin-top: 20px; box-shadow: 0 4px 12px rgba(0,0,0,0.08); }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 15px; }}
            th, td {{ padding: 12px 15px; text-align: left; border-bottom: 1px solid #eef; }}
            th {{ background-color: #f7f9fc; font-weight: 600; }}
            h1, h2 {{ margin: 0; }} h2 {{ margin-bottom: 15px; border-bottom: 2px solid #eee; padding-bottom: 10px; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>Portfolio Status Report</h1>
            <p>Session: {state.get('session_id', 'N/A')} | Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>

        <div class="metrics">
            <div class="metric-card">
                <div class="metric-value neutral">${total_equity:,.2f}</div>
                <div class="metric-label">Total Equity</div>
            </div>
            <div class="metric-card">
                <div class="metric-value {pnl_class}">${unrealized_pnl:+,.2f}</div>
                <div class="metric-label">Unrealized P&L</div>
            </div>
            <div class="metric-card">
                <div class="metric-value neutral">${cash_available:,.2f}</div>
                <div class="metric-label">Cash Available</div>
            </div>
        </div>

        <div class="section">
            <h2>Profitability Trend</h2>
            <canvas id="pnlChart"></canvas>
        </div>

        <div class="section">
            <h2>Current Holdings</h2>
            <table>
                <thead><tr><th>Symbol</th><th>Position (Shares)</th><th>Current Price</th><th>Market Value</th><th>Unrealized P&L</th></tr></thead>
                <tbody>
    """
    
    positions = state.get('positions', {})
    for symbol in sorted(positions.keys()):
        if positions[symbol] != 0:
            price = state.get('stock_prices', {}).get(symbol, 0)
            market_value = positions[symbol] * price
            pnl = state.get('stock_pnls', {}).get(symbol, 0)
            pnl_class_row = 'positive' if pnl > 0 else 'negative' if pnl < 0 else 'neutral'
            html_content += f"""
                <tr>
                    <td><strong>{symbol}</strong></td>
                    <td>{positions[symbol]}</td>
                    <td>${price:,.2f}</td>
                    <td>${market_value:,.2f}</td>
                    <td class="{pnl_class_row}">${pnl:+,.2f}</td>
                </tr>
            """
    
    html_content += """
                </tbody>
            </table>
        </div>

        <script>
            const ctx = document.getElementById('pnlChart').getContext('2d');
            new Chart(ctx, {
                type: 'line',
                data: {
                    labels: """ + chart_labels + """,
                    datasets: [{
                        label: 'Unrealized P&L ($)',
                        data: """ + chart_data + """,
                        borderColor: 'rgba(54, 162, 235, 1)',
                        backgroundColor: 'rgba(54, 162, 235, 0.2)',
                        borderWidth: 2,
                        fill: true,
                        tension: 0.1
                    }]
                },
                options: {
                    responsive: true,
                    scales: {
                        y: {
                            beginAtZero: false,
                            ticks: {
                                callback: function(value, index, values) {
                                    return '$' + value.toLocaleString();
                                }
                            }
                        }
                    }
                }
            });
        </script>
    </body>
    </html>
    """

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"📈 Portfolio Status Report saved: {filepath}")
    gcs_path = f"{datetime.now().strftime('%Y/%m/%d')}/{filename}"
    upload_to_gcs(str(filepath), gcs_path)
    return str(filepath)





### ------------->>>>> <<<<<------------------------
from utils import ensure_connection, setup_reporting_directory, upload_to_gcs
from config import PORTFOLIO_STOCKS
from ib_async import Stock

# === ENHANCED COMBINED PERFORMANCE AND PORTFOLIO STATUS REPORT ===
# === ENHANCED COMBINED PERFORMANCE AND PORTFOLIO STATUS REPORT ===
# Import required utilities at the top of your file
from utils import ensure_connection, setup_reporting_directory, upload_to_gcs
from ib_async import Stock
import pandas as pd
from datetime import datetime
from pathlib import Path
from config import PORTFOLIO_STOCKS  # Import portfolio stocks configuration

async def generate_enhanced_performance_and_status_report(state: PortfolioState):
    """Generate comprehensive performance summary with portfolio status report"""
    reports_dir = setup_reporting_directory()
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"performance_summary_{timestamp}.html"    
    filepath = reports_dir / filename

    # Get current portfolio status from IBKR
    print("📊 Fetching current portfolio status from IBKR...")
    portfolio_status = await get_current_portfolio_status()
    
    cycle_history = state.get('cycle_history', [])
    if len(cycle_history) < 2:
        print("Not enough cycle history for full performance report. Generating status report only.")
        # Still generate portfolio status even without history
    
    # --- 1. METRIC CALCULATIONS (Existing) ---
    # Basic Performance
    initial_value = cycle_history[0].get('total_portfolio_value', 0) if cycle_history else 0
    # current_value = cycle_history[-1].get('total_portfolio_value', 0) if cycle_history else portfolio_status.get('net_liquidation', 0)
    current_value = cycle_history[-1].get('total_portfolio_value', 0) if cycle_history else (portfolio_status.get('net_liquidation', 0) if portfolio_status else 0)

    total_return = current_value - initial_value
    return_pct = (total_return / initial_value * 100) if initial_value > 0 else 0
    total_trades = cycle_history[-1].get('total_trades', 0) if cycle_history else 0
    avg_trades_per_cycle = total_trades / len(cycle_history) if cycle_history else 0

    # Trade Analysis
    executed_trades = state.get('executed_trades', [])
    sell_trades = [t for t in executed_trades if t.get('action') == 'SELL' and 'net_profit' in t]
    win_count = len([t for t in sell_trades if t['net_profit'] > 0])
    loss_count = len([t for t in sell_trades if t['net_profit'] <= 0])
    total_win_loss_trades = win_count + loss_count
    win_rate_pct = (win_count / total_win_loss_trades * 100) if total_win_loss_trades > 0 else 0
    win_loss_ratio = win_count / loss_count if loss_count > 0 else float(win_count > 0)

    total_wins = sum(t['net_profit'] for t in sell_trades if t['net_profit'] > 0)
    total_losses = sum(t['net_profit'] for t in sell_trades if t['net_profit'] <= 0)
    profit_factor = total_wins / abs(total_losses) if total_losses < 0 else float('inf') if total_wins > 0 else 0

    # Advanced Metrics
    portfolio_returns = pd.Series([c.get('total_portfolio_value', 0) for c in cycle_history]).pct_change().dropna() if cycle_history else pd.Series()
    sharpe_ratio = (portfolio_returns.mean() / portfolio_returns.std()) * (252**0.5) if len(portfolio_returns) > 0 and portfolio_returns.std() > 0 else 0.0
    pnl_by_cycle = [cycle.get('total_unrealized_pnl', 0) for cycle in cycle_history]
    best_pnl = max(pnl_by_cycle) if pnl_by_cycle else 0
    worst_pnl = min(pnl_by_cycle) if pnl_by_cycle else 0

    # System Diagnostics
    connected_cycles = sum(1 for c in cycle_history if c.get('connection_status', False))
    connection_rate = (connected_cycles / len(cycle_history) * 100) if cycle_history else 100
    avg_data_quality = sum(c.get('data_quality', 0) for c in cycle_history) / len(cycle_history) if cycle_history else 0

    # Validation System
    total_validation_attempts = sum(c.get('validation_attempts', 0) for c in cycle_history)
    cycles_with_validation = sum(1 for c in cycle_history if c.get('validation_attempts', 0) > 0)
    avg_validation_per_cycle = total_validation_attempts / len(cycle_history) if cycle_history else 0

    # --- 2. DYNAMIC CONTENT PRE-CALCULATION ---
    # CSS Classes for Metric Cards
    return_pct_class = 'positive' if return_pct > 0 else 'negative' if return_pct < 0 else 'neutral'
    total_return_class = 'positive' if total_return > 0 else 'negative' if total_return < 0 else 'neutral'
    sharpe_ratio_class = 'positive' if sharpe_ratio >= 1 else 'negative' if sharpe_ratio < 0 else 'neutral'
    win_loss_ratio_class = 'positive' if win_loss_ratio >= 1 else 'negative'
    profit_factor_class = 'positive' if profit_factor >= 1.5 else 'negative' if profit_factor < 1 else 'neutral'

    # Descriptive Text for Insights
    sharpe_interpretation = 'excellent' if sharpe_ratio > 2 else 'good' if sharpe_ratio > 1 else 'moderate' if sharpe_ratio > 0 else 'poor'
    validation_engagement = 'Actively engaged' if cycles_with_validation > len(cycle_history) * 0.1 else 'Minimal engagement'

    # --- 3. HTML STRING CONSTRUCTION ---
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Complete Portfolio Report - {timestamp}</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; background-color: #f5f5f5; }}
            .header {{ background: linear-gradient(135deg, #4854c7 0%, #3a3897 100%); color: white; padding: 30px; border-radius: 10px; text-align: center; }}
            .metrics {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin: 20px 0; }}
            .metric-card {{ background: white; padding: 25px; border-radius: 10px; text-align: center; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
            .metric-value {{ font-size: 2.5em; font-weight: bold; color: #333; }}
            .metric-label {{ color: #666; margin-top: 10px; font-size: 1.1em; }}
            .positive {{ color: #28a745; }}
            .negative {{ color: #dc3545; }}
            .neutral {{ color: #6c757d; }}
            .performance-chart {{ background: white; padding: 25px; margin: 20px 0; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
            .cycle-table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
            .cycle-table th, .cycle-table td {{ padding: 12px; text-align: center; border-bottom: 1px solid #ddd; }}
            .cycle-table th {{ background-color: #f8f9fa; font-weight: bold; }}
            .insights, .validation-insights, .diagnostic {{ padding: 25px; margin: 20px 0; border-radius: 10px; }}
            .insights {{ background-color: #e8f4fd; border-left: 5px solid #007bff; }}
            .validation-insights {{ background-color: #e9f5e9; border-left: 5px solid #28a745; }}
            .diagnostic {{ background-color: #fff3cd; border-left: 5px solid #ffc107; }}
            .footer {{ text-align: center; color: #666; margin-top: 40px; }}
            .section-divider {{ border-top: 3px solid #4854c7; margin: 40px 0; padding-top: 20px; }}
            .portfolio-status-section {{ margin-top: 40px; }}
            .summary {{ background: white; padding: 25px; margin: 20px 0; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
            table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
            th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
            th {{ background-color: #f8f9fa; font-weight: bold; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>📊 Complete Portfolio Performance & Status Report</h1>
            <h2>Session: {state.get('session_id', 'N/A')}</h2>
            <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p>Cycles Analyzed: {len(cycle_history)} | Trading Period: {cycle_history[0].get('timestamp', 'N/A') if cycle_history else 'N/A'} - {cycle_history[-1].get('timestamp', 'N/A') if cycle_history else 'N/A'}</p>
        </div>

        <div class="metrics">
            <div class="metric-card">
                <div class="metric-value {return_pct_class}">{return_pct:+.2f}%</div>
                <div class="metric-label">Total Return</div>
            </div>
            <div class="metric-card">
                <div class="metric-value {sharpe_ratio_class}">{sharpe_ratio:.2f}</div>
                <div class="metric-label">Sharpe Ratio</div>
            </div>
            <div class="metric-card">
                <div class="metric-value {profit_factor_class}">{profit_factor:.2f}</div>
                <div class="metric-label">Profit Factor</div>
            </div>
            <div class="metric-card">
                <div class="metric-value {win_loss_ratio_class}">{win_loss_ratio:.2f}</div>
                <div class="metric-label">Win/Loss Ratio</div>
            </div>
            <div class="metric-card">
                <div class="metric-value positive">${best_pnl:+,.2f}</div>
                <div class="metric-label">Best Cycle P&L</div>
            </div>
            <div class="metric-card">
                <div class="metric-value negative">${worst_pnl:+,.2f}</div>
                <div class="metric-label">Worst Cycle P&L</div>
            </div>
        </div>

        <div class="insights">
            <h2>💡 Performance Insights</h2>
            <ul>
                <li><strong>Portfolio Growth:</strong> Achieved a total return of <strong>{return_pct:+.2f}%</strong> (${total_return:+,.2f}).</li>
                <li><strong>Risk-Adjusted Return:</strong> The Sharpe Ratio of <strong>{sharpe_ratio:.2f}</strong> indicates <strong>{sharpe_interpretation}</strong> performance.</li>
                <li><strong>Profitability:</strong> A Profit Factor of <strong>{profit_factor:.2f}</strong> shows that for every dollar lost, <strong>${profit_factor:.2f}</strong> was gained.</li>
                <li><strong>Win Rate:</strong> Of {total_win_loss_trades} completed trades, <strong>{win_count} were winners</strong> ({win_rate_pct:.1f}% win rate).</li>
                <li><strong>Trading Activity:</strong> Averaged <strong>{avg_trades_per_cycle:.1f} trades per cycle</strong>, incurring <strong>${state.get('total_fees_paid', 0):.2f}</strong> in total fees.</li>
            </ul>
        </div>
        
        <div class="diagnostic">
            <h3>🔧 System Diagnostics</h3>
            <p><strong>Connection Stability:</strong> {connection_rate:.1f}% ({connected_cycles}/{len(cycle_history) if cycle_history else 0} cycles) | <strong>Data Quality:</strong> {avg_data_quality:.1f}/{len(PORTFOLIO_STOCKS)} stocks/cycle</p>
        </div>
        
        <div class="validation-insights">
            <h3>🕵️ Validation System</h3>
            <p><strong>Engagement:</strong> {validation_engagement}, with an average of {avg_validation_per_cycle:.2f} checks per cycle.</p>
        </div>
    """

    # Add cycle history table if available
    if cycle_history:
        html_content += """
        <div class="performance-chart">
            <h2>📊 Recent Cycle Performance (Last 10)</h2>
            <table class="cycle-table">
                <thead>
                    <tr>
                        <th>Cycle</th>
                        <th>Portfolio Value</th>
                        <th>P&L</th>
                        <th>Trades</th>
                        <th>Shares Held</th>
                        <th>Connection</th>
                        <th>Validations</th>
                    </tr>
                </thead>
                <tbody>
        """

        for cycle in cycle_history[-10:]:
            pnl = cycle.get('total_unrealized_pnl', 0)
            pnl_class = 'positive' if pnl > 0 else 'negative' if pnl < 0 else 'neutral'
            connection_status = "✅" if cycle.get('connection_status', False) else "❌"
            validations = cycle.get('validation_attempts', 0)
            
            html_content += f"""
                        <tr>
                            <td>{cycle.get('cycle_number', 'N/A')}</td>
                            <td>${cycle.get('total_portfolio_value', 0):,.2f}</td>
                            <td class="{pnl_class}">${pnl:+.2f}</td>
                            <td>{cycle.get('executed_trades_count', 0)}</td>
                            <td>{cycle.get('total_shares', 0)}</td>
                            <td>{connection_status}</td>
                            <td>{validations}</td>
                        </tr>
            """

        html_content += """
                </tbody>
            </table>
        </div>
        """

    # === ADD PORTFOLIO STATUS SECTION ===
    html_content += """
        <div class="section-divider"></div>
        
        <div class="portfolio-status-section">
            <h1 style="text-align: center; color: #4854c7;">📈 Current Portfolio Status from Interactive Brokers</h1>
    """

    # Portfolio Status Metrics
    if portfolio_status:
        net_liq = portfolio_status.get('net_liquidation', 0)
        total_cash = portfolio_status.get('total_cash', 0)
        total_market_value = portfolio_status.get('total_market_value', 0)
        total_unrealized_pnl = portfolio_status.get('total_unrealized_pnl', 0)
        pnl_pct = (total_unrealized_pnl / (total_market_value - total_unrealized_pnl) * 100) if (total_market_value - total_unrealized_pnl) > 0 else 0
        
        html_content += f"""
            <div class="metrics">
                <div class="metric-card">
                    <div class="metric-value">${net_liq:,.2f}</div>
                    <div class="metric-label">Net Liquidation Value</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">${total_cash:,.2f}</div>
                    <div class="metric-label">Cash Balance (USD)</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">${total_market_value:,.2f}</div>
                    <div class="metric-label">Total Market Value</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value {'positive' if total_unrealized_pnl > 0 else 'negative'}">${total_unrealized_pnl:+,.2f}</div>
                    <div class="metric-label">Unrealized P&L</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value {'positive' if pnl_pct > 0 else 'negative'}">{pnl_pct:+.2f}%</div>
                    <div class="metric-label">P&L Percentage</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{len(portfolio_status.get('positions', {}))}</div>
                    <div class="metric-label">Active Positions</div>
                </div>
            </div>
            
            <div class="summary">
                <h2>📊 Current Portfolio Holdings</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Symbol</th>
                            <th>Shares</th>
                            <th>Avg Cost</th>
                            <th>Current Price</th>
                            <th>Market Value</th>
                            <th>Unrealized P&L</th>
                            <th>P&L %</th>
                            <th>Allocation %</th>
                        </tr>
                    </thead>
                    <tbody>
        """
        
        # Add positions
        positions = portfolio_status.get('positions', {})
        allocations = portfolio_status.get('allocations', {})
        
        for symbol, data in sorted(positions.items(), key=lambda x: x[1]['market_value'], reverse=True):
            pnl = data['unrealized_pnl']
            pnl_pct = data['unrealized_pnl_pct']
            pnl_class = 'positive' if pnl > 0 else 'negative' if pnl < 0 else 'neutral'
            allocation = allocations.get(symbol, 0)
            
            html_content += f"""
                        <tr>
                            <td><strong>{symbol}</strong></td>
                            <td>{data['shares']}</td>
                            <td>${data['average_cost']:.2f}</td>
                            <td>${data['current_price']:.2f}</td>
                            <td>${data['market_value']:,.2f}</td>
                            <td class="{pnl_class}">${pnl:+,.2f}</td>
                            <td class="{pnl_class}">{pnl_pct:+.2f}%</td>
                            <td>{allocation:.1f}%</td>
                        </tr>
            """
        
        html_content += """
                    </tbody>
                </table>
            </div>
            
            <div class="summary">
                <h2>💼 Account Information</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Metric</th>
                            <th>Value</th>
                            <th>Currency</th>
                        </tr>
                    </thead>
                    <tbody>
        """
        
        # Add account info
        account_info = portfolio_status.get('account_info', {})
        for key, info in account_info.items():
            html_content += f"""
                        <tr>
                            <td>{key}</td>
                            <td>${info['value']:,.2f}</td>
                            <td>{info['currency']}</td>
                        </tr>
            """
        
        html_content += """
                    </tbody>
                </table>
            </div>
        """
        
        # Add cash balances if multiple currencies
        cash_balances = portfolio_status.get('cash_balances', {})
        if len(cash_balances) > 1:
            html_content += """
            <div class="summary">
                <h2>💵 Cash Balances by Currency</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Currency</th>
                            <th>Balance</th>
                        </tr>
                    </thead>
                    <tbody>
            """
            
            for currency, balance in cash_balances.items():
                html_content += f"""
                        <tr>
                            <td>{currency}</td>
                            <td>{balance:,.2f}</td>
                        </tr>
                """
            
            html_content += """
                    </tbody>
                </table>
            </div>
            """
    
    html_content += """
        </div>
        
        <div class="footer">
            <p>Generated by Enhanced AI Portfolio Trading Agent</p>
            <p>Data Sources: Trading Algorithm History & Interactive Brokers API</p>
            <p>{}</p>
        </div>
    </body>
    </html>
    """.format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

    # Save the report
    with open(filepath, 'w', encoding='utf-8', errors='replace') as f:
        f.write(html_content)
    
    print(f"📈 Complete Portfolio Report saved: {filepath}")

    # Upload to GCS
    try:
        gcs_bucket_name = "portfolio_reports_algo"
        now = datetime.now()
        gcs_destination_path = f"{now.strftime('%Y/%m/%d')}/{filename}"
        
        # upload_to_gcs takes (source_file_path, destination_blob_name)
        upload_result = upload_to_gcs(str(filepath), gcs_destination_path)
        if upload_result:
            print(f"✅ Report uploaded to GCS: {upload_result}")
    except Exception as e:
        print(f"❌ GCS upload error: {e}")

    return str(filepath)


# Helper function to get current portfolio status from IBKR
async def get_current_portfolio_status():
    """Get current portfolio status from Interactive Brokers"""
    try:
        ib = await ensure_connection()
        if not ib:
            return None
        
        print("📊 Fetching portfolio status from IBKR...")
        
        # Get account values
        account_values = ib.accountValues()
        account_summary = ib.accountSummary()
        positions = ib.positions()
        
        # Initialize status dictionary
        status = {
            'net_liquidation': 0,
            'total_cash': 0,
            'total_market_value': 0,
            'total_unrealized_pnl': 0,
            'positions': {},
            'allocations': {},
            'cash_balances': {},
            'account_info': {}
        }
        
        # Process account values
        for value in account_values:
            if value.tag == 'NetLiquidation':
                status['net_liquidation'] = float(value.value)
            elif value.tag == 'TotalCashValue' and value.currency == 'USD':
                status['total_cash'] = float(value.value)
            elif value.tag == 'CashBalance':
                status['cash_balances'][value.currency] = float(value.value)
            
            # Store important account info
            if value.tag in ['NetLiquidation', 'TotalCashValue', 'GrossPositionValue', 
                           'UnrealizedPnL', 'RealizedPnL', 'AvailableFunds', 
                           'BuyingPower', 'MaintMarginReq', 'InitMarginReq']:
                status['account_info'][value.tag] = {
                    'value': float(value.value),
                    'currency': value.currency
                }
        
        # Process positions
        total_market_value = 0
        total_unrealized_pnl = 0
        
        for pos in positions:
            symbol = pos.contract.symbol
            if symbol in PORTFOLIO_STOCKS:
                try:
                    # Create and qualify the contract
                    contract = Stock(symbol, 'SMART', 'USD')
                    qualified_contracts = await ib.qualifyContractsAsync(contract)
                    
                    if not qualified_contracts:
                        print(f"⚠️ Could not qualify contract for {symbol}")
                        continue
                    
                    qualified_contract = qualified_contracts[0]
                    
                    # Get current price using the qualified contract
                    [ticker] = await ib.reqTickersAsync(qualified_contract)
                    current_price = ticker.marketPrice()
                    
                    # If marketPrice is not available, try other price fields
                    if pd.isna(current_price) or current_price <= 0:
                        if ticker.last is not None and ticker.last > 0:
                            current_price = ticker.last
                        elif ticker.close is not None and ticker.close > 0:
                            current_price = ticker.close
                        else:
                            print(f"⚠️ No valid price for {symbol}")
                            continue
                    
                    market_value = pos.position * current_price
                    unrealized_pnl = market_value - (pos.position * pos.avgCost)
                    unrealized_pnl_pct = ((current_price - pos.avgCost) / pos.avgCost * 100) if pos.avgCost > 0 else 0
                    
                    status['positions'][symbol] = {
                        'shares': pos.position,
                        'average_cost': pos.avgCost,
                        'current_price': current_price,
                        'market_value': market_value,
                        'unrealized_pnl': unrealized_pnl,
                        'unrealized_pnl_pct': unrealized_pnl_pct
                    }
                    
                    total_market_value += market_value
                    total_unrealized_pnl += unrealized_pnl
                    
                except Exception as e:
                    print(f"⚠️ Error processing {symbol}: {e}")
                    continue
        
        status['total_market_value'] = total_market_value
        status['total_unrealized_pnl'] = total_unrealized_pnl
        
        # Calculate allocations
        net_liq = status['net_liquidation']
        if net_liq > 0:
            for symbol, pos_data in status['positions'].items():
                status['allocations'][symbol] = (pos_data['market_value'] / net_liq) * 100
            # Add cash allocation
            status['allocations']['Cash'] = (status['total_cash'] / net_liq) * 100
        
        print("✅ Portfolio status retrieved successfully")
        return status
        
    except Exception as e:
        print(f"❌ Error getting portfolio status: {e}")
        import traceback
        traceback.print_exc()
        return None

def generate_benchmark_comparison_html(state: Dict) -> str:
    """Generate S&P 500 benchmark comparison HTML"""
    benchmark_data = state.get('benchmark_comparison', {})
    sp500_data = state.get('sp500_data', {})
    
    if 'error' in benchmark_data or not sp500_data.get('success'):
        return """
        <div class="metric-card">
            <h3>📊 S&P 500 Benchmark</h3>
            <p>⚠️ Benchmark data not available</p>
        </div>
        """
    
    alpha = benchmark_data.get('alpha', 0)
    portfolio_return = benchmark_data.get('portfolio_return_pct', 0)
    sp500_return = benchmark_data.get('sp500_return_pct', 0)
    
    status_color = "#4CAF50" if alpha > 0 else "#f44336"
    status_text = "OUTPERFORMING" if alpha > 0 else "UNDERPERFORMING"
    
    return f"""
    <div class="metric-card" style="border-left: 4px solid {status_color};">
        <h3>📊 S&P 500 Benchmark Comparison</h3>
        <div class="metric-row">
            <span>Portfolio Return:</span>
            <span style="color: {'#4CAF50' if portfolio_return > 0 else '#f44336'};">
                {portfolio_return:+.2f}%
            </span>
        </div>
        <div class="metric-row">
            <span>S&P 500 Return:</span>
            <span style="color: {'#4CAF50' if sp500_return > 0 else '#f44336'};">
                {sp500_return:+.2f}%
            </span>
        </div>
        <div class="metric-row">
            <span><strong>Alpha (Outperformance):</strong></span>
            <span style="color: {status_color}; font-weight: bold;">
                {alpha:+.2f}% ({status_text})
            </span>
        </div>
        <div class="metric-row">
            <span>S&P 500 Current Price:</span>
            <span>${sp500_data.get('price', 0):.2f}</span>
        </div>
    </div>
    """