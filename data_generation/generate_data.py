"""Generate realistic synthetic data across CRM, ERP, and QA systems.

Design goals
------------
1. Cross-system referential integrity (CRM account id ↔ ERP customer.external_account_id ↔ QA failure.external_account_id).
2. Realistic temporal patterns spanning 2024-01-01 → 2026-05-15:
   - Some growth, some decline, seasonality, key-account dominance (Pareto).
3. Differentiated product reliability — a handful of products have elevated
   failure rates and return rates, others are best-in-class.
4. Q1-2026 vs Q1-2025 deltas large enough to surface in the executive query.
5. Variable quote-to-revenue conversion across accounts so the
   highest/lowest conversion query returns interesting results.
"""
from __future__ import annotations

import json
import random
import sqlite3
import string
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from faker import Faker

from reference_data import (
    ACCOUNT_UNIVERSE,
    COMPETITORS,
    COMPLIANCE_STANDARDS,
    FAILURE_MODES,
    INDUSTRY_REQUIREMENTS,
    LEAD_SOURCES,
    LOSS_REASONS,
    OPP_STAGES,
    PRODUCT_CATALOG,
    REGIONS,
    RETURN_REASONS,
    ROOT_CAUSE_CATEGORIES,
    SALES_ROLES,
    TEST_TYPES,
)

# Reproducibility
SEED = 20260515
random.seed(SEED)
fake = Faker()
Faker.seed(SEED)

ROOT = Path(__file__).parent.parent
DB_DIR = ROOT / "databases"

START_DATE = date(2024, 1, 1)
END_DATE = date(2026, 5, 15)

# ---------------------------------------------------------------------------
# ID factories — mimic Salesforce ID prefixes
# ---------------------------------------------------------------------------
def _sf_id(prefix: str, n: int) -> str:
    suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=12))
    return f"{prefix}{n:04d}{suffix}"


def make_user_id(n: int) -> str:    return _sf_id("005", n)
def make_account_id(n: int) -> str: return _sf_id("001", n)
def make_contact_id(n: int) -> str: return _sf_id("003", n)
def make_lead_id(n: int) -> str:    return _sf_id("00Q", n)
def make_product_id(n: int) -> str: return _sf_id("01t", n)
def make_pbe_id(n: int) -> str:     return _sf_id("01u", n)
def make_opp_id(n: int) -> str:     return _sf_id("006", n)
def make_quote_id(n: int) -> str:   return _sf_id("0Q0", n)
def make_qli_id(n: int) -> str:     return _sf_id("0QL", n)


def rand_date(start: date, end: date) -> date:
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, max(delta, 0)))


def quarter_label(d: date) -> str:
    return f"{d.year}-Q{(d.month - 1) // 3 + 1}"


def fiscal_quarter(d: date) -> tuple[int, int]:
    return d.year, (d.month - 1) // 3 + 1


def weighted_choice(pairs):
    items, weights = zip(*pairs)
    return random.choices(items, weights=weights, k=1)[0]


# ===========================================================================
# 1. Users (sales reps)
# ===========================================================================
def generate_users(conn: sqlite3.Connection) -> list[dict]:
    users: list[dict] = []
    n = 0
    vps = []
    managers = []
    for role, count in SALES_ROLES:
        for _ in range(count):
            first = fake.first_name()
            last = fake.last_name()
            uid = make_user_id(n)
            user = {
                "id": uid,
                "name": f"{first} {last}",
                "email": f"{first.lower()}.{last.lower()}@example-semiconductor.com",
                "role": role,
                "region": random.choice(REGIONS),
                "manager_id": None,
                "quota_annual": {
                    "VP Sales": 25_000_000,
                    "Sales Manager": 8_000_000,
                    "Account Executive": 2_500_000,
                    "Sales Engineer": 0,
                    "SDR": 500_000,
                }[role],
                "hire_date": rand_date(date(2018, 1, 1), date(2025, 6, 1)).isoformat(),
                "is_active": 1,
            }
            if role == "VP Sales":
                vps.append(user)
            elif role == "Sales Manager":
                user["manager_id"] = random.choice(vps)["id"] if vps else None
                managers.append(user)
            elif role in ("Account Executive", "Sales Engineer", "SDR"):
                user["manager_id"] = random.choice(managers)["id"] if managers else None
            users.append(user)
            n += 1
    conn.executemany(
        """INSERT INTO users (id, name, email, role, region, manager_id, quota_annual, hire_date, is_active)
           VALUES (:id, :name, :email, :role, :region, :manager_id, :quota_annual, :hire_date, :is_active)""",
        users,
    )
    return users


# ===========================================================================
# 2. Accounts (with hierarchy + key-account flags + ownership)
# ===========================================================================
def generate_accounts(conn: sqlite3.Connection, users: list[dict]) -> list[dict]:
    aes = [u for u in users if u["role"] == "Account Executive"]
    accounts: list[dict] = []
    for i, src in enumerate(ACCOUNT_UNIVERSE):
        annual_revenue = {
            "Enterprise": random.uniform(5_000_000_000, 200_000_000_000),
            "Mid-Market": random.uniform(200_000_000, 5_000_000_000),
            "SMB":        random.uniform(10_000_000, 200_000_000),
        }[src["segment"]]
        employees = {
            "Enterprise": random.randint(10_000, 500_000),
            "Mid-Market": random.randint(500, 10_000),
            "SMB":        random.randint(50, 500),
        }[src["segment"]]
        created = rand_date(date(2019, 1, 1), date(2023, 12, 31))
        acct = {
            "id": make_account_id(i),
            "name": src["name"],
            "industry": src["industry"],
            "type": "Customer" if random.random() < 0.85 else "Prospect",
            "segment": src["segment"],
            "annual_revenue": round(annual_revenue, 2),
            "employee_count": employees,
            "billing_country": src["country"],
            "billing_state": fake.state_abbr() if src["country"] == "USA" else "",
            "billing_city": fake.city(),
            "website": "https://www." + src["name"].lower().replace(" ", "").replace(",", "").replace(".", "")[:18] + ".com",
            "is_key_account": 1 if src["key"] else 0,
            "owner_id": random.choice(aes)["id"],
            "parent_account_id": None,
            "created_date": created.isoformat(),
            "last_activity_date": rand_date(date(2026, 1, 1), END_DATE).isoformat(),
            "description": f"{src['industry']} {src['segment']} account headquartered in {src['country']}.",
        }
        accounts.append(acct)

    conn.executemany(
        """INSERT INTO accounts (id, name, industry, type, segment, annual_revenue, employee_count,
                                 billing_country, billing_state, billing_city, website, is_key_account,
                                 owner_id, parent_account_id, created_date, last_activity_date, description)
           VALUES (:id, :name, :industry, :type, :segment, :annual_revenue, :employee_count,
                   :billing_country, :billing_state, :billing_city, :website, :is_key_account,
                   :owner_id, :parent_account_id, :created_date, :last_activity_date, :description)""",
        accounts,
    )
    return accounts


# ===========================================================================
# 3. Contacts (1-5 per account)
# ===========================================================================
def generate_contacts(conn: sqlite3.Connection, accounts: list[dict]) -> list[dict]:
    titles = [
        "VP Engineering", "Director of Engineering", "Hardware Engineering Manager",
        "Senior Hardware Engineer", "Principal Engineer", "Procurement Manager",
        "Strategic Sourcing", "Quality Manager", "Reliability Engineer",
        "Director of Operations", "CTO", "VP Operations",
    ]
    departments = ["Engineering", "Procurement", "Quality", "Operations", "R&D"]
    contacts = []
    n = 0
    for acct in accounts:
        count = {"Enterprise": random.randint(3, 5), "Mid-Market": random.randint(2, 3), "SMB": random.randint(1, 2)}[acct["segment"]]
        for i in range(count):
            first = fake.first_name()
            last = fake.last_name()
            company_domain = acct["website"].replace("https://www.", "").rstrip("/")
            contacts.append({
                "id": make_contact_id(n),
                "account_id": acct["id"],
                "first_name": first,
                "last_name": last,
                "title": random.choice(titles),
                "department": random.choice(departments),
                "email": f"{first.lower()}.{last.lower()}@{company_domain}",
                "phone": fake.phone_number(),
                "is_primary": 1 if i == 0 else 0,
                "created_date": acct["created_date"],
            })
            n += 1
    conn.executemany(
        """INSERT INTO contacts (id, account_id, first_name, last_name, title, department, email, phone, is_primary, created_date)
           VALUES (:id, :account_id, :first_name, :last_name, :title, :department, :email, :phone, :is_primary, :created_date)""",
        contacts,
    )
    return contacts


