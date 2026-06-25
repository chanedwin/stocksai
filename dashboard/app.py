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
from pipeline.market_context import get_peer_comparison, get_macro_indicators, get_analyst_data, get_earnings_impact
from pipeline.earnings_analysis import compute_growth_trends, compute_margin_trends, compute_revenue_composition
from pipeline.signal_aggregator import aggregate_all_signals

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
show_market = st.sidebar.checkbox("Show Market Context", value=True)


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


@st.cache_data(ttl=900)
def load_market_context(t, p):
    peers = get_peer_comparison(t, p)
    macro = get_macro_indicators("2y")
    analyst = get_analyst_data(t)
    return peers, macro, analyst


@st.cache_data(ttl=900)
def load_signal_analysis(t):
    price = fetch_price_data(t, period="5y")
    fund = fetch_fundamental_data(t)
    return aggregate_all_signals(price, fund["info"], fund, t)


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


# --- Signal Overview ---
st.header("Signal Overview")

with st.spinner("Computing signals across all timeframes..."):
    sig_analysis = load_signal_analysis(ticker)

composite = sig_analysis["composite_score"]
verdict = sig_analysis["verdict"]
cat_scores = sig_analysis["category_scores"]
tf_scores = sig_analysis["timeframe_scores"]
all_sigs = sig_analysis["all_signals"]

# Composite gauge + category breakdown
gauge_col, cat_col = st.columns([1, 2])

with gauge_col:
    verdict_color = GREEN if composite > 15 else (RED if composite < -15 else YELLOW)
    gauge_fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=composite,
        number={"suffix": "", "font": {"size": 48}},
        title={"text": verdict, "font": {"size": 20, "color": verdict_color}},
        gauge={
            "axis": {"range": [-100, 100], "tickvals": [-100, -50, 0, 50, 100]},
            "bar": {"color": verdict_color},
            "steps": [
                {"range": [-100, -40], "color": f"{RED}22"},
                {"range": [-40, -15], "color": f"{RED}11"},
                {"range": [-15, 15], "color": f"{YELLOW}11"},
                {"range": [15, 40], "color": f"{GREEN}11"},
                {"range": [40, 100], "color": f"{GREEN}22"},
            ],
            "threshold": {"line": {"color": "white", "width": 2}, "thickness": 0.8, "value": composite},
        },
    ))
    gauge_fig.update_layout(height=250, margin=dict(l=30, r=30, t=60, b=20))
    st.plotly_chart(gauge_fig, use_container_width=True)

    st.markdown(
        f'<div style="text-align:center;color:#aaa;font-size:0.85em">'
        f'Bullish weight: <span style="color:{GREEN}">{sig_analysis["total_bullish"]}</span> | '
        f'Bearish weight: <span style="color:{RED}">{sig_analysis["total_bearish"]}</span></div>',
        unsafe_allow_html=True,
    )

