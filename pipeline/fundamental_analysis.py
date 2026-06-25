import pandas as pd


def compute_ratios(info: dict) -> dict:
    def _get(key, default=None):
        v = info.get(key)
        return v if v is not None else default

    return {
        "Valuation": {
            "P/E (Trailing)": _get("trailingPE"),
            "P/E (Forward)": _get("forwardPE"),
            "PEG Ratio": _get("pegRatio"),
            "P/B Ratio": _get("priceToBook"),
            "P/S Ratio": _get("priceToSalesTrailing12Months"),
            "EV/EBITDA": _get("enterpriseToEbitda"),
            "EV/Revenue": _get("enterpriseToRevenue"),
        },
        "Profitability": {
            "Gross Margin": _fmt_pct(_get("grossMargins")),
            "Operating Margin": _fmt_pct(_get("operatingMargins")),
            "Net Margin": _fmt_pct(_get("profitMargins")),
            "ROE": _fmt_pct(_get("returnOnEquity")),
            "ROA": _fmt_pct(_get("returnOnAssets")),
        },
        "Growth": {
            "Revenue Growth (YoY)": _fmt_pct(_get("revenueGrowth")),
            "Earnings Growth (YoY)": _fmt_pct(_get("earningsGrowth")),
            "EPS (Trailing)": _get("trailingEps"),
            "EPS (Forward)": _get("forwardEps"),
        },
        "Financial Health": {
            "Debt/Equity": _get("debtToEquity"),
            "Current Ratio": _get("currentRatio"),
            "Quick Ratio": _get("quickRatio"),
        },
        "Cash Flow": {
            "Operating Cash Flow": _fmt_large(_get("operatingCashflow")),
            "Free Cash Flow": _fmt_large(_get("freeCashflow")),
        },
        "Dividends": {
            "Dividend Yield": _fmt_pct(_get("dividendYield")),
            "Payout Ratio": _fmt_pct(_get("payoutRatio")),
        },
    }


def get_financial_statements(fundamentals: dict) -> dict:
    return {
        "Income Statement (Annual)": _clean_statement(fundamentals.get("income_stmt")),
        "Income Statement (Quarterly)": _clean_statement(fundamentals.get("quarterly_income_stmt")),
        "Balance Sheet (Annual)": _clean_statement(fundamentals.get("balance_sheet")),
        "Balance Sheet (Quarterly)": _clean_statement(fundamentals.get("quarterly_balance_sheet")),
        "Cash Flow (Annual)": _clean_statement(fundamentals.get("cashflow")),
        "Cash Flow (Quarterly)": _clean_statement(fundamentals.get("quarterly_cashflow")),
    }


def _clean_statement(df) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    df = df.copy()
    if isinstance(df.columns, pd.DatetimeIndex) and df.columns.tz is not None:
        df.columns = df.columns.tz_localize(None)
    df.columns = [c.strftime("%Y-%m-%d") if hasattr(c, "strftime") else str(c) for c in df.columns]
    return df


def _fmt_pct(val):
    if val is None:
        return None
    return f"{val * 100:.2f}%"


def _fmt_large(val):
    if val is None:
        return None
    if abs(val) >= 1e12:
        return f"${val / 1e12:.2f}T"
    if abs(val) >= 1e9:
        return f"${val / 1e9:.2f}B"
    if abs(val) >= 1e6:
        return f"${val / 1e6:.2f}M"
    return f"${val:,.0f}"
