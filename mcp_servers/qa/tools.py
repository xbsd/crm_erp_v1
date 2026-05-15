"""QA / Reliability MCP server tool implementations."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import qa, rows_to_dicts


# ---------------------------------------------------------------------------
# Reliability for a product
# ---------------------------------------------------------------------------
def get_product_reliability_report(external_product_id: str) -> dict[str, Any]:
    """Comprehensive reliability report for a single product:
      - Latest reliability score and grade
      - All reliability metrics by period (MTBF, MTTR, failure rate)
      - Recent failures (counts + severity breakdown)
      - Customer returns (counts + cost impact)
      - Compliance status
      - Test pass rates
    """
    conn = qa()
    score = conn.execute("""
        SELECT score, score_grade, recommendation, score_date, period
          FROM reliability_scores
         WHERE external_product_id = ?
         ORDER BY score_date DESC LIMIT 1
    """, (external_product_id,)).fetchone()

    metrics = rows_to_dicts(conn.execute("""
        SELECT period_label, mtbf_hours, mttr_hours, failure_rate_ppm, fit_rate, methodology
          FROM reliability_metrics
         WHERE external_product_id = ?
         ORDER BY period_start DESC LIMIT 12
    """, (external_product_id,)).fetchall())

    failures_summary = rows_to_dicts(conn.execute("""
        SELECT severity, COUNT(*) AS n, SUM(qty_affected) AS qty
          FROM failures
         WHERE external_product_id = ?
         GROUP BY severity
    """, (external_product_id,)).fetchall())
    failure_modes = rows_to_dicts(conn.execute("""
        SELECT failure_mode, COUNT(*) AS n
          FROM failures
         WHERE external_product_id = ?
         GROUP BY failure_mode ORDER BY n DESC LIMIT 6
    """, (external_product_id,)).fetchall())

    returns_summary = conn.execute("""
        SELECT COUNT(*) AS rma_count,
               COALESCE(SUM(qty_returned), 0) AS qty_returned,
               COALESCE(SUM(replacement_cost), 0) AS replacement_cost
          FROM customer_returns
         WHERE external_product_id = ?
    """, (external_product_id,)).fetchone()
    return_reasons = rows_to_dicts(conn.execute("""
        SELECT return_reason, COUNT(*) AS n
          FROM customer_returns
         WHERE external_product_id = ?
         GROUP BY return_reason ORDER BY n DESC
    """, (external_product_id,)).fetchall())

    compliance = rows_to_dicts(conn.execute("""
        SELECT standard, status, issue_date, expiry_date, certificate_number
          FROM compliance_records
         WHERE external_product_id = ?
         ORDER BY expiry_date DESC
    """, (external_product_id,)).fetchall())

    test_summary = conn.execute("""
        SELECT COUNT(*) AS runs, SUM(sample_size) AS samples,
               SUM(samples_failed) AS failed,
               ROUND(AVG(pass_rate), 4) AS avg_pass_rate
          FROM test_runs
         WHERE external_product_id = ?
    """, (external_product_id,)).fetchone()

    environmental = rows_to_dicts(conn.execute("""
        SELECT test_type, samples_tested, samples_passed, duration_hrs, passed
          FROM environmental_tests
         WHERE external_product_id = ?
         ORDER BY test_date DESC LIMIT 8
    """, (external_product_id,)).fetchall())

    conn.close()

    return {
        "product_id": external_product_id,
        "reliability_score": dict(score) if score else None,
        "metrics_by_quarter": metrics,
        "failures": {
            "by_severity": failures_summary,
            "by_mode": failure_modes,
        },
        "customer_returns": {
            "summary": dict(returns_summary) if returns_summary else None,
            "by_reason": return_reasons,
        },
        "compliance": compliance,
        "test_runs_summary": dict(test_summary) if test_summary else None,
        "environmental_tests": environmental,
    }


# ---------------------------------------------------------------------------
# Customer returns analysis
# ---------------------------------------------------------------------------
def customer_returns_by_product(
    period_start: str | None = None,
    period_end: str | None = None,
    external_product_id: str | None = None,
    top_n: int = 25,
) -> dict[str, Any]:
    """Aggregate customer returns by product (RMA count, qty, cost)."""
    conn = qa()
    where = []
    params: list[Any] = []
    if period_start:
        where.append("return_date >= ?"); params.append(period_start)
    if period_end:
        where.append("return_date <= ?"); params.append(period_end)
    if external_product_id:
        where.append("external_product_id = ?"); params.append(external_product_id)
    where_clause = ("WHERE " + " AND ".join(where)) if where else ""
    rows = conn.execute(f"""
        SELECT external_product_id,
               COUNT(*) AS rma_count,
               SUM(qty_returned) AS qty_returned,
               ROUND(SUM(replacement_cost), 2) AS replacement_cost,
               ROUND(AVG(days_in_service), 1) AS avg_days_in_service
          FROM customer_returns {where_clause}
         GROUP BY external_product_id
         ORDER BY rma_count DESC LIMIT ?
    """, params + [top_n]).fetchall()
    conn.close()
    return {"row_count": len(rows), "rows": rows_to_dicts(rows)}


def returns_trend_for_product(
    external_product_id: str,
    group_by: str = "month",
) -> dict[str, Any]:
    """Return-rate trend for one product (per month or quarter).

    Answers: 'Is there any increase in customer returns due to this product issues?'
    """
    conn = qa()
    if group_by == "quarter":
        period_expr = "strftime('%Y', return_date) || '-Q' || ((CAST(strftime('%m', return_date) AS INTEGER) - 1) / 3 + 1)"
    else:
        period_expr = "strftime('%Y-%m', return_date)"
    rows = conn.execute(f"""
        SELECT {period_expr} AS period,
               COUNT(*) AS rma_count,
               SUM(qty_returned) AS qty_returned,
               ROUND(SUM(replacement_cost), 2) AS replacement_cost
          FROM customer_returns
         WHERE external_product_id = ?
         GROUP BY period ORDER BY period
    """, (external_product_id,)).fetchall()
    conn.close()
    return {"row_count": len(rows), "rows": rows_to_dicts(rows)}


def customer_returns_by_account(
    external_account_id: str | None = None,
    period_start: str | None = None,
    period_end: str | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    """Customer return activity rolled up by account."""
    conn = qa()
    where = []
    params: list[Any] = []
    if external_account_id:
        where.append("external_account_id = ?"); params.append(external_account_id)
    if period_start:
        where.append("return_date >= ?"); params.append(period_start)
    if period_end:
        where.append("return_date <= ?"); params.append(period_end)
    where_clause = ("WHERE " + " AND ".join(where)) if where else ""
    rows = conn.execute(f"""
        SELECT external_account_id, COUNT(*) AS rma_count, SUM(qty_returned) AS qty,
               ROUND(SUM(replacement_cost), 2) AS replacement_cost
          FROM customer_returns {where_clause}
         GROUP BY external_account_id ORDER BY rma_count DESC LIMIT ?
    """, params + [limit]).fetchall()
    conn.close()
    return {"row_count": len(rows), "rows": rows_to_dicts(rows)}


# ---------------------------------------------------------------------------
# Reliability rankings
# ---------------------------------------------------------------------------
def list_reliability_scores(
    min_score: float | None = None,
    max_score: float | None = None,
    grade: str | None = None,
    limit: int = 30,
) -> dict[str, Any]:
    """List reliability scores across products, with optional score/grade filter."""
    conn = qa()
    where = []
    params: list[Any] = []
    if min_score is not None:
        where.append("score >= ?"); params.append(min_score)
    if max_score is not None:
        where.append("score <= ?"); params.append(max_score)
    if grade:
        where.append("score_grade = ?"); params.append(grade)
    sql = "SELECT * FROM reliability_scores"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY score DESC LIMIT ?"
    params.append(limit)
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return {"row_count": len(rows), "rows": rows_to_dicts(rows)}


# ---------------------------------------------------------------------------
# Failures
# ---------------------------------------------------------------------------
def list_failures(
    external_product_id: str | None = None,
    external_account_id: str | None = None,
    severity: str | None = None,
    period_start: str | None = None,
    period_end: str | None = None,
    limit: int = 100,
) -> dict[str, Any]:
    """List failure records with filters."""
    conn = qa()
    where = []
    params: list[Any] = []
    if external_product_id:
        where.append("external_product_id = ?"); params.append(external_product_id)
    if external_account_id:
        where.append("external_account_id = ?"); params.append(external_account_id)
    if severity:
        where.append("severity = ?"); params.append(severity)
    if period_start:
        where.append("failure_date >= ?"); params.append(period_start)
    if period_end:
        where.append("failure_date <= ?"); params.append(period_end)
    sql = "SELECT * FROM failures"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY failure_date DESC LIMIT ?"
    params.append(limit)
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return {"row_count": len(rows), "rows": rows_to_dicts(rows)}


# ---------------------------------------------------------------------------
# Test results summary
# ---------------------------------------------------------------------------
def test_run_summary(external_product_id: str, limit: int = 20) -> dict[str, Any]:
    """Recent test-run summary for a product."""
    conn = qa()
    rows = rows_to_dicts(conn.execute("""
        SELECT tr.run_number, ts.test_name, ts.test_type, ts.test_standard,
               tr.run_date, tr.sample_size, tr.samples_passed, tr.samples_failed, tr.pass_rate,
               tr.lab_location, tr.batch_lot_code
          FROM test_runs tr JOIN test_specifications ts ON ts.id = tr.spec_id
         WHERE tr.external_product_id = ?
         ORDER BY tr.run_date DESC LIMIT ?
    """, (external_product_id, limit)).fetchall())
    conn.close()
    return {"row_count": len(rows), "rows": rows}


# ---------------------------------------------------------------------------
# Tool schemas
# ---------------------------------------------------------------------------
TOOLS: list[dict] = [
    {
        "name": "qa_get_product_reliability_report",
        "description": "Comprehensive reliability report for a product: latest score, MTBF/MTTR trends, failures by severity & mode, customer returns, compliance, test pass rates.",
        "input_schema": {
            "type": "object",
            "properties": {
                "external_product_id": {"type": "string", "description": "Salesforce product ID"},
            },
            "required": ["external_product_id"],
        },
        "fn": get_product_reliability_report,
    },
    {
        "name": "qa_customer_returns_by_product",
        "description": "Aggregate customer returns by product. Filter by date range and/or product. Returns RMA count, units returned, replacement cost.",
        "input_schema": {
            "type": "object",
            "properties": {
                "period_start": {"type": "string"},
                "period_end": {"type": "string"},
                "external_product_id": {"type": "string"},
                "top_n": {"type": "integer", "default": 25},
            },
        },
        "fn": customer_returns_by_product,
    },
    {
        "name": "qa_returns_trend_for_product",
        "description": "Returns trend over time (month or quarter) for a single product.",
        "input_schema": {
            "type": "object",
            "properties": {
                "external_product_id": {"type": "string"},
                "group_by": {"type": "string", "enum": ["month", "quarter"], "default": "month"},
            },
            "required": ["external_product_id"],
        },
        "fn": returns_trend_for_product,
    },
    {
        "name": "qa_customer_returns_by_account",
        "description": "Customer-return activity rolled up by account (CRM external_account_id).",
        "input_schema": {
            "type": "object",
            "properties": {
                "external_account_id": {"type": "string"},
                "period_start": {"type": "string"},
                "period_end": {"type": "string"},
                "limit": {"type": "integer", "default": 50},
            },
        },
        "fn": customer_returns_by_account,
    },
    {
        "name": "qa_list_reliability_scores",
        "description": "List reliability scores across products (filter by score or grade A+/A/B/C/D/F).",
        "input_schema": {
            "type": "object",
            "properties": {
                "min_score": {"type": "number"},
                "max_score": {"type": "number"},
                "grade": {"type": "string"},
                "limit": {"type": "integer", "default": 30},
            },
        },
        "fn": list_reliability_scores,
    },
    {
        "name": "qa_list_failures",
        "description": "List failure records filtered by product, account, severity, or date range.",
        "input_schema": {
            "type": "object",
            "properties": {
                "external_product_id": {"type": "string"},
                "external_account_id": {"type": "string"},
                "severity": {"type": "string", "enum": ["Critical", "Major", "Minor", "Cosmetic"]},
                "period_start": {"type": "string"},
                "period_end": {"type": "string"},
                "limit": {"type": "integer", "default": 100},
            },
        },
        "fn": list_failures,
    },
    {
        "name": "qa_test_run_summary",
        "description": "Recent test runs for a product with sample size, pass/fail counts, and standards.",
        "input_schema": {
            "type": "object",
            "properties": {
                "external_product_id": {"type": "string"},
                "limit": {"type": "integer", "default": 20},
            },
            "required": ["external_product_id"],
        },
        "fn": test_run_summary,
    },
]
