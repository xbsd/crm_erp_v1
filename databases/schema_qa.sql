-- QA / Quality Systems Database Schema (Reliability Management)
-- Captures: Test specs, Test results, Reliability metrics (MTBF/MTTR/FIT),
-- Failures, Customer Returns, Environmental tests, Compliance, Reliability scores

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS test_specifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    spec_number TEXT UNIQUE NOT NULL,       -- TS-NNNNN
    external_product_id TEXT NOT NULL,      -- Link to CRM products.id
    test_name TEXT NOT NULL,
    test_type TEXT NOT NULL,                -- Electrical, Mechanical, Environmental, Burn-In, Functional, ESD, EMC
    test_standard TEXT,                     -- JEDEC, IPC, MIL-STD, AEC-Q100, etc.
    parameters TEXT,                        -- JSON for test parameters
    pass_criteria TEXT,
    typical_duration_hrs REAL,
    created_date DATE NOT NULL
);

CREATE TABLE IF NOT EXISTS test_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_number TEXT UNIQUE NOT NULL,        -- TR-YYYYNNNNNN
    spec_id INTEGER NOT NULL,
    external_product_id TEXT NOT NULL,
    run_date DATE NOT NULL,
    operator TEXT,
    lab_location TEXT,                      -- HQ Lab, APAC Lab, EU Lab
    sample_size INTEGER NOT NULL,
    samples_passed INTEGER DEFAULT 0,
    samples_failed INTEGER DEFAULT 0,
    samples_inconclusive INTEGER DEFAULT 0,
    pass_rate REAL,
    status TEXT,                            -- Complete, In Progress, Aborted
    batch_lot_code TEXT,
    FOREIGN KEY (spec_id) REFERENCES test_specifications(id)
);

CREATE TABLE IF NOT EXISTS test_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    test_run_id INTEGER NOT NULL,
    sample_id TEXT NOT NULL,
    pass_fail TEXT NOT NULL,                -- Pass, Fail, Marginal, Inconclusive
    measured_value REAL,
    measured_units TEXT,
    spec_min REAL,
    spec_max REAL,
    environmental_conditions TEXT,          -- JSON: temp_c, humidity_pct, voltage_v
    failure_mode TEXT,
    notes TEXT,
    FOREIGN KEY (test_run_id) REFERENCES test_runs(id)
);

CREATE TABLE IF NOT EXISTS reliability_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    external_product_id TEXT NOT NULL,      -- Link to CRM products.id
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    period_label TEXT NOT NULL,             -- YYYY-Qn
    mtbf_hours REAL,                        -- Mean Time Between Failures
    mttr_hours REAL,                        -- Mean Time To Repair
    failure_rate_ppm REAL,                  -- Parts Per Million failure rate
    fit_rate REAL,                          -- Failures In Time (per 10^9 hours)
    sample_size INTEGER,
    field_population INTEGER,               -- Estimated units in the field
    operating_hours_total REAL,
    confidence_pct REAL DEFAULT 90,
    methodology TEXT,                       -- Telcordia, MIL-HDBK-217, Field Data
    created_date DATE NOT NULL
);

CREATE TABLE IF NOT EXISTS failures (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    failure_number TEXT UNIQUE NOT NULL,    -- FLR-YYYYNNNNNN
    external_product_id TEXT NOT NULL,
    external_customer_id TEXT,              -- ERP customer
    external_account_id TEXT,               -- CRM account
    failure_date DATE NOT NULL,
    detection_stage TEXT,                   -- Incoming Inspection, Production, Burn-In, Field, Customer Return
    severity TEXT NOT NULL,                 -- Critical, Major, Minor, Cosmetic
    failure_mode TEXT NOT NULL,             -- Open, Short, Drift, Mechanical, Thermal Runaway, etc.
    root_cause TEXT,
    root_cause_category TEXT,               -- Design, Process, Material, Handling, Application
    qty_affected INTEGER DEFAULT 1,
    units_in_field_at_failure INTEGER,
    corrective_action TEXT,
    status TEXT,                            -- Open, Investigating, Resolved, Closed
    resolved_date DATE,
    cost_impact REAL
);

