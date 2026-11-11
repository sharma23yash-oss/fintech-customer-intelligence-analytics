"""End-to-end validation of the friction detector on the SYNTHETIC dataset.

Run:  python validation/validate.py
Writes validation/validation_results.json and docs/TESTING_RESULTS.md (numbers only; narrative lives in docs/TESTING.md).
Every check prints PASS/FAIL. Exit code 1 if any check fails.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "validation"))

import numpy as np
import pandas as pd

import oracle
from friction_detector import config as C
from friction_detector.engine import clean_users, derive_config, run_engine, watch_windows

DATA = ROOT / "data" / "synthetic"
SNAP = C.SNAPSHOT_DATE
results: list[dict] = []


def check(name: str, ok: bool, detail: str = ""):
    results.append({"check": name, "result": "PASS" if ok else "FAIL", "detail": detail})
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" - {detail}" if detail else ""))


users = pd.read_csv(DATA / "users.csv")
tickets = pd.read_csv(DATA / "tickets.csv")
monthly = pd.read_csv(DATA / "monthly_activity.csv")
cfg = derive_config(users, tickets)
watch = watch_windows(users, cfg)
res = run_engine(users, tickets, SNAP, cfg, monthly=monthly, watch=watch).set_index("user_id")

# ------------------------------------------------------------------ 1. input data quality
check("Input: user_id unique", users["user_id"].is_unique, f"{len(users):,} users")
check("Input: ticket_id unique", tickets["ticket_id"].is_unique, f"{len(tickets):,} tickets")
check("Input: all tickets map to a user", tickets["user_id"].isin(users["user_id"]).all())
check("Input: no missing registration dates", users["registration_date"].notna().all())
check("Input: every record labelled SYNTHETIC", set(res["data_label"]) == {"SYNTHETIC"})
_, issues = clean_users(users)
check("Cleaning found nothing to drop in the source data",
      issues["duplicate_user_rows_dropped"] == 0 and issues["rows_missing_registration_date_dropped"] == 0,
      json.dumps({k: v for k, v in issues.items() if v}))

# ------------------------------------------------------------------ 2. eligibility
check("Eligibility: every registered customer analysed exactly once", len(res) == len(users) and res.index.is_unique)
check("Eligibility: no flagged customer is inside its window",
      bool(((res["is_flagged"] == 1) & (res["primary_category"] == C.WITHIN_WINDOW)).sum() == 0))
jr = res[res["primary_category"].isin(["KYC_PENDING", "BANK_LINK_PENDING", "FIRST_DEPOSIT_PENDING", "FIRST_TRADE_PENDING"])]
check("Eligibility: every journey flag has dwell > window", bool((jr["dwell_days"] > jr["window_days"]).all()))
wi = res[res["primary_category"] == C.WITHIN_WINDOW]
check("Eligibility: every WITHIN_WINDOW customer has dwell <= window", bool((wi["dwell_days"] <= wi["window_days"]).all()),
      f"{len(wi):,} customers deliberately not flagged")
ina = res[res["friction_categories"].str.contains("INACTIVITY_RISK")]
check("Eligibility: inactivity flags only for traded customers with tenure >= 31 d and > 30 d inactive",
      bool(((ina["stage_idx"] == 4) & (ina["tenure_days"] >= 31) & (ina["days_inactive"] > 30)).all()), f"{len(ina):,} flagged")
check("Eligibility: nobody registered in the last 3 days is flagged for a journey step",
      bool(res[(res["tenure_days"] <= 3)]["primary_category"].isin(["KYC_PENDING", "BANK_LINK_PENDING",
                                                                    "FIRST_DEPOSIT_PENDING", "FIRST_TRADE_PENDING"]).sum() == 0))

# ------------------------------------------------------------------ 3. oracle comparison
orc, o_windows = oracle.run(DATA, SNAP)
check("Oracle: same windows as engine", list(cfg.windows().values()) == o_windows, f"{o_windows}")
check("Oracle: same population", set(orc) == set(res.index))
cmp_cols = ["stage_idx", "is_flagged", "friction_categories", "primary_category", "days_overdue", "days_inactive",
            "data_confidence", "priority_band", "tickets_total", "tickets_unresolved"]
mism = {}
for c in cmp_cols:
    o = pd.Series({k: v[c] for k, v in orc.items()})
    e = res[c].reindex(o.index)
    mism[c] = int((o.astype(str) != e.astype(str)).sum())
    check(f"Oracle: '{c}' agrees for all customers", mism[c] == 0, f"{mism[c]} mismatches")
os_ = pd.Series({k: v["priority_score"] for k, v in orc.items()})
diff = (os_ - res["priority_score"].reindex(os_.index)).abs()
check("Oracle: priority_score agrees within 0.05", bool((diff <= 0.05).all()), f"max abs diff {diff.max():.3f}")
agree = float(np.mean([orc[k]["primary_category"] == res.loc[k, "primary_category"] for k in orc]))

# ------------------------------------------------------------------ 4. false positives vs business rules
fp_rows = {}
# a "false positive" here = flagged although the written rule says it should not be.
o_flag = pd.Series({k: v["is_flagged"] for k, v in orc.items()})
e_flag = res["is_flagged"].reindex(o_flag.index)
fp = int(((e_flag == 1) & (o_flag == 0)).sum())
fn = int(((e_flag == 0) & (o_flag == 1)).sum())
check("False positives vs rule oracle = 0", fp == 0, f"engine flagged, oracle did not: {fp}")
check("False negatives vs rule oracle = 0", fn == 0, f"oracle flagged, engine did not: {fn}")

# ------------------------------------------------------------------ 5. reconciliation to earlier phases
ref = pd.read_csv(ROOT.parent / "data" / "cleaned" / "Cleaned_Users.csv", usecols=["user_id", "furthest_stage_asof"])
ref = ref.set_index("user_id")["furthest_stage_asof"]
same = (res["stage_name"].reindex(ref.index) == ref)
check("Reconcile: stage matches Phase 2 furthest_stage_asof for every user", bool(same.all()),
      f"{int((~same).sum())} differences")
stage_counts = res["stage_name"].value_counts().to_dict()
check("Reconcile: 3,536 customers have traded (Phase 3 funnel)", stage_counts.get("Traded") == 3536,
      f"engine {stage_counts.get('Traded')}")

# ------------------------------------------------------------------ 6. backtest: premature-flag rate by window choice
# Among users who DID complete a step, what share had waited longer than the window at completion time?
# Those customers would have been flagged "too early" (they were about to complete on their own).
bt = []
u2, _ = clean_users(users)
for label, q in [("p50", 0.50), ("p75", 0.75), ("p90", 0.90), ("p95 (used)", 0.95), ("max", 1.0)]:
    row = {"window_rule": label}
    for s, (a, b) in enumerate([("registration_date", "kyc_date_asof"), ("kyc_date_asof", "bank_date_asof"),
                                ("bank_date_asof", "deposit_date_asof"), ("deposit_date_asof", "trade_date_asof")]):
        lag = (u2[b] - u2[a]).dt.days.dropna()
        lag = lag[lag >= 0]
        w = max(int(np.ceil(lag.quantile(q))), 3)
        row[["KYC", "Bank", "Deposit", "Trade"][s] + "_window_days"] = w
        row[["KYC", "Bank", "Deposit", "Trade"][s] + "_premature_pct"] = round(float((lag > w).mean() * 100), 1)
    bt.append(row)
bt = pd.DataFrame(bt)
p95 = bt[bt["window_rule"] == "p95 (used)"].iloc[0]
check("Backtest: no eventual completer would have been flagged early at the chosen window",
      all(p95[c] == 0 for c in bt.columns if c.endswith("_premature_pct")),
      "; ".join(f"{c.split('_')[0]} {p95[c]}%" for c in bt.columns if c.endswith("_premature_pct")))
mx = bt[bt["window_rule"] == "max"].iloc[0]
same_as_max = all(p95[c] == mx[c] for c in bt.columns if c.endswith("_window_days"))
check("Disclosure: in this synthetic data the p95 window equals the maximum observed lag (0% early-flag rate holds BY CONSTRUCTION)",
      same_as_max, "completion lags are bounded in the generator, so this is not evidence of real-world accuracy; "
                   "on real data p95 would leave ~5% of eventual completers flagged early")

# ------------------------------------------------------------------ 7. internal consistency of scores
fl = res[res["is_flagged"] == 1]
check("Score: flagged scores within 0-100", bool(fl["priority_score"].between(0, 100).all()),
      f"min {fl['priority_score'].min():.1f}, max {fl['priority_score'].max():.1f}")
check("Score: non-flagged have score 0 and band NOT_FLAGGED",
      bool(((res["is_flagged"] == 0) <= ((res["priority_score"] == 0) & (res["priority_band"] == "NOT_FLAGGED"))).all()))
comp = fl[["pts_days_since_registration", "pts_funnel_stage", "pts_inactivity", "pts_support", "pts_activity",
           "pts_prior_transactions"]].sum(axis=1).round(1)
check("Score: components add up to the score", bool((comp - fl["priority_score"]).abs().max() < 0.06))
check("Score: labelled as a heuristic, not a probability",
      set(res["score_type"]) == {"heuristic_priority_score_NOT_a_probability"})
check("Score: component caps respected",
      bool((res["pts_days_since_registration"] <= 10).all() and (res["pts_funnel_stage"] <= 20).all()
           and (res["pts_inactivity"] <= 20).all() and (res["pts_support"] <= 20).all()
           and (res["pts_activity"] <= 10).all() and (res["pts_prior_transactions"] <= 20).all()))

# ------------------------------------------------------------------ 8. relationship to Phase 4 'needs support' flag
p4 = pd.read_csv(ROOT.parent / "data" / "cleaned" / "Cleaned_Support_Tickets.csv")
tc = p4.groupby("user_id").size()
rep_phase4 = set(tc[tc >= 3].index)
rep_engine = set(res.index[res["friction_categories"].str.contains("REPEATED_SUPPORT_ISSUES")])
check("Reconcile: REPEATED_SUPPORT_ISSUES = users with >= 3 tickets (Phase 4 rule)", rep_phase4 == rep_engine,
      f"phase4 {len(rep_phase4)}, engine {len(rep_engine)}")

# ------------------------------------------------------------------ 9. determinism / idempotence
res2 = run_engine(users, tickets, SNAP, cfg, monthly=monthly, watch=watch).set_index("user_id")
check("Determinism: two runs give identical results",
      bool(res[["primary_category", "priority_score", "data_confidence"]].equals(
          res2[["primary_category", "priority_score", "data_confidence"]])))

# ------------------------------------------------------------------ 10. robustness (injected faults, original data untouched)
dirty = users.copy()
dirty = pd.concat([dirty, dirty.iloc[:25]], ignore_index=True)                       # 25 duplicate rows
dirty.loc[dirty.index[:10], "city"] = np.nan                                           # missing city
dirty.loc[dirty.index[10:15], "kyc_date_asof"] = "not-a-date"                          # invalid date
dirty.loc[dirty.index[15:18], "user_id"] = np.nan                                      # missing id
dirty.loc[dirty.index[18:20], "registration_date"] = np.nan                            # missing registration
dirty_t = pd.concat([tickets, tickets.iloc[:15]], ignore_index=True)                   # duplicate tickets
try:
    rd = run_engine(dirty, dirty_t, SNAP, cfg, monthly=monthly, watch=watch)
    dq = rd.attrs["data_quality"]
    check("Robustness: engine runs on dirty input without error", True)
    # 25 duplicate rows were appended; 3 of their originals then lost their user_id (dropped as missing ID), so the
    # surviving copy of those 3 IDs is correctly kept as the first occurrence -> 22 duplicates expected.
    check("Robustness: duplicates removed (25 injected, 3 originals had their ID blanked -> 22 expected)",
          rd["user_id"].is_unique and dq["duplicate_user_rows_dropped"] == 22 and dq["duplicate_ticket_rows_dropped"] == 15,
          f"dropped {dq['duplicate_user_rows_dropped']} duplicate users, {dq['duplicate_ticket_rows_dropped']} duplicate tickets")
    check("Robustness: missing IDs and registration dates dropped, counted not hidden",
          dq["rows_missing_user_id_dropped"] == 3 and dq["rows_missing_registration_date_dropped"] == 2, json.dumps(
              {k: dq[k] for k in ("rows_missing_user_id_dropped", "rows_missing_registration_date_dropped")}))
    check("Robustness: missing city filled 'Unknown'", bool((rd["city"] == "Unknown").sum() >= 8))
    check("Robustness: invalid date treated as not completed (reported)", dq["unparseable_kyc_date_asof"] == 5,
          f"{dq['unparseable_kyc_date_asof']} unparseable KYC dates")
    check("Robustness: no NaN in key output columns",
          not rd[["primary_category", "priority_score", "stage_idx", "is_flagged"]].isna().any().any())
except Exception as exc:                                                                 # pragma: no cover
    check("Robustness: engine runs on dirty input without error", False, repr(exc))
check("Robustness: original source data unchanged by the test (fresh read has same row count)",
      len(pd.read_csv(DATA / "users.csv")) == len(users) == 10000)

# ------------------------------------------------------------------ 11. data confidence disclosure
n_low = int((fl["data_confidence"] == "LOW").sum())
check("Disclosure: LOW-confidence customers are reported, not hidden", n_low > 0,
      f"{n_low:,} of {len(fl):,} flagged ({n_low / len(fl) * 100:.0f}%)")

# ------------------------------------------------------------------ write results
bands = fl["priority_band"].value_counts().to_dict()
summary = {
    "snapshot": SNAP, "customers": int(len(res)), "flagged": int(len(fl)),
    "flagged_pct": round(len(fl) / len(res) * 100, 1),
    "by_primary_category": fl["primary_category"].value_counts().to_dict(),
    "priority_bands": bands, "within_window_not_flagged": int(len(wi)),
    "low_confidence_flagged": n_low, "oracle_primary_category_agreement_pct": round(agree * 100, 3),
    "windows_days": dict(zip(["kyc", "bank", "deposit", "trade"], o_windows)),
    "checks_passed": sum(r["result"] == "PASS" for r in results), "checks_total": len(results),
}
(ROOT / "validation" / "validation_results.json").write_text(json.dumps({"summary": summary, "checks": results,
                                                                         "backtest": bt.to_dict("records")}, indent=2))
bt.to_csv(ROOT / "validation" / "backtest_premature_flag_rates.csv", index=False)
print("\n", json.dumps(summary, indent=2))
print(bt.to_string(index=False))
sys.exit(0 if all(r["result"] == "PASS" for r in results) else 1)
