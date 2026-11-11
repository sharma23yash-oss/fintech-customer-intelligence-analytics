# 04 · SQL analytics (SQLite)

34 analytical queries over the cleaned synthetic data. **All data are synthetic.**

| File | Purpose |
|---|---|
| [`schema.sql`](schema.sql) | Four tables (`users`, `monthly_activity`, `support_tickets`, `campaigns`), indexes and three helper views |
| [`build_database.py`](build_database.py) | Builds `fintech_analytics.db` from `../data/cleaned/Cleaned_*.csv` (idempotent: deletes and recreates) |
| [`queries_def.py`](queries_def.py) | The 34 queries as named, commented definitions (the single source of truth) |
| [`run_queries.py`](run_queries.py) | Executes every query, writes `query_outputs/Qxx_*.csv`, `analysis_queries.sql`, `SQL_Query_Library.md`, `query_run_log.json` |
| [`analysis_queries.sql`](analysis_queries.sql) | **The readable query file**: all 34 queries with a business question above each |
| [`SQL_Query_Library.md`](SQL_Query_Library.md) | Same queries with the result of each, as a catalogue |
| [`query_outputs/`](query_outputs/) | One CSV per query result (committed so results can be read without running anything) |

## Dialect

**SQLite.** It was chosen because it needs no server and runs from the Python standard library. The queries use ANSI SQL plus a few SQLite details (`julianday` date arithmetic, window functions available in SQLite 3.25+). A median is computed with window functions because SQLite has no `MEDIAN()`. Moving to PostgreSQL or MySQL needs small edits (date functions mainly).

## Run

```bash
python3 04_sql/build_database.py     # creates 04_sql/fintech_analytics.db (git-ignored, rebuilt on demand)
python3 04_sql/run_queries.py        # runs all 34 queries and rewrites the outputs
```

The `sqlite3` command-line tool is not required. To explore interactively with it, if you have it: `sqlite3 04_sql/fintech_analytics.db`.

## Coverage

Registrations and monthly acquisition; channel, device and city performance; KYC, bank-link, deposit and first-trade conversion; funnel drop-off; campaign CAC and cost per first trader; MAU (new vs existing); cohort retention M0–M6; inactivity buckets and a dormant-three-months proxy; repeat trading; support categories, resolution time, CSAT, backlog ageing and repeated tickets; journey segments; source reconciliation between tables.

## Verification

The headline KPIs from these queries match the Python pipeline and the Excel workbooks: 71 of 71 KPI comparisons agree (see [`../documentation/verification/Phase4_Verification_Report.md`](../documentation/verification/Phase4_Verification_Report.md)).

## Notes

* Rates are stated with their denominators; the "mature cohort" (registered before October 2026, so each user has had time to convert; n = 9,116) is used for funnel and first-trade rates.
* Inactivity and dormancy are **proxies**, not confirmed churn.
* No revenue, fee or lifetime-value columns exist, so no query reports revenue or ROI.
