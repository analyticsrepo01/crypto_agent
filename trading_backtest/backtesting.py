import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import psycopg2
from abc import ABC, abstractmethod
import sys

# --- 0. Database Configuration ---
DB_CONFIG = {
    'host': 'localhost',
    'database': 'trading_historical',
    'user': 'trading_bot',
    'password': 'your_secure_password_here'  # ⚠️ CHANGE THIS PASSWORD
}

# --- 1. NEW Data Handling (from Database) ---
class DataHandlerDB:
    """
    Handles fetching and providing data from the PostgreSQL database.
    """
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.data = None
        self.generator = self._create_generator()

    def _fetch_data_from_db(self):
        """Fetches historical stock and indicator data from the database."""
        print(f"Fetching data for {self.symbol} from database...")
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            # Join prices and indicators tables on symbol and timestamp
            query = """
                SELECT
                    p.timestamp,
                    p.open,
                    p.high,
                    p.low,
                    p.close,
                    p.volume,
                    i.sma_20,
                    i.sma_50
                FROM historical_prices p
                LEFT JOIN historical_indicators i ON p.symbol = i.symbol AND p.timestamp = i.timestamp
                WHERE p.symbol = %s
                ORDER BY p.timestamp ASC;
            """
            # Use pandas to read directly from the DB, which is very efficient
            self.data = pd.read_sql(query, conn, params=(self.symbol,), index_col='timestamp')
            conn.close()
            
            if self.data.empty:
                raise ValueError("No data fetched. Check symbol or database content.")
            
            self.data.dropna(inplace=True) # Drop rows where indicators might be NaN (e.g., at the start)
            print("Data fetched successfully.")
        except Exception as e:
            print(f"Error fetching data from DB: {e}")
            sys.exit(1)

    def _create_generator(self):
        """Creates a generator to yield data row by row (bar by bar)."""
        self._fetch_data_from_db()
        for index, row in self.data.iterrows():
            yield index, row

    def get_next_bar(self):
        """Returns the next bar of data from the generator."""
        try:
            return next(self.generator)
        except StopIteration:
            return None, None
            
    def get_full_data(self):
        """Returns the entire DataFrame."""
        return self.data

# --- 2. Strategy Definition (Modified for DB data) ---
class Strategy(ABC):
    def __init__(self, data_handler: DataHandlerDB):
        self.data_handler = data_handler
        self.symbol = data_handler.symbol
        self.data = data_handler.get_full_data()
        self.signals = self._generate_signals()

    @abstractmethod
    def _generate_signals(self):
        raise NotImplementedError("Should implement _generate_signals()")

    def get_signal(self, date):
        try:
            return self.signals.loc[date]['signal']
        except KeyError:
            return 'HOLD'

class SMACrossoverStrategyDB(Strategy):
    """
    SMA Crossover strategy that uses pre-calculated SMAs from the database.
    """
    def _generate_signals(self):
        print("Generating signals from pre-calculated database indicators...")
        signals = pd.DataFrame(index=self.data.index)
        signals['signal'] = 'HOLD'
        
        # Use the SMA columns directly from the database
        signals['short_mavg'] = self.data['sma_20']
        signals['long_mavg'] = self.data['sma_50']

        # Generate buy/sell signals
        signals['positions'] = np.where(signals['short_mavg'] > signals['long_mavg'], 1, 0)
        signals['signal'] = signals['positions'].diff().replace(0, 'HOLD').replace(1, 'BUY').replace(-1, 'SELL')

        print("Signals generated.")
        return signals

