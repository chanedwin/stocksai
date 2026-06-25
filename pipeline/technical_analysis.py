import pandas as pd
import ta


def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # Trend: Simple Moving Averages
    df["sma_20"] = ta.trend.sma_indicator(df["close"], window=20)
    df["sma_50"] = ta.trend.sma_indicator(df["close"], window=50)
    df["sma_200"] = ta.trend.sma_indicator(df["close"], window=200)

    # Trend: Exponential Moving Averages
    df["ema_12"] = ta.trend.ema_indicator(df["close"], window=12)
    df["ema_26"] = ta.trend.ema_indicator(df["close"], window=26)

    # Momentum: RSI
    df["rsi"] = ta.momentum.rsi(df["close"], window=14)

    # Momentum: MACD
    macd = ta.trend.MACD(df["close"], window_slow=26, window_fast=12, window_sign=9)
    df["MACD_12_26_9"] = macd.macd()
    df["MACDs_12_26_9"] = macd.macd_signal()
    df["MACDh_12_26_9"] = macd.macd_diff()

    # Momentum: Stochastic Oscillator
    stoch = ta.momentum.StochasticOscillator(df["high"], df["low"], df["close"], window=14, smooth_window=3)
    df["STOCHk_14_3_3"] = stoch.stoch()
    df["STOCHd_14_3_3"] = stoch.stoch_signal()

    # Volatility: Bollinger Bands
    bb = ta.volatility.BollingerBands(df["close"], window=20, window_dev=2)
    df["BBU_20_2.0"] = bb.bollinger_hband()
    df["BBM_20_2.0"] = bb.bollinger_mavg()
    df["BBL_20_2.0"] = bb.bollinger_lband()

    # Volatility: Average True Range
    df["atr"] = ta.volatility.average_true_range(df["high"], df["low"], df["close"], window=14)

    # Volume: On Balance Volume
    df["obv"] = ta.volume.on_balance_volume(df["close"], df["volume"])

    # Volume: 20-day volume moving average
    df["volume_sma_20"] = ta.trend.sma_indicator(df["volume"].astype(float), window=20)

    # Volume: VWAP rolling 20-day approximation (true VWAP is intraday only)
    typical_price = (df["high"] + df["low"] + df["close"]) / 3
    df["vwap"] = (
        (typical_price * df["volume"]).rolling(window=20).sum()
        / df["volume"].rolling(window=20).sum()
    )

    # Daily returns
    df["daily_return"] = df["close"].pct_change()
    df["cumulative_return"] = (1 + df["daily_return"]).cumprod() - 1

    return df
