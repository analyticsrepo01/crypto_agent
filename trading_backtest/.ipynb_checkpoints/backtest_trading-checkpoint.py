import backtrader as bt
import psycopg2
import pandas as pd
from datetime import datetime

# 1. CUSTOM DATA FEED FROM YOUR DATABASE
class PostgreSQLData(bt.feeds.PandasData):
    """Custom data feed that reads from your PostgreSQL database"""
    
    lines = ('sentiment_score',)  # Add news sentiment as a data line
    params = (
        ('datetime', None),
        ('open', 'open'),
        ('high', 'high'), 
        ('low', 'low'),
        ('close', 'close'),
        ('volume', 'volume'),
        ('sentiment_score', 'sentiment_score'),
        ('timeframe', bt.TimeFrame.Days),
    )

def get_data_from_db(symbol, start_date, end_date):
    """Fetch data from your PostgreSQL database"""
    conn = psycopg2.connect(
        host='localhost',
        database='trading_historical',
        user='trading_bot',
        password='your_secure_password'
    )
    
    query = """
    SELECT 
        p.timestamp,
        p.open, p.high, p.low, p.close, p.volume,
        COALESCE(n.sentiment_score, 0) as sentiment_score,
        i.rsi, i.sma_20, i.macd_histogram
    FROM historical_prices p
    LEFT JOIN historical_news_sentiment n ON 
        p.symbol = n.symbol AND DATE(p.timestamp) = n.date
    LEFT JOIN historical_indicators i ON 
        p.symbol = i.symbol AND p.timestamp = i.timestamp
    WHERE p.symbol = %s 
    AND p.timestamp BETWEEN %s AND %s
    ORDER BY p.timestamp
    """
    
    df = pd.read_sql(query, conn, params=[symbol, start_date, end_date])
    df.set_index('timestamp', inplace=True)
    conn.close()
    
    return df

# 2. STRATEGY USING YOUR EXISTING AI LOGIC
class YourAIStrategy(bt.Strategy):
    """Backtrader strategy that uses your existing AI decision logic"""
    
    params = (
        ('trade_size', 10),
        ('aggressive_mode', False),
    )
    
    def __init__(self):
        # Store references to data
        self.data_close = self.datas[0].close
        self.sentiment = self.datas[0].sentiment_score
        
        # Track orders
        self.order = None
        
        # You can access all your technical indicators here
        # Or calculate them using your existing functions
        
    def next(self):
        """Called for each bar - integrate your AI logic here"""
        
        # Skip if we have a pending order
        if self.order:
            return
            
        # 1. Prepare data in your existing format
        current_data = self._prepare_data_for_ai()
        
        # 2. Call your existing AI analysis
        ai_decision = self._get_ai_recommendation(current_data)
        
        # 3. Execute trades based on AI decision
        if ai_decision['action'] == 'BUY' and not self.position:
            self.order = self.buy(size=self.params.trade_size)
            print(f"BUY signal: {ai_decision['reasoning']}")
            
        elif ai_decision['action'] == 'SELL' and self.position:
            self.order = self.sell(size=self.params.trade_size)
            print(f"SELL signal: {ai_decision['reasoning']}")
    
    def _prepare_data_for_ai(self):
        """Convert Backtrader data to your existing format"""
        # Get current bar data
        current_price = self.data_close[0]
        sentiment_score = self.sentiment[0]
        
        # Format it like your existing stock_data structure
        stock_data = {
            'AAPL': {  # or self.data._name for dynamic symbol
                'current_price': float(current_price),
                'sentiment_score': float(sentiment_score),
                'valid': True
                # Add other indicators as needed
            }
        }
        
        return stock_data
    
    def _get_ai_recommendation(self, stock_data):
        """Call your existing AI recommendation logic"""
        # Import your existing functions
        from agent import get_ai_portfolio_recommendations_with_news
        
        # Create a minimal state for your AI function
        state = {
            'stock_data': stock_data,
            'aggressive_mode': self.params.aggressive_mode,
            'news_sentiment': {'AAPL': {'sentiment_score': self.sentiment[0]}},
            'positions': {'AAPL': self.position.size if self.position else 0},
            'cash_available': self.broker.getcash(),
            # Add other required state fields
        }
        
        # This is your existing AI logic!
        recommendations = get_ai_portfolio_recommendations_with_news(state)
        
        return recommendations.get('AAPL', {'action': 'HOLD', 'reasoning': 'No signal'})
    
    def notify_order(self, order):
        """Track order execution"""
        if order.status in [order.Submitted, order.Accepted]:
            return
            
        if order.status in [order.Completed]:
            if order.isbuy():
                print(f"BUY EXECUTED: Price {order.executed.price:.2f}")
            else:
                print(f"SELL EXECUTED: Price {order.executed.price:.2f}")
                
        self.order = None

# 3. RUN BACKTEST
def run_backtest():
    cerebro = bt.Cerebro()
    
    # Add your strategy
    cerebro.addstrategy(YourAIStrategy, aggressive_mode=False)
    
    # Load data from your database
    for symbol in ['AAPL', 'MSFT', 'GOOGL']:
        df = get_data_from_db(symbol, '2023-01-01', '2024-12-31')
        data = PostgreSQLData(dataname=df)
        cerebro.adddata(data, name=symbol)
    
    # Set initial cash and commission
    cerebro.broker.setcash(1000000)
    cerebro.broker.setcommission(commission=0.001)  # 0.1%
    
    # Add analyzers for performance metrics
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
    
    print(f"Starting Portfolio Value: {cerebro.broker.getvalue():.2f}")
    
    # Run backtest
    results = cerebro.run()
    
    print(f"Final Portfolio Value: {cerebro.broker.getvalue():.2f}")
    
    # Print performance metrics
    strat = results[0]
    print(f"Sharpe Ratio: {strat.analyzers.sharpe.get_analysis()['sharperatio']:.2f}")
    print(f"Max Drawdown: {strat.analyzers.drawdown.get_analysis()['max']['drawdown']:.2%}")
    
    # Plot results
    cerebro.plot(style='candlestick')

if __name__ == "__main__":
    run_backtest()