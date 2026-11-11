# Phase 5 - DAX measure verification (oracle)

SYNTHETIC data. Power BI Desktop is not available in this environment, so the DAX itself has **not been executed**. Each measure's logic was re-implemented in pandas on the same star-schema CSVs and filter semantics, then checked against validated Phase 3/4 figures and independent SQL.

**231 / 231 oracle comparisons match.** Measures with at least one oracle check: **87 of 117**.

Measures without a direct oracle check (formatting/label measures, parameters, or those that need the Power BI engine, e.g. RANKX): Snapshot Date, SLA Hours, Efficient Index Threshold, Costly Index Threshold, Repeat Base Months, Repeat Trader Min Months, KYC Rate (Paid, Full Period), First Trade Rate (Paid, Full Period), Registration Share, Spend Share, City Share of Registrations, Device Share of Registrations, Rank Cost per First Trade (Paid), Rank First Trade Rate, Budget Signal, Evidence Strength, Phase 3 Scorecard Tier, Phase 3 Overall Score, CAC Scope Note, Segment Share, Registered Customers PM, MAU PM, Tickets PM, Tickets MoM %, Trading Value INR mn PM, Trading Value MoM %, Category Share, Mature Cohort Note, Data Disclaimer, Proxy Note

Paid-campaign budget indicator (expected on-screen values):

| campaign   |   cost_per_first_trade_inr |   rank_asc |   index_vs_median | budget_signal   |
|:-----------|---------------------------:|-----------:|------------------:|:----------------|
| CMP01      |                     1085.4 |          6 |             0.969 | In line         |
| CMP02      |                     1051.4 |          4 |             1     | In line         |
| CMP03      |                      920.8 |          3 |             1.142 | In line         |
| CMP04      |                     1251.8 |          8 |             0.84  | Costly          |
| CMP05      |                      438   |          1 |             2.401 | Efficient       |
| CMP06      |                     1216.2 |          7 |             0.865 | In line         |
| CMP09      |                     1051.8 |          5 |             1     | In line         |
| CMP10      |                      472.1 |          2 |             2.228 | Efficient       |

After building the model in Power BI Desktop, compare any card with `DAX_Oracle_Expected_Values.csv` (same measure name + context). A difference there means a DAX or model error, not a data difference.