# ===========================================================================
# 4. Products + Pricebook
# ===========================================================================
# Pre-designate some products as "problematic" — these will have lower
# reliability scores and higher return rates downstream.
PROBLEM_PRODUCT_FLAGS: dict[str, bool] = {}


def generate_products(conn: sqlite3.Connection) -> list[dict]:
    products = []
    pricebook = []
    n = 0
    pn = 0
    for cat_entry in PRODUCT_CATALOG:
        # 3-5 variants per category
        for variant in range(random.randint(3, 5)):
            base_low, base_high = cat_entry["base_price"]
            list_price = round(random.uniform(base_low, base_high), 2)
            pid = make_product_id(n)
            # ~12 % of products are flagged as problematic
            is_problem = random.random() < 0.12
            PROBLEM_PRODUCT_FLAGS[pid] = is_problem
            launch = rand_date(date(2019, 1, 1), date(2024, 6, 1))
            sku_num = f"{n + 100:04d}"
            specs = {
                "operating_temp_c": [-40, random.choice([85, 105, 125])],
                "supply_voltage_v": random.choice([1.8, 3.3, 5.0, 12.0, 24.0, 48.0]),
                "package": random.choice(["QFN-32", "QFN-48", "TSSOP-16", "TSSOP-24", "BGA-64", "BGA-256", "SOIC-8", "DFN-8", "LFCSP-32"]),
                "pin_count": random.choice([8, 16, 24, 32, 48, 64, 100, 144]),
                "current_consumption_ua": random.randint(1, 5000),
                "qualification": random.choice(["AEC-Q100", "JESD47", "MIL-STD-883", "Industrial"]),
                "lifetime_target_yrs": random.choice([5, 10, 15, 20]),
            }
            products.append({
                "id": pid,
                "sku": f"{cat_entry['sku']}-{sku_num}",
                "name": f"{cat_entry['category']} {cat_entry['sku']}{sku_num}",
                "product_family": cat_entry["family"],
                "product_category": cat_entry["category"],
                "description": f"{cat_entry['category']} for {', '.join(cat_entry['industries'][:2])} applications.",
                "list_price": list_price,
                "currency": "USD",
                "unit_of_measure": "EA",
                "status": "Active" if random.random() > 0.05 else "NRND",
                "launch_date": launch.isoformat(),
                "target_industries": ",".join(cat_entry["industries"]),
                "design_specs": json.dumps(specs),
                "created_date": launch.isoformat(),
            })
            # Pricebook entries — Standard, Enterprise, Distributor
            for pb_name, disc in [("Standard", 0.0), ("Enterprise", 12.0), ("Distributor", 25.0)]:
                pricebook.append({
                    "id": make_pbe_id(pn),
                    "product_id": pid,
                    "pricebook_name": pb_name,
                    "unit_price": round(list_price * (1 - disc / 100), 2),
                    "discount_pct": disc,
                    "min_quantity": 1 if pb_name == "Standard" else (1000 if pb_name == "Enterprise" else 10000),
                    "valid_from": "2024-01-01",
                    "valid_to": None,
                })
                pn += 1
            n += 1
    conn.executemany(
        """INSERT INTO products (id, sku, name, product_family, product_category, description, list_price, currency,
                                 unit_of_measure, status, launch_date, target_industries, design_specs, created_date)
           VALUES (:id, :sku, :name, :product_family, :product_category, :description, :list_price, :currency,
                   :unit_of_measure, :status, :launch_date, :target_industries, :design_specs, :created_date)""",
        products,
    )
    conn.executemany(
        """INSERT INTO pricebook_entries (id, product_id, pricebook_name, unit_price, discount_pct, min_quantity, valid_from, valid_to)
           VALUES (:id, :product_id, :pricebook_name, :unit_price, :discount_pct, :min_quantity, :valid_from, :valid_to)""",
        pricebook,
    )
    return products


# ===========================================================================
# 5. Leads
# ===========================================================================
def generate_leads(conn: sqlite3.Connection, users: list[dict], accounts: list[dict]) -> list[dict]:
    sdrs = [u for u in users if u["role"] == "SDR"]
    aes = [u for u in users if u["role"] == "Account Executive"]
    leads = []
    # ~6 leads per account average — but skew toward more on key accounts
    n = 0
    for acct in accounts:
        lead_count = random.randint(2, 8) + (4 if acct["is_key_account"] else 0)
        for _ in range(lead_count):
            created = rand_date(START_DATE, END_DATE - timedelta(days=30))
            status = weighted_choice([
                ("Converted",    0.35),
                ("Qualified",    0.20),
                ("Working",      0.15),
                ("Disqualified", 0.15),
                ("New",          0.15),
            ])
            converted_date = None
            converted_account_id = None
            disqualified_reason = None
            if status == "Converted":
                converted_date = (created + timedelta(days=random.randint(7, 60))).isoformat()
                converted_account_id = acct["id"]
            elif status == "Disqualified":
                disqualified_reason = random.choice(["Bad Fit", "No Budget", "Wrong Contact", "Competitor Locked In"])
            owner = random.choice(sdrs + aes)
            leads.append({
                "id": make_lead_id(n),
                "first_name": fake.first_name(),
                "last_name": fake.last_name(),
                "company": acct["name"],
                "title": random.choice(["Engineer", "Manager", "Director", "VP Engineering"]),
                "email": fake.email(),
                "phone": fake.phone_number(),
                "lead_source": random.choice(LEAD_SOURCES),
                "status": status,
                "lead_score": random.randint(10, 99),
                "industry": acct["industry"],
                "annual_revenue": acct["annual_revenue"],
                "owner_id": owner["id"],
                "created_date": created.isoformat(),
                "converted_date": converted_date,
                "converted_account_id": converted_account_id,
                "converted_opportunity_id": None,
                "disqualified_reason": disqualified_reason,
            })
            n += 1
    conn.executemany(
        """INSERT INTO leads (id, first_name, last_name, company, title, email, phone, lead_source, status, lead_score,
                              industry, annual_revenue, owner_id, created_date, converted_date, converted_account_id,
                              converted_opportunity_id, disqualified_reason)
           VALUES (:id, :first_name, :last_name, :company, :title, :email, :phone, :lead_source, :status, :lead_score,
                   :industry, :annual_revenue, :owner_id, :created_date, :converted_date, :converted_account_id,
                   :converted_opportunity_id, :disqualified_reason)""",
        leads,
    )
    return leads


# ===========================================================================
# 6. Opportunities, Quotes, QuoteLineItems
# ===========================================================================
def _account_opportunity_count(acct: dict) -> int:
    base = {"Enterprise": (15, 35), "Mid-Market": (6, 14), "SMB": (2, 6)}[acct["segment"]]
    n = random.randint(*base)
    if acct["is_key_account"]:
        n = int(n * 1.6)
    return n


def _account_conversion_bias(acct: dict) -> float:
    """Multiplier on quote→revenue conversion.  Some accounts are 'easy', some difficult.
    Returns a value in [0.4, 1.6]."""
    # Stable per-account bias based on hash of id so it's reproducible.
    h = abs(hash(acct["id"])) % 100 / 100.0  # 0..1
    return 0.4 + h * 1.2


