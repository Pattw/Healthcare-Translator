-- 1. Procedures Catalog (CPT / HCPCS & RVUs)
CREATE TABLE procedures (
    cpt_code VARCHAR(10) PRIMARY KEY,
    description TEXT NOT NULL,
    category VARCHAR(50) NOT NULL, -- e.g., 'IMAGING', 'SURGERY', 'EVALUATION', 'PREVENTIVE'
    base_rvu NUMERIC(6, 2) NOT NULL DEFAULT 0.00,
    base_allowable_cost NUMERIC(10, 2) NOT NULL, -- Medicare rate (RVU * Conversion Factor)
    is_preventive BOOLEAN DEFAULT FALSE
);

-- 2. Insurance Plans (Parsed from your SBC PDFs)
CREATE TABLE insurance_plans (
    plan_id VARCHAR(50) PRIMARY KEY,
    payer_name VARCHAR(100) NOT NULL,
    plan_name VARCHAR(150) NOT NULL,
    plan_type VARCHAR(20) NOT NULL, -- 'HMO', 'PPO', 'HDHP', 'MEDICARE'
    contract_multiplier NUMERIC(4, 2) NOT NULL DEFAULT 1.00,
    individual_deductible NUMERIC(10, 2) NOT NULL,
    oop_max NUMERIC(10, 2), -- Can be NULL for Original Medicare Part B
    pcp_copay NUMERIC(10, 2),
    specialist_copay NUMERIC(10, 2),
    imaging_coinsurance NUMERIC(4, 2) NOT NULL DEFAULT 0.20,
    outpatient_surgery_coinsurance NUMERIC(4, 2) NOT NULL DEFAULT 0.20,
    emergency_copay NUMERIC(10, 2) DEFAULT 0.00
);

-- 3. Synthetic Patients (Synthea Model + Accumulators)
CREATE TABLE patients (
    patient_id VARCHAR(20) PRIMARY KEY,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    date_of_birth DATE NOT NULL,
    gender VARCHAR(10) NOT NULL,
    plan_id VARCHAR(50) REFERENCES insurance_plans(plan_id),
    member_id VARCHAR(50) NOT NULL,
    scenario_title VARCHAR(150),
    deductible_met_ytd NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    oop_met_ytd NUMERIC(10, 2) NOT NULL DEFAULT 0.00
);

-- 4. Prior Authorization & Coverage Rules (CRD / DTR Engine)
CREATE TABLE coverage_rules (
    rule_id SERIAL PRIMARY KEY,
    cpt_code VARCHAR(10) REFERENCES procedures(cpt_code),
    plan_id VARCHAR(50) REFERENCES insurance_plans(plan_id),
    pa_required BOOLEAN DEFAULT FALSE,
    min_conservative_weeks INTEGER DEFAULT 0,
    red_flag_bypass_allowed BOOLEAN DEFAULT TRUE,
    required_documents JSONB DEFAULT '[]'::jsonb,
    denial_rationale TEXT,
    appeal_guidelines TEXT
);