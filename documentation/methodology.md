# Methodology

How the project moves from a raw synthetic extract to recommendations. **All data are synthetic.**

## Principles

1. **Raw data is read-only.** Cleaning writes new files; every change is logged ([`../02_data_cleaning/cleaning_log.csv`](../02_data_cleaning/cleaning_log.csv)).
2. **Label every number.** Each KPI is tagged actual, proxy, analyst-defined, scenario or assumption ([`KPI_definitions.md`](KPI_definitions.md)).
3. **State the denominator.** Funnel rates use the mature cohort; retention uses users old enough to observe the month.
4. **Prove it twice.** Headline KPIs are computed independently in SQL, Python and Excel and compared (71 of 71 match).
5. **Don't claim what the data can't carry.** No revenue, ROI or confirmed churn.

## Pipeline

| Step | What happens | Where |
|---|---|---|
| 1 Audit | Inventory, integrity checks, eight findings (F1–F8) that decide the treatments | [`../01_data_audit/`](../01_data_audit/) |
| 2 Clean | 13 logged changes: as-of flags to remove future information, maturity and eligibility columns, adjusted last-active date, boolean and date normalisation, organic CAC left undefined | [`../02_data_cleaning/`](../02_data_cleaning/) |
| 3 Analyse | Six modules: acquisition, funnel, retention/churn, segmentation, campaigns, support | [`../03_business_analytics/`](../03_business_analytics/) |
| 4 Verify | 34 SQL queries, a Python package and pipeline, Excel with live formulas; cross-checked | [`../04_sql/`](../04_sql/), [`../05_python/`](../05_python/), [`../documentation/verification/`](verification/) |
| 5 Visualise | Star schema, 117 DAX measures, Power Query, four-page design (kit and mockups only) | [`../06_dashboard/`](../06_dashboard/) |
| 6 Recommend | 15 recommendations, 10 proposed experiments, 30-60-90 roadmap, budget scenarios | [`../07_growth_strategy/`](../07_growth_strategy/) |
| 7 Operationalise | Friction Detector: rules, score, daily report, Streamlit app | [`../08_ai_friction_detector/`](../08_ai_friction_detector/) |

## Key analytical decisions

* **Mature cohort.** Users registered in October 2026 have not had time to convert, so including them understates conversion (on the source flags the October cohort showed 40.0 % first-trade conversion, which was future information; as of the snapshot it is 8.4 %). Funnel rates use the 9,116 users registered Nov 2025 – Sep 2026.
* **As-of flags.** 388 users had completion flags that included events after 2026-10-31; `*_asof` columns count only events up to the snapshot.
* **Organic CAC is undefined, not zero.** Organic activity has hidden costs the data does not record.
* **Cost per first trade** (CAC ÷ mature first-trade rate) is the main cost-efficiency measure, because KYC completion alone is not value to a brokerage.
* **Retention** uses calendar months from the activity table. Inactivity and dormancy are described as proxies throughout.
* **Statistics.** Wilson intervals for rates; chi-square for category differences; Holm adjustment when comparing campaigns; Mantel–Haenszel for the support–dormancy association; Kruskal–Wallis for priority vs resolution time.
* **Segmentation.** Ten rule-based journey segments (explainable) compared with k-means (k = 4, silhouette 0.33, bootstrap-stability adjusted Rand index 0.85; the silhouette-best k = 2 scores 0.37) and RFM profiles; the rule-based segments are used for action.
* **Prediction.** A logistic regression early-warning model was tried for month-3 retention; AUC 0.57 means it is not useful, and the result is reported as such.
* **Experiments.** Sample size by the two-proportion formula (α 0.05 two-sided, power 80 %), with sensitivity if the effect is halved or 1.5× larger. Nothing was run.

## Verification

| Check | Result |
|---|---|
| Python KPI report vs Phase 3 results | 31 of 31 match |
| SQL vs Python vs Excel headline KPIs | 71 of 71 match ([`verification/Phase4_Verification_Report.md`](verification/Phase4_Verification_Report.md)) |
| Excel `Phase3_Check` sheet | 114 of 114 |
| Dashboard model integrity | 27 of 27 |
| DAX logic vs pandas oracle | 231 of 231 comparisons (87 of 117 measures directly) |
| Strategy evidence vs Phase 3 | 14 of 14 |
| Friction Detector | 64 unit tests, 46 validation checks |

## Reproducing

See "How to reproduce" in the main [`README`](../README.md).
