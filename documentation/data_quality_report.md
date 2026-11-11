# Phase 2 — Data Quality Report

> **SYNTHETIC DATA NOTICE.** All customer records, campaigns, tickets and metrics are artificially generated for a fictional Indian online brokerage. Nothing here is Futu/moomoo, Groww, Zerodha or any other company's data.

**Pipeline:** `02_data_cleaning/01_phase2_clean_validate_transform.py` (re-runnable end-to-end) · **Raw files:** untouched in `data/raw/` · **Outputs:** `data/cleaned/` · **Snapshot date:** 2026-10-31

---

## 1. Executive summary

* **No records were deleted.** Every table has the same row count before and after cleaning. The data has no duplicate keys, no orphan keys, no negative amounts and no stage-order violations in the customer journey.
* **What was corrected (in the cleaned copy only):** (a) 388 users carry funnel events dated after the 31-Oct-2026 snapshot — new `*_asof` columns count only events that had happened; (b) 733 users whose last-active date pre-dates their own KYC / deposit / trade — `last_active_date_adj` fixes this; (c) 3 summary-sheet KPIs that do not reproduce from row-level data were recomputed; (d) zero-valued deposit placeholders became NULL.
* **What was flagged but deliberately not "fixed":** `Monthly_Activity` contradicts the funnel flags in `Users` (e.g. 5,640 trade rows belong to users flagged as never having traded) and `last_active_date` contradicts `Monthly_Activity` for 6,336 users. There is no ground truth that says which table is right, so rows are kept, flagged, and each metric uses one declared source of truth.
* **Outliers are legitimate.** Deposits and trading values are log-normal (log-scale skew ≈ 0). The large values are the expected right tail, not data-entry errors; none were removed.
* **Churn is not observable.** The supplied "churn" flags are inactivity proxies, and the 90-day proxy is bounded at 120 days. They are re-derived with explicit eligibility and always called *proxy*.

---

## 2. Records before and after cleaning

| Source table | Records before | Cleaned table(s) | Records after | Rows removed |
|---|---|---|---|---|
| Users_10000 | 10,000 | Cleaned_Users, Customer_Segments | 10,000 / 10,000 | 0 |
| Monthly_Activity | 64,645 | Cleaned_Monthly_Activity | 64,645 | 0 |
| Support_Tickets | 7,614 | Cleaned_Support_Tickets | 7,614 | 0 |
| Campaigns | 10 | Cleaned_Campaigns, Campaign_Performance | 10 / 10 | 0 |
| Cohort_Retention | 78 | Customer_Cohorts (full grid incl. not-yet-eligible cells, by channel) | 1,008 | n/a (rebuilt) |
| – | – | Customer_Funnel (long format, 8 cuts × 6 stages) | 312 | n/a (new) |

Rows are never dropped because a record that looks wrong is itself evidence for the data-quality report; the cleaned tables add flag columns instead.

---

## 3. Duplicates

| Test | Rows tested | Duplicates |
|---|---|---|
| `user_id` in Users | 10,000 | 0 |
| Fully duplicated user rows | 10,000 | 0 |
| `ticket_id` in Support_Tickets | 7,614 | 0 |
| (`user_id`, `activity_month`) in Monthly_Activity | 64,645 | 0 |
| `campaign_id` in Campaigns | 10 | 0 |
| Excel Users sheet vs CSV (cells that differ) | 250,000 | 0 |

No deduplication was needed.

---

## 4. Missing-value analysis

Every null in the source is **structural** — it means a stage was not reached or a ticket is unresolved — not a data-capture failure.

| Table.column | Nulls | Meaning |
|---|---|---|
| Users.kyc_completion_date | 2,925 | KYC not completed (flag = 0) |
| Users.bank_link_date | 3,774 | Bank not linked |
| Users.first_deposit_date | 5,214 | No first deposit |
| Users.first_trade_date / first_trade_segment | 6,184 | No first trade |
| Support_Tickets.resolution_time_hours / csat_score | 1,371 | Ticket Open (892) or Escalated (479) |
| All other fields in all tables | 0 | – |

