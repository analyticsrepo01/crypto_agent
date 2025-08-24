# /trading_bot/technical_analysis.py

import pandas as pd

def calculate_rsi(prices, period=14):
    """Calculate Relative Strength Index (RSI)"""
    if len(prices) < period + 1:
        return None
    deltas = pd.Series(prices).diff().dropna()
    gains = deltas.where(deltas > 0, 0)
    losses = -deltas.where(deltas < 0, 0)
    avg_gains = gains.rolling(window=period).mean()
    avg_losses = losses.rolling(window=period).mean()
    
    # Handle division by zero and NaN cases
    # Replace zero values with small values to avoid division by zero
    avg_gains = avg_gains.replace(0, 0.0001)
    avg_losses = avg_losses.replace(0, 0.0001)
    rs = avg_gains / avg_losses
    
    # Handle special cases
    rs = rs.fillna(1)  # If no gains or losses, neutral RSI = 50
    
    rsi = 100 - (100 / (1 + rs))
    
    # Ensure RSI is within valid range and handle any remaining NaN
    final_rsi = rsi.iloc[-1] if not rsi.empty else 50.0
    if pd.isna(final_rsi) or not (0 <= final_rsi <= 100):
        return 50.0  # Return neutral RSI for invalid values
    
    return final_rsi

def calculate_macd(prices, fast=12, slow=26, signal=9):
    """Calculate MACD (Moving Average Convergence Divergence)"""
    if len(prices) < slow + signal:
        return None, None, None
    price_series = pd.Series(prices)
    ema_fast = price_series.ewm(span=fast).mean()
    ema_slow = price_series.ewm(span=slow).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal).mean()
    histogram = macd_line - signal_line
    return (
        macd_line.iloc[-1] if not macd_line.empty else None,
        signal_line.iloc[-1] if not signal_line.empty else None,
        histogram.iloc[-1] if not histogram.empty else None
    )

def calculate_bollinger_bands(prices, period=20, std_dev=2):
    """Calculate Bollinger Bands"""
    if len(prices) < period:
        return None, None, None
    price_series = pd.Series(prices)
    sma = price_series.rolling(window=period).mean()
    std = price_series.rolling(window=period).std()
    upper_band = sma + (std * std_dev)
    lower_band = sma - (std * std_dev)
    return (
        upper_band.iloc[-1] if not upper_band.empty else None,
        sma.iloc[-1] if not sma.empty else None,
        lower_band.iloc[-1] if not lower_band.empty else None
    )

def calculate_stochastic(highs, lows, closes, k_period=14, d_period=3):
    """Calculate Stochastic Oscillator"""
    if len(closes) < k_period:
        return None, None
    high_series = pd.Series(highs)
    low_series = pd.Series(lows)
    close_series = pd.Series(closes)
    lowest_low = low_series.rolling(window=k_period).min()
    highest_high = high_series.rolling(window=k_period).max()
    k_percent = 100 * ((close_series - lowest_low) / (highest_high - lowest_low))
    d_percent = k_percent.rolling(window=d_period).mean()
    return (
        k_percent.iloc[-1] if not k_percent.empty else None,
        d_percent.iloc[-1] if not d_percent.empty else None
    )

def calculate_williams_r(highs, lows, closes, period=14):
    """Calculate Williams %R"""
    if len(closes) < period:
        return None
    high_series = pd.Series(highs)
    low_series = pd.Series(lows)
    close_series = pd.Series(closes)
    highest_high = high_series.rolling(window=period).max()
    lowest_low = low_series.rolling(window=period).min()
    williams_r = -100 * ((highest_high - close_series) / (highest_high - lowest_low))
    return williams_r.iloc[-1] if not williams_r.empty else None

def calculate_atr(highs, lows, closes, period=14):
    """Calculate Average True Range (ATR) for volatility"""
    if len(closes) < period + 1:
        return None
    high_series = pd.Series(highs)
    low_series = pd.Series(lows)
    close_series = pd.Series(closes)
    tr1 = high_series - low_series
    tr2 = abs(high_series - close_series.shift(1))
    tr3 = abs(low_series - close_series.shift(1))
    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = true_range.rolling(window=period).mean()
    return atr.iloc[-1] if not atr.empty else None

def calculate_volume_indicators(volumes, prices, period=20):
    """Calculate volume-based indicators like Volume Moving Average and OBV."""
    if len(volumes) < period or len(prices) < period:
        return None, None
    volume_series = pd.Series(volumes)
    price_series = pd.Series(prices)
    volume_ma = volume_series.rolling(window=period).mean()
    price_changes = price_series.diff()
    obv = volume_series.where(price_changes > 0, -volume_series).where(price_changes != 0, 0).cumsum()
    return (
        volume_ma.iloc[-1] if not volume_ma.empty else None,
        obv.iloc[-1] if not obv.empty else None
    )

def calculate_std_dev(prices, period=20):
    """Calculate Standard Deviation"""
    if len(prices) < period:
        return None
    price_series = pd.Series(prices)
    std_dev = price_series.rolling(window=period).std()
    return std_dev.iloc[-1] if not std_dev.empty else None

def calculate_ad_line(highs, lows, closes, volumes):
    """Calculate Accumulation/Distribution Line"""
    if len(closes) != len(highs) or len(closes) != len(lows) or len(closes) != len(volumes):
        return None
    high_series = pd.Series(highs)
    low_series = pd.Series(lows)
    close_series = pd.Series(closes)
    volume_series = pd.Series(volumes)
    clv = ((close_series - low_series) - (high_series - close_series)) / (high_series - low_series)
    clv = clv.fillna(0)  # Replace NaN with 0
    ad_line = (clv * volume_series).cumsum()
    return ad_line.iloc[-1] if not ad_line.empty else None

