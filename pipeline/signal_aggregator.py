import pandas as pd
import numpy as np
from pipeline.technical_analysis import compute_indicators
from pipeline.pattern_detection import detect_signals, compute_trend_scores, detect_support_resistance
from pipeline.flow_analysis import get_short_interest, get_options_flow, get_ownership_breakdown, get_insider_activity
from pipeline.market_context import get_analyst_data, get_earnings_impact
from pipeline.earnings_analysis import compute_growth_trends, compute_margin_trends


TIMEFRAMES = {
    "daily": None,
    "weekly": "W",
    "monthly": "ME",
}

SIGNAL_WEIGHTS = {
    "strong": 3,
    "moderate": 2,
    "weak": 1,
}


def resample_ohlcv(df: pd.DataFrame, freq: str) -> pd.DataFrame:
    resampled = df.resample(freq).agg({
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum",
    }).dropna(subset=["open", "close"])
    return resampled


def compute_timeframe_signals(price_df: pd.DataFrame) -> dict:
    results = {}
    for label, freq in TIMEFRAMES.items():
        if freq is None:
            tf_df = price_df.copy()
        else:
            tf_df = resample_ohlcv(price_df, freq)

        if len(tf_df) < 10:
            continue

        tf_df = compute_indicators(tf_df)
        sigs = detect_signals(tf_df)
        results[label] = {
            "signals": sigs,
            "df": tf_df,
        }
    return results


def compute_yearly_performance(price_df: pd.DataFrame) -> list:
    if price_df.empty:
        return []

    df = price_df.copy()
    df["year"] = df.index.year
    years = sorted(df["year"].unique())

    yearly = []
    for year in years:
        year_df = df[df["year"] == year]
        if len(year_df) < 2:
            continue
        open_price = year_df["close"].iloc[0]
        close_price = year_df["close"].iloc[-1]
        high = year_df["high"].max()
        low = year_df["low"].min()
        ret = (close_price - open_price) / open_price * 100
        yearly.append({
            "year": int(year),
            "return_pct": round(ret, 1),
            "high": round(float(high), 2),
            "low": round(float(low), 2),
            "range_pct": round((high - low) / low * 100, 1),
        })
    return yearly


def compute_seasonal_analysis(price_df: pd.DataFrame) -> dict:
    if len(price_df) < 252:
        return {"available": False}

    df = price_df.copy()
    df["month"] = df.index.month
    df["day_of_week"] = df.index.dayofweek
    df["daily_return"] = df["close"].pct_change() * 100

    # Monthly seasonality: average return by month across all years
    monthly = df.groupby("month")["daily_return"].agg(["mean", "std", "count"])
    monthly["total_return"] = df.groupby("month")[["close"]].apply(
        lambda g: (g["close"].iloc[-1] / g["close"].iloc[0] - 1) * 100
        if len(g) > 1 else 0
    ).values

    month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                   "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    monthly_results = []
    for month_num in range(1, 13):
        if month_num in monthly.index:
            row = monthly.loc[month_num]
            year_returns = []
            for year in df.index.year.unique():
                m_data = df[(df.index.year == year) & (df["month"] == month_num)]
                if len(m_data) >= 2:
                    ret = (m_data["close"].iloc[-1] / m_data["close"].iloc[0] - 1) * 100
                    year_returns.append(ret)

            avg_monthly_return = np.mean(year_returns) if year_returns else 0
            win_rate = sum(1 for r in year_returns if r > 0) / len(year_returns) * 100 if year_returns else 0

            monthly_results.append({
                "month": month_names[month_num - 1],
                "month_num": month_num,
                "avg_daily_return": round(row["mean"], 3),
                "avg_monthly_return": round(avg_monthly_return, 2),
                "win_rate": round(win_rate, 1),
                "years_analyzed": len(year_returns),
            })

    # Day of week seasonality
    dow_names = ["Mon", "Tue", "Wed", "Thu", "Fri"]
    dow = df.groupby("day_of_week")["daily_return"].agg(["mean", "std", "count"])
    dow_results = []
    for d in range(5):
        if d in dow.index:
            row = dow.loc[d]
            day_returns = df[df["day_of_week"] == d]["daily_return"].dropna()
            win_rate = (day_returns > 0).sum() / len(day_returns) * 100 if len(day_returns) > 0 else 0
            dow_results.append({
                "day": dow_names[d],
                "avg_return": round(row["mean"], 3),
                "win_rate": round(win_rate, 1),
                "observations": int(row["count"]),
            })

    # Quarter analysis
    df["quarter"] = df.index.quarter
    quarter_results = []
    for q in range(1, 5):
        q_data = df[df["quarter"] == q]
        year_returns = []
        for year in q_data.index.year.unique():
            qy_data = q_data[q_data.index.year == year]
            if len(qy_data) >= 2:
                ret = (qy_data["close"].iloc[-1] / qy_data["close"].iloc[0] - 1) * 100
                year_returns.append(ret)

        avg_return = np.mean(year_returns) if year_returns else 0
        win_rate = sum(1 for r in year_returns if r > 0) / len(year_returns) * 100 if year_returns else 0
        quarter_results.append({
            "quarter": f"Q{q}",
            "avg_return": round(avg_return, 2),
            "win_rate": round(win_rate, 1),
            "years_analyzed": len(year_returns),
        })

    return {
        "available": True,
        "monthly": monthly_results,
        "day_of_week": dow_results,
        "quarterly": quarter_results,
    }


