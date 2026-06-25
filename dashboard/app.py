import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd

from pipeline.data_fetcher import fetch_price_data, fetch_fundamental_data
from pipeline.technical_analysis import compute_indicators
from pipeline.fundamental_analysis import compute_ratios, get_financial_statements
from pipeline.flow_analysis import (
    get_ownership_breakdown, get_institutional_holders, get_mutualfund_holders,
    get_insider_activity, get_short_interest, get_options_flow,
)
from pipeline.pattern_detection import detect_support_resistance, detect_signals, compute_trend_scores

st.set_page_config(page_title="Stock Analysis", layout="wide")

# --- Color helpers ---
GREEN = "#26a69a"
RED = "#ef5350"
YELLOW = "#ffa726"
BLUE = "#42a5f5"
GREY = "#9e9e9e"


def color_value(val, good_if_high=True, thresholds=None):
    if val is None:
        return GREY
    if thresholds:
        low, high = thresholds
        if val > high:
            return GREEN if good_if_high else RED
        elif val < low:
            return RED if good_if_high else GREEN
        return YELLOW
    return GREEN if (val > 0) == good_if_high else RED


def colored_metric(label, value, delta=None, delta_suffix="", good_if_positive=True):
    if delta is not None:
        color = GREEN if (delta > 0) == good_if_positive else RED
        arrow = "^" if delta > 0 else "v"
        delta_str = f'<span style="color:{color};font-size:0.85em">{arrow} {abs(delta):.2f}{delta_suffix}</span>'
    else:
        delta_str = ""
    return f'<div style="text-align:center"><div style="color:#aaa;font-size:0.75em">{label}</div><div style="font-size:1.3em;font-weight:600">{value}</div>{delta_str}</div>'


def signal_badge(signal_type, text):
    colors = {"bullish": GREEN, "bearish": RED, "neutral": YELLOW}
    bg = colors.get(signal_type, GREY)
    return f'<span style="background:{bg}22;color:{bg};border:1px solid {bg};border-radius:4px;padding:2px 8px;font-size:0.85em;font-weight:500">{text}</span>'


# --- Sidebar ---
st.sidebar.title("Stock Analysis")
ticker = st.sidebar.text_input("Ticker", value="GOOGL").upper()
period = st.sidebar.selectbox("Period", ["6mo", "1y", "2y", "5y", "10y", "max"], index=2)
ta_overlays = st.sidebar.multiselect(
    "Chart Overlays",
    ["SMA 20", "SMA 50", "SMA 200", "EMA 12", "EMA 26", "Bollinger Bands", "Support/Resistance"],
    default=["SMA 50", "SMA 200", "Support/Resistance"],
)
show_flow = st.sidebar.checkbox("Show Money Flow", value=True)


@st.cache_data(ttl=900)
def load_data(t, p):
    price = fetch_price_data(t, period=p)
    fund = fetch_fundamental_data(t)
    return price, fund


@st.cache_data(ttl=900)
def load_flow_data(t):
    inst = get_institutional_holders(t)
    mf = get_mutualfund_holders(t)
    insider = get_insider_activity(t)
    options = get_options_flow(t)
    return inst, mf, insider, options


with st.spinner("Fetching data..."):
    price_df, fundamentals = load_data(ticker, period)

if price_df.empty:
    st.error(f"No data found for {ticker}.")
    st.stop()

df = compute_indicators(price_df)
info = fundamentals["info"]
ratios = compute_ratios(info)
statements = get_financial_statements(fundamentals)
sr_levels = detect_support_resistance(df)
signals = detect_signals(df)
trend_scores = compute_trend_scores(df, info)
short_data = get_short_interest(info)
ownership = get_ownership_breakdown(info)


# --- Header ---
company_name = info.get("longName", ticker)
current_price = info.get("currentPrice") or (df["close"].iloc[-1] if len(df) > 0 else None)
prev_close = info.get("previousClose")
market_cap = info.get("marketCap")
sector = info.get("sector", "N/A")
industry = info.get("industry", "N/A")

st.title(f"{company_name} ({ticker})")
st.caption(f"{sector} | {industry}")

