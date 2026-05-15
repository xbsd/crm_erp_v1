"""Generate visualizations and the Sales Quarterly Update presentation
from the data in the databases.

Run after data generation. Produces:
  outputs/chart_top_accounts.{png,html}
  outputs/chart_yoy_revenue.{png,html}
  outputs/chart_conversion.{png,html}
  outputs/chart_booking_lockheed.{png,html}
  outputs/chart_returns_tsn0124.{png,html}
  outputs/chart_pipeline_funnel.{png,html}
  outputs/chart_industry_donut.{png,html}
  outputs/chart_quarterly_revenue.{png,html}
  outputs/sales_quarterly_update_2026-Q1.pptx
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUTPUTS = ROOT / "outputs"
OUTPUTS.mkdir(exist_ok=True)

from agent.visualizations import (
    booking_pattern_line,
    conversion_scatter,
    pipeline_funnel,
    returns_trend_line,
    revenue_by_industry_donut,
    revenue_by_quarter_line,
    top_accounts_bar,
    yoy_comparison_bar,
)
from agent.presentation import build_quarterly_update_deck
from mcp_servers.analytics.tools import (
    order_booking_patterns_by_account_name,
    quarterly_executive_update,
    quote_to_revenue_conversion,
    returns_increase_for_product,
    revenue_pattern_change,
    top_key_accounts,
)
from mcp_servers.erp.tools import revenue_by_period


def main() -> None:
    print(">> Top key accounts chart")
    top = top_key_accounts(top_n=10)
    p, h = top_accounts_bar(top["rows"], OUTPUTS / "chart_top_accounts")
    print(f"   {p}, {h}")

    print(">> YoY revenue chart (Q1-25 vs Q1-26)")
    yoy = revenue_pattern_change(2025, 1, 2026, 1, key_accounts_only=True,
                                  significant_change_threshold_pct=0, top_n=15)
    p, h = yoy_comparison_bar(yoy["rows"], yoy["period_a"], yoy["period_b"],
                              OUTPUTS / "chart_yoy_revenue")
    print(f"   {p}, {h}")

    print(">> Quote-to-revenue conversion chart")
    conv = quote_to_revenue_conversion(top_n=8, min_quoted_amount=500_000)
    p, h = conversion_scatter(conv["lowest"], conv["highest"],
                              OUTPUTS / "chart_conversion")
    print(f"   {p}, {h}")

    print(">> Lockheed Martin booking pattern chart")
    book = order_booking_patterns_by_account_name("Lockheed Martin", group_by="quarter")
    p, h = booking_pattern_line(book["rows"], book["account"]["name"],
                                 OUTPUTS / "chart_booking_lockheed")
    print(f"   {p}, {h}")

    print(">> Returns trend for TSN0124")
    ret = returns_increase_for_product("TSN0124")
    p, h = returns_trend_line(ret["months_trend"], ret["product"]["name"],
                               OUTPUTS / "chart_returns_tsn0124")
    print(f"   {p}, {h}")

    print(">> Pipeline funnel chart")
    exec_update = quarterly_executive_update(2026, 1)
    p, h = pipeline_funnel(exec_update["pipeline_by_stage"],
                           OUTPUTS / "chart_pipeline_funnel")
    print(f"   {p}, {h}")

    print(">> Industry donut chart")
    p, h = revenue_by_industry_donut(exec_update["revenue_by_industry"],
                                     exec_update["period"],
                                     OUTPUTS / "chart_industry_donut")
    print(f"   {p}, {h}")

    print(">> Quarterly revenue line chart")
    rev_qtr = revenue_by_period(group_by="period")
    # Sort chronologically
    rev_qtr["rows"].sort(key=lambda r: r["period"])
    p, h = revenue_by_quarter_line(rev_qtr["rows"], OUTPUTS / "chart_quarterly_revenue")
    print(f"   {p}, {h}")

    print(">> Sales Quarterly Update deck (Q1 2026)")
    deck = build_quarterly_update_deck(exec_update)
    print(f"   {deck}")
    print("=== Done ===")


if __name__ == "__main__":
    main()