def _score_from_signals(signals: list) -> tuple:
    bullish = 0
    bearish = 0
    for s in signals:
        w = SIGNAL_WEIGHTS.get(s["strength"], 1)
        if s["type"] == "bullish":
            bullish += w
        elif s["type"] == "bearish":
            bearish += w
    return bullish, bearish


def compute_flow_signals(info: dict, ticker: str) -> list:
    signals = []

    # Short interest signal
    si = get_short_interest(info)
    si_pct = si.get("short_pct_of_float")
    if si_pct is not None:
        if si_pct > 0.10:
            signals.append({"signal": "High Short Interest", "type": "bearish", "strength": "moderate",
                            "category": "flow", "description": f"{si_pct*100:.1f}% of float sold short"})
        elif si_pct < 0.02:
            signals.append({"signal": "Low Short Interest", "type": "bullish", "strength": "weak",
                            "category": "flow", "description": f"Only {si_pct*100:.1f}% of float sold short"})

    si_change = si.get("short_change_pct")
    if si_change is not None:
        if si_change > 0.10:
            signals.append({"signal": "Short Interest Rising", "type": "bearish", "strength": "moderate",
                            "category": "flow", "description": f"Short interest up {si_change*100:.1f}% MoM"})
        elif si_change < -0.10:
            signals.append({"signal": "Short Covering", "type": "bullish", "strength": "moderate",
                            "category": "flow", "description": f"Short interest down {abs(si_change)*100:.1f}% MoM"})

    # Options sentiment
    try:
        options = get_options_flow(ticker, max_expirations=4)
        if options.get("available"):
            pc = options.get("pc_ratio_volume")
            if pc is not None:
                if pc > 1.2:
                    signals.append({"signal": "High Put/Call Ratio", "type": "bearish", "strength": "moderate",
                                    "category": "flow", "description": f"P/C ratio {pc:.2f}, heavy put buying"})
                elif pc < 0.5:
                    signals.append({"signal": "Low Put/Call Ratio", "type": "bullish", "strength": "moderate",
                                    "category": "flow", "description": f"P/C ratio {pc:.2f}, heavy call buying"})

            unusual = options.get("unusual_activity", [])
            call_unusual = sum(1 for u in unusual if u["type"] == "CALL")
            put_unusual = sum(1 for u in unusual if u["type"] == "PUT")
            if call_unusual > put_unusual and call_unusual >= 3:
                signals.append({"signal": "Unusual Call Activity", "type": "bullish", "strength": "moderate",
                                "category": "flow", "description": f"{call_unusual} unusual call contracts detected"})
            elif put_unusual > call_unusual and put_unusual >= 3:
                signals.append({"signal": "Unusual Put Activity", "type": "bearish", "strength": "moderate",
                                "category": "flow", "description": f"{put_unusual} unusual put contracts detected"})
    except Exception:
        pass

    # Insider activity
    try:
        insider = get_insider_activity(ticker)
        summary = insider.get("summary")
        if summary is not None and not summary.empty:
            for _, row in summary.iterrows():
                label = str(row.iloc[0])
                val = row.iloc[1]
                if "Net" in label and "%" not in label and isinstance(val, (int, float)):
                    if val > 0:
                        signals.append({"signal": "Net Insider Buying", "type": "bullish", "strength": "strong",
                                        "category": "flow", "description": f"Net {val:,.0f} insider shares purchased"})
                    elif val < 0:
                        signals.append({"signal": "Net Insider Selling", "type": "bearish", "strength": "weak",
                                        "category": "flow", "description": f"Net {abs(val):,.0f} insider shares sold"})
    except Exception:
        pass

    # Institutional ownership
    ownership = get_ownership_breakdown(info)
    inst_pct = ownership.get("institutions_pct")
    if inst_pct is not None:
        if inst_pct > 0.80:
            signals.append({"signal": "High Institutional Ownership", "type": "bullish", "strength": "weak",
                            "category": "flow", "description": f"{inst_pct*100:.0f}% held by institutions"})

    return signals


