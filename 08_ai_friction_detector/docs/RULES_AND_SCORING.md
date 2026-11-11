# Rules and scoring (all data SYNTHETIC)

Every number below is read from `db/friction.db` table `config` (written at build time) or from the 31 Oct 2026 run.
Nothing here was tuned against outcomes: the dataset has no friction or outcome labels.

## 1. Journey stage

Stage = number of *consecutive* completed steps at the as-of date, rebuilt from the dated events:

| Stage | Name | Needs |
|---|---|---|
| 0 | Registered | registration date <= as-of |
| 1 | KYC Completed | KYC date <= as-of |
| 2 | Bank Linked | stage 1 and bank date <= as-of |
| 3 | Funded | stage 2 and first-deposit date <= as-of |
| 4 | Traded | stage 3 and first-trade date <= as-of |

A bank date without a KYC date does not advance the stage (sequence is respected). The engine reproduces the
`furthest_stage_asof` field from Phase 2 for all 10,000 customers.

## 2. Observation windows (avoid flagging too early)

A pending step is flagged only after the customer has waited **longer than the 95th percentile of completion lags
observed for customers who did complete that step** (rounded up, minimum 3 days).

| Step | Window (days) | WATCH from (75th pct) |
|---|---|---|
| Registration -> KYC | 11 | 9 |
| KYC -> bank link | 7 | 6 |
| Bank link -> first deposit | 14 | 11 |
| First deposit -> first trade | 11 | 9 |

* `dwell <= window`: not flagged. Status is `IN_WINDOW`, or `WATCH` if past the 75th percentile. Primary category `WITHIN_WINDOW`.
* `dwell == window + 1`: flagged. Boundary tests cover both sides for every stage.
* Customers registered after the as-of date are not analysed. A customer registered today cannot be flagged for a journey step.
* Result on 31 Oct 2026: 543 customers are `WITHIN_WINDOW` (564 `IN_WINDOW` + 37 `WATCH` pending-step customers, minus those who are flagged for another reason).

**Important caveat.** In this synthetic dataset the 95th-percentile window equals the *maximum* observed lag, so no customer
who eventually completed a step would have been flagged early. That 0% is true by construction of the generator, not evidence that
the window would behave this way on real data (where p95 would leave about 5% of eventual completers flagged early). The backtest in
`validation/backtest_premature_flag_rates.csv` shows the trade-off for p50/p75/p90/p95/max.
Another consequence: since nobody in the synthetic data completes a step after the window, flagged customers never "recover", so the
daily report shows `no_longer_flagged = 0`. That is a property of the data, not a verified feature of the workflow (the set-difference
logic is unit-tested with synthetic examples).

## 3. Friction categories

| Category | Rule |
|---|---|
| `KYC_PENDING` | stage 0 and days since registration > 11 |
| `BANK_LINK_PENDING` | stage 1 and days since KYC > 7 |
| `FIRST_DEPOSIT_PENDING` | stage 2 and days since bank link > 14 |
| `FIRST_TRADE_PENDING` | stage 3 and days since first deposit > 11 |
| `INACTIVITY_RISK` | stage 4, registered >= 31 days ago, and no activity for > 30 days. Last-active falls back to the trade date if missing; a last-active date after the as-of date counts as 0 days inactive. A **proxy**, not churn. |
| `SUPPORT_UNRESOLVED` | a ticket that is not resolved at the as-of date and is either escalated (any age) or open for more than 2 days |
| `REPEATED_SUPPORT_ISSUES` | 3 or more tickets (same rule as Phase 4 "needs support"; matches 450 customers) |

A customer can carry several categories (`friction_categories`, pipe-joined; 1,158 flagged customers have more than one).
The **primary** category is the first that applies in this order: KYC, bank link, first deposit, first trade, inactivity,
unresolved support, repeated support. Non-flagged values: `WITHIN_WINDOW`, `NO_FRICTION`.

31 Oct 2026 result (primary category): KYC_PENDING 2,831; FIRST_DEPOSIT_PENDING 1,333; FIRST_TRADE_PENDING 881;
BANK_LINK_PENDING 818; INACTIVITY_RISK 654; SUPPORT_UNRESOLVED 321; REPEATED_SUPPORT_ISSUES 49.
Flagged 6,887 of 10,000 (68.9%); WITHIN_WINDOW 543; NO_FRICTION 2,570.

## 4. Priority score (heuristic, 0-100, NOT a probability)

`score_type = heuristic_priority_score_NOT_a_probability` is written on every row and every CSV.
It orders work; it does not estimate the chance that anything will happen. It was not trained and not validated against outcomes.

| Component | Max | Formula |
|---|---|---|
| Days since registration | 10 | 10 x min(1, tenure / 90) |
| Funnel stage | 20 | Registered 4, KYC 8, Bank 12, Funded 20, Traded 16 |
| Inactivity duration | 20 | 20 x min(1, days inactive / 90) |
| Support ticket history | 20 | escalated-open 12, or open past grace 8; +5 for 3+ tickets (+2 for 2); +3 if oldest unresolved > 90 days; capped at 20 |
| Customer activity | 10 | +5 if active in the last 30 days, plus min(5, active months in the last 6) |
| Previous transactions | 20 | first deposit >= p75 (INR 11,352) 8, >= p50 (INR 6,537) 5, >0 2; 6-month trading value >= p75 (INR 30,086) 8, >0 4; 2+ trading months 4 |

Bands: High >= 55, Medium >= 35, Low otherwise; non-flagged customers score 0 and band `NOT_FLAGGED`.
Result: High 1,158 (16.8%), Medium 3,200 (46.5%), Low 2,529 (36.7%) of flagged.

Why these weights: Funded customers score highest on stage (they are closest to the first trade and already put money in);
traded customers score a little lower. These are judgement calls to be reviewed by operations, not estimates. Change them in
`friction_detector/scoring.py` and `config.py`.

## 5. Data confidence (verify first)

The monthly activity log and the funnel dates disagree for many synthetic customers (a known issue from Phase 2).
Rather than silently choosing one, each flagged customer gets `data_confidence` for its primary category:

* `LOW` for journey categories if the log shows trades although no first trade is recorded, or deposits although no first deposit is recorded.
* `LOW` for `INACTIVITY_RISK` if the log shows activity in the last 30 days (month level).
* Support categories are `HIGH` (ticket data has no competing source).

4,550 of 6,887 flagged customers (66%) are `LOW`: KYC 73%, bank 75%, deposit 74%, trade 60%, inactivity 54% of each category.
Operations should confirm the real status in the source system before contacting a `LOW` customer.

## 6. Why scikit-learn is not used

Machine learning needs a label (for example "later completed KYC after outreach"). This dataset has no outreach, no outcome and no friction
label. Training on proxies such as "not active" would predict the rule that created the proxy (leakage) and would look accurate for the
wrong reason. The score is therefore a transparent additive heuristic. If real outcome data became available, a model could be
trained and compared against this baseline.

## 7. Limits of replay mode

`run-daily --as-of <earlier date>` rebuilds each customer's stage from dated events, so stage and KYC/bank/deposit/trade flags are exact.
Two things are approximate: inactivity (only the final last-active date exists, so activity after the as-of date is treated as 0 days inactive)
and tickets (resolution time = created date + resolution hours). The 24-31 Oct history is therefore a replay, not recorded daily runs.
