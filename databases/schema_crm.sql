-- Salesforce CRM Database Schema (Front Office)
-- Mirrors Salesforce objects: Lead, Account, Contact, Opportunity, Product, Pricebook, Quote, QuoteLineItem
-- Plus a revenue sync table representing data flowing back from ERP

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,                    -- Salesforce-style ID prefix 005
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    role TEXT NOT NULL,                     -- AE, SDR, Sales Manager, VP Sales, Sales Engineer
    region TEXT NOT NULL,                   -- NA, EMEA, APAC, LATAM
    manager_id TEXT,
    quota_annual REAL,
    hire_date DATE NOT NULL,
    is_active INTEGER DEFAULT 1,
    FOREIGN KEY (manager_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS accounts (
    id TEXT PRIMARY KEY,                    -- Salesforce-style ID prefix 001
    name TEXT NOT NULL,
    industry TEXT NOT NULL,
    type TEXT NOT NULL,                     -- Customer, Prospect, Partner, Reseller
    segment TEXT NOT NULL,                  -- Enterprise, Mid-Market, SMB
    annual_revenue REAL,
    employee_count INTEGER,
    billing_country TEXT,
    billing_state TEXT,
    billing_city TEXT,
    website TEXT,
    is_key_account INTEGER DEFAULT 0,       -- Flag for strategic/named accounts
    owner_id TEXT NOT NULL,
    parent_account_id TEXT,                 -- For hierarchy
    created_date DATE NOT NULL,
    last_activity_date DATE,
    description TEXT,
    FOREIGN KEY (owner_id) REFERENCES users(id),
    FOREIGN KEY (parent_account_id) REFERENCES accounts(id)
);

CREATE TABLE IF NOT EXISTS contacts (
    id TEXT PRIMARY KEY,                    -- Salesforce-style ID prefix 003
    account_id TEXT NOT NULL,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    title TEXT,
    department TEXT,
    email TEXT,
    phone TEXT,
    is_primary INTEGER DEFAULT 0,
    created_date DATE NOT NULL,
    FOREIGN KEY (account_id) REFERENCES accounts(id)
);

CREATE TABLE IF NOT EXISTS leads (
    id TEXT PRIMARY KEY,                    -- Salesforce-style ID prefix 00Q
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    company TEXT NOT NULL,
    title TEXT,
    email TEXT,
    phone TEXT,
    lead_source TEXT NOT NULL,              -- Web, Trade Show, Partner Referral, Cold Call, Email Campaign
    status TEXT NOT NULL,                   -- New, Working, Qualified, Converted, Disqualified
    lead_score INTEGER,
    industry TEXT,
    annual_revenue REAL,
    owner_id TEXT NOT NULL,
    created_date DATE NOT NULL,
    converted_date DATE,
    converted_account_id TEXT,
    converted_opportunity_id TEXT,
    disqualified_reason TEXT,
    FOREIGN KEY (owner_id) REFERENCES users(id),
    FOREIGN KEY (converted_account_id) REFERENCES accounts(id)
);

CREATE TABLE IF NOT EXISTS products (
    id TEXT PRIMARY KEY,                    -- Salesforce-style ID prefix 01t
    sku TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    product_family TEXT NOT NULL,           -- e.g. Power Management, Sensors, MCUs
    product_category TEXT NOT NULL,         -- e.g. DC-DC Converter, Temperature Sensor
    description TEXT,
    list_price REAL NOT NULL,
    currency TEXT DEFAULT 'USD',
    unit_of_measure TEXT DEFAULT 'EA',
    status TEXT NOT NULL,                   -- Active, EOL, NRND, Sample
    launch_date DATE,
    target_industries TEXT,                 -- comma-separated: Automotive, Industrial, Consumer, Aerospace
    design_specs TEXT,                      -- JSON: key specs for design fit matching
    created_date DATE NOT NULL
);

CREATE TABLE IF NOT EXISTS pricebook_entries (
    id TEXT PRIMARY KEY,
    product_id TEXT NOT NULL,
    pricebook_name TEXT NOT NULL,           -- Standard, Enterprise, OEM, Distributor
    unit_price REAL NOT NULL,
    discount_pct REAL DEFAULT 0,
    min_quantity INTEGER DEFAULT 1,
    valid_from DATE NOT NULL,
    valid_to DATE,
    FOREIGN KEY (product_id) REFERENCES products(id)
);

CREATE TABLE IF NOT EXISTS opportunities (
    id TEXT PRIMARY KEY,                    -- Salesforce-style ID prefix 006
    name TEXT NOT NULL,
    account_id TEXT NOT NULL,
    owner_id TEXT NOT NULL,
    stage TEXT NOT NULL,                    -- Prospecting, Qualification, Needs Analysis, Proposal, Negotiation, Closed Won, Closed Lost
    amount REAL,
    probability REAL,
    close_date DATE NOT NULL,
    forecast_category TEXT,                 -- Pipeline, Best Case, Commit, Closed
    lead_source TEXT,
    primary_product_family TEXT,
    competitor TEXT,
    next_step TEXT,
    description TEXT,
    created_date DATE NOT NULL,
    closed_date DATE,
    loss_reason TEXT,
    customer_design_requirements TEXT,      -- JSON: temp range, voltage, package, certification needs
    FOREIGN KEY (account_id) REFERENCES accounts(id),
    FOREIGN KEY (owner_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS quotes (
    id TEXT PRIMARY KEY,                    -- Salesforce-style ID prefix 0Q0
    quote_number TEXT UNIQUE NOT NULL,
    opportunity_id TEXT NOT NULL,
    account_id TEXT NOT NULL,
    owner_id TEXT NOT NULL,
    status TEXT NOT NULL,                   -- Draft, In Review, Approved, Sent, Accepted, Rejected, Expired
    pricebook_name TEXT,
    subtotal REAL NOT NULL,
    discount_amount REAL DEFAULT 0,
    tax_amount REAL DEFAULT 0,
    grand_total REAL NOT NULL,
    valid_until DATE,
    created_date DATE NOT NULL,
    sent_date DATE,
    approved_date DATE,
    accepted_date DATE,
    rejected_date DATE,
    rejection_reason TEXT,
    external_order_id TEXT,                 -- Link to ERP sales order
    FOREIGN KEY (opportunity_id) REFERENCES opportunities(id),
    FOREIGN KEY (account_id) REFERENCES accounts(id),
    FOREIGN KEY (owner_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS quote_line_items (
    id TEXT PRIMARY KEY,
    quote_id TEXT NOT NULL,
    product_id TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    unit_price REAL NOT NULL,
    discount_pct REAL DEFAULT 0,
    line_total REAL NOT NULL,
    sort_order INTEGER,
    FOREIGN KEY (quote_id) REFERENCES quotes(id),
    FOREIGN KEY (product_id) REFERENCES products(id)
);

-- Revenue data synced back from ERP, attached to the quote (per the PDF flow)
CREATE TABLE IF NOT EXISTS quote_revenue_sync (
    id TEXT PRIMARY KEY,
    quote_id TEXT NOT NULL,
    external_invoice_number TEXT,           -- From ERP
    external_invoice_id TEXT,               -- From ERP
    revenue_amount REAL NOT NULL,
    revenue_date DATE NOT NULL,
    recognition_status TEXT NOT NULL,       -- Recognized, Deferred, Pending
    sync_date DATE NOT NULL,
    FOREIGN KEY (quote_id) REFERENCES quotes(id)
);

-- Reliability insights flowing back into Salesforce on Opportunity/Quote/Account
CREATE TABLE IF NOT EXISTS reliability_insights_sync (
    id TEXT PRIMARY KEY,
    product_id TEXT NOT NULL,
    account_id TEXT,
    opportunity_id TEXT,
    reliability_score REAL NOT NULL,        -- 0-100
    failure_rate_ppm REAL,
    mtbf_hours REAL,
    recommendation TEXT,
    sync_date DATE NOT NULL,
    FOREIGN KEY (product_id) REFERENCES products(id),
    FOREIGN KEY (account_id) REFERENCES accounts(id),
    FOREIGN KEY (opportunity_id) REFERENCES opportunities(id)
);

CREATE INDEX IF NOT EXISTS idx_accounts_owner ON accounts(owner_id);
CREATE INDEX IF NOT EXISTS idx_accounts_key ON accounts(is_key_account);
CREATE INDEX IF NOT EXISTS idx_opps_account ON opportunities(account_id);
CREATE INDEX IF NOT EXISTS idx_opps_stage ON opportunities(stage);
CREATE INDEX IF NOT EXISTS idx_opps_close ON opportunities(close_date);
CREATE INDEX IF NOT EXISTS idx_quotes_opp ON quotes(opportunity_id);
CREATE INDEX IF NOT EXISTS idx_quotes_account ON quotes(account_id);
CREATE INDEX IF NOT EXISTS idx_quotes_status ON quotes(status);
CREATE INDEX IF NOT EXISTS idx_qli_quote ON quote_line_items(quote_id);
CREATE INDEX IF NOT EXISTS idx_qli_product ON quote_line_items(product_id);
CREATE INDEX IF NOT EXISTS idx_qrs_quote ON quote_revenue_sync(quote_id);
CREATE INDEX IF NOT EXISTS idx_leads_status ON leads(status);
CREATE INDEX IF NOT EXISTS idx_products_family ON products(product_family);