with cat_col:
    # Category score bars
    cat_display = {
        "technical": "Technical",
        "fundamental": "Fundamental",
        "flow": "Money Flow",
        "analyst": "Analyst",
    }
    cat_items = [(cat_display.get(k, k.title()), v) for k, v in cat_scores.items() if k in cat_display]

    st.markdown("**Signal Breakdown by Category**")
    for label, data in cat_items:
        score = data["score"]
        bar_color = GREEN if score > 15 else (RED if score < -15 else YELLOW)
        bar_label = "Bullish" if score > 15 else ("Bearish" if score < -15 else "Neutral")
        bar_width = abs(score)

        left_bar = ""
        right_bar = ""
        if score < 0:
            left_bar = f'<div style="height:22px;background:{RED};border-radius:4px 0 0 4px;width:{bar_width}%"></div>'
        if score >= 0:
            right_bar = f'<div style="height:22px;background:{GREEN};border-radius:0 4px 4px 0;width:{bar_width}%"></div>'

        st.markdown(
            f'<div style="display:flex;align-items:center;padding:6px 0;border-bottom:1px solid #33333366">'
            f'<span style="width:110px;font-weight:600">{label}</span>'
            f'<div style="flex:1;display:flex;align-items:center">'
            f'<div style="width:50%;display:flex;justify-content:flex-end">{left_bar}</div>'
            f'<div style="width:2px;height:28px;background:#666;margin:0 2px"></div>'
            f'<div style="width:50%">{right_bar}</div></div>'
            f'<span style="width:80px;text-align:right;color:{bar_color};font-weight:600;font-size:0.9em">{bar_label}</span>'
            f'<span style="width:50px;text-align:right;color:#aaa;font-size:0.8em">{data["signal_count"]} sig</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # Timeframe scores
    st.markdown("")
    st.markdown("**Timeframe Analysis**")
    tf_display = {"daily": "Daily", "weekly": "Weekly", "monthly": "Monthly"}
    tf_html = '<div style="display:flex;gap:12px">'
    for tf_key in ["daily", "weekly", "monthly"]:
        if tf_key not in tf_scores:
            continue
        data = tf_scores[tf_key]
        score = data["score"]
        tf_color = GREEN if score > 15 else (RED if score < -15 else YELLOW)
        tf_label = "Bullish" if score > 15 else ("Bearish" if score < -15 else "Neutral")
        tf_html += (
            f'<div style="flex:1;text-align:center;padding:10px;border:1px solid {tf_color}33;border-radius:8px;background:{tf_color}11">'
            f'<div style="color:#aaa;font-size:0.72em">{tf_display.get(tf_key, tf_key)}</div>'
            f'<div style="font-size:1.5em;font-weight:700;color:{tf_color}">{score:+d}</div>'
            f'<div style="font-size:0.8em;color:{tf_color}">{tf_label}</div>'
            f'<div style="font-size:0.7em;color:#aaa;margin-top:4px">'
            f'<span style="color:{GREEN}">{data["bullish_count"]}B</span> / '
            f'<span style="color:{RED}">{data["bearish_count"]}Be</span> / '
            f'<span style="color:{YELLOW}">{data["neutral_count"]}N</span></div>'
            f'</div>'
        )
    tf_html += '</div>'
    st.markdown(tf_html, unsafe_allow_html=True)

# Signal list grouped by category
st.subheader("All Active Signals")

sig_tabs = st.tabs(["All", "Technical", "Fundamental", "Money Flow", "Analyst"])

with sig_tabs[0]:
    sorted_sigs = sorted(all_sigs, key=lambda x: (
        {"strong": 0, "moderate": 1, "weak": 2}.get(x["strength"], 3),
        {"bearish": 0, "bullish": 1, "neutral": 2}.get(x["type"], 3),
    ))
    sig_html = '<div style="display:flex;flex-wrap:wrap;gap:6px">'
    for s in sorted_sigs:
        tf_tag = f'[{s.get("timeframe", "")}]' if s.get("timeframe") else ""
        strength_icon = {"strong": "***", "moderate": "**", "weak": "*"}.get(s["strength"], "")
        sig_html += signal_badge(s["type"], f'{strength_icon} {tf_tag} {s["signal"]}: {s["description"]}')
    sig_html += '</div>'
    st.markdown(sig_html, unsafe_allow_html=True)

cat_tab_map = {"Technical": "technical", "Fundamental": "fundamental", "Money Flow": "flow", "Analyst": "analyst"}
for tab, tab_label in zip(sig_tabs[1:], ["Technical", "Fundamental", "Money Flow", "Analyst"]):
    with tab:
        cat_key = cat_tab_map[tab_label]
        cat_sigs = [s for s in all_sigs if s.get("category") == cat_key]
        if cat_sigs:
            for s in sorted(cat_sigs, key=lambda x: {"strong": 0, "moderate": 1, "weak": 2}.get(x["strength"], 3)):
                tf_tag = f'[{s.get("timeframe", "")}] ' if s.get("timeframe") else ""
                st.markdown(
                    f'<div style="padding:6px 0;border-bottom:1px solid #33333322;display:flex;align-items:center;gap:8px">'
                    f'{signal_badge(s["type"], s["signal"])}'
                    f'<span style="color:#aaa;font-size:0.8em">{tf_tag}</span>'
                    f'<span style="font-size:0.9em">{s["description"]}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
        else:
            st.info(f"No {tab_label.lower()} signals detected.")

# Yearly performance
yearly_perf = sig_analysis["yearly_performance"]
if yearly_perf:
    st.subheader("Yearly Performance")
    yp_cols = min(len(yearly_perf), 8)
    year_html = f'<div style="display:grid;grid-template-columns:repeat({yp_cols}, 1fr);gap:6px">'
    for y in yearly_perf[-8:]:
        y_color = GREEN if y["return_pct"] > 0 else RED
        year_html += (
            f'<div style="text-align:center;padding:8px;border:1px solid {y_color}33;border-radius:8px;background:{y_color}11">'
            f'<div style="font-weight:700">{y["year"]}</div>'
            f'<div style="font-size:1.3em;font-weight:600;color:{y_color}">{y["return_pct"]:+.1f}%</div>'
            f'<div style="font-size:0.7em;color:#aaa">Range: {y["range_pct"]:.0f}%</div>'
            f'</div>'
        )
    year_html += '</div>'
    st.markdown(year_html, unsafe_allow_html=True)

# Seasonal Analysis
seasonal = sig_analysis.get("seasonal", {})
if seasonal.get("available"):
    st.subheader("Seasonal Analysis")

    season_tab1, season_tab2, season_tab3 = st.tabs(["Monthly", "Day of Week", "Quarterly"])

    with season_tab1:
        monthly_data = seasonal["monthly"]
        months = [m["month"] for m in monthly_data]
        avg_returns = [m["avg_monthly_return"] for m in monthly_data]
        win_rates = [m["win_rate"] for m in monthly_data]
        bar_colors = [GREEN if r > 0 else RED for r in avg_returns]

        fig_month = make_subplots(specs=[[{"secondary_y": True}]])
        fig_month.add_trace(
            go.Bar(x=months, y=avg_returns, name="Avg Monthly Return (%)",
                   marker_color=bar_colors,
                   text=[f"{r:+.1f}%" for r in avg_returns], textposition="outside"),
            secondary_y=False,
        )
        fig_month.add_trace(
            go.Scatter(x=months, y=win_rates, name="Win Rate (%)",
                       line=dict(color=BLUE, width=2), mode="lines+markers"),
            secondary_y=True,
        )
        fig_month.update_layout(
            height=350, margin=dict(l=60, r=60, t=20, b=20),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        fig_month.update_yaxes(title_text="Avg Return (%)", secondary_y=False)
        fig_month.update_yaxes(title_text="Win Rate (%)", secondary_y=True, range=[0, 100])
        fig_month.add_hline(y=0, line_color=GREY, opacity=0.3, secondary_y=False)
        st.plotly_chart(fig_month, use_container_width=True)

        current_month = pd.Timestamp.now().month
        current_month_data = next((m for m in monthly_data if m["month_num"] == current_month), None)
        if current_month_data:
            cm_color = GREEN if current_month_data["avg_monthly_return"] > 0 else RED
            st.markdown(
                f'<div style="padding:10px;border:1px solid {cm_color}33;border-radius:8px;background:{cm_color}11;text-align:center">'
                f'<span style="font-weight:600">Current month ({current_month_data["month"]}): </span>'
                f'<span style="color:{cm_color};font-weight:700">avg {current_month_data["avg_monthly_return"]:+.2f}%</span>'
                f' | Win rate: {current_month_data["win_rate"]:.0f}%'
                f' | Based on {current_month_data["years_analyzed"]} years</div>',
                unsafe_allow_html=True,
            )

    with season_tab2:
        dow_data = seasonal["day_of_week"]
        days = [d["day"] for d in dow_data]
        dow_returns = [d["avg_return"] for d in dow_data]
        dow_wins = [d["win_rate"] for d in dow_data]
        dow_colors = [GREEN if r > 0 else RED for r in dow_returns]

        fig_dow = make_subplots(specs=[[{"secondary_y": True}]])
        fig_dow.add_trace(
            go.Bar(x=days, y=dow_returns, name="Avg Daily Return (%)",
                   marker_color=dow_colors,
                   text=[f"{r:+.3f}%" for r in dow_returns], textposition="outside"),
            secondary_y=False,
        )
        fig_dow.add_trace(
            go.Scatter(x=days, y=dow_wins, name="Win Rate (%)",
                       line=dict(color=BLUE, width=2), mode="lines+markers"),
            secondary_y=True,
        )
        fig_dow.update_layout(
            height=300, margin=dict(l=60, r=60, t=20, b=20),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        fig_dow.update_yaxes(title_text="Avg Return (%)", secondary_y=False)
        fig_dow.update_yaxes(title_text="Win Rate (%)", secondary_y=True, range=[40, 65])
        fig_dow.add_hline(y=0, line_color=GREY, opacity=0.3, secondary_y=False)
        st.plotly_chart(fig_dow, use_container_width=True)

    with season_tab3:
        q_data = seasonal["quarterly"]
        quarters = [q["quarter"] for q in q_data]
        q_returns = [q["avg_return"] for q in q_data]
        q_wins = [q["win_rate"] for q in q_data]
        q_colors = [GREEN if r > 0 else RED for r in q_returns]

        fig_q = make_subplots(specs=[[{"secondary_y": True}]])
        fig_q.add_trace(
            go.Bar(x=quarters, y=q_returns, name="Avg Quarterly Return (%)",
                   marker_color=q_colors,
                   text=[f"{r:+.1f}%" for r in q_returns], textposition="outside"),
            secondary_y=False,
        )
        fig_q.add_trace(
            go.Scatter(x=quarters, y=q_wins, name="Win Rate (%)",
                       line=dict(color=BLUE, width=2), mode="lines+markers"),
            secondary_y=True,
        )
        fig_q.update_layout(
            height=300, margin=dict(l=60, r=60, t=20, b=20),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        fig_q.update_yaxes(title_text="Avg Return (%)", secondary_y=False)
        fig_q.update_yaxes(title_text="Win Rate (%)", secondary_y=True, range=[0, 100])
        fig_q.add_hline(y=0, line_color=GREY, opacity=0.3, secondary_y=False)
        st.plotly_chart(fig_q, use_container_width=True)

st.markdown("---")
st.caption("Analysis is for informational and educational purposes only, not financial advice.")


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


# --- Market Context ---
if show_market:
    st.header("Market Context & Drivers")

    with st.spinner("Loading market context..."):
        peers, macro, analyst = load_market_context(ticker, period)

    # Analyst Consensus
    st.subheader("Analyst Consensus")
    targets = analyst.get("price_targets")
    recs = analyst.get("recommendations")
    eps_est = analyst.get("eps_estimate")
    rev_est = analyst.get("revenue_estimate")

    if targets:
        an_col1, an_col2 = st.columns([1, 2])
        with an_col1:
            t_current = targets.get("current", current_price)
            t_low = targets.get("low", 0)
            t_mean = targets.get("mean", 0)
            t_median = targets.get("median", 0)
            t_high = targets.get("high", 0)

            upside = ((t_mean - t_current) / t_current * 100) if t_current else 0
            upside_color = GREEN if upside > 0 else RED

            st.markdown(
                f'<div style="text-align:center;padding:16px;border:1px solid {upside_color}33;border-radius:8px;background:{upside_color}11">'
                f'<div style="color:#aaa;font-size:0.75em">Mean Price Target</div>'
                f'<div style="font-size:2em;font-weight:700">${t_mean:.0f}</div>'
                f'<div style="color:{upside_color};font-size:1em;font-weight:600">{upside:+.1f}% upside</div>'
                f'<div style="color:#aaa;font-size:0.8em;margin-top:8px">Low ${t_low:.0f} | Median ${t_median:.0f} | High ${t_high:.0f}</div></div>',
                unsafe_allow_html=True,
            )

        with an_col2:
            if recs is not None and not recs.empty:
                latest_rec = recs.iloc[0]
                rec_data = {
                    "Strong Buy": int(latest_rec.get("strongBuy", 0)),
                    "Buy": int(latest_rec.get("buy", 0)),
                    "Hold": int(latest_rec.get("hold", 0)),
                    "Sell": int(latest_rec.get("sell", 0)),
                    "Strong Sell": int(latest_rec.get("strongSell", 0)),
                }
                rec_colors = [GREEN, "#66bb6a", YELLOW, "#ef9a9a", RED]

                fig_rec = go.Figure(data=[go.Bar(
                    x=list(rec_data.keys()),
                    y=list(rec_data.values()),
                    marker_color=rec_colors,
                    text=list(rec_data.values()),
                    textposition="auto",
                )])
                fig_rec.update_layout(
                    height=250, margin=dict(l=20, r=20, t=30, b=20),
                    title="Analyst Recommendations",
                    yaxis_title="Count",
                )
                st.plotly_chart(fig_rec, use_container_width=True)

    # EPS & Revenue estimates
    if eps_est is not None and not eps_est.empty:
        est_col1, est_col2 = st.columns(2)
        with est_col1:
            st.markdown("**EPS Estimates**")
            display_eps = eps_est[["avg", "low", "high", "yearAgoEps", "growth"]].copy()
            display_eps["growth"] = display_eps["growth"].apply(
                lambda x: f"{x*100:+.1f}%" if pd.notna(x) else "N/A"
            )
            display_eps.columns = ["Avg", "Low", "High", "Year Ago", "Growth"]
            st.dataframe(display_eps, use_container_width=True)

        with est_col2:
            if rev_est is not None and not rev_est.empty:
                st.markdown("**Revenue Estimates**")
                display_rev = rev_est[["avg", "low", "high", "growth"]].copy()
                display_rev["avg"] = display_rev["avg"].apply(lambda x: f"${x/1e9:.1f}B" if pd.notna(x) else "N/A")
                display_rev["low"] = display_rev["low"].apply(lambda x: f"${x/1e9:.1f}B" if pd.notna(x) else "N/A")
                display_rev["high"] = display_rev["high"].apply(lambda x: f"${x/1e9:.1f}B" if pd.notna(x) else "N/A")
                display_rev["growth"] = display_rev["growth"].apply(
                    lambda x: f"{x*100:+.1f}%" if pd.notna(x) else "N/A"
                )
                display_rev.columns = ["Avg", "Low", "High", "Growth"]
                st.dataframe(display_rev, use_container_width=True)

    # Peer Comparison
    if peers.get("available"):
        st.subheader("Peer Comparison")

        peer_col1, peer_col2 = st.columns([2, 1])

        with peer_col1:
            cum_ret = peers["cumulative_returns"]
            names = peers["names"]
            fig_peers = go.Figure()

            for col in cum_ret.columns:
                label = names.get(col, col)
                is_main = col == ticker
                color_map = {
                    ticker: BLUE, "SPY": GREY, "XLK": "#ab47bc",
                    "AAPL": "#78909c", "MSFT": "#4caf50", "META": "#2196f3",
                    "AMZN": "#ff9800", "NVDA": "#66bb6a",
                }
                fig_peers.add_trace(go.Scatter(
                    x=cum_ret.index, y=cum_ret[col] * 100,
                    name=label,
                    line=dict(
                        color=color_map.get(col, GREY),
                        width=3 if is_main else 1.5,
                        dash=None if is_main else ("dash" if col in ("SPY", "XLK") else None),
                    ),
                    opacity=1.0 if is_main else 0.7,
                ))

            fig_peers.update_layout(
                height=400,
                title="Cumulative Returns",
                yaxis_title="Return (%)",
                hovermode="x unified",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                margin=dict(l=60, r=20, t=40, b=20),
            )
            fig_peers.add_hline(y=0, line_dash="dot", line_color=GREY, opacity=0.3)
            st.plotly_chart(fig_peers, use_container_width=True)

        with peer_col2:
            st.markdown("**Correlation with " + ticker + "**")
            corr_data = peers["correlation"]
            names = peers["names"]
            for sym, corr_val in sorted(corr_data.items(), key=lambda x: abs(x[1]), reverse=True):
                label = names.get(sym, sym)
                if corr_val > 0.5:
                    color = GREEN
                elif corr_val > 0.3:
                    color = YELLOW
                elif corr_val < 0:
                    color = RED
                else:
                    color = GREY
                bar_width = abs(corr_val) * 100
                st.markdown(
                    f'<div style="display:flex;align-items:center;padding:4px 0;border-bottom:1px solid #333">'
                    f'<span style="width:80px">{label}</span>'
                    f'<div style="flex:1;background:#33333366;border-radius:4px;height:18px;margin:0 8px">'
                    f'<div style="width:{bar_width}%;background:{color};height:100%;border-radius:4px"></div></div>'
                    f'<span style="color:{color};font-weight:600;width:50px;text-align:right">{corr_val:.2f}</span></div>',
                    unsafe_allow_html=True,
                )

            st.markdown("")
            st.markdown("**Period Returns**")
            ret_data = peers["period_returns"]
            for sym, ret_val in sorted(ret_data.items(), key=lambda x: x[1], reverse=True):
                label = names.get(sym, sym)
                color = GREEN if ret_val > 0 else RED
                is_main = sym == ticker
                weight = "700" if is_main else "400"
                st.markdown(
                    f'<div style="display:flex;justify-content:space-between;padding:3px 0;font-weight:{weight}">'
                    f'<span>{">> " if is_main else ""}{label}</span>'
                    f'<span style="color:{color}">{ret_val*100:+.1f}%</span></div>',
                    unsafe_allow_html=True,
                )

        # Relative strength vs SPY
        rel = peers.get("relative_strength_vs_spy")
        if rel is not None and not rel.empty:
            fig_rel = go.Figure()
            fig_rel.add_trace(go.Scatter(
                x=rel.index, y=rel * 100,
                fill="tozeroy",
                fillcolor=f"rgba(38,166,154,0.15)",
                line=dict(color=BLUE, width=2),
                name=f"{ticker} vs SPY",
            ))
            fig_rel.add_hline(y=0, line_dash="dash", line_color=GREY, opacity=0.5)
            fig_rel.update_layout(
                height=250, title=f"Relative Strength: {ticker} vs S&P 500",
                yaxis_title="Excess Return (%)",
                margin=dict(l=60, r=20, t=40, b=20),
            )
            st.plotly_chart(fig_rel, use_container_width=True)

    # Macro Indicators
    if macro.get("available"):
        st.subheader("Macro Indicators")
        macro_data = macro["data"]

        fig_macro = make_subplots(
            rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.08,
            subplot_titles=("10Y Treasury Yield (%)", "VIX (Fear Index)"),
            row_heights=[0.5, 0.5],
        )

        if "10Y Treasury" in macro_data.columns:
            fig_macro.add_trace(
                go.Scatter(x=macro_data.index, y=macro_data["10Y Treasury"],
                           name="10Y Treasury", line=dict(color=YELLOW, width=1.5)),
                row=1, col=1,
            )

        if "VIX" in macro_data.columns:
            vix = macro_data["VIX"]
            fig_macro.add_trace(
                go.Scatter(x=vix.index, y=vix, name="VIX",
                           line=dict(color="#ab47bc", width=1.5)),
                row=2, col=1,
            )
            fig_macro.add_hline(y=20, line_dash="dash", line_color=YELLOW, opacity=0.5, row=2, col=1,
                               annotation_text="Normal", annotation_font_color=YELLOW)
            fig_macro.add_hline(y=30, line_dash="dash", line_color=RED, opacity=0.5, row=2, col=1,
                               annotation_text="Fear", annotation_font_color=RED)

        fig_macro.update_layout(
            height=450, showlegend=False,
            margin=dict(l=60, r=20, t=40, b=20),
        )
        st.plotly_chart(fig_macro, use_container_width=True)

    # Earnings Impact
    st.subheader("Earnings Impact Analysis")
    earnings_impact = get_earnings_impact(ticker, price_df)
    if not earnings_impact.empty:
        ei_col1, ei_col2 = st.columns([2, 1])

        with ei_col1:
            fig_ei = go.Figure()
            colors = [GREEN if s and s > 0 else (RED if s and s < 0 else GREY)
                      for s in earnings_impact["surprise_pct"]]
            fig_ei.add_trace(go.Bar(
                x=earnings_impact["date"],
                y=earnings_impact["day_return_pct"],
                marker_color=colors,
                name="Day Return",
                text=[f"{r:+.1f}%" for r in earnings_impact["day_return_pct"]],
                textposition="outside",
            ))
            fig_ei.update_layout(
                height=300, title="Stock Price Move on Earnings Day",
                yaxis_title="Return (%)",
                margin=dict(l=60, r=20, t=40, b=20),
            )
            fig_ei.add_hline(y=0, line_color=GREY, opacity=0.3)
            st.plotly_chart(fig_ei, use_container_width=True)

        with ei_col2:
            st.markdown("**Earnings History**")
            for _, row in earnings_impact.iterrows():
                surprise = row["surprise_pct"]
                ret = row["day_return_pct"]
                if surprise is not None:
                    s_color = GREEN if surprise > 0 else RED
                    s_str = f'{surprise:+.1f}% {"beat" if surprise > 0 else "miss"}'
                else:
                    s_color = GREY
                    s_str = "N/A"
                r_color = GREEN if ret > 0 else RED
                eps_str = f"${row['eps_actual']:.2f}" if row["eps_actual"] is not None else "N/A"
                st.markdown(
                    f'<div style="padding:6px 0;border-bottom:1px solid #333">'
                    f'<div style="font-weight:600">{row["date"]}</div>'
                    f'<div style="display:flex;justify-content:space-between">'
                    f'<span>EPS: {eps_str}</span>'
                    f'<span style="color:{s_color}">{s_str}</span>'
                    f'<span style="color:{r_color}">{ret:+.1f}%</span></div></div>',
                    unsafe_allow_html=True,
                )
    else:
        st.info("No earnings impact data available for this period.")


# --- Earnings Breakdown ---
st.header("Earnings & Revenue Breakdown")

growth_trends = compute_growth_trends(fundamentals)
margin_trends = compute_margin_trends(fundamentals)
rev_composition = compute_revenue_composition(fundamentals)

# Revenue composition waterfall
if rev_composition.get("available"):
    st.subheader(f"Where the Money Goes ({rev_composition['period']})")
    total_rev = rev_composition["total_revenue"]
    comp = rev_composition["components"]

    waterfall_items = [
        ("Revenue", total_rev, BLUE),
        ("Cost of Revenue", -comp.get("Cost of Revenue", {}).get("value", 0), RED),
        ("Gross Profit", comp.get("Gross Profit", {}).get("value", 0), GREEN),
        ("R&D", -comp.get("R&D Spend", {}).get("value", 0), YELLOW),
        ("SG&A", -comp.get("SG&A", {}).get("value", 0), YELLOW),
        ("Operating Income", comp.get("Operating Income", {}).get("value", 0), GREEN),
    ]

    wf_labels = [w[0] for w in waterfall_items]
    wf_values = [w[1] for w in waterfall_items]
    wf_colors = [w[2] for w in waterfall_items]
    wf_pcts = [abs(v) / total_rev * 100 for v in wf_values]

    fig_wf = go.Figure(go.Bar(
        x=wf_labels,
        y=[abs(v) / 1e9 for v in wf_values],
        marker_color=wf_colors,
        text=[f"${abs(v)/1e9:.1f}B\n({p:.0f}%)" for v, p in zip(wf_values, wf_pcts)],
        textposition="outside",
    ))
    fig_wf.update_layout(
        height=350,
        yaxis_title="$ Billions",
        margin=dict(l=60, r=20, t=20, b=20),
    )
    st.plotly_chart(fig_wf, use_container_width=True)

# Growth trends table
qt = growth_trends.get("quarterly")
if qt and qt.get("rows"):
    st.subheader("Quarterly Growth")

    growth_cards = []
    for row in qt["rows"]:
        yoy = row["yoy_growth"]
        qoq = row["seq_growth"]
        latest = row["latest"]

        if abs(latest) >= 1e9:
            val_str = f"${latest/1e9:.1f}B"
        elif abs(latest) >= 1e6:
            val_str = f"${latest/1e6:.0f}M"
        elif row["metric"] == "Diluted EPS":
            val_str = f"${latest:.2f}"
        else:
            val_str = f"${latest:,.0f}"

        yoy_color = GREEN if yoy and yoy > 0 else (RED if yoy and yoy < 0 else GREY)
        qoq_color = GREEN if qoq and qoq > 0 else (RED if qoq and qoq < 0 else GREY)
        yoy_str = f"{yoy:+.1f}%" if yoy is not None else "N/A"
        qoq_str = f"{qoq:+.1f}%" if qoq is not None else "N/A"

        growth_cards.append(
            f'<div style="padding:10px;border:1px solid #33333366;border-radius:8px">'
            f'<div style="color:#aaa;font-size:0.72em">{row["metric"]}</div>'
            f'<div style="font-size:1.2em;font-weight:600">{val_str}</div>'
            f'<div style="display:flex;gap:12px;margin-top:4px">'
            f'<span style="color:{yoy_color};font-size:0.85em">YoY {yoy_str}</span>'
            f'<span style="color:{qoq_color};font-size:0.85em">QoQ {qoq_str}</span>'
            f'</div></div>'
        )

    cols_count = min(len(growth_cards), 4)
    card_html = '<div style="display:grid;grid-template-columns:' + ' '.join(['1fr'] * cols_count) + ';gap:8px">'
    card_html += "".join(growth_cards) + "</div>"
    st.markdown(card_html, unsafe_allow_html=True)

# Margin trends chart
qm = margin_trends.get("quarterly")
if qm and qm.get("margins"):
    st.subheader("Margin Trends")

    fig_margins = go.Figure()
    margin_colors = {
        "Gross Margin": GREEN,
        "Operating Margin": BLUE,
        "Net Margin": YELLOW,
        "R&D % Revenue": "#ab47bc",
    }

    for name, vals in qm["margins"].items():
        fig_margins.add_trace(go.Scatter(
            x=qm["periods"],
            y=vals,
            name=name,
            line=dict(color=margin_colors.get(name, GREY), width=2),
            mode="lines+markers",
        ))

    fig_margins.update_layout(
        height=350,
        yaxis_title="% of Revenue",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=60, r=20, t=20, b=20),
    )
    st.plotly_chart(fig_margins, use_container_width=True)


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
