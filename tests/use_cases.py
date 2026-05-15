"""The 8 use case questions from the PDF, as agent test prompts."""
from __future__ import annotations

USE_CASES: list[dict] = [
    # --- Executive ---
    {
        "id": "exec_1",
        "audience": "Executive",
        "title": "Top 10 key accounts",
        "question": (
            "Who are my top 10 key accounts? Use recognized revenue from the ERP system "
            "and include each account's industry, total revenue, and current open pipeline."
        ),
        "tags": ["accounts", "revenue", "pipeline"],
    },
    {
        "id": "exec_2",
        "audience": "Executive",
        "title": "Q1 revenue change YoY (key accounts)",
        "question": (
            "Is there any big change in customer revenue pattern in Q1 2026 compared to Q1 2025 for key accounts? "
            "Show me the accounts with the largest absolute and percentage changes (both growth and decline)."
        ),
        "tags": ["revenue", "yoy", "key-accounts"],
    },
    {
        "id": "exec_3",
        "audience": "Executive",
        "title": "Quote-to-revenue conversion",
        "question": (
            "Give me the customers with the highest and lowest quote-to-revenue conversion. "
            "Include the quoted amount, recognized revenue, and conversion percentage."
        ),
        "tags": ["quote", "revenue", "conversion"],
    },
    {
        "id": "exec_4",
        "audience": "Executive",
        "title": "Quarterly executive update Q1 2026",
        "question": (
            "Generate a Sales Quarterly Update for Q1 2026 based on opportunity pipeline and recognized revenue. "
            "Cover: total revenue with YoY growth, revenue by industry and product family, "
            "open pipeline by stage, top 10 customers, and any reliability concerns."
        ),
        "tags": ["quarterly", "presentation"],
    },
    # --- Sales ---
    {
        "id": "sales_1",
        "audience": "Sales",
        "title": "Best product for customer design project",
        "question": (
            "I'm working an opportunity with Tesla, Inc. for a new EV powertrain program. "
            "They need an automotive-qualified power IC operating from -40°C to 125°C, "
            "supply voltage 12V, target price around $4 per unit, annual volume 500,000 units. "
            "What is the best product based on these design project requirements? "
            "Include the reliability score for the recommended part."
        ),
        "tags": ["product-recommendation", "design-fit", "reliability"],
    },
    {
        "id": "sales_2",
        "audience": "Sales",
        "title": "Reliability report for product",
        "question": (
            "Get me the reliability report for our highest-volume Temperature Sensor product. "
            "Find the one that has the most customer returns and pull its full reliability profile: "
            "score, MTBF, failure modes, returns, compliance."
        ),
        "tags": ["reliability-report"],
    },
    {
        "id": "sales_3",
        "audience": "Sales",
        "title": "Customer returns increase due to product",
        "question": (
            "Is there any increase in customer returns due to issues with the Temperature Sensor TSN0124 product? "
            "Show me the trend over time, compare recent vs prior windows, and tell me which accounts are returning it."
        ),
        "tags": ["returns", "trend"],
    },
    {
        "id": "sales_4",
        "audience": "Sales",
        "title": "Order booking patterns for account",
        "question": (
            "Show me the order booking patterns for Lockheed Martin — order count and booked amount by quarter. "
            "Also flag any unusual peaks or dips."
        ),
        "tags": ["orders", "booking"],
    },
]
