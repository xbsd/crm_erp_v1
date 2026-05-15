"""AI Assistant page — multi-turn conversational interface with live tool trace."""
from __future__ import annotations

import asyncio
import json
import sys
import time
import uuid
from pathlib import Path
from typing import Any

import streamlit as st

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent.mcp_client import MultiMCPClient
from agent.orchestrator import run_agent
from tests.use_cases import USE_CASES
from ui.theme import SERVER_COLOR_MAP, TOKENS
from ui.widgets import (
    empty_state,
    section_header,
    status_pill,
    tool_call_card,
)

# ---------------------------------------------------------------------------
# Session state initialization
# ---------------------------------------------------------------------------
if "conversations" not in st.session_state:
    st.session_state.conversations = []
if "current_conv_id" not in st.session_state:
    st.session_state.current_conv_id = None
# show_trace_panel is owned by the checkbox widget; don't pre-seed.


def _new_conversation(seed_prompt: str | None = None) -> str:
    cid = uuid.uuid4().hex[:8]
    conv = {
        "id": cid,
        "title": seed_prompt[:60] if seed_prompt else "New conversation",
        "created_at": time.time(),
        "messages": [],   # each: {role, content, trace, iterations, duration}
        "pending_prompt": seed_prompt,
    }
    st.session_state.conversations.insert(0, conv)
    st.session_state.current_conv_id = cid
    return cid


def _get_current_conv() -> dict | None:
    cid = st.session_state.current_conv_id
    if cid is None:
        return None
    for c in st.session_state.conversations:
        if c["id"] == cid:
            return c
    return None


# ---------------------------------------------------------------------------
# Sidebar — Conversation history + suggested prompts + settings
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("---")
    st.markdown("**🤖 AI Assistant**")
    if st.button("✨ New conversation", use_container_width=True, type="primary"):
        _new_conversation()
        st.rerun()

    persona = st.selectbox(
        "Persona",
        ["Executive", "VP Sales", "Sales Manager", "Sales Engineer"],
        index=["Executive", "VP Sales", "Sales Manager", "Sales Engineer"].index(st.session_state.get("persona", "Executive")),
        key="assist_persona",
    )
    st.session_state.persona = persona

    with st.expander("⚙️ Model & limits", expanded=False):
        model = st.selectbox(
            "Model",
            ["claude-sonnet-4-5", "claude-opus-4-7", "claude-haiku-4-5-20251001"],
            index=["claude-sonnet-4-5", "claude-opus-4-7", "claude-haiku-4-5-20251001"].index(
                st.session_state.get("model", "claude-sonnet-4-5")
            ),
            help="Sonnet 4.5 is the default — strong tool-use, fast.",
        )
        st.session_state.model = model
        max_iter = st.slider("Max agent iterations", 2, 15, st.session_state.get("max_iterations", 10))
        st.session_state.max_iterations = max_iter
        st.checkbox("Show tool-call trace panel", value=True, key="show_trace_panel")

    st.markdown("---")
    st.markdown("**💡 Suggested prompts**")
    # Filter prompts by persona
    persona_filter = "Executive" if persona == "Executive" else "Sales"
    for case in USE_CASES:
        if case["audience"] != persona_filter and persona != "Executive":
            continue
        if st.button(f"› {case['title']}", key=f"sg_{case['id']}", use_container_width=True):
            _new_conversation(case["question"])
            st.rerun()

    st.markdown("---")
    st.markdown("**🗂️ Recent conversations**")
    if not st.session_state.conversations:
        st.caption("No conversations yet — start a new one above.")
    else:
        for conv in st.session_state.conversations[:10]:
            active = conv["id"] == st.session_state.current_conv_id
            if st.button(
                f"💬 {conv['title'][:32]}",
                key=f"convopen_{conv['id']}",
                use_container_width=True,
                type="primary" if active else "secondary",
            ):
                st.session_state.current_conv_id = conv["id"]
                st.rerun()


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
section_header(
    "AI Assistant",
    "Ask anything across CRM · ERP · QA",
    action=f"Model: {st.session_state.model}",
)

# Tool-server status strip
strip_cols = st.columns(5)
servers_info = [
    ("Salesforce CRM", "10 tools", "success"),
    ("ERP System", "9 tools", "success"),
    ("QA / Reliability", "7 tools", "success"),
    ("Analytics (cross-system)", "7 tools", "success"),
]
strip_cols[0].markdown(
    f"<div style='font-size:0.8rem; color:{TOKENS['text_muted']}; padding-top:6px;'>Connected servers</div>",
    unsafe_allow_html=True,
)
for i, (name, count, status) in enumerate(servers_info):
    color = SERVER_COLOR_MAP.get(name, TOKENS["primary"])
    icon = {"Salesforce CRM": "☁️", "ERP System": "🏭", "QA / Reliability": "🔬", "Analytics (cross-system)": "📊"}.get(name, "🔧")
    strip_cols[i + 1].markdown(
        f"<div style='display:flex;align-items:center;gap:8px;padding:6px 10px;background:white;border:1px solid {TOKENS['border']};border-radius:8px;'>"
        f"<span style='font-size:1.1rem'>{icon}</span>"
        f"<div style='flex:1'>"
        f"<div style='font-size:0.78rem;font-weight:600;color:{color};'>{name}</div>"
        f"<div style='font-size:0.72rem;color:{TOKENS['text_muted']};'>{count} · "
        + status_pill("online", "success") +
        f"</div></div></div>",
        unsafe_allow_html=True,
    )

