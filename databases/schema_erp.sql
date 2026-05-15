-- ERP Database Schema (Back Office)
-- Modeled after typical enterprise ERP (SAP/Oracle/Microsoft Dynamics)
-- Contains: Customer master, Items master, Sales Orders, Invoices, Payments, GL, Revenue

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_number TEXT UNIQUE NOT NULL,   -- ERP-style: CUST-NNNNN
    external_account_id TEXT NOT NULL,      -- Link to CRM account.id (the integration key)
    name TEXT NOT NULL,
    billing_address TEXT,
    shipping_address TEXT,
    country TEXT,
    state TEXT,
    city TEXT,
    tax_id TEXT,
    payment_terms TEXT,                     -- NET30, NET45, NET60, NET90
    credit_limit REAL,
    customer_class TEXT,                    -- A (Strategic), B (Important), C (Standard), D (At Risk)
    currency TEXT DEFAULT 'USD',
    on_credit_hold INTEGER DEFAULT 0,
    created_date DATE NOT NULL
);

CREATE TABLE IF NOT EXISTS items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_number TEXT UNIQUE NOT NULL,       -- ERP-style: ITM-NNNNN
    external_product_id TEXT NOT NULL,      -- Link to CRM products.id
    name TEXT NOT NULL,
    description TEXT,
    item_category TEXT NOT NULL,
    unit_of_measure TEXT DEFAULT 'EA',
    standard_cost REAL NOT NULL,
    list_price REAL NOT NULL,
    inventory_on_hand INTEGER DEFAULT 0,
    lead_time_days INTEGER DEFAULT 14,
    abc_class TEXT,                         -- A, B, C inventory classification
    status TEXT NOT NULL,                   -- Active, Inactive, Obsolete
    created_date DATE NOT NULL
);

CREATE TABLE IF NOT EXISTS sales_orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_number TEXT UNIQUE NOT NULL,      -- SO-YYYYNNNNNN
    customer_id INTEGER NOT NULL,
    external_quote_id TEXT,                 -- Link to CRM quote.id (Quote-to-Order flow)
    external_quote_number TEXT,
    order_date DATE NOT NULL,
    requested_delivery_date DATE,
    confirmed_delivery_date DATE,
    actual_delivery_date DATE,
    status TEXT NOT NULL,                   -- Draft, Confirmed, In Production, Shipped, Delivered, Invoiced, Cancelled
    order_type TEXT,                        -- Standard, Rush, Sample, Service
    subtotal REAL NOT NULL,
    discount_amount REAL DEFAULT 0,
    tax_amount REAL DEFAULT 0,
    shipping_amount REAL DEFAULT 0,
    grand_total REAL NOT NULL,
    currency TEXT DEFAULT 'USD',
    shipping_method TEXT,
    payment_terms TEXT,
    sales_rep_external_id TEXT,             -- Link to CRM users.id
    cancellation_reason TEXT,
    FOREIGN KEY (customer_id) REFERENCES customers(id)
);

CREATE TABLE IF NOT EXISTS sales_order_lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    line_number INTEGER NOT NULL,
    item_id INTEGER NOT NULL,
    quantity_ordered INTEGER NOT NULL,
    quantity_shipped INTEGER DEFAULT 0,
    unit_price REAL NOT NULL,
    discount_pct REAL DEFAULT 0,
    line_total REAL NOT NULL,
    requested_date DATE,
    promised_date DATE,
    status TEXT,                            -- Open, Partial, Shipped, Cancelled
    FOREIGN KEY (order_id) REFERENCES sales_orders(id),
    FOREIGN KEY (item_id) REFERENCES items(id)
);

CREATE TABLE IF NOT EXISTS invoices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_number TEXT UNIQUE NOT NULL,    -- INV-YYYYNNNNNN
    order_id INTEGER NOT NULL,
    customer_id INTEGER NOT NULL,
    invoice_date DATE NOT NULL,
    due_date DATE NOT NULL,
    subtotal REAL NOT NULL,
    tax_amount REAL DEFAULT 0,
    total_amount REAL NOT NULL,
    amount_paid REAL DEFAULT 0,
    amount_outstanding REAL NOT NULL,
    status TEXT NOT NULL,                   -- Draft, Posted, Sent, Partially Paid, Paid, Overdue, Cancelled, Disputed
    payment_terms TEXT,
    currency TEXT DEFAULT 'USD',
    recognition_status TEXT,                -- Recognized, Deferred, Pending
    recognition_date DATE,
    posted_date DATE,
    last_payment_date DATE,
    FOREIGN KEY (order_id) REFERENCES sales_orders(id),
    FOREIGN KEY (customer_id) REFERENCES customers(id)
);

