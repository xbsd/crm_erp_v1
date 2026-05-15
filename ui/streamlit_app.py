"""Streamlit demo UI for the MCP-powered enterprise AI agent.

Run:
    streamlit run ui/streamlit_app.py
"""
from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pandas as pd
import streamlit as st

from agent.mcp_client import MultiMCPClient
from agent.orchestrator import run_agent
from tests.use_cases import USE_CASES

OUTPUTS = ROOT / "outputs"

st.set_page_config(
    page_title="MCP Enterprise Demo — CRM + ERP + QA",
    page_icon="🤖",
    layout="wide",
)


# -----------------------------------------------------------------------------
# Sidebar
# -----------------------------------------------------------------------------
st.sidebar.title("🤖 MCP Enterprise Demo")
st.sidebar.markdown(
    "Ask a natural-language question and watch a Claude-powered agent "
    "orchestrate tool calls across **four MCP servers** to answer it."
)
st.sidebar.markdown("---")
st.sidebar.subheader("Systems")
st.sidebar.markdown(
    "- 🟦 **Salesforce CRM** — leads, accounts, opportunities, products, quotes\n"
    "- 🟩 **ERP** — customers, sales orders, invoices, payments, revenue\n"
    "- 🟪 **QA / Reliability** — tests, MTBF, failures, customer returns\n"
    "- 🟧 **Analytics** — cross-system joins"
)

st.sidebar.markdown("---")
st.sidebar.subheader("Example questions")
default_question = None
for case in USE_CASES:
    if st.sidebar.button(f"[{case['audience'][:3].upper()}] {case['title']}", key=f"q_{case['id']}", use_container_width=True):
        default_question = case["question"]
        st.session_state["picked_case"] = case

st.sidebar.markdown("---")
st.sidebar.caption("Data: synthetic — semiconductor / industrial scenario, 2024-01 → 2026-05.")


# -----------------------------------------------------------------------------
# Main panel
# -----------------------------------------------------------------------------
st.title("Enterprise AI Agent across CRM + ERP + QA")
st.caption(
    "Natural-language questions → Claude Sonnet 4.5 → MCP tool calls "
    "across Salesforce, ERP, and Quality systems → executive answer + charts."
)

case_info = st.session_state.get("picked_case")
if case_info:
    st.info(f"**{case_info['audience']}: {case_info['title']}** — preview from PDF use cases")

prompt = st.text_area(
    "Ask a question",
    value=default_question or st.session_state.get("custom_q", ""),
    height=120,
    placeholder="e.g. 'Who are my top 10 key accounts?'",
)
col_a, col_b = st.columns([1, 4])
run_btn = col_a.button("▶ Run agent", type="primary", disabled=not prompt.strip())
col_b.caption("The agent will pick the right MCP tools across the four servers.")


# -----------------------------------------------------------------------------
# Agent execution
# -----------------------------------------------------------------------------
def _format_arg_value(v):
    if isinstance(v, str) and len(v) > 60:
        return v[:57] + "..."
    return v


def run_question(question: str) -> dict:
    log: list[dict] = []

    async def _go() -> dict:
        async with MultiMCPClient() as client:
            def on_step(event: str, payload: dict) -> None:
                log.append({"event": event, **payload})
            result = await run_agent(client, question, on_step=on_step)
            return {
                "final_answer": result.final_answer,
                "trace": [
                    {
                        "tool_name": t.tool_name,
                        "server_label": t.server_label,
                        "arguments": t.arguments,
                        "result_preview": t.result_preview,
                        "duration_s": t.duration_s,
                        "iteration": t.iteration,
                    }
                    for t in result.trace
                ],
                "iterations": result.iterations,
                "total_seconds": result.total_seconds,
                "log": log,
            }
    return asyncio.run(_go())


