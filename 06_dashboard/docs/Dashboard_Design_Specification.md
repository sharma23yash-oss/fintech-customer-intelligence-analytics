# Dashboard Design Specification

Synthetic data (fictional Indian retail brokerage, 10,000 customers, Nov 2025 - Oct 2026, INR, snapshot 2026-10-31).

> **Status (read this first).** This folder contains everything needed to build the dashboard in Power BI Desktop - star-schema data, 117 DAX measures, Power Query scripts, themes, page specifications and a validation sheet. **No `.pbix` file has been generated**: Power BI Desktop is not available in the build environment, and a PBIX cannot be produced without it. The PNG files in `mockups/` are static renderings of the intended design, **not Power BI screenshots**. The DAX has not been run in a DAX engine; its logic was checked with a pandas re-implementation (231 of 231 comparisons match validated Phase 3 / Phase 4 figures and independent SQL).

## 1. Purpose and audience

A four-page interactive dashboard for fintech growth managers, product-operations managers, customer-experience teams, marketing managers and strategy teams. It answers four questions, one per page:

| Page | Question | Primary audience |
|---|---|---|
| 1 Executive Overview | How is the business growing and where does onboarding leak? | everyone |
| 2 Acquisition & Marketing | Which campaigns and channels acquire customers efficiently? | marketing, growth |
| 3 Retention & Segmentation | Who stays active, who goes quiet, and which segments need action? | growth, product ops, CX |
| 4 Customer Operations | How much support demand do we create, and how well do we resolve it? | CX, product ops |

Every figure comes from the synthetic star schema in `data/`. Nothing is revenue, ROI or lifetime value: the data contains none, so the dashboard shows *cost per activated customer* and *directional budget signals*, never profit.

## 2. Canvas, grid and design tokens

* **Page size**: custom 1600 x 900 px (16:9), matching the mockups. Page background `#F4F6FA`, cards white with a 1 px `#E3E8EF` border and 6 px radius.
* **Header band** (0-64 px): navy `#0B1F3A`, page title (semibold, white), subtitle, and the fixed label "Synthetic data". **Slicer strip** at y = 74-98 px. **KPI row** at y = 108-186 px. Content cards from y = 200 px, 12 px gutters, 24 px outer margin. **Footer** text box at y = 890 px carrying `[Data Disclaimer]` and `[Proxy Note]`.
* **Typography**: Segoe UI Semibold for titles and KPI values, Segoe UI for labels. Card title 12 pt, axis/labels 9-10 pt, KPI value 22-24 pt (15 pt for the long "Rs 2,690,000" style values), KPI label 10 pt secondary ink.
* **Colour** (themes in `theme/`; palettes validated with the data-visualisation palette validator):

| Role | Light theme | Navy theme |
|---|---|---|
| Page background | `#F4F6FA` | `#0B1F3A` |
| Card | `#FFFFFF` | `#12294A` |
| Primary ink / secondary ink | `#0B1F3A` / `#52606D` | `#F0EFEC` / `#C3C2B7` |
| Categorical order (fixed, never cycled) | `#2A78D6 #EB6834 #1BAF7A #EDA100 #E87BA4 #008300 #6250D6 #E34948` | `#3987E5 #D95926 #199E70 #C98500 #D55181 #008300 #9085E9 #E66767` |
| Sequential (one hue, light to dark) | `#CDE2FB -> #0D366B` | `#184F95 -> #CDE2FB` |
| Status (fixed) | good `#0CA30C`, warning `#FAB219`, critical `#D03B3B` | same |

  Validation results: light palette passes lightness band, chroma floor, adjacent-pair colour-blind separation (worst 9.1) and normal-vision separation (worst 19.6); three light slots (aqua, yellow, magenta) are below 3:1 contrast on white, so **visible data labels or a table view are mandatory** wherever those colours are used. The navy palette passes all checks including contrast >= 3:1 on `#0B1F3A`.
* **Colour discipline**: magnitude uses one blue hue; categorical colours are used only for two-group comparisons (paid vs organic); the funnel uses an ordinal blue ramp (steps 250 to 700); heatmap uses a one-hue sequential ramp; status colours always come with an icon and a text label. No dual-axis charts - two measures of different scale get two visuals.
* **Hierarchy**: KPI row first (answer), then trend/mix visuals (context), then detail table or commentary (action).

## 3. Global elements (every page)

