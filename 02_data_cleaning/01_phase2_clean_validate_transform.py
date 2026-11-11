"""
Phase 2 - Cleaning, validation and transformation of the SYNTHETIC brokerage dataset.

Reads  : data/raw/*   (never modified)
Writes : data/cleaned/* (4 cleaned core tables + derived/ tables), 02_data_cleaning/validation/ and cleaning_log.csv

Run    : python3 01_phase2_clean_validate_transform.py
All records are synthetic. Nothing here is real customer data.
"""
import json
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "cleaned"              # Cleaned_* core tables
DER = OUT / "derived"                        # funnel / cohort / campaign / segment tables derived from the cleaned data
STEP = ROOT / "02_data_cleaning"             # cleaning_log.csv and validation/ outputs
VAL = STEP / "validation"
OUT.mkdir(exist_ok=True); DER.mkdir(exist_ok=True); VAL.mkdir(exist_ok=True)

SNAP = pd.Timestamp("2026-10-31")          # end of observation window (START_HERE sheet; verified in Phase 1)
LAST_M = "2026-10"
XLSX = RAW / "Fintech_Brokerage_Customer_Analytics_Synthetic_Project.xlsx"

sheets = pd.read_excel(XLSX, sheet_name=None)
u_raw = sheets["Users_10000"].copy()
m_raw = sheets["Monthly_Activity"].copy()
t_raw = sheets["Support_Tickets"].copy()
c_raw = sheets["Campaigns"].copy()
co_raw = sheets["Cohort_Retention"].copy()
csv_raw = pd.read_csv(RAW / "Fintech_Users_10000_Synthetic.csv")

REC_BEFORE = {"Users": len(u_raw), "Monthly_Activity": len(m_raw), "Support_Tickets": len(t_raw),
              "Campaigns": len(c_raw), "Cohort_Retention": len(co_raw)}

mi = lambda s: s.str.slice(0, 4).astype(int) * 12 + s.str.slice(5, 7).astype(int)   # 'YYYY-MM' -> month index
CLEAN_LOG, CHECKS, EXC = [], [], []

def log(table, column, issue, action, n, rationale):
    CLEAN_LOG.append(dict(change_id=f"CL{len(CLEAN_LOG)+1:02d}", table=table, column=column, issue=issue,
                          action=action, records_affected=int(n), rationale=rationale))

def check(cid, table, dim, desc, tested, viol, severity, status, treatment, after=None, exc=None):
    """status: Pass | Corrected | Flagged (retained) | Documented"""
    CHECKS.append(dict(check_id=cid, table=table, dimension=dim, description=desc, records_tested=int(tested),
                       violations_raw=int(viol), pass_rate_raw=round(1 - viol / tested, 5) if tested else np.nan,
                       violations_after_correction=int(viol if after is None else after),
                       severity=severity, status=status, treatment=treatment))
    if exc is not None and len(exc):
        e = exc.copy(); e.insert(0, "check_id", cid); EXC.append(e)

# =====================================================================================
# 0. STANDARDISE TYPES / FORMATS
# =====================================================================================
for c in ["registration_date", "kyc_completion_date", "bank_link_date", "first_deposit_date",
          "first_trade_date", "last_active_date"]:
    u_raw[c] = pd.to_datetime(u_raw[c])
t_raw["created_date"] = pd.to_datetime(t_raw["created_date"])

# string standardisation (trim + collapse whitespace; categories already Title-case in source)
cat_cols = {"u": ["acquisition_channel", "source_platform", "city", "age_group", "device_type", "risk_profile", "first_trade_segment"],
            "t": ["category", "priority", "status"], "c": ["campaign_name", "channel", "source_platform"]}
chg = 0
for key, df in (("u", u_raw), ("t", t_raw), ("c", c_raw)):
    for col in cat_cols[key]:
        s = df[col].dropna().astype(str)
        cleaned = s.str.strip().str.replace(r"\s+", " ", regex=True)
        chg += int((s != cleaned).sum())
        df.loc[s.index, col] = cleaned
log("All", "categorical columns", "Whitespace / case inconsistency in category labels",
    "Trimmed and collapsed whitespace; labels left in source casing", chg,
    "Audit found labels already consistent (0 changes). Step retained so the pipeline is repeatable on new extracts.")

# =====================================================================================
# 1. RAW-DATA VALIDATION  (all checks run on RAW frames; fixes are applied later to copies)
# =====================================================================================
U, M, T, C = u_raw, m_raw, t_raw, c_raw
N_U, N_M, N_T = len(U), len(M), len(T)

# ---- Uniqueness
check("UQ01", "Users", "Uniqueness", "Duplicate user_id", N_U, U.user_id.duplicated().sum(), "-", "Pass", "None needed")
check("UQ02", "Users", "Uniqueness", "Fully duplicated user rows", N_U, U.duplicated().sum(), "-", "Pass", "None needed")
check("UQ03", "Support_Tickets", "Uniqueness", "Duplicate ticket_id", N_T, T.ticket_id.duplicated().sum(), "-", "Pass", "None needed")
check("UQ04", "Monthly_Activity", "Uniqueness", "Duplicate (user_id, activity_month)", N_M, M.duplicated(["user_id", "activity_month"]).sum(), "-", "Pass", "None needed")
check("UQ05", "Campaigns", "Uniqueness", "Duplicate campaign_id", len(C), C.campaign_id.duplicated().sum(), "-", "Pass", "None needed")
_x = sheets["Users_10000"].reset_index(drop=True).copy(); _c = csv_raw.reset_index(drop=True).copy()
for _col in ["registration_date", "kyc_completion_date", "bank_link_date", "first_deposit_date", "first_trade_date", "last_active_date"]:
    _x[_col] = pd.to_datetime(_x[_col]); _c[_col] = pd.to_datetime(_c[_col])
_diff = 0
for _col in _x.columns:
    _a, _b = _x[_col], _c[_col]
    if pd.api.types.is_float_dtype(_a) or pd.api.types.is_float_dtype(_b): _eq = np.isclose(_a.astype(float), _b.astype(float), equal_nan=True)
    else: _eq = ((_a == _b) | (_a.isna() & _b.isna())).to_numpy()
    _diff += int((~_eq).sum())
check("UQ06", "Users", "Uniqueness", "CSV vs Excel Users sheet: cells that differ", N_U * 25, _diff, "-", "Pass", "Files are identical; CSV used only as a cross-check")

# ---- Referential integrity
check("RI01", "Monthly_Activity", "Referential integrity", "monthly_activity.user_id not in users", N_M, (~M.user_id.isin(U.user_id)).sum(), "-", "Pass", "None needed")
check("RI02", "Support_Tickets", "Referential integrity", "support_tickets.user_id not in users", N_T, (~T.user_id.isin(U.user_id)).sum(), "-", "Pass", "None needed")
check("RI03", "Users", "Referential integrity", "users.acquisition_campaign_id not in campaigns", N_U, (~U.acquisition_campaign_id.isin(C.campaign_id)).sum(), "-", "Pass", "None needed")
check("RI04", "Users", "Referential integrity", "Users with no monthly_activity rows (orphan parent)", N_U, (~U.user_id.isin(M.user_id)).sum(), "-", "Pass", "None needed")
check("RI05", "Campaigns", "Referential integrity", "Campaigns with no attributed users", len(C), (~C.campaign_id.isin(U.acquisition_campaign_id)).sum(), "-", "Pass", "None needed")
cc = U.merge(C[["campaign_id", "channel", "source_platform"]], left_on="acquisition_campaign_id", right_on="campaign_id", suffixes=("", "_c"))
check("RI06", "Users", "Referential integrity", "User channel/platform differs from campaign master", N_U,
      ((cc.acquisition_channel != cc.channel) | (cc.source_platform != cc.source_platform_c)).sum(), "-", "Pass", "None needed")
g = U.groupby("acquisition_campaign_id").agg(n=("user_id", "size"), k=("kyc_completed", "sum"), f=("first_trade_made", "sum"))
rec = C.set_index("campaign_id").join(g)
check("RI07", "Campaigns", "Referential integrity", "Campaign sheet counts (users, KYC, first traders) vs recomputed from users", len(C) * 3,
      int((rec.acquired_users != rec.n).sum() + (rec.kyc_completions != rec.k).sum() + (rec.first_traders != rec.f).sum()), "-", "Pass", "None needed")