Checks CP01–CP08 confirm the pattern is perfectly consistent: a date exists exactly when the matching flag is 1; a resolution time and CSAT exist exactly when a ticket is Resolved.
**Treatment:** `first_deposit_amount_inr` stored `0.0` for non-depositors; changed to NULL (5,214 rows) so averages and medians aren't diluted. **Caution for reporting:** average resolution time and CSAT describe resolved tickets only (82.0% of tickets); unresolved tickets are reported separately as a backlog.

---

## 5. Invalid records

| Test | Tested | Invalid |
|---|---|---|
| Non-Boolean values in Boolean columns | 70,000 | 0 |
| Negative amounts / counts / durations | 276,194 | 0 |
| CSAT outside 1–5 | 6,243 | 0 |
| Non-integer trade counts | 64,645 | 0 |
| `days_inactive` negative or longer than tenure | 10,000 | 0 |
| `days_inactive` does not recompute from dates | 10,000 | 0 |
| Churn flags inconsistent with `days_inactive` | 20,000 | 0 |

Data types and ranges are valid. Categorical labels had no whitespace or casing inconsistencies. Dates were converted to ISO `yyyy-mm-dd`; booleans to `0/1`.

---

## 6. Outlier analysis (retained, flagged)

| check_id | table | description | records_tested | violations_raw | share |
|---|---|---|---|---|---|
| OL01 | Users | First deposit above Tukey fence on raw scale (Rs 22,944) | 4786 | 321 | 6.71% |
| OL02 | Users | First deposit above Tukey fence on log scale (Rs 62,936) | 4786 | 17 | 0.36% |
| OL03 | Monthly_Activity | Monthly trading value above Tukey fence on raw scale (Rs 30,365) | 19718 | 1555 | 7.89% |
| OL04 | Monthly_Activity | Monthly trading value above Tukey fence on log scale (Rs 105,451) | 19718 | 70 | 0.36% |
| OL05 | Monthly_Activity | Average trade size above log-scale fence (Rs 35,759) | 19718 | 76 | 0.39% |
| OL06 | Support_Tickets | Resolution time above Tukey fence (27.9 h) | 6243 | 169 | 2.71% |

**Method:** Tukey fences (Q3 + 1.5×IQR) on both the raw scale and the log scale. A raw-scale rule on a right-skewed variable flags many ordinary large values; the log-scale rule is the fairer test.

**Verdict — legitimate extreme values, not data errors:**

* **First deposit** (n = 4,786): median ₹6,519, mean ₹9,254, max ₹135,951 (20.9× median). The distribution is log-normal (log-scale skewness ≈ 0.00 against raw skewness ≈ 4.05). Only 17 deposits exceed the log-scale fence. No value is round (0.0% multiples of ₹1,000), none is negative or zero, no sign of a unit error (e.g. ×100). The above-fence group has a risk-profile and age mix similar to all depositors.
* **Monthly trading value** (n = 19,718 positive rows): log-normal (log-skew ≈ 0.10). 70 rows exceed the log-scale fence. In a real brokerage these are active or high-net-worth traders and are commercially important, so removing them would erase the most valuable customers.
* **Resolution time**: 169 tickets above 27.85 h (max 79.2 h). Service-time tails are normal; report medians next to means.
* **Caveat:** in real data I would verify the top deposits against payment-gateway records before accepting them. Here, "legitimate" means *statistically consistent with the generating distribution*, not *verified*.

**Reporting rule:** use medians for deposits and trade values; show the mean only with the median beside it.

---

## 7. Relationship validation

**Source tables (raw):**

| Relationship | Rows tested | Orphans |
|---|---|---|
| users.user_id → monthly_activity.user_id | 64,645 | 0 |
| users.user_id → support_tickets.user_id | 7,614 | 0 |
| campaigns.campaign_id → users.acquisition_campaign_id | 10,000 | 0 |
| Users with no monthly rows | 10,000 | 0 |
| Campaigns with no users | 10 | 0 |
| User channel/platform vs campaign master | 10,000 | 0 |
| Campaign sheet counts vs recomputed from users | 30 | 0 |

**Cleaned tables (all eight):**

