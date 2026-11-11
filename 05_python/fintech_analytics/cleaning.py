"""Cleaning & validation. The raw -> cleaned transformation is Phase 2 (02_data_cleaning/01_phase2_clean_validate_transform.py).
This module (a) re-validates the CLEANED tables on every run and (b) provides light, idempotent type/derivation helpers.
It never overwrites the original raw file (data/raw) or the cleaned CSVs."""
import pandas as pd
from . import config as C


def standardise_types(users):
    """Idempotent dtype normalisation and derived columns used downstream (returns a copy)."""
    u = users.copy()
    for c in C.DATE_COLS_USERS:
        if c in u:
            u[c] = pd.to_datetime(u[c])
    u["registration_month"] = u["registration_month"].astype(str).str[:7]
    return u


def validate_cleaned(d):
    """Run integrity checks on the four cleaned tables. Returns a DataFrame(check, passed, detail)."""
    u, a, t, c = d["users"], d["activity"], d["tickets"], d["campaigns"]
    rows = []
    def chk(name, ok, detail=""):
        rows.append(dict(check=name, passed=bool(ok), detail=str(detail)))
    chk("users.user_id unique", u.user_id.is_unique, f"{len(u)} rows")
    chk("users row count = 10,000", len(u) == 10000, len(u))
    chk("campaign ids in users exist in campaigns", set(u.acquisition_campaign_id) <= set(c.campaign_id))
    chk("activity (user_id, month) unique", not a.duplicated(["user_id", "activity_month"]).any(), f"{len(a)} rows")
    chk("activity users exist in users", set(a.user_id) <= set(u.user_id))
    chk("tickets.ticket_id unique", t.ticket_id.is_unique, f"{len(t)} rows")
    chk("ticket users exist in users", set(t.user_id) <= set(u.user_id))
    chk("no registration after snapshot", (u.registration_date <= C.SNAPSHOT).all())
    for col in ["kyc_date_asof", "bank_date_asof", "deposit_date_asof", "trade_date_asof"]:
        chk(f"{col} not after snapshot", (u[col].dropna() <= C.SNAPSHOT).all())
    chk("funnel is nested (trade>=deposit>=bank>=kyc as flags)",
        ((u.trade_asof <= u.deposit_asof) & (u.deposit_asof <= u.bank_asof) & (u.bank_asof <= u.kyc_asof)).all())
    chk("mature + immature = all users", u.funnel_mature.sum() + (u.funnel_mature == 0).sum() == len(u), f"mature={int(u.funnel_mature.sum())}")
    chk("organic campaigns have no spend", (c.loc[c.is_paid == 0, "campaign_spend_inr"] == 0).all())
    chk("resolved tickets carry resolution time", t.loc[t.is_resolved == 1, "resolution_time_hours"].notna().all())
    chk("CSAT within 1-5", t.csat_score.dropna().between(1, 5).all())
    chk("no negative money values", (a[["trading_value_inr", "deposit_value_inr", "withdrawal_value_inr"]] >= 0).all().all())
    return pd.DataFrame(rows)


def source_conflict_summary(users, activity):
    """Quantify disagreement between the Users table and Monthly_Activity on 'ever traded' (known Phase 2 property)."""
    m = activity.groupby("user_id").traded_in_month.max().rename("traded_monthly")
    x = users[["user_id", "trade_asof"]].merge(m, on="user_id")
    return pd.crosstab(x.trade_asof, x.traded_monthly).rename(index={0: "users: not traded", 1: "users: traded"},
                                                              columns={0: "monthly: not traded", 1: "monthly: traded"})
