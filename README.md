<div align="center">

# 🤖 MCP Enterprise Integration Demo

### Agentic AI across Salesforce CRM · ERP · QA / Reliability

*One natural-language question — four MCP servers — one executive answer.*

<br>

![Hero Architecture](docs/images/hero_architecture.png)

<br>

<p>
<img alt="Python" src="https://img.shields.io/badge/Python-3.11-3776AB?style=flat-square&logo=python&logoColor=white">
<img alt="MCP" src="https://img.shields.io/badge/MCP-1.27-FF6F00?style=flat-square">
<img alt="Claude" src="https://img.shields.io/badge/Claude-Sonnet%204.5-D97757?style=flat-square">
<img alt="SQLite" src="https://img.shields.io/badge/SQLite-3-003B57?style=flat-square&logo=sqlite&logoColor=white">
<img alt="Streamlit" src="https://img.shields.io/badge/Streamlit-1.32-FF4B4B?style=flat-square&logo=streamlit&logoColor=white">
<img alt="Plotly" src="https://img.shields.io/badge/Plotly-5.20-3F4F75?style=flat-square&logo=plotly&logoColor=white">
</p>

</div>

---

## ✨ What is this?

A working, end-to-end demo that proves an agentic-AI workflow can:

1. **Take a natural-language question** like _"Who are my top 10 key accounts?"_ or _"Is there any increase in customer returns for product TSN0124?"_
2. **Decide which of 33 tools** spread across **4 MCP servers** to call,
3. **Join data live across Salesforce CRM, an ERP, and a QA / reliability system**, and
4. **Return an executive-grade answer** with tables, visualizations, and a downloadable PowerPoint deck.

The data model and use cases come directly from the requirements PDF (Lead → Account → Opportunity → Quote → Order → Invoice → Revenue, with Product Reliability data flowing back into the CRM).

> **Why this matters:** real enterprises have answers locked in three different systems. This demo shows that a thin MCP layer plus Claude can collapse that boundary — no warehouse build, no ETL pipeline, no copy-and-paste between Salesforce and SAP.

---

## 🎯 Demo use cases (from the PDF)

| # | Audience | Question | Tools touched |
|---|---|---|---|
| 1 | 👔 Executive | Who are my top 10 key accounts? | `analytics_top_key_accounts` |
| 2 | 👔 Executive | Any big change in Q1 revenue YoY for key accounts? | `analytics_revenue_pattern_change` |
| 3 | 👔 Executive | Customers with highest / lowest quote→revenue conversion? | `analytics_quote_to_revenue_conversion` |
| 4 | 👔 Executive | Generate the Sales Quarterly Update presentation. | `analytics_quarterly_executive_update` |
| 5 | 💼 Sales | Best product for this customer design project? | `analytics_recommend_product_for_customer_project` |
| 6 | 💼 Sales | Reliability report for this product. | `crm_search_products` → `qa_customer_returns_by_product` → `qa_get_product_reliability_report` → `crm_get_reliability_insights_for_product` |
| 7 | 💼 Sales | Customer returns increase for this product? | `analytics_returns_increase_for_product` |
| 8 | 💼 Sales | Order booking patterns for my account. | `analytics_order_booking_patterns_by_account_name` |

All 8 questions are wired up as one-click examples in the Streamlit UI and in the CLI demo.

---

## 🚀 Quick start

```bash
# 1. Install
pip install -r requirements.txt

# 2. Build the three databases and populate them with ~2.5 years of synthetic data
python databases/init_databases.py
python data_generation/generate_data.py

# 3. Render charts + the Sales Quarterly Update .pptx
python scripts/generate_outputs.py

# 4. Set your Anthropic key
export ANTHROPIC_API_KEY=sk-ant-...

# 5. Run the demo in your preferred mode:
python scripts/demo_cli.py               # interactive menu, rich CLI
streamlit run ui/streamlit_app.py        # web UI with sidebar shortcuts
python tests/run_all_use_cases.py        # all 8 questions in one go
```

That's it — the agent will spawn the four MCP servers as subprocesses on demand.

---

## 📊 What you get out

The agent produces real artifacts. Here is what came out of one full test run.

<details open>
<summary><b>Top 10 key accounts</b> — single tool call to <code>analytics_top_key_accounts</code></summary>

![Top Accounts](docs/images/chart_top_accounts.png)

</details>

<details>
<summary><b>Q1 2026 vs Q1 2025 revenue pattern change</b> — key accounts only</summary>

![YoY Revenue](docs/images/chart_yoy_revenue.png)

