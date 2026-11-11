# Power BI Data Model

Synthetic data. Star schema built by `06_dashboard/build_scripts/19_build_powerbi_model_data.py` from the validated Phase 2 cleaned data and the Phase 3 segment rule. Diagram: `mockups/Data_Model_Star_Schema.png` (a diagram, not a Power BI screenshot).

> **Status (read this first).** This folder contains everything needed to build the dashboard in Power BI Desktop - star-schema data, 117 DAX measures, Power Query scripts, themes, page specifications and a validation sheet. **No `.pbix` file has been generated**: Power BI Desktop is not available in the build environment, and a PBIX cannot be produced without it. The PNG files in `mockups/` are static renderings of the intended design, **not Power BI screenshots**. The DAX has not been run in a DAX engine; its logic was checked with a pandas re-implementation (231 of 231 comparisons match validated Phase 3 / Phase 4 figures and independent SQL).

## 1. Tables

| Table | Source | Grain | Rows | Columns |
|---|---|---|---|---|
| DimDate | calculated (DAX) | day | 365 | 10 |
| DimCampaign | Power Query (CSV) | campaign | 10 | 14 |
| DimCity | Power Query (CSV) | city | 11 | 2 |
| DimDevice | Power Query (CSV) | device type | 3 | 2 |
| DimSegment | Power Query (CSV) | journey segment | 10 | 4 |
| DimStage | Power Query (CSV) | funnel stage | 6 | 2 |
| FactCustomer | Power Query (CSV) | customer | 10,000 | 42 |
| FactActivity | Power Query (CSV) | customer x month | 64,645 | 17 |
| FactTicket | Power Query (CSV) | support ticket | 7,614 | 21 |
| _Measures | calculated (DAX) | measure host, hidden column | 1 | 117 measures |

* **Facts**: `FactCustomer` (funnel, tenure, retention flags, tickets per customer), `FactActivity` (monthly activity, trading and cash flow), `FactTicket` (support).
* **Dimensions**: `DimCampaign` (channel, spend, Phase 3 scorecard tier), `DimCity`, `DimDevice`, `DimSegment` (10 journey segments, group, recommended action), `DimDate`, and `DimStage` (disconnected helper for the funnel axis).
* **Keys on every fact**: `CampaignKey`, `CityKey`, `DeviceKey`, `SegmentKey` are repeated on all three facts, so each slicer filters every fact directly. This avoids fact-to-fact relationships (which would need bi-directional filtering and cause ambiguity).

## 2. Relationships (15, all active, all one-to-many, single direction)

| From (one) | To (many) | Cardinality | Filter direction | State |
|---|---|---|---|---|
| DimCampaign[CampaignKey] | FactCustomer[CampaignKey] | 1 : *  | single (dimension to fact) | active |
| DimCity[CityKey] | FactCustomer[CityKey] | 1 : *  | single (dimension to fact) | active |
| DimDevice[DeviceKey] | FactCustomer[DeviceKey] | 1 : *  | single (dimension to fact) | active |
| DimSegment[SegmentKey] | FactCustomer[SegmentKey] | 1 : *  | single (dimension to fact) | active |
| DimCampaign[CampaignKey] | FactActivity[CampaignKey] | 1 : *  | single (dimension to fact) | active |
| DimCity[CityKey] | FactActivity[CityKey] | 1 : *  | single (dimension to fact) | active |
| DimDevice[DeviceKey] | FactActivity[DeviceKey] | 1 : *  | single (dimension to fact) | active |
| DimSegment[SegmentKey] | FactActivity[SegmentKey] | 1 : *  | single (dimension to fact) | active |
| DimCampaign[CampaignKey] | FactTicket[CampaignKey] | 1 : *  | single (dimension to fact) | active |
| DimCity[CityKey] | FactTicket[CityKey] | 1 : *  | single (dimension to fact) | active |
| DimDevice[DeviceKey] | FactTicket[DeviceKey] | 1 : *  | single (dimension to fact) | active |
| DimSegment[SegmentKey] | FactTicket[SegmentKey] | 1 : *  | single (dimension to fact) | active |
| DimDate[Date] | FactCustomer[RegistrationDate] | 1 : * | single | active |
| DimDate[Date] | FactActivity[ActivityMonthDate] | 1 : * | single | active |
| DimDate[Date] | FactTicket[CreatedDate] | 1 : * | single | active |

