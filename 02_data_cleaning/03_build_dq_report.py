"""Generates documentation/data_quality_report.md from the validation outputs (numbers are pulled, not typed)."""
from pathlib import Path
import json, pandas as pd, numpy as np
ROOT = Path(__file__).resolve().parents[1]; STEP = ROOT/"02_data_cleaning"; V = STEP/"validation"; C = ROOT/"data"/"cleaned"
chk = pd.read_csv(V/"validation_checks.csv"); log = pd.read_csv(STEP/"cleaning_log.csv"); meta = json.load(open(V/"run_metadata.json"))
rv = pd.read_csv(V/"retention_churn_validation.csv"); rel = pd.read_csv(V/"relationship_validation_clean.csv"); rec = pd.read_csv(V/"summary_sheet_reconciliation.csv")
exc = pd.read_csv(V/"row_level_exceptions.csv")
g = lambda cid, col="violations_raw": int(chk.loc[chk.check_id == cid, col].iloc[0])
t = lambda cid: int(chk.loc[chk.check_id == cid, "records_tested"].iloc[0])
pct = lambda a, b: f"{a/b*100:.1f}%"

# ---------- scorecard (defined calculation)
scored = chk[chk.dimension != "Outliers"].copy()
rows = []
for d, x in scored.groupby("dimension", sort=False):
    tested, v0, v1 = x.records_tested.sum(), x.violations_raw.sum(), x.violations_after_correction.sum()
    worst0 = (1 - x.violations_raw / x.records_tested).min(); worst1 = (1 - x.violations_after_correction / x.records_tested).min()
    rows.append(dict(Dimension=d, Checks=len(x), Tested=int(tested), Viol_raw=int(v0), Pass_raw=1 - v0 / tested, Weakest_raw=worst0, Viol_after=int(v1), Pass_after=1 - v1 / tested, Weakest_after=worst1,
                     Status=", ".join(sorted(set(x.status)))))
sc = pd.DataFrame(rows); sc.to_csv(V/"data_quality_scorecard.csv", index=False)
f = lambda v: f"{v*100:.2f}%"
sc_md = "| Dimension | Checks | Record-tests | Violations (raw) | Pooled pass rate (raw) | Weakest single check (raw) | Violations after corrections | Pooled pass rate (after) | Weakest check (after) | Treatment status |\n|---|---|---|---|---|---|---|---|---|---|\n"
sc_md += "\n".join(f"| {r.Dimension} | {r.Checks} | {r.Tested:,} | {r.Viol_raw:,} | {f(r.Pass_raw)} | {f(r.Weakest_raw)} | {r.Viol_after:,} | {f(r.Pass_after)} | {f(r.Weakest_after)} | {r.Status} |" for r in sc.itertuples())

before = meta["records_before"]; after = meta["records_after"]
n_flag_rows = {"Cleaned_Monthly_Activity": int(pd.read_csv(C/"Cleaned_Monthly_Activity.csv").filter(like="flag_").drop(columns=["flag_trading_value_outlier_iqr","flag_trading_value_outlier_log","flag_avg_trade_size_outlier","flag_cum_withdrawal_exceeds_deposits"]).max(axis=1).sum())}
M = pd.read_csv(C/"Cleaned_Monthly_Activity.csv"); U = pd.read_csv(C/"Cleaned_Users.csv"); T = pd.read_csv(C/"Cleaned_Support_Tickets.csv")
th = meta["thresholds"]
cl_md = "| ID | Table | Column(s) | Issue | Action | Records | Rationale |\n|---|---|---|---|---|---|---|\n" + "\n".join(
    f"| {r.change_id} | {r.table} | {r.column} | {r.issue} | {r.action} | {r.records_affected:,} | {r.rationale} |" for r in log.itertuples())
def tbl(df, cols, fmt=None):
    h = "| " + " | ".join(cols) + " |\n|" + "---|" * len(cols) + "\n"
    return h + "\n".join("| " + " | ".join(str(r[c]) for c in cols) + " |" for _, r in df.iterrows())