Boeing **+9,136 %**, Medtronic **+465 %**, Volkswagen **+365 %**. Lockheed Martin **-62.5 %**, Raytheon **-100 %**.

</details>

<details>
<summary><b>Quote → revenue conversion</b> — which accounts close and which don't</summary>

![Conversion](docs/images/chart_conversion.png)

</details>

<details>
<summary><b>Customer returns trend</b> — is the temperature sensor TSN0124 getting worse?</summary>

![Returns Trend](docs/images/chart_returns_tsn0124.png)

</details>

<details>
<summary><b>Open pipeline by stage</b> & <b>Q1 2026 revenue by industry</b></summary>

<table>
<tr>
<td><img src="docs/images/chart_pipeline_funnel.png" alt="Pipeline"></td>
<td><img src="docs/images/chart_industry_donut.png" alt="Industry mix"></td>
</tr>
</table>

</details>

<details>
<summary><b>Recognized revenue by quarter</b> — full 2024 → 2026 series</summary>

![Quarterly Revenue](docs/images/chart_quarterly_revenue.png)

</details>

Plus a downloadable **9-slide Sales Quarterly Update PowerPoint** (`outputs/sales_quarterly_update_2026-Q1.pptx`), generated by `analytics_quarterly_executive_update` → `python-pptx`.

---

## 🖥️ Enterprise AI Workbench (Streamlit UI)

Six-page application with a custom design system, live agent orchestration, and drill-down views.

### 📊 Executive Dashboard

KPI strip, top-account ranking, quarterly revenue trend, industry mix, pipeline funnel, top movers, narrative insight cards, and a reliability watch-list — all on one screen with a persona switcher.

![Executive Dashboard](docs/images/ui_dashboard.png)

### 🤖 AI Assistant

Multi-turn conversational interface. Per-conversation history in the sidebar, persona switcher, model selector (Sonnet 4.5 / Opus 4.7 / Haiku 4.5), suggested prompts filtered by persona, live tool-call streaming inside `st.status`, right-panel "Conversation insights" with server pills + sequenced tool trace + suggested follow-ups, and "online" status indicators for each of the four MCP servers in the header.

![AI Assistant](docs/images/ui_assistant.png)

### 👥 Customer 360

Pick an account → see CRM + ERP + QA together. Hero card with avatar, key-account flag, and inline KPIs; tabs for Overview / CRM (opportunities + quotes) / ERP (orders + invoices + AR aging) / QA (returns) / Ask AI; booking-pattern chart; contact list; "Ask AI" deep-links that auto-open the Assistant with a pre-filled prompt.

![Customer 360](docs/images/ui_customer360.png)

### 🔬 Product Reliability Hub

Per-product circular reliability score (color-coded by grade), MTBF / failure-rate dual-axis trend, failure-mode distribution, returns-by-reason ranking, affected accounts table, compliance status with expiry pills, qualification-testing table. Sidebar shows a watch-list of products below 75. CTA generates a one-page reliability briefing via the AI Assistant.

![Product Reliability](docs/images/ui_reliability.png)

### 🔧 Tool Catalog

All 33 MCP tools grouped by server with color-coded headers and search/filter. Each tool expands to show its description, JSON-Schema-derived input table, and a built-in "Try it" form so you can invoke any tool manually with form-validated inputs and inspect the raw JSON response.

![Tool Catalog](docs/images/ui_catalog.png)

### ⚙️ System Health

Four MCP-server status cards with row-count badges, per-database expandable table-row inventory with charts, Anthropic runtime configuration (model, max iterations, API key status), and a live session-scoped agent activity log.

![System Health](docs/images/ui_system_health.png)

### Design system

Custom CSS layer with design tokens for color, spacing, and typography. Server-color identity (CRM = blue, ERP = green, QA = purple, Analytics = orange) is used consistently across tool cards, status strips, and section headers. KPI cards use a 4 px accent stripe and uppercase eyebrow labels. Status pills carry a colored dot and dimmed background. Dataframes, expanders, tabs, and chat bubbles are all themed to match.

```
ui/
├── streamlit_app.py        # entry — st.navigation() router
├── theme.py                # design tokens + global CSS injection
├── widgets.py              # kpi_card, tool_call_card, status_pill, account_card, ...
├── data_access.py          # cached, direct (non-MCP) reads for dashboards
└── pages/
    ├── dashboard.py        # Executive Dashboard
    ├── assistant.py        # Multi-turn AI chat with live tool trace
    ├── customer360.py      # CRM + ERP + QA per account
    ├── reliability.py      # Product Reliability Hub
    ├── catalog.py          # 33-tool browser with "Try it"
    └── system.py           # MCP server status + DB stats + activity log
```

