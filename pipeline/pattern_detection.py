import pandas as pd
import numpy as np


def detect_support_resistance(df: pd.DataFrame, window: int = 20, num_levels: int = 5) -> dict:
    highs = df["high"].values
    lows = df["low"].values
    close = df["close"].values
    current_price = close[-1]

    resistance_levels = []
    support_levels = []

    for i in range(window, len(highs) - window):
        if highs[i] == max(highs[i - window:i + window + 1]):
            resistance_levels.append({"price": float(highs[i]), "date": str(df.index[i].date()), "touches": 0})
        if lows[i] == min(lows[i - window:i + window + 1]):
            support_levels.append({"price": float(lows[i]), "date": str(df.index[i].date()), "touches": 0})

    resistance_levels = _cluster_levels(resistance_levels, tolerance=0.02)
    support_levels = _cluster_levels(support_levels, tolerance=0.02)

    resistance_levels = [r for r in resistance_levels if r["price"] > current_price]
    support_levels = [s for s in support_levels if s["price"] < current_price]

    resistance_levels.sort(key=lambda x: x["price"])
    support_levels.sort(key=lambda x: x["price"], reverse=True)

    return {
        "resistance": resistance_levels[:num_levels],
        "support": support_levels[:num_levels],
        "current_price": float(current_price),
    }


def _cluster_levels(levels, tolerance=0.02):
    if not levels:
        return []
    levels.sort(key=lambda x: x["price"])
    clustered = []
    current_cluster = [levels[0]]

    for level in levels[1:]:
        if abs(level["price"] - current_cluster[0]["price"]) / current_cluster[0]["price"] < tolerance:
            current_cluster.append(level)
        else:
            avg_price = sum(l["price"] for l in current_cluster) / len(current_cluster)
            clustered.append({
                "price": round(avg_price, 2),
                "touches": len(current_cluster),
                "first_seen": current_cluster[0]["date"],
                "last_seen": current_cluster[-1]["date"],
            })
            current_cluster = [level]

    if current_cluster:
        avg_price = sum(l["price"] for l in current_cluster) / len(current_cluster)
        clustered.append({
            "price": round(avg_price, 2),
            "touches": len(current_cluster),
            "first_seen": current_cluster[0]["date"],
            "last_seen": current_cluster[-1]["date"],
        })

    clustered.sort(key=lambda x: x["touches"], reverse=True)
    return clustered