CREATE TABLE IF NOT EXISTS customer_returns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rma_number TEXT UNIQUE NOT NULL,        -- RMA-YYYYNNNNNN
    external_product_id TEXT NOT NULL,
    external_customer_id TEXT,              -- ERP customer
    external_account_id TEXT,               -- CRM account
    external_invoice_number TEXT,           -- Original invoice in ERP
    return_date DATE NOT NULL,
    qty_returned INTEGER NOT NULL,
    return_reason TEXT NOT NULL,            -- Defective, Wrong Item, Customer Error, Damaged in Transit, Quality, Performance Below Spec
    defect_category TEXT,                   -- Functional, Cosmetic, Reliability, Premature Failure
    disposition TEXT,                       -- Repair, Replace, Refund, Scrap, RTV (Return to Vendor)
    replacement_cost REAL,
    days_in_service INTEGER,                -- Time from ship to return
    customer_complaint TEXT,
    investigation_notes TEXT,
    related_failure_id INTEGER,
    status TEXT,                            -- Received, Investigating, Approved, Resolved, Rejected
    FOREIGN KEY (related_failure_id) REFERENCES failures(id)
);

CREATE TABLE IF NOT EXISTS environmental_tests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    test_id TEXT UNIQUE NOT NULL,
    external_product_id TEXT NOT NULL,
    test_type TEXT NOT NULL,                -- Thermal Cycling, HAST, Humidity, Vibration, Shock, ESD, Salt Spray
    standard TEXT,
    conditions TEXT,                        -- JSON: temp_min/max, cycles, humidity, etc.
    duration_hrs REAL,
    samples_tested INTEGER,
    samples_passed INTEGER,
    test_date DATE NOT NULL,
    passed INTEGER NOT NULL,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS compliance_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    external_product_id TEXT NOT NULL,
    standard TEXT NOT NULL,                 -- UL, CE, FCC, RoHS, REACH, AEC-Q100, IATF 16949, ISO 9001
    certificate_number TEXT,
    issued_by TEXT,
    issue_date DATE NOT NULL,
    expiry_date DATE,
    status TEXT NOT NULL,                   -- Active, Expired, Pending Renewal, Revoked
    notes TEXT
);

CREATE TABLE IF NOT EXISTS reliability_scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    external_product_id TEXT NOT NULL,
    score REAL NOT NULL,                    -- 0-100 composite reliability score
    score_grade TEXT,                       -- A+, A, B, C, D, F
    score_date DATE NOT NULL,
    period TEXT NOT NULL,
    mtbf_component REAL,
    return_rate_component REAL,
    test_pass_component REAL,
    field_failure_component REAL,
    recommendation TEXT,
    methodology_version TEXT DEFAULT 'v1.2'
);

CREATE INDEX IF NOT EXISTS idx_ts_product ON test_specifications(external_product_id);
CREATE INDEX IF NOT EXISTS idx_tr_product ON test_runs(external_product_id);
CREATE INDEX IF NOT EXISTS idx_tres_run ON test_results(test_run_id);
CREATE INDEX IF NOT EXISTS idx_rm_product ON reliability_metrics(external_product_id);
CREATE INDEX IF NOT EXISTS idx_rm_period ON reliability_metrics(period_label);
CREATE INDEX IF NOT EXISTS idx_flr_product ON failures(external_product_id);
CREATE INDEX IF NOT EXISTS idx_flr_account ON failures(external_account_id);
CREATE INDEX IF NOT EXISTS idx_flr_date ON failures(failure_date);
CREATE INDEX IF NOT EXISTS idx_ret_product ON customer_returns(external_product_id);
CREATE INDEX IF NOT EXISTS idx_ret_account ON customer_returns(external_account_id);
CREATE INDEX IF NOT EXISTS idx_ret_date ON customer_returns(return_date);
CREATE INDEX IF NOT EXISTS idx_rs_product ON reliability_scores(external_product_id);