| Element | Specification |
|---|---|
| Slicers (synced across pages: View > Sync slicers) | **Month** `DimDate[MonthLabel]` (multi-select, sorted by MonthSort); **Campaign** `DimCampaign[CampaignName]`; **City** `DimCity[CityKey]`; **Channel** `DimCampaign[Channel]`; **Customer segment** `DimSegment[SegmentName]`. Optional extra: Device `DimDevice[DeviceKey]`. |
| Navigation | four page buttons in the header; a "Clear all slicers" bookmark button |
| Footer | cards with `[Data Disclaimer]` and `[Proxy Note]`; page label "Synthetic data - mockup design" is removed in the real report but the disclaimer stays |
| CAC scope note | small text card bound to `[CAC Scope Note]` next to every CAC visual; it shows a warning when a month, city, device or segment filter is active (spend is not dated, so CAC ignores those filters) |
| Alt text | every visual gets a one-line alt text; tab order follows reading order |

### Slicer scope (what each filter does to which measure family)

| Measure family | Month slicer | Campaign / Channel | City / Device | Segment |
|---|---|---|---|---|
| Customers and funnel (registrations, KYC, activation) | registration month | filters | filters | filters (snapshot attribute) |
| Acquisition cost (CAC, cost per KYC, cost per first trade, spend) | **ignored** (spend is undated) | filters | **ignored** | **ignored** |
| Engagement (MAU, retention, trading) | activity month | filters | filters | filters |
| Support (tickets, resolution, CSAT) | ticket created month | filters | filters | filters |
| Tickets per 1,000 customers | created month; denominator = customers registered up to month end | filters | filters | filters |

Behaviours to expect (they are intended, not defects): selecting only **Oct 26** blanks the funnel and funnel-rate KPIs because the October cohort is immature (mature cohort = registered before Oct 2026); **MAU** returns the latest selected month; the **cohort heatmap** is not driven by the Month slicer (turn that interaction off - see section 8); **segments** describe each customer as of 2026-10-31.

## 4. Page 1 - Executive Overview (`mockups/Page1_Executive_Overview.png`)

| # | Visual | Type | Fields | Notes |
|---|---|---|---|---|
| 1 | Registered customers | Card | `[Registered Customers]` | reference label: period text |
| 2 | KYC completion rate | Card | `[KYC Completion Rate]` | sub-label `[Mature Cohort Note]`; expected 70.5% |
| 3 | First-trade activation | Card | `[First Trade Activation Rate]` | expected 38.0% |
| 4 | MAU | Card | `[MAU]`, reference `[MAU Share of Customers]` | latest month in context; expected 4,611 |
| 5 | 30-day retention | Card | `[30-Day Retention]` | customers with 31+ days tenure |
| 6 | CAC | Card | `[CAC]` | blended paid CAC; `[CAC Scope Note]` beneath |
| 7 | Total campaign spend | Card | `[Total Campaign Spend]` | |
| 8 | Support ticket volume | Card | `[Tickets]`, reference `[Tickets per 1000 Customers]` | |
| 9 | Monthly acquisition trend | Clustered column | X `DimDate[MonthLabel]`; Y `[Registered Customers]` | data labels on; tooltip adds `[Registrations MoM %]`, `[Registrations 3M Avg]` |
| 10 | Customer activation funnel | Clustered bar | Axis `DimStage[StageName]` (sort by StageOrder); Values `[Funnel Users]` and label `[Funnel % of Registered]` | ordinal blue ramp per data point; tooltip page "Funnel stage" shows `[Funnel Step Conversion]`, `[Funnel Users Lost]`, `[Share of Funnel Losses]`, `[Median Days in Stage]`; footnote `[Mature Cohort Note]` |
| 11 | Channel performance | Clustered bar | Axis `DimCampaign[Channel]`; Values `[First Trade Activation Rate]`; sort descending | tooltip adds `[Registered Customers]`, `[CAC]` (blank for Organic), `[M3 Retention]` |
| 12 | Customer engagement trend | Line | X `DimDate[MonthLabel]`; Y `[MAU]` | markers on; label first, middle and last points |
| 13 | Key takeaways | Text box | static text from Phase 3 | static commentary; does not react to slicers - label it "as of snapshot" |

Expected default values: registered 10,000; MAU 4,611; CAC Rs 331.2; spend Rs 2,690,000; tickets 7,614.

## 5. Page 2 - Acquisition & Marketing (`mockups/Page2_Acquisition_Marketing.png`)

