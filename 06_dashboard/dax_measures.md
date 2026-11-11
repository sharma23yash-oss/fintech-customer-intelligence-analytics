# DAX measures

The full library lives in [`dax/`](dax/); this page is the map.

> **Verification status.** The 117 measures have **not been executed in a DAX engine** (Power BI Desktop was unavailable). Their logic was re-implemented in pandas and matched against validated figures (231 of 231 comparisons; 87 measures directly checked). See [`dashboard_documentation.md`](dashboard_documentation.md).

| File | Content |
|---|---|
| [`dax/DAX_Measure_Library.md`](dax/DAX_Measure_Library.md) | Every measure with purpose, definition, DAX and notes, grouped by display folder |
| [`dax/Measure_Library.dax`](dax/Measure_Library.dax) | The same measures as plain DAX, ready to paste into a `_Measures` table |
| [`dax/DimDate.dax`](dax/DimDate.dax) | Calculated date table |

## Display folders

| Folder | Measures | Examples |
|---|---|---|
| 00 Parameters | 6 | Snapshot Date, SLA Hours, Efficient / Costly Index Thresholds |
| 01 Customers and Funnel | 26 | Registered Customers, Mature Customers, KYC Completion Rate, First Trade Activation Rate, Funnel Step Conversion, Funnel Drop-off Rate |
| 02 Acquisition and Marketing | 24 | CAC, Cost per First Trade, Cost Efficiency Index, Budget Signal, Evidence Strength |
| 03 Retention and Engagement | 26 | Cohort Retention, MAU, Inactive 90d Rate, Dormant 3m Rate, Repeat Trader Share, trading volume in INR |
| 04 Time Intelligence | 10 | Registrations MoM %, 3-month average, YTD and prior-month helpers |
| 05 Customer Operations | 22 | Tickets, Median Resolution Hours, CSAT, Within SLA Rate, Backlog over 90 Days |
| 06 Labels and Notes | 3 | Data disclaimer, proxy note, mature-cohort note |

## Conventions

* Rates carry their denominator in the name (for example "Mature KYC Users" vs "Registered Customers").
* Funnel and first-trade measures use the mature cohort (registered before October 2026).
* Cost measures use recorded campaign spend only; organic cost is blank, not zero.
* "Inactive 90d" and "Dormant 3m" are proxies, not confirmed churn.
* No measure reports revenue or ROI, because the data has none. Trading value is customer trading volume, not brokerage income.
