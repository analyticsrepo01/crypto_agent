# /trading_bot/reporting.py

import json
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from utils import setup_reporting_directory, upload_to_gcs
from config import PORTFOLIO_STOCKS

# Define a type alias for state for clarity
PortfolioState = Dict[str, Any]

def generate_html_report(state: PortfolioState):
    """Generate comprehensive HTML report with validation information"""
    reports_dir = setup_reporting_directory()
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"portfolio_report_{timestamp}.html"
    filepath = reports_dir / filename

    # Basic state data
    portfolio_value = state.get('total_portfolio_value', 0)
    total_pnl = state.get('total_unrealized_pnl', 0)
    
    # CSS classes for positive/negative values
    pnl_class = 'positive' if total_pnl > 0 else 'negative' if total_pnl < 0 else 'neutral'

    # Start building HTML string
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>AI Trading Report - {timestamp}</title>
        <style>
            body {{ font-family: sans-serif; margin: 20px; background-color: #f9f9f9; }}
            .header {{ background: #4a69bd; color: white; padding: 20px; border-radius: 8px; text-align: center; }}
            .metric-card {{ background: white; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); text-align: center; }}
            .metrics {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; margin: 20px 0; }}
            .positive {{ color: #2ecc71; }} .negative {{ color: #e74c3c; }} .neutral {{ color: #7f8c8d; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
            th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
            th {{ background-color: #f2f2f2; }}
            .section {{ background: white; padding: 20px; border-radius: 8px; margin-top: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>AI Portfolio Trading Report</h1>
            <p>Session: {state.get('session_id', 'N/A')} | Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>

        <div class="metrics">
            <div class="metric-card"><h3>Portfolio Value</h3><p class="neutral">${portfolio_value:,.2f}</p></div>
            <div class="metric-card"><h3>Total P&L</h3><p class="{pnl_class}">${total_pnl:+,.2f}</p></div>
            <div class="metric-card"><h3>Total Trades</h3><p class="neutral">{state.get('total_trades', 0)}</p></div>
            <div class="metric-card"><h3>Cash</h3><p class="neutral">${state.get('cash_available', 0):,.2f}</p></div>
        </div>

        <div class="section">
            <h2>Holdings</h2>
            <table>
                <tr><th>Stock</th><th>Position</th><th>Price</th><th>P&L</th><th>Allocation</th><th>AI Action</th></tr>
    """

    for symbol in PORTFOLIO_STOCKS:
        pos = state.get('positions', {}).get(symbol, 0)
        price = state.get('stock_prices', {}).get(symbol, 0)
        pnl = state.get('stock_pnls', {}).get(symbol, 0)
        alloc = state.get('portfolio_allocation', {}).get(symbol, 0)
        rec = state.get('ai_recommendations', {}).get(symbol, {}).get('action', 'N/A')
        pnl_class_row = 'positive' if pnl > 0 else 'negative' if pnl < 0 else 'neutral'
        html += f"<tr><td>{symbol}</td><td>{pos}</td><td>${price:.2f}</td><td class='{pnl_class_row}'>${pnl:+.2f}</td><td>{alloc:.1f}%</td><td>{rec}</td></tr>"

    html += "</table></div>"

    # Executed Trades Section
    html += "<div class='section'><h2>Executed Trades in Cycle</h2>"
    executed_trades = state.get('executed_trades', [])
    if executed_trades:
        html += "<ul>"
        for trade in executed_trades:
            html += f"<li>{trade.get('action')} {trade.get('quantity')} {trade.get('symbol')} @ ${trade.get('price', 0):.2f}</li>"
        html += "</ul>"
    else:
        html += "<p>No trades executed in this cycle.</p>"
    html += "</div>"

    # Validation Log Section
    html += "<div class='section'><h2>Decision Validation Log</h2>"
    validation_history = state.get('validation_history', [])
    if validation_history:
        html += "<ul>"
        for attempt in validation_history:
            status = "✅ Proceed" if attempt.get('decision') == 'proceed' else "🔄 Rerun"
            html += f"<li><strong>Attempt #{attempt.get('attempt')}:</strong> {status} - <em>{attempt.get('reason')}</em></li>"
        html += "</ul>"
    else:
        html += "<p>No validation performed in this cycle.</p>"
    html += "</div></body></html>"

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"📄 HTML Report saved: {filepath}")
    gcs_path = f"{datetime.now().strftime('%Y/%m/%d')}/{filename}"
    upload_to_gcs(str(filepath), gcs_path)
    return str(filepath)

def generate_json_report(state: PortfolioState):
    """Generate detailed JSON report of the current state."""
    reports_dir = setup_reporting_directory()
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"portfolio_data_{timestamp}.json"
    filepath = reports_dir / filename

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=2, default=str)
        
    print(f"📊 JSON Report saved: {filepath}")
    return str(filepath)

def generate_csv_report(state: PortfolioState):
    """Generate CSV report for portfolio summary and trades."""
    reports_dir = setup_reporting_directory()
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Portfolio Summary CSV
    summary_filename = f"portfolio_summary_{timestamp}.csv"
    summary_filepath = reports_dir / summary_filename
    
    summary_data = []
    for symbol in PORTFOLIO_STOCKS:
        rec = state.get('ai_recommendations', {}).get(symbol, {})
        trend = state.get('ai_trend_analysis', {}).get(symbol, {})
        summary_data.append({
            'Symbol': symbol,
            'Price': state.get('stock_prices', {}).get(symbol, 0),
            'Position': state.get('positions', {}).get(symbol, 0),
            'PnL': state.get('stock_pnls', {}).get(symbol, 0),
            'AI_Action': rec.get('action', 'N/A'),
            'AI_Trend': trend.get('trend', 'N/A'),
            'Technical_Score': rec.get('technical_score', 0)
        })
    pd.DataFrame(summary_data).to_csv(summary_filepath, index=False)
    print(f"📋 Summary CSV saved: {summary_filepath}")

    # Trades CSV
    if state.get('executed_trades'):
        trades_filename = f"executed_trades_{timestamp}.csv"
        trades_filepath = reports_dir / trades_filename
        pd.DataFrame(state.get('executed_trades')).to_csv(trades_filepath, index=False)
        print(f"📈 Trades CSV saved: {trades_filepath}")

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
    current_value = cycle_history[-1].get('total_portfolio_value', 0) if cycle_history else portfolio_status.get('net_liquidation', 0)
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