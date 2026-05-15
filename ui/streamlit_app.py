"""Enterprise AI Workbench — multipage Streamlit app.

Run:
    streamlit run ui/streamlit_app.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

st.set_page_config(
    page_title="Enterprise AI Workbench",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get Help": None, "Report a bug": None,
        "About": "Enterprise AI Workbench — MCP-orchestrated CRM + ERP + QA demo.",
    },
)

from ui.theme import inject_global_css   # noqa: E402
from ui.widgets import brand_header      # noqa: E402

inject_global_css()

# ---------------------------------------------------------------------------
# Session-state defaults
# ---------------------------------------------------------------------------
if "conversations" not in st.session_state:
    st.session_state.conversations = []   # list of {id, title, messages}
if "current_conv_id" not in st.session_state:
    st.session_state.current_conv_id = None
if "persona" not in st.session_state:
    st.session_state.persona = "Executive"
if "model" not in st.session_state:
    st.session_state.model = "claude-sonnet-4-5"
if "max_iterations" not in st.session_state:
    st.session_state.max_iterations = 10
if "agent_activity_log" not in st.session_state:
    st.session_state.agent_activity_log = []

# ---------------------------------------------------------------------------
# Sidebar brand + persistent settings (independent of selected page)
# ---------------------------------------------------------------------------
with st.sidebar:
    brand_header("Enterprise AI", "MCP Workbench")
    st.markdown(
        "<div style='color: #64748B; font-size: 0.8rem; margin: 6px 0 18px 0;'>"
        "CRM · ERP · QA &nbsp;·&nbsp; live agentic orchestration"
        "</div>",
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------------------
# Navigation
# ---------------------------------------------------------------------------
pages = {
    "Workspace": [
        st.Page("pages/dashboard.py",    title="Executive Dashboard", icon="📊", default=True),
        st.Page("pages/assistant.py",    title="AI Assistant",        icon="🤖"),
    ],
    "Drill-down": [
        st.Page("pages/customer360.py",  title="Customer 360",        icon="👥"),
        st.Page("pages/reliability.py",  title="Product Reliability", icon="🔬"),
    ],
    "Operations": [
        st.Page("pages/catalog.py",      title="Tool Catalog",        icon="🔧"),
        st.Page("pages/system.py",       title="System Health",       icon="⚙️"),
    ],
}
nav = st.navigation(pages, position="sidebar")
nav.run()
