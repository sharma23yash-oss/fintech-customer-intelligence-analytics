# KPI definitions

Every KPI used in this repository, with its formula, denominator and caveat. **All figures come from a synthetic dataset** (fictional Indian retail brokerage, 10,000 users, Nov 2025 – Oct 2026, INR, snapshot 2026-10-31).

The same figure can appear with different denominators in different places. Always read the denominator column.

## Population definitions

| Term | Definition | Size |
|---|---|---|
| Registered users | All users in the dataset | 10,000 |
| **Mature cohort** | Users registered before October 2026 (Nov 2025 – Sep 2026), so each had time to convert | 9,116 |
| Eligible 30d / 90d | Tenure of at least 31 / 91 days at the snapshot; shorter-tenure users are *excluded*, not counted as inactive | – |
| As-of fields (`*_asof`) | Funnel flags and dates counting only events on or before 2026-10-31 (the source flags included 388 users' future events) | – |

## Acquisition and cost

| KPI | Formula | Denominator / scope | Value | Caveat |
|---|---|---|---|---|
| Registrations | Count of users | All users | 10,000 | – |
| Paid spend | Sum of recorded campaign spend | Paid campaigns only | Rs 2,690,000 | Spend is undated; organic has none |
| **CAC (blended, paid)** | Paid spend ÷ paid registrations | Paid registrations | ≈ Rs 331 | Recorded spend only; no team or tool costs |
| Cost per first trade (blended, paid) | CAC ÷ mature first-trade rate | Paid mature users | ≈ Rs 923 | Not ROI; no revenue exists |
| Organic CAC | not defined | – | n/a | Organic has hidden costs the data does not record, so it is blank, never zero |

## Funnel (mature cohort, n = 9,116)

| KPI | Formula | Value |
|---|---|---|
| KYC completion | KYC completed ÷ registered | 70.5 % |
| Bank-link conversion | Bank linked ÷ KYC completed | 87.8 % |
| First-deposit conversion | Funded ÷ bank linked | 76.9 % |
| First-trade conversion | First trade ÷ funded | 79.8 % |
| Active (30d) stage | First traders with last activity within 30 days of the snapshot ÷ first traders | 81.1 % |
| **Registered → first trade** | First traders ÷ registered (mature) | **38.0 %** (3,462) |
| Share of all funnel losses at KYC | Users lost at KYC ÷ all users lost | 42.6 % |

For reference: 3,536 of all 10,000 users made a first trade (35.4 %), but that figure includes the October 2026 cohort that has not had time to convert, which is why the headline conversion uses the mature cohort.

## Retention and engagement

| KPI | Formula | Denominator | Value | Caveat |
|---|---|---|---|---|
| M1 / M3 / M6 retention | Active in calendar month k after the registration month ÷ cohort users old enough to observe month k | Observable cohort users | 67.6 % / 56.0 % / 40.7 % | Calendar-month definition; month 0 = registration month |
| MAU (Oct 2026) | Users active in the month | – | 4,611 (46.1 % of 10,000) | – |
| 30-day active rate | Active within 30 days ÷ users with tenure ≥ 31 days | Eligible 30d | 54.0 % | **A different measure from the "Active (30d)" funnel stage** |
| Inactive 90d (proxy) | No activity for more than 90 days ÷ eligible 90d users | Eligible 90d | 14.9 % | Proxy, not churn |
| **Dormant 3 months (proxy)** | No active month Aug–Oct 2026 ÷ mature users | Mature | 22.0 % | Proxy, not churn |
| Repeat-trader share | Traded in at least 2 distinct months ÷ ever-traders | Users with ≥ 4 observed months (7,434) who ever traded | 69.3 % | – |

> The DAX measure named "30-Day Retention" is this 30-day active rate (54.0 %), not M1 retention (67.6 %).

## Support

| KPI | Formula | Value | Caveat |
|---|---|---|---|
| Tickets | Count | 7,614 (761 per 1,000 users) | – |
| Tickets per 1,000 customer-months | Tickets ÷ observed customer-months × 1,000 | 117.8 | Normalises for tenure |
| Median / mean resolution time | Created → resolved, resolved tickets only | 9.4 h / 10.9 h | Survivorship: unresolved tickets have no time |
| CSAT | Mean rating, rated tickets only | 3.83 | Only resolved tickets are rated |
| Unresolved tickets | Open + escalated | 1,371 (892 + 479) | – |
| Backlog over 90 days | Unresolved and older than 90 days at the snapshot | 563 | – |

## Analyst-defined scores and scenarios (not statistical models)

| Item | Definition | Label |
|---|---|---|
| Scorecard quality score | Mean rank-score of KYC rate, first-trade rate, 30-day active rate and M3 retention (0–100) | Analyst-defined |
| Cost-efficiency score | Mean rank-score of cost per KYC and cost per first trade (0–100), paid only | Analyst-defined |
| Budget scenario | Moved budget ÷ source vs destination cost per first trade, with a destination cost penalty | Arithmetic what-if, **not a forecast** |
| Experiment sample size | n per arm = [z(α/2)·√(2p̄(1−p̄)) + z(β)·√(p0(1−p0)+p1(1−p1))]² ÷ (p1−p0)²; α = 0.05 two-sided, power 80 % | Baselines actual; effects **assumed** |
| Friction priority score | 0–100 heuristic in the AI Friction Detector | Heuristic, not a probability |
| Early-warning model | Logistic regression, AUC 0.57 | Weak; not used for decisions |

## Statistics used

Wilson 95 % intervals for proportions; chi-square tests for category differences; Holm adjustment for multiple campaign comparisons; Mantel–Haenszel odds ratio for the ticket–dormancy association (stratified by registration cohort, association only); k-means with silhouette check (k = 4, silhouette 0.33).

Where each figure lives: [`../03_business_analytics/summary/Fintech_Growth_Analytics_Report.xlsx`](../03_business_analytics/summary/Fintech_Growth_Analytics_Report.xlsx) (sheet `KPI_Definitions`), [`../05_python/outputs/KPI_Report.md`](../05_python/outputs/KPI_Report.md), [`../06_dashboard/dax_measures.md`](../06_dashboard/dax_measures.md).
