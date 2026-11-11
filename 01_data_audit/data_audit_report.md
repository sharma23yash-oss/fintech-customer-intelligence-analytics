# Phase 1 — Data Inspection & Audit Report

> **SYNTHETIC DATA NOTICE.** Every customer record, campaign figure, ticket and metric in this project is artificially generated for a fictional Indian online brokerage. Nothing here is Futu/moomoo, Groww, Zerodha or any other company's data, and no figure may be presented as real company performance.

**Scope:** read-only audit of `Fintech_Brokerage_Customer_Analytics_Synthetic_Project.xlsx` (10 sheets) and `Fintech_Users_10000_Synthetic.csv`.
**Observation window (per START_HERE):** 2025-11-01 → 2026-10-31. **Snapshot date used in this audit:** 2026-10-31 (verified: `days_inactive_as_of_snapshot` recomputes exactly from this date for all 10,000 users).
**Raw files were not modified.** Copies sit in `data/raw/`; all checks are reproducible with `01_data_audit/00_phase1_audit.py` and `00b_phase1_deepdive.py`.

---

## 1. Verdict in one paragraph

The dataset is **structurally clean** (no duplicate keys, no orphan foreign keys, no nulls where a value is required, funnel stages are in the correct order for every user, campaign totals reconcile to the user table exactly, CSV is identical to the Excel Users sheet). It is **logically inconsistent in three places that matter for the analysis**: (1) the `Monthly_Activity` table contradicts the funnel flags in `Users_10000`; (2) `last_active_date` contradicts `Monthly_Activity` and is truncated at 120 days of inactivity; (3) the Oct-2026 cohort carries 388 users with events dated *after* the snapshot. Two numbers on the summary sheets are also wrong. None of this blocks the project, but each needs an explicit, documented treatment in Phase 2 — and the portfolio is stronger if these findings are shown rather than hidden.

---

## 2. File & table inventory

| Sheet / file | Rows × cols | Grain | Primary key | Foreign keys |
|---|---|---|---|---|
| `Users_10000` (= CSV) | 10,000 × 25 | 1 row per user | `user_id` | `acquisition_campaign_id` → `Campaigns.campaign_id` |
| `Monthly_Activity` | 64,645 × 8 | user × calendar month, from registration month | (`user_id`, `activity_month`) | `user_id` → `Users_10000` |
| `Support_Tickets` | 7,614 × 9 | 1 row per ticket | `ticket_id` | `user_id` → `Users_10000` |
| `Campaigns` | 10 × 13 | 1 row per campaign | `campaign_id` | — |
| `Cohort_Retention` | 78 × 5 | registration month × months-since-registration | (`registration_month`, `months_since_registration`) | derived from the two tables above |
| `Analysis_Summary`, `Funnel_Summary` | 12 / 7 rows | pre-computed KPIs | — | derived |
| `Data_Dictionary`, `KPI_Definitions`, `START_HERE` | 15 / 12 / 8 rows | documentation | — | — |

**Relationship map**

```
Campaigns (1) ──< Users_10000 (1) ──< Monthly_Activity (many)
                          └────────< Support_Tickets (many)
Cohort_Retention = aggregate of Users.registration_month × Monthly_Activity
```

The supplied Data Dictionary covers only 15 of the ~60 fields across the five data tables. A full dictionary will be produced in Phase 2.

---

## 3. What passed (no action needed)

| Check | Result |
|---|---|
| CSV vs Excel `Users_10000` | 0 cell differences across 250,000 cells |
| Duplicate `user_id` / `ticket_id` / `campaign_id` / (`user_id`,`activity_month`) | 0 / 0 / 0 / 0 |
| Orphan foreign keys (monthly, tickets, campaign) | 0 |
| Every user has monthly rows; row count equals the expected user-months | 64,645 = 64,645 |
| `months_since_registration` correct; no activity rows before registration month or after Oct-2026 | 0 errors |
| Flag ↔ date pairs (`kyc_completed` ↔ `kyc_completion_date`, etc.) | 0 mismatches |
| Stage order (reg ≤ KYC ≤ bank ≤ deposit ≤ trade) and no skipped stages | 0 violations |
| Deposit amount present only when deposit made; trade segment present only when trade made | 0 violations |
| `registration_month` matches `registration_date`; `created_month` matches `created_date` | 0 mismatches |
| Channel / source platform consistent with campaign master | 0 mismatches |
| Campaign sheet users, KYC completions, first traders vs Users table | exact match for all 10 campaigns |
| `Cohort_Retention` vs recomputation from Monthly_Activity | exact match, all 78 rows |
| Negative values; `trade_count>0` while inactive; trade value without trades | 0 |
| Resolved tickets all have resolution time and CSAT; unresolved have neither | consistent |
| Tickets created before the customer registered | 0 |

