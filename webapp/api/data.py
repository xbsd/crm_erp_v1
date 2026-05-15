"""Direct (non-MCP) data endpoints used for fast dashboard rendering.

These call the same Python tool functions used by the MCP servers, but
without going through the stdio protocol — keeping dashboards instant.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query, Request

from mcp_servers.analytics.tools import (
    order_booking_patterns_by_account_name,
    quarterly_executive_update,
    quote_to_revenue_conversion,
    recommend_product_for_customer_project,
    returns_increase_for_product,
    revenue_pattern_change,
    top_key_accounts,
)
from mcp_servers.common import CRM_DB, ERP_DB, QA_DB
from mcp_servers.crm.tools import (
    get_account_summary,
    list_accounts,
    list_opportunities,
    list_quotes,
    pipeline_summary_by_stage,
)
from mcp_servers.erp.tools import (
    ar_aging,
    list_invoices,
    list_sales_orders,
    revenue_by_period,
)
from mcp_servers.qa.tools import (
    customer_returns_by_account,
    customer_returns_by_product,
    get_product_reliability_report,
    list_reliability_scores,
    returns_trend_for_product,
)


def _attach_dbs() -> sqlite3.Connection:
    uri = f"file:{CRM_DB.as_posix()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    conn.execute(f"ATTACH DATABASE 'file:{ERP_DB.as_posix()}?mode=ro' AS erp")
    conn.execute(f"ATTACH DATABASE 'file:{QA_DB.as_posix()}?mode=ro' AS qa")
    return conn


def register_data_routes(app: FastAPI) -> None:

    # -----------------------------------------------------------------------
    # Dashboard
    # -----------------------------------------------------------------------
    @app.get("/api/dashboard")
    async def dashboard(year: int = 2026, quarter: int = 1):
        cur = quarterly_executive_update(year, quarter, prior_year_quarter=True)
        # Add quarterly time series
        ts = revenue_by_period(group_by="period")["rows"]
        ts.sort(key=lambda r: r["period"])
        # Top key accounts
        top = top_key_accounts(top_n=10)["rows"]
        # YoY pattern change
        yoy = revenue_pattern_change(year - 1, quarter, year, quarter,
                                     key_accounts_only=True,
                                     significant_change_threshold_pct=25, top_n=20)
        # Low reliability scores
        low_rel = list_reliability_scores(max_score=75, limit=10)["rows"]
        # Returns top
        returns_top = customer_returns_by_product(top_n=10)["rows"]

        pipeline_total = sum(p["amount"] for p in cur["pipeline_by_stage"])
        pipeline_count = sum(p["n"] for p in cur["pipeline_by_stage"])
        return {
            "period": cur["period"],
            "prior_period": cur["prior_period"],
            "totals": cur["totals"],
            "pipeline_total": pipeline_total,
            "pipeline_count": pipeline_count,
            "pipeline_by_stage": cur["pipeline_by_stage"],
            "revenue_by_industry": cur["revenue_by_industry"],
            "revenue_by_product_family": cur["revenue_by_product_family"],
            "revenue_by_region": cur["revenue_by_region"],
            "top_customers": cur["top_customers"],
            "top_key_accounts": top,
            "revenue_quarterly_series": ts,
            "yoy_changes": yoy["rows"],
            "low_reliability": low_rel,
            "returns_top_products": returns_top,
            "ar_aging": ar_aging()["rows"],
        }

    # -----------------------------------------------------------------------
    # Accounts
    # -----------------------------------------------------------------------
    @app.get("/api/accounts")
    async def accounts(limit: int = 500, key_only: bool = False):
        return list_accounts(limit=limit, key_accounts_only=key_only)

    @app.get("/api/account/{account_id}")
    async def account_detail(account_id: str):
        summary = get_account_summary(account_id=account_id)
        if "error" in summary:
            raise HTTPException(404, summary["error"])
        # Opportunities + quotes + orders + invoices + returns + booking
        opps = list_opportunities(account_id=account_id, limit=100)["rows"]
        quotes = list_quotes(account_id=account_id, limit=100)["rows"]
        orders = list_sales_orders(external_account_id=account_id, limit=100)["rows"]
        invoices = list_invoices(external_account_id=account_id, limit=100)["rows"]
        returns = customer_returns_by_account(external_account_id=account_id, limit=50)["rows"]
        # Booking pattern (quarterly)
        try:
            booking = order_booking_patterns_by_account_name(
                account_name=summary["name"], group_by="quarter",
            )["rows"]
        except Exception:
            booking = []
        return {
            "summary": summary,
            "opportunities": opps,
            "quotes": quotes,
            "orders": orders,
            "invoices": invoices,
            "returns": returns,
            "booking_by_quarter": booking,
        }

    # -----------------------------------------------------------------------
    # Products / Reliability
    # -----------------------------------------------------------------------
    @app.get("/api/products")
    async def products_list():
        conn = sqlite3.connect(CRM_DB); conn.row_factory = sqlite3.Row
        rows = [dict(r) for r in conn.execute("""
            SELECT id, sku, name, product_family, product_category, list_price,
                   status, target_industries
              FROM products ORDER BY name
        """).fetchall()]
        conn.close()
        # Attach latest reliability score
        conn = sqlite3.connect(QA_DB); conn.row_factory = sqlite3.Row
        rel = {r["external_product_id"]: dict(r) for r in conn.execute("""
            SELECT external_product_id, score, score_grade
              FROM reliability_scores
        """).fetchall()}
        conn.close()
        for p in rows:
            r = rel.get(p["id"])
            p["reliability_score"] = r["score"] if r else None
            p["reliability_grade"] = r["score_grade"] if r else None
        return {"row_count": len(rows), "rows": rows}

    @app.get("/api/product/{product_id}/reliability")
    async def product_reliability(product_id: str):
        rep = get_product_reliability_report(product_id)
        # Augment with trend
        trend = returns_trend_for_product(product_id, group_by="month")["rows"]
        rep["returns_trend"] = trend
        return rep

    # -----------------------------------------------------------------------
    # Database tables (System Health page + data-model page)
    # -----------------------------------------------------------------------
    @app.get("/api/databases")
    async def databases():
        result: dict[str, Any] = {}
        for label, path in [("crm", CRM_DB), ("erp", ERP_DB), ("qa", QA_DB)]:
            conn = sqlite3.connect(path); conn.row_factory = sqlite3.Row
            tables = [r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
            ).fetchall()]
            tbl_info: list[dict] = []
            for t in tables:
                cnt = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                cols = [{"name": c["name"], "type": c["type"], "pk": bool(c["pk"]), "notnull": bool(c["notnull"])}
                        for c in conn.execute(f"PRAGMA table_info({t})").fetchall()]
                tbl_info.append({"name": t, "row_count": cnt, "columns": cols})
            conn.close()
            result[label] = {"path": str(path), "tables": tbl_info}
        return result

    @app.get("/api/table/{database}/{table}")
    async def table_sample(database: str, table: str, limit: int = 50):
        path_map = {"crm": CRM_DB, "erp": ERP_DB, "qa": QA_DB}
        if database not in path_map:
            raise HTTPException(404, "Unknown database")
        conn = sqlite3.connect(path_map[database]); conn.row_factory = sqlite3.Row
        # Sanitize: ensure table exists
        if not conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name = ?", (table,)).fetchone():
            conn.close(); raise HTTPException(404, "Unknown table")
        rows = [dict(r) for r in conn.execute(f"SELECT * FROM {table} LIMIT {int(limit)}").fetchall()]
        conn.close()
        return {"row_count": len(rows), "rows": rows}

    # -----------------------------------------------------------------------
    # Tool catalog & manual invocation
    # -----------------------------------------------------------------------
    @app.get("/api/catalog")
    async def catalog(request: Request):
        runner = request.app.state.runner
        return {"servers": runner.server_summary(), "tools": runner.tool_catalog()}

    @app.post("/api/invoke-tool")
    async def invoke_tool(request: Request, payload: dict):
        """Manually invoke any MCP tool with given JSON args."""
        runner = request.app.state.runner
        name = payload.get("tool_name") or payload.get("name")
        args = payload.get("arguments") or {}
        if not name:
            raise HTTPException(400, "tool_name required")
        try:
            text = await runner.client.call_tool(name, args)
            try:
                import json as _json
                parsed = _json.loads(text)
            except Exception:
                parsed = {"text": text}
            return {"tool_name": name, "arguments": args, "result": parsed}
        except Exception as e:
            raise HTTPException(500, str(e))

    # -----------------------------------------------------------------------
    # Use cases (PDF questions)
    # -----------------------------------------------------------------------
    @app.get("/api/use-cases")
    async def use_cases_endpoint():
        from tests.use_cases import USE_CASES
        return {"row_count": len(USE_CASES), "rows": USE_CASES}
