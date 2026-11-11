"""Phase 5 - write the Power BI documentation set (SYNTHETIC data) with numbers pulled from the verified oracle table.
Run: python3 23_write_powerbi_docs.py"""
import json, sys
from pathlib import Path
import pandas as pd

HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1] / "05_python"))   # build_scripts + fintech_analytics package
import powerbi_measures as PM

ROOT = HERE.parents[1]; PB = ROOT / "06_dashboard"; DOCS = PB / "docs"; DOCS.mkdir(exist_ok=True)
EXP = pd.read_csv(PB / "validation/DAX_Oracle_Expected_Values.csv")
SIG = pd.read_csv(PB / "validation/Budget_Signal_Expected.csv")
META = json.loads((PB / "validation/model_tables_meta.json").read_text())
CHK = pd.read_csv(PB / "validation/model_integrity_checks.csv")
FMT = {n: f for _, n, _, f, _ in PM.M}
import re
N_MATCH = int((EXP.status == "MATCH").sum()); N_CMP = len(EXP)
_cov = re.search(r"oracle check: \*\*(\d+) of (\d+)\*\*", (PB / "validation/Phase5_Measure_Verification.md").read_text())
N_TESTED, N_ALL = int(_cov.group(1)), int(_cov.group(2))
N_M = len(PM.M); assert N_ALL == N_M
N_F = len(dict.fromkeys(m[0] for m in PM.M))
DC = pd.read_csv(PB / "data/DimCampaign.csv")


def val(measure, ctx="no filters"):
    r = EXP[(EXP.measure == measure) & (EXP.context == ctx)]
    assert len(r), (measure, ctx)
    return float(r.oracle_value.iloc[0])


def fmt(measure, v):
    f = FMT.get(measure, "#,0.00")
    if pd.isna(v): return "(blank)"
    return {"0.0%": f"{v:.1%}", "0.00%": f"{v:.2%}", "#,0": f"{v:,.0f}", "#,0.0": f"{v:,.1f}", "#,0.00": f"{v:,.2f}"}.get(f, f"{v:,.2f}")


def w(path, text): path.write_text(text.strip("\n") + "\n")


STATUS = f"""> **Status (read this first).** This folder contains everything needed to build the dashboard in Power BI Desktop - star-schema data, {N_M} DAX measures, Power Query scripts, themes, page specifications and a validation sheet. **No `.pbix` file has been generated**: Power BI Desktop is not available in the build environment, and a PBIX cannot be produced without it. The PNG files in `mockups/` are static renderings of the intended design, **not Power BI screenshots**. The DAX has not been run in a DAX engine; its logic was checked with a pandas re-implementation ({N_MATCH} of {N_CMP} comparisons match validated Phase 3 / Phase 4 figures and independent SQL)."""

# ------------------------------------------------------------------------------------------------ 1. design specification
spec = f"""# Dashboard Design Specification

Synthetic data (fictional Indian retail brokerage, 10,000 customers, Nov 2025 - Oct 2026, INR, snapshot 2026-10-31).

{STATUS}

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
| 2 | KYC completion rate | Card | `[KYC Completion Rate]` | sub-label `[Mature Cohort Note]`; expected {fmt('KYC Completion Rate', val('KYC Completion Rate'))} |
| 3 | First-trade activation | Card | `[First Trade Activation Rate]` | expected {fmt('First Trade Activation Rate', val('First Trade Activation Rate'))} |
| 4 | MAU | Card | `[MAU]`, reference `[MAU Share of Customers]` | latest month in context; expected {val('MAU'):,.0f} |
| 5 | 30-day retention | Card | `[30-Day Retention]` | customers with 31+ days tenure |
| 6 | CAC | Card | `[CAC]` | blended paid CAC; `[CAC Scope Note]` beneath |
| 7 | Total campaign spend | Card | `[Total Campaign Spend]` | |
| 8 | Support ticket volume | Card | `[Tickets]`, reference `[Tickets per 1000 Customers]` | |
| 9 | Monthly acquisition trend | Clustered column | X `DimDate[MonthLabel]`; Y `[Registered Customers]` | data labels on; tooltip adds `[Registrations MoM %]`, `[Registrations 3M Avg]` |
| 10 | Customer activation funnel | Clustered bar | Axis `DimStage[StageName]` (sort by StageOrder); Values `[Funnel Users]` and label `[Funnel % of Registered]` | ordinal blue ramp per data point; tooltip page "Funnel stage" shows `[Funnel Step Conversion]`, `[Funnel Users Lost]`, `[Share of Funnel Losses]`, `[Median Days in Stage]`; footnote `[Mature Cohort Note]` |
| 11 | Channel performance | Clustered bar | Axis `DimCampaign[Channel]`; Values `[First Trade Activation Rate]`; sort descending | tooltip adds `[Registered Customers]`, `[CAC]` (blank for Organic), `[M3 Retention]` |
| 12 | Customer engagement trend | Line | X `DimDate[MonthLabel]`; Y `[MAU]` | markers on; label first, middle and last points |
| 13 | Key takeaways | Text box | static text from Phase 3 | static commentary; does not react to slicers - label it "as of snapshot" |

Expected default values: registered {val('Registered Customers'):,.0f}; MAU {val('MAU'):,.0f}; CAC Rs {val('CAC'):,.1f}; spend Rs {val('Total Campaign Spend'):,.0f}; tickets {val('Tickets'):,.0f}.

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

{SIG.to_markdown(index=False)}

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
"""
w(DOCS / "Dashboard_Design_Specification.md", spec)