def generate_opportunities(
    conn_crm: sqlite3.Connection,
    accounts: list[dict],
    products: list[dict],
    users: list[dict],
) -> tuple[list[dict], list[dict], list[dict]]:
    aes = [u for u in users if u["role"] == "Account Executive"]
    by_industry = {}
    for p in products:
        for ind in p["target_industries"].split(","):
            by_industry.setdefault(ind, []).append(p)

    opportunities = []
    quotes = []
    qlines = []
    n_opp = 0
    n_quote = 0
    n_qli = 0

    for acct in accounts:
        opp_count = _account_opportunity_count(acct)
        bias = _account_conversion_bias(acct)
        for _ in range(opp_count):
            created = rand_date(START_DATE, END_DATE)
            cycle_days = random.randint(30, 240)
            close = created + timedelta(days=cycle_days)
            in_past = close <= END_DATE
            # Distribution: 55 % Closed Won / Lost in past; remainder open
            if in_past:
                stage_name = "Closed Won" if random.random() < min(0.95, 0.45 + 0.10 * bias) else "Closed Lost"
            else:
                stage_name = weighted_choice([
                    ("Prospecting",    0.20),
                    ("Qualification",  0.20),
                    ("Needs Analysis", 0.20),
                    ("Proposal",       0.20),
                    ("Negotiation",    0.20),
                ])
            stage_info = next(s for s in OPP_STAGES if s[0] == stage_name)
            probability = stage_info[1]
            forecast_cat = stage_info[2]

            # Choose product family appropriate for industry
            industry_products = by_industry.get(acct["industry"], products)
            product_family = random.choice(industry_products)["product_family"]
            chosen_products = random.sample(
                [p for p in industry_products if p["product_family"] == product_family],
                k=min(random.randint(1, 4), len([p for p in industry_products if p["product_family"] == product_family])),
            )

            req = INDUSTRY_REQUIREMENTS.get(acct["industry"], INDUSTRY_REQUIREMENTS["Industrial"])
            opp_id = make_opp_id(n_opp)
            amount = sum(p["list_price"] * random.randint(1000, 100000) for p in chosen_products) * random.uniform(0.6, 1.0)
            opp = {
                "id": opp_id,
                "name": f"{acct['name']} - {product_family} - {random.choice(['Design Win','New Project','Expansion','Replacement','Multi-Year Deal'])}",
                "account_id": acct["id"],
                "owner_id": acct["owner_id"],
                "stage": stage_name,
                "amount": round(amount, 2),
                "probability": probability,
                "close_date": close.isoformat(),
                "forecast_category": forecast_cat,
                "lead_source": random.choice(LEAD_SOURCES),
                "primary_product_family": product_family,
                "competitor": random.choice(COMPETITORS) if random.random() < 0.6 else None,
                "next_step": random.choice(["Technical review", "Pricing follow-up", "Sample request", "Design-in meeting", "Quote revision"]),
                "description": f"{product_family} opportunity for {acct['name']}'s {acct['industry']} program.",
                "created_date": created.isoformat(),
                "closed_date": close.isoformat() if stage_name.startswith("Closed") else None,
                "loss_reason": random.choice(LOSS_REASONS) if stage_name == "Closed Lost" else None,
                "customer_design_requirements": json.dumps({
                    "operating_temp_min_c": req["operating_temp_min_c"],
                    "operating_temp_max_c": req["operating_temp_max_c"],
                    "voltage_v": random.choice(req["typical_voltage_v"]),
                    "qualification": req["qualification"],
                    "certifications_required": req["key_certifications"],
                    "annual_volume": random.choice([1_000, 10_000, 100_000, 500_000, 2_000_000]),
                    "target_unit_price_usd": round(random.uniform(0.5, 30.0), 2),
                    "form_factor_constraints": random.choice(["QFN-32", "BGA-64", "TSSOP-24", "Any small package"]),
                    "design_phase": random.choice(["Concept", "Prototype", "Design-in", "Sustaining"]),
                }),
            }
            opportunities.append(opp)
            n_opp += 1

            # Generate a quote (and possibly a revision) for each opportunity
            quote_count = 1 if random.random() < 0.7 else random.randint(2, 3)
            for q_idx in range(quote_count):
                # Probability that this quote leads to revenue is conditioned on opp stage and account bias
                if stage_name == "Closed Won":
                    qstatus = "Accepted" if q_idx == quote_count - 1 else random.choice(["Sent", "Approved", "Rejected"])
                elif stage_name == "Closed Lost":
                    qstatus = "Rejected" if q_idx == quote_count - 1 else random.choice(["Sent", "Approved", "Expired"])
                else:
                    qstatus = random.choice(["Draft", "In Review", "Sent", "Approved"])

                pricebook_name = "Enterprise" if acct["segment"] in ("Enterprise", "Mid-Market") else "Standard"
                qcreated = created + timedelta(days=random.randint(5, max(6, cycle_days - 5)))
                qid = make_quote_id(n_quote)
                quote_number = f"Q-{qcreated.year}-{n_quote:06d}"
                subtotal = 0.0
                line_items: list[dict] = []
                for p in chosen_products:
                    qty = random.choice([500, 1000, 5000, 10000, 25000, 50000, 100000])
                    discount = round(random.choice([0, 5, 10, 12, 15, 18, 22, 25]), 2)
                    unit_price = round(p["list_price"] * (1 - discount / 100), 4)
                    line_total = round(unit_price * qty, 2)
                    subtotal += line_total
                    line_items.append({
                        "id": make_qli_id(n_qli),
                        "quote_id": qid,
                        "product_id": p["id"],
                        "quantity": qty,
                        "unit_price": unit_price,
                        "discount_pct": discount,
                        "line_total": line_total,
                        "sort_order": len(line_items) + 1,
                    })
                    n_qli += 1
                discount_amt = round(subtotal * random.uniform(0.0, 0.05), 2)
                tax = round((subtotal - discount_amt) * 0.0, 2)  # B2B no tax for sim
                grand_total = round(subtotal - discount_amt + tax, 2)
                quote = {
                    "id": qid,
                    "quote_number": quote_number,
                    "opportunity_id": opp_id,
                    "account_id": acct["id"],
                    "owner_id": opp["owner_id"],
                    "status": qstatus,
                    "pricebook_name": pricebook_name,
                    "subtotal": round(subtotal, 2),
                    "discount_amount": discount_amt,
                    "tax_amount": tax,
                    "grand_total": grand_total,
                    "valid_until": (qcreated + timedelta(days=90)).isoformat(),
                    "created_date": qcreated.isoformat(),
                    "sent_date": (qcreated + timedelta(days=2)).isoformat() if qstatus != "Draft" else None,
                    "approved_date": (qcreated + timedelta(days=5)).isoformat() if qstatus in ("Approved", "Accepted", "Sent") else None,
                    "accepted_date": (qcreated + timedelta(days=10)).isoformat() if qstatus == "Accepted" else None,
                    "rejected_date": (qcreated + timedelta(days=12)).isoformat() if qstatus == "Rejected" else None,
                    "rejection_reason": random.choice(LOSS_REASONS) if qstatus == "Rejected" else None,
                    "external_order_id": None,
                }
                quotes.append(quote)
                qlines.extend(line_items)
                n_quote += 1

    conn_crm.executemany(
        """INSERT INTO opportunities (id, name, account_id, owner_id, stage, amount, probability, close_date,
                                      forecast_category, lead_source, primary_product_family, competitor, next_step,
                                      description, created_date, closed_date, loss_reason, customer_design_requirements)
           VALUES (:id, :name, :account_id, :owner_id, :stage, :amount, :probability, :close_date,
                   :forecast_category, :lead_source, :primary_product_family, :competitor, :next_step,
                   :description, :created_date, :closed_date, :loss_reason, :customer_design_requirements)""",
        opportunities,
    )
    conn_crm.executemany(
        """INSERT INTO quotes (id, quote_number, opportunity_id, account_id, owner_id, status, pricebook_name,
                               subtotal, discount_amount, tax_amount, grand_total, valid_until, created_date,
                               sent_date, approved_date, accepted_date, rejected_date, rejection_reason, external_order_id)
           VALUES (:id, :quote_number, :opportunity_id, :account_id, :owner_id, :status, :pricebook_name,
                   :subtotal, :discount_amount, :tax_amount, :grand_total, :valid_until, :created_date,
                   :sent_date, :approved_date, :accepted_date, :rejected_date, :rejection_reason, :external_order_id)""",
        quotes,
    )
    conn_crm.executemany(
        """INSERT INTO quote_line_items (id, quote_id, product_id, quantity, unit_price, discount_pct, line_total, sort_order)
           VALUES (:id, :quote_id, :product_id, :quantity, :unit_price, :discount_pct, :line_total, :sort_order)""",
        qlines,
    )
    return opportunities, quotes, qlines


