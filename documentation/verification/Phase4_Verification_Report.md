# Phase 4 verification report (SYNTHETIC data)

Three independent implementations of the same KPIs - SQL (SQLite), Python (pandas) and Excel (live formulas, LibreOffice-recalculated) - are compared with each other and with the validated Phase 3 results.

**Result: 71 / 71 KPI comparisons match** (tolerances shown; integers must match exactly).
Excel's own Phase3_Check sheet reports **114 / 114** reconciled cells.

SQL query library: 34 queries executed - see `04_sql/query_run_log.json`.

| KPI | SQL | Python | Excel | Phase 3 | Max abs diff | Tol. | Status |
|---|---:|---:|---:|---:|---:|---:|:--:|
| Total registrations | 10,000 | 10,000 | 10,000 | 10,000 | 0.000000 | 0 | MATCH |
| Mature users | 9,116 | 9,116 | 9,116 | 9,116 | 0.000000 | 0 | MATCH |
| Funnel reached: KYC completed | 6,429 | 6,429 | 6,429 | 6,429 | 0.000000 | 0 | MATCH |
| Funnel reached: Bank linked | 5,645 | 5,645 | 5,645 | 5,645 | 0.000000 | 0 | MATCH |
| Funnel reached: First deposit | 4,340 | 4,340 | 4,340 | 4,340 | 0.000000 | 0 | MATCH |
| Funnel reached: First trade | 3,462 | 3,462 | 3,462 | 3,462 | 0.000000 | 0 | MATCH |
| Funnel: Active (30d) first traders | 2,808 | 2,808 | 2,808 | - | 0.000000 | 0 | MATCH |
| Step conversion: KYC completion | 0.7052 | 0.7052 | 0.7052 | 0.7052 | 0.000044 | 6e-05 | MATCH |
| Step conversion: Bank-link conversion | 0.8781 | 0.8781 | 0.8781 | 0.8781 | 0.000047 | 6e-05 | MATCH |
| Step conversion: First-deposit conversion | 0.7688 | 0.7688 | 0.7688 | 0.7688 | 0.000022 | 6e-05 | MATCH |
| Step conversion: First-trade activation | 0.7977 | 0.7977 | 0.7977 | 0.7977 | 0.000004 | 6e-05 | MATCH |
| Registered -> first trade (mature) | 0.3798 | 0.3798 | 0.3798 | 0.3798 | 0.000028 | 6e-05 | MATCH |
| M1 retention (pooled) | 0.6758 | 0.6758 | 0.6758 | 0.6758 | 0.000000 | 1e-09 | MATCH |
| M3 retention (pooled) | 0.5601 | 0.5601 | 0.5601 | 0.5601 | 0.000000 | 1e-09 | MATCH |
| M6 retention (pooled) | 0.4071 | 0.4071 | 0.4071 | 0.4071 | 0.000000 | 1e-09 | MATCH |
| MAU, Oct-2026 | 4,611 | 4,611 | 4,611 | 4,611 | 0.000000 | 0 | MATCH |
| MAU, Nov-2025 | 642 | 642 | 642 | 642 | 0.000000 | 0 | MATCH |
| Active in last 30 days | 0.5400 | 0.5400 | 0.5400 | 0.5400 | 0.000000 | 1e-09 | MATCH |
| Inactive > 90 days (proxy) | 0.1487 | 0.1487 | 0.1487 | 0.1487 | 0.000000 | 1e-09 | MATCH |
| Dormant 3 months (proxy) | 0.2195 | 0.2195 | 0.2195 | 0.2195 | 0.000000 | 1e-09 | MATCH |
| Repeat-trading base users | 7,434 | 7,434 | 7,434 | 7,434 | 0.000000 | 0 | MATCH |
| Repeat traders % of ever-traders | 0.6929 | 0.6929 | 0.6929 | 0.6929 | 0.000000 | 1e-09 | MATCH |
| Tickets | 7,614 | 7,614 | 7,614 | 7,614 | 0.000000 | 0 | MATCH |
| Tickets per 1,000 users | 761.4000 | 761.4000 | 761.4000 | 761.4000 | 0.000000 | 0.05 | MATCH |
| Resolved share | 0.8199 | 0.8199 | 0.8199 | 0.8199 | 0.000000 | 6e-05 | MATCH |
| Open tickets | 892 | 892 | 892 | 892 | 0.000000 | 0 | MATCH |
| Escalated tickets | 479 | 479 | 479 | 479 | 0.000000 | 0 | MATCH |
| Mean resolution (h) | 10.8884 | 10.8884 | 10.8884 | 10.8884 | 0.000000 | 0.001 | MATCH |
| Median resolution (h) | 9.4000 | 9.4000 | 9.4000 | 9.4000 | 0.000000 | 0.05 | MATCH |
| CSAT mean | 3.8267 | 3.8267 | 3.8267 | 3.8267 | 0.000000 | 0.0005 | MATCH |
| Unresolved tickets (open + escalated) | 1,371 | 1,371 | 1,371 | 1,371 | 0.000000 | 0 | MATCH |
| Backlog ageing total (Excel table) = unresolved | 1,371 | 1,371 | 1,371 | 1,371 | 0.000000 | 0 | MATCH |
| Registrations: Paid Search | 2,644 | 2,644 | - | 2,644 | 0.000000 | 0 | MATCH |
| Registrations: Paid Social | 2,544 | 2,544 | - | 2,544 | 0.000000 | 0 | MATCH |
| Registrations: Organic | 1,878 | 1,878 | - | 1,878 | 0.000000 | 0 | MATCH |
| Registrations: Referral | 1,036 | 1,036 | - | 1,036 | 0.000000 | 0 | MATCH |
| Registrations: Affiliate | 757 | 757 | - | 757 | 0.000000 | 0 | MATCH |
| Registrations: Partnerships | 580 | 580 | - | 580 | 0.000000 | 0 | MATCH |
| Registrations: CRM | 561 | 561 | - | 561 | 0.000000 | 0 | MATCH |
| First-trade rate (mature): Organic | 0.4715 | - | 0.4715 | 0.4715 | 0.000000 | 6e-05 | MATCH |
| M3 retention: Organic | 0.6036 | - | 0.6036 | 0.6036 | 0.000000 | 6e-05 | MATCH |
| First-trade rate (mature): Referral | 0.5289 | - | 0.5289 | 0.5289 | 0.000000 | 6e-05 | MATCH |
| M3 retention: Referral | 0.6120 | - | 0.6120 | 0.6120 | 0.000000 | 6e-05 | MATCH |
| First-trade rate (mature): CRM | 0.3398 | - | 0.3398 | 0.3398 | 0.000000 | 6e-05 | MATCH |
| M3 retention: CRM | 0.5597 | - | 0.5597 | 0.5597 | 0.000000 | 6e-05 | MATCH |
| First-trade rate (mature): Paid Search | 0.3658 | - | 0.3658 | 0.3658 | 0.000000 | 6e-05 | MATCH |
| M3 retention: Paid Search | 0.5455 | - | 0.5455 | 0.5455 | 0.000000 | 6e-05 | MATCH |
| First-trade rate (mature): Paid Social | 0.3035 | - | 0.3035 | 0.3035 | 0.000000 | 6e-05 | MATCH |
| M3 retention: Paid Social | 0.5406 | - | 0.5406 | 0.5406 | 0.000000 | 6e-05 | MATCH |
| First-trade rate (mature): Affiliate | 0.3367 | - | 0.3367 | 0.3367 | 0.000000 | 6e-05 | MATCH |
| M3 retention: Affiliate | 0.5435 | - | 0.5435 | 0.5435 | 0.000000 | 6e-05 | MATCH |
| First-trade rate (mature): Partnerships | 0.3114 | - | 0.3114 | 0.3114 | 0.000000 | 6e-05 | MATCH |
| M3 retention: Partnerships | 0.5077 | - | 0.5077 | 0.5077 | 0.000000 | 6e-05 | MATCH |
| CAC (INR): CMP01 | 384.9679 | - | 384.9679 | 384.9679 | 0.000019 | 0.01 | MATCH |
| CAC (INR): CMP02 | 392.7882 | - | 392.7882 | 392.7882 | 0.000048 | 0.01 | MATCH |
| CAC (INR): CMP03 | 276.1628 | - | 276.1628 | 276.1628 | 0.000009 | 0.01 | MATCH |
| CAC (INR): CMP04 | 385.2740 | - | 385.2740 | 385.2740 | 0.000027 | 0.01 | MATCH |
| CAC (INR): CMP05 | 231.6602 | - | 231.6602 | 231.6602 | 0.000032 | 0.01 | MATCH |
| CAC (INR): CMP06 | 409.5112 | - | 409.5112 | 409.5112 | 0.000029 | 0.01 | MATCH |
| CAC (INR): CMP09 | 327.5862 | - | 327.5862 | 327.5862 | 0.000007 | 0.01 | MATCH |
| CAC (INR): CMP10 | 160.4278 | - | 160.4278 | 160.4278 | 0.000007 | 0.01 | MATCH |
| Journey segment: 01 New / in-flight onboarding | 601 | - | 601 | 601 | 0.000000 | 0 | MATCH |
| Journey segment: 02 KYC-pending (stalled) | 2,831 | - | 2,831 | 2,831 | 0.000000 | 0 | MATCH |
| Journey segment: 03 Bank-link pending (stalled) | 818 | - | 818 | 818 | 0.000000 | 0 | MATCH |
| Journey segment: 04 Deposit-pending (stalled) | 1,333 | - | 1,333 | 1,333 | 0.000000 | 0 | MATCH |
| Journey segment: 05 Deposited, never traded (stalle | 881 | - | 881 | 881 | 0.000000 | 0 | MATCH |
| Journey segment: 06 First-time trader (<=30d since  | 317 | - | 317 | 317 | 0.000000 | 0 | MATCH |
| Journey segment: 07 Repeat trader (2-3 trading mont | 1,684 | - | 1,684 | 1,684 | 0.000000 | 0 | MATCH |
| Journey segment: 08 High-engagement trader (>=4 tra | 896 | - | 896 | 896 | 0.000000 | 0 | MATCH |
| Journey segment: 09 Inactive trader (no activity Au | 352 | - | 352 | 352 | 0.000000 | 0 | MATCH |
| Journey segment: 10 Occasional trader (0-1 trading  | 287 | - | 287 | 287 | 0.000000 | 0 | MATCH |

Notes
- Phase 3 stored some step conversions and rates rounded to 4 decimals, hence tolerances of 6e-5.
- '-' means that implementation does not report that figure (e.g. Python pipeline has no per-channel M3 in kpi_values; the full Python tables are in `05_python/outputs/tables`).
- Funnel 'Active (30d)' has no stored Phase 3 reference in results.json; SQL/Python/Excel are compared with each other (loss shares are verified in Phase 3's Funnel_Analysis.csv by the SQL Q09/Q30 outputs).