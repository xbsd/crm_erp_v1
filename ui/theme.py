"""Design tokens + CSS injection for the enterprise UI.

Single source of truth for colors, typography, spacing.  Streamlit's
default theme can be overridden via `.streamlit/config.toml`, but for
component-level polish we inject targeted CSS.
"""
from __future__ import annotations

import streamlit as st

# ---------------------------------------------------------------------------
# Design tokens
# ---------------------------------------------------------------------------
TOKENS = {
    # Brand
    "primary": "#1E40AF",
    "primary_dark": "#1E3A8A",
    "primary_light": "#3B82F6",
    "accent": "#F59E0B",
    # Surfaces
    "bg": "#F8FAFC",
    "surface": "#FFFFFF",
    "surface_alt": "#F1F5F9",
    "border": "#E2E8F0",
    "border_strong": "#CBD5E1",
    # Text
    "text": "#0F172A",
    "text_muted": "#64748B",
    "text_subtle": "#94A3B8",
    # Status
    "success": "#10B981",
    "warning": "#F59E0B",
    "error": "#EF4444",
    "info": "#0EA5E9",
    # Server identity
    "crm": "#3B82F6",
    "erp": "#10B981",
    "qa": "#8B5CF6",
    "analytics": "#F97316",
}

SERVER_COLOR_MAP = {
    "Salesforce CRM": TOKENS["crm"],
    "ERP System": TOKENS["erp"],
    "QA / Reliability": TOKENS["qa"],
    "Analytics (cross-system)": TOKENS["analytics"],
}

SERVER_ICON_MAP = {
    "Salesforce CRM": "☁️",
    "ERP System": "🏭",
    "QA / Reliability": "🔬",
    "Analytics (cross-system)": "📊",
}


