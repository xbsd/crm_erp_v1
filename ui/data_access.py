"""Direct (non-MCP) data access for dashboard pages.

Pages that don't need agentic reasoning can call the tool functions directly
for sub-100ms responses. This keeps dashboard renders fast.

The MCP layer is still used by the AI Assistant page so the demo shows
the protocol in action.
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path
from typing import Any

import streamlit as st

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from mcp_servers.analytics.tools import (  # noqa: E402
    order_booking_patterns_by_account_name,
    quarterly_executive_update,
    quote_to_revenue_conversion,
    recommend_product_for_customer_project,
    returns_increase_for_product,
    revenue_pattern_change,
    top_key_accounts,
)
from mcp_servers.common import CRM_DB, ERP_DB, QA_DB  # noqa: E402
from mcp_servers.crm.tools import (  # noqa: E402
    get_account_summary,
    list_accounts,
    list_opportunities,
    list_quotes,
    pipeline_summary_by_stage,
)
from mcp_servers.erp.tools import (  # noqa: E402
    ar_aging,
    list_invoices,
    list_sales_orders,
    revenue_by_period,
)
from mcp_servers.qa.tools import (  # noqa: E402
    customer_returns_by_account,
    customer_returns_by_product,
    get_product_reliability_report,
    list_reliability_scores,
)


# ---------------------------------------------------------------------------
# Cached lookups
# ---------------------------------------------------------------------------
@st.cache_data(ttl=120)
def all_accounts() -> list[dict]:
    return list_accounts(limit=500)["rows"]


@st.cache_data(ttl=120)
def all_products() -> list[dict]:
    conn = sqlite3.connect(CRM_DB)
    conn.row_factory = sqlite3.Row
    rows = [dict(r) for r in conn.execute(
        "SELECT id, sku, name, product_family, product_category, list_price, status, target_industries FROM products"
    ).fetchall()]
    conn.close()
    return rows


@st.cache_data(ttl=120)
def db_table_counts() -> dict[str, dict[str, int]]:
    counts: dict[str, dict[str, int]] = {}
    for label, path in [("CRM", CRM_DB), ("ERP", ERP_DB), ("QA", QA_DB)]:
        conn = sqlite3.connect(path)
        tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchall()]
        counts[label] = {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in tables}
        conn.close()
    return counts


@st.cache_data(ttl=120)
def headline_kpis() -> dict[str, Any]:
    """KPIs for the executive dashboard top strip."""
    # Latest full quarter is 2026-Q1 based on the demo data window
    cur = quarterly_executive_update(2026, 1, prior_year_quarter=True)
    pipeline_total = sum(p["amount"] for p in cur["pipeline_by_stage"])
    pipeline_count = sum(p["n"] for p in cur["pipeline_by_stage"])
    return {
        "period": cur["period"],
        "prior_period": cur["prior_period"],
        "revenue_current": cur["totals"]["revenue"],
        "revenue_prior": cur["totals"]["prior_year_revenue"],
        "yoy_pct": cur["totals"]["yoy_growth_pct"],
        "pipeline_total": pipeline_total,
        "pipeline_count": pipeline_count,
        "top_customer": cur["top_customers"][0]["customer_name"] if cur["top_customers"] else "—",
        "top_customer_revenue": cur["top_customers"][0]["revenue"] if cur["top_customers"] else 0,
        "by_industry": cur["revenue_by_industry"],
        "by_family": cur["revenue_by_product_family"],
        "by_region": cur["revenue_by_region"],
        "pipeline_by_stage": cur["pipeline_by_stage"],
        "top_customers": cur["top_customers"],
        "reliability_concerns": cur["top_reliability_concerns"],
    }


@st.cache_data(ttl=120)
def revenue_quarterly_series() -> list[dict]:
    rows = revenue_by_period(group_by="period")["rows"]
    return sorted(rows, key=lambda r: r["period"])


@st.cache_data(ttl=120)
def top_key_accounts_cached(n: int = 10) -> list[dict]:
    return top_key_accounts(top_n=n)["rows"]


@st.cache_data(ttl=120)
def revenue_pattern_change_cached(threshold: float = 25.0) -> dict:
    return revenue_pattern_change(2025, 1, 2026, 1, key_accounts_only=True,
                                   significant_change_threshold_pct=threshold,
                                   top_n=20)


@st.cache_data(ttl=120)
def returns_top_products_cached(top_n: int = 10) -> list[dict]:
    return customer_returns_by_product(top_n=top_n)["rows"]


@st.cache_data(ttl=120)
def reliability_low_scores(limit: int = 10) -> list[dict]:
    return list_reliability_scores(max_score=75, limit=limit)["rows"]


@st.cache_data(ttl=120)
def ar_aging_cached() -> list[dict]:
    return ar_aging()["rows"]


# Re-export tool fns for pages
__all__ = [
    "all_accounts", "all_products", "db_table_counts", "headline_kpis",
    "revenue_quarterly_series", "top_key_accounts_cached",
    "revenue_pattern_change_cached", "returns_top_products_cached",
    "reliability_low_scores", "ar_aging_cached",
    # Pass-through
    "list_accounts", "list_opportunities", "list_quotes", "get_account_summary",
    "pipeline_summary_by_stage", "list_sales_orders", "list_invoices",
    "revenue_by_period", "ar_aging",
    "get_product_reliability_report", "customer_returns_by_product",
    "customer_returns_by_account", "list_reliability_scores",
    "top_key_accounts", "revenue_pattern_change", "quote_to_revenue_conversion",
    "order_booking_patterns_by_account_name", "recommend_product_for_customer_project",
    "quarterly_executive_update", "returns_increase_for_product",
]