def compute_fundamental_signals(info: dict, fundamentals: dict) -> list:
    signals = []

    # P/E valuation
    pe = info.get("trailingPE")
    fwd_pe = info.get("forwardPE")
    if pe is not None and fwd_pe is not None:
        if fwd_pe < pe * 0.85:
            signals.append({"signal": "Earnings Growth Expected", "type": "bullish", "strength": "moderate",
                            "category": "fundamental", "description": f"Forward P/E ({fwd_pe:.1f}) well below trailing ({pe:.1f})"})
        elif fwd_pe > pe * 1.15:
            signals.append({"signal": "Earnings Decline Expected", "type": "bearish", "strength": "moderate",
                            "category": "fundamental", "description": f"Forward P/E ({fwd_pe:.1f}) above trailing ({pe:.1f})"})

    # PEG ratio
    peg = info.get("pegRatio")
    if peg is not None:
        if peg < 1:
            signals.append({"signal": "PEG Below 1", "type": "bullish", "strength": "moderate",
                            "category": "fundamental", "description": f"PEG ratio {peg:.2f}, growth at reasonable price"})
        elif peg > 2:
            signals.append({"signal": "PEG Above 2", "type": "bearish", "strength": "weak",
                            "category": "fundamental", "description": f"PEG ratio {peg:.2f}, growth may be priced in"})

    # Revenue growth
    rev_growth = info.get("revenueGrowth")
    if rev_growth is not None:
        if rev_growth > 0.20:
            signals.append({"signal": "Strong Revenue Growth", "type": "bullish", "strength": "strong",
                            "category": "fundamental", "description": f"Revenue growing {rev_growth*100:.0f}% YoY"})
        elif rev_growth > 0.05:
            signals.append({"signal": "Steady Revenue Growth", "type": "bullish", "strength": "weak",
                            "category": "fundamental", "description": f"Revenue growing {rev_growth*100:.0f}% YoY"})
        elif rev_growth < -0.05:
            signals.append({"signal": "Revenue Declining", "type": "bearish", "strength": "strong",
                            "category": "fundamental", "description": f"Revenue down {abs(rev_growth)*100:.0f}% YoY"})

    # Earnings growth
    earn_growth = info.get("earningsGrowth")
    if earn_growth is not None:
        if earn_growth > 0.25:
            signals.append({"signal": "Strong Earnings Growth", "type": "bullish", "strength": "strong",
                            "category": "fundamental", "description": f"Earnings up {earn_growth*100:.0f}% YoY"})
        elif earn_growth < -0.10:
            signals.append({"signal": "Earnings Decline", "type": "bearish", "strength": "moderate",
                            "category": "fundamental", "description": f"Earnings down {abs(earn_growth)*100:.0f}% YoY"})

    # Profit margins
    op_margin = info.get("operatingMargins")
    if op_margin is not None:
        if op_margin > 0.25:
            signals.append({"signal": "High Operating Margin", "type": "bullish", "strength": "weak",
                            "category": "fundamental", "description": f"{op_margin*100:.0f}% operating margin"})
        elif op_margin < 0.05:
            signals.append({"signal": "Thin Margins", "type": "bearish", "strength": "weak",
                            "category": "fundamental", "description": f"Only {op_margin*100:.1f}% operating margin"})

    # Margin trend from earnings analysis
    try:
        margin_data = compute_margin_trends(fundamentals)
        qm = margin_data.get("quarterly")
        if qm and qm.get("margins"):
            op_margins = qm["margins"].get("Operating Margin", [])
            valid = [v for v in op_margins if not (isinstance(v, float) and np.isnan(v))]
            if len(valid) >= 3:
                if valid[-1] > valid[-2] > valid[-3]:
                    signals.append({"signal": "Margin Expansion", "type": "bullish", "strength": "moderate",
                                    "category": "fundamental", "description": "Operating margin expanding for 3 consecutive quarters"})
                elif valid[-1] < valid[-2] < valid[-3]:
                    signals.append({"signal": "Margin Compression", "type": "bearish", "strength": "moderate",
                                    "category": "fundamental", "description": "Operating margin contracting for 3 consecutive quarters"})
    except Exception:
        pass

    # Debt health
    debt_equity = info.get("debtToEquity")
    if debt_equity is not None:
        if debt_equity > 200:
            signals.append({"signal": "High Leverage", "type": "bearish", "strength": "moderate",
                            "category": "fundamental", "description": f"Debt/equity ratio of {debt_equity:.0f}"})
        elif debt_equity < 30:
            signals.append({"signal": "Low Debt", "type": "bullish", "strength": "weak",
                            "category": "fundamental", "description": f"Debt/equity ratio of only {debt_equity:.0f}"})

    return signals


