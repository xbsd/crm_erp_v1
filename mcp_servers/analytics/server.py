"""Analytics MCP server entry point. Run with: python -m mcp_servers.analytics.server"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from server_base import make_server, run_stdio  # noqa: E402
from tools import TOOLS  # noqa: E402


def main() -> None:
    server = make_server("analytics-mcp-server", TOOLS)
    asyncio.run(run_stdio(server))


if __name__ == "__main__":
    main()