| test | object | rows | violations |
|---|---|---|---|
| primary key unique | Cleaned_Users.user_id | 10000 | 0 |
| primary key unique | Cleaned_Campaigns.campaign_id | 10 | 0 |
| primary key unique | Cleaned_Support_Tickets.ticket_id | 7614 | 0 |
| primary key unique | Customer_Segments.user_id | 10000 | 0 |
| primary key unique | Campaign_Performance.campaign_id | 10 | 0 |
| primary key unique | Cleaned_Monthly_Activity (user_id, activity_month) | 64645 | 0 |
| primary key unique | Customer_Cohorts (registration_month, channel, months_since_registration) | 1008 | 0 |
| foreign key (no orphans) | Cleaned_Monthly_Activity.user_id | 64645 | 0 |
| foreign key (no orphans) | Cleaned_Support_Tickets.user_id | 7614 | 0 |
| foreign key (no orphans) | Cleaned_Users.acquisition_campaign_id | 10000 | 0 |
| foreign key (no orphans) | Customer_Segments.user_id | 10000 | 0 |
| foreign key (no orphans) | Campaign_Performance.campaign_id | 10 | 0 |
| foreign key (no orphans) | Customer_Cohorts.acquisition_channel | 1008 | 0 |
| foreign key (no orphans) | Customer_Funnel (campaign cut).cut_value | 60 | 0 |

---

## 8. Date and customer-journey validation

Sequence tested: Registration → KYC → Bank link → First deposit → First trade.

| Rule | Tested | Violations |
|---|---|---|
| KYC before registration | 7,075 | 0 |
| Bank link before KYC | 6,226 | 0 |
| First deposit before bank link | 4,786 | 0 |
| First trade before first deposit | 3,816 | 0 |
| First trade before registration | 3,816 | 0 |
| Stage reached with a prerequisite stage skipped | 10,000 | 0 |
| Last active before registration | 10,000 | 0 |
| Monthly activity before registration month | 64,645 | 0 |
| Monthly activity after Oct-2026 | 64,645 | 0 |
| Ticket created before registration | 7,614 | 0 |

**Journey order is clean.** Two chronology problems exist, both of a different kind:

1. **Future-dated events (corrected).** 388 users — all from the Oct-2026 cohort — have KYC (116), bank-link (196), first-deposit (274) or first-trade (280) dates after 31-Oct-2026 (latest 2026-12-08) while the flag says "completed". The flags therefore describe *eventual* completion and leak future information. On the flags, the Oct-2026 cohort shows 40.0% first-trade conversion; as of the snapshot it is 8.4%. **Correction:** `*_asof` flags and dates (0 post-snapshot events remain); funnel rates use the 9,116 mature users registered Nov-2025 → Sep-2026.
2. **Activity earlier than the user's own event (corrected).** 733 users have `last_active_date` before a KYC, bank-link, deposit or trade date. A funnel event is itself activity, so `last_active_date_adj = max(last_active_date, latest as-of funnel event)`.

---

## 9. Cross-table consistency (flagged, not auto-corrected)

| Check | Tested | Violations | Share |
|---|---|---|---|
| Monthly trade rows for users flagged first_trade_made=False | 19,718 | 5,640 | 28.6% |
| Trade rows in a month earlier than the user's first-trade month | 14,078 | 2,242 | 15.9% |
| Monthly deposit rows for users flagged first_deposit_made=False | 5,680 | 2,613 | 46.0% |
| Deposit rows in a month earlier than the first-deposit month | 3,067 | 361 | 11.8% |
| Withdrawal rows for users who never made a first deposit | 3,895 | 1,818 | 46.7% |
| first_trade_made=True but no trade in Monthly_Activity | 3,816 | 114 | 3.0% |
| first_deposit_made=True but no deposit in Monthly_Activity | 4,786 | 2,548 | 53.2% |
| Month of last_active_date differs from last active month in Monthly_Activity | 10,000 | 6,336 | 63.4% |
| Active monthly rows after the month of last_active_date | 35,067 | 3,180 | 9.1% |
| Cumulative withdrawals exceed cumulative deposits in a user-month (informational) | 64,645 | 11,557 | 17.9% |

**Why not fix them?** Each contradiction can be resolved two ways (trust the funnel table, or trust the monthly table) and nothing in the data says which is right. A silent choice would manufacture precision. Instead:

| Metric family | Source of truth | Why |
|---|---|---|
| Funnel conversion, CAC, cost per KYC / trade, time between stages | `Users` (`*_asof`, mature cohorts) | Only table with stage dates |
| MAU, cohort retention, repeat trading, deposit / withdrawal trends | `Monthly_Activity` | Reconciles exactly with the supplied cohort sheet |
| Recency (days inactive) | `Users.days_inactive_adj`, labelled *proxy* | Contradicts the monthly table, so never called churn |
| Support | `Support_Tickets` | Self-contained |

Row-level exceptions are listed in `02_data_cleaning/validation/row_level_exceptions.csv` (26,451 rows) so any record can be traced.

---

## 10. Retention, churn and eligibility validation

| metric | definition | eligible_users | supplied_value | recalculated_value | note |
|---|---|---|---|---|---|
| Users not yet eligible for 30-day measurement | tenure < 31 days | 884 | – | 884.0 | Supplied sheets treat tenure<30 as ineligible; 21 boundary users (tenure=30) were inconsistent |
| 30-day active rate | days since last activity <= 30 | 9116 | 0.5275 | 0.54 | Recalculated after lifting last_active_date to the latest funnel event |
| 30-day inactivity proxy rate | days since last activity > 30 | 9116 | 0.4714 | 0.46 | Proxy only - not churn |
| 30-day inactivity proxy rate (supplied flag, all users) | churned_30d_proxy over 10,000 | 10000 | 0.4307 | 0.46 | Supplied rate on all users mixes in users too new to be inactive |
| Users not yet eligible for 90-day measurement | tenure < 91 days | 2534 | – | 2534.0 | Registered on/after 2026-08-01 |
| 90-day inactivity proxy rate | days since last activity > 90 | 7466 | 0.1515 | 0.1487 | TRUNCATED: max observable inactivity is 120 days; true long-run inactivity is higher |
| Maximum days inactive observed | max(days_inactive_as_of_snapshot) | 10000 | – | 120.0 | No user is inactive longer than 120 days even though Nov-2025 cohorts have 12 months of history: the 90-day proxy is bounded |
| 3-month dormancy (monthly source) | no active month in Aug-Oct 2026 | 7434 | – | 0.2195 | Event-based; registered <= Jul-2026 |
| Agreement: 90-day proxy vs 3-month dormancy | share of users where both agree (users eligible for both) | 7434 | – | 0.7046 | Low agreement = the two sources describe different things |
| M1 retention (monthly source) | active in calendar month 1 after registration month | 9116 | – | 0.6758 | Month 0 is a partial month |
| M3 retention (monthly source) | active in calendar month 3 after registration month | 7434 | – | 0.5601 | Month 0 is a partial month |
| M6 retention (monthly source) | active in calendar month 6 after registration month | 4955 | – | 0.4071 | Month 0 is a partial month |
| Users never active in any monthly row | no active_in_month=True | 337 | – | 337.0 | Not necessarily churn - never engaged |

**Key points**

* **Not yet eligible ≠ inactive.** 884 users registered fewer than 31 days before the snapshot cannot be "inactive >30 days". The supplied 43.1% inactivity rate divides by all 10,000; on eligible users the proxy is 46.0% inactive vs 54.0% active (recalculated). Each user carries `recency_status_30d` / `_90d` with a `not_yet_eligible` state, and retention flags `m1/m3/m6_retained` are NULL where the window has not yet passed.
* **Boundary users.** 21 users with tenure of exactly 30 days are internally inconsistent in the source (11 flagged active, 10 flagged neither). They are treated as not yet eligible.
* **90-day proxy is bounded.** No user is inactive longer than 120 days, even though 337 users have no active month at all and 926 of the 7,434 users registered by July have no active month in Jul–Oct 2026 in `Monthly_Activity` — yet all of them show a last-active date inside that window. The 90-day rate is therefore a lower bound.
* **Two sources disagree.** The 90-day proxy and the monthly 3-month dormancy agree for only 70.5% of eligible users.
* **Retention was recalculated from source events** (Monthly_Activity): M1 67.6%, M3 56.0%, M6 40.7% (observable cohorts only). The rebuilt cohort table matches the supplied `Cohort_Retention` sheet cell for cell (check RC01: 0 differences).
* **Genuine churn cannot be measured.** The data has no account-closure, asset-transfer or zero-balance field.