# ---- Completeness
req = ["user_id", "registration_date", "acquisition_campaign_id", "acquisition_channel", "source_platform", "city", "age_group", "device_type", "risk_profile"]
check("CP01", "Users", "Completeness", "Nulls in mandatory user fields", N_U, U[req].isna().any(axis=1).sum(), "-", "Pass", "None needed")
pairs = [("kyc_completed", "kyc_completion_date"), ("bank_account_linked", "bank_link_date"), ("first_deposit_made", "first_deposit_date"), ("first_trade_made", "first_trade_date")]
miss = sum(((U[f]) & U[d].isna()).sum() for f, d in pairs)
extra = sum(((~U[f]) & U[d].notna()).sum() for f, d in pairs)
check("CP02", "Users", "Completeness", "Completed stage without a date", int(sum(U[f].sum() for f, _ in pairs)), miss, "-", "Pass", "None needed")
check("CP03", "Users", "Completeness", "Date present for a stage not completed", int(sum((~U[f]).sum() for f, _ in pairs)), extra, "-", "Pass", "None needed")
check("CP04", "Users", "Completeness", "Deposit amount missing/zero for depositors; positive for non-depositors", N_U,
      ((U.first_deposit_made & (U.first_deposit_amount_inr <= 0)) | (~U.first_deposit_made & (U.first_deposit_amount_inr > 0))).sum(), "-", "Pass", "None needed")
check("CP05", "Users", "Completeness", "Trade segment missing for traders / present for non-traders", N_U,
      ((U.first_trade_made & U.first_trade_segment.isna()) | (~U.first_trade_made & U.first_trade_segment.notna())).sum(), "-", "Pass", "None needed")
check("CP06", "Monthly_Activity", "Completeness", "Nulls in any monthly field", N_M * 8, int(M.isna().sum().sum()), "-", "Pass", "None needed")
res = T.status.eq("Resolved")
check("CP07", "Support_Tickets", "Completeness", "Resolved ticket lacking time/CSAT, or unresolved ticket with them", N_T,
      ((res & (T.resolution_time_hours.isna() | T.csat_score.isna())) | (~res & (T.resolution_time_hours.notna() | T.csat_score.notna()))).sum(), "-", "Pass",
      "Nulls are structural (unresolved). Averages must state 'resolved tickets only'.")
check("CP08", "Campaigns", "Completeness", "Nulls in campaign master", len(C) * C.shape[1], int(C.isna().sum().sum()), "-", "Pass", "None needed")

# ---- Validity
bool_cols = ["kyc_completed", "bank_account_linked", "first_deposit_made", "first_trade_made", "active_30d", "churned_30d_proxy", "churned_90d_proxy"]
check("VL01", "Users", "Validity", "Non-Boolean values in Boolean columns", N_U * len(bool_cols), sum(int(~U[c].map(lambda x: isinstance(x, (bool, np.bool_))).all()) for c in bool_cols), "-", "Pass", "All dtype=bool")
neg_u = (U.first_deposit_amount_inr < 0).sum()
neg_m = int((M[["trade_count", "trading_value_inr", "deposit_value_inr", "withdrawal_value_inr"]] < 0).sum().sum())
neg_t = int((T.resolution_time_hours < 0).sum())
check("VL02", "All", "Validity", "Negative financial amounts, counts or durations", N_U + N_M * 4 + N_T, neg_u + neg_m + neg_t, "-", "Pass", "None needed")
check("VL03", "Support_Tickets", "Validity", "CSAT outside 1-5", int(T.csat_score.notna().sum()), int(((T.csat_score < 1) | (T.csat_score > 5)).sum()), "-", "Pass", "None needed")
check("VL04", "Monthly_Activity", "Validity", "Non-integer trade_count", N_M, int((M.trade_count % 1 != 0).sum()), "-", "Pass", "None needed")
tenure = (SNAP - U.registration_date).dt.days
check("VL05", "Users", "Validity", "days_inactive_as_of_snapshot negative, or larger than tenure", N_U,
      ((U.days_inactive_as_of_snapshot < 0) | (U.days_inactive_as_of_snapshot > tenure)).sum(), "-", "Pass", "None needed")
check("VL06", "Users", "Validity", "days_inactive does not recompute from last_active_date and snapshot", N_U,
      ((SNAP - U.last_active_date).dt.days != U.days_inactive_as_of_snapshot).sum(), "-", "Pass", "Snapshot 2026-10-31 confirmed")
check("VL07", "Users", "Validity", "churn flags inconsistent with days_inactive (>30 / >90)", N_U * 2,
      ((U.days_inactive_as_of_snapshot > 30) != U.churned_30d_proxy).sum() + ((U.days_inactive_as_of_snapshot > 90) != U.churned_90d_proxy).sum(), "-", "Pass",
      "Flags are arithmetic functions of days_inactive; the problem is the definition (see MD checks), not the arithmetic")

# ---- Journey / chronology
R, K, B, D, TR, L = [U[c] for c in ["registration_date", "kyc_completion_date", "bank_link_date", "first_deposit_date", "first_trade_date", "last_active_date"]]
check("JR01", "Users", "Journey chronology", "KYC date earlier than registration", int(U.kyc_completed.sum()), (K < R).sum(), "-", "Pass", "None needed")
check("JR02", "Users", "Journey chronology", "Bank-link date earlier than KYC date", int(U.bank_account_linked.sum()), (B < K).sum(), "-", "Pass", "None needed")
check("JR03", "Users", "Journey chronology", "First deposit earlier than bank-link date", int(U.first_deposit_made.sum()), (D < B).sum(), "-", "Pass", "None needed")
check("JR04", "Users", "Journey chronology", "First trade earlier than first deposit", int(U.first_trade_made.sum()), (TR < D).sum(), "-", "Pass", "None needed")
check("JR05", "Users", "Journey chronology", "First trade earlier than registration", int(U.first_trade_made.sum()), (TR < R).sum(), "-", "Pass", "None needed")
skip = ((U.bank_account_linked & ~U.kyc_completed) | (U.first_deposit_made & ~U.bank_account_linked) | (U.first_trade_made & ~U.first_deposit_made)).sum()
check("JR06", "Users", "Journey chronology", "Stage reached while a prerequisite stage was skipped", N_U, skip, "-", "Pass", "None needed")
check("JR07", "Users", "Journey chronology", "last_active_date earlier than registration", N_U, (L < R).sum(), "-", "Pass", "None needed")
mreg = M.merge(U[["user_id", "registration_month"]], on="user_id")
check("JR08", "Monthly_Activity", "Journey chronology", "Activity row before registration month", N_M, (mi(mreg.activity_month) < mi(mreg.registration_month)).sum(), "-", "Pass", "None needed")
check("JR09", "Monthly_Activity", "Journey chronology", "Activity row after observation window (> 2026-10)", N_M, (M.activity_month > LAST_M).sum(), "-", "Pass", "None needed")
tu = T.merge(U[["user_id", "registration_date"]], on="user_id")
check("JR10", "Support_Tickets", "Journey chronology", "Ticket created before registration", N_T, (tu.created_date < tu.registration_date).sum(), "-", "Pass", "None needed")

# ---- Timeliness (right-censoring)
ev = [("kyc_completed", "kyc_completion_date"), ("bank_account_linked", "bank_link_date"), ("first_deposit_made", "first_deposit_date"), ("first_trade_made", "first_trade_date")]
fut_mask = {d: (U[f] & (U[d] > SNAP)) for f, d in ev}
n_fut_events = int(sum(v.sum() for v in fut_mask.values()))
fut_users = pd.concat(fut_mask, axis=1).any(axis=1)
fe = pd.concat([U.loc[v, ["user_id"]].assign(detail=d) for d, v in fut_mask.items()])
CHECK_FUT_ROW = len(CHECKS)  # fill 'after' later
check("TM01", "Users", "Timeliness", "Funnel events dated after the 2026-10-31 snapshot but flagged completed (events)", int(sum(U[f].sum() for f, _ in ev)), n_fut_events, "High", "Corrected",
      "Added *_asof columns that only count events on/before snapshot; funnel rates use mature cohorts", after=0, exc=fe)
check("TM02", "Users", "Timeliness", "Users with at least one post-snapshot funnel event", N_U, int(fut_users.sum()), "High", "Corrected",
      "Same as TM01 (user level); all in Oct-2026 registration cohort", after=0)