# Key metrics row with deltas
cols = st.columns(6)
if current_price:
    cols[0].metric("Price", f"${current_price:,.2f}")
if prev_close and current_price:
    change = current_price - prev_close
    change_pct = (change / prev_close) * 100
    cols[1].metric("Change", f"${change:+,.2f}", f"{change_pct:+.2f}%")
if market_cap:
    if market_cap >= 1e12:
        cap_str = f"${market_cap / 1e12:.2f}T"
    elif market_cap >= 1e9:
        cap_str = f"${market_cap / 1e9:.2f}B"
    else:
        cap_str = f"${market_cap / 1e6:.0f}M"
    cols[2].metric("Market Cap", cap_str)
pe = info.get("trailingPE")
fwd_pe = info.get("forwardPE")
if pe:
    pe_delta = None
    if fwd_pe:
        pe_delta = f"{fwd_pe:.1f} fwd"
    cols[3].metric("P/E", f"{pe:.1f}", pe_delta)
eps = info.get("trailingEps")
if eps:
    cols[4].metric("EPS", f"${eps:.2f}")
div_yield = info.get("dividendYield")
cols[5].metric("Div Yield", f"{div_yield * 100:.2f}%" if div_yield else "N/A")


# --- Trend Scores & Signals ---
st.header("Signals & Trend Scores")

score_cols = st.columns(len(trend_scores) + 1)
for i, (key, data) in enumerate(trend_scores.items()):
    label = key.replace("_", " ").title()
    badge_type = "bullish" if "Bullish" in data["label"] else ("bearish" if "Bearish" in data["label"] else "neutral")
    if "max" in data:
        val_str = f"{data['value']}/{data['max']}"
    else:
        val_str = f"{data['value']}%"
    score_cols[i].markdown(
        f"**{label}**\n\n{val_str}\n\n{signal_badge(badge_type, data['label'])}",
        unsafe_allow_html=True,
    )

# Short interest in the last column
if short_data.get("short_pct_of_float") is not None:
    si_pct = short_data["short_pct_of_float"] * 100
    si_type = "bearish" if si_pct > 5 else ("neutral" if si_pct > 2 else "bullish")
    si_change = short_data.get("short_change_pct")
    si_delta = ""
    if si_change is not None:
        arrow = "^" if si_change > 0 else "v"
        si_color = RED if si_change > 0 else GREEN
        si_delta = f'<span style="color:{si_color}"> {arrow} {abs(si_change)*100:.1f}% MoM</span>'
    score_cols[-1].markdown(
        f"**Short Interest**\n\n{si_pct:.2f}% of float{si_delta}\n\n"
        f"{signal_badge(si_type, 'Days to cover: ' + str(short_data.get('short_ratio', 'N/A')))}",
        unsafe_allow_html=True,
    )

# Active signals
if signals:
    st.subheader("Active Signals")
    signal_html = " &nbsp; ".join(
        signal_badge(s["type"], f"{s['signal']}: {s['description']}")
        for s in sorted(signals, key=lambda x: {"strong": 0, "moderate": 1, "weak": 2}.get(x["strength"], 3))
    )
    st.markdown(signal_html, unsafe_allow_html=True)


# --- Technical Analysis ---
st.header("Technical Analysis")

fig = make_subplots(
    rows=4, cols=1,
    shared_xaxes=True,
    vertical_spacing=0.03,
    row_heights=[0.5, 0.15, 0.15, 0.2],
    subplot_titles=("Price", "RSI", "MACD", "Volume"),
)

# Candlestick
fig.add_trace(
    go.Candlestick(
        x=df.index, open=df["open"], high=df["high"], low=df["low"], close=df["close"],
        name="Price", increasing_line_color=GREEN, decreasing_line_color=RED,
    ),
    row=1, col=1,
)

# Support/Resistance lines
if "Support/Resistance" in ta_overlays:
    for level in sr_levels.get("resistance", []):
        fig.add_hline(
            y=level["price"], line_dash="dash", line_color=RED, opacity=0.6, row=1, col=1,
            annotation_text=f"R ${level['price']:.0f} ({level['touches']}x)",
            annotation_position="top right",
            annotation_font_color=RED,
        )
    for level in sr_levels.get("support", []):
        fig.add_hline(
            y=level["price"], line_dash="dash", line_color=GREEN, opacity=0.6, row=1, col=1,
            annotation_text=f"S ${level['price']:.0f} ({level['touches']}x)",
            annotation_position="bottom right",
            annotation_font_color=GREEN,
        )