---

## 11. Reconciliation with the supplied summary sheets

| item | reported | recalculated | matches |
|---|---|---|---|
| Analysis: KYC rate | 0.7075 | 0.7075 | ✅ |
| Analysis: bank-link rate | 0.6226 | 0.6226 | ✅ |
| Analysis: first-deposit rate | 0.4786 | 0.4786 | ✅ |
| Analysis: first-trade rate | 0.3816 | 0.3816 | ✅ |
| Analysis: 30d active rate | 0.5275 | 0.5275 | ✅ |
| Analysis: 30d churn proxy | 0.4725 | 0.4714 | ❌ |
| Analysis: spend | 2690000.0 | 2690000.0 | ✅ |
| Analysis: blended CAC (all users) | 331.2 | 269.0 | ❌ |
| Analysis: tickets | 7614.0 | 7614.0 | ✅ |
| Analysis: avg resolution h | 10.89 | 10.8884 | ✅ |
| Analysis: CSAT | 3.83 | 3.8267 | ✅ |
| Funnel: KYC | 7075.0 | 7075.0 | ✅ |
| Funnel: bank | 6226.0 | 6226.0 | ✅ |
| Funnel: deposit | 4786.0 | 4786.0 | ✅ |
| Funnel: trade | 3816.0 | 3816.0 | ✅ |
| Funnel: active 30d | 4820.0 | 4820.0 | ✅ |
| Funnel: churn proxy count | 6758.0 | 4307.0 | ❌ |

Three supplied values do not reproduce: the 30-day churn proxy (47.25% supplied vs 47.14% from the flags — it was computed as 1 − active rate); the "30-day churn proxy (eligible)" count of 6,758 vs 4,307 in the data; and "Blended CAC ₹331.2", which divides spend by the 8,122 paid-channel users only (₹269.0 over all 10,000). CAC is reproduced exactly for each paid campaign (check RC02). Cost-per-KYC and cost-per-first-trade in the supplied sheet use eventual completions; `Campaign_Performance` reports an as-of version and an "at maturity" version.

---

## 12. Corrections made — full change log

