"""Customer 360 page — pick an account, see CRM + ERP + QA together."""
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
    account_card,
    empty_state,
    format_money,
    insight_card,
    kpi_card,
    section_header,
)

# ---------------------------------------------------------------------------
# Sidebar: account picker
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("---")
    st.markdown("**👥 Customer 360**")
    accounts = da.all_accounts()
    account_names = sorted({a["name"] for a in accounts})
    selected = st.selectbox(
        "Account",
        ["—"] + account_names,
        index=(account_names.index("Lockheed Martin") + 1 if "Lockheed Martin" in account_names else 0),
        key="cust360_pick",
    )
    show_key_only = st.checkbox("Key accounts only", value=False)
    if show_key_only:
        filtered_names = sorted({a["name"] for a in accounts if a.get("is_key_account")})
        if selected != "—" and selected not in filtered_names:
            selected = filtered_names[0] if filtered_names else "—"
    st.markdown("---")
    st.markdown(f"**{len(accounts)} accounts**  ·  "
                f"{sum(1 for a in accounts if a.get('is_key_account'))} key  ·  "
                f"{sum(1 for a in accounts if a.get('segment') == 'Enterprise')} enterprise")

section_header("Drill-down", "Customer 360", action="CRM · ERP · QA combined view")

if selected == "—":
    empty_state("Pick an account from the sidebar",
                "Customer 360 brings together CRM relationships, ERP orders, and QA-side reliability for any account.",
                icon="👥")
    st.stop()

# Pull data via direct tools (fast)
account = da.get_account_summary(account_name=selected)
if "error" in account:
    st.error(account["error"])
    st.stop()
acct_id = account["id"]

# ---------------------------------------------------------------------------
# Header card with KPIs
# ---------------------------------------------------------------------------
# Compute KPIs
orders = da.list_sales_orders(external_account_id=acct_id, limit=1000)["rows"]
invoices = da.list_invoices(external_account_id=acct_id, limit=1000)["rows"]
returns = da.customer_returns_by_account(external_account_id=acct_id)["rows"]
total_revenue = sum(i.get("amount_paid", 0) + (i.get("total_amount", 0) - i.get("amount_paid", 0)) * 0 for i in invoices)  # use total
total_revenue = sum(i["total_amount"] for i in invoices if i["status"] == "Paid")
booked_amount = sum(o["grand_total"] for o in orders)

account_card(account, extra_kpis=[
    ("Lifetime Won", format_money(account.get("closed_won_amount", 0))),
    ("Open Pipeline", format_money(account.get("open_pipeline_amount", 0))),
    ("Total Orders", f"{len(orders):,}"),
    ("Total Invoiced", format_money(sum(i['total_amount'] for i in invoices))),
    ("Returns (RMAs)", f"{sum(r['rma_count'] for r in returns) if returns else 0}"),
])

st.markdown("&nbsp;")

# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------
tab_overview, tab_crm, tab_erp, tab_qa, tab_ai = st.tabs([
    "📋 Overview", "☁️ CRM", "🏭 ERP", "🔬 QA", "🤖 Ask the AI",
])

