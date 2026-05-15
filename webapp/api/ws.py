"""WebSocket endpoint that streams the agent run live.

Protocol:
  Client → Server:
    { "action": "ask", "question": "...", "model": "...", "max_iterations": 10 }
  Server → Client (one JSON line per event):
    { "type": "run_start", "question": "...", ... }
    { "type": "iteration_start", "iteration": 1 }
    { "type": "model_response", "iteration": 1, "duration_s": 2.3, "text": "...",
      "tool_calls_planned": [...], "stop_reason": "tool_use", "tokens": {...} }
    { "type": "tool_call", "iteration": 1, "tool_name": "...", "server_label": "...",
      "arguments": {...} }
    { "type": "tool_result", "iteration": 1, "tool_name": "...",
      "duration_s": 0.04, "result_preview": "...", "result_size": 1234 }
    { "type": "final", "answer": "...", "iterations": 2, "duration_s": 14.2 }
    { "type": "error", "error": "..." }
"""
from __future__ import annotations

import json
import logging
import os

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

log = logging.getLogger("webapp.ws")


def register_ws_routes(app: FastAPI) -> None:

    @app.websocket("/ws/agent")
    async def agent_ws(ws: WebSocket):
        await ws.accept()
        runner = ws.app.state.runner

        if not os.environ.get("ANTHROPIC_API_KEY"):
            await ws.send_json({
                "type": "error",
                "error": "ANTHROPIC_API_KEY is not set. Add it to ~/.env or the project .env file.",
            })
            await ws.close()
            return

        try:
            while True:
                raw = await ws.receive_text()
                try:
                    msg = json.loads(raw)
                except Exception:
                    await ws.send_json({"type": "error", "error": "Invalid JSON"})
                    continue
                action = msg.get("action") or "ask"

                if action == "ping":
                    await ws.send_json({"type": "pong"})
                    continue

                if action == "ask":
                    question = (msg.get("question") or "").strip()
                    if not question:
                        await ws.send_json({"type": "error", "error": "Missing question"})
                        continue
                    model = msg.get("model") or os.environ.get("CRM_DEMO_MODEL", "claude-sonnet-4-5")
                    max_iter = int(msg.get("max_iterations") or 10)

                    async def emit(ev):
                        try:
                            await ws.send_json(ev)
                        except Exception as e:
                            log.warning("WS emit failed: %s", e)

                    try:
                        await runner.ask(question, on_event=emit, model=model, max_iterations=max_iter)
                    except Exception as exc:
                        log.exception("Agent run failed")
                        await ws.send_json({"type": "error", "error": str(exc)})
                else:
                    await ws.send_json({"type": "error", "error": f"Unknown action: {action}"})
        except WebSocketDisconnect:
            log.info("WS client disconnected")
        except Exception as e:
            log.exception("WS error")
            try:
                await ws.send_json({"type": "error", "error": str(e)})
            except Exception:
                pass
