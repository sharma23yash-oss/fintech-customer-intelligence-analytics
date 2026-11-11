-- Brokerage Customer Friction Detector - SQLite schema (ALL DATA IS SYNTHETIC)
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    user_id                         TEXT PRIMARY KEY,
    registration_date               TEXT NOT NULL,
    registration_month              TEXT,
    acquisition_campaign_id         TEXT,
    acquisition_channel             TEXT,
    source_platform                 TEXT,
    city                            TEXT,
    age_group                       TEXT,
    device_type                     TEXT,
    risk_profile                    TEXT,
    kyc_date_asof                   TEXT,     -- NULL = step not completed on/before 2026-10-31
    bank_date_asof                  TEXT,
    deposit_date_asof               TEXT,
    trade_date_asof                 TEXT,
    first_deposit_amount_asof_inr   REAL,
    last_active_date_adj            TEXT,
    total_trades                    INTEGER,
    total_trading_value_inr         REAL,
    total_deposit_value_inr         REAL,
    trading_value_6m_inr            REAL,
    trade_months_6m                 INTEGER,
    active_months_6m                INTEGER,
    activity_ratio                  REAL,
    flag_trade_conflict             INTEGER,
    flag_deposit_conflict           INTEGER,
    flag_last_active_conflict       INTEGER,
    flag_activity_conflict          INTEGER,
    data_label                      TEXT DEFAULT 'SYNTHETIC'
);

CREATE TABLE IF NOT EXISTS tickets (
    ticket_id             TEXT PRIMARY KEY,
    user_id               TEXT NOT NULL REFERENCES users(user_id),
    created_date          TEXT NOT NULL,
    category              TEXT,
    priority              TEXT,
    status                TEXT,               -- Resolved / Open / Escalated
    resolution_time_hours REAL,               -- NULL while unresolved
    csat_score            REAL,
    data_label            TEXT DEFAULT 'SYNTHETIC'
);

CREATE TABLE IF NOT EXISTS monthly_activity (
    user_id            TEXT NOT NULL REFERENCES users(user_id),
    activity_month     TEXT NOT NULL,
    active_in_month    INTEGER,
    trade_count        INTEGER,
    trading_value_inr  REAL,
    deposit_value_inr  REAL,
    withdrawal_value_inr REAL,
    PRIMARY KEY (user_id, activity_month)
);

CREATE TABLE IF NOT EXISTS config (
    key   TEXT PRIMARY KEY,
    value TEXT,
    note  TEXT
);

-- Output of the latest engine run: one row per customer registered on/before the as-of date.
CREATE TABLE IF NOT EXISTS customer_friction (
    user_id               TEXT PRIMARY KEY,
    as_of_date            TEXT NOT NULL,
    registration_date     TEXT,
    registration_month    TEXT,
    city                  TEXT,
    acquisition_channel   TEXT,
    stage_idx             INTEGER,
    stage_name            TEXT,
    journey_status        TEXT,
    anchor_event          TEXT,
    anchor_date           TEXT,
    dwell_days            INTEGER,
    window_days           INTEGER,
    days_overdue          INTEGER,
    tenure_days           INTEGER,
    days_inactive         INTEGER,
    eligibility_status    TEXT,
    friction_categories   TEXT,
    primary_category      TEXT,
    is_flagged            INTEGER,
    tickets_total         INTEGER,
    tickets_unresolved    INTEGER,
    tickets_escalated     INTEGER,
    oldest_unresolved_days INTEGER,
    source_conflict_relevant INTEGER,
    conflict_detail       TEXT,
    data_confidence       TEXT,
    sequence_anomaly      INTEGER,
    pts_days_since_registration REAL,
    pts_funnel_stage      REAL,
    pts_inactivity        REAL,
    pts_support           REAL,
    pts_activity          REAL,
    pts_prior_transactions REAL,
    priority_score        REAL,
    priority_band         TEXT,
    score_type            TEXT,
    data_label            TEXT DEFAULT 'SYNTHETIC'
);

-- One row per (run date, flagged customer): history used to find NEWLY flagged customers.
CREATE TABLE IF NOT EXISTS friction_snapshot (
    run_date          TEXT NOT NULL,
    user_id           TEXT NOT NULL,
    primary_category  TEXT,
    friction_categories TEXT,
    priority_score    REAL,
    priority_band     TEXT,
    PRIMARY KEY (run_date, user_id)
);

CREATE TABLE IF NOT EXISTS friction_runs (
    run_date            TEXT PRIMARY KEY,
    run_timestamp_utc   TEXT,
    customers_analysed  INTEGER,
    customers_flagged   INTEGER,
    newly_flagged       INTEGER,
    no_longer_flagged   INTEGER,
    previous_run_date   TEXT,
    llm_used            INTEGER DEFAULT 0,
    note                TEXT
);

CREATE INDEX IF NOT EXISTS idx_tickets_user   ON tickets(user_id);
CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets(status);
CREATE INDEX IF NOT EXISTS idx_cf_category    ON customer_friction(primary_category);
CREATE INDEX IF NOT EXISTS idx_cf_flagged     ON customer_friction(is_flagged);
CREATE INDEX IF NOT EXISTS idx_snap_user      ON friction_snapshot(user_id);

CREATE VIEW IF NOT EXISTS v_flagged AS
    SELECT * FROM customer_friction WHERE is_flagged = 1;

CREATE VIEW IF NOT EXISTS v_category_summary AS
    SELECT primary_category,
           COUNT(*)                                             AS customers,
           SUM(priority_band = 'High')                          AS high_priority,
           ROUND(AVG(priority_score), 1)                        AS avg_priority_score,
           SUM(data_confidence = 'LOW')                         AS verify_first
    FROM customer_friction
    WHERE is_flagged = 1
    GROUP BY primary_category;
