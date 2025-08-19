# /trading_bot/config.py

import os
import pytz
import google.generativeai as genai
from google.cloud import storage

# === AI & GCS CONFIGURATION ===
# Configure Gemini AI
# It's recommended to use environment variables for API keys in production
GEMINI_API_KEY = os.environ.get('GOOGLE_API_KEY', 'AIzaSyC-zS7ACEltm2mPPFs3UtjK0_-wOoSkIJ8')
genai.configure(api_key=GEMINI_API_KEY)

# Initialize Gemini model
MODEL_GEMINI_2_0_FLASH = 'gemini-2.5-flash' #"gemini-2.0-flash"
gemini_model = genai.GenerativeModel(MODEL_GEMINI_2_0_FLASH)

# Initialize Google Cloud Storage client
storage_client = storage.Client()
GCS_BUCKET_NAME = "portfolio_reports_algo"


# === CRYPTO TRADING PARAMETERS ===
# Gemini Exchange Trading Configuration
MAX_TOTAL_CRYPTO_UNITS = 10.0  # Total crypto units (BTC equivalent)
MAX_UNITS_PER_CRYPTO = 2.0     # Max units per crypto pair
TRADE_SIZE = 0.001  # Crypto units per trade (0.001 BTC = ~$60-100)
MIN_USD_RESERVE = 1000  # Minimum USD to keep in account
MIN_CASH_RESERVE = MIN_USD_RESERVE  # Legacy compatibility
GEMINI_TRADING_FEE = 0.005  # 0.5% trading fee on Gemini

# Legacy stock trading compatibility values
MAX_TOTAL_SHARES = int(MAX_TOTAL_CRYPTO_UNITS)  # For compatibility
MAX_SHARES_PER_STOCK = int(MAX_UNITS_PER_CRYPTO)  # For compatibility
TRADING_FEE_PER_TRADE = GEMINI_TRADING_FEE  # For compatibility

# Stop-Loss and Take-Profit Configuration for Crypto
STOP_LOSS_PERCENTAGE = -3.0    # Crypto is more volatile, wider stops
TAKE_PROFIT_PERCENTAGE = 5.0   # Higher profit targets for crypto
PORTFOLIO_STOP_LOSS = -10.0    # Crypto portfolio emergency stop

# Crypto Portfolio Configuration (Gemini supported pairs)
PORTFOLIO_CRYPTOS = [
    'BTCUSD', 'ETHUSD', 'LINKUSD', 'LTCUSD', 'BCHUSD',
    'ZECUSD', 'XLMUSD', 'BATUSD', 'OXTUSD', '1INCHUSD'
]

# Legacy stock config for backward compatibility
PORTFOLIO_STOCKS = PORTFOLIO_CRYPTOS

# Market Hours (Crypto trades 24/7)
MARKET_TIMEZONE = pytz.timezone('US/Eastern')
CRYPTO_MARKET_24_7 = True  # Crypto markets never close

# === GEMINI EXCHANGE CONFIGURATION ===
GEMINI_API_KEY = 'master-gp4BiyhRb2aFXzQc57RJ'
GEMINI_API_SECRET = '38fL3t3QnyxMS7jgtUPxcZ11Q6dx'
GEMINI_SANDBOX = True  # Set to False for live trading
GEMINI_BASE_URL = "https://api.sandbox.gemini.com" if GEMINI_SANDBOX else "https://api.gemini.com"

# === NEWS CONFIGURATION SWITCHES ===
USE_IBKR_NEWS = False   # Set to False to disable IBKR news
USE_GCS_NEWS = False    # Set to False to disable GCS news from Cloud Run app
USE_GEMINI_ANALYSIS = False  # Set to False to disable Gemini AI news analysis

# If both news sources are disabled, the system will return empty news data
# This allows running the trading bot without any news influence