def calculate_pvt(prices, volumes):
    """Calculate Price and Volume Trend (PVT)"""
    if len(prices) != len(volumes) or len(prices) == 0:
        return None
    price_series = pd.Series(prices)
    volume_series = pd.Series(volumes)
    prev_close = price_series.shift(1)
    
    # Avoid division by zero
    prev_close_safe = prev_close.where(prev_close != 0, 1.0)
    
    pvt = (volume_series * (price_series - prev_close) / prev_close_safe).cumsum()
    return pvt.iloc[-1] if not pvt.empty else None

def calculate_parabolic_sar(highs, lows, acceleration=0.02, maximum=0.2):
    """Calculate Parabolic SAR"""
    if len(highs) != len(lows) or len(highs) == 0:
        return None
    high_series = pd.Series(highs)
    low_series = pd.Series(lows)
    sar = low_series.copy()
    trend = pd.Series(1, index=sar.index)
    af = pd.Series(acceleration, index=sar.index)
    ep = high_series.copy()

    for i in range(2, len(sar)):
        if trend.iloc[i-1] == 1: # Uptrend
            sar.iloc[i] = sar.iloc[i-1] + af.iloc[i-1] * (ep.iloc[i-1] - sar.iloc[i-1])
            if low_series.iloc[i] < sar.iloc[i]:
                trend.iloc[i] = -1
                sar.iloc[i] = ep.iloc[i-1]
                ep.iloc[i] = low_series.iloc[i]
                af.iloc[i] = acceleration
            else:
                trend.iloc[i] = 1
                if high_series.iloc[i] > ep.iloc[i-1]:
                    ep.iloc[i] = high_series.iloc[i]
                    af.iloc[i] = min(maximum, af.iloc[i-1] + acceleration)
                else:
                    ep.iloc[i] = ep.iloc[i-1]
                    af.iloc[i] = af.iloc[i-1]
        else: # Downtrend
            sar.iloc[i] = sar.iloc[i-1] - af.iloc[i-1] * (sar.iloc[i-1] - ep.iloc[i-1])
            if high_series.iloc[i] > sar.iloc[i]:
                trend.iloc[i] = 1
                sar.iloc[i] = ep.iloc[i-1]
                ep.iloc[i] = high_series.iloc[i]
                af.iloc[i] = acceleration
            else:
                trend.iloc[i] = -1
                if low_series.iloc[i] < ep.iloc[i-1]:
                    ep.iloc[i] = low_series.iloc[i]
                    af.iloc[i] = min(maximum, af.iloc[i-1] + acceleration)
                else:
                    ep.iloc[i] = ep.iloc[i-1]
                    af.iloc[i] = af.iloc[i-1]

    return sar.iloc[-1] if not sar.empty else None

def calculate_demarker(highs, lows, period=14):
    """Calculate DeMarker"""
    if len(highs) < period + 1 or len(lows) < period + 1:
        return None
    high_series = pd.Series(highs)
    low_series = pd.Series(lows)
    demax = (high_series - high_series.shift(1)).where(high_series > high_series.shift(1), 0)
    demin = (low_series.shift(1) - low_series).where(low_series < low_series.shift(1), 0)
    demax_avg = demax.rolling(window=period).mean()
    demin_avg = demin.rolling(window=period).mean()
    demarker = demax_avg / (demax_avg + demin_avg)
    return demarker.iloc[-1] if not demarker.empty else None

def calculate_adx(highs, lows, closes, period=14):
    """Calculate Average Directional Index (ADX)"""
    if len(closes) < period * 2:
        return None, None, None
    high_series = pd.Series(highs)
    low_series = pd.Series(lows)
    close_series = pd.Series(closes)
    
    up_move = high_series.diff()
    down_move = -low_series.diff()
    
    plus_dm = up_move.where((up_move > down_move) & (up_move > 0), 0)
    minus_dm = down_move.where((down_move > up_move) & (down_move > 0), 0)
    
    # Calculate ATR for the same period
    atr_values = []
    for i in range(period, len(close_series)):
        atr_val = calculate_atr(highs[i-period:i+1], lows[i-period:i+1], closes[i-period:i+1], period)
        if atr_val is not None:
            atr_values.append(atr_val)
        else:
            atr_values.append(1.0)  # Avoid division by zero
    
    if not atr_values:
        return None, None, None
        
    atr_series = pd.Series([1.0] * period + atr_values, index=close_series.index)
    
    plus_di = 100 * (plus_dm.ewm(alpha=1/period).mean() / atr_series)
    minus_di = 100 * (minus_dm.ewm(alpha=1/period).mean() / atr_series)
    
    # Avoid division by zero in DX calculation
    di_sum = plus_di + minus_di
    di_sum = di_sum.where(di_sum != 0, 1.0)  # Replace 0 with 1 to avoid division by zero
    
    dx = 100 * (abs(plus_di - minus_di) / di_sum)
    adx = dx.ewm(alpha=1/period).mean()
    
    return (adx.iloc[-1] if not adx.empty else None,
            plus_di.iloc[-1] if not plus_di.empty else None,
            minus_di.iloc[-1] if not minus_di.empty else None)

def calculate_moving_average_envelopes(prices, period=20, percentage=0.025):
    """Calculate Moving Average Envelopes"""
    if len(prices) < period:
        return None, None, None
    price_series = pd.Series(prices)
    sma = price_series.rolling(window=period).mean()
    upper_envelope = sma * (1 + percentage)
    lower_envelope = sma * (1 - percentage)
    return upper_envelope.iloc[-1], sma.iloc[-1], lower_envelope.iloc[-1]
