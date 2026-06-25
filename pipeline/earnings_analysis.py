import pandas as pd
import numpy as np


def compute_growth_trends(fundamentals: dict) -> dict:
    quarterly = fundamentals.get("quarterly_income_stmt")
    annual = fundamentals.get("income_stmt")

    result = {
        "quarterly": _extract_trends(quarterly, is_quarterly=True),
        "annual": _extract_trends(annual, is_quarterly=False),
    }

    return result


KEY_METRICS = [
    ("Total Revenue", "Revenue"),
    ("Cost Of Revenue", "Cost of Revenue"),
    ("Gross Profit", "Gross Profit"),
    ("Operating Expense", "Operating Expenses"),
    ("Operating Income", "Operating Income"),
    ("Net Income", "Net Income"),
    ("Research And Development", "R&D"),
    ("Diluted EPS", "Diluted EPS"),
]


def _extract_trends(stmt, is_quarterly=True):
    if stmt is None or stmt.empty:
        return None

    cols = sorted(stmt.columns, reverse=False)
    if len(cols) < 2:
        return None

    rows = []
    for raw_name, display_name in KEY_METRICS:
        if raw_name not in stmt.index:
            continue

        values = stmt.loc[raw_name, cols]
        latest = values.iloc[-1] if len(values) > 0 else None
        prev = values.iloc[-2] if len(values) > 1 else None

        if pd.isna(latest):
            continue

        yoy_growth = None
        if is_quarterly and len(values) >= 5:
            year_ago = values.iloc[-5]
            if pd.notna(year_ago) and year_ago != 0:
                yoy_growth = (latest - year_ago) / abs(year_ago) * 100
        elif not is_quarterly and pd.notna(prev) and prev != 0:
            yoy_growth = (latest - prev) / abs(prev) * 100

        seq_growth = None
        if pd.notna(prev) and prev != 0:
            seq_growth = (latest - prev) / abs(prev) * 100

        rows.append({
            "metric": display_name,
            "latest": latest,
            "previous": prev,
            "yoy_growth": round(yoy_growth, 1) if yoy_growth is not None else None,
            "seq_growth": round(seq_growth, 1) if seq_growth is not None else None,
        })

    periods = [c.strftime("%Y-%m-%d") if hasattr(c, "strftime") else str(c) for c in cols]
    return {"rows": rows, "periods": periods}


def compute_margin_trends(fundamentals: dict) -> dict:
    quarterly = fundamentals.get("quarterly_income_stmt")
    annual = fundamentals.get("income_stmt")

    return {
        "quarterly": _margin_series(quarterly),
        "annual": _margin_series(annual),
    }


def _margin_series(stmt):
    if stmt is None or stmt.empty:
        return None

    cols = sorted(stmt.columns, reverse=False)
    revenue = stmt.loc["Total Revenue", cols] if "Total Revenue" in stmt.index else None
    if revenue is None or revenue.isna().all():
        return None

    margins = {}
    for raw, label in [
        ("Gross Profit", "Gross Margin"),
        ("Operating Income", "Operating Margin"),
        ("Net Income", "Net Margin"),
        ("Research And Development", "R&D % Revenue"),
    ]:
        if raw in stmt.index:
            vals = stmt.loc[raw, cols]
            pct = (vals / revenue * 100).round(1)
            margins[label] = pct.tolist()

    periods = [c.strftime("%Y-%m-%d") if hasattr(c, "strftime") else str(c) for c in cols]
    return {"margins": margins, "periods": periods}


def compute_revenue_composition(fundamentals: dict) -> dict:
    stmt = fundamentals.get("quarterly_income_stmt")
    if stmt is None or stmt.empty:
        return {"available": False}

    cols = sorted(stmt.columns, reverse=False)
    latest_col = cols[-1]

    revenue = stmt.loc["Total Revenue", latest_col] if "Total Revenue" in stmt.index else None
    if revenue is None or pd.isna(revenue) or revenue == 0:
        return {"available": False}

    components = {}
    for raw, label in [
        ("Cost Of Revenue", "Cost of Revenue"),
        ("Gross Profit", "Gross Profit"),
        ("Research And Development", "R&D Spend"),
        ("Selling General And Administration", "SG&A"),
        ("Operating Income", "Operating Income"),
        ("Net Income", "Net Income"),
    ]:
        if raw in stmt.index:
            val = stmt.loc[raw, latest_col]
            if pd.notna(val):
                components[label] = {
                    "value": float(val),
                    "pct_of_revenue": round(float(val / revenue * 100), 1),
                }

    period = latest_col.strftime("%Y-%m-%d") if hasattr(latest_col, "strftime") else str(latest_col)
    return {
        "available": True,
        "period": period,
        "total_revenue": float(revenue),
        "components": components,
    }
