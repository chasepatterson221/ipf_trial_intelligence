-- Sponsors: organizations running IPF/PF trials
CREATE TABLE sponsors (
    sponsor_id SERIAL PRIMARY KEY,
    sponsor_name TEXT NOT NULL UNIQUE,
    sponsor_class TEXT,              -- e.g. INDUSTRY, NIH, OTHER (from CT.gov)
    publicly_traded BOOLEAN DEFAULT FALSE,  -- bridges to Project 2 (earnings tracker)
    ticker_symbol TEXT,              -- nullable, only for publicly_traded = TRUE
    created_at TIMESTAMP DEFAULT NOW()
);

-- Trials: core trial-level data from ClinicalTrials.gov
CREATE TABLE trials (
    nct_id TEXT PRIMARY KEY,         -- ClinicalTrials.gov identifier, e.g. NCT01234567
    sponsor_id INTEGER REFERENCES sponsors(sponsor_id),
    brief_title TEXT,
    overall_status TEXT,             -- RECRUITING, COMPLETED, TERMINATED, etc.
    phase TEXT,                      -- PHASE1, PHASE2, PHASE3, PHASE4, NA
    study_type TEXT,                 -- INTERVENTIONAL, OBSERVATIONAL
    condition TEXT,                  -- raw condition string from API
    start_date DATE,
    primary_completion_date DATE,
    completion_date DATE,
    enrollment_count INTEGER,
    why_stopped TEXT,                -- populated when status = TERMINATED/WITHDRAWN
    created_at TIMESTAMP DEFAULT NOW()
);

-- Interventions: drugs/devices tested per trial (many-to-one with trials)
CREATE TABLE interventions (
    intervention_id SERIAL PRIMARY KEY,
    nct_id TEXT REFERENCES trials(nct_id),
    intervention_type TEXT,          -- DRUG, DEVICE, BIOLOGICAL, etc.
    intervention_name TEXT,
    mechanism_class TEXT             -- you'll hand-tag/derive this: e.g. "antifibrotic", "anti-inflammatory"
);

-- FDA outcomes: approval status linked to trials via sponsor/drug matching
CREATE TABLE fda_outcomes (
    outcome_id SERIAL PRIMARY KEY,
    nct_id TEXT REFERENCES trials(nct_id),
    application_number TEXT,         -- openFDA application number
    approval_status TEXT,            -- APPROVED, NOT APPROVED, PENDING
    approval_date DATE,
    application_type TEXT            -- NDA, BLA, etc.
);

-- Trial risk scores: written by your logistic regression model (Project step 4)
CREATE TABLE trial_risk_scores (
    nct_id TEXT PRIMARY KEY REFERENCES trials(nct_id),
    termination_risk_score NUMERIC(5,4),  -- predicted probability 0-1
    model_version TEXT,
    scored_at TIMESTAMP DEFAULT NOW()
);

-- Indexes you'll actually use in your CTE/window function queries
CREATE INDEX idx_trials_sponsor ON trials(sponsor_id);
CREATE INDEX idx_trials_status ON trials(overall_status);
CREATE INDEX idx_trials_phase ON trials(phase);
CREATE INDEX idx_interventions_nct ON interventions(nct_id);
CREATE INDEX idx_fda_nct ON fda_outcomes(nct_id);