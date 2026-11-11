# Dashboard documentation

> **Status: Power BI build kit and design mockups. There is no `.pbix` file and no Power BI Desktop screenshot.**
> The dashboard was designed, modelled and specified, and its measure logic was verified in pandas. It was **never built or opened in Power BI Desktop**, and the DAX and Power Query were never executed there. The PNG images in [`mockups/`](mockups/) are matplotlib renderings of the intended design (each carries the label "SYNTHETIC DATA | MOCKUP - not a Power BI screenshot").
> All data are synthetic (fictional Indian retail brokerage, snapshot 2026-10-31). No revenue, ROI or lifetime value is shown because the data contains none.

## What is in this folder

| Item | Path | Status |
|---|---|---|
| Design specification (4 pages, canvas, tokens, every visual and its fields) | [`docs/Dashboard_Design_Specification.md`](docs/Dashboard_Design_Specification.md) | complete |
| Data model (star schema, 8 tables, 15 relationships) | [`docs/Data_Model.md`](docs/Data_Model.md), [`mockups/Data_Model_Star_Schema.png`](mockups/Data_Model_Star_Schema.png) | complete |
| Model data | [`data/`](data/) (`FactCustomer`, `FactActivity`, `FactTicket`, `DimCampaign`, `DimCity`, `DimDevice`, `DimSegment`, `DimStage`) | 27 of 27 integrity checks pass ([`validation/model_integrity_checks.csv`](validation/model_integrity_checks.csv)) |
| DAX measures | [`dax/`](dax/) – 117 measures; see [`dax_measures.md`](dax_measures.md) | logic verified in pandas; **not run in a DAX engine** |
| Power Query | [`power_query/`](power_query/) – 8 queries, 1 folder parameter | **not run in Power BI** |
| Themes | [`theme/`](theme/) (light and navy) | palettes validated; not imported into Power BI |
| Semantic-model scaffold | [`tmdl_scaffold/`](tmdl_scaffold/) | **untested** |
| Implementation guide and checklist | [`docs/Implementation_Guide.md`](docs/Implementation_Guide.md), [`docs/Validation_Checklist.md`](docs/Validation_Checklist.md) | complete |
| Design mockups | [`mockups/`](mockups/) – 4 pages and the model diagram | mockups only |
| `.pbix` file | – | **does not exist** |

## The four pages

| Page | Question it answers | Mockup |
|---|---|---|
| 1 Executive Overview | How is the business growing and where does onboarding leak? | [`Page1_Executive_Overview.png`](mockups/Page1_Executive_Overview.png) |
| 2 Acquisition & Marketing | Which campaigns and channels acquire customers efficiently? | [`Page2_Acquisition_Marketing.png`](mockups/Page2_Acquisition_Marketing.png) |
| 3 Retention & Segmentation | Who stays active, who goes quiet, which segments need action? | [`Page3_Retention_Segmentation.png`](mockups/Page3_Retention_Segmentation.png) |
| 4 Customer Operations | How much support demand do we create and how well do we resolve it? | [`Page4_Customer_Operations.png`](mockups/Page4_Customer_Operations.png) |

## How the measures were verified

`build_scripts/verify_phase5.py` re-implements the measure logic in pandas under several filter contexts (none, channel, campaign, city and device, segment, month) and compares the results with the Phase 3 analysis, the Phase 4 Excel values and independent SQL: **231 of 231 comparisons match**, covering 87 of the 117 measures directly. The other 30 (parameters, labels, ranks, time-intelligence wrappers) depend on the Power BI engine and were not oracle-tested. Details: [`validation/Phase5_Measure_Verification.md`](validation/Phase5_Measure_Verification.md).

This proves the *logic* matches. It does not prove the DAX parses or behaves identically in Power BI. The first step when building is to compare the cards against [`validation/DAX_Oracle_Expected_Values.csv`](validation/DAX_Oracle_Expected_Values.csv).

## Build it in Power BI Desktop

1. Follow [`docs/Implementation_Guide.md`](docs/Implementation_Guide.md): load `data/` (parameter in `power_query/00_DataFolder.pq`), create relationships, paste `dax/Measure_Library.dax` and `dax/DimDate.dax`, import a theme from `theme/`.
2. Build the four pages from [`docs/Dashboard_Design_Specification.md`](docs/Dashboard_Design_Specification.md).
3. Tick every row of [`docs/Validation_Checklist.md`](docs/Validation_Checklist.md).
4. Export the screenshots listed below and save them in [`screenshots/`](screenshots/).

## Screenshots to export once the dashboard exists

Save as PNG, 1600 × 900, in `06_dashboard/screenshots/`. Until these exist, the README shows the mockups and says so.

| File name | What to capture |
|---|---|
| `01_executive_overview.png` | Page 1 with no slicer selected |
| `02_acquisition_marketing.png` | Page 2 with no slicer selected |
| `03_retention_segmentation.png` | Page 3 with no slicer selected |
| `04_customer_operations.png` | Page 4 with no slicer selected |
| `05_model_view.png` | Model view showing the star schema |
| `06_filtered_example.png` | Any page with one campaign selected, showing slicers working |
| `07_tooltip_funnel_stage.png` | The funnel-stage tooltip page on hover |

## Limitations

* No `.pbix`; no Power BI screenshots; DAX and M not executed in Power BI.
* Spend is undated, so cost measures ignore date, city, device and segment filters.
* Segments are a snapshot as of 2026-10-31.
* "Inactive 90d" and "Dormant 3m" are proxies, not confirmed churn.
* Budget indicators are directional, not ROI; campaign differences are observational associations in synthetic data.