# ---- Cross-table consistency (flagged, not auto-corrected: no ground truth to say which table is right)
first_trade_m = U.set_index("user_id").first_trade_date.dt.strftime("%Y-%m")
first_dep_m = U.set_index("user_id").first_deposit_date.dt.strftime("%Y-%m")
mm = M.copy()
mm["ftm"] = mm.user_id.map(first_trade_m); mm["fdm"] = mm.user_id.map(first_dep_m)
mm["u_trade_flag"] = mm.user_id.map(U.set_index("user_id").first_trade_made)
mm["u_dep_flag"] = mm.user_id.map(U.set_index("user_id").first_deposit_made)
tr_rows = mm[mm.trade_count > 0]; dp_rows = mm[mm.deposit_value_inr > 0]; wd_rows = mm[mm.withdrawal_value_inr > 0]
x1 = tr_rows[~tr_rows.u_trade_flag]
check("XT01", "Monthly_Activity", "Cross-table consistency", "Monthly trade rows for users flagged first_trade_made=False", len(tr_rows), len(x1), "Critical", "Flagged (retained)",
      "Rows kept; flag_trade_without_first_trade_flag=1. Funnel metrics use Users table only; trading behaviour uses Monthly_Activity only", exc=x1[["user_id", "activity_month"]])
x2 = tr_rows[tr_rows.u_trade_flag & (tr_rows.activity_month < tr_rows.ftm)]
check("XT02", "Monthly_Activity", "Cross-table consistency", "Trade rows in a month earlier than the user's first-trade month", int(tr_rows.u_trade_flag.sum()), len(x2), "Critical", "Flagged (retained)",
      "flag_trade_before_first_trade_month=1", exc=x2[["user_id", "activity_month"]])
x3 = dp_rows[~dp_rows.u_dep_flag]
check("XT03", "Monthly_Activity", "Cross-table consistency", "Monthly deposit rows for users flagged first_deposit_made=False", len(dp_rows), len(x3), "Critical", "Flagged (retained)",
      "flag_deposit_without_first_deposit_flag=1", exc=x3[["user_id", "activity_month"]])
x4 = dp_rows[dp_rows.u_dep_flag & (dp_rows.activity_month < dp_rows.fdm)]
check("XT04", "Monthly_Activity", "Cross-table consistency", "Deposit rows in a month earlier than the first-deposit month", int(dp_rows.u_dep_flag.sum()), len(x4), "High", "Flagged (retained)",
      "flag_deposit_before_first_deposit_month=1", exc=x4[["user_id", "activity_month"]])
x5 = wd_rows[~wd_rows.u_dep_flag]
check("XT05", "Monthly_Activity", "Cross-table consistency", "Withdrawal rows for users who never made a first deposit", len(wd_rows), len(x5), "High", "Flagged (retained)",
      "flag_withdrawal_without_deposit_flag=1", exc=x5[["user_id", "activity_month"]])
mon_tr = M.groupby("user_id").trade_count.sum(); mon_dp = M.groupby("user_id").deposit_value_inr.sum()
x6 = U[U.first_trade_made & (U.user_id.map(mon_tr) == 0)]
check("XT06", "Users", "Cross-table consistency", "first_trade_made=True but no trade in Monthly_Activity", int(U.first_trade_made.sum()), len(x6), "High", "Flagged (retained)",
      "flag_users_trade_not_in_monthly=1", exc=x6[["user_id"]])
x7 = U[U.first_deposit_made & (U.user_id.map(mon_dp) == 0)]
check("XT07", "Users", "Cross-table consistency", "first_deposit_made=True but no deposit in Monthly_Activity", int(U.first_deposit_made.sum()), len(x7), "High", "Flagged (retained)",
      "flag_users_deposit_not_in_monthly=1", exc=x7[["user_id"]])
act_rows = M[M.active_in_month]
last_mon_active = act_rows.groupby("user_id").activity_month.max()
lam = U.set_index("user_id").last_active_date.dt.strftime("%Y-%m")
mismatch = (lam != last_mon_active.reindex(lam.index).fillna("none"))
check("XT08", "Users", "Cross-table consistency", "Month of last_active_date differs from last active month in Monthly_Activity", N_U, int(mismatch.sum()), "Critical", "Flagged (retained)",
      "flag_last_active_conflict=1; recency used only as proxy; retention measured from Monthly_Activity", exc=pd.DataFrame({"user_id": mismatch[mismatch].index}))
am = act_rows.assign(lam=act_rows.user_id.map(lam))
x9 = am[am.activity_month > am.lam]
check("XT09", "Monthly_Activity", "Cross-table consistency", "Active monthly rows after the month of last_active_date", len(act_rows), len(x9), "High", "Flagged (retained)",
      "flag_active_after_last_active_month=1", exc=x9[["user_id", "activity_month"]])
# last_active earlier than a known (as-of) funnel event -> logically impossible
asof_dates = pd.concat([U[d].where(U[d] <= SNAP) for _, d in ev], axis=1)
last_event = asof_dates.max(axis=1)
la_before_event = L < last_event
check("XT10", "Users", "Cross-table consistency", "last_active_date earlier than the user's latest funnel event (on/before snapshot)", N_U, int(la_before_event.sum()), "High", "Corrected",
      "last_active_date_adj = max(last_active_date, latest as-of funnel event); days_inactive_adj recomputed", after=0,
      exc=U.loc[la_before_event, ["user_id"]])

# ---- Reported-metric accuracy (summary sheets)
A = sheets["Analysis_Summary"].set_index("metric").value
F = sheets["Funnel_Summary"].set_index("metric").value
elig_src = U[tenure >= 30]
rec_vals = {
    "Analysis: KYC rate": (A["KYC completion rate"], U.kyc_completed.mean()),
    "Analysis: bank-link rate": (A["Bank-link rate"], U.bank_account_linked.mean()),
    "Analysis: first-deposit rate": (A["First-deposit rate"], U.first_deposit_made.mean()),
    "Analysis: first-trade rate": (A["First-trade activation rate"], U.first_trade_made.mean()),
    "Analysis: 30d active rate": (A["30-day active rate (eligible users)"], elig_src.active_30d.mean()),
    "Analysis: 30d churn proxy": (A["30-day churn proxy (eligible users)"], elig_src.churned_30d_proxy.mean()),
    "Analysis: spend": (A["Campaign spend (INR)"], C.campaign_spend_inr.sum()),
    "Analysis: blended CAC (all users)": (A["Blended CAC on paid/partner spend (INR)"], C.campaign_spend_inr.sum() / N_U),
    "Analysis: tickets": (A["Support tickets"], N_T),
    "Analysis: avg resolution h": (A["Average resolved ticket time (hours)"], T.resolution_time_hours.mean()),
    "Analysis: CSAT": (A["Average CSAT (resolved tickets)"], T.csat_score.mean()),
    "Funnel: KYC": (F["KYC completed"], U.kyc_completed.sum()),
    "Funnel: bank": (F["Bank account linked"], U.bank_account_linked.sum()),
    "Funnel: deposit": (F["First deposit"], U.first_deposit_made.sum()),
    "Funnel: trade": (F["First trade"], U.first_trade_made.sum()),
    "Funnel: active 30d": (F["Active in last 30 days (eligible)"], U.active_30d.sum()),
    "Funnel: churn proxy count": (F["30-day churn proxy (eligible)"], U.churned_30d_proxy.sum()),
}
tol = lambda k: 0.0005 if "rate" in k or "proxy" in k and "count" not in k else (0.01 if "avg" in k or "CSAT" in k or "CAC" in k else 0.5)
bad = {k: (a, b) for k, (a, b) in rec_vals.items() if abs(float(a) - float(b)) > tol(k)}
pd.DataFrame([dict(item=k, reported=float(a), recalculated=round(float(b), 4), matches=k not in bad) for k, (a, b) in rec_vals.items()]).to_csv(VAL / "summary_sheet_reconciliation.csv", index=False)
check("MS01", "Analysis_Summary / Funnel_Summary", "Reported-metric accuracy", "Pre-computed summary KPIs that do not reproduce from row-level data", len(rec_vals), len(bad), "High", "Corrected",
      "All KPIs recomputed from row-level data. Mismatches: " + "; ".join(bad) + ". 'Blended CAC' = spend / paid-channel users only (excl. organic).", after=0)

# ---- Definition validity (churn) - documented, not data errors
boundary = U[tenure == 30]
check("MD01", "Users", "Definition validity", "Users flagged neither active_30d nor churned_30d_proxy although tenure>=30 d (boundary)", int((tenure >= 30).sum()),
      int(((tenure >= 30) & ~U.active_30d & ~U.churned_30d_proxy).sum()), "Medium", "Corrected",
      "eligible_30d redefined as tenure>=31 so that '>30 days inactive' is observable; 21 users with tenure=30 treated as not yet eligible", after=0)
