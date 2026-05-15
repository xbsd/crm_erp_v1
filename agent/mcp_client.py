"""Lightweight client that connects to multiple MCP servers over stdio.

Spawns one subprocess per server and presents the union of their tools as a
flat list. Each tool is tagged with its source server so the agent can show
which system answered a question.
"""
from __future__ import annotations

import asyncio
import contextlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

REPO_ROOT = Path(__file__).resolve().parent.parent


@dataclass
class ServerSpec:
    name: str            # short id, e.g. "crm"
    module: str          # python -m target, e.g. "mcp_servers.crm.server"
    label: str           # human label, e.g. "Salesforce CRM"


DEFAULT_SERVERS: list[ServerSpec] = [
    ServerSpec("crm", "mcp_servers.crm.server", "Salesforce CRM"),
    ServerSpec("erp", "mcp_servers.erp.server", "ERP System"),
    ServerSpec("qa", "mcp_servers.qa.server", "QA / Reliability"),
    ServerSpec("analytics", "mcp_servers.analytics.server", "Analytics (cross-system)"),
]


@dataclass
class ToolBinding:
    name: str
    description: str
    input_schema: dict
    server_name: str
    server_label: str


class MultiMCPClient:
    """Async context manager that owns connections to all configured servers."""

    def __init__(self, servers: list[ServerSpec] | None = None) -> None:
        self.servers = servers or DEFAULT_SERVERS
        self._stack: contextlib.AsyncExitStack | None = None
        self._sessions: dict[str, ClientSession] = {}
        self._tool_index: dict[str, ToolBinding] = {}

    async def __aenter__(self) -> "MultiMCPClient":
        self._stack = contextlib.AsyncExitStack()
        await self._stack.__aenter__()
        for spec in self.servers:
            params = StdioServerParameters(
                command=sys.executable,
                args=["-m", spec.module],
                cwd=str(REPO_ROOT),
            )
            read, write = await self._stack.enter_async_context(stdio_client(params))
            session = await self._stack.enter_async_context(ClientSession(read, write))
            await session.initialize()
            self._sessions[spec.name] = session
            tools = await session.list_tools()
            for t in tools.tools:
                self._tool_index[t.name] = ToolBinding(
                    name=t.name,
                    description=t.description or "",
                    input_schema=t.inputSchema or {"type": "object", "properties": {}},
                    server_name=spec.name,
                    server_label=spec.label,
                )
        return self

    async def __aexit__(self, *exc_info: Any) -> None:
        if self._stack:
            await self._stack.__aexit__(*exc_info)
            self._stack = None
            self._sessions = {}
            self._tool_index = {}

    @property
    def tool_bindings(self) -> list[ToolBinding]:
        return list(self._tool_index.values())

    def get_binding(self, name: str) -> ToolBinding | None:
        return self._tool_index.get(name)

    async def call_tool(self, name: str, arguments: dict | None) -> str:
        binding = self._tool_index.get(name)
        if not binding:
            return json.dumps({"error": f"Unknown tool {name}"})
        session = self._sessions[binding.server_name]
        result = await session.call_tool(name, arguments or {})
        # Concatenate text contents
        chunks: list[str] = []
        for c in result.content:
            text = getattr(c, "text", None)
            if text:
                chunks.append(text)
        return "\n".join(chunks) or "(no content)"
