"""Executes every query in queries_def.py against fintech_analytics.db (SYNTHETIC DATA).
Outputs: query_outputs/Qxx_*.csv, analysis_queries.sql, SQL_Query_Library.md, query_run_log.json
Run: python3 run_queries.py   (build the database first with build_database.py)"""
import json, re, sqlite3, sys
from pathlib import Path
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from queries_def import Q  # noqa: E402

con = sqlite3.connect(HERE / "fintech_analytics.db")
out_dir = HERE / "query_outputs"
out_dir.mkdir(exist_ok=True)
for f in out_dir.glob("*.csv"):
    f.unlink()

log, md, sql_file = [], [], []


def slug(s):
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")[:45]


def fmt_table(df, n=8):
    d = df.head(n).copy()
    d = d.astype(object).where(d.notna(), "NULL")
    cols = list(d.columns)
    lines = ["| " + " | ".join(cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for r in d.itertuples(index=False):
        lines.append("| " + " | ".join(str(v) for v in r) + " |")
    return "\n".join(lines)


for q in Q:
    df = pd.read_sql_query(q["sql"], con)
    fn = f"{q['id']}_{slug(q['title'])}.csv"
    df.to_csv(out_dir / fn, index=False)
    log.append(dict(id=q["id"], title=q["title"], rows=len(df), cols=list(df.columns), file=fn))
    sql_file.append(f"-- {'=' * 90}\n-- {q['id']}: {q['title']}   [{q['topic']}]\n-- Logic    : {q['logic']}\n-- Business : {q['business']}\n"
                    f"-- Output   : {q['output']}\n-- {'=' * 90}\n{q['sql'].rstrip(';')};\n")
    md.append(f"### {q['id']} — {q['title']}\n\n**Topic covered:** {q['topic']}\n\n```sql\n{q['sql']}\n```\n\n"
              f"**Logic.** {q['logic']}\n\n**Business use.** {q['business']}\n\n**Expected output structure.** {q['output']}\n\n"
              f"**Actual output on the synthetic database** ({len(df)} row(s) × {len(df.columns)} columns; first rows):\n\n{fmt_table(df)}\n\n"
              f"*CSV: `04_sql/query_outputs/{fn}`*\n\n---\n")

header_sql = ("-- Fintech Growth Analytics - SQL Query Library (SQLite). ALL DATA ARE SYNTHETIC.\n"
              "-- Database: fintech_analytics.db  (build with build_database.py). Snapshot date: 2026-10-31.\n"
              "-- Run all: python3 run_queries.py   |   or open this file in DB Browser for SQLite / the sqlite3 shell (sqlite3 fintech_analytics.db < analysis_queries.sql).\n"
              "-- Mature cohort = registered before 2026-10 (funnel_mature = 1, n = 9,116). Retention flags are PROXIES, not confirmed churn.\n\n")
(HERE / "analysis_queries.sql").write_text(header_sql + "\n".join(sql_file))

topics = ", ".join(sorted({q["topic"] for q in Q}))
intro = ("# SQL Query Library — Fintech Growth Analytics (SQLite)\n\n"
         "> **All data are synthetic** (fictional Indian retail brokerage, 10,000 users, Nov 2025 – Oct 2026, INR; snapshot 2026-10-31). "
         "No real company data are used.\n\n"
         f"**{len(Q)} queries**, each with SQL, logic, business use, expected output structure and the actual output from the database.\n\n"
         "## Database model\n\n"
         "| Table | Grain | Rows | Key |\n|---|---|---|---|\n"
         "| `campaigns` | one row per acquisition campaign | 10 | `campaign_id` |\n"
         "| `users` | one row per registered user (funnel flags, derived metrics) | 10,000 | `user_id` → `campaigns` |\n"
         "| `monthly_activity` | one row per user per calendar month since registration | 64,645 | (`user_id`, `activity_month`) |\n"
         "| `support_tickets` | one row per ticket | 7,614 | `ticket_id` → `users` |\n\n"
         "Views: `v_mature_users`, `v_user_journey`, `v_journey_segment` (Phase 3 journey-segment rule).\n\n"
         "## Conventions (read before reusing a query)\n\n"
         "- **Mature cohort** (`funnel_mature = 1`, 9,116 users) is used for every funnel/conversion rate; the Oct-2026 cohort (884) is immature.\n"
         "- **Source of truth:** `users` for funnel/CAC/conversion; `monthly_activity` for MAU, retention, repeat trading. The two sources disagree for many users (see Q34), so mixed-source figures are indicative only.\n"
         "- **Retention M1/M3/M6** = share active in calendar month k after the registration month (a proxy, not exact 30/90/180 days). "
         "**Dormant 3m** / **inactive 90d** are churn **proxies**.\n"
         "- **CAC** = recorded campaign spend ÷ registered users; organic campaigns have no recorded spend, so CAC is `NULL`. No revenue or ROI is computed.\n"
         "- SQLite has no `MEDIAN`; medians use `ROW_NUMBER()` windows.\n\n"
         f"## Topic coverage\n\n{topics}.\n\n---\n\n## Queries\n\n")
(HERE / "SQL_Query_Library.md").write_text(intro + "\n".join(md))
(HERE / "query_run_log.json").write_text(json.dumps(log, indent=1))
print(f"{len(Q)} queries executed; outputs -> {out_dir}")
for l in log:
    print(f"{l['id']} rows={l['rows']:>3} cols={len(l['cols']):>2}  {l['title']}")