def compute_analyst_signals(ticker: str) -> list:
    signals = []
    try:
        analyst = get_analyst_data(ticker)

        # Price target vs current
        targets = analyst.get("price_targets")
        if targets:
            current = targets.get("current")
            mean_target = targets.get("mean")
            if current and mean_target:
                upside = (mean_target - current) / current * 100
                if upside > 20:
                    signals.append({"signal": "Strong Analyst Upside", "type": "bullish", "strength": "moderate",
                                    "category": "analyst", "description": f"Mean target ${mean_target:.0f} ({upside:+.0f}% upside)"})
                elif upside > 5:
                    signals.append({"signal": "Analyst Upside", "type": "bullish", "strength": "weak",
                                    "category": "analyst", "description": f"Mean target ${mean_target:.0f} ({upside:+.0f}%)"})
                elif upside < -10:
                    signals.append({"signal": "Analyst Downside", "type": "bearish", "strength": "moderate",
                                    "category": "analyst", "description": f"Mean target ${mean_target:.0f} ({upside:+.0f}%)"})

        # Recommendation consensus
        recs = analyst.get("recommendations")
        if recs is not None and not recs.empty:
            latest = recs.iloc[0]
            buys = int(latest.get("strongBuy", 0)) + int(latest.get("buy", 0))
            sells = int(latest.get("sell", 0)) + int(latest.get("strongSell", 0))
            holds = int(latest.get("hold", 0))
            total = buys + sells + holds
            if total > 0:
                buy_pct = buys / total * 100
                if buy_pct > 70:
                    signals.append({"signal": "Strong Buy Consensus", "type": "bullish", "strength": "moderate",
                                    "category": "analyst", "description": f"{buy_pct:.0f}% of analysts rate Buy/Strong Buy"})
                elif buy_pct < 30:
                    signals.append({"signal": "Weak Analyst Sentiment", "type": "bearish", "strength": "weak",
                                    "category": "analyst", "description": f"Only {buy_pct:.0f}% of analysts rate Buy"})

        # EPS estimate growth
        eps_est = analyst.get("eps_estimate")
        if eps_est is not None and not eps_est.empty and "growth" in eps_est.columns:
            growth_vals = eps_est["growth"].dropna()
            if len(growth_vals) > 0:
                next_growth = growth_vals.iloc[0]
                if next_growth > 0.15:
                    signals.append({"signal": "EPS Growth Expected", "type": "bullish", "strength": "weak",
                                    "category": "analyst", "description": f"Next period EPS growth estimate: {next_growth*100:+.0f}%"})
                elif next_growth < -0.10:
                    signals.append({"signal": "EPS Decline Expected", "type": "bearish", "strength": "weak",
                                    "category": "analyst", "description": f"Next period EPS growth estimate: {next_growth*100:+.0f}%"})
    except Exception:
        pass

    return signals


def compute_sr_signals(sr_levels: dict) -> list:
    signals = []
    current = sr_levels.get("current_price", 0)
    if current == 0:
        return signals

    supports = sr_levels.get("support", [])
    resistances = sr_levels.get("resistance", [])

    if supports:
        nearest_support = supports[0]
        dist = (current - nearest_support["price"]) / current * 100
        if dist < 2:
            signals.append({"signal": "Near Support", "type": "bullish", "strength": "moderate",
                            "category": "technical", "description": f"Price within {dist:.1f}% of support at ${nearest_support['price']:.0f} ({nearest_support['touches']}x tested)"})
        elif dist < 5 and nearest_support["touches"] >= 3:
            signals.append({"signal": "Strong Support Below", "type": "bullish", "strength": "weak",
                            "category": "technical", "description": f"Support at ${nearest_support['price']:.0f} ({nearest_support['touches']}x tested, {dist:.1f}% below)"})

    if resistances:
        nearest_resistance = resistances[0]
        dist = (nearest_resistance["price"] - current) / current * 100
        if dist < 2:
            signals.append({"signal": "Near Resistance", "type": "bearish", "strength": "moderate",
                            "category": "technical", "description": f"Price within {dist:.1f}% of resistance at ${nearest_resistance['price']:.0f} ({nearest_resistance['touches']}x tested)"})

    return signals


