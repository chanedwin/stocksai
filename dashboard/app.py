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

st.set_page_config(page_title="Stock Analysis", layout="wide")


# --- Sidebar ---
st.sidebar.title("Stock Analysis")
ticker = st.sidebar.text_input("Ticker", value="GOOGL").upper()
period = st.sidebar.selectbox("Period", ["6mo", "1y", "2y", "5y", "10y", "max"], index=2)
ta_overlays = st.sidebar.multiselect(
    "Chart Overlays",
    ["SMA 20", "SMA 50", "SMA 200", "EMA 12", "EMA 26", "Bollinger Bands"],
    default=["SMA 50", "SMA 200"],
)


@st.cache_data(ttl=900)
def load_data(t, p):
    price = fetch_price_data(t, period=p)
    fund = fetch_fundamental_data(t)
    return price, fund


with st.spinner("Fetching data..."):
    price_df, fundamentals = load_data(ticker, period)

if price_df.empty:
    st.error(f"No data found for {ticker}.")
    st.stop()

df = compute_indicators(price_df)
info = fundamentals["info"]
ratios = compute_ratios(info)
statements = get_financial_statements(fundamentals)


# --- Header ---
company_name = info.get("longName", ticker)
current_price = info.get("currentPrice") or (df["close"].iloc[-1] if len(df) > 0 else None)
prev_close = info.get("previousClose")
market_cap = info.get("marketCap")
sector = info.get("sector", "N/A")
industry = info.get("industry", "N/A")

st.title(f"{company_name} ({ticker})")
st.caption(f"{sector} | {industry}")

# Key metrics row
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
if pe:
    cols[3].metric("P/E", f"{pe:.1f}")
eps = info.get("trailingEps")
if eps:
    cols[4].metric("EPS", f"${eps:.2f}")
div_yield = info.get("dividendYield")
if div_yield:
    cols[5].metric("Div Yield", f"{div_yield * 100:.2f}%")
else:
    cols[5].metric("Div Yield", "N/A")


# --- Technical Analysis ---
st.header("Technical Analysis")

# Price chart with overlays
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
        x=df.index,
        open=df["open"],
        high=df["high"],
        low=df["low"],
        close=df["close"],
        name="Price",
        increasing_line_color="#26a69a",
        decreasing_line_color="#ef5350",
    ),
    row=1, col=1,
)

# Overlays
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

# RSI
if "rsi" in df.columns:
    fig.add_trace(
        go.Scatter(x=df.index, y=df["rsi"], name="RSI", line=dict(color="#7e57c2", width=1.5)),
        row=2, col=1,
    )
    fig.add_hline(y=70, line_dash="dash", line_color="red", opacity=0.5, row=2, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="green", opacity=0.5, row=2, col=1)

# MACD
macd_col = f"MACD_12_26_9"
signal_col = f"MACDs_12_26_9"
hist_col = f"MACDh_12_26_9"

if macd_col in df.columns:
    fig.add_trace(
        go.Scatter(x=df.index, y=df[macd_col], name="MACD", line=dict(color="#2196f3", width=1.5)),
        row=3, col=1,
    )
if signal_col in df.columns:
    fig.add_trace(
        go.Scatter(x=df.index, y=df[signal_col], name="Signal", line=dict(color="#ff9800", width=1.5)),
        row=3, col=1,
    )
if hist_col in df.columns:
    colors = ["#26a69a" if v >= 0 else "#ef5350" for v in df[hist_col].fillna(0)]
    fig.add_trace(
        go.Bar(x=df.index, y=df[hist_col], name="Histogram", marker_color=colors),
        row=3, col=1,
    )

# Volume
vol_colors = ["#26a69a" if c >= o else "#ef5350" for c, o in zip(df["close"], df["open"])]
fig.add_trace(
    go.Bar(x=df.index, y=df["volume"], name="Volume", marker_color=vol_colors, opacity=0.7),
    row=4, col=1,
)
if "volume_sma_20" in df.columns:
    fig.add_trace(
        go.Scatter(x=df.index, y=df["volume_sma_20"], name="Vol SMA 20",
                   line=dict(color="#ff9800", width=1)),
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

# TA Summary table
st.subheader("Current Indicator Values")
latest = df.iloc[-1] if len(df) > 0 else pd.Series()
ta_summary = {}
for label, col in [
    ("SMA 20", "sma_20"), ("SMA 50", "sma_50"), ("SMA 200", "sma_200"),
    ("EMA 12", "ema_12"), ("EMA 26", "ema_26"),
    ("RSI (14)", "rsi"), ("ATR (14)", "atr"),
    ("MACD", macd_col), ("Signal", signal_col),
]:
    if col in latest.index and pd.notna(latest[col]):
        ta_summary[label] = f"{latest[col]:.2f}"

if ta_summary:
    summary_cols = st.columns(len(ta_summary))
    for i, (label, val) in enumerate(ta_summary.items()):
        summary_cols[i].metric(label, val)


# --- Fundamental Analysis ---
st.header("Fundamental Analysis")

for category, metrics in ratios.items():
    st.subheader(category)
    filtered = {k: (v if v is not None else "N/A") for k, v in metrics.items()}
    num_cols = min(len(filtered), 4)
    if num_cols == 0:
        continue
    cols = st.columns(num_cols)
    for i, (label, val) in enumerate(filtered.items()):
        cols[i % num_cols].metric(label, str(val))

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