# ---------------------------------------------------------------------------
# Tab: Overview
# ---------------------------------------------------------------------------
with tab_overview:
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi_card("Industry", account["industry"], accent_color=TOKENS["primary"])
    with c2:
        kpi_card("Segment", account["segment"], accent_color=TOKENS["info"])
    with c3:
        annual_rev_b = (account.get("annual_revenue") or 0) / 1e9
        kpi_card("Annual Revenue", f"${annual_rev_b:.1f}B", sub="reported")
    with c4:
        kpi_card("Employees", f"{account.get('employee_count', 0):,}",
                 sub=account.get("billing_country", ""))

    st.markdown("&nbsp;")
    g1, g2 = st.columns([3, 2])
    # Booking pattern
    with g1:
        st.markdown("<div class='ent-card'>", unsafe_allow_html=True)
        st.markdown("<div class='ent-card-header'><div><div class='ent-card-title'>Booking pattern — last 12 quarters</div></div></div>", unsafe_allow_html=True)
        book = da.order_booking_patterns_by_account_name(account["name"], group_by="quarter")
        if book.get("rows"):
            df = pd.DataFrame(book["rows"])
            fig = go.Figure()
            fig.add_trace(go.Bar(x=df["period"], y=df["booked_amount"], name="Booked $",
                                 marker_color=TOKENS["primary"],
                                 hovertemplate="<b>%{x}</b><br>$%{y:,.0f}<extra></extra>"))
            fig.add_trace(go.Scatter(x=df["period"], y=df["order_count"], name="Order count",
                                     mode="lines+markers", line=dict(color=TOKENS["accent"], width=2),
                                     yaxis="y2"))
            fig.update_layout(
                height=320, margin=dict(l=0, r=0, t=10, b=0),
                xaxis=dict(showgrid=False),
                yaxis=dict(title="Booked ($)", showgrid=True, gridcolor=TOKENS["border"]),
                yaxis2=dict(title="Order count", overlaying="y", side="right", showgrid=False),
                legend=dict(orientation="h", yanchor="bottom", y=1.02),
                plot_bgcolor="white", paper_bgcolor="white",
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.caption("No bookings recorded for this account.")
        st.markdown("</div>", unsafe_allow_html=True)

    with g2:
        st.markdown("<div class='ent-card'>", unsafe_allow_html=True)
        st.markdown("<div class='ent-card-header'><div><div class='ent-card-title'>Contacts</div></div></div>", unsafe_allow_html=True)
        for c in account.get("contacts", [])[:5]:
            name = f"{c.get('first_name', '')} {c.get('last_name', '')}".strip()
            st.markdown(
                f"<div style='padding:8px 12px;background:{TOKENS['surface']};border:1px solid {TOKENS['border']};border-radius:6px;margin-bottom:6px;'>"
                f"<div style='font-weight:600;color:{TOKENS['text']};'>{name}</div>"
                f"<div style='font-size:0.8rem;color:{TOKENS['text_muted']};'>{c.get('title', '')}</div>"
                f"<div style='font-size:0.75rem;color:{TOKENS['text_subtle']};margin-top:2px;'>{c.get('email', '')}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Tab: CRM
# ---------------------------------------------------------------------------
with tab_crm:
    c1, c2 = st.columns([3, 2])
    with c1:
        st.subheader("Open opportunities")
        opps = da.list_opportunities(account_id=acct_id, limit=200)["rows"]
        open_opps = [o for o in opps if not o["stage"].startswith("Closed")]
        if open_opps:
            df = pd.DataFrame(open_opps)[
                ["name", "stage", "amount", "probability", "close_date", "primary_product_family"]
            ]
            df["amount"] = df["amount"].apply(format_money)
            df["probability"] = df["probability"].apply(lambda p: f"{int(p*100)}%")
            df.columns = ["Opportunity", "Stage", "Amount", "Prob.", "Close date", "Product family"]
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.caption("No open opportunities.")
    with c2:
        st.subheader("Pipeline by stage")
        if open_opps:
            df = pd.DataFrame(open_opps)
            agg = df.groupby("stage").agg(amount=("amount", "sum"), n=("name", "count")).reset_index()
            fig = px.bar(agg, x="amount", y="stage", orientation="h",
                          color="amount", color_continuous_scale="Blues",
                          labels={"amount": "Amount ($)", "stage": ""})
            fig.update_layout(height=300, margin=dict(l=0, r=0, t=10, b=0),
                              coloraxis_showscale=False,
                              plot_bgcolor="white", paper_bgcolor="white")
            st.plotly_chart(fig, use_container_width=True)

    st.markdown("&nbsp;")
    st.subheader("Recent quotes")
    quotes = da.list_quotes(account_id=acct_id, limit=20)["rows"]
    if quotes:
        df = pd.DataFrame(quotes)[
            ["quote_number", "status", "grand_total", "created_date", "accepted_date"]
        ]
        df["grand_total"] = df["grand_total"].apply(format_money)
        df.columns = ["Quote #", "Status", "Total", "Created", "Accepted"]
        st.dataframe(df, use_container_width=True, hide_index=True)

# ---------------------------------------------------------------------------
# Tab: ERP
# ---------------------------------------------------------------------------
with tab_erp:
    c1, c2, c3, c4 = st.columns(4)
    paid_inv = [i for i in invoices if i["status"] == "Paid"]
    open_inv = [i for i in invoices if i["status"] in ("Open", "Posted", "Sent", "Partially Paid")]
    overdue_inv = [i for i in invoices if i["status"] == "Overdue"]
    c1.metric("Total orders", f"{len(orders):,}")
    c2.metric("Total invoiced", format_money(sum(i["total_amount"] for i in invoices)))
    c3.metric("Outstanding AR", format_money(sum(i["amount_outstanding"] for i in invoices)))
    c4.metric("Overdue invoices", f"{len(overdue_inv)}",
              delta=f"-{format_money(sum(i['amount_outstanding'] for i in overdue_inv))}" if overdue_inv else None,
              delta_color="inverse" if overdue_inv else "normal")

    st.markdown("&nbsp;")
    cl, cr = st.columns([3, 2])
    with cl:
        st.subheader("Recent sales orders")
        if orders:
            df = pd.DataFrame(orders).head(20)[
                ["order_number", "order_date", "status", "grand_total", "actual_delivery_date"]
            ]
            df["grand_total"] = df["grand_total"].apply(format_money)
            df.columns = ["Order #", "Date", "Status", "Total", "Delivered"]
            st.dataframe(df, use_container_width=True, hide_index=True)
    with cr:
        st.subheader("Invoice status mix")
        statuses = pd.DataFrame(invoices).get("status")
        if statuses is not None and len(statuses):
            counts = statuses.value_counts().reset_index()
            counts.columns = ["status", "n"]
            color_map = {"Paid": TOKENS["success"], "Posted": TOKENS["info"],
                         "Partially Paid": TOKENS["warning"], "Overdue": TOKENS["error"],
                         "Disputed": "#9333EA", "Open": TOKENS["primary"], "Sent": TOKENS["primary_light"]}
            fig = px.pie(counts, names="status", values="n", hole=0.55,
                         color="status", color_discrete_map=color_map)
            fig.update_layout(height=300, margin=dict(l=0, r=0, t=10, b=0),
                              showlegend=True)
            st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------------------------
# Tab: QA
# ---------------------------------------------------------------------------
with tab_qa:
    if not returns:
        st.success("No customer returns recorded for this account.")
    else:
        c1, c2, c3 = st.columns(3)
        c1.metric("Total RMAs", f"{sum(r['rma_count'] for r in returns):,}")
        c2.metric("Units returned", f"{sum(r['qty'] for r in returns):,}")
        c3.metric("Replacement cost", format_money(sum(r['replacement_cost'] for r in returns)))

        st.markdown("&nbsp;")
        st.subheader("Top products returned by this account")
        df = pd.DataFrame(returns)
        products = {p["id"]: p for p in da.all_products()}
        df["product"] = df["external_account_id"].map(lambda x: account["name"])
        # Actually need to drill into customer_returns_by_product for accurate per-account-per-product breakdown
        from mcp_servers.qa.tools import qa as qa_conn  # noqa
        import sqlite3
        from mcp_servers.common import QA_DB
        conn = sqlite3.connect(QA_DB)
        conn.row_factory = sqlite3.Row
        per_prod = [dict(r) for r in conn.execute("""
            SELECT external_product_id, COUNT(*) AS rmas, SUM(qty_returned) AS qty,
                   ROUND(SUM(replacement_cost), 2) AS cost
              FROM customer_returns
             WHERE external_account_id = ?
             GROUP BY external_product_id
             ORDER BY rmas DESC LIMIT 15
        """, (acct_id,)).fetchall()]
        conn.close()
        if per_prod:
            df = pd.DataFrame(per_prod)
            df["product"] = df["external_product_id"].map(lambda x: products.get(x, {}).get("name", x[:12] + "…"))
            df["cost_fmt"] = df["cost"].apply(format_money)
            display = df[["product", "rmas", "qty", "cost_fmt"]].rename(
                columns={"product": "Product", "rmas": "RMAs", "qty": "Units", "cost_fmt": "Cost"}
            )
            st.dataframe(display, use_container_width=True, hide_index=True)

# ---------------------------------------------------------------------------
# Tab: Ask the AI
# ---------------------------------------------------------------------------
with tab_ai:
    st.markdown(
        f"<div class='ent-card'>"
        f"<div class='ent-card-title'>Quick AI prompts for {account['name']}</div>"
        f"<div class='ent-card-subtitle'>Click to open in the AI Assistant.</div>"
        f"</div>", unsafe_allow_html=True,
    )
    st.markdown("&nbsp;")
    suggestions = [
        f"Show me {account['name']}'s revenue trend over the last 8 quarters with YoY comparison.",
        f"What are {account['name']}'s top open opportunities and which products are involved?",
        f"Are there any reliability or returns issues with products that {account['name']} is buying?",
        f"Generate a one-page customer-success briefing for {account['name']}.",
    ]
    for s in suggestions:
        if st.button(f"💬 {s}", key=f"sug_{hash(s)}", use_container_width=True):
            # Inject the question as a pending prompt on a new conversation
            import uuid as _uuid, time as _time
            conv = {
                "id": _uuid.uuid4().hex[:8],
                "title": s[:60],
                "created_at": _time.time(),
                "messages": [],
                "pending_prompt": s,
            }
            if "conversations" not in st.session_state:
                st.session_state.conversations = []
            st.session_state.conversations.insert(0, conv)
            st.session_state.current_conv_id = conv["id"]
            st.switch_page("pages/assistant.py")