# ===========================================================================
# 7. ERP — Customers, Items, Sales Orders, Invoices, Payments, GL, Revenue
# ===========================================================================
def generate_erp(
    conn_erp: sqlite3.Connection,
    accounts: list[dict],
    products: list[dict],
    quotes: list[dict],
    qlines: list[dict],
    opportunities: list[dict],
) -> dict[str, Any]:
    # Customer master — 1-to-1 mapping
    customers = []
    for i, acct in enumerate(accounts):
        cust_class = "A" if acct["is_key_account"] else ("B" if acct["segment"] == "Enterprise" else ("C" if acct["segment"] == "Mid-Market" else "D"))
        customers.append({
            "customer_number": f"CUST-{i + 10001:05d}",
            "external_account_id": acct["id"],
            "name": acct["name"],
            "billing_address": f"{fake.street_address()}, {acct['billing_city']}, {acct['billing_state']}",
            "shipping_address": f"{fake.street_address()}, {acct['billing_city']}, {acct['billing_state']}",
            "country": acct["billing_country"],
            "state": acct["billing_state"],
            "city": acct["billing_city"],
            "tax_id": fake.bothify("##-#######"),
            "payment_terms": random.choice(["NET30", "NET45", "NET60", "NET90"]),
            "credit_limit": round(acct["annual_revenue"] * 0.01, 2),
            "customer_class": cust_class,
            "currency": "USD",
            "on_credit_hold": 1 if random.random() < 0.03 else 0,
            "created_date": acct["created_date"],
        })
    conn_erp.executemany(
        """INSERT INTO customers (customer_number, external_account_id, name, billing_address, shipping_address,
                                  country, state, city, tax_id, payment_terms, credit_limit, customer_class,
                                  currency, on_credit_hold, created_date)
           VALUES (:customer_number, :external_account_id, :name, :billing_address, :shipping_address,
                   :country, :state, :city, :tax_id, :payment_terms, :credit_limit, :customer_class,
                   :currency, :on_credit_hold, :created_date)""",
        customers,
    )

    # Build lookup: external_account_id -> customer_id
    cust_by_ext = {c["external_account_id"]: row[0] for c, row in zip(
        customers,
        conn_erp.execute("SELECT id FROM customers ORDER BY id").fetchall(),
    )}

    # Items master
    items = []
    for p in products:
        items.append({
            "item_number": f"ITM-{p['sku']}",
            "external_product_id": p["id"],
            "name": p["name"],
            "description": p["description"],
            "item_category": p["product_category"],
            "unit_of_measure": "EA",
            "standard_cost": round(p["list_price"] * random.uniform(0.30, 0.55), 4),
            "list_price": p["list_price"],
            "inventory_on_hand": random.randint(0, 250_000),
            "lead_time_days": random.choice([8, 12, 14, 21, 28, 42, 56]),
            "abc_class": random.choice(["A", "A", "B", "B", "C"]),
            "status": p["status"],
            "created_date": p["created_date"],
        })
    conn_erp.executemany(
        """INSERT INTO items (item_number, external_product_id, name, description, item_category, unit_of_measure,
                              standard_cost, list_price, inventory_on_hand, lead_time_days, abc_class, status, created_date)
           VALUES (:item_number, :external_product_id, :name, :description, :item_category, :unit_of_measure,
                   :standard_cost, :list_price, :inventory_on_hand, :lead_time_days, :abc_class, :status, :created_date)""",
        items,
    )
    item_by_ext = {row[1]: row[0] for row in conn_erp.execute("SELECT id, external_product_id FROM items").fetchall()}

    # Index quote lines by quote
    qlines_by_quote: dict[str, list[dict]] = {}
    for ql in qlines:
        qlines_by_quote.setdefault(ql["quote_id"], []).append(ql)

    # Index opps by id
    opp_by_id = {o["id"]: o for o in opportunities}
    acct_by_id = {a["id"]: a for a in accounts}

    # Generate sales orders ONLY for Accepted quotes (the canonical flow)
    orders: list[dict] = []
    order_lines: list[dict] = []
    invoices: list[dict] = []
    invoice_lines: list[dict] = []
    payments: list[dict] = []
    gl_entries: list[dict] = []
    revenue_rows: list[dict] = []
    quote_revenue_sync: list[dict] = []

    order_seq = 0
    inv_seq = 0
    pay_seq = 0
    gl_seq = 0

    for q in quotes:
        if q["status"] != "Accepted":
            continue
        opp = opp_by_id[q["opportunity_id"]]
        acct = acct_by_id[q["account_id"]]
        bias = _account_conversion_bias(acct)
        # Most accepted quotes lead to revenue; conversion bias adjusts probability
        if random.random() > min(0.98, 0.55 + 0.40 * bias):
            continue

        cust_id = cust_by_ext[acct["id"]]
        accepted = datetime.fromisoformat(q["accepted_date"]).date()
        order_date = accepted + timedelta(days=random.randint(1, 14))
        if order_date > END_DATE:
            order_date = END_DATE
        confirmed_delivery = order_date + timedelta(days=random.randint(14, 60))
        actual_delivery = confirmed_delivery + timedelta(days=random.randint(-3, 10))
        order_status = "Invoiced" if actual_delivery <= END_DATE else "Confirmed"

        order_seq += 1
        order_number = f"SO-{order_date.year}{order_seq:06d}"
        order_lines_for_this: list[dict] = []
        order_subtotal = 0.0
        # Replicate quote lines as order lines (partial orders allowed)
        partial = random.random() < 0.05
        for line_idx, ql in enumerate(qlines_by_quote[q["id"]]):
            qty_ratio = random.uniform(0.7, 1.0) if partial else 1.0
            qty = max(1, int(ql["quantity"] * qty_ratio))
            line_total = round(qty * ql["unit_price"], 2)
            order_subtotal += line_total
            order_lines_for_this.append({
                "line_number": line_idx + 1,
                "external_product_id": ql["product_id"],
                "quantity_ordered": qty,
                "quantity_shipped": qty if order_status in ("Shipped", "Delivered", "Invoiced") else 0,
                "unit_price": ql["unit_price"],
                "discount_pct": ql["discount_pct"],
                "line_total": line_total,
                "requested_date": confirmed_delivery.isoformat(),
                "promised_date": confirmed_delivery.isoformat(),
                "status": "Shipped" if order_status in ("Shipped", "Delivered", "Invoiced") else "Open",
            })
        order = {
            "order_number": order_number,
            "customer_id": cust_id,
            "external_quote_id": q["id"],
            "external_quote_number": q["quote_number"],
            "order_date": order_date.isoformat(),
            "requested_delivery_date": confirmed_delivery.isoformat(),
            "confirmed_delivery_date": confirmed_delivery.isoformat(),
            "actual_delivery_date": actual_delivery.isoformat() if order_status == "Invoiced" else None,
            "status": order_status,
            "order_type": random.choice(["Standard", "Standard", "Standard", "Rush", "Sample"]),
            "subtotal": round(order_subtotal, 2),
            "discount_amount": 0.0,
            "tax_amount": 0.0,
            "shipping_amount": round(random.uniform(50, 500), 2),
            "grand_total": round(order_subtotal + random.uniform(50, 500), 2),
            "currency": "USD",
            "shipping_method": random.choice(["FedEx Air", "UPS Ground", "DHL Express", "Sea Freight"]),
            "payment_terms": next(c["payment_terms"] for c in customers if c["external_account_id"] == acct["id"]),
            "sales_rep_external_id": opp["owner_id"],
            "cancellation_reason": None,
        }
        orders.append(order)
        order_lines.append(order_lines_for_this)

    # Bulk insert orders
    cur = conn_erp.cursor()
    for o in orders:
        cur.execute(
            """INSERT INTO sales_orders (order_number, customer_id, external_quote_id, external_quote_number,
                                         order_date, requested_delivery_date, confirmed_delivery_date,
                                         actual_delivery_date, status, order_type, subtotal, discount_amount,
                                         tax_amount, shipping_amount, grand_total, currency, shipping_method,
                                         payment_terms, sales_rep_external_id, cancellation_reason)
               VALUES (:order_number, :customer_id, :external_quote_id, :external_quote_number,
                       :order_date, :requested_delivery_date, :confirmed_delivery_date,
                       :actual_delivery_date, :status, :order_type, :subtotal, :discount_amount,
                       :tax_amount, :shipping_amount, :grand_total, :currency, :shipping_method,
                       :payment_terms, :sales_rep_external_id, :cancellation_reason)""",
            o,
        )

    # Pull back order ids in insertion order
    order_ids = [row[0] for row in conn_erp.execute("SELECT id FROM sales_orders ORDER BY id").fetchall()]

    # Insert order lines and invoices
    for o, oid, ol_set in zip(orders, order_ids, order_lines):
        for ol in ol_set:
            item_id = item_by_ext[ol["external_product_id"]]
            cur.execute(
                """INSERT INTO sales_order_lines (order_id, line_number, item_id, quantity_ordered, quantity_shipped,
                                                   unit_price, discount_pct, line_total, requested_date,
                                                   promised_date, status)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (oid, ol["line_number"], item_id, ol["quantity_ordered"], ol["quantity_shipped"],
                 ol["unit_price"], ol["discount_pct"], ol["line_total"], ol["requested_date"],
                 ol["promised_date"], ol["status"]),
            )

        # Invoice — only for orders that have been invoiced
        if o["status"] == "Invoiced":
            inv_seq += 1
            invoice_number = f"INV-{datetime.fromisoformat(o['actual_delivery_date']).year}{inv_seq:06d}"
            inv_date = datetime.fromisoformat(o["actual_delivery_date"]).date()
            terms = o["payment_terms"]
            days = int(terms.replace("NET", ""))
            due_date = inv_date + timedelta(days=days)
            subtotal = round(o["subtotal"], 2)
            tax = 0.0
            total = round(subtotal + tax, 2)
            # Payment behavior — most paid in time, some overdue/disputed
            today = END_DATE
            r = random.random()
            if today >= due_date:
                if r < 0.85:
                    amount_paid = total
                    status = "Paid"
                    last_payment_date = (due_date - timedelta(days=random.randint(0, 5))).isoformat()
                elif r < 0.92:
                    amount_paid = round(total * random.uniform(0.4, 0.85), 2)
                    status = "Partially Paid"
                    last_payment_date = (inv_date + timedelta(days=random.randint(15, days))).isoformat()
                elif r < 0.97:
                    amount_paid = 0.0
                    status = "Overdue"
                    last_payment_date = None
                else:
                    amount_paid = 0.0
                    status = "Disputed"
                    last_payment_date = None
            else:
                if r < 0.50:
                    amount_paid = total
                    status = "Paid"
                    upper = min(days, max(1, (today - inv_date).days))
                    lower = min(5, upper)
                    last_payment_date = (inv_date + timedelta(days=random.randint(lower, upper))).isoformat()
                else:
                    amount_paid = 0.0
                    status = "Posted"
                    last_payment_date = None

            amount_outstanding = round(total - amount_paid, 2)
            recognition_status = "Recognized" if status in ("Paid", "Partially Paid", "Posted") else "Pending"
            recognition_date = inv_date.isoformat() if recognition_status == "Recognized" else None

            invoices.append({
                "order_id": oid,
                "invoice_number": invoice_number,
                "customer_id": o["customer_id"],
                "invoice_date": inv_date.isoformat(),
                "due_date": due_date.isoformat(),
                "subtotal": subtotal,
                "tax_amount": tax,
                "total_amount": total,
                "amount_paid": amount_paid,
                "amount_outstanding": amount_outstanding,
                "status": status,
                "payment_terms": terms,
                "currency": "USD",
                "recognition_status": recognition_status,
                "recognition_date": recognition_date,
                "posted_date": inv_date.isoformat(),
                "last_payment_date": last_payment_date,
                "external_quote_id": o["external_quote_id"],
                "external_account_id": next(c["external_account_id"] for c in customers if cust_by_ext[c["external_account_id"]] == o["customer_id"]),
                "lines_data": ol_set,
            })

    for inv in invoices:
        cur.execute(
            """INSERT INTO invoices (invoice_number, order_id, customer_id, invoice_date, due_date, subtotal,
                                     tax_amount, total_amount, amount_paid, amount_outstanding, status, payment_terms,
                                     currency, recognition_status, recognition_date, posted_date, last_payment_date)
               VALUES (:invoice_number, :order_id, :customer_id, :invoice_date, :due_date, :subtotal,
                       :tax_amount, :total_amount, :amount_paid, :amount_outstanding, :status, :payment_terms,
                       :currency, :recognition_status, :recognition_date, :posted_date, :last_payment_date)""",
            {k: inv[k] for k in (
                "invoice_number", "order_id", "customer_id", "invoice_date", "due_date", "subtotal",
                "tax_amount", "total_amount", "amount_paid", "amount_outstanding", "status", "payment_terms",
                "currency", "recognition_status", "recognition_date", "posted_date", "last_payment_date",
            )},
        )
    invoice_ids = [row[0] for row in conn_erp.execute("SELECT id FROM invoices ORDER BY id").fetchall()]

    # Invoice lines, payments, GL, revenue
    for inv, inv_id in zip(invoices, invoice_ids):
        # Invoice lines mirror order lines
        for line_idx, ol in enumerate(inv["lines_data"]):
            item_id = item_by_ext[ol["external_product_id"]]
            cur.execute(
                """INSERT INTO invoice_lines (invoice_id, line_number, item_id, quantity, unit_price, line_total)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (inv_id, line_idx + 1, item_id, ol["quantity_ordered"], ol["unit_price"], ol["line_total"]),
            )

        # Payments
        if inv["amount_paid"] > 0:
            pay_seq += 1
            payment_date = inv["last_payment_date"]
            cur.execute(
                """INSERT INTO payments (payment_number, invoice_id, customer_id, payment_date, amount,
                                         payment_method, reference_number, status)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (f"PAY-{datetime.fromisoformat(payment_date).year}{pay_seq:06d}",
                 inv_id, inv["customer_id"], payment_date, inv["amount_paid"],
                 random.choice(["Wire", "ACH", "Check", "Credit Card", "PO"]),
                 fake.bothify("REF########"), "Cleared"),
            )

        # GL entries
        gl_seq += 1
        period = inv["invoice_date"][:7]
        cur.execute(
            """INSERT INTO gl_entries (journal_number, entry_date, account_code, account_name, debit, credit,
                                       description, source_doc_type, source_doc_id, cost_center, period)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (f"JE-{gl_seq:08d}", inv["invoice_date"], "1200", "Accounts Receivable",
             inv["total_amount"], 0.0, f"AR for {inv['invoice_number']}", "Invoice", inv_id, "SALES", period),
        )
        cur.execute(
            """INSERT INTO gl_entries (journal_number, entry_date, account_code, account_name, debit, credit,
                                       description, source_doc_type, source_doc_id, cost_center, period)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (f"JE-{gl_seq:08d}", inv["invoice_date"], "4000", "Product Revenue",
             0.0, inv["total_amount"], f"Revenue for {inv['invoice_number']}", "Invoice", inv_id, "SALES", period),
        )

        # Revenue rows (per line — for product family analytics)
        if inv["recognition_status"] == "Recognized":
            inv_date = datetime.fromisoformat(inv["invoice_date"]).date()
            fy, fq = fiscal_quarter(inv_date)
            for ol in inv["lines_data"]:
                item_id = item_by_ext[ol["external_product_id"]]
                # Look up product family from product list
                product = next(p for p in products if p["id"] == ol["external_product_id"])
                acct = next(a for a in accounts if a["id"] == inv["external_account_id"])
                # Get sales rep region
                rev_amount = ol["line_total"]
                revenue_rows.append({
                    "invoice_id": inv_id,
                    "customer_id": inv["customer_id"],
                    "item_id": item_id,
                    "external_account_id": inv["external_account_id"],
                    "external_quote_id": inv["external_quote_id"],
                    "recognized_date": inv["invoice_date"],
                    "period": f"{fy}-Q{fq}",
                    "fiscal_year": fy,
                    "fiscal_quarter": fq,
                    "amount": rev_amount,
                    "recognition_status": "Recognized",
                    "product_family": product["product_family"],
                    "region": acct["billing_country"],
                })

    for r in revenue_rows:
        cur.execute(
            """INSERT INTO revenue (invoice_id, customer_id, item_id, external_account_id, external_quote_id,
                                    recognized_date, period, fiscal_year, fiscal_quarter, amount,
                                    recognition_status, product_family, region)
               VALUES (:invoice_id, :customer_id, :item_id, :external_account_id, :external_quote_id,
                       :recognized_date, :period, :fiscal_year, :fiscal_quarter, :amount,
                       :recognition_status, :product_family, :region)""",
            r,
        )

    # Build quote_revenue_sync rows that we'll later insert back into CRM
    sync_rows: list[dict] = []
    inv_lookup = {row[0]: row for row in conn_erp.execute(
        "SELECT id, invoice_number, total_amount, invoice_date, recognition_status, order_id FROM invoices"
    ).fetchall()}
    order_to_quote = {row[0]: row[1] for row in conn_erp.execute(
        "SELECT id, external_quote_id FROM sales_orders"
    ).fetchall()}
    for inv_id, (i_id, inv_num, total, inv_date, rec_status, order_id) in inv_lookup.items():
        qid = order_to_quote.get(order_id)
        if not qid:
            continue
        sync_rows.append({
            "quote_id": qid,
            "external_invoice_number": inv_num,
            "external_invoice_id": str(i_id),
            "revenue_amount": total,
            "revenue_date": inv_date,
            "recognition_status": rec_status,
            "sync_date": inv_date,
        })

    return {
        "orders_inserted": len(orders),
        "invoices_inserted": len(invoices),
        "revenue_rows": len(revenue_rows),
        "sync_rows": sync_rows,
    }


# ===========================================================================
# 8. QA System data
# ===========================================================================
def generate_qa(
    conn_qa: sqlite3.Connection,
    products: list[dict],
    accounts: list[dict],
    erp_invoices: list[tuple],  # list of (invoice_number, external_account_id, external_product_id, date)
) -> dict[str, Any]:
    # Test specifications — multiple per product
    specs_data: list[dict] = []
    spec_seq = 0
    for p in products:
        test_count = random.randint(3, 7)
        for _ in range(test_count):
            tt, std, dur = random.choice(TEST_TYPES)
            spec_seq += 1
            specs_data.append({
                "spec_number": f"TS-{spec_seq:05d}",
                "external_product_id": p["id"],
                "test_name": f"{tt} - {p['name']}",
                "test_type": tt.split("(")[0].strip(),
                "test_standard": std,
                "parameters": json.dumps({"voltage_v": json.loads(p["design_specs"])["supply_voltage_v"], "duration_hrs": dur}),
                "pass_criteria": f"All parameters within ±5% of nominal across temperature range.",
                "typical_duration_hrs": dur,
                "created_date": p["launch_date"],
            })

    cur = conn_qa.cursor()
    for s in specs_data:
        cur.execute(
            """INSERT INTO test_specifications (spec_number, external_product_id, test_name, test_type, test_standard,
                                                parameters, pass_criteria, typical_duration_hrs, created_date)
               VALUES (:spec_number, :external_product_id, :test_name, :test_type, :test_standard,
                       :parameters, :pass_criteria, :typical_duration_hrs, :created_date)""",
            s,
        )
    spec_rows = list(conn_qa.execute("SELECT id, external_product_id FROM test_specifications").fetchall())

    # Test runs (campaigns) — historical
    run_seq = 0
    test_runs_data: list[dict] = []
    test_results_data: list[dict] = []
    for spec_id, ext_pid in spec_rows:
        runs_per_spec = random.randint(2, 6)
        for _ in range(runs_per_spec):
            run_seq += 1
            run_date = rand_date(START_DATE, END_DATE)
            sample_size = random.choice([50, 77, 100, 200, 500, 1000])
            is_problem = PROBLEM_PRODUCT_FLAGS.get(ext_pid, False)
            fail_rate = random.uniform(0.04, 0.18) if is_problem else random.uniform(0.0, 0.025)
            failed = int(sample_size * fail_rate)
            inconclusive = int(sample_size * random.uniform(0.0, 0.01))
            passed = sample_size - failed - inconclusive
            pass_rate = passed / sample_size
            test_runs_data.append({
                "run_number": f"TR-{run_date.year}{run_seq:06d}",
                "spec_id": spec_id,
                "external_product_id": ext_pid,
                "run_date": run_date.isoformat(),
                "operator": fake.name(),
                "lab_location": random.choice(["HQ Lab", "APAC Lab", "EU Lab"]),
                "sample_size": sample_size,
                "samples_passed": passed,
                "samples_failed": failed,
                "samples_inconclusive": inconclusive,
                "pass_rate": pass_rate,
                "status": "Complete",
                "batch_lot_code": fake.bothify("LOT-####??"),
            })

    for r in test_runs_data:
        cur.execute(
            """INSERT INTO test_runs (run_number, spec_id, external_product_id, run_date, operator, lab_location,
                                      sample_size, samples_passed, samples_failed, samples_inconclusive, pass_rate,
                                      status, batch_lot_code)
               VALUES (:run_number, :spec_id, :external_product_id, :run_date, :operator, :lab_location,
                       :sample_size, :samples_passed, :samples_failed, :samples_inconclusive, :pass_rate,
                       :status, :batch_lot_code)""",
            r,
        )
    run_rows = list(conn_qa.execute("SELECT id, external_product_id, sample_size, samples_failed FROM test_runs").fetchall())

    # Generate sample-level test results (only sample of run for size — store ~30 per run)
    for run_id, ext_pid, sample_size, samples_failed in run_rows:
        results_to_store = min(sample_size, 30)
        failed_to_store = min(samples_failed, max(1, int(results_to_store * (samples_failed / sample_size))))
        for i in range(results_to_store):
            is_fail = i < failed_to_store
            test_results_data.append({
                "test_run_id": run_id,
                "sample_id": f"S{run_id}-{i+1:04d}",
                "pass_fail": "Fail" if is_fail else ("Marginal" if random.random() < 0.02 else "Pass"),
                "measured_value": round(random.gauss(5.0, 0.4 if not is_fail else 1.5), 4),
                "measured_units": "V",
                "spec_min": 4.5,
                "spec_max": 5.5,
                "environmental_conditions": json.dumps({"temp_c": random.choice([-40, 25, 85, 125]), "humidity_pct": random.choice([20, 50, 85])}),
                "failure_mode": random.choice(FAILURE_MODES) if is_fail else None,
                "notes": "Burn-in stress test" if random.random() < 0.1 else None,
            })

    for tr in test_results_data:
        cur.execute(
            """INSERT INTO test_results (test_run_id, sample_id, pass_fail, measured_value, measured_units,
                                          spec_min, spec_max, environmental_conditions, failure_mode, notes)
               VALUES (:test_run_id, :sample_id, :pass_fail, :measured_value, :measured_units,
                       :spec_min, :spec_max, :environmental_conditions, :failure_mode, :notes)""",
            tr,
        )

    # Reliability metrics — quarterly per product
    rel_metrics: list[dict] = []
    quarters = []
    d = date(2024, 1, 1)
    while d <= END_DATE:
        q_start = date(d.year, ((d.month - 1) // 3) * 3 + 1, 1)
        q_end_month = q_start.month + 2
        last_day = (date(q_start.year + (q_end_month // 12), (q_end_month % 12) + 1, 1) - timedelta(days=1))
        quarters.append((q_start, last_day, quarter_label(q_start)))
        d = last_day + timedelta(days=1)

    for p in products:
        is_problem = PROBLEM_PRODUCT_FLAGS.get(p["id"], False)
        base_mtbf = random.uniform(40_000, 80_000) if is_problem else random.uniform(150_000, 800_000)
        base_failure_ppm = random.uniform(800, 3500) if is_problem else random.uniform(20, 250)
        for q_start, q_end, label in quarters:
            # Slight trend variation per quarter
            jitter = random.uniform(0.85, 1.15)
            rel_metrics.append({
                "external_product_id": p["id"],
                "period_start": q_start.isoformat(),
                "period_end": q_end.isoformat(),
                "period_label": label,
                "mtbf_hours": round(base_mtbf * jitter, 2),
                "mttr_hours": round(random.uniform(1.5, 6.0), 2),
                "failure_rate_ppm": round(base_failure_ppm * jitter, 2),
                "fit_rate": round(base_failure_ppm / 8.76, 2),  # PPM/year ≈ FIT/100
                "sample_size": random.randint(500, 5000),
                "field_population": random.randint(10_000, 5_000_000),
                "operating_hours_total": random.uniform(1e6, 1e9),
                "confidence_pct": 90,
                "methodology": random.choice(["Telcordia SR-332", "MIL-HDBK-217F", "Field Data Analysis"]),
                "created_date": q_end.isoformat(),
            })

    for r in rel_metrics:
        cur.execute(
            """INSERT INTO reliability_metrics (external_product_id, period_start, period_end, period_label, mtbf_hours,
                                                mttr_hours, failure_rate_ppm, fit_rate, sample_size, field_population,
                                                operating_hours_total, confidence_pct, methodology, created_date)
               VALUES (:external_product_id, :period_start, :period_end, :period_label, :mtbf_hours,
                       :mttr_hours, :failure_rate_ppm, :fit_rate, :sample_size, :field_population,
                       :operating_hours_total, :confidence_pct, :methodology, :created_date)""",
            r,
        )

    # Failures — tied to products and accounts
    failures_data: list[dict] = []
    failure_seq = 0
    for p in products:
        is_problem = PROBLEM_PRODUCT_FLAGS.get(p["id"], False)
        failure_count = random.randint(8, 40) if is_problem else random.randint(0, 8)
        for _ in range(failure_count):
            failure_seq += 1
            fdate = rand_date(date(2024, 6, 1), END_DATE)
            acct = random.choice(accounts)
            failures_data.append({
                "failure_number": f"FLR-{fdate.year}{failure_seq:06d}",
                "external_product_id": p["id"],
                "external_customer_id": None,
                "external_account_id": acct["id"],
                "failure_date": fdate.isoformat(),
                "detection_stage": random.choice(["Field", "Field", "Customer Return", "Burn-In", "Incoming Inspection"]),
                "severity": weighted_choice([("Critical", 0.10), ("Major", 0.35), ("Minor", 0.45), ("Cosmetic", 0.10)]),
                "failure_mode": random.choice(FAILURE_MODES),
                "root_cause": random.choice([
                    "Material variation in fab",
                    "Process drift during assembly",
                    "ESD exposure during handling",
                    "Customer overvoltage event",
                    "Thermal stress beyond rating",
                    "Solder joint fatigue",
                    "Moisture ingress through package",
                ]),
                "root_cause_category": random.choice(ROOT_CAUSE_CATEGORIES),
                "qty_affected": random.choice([1, 1, 5, 10, 50, 100]),
                "units_in_field_at_failure": random.randint(10_000, 5_000_000),
                "corrective_action": random.choice([
                    "Process change implemented",
                    "Vendor change for raw material",
                    "Customer education on handling",
                    "Datasheet update with new derating",
                    "Design revision in next rev",
                ]),
                "status": random.choice(["Resolved", "Resolved", "Investigating", "Closed"]),
                "resolved_date": (fdate + timedelta(days=random.randint(15, 120))).isoformat() if random.random() < 0.7 else None,
                "cost_impact": round(random.uniform(500, 250_000), 2),
            })

    for f in failures_data:
        cur.execute(
            """INSERT INTO failures (failure_number, external_product_id, external_customer_id, external_account_id,
                                     failure_date, detection_stage, severity, failure_mode, root_cause,
                                     root_cause_category, qty_affected, units_in_field_at_failure, corrective_action,
                                     status, resolved_date, cost_impact)
               VALUES (:failure_number, :external_product_id, :external_customer_id, :external_account_id,
                       :failure_date, :detection_stage, :severity, :failure_mode, :root_cause,
                       :root_cause_category, :qty_affected, :units_in_field_at_failure, :corrective_action,
                       :status, :resolved_date, :cost_impact)""",
            f,
        )

    # Customer returns — anchor to actual ERP invoices when possible
    returns_data: list[dict] = []
    rma_seq = 0
    # Build invoice index by (product, account) so we can attach returns realistically
    invs_by_acct_prod: dict[tuple, list] = {}
    for inv_num, ext_acct, ext_pid, idate in erp_invoices:
        invs_by_acct_prod.setdefault((ext_acct, ext_pid), []).append((inv_num, idate))

    # Returns happen mostly for problem products
    for p in products:
        is_problem = PROBLEM_PRODUCT_FLAGS.get(p["id"], False)
        # Higher return rate for problem products
        return_count = random.randint(6, 25) if is_problem else random.randint(0, 5)
        for _ in range(return_count):
            rma_seq += 1
            acct = random.choice(accounts)
            invs_for_this = invs_by_acct_prod.get((acct["id"], p["id"]), [])
            inv_num = None
            inv_date = None
            if invs_for_this:
                inv_num, inv_date = random.choice(invs_for_this)
                inv_d = datetime.fromisoformat(inv_date).date()
                rdate = inv_d + timedelta(days=random.randint(10, 540))
                if rdate > END_DATE:
                    rdate = END_DATE
            else:
                rdate = rand_date(date(2024, 6, 1), END_DATE)
                inv_d = rdate - timedelta(days=random.randint(30, 360))

            qty = random.choice([10, 50, 100, 500, 1000, 5000])
            unit_cost = p["list_price"] * 0.45
            returns_data.append({
                "rma_number": f"RMA-{rdate.year}{rma_seq:06d}",
                "external_product_id": p["id"],
                "external_customer_id": None,
                "external_account_id": acct["id"],
                "external_invoice_number": inv_num,
                "return_date": rdate.isoformat(),
                "qty_returned": qty,
                "return_reason": random.choice(RETURN_REASONS),
                "defect_category": random.choice(["Functional", "Reliability", "Cosmetic", "Premature Failure"]),
                "disposition": random.choice(["Replace", "Refund", "Repair", "Scrap"]),
                "replacement_cost": round(qty * unit_cost, 2),
                "days_in_service": (rdate - inv_d).days,
                "customer_complaint": random.choice([
                    "Unit failed in field within first 90 days",
                    "Performance below datasheet specification at temperature corner",
                    "Failed during burn-in at customer site",
                    "Visible damage on receipt — possible transit issue",
                    "Failed automated test on assembly line",
                    "Multiple units in same lot showed early failure",
                    "Intermittent operation reported by end users",
                ]),
                "investigation_notes": "Root cause analysis underway — see failure record FLR-XXXX.",
                "related_failure_id": None,
                "status": random.choice(["Resolved", "Approved", "Investigating", "Received"]),
            })

    for ret in returns_data:
        cur.execute(
            """INSERT INTO customer_returns (rma_number, external_product_id, external_customer_id, external_account_id,
                                             external_invoice_number, return_date, qty_returned, return_reason,
                                             defect_category, disposition, replacement_cost, days_in_service,
                                             customer_complaint, investigation_notes, related_failure_id, status)
               VALUES (:rma_number, :external_product_id, :external_customer_id, :external_account_id,
                       :external_invoice_number, :return_date, :qty_returned, :return_reason,
                       :defect_category, :disposition, :replacement_cost, :days_in_service,
                       :customer_complaint, :investigation_notes, :related_failure_id, :status)""",
            ret,
        )

    # Environmental tests
    env_seq = 0
    for p in products:
        for _ in range(random.randint(2, 5)):
            env_seq += 1
            tt, std, dur = random.choice([
                ("Thermal Cycling", "JESD22-A104", random.randint(500, 2000)),
                ("HAST", "JESD22-A110", random.randint(96, 200)),
                ("Vibration", "MIL-STD-810G", random.randint(4, 24)),
                ("Shock", "MIL-STD-883", random.randint(1, 8)),
                ("Salt Spray", "MIL-STD-810G", random.randint(48, 240)),
            ])
            samples = random.randint(20, 100)
            is_problem = PROBLEM_PRODUCT_FLAGS.get(p["id"], False)
            passed = samples - (random.randint(2, 8) if is_problem else random.randint(0, 2))
            cur.execute(
                """INSERT INTO environmental_tests (test_id, external_product_id, test_type, standard, conditions,
                                                     duration_hrs, samples_tested, samples_passed, test_date, passed, notes)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (f"ENV-{env_seq:05d}", p["id"], tt, std,
                 json.dumps({"min_temp_c": -55, "max_temp_c": 125, "cycles": random.choice([500, 1000, 2000])}),
                 dur, samples, passed, rand_date(date(2024, 1, 1), END_DATE).isoformat(),
                 1 if (passed / samples) >= 0.95 else 0,
                 "Passed all post-stress electrical tests." if (passed / samples) >= 0.95 else "Minor parametric shifts observed."),
            )

    # Compliance records
    for p in products:
        chosen_stds = random.sample(COMPLIANCE_STANDARDS, k=random.randint(3, 6))
        for std, std_type, months in chosen_stds:
            issued = rand_date(date(2022, 1, 1), date(2024, 12, 31))
            expiry = issued + timedelta(days=months * 30)
            status = "Active" if expiry > END_DATE else ("Pending Renewal" if (expiry - END_DATE).days > -30 else "Expired")
            cur.execute(
                """INSERT INTO compliance_records (external_product_id, standard, certificate_number, issued_by,
                                                    issue_date, expiry_date, status, notes)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (p["id"], std, fake.bothify("CERT-########"),
                 random.choice(["TÜV Rheinland", "Underwriters Laboratories", "Intertek", "DEKRA", "SGS"]),
                 issued.isoformat(), expiry.isoformat(), status, f"{std_type} compliance."),
            )

    # Reliability scores — one current per product
    for p in products:
        # Aggregate from this product's failures/returns/test pass rate
        pid = p["id"]
        is_problem = PROBLEM_PRODUCT_FLAGS.get(pid, False)
        base_score = random.uniform(55, 78) if is_problem else random.uniform(82, 98)
        score = round(base_score, 1)
        if score >= 95:    grade = "A+"
        elif score >= 90:  grade = "A"
        elif score >= 80:  grade = "B"
        elif score >= 70:  grade = "C"
        elif score >= 60:  grade = "D"
        else:              grade = "F"
        recommendation = (
            "Suitable for high-reliability applications including automotive and aerospace."
            if score >= 90 else
            "Acceptable for general industrial and consumer applications; not recommended for safety-critical use."
            if score >= 75 else
            "Caution advised — recent reliability trends suggest qualification testing or alternative part."
        )
        cur.execute(
            """INSERT INTO reliability_scores (external_product_id, score, score_grade, score_date, period,
                                                mtbf_component, return_rate_component, test_pass_component,
                                                field_failure_component, recommendation, methodology_version)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (pid, score, grade, END_DATE.isoformat(), quarter_label(END_DATE),
             round(score * random.uniform(0.95, 1.0), 1),
             round(score * random.uniform(0.92, 1.0), 1),
             round(score * random.uniform(0.95, 1.0), 1),
             round(score * random.uniform(0.90, 1.0), 1),
             recommendation, "v1.2"),
        )

    return {
        "test_specs": len(specs_data),
        "test_runs": len(test_runs_data),
        "test_results": len(test_results_data),
        "reliability_metrics": len(rel_metrics),
        "failures": len(failures_data),
        "returns": len(returns_data),
    }