st.markdown("&nbsp;")

# ---------------------------------------------------------------------------
# Layout: main chat (left) + trace panel (right)
# ---------------------------------------------------------------------------
conv = _get_current_conv()

if conv is None:
    empty_state(
        "Start a conversation",
        "Pick a suggested prompt on the left, or click ‘New conversation’ and type a question.",
        icon="🤖",
    )
    st.stop()

if st.session_state.show_trace_panel:
    chat_col, trace_col = st.columns([3, 2])
else:
    chat_col = st.container()
    trace_col = None


# ---------------------------------------------------------------------------
# Render conversation thread (chat_col)
# ---------------------------------------------------------------------------
def _render_assistant_message(msg: dict, container) -> None:
    container.markdown(msg["content"])
    if msg.get("trace"):
        with container.expander(
            f"🔧 {len(msg['trace'])} tool call{'s' if len(msg['trace']) != 1 else ''}  ·  "
            f"{msg.get('iterations', 1)} iteration{'s' if msg.get('iterations', 1) != 1 else ''}  ·  "
            f"{msg.get('duration', 0):.1f}s",
            expanded=False,
        ):
            for t in msg["trace"]:
                tool_call_card(
                    t["server_label"], t["tool_name"], t["arguments"],
                    duration_s=t["duration_s"], result_preview=t.get("result_preview"),
                    iteration=t.get("iteration"),
                )


with chat_col:
    if not conv["messages"] and not conv.get("pending_prompt"):
        empty_state(
            f"How can I help, {st.session_state.persona}?",
            "Ask about accounts, opportunities, revenue patterns, product reliability, or anything that needs data from CRM, ERP, or QA.",
            icon="✨",
        )
    for msg in conv["messages"]:
        if msg["role"] == "user":
            with st.chat_message("user", avatar="👤"):
                st.markdown(msg["content"])
        else:
            with st.chat_message("assistant", avatar="🤖"):
                _render_assistant_message(msg, st)


# ---------------------------------------------------------------------------
# Agent runner — async helper
# ---------------------------------------------------------------------------
def _run_agent_sync(question: str, live_callback) -> dict:
    async def _go() -> dict:
        async with MultiMCPClient() as client:
            result = await run_agent(
                client, question,
                model=st.session_state.model,
                max_iterations=st.session_state.max_iterations,
                on_step=live_callback,
            )
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
                "duration": result.total_seconds,
            }
    return asyncio.run(_go())


# ---------------------------------------------------------------------------
# Handle a pending or new user prompt
# ---------------------------------------------------------------------------
prompt_to_run = conv.pop("pending_prompt", None)
chat_input = chat_col.chat_input(
    f"Ask the {st.session_state.persona}-grade AI anything…",
    key=f"chat_in_{conv['id']}",
)
if chat_input:
    prompt_to_run = chat_input