CREATE TABLE IF NOT EXISTS invoice_lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id INTEGER NOT NULL,
    order_line_id INTEGER,
    line_number INTEGER NOT NULL,
    item_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    unit_price REAL NOT NULL,
    line_total REAL NOT NULL,
    FOREIGN KEY (invoice_id) REFERENCES invoices(id),
    FOREIGN KEY (order_line_id) REFERENCES sales_order_lines(id),
    FOREIGN KEY (item_id) REFERENCES items(id)
);

CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    payment_number TEXT UNIQUE NOT NULL,    -- PAY-YYYYNNNNNN
    invoice_id INTEGER NOT NULL,
    customer_id INTEGER NOT NULL,
    payment_date DATE NOT NULL,
    amount REAL NOT NULL,
    payment_method TEXT,                    -- Wire, ACH, Check, Credit Card, PO
    reference_number TEXT,
    status TEXT NOT NULL,                   -- Posted, Cleared, Reconciled, Failed
    FOREIGN KEY (invoice_id) REFERENCES invoices(id),
    FOREIGN KEY (customer_id) REFERENCES customers(id)
);

CREATE TABLE IF NOT EXISTS gl_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    journal_number TEXT NOT NULL,
    entry_date DATE NOT NULL,
    account_code TEXT NOT NULL,             -- 4000 Revenue, 1200 AR, 5000 COGS, etc.
    account_name TEXT NOT NULL,
    debit REAL DEFAULT 0,
    credit REAL DEFAULT 0,
    description TEXT,
    source_doc_type TEXT,                   -- Invoice, Payment, JE
    source_doc_id INTEGER,
    cost_center TEXT,
    period TEXT                             -- YYYY-MM
);

CREATE TABLE IF NOT EXISTS revenue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id INTEGER NOT NULL,
    customer_id INTEGER NOT NULL,
    item_id INTEGER NOT NULL,
    external_account_id TEXT,               -- For CRM linkage
    external_quote_id TEXT,                 -- For CRM linkage
    recognized_date DATE NOT NULL,
    period TEXT NOT NULL,                   -- YYYY-Qn
    fiscal_year INTEGER NOT NULL,
    fiscal_quarter INTEGER NOT NULL,
    amount REAL NOT NULL,
    recognition_status TEXT NOT NULL,
    product_family TEXT,
    region TEXT,
    FOREIGN KEY (invoice_id) REFERENCES invoices(id),
    FOREIGN KEY (customer_id) REFERENCES customers(id),
    FOREIGN KEY (item_id) REFERENCES items(id)
);

CREATE INDEX IF NOT EXISTS idx_customers_ext ON customers(external_account_id);
CREATE INDEX IF NOT EXISTS idx_items_ext ON items(external_product_id);
CREATE INDEX IF NOT EXISTS idx_so_customer ON sales_orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_so_quote ON sales_orders(external_quote_id);
CREATE INDEX IF NOT EXISTS idx_so_date ON sales_orders(order_date);
CREATE INDEX IF NOT EXISTS idx_sol_order ON sales_order_lines(order_id);
CREATE INDEX IF NOT EXISTS idx_inv_customer ON invoices(customer_id);
CREATE INDEX IF NOT EXISTS idx_inv_order ON invoices(order_id);
CREATE INDEX IF NOT EXISTS idx_inv_date ON invoices(invoice_date);
CREATE INDEX IF NOT EXISTS idx_rev_customer ON revenue(customer_id);
CREATE INDEX IF NOT EXISTS idx_rev_period ON revenue(period);
CREATE INDEX IF NOT EXISTS idx_rev_fy_q ON revenue(fiscal_year, fiscal_quarter);
CREATE INDEX IF NOT EXISTS idx_rev_ext_account ON revenue(external_account_id);