| ID | Table | Column(s) | Issue | Action | Records | Rationale |
|---|---|---|---|---|---|---|
| CL01 | All | categorical columns | Whitespace / case inconsistency in category labels | Trimmed and collapsed whitespace; labels left in source casing | 0 | Audit found labels already consistent (0 changes). Step retained so the pipeline is repeatable on new extracts. |
| CL02 | Campaigns | channel_group, is_paid, spend_basis | No grouping of channels; organic CAC would show as 0 (misleading) | Added analyst-defined channel_group and is_paid; organic left with no CAC in downstream tables | 10 | Organic activity has hidden costs (content, SEO, brand) that the data does not record, so CAC=0 is not 'free acquisition'. |
| CL03 | Users | first_deposit_amount_inr | 0.0 used as placeholder for 'no deposit' | Set to NULL when no deposit was made | 5,214 | A zero would pull down averages and medians; NULL makes the 'not funded' state explicit. |
| CL04 | Users | kyc/bank/deposit/trade _asof and _date_asof | Completion flags include events dated after the 2026-10-31 snapshot (future information) | Added *_asof flags and *_date_asof dates counting only events on/before snapshot; original columns retained untouched | 388 | Prevents the Oct-2026 cohort from showing conversion that had not yet happened (first-trade 40.0% on flags vs 8.4% as-of). |
| CL05 | Users | cohort_maturity, funnel_mature, eligible_30d, eligible_90d | No explicit eligibility for conversion or inactivity metrics | Added maturity and eligibility columns (mature = registered before 2026-10; eligible_30d = tenure>=31 d; eligible_90d = tenure>=91 d) | 884 | Separates 'not yet eligible' from 'genuinely inactive'. 21 users with tenure=30 d are inconsistent in the source flag and are treated as not yet eligible. |
| CL06 | Users | last_active_date_adj, days_inactive_adj | last_active_date earlier than the user's own KYC/bank/deposit/trade date | last_active_date_adj = max(last_active_date, latest as-of funnel event); days_inactive_adj recomputed from it | 733 | A user cannot be last active before completing an action; the funnel event is itself proof of activity. Original columns kept. |
| CL07 | Users | inactive_30d_adj, inactive_90d_adj, active_30d_adj, recency_status_30d/90d | Churn proxies computed on all users incl. those too new to be inactive; 90-day proxy truncated at 120 days | Re-derived from days_inactive_adj with explicit eligibility; ineligible users get NULL and status 'not_yet_eligible'. Called 'inactive proxy', never 'churn' | 884 | Genuine churn (closure, asset transfer-out, zero balance) is not observable in this dataset. |
| CL08 | Users | months_observed … m1/m3/m6_retained, dormant_3m_monthly | Engagement fields exist only at user-month grain | Aggregated Monthly_Activity to user level; retention flags are NULL where the window is not yet observable (e.g. M3 needs registration <= 2026-07) | 10,000 | Retention is recalculated from source events (monthly activity), not from the supplied snapshot flags. |
| CL09 | Users | flag_* columns | Cross-table contradictions and outliers | Added row-level flags; no rows deleted or values overwritten | 8,643 | No ground truth identifies which table is wrong, so contradictions are exposed, not silently resolved. |
| CL10 | All | Boolean columns | True/False text booleans | Converted to 0/1 int8 in all output files | 70,000 | Consistent typing for SQL, Excel and Power BI. |
| CL11 | All | date columns | Mixed datetime representation | All dates written as ISO yyyy-mm-dd; months as yyyy-mm | 60,000 | Single date format across tables. |
| CL12 | Monthly_Activity | flag_* , net_flow_inr, avg_trade_value_inr, cum_* | Source rows contradict the Users funnel flags | Rows kept. Added consistency, outlier and derived-measure columns | 21,761 | Monthly_Activity is the source of truth for engagement; Users for funnel. Rows are neither deleted nor 'fixed' because the true value is unknown. |
| CL13 | Support_Tickets | is_resolved, ticket_age_days, backlog_age_bucket, related_funnel_stage, stage_pending_at_ticket | Resolution time / CSAT exist only for resolved tickets (survivorship); no backlog ageing; no link between ticket and funnel stage | Added resolved/unresolved flags, ageing buckets and a stage-pending flag (ticket created before the related funnel event, or event never reached) | 1,371 | Lets Phase 3 report resolved-only averages alongside the unresolved backlog and test the 'stuck at stage' hypothesis. |

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

| Dimension | Checks | Record-tests | Violations (raw) | Pooled pass rate (raw) | Weakest single check (raw) | Violations after corrections | Pooled pass rate (after) | Weakest check (after) | Treatment status |
|---|---|---|---|---|---|---|---|---|---|
| Uniqueness | 6 | 342,269 | 0 | 100.00% | 100.00% | 0 | 100.00% | 100.00% | Pass |
| Referential integrity | 7 | 102,299 | 0 | 100.00% | 100.00% | 0 | 100.00% | 100.00% | Pass |
| Completeness | 8 | 594,904 | 0 | 100.00% | 100.00% | 0 | 100.00% | 100.00% | Pass |
| Validity | 7 | 457,082 | 0 | 100.00% | 100.00% | 0 | 100.00% | 100.00% | Pass |
| Journey chronology | 10 | 182,623 | 0 | 100.00% | 100.00% | 0 | 100.00% | 100.00% | Pass |
| Timeliness | 2 | 31,903 | 1,254 | 96.07% | 96.05% | 0 | 100.00% | 100.00% | Corrected |
| Cross-table consistency | 11 | 174,752 | 37,142 | 78.75% | 36.64% | 36,409 | 79.17% | 36.64% | Corrected, Flagged (retained) |
| Reported-metric accuracy | 1 | 17 | 3 | 82.35% | 82.35% | 0 | 100.00% | 100.00% | Corrected |
| Definition validity | 2 | 16,571 | 936 | 94.35% | 87.54% | 926 | 94.41% | 87.54% | Corrected, Documented |
| Reconciliation | 2 | 164 | 0 | 100.00% | 100.00% | 0 | 100.00% | 100.00% | Pass |

**Reading it:** structural dimensions (uniqueness, referential integrity, completeness, validity, journey order) pass at 100%. The weak spots are *cross-table consistency* and *timeliness*; timeliness is repaired in the cleaned copy while cross-table consistency can only be disclosed.