# Moving average overlays
overlay_map = {
    "SMA 20": ("sma_20", "#ff9800"),
    "SMA 50": ("sma_50", "#2196f3"),
    "SMA 200": ("sma_200", "#9c27b0"),
    "EMA 12": ("ema_12", "#4caf50"),
    "EMA 26": ("ema_26", "#f44336"),
}

for name in ta_overlays:
    if name == "Bollinger Bands":
        for col_name, color, dash in [
            ("BBU_20_2.0", "rgba(33,150,243,0.3)", "dash"),
            ("BBM_20_2.0", "rgba(33,150,243,0.5)", "dot"),
            ("BBL_20_2.0", "rgba(33,150,243,0.3)", "dash"),
        ]:
            if col_name in df.columns:
                fig.add_trace(
                    go.Scatter(x=df.index, y=df[col_name], name=col_name.split("_")[0],
                               line=dict(color=color, dash=dash, width=1)),
                    row=1, col=1,
                )
    elif name in overlay_map:
        col_name, color = overlay_map[name]
        if col_name in df.columns:
            fig.add_trace(
                go.Scatter(x=df.index, y=df[col_name], name=name,
                           line=dict(color=color, width=1.5)),
                row=1, col=1,
            )

# RSI with colored zones
if "rsi" in df.columns:
    rsi_colors = [RED if v > 70 else (GREEN if v < 30 else "#7e57c2") for v in df["rsi"].fillna(50)]
    fig.add_trace(
        go.Scatter(x=df.index, y=df["rsi"], name="RSI",
                   line=dict(color="#7e57c2", width=1.5)),
        row=2, col=1,
    )
    fig.add_hrect(y0=70, y1=100, fillcolor=RED, opacity=0.08, line_width=0, row=2, col=1)
    fig.add_hrect(y0=0, y1=30, fillcolor=GREEN, opacity=0.08, line_width=0, row=2, col=1)
    fig.add_hline(y=70, line_dash="dash", line_color=RED, opacity=0.5, row=2, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color=GREEN, opacity=0.5, row=2, col=1)
    fig.add_hline(y=50, line_dash="dot", line_color=GREY, opacity=0.3, row=2, col=1)

# MACD
macd_col = "MACD_12_26_9"
signal_col_name = "MACDs_12_26_9"
hist_col = "MACDh_12_26_9"

if macd_col in df.columns:
    fig.add_trace(
        go.Scatter(x=df.index, y=df[macd_col], name="MACD", line=dict(color=BLUE, width=1.5)),
        row=3, col=1,
    )
if signal_col_name in df.columns:
    fig.add_trace(
        go.Scatter(x=df.index, y=df[signal_col_name], name="Signal", line=dict(color=YELLOW, width=1.5)),
        row=3, col=1,
    )
if hist_col in df.columns:
    hist_colors = [GREEN if v >= 0 else RED for v in df[hist_col].fillna(0)]
    fig.add_trace(
        go.Bar(x=df.index, y=df[hist_col], name="Histogram", marker_color=hist_colors),
        row=3, col=1,
    )
    fig.add_hline(y=0, line_color=GREY, opacity=0.3, row=3, col=1)

# Volume
vol_colors = [GREEN if c >= o else RED for c, o in zip(df["close"], df["open"])]
fig.add_trace(
    go.Bar(x=df.index, y=df["volume"], name="Volume", marker_color=vol_colors, opacity=0.7),
    row=4, col=1,
)
if "volume_sma_20" in df.columns:
    fig.add_trace(
        go.Scatter(x=df.index, y=df["volume_sma_20"], name="Vol SMA 20",
                   line=dict(color=YELLOW, width=1)),
        row=4, col=1,
    )

