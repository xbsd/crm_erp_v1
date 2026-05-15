"""Agentic AI orchestrator using Anthropic Claude + MCP tools.

Connects Claude (with extended thinking turned off for snappier demos) to the
four MCP servers (CRM, ERP, QA, Analytics) and lets it answer
natural-language questions by calling tools.  Every tool invocation is
captured in a structured trace so the UI can show which system answered
each part of a question — the core of the demo.
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from typing import Any

import anthropic

from agent.mcp_client import MultiMCPClient, ToolBinding

MODEL = os.environ.get("CRM_DEMO_MODEL", "claude-sonnet-4-5")
MAX_ITERATIONS = 10  # max agent loop turns

SYSTEM_PROMPT = """You are an enterprise AI assistant for a semiconductor / electronic components company. \
You answer executive and sales questions by orchestrating tool calls across four backend systems:

  1. Salesforce CRM (front office) — leads, accounts, opportunities, products, quotes
  2. ERP System (back office) — customers, sales orders, invoices, payments, revenue
  3. QA / Reliability Systems — test results, MTBF/MTTR, failures, customer returns, compliance, reliability scores
  4. Analytics (cross-system joins) — top key accounts, YoY revenue patterns, quote→revenue conversion, \
product recommendations that blend design fit with QA reliability data, quarterly executive updates.

Use the tools to retrieve the data you need.  Prefer the **analytics_** tools for cross-system questions \
(top key accounts, YoY revenue change, quote→revenue conversion, executive updates, product fit + reliability).  \
Use single-system tools for drill-down details.

When you've gathered enough data, write a clear, concise executive-grade response that:
  - States the answer first with the most important numbers
  - Calls out which system(s) the data came from
  - Lists the top 3-10 items with key metrics
  - Notes any caveats or follow-ups worth investigating

Today's date is 2026-05-15.  The fiscal year aligns with the calendar year (Jan-Dec).  \
Use ISO date format YYYY-MM-DD for any date arguments.
"""


@dataclass
class ToolCallTrace:
    tool_name: str
    server_label: str
    arguments: dict
    result_preview: str          # first ~600 chars of the JSON result
    duration_s: float
    iteration: int


@dataclass
class AgentResult:
    question: str
    final_answer: str
    trace: list[ToolCallTrace] = field(default_factory=list)
    iterations: int = 0
    total_seconds: float = 0.0
    raw_result: Any = None


def _tools_for_anthropic(bindings: list[ToolBinding]) -> list[dict]:
    """Convert MCP tool bindings into Anthropic-tool-format."""
    return [
        {
            "name": b.name,
            "description": f"[{b.server_label}] {b.description}",
            "input_schema": b.input_schema,
        }
        for b in bindings
    ]


async def run_agent(
    client: MultiMCPClient,
    question: str,
    model: str = MODEL,
    max_iterations: int = MAX_ITERATIONS,
    on_step: Any = None,
) -> AgentResult:
    """Run the agent loop for one question.

    `on_step(event_type, payload)` is called for ['plan', 'tool_call', 'tool_result', 'final']
    so a UI can stream progress.
    """
    bindings = client.tool_bindings
    tools = _tools_for_anthropic(bindings)
    anthropic_client = anthropic.Anthropic()
    messages: list[dict] = [{"role": "user", "content": question}]
    trace: list[ToolCallTrace] = []
    started = time.time()
    final_text = ""
    iterations = 0
    raw_response = None

    for iteration in range(1, max_iterations + 1):
        iterations = iteration
        response = anthropic_client.messages.create(
            model=model,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=tools,
            messages=messages,
        )
        raw_response = response

        # Did we get text plus possible tool_use blocks?
        tool_uses = [b for b in response.content if b.type == "tool_use"]
        text_blocks = [b for b in response.content if b.type == "text"]

        if text_blocks:
            text_chunk = "\n".join(b.text for b in text_blocks).strip()
            if text_chunk and on_step:
                on_step("text", {"iteration": iteration, "text": text_chunk})

        if response.stop_reason == "end_turn" or not tool_uses:
            # Final answer
            final_text = "\n".join(b.text for b in text_blocks).strip()
            if on_step:
                on_step("final", {"answer": final_text, "iterations": iteration})
            break

        # Append assistant turn that includes tool_use blocks
        messages.append({"role": "assistant", "content": response.content})

        # Execute every tool call requested in this turn
        tool_result_blocks = []
        for tu in tool_uses:
            binding = client.get_binding(tu.name)
            if on_step:
                on_step("tool_call", {
                    "iteration": iteration,
                    "tool_name": tu.name,
                    "server_label": binding.server_label if binding else "unknown",
                    "arguments": tu.input,
                })
            t0 = time.time()
            try:
                result_text = await client.call_tool(tu.name, tu.input)
            except Exception as exc:
                result_text = json.dumps({"error": str(exc)})
            elapsed = time.time() - t0
            preview = result_text if len(result_text) < 600 else result_text[:600] + "..."
            trace.append(ToolCallTrace(
                tool_name=tu.name,
                server_label=binding.server_label if binding else "unknown",
                arguments=tu.input,
                result_preview=preview,
                duration_s=elapsed,
                iteration=iteration,
            ))
            if on_step:
                on_step("tool_result", {
                    "iteration": iteration,
                    "tool_name": tu.name,
                    "duration_s": elapsed,
                    "result_preview": preview,
                })
            tool_result_blocks.append({
                "type": "tool_result",
                "tool_use_id": tu.id,
                "content": result_text,
            })

        # Send tool results back
        messages.append({"role": "user", "content": tool_result_blocks})

    return AgentResult(
        question=question,
        final_answer=final_text or "(no final answer)",
        trace=trace,
        iterations=iterations,
        total_seconds=time.time() - started,
        raw_result=raw_response,
    )


async def ask_one(question: str, **kwargs: Any) -> AgentResult:
    async with MultiMCPClient() as client:
        return await run_agent(client, question, **kwargs)
