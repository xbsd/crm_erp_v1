"""Shared MCP-server scaffolding.

Every server (CRM, ERP, QA, Analytics) imports a TOOLS list — a list of
dicts {name, description, input_schema, fn} — and `make_server` wires it
up to the MCP Server protocol (stdio).
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool


def make_server(name: str, tools: list[dict]) -> Server:
    server: Server = Server(name)

    @server.list_tools()
    async def _list_tools() -> list[Tool]:
        return [
            Tool(name=t["name"], description=t["description"], inputSchema=t["input_schema"])
            for t in tools
        ]

    name_to_fn = {t["name"]: t["fn"] for t in tools}

    @server.call_tool()
    async def _call_tool(name: str, arguments: dict[str, Any] | None) -> list[TextContent]:
        if name not in name_to_fn:
            return [TextContent(type="text", text=json.dumps({"error": f"Unknown tool {name}"}))]
        try:
            args = arguments or {}
            result = name_to_fn[name](**args)
            return [TextContent(type="text", text=json.dumps(result, default=str, indent=2))]
        except TypeError as e:
            return [TextContent(type="text", text=json.dumps({"error": f"Invalid arguments: {e}"}))]
        except Exception as e:  # pragma: no cover - last-resort safety
            logging.exception("Tool execution failed: %s", name)
            return [TextContent(type="text", text=json.dumps({"error": str(e)}))]

    return server


async def run_stdio(server: Server) -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def main_for(server_name: str, tools_module_path: str) -> None:
    """Convenience: load TOOLS from a module and run an stdio server."""
    import importlib
    mod = importlib.import_module(tools_module_path)
    server = make_server(server_name, mod.TOOLS)
    asyncio.run(run_stdio(server))