fig.update_layout(
    height=900,
    xaxis_rangeslider_visible=False,
    showlegend=True,
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    margin=dict(l=60, r=20, t=40, b=20),
)
fig.update_yaxes(title_text="Price ($)", row=1, col=1)
fig.update_yaxes(title_text="RSI", row=2, col=1, range=[0, 100])
fig.update_yaxes(title_text="MACD", row=3, col=1)
fig.update_yaxes(title_text="Volume", row=4, col=1)

st.plotly_chart(fig, use_container_width=True)

# Support/Resistance table
sr_col1, sr_col2 = st.columns(2)
with sr_col1:
    st.subheader("Support Levels")
    for level in sr_levels.get("support", []):
        dist = ((level["price"] - sr_levels["current_price"]) / sr_levels["current_price"]) * 100
        st.markdown(
            f'<div style="display:flex;justify-content:space-between;padding:4px 0;border-bottom:1px solid #333">'
            f'<span style="color:{GREEN};font-weight:600">${level["price"]:.2f}</span>'
            f'<span style="color:{GREY}">{level["touches"]}x tested</span>'
            f'<span style="color:{GREEN}">{dist:.1f}%</span></div>',
            unsafe_allow_html=True,
        )
with sr_col2:
    st.subheader("Resistance Levels")
    for level in sr_levels.get("resistance", []):
        dist = ((level["price"] - sr_levels["current_price"]) / sr_levels["current_price"]) * 100
        st.markdown(
            f'<div style="display:flex;justify-content:space-between;padding:4px 0;border-bottom:1px solid #333">'
            f'<span style="color:{RED};font-weight:600">${level["price"]:.2f}</span>'
            f'<span style="color:{GREY}">{level["touches"]}x tested</span>'
            f'<span style="color:{RED}">+{dist:.1f}%</span></div>',
            unsafe_allow_html=True,
        )

# TA indicator values with color coding
st.subheader("Current Indicator Values")
latest = df.iloc[-1] if len(df) > 0 else pd.Series()
close_price = latest.get("close", 0)

indicator_cards = []
for label, col, ref in [
    ("SMA 20", "sma_20", close_price), ("SMA 50", "sma_50", close_price),
    ("SMA 200", "sma_200", close_price),
]:
    if col in latest.index and pd.notna(latest[col]):
        val = latest[col]
        above = close_price > val
        color = GREEN if above else RED
        indicator_cards.append(
            f'<div style="text-align:center;padding:8px;border:1px solid {color}33;border-radius:8px;background:{color}11">'
            f'<div style="color:#aaa;font-size:0.75em">{label}</div>'
            f'<div style="font-size:1.2em;font-weight:600">${val:.2f}</div>'
            f'<div style="color:{color};font-size:0.8em">Price {"above" if above else "below"}</div></div>'
        )

rsi_val = latest.get("rsi")
if pd.notna(rsi_val):
    rsi_color = RED if rsi_val > 70 else (GREEN if rsi_val < 30 else YELLOW)
    rsi_label = "Overbought" if rsi_val > 70 else ("Oversold" if rsi_val < 30 else "Neutral")
    indicator_cards.append(
        f'<div style="text-align:center;padding:8px;border:1px solid {rsi_color}33;border-radius:8px;background:{rsi_color}11">'
        f'<div style="color:#aaa;font-size:0.75em">RSI (14)</div>'
        f'<div style="font-size:1.2em;font-weight:600">{rsi_val:.1f}</div>'
        f'<div style="color:{rsi_color};font-size:0.8em">{rsi_label}</div></div>'
    )

macd_val = latest.get(macd_col)
if pd.notna(macd_val):
    macd_color = GREEN if macd_val > 0 else RED
    indicator_cards.append(
        f'<div style="text-align:center;padding:8px;border:1px solid {macd_color}33;border-radius:8px;background:{macd_color}11">'
        f'<div style="color:#aaa;font-size:0.75em">MACD</div>'
        f'<div style="font-size:1.2em;font-weight:600">{macd_val:.2f}</div>'
        f'<div style="color:{macd_color};font-size:0.8em">{"Bullish" if macd_val > 0 else "Bearish"}</div></div>'
    )

