# Experiment design

> **All data are synthetic** (a fictional Indian retail brokerage: 10,000 users, Nov 2025 - Oct 2026, INR, snapshot 2026-10-31). No revenue, ROI or lifetime value is computed because the dataset contains none of those fields. Nothing below has been tested in a real business; experiments are **proposed, not run**.

Ten A/B tests are **proposed**. **None has been run.** Baselines are actual rates from the synthetic data; every expected lift is an **assumption** chosen only to size the test. They are not forecasts.

## Standards applied to every test

* Two-sided test, 5% significance, 80% power, normal approximation (two proportions, or a rate comparison for count outcomes).
* Random assignment of users, stratified by channel and device; analysis of all assigned users (intention to treat).
* One primary KPI and at least one guardrail KPI written down **before** launch; no early stopping unless a sequential rule is written in advance.
* Ship only when the confidence interval excludes zero and no guardrail is breached.
* Compliance reviews KYC, consent and incentive wording before any test launches.

## The ten tests

| Experiment | Area | Baseline | Assumed effect | Users per arm | Per arm if effect halved | Weeks to read out |
|---|---|---|---|---|---|---|
| EXP-01 Guided KYC checklist + auto-resume reminder (D+2, D+5) | KYC completion | 70.5% | +5 pp (ASSUMED) | 1,236 | 5,088 | 16 |
| EXP-02 Assisted-KYC outreach for stalled applicants (backlog + new) | KYC completion (support-assisted) | 2.0% | +6 pp (ASSUMED) | 206 | 588 | 5 |
| EXP-03 UPI-first bank link with alternate-method fallback | Bank linking | 87.8% | +4 pp (ASSUMED) | 897 | 3,899 | 10 |
| EXP-04 Low-ticket first-deposit prompt with quick-amount chips | First deposit | 76.9% | +5 pp (ASSUMED) | 1,027 | 4,291 | 10 |
| EXP-05 Guided first-trade walkthrough with a practice order | First trade | 79.8% | +5 pp (ASSUMED) | 915 | 3,862 | 14 |
| EXP-06 Two-sided referral prompt at first-trade moment | Referral | 2.9% | +50% relative (ASSUMED) | 2,657 | 9,565 | 15 |
| EXP-07 Week-2 / month-1 habit nudges for first-time traders | Retention | 56.0% | +6 pp (ASSUMED) | 1,054 | 4,261 | 40 |
| EXP-08 In-flow KYC status tracker + contextual help | Ticket reduction | 17.3% | -20% relative (ASSUMED) | 2,046 | 8,636 | 27 |
| EXP-09 Dormant-user win-back sequence (value-led, no incentive vs small incentive) | Re-engagement of inactive users | 34.7% | +6 pp (ASSUMED) | 1,023 | 4,027 | 9 |
| EXP-10 Pre-qualification landing page for Paid Social (CMP03 + CMP04) | Acquisition quality (paid social) | 30.3% | +6 pp (ASSUMED) | 969 | 3,785 | 48 |

Sample sizes are very sensitive to the assumed effect: the *Per arm if effect halved* column shows how fast the requirement grows if the true lift is smaller than assumed.

## Feasibility at observed traffic

| ID | Baseline source | Eligible per week | Accrual weeks | Follow-up weeks | Feasibility |
|---|---|---|---|---|---|
| EXP-01 | ACTUAL: Registered->KYC conversion (mature cohorts) | 192 | 14 | 2 | Slow (14-26 weeks accrual): run concurrently with other tests or accept a larger MDE |
| EXP-02 | ASSUMPTION: 2% unaided late recovery. The data show no KYC completions after day 11, so the true unaided rate is near 0 and cannot be estimated | 28 | 1 | 4 | Feasible (<= 13 weeks accrual) |
| EXP-03 | ACTUAL: KYC->Bank conversion (mature cohorts) | 136 | 9 | 1 | Feasible (<= 13 weeks accrual) |
| EXP-04 | ACTUAL: Bank->Deposit conversion (mature cohorts) | 119 | 8 | 2 | Feasible (<= 13 weeks accrual) |
| EXP-05 | ACTUAL: Deposit->First Trade conversion (mature cohorts) | 92 | 12 | 2 | Feasible (<= 13 weeks accrual) |
| EXP-06 | ACTUAL (approximate): mean monthly referral registrations / mean MAU. Referrer IDs are not in the dataset, so attribution is approximated | 73 | 11 | 4 | Feasible (<= 13 weeks accrual) |
| EXP-07 | ACTUAL: pooled M3 retention, all mature registrants (traders-only baseline is higher; not computed) | 73 | 26 | 14 | Slow (14-26 weeks accrual): run concurrently with other tests or accept a larger MDE |
| EXP-08 | ACTUAL: KYC & verification tickets / registered users (all-time per user) | 192 | 23 | 4 | Slow (14-26 weeks accrual): run concurrently with other tests or accept a larger MDE |
| EXP-09 | ACTUAL: pooled P(active in month t | no activity in t-3..t-1) from Monthly_Activity | 113 | 5 | 4 | Feasible (<= 13 weeks accrual) |
| EXP-10 | ACTUAL: Paid Social mature first-trade rate (CMP03 + CMP04) | 49 | 41 | 7 | Traffic-constrained (> 26 weeks): needs larger MDE, pooling, or a longer run |

Traffic is the binding constraint (about 190 registrations a week). *Weeks to read out* counts from launch. Slow tests should run concurrently, be designed as factorials where they touch the same screen, or accept a larger minimum detectable effect.

## Linked recommendations

| Rec | Recommendation | Experiment(s) |
|---|---|---|
| A03 | Scale referral with a prompt at the first-trade moment | EXP-06 |
| A04 | Put Video Awareness (CMP04) and Finance Affiliate (CMP06) on improvement plans | EXP-10 |
| B01 | Fix the KYC step: checklist, status tracker and assisted KYC | EXP-01, EXP-02, EXP-08 |
| B02 | Offer UPI-first bank linking with a one-tap fallback | EXP-03 |
| B03 | Reduce first-deposit hesitation with quick-amount chips and reminders | EXP-04 |
| B04 | Convert funded-but-untraded users with a guided first trade | EXP-05 |
| C01 | Build onboarding around an early first-trade milestone | EXP-07 |
| C02 | Run a value-led win-back sequence with a holdout | EXP-09 |
| C03 | Protect repeat and high-engagement traders | EXP-06 |

The full machine-readable plan is [`tables/p6_experiment_plan.csv`](tables/p6_experiment_plan.csv); the earlier Phase 3 design with the power grid is in [`phase3_experiments/`](phase3_experiments/).