| # | Visual | Type | Fields | Notes |
|---|---|---|---|---|
| 1 | Total campaign spend | Card | `[Total Campaign Spend]` | |
| 2 | Paid registrations | Card | `[Paid Registrations (Full Period)]`, reference `[Paid Share of Registrations]` | |
| 3 | Blended CAC | Card | `[CAC]` | recorded spend / paid registrations |
| 4 | Median cost per KYC | Card | `[Median Paid Cost per KYC]` | peer benchmark across paid campaigns |
| 5 | Median cost per first trade | Card | `[Median Paid Cost per First Trade]` | |
| 6 | Organic registrations | Card | `[Registered Customers]` with visual filter `DimCampaign[AcquisitionType]` = "Organic (no spend recorded)" | organic has no CAC |
| 7 | Cost per first trade by paid campaign | Clustered bar | Axis `DimCampaign[CampaignKey]`; Values `[Cost per First Trade]`; sort ascending | visual filter IsPaid = 1; colour by rule on `[Cost Efficiency Index]` (>= `[Efficient Index Threshold]` green, <= `[Costly Index Threshold]` red, else blue); constant line (fx) = `[Median Paid Cost per First Trade]` |
| 8 | CAC by channel | Clustered bar | Axis `DimCampaign[Channel]`; Values `[CAC]` | visual filter IsPaid = 1 |
| 9 | Paid vs organic | 100% stacked bar | Values `[Registered Customers]`; Legend `DimCampaign[AcquisitionType]` | pair with a small table of `[First Trade Activation Rate]` by AcquisitionType; organic cost is blank, not zero |
| 10 | Registrations by city | Clustered bar | Axis `DimCity[CityKey]`; Values `[Registered Customers]`; sort descending | tooltip `[City Share of Registrations]` |
| 11 | Registrations by device | Clustered bar | Axis `DimDevice[DeviceKey]`; Values `[Registered Customers]` | tooltip `[Device Share of Registrations]`; second bar visual with `[First Trade Activation Rate]` |
| 12 | Campaign ranking and budget indicators | Table | `CampaignKey`, `Channel`, `[Total Campaign Spend]`, `[Registered Customers]`, `[CAC]`, `[Cost per KYC]`, `[Cost per First Trade]`, `[Cost Efficiency Index]`, `[Budget Signal]`, `[Phase 3 Scorecard Tier]`, `[Rank Cost per First Trade (Paid)]` | icon rules on the index (up-arrow green >= 1.15, down-arrow red <= 0.85); the mockup shortens the signal text; drill-through to Campaign Detail |

Budget indicators are **directional**: they compare each paid campaign's cost per first trade with the peer median. They are not ROI, and `[Evidence Strength]` (from the Phase 3 Holm-adjusted tests) must be shown in the Campaign Detail page so a strong-looking signal is never read as proof. Expected values:

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

## 6. Page 3 - Retention & Segmentation (`mockups/Page3_Retention_Segmentation.png`)

| # | Visual | Type | Fields | Notes |
|---|---|---|---|---|
| 1-7 | KPI cards | Card | `[MAU]`, `[M1 Retention]`, `[M3 Retention]`, `[M6 Retention]`, `[Inactive 90d Rate]`, `[Dormant 3m Rate]`, `[Repeat Trader Share]` | inactive/dormant are churn **proxies**; `[Proxy Note]` in footer |
| 8 | Cohort retention heatmap | Matrix | Rows `FactActivity[RegMonthDate]` (mmm yy, ascending); Columns `FactActivity[MonthsSinceRegistration]`; Values `[Cohort Retention]` | background colour gradient (min `#CDE2FB`, max `#0D366B`), font white above mid-scale; subtotals off; tooltip page "Cohort cell" shows `[Cohort Size]`, `[Cohort Retention]`; Month slicer interaction off |
| 9 | Inactive-customer distribution | Clustered column | Axis `FactCustomer[InactivityBucket]` (sort by InactivitySort); Values `[Inactivity Share (Eligible)]` | base: customers with 31+ days tenure |
| 10 | M3 retention by channel | Clustered bar | Axis `DimCampaign[Channel]`; Values `[M3 Retention]` | |
| 11 | Customer segments | Clustered bar | Axis `DimSegment[SegmentName]`; Values `[Registered Customers]` + `[Segment Share]` | sort descending; drill-through to Segment Detail; a second view grouped by `DimSegment[SegmentGroup]` isolates "Inactive / occasional" |
| 12 | Trading activity | Line | X `DimDate[MonthLabel]`; Y `[Trading Users]` | optional second chart `[Trades per Trading User]` |
| 13 | Reading the heatmap | Text box | static | |

## 7. Page 4 - Customer Operations (`mockups/Page4_Customer_Operations.png`)

