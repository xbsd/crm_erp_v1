# Data Model Reference

This document explains how the application maps to the PDF data model (`info/AI Data Model and Questions.pdf`) and walks through every database table, integration key, and use-case routing decision.

The same content is rendered interactively at **/data-model** in the web UI, along with live row counts and column metadata pulled directly from the SQLite databases.

---

## 1. The end-to-end process

The PDF describes an eight-step business flow that the application implements end-to-end:

```
1. Lead Generation   ─►  2. Account Mgmt   ─►  3. Opportunity   ─►  4. Quote Mgmt
       (CRM)                (CRM)                (CRM)                (CRM)
                                                                            │
                                                                            ▼
8. Quality & Reliability  ◄─── 7. Revenue Update ◄── 6. Invoice Mgmt ◄── 5. Order Processing
       (QA)                       to Salesforce        (ERP)              (ERP)
```

This means a single customer transaction touches all three back-end systems. The reliability feedback loop (step 8 → CRM) is the differentiator that makes the agent's product-recommendation answers smart: it blends design fit (CRM specs) with reliability evidence (QA scores).

---

## 2. Three databases, three roles

### 🟦 Salesforce CRM (front office) — `databases/crm.db`

| Table | Rows | Purpose | PDF entity |
|---|---:|---|---|
| `users` | 40 | Sales reps & managers | (Salesforce User) |
| `accounts` | 92 | Customer master record, key-account flag | **Account** |
| `contacts` | 301 | Contacts tied to accounts | (Salesforce Contact) |
| `leads` | 563 | Lead capture + qualification | **Lead** |
| `opportunities` | 1,966 | Pipeline with close-stage | **Opportunity** |
| `products` | 132 | Product catalog with design specs | **Product** |
| `pricebook_entries` | 396 | Pricelist variants | **Pricebook** |
| `quotes` | 2,856 | Customer quotes | **Quote** |
| `quote_line_items` | 7,137 | Quote line detail | (Quote Line Item) |
| `quote_revenue_sync` | 756 | Revenue pushed from ERP onto Quote | ✦ ERP → CRM feedback |
| `reliability_insights_sync` | 396 | QA score pushed back onto product/opp/account | ✦ QA → CRM feedback |

### 🟩 ERP System (back office) — `databases/erp.db`

| Table | Rows | Purpose | PDF entity |
|---|---:|---|---|
| `customers` | 92 | ERP customer master (1-1 with CRM accounts) | **Customer** |
| `items` | 132 | ERP item master (1-1 with CRM products) | **Items** |
| `sales_orders` | 776 | Sales order header | **Sales Order** |
| `sales_order_lines` | 1,958 | Sales order detail | (SO Line) |
| `invoices` | 756 | Customer invoices | **Invoice** |
| `invoice_lines` | 1,907 | Invoice detail | (Invoice Line) |
| `payments` | 669 | Payment receipts | (Payment) |
| `gl_entries` | 1,512 | GL journal entries | **Accounting / GL** |
| `revenue` | 1,763 | Recognized revenue per period | **Revenue** |

### 🟪 QA / Reliability — `databases/qa.db`

| Table | Rows | Purpose | PDF entity |
|---|---:|---|---|
| `test_specifications` | 635 | Per-product test definitions | **Test Results (spec)** |
| `test_runs` | 2,514 | Executions of test specs | (Test Run) |
| `test_results` | 75,420 | Sample-level pass/fail outcomes | **Test Results** |
| `reliability_metrics` | 1,320 | MTBF, MTTR, FIT, failure rate by quarter | **Reliability Metrics** |
| `failures` | 863 | Failure records with root cause | **Failure Rates** |
| `customer_returns` | 552 | RMAs linked to product + account | (Customer Returns) |
| `environmental_tests` | 474 | Thermal / vibration / HAST | **Environmental Data** |
| `compliance_records` | 591 | UL · CE · AEC-Q100 · ISO certifications | **Compliance Data** |
| `reliability_scores` | 132 | Composite 0–100 score + grade per product | (Reliability Score) |

---

## 3. Cross-system integration keys

Three integration columns glue everything together — exactly as the PDF's "System Integration Overview" section specifies.

```
CRM accounts.id   ─────►  ERP customers.external_account_id
                  ─────►  QA failures.external_account_id
                  ─────►  QA customer_returns.external_account_id

CRM products.id   ─────►  ERP items.external_product_id
                  ─────►  QA test_specifications.external_product_id
                  ─────►  QA reliability_metrics.external_product_id
                  ─────►  QA customer_returns.external_product_id
                  ─────►  QA reliability_scores.external_product_id

CRM quotes.id    ◄─────►  ERP sales_orders.external_quote_id      (Quote-to-Order link)
ERP invoices     ─────►   CRM quote_revenue_sync                  (Revenue back-sync)
QA scores        ─────►   CRM reliability_insights_sync           (Insight back-sync)
```

The Analytics MCP server uses `SQLite ATTACH` to query across all three databases in a single SQL statement, which is how cross-system tools like `analytics_top_key_accounts` and `analytics_quote_to_revenue_conversion` work.

---

## 4. The 8 PDF use cases — and which tools answer them

| # | Audience | Question (paraphrased) | Tool(s) the agent calls |
|---|---|---|---|
| 1 | Executive | Who are my top 10 key accounts? | `analytics_top_key_accounts` |
| 2 | Executive | Q1 revenue change YoY for key accounts? | `analytics_revenue_pattern_change` |
| 3 | Executive | Highest/lowest quote-to-revenue conversion? | `analytics_quote_to_revenue_conversion` |
| 4 | Executive | Quarterly executive update | `analytics_quarterly_executive_update` |
| 5 | Sales | Best product for customer design project | `analytics_recommend_product_for_customer_project` |
| 6 | Sales | Reliability report for product | `crm_search_products` → `qa_customer_returns_by_product` → `qa_get_product_reliability_report` → `crm_get_reliability_insights_for_product` |
| 7 | Sales | Customer returns increase for product | `analytics_returns_increase_for_product` |
| 8 | Sales | Order booking patterns for account | `analytics_order_booking_patterns_by_account_name` |

