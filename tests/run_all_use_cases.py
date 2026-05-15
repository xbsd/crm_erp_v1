"""Run all 8 PDF use-case questions through the agent and save outputs.

Generates:
  - outputs/use_case_runs.json  — full transcript + tool traces
  - outputs/use_case_runs.md    — human-readable markdown report
"""
from __future__ import annotations

import asyncio
import json
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agent.mcp_client import MultiMCPClient  # noqa: E402
from agent.orchestrator import run_agent  # noqa: E402
from tests.use_cases import USE_CASES  # noqa: E402

OUTPUTS_DIR = ROOT / "outputs"
OUTPUTS_DIR.mkdir(exist_ok=True)


async def main() -> None:
    started = time.time()
    print(f"=== Running {len(USE_CASES)} use cases ===")
    runs: list[dict] = []
    async with MultiMCPClient() as client:
        print(f"Connected to {len(client.servers)} MCP servers with {len(client.tool_bindings)} total tools")
        for case in USE_CASES:
            print(f"\n>>> [{case['id']}] {case['audience']}: {case['title']}")
            print(f"    Q: {case['question'][:100]}...")
            t0 = time.time()
            steps: list[dict] = []

            def on_step(event: str, payload: dict, _steps=steps, _start=t0):
                if event == "tool_call":
                    print(f"      → {payload['server_label']}::{payload['tool_name']}")
                steps.append({"event": event, "payload": payload, "t": time.time() - _start})

            try:
                result = await run_agent(client, case["question"], on_step=on_step)
                runs.append({
                    "id": case["id"],
                    "audience": case["audience"],
                    "title": case["title"],
                    "question": case["question"],
                    "answer": result.final_answer,
                    "iterations": result.iterations,
                    "tool_calls": len(result.trace),
                    "duration_s": round(result.total_seconds, 2),
                    "trace": [
                        {
                            "tool_name": t.tool_name,
                            "server_label": t.server_label,
                            "arguments": t.arguments,
                            "result_preview": t.result_preview,
                            "duration_s": round(t.duration_s, 3),
                            "iteration": t.iteration,
                        }
                        for t in result.trace
                    ],
                })
                print(f"    OK in {result.total_seconds:.1f}s, {len(result.trace)} tool calls, {result.iterations} iterations")
            except Exception as exc:
                print(f"    FAILED: {exc}")
                runs.append({
                    "id": case["id"], "audience": case["audience"], "title": case["title"],
                    "question": case["question"], "answer": f"ERROR: {exc}",
                    "iterations": 0, "tool_calls": 0, "duration_s": 0, "trace": [],
                })

    total = time.time() - started
    summary = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "model": "claude-sonnet-4-5",
        "use_cases_run": len(runs),
        "total_duration_s": round(total, 1),
        "runs": runs,
    }
    (OUTPUTS_DIR / "use_case_runs.json").write_text(json.dumps(summary, indent=2))
    write_markdown_report(summary, OUTPUTS_DIR / "use_case_runs.md")
    print(f"\n=== Wrote {OUTPUTS_DIR / 'use_case_runs.json'} ===")
    print(f"=== Wrote {OUTPUTS_DIR / 'use_case_runs.md'} ===")
    print(f"Total: {total:.1f}s across {len(runs)} use cases")


def write_markdown_report(summary: dict, path: Path) -> None:
    lines = []
    lines.append(f"# MCP Enterprise Integration — Use Case Runs\n")
    lines.append(f"_Generated {summary['generated_at']} — model {summary['model']} — total {summary['total_duration_s']}s_\n")
    lines.append("\n## Overview\n")
    lines.append(f"- Use cases run: **{summary['use_cases_run']}**")
    lines.append(f"- Total tool calls: **{sum(r['tool_calls'] for r in summary['runs'])}**")
    lines.append(f"- Avg iterations: **{round(sum(r['iterations'] for r in summary['runs']) / max(1, len(summary['runs'])), 2)}**\n")
    for r in summary["runs"]:
        lines.append(f"---\n\n## [{r['id']}] {r['audience']}: {r['title']}\n")
        lines.append(f"**Question:** {r['question']}\n")
        lines.append(f"**Agent loop:** {r['iterations']} iterations, {r['tool_calls']} tool calls, {r['duration_s']}s\n")
        if r["trace"]:
            lines.append("\n### Tool trace\n")
            for t in r["trace"]:
                arg_str = ", ".join(f"{k}={v!r}" for k, v in t["arguments"].items())
                lines.append(f"- `{t['server_label']} :: {t['tool_name']}` ({arg_str}) — {t['duration_s']}s")
        lines.append("\n### Answer\n")
        lines.append(r["answer"])
        lines.append("\n")
    path.write_text("\n".join(lines))


if __name__ == "__main__":
    asyncio.run(main())
