# Final project report

**Fintech Brokerage Customer Intelligence & Growth Analytics**
Author: Yash Sharma · Data: fully synthetic (fictional Indian retail brokerage, 10,000 users, Nov 2025 – Oct 2026, INR, snapshot 2026-10-31)

> This report summarises the project for a reader with ten minutes. Nothing here is real company data. The dataset contains **no revenue, fee or lifetime-value fields, so no revenue or ROI is calculated**. Experiments are proposed, not run. A Power BI build kit and design mockups exist; a finished Power BI dashboard does not.

## 1. Business problem

A retail brokerage can add thousands of registrations and still grow slowly if few of them fund an account and trade. The questions: where does onboarding lose customers, which acquisition spend produces first-time traders rather than sign-ups, who stays active, how does support demand relate to onboarding, and what should the team do first?

## 2. Approach

1. **Audit** the raw extract (eight findings that shape every later decision).
2. **Clean** without touching the original: 13 logged changes, mainly removing future information from completion flags, defining a mature cohort, and leaving organic CAC undefined rather than zero.
3. **Analyse** six areas: acquisition, funnel, retention, segmentation, campaigns, support.
4. **Verify** in three tools (SQL, Python, Excel): 71 of 71 headline KPIs agree.
5. **Recommend**: 15 actions, 10 proposed experiments, a 30-60-90 plan.
6. **Prototype** an operations tool (AI Friction Detector) that turns the findings into a daily exception list.

Details: [`../documentation/methodology.md`](../documentation/methodology.md).

## 3. Results

### Funnel (mature cohort, n = 9,116)

| Stage | Users | Step conversion | Lost |
|---|---|---|---|
| Registered | 9,116 | – | – |
| KYC completed | 6,429 | 70.5 % | 2,687 |
| Bank linked | 5,645 | 87.8 % | 784 |
| First deposit | 4,340 | 76.9 % | 1,305 |
| First trade | 3,462 | 79.8 % | 878 |
| Active (30d) | 2,808 | 81.1 % | 654 |

38.0 % of mature registrants make a first trade. **KYC accounts for 42.6 % of all funnel losses.** Median time from registration to first trade is 23 days.

### Acquisition and campaigns

| Channel | Share of registrations | First-trade rate (mature) | Cost per first trade |
|---|---|---|---|
| Referral | 10.4 % | 52.9 % | Rs 438 |
| Organic | 18.8 % | 47.2 % | not defined (no recorded spend) |
| Paid Search | 26.4 % | 36.6 % | Rs 1,065 |
| Paid Social | 25.4 % | 30.3 % | Rs 1,075 |

Paid spend is Rs 2,690,000 with a blended CAC of about Rs 331 and a blended cost per first trade of about Rs 923. Customer Referral is the most efficient campaign; Video Awareness (Rs 1,252) and Finance Affiliate (Rs 1,216) are the least. Video Awareness is significantly below the rest after Holm correction; Finance Affiliate is not (p = 0.061). Moving 25 % of those two budgets (Rs 190,000) to the two strongest campaigns adds about 265 first traders at observed efficiency, but the gain disappears if destination costs rise by about 172 %; it is arithmetic, not a forecast.

### Retention

M1 / M3 / M6 retention is 67.6 % / 56.0 % / 40.7 %. October 2026 MAU is 4,611 (46.1 %). 22.0 % of mature users have been dormant for three months (a proxy for churn, not churn). Referral and organic cohorts retain best (M3 about 61 %), partnerships worst (50.8 %). Trading in months 0–1 is associated with better M3 retention (60.7 % vs 50.0 %), but a logistic early-warning model reaches only AUC 0.57, so it is not used.

### Segmentation

Rule-based journey segments show that 58.6 % of users sit in a stalled onboarding state (KYC-pending 28.3 %, deposit-pending 13.3 %, deposited-never-traded 8.8 %, bank-link-pending 8.2 %), while high-engagement traders are 9.0 % and repeat traders 16.8 %. K-means found weakly separated clusters (silhouette 0.33), so the explainable rule segments are used for action.

### Support

7,614 tickets (761 per 1,000 users); 52 % of users raised at least one. KYC and verification is the largest category (22.7 %). Median resolution is 9.4 h and CSAT 3.83. 1,371 tickets are unresolved (892 open, 479 escalated) and 563 are older than 90 days. Priority does not change resolution time (p = 0.59). Ticket-raisers are only slightly more likely to go dormant (cohort-adjusted odds ratio 1.15, 95 % CI 1.03–1.30), an association rather than a cause.

## 4. Recommendations (summary)

| Theme | Examples | Detail |
|---|---|---|
| Growth | Make cost per first trade the headline campaign KPI; stage a budget shift with a break-even rule; scale referral at the first-trade moment | [`business_recommendations.md`](../07_growth_strategy/business_recommendations.md) |
| Customer experience | Fix the KYC step (checklist, status tracker, assisted KYC); reduce deposit hesitation; guide the first trade | |
| Retention | First-trade milestone onboarding; value-led win-back with a holdout | |
| Operations | Make support priority real and clear the 90-day backlog; fix the data foundation (reconcile flags, log step events, date the spend) | |

Ten experiments (EXP-01 to EXP-10) are sized with baselines from the data and **assumed** effects; at about 190 registrations a week they need 5 to 48 weeks from launch; because pilots start in Days 31–60 of the roadmap, only EXP-02 fully reads out by Day 90 (EXP-09 about Day 93) ([`experiment_design.md`](../07_growth_strategy/experiment_design.md)).

## 5. AI Friction Detector

A prototype that finds customers stuck in onboarding, explains why, ranks them with a transparent 0–100 heuristic and produces a daily exception report. On the synthetic data it flags 6,887 of 10,000 customers (68.9 %); 543 are deliberately not flagged because they are still inside the normal completion window (KYC 11 days, bank 7, deposit 14, trade 11). 66 % of flagged customers are marked low data confidence because the activity log contradicts the funnel record. 64 tests and 46 validation checks pass. The priority score is not a probability, and the optional LLM wording step has not been run against a live model.

## 6. Limitations

* Synthetic data; patterns reflect the generator.
* No revenue, fees, lifetime value or confirmed churn; no ROI.
* Inactivity and dormancy are proxies.
* Differences between campaigns and channels are observational.
* No `.pbix`; DAX and Power Query never run in Power BI; mockups are not screenshots.
* Experiments proposed, not run.
* Built and tested on Linux; not run on macOS.

Full list: [`../documentation/limitations.md`](../documentation/limitations.md).

## 7. Next steps if this were a real engagement

1. Reconcile the activity log with the funnel record and add step-level event logging.
2. Date the marketing spend and capture clicks.
3. Add revenue and fee data so cost per first trade can become a return measure.
4. Run EXP-02 (assisted KYC) first, the only test small enough to read out within 90 days.
5. Build the Power BI report from the kit and validate against the supplied expected values.
