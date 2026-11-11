# Dashboard Validation Checklist

Synthetic data. After building the report, put each context on a card (or a table visual) and compare with the expected value. A difference means a DAX or model error, not a data difference, because the expected values were computed independently in pandas on the same star-schema CSVs and matched to Phase 3 / Phase 4 / SQL (see `validation/Phase5_Measure_Verification.md`).

Context names: `channel=Referral` means the Channel slicer = Referral; `segment=9` means DimSegment segment 09; `months=Aug 26` means the Month slicer = Aug 26 only.

| # | Slicer context | Measure | Expected |
|---|---|---|---|
| 1 | no filters | Registered Customers | 10,000 |
| 2 | no filters | KYC Completion Rate | 70.5% |
| 3 | no filters | First Trade Activation Rate | 38.0% |
| 4 | no filters | MAU | 4,611 |
| 5 | no filters | 30-Day Retention | 54.0% |
| 6 | no filters | CAC | 331.2 |
| 7 | no filters | Total Campaign Spend | 2,690,000 |
| 8 | no filters | Median Paid Cost per KYC | 523 |
| 9 | no filters | Median Paid Cost per First Trade | 1,052 |
| 10 | no filters | M1 Retention | 67.58% |
| 11 | no filters | M3 Retention | 56.01% |
| 12 | no filters | M6 Retention | 40.71% |
| 13 | no filters | Inactive 90d Rate | 14.9% |
| 14 | no filters | Dormant 3m Rate | 22.0% |
| 15 | no filters | Repeat Trader Share | 69.3% |
| 16 | no filters | Tickets | 7,614 |
| 17 | no filters | Tickets per 1000 Customers | 761 |
| 18 | no filters | Resolved Rate | 82.0% |
| 19 | no filters | Escalation Rate | 6.29% |
| 20 | no filters | Median Resolution Hours | 9.4 |
| 21 | no filters | P90 Resolution Hours | 20.4 |
| 22 | no filters | Within SLA Rate | 94.3% |
| 23 | no filters | CSAT | 3.83 |
| 24 | no filters | Backlog over 90 Days | 563 |
| 25 | channel=Referral | Registered Customers | 1,036 |
| 26 | channel=Referral | First Trade Activation Rate | 52.9% |
| 27 | channel=Referral | CAC | 231.7 |
| 28 | channel=Referral | M3 Retention | 61.20% |
| 29 | campaign=CMP04 | Registered Customers | 1,168 |
| 30 | campaign=CMP04 | CAC | 385.3 |
| 31 | campaign=CMP04 | Cost per KYC | 587 |
| 32 | campaign=CMP04 | Cost per First Trade | 1,252 |
| 33 | campaign=CMP04 | Tickets | 892 |
| 34 | campaign=CMP07 | Registered Customers | 1,174 |
| 35 | campaign=CMP07 | CAC | (blank) |
| 36 | city=Pune, device=Android | Registered Customers | 572 |
| 37 | city=Pune, device=Android | MAU | 248 |
| 38 | city=Pune, device=Android | Tickets | 446 |
| 39 | segment=9 | Registered Customers | 352 |
| 40 | segment=9 | First Trade Activation Rate | 100.0% |
| 41 | segment=9 | Tickets | 206 |
| 42 | months=Aug 26 | Registered Customers | 850 |
| 43 | months=Aug 26 | MAU | 4,135 |
| 44 | months=Aug 26 | Tickets | 1,026 |
| 45 | months=Aug 26 | Tickets per 1000 Customers | 124 |
| 46 | months=Aug 26 | Registrations MoM % | 0.0% |

## Funnel (mature cohort, no filters)

| Stage | Users |
|---|---|
| Registered | 9,116 |
| KYC Completed | 6,429 |
| Bank Linked | 5,645 |
| First Deposit | 4,340 |
| First Trade | 3,462 |
| Active (30d) | 2,808 |

## Budget indicators (no filters, paid campaigns)

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

The complete table (231 measure x context checks) is `validation/DAX_Oracle_Expected_Values.csv`.
