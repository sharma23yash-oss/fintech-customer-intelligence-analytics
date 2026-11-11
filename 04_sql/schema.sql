-- Fintech synthetic analytics database (SQLite). ALL DATA ARE SYNTHETIC.
-- Source: cleaned tables (data/cleaned/*.csv). Snapshot date: 2026-10-31.
-- Conventions: *_asof columns count only events on or before the snapshot. Mature cohort = registered before 2026-10.
PRAGMA foreign_keys = ON;

CREATE TABLE campaigns (
    campaign_id         TEXT PRIMARY KEY,
    campaign_name       TEXT NOT NULL,
    channel             TEXT NOT NULL,
    source_platform     TEXT,
    campaign_spend_inr  INTEGER NOT NULL CHECK (campaign_spend_inr >= 0),
    channel_group       TEXT,
    is_paid             INTEGER NOT NULL CHECK (is_paid IN (0,1)),
    spend_basis         TEXT                       -- 'recorded_spend' or 'no_recorded_spend' (organic: CAC not defined)
);

CREATE TABLE users (
    user_id                  TEXT PRIMARY KEY,
    registration_date        TEXT NOT NULL,         -- ISO yyyy-mm-dd
    registration_month       TEXT NOT NULL,         -- yyyy-mm
    acquisition_campaign_id  TEXT NOT NULL REFERENCES campaigns(campaign_id),
    acquisition_channel      TEXT NOT NULL,
    city TEXT, age_group TEXT, device_type TEXT, risk_profile TEXT,
    kyc_asof INTEGER, bank_asof INTEGER, deposit_asof INTEGER, trade_asof INTEGER,
    kyc_date_asof TEXT, bank_date_asof TEXT, deposit_date_asof TEXT, trade_date_asof TEXT,
    first_deposit_amount_asof_inr REAL,
    cohort_maturity TEXT, funnel_mature INTEGER, eligible_30d INTEGER, eligible_90d INTEGER,
    furthest_stage_asof TEXT,
    days_reg_to_kyc REAL, days_kyc_to_bank REAL, days_bank_to_deposit REAL, days_deposit_to_trade REAL, days_reg_to_trade REAL,
    active_30d_adj REAL, inactive_30d_adj REAL, inactive_90d_adj REAL, days_inactive_adj REAL,
    tenure_days INTEGER, months_observed INTEGER, active_months INTEGER, trade_months INTEGER,
    total_trades REAL, total_trading_value_inr REAL, total_deposit_value_inr REAL,
    trade_months_6m REAL, trading_value_6m_inr REAL, active_months_6m REAL, activity_ratio REAL,
    months_since_last_active_monthly REAL, never_active_monthly INTEGER, dormant_3m_monthly INTEGER,
    m1_retained REAL, m3_retained REAL, m6_retained REAL,
    ticket_count INTEGER, unresolved_ticket_count INTEGER
);

CREATE TABLE monthly_activity (
    user_id TEXT NOT NULL REFERENCES users(user_id),
    activity_month TEXT NOT NULL,                  -- yyyy-mm
    months_since_registration INTEGER NOT NULL,    -- 0 = registration month
    registration_month TEXT,
    active_in_month INTEGER NOT NULL, traded_in_month INTEGER, deposited_in_month INTEGER, withdrew_in_month INTEGER,
    trade_count INTEGER, trading_value_inr REAL, deposit_value_inr REAL, withdrawal_value_inr REAL, net_flow_inr REAL,
    PRIMARY KEY (user_id, activity_month)
);

CREATE TABLE support_tickets (
    ticket_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(user_id),
    created_date TEXT, created_month TEXT,
    category TEXT, priority TEXT, status TEXT,
    resolution_time_hours REAL, csat_score REAL,
    is_resolved INTEGER, is_unresolved INTEGER, ticket_age_days INTEGER, backlog_age_bucket TEXT, csat_band TEXT,
    days_since_registration INTEGER, related_funnel_stage TEXT, stage_pending_at_ticket REAL
);

CREATE INDEX ix_users_channel   ON users(acquisition_channel);
CREATE INDEX ix_users_campaign  ON users(acquisition_campaign_id);
CREATE INDEX ix_users_regmonth  ON users(registration_month);
CREATE INDEX ix_act_month       ON monthly_activity(activity_month);
CREATE INDEX ix_act_offset      ON monthly_activity(months_since_registration);
CREATE INDEX ix_tkt_user        ON support_tickets(user_id);
CREATE INDEX ix_tkt_category    ON support_tickets(category);

-- Reusable views -------------------------------------------------------------------------
CREATE VIEW v_mature_users AS SELECT * FROM users WHERE funnel_mature = 1;   -- n = 9,116

-- Journey segment (Phase 3 rule). Max historic stage lags in mature data (days): KYC 11, bank 7, deposit 14, trade 11.
CREATE VIEW v_user_journey AS
SELECT u.*,
       CAST(julianday('2026-10-31') - julianday(MAX(registration_date,
              COALESCE(kyc_date_asof, registration_date), COALESCE(bank_date_asof, registration_date),
              COALESCE(deposit_date_asof, registration_date))) AS INTEGER) AS days_since_last_stage_event,
       CASE WHEN trade_date_asof IS NULL THEN NULL
            ELSE CAST(julianday('2026-10-31') - julianday(trade_date_asof) AS INTEGER) END AS days_since_first_trade
FROM users u;

CREATE VIEW v_journey_segment AS
SELECT user_id, acquisition_channel, registration_month, furthest_stage_asof,
  CASE
    WHEN furthest_stage_asof = 'Registered'    AND days_since_last_stage_event <= 11 THEN '01 New / in-flight onboarding'
    WHEN furthest_stage_asof = 'KYC Completed' AND days_since_last_stage_event <= 7  THEN '01 New / in-flight onboarding'
    WHEN furthest_stage_asof = 'Bank Linked'   AND days_since_last_stage_event <= 14 THEN '01 New / in-flight onboarding'
    WHEN furthest_stage_asof = 'Funded'        AND days_since_last_stage_event <= 11 THEN '01 New / in-flight onboarding'
    WHEN furthest_stage_asof = 'Registered'    THEN '02 KYC-pending (stalled)'
    WHEN furthest_stage_asof = 'KYC Completed' THEN '03 Bank-link pending (stalled)'
    WHEN furthest_stage_asof = 'Bank Linked'   THEN '04 Deposit-pending (stalled)'
    WHEN furthest_stage_asof = 'Funded'        THEN '05 Deposited, never traded (stalled)'
    WHEN days_since_first_trade <= 30          THEN '06 First-time trader (<=30d since first trade)'
    WHEN dormant_3m_monthly = 1                THEN '09 Inactive trader (no activity Aug-Oct)'
    WHEN trade_months_6m >= 4                  THEN '08 High-engagement trader (>=4 trading months of last 6)'
    WHEN trade_months_6m >= 2                  THEN '07 Repeat trader (2-3 trading months of last 6)'
    ELSE                                            '10 Occasional trader (0-1 trading months of last 6)'
  END AS journey_segment
FROM v_user_journey;
