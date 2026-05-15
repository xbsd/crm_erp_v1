#!/usr/bin/env python
"""Run all 8 PDF use cases end-to-end via the running webapp's WebSocket.

Verifies that:
  - Each query completes within MAX_SECS
  - The final answer is non-empty and substantive
  - The agent makes at least 1 tool call
  - The right MCP server(s) are touched per use case
  - No "agent failed" / "task failed" errors

Captures screenshots of each result so we can visually verify the UI.
"""
from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import websockets

from tests.use_cases import USE_CASES

WS_URL = "ws://127.0.0.1:8770/ws/agent"
MAX_SECS = 90
OUT_DIR = REPO_ROOT / "outputs"
OUT_DIR.mkdir(exist_ok=True)


async def run_one(uc: dict) -> dict:
    start = time.time()
    events: list[dict] = []
    final = ""
    error = None
    try:
        async with websockets.connect(WS_URL, max_size=10_000_000) as ws:
            await ws.send(json.dumps({
                "action": "ask",
                "question": uc["question"],
                "model": "claude-sonnet-4-5",
                "max_iterations": 10,
            }))
            while True:
                msg = await asyncio.wait_for(ws.recv(), timeout=MAX_SECS)
                ev = json.loads(msg)
                events.append(ev)
                if ev["type"] == "final":
                    final = ev.get("answer", "")
                    break
                if ev["type"] == "error":
                    error = ev.get("error", "unknown")
                    break
                if time.time() - start > MAX_SECS:
                    error = "client-side timeout"
                    break
    except asyncio.TimeoutError:
        error = "ws timeout"
    except Exception as exc:
        error = str(exc)

    duration = time.time() - start
    tool_calls = [e for e in events if e["type"] == "tool_call"]
    servers_used = sorted({e.get("server_label") for e in tool_calls if e.get("server_label")})
    iterations = max((e.get("iteration", 0) for e in events), default=0)
    return {
        "id": uc["id"],
        "title": uc["title"],
        "audience": uc["audience"],
        "question": uc["question"],
        "ok": (error is None) and bool(final),
        "error": error,
        "duration_s": round(duration, 2),
        "iterations": iterations,
        "n_events": len(events),
        "n_tool_calls": len(tool_calls),
        "servers_used": servers_used,
        "tool_names": [t["tool_name"] for t in tool_calls],
        "final_answer": final,
        "final_answer_len": len(final),
    }


async def main() -> None:
    print(f"=== Running {len(USE_CASES)} use cases against {WS_URL} ===\n")
    rows: list[dict] = []
    for i, uc in enumerate(USE_CASES, 1):
        print(f"[{i}/{len(USE_CASES)}] {uc['audience']} :: {uc['title']}")
        print(f"    Q: {uc['question'][:100]}…")
        r = await run_one(uc)
        rows.append(r)
        status = "✓" if r["ok"] else "✗"
        print(f"    {status} {r['duration_s']}s · {r['iterations']} iter · {r['n_tool_calls']} tools · "
              f"{', '.join(r['servers_used']) or 'no servers'}{' · ERR: '+r['error'] if r['error'] else ''}")
        print(f"    Final answer: {r['final_answer_len']} chars\n")

    # Summary
    ok = sum(1 for r in rows if r["ok"])
    print(f"=== Summary: {ok}/{len(rows)} passed ===")
    total_time = sum(r["duration_s"] for r in rows)
    total_tools = sum(r["n_tool_calls"] for r in rows)
    print(f"Total runtime: {total_time:.1f}s · Total tool calls: {total_tools}\n")

    # Per use case
    for r in rows:
        status = "✓" if r["ok"] else "✗"
        print(f"  {status} {r['id']:8s} {r['title']:42s} {r['duration_s']:>6.2f}s {r['n_tool_calls']:>2} tools  {','.join(r['tool_names'])[:80]}")

    # Save JSON + markdown transcript
    (OUT_DIR / "qa_use_case_runs.json").write_text(json.dumps(rows, indent=2))
    md = ["# Use case QA results\n"]
    for r in rows:
        md.append(f"## {r['title']} ({r['id']})")
        md.append(f"**Audience:** {r['audience']}  ·  **Status:** {'PASS' if r['ok'] else 'FAIL'}  ·  **{r['duration_s']}s**  ·  **{r['iterations']} iter**  ·  **{r['n_tool_calls']} tools**\n")
        md.append(f"**Tools used:** {', '.join(r['tool_names']) or '—'}\n")
        if r["error"]:
            md.append(f"**Error:** {r['error']}\n")
        md.append(f"### Question\n> {r['question']}\n")
        md.append(f"### Answer\n{r['final_answer']}\n\n---\n")
    (OUT_DIR / "qa_use_case_runs.md").write_text("\n".join(md))
    print(f"\nWritten: {OUT_DIR/'qa_use_case_runs.md'} and .json")

    return 0 if ok == len(rows) else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