def aggregate_all_signals(
    price_df: pd.DataFrame,
    info: dict,
    fundamentals: dict,
    ticker: str,
) -> dict:
    # Multi-timeframe technical signals
    tf_results = compute_timeframe_signals(price_df)

    # Add category to technical signals
    for tf_label, tf_data in tf_results.items():
        for s in tf_data["signals"]:
            s["category"] = "technical"
            s["timeframe"] = tf_label

    # S/R proximity signals (daily only)
    sr_levels = detect_support_resistance(price_df)
    sr_signals = compute_sr_signals(sr_levels)
    for s in sr_signals:
        s["timeframe"] = "daily"

    # Flow signals
    flow_sigs = compute_flow_signals(info, ticker)
    for s in flow_sigs:
        s["timeframe"] = "current"

    # Fundamental signals
    fund_sigs = compute_fundamental_signals(info, fundamentals)
    for s in fund_sigs:
        s["timeframe"] = "current"

    # Analyst signals
    analyst_sigs = compute_analyst_signals(ticker)
    for s in analyst_sigs:
        s["timeframe"] = "current"

    # Yearly performance
    yearly = compute_yearly_performance(price_df)

    # Seasonal analysis
    seasonal = compute_seasonal_analysis(price_df)

    # Collect all signals
    all_signals = sr_signals[:]
    for tf_data in tf_results.values():
        all_signals.extend(tf_data["signals"])
    all_signals.extend(flow_sigs)
    all_signals.extend(fund_sigs)
    all_signals.extend(analyst_sigs)

    # Compute composite scores
    categories = {}
    for s in all_signals:
        cat = s.get("category", "other")
        if cat not in categories:
            categories[cat] = {"bullish": 0, "bearish": 0, "signals": []}
        w = SIGNAL_WEIGHTS.get(s["strength"], 1)
        if s["type"] == "bullish":
            categories[cat]["bullish"] += w
        elif s["type"] == "bearish":
            categories[cat]["bearish"] += w
        categories[cat]["signals"].append(s)

    # Timeframe scores
    timeframe_scores = {}
    for tf_label, tf_data in tf_results.items():
        b, br = _score_from_signals(tf_data["signals"])
        total = b + br
        if total > 0:
            score = round((b - br) / total * 100)
        else:
            score = 0
        timeframe_scores[tf_label] = {
            "score": score,
            "bullish_count": sum(1 for s in tf_data["signals"] if s["type"] == "bullish"),
            "bearish_count": sum(1 for s in tf_data["signals"] if s["type"] == "bearish"),
            "neutral_count": sum(1 for s in tf_data["signals"] if s["type"] == "neutral"),
        }

    # Overall composite
    total_bull = sum(c["bullish"] for c in categories.values())
    total_bear = sum(c["bearish"] for c in categories.values())
    total_weight = total_bull + total_bear
    if total_weight > 0:
        composite_score = round((total_bull - total_bear) / total_weight * 100)
    else:
        composite_score = 0

    if composite_score > 40:
        verdict = "Bullish"
    elif composite_score > 15:
        verdict = "Slightly Bullish"
    elif composite_score > -15:
        verdict = "Neutral"
    elif composite_score > -40:
        verdict = "Slightly Bearish"
    else:
        verdict = "Bearish"

    category_scores = {}
    for cat, data in categories.items():
        total = data["bullish"] + data["bearish"]
        if total > 0:
            cat_score = round((data["bullish"] - data["bearish"]) / total * 100)
        else:
            cat_score = 0
        category_scores[cat] = {
            "score": cat_score,
            "bullish_weight": data["bullish"],
            "bearish_weight": data["bearish"],
            "signal_count": len(data["signals"]),
        }

    return {
        "composite_score": composite_score,
        "verdict": verdict,
        "total_bullish": total_bull,
        "total_bearish": total_bear,
        "category_scores": category_scores,
        "timeframe_scores": timeframe_scores,
        "all_signals": all_signals,
        "yearly_performance": yearly,
        "seasonal": seasonal,
    }
