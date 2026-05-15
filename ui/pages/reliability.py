"""Product Reliability Hub."""
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
    empty_state,
    format_money,
    insight_card,
    kpi_card,
    section_header,
    status_pill,
)


def grade_color(grade: str) -> str:
    return {
        "A+": TOKENS["success"], "A": TOKENS["success"],
        "B": TOKENS["primary_light"],
        "C": TOKENS["warning"], "D": TOKENS["warning"],
        "F": TOKENS["error"],
    }.get(grade, TOKENS["text_muted"])


def grade_status(grade: str) -> str:
    return {"A+": "success", "A": "success", "B": "info",
            "C": "warning", "D": "warning", "F": "error"}.get(grade, "neutral")


# ---------------------------------------------------------------------------
# Sidebar: filter + product picker
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("---")
    st.markdown("**🔬 Product Reliability**")
    products = da.all_products()
    families = sorted({p["product_family"] for p in products})
    family_filter = st.selectbox("Family", ["All"] + families)
    filtered = products if family_filter == "All" else [p for p in products if p["product_family"] == family_filter]
    product_names = sorted({p["name"] for p in filtered})
    selected = st.selectbox("Product", ["—"] + product_names,
                             index=(product_names.index("Temperature Sensor TSN0124") + 1)
                             if "Temperature Sensor TSN0124" in product_names else 0)
    st.markdown("---")
    st.markdown("**Watch-list**")
    st.caption("Lowest-scoring products (below 75)")
    low = da.reliability_low_scores(8)
    prod_map = {p["id"]: p for p in products}
    for r in low:
        pname = prod_map.get(r["external_product_id"], {}).get("name", "Unknown")
        if st.button(f"⚠️ {pname[:30]}  ·  {r['score']}",
                      key=f"wl_{r['external_product_id']}",
                      use_container_width=True):
            st.session_state["reliab_pick"] = pname
            st.rerun()
    if "reliab_pick" in st.session_state:
        selected = st.session_state.pop("reliab_pick")

section_header("Drill-down", "Product Reliability Hub", action="QA + cross-system")

if selected == "—":
    empty_state("Pick a product",
                "Reliability score, MTBF/MTTR trend, failure modes, customer returns, and affected accounts — all from the QA MCP server.",
                icon="🔬")
    st.stop()

# Resolve product id
product = next((p for p in products if p["name"] == selected), None)
if not product:
    st.error("Product not found.")
    st.stop()

pid = product["id"]
report = da.get_product_reliability_report(pid)

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
score_obj = report.get("reliability_score") or {}
score = score_obj.get("score", 0)
grade = score_obj.get("score_grade", "—")

