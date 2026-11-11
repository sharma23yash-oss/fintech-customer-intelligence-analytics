"""Central, transparent configuration for the rule engine and the priority score.

Every threshold lives here so that the rules can be audited and changed in one place.
Stage windows are DERIVED from the data (95th percentile of observed completion lags
among customers who did complete the step) unless overridden, and the derived values
are stored in the database `config` table for transparency.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_DIR / "data" / "synthetic"
DB_PATH = PROJECT_DIR / "db" / "friction.db"
OUTPUT_DIR = PROJECT_DIR / "outputs" / "daily_reports"
SCHEMA_SQL = PROJECT_DIR / "sql" / "schema.sql"

SNAPSHOT_DATE = "2026-10-31"          # last day covered by the synthetic dataset

# Funnel stages in order. Index = number of consecutive completed steps.
STAGES = ["Registered", "KYC Completed", "Bank Linked", "Funded", "Traded"]

# Friction categories ---------------------------------------------------------
KYC_PENDING = "KYC_PENDING"
BANK_LINK_PENDING = "BANK_LINK_PENDING"
FIRST_DEPOSIT_PENDING = "FIRST_DEPOSIT_PENDING"
FIRST_TRADE_PENDING = "FIRST_TRADE_PENDING"
INACTIVITY_RISK = "INACTIVITY_RISK"
REPEATED_SUPPORT_ISSUES = "REPEATED_SUPPORT_ISSUES"
SUPPORT_UNRESOLVED = "SUPPORT_UNRESOLVED"
WITHIN_WINDOW = "WITHIN_WINDOW"        # pending step, but still inside the normal window: NOT flagged
NO_FRICTION = "NO_FRICTION"

JOURNEY_CATEGORY_BY_STAGE = {
    0: KYC_PENDING,
    1: BANK_LINK_PENDING,
    2: FIRST_DEPOSIT_PENDING,
    3: FIRST_TRADE_PENDING,
}
FLAGGED_CATEGORIES = [
    KYC_PENDING, BANK_LINK_PENDING, FIRST_DEPOSIT_PENDING, FIRST_TRADE_PENDING,
    INACTIVITY_RISK, SUPPORT_UNRESOLVED, REPEATED_SUPPORT_ISSUES,
]
# When several categories apply, the primary one is the first in this order:
# the journey blocker first, then inactivity, then support issues.
PRIMARY_PRECEDENCE = [
    KYC_PENDING, BANK_LINK_PENDING, FIRST_DEPOSIT_PENDING, FIRST_TRADE_PENDING,
    INACTIVITY_RISK, SUPPORT_UNRESOLVED, REPEATED_SUPPORT_ISSUES,
]

OWNER_TEAM = {
    KYC_PENDING: "Onboarding / KYC Operations",
    BANK_LINK_PENDING: "Onboarding Ops / Payments Support",
    FIRST_DEPOSIT_PENDING: "CRM / Onboarding",
    FIRST_TRADE_PENDING: "CRM / Product Education",
    INACTIVITY_RISK: "CRM / Retention",
    SUPPORT_UNRESOLVED: "Customer Support (ticket owner)",
    REPEATED_SUPPORT_ISSUES: "Customer Support (team lead review)",
}

SCORE_TYPE = "heuristic_priority_score_NOT_a_probability"


@dataclass
class EngineConfig:
    # Observation windows (days a customer may sit at a step before being flagged).
    # None -> derived from data (see rules.derive_windows).
    window_kyc_days: int | None = None
    window_bank_days: int | None = None
    window_deposit_days: int | None = None
    window_trade_days: int | None = None
    window_percentile: float = 0.95
    window_floor_days: int = 3
    watch_percentile: float = 0.75          # between this and the window = WATCH (not flagged)

    inactivity_days: int = 30               # same proxy definition as Phases 2-6
    min_tenure_for_inactivity_days: int = 31

    repeated_ticket_min: int = 3            # same as Phase 4 'needs support' rule
    open_ticket_grace_days: int = 2         # ~ceil(p95 resolution 24.8h) + 1 day
    # Escalated tickets are flagged at any age.

    # Priority bands (sum of six components, 0-100). See scoring.py.
    band_high_min: float = 55.0
    band_medium_min: float = 35.0

    # Value tiers for 'previous transaction activity' (derived from data if None)
    deposit_p50: float | None = None
    deposit_p75: float | None = None
    trading6m_p75: float | None = None

    def windows(self) -> dict[int, int]:
        return {0: self.window_kyc_days, 1: self.window_bank_days,
                2: self.window_deposit_days, 3: self.window_trade_days}

    def to_dict(self) -> dict:
        return asdict(self)
