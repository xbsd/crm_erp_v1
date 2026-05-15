"""Reusable enterprise UI widgets."""
from __future__ import annotations

import html
import json
from typing import Any

import streamlit as st

from ui.theme import SERVER_COLOR_MAP, SERVER_ICON_MAP, TOKENS


# ---------------------------------------------------------------------------
# Brand header (sidebar top)
# ---------------------------------------------------------------------------
def brand_header(title: str = "Enterprise AI", subtitle: str = "MCP Workbench") -> None:
    st.markdown(
        f"""
        <div class="ent-brand">
          <div class="ent-brand-logo">EA</div>
          <div>
            <div class="ent-brand-title">{html.escape(title)}</div>
            <div class="ent-brand-subtitle">{html.escape(subtitle)}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Section header
# ---------------------------------------------------------------------------
def section_header(eyebrow: str, title: str, action: str | None = None) -> None:
    action_html = f'<span class="ent-pill ent-pill-info">{html.escape(action)}</span>' if action else ""
    st.markdown(
        f"""
        <div class="ent-section">
          <div>
            <div class="ent-section-eyebrow">{html.escape(eyebrow)}</div>
            <div class="ent-section-title">{html.escape(title)}</div>
          </div>
          {action_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# KPI card with optional delta
# ---------------------------------------------------------------------------
def kpi_card(
    label: str,
    value: str,
    delta: str | None = None,
    delta_sign: int = 0,            # 1 positive, -1 negative, 0 flat
    sub: str | None = None,
    accent_color: str = TOKENS["primary"],
) -> None:
    delta_html = ""
    if delta is not None:
        cls = "ent-kpi-delta-pos" if delta_sign > 0 else ("ent-kpi-delta-neg" if delta_sign < 0 else "ent-kpi-delta-flat")
        arrow = "↑" if delta_sign > 0 else ("↓" if delta_sign < 0 else "→")
        delta_html = f'<span class="{cls}">{arrow} {html.escape(delta)}</span>'
    sub_html = f'<div class="ent-kpi-sub">{html.escape(sub)} &nbsp; {delta_html}</div>' if sub else (f'<div class="ent-kpi-sub">{delta_html}</div>' if delta else "")
    st.markdown(
        f"""
        <div class="ent-kpi">
          <div class="ent-kpi-accent" style="background: {accent_color};"></div>
          <div class="ent-kpi-label">{html.escape(label)}</div>
          <div class="ent-kpi-value">{html.escape(value)}</div>
          {sub_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Status pill
# ---------------------------------------------------------------------------
def status_pill(text: str, status: str = "neutral") -> str:
    """Return HTML for an inline status pill. Status: success/warning/error/info/neutral."""
    return f'<span class="ent-pill ent-pill-{status}"><span class="ent-pill-dot" style="background: currentColor;"></span>{html.escape(text)}</span>'


# ---------------------------------------------------------------------------
# Tool call card
# ---------------------------------------------------------------------------
def tool_call_card(
    server_label: str,
    tool_name: str,
    arguments: dict,
    duration_s: float | None = None,
    result_preview: str | None = None,
    iteration: int | None = None,
    show_result: bool = True,
) -> None:
    color = SERVER_COLOR_MAP.get(server_label, TOKENS["primary"])
    icon = SERVER_ICON_MAP.get(server_label, "🔧")
    args_str = ", ".join(f"{k}={v!r}" for k, v in (arguments or {}).items())
    if len(args_str) > 160:
        args_str = args_str[:157] + "..."
    iter_html = f'&nbsp;·&nbsp;iter {iteration}' if iteration is not None else ""
    time_html = f'{duration_s * 1000:.0f} ms' if duration_s is not None else ""

    st.markdown(
        f"""
        <div class="ent-toolcard" style="border-left-color: {color};">
          <div class="ent-toolcard-header">
            <span>
              {icon} <span class="ent-toolcard-server" style="color: {color};">{html.escape(server_label)}</span>
              &nbsp;::&nbsp;<span class="ent-toolcard-name">{html.escape(tool_name)}</span>
            </span>
            <span class="ent-toolcard-time">{time_html}{iter_html}</span>
          </div>
          <div class="ent-toolcard-args">{html.escape(args_str) if args_str else "<em>no arguments</em>"}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if show_result and result_preview:
        with st.expander("View result", expanded=False):
            try:
                parsed = json.loads(result_preview.rstrip(".") if result_preview.endswith("...") else result_preview)
                st.json(parsed, expanded=False)
            except Exception:
                st.code(result_preview[:2000], language="json")


# ---------------------------------------------------------------------------
# Account card (Customer 360 header)
# ---------------------------------------------------------------------------
def account_card(account: dict, extra_kpis: list[tuple[str, str]] | None = None) -> None:
    industry = account.get("industry", "")
    segment = account.get("segment", "")
    country = account.get("billing_country", account.get("country", ""))
    revenue = account.get("annual_revenue", 0) or 0
    initials = "".join([w[0] for w in (account.get("name") or "??").split()[:2]]).upper()
    key_pill = (
        '<span class="ent-pill ent-pill-warning">⭐ KEY ACCOUNT</span>'
        if account.get("is_key_account") else
        '<span class="ent-pill ent-pill-neutral">Standard</span>'
    )

    kpi_html = ""
    if extra_kpis:
        kpi_html = '<div style="display: flex; gap: 24px; margin-top: 14px;">'
        for label, value in extra_kpis:
            kpi_html += (
                f'<div><div class="ent-kpi-label">{html.escape(label)}</div>'
                f'<div style="font-size: 1.2rem; font-weight: 700; color: {TOKENS["text"]};">{html.escape(value)}</div></div>'
            )
        kpi_html += "</div>"

    st.markdown(
        f"""
        <div class="ent-card" style="display: flex; flex-direction: column; gap: 8px;">
          <div style="display: flex; gap: 14px; align-items: center;">
            <div style="width:56px;height:56px;background:linear-gradient(135deg,{TOKENS['primary']},{TOKENS['primary_light']});color:white;display:flex;align-items:center;justify-content:center;border-radius:12px;font-weight:700;font-size:1.2rem;">{html.escape(initials)}</div>
            <div style="flex: 1;">
              <div style="display: flex; gap: 10px; align-items: baseline;">
                <div style="font-weight: 700; font-size: 1.3rem; color: {TOKENS['text']};">{html.escape(account.get('name') or '')}</div>
                {key_pill}
              </div>
              <div style="color: {TOKENS['text_muted']}; font-size: 0.85rem; margin-top: 2px;">
                {html.escape(industry)} &nbsp;·&nbsp; {html.escape(segment)} &nbsp;·&nbsp; {html.escape(country)}
                &nbsp;·&nbsp; Annual revenue ${revenue/1e9:.1f} B
              </div>
            </div>
          </div>
          {kpi_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Server status row (for the System Health page)
# ---------------------------------------------------------------------------
def server_status_card(
    server_label: str,
    tool_count: int,
    db_rows: int | None = None,
    status: str = "success",
    status_text: str = "Connected",
) -> None:
    color = SERVER_COLOR_MAP.get(server_label, TOKENS["primary"])
    icon = SERVER_ICON_MAP.get(server_label, "🔧")
    db_html = f"<div class='ent-kpi-sub'>{db_rows:,} rows in primary DB</div>" if db_rows is not None else ""
    pill = status_pill(status_text, status)
    st.markdown(
        f"""
        <div class="ent-kpi" style="height: 100%;">
          <div class="ent-kpi-accent" style="background: {color};"></div>
          <div style="display: flex; justify-content: space-between; align-items: flex-start;">
            <div>
              <div class="ent-kpi-label">{icon}&nbsp;&nbsp;MCP Server</div>
              <div style="font-size: 1.1rem; font-weight: 700; color: {TOKENS['text']}; margin-top: 4px;">{html.escape(server_label)}</div>
            </div>
            <div>{pill}</div>
          </div>
          <div class="ent-kpi-sub" style="margin-top: 14px;">
            <strong>{tool_count}</strong> tools exposed
          </div>
          {db_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Insight card — for displaying narrative insights with optional icon
# ---------------------------------------------------------------------------
def insight_card(title: str, body: str, icon: str = "💡", tone: str = "info") -> None:
    color_map = {
        "info": TOKENS["info"], "success": TOKENS["success"],
        "warning": "#B45309", "error": TOKENS["error"], "neutral": TOKENS["text_muted"],
    }
    border = color_map.get(tone, TOKENS["info"])
    st.markdown(
        f"""
        <div class="ent-card" style="border-left: 4px solid {border};">
          <div class="ent-card-header">
            <div class="ent-card-title">{icon} &nbsp; {html.escape(title)}</div>
          </div>
          <div style="color: {TOKENS['text']}; font-size: 0.92rem; line-height: 1.5;">{body}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Conversation list item (sidebar of AI Assistant)
# ---------------------------------------------------------------------------
def conversation_list_item(conv_id: str, title: str, last_message: str, active: bool = False) -> bool:
    """Renders a clickable conversation row. Returns True if clicked this render."""
    border = TOKENS["primary"] if active else TOKENS["border"]
    bg = "rgba(30, 64, 175, 0.06)" if active else TOKENS["surface"]
    button = st.button(
        f"💬 {title[:38]}{'…' if len(title) > 38 else ''}",
        key=f"convbtn_{conv_id}",
        use_container_width=True,
        type="primary" if active else "secondary",
    )
    return button


# ---------------------------------------------------------------------------
# Empty state
# ---------------------------------------------------------------------------
def empty_state(title: str, subtitle: str, icon: str = "🤖") -> None:
    st.markdown(
        f"""
        <div style="text-align: center; padding: 60px 20px; color: {TOKENS['text_muted']};">
          <div style="font-size: 3rem; margin-bottom: 10px;">{icon}</div>
          <div style="font-size: 1.1rem; font-weight: 600; color: {TOKENS['text']}; margin-bottom: 6px;">{html.escape(title)}</div>
          <div style="font-size: 0.9rem;">{html.escape(subtitle)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------
def format_money(amount: float, compact: bool = True) -> str:
    if amount is None:
        return "—"
    sign = "-" if amount < 0 else ""
    a = abs(amount)
    if compact:
        if a >= 1e9: return f"{sign}${a / 1e9:.2f}B"
        if a >= 1e6: return f"{sign}${a / 1e6:.2f}M"
        if a >= 1e3: return f"{sign}${a / 1e3:.1f}K"
    return f"{sign}${a:,.0f}"


def format_pct(pct: float | None) -> str:
    if pct is None:
        return "—"
    return f"{pct:+.1f}%"


def delta_sign(delta: float | None) -> int:
    if delta is None: return 0
    if delta > 0:    return 1
    if delta < 0:    return -1
    return 0
