# Data

**Every record in this repository is synthetic.** The dataset describes a fictional Indian retail brokerage: 10,000 customers, November 2025 – October 2026, amounts in INR, snapshot date 2026-10-31. It is not data from any real broker, bank or person, and no real customer is represented.

| Path | Content | Notes |
|---|---|---|
| [`raw/Fintech_Users_10000_Synthetic.csv`](raw/Fintech_Users_10000_Synthetic.csv) | Original users table as received | Read-only input. Never edited. |
| [`raw/Fintech_Brokerage_Customer_Analytics_Synthetic_Project.xlsx`](raw/Fintech_Brokerage_Customer_Analytics_Synthetic_Project.xlsx) | Original workbook (10 sheets: users, monthly activity, support tickets, campaigns, cohort retention, funnel and analysis summaries, data dictionary, KPI definitions) | Read-only input. |
| [`cleaned/`](cleaned/) | `Cleaned_Users.csv`, `Cleaned_Monthly_Activity.csv`, `Cleaned_Support_Tickets.csv`, `Cleaned_Campaigns.csv` | Output of `02_data_cleaning/`. Adds `*_asof` flags, maturity and eligibility columns. |
| [`cleaned/derived/`](cleaned/derived/) | `Customer_Funnel.csv`, `Customer_Cohorts.csv`, `Customer_Segments.csv`, `Campaign_Performance.csv` | Derived tables. |
| [`data_dictionary.csv`](data_dictionary.csv) | Column-level dictionary: table, column, type, origin, null %, description | Readable version: [`../documentation/data_dictionary.md`](../documentation/data_dictionary.md) |

## Things to know

* Cleaning never overwrites `raw/`; every change is listed in [`../02_data_cleaning/cleaning_log.csv`](../02_data_cleaning/cleaning_log.csv).
* The dataset has **no revenue, fee, brokerage-income or lifetime-value fields**, so no analysis in this repository reports revenue or ROI.
* Marketing spend is recorded per campaign, undated. Organic has no spend.
* The monthly activity log and the funnel dates disagree for some users; this is flagged, not corrected ([`../documentation/data_quality_report.md`](../documentation/data_quality_report.md)).
* Full provenance and limitations: [`../documentation/limitations.md`](../documentation/limitations.md).
