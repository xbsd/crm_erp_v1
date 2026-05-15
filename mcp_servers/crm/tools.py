"""CRM MCP server tool implementations.

These functions wrap the Salesforce-like CRM database. Each returns a
JSON-serializable dict so the MCP layer can render it as `TextContent`.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import crm, rows_to_dicts


# ---------------------------------------------------------------------------
# Accounts
# ---------------------------------------------------------------------------
def list_accounts(
    limit: int = 50,
    industry: str | None = None,
    segment: str | None = None,
    key_accounts_only: bool = False,
    country: str | None = None,
) -> dict[str, Any]:
    """List CRM accounts with optional filters.

    Returns id, name, industry, segment, country, annual revenue, and whether
    each account is flagged as key/strategic.
    """
    conn = crm()
    where = []
    params: list[Any] = []
    if industry:
        where.append("industry = ?"); params.append(industry)
    if segment:
        where.append("segment = ?"); params.append(segment)
    if key_accounts_only:
        where.append("is_key_account = 1")
    if country:
        where.append("billing_country = ?"); params.append(country)
    sql = """SELECT id, name, industry, segment, billing_country AS country,
                    annual_revenue, employee_count, is_key_account, owner_id, created_date
               FROM accounts"""
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY annual_revenue DESC LIMIT ?"
    params.append(limit)
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return {"row_count": len(rows), "rows": rows_to_dicts(rows)}


def get_account_summary(account_id: str | None = None, account_name: str | None = None) -> dict[str, Any]:
    """Get a single account with key facts (id, name, primary contact, opps count, etc.).

    Provide either `account_id` or `account_name` (fuzzy match).
    """
    conn = crm()
    if account_id:
        row = conn.execute("SELECT * FROM accounts WHERE id = ?", (account_id,)).fetchone()
    elif account_name:
        row = conn.execute(
            "SELECT * FROM accounts WHERE name LIKE ? ORDER BY annual_revenue DESC LIMIT 1",
            (f"%{account_name}%",),
        ).fetchone()
    else:
        return {"error": "Provide account_id or account_name"}
    if not row:
        return {"error": "No account found"}
    acct = dict(row)
    opps = conn.execute("SELECT COUNT(*) FROM opportunities WHERE account_id = ?", (acct["id"],)).fetchone()[0]
    open_amt = conn.execute(
        "SELECT COALESCE(SUM(amount), 0) FROM opportunities WHERE account_id = ? AND stage NOT LIKE 'Closed%'",
        (acct["id"],),
    ).fetchone()[0]
    won_amt = conn.execute(
        "SELECT COALESCE(SUM(amount), 0) FROM opportunities WHERE account_id = ? AND stage = 'Closed Won'",
        (acct["id"],),
    ).fetchone()[0]
    contacts = rows_to_dicts(conn.execute(
        "SELECT first_name, last_name, title, email FROM contacts WHERE account_id = ? ORDER BY is_primary DESC LIMIT 5",
        (acct["id"],),
    ).fetchall())
    conn.close()
    acct["total_opportunities"] = opps
    acct["open_pipeline_amount"] = open_amt
    acct["closed_won_amount"] = won_amt
    acct["contacts"] = contacts
    return acct


# ---------------------------------------------------------------------------
# Opportunities & Pipeline
# ---------------------------------------------------------------------------
def list_opportunities(
    account_id: str | None = None,
    stage: str | None = None,
    owner_id: str | None = None,
    forecast_category: str | None = None,
    min_amount: float | None = None,
    closing_after: str | None = None,
    closing_before: str | None = None,
    limit: int = 100,
) -> dict[str, Any]:
    """List opportunities with multi-filter support.

    Useful for pipeline analysis. `closing_after` / `closing_before` accept ISO date strings (YYYY-MM-DD).
    """
    conn = crm()
    where = []
    params: list[Any] = []
    if account_id:
        where.append("o.account_id = ?"); params.append(account_id)
    if stage:
        where.append("o.stage = ?"); params.append(stage)
    if owner_id:
        where.append("o.owner_id = ?"); params.append(owner_id)
    if forecast_category:
        where.append("o.forecast_category = ?"); params.append(forecast_category)
    if min_amount is not None:
        where.append("o.amount >= ?"); params.append(min_amount)
    if closing_after:
        where.append("o.close_date >= ?"); params.append(closing_after)
    if closing_before:
        where.append("o.close_date <= ?"); params.append(closing_before)
    sql = """
        SELECT o.id, o.name, o.account_id, a.name AS account_name, o.stage, o.amount, o.probability,
               o.close_date, o.forecast_category, o.primary_product_family, o.created_date, o.competitor
          FROM opportunities o
          JOIN accounts a ON a.id = o.account_id
    """
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY o.amount DESC LIMIT ?"
    params.append(limit)
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return {"row_count": len(rows), "rows": rows_to_dicts(rows)}


def pipeline_summary_by_stage(period_close_after: str | None = None) -> dict[str, Any]:
    """Pipeline rollup by stage with count and weighted/unweighted amount.

    Optionally restrict to opportunities closing after a given date.
    """
    conn = crm()
    where = "WHERE stage NOT LIKE 'Closed%'"
    params: list[Any] = []
    if period_close_after:
        where += " AND close_date >= ?"; params.append(period_close_after)
    rows = conn.execute(f"""
        SELECT stage, COUNT(*) AS opp_count,
               COALESCE(SUM(amount), 0) AS total_amount,
               COALESCE(SUM(amount * probability), 0) AS weighted_amount,
               COALESCE(AVG(amount), 0) AS avg_amount
          FROM opportunities {where}
         GROUP BY stage
         ORDER BY total_amount DESC
    """, params).fetchall()
    conn.close()
    return {"row_count": len(rows), "rows": rows_to_dicts(rows)}


def opportunity_funnel(period_start: str | None = None, period_end: str | None = None) -> dict[str, Any]:
    """Win/loss funnel: counts and $ for Closed Won vs Lost in a period.
    Period filter is on `closed_date`.
    """
    conn = crm()
    where = []
    params: list[Any] = []
    if period_start:
        where.append("closed_date >= ?"); params.append(period_start)
    if period_end:
        where.append("closed_date <= ?"); params.append(period_end)
    where_clause = ("WHERE " + " AND ".join(where)) if where else ""
    rows = conn.execute(f"""
        SELECT stage,
               COUNT(*) AS n,
               COALESCE(SUM(amount), 0) AS amt,
               COALESCE(AVG(amount), 0) AS avg_amt
          FROM opportunities
         WHERE stage IN ('Closed Won', 'Closed Lost')
           {('AND ' + ' AND '.join(where)) if where else ''}
         GROUP BY stage
    """, params).fetchall()
    conn.close()
    return {"row_count": len(rows), "rows": rows_to_dicts(rows)}


# ---------------------------------------------------------------------------
# Quotes
# ---------------------------------------------------------------------------
def list_quotes(
    account_id: str | None = None,
    status: str | None = None,
    created_after: str | None = None,
    created_before: str | None = None,
    limit: int = 100,
) -> dict[str, Any]:
    """List quotes with optional filters."""
    conn = crm()
    where = []
    params: list[Any] = []
    if account_id:
        where.append("q.account_id = ?"); params.append(account_id)
    if status:
        where.append("q.status = ?"); params.append(status)
    if created_after:
        where.append("q.created_date >= ?"); params.append(created_after)
    if created_before:
        where.append("q.created_date <= ?"); params.append(created_before)
    sql = """SELECT q.id, q.quote_number, q.opportunity_id, q.account_id, a.name AS account_name,
                    q.status, q.grand_total, q.valid_until, q.created_date, q.accepted_date
               FROM quotes q
               JOIN accounts a ON a.id = q.account_id"""
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY q.grand_total DESC LIMIT ?"
    params.append(limit)
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return {"row_count": len(rows), "rows": rows_to_dicts(rows)}


def get_quote_detail(quote_id: str) -> dict[str, Any]:
    """Full quote detail incl. line items and any synced revenue from ERP."""
    conn = crm()
    quote = conn.execute("""
        SELECT q.*, a.name AS account_name
          FROM quotes q JOIN accounts a ON a.id = q.account_id
         WHERE q.id = ?
    """, (quote_id,)).fetchone()
    if not quote:
        return {"error": "Quote not found"}
    lines = rows_to_dicts(conn.execute("""
        SELECT qli.*, p.name AS product_name, p.product_family, p.product_category
          FROM quote_line_items qli
          JOIN products p ON p.id = qli.product_id
         WHERE qli.quote_id = ?
         ORDER BY qli.sort_order
    """, (quote_id,)).fetchall())
    revenue = rows_to_dicts(conn.execute(
        "SELECT * FROM quote_revenue_sync WHERE quote_id = ?", (quote_id,),
    ).fetchall())
    conn.close()
    q = dict(quote)
    q["line_items"] = lines
    q["revenue_sync"] = revenue
    return q


# ---------------------------------------------------------------------------
# Products & matching
# ---------------------------------------------------------------------------
def search_products(
    family: str | None = None,
    category: str | None = None,
    target_industry: str | None = None,
    max_price: float | None = None,
    min_temp_c: int | None = None,
    max_temp_c: int | None = None,
    qualification: str | None = None,
    status: str = "Active",
    limit: int = 30,
) -> dict[str, Any]:
    """Search the product catalog by family, category, target industry, price, or temperature range.

    Use this to find candidate products for a customer's design requirements.
    """
    conn = crm()
    where = ["status = ?"]
    params: list[Any] = [status]
    if family:
        where.append("product_family = ?"); params.append(family)
    if category:
        where.append("product_category LIKE ?"); params.append(f"%{category}%")
    if target_industry:
        where.append("(target_industries LIKE ? OR target_industries LIKE ? OR target_industries LIKE ?)")
        params.extend([f"{target_industry},%", f"%,{target_industry},%", f"%,{target_industry}"])
    if max_price is not None:
        where.append("list_price <= ?"); params.append(max_price)
    sql = "SELECT * FROM products"
    if where:
        sql += " WHERE " + " AND ".join(where)
    rows = conn.execute(sql, params).fetchall()
    conn.close()

    # Post-filter on temp/qualification (stored in JSON design_specs)
    matches: list[dict] = []
    for r in rows:
        d = dict(r)
        specs = json.loads(d.get("design_specs") or "{}")
        if min_temp_c is not None and specs.get("operating_temp_c", [None, None])[0] is not None:
            if specs["operating_temp_c"][0] > min_temp_c:
                continue
        if max_temp_c is not None and specs.get("operating_temp_c", [None, None])[1] is not None:
            if specs["operating_temp_c"][1] < max_temp_c:
                continue
        if qualification and specs.get("qualification") != qualification:
            continue
        d["specs"] = specs
        matches.append(d)
    matches.sort(key=lambda p: p["list_price"])
    return {"row_count": len(matches), "rows": matches[:limit]}


def find_product_for_requirements(
    industry: str,
    application: str | None = None,
    voltage_v: float | None = None,
    annual_volume: int | None = None,
    target_unit_price: float | None = None,
    operating_temp_min_c: int | None = None,
    operating_temp_max_c: int | None = None,
    qualification: str | None = None,
    product_family: str | None = None,
    top_n: int = 5,
) -> dict[str, Any]:
    """Score-rank the catalog against a set of customer design requirements.

    Returns top_n products ranked by a composite score (temperature fit,
    voltage fit, price fit, qualification match, industry alignment).
    """
    conn = crm()
    rows = conn.execute("SELECT * FROM products WHERE status = 'Active'").fetchall()
    conn.close()

    scored: list[dict] = []
    for r in rows:
        d = dict(r)
        specs = json.loads(d.get("design_specs") or "{}")
        score = 0.0
        notes = []

        # Industry alignment
        target_inds = (d.get("target_industries") or "").split(",")
        if industry in target_inds:
            score += 25
            notes.append(f"Industry '{industry}' is a target market.")
        else:
            score += 5
            notes.append("Outside primary target industries.")

        # Product family preference
        if product_family and d["product_family"] == product_family:
            score += 15
            notes.append("Exact product family match.")

        # Temperature fit
        spec_temp = specs.get("operating_temp_c", [None, None])
        if operating_temp_min_c is not None and spec_temp[0] is not None:
            if spec_temp[0] <= operating_temp_min_c:
                score += 15; notes.append(f"Meets min temp ({spec_temp[0]}°C ≤ {operating_temp_min_c}°C).")
            else:
                notes.append(f"FAIL min temp ({spec_temp[0]}°C > {operating_temp_min_c}°C).")
                continue
        if operating_temp_max_c is not None and spec_temp[1] is not None:
            if spec_temp[1] >= operating_temp_max_c:
                score += 15; notes.append(f"Meets max temp ({spec_temp[1]}°C ≥ {operating_temp_max_c}°C).")
            else:
                notes.append(f"FAIL max temp ({spec_temp[1]}°C < {operating_temp_max_c}°C).")
                continue

        # Voltage fit
        if voltage_v is not None:
            sv = specs.get("supply_voltage_v")
            if sv is not None and abs(sv - voltage_v) < 0.5:
                score += 15; notes.append(f"Supply voltage match ({sv}V).")
            elif sv is not None:
                notes.append(f"Voltage mismatch ({sv}V vs req {voltage_v}V).")
                score -= 5

        # Qualification
        if qualification:
            spec_q = specs.get("qualification", "")
            if qualification in spec_q or spec_q in qualification:
                score += 15; notes.append(f"Qualification {spec_q} matches request.")
            else:
                notes.append(f"Qualification {spec_q} does not match {qualification}.")
                score -= 5

        # Target price
        if target_unit_price is not None:
            if d["list_price"] <= target_unit_price * 1.10:
                score += 10; notes.append(f"List price ${d['list_price']:.2f} within 10 % of target.")
            elif d["list_price"] <= target_unit_price * 1.30:
                score += 4; notes.append(f"List price ${d['list_price']:.2f} within 30 % of target.")
            else:
                notes.append(f"List price ${d['list_price']:.2f} above target ${target_unit_price:.2f}.")

        scored.append({
            "id": d["id"],
            "sku": d["sku"],
            "name": d["name"],
            "product_family": d["product_family"],
            "product_category": d["product_category"],
            "list_price": d["list_price"],
            "target_industries": d["target_industries"],
            "specs": specs,
            "fit_score": round(score, 1),
            "fit_notes": notes,
        })
    scored.sort(key=lambda x: x["fit_score"], reverse=True)
    return {
        "criteria": {
            "industry": industry,
            "application": application,
            "voltage_v": voltage_v,
            "operating_temp_min_c": operating_temp_min_c,
            "operating_temp_max_c": operating_temp_max_c,
            "qualification": qualification,
            "target_unit_price": target_unit_price,
            "annual_volume": annual_volume,
            "product_family": product_family,
        },
        "row_count": min(len(scored), top_n),
        "rows": scored[:top_n],
    }


# ---------------------------------------------------------------------------
# Cross-cutting: reliability insights that have been synced into CRM
# ---------------------------------------------------------------------------
def get_reliability_insights_for_product(product_id: str) -> dict[str, Any]:
    """Get the most recent reliability insights synced from QA into CRM for a product."""
    conn = crm()
    rows = rows_to_dicts(conn.execute("""
        SELECT * FROM reliability_insights_sync
         WHERE product_id = ?
         ORDER BY sync_date DESC
    """, (product_id,)).fetchall())
    conn.close()
    return {"row_count": len(rows), "rows": rows}


# ---------------------------------------------------------------------------
# Tool schema definitions for MCP
# ---------------------------------------------------------------------------
TOOLS: list[dict] = [
    {
        "name": "crm_list_accounts",
        "description": "List CRM accounts. Filter by industry, segment, country, or key_accounts_only. Returns name, revenue, segment, and key-account flag.",
        "input_schema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "default": 50},
                "industry": {"type": "string"},
                "segment": {"type": "string", "enum": ["Enterprise", "Mid-Market", "SMB"]},
                "key_accounts_only": {"type": "boolean", "default": False},
                "country": {"type": "string"},
            },
        },
        "fn": list_accounts,
    },
    {
        "name": "crm_get_account_summary",
        "description": "Get full account summary by id or name (incl. pipeline, won amount, primary contacts).",
        "input_schema": {
            "type": "object",
            "properties": {
                "account_id": {"type": "string"},
                "account_name": {"type": "string"},
            },
        },
        "fn": get_account_summary,
    },
    {
        "name": "crm_list_opportunities",
        "description": "List opportunities with multi-filter (account_id, stage, owner, forecast_category, amount, close-date window).",
        "input_schema": {
            "type": "object",
            "properties": {
                "account_id": {"type": "string"},
                "stage": {"type": "string"},
                "owner_id": {"type": "string"},
                "forecast_category": {"type": "string"},
                "min_amount": {"type": "number"},
                "closing_after": {"type": "string", "description": "ISO date YYYY-MM-DD"},
                "closing_before": {"type": "string", "description": "ISO date YYYY-MM-DD"},
                "limit": {"type": "integer", "default": 100},
            },
        },
        "fn": list_opportunities,
    },
    {
        "name": "crm_pipeline_summary_by_stage",
        "description": "Pipeline rollup by stage with count, total $, weighted $, and average deal size.",
        "input_schema": {
            "type": "object",
            "properties": {
                "period_close_after": {"type": "string", "description": "Restrict to opps closing on/after this date"},
            },
        },
        "fn": pipeline_summary_by_stage,
    },
    {
        "name": "crm_opportunity_funnel",
        "description": "Closed-Won / Closed-Lost funnel for a given period (counts, total $, avg $).",
        "input_schema": {
            "type": "object",
            "properties": {
                "period_start": {"type": "string"},
                "period_end": {"type": "string"},
            },
        },
        "fn": opportunity_funnel,
    },
    {
        "name": "crm_list_quotes",
        "description": "List quotes filtered by account, status, or creation window.",
        "input_schema": {
            "type": "object",
            "properties": {
                "account_id": {"type": "string"},
                "status": {"type": "string"},
                "created_after": {"type": "string"},
                "created_before": {"type": "string"},
                "limit": {"type": "integer", "default": 100},
            },
        },
        "fn": list_quotes,
    },
    {
        "name": "crm_get_quote_detail",
        "description": "Get a quote with its line items and any revenue synced from ERP.",
        "input_schema": {
            "type": "object",
            "properties": {"quote_id": {"type": "string"}},
            "required": ["quote_id"],
        },
        "fn": get_quote_detail,
    },
    {
        "name": "crm_search_products",
        "description": "Search the product catalog by family, category, target industry, price ceiling, or temp range.",
        "input_schema": {
            "type": "object",
            "properties": {
                "family": {"type": "string"},
                "category": {"type": "string"},
                "target_industry": {"type": "string"},
                "max_price": {"type": "number"},
                "min_temp_c": {"type": "integer"},
                "max_temp_c": {"type": "integer"},
                "qualification": {"type": "string"},
                "status": {"type": "string", "default": "Active"},
                "limit": {"type": "integer", "default": 30},
            },
        },
        "fn": search_products,
    },
    {
        "name": "crm_find_product_for_requirements",
        "description": "Score-rank products against a set of customer design requirements (industry, voltage, temperature, qualification, target price). Returns top_n recommendations with fit_score and reasoning.",
        "input_schema": {
            "type": "object",
            "properties": {
                "industry": {"type": "string"},
                "application": {"type": "string"},
                "voltage_v": {"type": "number"},
                "annual_volume": {"type": "integer"},
                "target_unit_price": {"type": "number"},
                "operating_temp_min_c": {"type": "integer"},
                "operating_temp_max_c": {"type": "integer"},
                "qualification": {"type": "string"},
                "product_family": {"type": "string"},
                "top_n": {"type": "integer", "default": 5},
            },
            "required": ["industry"],
        },
        "fn": find_product_for_requirements,
    },
    {
        "name": "crm_get_reliability_insights_for_product",
        "description": "Get reliability insights (from QA, synced into CRM) for a product across opportunities/accounts.",
        "input_schema": {
            "type": "object",
            "properties": {"product_id": {"type": "string"}},
            "required": ["product_id"],
        },
        "fn": get_reliability_insights_for_product,
    },
]