---

## 🧭 How the agent routes questions

Heat-map of which MCP server answered each of the 8 use cases (generated from the actual end-to-end run):

![Tool Routing](docs/images/tool_routing.png)

Notice how the agent picks the **cross-system Analytics server** for most questions but happily chains together CRM + QA tools when it needs to (use case #6 — find a product → find returns for it → pull the full reliability report → check the CRM-side insights).

---

## 🏗️ Architecture deep-dive

### The four MCP servers

| Server | Module | Tools | Owns |
|---|---|---|---|
| 🟦 **Salesforce CRM** | `mcp_servers.crm.server` | 10 | Leads, Accounts, Contacts, Opportunities, Products, Pricebook, Quotes, Quote Line Items, plus revenue & reliability sync tables |
| 🟩 **ERP System** | `mcp_servers.erp.server` | 9 | Customer master, Items master, Sales Orders, Invoices, Payments, GL entries, recognized Revenue |
| 🟪 **QA / Reliability** | `mcp_servers.qa.server` | 7 | Test specs, Test runs, Test results, Reliability metrics (MTBF/MTTR/FIT), Failures, Customer Returns, Environmental tests, Compliance records, Reliability scores |
| 🟧 **Analytics** | `mcp_servers.analytics.server` | 7 | Cross-system joins via SQLite `ATTACH` — top key accounts, YoY patterns, quote→revenue conversion, product-fit + reliability, quarterly exec update, returns trend |

Each is a standalone stdio process that the agent spawns on demand.

### Cross-system integration model

Every CRM `account.id` lives as the **`external_account_id`** in the ERP customer master, and on every QA failure / return record. CRM `product.id` lives as ERP `external_product_id`. Accepted CRM quotes carry an `external_order_id` link to the ERP order they spawned, and the ERP order carries the inverse `external_quote_id`. Revenue rows propagate the `external_account_id` so analytics joins are free.

```
 CRM accounts.id  ─────────────►  ERP customers.external_account_id
                  ─────────────►  QA failures.external_account_id
                  ─────────────►  QA customer_returns.external_account_id

 CRM products.id  ─────────────►  ERP items.external_product_id
                  ─────────────►  QA test_specifications.external_product_id
                  ─────────────►  QA reliability_metrics.external_product_id

 CRM quotes.id   ◄─────────────►  ERP sales_orders.external_quote_id

 ERP invoices    ─────────────►  CRM quote_revenue_sync (back-sync)
 QA scores       ─────────────►  CRM reliability_insights_sync (back-sync)
```

This mirrors how a real Salesforce↔SAP↔Quality-System integration is wired.

### Agent loop

1. User prompt + tool catalog (the 33 MCP tools, each tagged with its server) is sent to **Claude Sonnet 4.5**.
2. Claude returns either a final answer or a list of `tool_use` blocks.
3. For each `tool_use`, the orchestrator routes the call to the right MCP server over stdio, gets JSON back, and feeds it as a `tool_result` block.
4. Repeat until Claude emits `stop_reason: end_turn`.

Typical run: **1 – 3 iterations, 1 – 5 tool calls, 15 – 35 seconds wallclock**.

---

## 🧱 Tech stack

| Layer            | Choice                              | Why                                                        |
|------------------|-------------------------------------|------------------------------------------------------------|
| Databases        | SQLite × 3 (CRM / ERP / QA)         | Three isolated systems, zero infra — copies the topology   |
| MCP servers      | Python + official `mcp` SDK 1.27    | Standard stdio MCP protocol — same wire format as Claude Desktop |
| Agent            | Anthropic Claude Sonnet 4.5         | Best tool-use model for multi-step reasoning               |
| Synthetic data   | `Faker` + curated industry reference | Real Fortune-1000 names, real semiconductor taxonomy, real test standards |
| Charts           | Plotly + Kaleido                    | Interactive HTML for the UI, PNG for the deck              |
| Presentations    | `python-pptx`                       | 16:9 executive deck, programmatically built                |
| Web UI           | Streamlit                           | One file, zero JS, instant demo                            |
| CLI              | Rich                                | Live tool-call streaming with colors and tables            |

---

## 📦 Data overview

| Database | Tables | Rows (approx) |
|----------|--------|---------------|
| 🟦 CRM   | 11 | ~14,000 — 92 accounts (25 key), 132 products (15 flagged problematic), 563 leads, 2,048 opportunities, 2,975 quotes, 7,435 line items |
| 🟩 ERP   | 8  | ~5,000 — 92 customers, 132 items, 860 sales orders, 850 invoices, 1,939 revenue rows, GL entries, payments |
| 🟪 QA    | 9  | ~80,000 — 630 test specs, 2,481 test runs, **74,430 sample-level test results**, 1,320 reliability metrics, 785 failures, 452 customer returns |

**Time window:** `2024-01-01 → 2026-05-15` (today).

**Calibration:** Q1-25 vs Q1-26 deltas are large enough to surface real changes; account revenue follows a Pareto distribution with the top 10 key accounts dominating; ~12 % of products are intentionally given elevated failure rates so the reliability and returns questions return interesting results.

**Realism:** account names are real publicly-listed companies (Tesla, Lockheed Martin, Bosch, Medtronic…); product categories follow standard semiconductor taxonomy (DC-DC converters, Hall sensors, AEC-Q100 MCUs, SiC MOSFETs…); test standards are real (JESD22-A108, MIL-STD-883, AEC-Q100); failure modes are textbook FMEA.

---

## 📂 Repo layout

```
crm_erp_v1/
├── databases/                       # SQLite DBs + schemas
│   ├── schema_{crm,erp,qa}.sql
│   ├── {crm,erp,qa}.db              # generated
│   └── init_databases.py
├── data_generation/                 # Realistic synthetic-data generator
│   ├── reference_data.py            # Real company names, product taxonomy, standards
│   └── generate_data.py
├── mcp_servers/                     # Four MCP servers (stdio)
│   ├── common.py                    # Shared DB helpers
│   ├── server_base.py               # Shared MCP scaffolding
│   ├── crm/        {tools,server}.py
│   ├── erp/        {tools,server}.py
│   ├── qa/         {tools,server}.py
│   └── analytics/  {tools,server}.py
├── agent/                           # Agentic AI orchestrator
│   ├── mcp_client.py                # Connects to all 4 MCP servers over stdio
│   ├── orchestrator.py              # Anthropic Claude + tool-use loop
│   ├── visualizations.py            # Plotly charts (PNG + HTML)
│   └── presentation.py              # python-pptx executive deck
├── ui/streamlit_app.py              # Web demo
├── scripts/
│   ├── demo_cli.py                  # Rich-formatted CLI demo
│   ├── generate_outputs.py          # Render all charts + .pptx
│   ├── make_hero_image.py           # README hero diagram
│   └── make_routing_image.py        # README routing heat-map
├── tests/
│   ├── use_cases.py                 # The 8 PDF questions as prompts
│   └── run_all_use_cases.py         # Run all 8 end-to-end, save outputs
├── docs/images/                     # README assets (committed)
└── outputs/                         # Generated charts + .pptx (gitignored)
```

---

## ▶️ Run modes

### 1. CLI demo

```bash
python scripts/demo_cli.py              # interactive menu of the 8 questions
python scripts/demo_cli.py 4            # run use case #4 directly
python scripts/demo_cli.py "Show me Lockheed Martin's order trend by quarter"
```

You get live, color-coded tool-call streaming:

```
  → Analytics (cross-system)::analytics_order_booking_patterns_by_account_name(account_name='Lockheed Martin', ...)
    ✓ analytics_order_booking_patterns_by_account_name returned in 0.04s
  → Salesforce CRM::crm_get_account_summary(account_name='Lockheed Martin')
    ✓ crm_get_account_summary returned in 0.01s
  → Salesforce CRM::crm_list_opportunities(account_id='0010015LBS7KA1P48IL', stage=None, ...)
    ✓ crm_list_opportunities returned in 0.01s
───── Answer ─────
## Lockheed Martin Analysis: Q1 2026 Revenue Decline
...
```

### 2. Streamlit web UI

```bash
streamlit run ui/streamlit_app.py
```

Sidebar buttons for all 8 PDF questions, a custom-question text area, live tool-call expanders, inline charts, and a download button for the quarterly deck.

### 3. Full test harness

```bash
python tests/run_all_use_cases.py
# → outputs/use_case_runs.md   (human-readable transcript of all 8 questions)
# → outputs/use_case_runs.json (full trace incl. arguments and previews)
```

---

## 🧪 Example: full agent transcript

> **Q:** _Lockheed Martin shows declining Q1 revenue YoY. Pull their booking pattern and the open pipeline so I can see what's coming._

```
Iter 1  →  Analytics (cross-system) :: analytics_order_booking_patterns_by_account_name  (0.04s)
Iter 2  →  Salesforce CRM           :: crm_get_account_summary                           (0.01s)
Iter 2  →  Salesforce CRM           :: crm_list_opportunities                            (0.01s)
Iter 3  →  (final answer)
```

> ## Lockheed Martin Analysis: Q1 2026 Revenue Decline
>
> **Source:** ERP booking data + Salesforce CRM pipeline
>
> ### Key Findings
> **Q1 2026 booking patterns show a sharp decline:**
> - Q1 2026: Only $1.996M booked across 3 orders
> - Q1 2025: $15.17M booked across 7 orders
> - **YoY decline:** -87 % in Q1 booking value
>
> **Total relationship metrics (CRM):**
> - Open pipeline: $21.38M
> - Historical closed-won: $157.14M lifetime
> - Total opportunities: 56
>
> ### Open Pipeline Breakdown (sorted by stage maturity)
> | Opportunity | Stage | Amount | Probability | Close Date | Family |
> |---|---|---|---|---|---|
> | MCU Design Win | Negotiation | $1.34M | 75 % | Nov 2026 | MCU |
> | MCU New Project | Proposal | $1.88M | 50 % | Sep 2026 | MCU |
> | …  | …  | …  | …  | …  | …  |
>
> **Weighted pipeline value: ~$7.6M**

The agent picked the right tools, joined data from two systems, and wrote a clean exec summary — all from a single English sentence.

---

## 🛠️ Built-in MCP tools (33 total)

<details>
<summary><b>🟦 Salesforce CRM (10)</b></summary>

- `crm_list_accounts` — Filter by industry, segment, country, key flag
- `crm_get_account_summary` — One account with pipeline, won amount, contacts
- `crm_list_opportunities` — Multi-filter on stage / owner / amount / close date
- `crm_pipeline_summary_by_stage` — Rollup with weighted and unweighted $
- `crm_opportunity_funnel` — Won/Lost counts and $ for a period
- `crm_list_quotes` — Filter by account / status / date
- `crm_get_quote_detail` — Quote + line items + ERP revenue sync
- `crm_search_products` — Catalog filter by family / category / temp / qualification / price
- `crm_find_product_for_requirements` — Score-rank products by design fit
- `crm_get_reliability_insights_for_product` — QA-synced insights for the product

</details>

<details>
<summary><b>🟩 ERP (9)</b></summary>

- `erp_list_customers` — By external account id / class / country
- `erp_list_sales_orders` — Multi-filter
- `erp_order_booking_patterns` — Order count + $ per month / quarter
- `erp_get_order_detail` — Order + lines + customer + quote link
- `erp_list_invoices` — Multi-filter
- `erp_ar_aging` — Aging buckets (Current / 1-30 / 31-60 / 61-90 / 90+)
- `erp_revenue_by_period` — Group by customer / product family / region / period
- `erp_top_customers_by_revenue` — Top N
- `erp_revenue_yoy_comparison` — Two-quarter customer-level comparison

</details>

<details>
<summary><b>🟪 QA / Reliability (7)</b></summary>

- `qa_get_product_reliability_report` — Score, MTBF, failures, returns, compliance, tests
- `qa_customer_returns_by_product` — Aggregate by product
- `qa_returns_trend_for_product` — Month / quarter trend
- `qa_customer_returns_by_account` — Rolled up by account
- `qa_list_reliability_scores` — Filter by score / grade
- `qa_list_failures` — Multi-filter
- `qa_test_run_summary` — Recent runs with pass/fail counts

</details>

<details>
<summary><b>🟧 Analytics (7) — cross-system</b></summary>

- `analytics_top_key_accounts` — CRM key flag + ERP revenue → top N
- `analytics_revenue_pattern_change` — Two-quarter delta for key accounts
- `analytics_quote_to_revenue_conversion` — Highest / lowest converting accounts
- `analytics_order_booking_patterns_by_account_name` — Lookup by CRM name
- `analytics_recommend_product_for_customer_project` — Design fit + QA reliability blend
- `analytics_quarterly_executive_update` — Everything needed for the exec deck
- `analytics_returns_increase_for_product` — Trend + recent-vs-prior + accounts

</details>

---

## ⚙️ Configuration

| Variable | Default | Purpose |
|---|---|---|
| `ANTHROPIC_API_KEY` | _(required)_ | Claude API key |
| `CRM_DEMO_MODEL` | `claude-sonnet-4-5` | Override the model (e.g. `claude-opus-4-7`) |
| `ANTHROPIC_BASE_URL` | `https://api.anthropic.com` | Useful for proxies / corp gateways |

---

## 📝 License

Sample/demo code. Use freely.

---

<div align="center">

**Built to show that MCP turns three siloed enterprise systems into one conversational interface.**

</div>