if prompt_to_run:
    # Update conversation title to first prompt
    if not conv["messages"]:
        conv["title"] = prompt_to_run[:60]

    conv["messages"].append({"role": "user", "content": prompt_to_run})

    # Render user bubble immediately
    with chat_col:
        with st.chat_message("user", avatar="👤"):
            st.markdown(prompt_to_run)

    # Run agent with live status updates
    trace_buffer: list[dict] = []
    activity_log: list[str] = []

    def on_step(event: str, payload: dict) -> None:
        if event == "tool_call":
            activity_log.append(
                f"→ {payload['server_label']} :: {payload['tool_name']}"
            )
        elif event == "tool_result":
            trace_buffer.append({
                "tool_name": payload["tool_name"],
                "duration_s": payload["duration_s"],
                "result_preview": payload.get("result_preview", ""),
            })

    with chat_col:
        with st.chat_message("assistant", avatar="🤖"):
            with st.status("🧠 Thinking…", expanded=True) as status:
                progress_box = st.empty()

                # Capture into an updated status block
                def live_cb(event: str, payload: dict) -> None:
                    on_step(event, payload)
                    if event == "tool_call":
                        status.update(label=f"📡 Calling {payload['server_label']} → {payload['tool_name']}")
                        progress_box.markdown(
                            "\n".join(f"- {a}" for a in activity_log[-6:])
                        )
                    elif event == "tool_result":
                        status.update(label=f"✓ {payload['tool_name']} returned in {payload['duration_s']:.2f}s")
                    elif event == "final":
                        status.update(label="✨ Composing answer…")

                try:
                    result = _run_agent_sync(prompt_to_run, live_cb)
                    status.update(
                        label=f"✅ Answered in {result['duration']:.1f}s  ·  {result['iterations']} iterations  ·  {len(result['trace'])} tool calls",
                        state="complete",
                    )
                except Exception as exc:
                    st.error(f"Agent error: {exc}")
                    status.update(label="❌ Agent failed", state="error")
                    st.stop()

            # Now render the full answer markdown
            st.markdown(result["final_answer"])
            # Inline tool trace expander
            if result["trace"]:
                with st.expander(
                    f"🔧 {len(result['trace'])} tool call{'s' if len(result['trace']) != 1 else ''}  ·  "
                    f"{result['iterations']} iteration{'s' if result['iterations'] != 1 else ''}  ·  "
                    f"{result['duration']:.1f}s",
                    expanded=False,
                ):
                    for t in result["trace"]:
                        tool_call_card(
                            t["server_label"], t["tool_name"], t["arguments"],
                            duration_s=t["duration_s"], result_preview=t.get("result_preview"),
                            iteration=t.get("iteration"),
                        )

    # Save message to conversation
    conv["messages"].append({
        "role": "assistant",
        "content": result["final_answer"],
        "trace": result["trace"],
        "iterations": result["iterations"],
        "duration": result["duration"],
    })

    # Update activity log
    for entry in activity_log:
        st.session_state.agent_activity_log.append(
            f"[{time.strftime('%H:%M:%S')}] {entry}"
        )
    st.rerun()


# ---------------------------------------------------------------------------
# Right panel: live trace + system info
# ---------------------------------------------------------------------------
if trace_col is not None:
    with trace_col:
        st.markdown(
            "<div class='ent-card'>"
            "<div class='ent-card-header'>"
            "<div><div class='ent-card-title'>🔍 Conversation insights</div>"
            "<div class='ent-card-subtitle'>What the agent did, summarized</div></div></div>",
            unsafe_allow_html=True,
        )
        # Latest assistant message's trace
        latest_assistant = next(
            (m for m in reversed(conv["messages"]) if m["role"] == "assistant"),
            None,
        )
        if latest_assistant and latest_assistant.get("trace"):
            tr = latest_assistant["trace"]
            # Stats
            servers_hit = sorted({t["server_label"] for t in tr})
            st.markdown(
                f"<div style='display:flex;flex-wrap:wrap;gap:6px;margin-bottom:10px;'>"
                + "".join(
                    f"<span class='ent-pill ent-pill-info'>{s}</span>"
                    for s in servers_hit
                ) + "</div>",
                unsafe_allow_html=True,
            )
            st.markdown(
                f"<div style='color:{TOKENS['text_muted']};font-size:0.85rem;margin-bottom:10px;'>"
                f"<b>{len(tr)}</b> tool call{'s' if len(tr) != 1 else ''} · "
                f"<b>{latest_assistant.get('iterations', 0)}</b> iteration{'s' if latest_assistant.get('iterations', 0) != 1 else ''} · "
                f"<b>{latest_assistant.get('duration', 0):.1f}s</b> elapsed"
                f"</div>",
                unsafe_allow_html=True,
            )

            # Compact tool trace
            st.markdown("**Tool sequence**")
            for i, t in enumerate(tr, 1):
                color = SERVER_COLOR_MAP.get(t["server_label"], TOKENS["primary"])
                st.markdown(
                    f"<div style='padding:8px 12px;background:white;border:1px solid {TOKENS['border']};border-left:3px solid {color};border-radius:6px;margin-bottom:6px;font-size:0.82rem;'>"
                    f"<div style='font-weight:600;color:{color};'>{i}. {t['server_label']}</div>"
                    f"<div style='font-family:monospace;color:{TOKENS['text']};margin-top:2px;'>{t['tool_name']}</div>"
                    f"<div style='color:{TOKENS['text_muted']};font-size:0.72rem;margin-top:2px;'>"
                    f"iter {t['iteration']} · {t['duration_s'] * 1000:.0f} ms</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
        else:
            st.caption("Ask something to see live tool calls here.")
        st.markdown("</div>", unsafe_allow_html=True)

        # Suggested follow-ups
        st.markdown("&nbsp;")
        st.markdown(
            "<div class='ent-card'>"
            "<div class='ent-card-header'>"
            "<div><div class='ent-card-title'>💡 Suggested follow-ups</div></div></div>",
            unsafe_allow_html=True,
        )
        followups = [
            "Drill into the top customer by revenue",
            "Compare with Q4 2025 results",
            "Show me the at-risk accounts",
            "Generate the executive deck",
        ]
        for f in followups:
            if st.button(f"› {f}", key=f"fu_{f}", use_container_width=True):
                # Queue as pending prompt
                conv["pending_prompt"] = f
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
