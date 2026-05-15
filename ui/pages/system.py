"""System Health — MCP server status, DB stats, recent activity, config."""
from __future__ import annotations

import os
import sqlite3
import sys
import time
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mcp_servers.analytics.tools import TOOLS as ANA_TOOLS
from mcp_servers.common import CRM_DB, ERP_DB, QA_DB
from mcp_servers.crm.tools import TOOLS as CRM_TOOLS
from mcp_servers.erp.tools import TOOLS as ERP_TOOLS
from mcp_servers.qa.tools import TOOLS as QA_TOOLS
from ui import data_access as da
from ui.theme import TOKENS
from ui.widgets import kpi_card, section_header, server_status_card, status_pill

with st.sidebar:
    st.markdown("---")
    st.markdown("**⚙️ System Health**")
    st.caption("Live status of the MCP infrastructure")
    st.markdown("---")

section_header("Operations", "System Health", action="All services operational")

# ---------------------------------------------------------------------------
# MCP server status row (4 cards)
# ---------------------------------------------------------------------------
counts = da.db_table_counts()
crm_rows = sum(counts["CRM"].values())
erp_rows = sum(counts["ERP"].values())
qa_rows = sum(counts["QA"].values())

c1, c2, c3, c4 = st.columns(4)
with c1: server_status_card("Salesforce CRM", len(CRM_TOOLS), db_rows=crm_rows)
with c2: server_status_card("ERP System", len(ERP_TOOLS), db_rows=erp_rows)
with c3: server_status_card("QA / Reliability", len(QA_TOOLS), db_rows=qa_rows)
with c4: server_status_card("Analytics (cross-system)", len(ANA_TOOLS), db_rows=crm_rows + erp_rows + qa_rows)

st.markdown("&nbsp;")

# ---------------------------------------------------------------------------
# Database table-level stats
# ---------------------------------------------------------------------------
section_header("Databases", "Row counts by table")
for label, tables in counts.items():
    with st.expander(f"📦 {label} database — {sum(tables.values()):,} rows across {len(tables)} tables", expanded=(label == "CRM")):
        df = pd.DataFrame([(t, n) for t, n in tables.items()], columns=["Table", "Rows"])
        df = df.sort_values("Rows", ascending=False)
        col_left, col_right = st.columns([2, 3])
        with col_left:
            st.dataframe(df, use_container_width=True, hide_index=True, height=320)
        with col_right:
            fig = px.bar(df, x="Rows", y="Table", orientation="h",
                          color="Rows", color_continuous_scale="Blues")
            fig.update_layout(height=320, margin=dict(l=0, r=0, t=10, b=0),
                              coloraxis_showscale=False,
                              yaxis_title="", plot_bgcolor="white", paper_bgcolor="white")
            st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
st.markdown("&nbsp;")
section_header("Configuration", "Runtime")
config_l, config_r = st.columns(2)
with config_l:
    st.markdown(
        f"<div class='ent-card'>"
        f"<div class='ent-card-title'>🔑 Anthropic configuration</div>"
        f"<table style='width:100%;margin-top:10px;font-size:0.88rem;'>"
        f"<tr><td style='color:{TOKENS['text_muted']};padding:4px 0;'>Active model</td>"
        f"<td><code>{st.session_state.get('model', 'claude-sonnet-4-5')}</code></td></tr>"
        f"<tr><td style='color:{TOKENS['text_muted']};padding:4px 0;'>Max agent iterations</td>"
        f"<td><code>{st.session_state.get('max_iterations', 10)}</code></td></tr>"
        f"<tr><td style='color:{TOKENS['text_muted']};padding:4px 0;'>API base URL</td>"
        f"<td><code>{os.environ.get('ANTHROPIC_BASE_URL', 'https://api.anthropic.com')}</code></td></tr>"
        f"<tr><td style='color:{TOKENS['text_muted']};padding:4px 0;'>API key</td>"
        f"<td>"
        + (status_pill("Set", "success") if os.environ.get("ANTHROPIC_API_KEY")
           else status_pill("Missing", "error"))
        + f"</td></tr>"
        f"</table></div>",
        unsafe_allow_html=True,
    )
with config_r:
    st.markdown(
        f"<div class='ent-card'>"
        f"<div class='ent-card-title'>🗄️ Database files</div>"
        f"<table style='width:100%;margin-top:10px;font-size:0.88rem;'>"
        f"<tr><td style='color:{TOKENS['text_muted']};padding:4px 0;'>CRM</td>"
        f"<td><code>{CRM_DB.name}</code> · {CRM_DB.stat().st_size // 1024} KB</td></tr>"
        f"<tr><td style='color:{TOKENS['text_muted']};padding:4px 0;'>ERP</td>"
        f"<td><code>{ERP_DB.name}</code> · {ERP_DB.stat().st_size // 1024} KB</td></tr>"
        f"<tr><td style='color:{TOKENS['text_muted']};padding:4px 0;'>QA</td>"
        f"<td><code>{QA_DB.name}</code> · {QA_DB.stat().st_size // 1024} KB</td></tr>"
        f"</table></div>",
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------------------
# Recent agent activity
# ---------------------------------------------------------------------------
st.markdown("&nbsp;")
section_header("Activity log", "Recent agent tool calls (this session)")

activity = st.session_state.get("agent_activity_log", [])
if activity:
    with st.container(border=True):
        for entry in reversed(activity[-30:]):
            st.markdown(
                f"<div style='font-family:monospace;font-size:0.82rem;padding:3px 8px;color:{TOKENS['text']};'>{entry}</div>",
                unsafe_allow_html=True,
            )
else:
    st.caption("No agent activity yet — head to the AI Assistant and ask a question.")