st.markdown(
    f"""
    <div class='ent-card' style='display:flex;gap:24px;align-items:center;'>
      <div style='flex-shrink:0;width:120px;height:120px;border-radius:50%;
                  background:conic-gradient({grade_color(grade)} {score * 3.6}deg, {TOKENS['surface_alt']} 0);
                  display:flex;align-items:center;justify-content:center;'>
        <div style='background:white;width:90px;height:90px;border-radius:50%;
                    display:flex;flex-direction:column;align-items:center;justify-content:center;'>
          <div style='font-size:1.8rem;font-weight:700;color:{TOKENS['text']};line-height:1;'>{score}</div>
          <div style='font-size:0.7rem;color:{TOKENS['text_muted']};'>RELIABILITY</div>
        </div>
      </div>
      <div style='flex:1;'>
        <div style='display:flex;gap:10px;align-items:baseline;'>
          <div style='font-size:1.5rem;font-weight:700;color:{TOKENS['text']};'>{product['name']}</div>
          <span class='ent-pill ent-pill-{grade_status(grade)}'>Grade {grade}</span>
        </div>
        <div style='color:{TOKENS['text_muted']};font-size:0.9rem;margin-top:4px;'>
          {product['product_family']} · {product['product_category']} ·
          SKU <code>{product['sku']}</code> ·
          List price ${product['list_price']:.2f}
        </div>
        <div style='color:{TOKENS['text']};font-size:0.92rem;margin-top:10px;line-height:1.4;'>
          {score_obj.get('recommendation', '')}
        </div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown("&nbsp;")

# ---------------------------------------------------------------------------
# KPI row: MTBF, failure rate, RMAs, replacement cost
# ---------------------------------------------------------------------------
metrics_rows = report.get("metrics_by_quarter") or []
latest_mtbf = metrics_rows[0]["mtbf_hours"] if metrics_rows else None
latest_fr = metrics_rows[0]["failure_rate_ppm"] if metrics_rows else None
ret_sum = report.get("customer_returns", {}).get("summary") or {}
fail_count = sum(b["n"] for b in (report.get("failures", {}).get("by_severity") or []))

c1, c2, c3, c4 = st.columns(4)
with c1:
    kpi_card("MTBF (latest)",
             f"{latest_mtbf / 1000:.1f}k hrs" if latest_mtbf else "—",
             sub="Mean Time Between Failures",
             accent_color=TOKENS["primary"])
with c2:
    kpi_card("Failure rate",
             f"{latest_fr:,.0f} PPM" if latest_fr else "—",
             sub="Parts per million / quarter",
             accent_color=TOKENS["accent"])
with c3:
    kpi_card("Total RMAs",
             f"{ret_sum.get('rma_count', 0):,}",
             sub=f"{ret_sum.get('qty_returned', 0):,} units returned",
             accent_color=TOKENS["error"] if ret_sum.get("rma_count", 0) > 10 else TOKENS["warning"])
with c4:
    kpi_card("Replacement cost",
             format_money(ret_sum.get("replacement_cost", 0)),
             sub=f"{fail_count} failure records",
             accent_color=TOKENS["qa"])

st.markdown("&nbsp;")

# ---------------------------------------------------------------------------
# Charts: MTBF trend + failure modes pie
# ---------------------------------------------------------------------------
g1, g2 = st.columns([3, 2])
with g1:
    st.markdown("<div class='ent-card'>", unsafe_allow_html=True)
    st.markdown("<div class='ent-card-header'><div><div class='ent-card-title'>MTBF & Failure-rate trend</div><div class='ent-card-subtitle'>By quarter · most recent on the right</div></div></div>", unsafe_allow_html=True)
    df = pd.DataFrame(metrics_rows).sort_values("period_label") if metrics_rows else pd.DataFrame()
    if not df.empty:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df["period_label"], y=df["mtbf_hours"],
            mode="lines+markers", name="MTBF (hrs)",
            line=dict(color=TOKENS["primary"], width=3),
            marker=dict(size=8),
        ))
        fig.add_trace(go.Scatter(
            x=df["period_label"], y=df["failure_rate_ppm"],
            mode="lines+markers", name="Failure rate (PPM)",
            line=dict(color=TOKENS["error"], width=2, dash="dot"),
            yaxis="y2",
        ))
        fig.update_layout(
            height=340, margin=dict(l=0, r=0, t=10, b=0),
            yaxis=dict(title="MTBF (hours)", showgrid=True, gridcolor=TOKENS["border"]),
            yaxis2=dict(title="Failure rate (PPM)", overlaying="y", side="right"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
            plot_bgcolor="white", paper_bgcolor="white",
        )
        st.plotly_chart(fig, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

with g2:
    st.markdown("<div class='ent-card'>", unsafe_allow_html=True)
    st.markdown("<div class='ent-card-header'><div><div class='ent-card-title'>Failure modes</div><div class='ent-card-subtitle'>Distribution of recorded failures</div></div></div>", unsafe_allow_html=True)
    modes = report.get("failures", {}).get("by_mode") or []
    if modes:
        df = pd.DataFrame(modes)
        fig = px.pie(df, names="failure_mode", values="n", hole=0.5,
                     color_discrete_sequence=px.colors.qualitative.Bold)
        fig.update_layout(height=340, margin=dict(l=0, r=0, t=10, b=0))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.caption("No failure records yet.")
    st.markdown("</div>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Returns by reason + Affected accounts
# ---------------------------------------------------------------------------
g1, g2 = st.columns(2)
with g1:
    st.markdown("<div class='ent-card'>", unsafe_allow_html=True)
    st.markdown("<div class='ent-card-header'><div><div class='ent-card-title'>Returns by reason</div></div></div>", unsafe_allow_html=True)
    reasons = report.get("customer_returns", {}).get("by_reason") or []
    if reasons:
        df = pd.DataFrame(reasons).sort_values("n", ascending=True)
        fig = px.bar(df, x="n", y="return_reason", orientation="h",
                     color="n", color_continuous_scale="Reds")
        fig.update_layout(height=320, margin=dict(l=0, r=0, t=10, b=0),
                          coloraxis_showscale=False,
                          xaxis_title="RMA count", yaxis_title="",
                          plot_bgcolor="white", paper_bgcolor="white")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.caption("No returns reported.")
    st.markdown("</div>", unsafe_allow_html=True)

with g2:
    st.markdown("<div class='ent-card'>", unsafe_allow_html=True)
    st.markdown("<div class='ent-card-header'><div><div class='ent-card-title'>Affected accounts</div><div class='ent-card-subtitle'>Top accounts returning this product</div></div></div>", unsafe_allow_html=True)
    # Fetch returns trend & accounts
    ret = da.returns_increase_for_product(product["sku"])
    if "top_accounts_returning" in ret:
        df = pd.DataFrame(ret["top_accounts_returning"]).head(8)
        if not df.empty:
            df["cost_fmt"] = df["cost"].apply(format_money)
            st.dataframe(
                df[["account_name", "industry", "rmas", "qty", "cost_fmt"]].rename(
                    columns={"account_name": "Account", "industry": "Industry",
                             "rmas": "RMAs", "qty": "Units", "cost_fmt": "Cost"},
                ),
                use_container_width=True, hide_index=True, height=320,
            )
        else:
            st.caption("No affected accounts.")
    st.markdown("</div>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Compliance + Test runs
# ---------------------------------------------------------------------------
st.markdown("&nbsp;")
g1, g2 = st.columns([1, 1])
with g1:
    st.markdown("<div class='ent-card'>", unsafe_allow_html=True)
    st.markdown("<div class='ent-card-header'><div><div class='ent-card-title'>Compliance status</div></div></div>", unsafe_allow_html=True)
    comps = report.get("compliance") or []
    if comps:
        for c in comps[:8]:
            tone = "success" if c["status"] == "Active" else ("warning" if c["status"] == "Pending Renewal" else "error")
            st.markdown(
                f"<div style='display:flex;justify-content:space-between;align-items:center;"
                f"padding:6px 10px;background:white;border-radius:6px;border:1px solid {TOKENS['border']};margin-bottom:4px;'>"
                f"<div><b>{c['standard']}</b> · <span style='color:{TOKENS['text_muted']};font-size:0.78rem;'>{c['certificate_number']}</span></div>"
                + status_pill(c["status"], tone)
                + f"<div style='font-size:0.78rem;color:{TOKENS['text_muted']};'>exp {c['expiry_date'][:7]}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )
    st.markdown("</div>", unsafe_allow_html=True)

with g2:
    st.markdown("<div class='ent-card'>", unsafe_allow_html=True)
    test = report.get("test_runs_summary") or {}
    st.markdown(
        f"<div class='ent-card-header'><div><div class='ent-card-title'>Qualification testing</div>"
        f"<div class='ent-card-subtitle'>{test.get('runs', 0)} test runs · "
        f"{test.get('samples', 0):,} samples · "
        f"avg pass rate {(test.get('avg_pass_rate', 0) or 0) * 100:.1f}%</div></div></div>",
        unsafe_allow_html=True,
    )
    env_tests = report.get("environmental_tests") or []
    if env_tests:
        df = pd.DataFrame(env_tests)
        df["pass_rate"] = (df["samples_passed"] / df["samples_tested"] * 100).round(1)
        df["pass_fmt"] = df["pass_rate"].apply(lambda x: f"{x}%")
        st.dataframe(
            df[["test_type", "samples_tested", "samples_passed", "pass_fmt", "duration_hrs"]].rename(
                columns={"test_type": "Test", "samples_tested": "Tested",
                         "samples_passed": "Passed", "pass_fmt": "Pass %", "duration_hrs": "Hours"},
            ),
            use_container_width=True, hide_index=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# AI deep-dive
# ---------------------------------------------------------------------------
st.markdown("&nbsp;")
ai_l, ai_r = st.columns([3, 2])
with ai_l:
    if st.button(f"🤖 Ask AI: Generate a reliability briefing for {product['name']}",
                  type="primary", use_container_width=True):
        import uuid, time
        conv = {
            "id": uuid.uuid4().hex[:8],
            "title": f"Reliability briefing — {product['name']}"[:60],
            "created_at": time.time(),
            "messages": [],
            "pending_prompt": (
                f"Generate a one-page reliability briefing for {product['name']} (SKU {product['sku']}). "
                f"Cover: current score and grade, MTBF/failure-rate trend, top failure modes, "
                f"customer-return summary including which accounts are most affected, and a clear recommendation."
            ),
        }
        st.session_state.conversations.insert(0, conv)
        st.session_state.current_conv_id = conv["id"]
        st.switch_page("pages/assistant.py")
with ai_r:
    if ret.get("comparison", {}).get("increase_detected"):
        insight_card(
            "Returns are trending up",
            f"Recent vs prior {ret['comparison']['recent_window']}: "
            f"<b>{ret['comparison']['recent_rmas']}</b> RMAs vs "
            f"<b>{ret['comparison']['prior_rmas']}</b> prior — "
            f"<span style='color:{TOKENS['error']};font-weight:600;'>"
            f"{ret['comparison']['delta_pct']:+.1f}%</span>",
            icon="📈", tone="error",
        )
    else:
        insight_card(
            "Returns trend stable",
            f"No significant change detected between recent and prior windows.",
            icon="✅", tone="success",
        )