# ------------------------------------------------------------------------------------------------ 2. data model
rel_rows = []
for fact in ("FactCustomer", "FactActivity", "FactTicket"):
    for dim, col in (("DimCampaign", "CampaignKey"), ("DimCity", "CityKey"), ("DimDevice", "DeviceKey"), ("DimSegment", "SegmentKey")):
        rel_rows.append(f"| {dim}[{col}] | {fact}[{col}] | 1 : *  | single (dimension to fact) | active |")
rel_rows += ["| DimDate[Date] | FactCustomer[RegistrationDate] | 1 : * | single | active |", "| DimDate[Date] | FactActivity[ActivityMonthDate] | 1 : * | single | active |", "| DimDate[Date] | FactTicket[CreatedDate] | 1 : * | single | active |"]
tbl = []
for t in ["DimDate", "DimCampaign", "DimCity", "DimDevice", "DimSegment", "DimStage", "FactCustomer", "FactActivity", "FactTicket"]:
    if t == "DimDate": tbl.append("| DimDate | calculated (DAX) | day | 365 | 10 |"); continue
    g = {"DimCampaign": "campaign", "DimCity": "city", "DimDevice": "device type", "DimSegment": "journey segment", "DimStage": "funnel stage", "FactCustomer": "customer", "FactActivity": "customer x month", "FactTicket": "support ticket"}[t]
    tbl.append(f"| {t} | Power Query (CSV) | {g} | {META[t]['rows']:,} | {len(META[t]['columns'])} |")
passed = int(CHK.passed.sum())
dm = f"""# Power BI Data Model

Synthetic data. Star schema built by `06_dashboard/build_scripts/19_build_powerbi_model_data.py` from the validated Phase 2 cleaned data and the Phase 3 segment rule. Diagram: `mockups/Data_Model_Star_Schema.png` (a diagram, not a Power BI screenshot).

{STATUS}

## 1. Tables

| Table | Source | Grain | Rows | Columns |
|---|---|---|---|---|
{chr(10).join(tbl)}
| _Measures | calculated (DAX) | measure host, hidden column | 1 | {N_M} measures |

* **Facts**: `FactCustomer` (funnel, tenure, retention flags, tickets per customer), `FactActivity` (monthly activity, trading and cash flow), `FactTicket` (support).
* **Dimensions**: `DimCampaign` (channel, spend, Phase 3 scorecard tier), `DimCity`, `DimDevice`, `DimSegment` (10 journey segments, group, recommended action), `DimDate`, and `DimStage` (disconnected helper for the funnel axis).
* **Keys on every fact**: `CampaignKey`, `CityKey`, `DeviceKey`, `SegmentKey` are repeated on all three facts, so each slicer filters every fact directly. This avoids fact-to-fact relationships (which would need bi-directional filtering and cause ambiguity).

## 2. Relationships (15, all active, all one-to-many, single direction)

| From (one) | To (many) | Cardinality | Filter direction | State |
|---|---|---|---|---|
{chr(10).join(rel_rows)}

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

## 5. Data-integrity checks run on the model tables ({passed} of {len(CHK)} passed)

{CHK.assign(result=CHK.passed.map({True: 'pass', False: 'FAIL'}))[['check', 'result']].to_markdown(index=False)}

Full list with details: `validation/model_integrity_checks.csv`. Column types: `validation/model_tables_meta.json`.

## 6. Traceability

`CSV (06_dashboard/data)` <- `19_build_powerbi_model_data.py` <- Phase 2 cleaned data (`loading.load_all()`) + Phase 3 segment rule (`fintech_analytics.segmentation.journey_segment`). Every dashboard measure is defined in `dax/` and re-computed independently in `06_dashboard/build_scripts/verify_phase5.py` (output: `validation/DAX_Oracle_Expected_Values.csv`).
"""
w(DOCS / "Data_Model.md", dm)