# ---------------------------------------------------------------------------
# Global CSS — call once at the top of every page
# ---------------------------------------------------------------------------
def inject_global_css() -> None:
    st.markdown(
        f"""
        <style>
        /* --- Base typography & background --- */
        html, body, [class*="css"]  {{
            font-family: -apple-system, BlinkMacSystemFont, "Inter", "Segoe UI", Roboto, sans-serif;
        }}
        .stApp {{
            background: {TOKENS['bg']};
        }}
        .main .block-container {{
            padding-top: 1.4rem;
            padding-bottom: 4rem;
            max-width: 1400px;
        }}

        /* --- Sidebar styling --- */
        [data-testid="stSidebar"] {{
            background: {TOKENS['surface']};
            border-right: 1px solid {TOKENS['border']};
        }}
        [data-testid="stSidebar"] .block-container {{
            padding-top: 1rem;
        }}

        /* --- Headings --- */
        h1, h2, h3 {{
            color: {TOKENS['text']};
            font-weight: 700;
            letter-spacing: -0.02em;
        }}
        h1 {{ font-size: 1.75rem; }}
        h2 {{ font-size: 1.35rem; margin-top: 1.2rem; }}
        h3 {{ font-size: 1.1rem; }}

        /* --- Buttons --- */
        .stButton > button {{
            border-radius: 8px;
            border: 1px solid {TOKENS['border']};
            background: {TOKENS['surface']};
            color: {TOKENS['text']};
            font-weight: 500;
            transition: all 0.15s ease;
            padding: 0.45rem 0.9rem;
        }}
        .stButton > button:hover {{
            border-color: {TOKENS['primary']};
            color: {TOKENS['primary']};
        }}
        .stButton > button[kind="primary"] {{
            background: {TOKENS['primary']};
            color: white;
            border: none;
        }}
        .stButton > button[kind="primary"]:hover {{
            background: {TOKENS['primary_dark']};
            color: white;
        }}

        /* --- Inputs --- */
        .stTextInput input, .stTextArea textarea, .stSelectbox > div > div, .stNumberInput input {{
            border-radius: 8px !important;
            border: 1px solid {TOKENS['border']} !important;
        }}
        .stTextInput input:focus, .stTextArea textarea:focus {{
            border-color: {TOKENS['primary']} !important;
            box-shadow: 0 0 0 3px rgba(30, 64, 175, 0.1) !important;
        }}

        /* --- Tabs --- */
        .stTabs [data-baseweb="tab-list"] {{
            gap: 6px;
            border-bottom: 1px solid {TOKENS['border']};
        }}
        .stTabs [data-baseweb="tab"] {{
            border-radius: 8px 8px 0 0;
            padding: 8px 16px;
            font-weight: 500;
            color: {TOKENS['text_muted']};
        }}
        .stTabs [aria-selected="true"] {{
            color: {TOKENS['primary']} !important;
            font-weight: 600;
            background: rgba(30, 64, 175, 0.05);
        }}

        /* --- Metric --- */
        [data-testid="stMetric"] {{
            background: {TOKENS['surface']};
            border: 1px solid {TOKENS['border']};
            padding: 18px 22px;
            border-radius: 12px;
            box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
        }}
        [data-testid="stMetricLabel"] {{
            color: {TOKENS['text_muted']};
            font-weight: 500;
            font-size: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 0.06em;
        }}
        [data-testid="stMetricValue"] {{
            color: {TOKENS['text']};
            font-weight: 700;
        }}

        /* --- Cards --- */
        .ent-card {{
            background: {TOKENS['surface']};
            border: 1px solid {TOKENS['border']};
            border-radius: 12px;
            padding: 18px 20px;
            box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
        }}
        .ent-card-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
        }}
        .ent-card-title {{
            font-weight: 700;
            color: {TOKENS['text']};
            font-size: 0.95rem;
        }}
        .ent-card-subtitle {{
            color: {TOKENS['text_muted']};
            font-size: 0.8rem;
            margin-top: 2px;
        }}

        /* --- KPI card variant --- */
        .ent-kpi {{
            background: {TOKENS['surface']};
            border: 1px solid {TOKENS['border']};
            border-radius: 12px;
            padding: 16px 18px;
            box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
            position: relative;
            overflow: hidden;
        }}
        .ent-kpi-accent {{
            position: absolute;
            top: 0; left: 0;
            height: 100%; width: 4px;
            background: {TOKENS['primary']};
        }}
        .ent-kpi-label {{
            color: {TOKENS['text_muted']};
            font-size: 0.72rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            font-weight: 600;
        }}
        .ent-kpi-value {{
            color: {TOKENS['text']};
            font-size: 1.7rem;
            font-weight: 700;
            margin-top: 4px;
            line-height: 1.1;
        }}
        .ent-kpi-sub {{
            color: {TOKENS['text_subtle']};
            font-size: 0.78rem;
            margin-top: 6px;
        }}
        .ent-kpi-delta-pos {{ color: {TOKENS['success']}; font-weight: 600; }}
        .ent-kpi-delta-neg {{ color: {TOKENS['error']}; font-weight: 600; }}
        .ent-kpi-delta-flat {{ color: {TOKENS['text_muted']}; font-weight: 600; }}

        /* --- Status pill --- */
        .ent-pill {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 3px 10px;
            border-radius: 999px;
            font-size: 0.75rem;
            font-weight: 600;
            line-height: 1.3;
        }}
        .ent-pill-success {{ background: rgba(16, 185, 129, 0.12); color: {TOKENS['success']}; }}
        .ent-pill-warning {{ background: rgba(245, 158, 11, 0.15); color: #B45309; }}
        .ent-pill-error   {{ background: rgba(239, 68, 68, 0.12); color: {TOKENS['error']}; }}
        .ent-pill-info    {{ background: rgba(14, 165, 233, 0.12); color: {TOKENS['info']}; }}
        .ent-pill-neutral {{ background: {TOKENS['surface_alt']}; color: {TOKENS['text_muted']}; }}
        .ent-pill-dot {{
            width: 6px; height: 6px; border-radius: 50%;
            display: inline-block;
        }}

        /* --- Tool call card --- */
        .ent-toolcard {{
            background: {TOKENS['surface']};
            border: 1px solid {TOKENS['border']};
            border-left: 4px solid {TOKENS['primary']};
            border-radius: 8px;
            padding: 10px 14px;
            margin-bottom: 8px;
            font-family: "SF Mono", Menlo, Monaco, "Cascadia Code", monospace;
            font-size: 0.82rem;
        }}
        .ent-toolcard-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 10px;
            margin-bottom: 4px;
        }}
        .ent-toolcard-server {{
            font-weight: 700;
            color: {TOKENS['primary']};
        }}
        .ent-toolcard-name {{
            color: {TOKENS['text']};
            font-weight: 600;
        }}
        .ent-toolcard-time {{
            color: {TOKENS['text_subtle']};
            font-size: 0.72rem;
        }}
        .ent-toolcard-args {{
            color: {TOKENS['text_muted']};
            font-size: 0.78rem;
            word-break: break-all;
        }}

        /* --- Brand header --- */
        .ent-brand {{
            display: flex;
            align-items: center;
            gap: 10px;
            margin: 0 0 4px 0;
        }}
        .ent-brand-logo {{
            width: 32px; height: 32px;
            background: linear-gradient(135deg, {TOKENS['primary']}, {TOKENS['primary_light']});
            border-radius: 8px;
            display: flex; align-items: center; justify-content: center;
            color: white; font-weight: 700; font-size: 1.05rem;
        }}
        .ent-brand-title {{
            font-weight: 700; font-size: 1.05rem; color: {TOKENS['text']};
            line-height: 1;
        }}
        .ent-brand-subtitle {{
            font-size: 0.72rem; color: {TOKENS['text_muted']};
            margin-top: 2px;
        }}

        /* --- Section header strip --- */
        .ent-section {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 12px 0;
            margin: 8px 0 12px 0;
            border-bottom: 1px solid {TOKENS['border']};
        }}
        .ent-section-title {{
            font-weight: 700;
            font-size: 1.15rem;
            color: {TOKENS['text']};
        }}
        .ent-section-eyebrow {{
            font-size: 0.7rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: {TOKENS['text_muted']};
            font-weight: 600;
        }}

        /* --- Chat bubbles --- */
        [data-testid="stChatMessage"] {{
            background: transparent !important;
            padding: 8px 0 !important;
        }}

        /* --- Hide default streamlit chrome --- */
        #MainMenu {{ visibility: hidden; }}
        footer {{ visibility: hidden; }}
        header[data-testid="stHeader"] {{
            background: transparent;
            height: 0;
        }}

        /* --- Dataframe polish --- */
        [data-testid="stDataFrame"] {{
            border: 1px solid {TOKENS['border']};
            border-radius: 8px;
        }}

        /* --- Expander --- */
        .streamlit-expanderHeader {{
            background: {TOKENS['surface_alt']};
            border-radius: 6px;
            font-weight: 600;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )
