"""ERP MCP server tool implementations."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import erp, rows_to_dicts


# ---------------------------------------------------------------------------
# Customer master
# ---------------------------------------------------------------------------
def list_customers(
    external_account_id: str | None = None,
    customer_class: str | None = None,
    country: str | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    """List ERP customers with optional filters. customer_class: A/B/C/D."""
    conn = erp()
    where = []
    params: list[Any] = []
    if external_account_id:
        where.append("external_account_id = ?"); params.append(external_account_id)
    if customer_class:
        where.append("customer_class = ?"); params.append(customer_class)
    if country:
        where.append("country = ?"); params.append(country)
    sql = "SELECT * FROM customers"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY credit_limit DESC LIMIT ?"
    params.append(limit)
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return {"row_count": len(rows), "rows": rows_to_dicts(rows)}


# ---------------------------------------------------------------------------
# Sales orders
# ---------------------------------------------------------------------------
def list_sales_orders(
    external_account_id: str | None = None,
    customer_number: str | None = None,
    status: str | None = None,
    ordered_after: str | None = None,
    ordered_before: str | None = None,
    limit: int = 100,
) -> dict[str, Any]:
    """List sales orders.  Filter by customer (external account id or customer number), status, or order-date window."""
    conn = erp()
    where = []
    params: list[Any] = []
    if external_account_id:
        where.append("c.external_account_id = ?"); params.append(external_account_id)
    if customer_number:
        where.append("c.customer_number = ?"); params.append(customer_number)
    if status:
        where.append("so.status = ?"); params.append(status)
    if ordered_after:
        where.append("so.order_date >= ?"); params.append(ordered_after)
    if ordered_before:
        where.append("so.order_date <= ?"); params.append(ordered_before)
    sql = """
        SELECT so.id, so.order_number, c.customer_number, c.name AS customer_name, c.external_account_id,
               so.external_quote_number, so.order_date, so.status, so.grand_total, so.confirmed_delivery_date,
               so.actual_delivery_date, so.order_type
          FROM sales_orders so JOIN customers c ON c.id = so.customer_id
    """
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY so.order_date DESC LIMIT ?"
    params.append(limit)
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return {"row_count": len(rows), "rows": rows_to_dicts(rows)}


def order_booking_patterns(
    external_account_id: str | None = None,
    customer_number: str | None = None,
    group_by: str = "month",
) -> dict[str, Any]:
    """Booking pattern: order count and total $ per period (month or quarter) for an account.

    Use to answer 'order booking patterns for my accounts'.
    """
    conn = erp()
    where = []
    params: list[Any] = []
    if external_account_id:
        where.append("c.external_account_id = ?"); params.append(external_account_id)
    elif customer_number:
        where.append("c.customer_number = ?"); params.append(customer_number)
    if not where:
        return {"error": "Provide external_account_id or customer_number"}
    if group_by == "quarter":
        period_expr = "strftime('%Y', so.order_date) || '-Q' || ((CAST(strftime('%m', so.order_date) AS INTEGER) - 1) / 3 + 1)"
    else:
        period_expr = "strftime('%Y-%m', so.order_date)"
    sql = f"""
        SELECT {period_expr} AS period,
               COUNT(*) AS order_count,
               COALESCE(SUM(so.grand_total), 0) AS booked_amount,
               COALESCE(AVG(so.grand_total), 0) AS avg_order_size
          FROM sales_orders so JOIN customers c ON c.id = so.customer_id
         WHERE {' AND '.join(where)}
         GROUP BY period ORDER BY period
    """
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return {"row_count": len(rows), "rows": rows_to_dicts(rows)}


def get_order_detail(order_number: str | None = None, order_id: int | None = None) -> dict[str, Any]:
    """Get full sales order detail incl. line items."""
    conn = erp()
    if order_id:
        order = conn.execute("SELECT so.*, c.name AS customer_name, c.external_account_id FROM sales_orders so JOIN customers c ON c.id=so.customer_id WHERE so.id = ?", (order_id,)).fetchone()
    elif order_number:
        order = conn.execute("SELECT so.*, c.name AS customer_name, c.external_account_id FROM sales_orders so JOIN customers c ON c.id=so.customer_id WHERE so.order_number = ?", (order_number,)).fetchone()
    else:
        return {"error": "Provide order_number or order_id"}
    if not order:
        return {"error": "Order not found"}
    o = dict(order)
    lines = rows_to_dicts(conn.execute("""
        SELECT sol.*, it.item_number, it.name AS item_name, it.external_product_id
          FROM sales_order_lines sol JOIN items it ON it.id = sol.item_id
         WHERE sol.order_id = ?
         ORDER BY sol.line_number
    """, (o["id"],)).fetchall())
    conn.close()
    o["lines"] = lines
    return o


# ---------------------------------------------------------------------------
# Invoices & payments
# ---------------------------------------------------------------------------
def list_invoices(
    external_account_id: str | None = None,
    status: str | None = None,
    invoiced_after: str | None = None,
    invoiced_before: str | None = None,
    limit: int = 100,
) -> dict[str, Any]:
    """List invoices with status / date filters."""
    conn = erp()
    where = []
    params: list[Any] = []
    if external_account_id:
        where.append("c.external_account_id = ?"); params.append(external_account_id)
    if status:
        where.append("i.status = ?"); params.append(status)
    if invoiced_after:
        where.append("i.invoice_date >= ?"); params.append(invoiced_after)
    if invoiced_before:
        where.append("i.invoice_date <= ?"); params.append(invoiced_before)
    sql = """
        SELECT i.id, i.invoice_number, c.customer_number, c.name AS customer_name, c.external_account_id,
               i.invoice_date, i.due_date, i.total_amount, i.amount_paid, i.amount_outstanding,
               i.status, i.recognition_status, i.recognition_date, i.payment_terms
          FROM invoices i JOIN customers c ON c.id = i.customer_id
    """
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY i.invoice_date DESC LIMIT ?"
    params.append(limit)
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return {"row_count": len(rows), "rows": rows_to_dicts(rows)}


def ar_aging(as_of_date: str | None = None) -> dict[str, Any]:
    """Accounts-receivable aging buckets (0-30, 31-60, 61-90, >90 days) based on `due_date`."""
    if not as_of_date:
        from datetime import date
        as_of_date = date.today().isoformat()
    conn = erp()
    rows = conn.execute(f"""
        WITH outstanding AS (
            SELECT i.id, i.invoice_number, c.name AS customer_name, c.external_account_id,
                   i.amount_outstanding, julianday(?) - julianday(i.due_date) AS days_overdue
              FROM invoices i JOIN customers c ON c.id = i.customer_id
             WHERE i.amount_outstanding > 0
        )
        SELECT CASE
                 WHEN days_overdue <= 0  THEN '0-30 Current'
                 WHEN days_overdue <= 30 THEN '1-30 Overdue'
                 WHEN days_overdue <= 60 THEN '31-60 Overdue'
                 WHEN days_overdue <= 90 THEN '61-90 Overdue'
                 ELSE '90+ Overdue'
               END AS bucket,
               COUNT(*) AS invoice_count,
               ROUND(SUM(amount_outstanding), 2) AS amount
          FROM outstanding
         GROUP BY bucket
         ORDER BY bucket
    """, (as_of_date,)).fetchall()
    conn.close()
    return {"as_of_date": as_of_date, "row_count": len(rows), "rows": rows_to_dicts(rows)}


# ---------------------------------------------------------------------------
# Revenue analytics
# ---------------------------------------------------------------------------
def revenue_by_period(
    fiscal_year: int | None = None,
    fiscal_quarter: int | None = None,
    period_label: str | None = None,
    group_by: str = "customer",
    limit: int = 50,
) -> dict[str, Any]:
    """Revenue rollup by customer / product family / region / period.

    group_by: customer, product_family, region, period
    """
    conn = erp()
    where = []
    params: list[Any] = []
    if fiscal_year is not None:
        where.append("r.fiscal_year = ?"); params.append(fiscal_year)
    if fiscal_quarter is not None:
        where.append("r.fiscal_quarter = ?"); params.append(fiscal_quarter)
    if period_label:
        where.append("r.period = ?"); params.append(period_label)

    if group_by == "customer":
        sql = """SELECT c.name AS customer_name, c.external_account_id,
                        COUNT(*) AS txn_count,
                        ROUND(SUM(r.amount), 2) AS revenue
                   FROM revenue r JOIN customers c ON c.id = r.customer_id"""
        group = "GROUP BY c.id"
    elif group_by == "product_family":
        sql = """SELECT r.product_family, COUNT(*) AS txn_count, ROUND(SUM(r.amount), 2) AS revenue
                   FROM revenue r"""
        group = "GROUP BY r.product_family"
    elif group_by == "region":
        sql = """SELECT r.region, COUNT(*) AS txn_count, ROUND(SUM(r.amount), 2) AS revenue
                   FROM revenue r"""
        group = "GROUP BY r.region"
    elif group_by == "period":
        sql = """SELECT r.period, COUNT(*) AS txn_count, ROUND(SUM(r.amount), 2) AS revenue
                   FROM revenue r"""
        group = "GROUP BY r.period"
    else:
        return {"error": f"Unknown group_by: {group_by}"}

    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += f" {group} ORDER BY revenue DESC LIMIT ?"
    params.append(limit)
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return {"row_count": len(rows), "rows": rows_to_dicts(rows)}


def top_customers_by_revenue(
    fiscal_year: int | None = None,
    fiscal_quarter: int | None = None,
    period_label: str | None = None,
    top_n: int = 10,
) -> dict[str, Any]:
    """Top N customers by recognized revenue for an optional period."""
    return revenue_by_period(
        fiscal_year=fiscal_year, fiscal_quarter=fiscal_quarter,
        period_label=period_label, group_by="customer", limit=top_n,
    )


def revenue_yoy_comparison(
    year_a: int,
    quarter_a: int,
    year_b: int,
    quarter_b: int,
    key_accounts_only: bool = False,
    top_n: int = 25,
) -> dict[str, Any]:
    """Compare revenue between two fiscal quarters.

    For each customer, return revenue in period A, period B, $ delta, % delta.
    Set key_accounts_only=True to require the CRM `is_key_account` flag — note
    this requires the CRM DB to be available (joined externally via the
    analytics server in practice). Here we just return all customers; the
    analytics server can filter further.
    """
    conn = erp()
    rows = conn.execute("""
        SELECT c.external_account_id, c.name AS customer_name,
               COALESCE(SUM(CASE WHEN r.fiscal_year=? AND r.fiscal_quarter=? THEN r.amount ELSE 0 END), 0) AS revenue_a,
               COALESCE(SUM(CASE WHEN r.fiscal_year=? AND r.fiscal_quarter=? THEN r.amount ELSE 0 END), 0) AS revenue_b
          FROM revenue r JOIN customers c ON c.id = r.customer_id
         GROUP BY c.id
    """, (year_a, quarter_a, year_b, quarter_b)).fetchall()
    conn.close()
    results = []
    for r in rows:
        d = dict(r)
        if d["revenue_a"] == 0 and d["revenue_b"] == 0:
            continue
        d["delta_abs"] = round(d["revenue_b"] - d["revenue_a"], 2)
        d["delta_pct"] = (
            round((d["revenue_b"] - d["revenue_a"]) / d["revenue_a"] * 100, 1)
            if d["revenue_a"] > 0 else None
        )
        results.append(d)
    results.sort(key=lambda x: abs(x["delta_abs"]), reverse=True)
    return {
        "period_a": f"{year_a}-Q{quarter_a}",
        "period_b": f"{year_b}-Q{quarter_b}",
        "row_count": min(len(results), top_n),
        "rows": results[:top_n],
        "totals": {
            "revenue_a": round(sum(r["revenue_a"] for r in results), 2),
            "revenue_b": round(sum(r["revenue_b"] for r in results), 2),
        },
    }


# ---------------------------------------------------------------------------
# Tool schema definitions
# ---------------------------------------------------------------------------
TOOLS: list[dict] = [
    {
        "name": "erp_list_customers",
        "description": "List ERP customer master records, optionally filtered by external_account_id (CRM link), class (A/B/C/D), or country.",
        "input_schema": {
            "type": "object",
            "properties": {
                "external_account_id": {"type": "string", "description": "Salesforce account ID — the integration key"},
                "customer_class": {"type": "string", "enum": ["A", "B", "C", "D"]},
                "country": {"type": "string"},
                "limit": {"type": "integer", "default": 50},
            },
        },
        "fn": list_customers,
    },
    {
        "name": "erp_list_sales_orders",
        "description": "List sales orders. Filter by customer (external account id or ERP customer number), status, or order-date range.",
        "input_schema": {
            "type": "object",
            "properties": {
                "external_account_id": {"type": "string"},
                "customer_number": {"type": "string"},
                "status": {"type": "string"},
                "ordered_after": {"type": "string", "description": "ISO date"},
                "ordered_before": {"type": "string"},
                "limit": {"type": "integer", "default": 100},
            },
        },
        "fn": list_sales_orders,
    },
    {
        "name": "erp_order_booking_patterns",
        "description": "Order booking patterns for an account: order count and booked $ per month or quarter.",
        "input_schema": {
            "type": "object",
            "properties": {
                "external_account_id": {"type": "string"},
                "customer_number": {"type": "string"},
                "group_by": {"type": "string", "enum": ["month", "quarter"], "default": "month"},
            },
        },
        "fn": order_booking_patterns,
    },
    {
        "name": "erp_get_order_detail",
        "description": "Get a single sales order with all line items, customer, quote linkage.",
        "input_schema": {
            "type": "object",
            "properties": {
                "order_number": {"type": "string"},
                "order_id": {"type": "integer"},
            },
        },
        "fn": get_order_detail,
    },
    {
        "name": "erp_list_invoices",
        "description": "List invoices filtered by account, status, or invoice-date range.",
        "input_schema": {
            "type": "object",
            "properties": {
                "external_account_id": {"type": "string"},
                "status": {"type": "string"},
                "invoiced_after": {"type": "string"},
                "invoiced_before": {"type": "string"},
                "limit": {"type": "integer", "default": 100},
            },
        },
        "fn": list_invoices,
    },
    {
        "name": "erp_ar_aging",
        "description": "AR aging buckets (Current, 1-30, 31-60, 61-90, 90+) for all open invoices as of a given date.",
        "input_schema": {
            "type": "object",
            "properties": {"as_of_date": {"type": "string", "description": "ISO date; defaults to today"}},
        },
        "fn": ar_aging,
    },
    {
        "name": "erp_revenue_by_period",
        "description": "Recognized revenue rolled up by customer / product family / region / period for an optional fiscal year/quarter.",
        "input_schema": {
            "type": "object",
            "properties": {
                "fiscal_year": {"type": "integer"},
                "fiscal_quarter": {"type": "integer", "minimum": 1, "maximum": 4},
                "period_label": {"type": "string", "description": "e.g. 2026-Q1"},
                "group_by": {"type": "string", "enum": ["customer", "product_family", "region", "period"], "default": "customer"},
                "limit": {"type": "integer", "default": 50},
            },
        },
        "fn": revenue_by_period,
    },
    {
        "name": "erp_top_customers_by_revenue",
        "description": "Top N customers by recognized revenue, optionally for a specific fiscal year/quarter.",
        "input_schema": {
            "type": "object",
            "properties": {
                "fiscal_year": {"type": "integer"},
                "fiscal_quarter": {"type": "integer", "minimum": 1, "maximum": 4},
                "period_label": {"type": "string"},
                "top_n": {"type": "integer", "default": 10},
            },
        },
        "fn": top_customers_by_revenue,
    },
    {
        "name": "erp_revenue_yoy_comparison",
        "description": "Compare recognized revenue between two fiscal quarters per customer (e.g. Q1-2025 vs Q1-2026). Returns absolute and percentage deltas.",
        "input_schema": {
            "type": "object",
            "properties": {
                "year_a": {"type": "integer"},
                "quarter_a": {"type": "integer"},
                "year_b": {"type": "integer"},
                "quarter_b": {"type": "integer"},
                "key_accounts_only": {"type": "boolean", "default": False},
                "top_n": {"type": "integer", "default": 25},
            },
            "required": ["year_a", "quarter_a", "year_b", "quarter_b"],
        },
        "fn": revenue_yoy_comparison,
    },
]