---

## 4. Findings that require a decision

Severity: **Critical** = would produce wrong conclusions if ignored · **High** = distorts headline KPIs · **Medium** = needs a caveat · **Low** = cosmetic.

### F1 — Monthly_Activity contradicts the Users funnel flags · **Critical**

The two tables look like they were generated independently.

| Test | Count |
|---|---|
| Users with `first_trade_made = False` but trades in Monthly_Activity | **3,676** (5,640 monthly rows) |
| Users with `first_trade_made = True` but zero trades in Monthly_Activity | 114 |
| Trade rows in a month *earlier* than the user's first-trade month | 2,242 of 19,718 |
| Users with `first_deposit_made = False` but monthly deposits > 0 | **2,047** |
| Users with `first_deposit_made = True` but zero monthly deposits | 2,548 |
| Withdrawal rows for users who never made a first deposit | 1,818 of 3,895 |
| Deposit rows before the first-deposit month | 361 |

Distinct users with any monthly trade: 7,378, versus 3,816 `first_trade_made` users.

**Why it matters:** if I joined the tables naively, "customers who never traded" would show trading volume and "first trade" would not precede repeat trading. Any analysis that mixes funnel conversion with monthly trading behaviour would be unreliable.

**Proposed treatment (Phase 2):** keep the two tables as separate, single-purpose sources of truth and never derive one from the other. Funnel, CAC and conversion use `Users_10000`. MAU, cohorts, repeat trading and deposit/withdrawal trends use `Monthly_Activity`. Add a `flag_activity_conflict` column in the cleaned user table, and disclose this limitation in the README and the presentation. In a real brokerage, a reconciliation between order-book and onboarding tables is exactly the kind of check a customer-operations analyst would run.

### F2 — `last_active_date` is unreliable and truncated · **Critical for churn**

- Every user's `last_active_date` falls between **2026-07-03 and 2026-10-31** — including users who registered in Nov-2025. Maximum possible inactivity is therefore 120 days by construction.
- **6,336 users** have a `last_active_date` month different from the last active month in `Monthly_Activity`.
- **543 users** have `last_active_date` earlier than their own `first_trade_date` (627 earlier than first deposit, 483 earlier than KYC).
- 3,180 of 35,067 active monthly rows fall *after* the month of the user's `last_active_date`.
- Oct-2026 actives: 4,611 (Monthly_Activity) vs 5,693 (`last_active_date` in Oct) vs 4,820 (`active_30d`).

**Treatment:** `days_inactive_as_of_snapshot` is used only as a recency indicator, labelled "inactivity proxy", never as churn. Retention is measured from `Monthly_Activity`.

### F3 — Right-censoring: events dated after the snapshot · **High**

388 users (all registered in Oct-2026) have at least one funnel event dated *after* 2026-10-31 (KYC 116, bank link 196, first deposit 274, first trade 280; latest date 2026-12-08). Yet their completion flags are `True`.

| Funnel metric | Flags as supplied | As-of 31-Oct-2026 |
|---|---|---|
| KYC completed | 7,075 | 6,959 |
| Bank linked | 6,226 | 6,030 |
| First deposit | 4,786 | 4,512 |
| First trade | 3,816 | 3,536 |

The Oct-2026 cohort shows first-trade conversion of **40.0% on flags vs 8.4% as-of snapshot** — an artefact of the cohort not having had time to convert. The supplied flags record *eventual* completion, so they leak future information.

**Treatment:** add `*_asof_snapshot` columns. Report funnel conversion on **mature cohorts (Nov-2025 → Sep-2026, n = 9,116)** and show Oct-2026 separately as "immature". On mature cohorts: KYC 70.5%, bank link 61.9%, first deposit 47.6%, first trade 38.0%.

