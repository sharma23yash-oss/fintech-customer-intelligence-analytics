# Testing and validation (all data SYNTHETIC)

Two layers, both reproducible:

```bash
python -m pytest -q                 # 64 unit / integration / smoke tests (about 20 seconds)
python validation/validate.py       # 46 end-to-end checks on the full 10,000-customer dataset; writes validation/validation_results.json
```

Result at hand-over: **64 of 64 pytest tests pass; 46 of 46 validation checks pass.** Both were run on Python 3.13 with pandas 3.0.5 / numpy 2.5.3 / streamlit 1.67
and again on pandas 2.2.3 / numpy 2.2.6 (same results). Not run on macOS.

## What "detection accuracy" means here

There are no ground-truth friction labels, so accuracy cannot be measured against reality. I tested it against the **written business rules** in
`docs/RULES_AND_SCORING.md` with an **independent oracle** (`validation/oracle.py`): a plain-Python, row-by-row re-implementation that reads the raw CSVs and does
not import the engine. If both implementations share a misunderstanding of the rules, this will not catch it; it catches coding errors, not wrong rules.

| Compared for all 10,000 customers | Mismatches |
|---|---|
| stage, is_flagged, all friction categories, primary category | 0 |
| days overdue, days inactive, tickets total, tickets unresolved | 0 |
| data confidence, priority band | 0 |
| priority score (tolerance 0.05) | max difference 0.000 |

Therefore: **false positives 0, false negatives 0 against the written rules.** Whether the rules are *good* rules is a separate question that only real outcome data could answer.

## Customer eligibility

| Check | Result |
|---|---|
| Every registered customer analysed exactly once (10,000) | pass |
| No flagged customer is inside its observation window | pass |
| Every journey flag has dwell > window; every WITHIN_WINDOW has dwell <= window (543 customers) | pass |
| Inactivity flags only for traded customers with tenure >= 31 d and > 30 d inactive (654) | pass |
| Nobody registered in the last 3 days is flagged for a journey step | pass |
| Customer registered after the as-of date is excluded (unit test) | pass |

## Edge cases (pytest, hand-built customers)

* Window boundary for every stage: dwell = window - 1 and = window are not flagged; window + 1 is flagged with `days_overdue = 1`.
* New registrant (0 days) not flagged; score 0.
* Inactivity at exactly 30 days not flagged, 31 flagged; tenure under 31 days not assessed; last-active in the future counts as 0 days; missing last-active falls back to the trade date.
* Ticket created today: not flagged unless escalated; open for 3 days: flagged; resolved: not unresolved; ticket after the as-of date ignored; ticket resolved after the as-of date counts as unresolved in replay.
* 2 tickets do not trigger the repeat rule; 3 do. Multi-label and primary-category precedence.
* Out-of-order event dates are flagged as `sequence_anomaly` and do not crash; a bank date without a KYC date does not advance the stage.
* Replay: an earlier as-of date gives an earlier stage.

## Missing values and duplicates

Injected into a copy of the data (the source is never modified): 25 duplicate user rows, 15 duplicate tickets, 10 missing cities, 5 invalid dates,
3 missing user IDs, 2 missing registration dates. The engine ran without error, removed 22 duplicate users (25 injected; 3 of the originals had their ID blanked and
were counted as missing IDs, so the surviving copies are correctly kept) and 15 duplicate tickets, dropped the 3 + 2 unusable rows, filled missing cities with `Unknown`,
treated the 5 invalid dates as "step not completed", and reported every count in `result.attrs["data_quality"]`. No NaN remained in the key output columns.
The real source data had none of these problems (checked).

## Reconciliation with earlier phases

| Check | Result |
|---|---|
| Engine stage = Phase 2 `furthest_stage_asof` for every customer | 0 differences |
| 3,536 traded customers (Phase 3 funnel) | 3,536 |
| REPEATED_SUPPORT_ISSUES = customers with 3+ tickets (Phase 4 rule) | 450 = 450 |

## Backtest of window choice (`validation/backtest_premature_flag_rates.csv`)

Share of customers who *did* complete a step but had waited longer than the window when they completed (they would have been flagged early):

| Window rule | KYC | Bank | Deposit | Trade |
|---|---|---|---|---|
| p50 | 44.1% | 42.4% | 47.4% | 44.9% |
| p75 | 17.4% | 14.2% | 20.0% | 17.5% |
| p90 | 8.3% | 0.0% | 6.8% | 8.6% |
| **p95 (used)** | **0.0%** | **0.0%** | **0.0%** | **0.0%** |
| max | 0.0% | 0.0% | 0.0% | 0.0% |

**Read this carefully:** p95 equals the maximum observed lag in this dataset, so the 0% is a property of the synthetic generator (bounded lags), not proof of real-world performance.
The check `Disclosure: ... BY CONSTRUCTION` in `validate.py` asserts and prints this. The useful part of the table is the shape: tighter windows would flag many customers who were about to complete on their own.

## Score checks

Flagged scores within 0-100 (min 10.7, max 85.0); non-flagged score 0 and `NOT_FLAGGED`; the six components add up to the score; each component respects its cap;
`score_type` is `heuristic_priority_score_NOT_a_probability` on every row; two runs are identical (deterministic). More inactivity gives a higher score; an escalated ticket adds more than an open one.

## Pipeline and application

* Database build: 10,000 users, 7,614 tickets, 64,645 activity rows; tables and views exist; stored config reloads to the same windows.
* Daily workflow: files written; every CSV row labelled SYNTHETIC with the score-type column; sorted by priority; by-category files partition the exception report; first run is a baseline with 0 new;
  `newly_flagged` equals the set difference of two snapshots and none of them were flagged the day before; re-running a date is idempotent; user data unchanged by runs;
  spreadsheet formula-injection characters are neutralised.
* Streamlit (`streamlit.testing`): all four views render without exception; filter by city changes the counts (10,000 -> 929 analysed for Pune); unknown ID shows an error; lower-case ID accepted.
  Screenshots in `docs/screenshots/` were captured from the running app in headless Chrome.
* Insights: explanation contains the real window and dwell values; stale cases get a stronger intervention; LOW-confidence customers get a "verify first" note; no promise of money in any intervention text.
* LLM path: payload is whitelisted and contains no user ID, city, channel or date; extra fields or an ID-like string raise an error; small counts are suppressed; with no key the fallback is used;
  with a **mocked** transport the reworded text is used and the mock only ever receives the safe payload; network failure or empty reply falls back; kill switch works.

## Not tested / known gaps

* The real Anthropic API call (no key available here). Only the surrounding logic and a mock were tested.
* macOS Apple Silicon execution, and Python versions other than 3.13.
* Large-scale performance (10,000 customers run in about 1.5 seconds per day; nothing larger was tried).
* Browser compatibility beyond headless Chrome; accessibility of the dashboard.
* Whether the rules and intervention suggestions help real customers. That would need an experiment with real outcomes.
