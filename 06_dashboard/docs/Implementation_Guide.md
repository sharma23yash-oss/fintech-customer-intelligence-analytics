# Power BI Implementation Guide

Synthetic data. Follow these steps in **Power BI Desktop** (any recent release) to build the dashboard from this folder. Estimated time for an experienced developer: 3-4 hours; for a first build: a day.

> **Status (read this first).** This folder contains everything needed to build the dashboard in Power BI Desktop - star-schema data, 117 DAX measures, Power Query scripts, themes, page specifications and a validation sheet. **No `.pbix` file has been generated**: Power BI Desktop is not available in the build environment, and a PBIX cannot be produced without it. The PNG files in `mockups/` are static renderings of the intended design, **not Power BI screenshots**. The DAX has not been run in a DAX engine; its logic was checked with a pandas re-implementation (231 of 231 comparisons match validated Phase 3 / Phase 4 figures and independent SQL).

## 0. What you need

* Power BI Desktop on Windows.
* This folder: `data/` (8 CSVs), `power_query/`, `dax/`, `theme/`, `docs/`, `mockups/`, `validation/`.

## 1. Load the data (Power Query)

1. Home > Transform data > New Source > Blank Query. Paste `power_query/00_DataFolder.pq`, set your local path to `06_dashboard/data` (no trailing backslash) and name the query `DataFolder`.
2. Create one blank query per file `01_DimCampaign.pq` ... `08_FactTicket.pq`, paste the M text, and name each query exactly as the table.
3. Close and apply. Details and column types: `power_query/Power_Query_Transformations.md`. Blank integer cells (for example `CSAT` on unrated tickets) stay null on purpose.

## 2. Build the date table and measure host

1. Modeling > New table, paste `dax/DimDate.dax`. Then Table tools > Mark as date table > `Date`.
2. Modeling > New table: `_Measures = ROW("Placeholder", BLANK())`. Hide the `Placeholder` column.

## 3. Create relationships (Model view)

Create the 15 relationships listed in `docs/Data_Model.md` section 2: every dimension key to the same-named key on each fact, plus `DimDate[Date]` to `FactCustomer[RegistrationDate]`, `FactActivity[ActivityMonthDate]` and `FactTicket[CreatedDate]`. All one-to-many, single direction. Leave `DimStage` unrelated. Apply the sort-by, hidden-column and summarisation settings from section 3 of the data-model document.

## 4. Add the measures

Two options:

* **Manual**: select `_Measures`, New measure, and paste each block from `dax/DAX_Measure_Library.md` (or `dax/Measure_Library.dax`). Set the format string and display folder shown with each measure. Do the `00 Parameters` and `01 Customers and Funnel` folders first.
* **Faster**: open `tmdl_scaffold/` in Power BI Desktop or Tabular Editor. This scaffold is **untested** - it has never been opened in either tool - so treat it as a head start and fall back to the manual route if it does not open.

After the measures are in, run the first check: a card with `[Registered Customers]` must show 10,000; `[CAC]` must show Rs 331.2.

## 5. Apply the theme

View > Themes > Browse for themes > `theme/Fintech_Theme_Light.json` (default) or `theme/Fintech_Theme_Navy.json` (dark variant). Both palettes were validated.

## 6. Build the pages

1. Page setup: View > Page view > Custom 1600 x 900; name the pages `Executive Overview`, `Acquisition & Marketing`, `Retention & Segmentation`, `Customer Operations`.
2. Add the header band (navy rectangle 1600 x 64), title text, slicer strip and footer on page 1, then copy them to the other pages.
3. Add slicers (Month, Campaign, City, Channel, Segment) and sync them across all pages (View > Sync slicers).
4. Add the KPI cards, then the visuals in the order listed in `docs/Dashboard_Design_Specification.md` sections 4-7. `mockups/*.png` show the target layout.
5. Apply conditional formatting: funnel data-point colours (ordinal blue ramp), campaign bars (rules on `[Cost Efficiency Index]`), heatmap gradient (`#CDE2FB` to `#0D366B`), icon rules in the campaign table.
6. Place `[CAC Scope Note]`, `[Mature Cohort Note]`, `[Proxy Note]` and `[Data Disclaimer]` text cards as the specification says.

## 7. Drill-through and tooltip pages

Create `Campaign Detail` and `Segment Detail` (Page information > Drill-through; fields in the specification, section 9) and the three tooltip pages (Page information > Allow use as tooltip, page size Tooltip or 320 x 220). In each source visual, Format > General > Tooltips > Type: Report page.

## 8. Interactions and navigation

Apply the table in specification section 8 (View > Edit interactions): turn the Month slicer off for the cohort heatmap, make the funnel non-filtering, and add page-navigation buttons plus a "Clear all slicers" bookmark.

## 9. Validate before sharing

Work through `docs/Validation_Checklist.md` (every row has an expected value). Then test these behaviours:

| Test | Expected |
|---|---|
| Select only Oct 26 | funnel and funnel-rate KPIs go blank (immature cohort); CAC scope note appears |
| Select Channel = Organic | CAC cards blank (no recorded spend), registrations and activation still show |
| Select one segment, then a month | counts reflect customers *currently* in that segment, registered in that month |
| Clear all | every card returns to the default values in the checklist |

## 10. Publish notes

Publishing to the Power BI service needs a licence and a workspace; the CSV paths in `DataFolder` must then be replaced by a gateway or cloud location. The report contains only synthetic data and shows the disclaimer on every page; do not present it as real company data.

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| Month slicer shows months in alphabetical order | `MonthLabel` not sorted by `MonthSort` |
| Funnel shows one bar | `DimStage` was related to a fact - delete the relationship |
| CAC changes when month changes | a measure was edited and lost `REMOVEFILTERS(DimDate)`; compare with the library |
| Numbers differ from the checklist | check relationships are one-to-many and single direction; check no numeric column is set to auto-summarise |
| TMDL scaffold will not open | expected possibility - use the manual route |
