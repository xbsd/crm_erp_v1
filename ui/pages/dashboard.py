"""Executive Dashboard page."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui import data_access as da
from ui.theme import TOKENS
from ui.widgets import (
    format_money,
    format_pct,
    insight_card,
    kpi_card,
    section_header,
    delta_sign,
    status_pill,
)

# ---------------------------------------------------------------------------
# Sidebar context (persona switcher etc.)
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("---")
    st.markdown("**View as**")
    persona = st.selectbox(
        "Role",
        ["Executive", "VP Sales", "Sales Manager", "Sales Engineer"],
        index=["Executive", "VP Sales", "Sales Manager", "Sales Engineer"].index(st.session_state.get("persona", "Executive")),
        label_visibility="collapsed",
    )
    st.session_state.persona = persona
    period = st.selectbox("Reporting period", ["Q1 2026 (latest)", "Q4 2025", "Q3 2025", "Q2 2025", "Q1 2025"], index=0)
    st.markdown("---")

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
section_header("Workspace", "Executive Dashboard", action=f"📅 {period}")

# Load KPI snapshot
kpi = da.headline_kpis()

# ---------------------------------------------------------------------------
# KPI strip
# ---------------------------------------------------------------------------
c1, c2, c3, c4, c5 = st.columns(5)
with c1:
    kpi_card(
        "Revenue · Current Quarter",
        format_money(kpi["revenue_current"]),
        delta=format_pct(kpi["yoy_pct"]),
        delta_sign=delta_sign(kpi["yoy_pct"]),
        sub=f"vs {kpi['prior_period']} {format_money(kpi['revenue_prior'])}",
        accent_color=TOKENS["primary"],
    )
with c2:
    kpi_card(
        "Open Pipeline",
        format_money(kpi["pipeline_total"]),
        sub=f"{kpi['pipeline_count']} opportunities",
        accent_color=TOKENS["info"],
    )
with c3:
    accounts = da.all_accounts()
    key_count = sum(1 for a in accounts if a.get("is_key_account"))
    kpi_card(
        "Key Accounts",
        f"{key_count}",
        sub=f"of {len(accounts)} total accounts",
        accent_color=TOKENS["accent"],
    )
with c4:
    returns = da.returns_top_products_cached(top_n=200)
    total_rmas = sum(r["rma_count"] for r in returns)
    kpi_card(
        "RMAs (cumulative)",
        f"{total_rmas:,}",
        sub=f"across {len(returns)} products",
        accent_color=TOKENS["qa"],
    )
with c5:
    ar = da.ar_aging_cached()
    overdue = sum(r["amount"] for r in ar if "Overdue" in r["bucket"])
    kpi_card(
        "AR Overdue",
        format_money(overdue),
        sub=f"{sum(r['invoice_count'] for r in ar if 'Overdue' in r['bucket'])} invoices",
        accent_color=TOKENS["error"] if overdue > 5_000_000 else TOKENS["warning"],
    )

st.markdown("&nbsp;")

# ---------------------------------------------------------------------------
# Charts row 1: Top key accounts + Quarterly revenue trend
# ---------------------------------------------------------------------------
col_l, col_r = st.columns([3, 2])

with col_l:
    with st.container(border=False):
        st.markdown("<div class='ent-card'>", unsafe_allow_html=True)
        st.markdown("<div class='ent-card-header'><div><div class='ent-card-title'>Top 10 Key Accounts by Revenue</div><div class='ent-card-subtitle'>All-time recognized revenue · CRM key-account flag applied</div></div></div>", unsafe_allow_html=True)
        top_accts = da.top_key_accounts_cached(10)
        df = pd.DataFrame(top_accts)
        if not df.empty:
            fig = px.bar(
                df.sort_values("total_revenue"),
                x="total_revenue", y="account_name",
                color="industry", orientation="h",
                color_discrete_sequence=px.colors.qualitative.Bold,
                labels={"total_revenue": "Revenue ($)", "account_name": ""},
            )
            fig.update_layout(
                height=360, margin=dict(l=0, r=0, t=10, b=0),
                showlegend=True, legend=dict(orientation="h", yanchor="bottom", y=-0.25),
                plot_bgcolor="white", paper_bgcolor="white",
                xaxis=dict(showgrid=True, gridcolor=TOKENS["border"]),
                yaxis=dict(showgrid=False),
            )
            st.plotly_chart(fig, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

with col_r:
    st.markdown("<div class='ent-card'>", unsafe_allow_html=True)
    st.markdown("<div class='ent-card-header'><div><div class='ent-card-title'>Quarterly Revenue Trend</div><div class='ent-card-subtitle'>Recognized revenue · all customers</div></div></div>", unsafe_allow_html=True)
    qrev = da.revenue_quarterly_series()
    df = pd.DataFrame(qrev)
    if not df.empty:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df["period"], y=df["revenue"], mode="lines+markers",
            line=dict(width=3, color=TOKENS["primary"]), marker=dict(size=8),
            fill="tozeroy", fillcolor=f"rgba(30, 64, 175, 0.08)",
            hovertemplate="%{x}<br>$%{y:,.0f}<extra></extra>",
        ))
        fig.update_layout(
            height=360, margin=dict(l=0, r=0, t=10, b=0),
            plot_bgcolor="white", paper_bgcolor="white",
            xaxis=dict(showgrid=False),
            yaxis=dict(showgrid=True, gridcolor=TOKENS["border"], title="Revenue ($)"),
        )
        st.plotly_chart(fig, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Charts row 2: Industry mix + Pipeline funnel + Top movers
# ---------------------------------------------------------------------------
c1, c2, c3 = st.columns(3)

with c1:
    st.markdown("<div class='ent-card'>", unsafe_allow_html=True)
    st.markdown(f"<div class='ent-card-header'><div><div class='ent-card-title'>{kpi['period']} Revenue by Industry</div></div></div>", unsafe_allow_html=True)
    df = pd.DataFrame(kpi["by_industry"])
    if not df.empty:
        fig = go.Figure(go.Pie(
            labels=df["industry"], values=df["revenue"], hole=0.55,
            marker=dict(colors=px.colors.qualitative.Bold),
            textinfo="percent", hovertemplate="<b>%{label}</b><br>$%{value:,.0f}<extra></extra>",
        ))
        fig.update_layout(
            height=320, margin=dict(l=0, r=0, t=10, b=0),
            showlegend=True, legend=dict(orientation="v", yanchor="middle", y=0.5, x=1.02),
        )
        st.plotly_chart(fig, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

with c2:
    st.markdown("<div class='ent-card'>", unsafe_allow_html=True)
    st.markdown("<div class='ent-card-header'><div><div class='ent-card-title'>Open Pipeline by Stage</div></div></div>", unsafe_allow_html=True)
    df = pd.DataFrame(kpi["pipeline_by_stage"])
    if not df.empty:
        stage_order = ["Prospecting", "Qualification", "Needs Analysis", "Proposal", "Negotiation"]
        df["sort"] = df["stage"].apply(lambda s: stage_order.index(s) if s in stage_order else 99)
        df = df.sort_values("sort")
        fig = go.Figure(go.Funnel(
            y=df["stage"], x=df["amount"],
            marker=dict(color=[TOKENS["info"], TOKENS["primary_light"], TOKENS["primary"], TOKENS["primary_dark"], TOKENS["accent"]]),
            textinfo="value+percent initial",
            hovertemplate="<b>%{y}</b><br>$%{x:,.0f}<extra></extra>",
        ))
        fig.update_layout(height=320, margin=dict(l=0, r=0, t=10, b=0))
        st.plotly_chart(fig, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

with c3:
    st.markdown("<div class='ent-card'>", unsafe_allow_html=True)
    st.markdown("<div class='ent-card-header'><div><div class='ent-card-title'>Q1 2025 → Q1 2026 Top Movers</div><div class='ent-card-subtitle'>Key accounts only</div></div></div>", unsafe_allow_html=True)
    moves = da.revenue_pattern_change_cached(threshold=0)["rows"]
    df = pd.DataFrame(moves)
    if not df.empty:
        df = df.sort_values("delta_abs", key=abs, ascending=False).head(8)
        df["color"] = df["delta_abs"].apply(lambda v: TOKENS["success"] if v >= 0 else TOKENS["error"])
        fig = go.Figure(go.Bar(
            x=df["delta_abs"], y=df["account_name"],
            orientation="h",
            marker_color=df["color"],
            hovertemplate="<b>%{y}</b><br>Δ $%{x:,.0f}<extra></extra>",
        ))
        fig.update_layout(
            height=320, margin=dict(l=0, r=0, t=10, b=0),
            plot_bgcolor="white", paper_bgcolor="white",
            xaxis=dict(showgrid=True, gridcolor=TOKENS["border"], title="Δ Revenue ($)"),
            yaxis=dict(showgrid=False, autorange="reversed"),
        )
        st.plotly_chart(fig, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Insight strip
# ---------------------------------------------------------------------------
st.markdown("&nbsp;")
ins_l, ins_m, ins_r = st.columns(3)
with ins_l:
    insight_card(
        title="Strong YoY momentum",
        body=f"Recognized revenue is up <b>{format_pct(kpi['yoy_pct'])}</b> in {kpi['period']} compared to {kpi['prior_period']}.  "
             f"<b>{kpi['top_customer']}</b> leads at {format_money(kpi['top_customer_revenue'])}.",
        icon="📈", tone="success",
    )
with ins_m:
    moves = da.revenue_pattern_change_cached(threshold=25)["rows"]
    growers = [r for r in moves if (r.get("change_type") or "").startswith(("Growth", "New"))]
    decliners = [r for r in moves if (r.get("change_type") or "").startswith(("Decline", "Lost"))]
    insight_card(
        title="Revenue pattern shifts",
        body=f"{len(growers)} key accounts in <span style='color:#10B981;font-weight:600'>growth or new</span>, "
             f"{len(decliners)} in <span style='color:#EF4444;font-weight:600'>decline or lost</span>.  "
             f"Open the AI Assistant to drill into specific movers.",
        icon="🔄", tone="info",
    )
with ins_r:
    rels = da.reliability_low_scores(5)
    n_low = len(rels)
    insight_card(
        title="Reliability watch-list",
        body=f"<b>{n_low}</b> products currently scoring below 75. Review the Product Reliability page to see affected accounts and corrective actions.",
        icon="⚠️", tone="warning" if n_low > 0 else "success",
    )

# ---------------------------------------------------------------------------
# Bottom: Top customers + Reliability concerns
# ---------------------------------------------------------------------------
st.markdown("&nbsp;")
b1, b2 = st.columns([3, 2])

with b1:
    st.markdown("<div class='ent-card'>", unsafe_allow_html=True)
    st.markdown(f"<div class='ent-card-header'><div><div class='ent-card-title'>Top customers · {kpi['period']}</div></div></div>", unsafe_allow_html=True)
    df = pd.DataFrame(kpi["top_customers"]).head(10)
    if not df.empty:
        df_display = df[["customer_name", "revenue"]].copy()
        df_display["revenue"] = df_display["revenue"].apply(lambda v: format_money(v))
        df_display.columns = ["Customer", "Revenue (Q1 2026)"]
        df_display.index = range(1, len(df_display) + 1)
        st.dataframe(df_display, use_container_width=True, height=380)
    st.markdown("</div>", unsafe_allow_html=True)

with b2:
    st.markdown("<div class='ent-card'>", unsafe_allow_html=True)
    st.markdown("<div class='ent-card-header'><div><div class='ent-card-title'>Reliability concerns</div><div class='ent-card-subtitle'>Highest RMA volume — current quarter</div></div></div>", unsafe_allow_html=True)
    rc = pd.DataFrame(kpi["reliability_concerns"])
    if not rc.empty:
        rc = rc.head(8).copy()
        # Map product id → name
        products = {p["id"]: p for p in da.all_products()}
        rc["product"] = rc["external_product_id"].map(lambda x: products.get(x, {}).get("name", x[:14] + "…"))
        rc["cost_fmt"] = rc["cost"].apply(format_money)
        st.dataframe(
            rc[["product", "rmas", "cost_fmt"]].rename(columns={"product": "Product", "rmas": "RMAs", "cost_fmt": "Cost"}),
            use_container_width=True, height=380, hide_index=True,
        )
    else:
        st.write("No reliability concerns flagged this quarter.")
    st.markdown("</div>", unsafe_allow_html=True)
