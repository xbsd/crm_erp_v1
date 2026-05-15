# MCP Enterprise Integration Demo — CRM + ERP + QA + AI Agent

End-to-end demo of an agentic-AI system that answers executive and sales
questions by orchestrating tool calls across **four MCP servers** (Salesforce
CRM, ERP, QA/Reliability, and a cross-system Analytics server).

Implements the data model and use cases from
`AI_Data_Model_and_Questions.pdf`: Lead → Account → Opportunity → Quote →
Order → Invoice → Revenue, with Product Reliability data flowing back into
opportunities and accounts.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                  Natural-language question                          │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│            Claude Sonnet 4.5  (Anthropic API)                       │
│            • picks tools, calls them, synthesizes answer            │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ stdio (MCP protocol)
        ┌───────────┬──────────┴──────────┬───────────────┐
        ▼           ▼                     ▼               ▼
┌───────────────┐ ┌───────────────┐ ┌───────────────┐ ┌───────────────┐
│   CRM MCP     │ │   ERP MCP     │ │   QA MCP      │ │ Analytics MCP │
│   10 tools    │ │   9 tools     │ │   7 tools     │ │   7 tools     │
└──────┬────────┘ └──────┬────────┘ └──────┬────────┘ └──────┬────────┘
       │                 │                 │                 │
       ▼                 ▼                 ▼                 ▼ (joins all 3)
   crm.db            erp.db            qa.db
   (Salesforce)      (Customers,       (Tests, MTBF,
   Accounts,         Sales Orders,     Failures, Returns,
   Opps, Quotes,     Invoices, GL,     Compliance,
   Products)         Payments,         Reliability Scores)
                     Revenue)
```

## Demo questions (from the PDF)

**Executive:**
1. Who are my top 10 key accounts?
2. Is there any big change in customer revenue pattern in Q1 2026 vs Q1 2025?
3. Customers with highest / lowest quote-to-revenue conversion.
4. Generate a Sales Quarterly Update presentation (with visualizations).

**Sales:**
5. What is the best product for this customer design project? (industry, voltage, temp, qualification, price, reliability)
6. Get me the reliability report for this product.
7. Is there any increase in customer returns for this product?
8. Order booking patterns for my account.

## Tech stack

| Layer            | Choice                            | Why                                  |
|------------------|-----------------------------------|--------------------------------------|
| Databases        | SQLite × 3 (CRM / ERP / QA)       | Mimics 3 isolated systems, zero setup |
| MCP servers      | Python + official `mcp` SDK 1.27  | Standard stdio MCP protocol           |
| Agent            | Anthropic Claude Sonnet 4.5       | Tool-use orchestration                |
| Data generation  | Faker + curated industry data     | Realistic semiconductor / industrial scenario |
| Visualizations   | Plotly (PNG via Kaleido)          | Interactive HTML + slide-ready PNG    |
| Presentations    | python-pptx                       | 16:9 executive deck                   |
| UI               | Streamlit + Rich (CLI)            | Two demo modes                        |

## Repo layout

```
crm_erp_v1/
├── databases/                  # SQLite DBs + schemas
│   ├── schema_crm.sql / crm.db
│   ├── schema_erp.sql / erp.db
│   ├── schema_qa.sql  / qa.db
│   └── init_databases.py
├── data_generation/            # Realistic synthetic-data generator
│   ├── reference_data.py       # Real company names, product taxonomy, standards
│   └── generate_data.py
├── mcp_servers/                # Four MCP servers (stdio)
│   ├── common.py               # Shared DB helpers
│   ├── server_base.py          # Shared MCP scaffolding
│   ├── crm/{tools,server}.py
│   ├── erp/{tools,server}.py
│   ├── qa/{tools,server}.py
│   └── analytics/{tools,server}.py
├── agent/                      # Agentic AI orchestrator
│   ├── mcp_client.py           # Connects to all 4 MCP servers over stdio
│   ├── orchestrator.py         # Anthropic Claude + tool loop
│   ├── visualizations.py       # Plotly charts
│   └── presentation.py         # python-pptx deck generator
├── ui/
│   └── streamlit_app.py        # Interactive web demo
├── scripts/
│   ├── demo_cli.py             # CLI demo
│   └── generate_outputs.py     # Render all charts + presentation
├── tests/
│   ├── use_cases.py            # The 8 PDF questions as agent prompts
│   └── run_all_use_cases.py    # Run all 8 end-to-end and save outputs
└── outputs/                    # Generated charts (.png/.html) + presentation (.pptx)
```

## Setup

```bash
pip install -r requirements.txt           # one-time
python databases/init_databases.py        # creates the 3 DBs
python data_generation/generate_data.py   # populates them (~5 sec)
python scripts/generate_outputs.py        # renders charts + .pptx
```

API key required for the agent: `export ANTHROPIC_API_KEY=...`

## Run

```bash
# CLI demo: pick from menu, watch tool calls live
python scripts/demo_cli.py