### F4 — Two summary-sheet errors · **High**

| Cell | As supplied | Recalculated | Issue |
|---|---|---|---|
| `Funnel_Summary` "30-day churn proxy (eligible)" | **6,758** | 4,307 | Value is not derivable from any field; active + churn would be 11,578 against 9,137 eligible users |
| `Analysis_Summary` "30-day churn proxy" | 47.25% | 47.14% (4,307 / 9,137) | Reported as 1 − active rate rather than from the churn flag. 10 eligible users (tenure exactly 30 days) are neither active nor churned |
| `Analysis_Summary` "Blended CAC" | ₹331.2 | ₹331.2 = ₹2.69M ÷ **8,122 paid-channel users**; ₹269.0 over all 10,000 | The label "blended" is misleading — organic users are excluded from the denominator |

**Treatment:** recompute all KPIs from row-level data; never reuse the summary sheets. Label CAC precisely ("paid-channel CAC" vs "blended CAC").

### F5 — Churn and retention definitions · **High**

| Question | Assessment |
|---|---|
| Is `churned_30d_proxy` genuine churn? | **No.** It means "no activity for >30 days at one snapshot". For a long-term investor (SIP, buy-and-hold) 30 days of silence is normal; for an active trader it is a warning. |
| Is the denominator appropriate? | Eligibility (tenure ≥ 30 days, n = 9,137) is sensible. Using all 10,000 gives 43.1%, which mixes in users who could not yet be inactive. |
| Is `churned_90d_proxy` comparable to 30d? | **No.** Maximum observable inactivity is 120 days (F2), and users registered <90 days ago cannot be 90-day-inactive. The 11.3% rate is truncated and under-states long-run inactivity. |
| Is it a point-in-time snapshot? | Yes — one date, no event time. It cannot support survival or time-to-churn analysis. |
| Is it consistent with `Monthly_Activity`? | Not fully (F2). |

**Treatment:** three separate concepts, labelled consistently throughout:
1. **Recency (inactivity) proxy:** days since last activity at snapshot (users table).
2. **Cohort retention:** share of a registration cohort active in month *N* (Monthly_Activity).
3. **Genuine churn:** *not observable* in this dataset (no account-closure, asset-withdrawal or zero-balance field). I will say so, and list the data needed.

### F6 — What the dataset cannot support · **High (scope)**

| Requested item | Status | Handling |
|---|---|---|
| **App Visit** funnel stage | **No data.** Earliest event is registration | Funnel starts at Registration. Visit → Registration shown as "not available" with the tracking required (GA4/Mixpanel events) |
| Campaign ROI / LTV | **No revenue, commission or AUM fields** | Not computed. Documented what is needed: brokerage commission per trade, fees, interest on margin, AUM, contribution margin |
| CAC trend over time | Spend is a **single lump sum per campaign**, no dates | CAC is cross-sectional only |
| Marketing attribution | `acquisition_campaign_id` is last-touch only | Noted |
| True "30-Day Active User" as a lifecycle stage | `active_30d` is a snapshot recency flag, not "active within 30 days of first trade" | Defined in Phase 2 (see §6) |
| Predictive modelling | Features and labels derived from the same snapshot, flags leak future information (F3) | Optional; will only attempt where leakage can be avoided, and with caveats |

### F7 — Support-ticket data · **Medium**

- **18.0% of tickets (1,371) are unresolved** (Open 892, Escalated 479). The supplied average resolution time (10.89 h) and CSAT (3.83) cover **resolved tickets only** — survivorship bias.
- **563 unresolved tickets are older than 90 days; 208 older than 180 days** (oldest 344 days). A real operations team would treat this as backlog hygiene.
- Resolution time barely varies by priority (High 11.05 h, Medium 10.83 h, Low 10.90 h); escalation rate is also flat (6–7%). There is **no sign of priority-based SLA handling** in the data — report as observed, not as an insight about the operations team.
- "Tickets per 1,000 customers" is 761 on a lifetime basis, but customers have different tenures. Exposure-adjusted: **117.8 tickets per 1,000 customer-months.** I will report both, and use the exposure-adjusted figure for comparisons.
- Many tickets come from users who have not reached the related stage (e.g. 661 of 1,727 KYC tickets from users who never completed KYC; 592 of 1,246 bank-linking tickets from users who never linked). That is consistent with users being *stuck* and is a usable funnel-friction signal, though it is a hypothesis until a ticket-to-stage timeline is available.