# ------------------------------------------------------------------------------------------------ 3. validation checklist
rows = []
picks = [("no filters", ["Registered Customers", "KYC Completion Rate", "First Trade Activation Rate", "MAU", "30-Day Retention", "CAC", "Total Campaign Spend", "Median Paid Cost per KYC", "Median Paid Cost per First Trade",
                         "M1 Retention", "M3 Retention", "M6 Retention", "Inactive 90d Rate", "Dormant 3m Rate", "Repeat Trader Share", "Tickets", "Tickets per 1000 Customers", "Resolved Rate", "Escalation Rate",
                         "Median Resolution Hours", "P90 Resolution Hours", "Within SLA Rate", "CSAT", "Backlog over 90 Days"]),
         ("channel=Referral", ["Registered Customers", "First Trade Activation Rate", "CAC", "M3 Retention"]), ("campaign=CMP04", ["Registered Customers", "CAC", "Cost per KYC", "Cost per First Trade", "Tickets"]),
         ("campaign=CMP07", ["Registered Customers", "CAC"]), ("city=Pune, device=Android", ["Registered Customers", "MAU", "Tickets"]), ("segment=9", ["Registered Customers", "First Trade Activation Rate", "Tickets"]),
         ("months=Aug 26", ["Registered Customers", "MAU", "Tickets", "Tickets per 1000 Customers", "Registrations MoM %"])]
n = 0
for ctx, ms in picks:
    for m in ms:
        n += 1; v = val(m, ctx); rows.append(f"| {n} | {ctx} | {m} | {fmt(m, v)} |")
funnel = [(s, val(m_)) for s, m_ in [("Registered", "Mature Customers"), ("KYC Completed", "Mature KYC Users"), ("Bank Linked", "Mature Bank Linked Users"), ("First Deposit", "Mature Funded Users"), ("First Trade", "Mature First Traders"), ("Active (30d)", "Mature Active 30d Traders")]]
chk = f"""# Dashboard Validation Checklist

Synthetic data. After building the report, put each context on a card (or a table visual) and compare with the expected value. A difference means a DAX or model error, not a data difference, because the expected values were computed independently in pandas on the same star-schema CSVs and matched to Phase 3 / Phase 4 / SQL (see `validation/Phase5_Measure_Verification.md`).

Context names: `channel=Referral` means the Channel slicer = Referral; `segment=9` means DimSegment segment 09; `months=Aug 26` means the Month slicer = Aug 26 only.

| # | Slicer context | Measure | Expected |
|---|---|---|---|
{chr(10).join(rows)}

## Funnel (mature cohort, no filters)

| Stage | Users |
|---|---|
{chr(10).join(f'| {s} | {v:,.0f} |' for s, v in funnel)}

## Budget indicators (no filters, paid campaigns)

{SIG.to_markdown(index=False)}

The complete table ({len(EXP)} measure x context checks) is `validation/DAX_Oracle_Expected_Values.csv`.
"""
w(DOCS / "Validation_Checklist.md", chk)