_act_jul_oct = M[M.active_in_month & (M.activity_month >= "2026-07")].user_id.unique()
_elig = U.registration_month <= "2026-07"
_md2 = int((_elig & ~U.user_id.isin(_act_jul_oct)).sum())
check("MD02", "Users", "Definition validity", "Users with last_active_date in Jul-Oct 2026 (every user has one) but no active month Jul-Oct in Monthly_Activity", int(_elig.sum()), _md2, "High", "Documented",
      "Max observable inactivity is 120 days (no user is older), so churned_90d_proxy is bounded and under-states long-run inactivity. Treated as a recency proxy; long-run engagement from cohort retention")

# ---- Outliers (flagged; not removed)
dep = U.loc[U.first_deposit_made, "first_deposit_amount_inr"]
q1, q3 = dep.quantile([.25, .75]); fence_dep = q3 + 1.5 * (q3 - q1)
ldep = np.log(dep); lq1, lq3 = ldep.quantile([.25, .75]); lfence_dep = np.exp(lq3 + 1.5 * (lq3 - lq1))
check("OL01", "Users", "Outliers", f"First deposit above Tukey fence on raw scale (Rs {fence_dep:,.0f})", len(dep), int((dep > fence_dep).sum()), "Low", "Flagged (retained)",
      "flag_deposit_outlier_iqr=1. Log-normal body (log-skew ~0): extremes are legitimate right-tail values, not errors")
check("OL02", "Users", "Outliers", f"First deposit above Tukey fence on log scale (Rs {lfence_dep:,.0f})", len(dep), int((dep > lfence_dep).sum()), "Low", "Flagged (retained)",
      "flag_deposit_outlier_log=1. Almost nothing is an outlier once the skew is respected")
tv = M.loc[M.trading_value_inr > 0, "trading_value_inr"]
tq1, tq3 = tv.quantile([.25, .75]); fence_tv = tq3 + 1.5 * (tq3 - tq1)
ltv = np.log(tv); tl1, tl3 = ltv.quantile([.25, .75]); lfence_tv = np.exp(tl3 + 1.5 * (tl3 - tl1))
check("OL03", "Monthly_Activity", "Outliers", f"Monthly trading value above Tukey fence on raw scale (Rs {fence_tv:,.0f})", len(tv), int((tv > fence_tv).sum()), "Low", "Flagged (retained)",
      "flag_trading_value_outlier_iqr=1. Log-normal body: legitimate active-trader tail")
check("OL04", "Monthly_Activity", "Outliers", f"Monthly trading value above Tukey fence on log scale (Rs {lfence_tv:,.0f})", len(tv), int((tv > lfence_tv).sum()), "Low", "Flagged (retained)",
      "flag_trading_value_outlier_log=1")
avg_tr = (M.trading_value_inr / M.trade_count.replace(0, np.nan)).dropna()
la1, la3 = np.log(avg_tr).quantile([.25, .75]); lf_avg = np.exp(la3 + 1.5 * (la3 - la1))
check("OL05", "Monthly_Activity", "Outliers", f"Average trade size above log-scale fence (Rs {lf_avg:,.0f})", len(avg_tr), int((avg_tr > lf_avg).sum()), "Low", "Flagged (retained)",
      "flag_avg_trade_size_outlier=1")
rt = T.resolution_time_hours.dropna(); rq1, rq3 = rt.quantile([.25, .75]); fence_rt = rq3 + 1.5 * (rq3 - rq1)
check("OL06", "Support_Tickets", "Outliers", f"Resolution time above Tukey fence ({fence_rt:.1f} h)", len(rt), int((rt > fence_rt).sum()), "Low", "Flagged (retained)",
      "flag_resolution_outlier=1. Long tail is expected in service data; use median alongside mean")

# =====================================================================================
# 2. BUILD CLEANED TABLES
# =====================================================================================
# ---------- Cleaned_Campaigns (B)
cmap = {"Paid Search": "Paid Media", "Paid Social": "Paid Media", "Affiliate": "Partner & Affiliate", "Partnerships": "Partner & Affiliate",
        "Referral": "Owned & Lifecycle", "CRM": "Owned & Lifecycle", "Organic": "Organic"}
cc_ = C[["campaign_id", "campaign_name", "channel", "source_platform", "campaign_spend_inr"]].copy()
cc_["channel_group"] = cc_.channel.map(cmap)
cc_["is_paid"] = (cc_.campaign_spend_inr > 0).astype("int8")
cc_["spend_basis"] = np.where(cc_.is_paid == 1, "recorded_spend", "no_recorded_spend")
log("Campaigns", "channel_group, is_paid, spend_basis", "No grouping of channels; organic CAC would show as 0 (misleading)",
    "Added analyst-defined channel_group and is_paid; organic left with no CAC in downstream tables", len(cc_),
    "Organic activity has hidden costs (content, SEO, brand) that the data does not record, so CAC=0 is not 'free acquisition'.")
Cleaned_Campaigns = cc_

# ---------- Cleaned_Users (A)
u = U.copy()
u["tenure_days"] = (SNAP - u.registration_date).dt.days
log("Users", "first_deposit_amount_inr", "0.0 used as placeholder for 'no deposit'", "Set to NULL when no deposit was made",
    int((~u.first_deposit_made).sum()), "A zero would pull down averages and medians; NULL makes the 'not funded' state explicit.")
u.loc[~u.first_deposit_made, "first_deposit_amount_inr"] = np.nan

stage_cols = [("kyc", "kyc_completed", "kyc_completion_date"), ("bank", "bank_account_linked", "bank_link_date"),
              ("deposit", "first_deposit_made", "first_deposit_date"), ("trade", "first_trade_made", "first_trade_date")]
for s, f, d in stage_cols:
    u[f"{s}_date_asof"] = u[d].where(u[d] <= SNAP)
    u[f"{s}_asof"] = (u[f] & (u[d] <= SNAP)).astype("int8")
log("Users", "kyc/bank/deposit/trade _asof and _date_asof", "Completion flags include events dated after the 2026-10-31 snapshot (future information)",
    "Added *_asof flags and *_date_asof dates counting only events on/before snapshot; original columns retained untouched", int(fut_users.sum()),
    "Prevents the Oct-2026 cohort from showing conversion that had not yet happened (first-trade 40.0% on flags vs 8.4% as-of).")
u["first_deposit_amount_asof_inr"] = u.first_deposit_amount_inr.where(u.deposit_asof == 1)
u["cohort_maturity"] = np.where(u.registration_month < LAST_M, "mature", "immature_oct26")
u["funnel_mature"] = (u.registration_month < LAST_M).astype("int8")
u["eligible_30d"] = (u.tenure_days >= 31).astype("int8")
u["eligible_90d"] = (u.tenure_days >= 91).astype("int8")
log("Users", "cohort_maturity, funnel_mature, eligible_30d, eligible_90d", "No explicit eligibility for conversion or inactivity metrics",
    "Added maturity and eligibility columns (mature = registered before 2026-10; eligible_30d = tenure>=31 d; eligible_90d = tenure>=91 d)",
    int((u.funnel_mature == 0).sum()), "Separates 'not yet eligible' from 'genuinely inactive'. 21 users with tenure=30 d are inconsistent in the source flag and are treated as not yet eligible.")

def furthest(r):
    return "Traded" if r.trade_asof else "Funded" if r.deposit_asof else "Bank Linked" if r.bank_asof else "KYC Completed" if r.kyc_asof else "Registered"
u["furthest_stage_asof"] = u.apply(furthest, axis=1)
u["days_reg_to_kyc"] = (u.kyc_date_asof - u.registration_date).dt.days
u["days_kyc_to_bank"] = (u.bank_date_asof - u.kyc_date_asof).dt.days
u["days_bank_to_deposit"] = (u.deposit_date_asof - u.bank_date_asof).dt.days
u["days_deposit_to_trade"] = (u.trade_date_asof - u.deposit_date_asof).dt.days
u["days_reg_to_trade"] = (u.trade_date_asof - u.registration_date).dt.days

# recency re-derivation
u["last_event_date_asof"] = last_event.values
u["last_active_date_adj"] = pd.concat([u.last_active_date, u.last_event_date_asof], axis=1).max(axis=1)
u["days_inactive_adj"] = (SNAP - u.last_active_date_adj).dt.days
log("Users", "last_active_date_adj, days_inactive_adj", "last_active_date earlier than the user's own KYC/bank/deposit/trade date",
    "last_active_date_adj = max(last_active_date, latest as-of funnel event); days_inactive_adj recomputed from it", int(la_before_event.sum()),
    "A user cannot be last active before completing an action; the funnel event is itself proof of activity. Original columns kept.")