if run_btn and prompt.strip():
    st.session_state["custom_q"] = prompt
    placeholder = st.container()
    with placeholder.status("Running agent — connecting to MCP servers...", expanded=True) as status:
        try:
            result = run_question(prompt.strip())
            status.update(label=f"✓ Done in {result['total_seconds']:.1f}s "
                                f"({result['iterations']} iterations, {len(result['trace'])} tool calls)",
                          state="complete")
        except Exception as exc:
            st.error(f"Error: {exc}")
            st.stop()
        st.write("**Tool trace:**")
        for t in result["trace"]:
            with st.expander(f"🔧 `{t['server_label']}` :: `{t['tool_name']}`  ({t['duration_s']:.2f}s)"):
                st.json({k: _format_arg_value(v) for k, v in t["arguments"].items()})
                st.code(t["result_preview"][:1500], language="json")

    st.markdown("---")
    st.subheader("Answer")
    st.markdown(result["final_answer"])

    # Render pre-generated chart if relevant
    q_lower = prompt.lower()
    rendered_charts = []
    if any(kw in q_lower for kw in ["top 10", "key account", "top account"]):
        rendered_charts.append(("Top Key Accounts (chart)", OUTPUTS / "chart_top_accounts.png"))
    if "q1" in q_lower or "year" in q_lower or "yoy" in q_lower:
        rendered_charts.append(("Q1 YoY Comparison", OUTPUTS / "chart_yoy_revenue.png"))
    if "conversion" in q_lower or "quote" in q_lower:
        rendered_charts.append(("Quote → Revenue Conversion", OUTPUTS / "chart_conversion.png"))
    if "booking" in q_lower or "order" in q_lower:
        rendered_charts.append(("Order Booking Pattern", OUTPUTS / "chart_booking_lockheed.png"))
    if "return" in q_lower or "tsn" in q_lower:
        rendered_charts.append(("Returns Trend", OUTPUTS / "chart_returns_tsn0124.png"))
    if "pipeline" in q_lower or "stage" in q_lower:
        rendered_charts.append(("Pipeline Funnel", OUTPUTS / "chart_pipeline_funnel.png"))
    if "quarterly" in q_lower or "presentation" in q_lower:
        rendered_charts.append(("Industry mix", OUTPUTS / "chart_industry_donut.png"))
        rendered_charts.append(("Quarterly revenue", OUTPUTS / "chart_quarterly_revenue.png"))
    rendered_charts = [(t, p) for t, p in rendered_charts if p.exists()]
    if rendered_charts:
        st.markdown("---")
        st.subheader("Related visualizations")
        cols = st.columns(min(2, len(rendered_charts)))
        for i, (title, path) in enumerate(rendered_charts):
            with cols[i % len(cols)]:
                st.markdown(f"**{title}**")
                st.image(str(path), use_container_width=True)

    # Download button for a quarterly deck if relevant
    deck_path = OUTPUTS / "sales_quarterly_update_2026-Q1.pptx"
    if "quarterly" in q_lower and deck_path.exists():
        with open(deck_path, "rb") as fh:
            st.download_button(
                "📥 Download Sales Quarterly Update (.pptx)",
                data=fh.read(),
                file_name=deck_path.name,
                mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            )
else:
    st.markdown("---")
    st.subheader("How it works")
    st.markdown(
        """
1. Your question is sent to **Claude Sonnet 4.5** with descriptions of every tool exposed by the 4 MCP servers.
2. Claude decides which tools to call (often the cross-system Analytics ones) and with what arguments.
3. Each MCP server runs the actual query against its database (CRM / ERP / QA) and returns JSON.
4. Claude reads the results and either calls more tools or writes the final answer.

The agent loop typically completes in **1–3 iterations** with **1–5 tool calls** for these executive questions.
        """
    )
    st.markdown("---")
    st.subheader("Sample data shape")
    counts = {}
    import sqlite3
    for name, path in [("CRM", "databases/crm.db"), ("ERP", "databases/erp.db"), ("QA", "databases/qa.db")]:
        conn = sqlite3.connect(path)
        tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        counts[name] = {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in tables}
        conn.close()
    for name, table_counts in counts.items():
        with st.expander(f"{name} database ({sum(table_counts.values())} rows across {len(table_counts)} tables)"):
            df = pd.DataFrame([(t, n) for t, n in table_counts.items()], columns=["Table", "Row count"])
            st.dataframe(df, use_container_width=True, hide_index=True)
