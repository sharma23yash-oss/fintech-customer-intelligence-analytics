# Power BI build kit and design mockups (no .pbix yet)

**All data are synthetic**: a fictional Indian retail brokerage (10,000 customers, Nov 2025 - Oct 2026, INR, snapshot 2026-10-31). Nothing here is real Groww, moomoo, Futu or Zerodha data. The data contains no revenue, so no ROI or lifetime value is shown.

> **Status (read this first).** This folder contains everything needed to build the dashboard in Power BI Desktop - star-schema data, 117 DAX measures, Power Query scripts, themes, page specifications and a validation sheet. **No `.pbix` file has been generated**: Power BI Desktop is not available in the build environment, and a PBIX cannot be produced without it. The PNG files in `mockups/` are static renderings of the intended design, **not Power BI screenshots**. The DAX has not been run in a DAX engine; its logic was checked with a pandas re-implementation (231 of 231 comparisons match validated Phase 3 / Phase 4 figures and independent SQL).

## Deliverables

| # | Requested | Delivered | Status |
|---|---|---|---|
| 1 | Dashboard design specification | `docs/Dashboard_Design_Specification.md` | complete |
| 2 | Power BI data model | `docs/Data_Model.md`, `mockups/Data_Model_Star_Schema.png`, `data/*.csv` (8 tables), `validation/model_integrity_checks.csv` | complete; 27/27 integrity checks pass |
| 3 | DAX measure library | `dax/DAX_Measure_Library.md`, `dax/Measure_Library.dax`, `dax/DimDate.dax` (117 measures, 7 folders) | complete; logic verified in pandas, **not executed in a DAX engine** |
| 4 | Power Query transformation instructions | `power_query/` (8 queries + parameter + guide) | complete; not executed in Power BI |
| 5 | Dashboard screenshots or mockups | `mockups/Page1..4_*.png`, `Data_Model_Star_Schema.png` | **mockups only**, not Power BI screenshots |
| 6 | Power BI implementation guide | `docs/Implementation_Guide.md`, `docs/Validation_Checklist.md` | complete |
| 7 | PBIX file | - | **not generated** (Power BI Desktop unavailable here) |
| extra | Themes (light and navy) | `theme/` | palettes validated |
| extra | TMDL semantic-model scaffold | `tmdl_scaffold/` | **untested** |

## Verification

* `06_dashboard/build_scripts/verify_phase5.py` re-implements the measure logic in pandas under filter contexts (no filter, channel, campaign, city + device, segment, month) and compares with Phase 3 results, Phase 4 Excel values and independent SQL: **231 of 231 match** (`validation/Phase5_Measure_Verification.md`).
* One defect was found and fixed through this check: the inactivity-distribution measure had used the 90-day-eligible base; Phase 3 (and now the measure) uses the 30-day-eligible base.
* A further defect was fixed in review: documentation claimed an inactive relationship was used by cohort measures; no measure uses it, so the relationship was removed (15 relationships remain).
* Not oracle-tested (30 of 117 measures): parameters, text/label measures, shares, ranks and time-intelligence helpers that depend on the Power BI engine. They are simple wrappers over tested measures.

## Headline numbers (traceable to the checklist)

| Measure | Value |
|---|---|
| Registered customers | 10,000 |
| KYC completion (mature cohort) | 70.5% |
| First-trade activation | 38.0% |
| MAU Oct 2026 | 4,611 (46.1% of customers) |
| 30-day retention | 54.0% |
| Blended CAC (paid) | Rs 331.2 |
| Total campaign spend | Rs 2,690,000 |
| Support tickets | 7,614 (761.4 per 1,000 customers) |
| CSAT | 3.83 |

## Limitations (stated plainly)

* No PBIX; no Power BI Desktop screenshots; DAX and M not run in Power BI.
* Spend is undated, so cost measures ignore date, city, device and segment filters.
* Segments are a snapshot as of 2026-10-31.
* Inactive 90d and Dormant 3m are churn proxies, not confirmed churn.
* Budget indicators are directional and not ROI; campaign differences are observational associations in synthetic data.

## Rebuild the artifacts

```bash
python3 06_dashboard/build_scripts/19_build_powerbi_model_data.py   # star-schema CSVs + 27 integrity checks
python3 06_dashboard/build_scripts/verify_phase5.py                 # measure oracle, exit 1 on any mismatch
python3 06_dashboard/build_scripts/21_emit_powerbi_artifacts.py     # DAX, Power Query, themes, TMDL scaffold
python3 06_dashboard/build_scripts/22_render_mockups.py             # mockups + model diagram
python3 06_dashboard/build_scripts/23_write_powerbi_docs.py         # documentation
```