### F8 — Outliers and categories · **Medium / Low**

- First-deposit amount: median ₹6,519, mean ₹9,254; **321 deposits above the IQR fence (₹22,944)**, maximum ₹135,951. Retained (plausible for high-net-worth users); reported with medians and a winsorised mean.
- Resolution time: 169 values above 27.9 h, maximum 79.2 h. Retained.
- City `Other` holds 923 users (9.2%). Kept as its own category; cannot be analysed geographically.
- Campaign names: organic CAC is ₹0 because spend is zero; this is not "free acquisition" (content, SEO and brand costs exist but are not recorded).

---

## 5. Data-quality scorecard

| Dimension | Score | Comment |
|---|---|---|
| Completeness | ✅ Pass | Nulls exist only where a stage was not reached or a ticket is unresolved |
| Uniqueness | ✅ Pass | No duplicates |
| Referential integrity | ✅ Pass | No orphans |
| Validity (types, ranges) | ✅ Pass | Boolean, date and numeric types correct |
| Funnel-order logic | ✅ Pass | All stages in sequence |
| Timeliness / censoring | ⚠️ Issue | F3 — 388 users with post-snapshot events |
| Cross-table consistency | ❌ Fail | F1, F2 |
| Metric correctness (summary sheets) | ⚠️ Issue | F4 |
| Definition validity (churn) | ⚠️ Issue | F5 |
| Fitness for requested scope | ⚠️ Partial | F6 — no app-visit, revenue, spend timeline |

---

## 6. Treatments I will apply in Phase 2 (defaults — tell me if you disagree)

1. **Raw files stay untouched.** Cleaned outputs go to `data/cleaned/` with a column-level change log (`cleaning_log.csv`).
2. **New columns, no deletions:** `kyc_asof`, `bank_link_asof`, `first_deposit_asof`, `first_trade_asof`; `cohort_maturity` (`mature` / `immature_oct26`); `tenure_days`; `eligible_30d` (tenure ≥ 30); `flag_activity_conflict`; `flag_last_active_conflict`; stage durations in days.
3. **Source-of-truth rules:** funnel / CAC / conversion → Users table (mature cohorts); MAU / retention / cohorts / repeat trading / deposits-withdrawals → Monthly_Activity; support → Support_Tickets; recency → `days_inactive_as_of_snapshot`, labelled as a proxy.
4. **Funnel definition:** Registration → KYC → Bank Link → First Deposit → First Trade → **Active (≥30 days since registration, active in last 30 days at snapshot)**. Median stage times computed on completers; "App Visit" shown as unavailable.
5. **CAC naming:** paid-channel CAC (₹331.2), blended CAC across all users (₹269.0), and organic reported separately as zero recorded spend.
6. **ROI:** not calculated; data-requirement list provided instead.
7. **Churn:** never called churn without the word "proxy"; genuine churn is stated as unobservable.
8. **Tickets:** report unresolved backlog alongside resolved-only averages; use per-1,000 customer-months.

---

## 7. A framing note: market transferability

The dataset is a fictional **Indian** brokerage (INR, Indian cities). The project is therefore presented as a *transferable analytical framework* (funnel, cohorts, campaign efficiency, support operations) demonstrated on a synthetic dataset, rather than as a market-specific study. The recommendations avoid claims about any real market's customers or about regulator-specific onboarding rules that this data cannot support.

---

## 8. Files produced in Phase 1

| File | Purpose |
|---|---|
| `01_data_audit/data_audit_report.md` | This report |
| `01_data_audit/phase1_audit_raw_log.txt` | Full console output of the audit |
| `01_data_audit/00_phase1_audit.py` | Reproducible audit — keys, dtypes, nulls, funnel logic, reconciliation |
| `01_data_audit/00b_phase1_deepdive.py` | Deep-dive: churn flags, censoring, cross-table conflicts, tickets |
| `data/raw/` | Untouched copies of the two input files |
