# 03 · Business analytics

Six analysis modules, one folder each, plus summary workbooks. **All data are synthetic** (fictional Indian retail brokerage, 10,000 users, Nov 2025 – Oct 2026, INR, snapshot 2026-10-31).

| Folder | Module | Business question | Key files |
|---|---|---|---|
| [`acquisition/`](acquisition/) | M1 | Where do registrations come from, and what do they cost? | `m1_channel_performance.csv`, `m1_paid_vs_organic.csv`, `m1_registrations_monthly.csv` |
| [`funnel/`](funnel/) | M2 | Where do customers drop between registration and first trade? | `m2_bottlenecks.csv`, `m2_stage_timing_by_*.csv`, `m2_dimension_significance_tests.csv` |
| [`retention_churn/`](retention_churn/) | M3 | Who stays active, who goes quiet? | `m3_cohort_retention_*.csv`, `m3_mau_and_flows_monthly.csv`, `m3_early_warning_model_coefficients.csv` |
| [`segmentation/`](segmentation/) | M4 | Which customer groups need different treatment? | `m4_journey_segment_profile.csv`, `m4_rfm_profile.csv`, `m4_kmeans_*.csv` |
| [`campaign_performance/`](campaign_performance/) | M5 | Which campaigns turn spend into first trades? | `m5_campaign_vs_others_tests.csv`, `m5_budget_reallocation_scenarios.csv` |
| [`customer_support/`](customer_support/) | M6 | How much support demand does onboarding create, and how well is it resolved? | `m6_ticket_categories.csv`, `m6_backlog_ageing.csv`, `m6_csat_*.csv` |

Experiments (M7) and findings (M8) live with the strategy work in [`../07_growth_strategy/phase3_experiments/`](../07_growth_strategy/phase3_experiments/) and [`../07_growth_strategy/phase3_findings/`](../07_growth_strategy/phase3_findings/).

## Other folders

| Folder | Content |
|---|---|
| [`summary/`](summary/) | `Funnel_Analysis.csv`, `Retention_Analysis.csv`, `Campaign_Performance.csv`, `Customer_Segmentation.csv`, `results.json`, `findings_numbers.json`, and `Fintech_Growth_Analytics_Report.xlsx` (10 sheets: KPI definitions, one sheet per module, insights, charts) and `Growth_Experiments.xlsx` |
| [`excel/`](excel/) | `Fintech_Advanced_Excel_Analytics.xlsx` (16 sheets with live formulas; `Phase3_Check` reconciles 114 of 114 values to the Python results) and `Fintech_PivotTables_Demo.xlsx` |
| [`excel_and_report_builders/`](excel_and_report_builders/) | Scripts that built the workbooks and reports (archival; see below) |

## Two files called `Campaign_Performance.csv`

They are different files:

| Path | What it is |
|---|---|
| `../data/cleaned/derived/Campaign_Performance.csv` | Phase 2 derived table: one row per campaign, built during cleaning |
| `summary/Campaign_Performance.csv` | Phase 3 analysis output: the campaign scorecard used in the report |

## How the analysis is produced

`05_python/pipeline/10_phase3_analysis.py` writes the module folders; `11_phase3_experiments_findings.py` writes experiments and findings; `12_phase3_charts.py` writes `../assets/charts/phase3_*.png`. Run from the repository root:

```bash
python3 05_python/pipeline/10_phase3_analysis.py
```

## Workbooks and the legacy folder names

The Excel workbooks and the Word/PDF reports were built before the folders were renamed. They are committed as built, **not regenerated**, so some text inside them still uses the earlier layout. The mapping is:

| Legacy path (text inside the workbooks) | Current path |
|---|---|
| `01_data_raw/` | `data/raw/` |
| `02_data_clean/` | `data/cleaned/` |
| `03_python/` | `05_python/` |
| `05_excel/` | `03_business_analytics/excel/` |
| `07_reports/` | `reports/` |

Only descriptive text cells contain these paths (checked: no formula uses them): `Raw_Data_Reference`, `README`, `PivotTable_Guide` and the data-sheet notes in `Fintech_Advanced_Excel_Analytics.xlsx`, and the `README` sheet of `Fintech_Growth_Analytics_Report.xlsx`. The Word and PDF reports in `../reports/` refer to charts by their original numbered names (for example `01_funnel`), which are now `assets/charts/phase3_c01_funnel.png` and so on.

The builder scripts here were updated to the current layout and syntax-checked (`py_compile`) but were **not re-run**; rebuilding the workbooks needs LibreOffice, and the Word report needs Node.

## Read this before quoting a number

* Funnel and first-trade rates use the mature cohort (registered before October 2026, n = 9,116) unless stated.
* Retention flags and dormancy are **proxies**, not confirmed churn.
* There is no revenue, fee or lifetime-value field, so nothing here reports revenue or ROI.