# --- 3. Portfolio Management (No changes needed) ---
class Portfolio:
    def __init__(self, data_handler: DataHandlerDB, initial_cash: float = 100000.0):
        self.data_handler = data_handler
        self.symbol = data_handler.symbol
        self.initial_cash = initial_cash
        self.cash = initial_cash
        self.positions = {self.symbol: 0}
        self.holdings = {self.symbol: 0.0}
        self.total_value_history = []
        self.trade_log = []

    def update_timeindex(self, date, price):
        current_holdings_value = self.positions[self.symbol] * price
        self.holdings[self.symbol] = current_holdings_value
        total_value = self.cash + current_holdings_value
        self.total_value_history.append({'date': date, 'total_value': total_value})

    def execute_order(self, date, signal, price, quantity=100):
        if signal == 'BUY' and self.cash >= price * quantity:
            self.cash -= price * quantity
            self.positions[self.symbol] += quantity
            self.trade_log.append(f"{date.date()}: BOUGHT {quantity} {self.symbol} @ {price:.2f}")
        elif signal == 'SELL' and self.positions[self.symbol] > 0:
            sell_quantity = self.positions[self.symbol]
            self.cash += price * sell_quantity
            self.positions[self.symbol] = 0
            self.trade_log.append(f"{date.date()}: SOLD {sell_quantity} {self.symbol} @ {price:.2f}")

    def get_performance_report(self):
        if not self.total_value_history: return {}
        report = {}
        portfolio_df = pd.DataFrame(self.total_value_history).set_index('date')
        portfolio_df['returns'] = portfolio_df['total_value'].pct_change()
        total_return = (portfolio_df['total_value'][-1] / self.initial_cash) - 1
        days = (portfolio_df.index[-1] - portfolio_df.index[0]).days
        annualized_return = (1 + total_return) ** (365.0 / days) - 1 if days > 0 else 0
        annualized_volatility = portfolio_df['returns'].std() * np.sqrt(252)
        sharpe_ratio = annualized_return / annualized_volatility if annualized_volatility != 0 else 0
        report['Total Return'] = f"{total_return:.2%}"
        report['Annualized Return'] = f"{annualized_return:.2%}"
        report['Annualized Volatility'] = f"{annualized_volatility:.2%}"
        report['Sharpe Ratio'] = f"{sharpe_ratio:.2f}"
        return report

# --- 4. Backtesting Engine (No changes needed) ---
class Backtester:
    def __init__(self, data_handler: DataHandlerDB, strategy: Strategy, portfolio: Portfolio):
        self.data_handler = data_handler
        self.strategy = strategy
        self.portfolio = portfolio

    def run_backtest(self):
        print("\n--- Starting Backtest ---")
        date, bar = self.data_handler.get_next_bar()
        while date is not None:
            price = bar['close']
            self.portfolio.update_timeindex(date, price)
            signal = self.strategy.get_signal(date)
            if signal in ['BUY', 'SELL']:
                self.portfolio.execute_order(date, signal, price)
            date, bar = self.data_handler.get_next_bar()
        print("--- Backtest Finished ---\n")

    def plot_performance(self):
        portfolio_df = pd.DataFrame(self.portfolio.total_value_history).set_index('date')
        plt.style.use('seaborn-v0_8-darkgrid')
        fig, ax1 = plt.subplots(figsize=(14, 7))
        color = 'tab:blue'
        ax1.set_xlabel('Date')
        ax1.set_ylabel('Portfolio Value ($)', color=color)
        ax1.plot(portfolio_df.index, portfolio_df['total_value'], color=color)
        ax1.tick_params(axis='y', labelcolor=color)
        ax2 = ax1.twinx()
        color = 'tab:gray'
        ax2.set_ylabel(f'{self.data_handler.symbol} Price ($)', color=color)
        ax2.plot(self.data_handler.data.index, self.data_handler.data['close'], color=color, alpha=0.6)
        ax2.tick_params(axis='y', labelcolor=color)
        fig.tight_layout()
        plt.title(f'Portfolio Performance vs. {self.data_handler.symbol}')
        plt.show()

# --- Main Execution ---
if __name__ == '__main__':
    # --- Configuration ---
    SYMBOL = 'NVDA' # Test a different symbol from your database
    INITIAL_CASH = 100000.0

    # ⚠️ IMPORTANT: Update the password in DB_CONFIG before running!
    if DB_CONFIG['password'] == 'your_secure_password_here':
        print("❌ Please update the database password in DB_CONFIG before running!")
        sys.exit(1)

    # --- Initialization ---
    data = DataHandlerDB(symbol=SYMBOL)
    strategy = SMACrossoverStrategyDB(data) # Using the new DB-aware strategy
    portfolio = Portfolio(data, initial_cash=INITIAL_CASH)
    backtester = Backtester(data, strategy, portfolio)

    # --- Run ---
    backtester.run_backtest()

    # --- Results ---
    print("--- Performance Report ---")
    performance_metrics = portfolio.get_performance_report()
    for metric, value in performance_metrics.items():
        print(f"{metric}: {value}")
    
    print("\n--- Recent Trades ---")
    for trade in portfolio.trade_log[-10:]: # Print last 10 trades
        print(trade)

    # --- Plotting ---
    backtester.plot_performance()
