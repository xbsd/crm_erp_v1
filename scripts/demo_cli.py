"""Interactive CLI demo runner.

Lets the user pick from the 8 PDF use cases or type a custom question,
then shows the agent's tool calls and final answer in real time.

Usage:
    python scripts/demo_cli.py              # interactive menu
    python scripts/demo_cli.py 3            # run use case #3
    python scripts/demo_cli.py "Top 5 ..."  # ask a custom question
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from agent.mcp_client import MultiMCPClient
from agent.orchestrator import run_agent
from tests.use_cases import USE_CASES

console = Console()


def show_menu() -> None:
    table = Table(title="Demo Use Cases (from PDF)", title_style="bold cyan", show_header=True)
    table.add_column("#", style="cyan", width=4)
    table.add_column("Audience", style="magenta", width=10)
    table.add_column("Title", style="green")
    table.add_column("Question (truncated)", style="dim")
    for i, c in enumerate(USE_CASES, 1):
        q = c["question"]
        if len(q) > 80:
            q = q[:77] + "..."
        table.add_row(str(i), c["audience"], c["title"], q)
    console.print(table)
    console.print("\n[bold]Enter a number, or type a custom question.[/bold]")


async def run(question: str, title: str = "") -> None:
    async with MultiMCPClient() as client:
        console.print(Panel.fit(
            f"[bold cyan]Connected to {len(client.servers)} MCP servers[/bold cyan]\n"
            + "\n".join(f"  • {s.label} ({s.name}-mcp-server) — {sum(1 for b in client.tool_bindings if b.server_name == s.name)} tools" for s in client.servers)
            + f"\n[dim]Total {len(client.tool_bindings)} tools available to the agent[/dim]",
            border_style="cyan",
        ))
        console.print(Panel.fit(
            f"[bold]Question[/bold]\n{question}",
            border_style="yellow",
            title=title or "Demo question",
        ))

        def on_step(event: str, payload: dict) -> None:
            if event == "tool_call":
                args = payload["arguments"]
                arg_str = ", ".join(f"{k}={v!r}" for k, v in args.items())
                if len(arg_str) > 80:
                    arg_str = arg_str[:77] + "..."
                console.print(f"  [cyan]→[/cyan] [bold]{payload['server_label']}[/bold]::{payload['tool_name']}([dim]{arg_str}[/dim])")
            elif event == "tool_result":
                console.print(f"    [green]✓[/green] {payload['tool_name']} returned in {payload['duration_s']:.2f}s")
            elif event == "final":
                console.rule("[bold green]Answer[/bold green]")

        result = await run_agent(client, question, on_step=on_step)
        console.print(Markdown(result.final_answer))
        console.rule()
        console.print(f"[dim]Agent ran {result.iterations} iterations with {len(result.trace)} tool calls in {result.total_seconds:.1f}s[/dim]")


def main() -> None:
    if len(sys.argv) == 1:
        show_menu()
        try:
            choice = input("\n> ").strip()
        except KeyboardInterrupt:
            sys.exit(0)
    else:
        choice = " ".join(sys.argv[1:])
    # Numeric pick?
    if choice.isdigit() and 1 <= int(choice) <= len(USE_CASES):
        case = USE_CASES[int(choice) - 1]
        asyncio.run(run(case["question"], title=f"{case['audience']} — {case['title']}"))
    elif choice:
        asyncio.run(run(choice, title="Custom question"))


if __name__ == "__main__":
    main()
