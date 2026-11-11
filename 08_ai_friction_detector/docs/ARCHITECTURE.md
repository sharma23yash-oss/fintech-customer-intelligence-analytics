# Architecture (SYNTHETIC-data prototype, not a production system)

```
 data/synthetic/*.csv  (users, tickets, monthly_activity - fictional)
          |  build-db
          v
   db/friction.db  (SQLite)  <-- sql/schema.sql
   users | tickets | monthly_activity | config
          |
          |  run-daily --as-of D   (reads only the input tables)
          v
 +------------------------------+      +-----------------------------+
 | engine.py  rule detection    | ---> | scoring.py  heuristic 0-100 |
 | stage, windows, categories,  |      | six components, bands       |
 | data confidence              |      +-----------------------------+
 +------------------------------+
          |
          v
   customer_friction (latest run) | friction_snapshot (flagged users per run date) | friction_runs
          |                                   |
          |                       newly flagged = flagged today AND not flagged in the previous stored run
          v
 +------------------------------+      +------------------------------------+
 | insights.py                  |      | reports.py                         |
 | rule-based explanations,     | ---> | outputs/daily_reports/<date>/      |
 | interventions, daily summary |      |  exception_report.csv              |
 | optional LLM re-wording      |      |  newly_flagged.csv                 |
 +------------------------------+      |  by_category/<CATEGORY>.csv        |
          |                            |  summary_by_category.csv           |
          v                            |  daily_summary.md, run_manifest.json|
 app/streamlit_app.py (read-only)      +------------------------------------+
```

## Modules

| File | Responsibility |
|---|---|
| `friction_detector/config.py` | Every threshold, category name, owner team, path. One place to audit. |
| `friction_detector/engine.py` | Cleaning, derived windows, stage reconstruction for any as-of date, categories, primary category, data confidence. |
| `friction_detector/scoring.py` | Additive 0-100 priority heuristic with a docstring of the formula. |
| `friction_detector/insights.py` | Templates for summary, reason, intervention, owner team. Optional LLM wrapper with a whitelist payload and fallback. |
| `friction_detector/db.py` | Build the SQLite database, store the derived config, save each run. |
| `friction_detector/reports.py` | The daily workflow: detect, compare with previous run, write CSV and markdown. |
| `friction_detector/cli.py` | `build-db`, `run-daily`, `replay`. |
| `app/streamlit_app.py` | Four views: Overview, Customer lookup, Daily report, Method and limits. |
| `validation/oracle.py` | Independent plain-Python re-implementation of the rules, used only for testing. |
| `validation/validate.py` | 46 end-to-end checks; writes `validation_results.json` and the backtest CSV. |
| `tests/` | 64 pytest tests. |

## Design decisions

1. **Rules first, transparent.** All thresholds are in `config.py` and are written into the database `config` table at build time, so a run can be audited later.
2. **Windows come from the data.** The 95th percentile of observed completion lags, not a number I picked, decides when a customer counts as stalled.
3. **Contradictions are shown, not resolved.** `data_confidence = LOW` marks customers whose activity log contradicts the funnel record.
4. **Score is separate from category.** Category says *why*; score says *in what order to work*. The score is labelled as a heuristic on every row and every CSV.
5. **Safe by construction.** No module imports an email, SMS, push or broker API. The engine returns tables; the reports module writes files under `outputs/`; the Streamlit app only reads the database and offers downloads. Nothing can place a trade, a deposit or a withdrawal.
6. **LLM optional and minimal.** With no `ANTHROPIC_API_KEY` the rule-based text is used. With a key, only a whitelist of bucketed, de-identified fields is sent (no user ID, city, channel, dates or amounts; counts under 5 suppressed) and any failure falls back to the rule-based text. `FRICTION_DISABLE_LLM=1` is a kill switch. The live API call was **not** exercised in testing; the payload builder, whitelist guard, fallback and a mocked transport were.
7. **CSV safety.** Text cells starting with `=`, `+`, `-` or `@` are prefixed with `'` so spreadsheets do not evaluate them.

## How "newly flagged" works

Each run stores the set of flagged `user_id`s in `friction_snapshot(run_date, user_id, ...)`. A customer is *new* on date D if they are flagged on D and were not in the snapshot of the previous stored run date. The first stored run is a baseline (0 new). Re-running the same date replaces that date's snapshot and run row (idempotent).

## What is not built

No scheduler is installed. To automate, call `python -m friction_detector.cli run-daily --as-of <today>` from cron or launchd; example in the README. There is no authentication, no role-based access, no audit log, no connection to a real CRM or ticketing system, and no outcome tracking. These would be needed before any production use.
