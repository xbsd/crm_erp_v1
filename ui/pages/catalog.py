"""Tool Catalog — browse and try the 33 MCP tools manually."""
from __future__ import annotations

import inspect
import json
import sys
import time
from pathlib import Path
from typing import Any

import streamlit as st

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mcp_servers.analytics.tools import TOOLS as ANA_TOOLS
from mcp_servers.crm.tools import TOOLS as CRM_TOOLS
from mcp_servers.erp.tools import TOOLS as ERP_TOOLS
from mcp_servers.qa.tools import TOOLS as QA_TOOLS
from ui.theme import SERVER_COLOR_MAP, TOKENS
from ui.widgets import section_header, status_pill

ALL_SERVERS = [
    ("Salesforce CRM", CRM_TOOLS, "☁️"),
    ("ERP System", ERP_TOOLS, "🏭"),
    ("QA / Reliability", QA_TOOLS, "🔬"),
    ("Analytics (cross-system)", ANA_TOOLS, "📊"),
]

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("---")
    st.markdown("**🔧 Tool Catalog**")
    server_filter = st.selectbox(
        "Filter by server",
        ["All"] + [s[0] for s in ALL_SERVERS],
    )
    search = st.text_input("🔍 Search", placeholder="e.g. revenue, account, reliability")
    st.markdown("---")
    st.caption(f"{sum(len(t) for _, t, _ in ALL_SERVERS)} tools available across {len(ALL_SERVERS)} MCP servers")

section_header("Operations", "Tool Catalog", action=f"{sum(len(t) for _, t, _ in ALL_SERVERS)} tools")

# ---------------------------------------------------------------------------
# Render tool cards grouped by server
# ---------------------------------------------------------------------------
for server_name, tools, icon in ALL_SERVERS:
    if server_filter != "All" and server_filter != server_name:
        continue
    filtered = tools
    if search:
        q = search.lower()
        filtered = [t for t in tools if q in t["name"].lower() or q in t["description"].lower()]
    if not filtered:
        continue
    color = SERVER_COLOR_MAP.get(server_name, TOKENS["primary"])
    st.markdown(
        f"""
        <div style='display:flex;align-items:center;gap:8px;margin:18px 0 10px 0;'>
          <span style='font-size:1.3rem;'>{icon}</span>
          <span style='font-size:1.15rem;font-weight:700;color:{color};'>{server_name}</span>
          <span class='ent-pill ent-pill-neutral'>{len(filtered)} of {len(tools)} tools</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    for tool in filtered:
        with st.expander(f"🛠️  `{tool['name']}` — {tool['description'][:80]}"):
            schema = tool.get("input_schema", {}) or {}
            properties = schema.get("properties", {}) or {}
            required = set(schema.get("required", []) or [])

            l, r = st.columns([2, 1])
            with l:
                st.markdown(f"**Description**")
                st.markdown(tool["description"])

                st.markdown("**Inputs**")
                if properties:
                    rows = []
                    for k, v in properties.items():
                        rows.append({
                            "Name": k + (" *" if k in required else ""),
                            "Type": v.get("type", "any"),
                            "Default": "—" if v.get("default") is None else str(v.get("default")),
                            "Description": (v.get("description") or "")[:140],
                        })
                    st.dataframe(rows, use_container_width=True, hide_index=True)
                else:
                    st.caption("No arguments.")

            with r:
                st.markdown("**Try it**")
                # Build input form
                args: dict[str, Any] = {}
                for k, v in properties.items():
                    typ = v.get("type", "string")
                    label = f"{k}{' *' if k in required else ''}"
                    default = v.get("default")
                    key = f"try_{tool['name']}_{k}"
                    if typ == "boolean":
                        args[k] = st.checkbox(label, value=bool(default), key=key)
                    elif typ == "integer":
                        val = st.number_input(label, value=int(default or 0), step=1, key=key)
                        args[k] = int(val) if val is not None else None
                    elif typ == "number":
                        val = st.number_input(label, value=float(default or 0.0), key=key)
                        args[k] = float(val) if val is not None else None
                    else:
                        enum_vals = v.get("enum")
                        if enum_vals:
                            args[k] = st.selectbox(label, [""] + list(enum_vals), key=key)
                        else:
                            args[k] = st.text_input(label, value=str(default) if default else "", key=key)
                # Strip empty optional fields
                args = {k: v for k, v in args.items() if v not in ("", None) or k in required}

                if st.button(f"▶ Run", key=f"run_{tool['name']}", type="primary",
                             use_container_width=True):
                    fn = tool["fn"]
                    try:
                        t0 = time.time()
                        result = fn(**args)
                        elapsed = time.time() - t0
                        st.markdown(status_pill(f"✓ {elapsed*1000:.0f} ms", "success"),
                                     unsafe_allow_html=True)
                        st.json(result, expanded=False)
                    except Exception as exc:
                        st.error(f"Error: {exc}")