`DimStage` has no relationship on purpose: it only supplies the funnel stage axis and measures branch on `SELECTEDVALUE(DimStage[StageName])`. `FactActivity[RegMonthDate]` is deliberately **not** related to `DimDate`: the cohort matrix uses it directly as a row field.

## 3. Model settings to apply (not stored in the CSVs)

| Setting | Columns |
|---|---|
| Mark as date table | `DimDate[Date]` |
| Sort by column | `DimDate[MonthLabel]` by `MonthSort`; `DimCampaign[Channel]` by `ChannelSort`; `DimCity[CityKey]` by `CitySort`; `DimDevice[DeviceKey]` by `DeviceSort`; `DimStage[StageName]` by `StageOrder`; `FactCustomer[InactivityBucket]` by `InactivitySort`; `FactTicket[Priority]` by `PrioritySort`; `FactTicket[BacklogAgeBucket]` by `BacklogSort` |
| Summarize by | "Don't summarize" on every numeric column (the model uses explicit measures only) |
| Hidden | the four dimension keys on each fact, all `*Sort` columns, `_Measures[Placeholder]` |
| Formats | dates `yyyy-mm-dd`; month label as text; measure formats are in `dax/DAX_Measure_Library.md` |
| Display folders | measure folders `00 Parameters` ... `06 Labels and Notes` |

## 4. Why this design

* **One grain per fact** keeps each measure simple and fast: customer-level facts for funnel and retention flags, customer-month for activity, ticket-level for support.
* **Snapshot segments**: the segment is assigned once as of 2026-10-31 (Phase 3 rule), so a customer does not move between segments as the Month slicer changes.
* **Spend is undated** in the source, so cost measures deliberately ignore date, city, device and segment filters (`REMOVEFILTERS`) and a scope note warns the user.
* **Mature cohort** (registered before 2026-10, n = 9,116) is the denominator for funnel rates; the 884 October registrants have not had time to finish onboarding.

## 5. Data-integrity checks run on the model tables (27 of 27 passed)

| check                                                         | result   |
|:--------------------------------------------------------------|:---------|
| FactCustomer rows = 10,000                                    | pass     |
| FactActivity rows = 64,645                                    | pass     |
| FactTicket rows = 7,614                                       | pass     |
| CustomerID unique in FactCustomer                             | pass     |
| TicketID unique                                               | pass     |
| FactActivity (CustomerID, month) unique                       | pass     |
| FactCustomer.CampaignKey in DimCampaign                       | pass     |
| FactCustomer.CityKey in DimCity                               | pass     |
| FactCustomer.DeviceKey in DimDevice                           | pass     |
| FactCustomer.SegmentKey in DimSegment                         | pass     |
| FactActivity.CampaignKey in DimCampaign                       | pass     |
| FactActivity.CityKey in DimCity                               | pass     |
| FactActivity.DeviceKey in DimDevice                           | pass     |
| FactActivity.SegmentKey in DimSegment                         | pass     |
| FactTicket.CampaignKey in DimCampaign                         | pass     |
| FactTicket.CityKey in DimCity                                 | pass     |
| FactTicket.DeviceKey in DimDevice                             | pass     |
| FactTicket.SegmentKey in DimSegment                           | pass     |
| FactActivity.CustomerID in FactCustomer                       | pass     |
| FactTicket.CustomerID in FactCustomer                         | pass     |
| RegistrationDate within DimDate range 2025-11-01..2026-10-31  | pass     |
| ActivityMonthDate within DimDate range 2025-11-01..2026-10-31 | pass     |
| RegMonthDate within DimDate range 2025-11-01..2026-10-31      | pass     |
| CreatedDate within DimDate range 2025-11-01..2026-10-31       | pass     |
| ActivityMonthDate and RegMonthDate are month starts           | pass     |
| Journey segment counts equal Phase 3                          | pass     |
| DimCampaign spend total = 2,690,000 (Rs 26.9 lakh)            | pass     |

Full list with details: `validation/model_integrity_checks.csv`. Column types: `validation/model_tables_meta.json`.

## 6. Traceability

`CSV (06_dashboard/data)` <- `19_build_powerbi_model_data.py` <- Phase 2 cleaned data (`loading.load_all()`) + Phase 3 segment rule (`fintech_analytics.segmentation.journey_segment`). Every dashboard measure is defined in `dax/` and re-computed independently in `06_dashboard/build_scripts/verify_phase5.py` (output: `validation/DAX_Oracle_Expected_Values.csv`).