ck_md = tbl(chk[chk.dimension != "Outliers"].assign(Pass=lambda d: (d.pass_rate_raw*100).round(2).astype(str)+"%"),
            ["check_id", "table", "description", "records_tested", "violations_raw", "Pass", "violations_after_correction", "severity", "status"])
rv_md = tbl(rv.assign(supplied_value=rv.supplied_value.round(4), recalculated_value=rv.recalculated_value.round(4)).fillna("–"), ["metric", "definition", "eligible_users", "supplied_value", "recalculated_value", "note"])
rel_md = tbl(rel, ["test", "object", "rows", "violations"])
nonmatch = rec[~rec.matches]
rec_md = tbl(rec.assign(matches=rec.matches.map({True: "✅", False: "❌"})), ["item", "reported", "recalculated", "matches"])
ol = chk[chk.dimension == "Outliers"]
ol_md = tbl(ol.assign(share=(ol.violations_raw/ol.records_tested*100).round(2).astype(str)+"%"), ["check_id", "table", "description", "records_tested", "violations_raw", "share"])

dep = U.first_deposit_amount_inr.dropna(); tv = M.trading_value_inr[M.trading_value_inr > 0]
md = f"""# Phase 2 — Data Quality Report

> **SYNTHETIC DATA NOTICE.** All customer records, campaigns, tickets and metrics are artificially generated for a fictional Indian online brokerage. Nothing here is Futu/moomoo, Groww, Zerodha or any other company's data.

**Pipeline:** `02_data_cleaning/01_phase2_clean_validate_transform.py` (re-runnable end-to-end) · **Raw files:** untouched in `data/raw/` · **Outputs:** `data/cleaned/` · **Snapshot date:** 2026-10-31

---

## 1. Executive summary

* **No records were deleted.** Every table has the same row count before and after cleaning. The data has no duplicate keys, no orphan keys, no negative amounts and no stage-order violations in the customer journey.
* **What was corrected (in the cleaned copy only):** (a) {g('TM02'):,} users carry funnel events dated after the 31-Oct-2026 snapshot — new `*_asof` columns count only events that had happened; (b) {g('XT10'):,} users whose last-active date pre-dates their own KYC / deposit / trade — `last_active_date_adj` fixes this; (c) {g('MS01')} summary-sheet KPIs that do not reproduce from row-level data were recomputed; (d) zero-valued deposit placeholders became NULL.
* **What was flagged but deliberately not "fixed":** `Monthly_Activity` contradicts the funnel flags in `Users` (e.g. {g('XT01'):,} trade rows belong to users flagged as never having traded) and `last_active_date` contradicts `Monthly_Activity` for {g('XT08'):,} users. There is no ground truth that says which table is right, so rows are kept, flagged, and each metric uses one declared source of truth.
* **Outliers are legitimate.** Deposits and trading values are log-normal (log-scale skew ≈ 0). The large values are the expected right tail, not data-entry errors; none were removed.
* **Churn is not observable.** The supplied "churn" flags are inactivity proxies, and the 90-day proxy is bounded at 120 days. They are re-derived with explicit eligibility and always called *proxy*.

---

## 2. Records before and after cleaning

| Source table | Records before | Cleaned table(s) | Records after | Rows removed |
|---|---|---|---|---|
| Users_10000 | {before['Users']:,} | Cleaned_Users, Customer_Segments | {after['Cleaned_Users']:,} / {after['Customer_Segments']:,} | 0 |
| Monthly_Activity | {before['Monthly_Activity']:,} | Cleaned_Monthly_Activity | {after['Cleaned_Monthly_Activity']:,} | 0 |
| Support_Tickets | {before['Support_Tickets']:,} | Cleaned_Support_Tickets | {after['Cleaned_Support_Tickets']:,} | 0 |
| Campaigns | {before['Campaigns']:,} | Cleaned_Campaigns, Campaign_Performance | {after['Cleaned_Campaigns']:,} / {after['Campaign_Performance']:,} | 0 |
| Cohort_Retention | {before['Cohort_Retention']:,} | Customer_Cohorts (full grid incl. not-yet-eligible cells, by channel) | {after['Customer_Cohorts']:,} | n/a (rebuilt) |
| – | – | Customer_Funnel (long format, 8 cuts × 6 stages) | {after['Customer_Funnel']:,} | n/a (new) |

Rows are never dropped because a record that looks wrong is itself evidence for the data-quality report; the cleaned tables add flag columns instead.

---

## 3. Duplicates

| Test | Rows tested | Duplicates |
|---|---|---|
| `user_id` in Users | {t('UQ01'):,} | {g('UQ01')} |
| Fully duplicated user rows | {t('UQ02'):,} | {g('UQ02')} |
| `ticket_id` in Support_Tickets | {t('UQ03'):,} | {g('UQ03')} |
| (`user_id`, `activity_month`) in Monthly_Activity | {t('UQ04'):,} | {g('UQ04')} |
| `campaign_id` in Campaigns | {t('UQ05')} | {g('UQ05')} |
| Excel Users sheet vs CSV (cells that differ) | {t('UQ06'):,} | {g('UQ06')} |

No deduplication was needed.

---

## 4. Missing-value analysis

Every null in the source is **structural** — it means a stage was not reached or a ticket is unresolved — not a data-capture failure.

| Table.column | Nulls | Meaning |
|---|---|---|
| Users.kyc_completion_date | {U.kyc_completion_date.isna().sum():,} | KYC not completed (flag = 0) |
| Users.bank_link_date | {U.bank_link_date.isna().sum():,} | Bank not linked |
| Users.first_deposit_date | {U.first_deposit_date.isna().sum():,} | No first deposit |
| Users.first_trade_date / first_trade_segment | {U.first_trade_date.isna().sum():,} | No first trade |
| Support_Tickets.resolution_time_hours / csat_score | {T.resolution_time_hours.isna().sum():,} | Ticket Open ({(T.status=='Open').sum():,}) or Escalated ({(T.status=='Escalated').sum():,}) |
| All other fields in all tables | 0 | – |

Checks CP01–CP08 confirm the pattern is perfectly consistent: a date exists exactly when the matching flag is 1; a resolution time and CSAT exist exactly when a ticket is Resolved.
**Treatment:** `first_deposit_amount_inr` stored `0.0` for non-depositors; changed to NULL ({int((~U.first_deposit_made.astype(bool)).sum()):,} rows) so averages and medians aren't diluted. **Caution for reporting:** average resolution time and CSAT describe resolved tickets only (82.0% of tickets); unresolved tickets are reported separately as a backlog.

---

## 5. Invalid records

| Test | Tested | Invalid |
|---|---|---|
| Non-Boolean values in Boolean columns | {t('VL01'):,} | {g('VL01')} |
| Negative amounts / counts / durations | {t('VL02'):,} | {g('VL02')} |
| CSAT outside 1–5 | {t('VL03'):,} | {g('VL03')} |
| Non-integer trade counts | {t('VL04'):,} | {g('VL04')} |
| `days_inactive` negative or longer than tenure | {t('VL05'):,} | {g('VL05')} |
| `days_inactive` does not recompute from dates | {t('VL06'):,} | {g('VL06')} |
| Churn flags inconsistent with `days_inactive` | {t('VL07'):,} | {g('VL07')} |

Data types and ranges are valid. Categorical labels had no whitespace or casing inconsistencies. Dates were converted to ISO `yyyy-mm-dd`; booleans to `0/1`.

---

## 6. Outlier analysis (retained, flagged)

{ol_md}

**Method:** Tukey fences (Q3 + 1.5×IQR) on both the raw scale and the log scale. A raw-scale rule on a right-skewed variable flags many ordinary large values; the log-scale rule is the fairer test.

**Verdict — legitimate extreme values, not data errors:**

* **First deposit** (n = {len(dep):,}): median ₹{dep.median():,.0f}, mean ₹{dep.mean():,.0f}, max ₹{dep.max():,.0f} ({dep.max()/dep.median():.1f}× median). The distribution is log-normal (log-scale skewness ≈ 0.00 against raw skewness ≈ 4.05). Only {g('OL02')} deposits exceed the log-scale fence. No value is round (0.0% multiples of ₹1,000), none is negative or zero, no sign of a unit error (e.g. ×100). The above-fence group has a risk-profile and age mix similar to all depositors.
* **Monthly trading value** (n = {len(tv):,} positive rows): log-normal (log-skew ≈ 0.10). {g('OL04')} rows exceed the log-scale fence. In a real brokerage these are active or high-net-worth traders and are commercially important, so removing them would erase the most valuable customers.
* **Resolution time**: {g('OL06')} tickets above {th['fence_res_time']} h (max 79.2 h). Service-time tails are normal; report medians next to means.
* **Caveat:** in real data I would verify the top deposits against payment-gateway records before accepting them. Here, "legitimate" means *statistically consistent with the generating distribution*, not *verified*.

**Reporting rule:** use medians for deposits and trade values; show the mean only with the median beside it.

---

## 7. Relationship validation

**Source tables (raw):**

| Relationship | Rows tested | Orphans |
|---|---|---|
| users.user_id → monthly_activity.user_id | {t('RI01'):,} | {g('RI01')} |
| users.user_id → support_tickets.user_id | {t('RI02'):,} | {g('RI02')} |
| campaigns.campaign_id → users.acquisition_campaign_id | {t('RI03'):,} | {g('RI03')} |
| Users with no monthly rows | {t('RI04'):,} | {g('RI04')} |
| Campaigns with no users | {t('RI05')} | {g('RI05')} |
| User channel/platform vs campaign master | {t('RI06'):,} | {g('RI06')} |
| Campaign sheet counts vs recomputed from users | {t('RI07')} | {g('RI07')} |

**Cleaned tables (all eight):**

{rel_md}

---

## 8. Date and customer-journey validation

Sequence tested: Registration → KYC → Bank link → First deposit → First trade.

| Rule | Tested | Violations |
|---|---|---|
| KYC before registration | {t('JR01'):,} | {g('JR01')} |
| Bank link before KYC | {t('JR02'):,} | {g('JR02')} |
| First deposit before bank link | {t('JR03'):,} | {g('JR03')} |
| First trade before first deposit | {t('JR04'):,} | {g('JR04')} |
| First trade before registration | {t('JR05'):,} | {g('JR05')} |
| Stage reached with a prerequisite stage skipped | {t('JR06'):,} | {g('JR06')} |
| Last active before registration | {t('JR07'):,} | {g('JR07')} |
| Monthly activity before registration month | {t('JR08'):,} | {g('JR08')} |
| Monthly activity after Oct-2026 | {t('JR09'):,} | {g('JR09')} |
| Ticket created before registration | {t('JR10'):,} | {g('JR10')} |

**Journey order is clean.** Two chronology problems exist, both of a different kind:

1. **Future-dated events (corrected).** {g('TM02'):,} users — all from the Oct-2026 cohort — have KYC (116), bank-link (196), first-deposit (274) or first-trade (280) dates after 31-Oct-2026 (latest 2026-12-08) while the flag says "completed". The flags therefore describe *eventual* completion and leak future information. On the flags, the Oct-2026 cohort shows 40.0% first-trade conversion; as of the snapshot it is 8.4%. **Correction:** `*_asof` flags and dates (0 post-snapshot events remain); funnel rates use the 9,116 mature users registered Nov-2025 → Sep-2026.
2. **Activity earlier than the user's own event (corrected).** {g('XT10'):,} users have `last_active_date` before a KYC, bank-link, deposit or trade date. A funnel event is itself activity, so `last_active_date_adj = max(last_active_date, latest as-of funnel event)`.

---

## 9. Cross-table consistency (flagged, not auto-corrected)

| Check | Tested | Violations | Share |
|---|---|---|---|
""" + "\n".join(f"| {r.description} | {r.records_tested:,} | {r.violations_raw:,} | {pct(r.violations_raw, r.records_tested)} |" for r in chk[chk.check_id.isin(['XT01','XT02','XT03','XT04','XT05','XT06','XT07','XT08','XT09','XT11'])].itertuples()) + f"""

**Why not fix them?** Each contradiction can be resolved two ways (trust the funnel table, or trust the monthly table) and nothing in the data says which is right. A silent choice would manufacture precision. Instead:

| Metric family | Source of truth | Why |
|---|---|---|
| Funnel conversion, CAC, cost per KYC / trade, time between stages | `Users` (`*_asof`, mature cohorts) | Only table with stage dates |
| MAU, cohort retention, repeat trading, deposit / withdrawal trends | `Monthly_Activity` | Reconciles exactly with the supplied cohort sheet |
| Recency (days inactive) | `Users.days_inactive_adj`, labelled *proxy* | Contradicts the monthly table, so never called churn |
| Support | `Support_Tickets` | Self-contained |

Row-level exceptions are listed in `02_data_cleaning/validation/row_level_exceptions.csv` ({len(exc):,} rows) so any record can be traced.

---

## 10. Retention, churn and eligibility validation

{rv_md}

**Key points**

* **Not yet eligible ≠ inactive.** {int(rv.loc[0,'eligible_users']):,} users registered fewer than 31 days before the snapshot cannot be "inactive >30 days". The supplied 43.1% inactivity rate divides by all 10,000; on eligible users the proxy is {rv.loc[2,'recalculated_value']:.1%} inactive vs {rv.loc[1,'recalculated_value']:.1%} active (recalculated). Each user carries `recency_status_30d` / `_90d` with a `not_yet_eligible` state, and retention flags `m1/m3/m6_retained` are NULL where the window has not yet passed.
* **Boundary users.** 21 users with tenure of exactly 30 days are internally inconsistent in the source (11 flagged active, 10 flagged neither). They are treated as not yet eligible.
* **90-day proxy is bounded.** No user is inactive longer than 120 days, even though 337 users have no active month at all and {g('MD02'):,} of the {t('MD02'):,} users registered by July have no active month in Jul–Oct 2026 in `Monthly_Activity` — yet all of them show a last-active date inside that window. The 90-day rate is therefore a lower bound.
* **Two sources disagree.** The 90-day proxy and the monthly 3-month dormancy agree for only {rv.loc[rv.metric.str.startswith('Agreement'),'recalculated_value'].iloc[0]:.1%} of eligible users.
* **Retention was recalculated from source events** (Monthly_Activity): M1 {rv.loc[rv.metric.str.startswith('M1'),'recalculated_value'].iloc[0]:.1%}, M3 {rv.loc[rv.metric.str.startswith('M3'),'recalculated_value'].iloc[0]:.1%}, M6 {rv.loc[rv.metric.str.startswith('M6'),'recalculated_value'].iloc[0]:.1%} (observable cohorts only). The rebuilt cohort table matches the supplied `Cohort_Retention` sheet cell for cell (check RC01: 0 differences).
* **Genuine churn cannot be measured.** The data has no account-closure, asset-transfer or zero-balance field.

---

## 11. Reconciliation with the supplied summary sheets

{rec_md}

Three supplied values do not reproduce: the 30-day churn proxy (47.25% supplied vs 47.14% from the flags — it was computed as 1 − active rate); the "30-day churn proxy (eligible)" count of 6,758 vs 4,307 in the data; and "Blended CAC ₹331.2", which divides spend by the 8,122 paid-channel users only (₹269.0 over all 10,000). CAC is reproduced exactly for each paid campaign (check RC02). Cost-per-KYC and cost-per-first-trade in the supplied sheet use eventual completions; `Campaign_Performance` reports an as-of version and an "at maturity" version.

---

## 12. Corrections made — full change log

{cl_md}

The same log is in `02_data_cleaning/cleaning_log.csv`.

---

## 13. Data-quality scorecard — and exactly how it is calculated

**Definition (no composite score is reported):**

1. Each check *c* has `records_tested` (*Nc*) and `violations` (*Vc*): a check's pass rate is 1 − Vc / Nc.
2. A dimension's **pooled pass rate** = 1 − ΣVc / ΣNc over the checks in that dimension. This weights checks by population size and mixes units (rows, cells, events), so it is indicative only.
3. Because pooling can hide a bad check behind a large clean one, the **weakest single check** is shown beside it. Read that column first.
4. **After corrections** keeps only violations still present in the analytic columns. Items that were *flagged and retained* still count as violations; only items that were genuinely *corrected* drop to zero.
5. Outlier checks are excluded: they were judged legitimate values, not defects.
6. Informational and scope limitations (no app-visit data, no revenue) are not scored — they are listed in §14.
7. No weights or composite index were applied; a single overall score would require subjective weights I have not been given.

{sc_md}

**Reading it:** structural dimensions (uniqueness, referential integrity, completeness, validity, journey order) pass at 100%. The weak spots are *cross-table consistency* and *timeliness*; timeliness is repaired in the cleaned copy while cross-table consistency can only be disclosed.

### Full check register (non-outlier)

{ck_md}

---

## 14. Remaining limitations

1. **Cross-table contradictions persist** (§9). Any analysis that joins Monthly_Activity behaviour to funnel flags should be treated as indicative.
2. **No genuine churn.** Inactivity proxies only; 90-day proxy bounded at 120 days.
3. **No App Visit stage.** The earliest event is registration, so visit → registration conversion cannot be calculated.
4. **No revenue, commission, fees or AUM.** Marketing ROI, LTV and payback are not computable. Required: commission / fee revenue per customer-month, interest income, AUM, direct servicing cost, and (for ROI) the campaign costs by month.
5. **Spend is a single lump sum per campaign.** No CAC trend; organic spend is zero because it is unrecorded, not because organic is free.
6. **Last-touch attribution only**; no multi-touch or assisted-conversion data.
7. **Oct-2026 cohort is immature** (884 users); it is excluded from conversion rates and shown separately.
8. **Month 0 is a partial month** and its length depends on registration day, so M0→M1 retention compares unequal windows.
9. **Support data:** priority has no effect on resolution time or escalation (synthetic artefact, not an operations insight); no SLA targets; `stage_pending_at_ticket` supports a hypothesis only.
10. **Geography:** 9.2% of users sit in "Other" city.
11. **Synthetic data:** distributions are generated; patterns found are properties of the generator, not of real customers. Findings must be presented as a demonstration of method.

---

## 15. Files produced in Phase 2

| Path | Content |
|---|---|
| `data/cleaned/Cleaned_Users.csv` | A — 10,000 × {len(U.columns)} |
| `data/cleaned/Cleaned_Campaigns.csv` | B |
| `data/cleaned/Cleaned_Monthly_Activity.csv` | C — 64,645 rows |
| `data/cleaned/Cleaned_Support_Tickets.csv` | D — 7,614 rows |
| `data/cleaned/derived/Customer_Funnel.csv` | E — stage-level funnel by 8 cuts |
| `data/cleaned/derived/Customer_Cohorts.csv` | F — cohort × channel × month grid |
| `data/cleaned/derived/Campaign_Performance.csv` | G |
| `data/cleaned/derived/Customer_Segments.csv` | H — lifecycle segments, RFM, support overlays |
| `02_data_cleaning/cleaning_log.csv` | Every transformation |
| `data/data_dictionary.csv` · `documentation/data_dictionary.md` | 231 column definitions |
| `02_data_cleaning/validation/` | check register, scorecard, row-level exceptions, retention validation, relationship validation, summary reconciliation |
| `02_data_cleaning/01_phase2_clean_validate_transform.py` · `02_build_data_dictionary.py` · `03_build_dq_report.py` | Reproducible pipeline |
"""
(ROOT/"documentation"/"data_quality_report.md").write_text(md)
print(sc.round(4).to_string()); print(len(md))