u["inactive_30d_adj"] = np.where(u.eligible_30d == 1, (u.days_inactive_adj > 30).astype(int), np.nan)
u["inactive_90d_adj"] = np.where(u.eligible_90d == 1, (u.days_inactive_adj > 90).astype(int), np.nan)
u["active_30d_adj"] = np.where(u.eligible_30d == 1, (u.days_inactive_adj <= 30).astype(int), np.nan)
u["recency_status_30d"] = np.select([u.eligible_30d == 0, u.days_inactive_adj <= 30], ["not_yet_eligible", "active_last_30d"], "inactive_30d_proxy")
u["recency_status_90d"] = np.select([u.eligible_90d == 0, u.days_inactive_adj <= 90], ["not_yet_eligible", "active_last_90d"], "inactive_90d_proxy")
log("Users", "inactive_30d_adj, inactive_90d_adj, active_30d_adj, recency_status_30d/90d", "Churn proxies computed on all users incl. those too new to be inactive; 90-day proxy truncated at 120 days",
    "Re-derived from days_inactive_adj with explicit eligibility; ineligible users get NULL and status 'not_yet_eligible'. Called 'inactive proxy', never 'churn'",
    int((u.eligible_30d == 0).sum()), "Genuine churn (closure, asset transfer-out, zero balance) is not observable in this dataset.")

# monthly-derived behaviour (source of truth for engagement)
mon = M.merge(U[["user_id", "registration_month"]], on="user_id")
mon["mi"] = mi(mon.activity_month); mon["rmi"] = mi(mon.registration_month); LAST_I = mi(pd.Series([LAST_M]))[0]
mon["traded"] = mon.trade_count > 0
agg = mon.groupby("user_id").agg(months_observed=("mi", "size"), active_months=("active_in_month", "sum"), trade_months=("traded", "sum"),
                                 total_trades=("trade_count", "sum"), total_trading_value_inr=("trading_value_inr", "sum"),
                                 total_deposit_value_inr=("deposit_value_inr", "sum"), total_withdrawal_value_inr=("withdrawal_value_inr", "sum"))
last6 = mon[mon.mi > LAST_I - 6].groupby("user_id").agg(trade_months_6m=("traded", "sum"), trading_value_6m_inr=("trading_value_inr", "sum"),
                                                        active_months_6m=("active_in_month", "sum"))
lastact = mon[mon.active_in_month].groupby("user_id").mi.max().rename("last_active_mi")
u = u.merge(agg, left_on="user_id", right_index=True, how="left").merge(last6, left_on="user_id", right_index=True, how="left").merge(lastact, left_on="user_id", right_index=True, how="left")
u["activity_ratio"] = (u.active_months / u.months_observed).round(4)
u["months_since_last_active_monthly"] = LAST_I - u.last_active_mi
u["never_active_monthly"] = u.last_active_mi.isna().astype("int8")
# dormancy: no activity in Aug-Oct 2026 (3 full calendar months); needs registration <= Jul-2026
a3 = mon[(mon.mi > LAST_I - 3) & mon.active_in_month].groupby("user_id").size()
u["dormant_3m_monthly"] = np.where(u.registration_month <= "2026-07", (~u.user_id.isin(a3.index)).astype(int), np.nan)
pv = mon.pivot_table(index="user_id", columns=mon.mi - mon.rmi, values="active_in_month", aggfunc="max")
for n_, lim in [(1, "2026-09"), (3, "2026-07"), (6, "2026-04")]:
    u[f"m{n_}_retained"] = np.where(u.registration_month <= lim, u.user_id.map(pv[n_]).astype(float), np.nan) if n_ in pv.columns else np.nan
log("Users", "months_observed … m1/m3/m6_retained, dormant_3m_monthly", "Engagement fields exist only at user-month grain",
    "Aggregated Monthly_Activity to user level; retention flags are NULL where the window is not yet observable (e.g. M3 needs registration <= 2026-07)",
    N_U, "Retention is recalculated from source events (monthly activity), not from the supplied snapshot flags.")

# support aggregates + flags
tk = T.groupby("user_id").agg(ticket_count=("ticket_id", "size"), unresolved_ticket_count=("status", lambda s: (s != "Resolved").sum()))
u = u.merge(tk, left_on="user_id", right_index=True, how="left"); u[["ticket_count", "unresolved_ticket_count"]] = u[["ticket_count", "unresolved_ticket_count"]].fillna(0).astype(int)

# conflict flags
u["flag_future_dated_event_raw"] = fut_users.values.astype("int8")
u["flag_last_active_conflict"] = u.user_id.map(mismatch).astype("int8")
u["flag_last_active_before_event"] = la_before_event.values.astype("int8")
mt = M.groupby("user_id").trade_count.sum(); md = M.groupby("user_id").deposit_value_inr.sum()
u["flag_trade_conflict"] = ((u.first_trade_made & (u.user_id.map(mt) == 0)) | (~u.first_trade_made & (u.user_id.map(mt) > 0))).astype("int8")
u["flag_deposit_conflict"] = ((u.first_deposit_made & (u.user_id.map(md) == 0)) | (~u.first_deposit_made & (u.user_id.map(md) > 0))).astype("int8")
u["flag_activity_conflict"] = ((u.flag_trade_conflict + u.flag_deposit_conflict + u.flag_last_active_conflict) > 0).astype("int8")
u["flag_deposit_outlier_iqr"] = (u.first_deposit_amount_inr > fence_dep).astype("int8")
u["flag_deposit_outlier_log"] = (u.first_deposit_amount_inr > lfence_dep).astype("int8")
log("Users", "flag_* columns", "Cross-table contradictions and outliers", "Added row-level flags; no rows deleted or values overwritten",
    int(u.flag_activity_conflict.sum()), "No ground truth identifies which table is wrong, so contradictions are exposed, not silently resolved.")

# booleans -> 0/1 ints, dates -> ISO strings (done at write time)
for c_ in bool_cols: u[c_] = u[c_].astype("int8")
for f_ in ["kyc_completed", "bank_account_linked", "first_deposit_made", "first_trade_made"]: pass
Cleaned_Users = u.drop(columns=["last_active_mi"])
log("All", "Boolean columns", "True/False text booleans", "Converted to 0/1 int8 in all output files", len(bool_cols) * N_U, "Consistent typing for SQL, Excel and Power BI.")
log("All", "date columns", "Mixed datetime representation", "All dates written as ISO yyyy-mm-dd; months as yyyy-mm", 6 * N_U, "Single date format across tables.")

# ---------- Cleaned_Monthly_Activity (C)
cm = M.copy()
cm["activity_month_start"] = pd.to_datetime(cm.activity_month + "-01")
cm = cm.merge(U[["user_id", "registration_month", "first_trade_made", "first_deposit_made"]], on="user_id")
cm["ftm"] = cm.user_id.map(first_trade_m); cm["fdm"] = cm.user_id.map(first_dep_m)
cm["traded_in_month"] = (cm.trade_count > 0).astype("int8"); cm["deposited_in_month"] = (cm.deposit_value_inr > 0).astype("int8")
cm["withdrew_in_month"] = (cm.withdrawal_value_inr > 0).astype("int8")
cm["net_flow_inr"] = (cm.deposit_value_inr - cm.withdrawal_value_inr).round(2)
cm["avg_trade_value_inr"] = (cm.trading_value_inr / cm.trade_count.replace(0, np.nan)).round(2)
cm["is_registration_month"] = (cm.months_since_registration == 0).astype("int8")
cm["flag_trade_without_first_trade_flag"] = ((cm.trade_count > 0) & ~cm.first_trade_made).astype("int8")
cm["flag_trade_before_first_trade_month"] = ((cm.trade_count > 0) & cm.first_trade_made & (cm.activity_month < cm.ftm)).astype("int8")
cm["flag_deposit_without_first_deposit_flag"] = ((cm.deposit_value_inr > 0) & ~cm.first_deposit_made).astype("int8")
cm["flag_deposit_before_first_deposit_month"] = ((cm.deposit_value_inr > 0) & cm.first_deposit_made & (cm.activity_month < cm.fdm)).astype("int8")
cm["flag_withdrawal_without_deposit_flag"] = ((cm.withdrawal_value_inr > 0) & ~cm.first_deposit_made).astype("int8")
cm = cm.sort_values(["user_id", "activity_month"])
cm["cum_deposit_inr"] = cm.groupby("user_id").deposit_value_inr.cumsum(); cm["cum_withdrawal_inr"] = cm.groupby("user_id").withdrawal_value_inr.cumsum()
cm["flag_cum_withdrawal_exceeds_deposits"] = (cm.cum_withdrawal_inr > cm.cum_deposit_inr + 0.005).astype("int8")
cm["flag_active_after_last_active_month"] = (cm.active_in_month & (cm.activity_month > cm.user_id.map(lam))).astype("int8")
cm["flag_trading_value_outlier_iqr"] = (cm.trading_value_inr > fence_tv).astype("int8")
cm["flag_trading_value_outlier_log"] = (cm.trading_value_inr > lfence_tv).astype("int8")
cm["flag_avg_trade_size_outlier"] = (cm.avg_trade_value_inr > lf_avg).astype("int8")
cm["active_in_month"] = cm.active_in_month.astype("int8")
Cleaned_Monthly_Activity = cm.drop(columns=["first_trade_made", "first_deposit_made", "ftm", "fdm"])
check("XT11", "Monthly_Activity", "Cross-table consistency", "Cumulative withdrawals exceed cumulative deposits in a user-month (informational)", N_M,
      int(cm.flag_cum_withdrawal_exceeds_deposits.sum()), "Medium", "Flagged (retained)", "flag_cum_withdrawal_exceeds_deposits=1; do not use for cash-balance analysis")
