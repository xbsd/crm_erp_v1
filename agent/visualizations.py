"""Visualization helpers for the demo: bar charts, line charts, tables.

Uses Plotly so we can render to PNG (for slides) and HTML (for Streamlit).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import plotly.express as px
import plotly.graph_objects as go


def _save_png_html(fig: go.Figure, out_basename: Path) -> tuple[Path, Path]:
    png_path = out_basename.with_suffix(".png")
    html_path = out_basename.with_suffix(".html")
    try:
        fig.write_image(str(png_path), width=1280, height=720, scale=2)
    except Exception:
        # Falls back to HTML only if kaleido isn't installed
        png_path = None  # type: ignore
    fig.write_html(str(html_path), include_plotlyjs="cdn", full_html=True)
    return png_path, html_path


def top_accounts_bar(rows: list[dict], out: Path, title: str = "Top Key Accounts by Revenue") -> tuple[Path | None, Path]:
    if not rows:
        return None, out.with_suffix(".html")
    names = [r["account_name"] for r in rows]
    revs = [r.get("total_revenue", r.get("revenue", 0)) for r in rows]
    industries = [r.get("industry", "") for r in rows]
    fig = px.bar(
        x=revs, y=names, color=industries, orientation="h",
        labels={"x": "Total Revenue ($)", "y": "Account", "color": "Industry"},
        title=title,
    )
    fig.update_layout(yaxis={"categoryorder": "total ascending"}, height=600,
                      margin=dict(l=180, r=40, t=60, b=40))
    return _save_png_html(fig, out)


def yoy_comparison_bar(rows: list[dict], period_a: str, period_b: str, out: Path) -> tuple[Path | None, Path]:
    if not rows:
        return None, out.with_suffix(".html")
    names = [r["account_name"] for r in rows][:15]
    a = [r["revenue_a"] for r in rows][:15]
    b = [r["revenue_b"] for r in rows][:15]
    fig = go.Figure()
    fig.add_bar(name=period_a, x=names, y=a, marker_color="#9CB7F2")
    fig.add_bar(name=period_b, x=names, y=b, marker_color="#3B6CCC")
    fig.update_layout(
        title=f"Revenue Pattern Change: {period_a} vs {period_b}",
        barmode="group", xaxis_tickangle=-30, height=520,
        yaxis_title="Revenue ($)",
        margin=dict(l=60, r=40, t=60, b=140),
    )
    return _save_png_html(fig, out)


def conversion_scatter(low: list[dict], high: list[dict], out: Path) -> tuple[Path | None, Path]:
    pts = []
    for r in low + high:
        pts.append({
            "account": r["account_name"],
            "quoted": r["quoted_amount"],
            "revenue": r["recognized_revenue"],
            "conversion_pct": r["conversion_pct"] or 0,
            "segment": r.get("segment", ""),
            "industry": r.get("industry", ""),
        })
    if not pts:
        return None, out.with_suffix(".html")
    fig = px.scatter(
        pts, x="quoted", y="revenue", color="conversion_pct", hover_name="account",
        color_continuous_scale="RdYlGn",
        labels={"quoted": "Quoted Amount ($)", "revenue": "Recognized Revenue ($)", "conversion_pct": "Conv %"},
        title="Quote → Revenue Conversion by Account",
        size_max=20,
    )
    fig.update_traces(marker=dict(size=14, line=dict(width=1, color="DarkSlateGrey")))
    fig.update_layout(height=520)
    return _save_png_html(fig, out)


def booking_pattern_line(rows: list[dict], account_name: str, out: Path) -> tuple[Path | None, Path]:
    if not rows:
        return None, out.with_suffix(".html")
    periods = [r["period"] for r in rows]
    amounts = [r["booked_amount"] for r in rows]
    counts = [r["order_count"] for r in rows]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=periods, y=amounts, name="Booked $", marker_color="#3B6CCC", yaxis="y"))
    fig.add_trace(go.Scatter(x=periods, y=counts, name="Order Count", mode="lines+markers",
                              marker_color="#E26A2C", yaxis="y2"))
    fig.update_layout(
        title=f"Order Booking Pattern — {account_name}",
        xaxis_title="Period", yaxis=dict(title="Booked Amount ($)"),
        yaxis2=dict(title="Order Count", overlaying="y", side="right"),
        height=480, legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    return _save_png_html(fig, out)


def returns_trend_line(rows: list[dict], product_name: str, out: Path) -> tuple[Path | None, Path]:
    if not rows:
        return None, out.with_suffix(".html")
    months = [r["month"] for r in rows]
    rmas = [r["rmas"] for r in rows]
    qty = [r["qty"] for r in rows]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=months, y=rmas, name="RMA count", marker_color="#CC3344"))
    fig.add_trace(go.Scatter(x=months, y=qty, name="Units returned", mode="lines+markers",
                              marker_color="#FFA94D", yaxis="y2"))
    fig.update_layout(
        title=f"Customer Returns Trend — {product_name}",
        xaxis_title="Month",
        yaxis=dict(title="RMA Count"),
        yaxis2=dict(title="Units Returned", overlaying="y", side="right"),
        height=480, legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    return _save_png_html(fig, out)


def pipeline_funnel(rows: list[dict], out: Path) -> tuple[Path | None, Path]:
    if not rows:
        return None, out.with_suffix(".html")
    stages = [r["stage"] for r in rows]
    amounts = [r.get("total_amount", r.get("amount", 0)) for r in rows]
    fig = go.Figure(go.Funnel(y=stages, x=amounts, marker={"color": ["#264E86", "#3B6CCC", "#5C8EE6", "#85B0F0", "#B7D0F8"]}))
    fig.update_layout(title="Open Pipeline by Stage", height=520)
    return _save_png_html(fig, out)


def revenue_by_industry_donut(rows: list[dict], period: str, out: Path) -> tuple[Path | None, Path]:
    if not rows:
        return None, out.with_suffix(".html")
    fig = go.Figure(go.Pie(
        labels=[r["industry"] for r in rows],
        values=[r["revenue"] for r in rows],
        hole=0.45,
    ))
    fig.update_layout(title=f"{period} Revenue by Industry", height=460)
    return _save_png_html(fig, out)


def revenue_by_quarter_line(rows: list[dict], out: Path) -> tuple[Path | None, Path]:
    if not rows:
        return None, out.with_suffix(".html")
    fig = px.line(
        x=[r["period"] for r in rows],
        y=[r["revenue"] for r in rows],
        markers=True,
        labels={"x": "Quarter", "y": "Revenue ($)"},
        title="Recognized Revenue by Quarter",
    )
    fig.update_traces(line=dict(width=3, color="#264E86"))
    fig.update_layout(height=420)
    return _save_png_html(fig, out)