| # | Visual | Type | Fields | Notes |
|---|---|---|---|---|
| 1-7 | KPI cards | Card | `[Tickets]`, `[Tickets per 1000 Customers]`, `[Resolved Rate]`, `[Escalation Rate]`, `[Median Resolution Hours]`, `[CSAT]`, `[Backlog over 90 Days]` | |
| 8 | Ticket volume | Clustered column | X `DimDate[MonthLabel]`; Y `[Tickets]` | |
| 9 | Tickets per 1,000 customers | Line | X `DimDate[MonthLabel]`; Y `[Tickets per 1000 Customers]` | denominator = customers registered up to month end |
| 10 | Ticket categories | Clustered bar | Axis `FactTicket[Category]`; Values `[Tickets]` | tooltip `[Median Resolution Hours]`, `[CSAT]`, `[Escalation Rate]` |
| 11 | Priority distribution | Clustered bar | Axis `FactTicket[Priority]` (sort by PrioritySort); Values `[Tickets]` + `[Priority Share]` | ordinal blue ramp |
| 12 | Backlog ageing | Clustered column | Axis `FactTicket[BacklogAgeBucket]` (sort by BacklogSort); Values `[Unresolved Tickets]` | open + escalated tickets |
| 13 | Onboarding bottlenecks | Clustered bar | Axis `FactTicket[RelatedFunnelStage]`; Values `[Onboarding Tickets]` | tooltip `[Pending Stage Ticket Share]`; source labels are lower case (kyc, bank, deposit, trade) - the mockup capitalises them for readability |
| 14 | Resolution time | Add to tooltips / optional card | `[Median Resolution Hours]`, `[Avg Resolution Hours]`, `[P90 Resolution Hours]`, `[Within SLA Rate]` | SLA = `[SLA Hours]` parameter (24 h) |

## 8. Interactions

| Source visual | Target | Setting |
|---|---|---|
| Any slicer | all visuals on synced pages | filter |
| Funnel (page 1) | other visuals | none (DimStage is disconnected, so it cannot filter the model) |
| Monthly acquisition column (page 1) | all other visuals | cross-filter (selecting a month filters registrations, activity and tickets for that month) |
| Month slicer | cohort heatmap (page 3) | **off** (Format > Edit interactions) so the matrix always shows every cohort |
| Campaign table row (page 2) | other page-2 visuals | cross-highlight; CAC visuals respect the campaign filter only |
| Segment bar (page 3) | other page-3 visuals | cross-filter |

## 9. Drill-through and tooltip pages

| Page | Type | Drill-through / trigger field | Content |
|---|---|---|---|
| Campaign Detail | drill-through (keep all filters) | `DimCampaign[CampaignKey]` | title (`CampaignName`, `[Phase 3 Scorecard Tier]`, `[Phase 3 Overall Score]`, `[Evidence Strength]`); cards `[Total Campaign Spend]`, `[Registered Customers]`, `[CAC]`, `[Cost per KYC]`, `[Cost per First Trade]`, `[First Trade Activation Rate]`, `[M3 Retention]`; text card `[Budget Signal]`; funnel, monthly registrations, city and device bars for that campaign |
| Segment Detail | drill-through | `DimSegment[SegmentName]` | cards `[Registered Customers]`, `[Segment Share]`, `[Funded Never Traded]`, `[Tickets per 1000 Customers]`; text of `DimSegment[RecommendedAction]`; channel, city and device mix; ticket categories |
| Funnel stage | tooltip (320 x 220) | `DimStage[StageName]` | `[Funnel Users]`, `[Funnel Step Conversion]`, `[Funnel Users Lost]`, `[Share of Funnel Losses]`, `[Median Days in Stage]` |
| Campaign | tooltip | `DimCampaign[CampaignKey]` | `[Cost per First Trade]`, `[Cost Efficiency Index]`, `[Budget Signal]`, `[Evidence Strength]`, `[Phase 3 Scorecard Tier]` |
| Cohort cell | tooltip | `FactActivity[RegMonthDate]` | `[Cohort Size]`, `[Cohort Retention]` |

## 10. Accessibility and quality rules

* No meaning by colour alone: every status colour is paired with an icon and a label; every multi-series chart has a legend or direct labels.
* Direct data labels on bars and the first/middle/last points of lines; no label on every point of a long line.
* Contrast: body text uses primary or secondary ink only; chart colours never carry text.
* Every page shows the synthetic-data disclaimer and the churn-proxy note.
* Check each page with the **Performance analyzer** after building; all measures are simple aggregates over a 64,645-row fact table.