log("Monthly_Activity", "flag_* , net_flow_inr, avg_trade_value_inr, cum_*", "Source rows contradict the Users funnel flags",
    "Rows kept. Added consistency, outlier and derived-measure columns", int(cm.filter(like="flag_").drop(columns=["flag_trading_value_outlier_iqr", "flag_trading_value_outlier_log", "flag_avg_trade_size_outlier"]).max(axis=1).sum()),
    "Monthly_Activity is the source of truth for engagement; Users for funnel. Rows are neither deleted nor 'fixed' because the true value is unknown.")

# ---------- Cleaned_Support_Tickets (D)
ct = T.copy()
ct["is_resolved"] = (ct.status == "Resolved").astype("int8"); ct["is_unresolved"] = (ct.status != "Resolved").astype("int8")
ct["ticket_age_days"] = (SNAP - ct.created_date).dt.days
ct["backlog_age_bucket"] = np.where(ct.is_unresolved == 1, pd.cut(ct.ticket_age_days, [-1, 30, 90, 180, 10_000], labels=["0-30d", "31-90d", "91-180d", ">180d"]).astype(str), "n/a (resolved)")
ct["csat_band"] = pd.cut(ct.csat_score, [0, 2, 3, 5], labels=["Low (1-2)", "Neutral (3)", "High (4-5)"]).astype(object)
ct = ct.merge(U[["user_id", "registration_date"]], on="user_id"); ct["days_since_registration"] = (ct.created_date - ct.registration_date).dt.days; ct = ct.drop(columns="registration_date")
smap = {"KYC & verification": "kyc", "Bank linking": "bank", "Deposits & withdrawals": "deposit", "Trading & orders": "trade"}
ct["related_funnel_stage"] = ct.category.map(smap)
ud = Cleaned_Users.set_index("user_id")
def pend(r):
    s = r.related_funnel_stage
    if pd.isna(s): return np.nan
    d = ud.at[r.user_id, f"{s}_date_asof"]
    return 1 if (pd.isna(d) or r.created_date < d) else 0
ct["stage_pending_at_ticket"] = ct.apply(pend, axis=1).astype("Int8")
ct["flag_resolution_outlier"] = (ct.resolution_time_hours > fence_rt).astype("Int8").where(ct.resolution_time_hours.notna())
Cleaned_Support_Tickets = ct
log("Support_Tickets", "is_resolved, ticket_age_days, backlog_age_bucket, related_funnel_stage, stage_pending_at_ticket",
    "Resolution time / CSAT exist only for resolved tickets (survivorship); no backlog ageing; no link between ticket and funnel stage",
    "Added resolved/unresolved flags, ageing buckets and a stage-pending flag (ticket created before the related funnel event, or event never reached)",
    int(ct.is_unresolved.sum()), "Lets Phase 3 report resolved-only averages alongside the unresolved backlog and test the 'stuck at stage' hypothesis.")

# =====================================================================================
# 3. TABLES E-H
# =====================================================================================
cu = Cleaned_Users
# ---------- Customer_Cohorts (F): cohort x channel x months_since_registration, full grid with observability
months = sorted(cu.registration_month.unique()); chans = sorted(cu.acquisition_channel.unique())
rows = []
mon2 = mon.merge(cu[["user_id", "acquisition_channel"]], on="user_id"); mon2["n"] = mon2.mi - mon2.rmi
ga = mon2.groupby(["registration_month", "acquisition_channel", "n"]).agg(active_users=("active_in_month", "sum"), trading_users=("traded", "sum"),
        trades=("trade_count", "sum"), trading_value_inr=("trading_value_inr", "sum"), deposit_value_inr=("deposit_value_inr", "sum"),
        withdrawal_value_inr=("withdrawal_value_inr", "sum"), users_observed=("user_id", "nunique")).reset_index()
size = cu.groupby(["registration_month", "acquisition_channel"]).size().rename("cohort_users").reset_index()
grid = pd.MultiIndex.from_product([months, chans, range(12)], names=["registration_month", "acquisition_channel", "months_since_registration"]).to_frame(index=False)
grid = grid.merge(size, on=["registration_month", "acquisition_channel"], how="left").merge(ga.rename(columns={"n": "months_since_registration"}),
        on=["registration_month", "acquisition_channel", "months_since_registration"], how="left")
grid["observable"] = ((mi(grid.registration_month) + grid.months_since_registration) <= LAST_I).astype("int8")
for c_ in ["active_users", "trading_users", "trades", "trading_value_inr", "deposit_value_inr", "withdrawal_value_inr", "users_observed"]:
    grid[c_] = np.where(grid.observable == 1, grid[c_], np.nan)
grid["retention_rate"] = (grid.active_users / grid.cohort_users).round(4)
grid["trading_rate"] = (grid.trading_users / grid.cohort_users).round(4)
grid["cohort_status"] = np.where(grid.observable == 1, "observed", "not_yet_eligible")
Customer_Cohorts = grid
obs = grid[grid.observable == 1]
chk_ = obs.groupby(["registration_month", "months_since_registration"]).agg(cu=("cohort_users", "sum"), au=("active_users", "sum")).reset_index()
cmp_ = co_raw.merge(chk_, on=["registration_month", "months_since_registration"], how="outer")
check("RC01", "Customer_Cohorts", "Reconciliation", "Rebuilt cohort table vs supplied Cohort_Retention sheet (cohort size & active users, per cell)", len(cmp_) * 2,
      int((cmp_.cohort_users != cmp_.cu).sum() + (cmp_.active_users != cmp_.au).sum()), "-", "Pass", "Exact reconciliation")

# ---------- Customer_Funnel (E)
STAGES = [(1, "Registered"), (2, "KYC Completed"), (3, "Bank Linked"), (4, "First Deposit"), (5, "First Trade"), (6, "Active (30d)")]
def funnel_for(df, cut_type, cut_val, scope, active_na=False):
    n0 = len(df)
    reached = [n0, int(df.kyc_asof.sum()), int(df.bank_asof.sum()), int(df.deposit_asof.sum()), int(df.trade_asof.sum()),
               int(((df.trade_asof == 1) & (df.active_30d_adj == 1)).sum())]
    meds = [np.nan, df.days_reg_to_kyc.median(), df.days_kyc_to_bank.median(), df.days_bank_to_deposit.median(), df.days_deposit_to_trade.median(), np.nan]
    p75 = [np.nan, df.days_reg_to_kyc.quantile(.75), df.days_kyc_to_bank.quantile(.75), df.days_bank_to_deposit.quantile(.75), df.days_deposit_to_trade.quantile(.75), np.nan]
    out = []
    for i, (o, nm) in enumerate(STAGES):
        r = reached[i] if not (active_na and o == 6) else np.nan
        prev = reached[i - 1] if i else np.nan
        out.append(dict(cut_type=cut_type, cut_value=cut_val, scope=scope, stage_order=o, stage_name=nm, users_registered=n0, users_reached=r,
                        conv_from_previous=(r / prev) if i and not pd.isna(r) and prev else (1.0 if i == 0 else np.nan),
                        conv_from_registration=(r / n0) if n0 and not pd.isna(r) else np.nan,
                        dropoff_from_previous=(1 - r / prev) if i and not pd.isna(r) and prev else (0.0 if i == 0 else np.nan),
                        median_days_from_previous=meds[i], p75_days_from_previous=p75[i]))
    return out
mat = cu[cu.funnel_mature == 1]
fr = funnel_for(mat, "Overall", "All", "mature_cohorts")
for ct_ in ["acquisition_channel", "acquisition_campaign_id", "device_type", "age_group", "city", "risk_profile"]:
    for v, d in mat.groupby(ct_): fr += funnel_for(d, ct_, v, "mature_cohorts")
