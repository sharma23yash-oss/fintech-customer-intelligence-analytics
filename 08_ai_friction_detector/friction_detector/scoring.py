"""Transparent, additive PRIORITY score (0-100) for flagged customers.

IMPORTANT: this is a hand-built heuristic for ORDERING operational work. It is NOT a
probability of conversion, churn or any other outcome, it has not been validated against
outcomes, and it must never be presented as a machine-learning prediction.

Six components, each with a documented maximum:

  1. Days since registration ........ 0-10   10 * min(1, tenure/90)
  2. Funnel stage ................... 0-20   Registered 4, KYC 8, Bank 12, Funded 20, Traded 16
  3. Inactivity duration ............ 0-20   20 * min(1, days_inactive/90)
  4. Support ticket history ......... 0-20   escalated-open 12 / open past grace 8;
                                              +5 if >=3 tickets (+2 if 2); +3 if oldest unresolved >90d (cap 20)
  5. Customer activity .............. 0-10   +5 if active in last 30 days, + min(5, active months in last 6)
  6. Previous transaction activity .. 0-20   first deposit >=p75: 8, >=p50: 5, >0: 2;
                                              6-month trading value >=p75: 8, >0: 4; >=2 trading months: 4

Bands (configurable): High >= 55, Medium >= 35, Low otherwise.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config as C

COMPONENTS = ["pts_days_since_registration", "pts_funnel_stage", "pts_inactivity",
              "pts_support", "pts_activity", "pts_prior_transactions"]
STAGE_POINTS = {0: 4, 1: 8, 2: 12, 3: 20, 4: 16}


def score_customers(df: pd.DataFrame, cfg) -> pd.DataFrame:
    d = df.copy()
    d["pts_days_since_registration"] = 10 * np.minimum(1.0, d["tenure_days"].clip(lower=0) / 90.0)
    d["pts_funnel_stage"] = d["stage_idx"].map(STAGE_POINTS).astype(float)
    d["pts_inactivity"] = 20 * np.minimum(1.0, d["days_inactive"].clip(lower=0) / 90.0)

    sup = np.where(d["tickets_escalated"] > 0, 12, np.where(d["flagged_unresolved_n"] > 0, 8, 0)).astype(float)
    sup += np.where(d["tickets_total"] >= 3, 5, np.where(d["tickets_total"] == 2, 2, 0))
    sup += np.where(d["oldest_unresolved_days"] > 90, 3, 0)
    d["pts_support"] = np.minimum(20.0, sup)

    d["pts_activity"] = np.where(d["days_inactive"] <= cfg.inactivity_days, 5, 0) + np.minimum(
        5, d["active_months_6m"].clip(lower=0))
    d["pts_activity"] = d["pts_activity"].astype(float)

    dep = d["first_deposit_amount_asof_inr"].where(d["stage_idx"] >= 3).fillna(0)
    dep_pts = np.where(dep >= (cfg.deposit_p75 or np.inf), 8,
                       np.where(dep >= (cfg.deposit_p50 or np.inf), 5, np.where(dep > 0, 2, 0)))
    tv = d["trading_value_6m_inr"].fillna(0)
    tv_pts = np.where(tv >= (cfg.trading6m_p75 or np.inf), 8, np.where(tv > 0, 4, 0))
    tm_pts = np.where(d["trade_months_6m"] >= 2, 4, 0)
    d["pts_prior_transactions"] = (dep_pts + tv_pts + tm_pts).astype(float)

    raw = d[COMPONENTS].sum(axis=1)
    flagged = d["is_flagged"] == 1
    d["priority_score"] = np.where(flagged, raw, 0.0).round(1)
    d["priority_band"] = np.select(
        [~flagged, d["priority_score"] >= cfg.band_high_min, d["priority_score"] >= cfg.band_medium_min],
        ["NOT_FLAGGED", "High", "Medium"], default="Low")
    d["score_type"] = C.SCORE_TYPE
    return d