# ------------------------------------------------------------------------------------------------ 4. implementation guide
impl = f"""# Power BI Implementation Guide

Synthetic data. Follow these steps in **Power BI Desktop** (any recent release) to build the dashboard from this folder. Estimated time for an experienced developer: 3-4 hours; for a first build: a day.

{STATUS}

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

After the measures are in, run the first check: a card with `[Registered Customers]` must show {val('Registered Customers'):,.0f}; `[CAC]` must show Rs {val('CAC'):,.1f}.

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
"""
w(DOCS / "Implementation_Guide.md", impl)

# ------------------------------------------------------------------------------------------------ 5. README
readme = f"""# Power BI build kit and design mockups (no .pbix yet)

**All data are synthetic**: a fictional Indian retail brokerage (10,000 customers, Nov 2025 - Oct 2026, INR, snapshot 2026-10-31). Nothing here is real Groww, moomoo, Futu or Zerodha data. The data contains no revenue, so no ROI or lifetime value is shown.

{STATUS}

## Deliverables

| # | Requested | Delivered | Status |
|---|---|---|---|
| 1 | Dashboard design specification | `docs/Dashboard_Design_Specification.md` | complete |
| 2 | Power BI data model | `docs/Data_Model.md`, `mockups/Data_Model_Star_Schema.png`, `data/*.csv` (8 tables), `validation/model_integrity_checks.csv` | complete; {int(CHK.passed.sum())}/{len(CHK)} integrity checks pass |
| 3 | DAX measure library | `dax/DAX_Measure_Library.md`, `dax/Measure_Library.dax`, `dax/DimDate.dax` ({N_M} measures, {N_F} folders) | complete; logic verified in pandas, **not executed in a DAX engine** |
| 4 | Power Query transformation instructions | `power_query/` (8 queries + parameter + guide) | complete; not executed in Power BI |
| 5 | Dashboard screenshots or mockups | `mockups/Page1..4_*.png`, `Data_Model_Star_Schema.png` | **mockups only**, not Power BI screenshots |
| 6 | Power BI implementation guide | `docs/Implementation_Guide.md`, `docs/Validation_Checklist.md` | complete |
| 7 | PBIX file | - | **not generated** (Power BI Desktop unavailable here) |
| extra | Themes (light and navy) | `theme/` | palettes validated |
| extra | TMDL semantic-model scaffold | `tmdl_scaffold/` | **untested** |

## Verification

* `06_dashboard/build_scripts/verify_phase5.py` re-implements the measure logic in pandas under filter contexts (no filter, channel, campaign, city + device, segment, month) and compares with Phase 3 results, Phase 4 Excel values and independent SQL: **{N_MATCH} of {N_CMP} match** (`validation/Phase5_Measure_Verification.md`).
* One defect was found and fixed through this check: the inactivity-distribution measure had used the 90-day-eligible base; Phase 3 (and now the measure) uses the 30-day-eligible base.
* A further defect was fixed in review: documentation claimed an inactive relationship was used by cohort measures; no measure uses it, so the relationship was removed (15 relationships remain).
* Not oracle-tested ({N_M - N_TESTED} of {N_M} measures): parameters, text/label measures, shares, ranks and time-intelligence helpers that depend on the Power BI engine. They are simple wrappers over tested measures.

## Headline numbers (traceable to the checklist)

| Measure | Value |
|---|---|
| Registered customers | {val('Registered Customers'):,.0f} |
| KYC completion (mature cohort) | {val('KYC Completion Rate'):.1%} |
| First-trade activation | {val('First Trade Activation Rate'):.1%} |
| MAU Oct 2026 | {val('MAU'):,.0f} ({val('MAU Share of Customers'):.1%} of customers) |
| 30-day retention | {val('30-Day Retention'):.1%} |
| Blended CAC (paid) | Rs {val('CAC'):,.1f} |
| Total campaign spend | Rs {val('Total Campaign Spend'):,.0f} |
| Support tickets | {val('Tickets'):,.0f} ({val('Tickets per 1000 Customers'):.1f} per 1,000 customers) |
| CSAT | {val('CSAT'):.2f} |

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
"""
w(PB / "README.md", readme)
print("docs written:", *sorted(str(p.relative_to(PB)) for p in list(DOCS.glob("*.md")) + [PB / "README.md"]), sep="\n  ")