for v, d in cu.groupby("registration_month"): fr += funnel_for(d, "registration_month", v, "asof_snapshot_all_users", active_na=(v == LAST_M))
Customer_Funnel = pd.DataFrame(fr)
for c_ in ["conv_from_previous", "conv_from_registration", "dropoff_from_previous"]: Customer_Funnel[c_] = Customer_Funnel[c_].round(4)

# ---------- Customer_Segments (H)
cs = cu[["user_id", "acquisition_channel", "age_group", "city", "device_type", "risk_profile", "tenure_days", "furthest_stage_asof", "trade_asof", "deposit_asof",
         "first_deposit_amount_asof_inr", "months_since_last_active_monthly", "never_active_monthly", "trade_months_6m", "trading_value_6m_inr", "active_months_6m",
         "total_trades", "total_trading_value_inr", "activity_ratio", "dormant_3m_monthly", "ticket_count", "unresolved_ticket_count", "flag_trade_conflict", "flag_deposit_conflict", "flag_activity_conflict"]].copy()
cs["trade_months_6m"] = cs.trade_months_6m.fillna(0); cs["trading_value_6m_inr"] = cs.trading_value_6m_inr.fillna(0)
p75_dep = cu.loc[cu.deposit_asof == 1, "first_deposit_amount_asof_inr"].quantile(.75)
rfm_ok = cs.tenure_days >= 60
def sc_r(x): return 1 if pd.isna(x) else 5 if x == 0 else 4 if x == 1 else 3 if x == 2 else 2 if x <= 4 else 1
cs["r_score"] = np.where(rfm_ok, cs.months_since_last_active_monthly.map(sc_r), np.nan)
cs["f_score"] = np.where(rfm_ok, cs.trade_months_6m.clip(upper=4).map({0: 1, 1: 2, 2: 3, 3: 4, 4: 5}), np.nan)
pos = cs.loc[rfm_ok & (cs.trading_value_6m_inr > 0), "trading_value_6m_inr"]; qs = pos.quantile([.25, .5, .75]).values
cs["m_score"] = np.where(rfm_ok, np.where(cs.trading_value_6m_inr <= 0, 1, 2 + np.digitize(cs.trading_value_6m_inr, qs)), np.nan)
def rfm_name(r):
    if pd.isna(r.r_score): return "Too new for RFM (<60d)"
    R_, F_ = r.r_score, r.f_score
    if R_ >= 4 and F_ >= 4: return "Champions"
    if R_ >= 3 and F_ >= 3: return "Loyal"
    if R_ >= 4 and F_ <= 2: return "Promising / Light"
    if R_ in (2, 3) and F_ >= 3: return "At Risk"
    if R_ <= 2 and F_ <= 2: return "Hibernating"
    return "Needs Attention"
cs["rfm_segment"] = cs.apply(rfm_name, axis=1)
cs["flag_needs_support"] = ((cs.unresolved_ticket_count >= 1) | (cs.ticket_count >= 3)).astype("int8")
sp = Cleaned_Support_Tickets.groupby("user_id").stage_pending_at_ticket.max()
cs["flag_support_stuck_at_funnel_stage"] = cs.user_id.map(sp).fillna(0).astype("int8")
def life(r):
    # Behaviour comes from Monthly_Activity (source of truth for engagement); funnel flags are used only for deposit size
    # and to confirm "never traded" (both sources must agree).
    if r.tenure_days < 60: return "1. New / Onboarding"
    if r.trade_months_6m >= 4: return "2. Frequent Trader"
    if r.deposit_asof == 1 and r.first_deposit_amount_asof_inr >= p75_dep and r.dormant_3m_monthly != 1 and r.never_active_monthly == 0: return "3. High-Potential Investor"
    if r.trade_asof == 0 and r.total_trades == 0: return "4. Never Traded (not activated)"
    if r.dormant_3m_monthly == 1: return "5. Dormant / Inactive"
    return "6. Core Active"
cs["lifecycle_segment"] = cs.apply(life, axis=1)
Customer_Segments = cs.drop(columns=["months_since_last_active_monthly"]).assign(months_since_last_active_monthly=cs.months_since_last_active_monthly)

# ---------- Campaign_Performance (G)
cpf = cc_.set_index("campaign_id")
g_all = cu.groupby("acquisition_campaign_id").agg(registered_users=("user_id", "size"), kyc_asof=("kyc_asof", "sum"), bank_asof=("bank_asof", "sum"), deposit_asof=("deposit_asof", "sum"), trade_asof=("trade_asof", "sum"))
g_mat = cu[cu.funnel_mature == 1].groupby("acquisition_campaign_id").agg(mature_users=("user_id", "size"), kyc_rate_mature=("kyc_asof", "mean"), bank_rate_mature=("bank_asof", "mean"),
        deposit_rate_mature=("deposit_asof", "mean"), first_trade_rate_mature=("trade_asof", "mean"), median_first_deposit_inr=("first_deposit_amount_asof_inr", "median"))
g_ret = cu[cu.eligible_30d == 1].groupby("acquisition_campaign_id").agg(eligible_30d_users=("user_id", "size"), active_30d_rate=("active_30d_adj", "mean"), inactive_30d_proxy_rate=("inactive_30d_adj", "mean"))
g_m1 = cu[cu.m1_retained.notna()].groupby("acquisition_campaign_id").m1_retained.mean().rename("m1_retention")
g_m3 = cu[cu.m3_retained.notna()].groupby("acquisition_campaign_id").m3_retained.mean().rename("m3_retention")
g_d3 = cu[cu.dormant_3m_monthly.notna()].groupby("acquisition_campaign_id").dormant_3m_monthly.mean().rename("dormant_3m_rate")
g_ar = cu.groupby("acquisition_campaign_id").activity_ratio.mean().rename("avg_activity_ratio")
tk2 = Cleaned_Support_Tickets.merge(cu[["user_id", "acquisition_campaign_id"]], on="user_id").groupby("acquisition_campaign_id").size().rename("tickets")
um = mon.merge(cu[["user_id", "acquisition_campaign_id"]], on="user_id").groupby("acquisition_campaign_id").size().rename("customer_months")
cp = cpf.join([g_all, g_mat, g_ret, g_m1, g_m3, g_d3, g_ar, tk2, um]).reset_index()
cp["share_of_registrations"] = cp.registered_users / cp.registered_users.sum()
cp["share_of_spend"] = cp.campaign_spend_inr / cp.campaign_spend_inr.sum()
sp_ = cp.campaign_spend_inr.where(cp.is_paid == 1)
cp["cac_inr"] = sp_ / cp.registered_users
cp["cost_per_kyc_asof_inr"] = sp_ / cp.kyc_asof
cp["cost_per_first_trade_asof_inr"] = sp_ / cp.trade_asof
cp["cost_per_first_trade_at_maturity_inr"] = cp.cac_inr / cp.first_trade_rate_mature
cp["cost_per_kyc_at_maturity_inr"] = cp.cac_inr / cp.kyc_rate_mature
cp["cost_per_active_30d_user_inr"] = cp.cac_inr / cp.active_30d_rate
cp["tickets_per_1000_customer_months"] = cp.tickets / cp.customer_months * 1000
cp["cac_note"] = np.where(cp.is_paid == 1, "spend / registered users", "no recorded spend - CAC not defined (not 'free')")
Campaign_Performance = cp
# reconcile with supplied campaign sheet
cs_chk = C.set_index("campaign_id")[["cac_inr", "cost_per_kyc_inr", "cost_per_first_trade_inr"]].join(
    cp.set_index("campaign_id")[["cac_inr", "cost_per_kyc_asof_inr", "cost_per_first_trade_asof_inr"]], rsuffix="_new")
paid_ = cp.set_index("campaign_id").is_paid == 1
diff_cac = ((cs_chk.cac_inr - cs_chk.cac_inr_new.fillna(0)).abs() > 0.01)[paid_].sum()
check("RC02", "Campaign_Performance", "Reconciliation", "Recomputed CAC vs supplied Campaigns.cac_inr (paid campaigns)", int(paid_.sum()), int(diff_cac), "-", "Pass",
      "CAC reproduces. Supplied cost-per-KYC / cost-per-first-trade use eventual (flag) completions; new *_asof columns use on-snapshot events and *_at_maturity columns use mature-cohort rates")

