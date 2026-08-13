"""Minimal synchronous MCP client for the local stdio MCP server.

The LangGraph tool nodes are synchronous, so this module wraps the async MCP
1.x protocol (``StdioServerParameters`` / ``stdio_client`` / ``ClientSession``)
behind synchronous methods via ``asyncio.run``.  Every operation opens a
short-lived stdio session, performs a single discovery or tool call, and tears
down the session and its subprocess through the ``async with`` context
managers.  Tool schemas are cached in-process so decision nodes do not spawn a
discovery subprocess on every loop.

Security notes:

- Error logs only record the exception type (never patient arguments, API keys,
  or full tool results).
- Only the four whitelisted business tools may be discovered or invoked.
"""

import asyncio
import json
import logging
import sys
import textwrap
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

logger = logging.getLogger(__name__)

# Absolute path to Agent/ so the subprocess is always launched with a stable
# working directory regardless of the caller's cwd.
AGENT_DIR = Path(__file__).resolve().parent.parent

ALLOWED_TOOLS = frozenset(
    {
        "verify_patient_identity",
        "get_patient_profile",
        "get_patient_medical_cases",
        "get_patient_visit_records",
    }
)

DEFAULT_TIMEOUT_SECONDS = 60.0


class MCPToolError(RuntimeError):
    """Raised when an MCP operation times out or fails at the protocol level."""


class MCPToolClient:
    """Synchronous client for ``app.mcp_server`` over the stdio transport."""

    def __init__(
        self,
        agent_dir: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        self.agent_dir = Path(agent_dir) if agent_dir else AGENT_DIR
        self.timeout = timeout

    # ------------------------------------------------------------------
    # Public synchronous API
    # ------------------------------------------------------------------

    def list_tools(self) -> List[Dict[str, Any]]:
        """Return the whitelisted tools (name / description / inputSchema)."""
        global _tools_cache
        if _tools_cache is not None:
            return _tools_cache
        with _tools_cache_lock:
            if _tools_cache is None:
                _tools_cache = self._run(self._list_tools_async())
        return _tools_cache

    def call_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        """Invoke a whitelisted tool and return its structured result."""
        if name not in ALLOWED_TOOLS:
            raise MCPToolError(f"unknown tool: {name}")
        return self._run(self._call_tool_async(name, arguments))

    # ------------------------------------------------------------------
    # Async internals
    # ------------------------------------------------------------------

    def _server_params(self) -> StdioServerParameters:
        return StdioServerParameters(
            command=sys.executable,
            args=["-m", "app.mcp_server"],
            env=None,
            cwd=str(self.agent_dir),
        )

    def _run(self, coro: Any) -> Any:
        try:
            return asyncio.run(coro)
        except MCPToolError:
            raise
        except (asyncio.TimeoutError, TimeoutError) as exc:
            raise MCPToolError("MCP operation timed out") from exc
        except Exception as exc:  # noqa: BLE001 - converted to a safe error
            logger.error("MCP operation failed (%s)", type(exc).__name__)
            raise MCPToolError("MCP operation failed") from exc

    async def _with_session(self, op: Any) -> Any:
        server_params = self._server_params()
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await asyncio.wait_for(session.initialize(), timeout=self.timeout)
                return await asyncio.wait_for(op(session), timeout=self.timeout)

    async def _list_tools_async(self) -> List[Dict[str, Any]]:
        async def op(session: ClientSession) -> List[Dict[str, Any]]:
            result = await session.list_tools()
            return [
                self._normalize_tool(tool)
                for tool in result.tools
                if tool.name in ALLOWED_TOOLS
            ]

        return await self._with_session(op)

    async def _call_tool_async(self, name: str, arguments: Dict[str, Any]) -> Any:
        async def op(session: ClientSession) -> Any:
            result = await session.call_tool(name, arguments=arguments)
            return self._parse_result(result)

        return await self._with_session(op)

    # ------------------------------------------------------------------
    # Result / schema normalisation
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_tool(tool: Any) -> Dict[str, Any]:
        description = textwrap.dedent(tool.description or "").strip()
        return {
            "name": tool.name,
            "description": description,
            "inputSchema": tool.inputSchema or {"type": "object", "properties": {}},
        }

    @staticmethod
    def _extract_text_content(result: Any) -> Optional[str]:
        for item in getattr(result, "content", None) or []:
            if getattr(item, "type", None) == "text":
                return getattr(item, "text", None)
        return None

    def _parse_result(self, result: Any) -> Any:
        if getattr(result, "isError", False):
            raise MCPToolError("MCP tool reported an error")

        structured = getattr(result, "structuredContent", None)
        if isinstance(structured, (dict, list)) and structured:
            return structured
        if structured is not None:
            return structured

        text = self._extract_text_content(result)
        if text is None:
            return {}
        try:
            return json.loads(text)
        except (json.JSONDecodeError, TypeError):
            return {"text": text}


# Process-wide tool-schema cache.  list_tools() is idempotent and the schemas
# only change when the server code changes (which requires a process restart),
# so caching once per process avoids a subprocess discovery on every request.
_tools_cache: Optional[List[Dict[str, Any]]] = None
_tools_cache_lock = threading.Lock()