atr_val = latest.get("atr")
if pd.notna(atr_val) and close_price > 0:
    atr_pct = (atr_val / close_price) * 100
    atr_color = RED if atr_pct > 3 else (YELLOW if atr_pct > 1.5 else GREEN)
    indicator_cards.append(
        f'<div style="text-align:center;padding:8px;border:1px solid {atr_color}33;border-radius:8px;background:{atr_color}11">'
        f'<div style="color:#aaa;font-size:0.75em">ATR (14)</div>'
        f'<div style="font-size:1.2em;font-weight:600">${atr_val:.2f} ({atr_pct:.1f}%)</div>'
        f'<div style="color:{atr_color};font-size:0.8em">{"High" if atr_pct > 3 else ("Moderate" if atr_pct > 1.5 else "Low")} vol</div></div>'
    )

if indicator_cards:
    cols_per_row = min(len(indicator_cards), 6)
    card_html = '<div style="display:grid;grid-template-columns:' + ' '.join(['1fr'] * cols_per_row) + ';gap:8px">'
    card_html += "".join(indicator_cards) + "</div>"
    st.markdown(card_html, unsafe_allow_html=True)


# --- Money Flow ---
if show_flow:
    st.header("Money Flow & Institutional Activity")

    with st.spinner("Loading flow data..."):
        inst_holders, mf_holders, insider_data, options_flow = load_flow_data(ticker)

    # Ownership breakdown
    flow_col1, flow_col2, flow_col3 = st.columns(3)

    with flow_col1:
        st.subheader("Ownership Breakdown")
        ins_pct = (ownership.get("insiders_pct") or 0) * 100
        inst_pct = (ownership.get("institutions_pct") or 0) * 100
        retail_pct = max(0, 100 - ins_pct - inst_pct)

        fig_pie = go.Figure(data=[go.Pie(
            labels=["Institutional", "Insider", "Retail/Other"],
            values=[inst_pct, ins_pct, retail_pct],
            marker_colors=[BLUE, YELLOW, GREY],
            hole=0.4,
            textinfo="label+percent",
        )])
        fig_pie.update_layout(height=300, margin=dict(l=20, r=20, t=20, b=20), showlegend=False)
        st.plotly_chart(fig_pie, use_container_width=True)

    with flow_col2:
        st.subheader("Insider Activity (6m)")
        summary = insider_data.get("summary")
        if summary is not None and not summary.empty:
            for _, row in summary.iterrows():
                label = str(row.iloc[0])
                val = row.iloc[1]
                if "Purchase" in label and "%" not in label and "Total" not in label:
                    color = GREEN
                elif "Sale" in label and "%" not in label and "Total" not in label:
                    color = RED
                elif "Net" in label and "%" not in label:
                    color = GREEN if (isinstance(val, (int, float)) and val > 0) else RED
                else:
                    color = GREY
                val_str = f"{val:,.0f}" if isinstance(val, (int, float)) else str(val)
                st.markdown(
                    f'<div style="display:flex;justify-content:space-between;padding:4px 0;border-bottom:1px solid #333">'
                    f'<span>{label}</span><span style="color:{color};font-weight:600">{val_str}</span></div>',
                    unsafe_allow_html=True,
                )
        else:
            st.info("No insider activity data.")

    with flow_col3:
        st.subheader("Short Interest")
        si_items = [
            ("Shares Short", short_data.get("shares_short"), None, True),
            ("Prior Month", short_data.get("shares_short_prior_month"), None, True),
            ("% of Float", short_data.get("short_pct_of_float"), True, False),
            ("Short Ratio", short_data.get("short_ratio"), None, False),
        ]
        for label, val, is_pct, is_count in si_items:
            if val is None:
                continue
            if is_pct:
                val_str = f"{val * 100:.2f}%"
                color = RED if val > 0.05 else (YELLOW if val > 0.02 else GREEN)
            elif is_count:
                val_str = f"{val:,.0f}"
                color = GREY
            else:
                val_str = f"{val:.2f}"
                color = RED if val > 5 else (YELLOW if val > 2 else GREEN)
            st.markdown(
                f'<div style="display:flex;justify-content:space-between;padding:4px 0;border-bottom:1px solid #333">'
                f'<span>{label}</span><span style="color:{color};font-weight:600">{val_str}</span></div>',
                unsafe_allow_html=True,
            )

        if short_data.get("short_change_pct") is not None:
            change = short_data["short_change_pct"] * 100
            color = RED if change > 0 else GREEN
            arrow = "^" if change > 0 else "v"
            st.markdown(
                f'<div style="padding:8px 0"><span style="color:{color};font-weight:600">'
                f'{arrow} {abs(change):.1f}% MoM change</span></div>',
                unsafe_allow_html=True,
            )

    # Options Flow
    if options_flow.get("available"):
        st.subheader("Options Flow")
        opt_col1, opt_col2, opt_col3, opt_col4 = st.columns(4)

        pc_vol = options_flow.get("pc_ratio_volume")
        pc_oi = options_flow.get("pc_ratio_oi")
        max_pain = options_flow.get("max_pain")

        if pc_vol is not None:
            pc_color = RED if pc_vol > 1 else (YELLOW if pc_vol > 0.7 else GREEN)
            pc_label = "Bearish" if pc_vol > 1 else ("Neutral" if pc_vol > 0.7 else "Bullish")
            opt_col1.markdown(
                f'<div style="text-align:center;padding:12px;border:1px solid {pc_color}33;border-radius:8px;background:{pc_color}11">'
                f'<div style="color:#aaa;font-size:0.75em">P/C Ratio (Vol)</div>'
                f'<div style="font-size:1.5em;font-weight:700;color:{pc_color}">{pc_vol:.2f}</div>'
                f'<div style="color:{pc_color};font-size:0.8em">{pc_label}</div></div>',
                unsafe_allow_html=True,
            )

        if pc_oi is not None:
            oi_color = RED if pc_oi > 1 else (YELLOW if pc_oi > 0.7 else GREEN)
            oi_label = "Bearish" if pc_oi > 1 else ("Neutral" if pc_oi > 0.7 else "Bullish")
            opt_col2.markdown(
                f'<div style="text-align:center;padding:12px;border:1px solid {oi_color}33;border-radius:8px;background:{oi_color}11">'
                f'<div style="color:#aaa;font-size:0.75em">P/C Ratio (OI)</div>'
                f'<div style="font-size:1.5em;font-weight:700;color:{oi_color}">{pc_oi:.2f}</div>'
                f'<div style="color:{oi_color};font-size:0.8em">{oi_label}</div></div>',
                unsafe_allow_html=True,
            )

        opt_col3.markdown(
            f'<div style="text-align:center;padding:12px;border:1px solid {BLUE}33;border-radius:8px;background:{BLUE}11">'
            f'<div style="color:#aaa;font-size:0.75em">Call / Put Volume</div>'
            f'<div style="font-size:1.2em;font-weight:600">'
            f'<span style="color:{GREEN}">{options_flow["call_volume"]:,}</span> / '
            f'<span style="color:{RED}">{options_flow["put_volume"]:,}</span></div>'
            f'<div style="color:#aaa;font-size:0.8em">{", ".join(options_flow["expirations_analyzed"])}</div></div>',
            unsafe_allow_html=True,
        )

        if max_pain is not None:
            mp_diff = ((max_pain - current_price) / current_price) * 100 if current_price else 0
            mp_color = GREEN if mp_diff > 0 else RED
            opt_col4.markdown(
                f'<div style="text-align:center;padding:12px;border:1px solid {YELLOW}33;border-radius:8px;background:{YELLOW}11">'
                f'<div style="color:#aaa;font-size:0.75em">Max Pain</div>'
                f'<div style="font-size:1.5em;font-weight:700">${max_pain:.0f}</div>'
                f'<div style="color:{mp_color};font-size:0.8em">{mp_diff:+.1f}% from price</div></div>',
                unsafe_allow_html=True,
            )

        # Unusual options activity
        unusual = options_flow.get("unusual_activity", [])
        if unusual:
            st.markdown("**Unusual Options Activity** (volume > 3x open interest)")
            unusual_df = pd.DataFrame(unusual)
            unusual_df.columns = ["Type", "Expiration", "Strike", "Volume", "Open Interest", "Vol/OI", "IV%"]

            def style_unusual(row):
                color = GREEN if row["Type"] == "CALL" else RED
                return [f"color: {color}"] * len(row)

            st.dataframe(
                unusual_df.style.apply(style_unusual, axis=1),
                use_container_width=True,
                hide_index=True,
            )

    # Top Institutional Holders
    if not inst_holders.empty:
        st.subheader("Top Institutional Holders")
        display_inst = inst_holders.head(10).copy()
        if "Value" in display_inst.columns:
            display_inst["Value"] = display_inst["Value"].apply(
                lambda x: f"${x/1e9:.1f}B" if isinstance(x, (int, float)) and x >= 1e9
                else (f"${x/1e6:.0f}M" if isinstance(x, (int, float)) else x)
            )
        if "pctHeld" in display_inst.columns:
            display_inst["pctHeld"] = display_inst["pctHeld"].apply(
                lambda x: f"{x*100:.2f}%" if isinstance(x, (int, float)) else x
            )
        if "pctChange" in display_inst.columns:
            display_inst["pctChange"] = display_inst["pctChange"].apply(
                lambda x: f"{x*100:+.1f}%" if isinstance(x, (int, float)) else x
            )
        st.dataframe(display_inst, use_container_width=True, hide_index=True)

    # Insider transactions
    transactions = insider_data.get("transactions")
    if transactions is not None and not transactions.empty:
        st.subheader("Recent Insider Transactions")
        display_txn = transactions.head(10).copy()
        if "Value" in display_txn.columns:
            display_txn["Value"] = display_txn["Value"].apply(
                lambda x: f"${x:,.0f}" if isinstance(x, (int, float)) and x > 0 else str(x)
            )
        cols_to_show = [c for c in ["Start Date", "Insider", "Position", "Transaction", "Shares", "Value"] if c in display_txn.columns]
        if cols_to_show:
            st.dataframe(display_txn[cols_to_show], use_container_width=True, hide_index=True)