### Full check register (non-outlier)

| check_id | table | description | records_tested | violations_raw | Pass | violations_after_correction | severity | status |
|---|---|---|---|---|---|---|---|---|
| UQ01 | Users | Duplicate user_id | 10000 | 0 | 100.0% | 0 | - | Pass |
| UQ02 | Users | Fully duplicated user rows | 10000 | 0 | 100.0% | 0 | - | Pass |
| UQ03 | Support_Tickets | Duplicate ticket_id | 7614 | 0 | 100.0% | 0 | - | Pass |
| UQ04 | Monthly_Activity | Duplicate (user_id, activity_month) | 64645 | 0 | 100.0% | 0 | - | Pass |
| UQ05 | Campaigns | Duplicate campaign_id | 10 | 0 | 100.0% | 0 | - | Pass |
| UQ06 | Users | CSV vs Excel Users sheet: cells that differ | 250000 | 0 | 100.0% | 0 | - | Pass |
| RI01 | Monthly_Activity | monthly_activity.user_id not in users | 64645 | 0 | 100.0% | 0 | - | Pass |
| RI02 | Support_Tickets | support_tickets.user_id not in users | 7614 | 0 | 100.0% | 0 | - | Pass |
| RI03 | Users | users.acquisition_campaign_id not in campaigns | 10000 | 0 | 100.0% | 0 | - | Pass |
| RI04 | Users | Users with no monthly_activity rows (orphan parent) | 10000 | 0 | 100.0% | 0 | - | Pass |
| RI05 | Campaigns | Campaigns with no attributed users | 10 | 0 | 100.0% | 0 | - | Pass |
| RI06 | Users | User channel/platform differs from campaign master | 10000 | 0 | 100.0% | 0 | - | Pass |
| RI07 | Campaigns | Campaign sheet counts (users, KYC, first traders) vs recomputed from users | 30 | 0 | 100.0% | 0 | - | Pass |
| CP01 | Users | Nulls in mandatory user fields | 10000 | 0 | 100.0% | 0 | - | Pass |
| CP02 | Users | Completed stage without a date | 21903 | 0 | 100.0% | 0 | - | Pass |
| CP03 | Users | Date present for a stage not completed | 18097 | 0 | 100.0% | 0 | - | Pass |
| CP04 | Users | Deposit amount missing/zero for depositors; positive for non-depositors | 10000 | 0 | 100.0% | 0 | - | Pass |
| CP05 | Users | Trade segment missing for traders / present for non-traders | 10000 | 0 | 100.0% | 0 | - | Pass |
| CP06 | Monthly_Activity | Nulls in any monthly field | 517160 | 0 | 100.0% | 0 | - | Pass |
| CP07 | Support_Tickets | Resolved ticket lacking time/CSAT, or unresolved ticket with them | 7614 | 0 | 100.0% | 0 | - | Pass |
| CP08 | Campaigns | Nulls in campaign master | 130 | 0 | 100.0% | 0 | - | Pass |
| VL01 | Users | Non-Boolean values in Boolean columns | 70000 | 0 | 100.0% | 0 | - | Pass |
| VL02 | All | Negative financial amounts, counts or durations | 276194 | 0 | 100.0% | 0 | - | Pass |
| VL03 | Support_Tickets | CSAT outside 1-5 | 6243 | 0 | 100.0% | 0 | - | Pass |
| VL04 | Monthly_Activity | Non-integer trade_count | 64645 | 0 | 100.0% | 0 | - | Pass |
| VL05 | Users | days_inactive_as_of_snapshot negative, or larger than tenure | 10000 | 0 | 100.0% | 0 | - | Pass |
| VL06 | Users | days_inactive does not recompute from last_active_date and snapshot | 10000 | 0 | 100.0% | 0 | - | Pass |
| VL07 | Users | churn flags inconsistent with days_inactive (>30 / >90) | 20000 | 0 | 100.0% | 0 | - | Pass |
| JR01 | Users | KYC date earlier than registration | 7075 | 0 | 100.0% | 0 | - | Pass |
| JR02 | Users | Bank-link date earlier than KYC date | 6226 | 0 | 100.0% | 0 | - | Pass |
| JR03 | Users | First deposit earlier than bank-link date | 4786 | 0 | 100.0% | 0 | - | Pass |
| JR04 | Users | First trade earlier than first deposit | 3816 | 0 | 100.0% | 0 | - | Pass |
| JR05 | Users | First trade earlier than registration | 3816 | 0 | 100.0% | 0 | - | Pass |
| JR06 | Users | Stage reached while a prerequisite stage was skipped | 10000 | 0 | 100.0% | 0 | - | Pass |
| JR07 | Users | last_active_date earlier than registration | 10000 | 0 | 100.0% | 0 | - | Pass |
| JR08 | Monthly_Activity | Activity row before registration month | 64645 | 0 | 100.0% | 0 | - | Pass |
| JR09 | Monthly_Activity | Activity row after observation window (> 2026-10) | 64645 | 0 | 100.0% | 0 | - | Pass |
| JR10 | Support_Tickets | Ticket created before registration | 7614 | 0 | 100.0% | 0 | - | Pass |
| TM01 | Users | Funnel events dated after the 2026-10-31 snapshot but flagged completed (events) | 21903 | 866 | 96.05% | 0 | High | Corrected |
| TM02 | Users | Users with at least one post-snapshot funnel event | 10000 | 388 | 96.12% | 0 | High | Corrected |
| XT01 | Monthly_Activity | Monthly trade rows for users flagged first_trade_made=False | 19718 | 5640 | 71.4% | 5640 | Critical | Flagged (retained) |
| XT02 | Monthly_Activity | Trade rows in a month earlier than the user's first-trade month | 14078 | 2242 | 84.07% | 2242 | Critical | Flagged (retained) |
| XT03 | Monthly_Activity | Monthly deposit rows for users flagged first_deposit_made=False | 5680 | 2613 | 54.0% | 2613 | Critical | Flagged (retained) |
| XT04 | Monthly_Activity | Deposit rows in a month earlier than the first-deposit month | 3067 | 361 | 88.23% | 361 | High | Flagged (retained) |
| XT05 | Monthly_Activity | Withdrawal rows for users who never made a first deposit | 3895 | 1818 | 53.32% | 1818 | High | Flagged (retained) |
| XT06 | Users | first_trade_made=True but no trade in Monthly_Activity | 3816 | 114 | 97.01% | 114 | High | Flagged (retained) |
| XT07 | Users | first_deposit_made=True but no deposit in Monthly_Activity | 4786 | 2548 | 46.76% | 2548 | High | Flagged (retained) |
| XT08 | Users | Month of last_active_date differs from last active month in Monthly_Activity | 10000 | 6336 | 36.64% | 6336 | Critical | Flagged (retained) |
| XT09 | Monthly_Activity | Active monthly rows after the month of last_active_date | 35067 | 3180 | 90.93% | 3180 | High | Flagged (retained) |
| XT10 | Users | last_active_date earlier than the user's latest funnel event (on/before snapshot) | 10000 | 733 | 92.67% | 0 | High | Corrected |
| MS01 | Analysis_Summary / Funnel_Summary | Pre-computed summary KPIs that do not reproduce from row-level data | 17 | 3 | 82.35% | 0 | High | Corrected |
| MD01 | Users | Users flagged neither active_30d nor churned_30d_proxy although tenure>=30 d (boundary) | 9137 | 10 | 99.89% | 0 | Medium | Corrected |
| MD02 | Users | Users with last_active_date in Jul-Oct 2026 (every user has one) but no active month Jul-Oct in Monthly_Activity | 7434 | 926 | 87.54% | 926 | High | Documented |
| XT11 | Monthly_Activity | Cumulative withdrawals exceed cumulative deposits in a user-month (informational) | 64645 | 11557 | 82.12% | 11557 | Medium | Flagged (retained) |
| RC01 | Customer_Cohorts | Rebuilt cohort table vs supplied Cohort_Retention sheet (cohort size & active users, per cell) | 156 | 0 | 100.0% | 0 | - | Pass |
| RC02 | Campaign_Performance | Recomputed CAC vs supplied Campaigns.cac_inr (paid campaigns) | 8 | 0 | 100.0% | 0 | - | Pass |

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
| `data/cleaned/Cleaned_Users.csv` | A — 10,000 × 80 |
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
