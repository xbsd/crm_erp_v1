"""Long-lived agent runner that owns a single MultiMCPClient.

Streams every agent step (plan, tool_call, tool_result, final) to a queue so
the WebSocket layer can broadcast it as JSON. This is the visible "agent-to-
agent" communication: orchestrator (Claude) ⇆ tools ⇆ MCP servers ⇆ DBs.
"""
from __future__ import annotations

import asyncio
import json
import os
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, Awaitable, Callable

import anthropic

from agent.mcp_client import MultiMCPClient, ToolBinding
from agent.orchestrator import SYSTEM_PROMPT, MODEL, MAX_ITERATIONS

EventCallback = Callable[[dict[str, Any]], Awaitable[None]]


@dataclass
class RunState:
    run_id: str
    question: str
    model: str
    started_at: float
    finished_at: float | None = None
    final_answer: str = ""
    iterations: int = 0
    events: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None


def _tools_for_anthropic(bindings: list[ToolBinding]) -> list[dict]:
    return [
        {
            "name": b.name,
            "description": f"[{b.server_label}] {b.description}",
            "input_schema": b.input_schema,
        }
        for b in bindings
    ]


class AgentRunner:
    """Owns the MCP connection and runs queries against it.

    Use as an async context manager; one instance per FastAPI app lifetime.
    """

    def __init__(self) -> None:
        self.client: MultiMCPClient | None = None
        self._client_cm: MultiMCPClient | None = None
        self._lock = asyncio.Lock()
        self.runs: dict[str, RunState] = {}

    async def __aenter__(self) -> "AgentRunner":
        self._client_cm = MultiMCPClient()
        self.client = await self._client_cm.__aenter__()
        return self

    async def __aexit__(self, *exc: Any) -> None:
        if self._client_cm is not None:
            await self._client_cm.__aexit__(*exc)
            self._client_cm = None
            self.client = None

    def tool_catalog(self) -> list[dict[str, Any]]:
        assert self.client is not None
        return [
            {
                "name": b.name,
                "server_name": b.server_name,
                "server_label": b.server_label,
                "description": b.description,
                "input_schema": b.input_schema,
            }
            for b in self.client.tool_bindings
        ]

    def server_summary(self) -> list[dict[str, Any]]:
        assert self.client is not None
        servers: dict[str, dict[str, Any]] = {}
        for b in self.client.tool_bindings:
            s = servers.setdefault(b.server_name, {
                "name": b.server_name, "label": b.server_label, "tools": 0,
            })
            s["tools"] += 1
        return list(servers.values())

    async def ask(
        self,
        question: str,
        on_event: EventCallback,
        model: str = MODEL,
        max_iterations: int = MAX_ITERATIONS,
    ) -> RunState:
        """Run the agent loop, emitting structured events to `on_event`."""
        assert self.client is not None
        bindings = self.client.tool_bindings
        tools = _tools_for_anthropic(bindings)
        anthropic_client = anthropic.Anthropic()
        run_id = uuid.uuid4().hex[:12]
        state = RunState(run_id=run_id, question=question, model=model, started_at=time.time())
        self.runs[run_id] = state

        async def emit(event_type: str, payload: dict[str, Any]) -> None:
            ev = {"type": event_type, "run_id": run_id, "ts": time.time(), **payload}
            state.events.append(ev)
            try:
                await on_event(ev)
            except Exception:
                pass

        await emit("run_start", {
            "question": question, "model": model,
            "tool_count": len(bindings),
            "servers": self.server_summary(),
        })

        messages: list[dict] = [{"role": "user", "content": question}]
        try:
            for iteration in range(1, max_iterations + 1):
                state.iterations = iteration
                await emit("iteration_start", {"iteration": iteration})

                # Anthropic call (blocking) — run in thread so we don't block the loop
                t0 = time.time()
                response = await asyncio.to_thread(
                    anthropic_client.messages.create,
                    model=model,
                    max_tokens=4096,
                    system=SYSTEM_PROMPT,
                    tools=tools,
                    messages=messages,
                )
                think_s = time.time() - t0

                tool_uses = [b for b in response.content if b.type == "tool_use"]
                text_blocks = [b for b in response.content if b.type == "text"]
                text_chunk = "\n".join(b.text for b in text_blocks).strip()

                await emit("model_response", {
                    "iteration": iteration,
                    "duration_s": round(think_s, 2),
                    "text": text_chunk,
                    "tool_calls_planned": [
                        {"tool_name": tu.name, "arguments": tu.input} for tu in tool_uses
                    ],
                    "stop_reason": response.stop_reason,
                    "tokens": {
                        "input": getattr(response.usage, "input_tokens", 0),
                        "output": getattr(response.usage, "output_tokens", 0),
                    },
                })

                if response.stop_reason == "end_turn" or not tool_uses:
                    state.final_answer = text_chunk
                    state.finished_at = time.time()
                    await emit("final", {
                        "answer": text_chunk,
                        "iterations": iteration,
                        "duration_s": round(state.finished_at - state.started_at, 2),
                    })
                    return state

                messages.append({"role": "assistant", "content": response.content})

                tool_result_blocks: list[dict[str, Any]] = []
                for tu in tool_uses:
                    binding = self.client.get_binding(tu.name)
                    server_label = binding.server_label if binding else "unknown"
                    server_name = binding.server_name if binding else "unknown"
                    await emit("tool_call", {
                        "iteration": iteration,
                        "tool_name": tu.name,
                        "server_label": server_label,
                        "server_name": server_name,
                        "arguments": tu.input,
                    })
                    t0 = time.time()
                    try:
                        result_text = await self.client.call_tool(tu.name, tu.input)
                        error = None
                    except Exception as exc:
                        result_text = json.dumps({"error": str(exc)})
                        error = str(exc)
                    elapsed = time.time() - t0
                    preview = result_text if len(result_text) < 1200 else result_text[:1200] + "…"
                    await emit("tool_result", {
                        "iteration": iteration,
                        "tool_name": tu.name,
                        "server_label": server_label,
                        "server_name": server_name,
                        "duration_s": round(elapsed, 3),
                        "result_preview": preview,
                        "result_size": len(result_text),
                        "error": error,
                    })
                    tool_result_blocks.append({
                        "type": "tool_result",
                        "tool_use_id": tu.id,
                        "content": result_text,
                    })

                messages.append({"role": "user", "content": tool_result_blocks})

            state.error = "Max iterations exceeded"
            state.finished_at = time.time()
            await emit("error", {"error": state.error})
        except Exception as exc:
            state.error = str(exc)
            state.finished_at = time.time()
            await emit("error", {"error": str(exc)})

        return state
