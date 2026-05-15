"""Analytics MCP server — cross-system joins and complex queries.

These tools deliberately span CRM + ERP + QA databases (using SQLite ATTACH)
to answer questions that single-system tools cannot.
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import CRM_DB, ERP_DB, QA_DB, rows_to_dicts


def _multi_conn() -> sqlite3.Connection:
    """Open a CRM connection and ATTACH the ERP and QA databases."""
    uri = f"file:{CRM_DB.as_posix()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    conn.execute(f"ATTACH DATABASE 'file:{ERP_DB.as_posix()}?mode=ro' AS erp")
    conn.execute(f"ATTACH DATABASE 'file:{QA_DB.as_posix()}?mode=ro' AS qa")
    return conn


# ---------------------------------------------------------------------------
# Top key accounts (combines CRM key flag with ERP revenue)
# ---------------------------------------------------------------------------
def top_key_accounts(
    top_n: int = 10,
    fiscal_year: int | None = None,
    fiscal_quarter: int | None = None,
    period_label: str | None = None,
    require_key_flag: bool = True,
) -> dict[str, Any]:
    """Top N accounts ranked by recognized revenue. Optionally restrict to CRM key accounts.

    Use to answer: 'Who are my top 10 key accounts?'
    """
    conn = _multi_conn()
    where = []
    params: list[Any] = []
    if fiscal_year is not None:
        where.append("r.fiscal_year = ?"); params.append(fiscal_year)
    if fiscal_quarter is not None:
        where.append("r.fiscal_quarter = ?"); params.append(fiscal_quarter)
    if period_label:
        where.append("r.period = ?"); params.append(period_label)
    if require_key_flag:
        where.append("a.is_key_account = 1")
    where_clause = ("WHERE " + " AND ".join(where)) if where else ""
    sql = f"""
        SELECT a.id AS account_id, a.name AS account_name, a.industry, a.segment, a.billing_country,
               a.is_key_account,
               COUNT(DISTINCT r.id) AS revenue_txns,
               ROUND(COALESCE(SUM(r.amount), 0), 2) AS total_revenue,
               (SELECT COUNT(*) FROM opportunities o WHERE o.account_id = a.id AND o.stage = 'Closed Won') AS closed_won_count,
               (SELECT ROUND(COALESCE(SUM(amount), 0), 2) FROM opportunities o WHERE o.account_id = a.id AND o.stage NOT LIKE 'Closed%') AS open_pipeline
          FROM accounts a
     LEFT JOIN erp.revenue r ON r.external_account_id = a.id
        {where_clause}
         GROUP BY a.id
         ORDER BY total_revenue DESC
         LIMIT ?
    """
    rows = conn.execute(sql, params + [top_n]).fetchall()
    conn.close()
    return {
        "criteria": {
            "fiscal_year": fiscal_year, "fiscal_quarter": fiscal_quarter,
            "period_label": period_label, "require_key_flag": require_key_flag,
        },
        "row_count": len(rows),
        "rows": rows_to_dicts(rows),
    }


# ---------------------------------------------------------------------------
# Revenue pattern change Q-over-Q (key accounts)
# ---------------------------------------------------------------------------
def revenue_pattern_change(
    year_a: int,
    quarter_a: int,
    year_b: int,
    quarter_b: int,
    key_accounts_only: bool = True,
    significant_change_threshold_pct: float = 25.0,
    top_n: int = 25,
) -> dict[str, Any]:
    """Identify accounts with significant revenue pattern changes between two quarters.

    Returns accounts whose absolute % change exceeds threshold (default 25 %),
    sorted by absolute delta.  Distinguishes 'growth', 'decline', 'new', 'lost'.
    """
    conn = _multi_conn()
    where_account = "WHERE a.is_key_account = 1" if key_accounts_only else ""
    rows = conn.execute(f"""
        SELECT a.id AS account_id, a.name AS account_name, a.industry, a.segment, a.is_key_account,
               COALESCE(SUM(CASE WHEN r.fiscal_year=? AND r.fiscal_quarter=? THEN r.amount ELSE 0 END), 0) AS revenue_a,
               COALESCE(SUM(CASE WHEN r.fiscal_year=? AND r.fiscal_quarter=? THEN r.amount ELSE 0 END), 0) AS revenue_b
          FROM accounts a
     LEFT JOIN erp.revenue r ON r.external_account_id = a.id
         {where_account}
         GROUP BY a.id
    """, (year_a, quarter_a, year_b, quarter_b)).fetchall()
    conn.close()

    results: list[dict] = []
    for r in rows:
        d = dict(r)
        if d["revenue_a"] == 0 and d["revenue_b"] == 0:
            continue
        if d["revenue_a"] == 0:
            d["change_type"] = "New revenue (no comparison base)"
            d["delta_pct"] = None
        elif d["revenue_b"] == 0:
            d["change_type"] = "Lost revenue"
            d["delta_pct"] = -100.0
        else:
            d["delta_pct"] = round((d["revenue_b"] - d["revenue_a"]) / d["revenue_a"] * 100, 1)
            if abs(d["delta_pct"]) < significant_change_threshold_pct:
                continue
            d["change_type"] = "Growth" if d["delta_pct"] > 0 else "Decline"
        d["delta_abs"] = round(d["revenue_b"] - d["revenue_a"], 2)
        d["revenue_a"] = round(d["revenue_a"], 2)
        d["revenue_b"] = round(d["revenue_b"], 2)
        results.append(d)

    results.sort(key=lambda x: abs(x["delta_abs"]), reverse=True)
    return {
        "period_a": f"{year_a}-Q{quarter_a}",
        "period_b": f"{year_b}-Q{quarter_b}",
        "threshold_pct": significant_change_threshold_pct,
        "row_count": min(len(results), top_n),
        "rows": results[:top_n],
    }


# ---------------------------------------------------------------------------
# Quote-to-revenue conversion analysis
# ---------------------------------------------------------------------------
def quote_to_revenue_conversion(
    period_start: str | None = None,
    period_end: str | None = None,
    min_quoted_amount: float = 500_000,
    top_n: int = 10,
    direction: str = "both",
) -> dict[str, Any]:
    """Identify accounts with the highest and lowest quote-to-revenue conversion.

    Conversion = (revenue recognized from quotes / total quoted amount on accepted+sent quotes).

    direction: 'both' (returns top + bottom), 'highest', 'lowest'
    """
    conn = _multi_conn()
    where_q = []
    params_q: list[Any] = []
    if period_start:
        where_q.append("q.created_date >= ?"); params_q.append(period_start)
    if period_end:
        where_q.append("q.created_date <= ?"); params_q.append(period_end)
    where_clause = ("WHERE " + " AND ".join(where_q)) if where_q else ""

    quotes_by_acct = {
        row[0]: row[1] for row in conn.execute(f"""
            SELECT q.account_id, ROUND(SUM(q.grand_total), 2) AS quoted_amount
              FROM quotes q
              {where_clause}
              {('AND' if where_clause else 'WHERE')} q.status IN ('Accepted', 'Sent', 'Approved')
             GROUP BY q.account_id
        """, params_q).fetchall()
    }
    revenue_by_acct = {
        row[0]: row[1] for row in conn.execute("""
            SELECT external_account_id, ROUND(SUM(amount), 2) AS revenue
              FROM erp.revenue GROUP BY external_account_id
        """).fetchall()
    }
    name_by_acct = {row[0]: (row[1], row[2], row[3]) for row in conn.execute(
        "SELECT id, name, industry, segment FROM accounts"
    ).fetchall()}
    conn.close()

    results: list[dict] = []
    for ext_id, qamt in quotes_by_acct.items():
        if qamt < min_quoted_amount:
            continue
        rev = revenue_by_acct.get(ext_id, 0)
        ratio = (rev / qamt) if qamt > 0 else None
        name, industry, segment = name_by_acct.get(ext_id, (None, None, None))
        results.append({
            "account_id": ext_id,
            "account_name": name,
            "industry": industry,
            "segment": segment,
            "quoted_amount": qamt,
            "recognized_revenue": rev,
            "conversion_ratio": round(ratio, 4) if ratio is not None else None,
            "conversion_pct": round(ratio * 100, 1) if ratio is not None else None,
        })

    results.sort(key=lambda x: x["conversion_ratio"] or 0)
    if direction == "highest":
        return {"row_count": top_n, "rows": list(reversed(results[-top_n:]))}
    elif direction == "lowest":
        return {"row_count": top_n, "rows": results[:top_n]}
    else:
        return {
            "lowest": results[:top_n],
            "highest": list(reversed(results[-top_n:])),
            "row_count": min(len(results), top_n * 2),
        }


# ---------------------------------------------------------------------------
# Order booking patterns (CRM-account view, ERP data)
# ---------------------------------------------------------------------------
def order_booking_patterns_by_account_name(
    account_name: str,
    group_by: str = "month",
) -> dict[str, Any]:
    """Order booking patterns for an account, looked up by CRM account name.

    Combines CRM (account lookup) + ERP (orders) for natural-language friendliness.
    """
    conn = _multi_conn()
    acct = conn.execute(
        "SELECT id, name, industry, segment FROM accounts WHERE name LIKE ? ORDER BY annual_revenue DESC LIMIT 1",
        (f"%{account_name}%",),
    ).fetchone()
    if not acct:
        conn.close()
        return {"error": f"No account matched name '{account_name}'"}
    if group_by == "quarter":
        period_expr = "strftime('%Y', so.order_date) || '-Q' || ((CAST(strftime('%m', so.order_date) AS INTEGER) - 1) / 3 + 1)"
    else:
        period_expr = "strftime('%Y-%m', so.order_date)"
    rows = conn.execute(f"""
        SELECT {period_expr} AS period, COUNT(*) AS order_count,
               ROUND(SUM(so.grand_total), 2) AS booked_amount
          FROM erp.sales_orders so
          JOIN erp.customers c ON c.id = so.customer_id
         WHERE c.external_account_id = ?
         GROUP BY period ORDER BY period
    """, (acct["id"],)).fetchall()
    conn.close()
    return {
        "account": dict(acct),
        "group_by": group_by,
        "row_count": len(rows),
        "rows": rows_to_dicts(rows),
    }


# ---------------------------------------------------------------------------
# Best product recommendation with reliability blended in
# ---------------------------------------------------------------------------
def recommend_product_for_customer_project(
    customer_name: str | None = None,
    industry: str | None = None,
    application: str | None = None,
    voltage_v: float | None = None,
    annual_volume: int | None = None,
    target_unit_price: float | None = None,
    operating_temp_min_c: int | None = None,
    operating_temp_max_c: int | None = None,
    qualification: str | None = None,
    product_family: str | None = None,
    top_n: int = 5,
    weight_reliability: float = 0.4,
) -> dict[str, Any]:
    """Cross-system product recommendation:
      1. Score products by CRM spec match (industry, voltage, temp, qualification, price).
      2. Blend in QA reliability score (weight_reliability default 0.4).
      3. Return top_n with combined score, fit notes, reliability score and grade.

    If `customer_name` is provided, the customer's industry overrides the
    `industry` argument when not supplied.
    """
    # Resolve customer industry if needed
    conn = _multi_conn()
    if customer_name and not industry:
        a = conn.execute(
            "SELECT industry FROM accounts WHERE name LIKE ? ORDER BY annual_revenue DESC LIMIT 1",
            (f"%{customer_name}%",),
        ).fetchone()
        if a:
            industry = a["industry"]

    if not industry:
        conn.close()
        return {"error": "Provide `industry` or `customer_name` to resolve industry."}

    # Pull all candidate products
    products = rows_to_dicts(conn.execute("SELECT * FROM products WHERE status = 'Active'").fetchall())

    # Reliability scores (latest per product)
    reliability = {
        row[0]: {"score": row[1], "grade": row[2], "recommendation": row[3]}
        for row in conn.execute(
            "SELECT external_product_id, score, score_grade, recommendation FROM qa.reliability_scores"
        ).fetchall()
    }
    conn.close()

    import json as _json
    scored: list[dict] = []
    for p in products:
        specs = _json.loads(p.get("design_specs") or "{}")
        notes = []
        fit_score = 0.0

        target_inds = (p.get("target_industries") or "").split(",")
        if industry in target_inds:
            fit_score += 25
            notes.append(f"Industry '{industry}' is target market.")
        if product_family and p["product_family"] == product_family:
            fit_score += 15
            notes.append("Exact product family match.")

        spec_temp = specs.get("operating_temp_c", [None, None])
        if operating_temp_min_c is not None and spec_temp[0] is not None:
            if spec_temp[0] <= operating_temp_min_c:
                fit_score += 15; notes.append(f"Min temp OK ({spec_temp[0]}°C ≤ {operating_temp_min_c}°C).")
            else:
                continue
        if operating_temp_max_c is not None and spec_temp[1] is not None:
            if spec_temp[1] >= operating_temp_max_c:
                fit_score += 15; notes.append(f"Max temp OK ({spec_temp[1]}°C ≥ {operating_temp_max_c}°C).")
            else:
                continue
        if voltage_v is not None:
            sv = specs.get("supply_voltage_v")
            if sv is not None and abs(sv - voltage_v) < 0.5:
                fit_score += 12; notes.append(f"Voltage match ({sv}V).")
        if qualification:
            sq = specs.get("qualification", "")
            if qualification in sq or sq in qualification:
                fit_score += 13; notes.append(f"Qualification match: {sq}.")
        if target_unit_price is not None:
            if p["list_price"] <= target_unit_price * 1.10:
                fit_score += 10
            elif p["list_price"] <= target_unit_price * 1.30:
                fit_score += 4

        # Reliability blend
        rel = reliability.get(p["id"])
        rel_score = rel["score"] if rel else 70.0
        # Normalize fit_score to 0-100 ish
        normalized_fit = min(100.0, fit_score)
        combined = (1 - weight_reliability) * normalized_fit + weight_reliability * rel_score

        scored.append({
            "product_id": p["id"],
            "sku": p["sku"],
            "name": p["name"],
            "family": p["product_family"],
            "category": p["product_category"],
            "list_price": p["list_price"],
            "target_industries": p["target_industries"],
            "specs": specs,
            "fit_score": round(normalized_fit, 1),
            "reliability_score": rel_score,
            "reliability_grade": rel["grade"] if rel else "—",
            "reliability_recommendation": rel["recommendation"] if rel else None,
            "combined_score": round(combined, 1),
            "fit_notes": notes,
        })
    scored.sort(key=lambda x: x["combined_score"], reverse=True)
    return {
        "criteria": {
            "customer_name": customer_name,
            "industry": industry,
            "application": application,
            "voltage_v": voltage_v,
            "operating_temp_min_c": operating_temp_min_c,
            "operating_temp_max_c": operating_temp_max_c,
            "qualification": qualification,
            "target_unit_price": target_unit_price,
            "annual_volume": annual_volume,
            "product_family": product_family,
            "weight_reliability": weight_reliability,
        },
        "row_count": min(len(scored), top_n),
        "rows": scored[:top_n],
    }


# ---------------------------------------------------------------------------
# Quarterly executive update — sales pipeline + revenue with everything joined
# ---------------------------------------------------------------------------
def quarterly_executive_update(
    fiscal_year: int,
    fiscal_quarter: int,
    prior_year_quarter: bool = True,
) -> dict[str, Any]:
    """Build a comprehensive quarterly executive update with:

      - Total recognized revenue for the quarter (+ prior-year comparison if enabled)
      - Revenue by industry, region, product family
      - Pipeline open by stage
      - Top 10 customers for the quarter
      - Closed won/lost summary
      - Top reliability concerns (high-return products)
    """
    conn = _multi_conn()
    period = f"{fiscal_year}-Q{fiscal_quarter}"
    prior_period = f"{fiscal_year - 1}-Q{fiscal_quarter}"

    total_rev = conn.execute(
        "SELECT COALESCE(SUM(amount), 0) FROM erp.revenue WHERE period = ?", (period,),
    ).fetchone()[0]
    prior_rev = conn.execute(
        "SELECT COALESCE(SUM(amount), 0) FROM erp.revenue WHERE period = ?", (prior_period,),
    ).fetchone()[0] if prior_year_quarter else None

    by_industry = rows_to_dicts(conn.execute("""
        SELECT a.industry, ROUND(SUM(r.amount), 2) AS revenue, COUNT(*) AS txns
          FROM erp.revenue r JOIN accounts a ON a.id = r.external_account_id
         WHERE r.period = ?
         GROUP BY a.industry ORDER BY revenue DESC
    """, (period,)).fetchall())

    by_family = rows_to_dicts(conn.execute("""
        SELECT r.product_family, ROUND(SUM(r.amount), 2) AS revenue
          FROM erp.revenue r WHERE r.period = ?
         GROUP BY r.product_family ORDER BY revenue DESC
    """, (period,)).fetchall())

    by_region = rows_to_dicts(conn.execute("""
        SELECT r.region, ROUND(SUM(r.amount), 2) AS revenue, COUNT(*) AS txns
          FROM erp.revenue r WHERE r.period = ?
         GROUP BY r.region ORDER BY revenue DESC LIMIT 10
    """, (period,)).fetchall())

    top_customers = rows_to_dicts(conn.execute("""
        SELECT c.name AS customer_name, c.external_account_id,
               ROUND(SUM(r.amount), 2) AS revenue
          FROM erp.revenue r JOIN erp.customers c ON c.id = r.customer_id
         WHERE r.period = ?
         GROUP BY c.id ORDER BY revenue DESC LIMIT 10
    """, (period,)).fetchall())

    pipeline = rows_to_dicts(conn.execute("""
        SELECT stage, COUNT(*) AS n,
               ROUND(SUM(amount), 2) AS amount,
               ROUND(SUM(amount * probability), 2) AS weighted
          FROM opportunities
         WHERE stage NOT LIKE 'Closed%'
         GROUP BY stage ORDER BY amount DESC
    """).fetchall())

    won_lost = rows_to_dicts(conn.execute(f"""
        SELECT stage, COUNT(*) AS n, ROUND(SUM(amount), 2) AS amount
          FROM opportunities
         WHERE stage IN ('Closed Won', 'Closed Lost')
           AND substr(closed_date, 1, 4) = ?
           AND ((cast(substr(closed_date, 6, 2) AS INTEGER) - 1) / 3 + 1) = ?
         GROUP BY stage
    """, (str(fiscal_year), fiscal_quarter)).fetchall())

    reliability_concerns = rows_to_dicts(conn.execute("""
        SELECT external_product_id, COUNT(*) AS rmas, ROUND(SUM(replacement_cost), 2) AS cost
          FROM qa.customer_returns
         WHERE return_date >= ? AND return_date <= ?
         GROUP BY external_product_id ORDER BY rmas DESC LIMIT 5
    """, (
        f"{fiscal_year}-{(fiscal_quarter - 1) * 3 + 1:02d}-01",
        f"{fiscal_year}-{fiscal_quarter * 3:02d}-31",
    )).fetchall())

    conn.close()

    return {
        "period": period,
        "prior_period": prior_period if prior_year_quarter else None,
        "totals": {
            "revenue": round(total_rev, 2),
            "prior_year_revenue": round(prior_rev, 2) if prior_rev is not None else None,
            "yoy_growth_pct": round((total_rev - prior_rev) / prior_rev * 100, 1) if prior_rev else None,
        },
        "revenue_by_industry": by_industry,
        "revenue_by_product_family": by_family,
        "revenue_by_region": by_region,
        "top_customers": top_customers,
        "pipeline_by_stage": pipeline,
        "closed_won_lost": won_lost,
        "top_reliability_concerns": reliability_concerns,
    }


# ---------------------------------------------------------------------------
# Customer returns linked to opportunities/accounts (cross-system)
# ---------------------------------------------------------------------------
def returns_increase_for_product(
    product_search: str,
    months_window: int = 6,
) -> dict[str, Any]:
    """For a product matched by name/SKU, return:
      - Returns trend by month
      - Comparison: last `months_window` months vs prior `months_window` months
      - Top accounts that returned the product
    """
    conn = _multi_conn()
    p = conn.execute(
        "SELECT id, name, sku, product_family FROM products WHERE name LIKE ? OR sku LIKE ? LIMIT 1",
        (f"%{product_search}%", f"%{product_search}%"),
    ).fetchone()
    if not p:
        conn.close()
        return {"error": f"No product matched '{product_search}'"}
    pid = p["id"]

    rows = rows_to_dicts(conn.execute("""
        SELECT strftime('%Y-%m', return_date) AS month,
               COUNT(*) AS rmas,
               SUM(qty_returned) AS qty,
               ROUND(SUM(replacement_cost), 2) AS cost
          FROM qa.customer_returns
         WHERE external_product_id = ?
         GROUP BY month ORDER BY month
    """, (pid,)).fetchall())

    # Recent vs prior window
    from datetime import date
    today = date(2026, 5, 15)  # data end
    from dateutil.relativedelta import relativedelta  # type: ignore
    try:
        recent_start = today - relativedelta(months=months_window)
        prior_start = recent_start - relativedelta(months=months_window)
    except Exception:
        # Fallback if dateutil not available
        recent_start = date(today.year, today.month, 1)
        prior_start = date(today.year, today.month, 1)

    recent_rmas = sum(r["rmas"] for r in rows if r["month"] >= recent_start.isoformat()[:7])
    prior_rmas = sum(r["rmas"] for r in rows if prior_start.isoformat()[:7] <= r["month"] < recent_start.isoformat()[:7])

    by_account = rows_to_dicts(conn.execute("""
        SELECT a.name AS account_name, a.industry, COUNT(*) AS rmas,
               SUM(cr.qty_returned) AS qty, ROUND(SUM(cr.replacement_cost), 2) AS cost
          FROM qa.customer_returns cr JOIN accounts a ON a.id = cr.external_account_id
         WHERE cr.external_product_id = ?
         GROUP BY a.id ORDER BY rmas DESC LIMIT 10
    """, (pid,)).fetchall())
    conn.close()

    delta_pct = None
    if prior_rmas > 0:
        delta_pct = round((recent_rmas - prior_rmas) / prior_rmas * 100, 1)
    return {
        "product": dict(p),
        "months_trend": rows,
        "comparison": {
            "recent_window": f"{recent_start.isoformat()[:7]} → {today.isoformat()[:7]}",
            "prior_window": f"{prior_start.isoformat()[:7]} → {recent_start.isoformat()[:7]}",
            "recent_rmas": recent_rmas,
            "prior_rmas": prior_rmas,
            "delta_pct": delta_pct,
            "increase_detected": delta_pct is not None and delta_pct > 25,
        },
        "top_accounts_returning": by_account,
    }


# ---------------------------------------------------------------------------
# Tool schema definitions
# ---------------------------------------------------------------------------
TOOLS: list[dict] = [
    {
        "name": "analytics_top_key_accounts",
        "description": "Top N key accounts ranked by recognized revenue. Combines CRM is_key_account flag with ERP revenue. Use for 'who are my top 10 key accounts'.",
        "input_schema": {
            "type": "object",
            "properties": {
                "top_n": {"type": "integer", "default": 10},
                "fiscal_year": {"type": "integer"},
                "fiscal_quarter": {"type": "integer", "minimum": 1, "maximum": 4},
                "period_label": {"type": "string"},
                "require_key_flag": {"type": "boolean", "default": True},
            },
        },
        "fn": top_key_accounts,
    },
    {
        "name": "analytics_revenue_pattern_change",
        "description": "Find key accounts with significant revenue changes between two quarters (e.g. Q1-2025 vs Q1-2026). Identifies growth/decline/new/lost patterns. Use for 'is there any big change in customer revenue pattern in Q1 compared to last year'.",
        "input_schema": {
            "type": "object",
            "properties": {
                "year_a": {"type": "integer"},
                "quarter_a": {"type": "integer"},
                "year_b": {"type": "integer"},
                "quarter_b": {"type": "integer"},
                "key_accounts_only": {"type": "boolean", "default": True},
                "significant_change_threshold_pct": {"type": "number", "default": 25.0},
                "top_n": {"type": "integer", "default": 25},
            },
            "required": ["year_a", "quarter_a", "year_b", "quarter_b"],
        },
        "fn": revenue_pattern_change,
    },
    {
        "name": "analytics_quote_to_revenue_conversion",
        "description": "Quote-to-revenue conversion ratio per account. Identifies customers with highest and lowest conversion.",
        "input_schema": {
            "type": "object",
            "properties": {
                "period_start": {"type": "string"},
                "period_end": {"type": "string"},
                "min_quoted_amount": {"type": "number", "default": 500000},
                "top_n": {"type": "integer", "default": 10},
                "direction": {"type": "string", "enum": ["both", "highest", "lowest"], "default": "both"},
            },
        },
        "fn": quote_to_revenue_conversion,
    },
    {
        "name": "analytics_order_booking_patterns_by_account_name",
        "description": "Order booking patterns over time for an account looked up by CRM account name (no need to know IDs).",
        "input_schema": {
            "type": "object",
            "properties": {
                "account_name": {"type": "string"},
                "group_by": {"type": "string", "enum": ["month", "quarter"], "default": "month"},
            },
            "required": ["account_name"],
        },
        "fn": order_booking_patterns_by_account_name,
    },
    {
        "name": "analytics_recommend_product_for_customer_project",
        "description": "Best-product recommendation that blends design-fit scoring (industry/voltage/temp/qualification/price) with QA reliability score. Use for 'what is the best product based on customer design project requirements'.",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_name": {"type": "string"},
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
                "weight_reliability": {"type": "number", "default": 0.4, "minimum": 0, "maximum": 1},
            },
        },
        "fn": recommend_product_for_customer_project,
    },
    {
        "name": "analytics_quarterly_executive_update",
        "description": "Build a comprehensive quarterly executive update: revenue (with YoY), revenue by industry/family/region, pipeline by stage, top customers, won/lost, reliability concerns. Use for 'generate sales quarterly update presentation'.",
        "input_schema": {
            "type": "object",
            "properties": {
                "fiscal_year": {"type": "integer"},
                "fiscal_quarter": {"type": "integer", "minimum": 1, "maximum": 4},
                "prior_year_quarter": {"type": "boolean", "default": True},
            },
            "required": ["fiscal_year", "fiscal_quarter"],
        },
        "fn": quarterly_executive_update,
    },
    {
        "name": "analytics_returns_increase_for_product",
        "description": "Determine whether customer returns are increasing for a product. Trend by month, recent-vs-prior window comparison, and top accounts returning. Use for 'is there any increase in customer returns due to this product issues'.",
        "input_schema": {
            "type": "object",
            "properties": {
                "product_search": {"type": "string", "description": "Product name or SKU substring"},
                "months_window": {"type": "integer", "default": 6},
            },
            "required": ["product_search"],
        },
        "fn": returns_increase_for_product,
    },
]
