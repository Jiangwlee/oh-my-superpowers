"""FastMCP adapter: expose the REST facade as MCP with zero new semantics.

FastMCP derives MCP tools from the FastAPI routes, so ``/session``, ``/dom``,
``/act``, ``/shot`` become the same operations over MCP for agents that call
tools directly. Same engine, same contract — this file adds no logic.
"""

from __future__ import annotations

import os

from fastmcp import FastMCP

from ..rest.main import app

mcp = FastMCP.from_fastapi(app=app, name="omp-browser-container")


def main() -> None:
    host = os.environ.get("MCP_HOST", "0.0.0.0")
    port = int(os.environ.get("MCP_PORT", "9223"))
    mcp.run(transport="http", host=host, port=port)


if __name__ == "__main__":
    main()