Use case #6 is the textbook multi-system orchestration: the agent finds candidate products in the CRM, asks the QA server for return data to identify the highest-volume return, pulls a full reliability profile from QA, and finally crosses back to the CRM-synced insights table. Every tool call appears in the **Live Agent Trace** panel.

---

## 5. The 33 MCP tools

### 🟦 Salesforce CRM (10 tools)

| Tool | Purpose |
|---|---|
| `crm_list_accounts` | Filter by industry / segment / country / key-flag |
| `crm_get_account_summary` | One account incl. pipeline, won amount, contacts |
| `crm_list_opportunities` | Multi-filter on stage / owner / amount / close date |
| `crm_pipeline_summary_by_stage` | Rollup with weighted + unweighted $ |
| `crm_opportunity_funnel` | Won/Lost counts and $ for a period |
| `crm_list_quotes` | Filter by account / status / date |
| `crm_get_quote_detail` | Quote + line items + ERP-synced revenue |
| `crm_search_products` | Catalog filter by family / category / temp / qualification / price |
| `crm_find_product_for_requirements` | Score-rank products by design fit |
| `crm_get_reliability_insights_for_product` | QA-synced insights for the product |

### 🟩 ERP (9 tools)

| Tool | Purpose |
|---|---|
| `erp_list_customers` | By external account id / class / country |
| `erp_list_sales_orders` | Multi-filter |
| `erp_order_booking_patterns` | Order count + $ per month / quarter |
| `erp_get_order_detail` | Order + lines + customer + quote link |
| `erp_list_invoices` | Multi-filter |
| `erp_ar_aging` | Aging buckets (Current / 1-30 / 31-60 / 61-90 / 90+) |
| `erp_revenue_by_period` | Group by customer / product family / region / period |
| `erp_top_customers_by_revenue` | Top N |
| `erp_revenue_yoy_comparison` | Two-quarter customer-level comparison |

### 🟪 QA / Reliability (7 tools)

| Tool | Purpose |
|---|---|
| `qa_get_product_reliability_report` | Score, MTBF, failures, returns, compliance, tests |
| `qa_customer_returns_by_product` | Aggregate by product |
| `qa_returns_trend_for_product` | Month / quarter trend |
| `qa_customer_returns_by_account` | Rolled up by account |
| `qa_list_reliability_scores` | Filter by score / grade |
| `qa_list_failures` | Multi-filter |
| `qa_test_run_summary` | Recent runs with pass/fail counts |

### 🟧 Analytics — cross-system (7 tools)

| Tool | Purpose |
|---|---|
| `analytics_top_key_accounts` | CRM key flag + ERP revenue → top N |
| `analytics_revenue_pattern_change` | Two-quarter delta for key accounts |
| `analytics_quote_to_revenue_conversion` | Highest / lowest converting accounts |
| `analytics_order_booking_patterns_by_account_name` | Lookup by CRM name |
| `analytics_recommend_product_for_customer_project` | Design fit + QA reliability blend |
| `analytics_quarterly_executive_update` | Everything needed for the exec deck |
| `analytics_returns_increase_for_product` | Trend + recent-vs-prior + accounts |

---

## 6. Time window and data shape

- **Date range:** `2024-01-01 → 2026-05-15` (today)
- **Top 10 key accounts** account for the bulk of revenue (Pareto distribution)
- **Q1-2026 vs Q1-2025** is calibrated to surface large, realistic deltas
- **~12% of products** are seeded with elevated failure rates so the reliability questions return interesting results
- **Account names** are real Fortune-1000 companies (Tesla, Lockheed, Bosch, Medtronic…)
- **Product categories** follow standard semiconductor taxonomy
- **Test standards** are real (JESD22-A108, MIL-STD-883, AEC-Q100)
- **Failure modes** come from textbook FMEA

---

## 7. Where to look in the UI

| Page | What it shows |
|---|---|
| `/` (Dashboard) | KPIs, revenue trend, key accounts, YoY movers, reliability watch list, AR aging |
| `/assistant` | AI Assistant with **Live Agent Trace** — see every tool call across servers |
| `/customer-360` | Single-customer hub: opportunities, quotes, orders, invoices, returns |
| `/reliability` | Per-product reliability score, MTBF/failure-rate trend, return reasons, compliance |
| `/tools` | All 33 MCP tools with form-based "Try it" invocation |
| `/data-model` | This document, rendered live with table row counts and sample previews |
| `/system` | MCP server health + database inventory + Anthropic runtime |

---

## 8. Running the application

```bash
# 1. One-time setup
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. Build databases and seed synthetic data (only first time)
python databases/init_databases.py
python data_generation/generate_data.py

# 3. (Optional) render charts + PowerPoint deck
python scripts/generate_outputs.py

# 4. Make sure ANTHROPIC_API_KEY is set
#    The webapp auto-loads it from ~/.env, then ./.env (project local)
#    Verify:  python -c "import os; print(bool(os.environ.get('ANTHROPIC_API_KEY')))"

# 5. Run the new sophisticated FastAPI web app
python scripts/run_webapp.py --port 8000

# 6. Open the browser
open http://127.0.0.1:8000
```

The legacy Streamlit UI (`ui/streamlit_app.py`) is still available as `streamlit run ui/streamlit_app.py` but the new FastAPI app under `webapp/` is the recommended interface.
