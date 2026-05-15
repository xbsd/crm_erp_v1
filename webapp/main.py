"""FastAPI application — Enterprise AI Workbench.

Sophisticated executive-grade UI replacing the Streamlit prototype.

Run:
    python -m uvicorn webapp.main:app --host 127.0.0.1 --port 8000 --reload

Or:
    python scripts/run_webapp.py
"""
from __future__ import annotations

import contextlib
import logging
import os
import sys
from pathlib import Path

# Make repo importable
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Auto-load .env before importing anthropic
from webapp.env_loader import load_env  # noqa: E402
load_env(verbose=True)

import time  # noqa: E402

from fastapi import FastAPI, Request  # noqa: E402
from fastapi.responses import HTMLResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402
from fastapi.templating import Jinja2Templates  # noqa: E402
from starlette.middleware.base import BaseHTTPMiddleware  # noqa: E402

from webapp.agent_runner import AgentRunner  # noqa: E402
from webapp.api.data import register_data_routes  # noqa: E402
from webapp.api.ws import register_ws_routes  # noqa: E402
from webapp.api.routes import register_page_routes  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("webapp")


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    """Start one MultiMCPClient for the app's lifetime."""
    log.info("Starting MCP client (spawning 4 stdio servers)…")
    runner = AgentRunner()
    try:
        await runner.__aenter__()
        app.state.runner = runner
        log.info("MCP client ready — %d tools across %d servers",
                 len(runner.tool_catalog()), len(runner.server_summary()))
        yield
    finally:
        log.info("Shutting down MCP client…")
        await runner.__aexit__(None, None, None)


class NoCacheStaticMiddleware(BaseHTTPMiddleware):
    """Tell browsers to revalidate /static assets on every request.

    Hot-reload-friendly: editing dashboard.js etc. takes effect on the
    next page load without needing a hard refresh.
    """
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        if request.url.path.startswith("/static/"):
            response.headers["Cache-Control"] = "no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response


app = FastAPI(title="Enterprise AI Workbench", lifespan=lifespan)
app.add_middleware(NoCacheStaticMiddleware)
app.mount("/static", StaticFiles(directory=str(Path(__file__).parent / "static")), name="static")
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

# Static-asset version tag — re-stamped at app start so every server reboot
# busts the browser cache. Template files reference {{ asset_v }} on
# <script> and <link> tags.
ASSET_V = str(int(time.time()))
templates.env.globals["asset_v"] = ASSET_V

# Pass templates into route modules
app.state.templates = templates
app.state.repo_root = REPO_ROOT

register_page_routes(app, templates)
register_data_routes(app)
register_ws_routes(app)


@app.get("/health")
async def health() -> dict[str, object]:
    runner: AgentRunner = app.state.runner
    return {
        "status": "ok",
        "anthropic_api_key": bool(os.environ.get("ANTHROPIC_API_KEY")),
        "tools": len(runner.tool_catalog()),
        "servers": runner.server_summary(),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