# ===========================================================================
# 9. Sync revenue & reliability back to CRM
# ===========================================================================
def sync_back_to_crm(
    conn_crm: sqlite3.Connection,
    conn_qa: sqlite3.Connection,
    sync_rows: list[dict],
    products: list[dict],
    accounts: list[dict],
    opportunities: list[dict],
) -> None:
    n = 0
    for r in sync_rows:
        n += 1
        conn_crm.execute(
            """INSERT INTO quote_revenue_sync (id, quote_id, external_invoice_number, external_invoice_id,
                                                revenue_amount, revenue_date, recognition_status, sync_date)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (f"QRS{n:08d}", r["quote_id"], r["external_invoice_number"], r["external_invoice_id"],
             r["revenue_amount"], r["revenue_date"], r["recognition_status"], r["sync_date"]),
        )

    # Reliability insights — for each product, sync top-level insights tied to its
    # most recent opportunity for each account that has bought it.
    rel_scores = {row[0]: (row[1], row[2]) for row in conn_qa.execute(
        "SELECT external_product_id, score, score_grade FROM reliability_scores"
    ).fetchall()}
    latest_rm = {}
    for row in conn_qa.execute(
        "SELECT external_product_id, period_label, mtbf_hours, failure_rate_ppm FROM reliability_metrics ORDER BY period_label"
    ).fetchall():
        latest_rm[row[0]] = (row[2], row[3])

    sync_seq = 0
    for p in products:
        score_info = rel_scores.get(p["id"])
        rm_info = latest_rm.get(p["id"])
        if not score_info or not rm_info:
            continue
        score, grade = score_info
        mtbf, fr_ppm = rm_info
        # Sync to 1-3 opportunities that involve this product family/account
        relevant_opps = [o for o in opportunities if o["primary_product_family"] == p["product_family"]]
        sample = random.sample(relevant_opps, k=min(3, len(relevant_opps))) if relevant_opps else []
        for opp in sample:
            sync_seq += 1
            recommendation = (
                f"Reliability score {score} ({grade}) — strongly recommended for {opp.get('primary_product_family', '')} programs."
                if score >= 90 else
                f"Reliability score {score} ({grade}) — qualified for general use; review specs for safety-critical."
                if score >= 75 else
                f"Reliability score {score} ({grade}) — caution; consider alternate qualified part."
            )
            conn_crm.execute(
                """INSERT INTO reliability_insights_sync (id, product_id, account_id, opportunity_id, reliability_score,
                                                           failure_rate_ppm, mtbf_hours, recommendation, sync_date)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (f"RIS{sync_seq:08d}", p["id"], opp["account_id"], opp["id"], score, fr_ppm, mtbf, recommendation,
                 END_DATE.isoformat()),
            )