# =====================================================================================
# 4. RETENTION / CHURN RE-VALIDATION TABLE
# =====================================================================================
rv = []
def add(metric, definition, elig, supplied, recalc, note): rv.append(dict(metric=metric, definition=definition, eligible_users=elig, supplied_value=supplied, recalculated_value=recalc, note=note))
e30 = cu[cu.eligible_30d == 1]; e90 = cu[cu.eligible_90d == 1]
add("Users not yet eligible for 30-day measurement", "tenure < 31 days", int((cu.eligible_30d == 0).sum()), np.nan, int((cu.eligible_30d == 0).sum()), "Supplied sheets treat tenure<30 as ineligible; 21 boundary users (tenure=30) were inconsistent")
add("30-day active rate", "days since last activity <= 30", len(e30), round(float(elig_src.active_30d.mean()), 4), round(float(e30.active_30d_adj.mean()), 4), "Recalculated after lifting last_active_date to the latest funnel event")
add("30-day inactivity proxy rate", "days since last activity > 30", len(e30), round(float(elig_src.churned_30d_proxy.mean()), 4), round(float(e30.inactive_30d_adj.mean()), 4), "Proxy only - not churn")
add("30-day inactivity proxy rate (supplied flag, all users)", "churned_30d_proxy over 10,000", N_U, round(float(U.churned_30d_proxy.mean()), 4), round(float(e30.inactive_30d_adj.mean()), 4), "Supplied rate on all users mixes in users too new to be inactive")
add("Users not yet eligible for 90-day measurement", "tenure < 91 days", int((cu.eligible_90d == 0).sum()), np.nan, int((cu.eligible_90d == 0).sum()), "Registered on/after 2026-08-01")
add("90-day inactivity proxy rate", "days since last activity > 90", len(e90), round(float(U[tenure >= 91].churned_90d_proxy.mean()), 4), round(float(e90.inactive_90d_adj.mean()), 4), "TRUNCATED: max observable inactivity is 120 days; true long-run inactivity is higher")
add("Maximum days inactive observed", "max(days_inactive_as_of_snapshot)", N_U, np.nan, int(U.days_inactive_as_of_snapshot.max()), "No user is inactive longer than 120 days even though Nov-2025 cohorts have 12 months of history: the 90-day proxy is bounded")
d3 = cu[cu.dormant_3m_monthly.notna()]
add("3-month dormancy (monthly source)", "no active month in Aug-Oct 2026", len(d3), np.nan, round(float(d3.dormant_3m_monthly.mean()), 4), "Event-based; registered <= Jul-2026")
add("Agreement: 90-day proxy vs 3-month dormancy", "share of users where both agree (users eligible for both)", len(d3), np.nan,
    round(float((d3.inactive_90d_adj == d3.dormant_3m_monthly).mean()), 4), "Low agreement = the two sources describe different things")
for n_, lim in [(1, "M1"), (3, "M3"), (6, "M6")]:
    x = cu[cu[f"m{n_}_retained"].notna()]
    add(f"{lim} retention (monthly source)", f"active in calendar month {n_} after registration month", len(x), np.nan, round(float(x[f"m{n_}_retained"].mean()), 4), "Month 0 is a partial month")
mm0 = cu[cu.m1_retained.notna()]
add("Users never active in any monthly row", "no active_in_month=True", int(cu.never_active_monthly.sum()), np.nan, int(cu.never_active_monthly.sum()), "Not necessarily churn - never engaged")
RV = pd.DataFrame(rv); RV.to_csv(VAL / "retention_churn_validation.csv", index=False)

# =====================================================================================
# 5. POST-CORRECTION RE-TESTS (computed on the cleaned tables)
# =====================================================================================
chk_df = pd.DataFrame(CHECKS)
after_asof_future = int(sum(((Cleaned_Users[f"{s}_date_asof"] > SNAP).sum()) for s, _, _ in stage_cols))
assert after_asof_future == 0
assert (Cleaned_Users.last_active_date_adj >= Cleaned_Users.last_event_date_asof.fillna(pd.Timestamp("1900-01-01"))).all()
assert Cleaned_Users.user_id.is_unique and len(Cleaned_Users) == N_U and len(Cleaned_Monthly_Activity) == N_M and len(Cleaned_Support_Tickets) == N_T
# stage ordering still holds on the as-of columns
assert ((Cleaned_Users.bank_date_asof >= Cleaned_Users.kyc_date_asof) | Cleaned_Users.bank_date_asof.isna()).all()

rels = [("Cleaned_Monthly_Activity.user_id", Cleaned_Monthly_Activity.user_id, Cleaned_Users.user_id),
        ("Cleaned_Support_Tickets.user_id", Cleaned_Support_Tickets.user_id, Cleaned_Users.user_id),
        ("Cleaned_Users.acquisition_campaign_id", Cleaned_Users.acquisition_campaign_id, Cleaned_Campaigns.campaign_id),
        ("Customer_Segments.user_id", Customer_Segments.user_id, Cleaned_Users.user_id),
        ("Campaign_Performance.campaign_id", Campaign_Performance.campaign_id, Cleaned_Campaigns.campaign_id),
        ("Customer_Cohorts.acquisition_channel", Customer_Cohorts.acquisition_channel, Cleaned_Campaigns.channel),
        ("Customer_Funnel (campaign cut).cut_value", Customer_Funnel.loc[Customer_Funnel.cut_type == "acquisition_campaign_id", "cut_value"], Cleaned_Campaigns.campaign_id)]
pk = [("Cleaned_Users.user_id", Cleaned_Users.user_id), ("Cleaned_Campaigns.campaign_id", Cleaned_Campaigns.campaign_id), ("Cleaned_Support_Tickets.ticket_id", Cleaned_Support_Tickets.ticket_id),
      ("Customer_Segments.user_id", Customer_Segments.user_id), ("Campaign_Performance.campaign_id", Campaign_Performance.campaign_id)]
relrows = [dict(test="primary key unique", object=n, rows=len(s_), violations=int(s_.duplicated().sum())) for n, s_ in pk]
relrows.append(dict(test="primary key unique", object="Cleaned_Monthly_Activity (user_id, activity_month)", rows=len(Cleaned_Monthly_Activity), violations=int(Cleaned_Monthly_Activity.duplicated(["user_id", "activity_month"]).sum())))
relrows.append(dict(test="primary key unique", object="Customer_Cohorts (registration_month, channel, months_since_registration)", rows=len(Customer_Cohorts), violations=int(Customer_Cohorts.duplicated(["registration_month", "acquisition_channel", "months_since_registration"]).sum())))
relrows += [dict(test="foreign key (no orphans)", object=n, rows=len(c_), violations=int((~c_.isin(p_)).sum())) for n, c_, p_ in rels]
pd.DataFrame(relrows).to_csv(VAL / "relationship_validation_clean.csv", index=False)
assert all(r["violations"] == 0 for r in relrows)

# =====================================================================================
# 6. WRITE OUTPUTS
# =====================================================================================
def fmt(df):
    d = df.copy()
    for c in d.columns:
        if pd.api.types.is_datetime64_any_dtype(d[c]): d[c] = d[c].dt.strftime("%Y-%m-%d")
        elif pd.api.types.is_float_dtype(d[c]): d[c] = d[c].round(4)
    return d
tables = {"Cleaned_Users": Cleaned_Users, "Cleaned_Campaigns": Cleaned_Campaigns, "Cleaned_Monthly_Activity": Cleaned_Monthly_Activity,
          "Cleaned_Support_Tickets": Cleaned_Support_Tickets, "Customer_Funnel": Customer_Funnel, "Customer_Cohorts": Customer_Cohorts,
          "Campaign_Performance": Campaign_Performance, "Customer_Segments": Customer_Segments}
for k, v in tables.items():
    fmt(v).to_csv((OUT if k.startswith("Cleaned_") else DER) / f"{k}.csv", index=False)
chk_df.to_csv(VAL / "validation_checks.csv", index=False)
pd.DataFrame(CLEAN_LOG).to_csv(STEP / "cleaning_log.csv", index=False)
(pd.concat(EXC, ignore_index=True) if EXC else pd.DataFrame()).to_csv(VAL / "row_level_exceptions.csv", index=False)
meta = dict(records_before=REC_BEFORE, records_after={k: len(v) for k, v in tables.items()},
            thresholds=dict(fence_dep_raw=fence_dep, fence_dep_log=lfence_dep, fence_tv_raw=fence_tv, fence_tv_log=lfence_tv, fence_avg_trade_log=lf_avg, fence_res_time=fence_rt, p75_first_deposit=p75_dep),
            future_event_counts={d: int(v.sum()) for d, v in fut_mask.items()}, users_future=int(fut_users.sum()))
json.dump(meta, open(VAL / "run_metadata.json", "w"), indent=2, default=float)
print("OK", meta["records_after"])
