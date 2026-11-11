"""Rule-based friction detection engine.

Design principles
-----------------
* Deterministic, transparent rules. Every threshold is in config.EngineConfig.
* Observation windows: a customer is flagged for a stalled journey step only AFTER the
  longest normal completion lag seen for customers who did complete that step
  (95th percentile, derived from the data). Inside the window the customer is
  IN_WINDOW / WATCH and is NOT flagged, so new registrants are never flagged prematurely.
* The engine works for any as-of date <= the dataset snapshot by rebuilding the state of each
  customer from event dates (replay mode). Replay is an approximation for inactivity because
  only the last-active date, not the full activity history by day, is available.
* The engine never contacts anyone. It only returns a table.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config as C
from .config import EngineConfig
from .scoring import score_customers

DATE_COLS = ["registration_date", "kyc_date_asof", "bank_date_asof", "deposit_date_asof",
             "trade_date_asof", "last_active_date_adj"]
TEXT_COLS = ["city", "acquisition_channel", "registration_month", "device_type"]
NUM_COLS = ["total_trades", "total_trading_value_inr", "total_deposit_value_inr", "trading_value_6m_inr",
            "trade_months_6m", "active_months_6m", "activity_ratio", "flag_trade_conflict",
            "flag_deposit_conflict", "flag_last_active_conflict", "flag_activity_conflict"]


# --------------------------------------------------------------------------- cleaning
def clean_users(users: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Defensive cleaning. Never raises on bad input; counts what it fixed or dropped."""
    issues: dict[str, int] = {}
    u = users.copy()
    n0 = len(u)
    u = u[u["user_id"].notna()]
    issues["rows_missing_user_id_dropped"] = n0 - len(u)
    dup = u.duplicated("user_id", keep="first")
    issues["duplicate_user_rows_dropped"] = int(dup.sum())
    u = u[~dup].copy()
    for c in DATE_COLS:
        if c not in u:
            u[c] = pd.NaT
        raw = u[c]
        u[c] = pd.to_datetime(raw, errors="coerce")
        issues[f"unparseable_{c}"] = int((raw.notna() & u[c].isna()).sum())
    bad_reg = u["registration_date"].isna()
    issues["rows_missing_registration_date_dropped"] = int(bad_reg.sum())
    u = u[~bad_reg].copy()
    for c in TEXT_COLS:
        if c not in u:
            u[c] = "Unknown"
        issues[f"missing_{c}_filled_Unknown"] = int(u[c].isna().sum())
        u[c] = u[c].fillna("Unknown").astype(str)
    for c in NUM_COLS:
        if c not in u:
            u[c] = 0
        u[c] = pd.to_numeric(u[c], errors="coerce").fillna(0)
    if "first_deposit_amount_asof_inr" not in u:
        u["first_deposit_amount_asof_inr"] = np.nan
    u["first_deposit_amount_asof_inr"] = pd.to_numeric(u["first_deposit_amount_asof_inr"], errors="coerce")
    return u.reset_index(drop=True), issues


