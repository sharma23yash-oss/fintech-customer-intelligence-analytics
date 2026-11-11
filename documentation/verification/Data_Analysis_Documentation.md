# Phase 4 - Data Analysis Documentation (SYNTHETIC data)

## 1. Purpose and scope
Turn the Phase 2 cleaned data and Phase 3 findings into reproducible, executable analytics in three tools (Excel, SQL, Python) and prove they agree. Fictional Indian retail brokerage; 10,000 users; Nov 2025 - Oct 2026; INR; snapshot 2026-10-31.

## 2. Data model
| Table | Rows | Grain | Key |
|---|---:|---|---|
| users | 10,000 | one per user | user_id (FK campaign) |
| campaigns | 10 | one per campaign | campaign_id |
| monthly_activity | 64,645 | user x calendar month since registration | (user_id, activity_month) |
| support_tickets | 7,614 | one per ticket | ticket_id (FK user) |

Views: `v_mature_users`, `v_user_journey`, `v_journey_segment`. Raw data are never modified; the cleaning log (13 documented changes) is in Excel's `Raw_Data_Reference` sheet and `02_data_cleaning/cleaning_log.csv`.

## 3. Metric definitions
See README "Key definitions". Additional rules: `*_asof` columns count only events on or before 2026-10-31; `eligible_30d` / `eligible_90d` restrict recency flags to users old enough to be judged; dormancy is defined only for users registered by Jul-2026; repeat trading uses users with at least 4 observed months.

Journey segment rule (identical in SQL view, Python `segmentation.journey_segment` and Excel nested IFS): a user is "in-flight" if their furthest stage is recent relative to the historical maximum lag for that stage (Registered 11 d, KYC 7 d, Bank 14 d, Funded 11 d); otherwise stalled at that stage. Traders are split by recency of first trade (<= 30 d), dormancy (no activity Aug-Oct), and trading months in the last six (>= 4 high, 2-3 repeat, else occasional).

## 4. Module A - Excel workbook (`03_business_analytics/excel/Fintech_Advanced_Excel_Analytics.xlsx`)
Required sheets: Raw_Data_Reference, Cleaned_Users, Campaign_Analysis, Funnel_Analysis, Retention_Analysis, Customer_Segmentation, Support_Analysis, KPI_Summary. Supporting: Phase3_Check, Assumptions, Formula_Guide, XLOOKUP_Demo, PivotTable_Guide, Monthly_Activity_Data, Support_Tickets_Data, README.

| Requirement | Where implemented |
|---|---|
| Excel Tables + structured references | tblUsers, tblActivity, tblTickets, tblCampaigns; every analysis formula |
| XLOOKUP and INDEX-MATCH | INDEX/MATCH: Cleaned_Users[campaign_name], Customer_Segmentation top-25 list; XLOOKUP: XLOOKUP_Demo (Excel 365) |
| SUMIFS / COUNTIFS / AVERAGEIFS | Campaign, Funnel, Retention, Support, KPI_Summary |
| IF / IFS / nested logic | deposit_band, tenure_bucket, journey_segment, cost_flag, sla_flag |
| Date and time | DATEDIF, EDATE, WEEKDAY, Snapshot arithmetic, stage-time medians |
| PivotTables / PivotCharts | Companion `Fintech_PivotTables_Demo.xlsx` (5 PivotTables); PivotCharts: instructions only |
| Conditional formatting | colour scales (retention, conversion), data bars (volume), status fills (MATCH/DIFF) |
| Dynamic KPIs | KPI_Summary selectors (channel, device, date window) with wildcard criteria |
| Segmentation, funnel, CAC, cohort | Customer_Segmentation, Funnel_Analysis (+ Wilson 95% CI), Campaign_Analysis, Retention_Analysis |

Formula-by-formula explanations are on the `Formula_Guide` sheet (22 techniques with where/how/why). Inputs and thresholds live on `Assumptions` as named ranges. Build chain: `16_build_advanced_excel.py` (openpyxl) -> LibreOffice recalculation (0 errors, 129,276 formulas) -> `17_finalize_excel.py`.
Gotchas found and fixed while building: COUNTIFS criteria that start with `<`, `>` or `=` (labels such as ">180d") are parsed as operators - use `"="&cell`; month keys are integers (yyyymm) to avoid text-to-date coercion.

## 5. Module B - SQL (`04_sql/`)
34 queries (`queries_def.py`) cover all 30 requested topics (registrations, monthly acquisition, channel acquisition, campaign CAC, KYC / bank-link / deposit / trade conversion, funnel drop-offs, city, device, MAU, cohort retention, inactivity, churn proxy, repeat trading, segmentation, ticket categories, resolution time, CSAT, campaign ranking, acquisition by month, high-potential customers, deposited-but-inactive, KYC-pending ageing, repeat tickets, channel quality, lifetime activity, monthly trading volume, bottleneck analysis) plus four extras (time-to-first-trade, backlog ageing, support vs dormancy, source reconciliation). Each has SQL, logic, business use and expected output structure in `SQL_Query_Library.md`; executed outputs are in `query_outputs/`. SQLite has no MEDIAN, so medians use the ROW_NUMBER pattern.

## 6. Module C - Python (`05_python/`)
Package `fintech_analytics`: loading, cleaning (18 validation checks), eda, funnel, campaign, cohort, segmentation (rules + K-means), support, kpi_report. `run_pipeline.py` writes tables, charts and `KPI_Report.md`; `build_notebooks.py` creates and executes five notebooks (loading/cleaning/EDA; funnel and campaign; cohort and segmentation; support operations; automated KPI report incl. SQL-vs-Python reconciliation).

## 7. Verification (see `Phase4_Verification_Report.md`)
71 KPI comparisons across SQL, Python, Excel and the validated Phase 3 results all match within stated tolerances (integers exactly). Excel additionally reconciles 114 cells on its own `Phase3_Check` sheet. Python pipeline: 31 / 31 Phase 3 matches. SQL funnel loss shares match Phase 3 once the sixth stage "Active (30d)" is included.

## 8. Findings worth acting on (descriptive; synthetic)
1. KYC is the biggest funnel leak (42.6% of losses) - the strongest case for assisted-verification experiments.
2. Retention decays from 67.6% (M1) to 40.7% (M6), losing roughly 4-9 percentage points each month with no plateau within six months.
3. Funded-but-never-traded users form an activation pool (list on Customer_Segmentation) - nudge test candidates, not a revenue estimate.
4. 563 of the 1,371 unresolved tickets (41%) are older than 90 days; median resolution times are similar across categories (about 9-10 h), so ticket volume (KYC and trading lead) differs more than speed.
5. Channel gaps in first-trade and M3 rates are small; check Phase 3 significance tests before reallocating spend.

## 9. Limitations
See README "Honest limitations". In particular: synthetic data, no revenue or churn label, mixed-source figures indicative, group differences may be statistically insignificant, associations are not causation.