def detect_signals(df: pd.DataFrame) -> list:
    signals = []
    if len(df) < 5:
        return signals

    latest = df.iloc[-1]
    prev = df.iloc[-2]

    # Golden Cross / Death Cross
    if "sma_50" in df.columns and "sma_200" in df.columns:
        sma50 = df["sma_50"].dropna()
        sma200 = df["sma_200"].dropna()
        if len(sma50) >= 2 and len(sma200) >= 2:
            if sma50.iloc[-2] < sma200.iloc[-2] and sma50.iloc[-1] > sma200.iloc[-1]:
                signals.append({"signal": "Golden Cross", "type": "bullish", "strength": "strong",
                                "description": "SMA 50 crossed above SMA 200"})
            elif sma50.iloc[-2] > sma200.iloc[-2] and sma50.iloc[-1] < sma200.iloc[-1]:
                signals.append({"signal": "Death Cross", "type": "bearish", "strength": "strong",
                                "description": "SMA 50 crossed below SMA 200"})

    # RSI signals
    if "rsi" in df.columns and pd.notna(latest.get("rsi")):
        rsi = latest["rsi"]
        if rsi > 70:
            signals.append({"signal": "RSI Overbought", "type": "bearish", "strength": "moderate",
                            "description": f"RSI at {rsi:.1f}, above 70 threshold"})
        elif rsi < 30:
            signals.append({"signal": "RSI Oversold", "type": "bullish", "strength": "moderate",
                            "description": f"RSI at {rsi:.1f}, below 30 threshold"})
        elif rsi > 50 and pd.notna(prev.get("rsi")) and prev["rsi"] <= 50:
            signals.append({"signal": "RSI Bullish Cross", "type": "bullish", "strength": "weak",
                            "description": "RSI crossed above 50 midline"})
        elif rsi < 50 and pd.notna(prev.get("rsi")) and prev["rsi"] >= 50:
            signals.append({"signal": "RSI Bearish Cross", "type": "bearish", "strength": "weak",
                            "description": "RSI crossed below 50 midline"})

    # MACD crossover
    macd_col, signal_col = "MACD_12_26_9", "MACDs_12_26_9"
    if macd_col in df.columns and signal_col in df.columns:
        if (pd.notna(latest.get(macd_col)) and pd.notna(latest.get(signal_col))
                and pd.notna(prev.get(macd_col)) and pd.notna(prev.get(signal_col))):
            if prev[macd_col] < prev[signal_col] and latest[macd_col] > latest[signal_col]:
                signals.append({"signal": "MACD Bullish Cross", "type": "bullish", "strength": "moderate",
                                "description": "MACD line crossed above signal line"})
            elif prev[macd_col] > prev[signal_col] and latest[macd_col] < latest[signal_col]:
                signals.append({"signal": "MACD Bearish Cross", "type": "bearish", "strength": "moderate",
                                "description": "MACD line crossed below signal line"})

    # Bollinger Band signals
    if "BBU_20_2.0" in df.columns and "BBL_20_2.0" in df.columns:
        bbu = latest.get("BBU_20_2.0")
        bbl = latest.get("BBL_20_2.0")
        close = latest["close"]
        if pd.notna(bbu) and close > bbu:
            signals.append({"signal": "BB Upper Break", "type": "bearish", "strength": "moderate",
                            "description": "Price above upper Bollinger Band"})
        elif pd.notna(bbl) and close < bbl:
            signals.append({"signal": "BB Lower Break", "type": "bullish", "strength": "moderate",
                            "description": "Price below lower Bollinger Band"})

        if pd.notna(bbu) and pd.notna(bbl) and bbu > 0:
            bandwidth = (bbu - bbl) / latest.get("BBM_20_2.0", bbu)
            if bandwidth < 0.04:
                signals.append({"signal": "BB Squeeze", "type": "neutral", "strength": "moderate",
                                "description": f"Bollinger Band squeeze (bandwidth {bandwidth:.3f}), breakout may follow"})

    # Volume spike
    if "volume" in df.columns and "volume_sma_20" in df.columns:
        vol = latest["volume"]
        vol_avg = latest.get("volume_sma_20")
        if pd.notna(vol_avg) and vol_avg > 0 and vol > vol_avg * 2:
            signals.append({"signal": "Volume Spike", "type": "neutral", "strength": "moderate",
                            "description": f"Volume {vol / vol_avg:.1f}x above 20-day average"})

    # Price vs Moving Averages
    close = latest["close"]
    for ma_name, ma_col in [("SMA 200", "sma_200"), ("SMA 50", "sma_50")]:
        if ma_col in df.columns and pd.notna(latest.get(ma_col)):
            ma_val = latest[ma_col]
            pct_from_ma = (close - ma_val) / ma_val * 100
            if close > ma_val:
                signals.append({"signal": f"Above {ma_name}", "type": "bullish", "strength": "weak",
                                "description": f"Price is {pct_from_ma:.1f}% above {ma_name}"})
            else:
                signals.append({"signal": f"Below {ma_name}", "type": "bearish", "strength": "weak",
                                "description": f"Price is {pct_from_ma:.1f}% below {ma_name}"})

    return signals


def compute_trend_scores(df: pd.DataFrame, info: dict) -> dict:
    latest = df.iloc[-1] if len(df) > 0 else pd.Series()
    scores = {}

    # Trend score based on MA alignment
    ma_score = 0
    close = latest.get("close", 0)
    for col in ["sma_20", "sma_50", "sma_200"]:
        if col in latest.index and pd.notna(latest[col]):
            ma_score += 1 if close > latest[col] else -1
    scores["trend"] = {"value": ma_score, "max": 3, "label": _score_label(ma_score, 3)}

    # Momentum score
    mom_score = 0
    rsi = latest.get("rsi")
    if pd.notna(rsi):
        if rsi > 50:
            mom_score += 1
        if rsi > 30:
            mom_score += 1
        if rsi < 70:
            mom_score += 1
    macd_h = latest.get("MACDh_12_26_9")
    if pd.notna(macd_h):
        mom_score += 1 if macd_h > 0 else -1
    scores["momentum"] = {"value": mom_score, "max": 4, "label": _score_label(mom_score, 4)}

    # Volatility assessment
    atr = latest.get("atr")
    if pd.notna(atr) and close > 0:
        atr_pct = (atr / close) * 100
        if atr_pct < 1.5:
            vol_label = "Low"
        elif atr_pct < 3:
            vol_label = "Moderate"
        else:
            vol_label = "High"
        scores["volatility"] = {"value": round(atr_pct, 2), "label": vol_label}

    # Short interest sentiment
    short_pct = info.get("shortPercentOfFloat")
    if short_pct is not None:
        if short_pct > 0.10:
            si_label = "High short interest"
        elif short_pct > 0.05:
            si_label = "Moderate"
        else:
            si_label = "Low"
        scores["short_interest"] = {"value": round(short_pct * 100, 2), "label": si_label}

    return scores


def _score_label(score, max_val):
    ratio = score / max_val if max_val > 0 else 0
    if ratio > 0.5:
        return "Bullish"
    elif ratio > 0:
        return "Slightly Bullish"
    elif ratio == 0:
        return "Neutral"
    elif ratio > -0.5:
        return "Slightly Bearish"
    else:
        return "Bearish"