# ===========================================================================
# Driver
# ===========================================================================
def main() -> None:
    conn_crm = sqlite3.connect(DB_DIR / "crm.db")
    conn_erp = sqlite3.connect(DB_DIR / "erp.db")
    conn_qa = sqlite3.connect(DB_DIR / "qa.db")
    conn_crm.execute("PRAGMA foreign_keys=ON")
    conn_erp.execute("PRAGMA foreign_keys=ON")
    conn_qa.execute("PRAGMA foreign_keys=ON")

    print(">> Generating users...")
    users = generate_users(conn_crm)
    print(f"   {len(users)} users")

    print(">> Generating accounts...")
    accounts = generate_accounts(conn_crm, users)
    print(f"   {len(accounts)} accounts ({sum(1 for a in accounts if a['is_key_account'])} key)")

    print(">> Generating contacts...")
    contacts = generate_contacts(conn_crm, accounts)
    print(f"   {len(contacts)} contacts")

    print(">> Generating products & pricebook...")
    products = generate_products(conn_crm)
    print(f"   {len(products)} products ({sum(1 for p in products if PROBLEM_PRODUCT_FLAGS.get(p['id']))} flagged problematic)")

    print(">> Generating leads...")
    leads = generate_leads(conn_crm, users, accounts)
    print(f"   {len(leads)} leads")

    print(">> Generating opportunities, quotes, line items...")
    opportunities, quotes, qlines = generate_opportunities(conn_crm, accounts, products, users)
    print(f"   {len(opportunities)} opps, {len(quotes)} quotes, {len(qlines)} line items")

    conn_crm.commit()

    print(">> Generating ERP (customers, orders, invoices, payments, GL, revenue)...")
    erp_summary = generate_erp(conn_erp, accounts, products, quotes, qlines, opportunities)
    conn_erp.commit()
    print(f"   {erp_summary['orders_inserted']} orders, {erp_summary['invoices_inserted']} invoices, {erp_summary['revenue_rows']} revenue rows")

    # Pull back ERP invoice index for QA returns linkage
    erp_invoices = []
    for row in conn_erp.execute(
        """SELECT i.invoice_number, c.external_account_id, it.external_product_id, i.invoice_date
           FROM invoices i
           JOIN customers c ON c.id = i.customer_id
           JOIN invoice_lines il ON il.invoice_id = i.id
           JOIN items it ON it.id = il.item_id"""
    ).fetchall():
        erp_invoices.append(row)

    print(">> Generating QA data...")
    qa_summary = generate_qa(conn_qa, products, accounts, erp_invoices)
    conn_qa.commit()
    print(f"   {qa_summary}")

    print(">> Syncing revenue + reliability back to CRM...")
    sync_back_to_crm(conn_crm, conn_qa, erp_summary["sync_rows"], products, accounts, opportunities)
    conn_crm.commit()

    conn_crm.close()
    conn_erp.close()
    conn_qa.close()
    print("=== Done ===")


if __name__ == "__main__":
    main()