# Run one specific use case (1-8)
python scripts/demo_cli.py 4

# Ask a custom question
python scripts/demo_cli.py "Show me Lockheed Martin's order trend by quarter"

# Run all 8 PDF questions and save full report
python tests/run_all_use_cases.py        # → outputs/use_case_runs.{json,md}

# Web UI
streamlit run ui/streamlit_app.py
```

## Data overview

| Database | Tables | Rows (approx)             |
|----------|--------|---------------------------|
| CRM      | 11     | ~14,000 (incl. 2 k opps, 3 k quotes, 7.4 k line items, 92 accounts, 132 products) |
| ERP      | 8      | ~5,000  (860 orders, 850 invoices, 1.9 k revenue rows, GL entries)               |
| QA       | 9      | ~80,000 (74 k test results, 1.3 k reliability metrics, 785 failures, 452 returns) |

**Time window:** 2024-01-01 → 2026-05-15 (today). Quarterly patterns are
calibrated so Q1-25 vs Q1-26 comparisons surface meaningful deltas, the
top-10 accounts emerge cleanly, and a subset of products carries
elevated failure / return rates for the reliability questions.

**Cross-system keys:** Every CRM `account.id` exists as an ERP
`customers.external_account_id`. Every CRM `product.id` exists as an ERP
`items.external_product_id`. Every accepted CRM quote that materialized
into an order has an ERP `sales_orders.external_quote_id` pointing back.
Revenue rows carry the `external_account_id` so analytics-server joins
work without ID translation.

## MCP servers

Each server is a standalone stdio process started by the agent:

| Server              | Module                          | Tools |
|---------------------|---------------------------------|-------|
| CRM                 | `mcp_servers.crm.server`        | 10    |
| ERP                 | `mcp_servers.erp.server`        | 9     |
| QA / Reliability    | `mcp_servers.qa.server`         | 7     |
| Analytics (joins)   | `mcp_servers.analytics.server`  | 7     |

The Analytics server uses SQLite `ATTACH` to combine all three databases
and answers cross-system questions (top key accounts by revenue, YoY
change for key accounts, quote→revenue conversion, product-fit + reliability
combined recommendation, quarterly executive update, returns-increase
analysis).

## Sample output

After running the test harness:

```
outputs/
├── use_case_runs.md                       # Full transcript of all 8 questions
├── use_case_runs.json
├── chart_top_accounts.png/.html
├── chart_yoy_revenue.png/.html
├── chart_conversion.png/.html
├── chart_booking_lockheed.png/.html
├── chart_returns_tsn0124.png/.html
├── chart_pipeline_funnel.png/.html
├── chart_industry_donut.png/.html
├── chart_quarterly_revenue.png/.html
└── sales_quarterly_update_2026-Q1.pptx    # 9-slide executive deck
```
