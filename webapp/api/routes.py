"""Server-rendered page routes."""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from tests.use_cases import USE_CASES


def register_page_routes(app: FastAPI, templates: Jinja2Templates) -> None:

    def render(request: Request, name: str, page: str, **extra) -> HTMLResponse:
        ctx = {"current_page": page, "use_cases": USE_CASES, **extra}
        return templates.TemplateResponse(request, name, ctx)

    @app.get("/", response_class=HTMLResponse)
    async def home(request: Request):
        return render(request, "dashboard.html", "dashboard")

    @app.get("/assistant", response_class=HTMLResponse)
    async def assistant(request: Request):
        runner = request.app.state.runner
        return render(request, "assistant.html", "assistant",
                      servers=runner.server_summary(),
                      tool_catalog=runner.tool_catalog())

    @app.get("/customer-360", response_class=HTMLResponse)
    async def customer_360(request: Request):
        return render(request, "customer360.html", "customer360")

    @app.get("/reliability", response_class=HTMLResponse)
    async def reliability(request: Request):
        return render(request, "reliability.html", "reliability")

    @app.get("/tools", response_class=HTMLResponse)
    async def tools(request: Request):
        runner = request.app.state.runner
        return render(request, "catalog.html", "tools",
                      servers=runner.server_summary(),
                      tool_catalog=runner.tool_catalog())

    @app.get("/data-model", response_class=HTMLResponse)
    async def data_model(request: Request):
        return render(request, "data_model.html", "data_model")

    @app.get("/system", response_class=HTMLResponse)
    async def system(request: Request):
        runner = request.app.state.runner
        return render(request, "system.html", "system",
                      servers=runner.server_summary(),
                      tool_catalog=runner.tool_catalog())