# --- Fundamental Analysis ---
st.header("Fundamental Analysis")

for category, metrics in ratios.items():
    st.subheader(category)
    filtered = {k: v for k, v in metrics.items()}
    num_cols = min(len(filtered), 4)
    if num_cols == 0:
        continue

    cards = []
    for label, val in filtered.items():
        if val is None:
            val_str = "N/A"
            color = GREY
        elif isinstance(val, str) and "%" in val:
            pct_val = float(val.replace("%", ""))
            color = GREEN if pct_val > 0 else RED
            val_str = val
        elif isinstance(val, (int, float)):
            val_str = f"{val:.2f}" if isinstance(val, float) else str(val)
            color = GREY
        else:
            val_str = str(val)
            color = GREY

        cards.append(
            f'<div style="text-align:center;padding:8px;border:1px solid #33333366;border-radius:8px">'
            f'<div style="color:#aaa;font-size:0.72em">{label}</div>'
            f'<div style="font-size:1.1em;font-weight:600;color:{color}">{val_str}</div></div>'
        )

    cols_count = min(len(cards), 4)
    card_html = '<div style="display:grid;grid-template-columns:' + ' '.join(['1fr'] * cols_count) + ';gap:8px;margin-bottom:12px">'
    card_html += "".join(cards) + "</div>"
    st.markdown(card_html, unsafe_allow_html=True)

# Financial Statements
st.header("Financial Statements")
stmt_tab_names = [k for k, v in statements.items() if not v.empty]
if stmt_tab_names:
    tabs = st.tabs(stmt_tab_names)
    for tab, name in zip(tabs, stmt_tab_names):
        with tab:
            display_df = statements[name].copy()
            display_df = display_df.map(
                lambda x: f"${x / 1e9:.2f}B" if isinstance(x, (int, float)) and abs(x) >= 1e9
                else (f"${x / 1e6:.0f}M" if isinstance(x, (int, float)) and abs(x) >= 1e6
                      else x)
            )
            st.dataframe(display_df, use_container_width=True)

# Earnings
st.header("Earnings History")
earnings_df = fundamentals.get("earnings_dates")
if earnings_df is not None and not earnings_df.empty:
    st.dataframe(earnings_df.head(12), use_container_width=True)
else:
    st.info("No earnings data available.")

# Company description
with st.expander("About " + company_name):
    st.write(info.get("longBusinessSummary", "No description available."))