def clean_tickets(tickets: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    issues: dict[str, int] = {}
    if tickets is None or len(tickets) == 0:
        return pd.DataFrame(columns=["ticket_id", "user_id", "created_date", "category", "priority",
                                     "status", "resolution_time_hours"]), {"tickets_empty": 1}
    t = tickets.copy()
    dup = t.duplicated("ticket_id", keep="first")
    issues["duplicate_ticket_rows_dropped"] = int(dup.sum())
    t = t[~dup].copy()
    raw = t["created_date"]
    t["created_date"] = pd.to_datetime(raw, errors="coerce")
    issues["tickets_unparseable_created_date_dropped"] = int(t["created_date"].isna().sum())
    t = t[t["created_date"].notna()].copy()
    t["status"] = t["status"].fillna("Open").astype(str).str.strip().str.title()
    t["resolution_time_hours"] = pd.to_numeric(t["resolution_time_hours"], errors="coerce")
    return t.reset_index(drop=True), issues


# --------------------------------------------------------------------------- derived parameters
def derive_config(users: pd.DataFrame, tickets: pd.DataFrame | None = None,
                  cfg: EngineConfig | None = None) -> EngineConfig:
    """Fill windows and value tiers from the data when not set explicitly."""
    cfg = cfg or EngineConfig()
    u, _ = clean_users(users)
    pairs = [("window_kyc_days", "registration_date", "kyc_date_asof"),
             ("window_bank_days", "kyc_date_asof", "bank_date_asof"),
             ("window_deposit_days", "bank_date_asof", "deposit_date_asof"),
             ("window_trade_days", "deposit_date_asof", "trade_date_asof")]
    for attr, a, b in pairs:
        if getattr(cfg, attr) is None:
            lag = (u[b] - u[a]).dt.days.dropna()
            lag = lag[lag >= 0]
            val = int(np.ceil(lag.quantile(cfg.window_percentile))) if len(lag) else 14
            setattr(cfg, attr, max(val, cfg.window_floor_days))
    dep = u["first_deposit_amount_asof_inr"].dropna()
    dep = dep[dep > 0]
    if cfg.deposit_p50 is None:
        cfg.deposit_p50 = float(dep.quantile(0.5)) if len(dep) else 0.0
    if cfg.deposit_p75 is None:
        cfg.deposit_p75 = float(dep.quantile(0.75)) if len(dep) else 0.0
    if cfg.trading6m_p75 is None:
        tv = u.loc[u["total_trades"] > 0, "trading_value_6m_inr"]
        cfg.trading6m_p75 = float(tv.quantile(0.75)) if len(tv) else 0.0
    return cfg


def watch_windows(users: pd.DataFrame, cfg: EngineConfig) -> dict[int, int]:
    """Lower bound of the 'WATCH' band (75th percentile lag). Customers here are NOT flagged."""
    u, _ = clean_users(users)
    pairs = {0: ("registration_date", "kyc_date_asof"), 1: ("kyc_date_asof", "bank_date_asof"),
             2: ("bank_date_asof", "deposit_date_asof"), 3: ("deposit_date_asof", "trade_date_asof")}
    out = {}
    for s, (a, b) in pairs.items():
        lag = (u[b] - u[a]).dt.days.dropna()
        lag = lag[lag >= 0]
        w = int(np.ceil(lag.quantile(cfg.watch_percentile))) if len(lag) else cfg.windows()[s]
        out[s] = min(w, cfg.windows()[s])
    return out


# --------------------------------------------------------------------------- main engine
def run_engine(users: pd.DataFrame, tickets: pd.DataFrame, as_of: str | pd.Timestamp,
               cfg: EngineConfig | None = None, monthly: pd.DataFrame | None = None,
               watch: dict[int, int] | None = None) -> pd.DataFrame:
    """Return one row per customer registered on/before `as_of` with friction category and score."""
    as_of = pd.Timestamp(as_of).normalize()
    cfg = derive_config(users, tickets, cfg)
    watch = watch or watch_windows(users, cfg)
    u, u_issues = clean_users(users)
    t, t_issues = clean_tickets(tickets)

    u = u[u["registration_date"] <= as_of].copy()          # not yet registered -> not analysed
    if u.empty:
        out = pd.DataFrame()
        out.attrs["data_quality"] = {**u_issues, **t_issues}
        return out

    # ---- journey state at as_of (rebuilt from event dates)
    k = (u["kyc_date_asof"] <= as_of)
    b = (u["bank_date_asof"] <= as_of)
    d = (u["deposit_date_asof"] <= as_of)
    tr = (u["trade_date_asof"] <= as_of)
    s1, s2 = k, k & b
    s3 = s2 & d
    s4 = s3 & tr
    stage = s1.astype(int) + s2.astype(int) + s3.astype(int) + s4.astype(int)
    u["stage_idx"] = stage.values
    u["sequence_anomaly"] = ((b & ~k) | (d & ~b) | (tr & ~d)).astype(int).values
    # events out of chronological order (e.g. bank date before KYC date)
    prev = [u["registration_date"], u["kyc_date_asof"], u["bank_date_asof"], u["deposit_date_asof"]]
    cur = [u["kyc_date_asof"], u["bank_date_asof"], u["deposit_date_asof"], u["trade_date_asof"]]
    order_bad = np.zeros(len(u), dtype=bool)
    for p, c in zip(prev, cur):
        order_bad |= (c.notna() & p.notna() & (c < p)).values
    u["sequence_anomaly"] = (u["sequence_anomaly"].astype(bool) | order_bad).astype(int)

    anchors = np.select(
        [stage == 0, stage == 1, stage == 2, stage == 3, stage == 4],
        [u["registration_date"], u["kyc_date_asof"], u["bank_date_asof"],
         u["deposit_date_asof"], u["trade_date_asof"]],
        default=pd.NaT)
    u["anchor_date"] = pd.to_datetime(anchors)
    anchor_names = np.array(["registration", "KYC completion", "bank link", "first deposit", "first trade"])
    u["anchor_event"] = anchor_names[stage.values]
    u["stage_name"] = np.array(C.STAGES)[stage.values]
    u["tenure_days"] = (as_of - u["registration_date"]).dt.days
    u["dwell_days"] = (as_of - u["anchor_date"]).dt.days

    win = cfg.windows()
    u["window_days"] = u["stage_idx"].map(win)
    u["watch_days"] = u["stage_idx"].map(watch)
    pending = u["stage_idx"] < 4
    stalled = pending & (u["dwell_days"] > u["window_days"])
    watching = pending & ~stalled & (u["dwell_days"] > u["watch_days"])
    u["days_overdue"] = np.where(stalled, u["dwell_days"] - u["window_days"], 0).astype(int)
    u["journey_status"] = np.select([stalled, watching, pending], ["STALLED", "WATCH", "IN_WINDOW"],
                                    default="FIRST_TRADE_DONE")

    # ---- inactivity (traded customers only)
    last_active = u["last_active_date_adj"].fillna(u["anchor_date"])
    last_active = pd.concat([last_active, u["anchor_date"]], axis=1).max(axis=1)
    inactive_days = (as_of - last_active).dt.days
    inactive_days = inactive_days.where(last_active <= as_of, 0).clip(lower=0)   # unknown future activity -> 0
    u["days_inactive"] = inactive_days.fillna(0).astype(int)
    traded = u["stage_idx"] == 4
    inactivity_assessable = traded & (u["tenure_days"] >= cfg.min_tenure_for_inactivity_days)
    inactivity_flag = inactivity_assessable & (u["days_inactive"] > cfg.inactivity_days)

    # ---- optional activity-log evidence (months <= as_of month)
    if monthly is not None and len(monthly):
        m = monthly.copy()
        m["activity_month"] = m["activity_month"].astype(str)
        m = m[m["activity_month"] <= as_of.strftime("%Y-%m")]
        g = m.groupby("user_id").agg(
            log_trades=("trade_count", "sum"),
            log_deposit_value=("deposit_value_inr", "sum"),
        )
        act = m[m["active_in_month"] == 1].groupby("user_id")["activity_month"].max().rename("log_last_active_month")
        u = u.merge(g, on="user_id", how="left").merge(act, on="user_id", how="left")
        u["log_trades"] = u["log_trades"].fillna(0)
        u["log_deposit_value"] = u["log_deposit_value"].fillna(0)
    else:
        u["log_trades"] = u["total_trades"]
        u["log_deposit_value"] = u["total_deposit_value_inr"]
        u["log_last_active_month"] = np.nan
    u = u.reset_index(drop=True)

    # ---- tickets at as_of
    u = _attach_ticket_features(u, t, as_of, cfg)
    support_unres = u["flagged_unresolved_n"] > 0
    support_repeat = u["tickets_total"] >= cfg.repeated_ticket_min

    # ---- categories
    cats = []
    stage_arr = u["stage_idx"].values
    stalled_arr = stalled.values
    inact_arr = inactivity_flag.values
    unres_arr = support_unres.values
    rep_arr = support_repeat.values
    for i in range(len(u)):
        c = []
        if stalled_arr[i]:
            c.append(C.JOURNEY_CATEGORY_BY_STAGE[stage_arr[i]])
        if inact_arr[i]:
            c.append(C.INACTIVITY_RISK)
        if unres_arr[i]:
            c.append(C.SUPPORT_UNRESOLVED)
        if rep_arr[i]:
            c.append(C.REPEATED_SUPPORT_ISSUES)
        cats.append(c)
    u["friction_categories"] = ["|".join(c) for c in cats]
    prim = []
    pending_arr = pending.values
    for i, c in enumerate(cats):
        if c:
            prim.append(next(p for p in C.PRIMARY_PRECEDENCE if p in c))
        elif pending_arr[i]:
            prim.append(C.WITHIN_WINDOW)
        else:
            prim.append(C.NO_FRICTION)
    u["primary_category"] = prim
    u["is_flagged"] = u["primary_category"].isin(C.FLAGGED_CATEGORIES).astype(int)
    u["eligibility_status"] = np.select(
        [pending & stalled, pending & ~stalled, traded & inactivity_assessable, traded & ~inactivity_assessable],
        ["ELIGIBLE", "TOO_EARLY_FOR_STAGE_CHECK", "ELIGIBLE", "TOO_NEW_FOR_INACTIVITY_CHECK"],
        default="UNKNOWN")

    # ---- data confidence (source conflict relevant to the PRIMARY category)
    detail = []
    for row in u[["primary_category", "log_trades", "log_deposit_value", "log_last_active_month",
                  "flag_last_active_conflict", "stage_idx"]].itertuples(index=False):
        pc, lt, ld, lm, lac, st = row
        d_ = ""
        if pc in (C.KYC_PENDING, C.BANK_LINK_PENDING, C.FIRST_DEPOSIT_PENDING, C.FIRST_TRADE_PENDING):
            parts = []
            if lt > 0:
                parts.append("activity log shows trades although first trade is not recorded")
            if st < 3 and ld > 0:
                parts.append("activity log shows deposits although first deposit is not recorded")
            d_ = "; ".join(parts)
        elif pc == C.INACTIVITY_RISK:
            cutoff = (as_of - pd.Timedelta(days=cfg.inactivity_days)).strftime("%Y-%m")
            if isinstance(lm, str) and lm >= cutoff:
                d_ = "activity log shows activity in the last 30 days (month-level)"
        detail.append(d_)
    u["conflict_detail"] = detail
    u["source_conflict_relevant"] = (u["conflict_detail"] != "").astype(int)
    u["data_confidence"] = np.where(u["is_flagged"] == 0, "",
                                    np.where(u["source_conflict_relevant"] == 1, "LOW", "HIGH"))

    u["as_of_date"] = as_of.strftime("%Y-%m-%d")
    out = score_customers(u, cfg)
    out["data_label"] = C_LABEL
    out.attrs["data_quality"] = {**u_issues, **t_issues}
    out.attrs["config"] = cfg.to_dict()
    return out


C_LABEL = "SYNTHETIC"


def _attach_ticket_features(u: pd.DataFrame, t: pd.DataFrame, as_of: pd.Timestamp, cfg: EngineConfig) -> pd.DataFrame:
    cols = ["tickets_total", "tickets_unresolved", "tickets_escalated", "oldest_unresolved_days",
            "flagged_unresolved_n", "last_ticket_category"]
    if t is None or len(t) == 0:
        for c in cols:
            u[c] = 0 if c != "last_ticket_category" else ""
        return u
    t = t[(t["created_date"] <= as_of) & t["user_id"].isin(u["user_id"])].copy()
    hrs = t["resolution_time_hours"].fillna(0)
    resolved_at = t["created_date"] + pd.to_timedelta(hrs, unit="h")
    is_res_status = t["status"].eq("Resolved")
    t["unresolved"] = (~is_res_status) | (is_res_status & (resolved_at > as_of))
    t["escalated"] = t["status"].eq("Escalated") & t["unresolved"]
    t["age"] = (as_of - t["created_date"]).dt.days
    t["flagged_unres"] = t["unresolved"] & (t["escalated"] | (t["age"] > cfg.open_ticket_grace_days))
    t = t.sort_values("created_date")
    g = t.groupby("user_id").agg(
        tickets_total=("ticket_id", "size"),
        tickets_unresolved=("unresolved", "sum"),
        tickets_escalated=("escalated", "sum"),
        flagged_unresolved_n=("flagged_unres", "sum"),
        last_ticket_category=("category", "last"),
    )
    old = t[t["unresolved"]].groupby("user_id")["age"].max().rename("oldest_unresolved_days")
    u = u.merge(g, on="user_id", how="left").merge(old, on="user_id", how="left")
    for c in ["tickets_total", "tickets_unresolved", "tickets_escalated", "flagged_unresolved_n",
              "oldest_unresolved_days"]:
        u[c] = u[c].fillna(0).astype(int)
    u["last_ticket_category"] = u["last_ticket_category"].fillna("")
    return u
