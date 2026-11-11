# DAX Measure Library

Synthetic data (fictional Indian retail brokerage, INR, snapshot 2026-10-31). **117 measures** in the `_Measures` table, grouped by display folder.

> **Verification status.** Power BI Desktop is not available in the build environment, so this DAX has *not been executed in a DAX engine*. Each measure's logic was re-implemented in pandas on the same star-schema CSVs and checked against validated Phase 3/4 figures and independent SQL (`06_dashboard/build_scripts/verify_phase5.py`, results in `06_dashboard/validation/`). After you build the model, compare cards with `DAX_Oracle_Expected_Values.csv`.

## How to read the measures

- **Mature cohort**: funnel rates use customers registered before 2026-10 (`FactCustomer[FunnelMature] = 1`). October-2026 registrants have not had time to finish onboarding.
- **CAC family** divides *recorded campaign spend* by paid registrations. Spend is not dated in the source data, so these measures deliberately ignore the date, city, device and segment slicers (`REMOVEFILTERS`) and show a scope note. Organic campaigns return **blank**, not zero.
- **Churn proxies**: *Inactive 90d* and *Dormant 3m* are inactivity proxies, not confirmed churn.
- **Segments** are a snapshot attribute as of 2026-10-31, so a month slicer combined with a segment slicer shows customers currently in that segment.
- **Budget indicators** (Cost Efficiency Index, Budget Signal) are directional: they compare cost per first trade to the peer median. The data has no revenue, so they are not ROI.

## Prerequisites

1. Calculated table `DimDate` - see [DimDate.dax](DimDate.dax); mark it as the date table on `[Date]`.
2. Empty measure host table: `_Measures = ROW("Placeholder", BLANK())` (calculated table); hide its column.
3. Relationships as in `docs/Data_Model.md` (15 one-to-many relationships, all active). The cohort matrix needs no extra relationship: it uses `FactActivity[RegMonthDate]` (rows) and `FactActivity[MonthsSinceRegistration]` (columns) directly.

## 00 Parameters (6)

| Measure | Format | Purpose |
|---|---|---|
| Snapshot Date | `yyyy-mm-dd` | Data cut-off; all *_asof columns count events on or before this date. |
| SLA Hours | `#,0` | Illustrative internal resolution SLA (hours). Not a regulatory figure. |
| Efficient Index Threshold | `#,0.00` | Cost Efficiency Index at or above this = efficient vs paid peers. |
| Costly Index Threshold | `#,0.00` | Cost Efficiency Index at or below this = costly vs paid peers. |
| Repeat Base Months | `#,0` | Customers need this many observed months to be judged on repeat trading. |
| Repeat Trader Min Months | `#,0` | Trading in at least this many calendar months = repeat trader. |

### Snapshot Date

```dax
Snapshot Date =
DATE(2026, 10, 31)
```

### SLA Hours

```dax
SLA Hours =
24
```

### Efficient Index Threshold

```dax
Efficient Index Threshold =
1.15
```

### Costly Index Threshold

```dax
Costly Index Threshold =
0.85
```

### Repeat Base Months

```dax
Repeat Base Months =
4
```

### Repeat Trader Min Months

```dax
Repeat Trader Min Months =
2
```

## 01 Customers and Funnel (26)

| Measure | Format | Purpose |
|---|---|---|
| Registered Customers | `#,0` | Customers registered (all cohorts). |
| Mature Customers | `#,0` | Customers registered before Oct-2026; denominator for funnel rates. |
| Mature KYC Users | `#,0` | Mature customers with KYC completed (as of snapshot). |
| Mature Bank Linked Users | `#,0` | Mature customers with a bank account linked. |
| Mature Funded Users | `#,0` | Mature customers who made a first deposit. |
| Mature First Traders | `#,0` | Mature customers who placed a first trade. |
| Mature Active 30d Traders | `#,0` | Mature first traders active in the last 30 days (funnel stage 6). |
| KYC Completion Rate | `0.0%` | KYC completed / mature registered. |
| Bank Link Conversion | `0.0%` | Bank linked / KYC completed. |
| First Deposit Conversion | `0.0%` | Funded / bank linked. |
| First Trade Conversion | `0.0%` | First traders / funded (activation of funded customers). |
| First Trade Activation Rate | `0.0%` | End-to-end: mature registered -> first trade. |
| Active 30d Share of First Traders | `0.0%` | Funnel stage 6 conversion. |
| Funnel Users | `#,0` | Users reached at the stage on the DimStage axis (disconnected table). |
| Funnel Previous Stage Users | `#,0` | Users who reached the stage before the one on the axis. |
| Funnel % of Registered | `0.0%` | Stage users as a share of mature registered. |
| Funnel Step Conversion | `0.0%` | Stage users / previous-stage users. |
| Funnel Users Lost | `#,0` | Users lost between the previous stage and this one. |
| Funnel Drop-off Rate | `0.0%` | Share of previous-stage users lost at this step. |
| Total Funnel Loss | `#,0` | All users lost between registration and active-30d trader. |
| Share of Funnel Losses | `0.0%` | Bottleneck share: this step's losses / all losses. |
| Median Days in Stage | `#,0.0` | Median days from the previous stage (mature customers who reached the stage). |
| Median Days Registration to First Trade | `#,0.0` | Median end-to-end time to first trade. |
| Funded Never Traded | `#,0` | High-potential activation pool: funded, no trade yet. |
| Funded Never Traded Deposits INR | `#,0` | Sum of first deposits of funded-never-traded customers (balance sitting idle; not revenue). |
| Stalled Onboarding Customers | `#,0` | Customers stalled beyond the historical maximum stage lag (segments 02-05). |

### Registered Customers

```dax
Registered Customers =
COUNTROWS(FactCustomer)
```

### Mature Customers

```dax
Mature Customers =
CALCULATE(COUNTROWS(FactCustomer), FactCustomer[FunnelMature] = 1)
```

### Mature KYC Users

```dax
Mature KYC Users =
CALCULATE(SUM(FactCustomer[KYCDone]), FactCustomer[FunnelMature] = 1)
```

### Mature Bank Linked Users

```dax
Mature Bank Linked Users =
CALCULATE(SUM(FactCustomer[BankLinked]), FactCustomer[FunnelMature] = 1)
```

### Mature Funded Users

```dax
Mature Funded Users =
CALCULATE(SUM(FactCustomer[Deposited]), FactCustomer[FunnelMature] = 1)
```

### Mature First Traders

```dax
Mature First Traders =
CALCULATE(SUM(FactCustomer[Traded]), FactCustomer[FunnelMature] = 1)
```

### Mature Active 30d Traders

```dax
Mature Active 30d Traders =
CALCULATE(
    COUNTROWS(FactCustomer),
    FactCustomer[FunnelMature] = 1,
    FactCustomer[Traded] = 1,
    FactCustomer[Active30d] = 1
)
```

### KYC Completion Rate

```dax
KYC Completion Rate =
DIVIDE([Mature KYC Users], [Mature Customers])
```

### Bank Link Conversion

```dax
Bank Link Conversion =
DIVIDE([Mature Bank Linked Users], [Mature KYC Users])
```

### First Deposit Conversion

```dax
First Deposit Conversion =
DIVIDE([Mature Funded Users], [Mature Bank Linked Users])
```

### First Trade Conversion

```dax
First Trade Conversion =
DIVIDE([Mature First Traders], [Mature Funded Users])
```

### First Trade Activation Rate

```dax
First Trade Activation Rate =
DIVIDE([Mature First Traders], [Mature Customers])
```

### Active 30d Share of First Traders

```dax
Active 30d Share of First Traders =
DIVIDE([Mature Active 30d Traders], [Mature First Traders])
```

### Funnel Users

```dax
Funnel Users =
SWITCH(
    SELECTEDVALUE(DimStage[StageName]),
    "Registered",
    [Mature Customers],
    "KYC Completed",
    [Mature KYC Users],
    "Bank Linked",
    [Mature Bank Linked Users],
    "First Deposit",
    [Mature Funded Users],
    "First Trade",
    [Mature First Traders],
    "Active (30d)",
    [Mature Active 30d Traders],
    BLANK()
)
```

### Funnel Previous Stage Users

```dax
Funnel Previous Stage Users =
SWITCH(
    SELECTEDVALUE(DimStage[StageName]),
    "KYC Completed",
    [Mature Customers],
    "Bank Linked",
    [Mature KYC Users],
    "First Deposit",
    [Mature Bank Linked Users],
    "First Trade",
    [Mature Funded Users],
    "Active (30d)",
    [Mature First Traders],
    BLANK()
)
```

### Funnel % of Registered

```dax
Funnel % of Registered =
DIVIDE([Funnel Users], [Mature Customers])
```

### Funnel Step Conversion

```dax
Funnel Step Conversion =
DIVIDE([Funnel Users], [Funnel Previous Stage Users])
```

### Funnel Users Lost

```dax
Funnel Users Lost =
IF(
    ISBLANK([Funnel Previous Stage Users]),
    BLANK(),
    [Funnel Previous Stage Users] - [Funnel Users]
)
```

### Funnel Drop-off Rate

```dax
Funnel Drop-off Rate =
DIVIDE([Funnel Users Lost], [Funnel Previous Stage Users])
```

### Total Funnel Loss

```dax
Total Funnel Loss =
[Mature Customers] - [Mature Active 30d Traders]
```

### Share of Funnel Losses

```dax
Share of Funnel Losses =
DIVIDE([Funnel Users Lost], [Total Funnel Loss])
```

### Median Days in Stage

```dax
Median Days in Stage =
CALCULATE(
    SWITCH(
        SELECTEDVALUE(DimStage[StageName]),
        "KYC Completed",
        MEDIAN(FactCustomer[DaysRegToKYC]),
        "Bank Linked",
        MEDIAN(FactCustomer[DaysKYCToBank]),
        "First Deposit",
        MEDIAN(FactCustomer[DaysBankToDeposit]),
        "First Trade",
        MEDIAN(FactCustomer[DaysDepositToTrade]),
        BLANK()
    ),
    FactCustomer[FunnelMature] = 1
)
```

### Median Days Registration to First Trade

```dax
Median Days Registration to First Trade =
CALCULATE(MEDIAN(FactCustomer[DaysRegToTrade]), FactCustomer[FunnelMature] = 1)
```

### Funded Never Traded

```dax
Funded Never Traded =
CALCULATE(COUNTROWS(FactCustomer), FactCustomer[Deposited] = 1, FactCustomer[Traded] = 0)
```

### Funded Never Traded Deposits INR

```dax
Funded Never Traded Deposits INR =
CALCULATE(
    SUM(FactCustomer[FirstDepositAmountINR]),
    FactCustomer[Deposited] = 1,
    FactCustomer[Traded] = 0
)
```

### Stalled Onboarding Customers

```dax
Stalled Onboarding Customers =
CALCULATE(COUNTROWS(FactCustomer), DimSegment[SegmentKey] IN {2, 3, 4, 5})
```

## 02 Acquisition and Marketing (24)

| Measure | Format | Purpose |
|---|---|---|
| Total Campaign Spend | `#,0` | Recorded campaign spend (INR). Spend is not dated, so it ignores month/city/device/segment filters by design. |
| Paid Spend | `#,0` | Spend of campaigns with recorded spend. |
| Registered Customers (Full Period) | `#,0` | Registrations over the whole period; only campaign/channel filters apply. Matches the undated spend. |
| Paid Registrations (Full Period) | `#,0` | Registrations from campaigns with recorded spend. |
| CAC | `#,0.0` | Customer acquisition cost = recorded spend / registered customers of paid campaigns. Blank for organic (no spend recorded) - not zero. |
| KYC Rate (Paid, Full Period) | `0.0%` | Mature KYC rate of the paid population in scope. |
| First Trade Rate (Paid, Full Period) | `0.0%` | Mature first-trade rate of the paid population in scope. |
| Cost per KYC | `#,0` | CAC / mature KYC rate = cost per KYC-complete customer at maturity. |
| Cost per First Trade | `#,0` | CAC / mature first-trade rate = cost per first trader at maturity. No revenue or ROI is implied. |
| Paid Share of Registrations | `0.0%` | Share of registrations from campaigns with recorded spend. |
| Registration Share | `0.0%` | Share of selected registrations (campaign axis). |
| Spend Share | `0.0%` | Share of selected spend. |
| City Share of Registrations | `0.0%` | City axis share. |
| Device Share of Registrations | `0.0%` | Device axis share. |
| Rank Cost per First Trade (Paid) | `#,0` | 1 = lowest cost per first trader among selected paid campaigns. |
| Rank First Trade Rate | `#,0` | 1 = highest mature first-trade rate among selected campaigns. |
| Median Paid Cost per First Trade | `#,0` | Median across selected paid campaigns (peer benchmark). |
| Median Paid Cost per KYC | `#,0` | Median across selected paid campaigns (peer benchmark for onboarding cost). |
| Cost Efficiency Index | `#,0.00` | Peer median / own cost per first trade. Above 1 = cheaper than the median paid campaign. |
| Budget Signal | `` | Indicator only: ranks cost per first trader against peers. Not a recommendation without a test (no revenue data). |
| Evidence Strength | `` | Statistical caution carried over from Phase 3. |
| Phase 3 Scorecard Tier | `` | Tier assigned by the Phase 3 scorecard (static input). |
| Phase 3 Overall Score | `#,0.0` | Phase 3 composite score (paid campaigns only). |
| CAC Scope Note | `` | Warning shown on cards when a filter the spend cannot follow is active. |

### Total Campaign Spend

```dax
Total Campaign Spend =
SUM(DimCampaign[CampaignSpendINR])
```

### Paid Spend

```dax
Paid Spend =
CALCULATE([Total Campaign Spend], DimCampaign[IsPaid] = 1)
```

### Registered Customers (Full Period)

```dax
Registered Customers (Full Period) =
CALCULATE(
    [Registered Customers],
    REMOVEFILTERS(DimDate),
    REMOVEFILTERS(DimCity),
    REMOVEFILTERS(DimDevice),
    REMOVEFILTERS(DimSegment)
)
```

### Paid Registrations (Full Period)

```dax
Paid Registrations (Full Period) =
CALCULATE([Registered Customers (Full Period)], DimCampaign[IsPaid] = 1)
```

### CAC

```dax
CAC =
DIVIDE([Total Campaign Spend], [Paid Registrations (Full Period)])
```

### KYC Rate (Paid, Full Period)

```dax
KYC Rate (Paid, Full Period) =
CALCULATE(
    [KYC Completion Rate],
    REMOVEFILTERS(DimDate),
    REMOVEFILTERS(DimCity),
    REMOVEFILTERS(DimDevice),
    REMOVEFILTERS(DimSegment),
    DimCampaign[IsPaid] = 1
)
```

### First Trade Rate (Paid, Full Period)

```dax
First Trade Rate (Paid, Full Period) =
CALCULATE(
    [First Trade Activation Rate],
    REMOVEFILTERS(DimDate),
    REMOVEFILTERS(DimCity),
    REMOVEFILTERS(DimDevice),
    REMOVEFILTERS(DimSegment),
    DimCampaign[IsPaid] = 1
)
```

### Cost per KYC

```dax
Cost per KYC =
DIVIDE([CAC], [KYC Rate (Paid, Full Period)])
```

### Cost per First Trade

```dax
Cost per First Trade =
DIVIDE([CAC], [First Trade Rate (Paid, Full Period)])
```

### Paid Share of Registrations

```dax
Paid Share of Registrations =
DIVIDE(CALCULATE([Registered Customers], DimCampaign[IsPaid] = 1), [Registered Customers])
```

### Registration Share

```dax
Registration Share =
DIVIDE([Registered Customers], CALCULATE([Registered Customers], ALLSELECTED(DimCampaign)))
```

### Spend Share

```dax
Spend Share =
DIVIDE([Total Campaign Spend], CALCULATE([Total Campaign Spend], ALLSELECTED(DimCampaign)))
```

### City Share of Registrations

```dax
City Share of Registrations =
DIVIDE([Registered Customers], CALCULATE([Registered Customers], ALLSELECTED(DimCity)))
```

### Device Share of Registrations

```dax
Device Share of Registrations =
DIVIDE([Registered Customers], CALCULATE([Registered Customers], ALLSELECTED(DimDevice)))
```

### Rank Cost per First Trade (Paid)

```dax
Rank Cost per First Trade (Paid) =
IF(
    ISBLANK([Cost per First Trade]),
    BLANK(),
    RANKX(
        FILTER(ALLSELECTED(DimCampaign[CampaignName]), NOT(ISBLANK([Cost per First Trade]))),
        [Cost per First Trade],
        ,
        ASC,
        DENSE
    )
)
```

### Rank First Trade Rate

```dax
Rank First Trade Rate =
RANKX(ALLSELECTED(DimCampaign[CampaignName]), [First Trade Activation Rate], , DESC, DENSE)
```

### Median Paid Cost per First Trade

```dax
Median Paid Cost per First Trade =
MEDIANX(
    FILTER(ALLSELECTED(DimCampaign[CampaignName]), NOT(ISBLANK([Cost per First Trade]))),
    [Cost per First Trade]
)
```

### Median Paid Cost per KYC

```dax
Median Paid Cost per KYC =
MEDIANX(
    FILTER(ALLSELECTED(DimCampaign[CampaignName]), NOT(ISBLANK([Cost per KYC]))),
    [Cost per KYC]
)
```

### Cost Efficiency Index

```dax
Cost Efficiency Index =
DIVIDE([Median Paid Cost per First Trade], [Cost per First Trade])
```

### Budget Signal

```dax
Budget Signal =
SWITCH(
    TRUE(),
    ISBLANK([Cost per First Trade]),
    "Organic - no spend to optimise",
    [Cost Efficiency Index] >= [Efficient Index Threshold],
    "Efficient vs peers - protect / test scaling",
    [Cost Efficiency Index] <= [Costly Index Threshold],
    "Costly vs peers - review / test cut-back",
    "In line with peers"
)
```

### Evidence Strength

```dax
Evidence Strength =
IF(
    SELECTEDVALUE(DimCampaign[Phase3SignificantAt5pct]) = "Yes",
    "First-trade rate differs significantly from other campaigns (Phase 3, Holm)",
    "Not significant at 5% - treat as indicative"
)
```

### Phase 3 Scorecard Tier

```dax
Phase 3 Scorecard Tier =
SELECTEDVALUE(DimCampaign[Phase3Tier], "Multiple campaigns")
```

### Phase 3 Overall Score

```dax
Phase 3 Overall Score =
SELECTEDVALUE(DimCampaign[Phase3OverallScore])
```

### CAC Scope Note

```dax
CAC Scope Note =
IF(
    ISFILTERED(
        DimDate
    ) || ISFILTERED(DimCity) || ISFILTERED(DimDevice) || ISFILTERED(DimSegment),
    "Spend is not dated: CAC and cost per trade ignore month, city, device and segment filters.",
    ""
)
```

## 03 Retention and Engagement (26)

| Measure | Format | Purpose |
|---|---|---|
| Customers To Date | `#,0` | Cumulative registrations up to the last selected date. |
| MAU | `#,0` | Monthly active users of the latest month in context (Oct-2026 when unfiltered). |
| MAU Share of Customers | `0.0%` | MAU / customers registered by month end. |
| 30-Day Retention | `0.0%` | Share active in the last 30 days among customers with tenure of at least 31 days. |
| Inactive 90d Rate | `0.0%` | Share inactive for more than 90 days (proxy for churn, not confirmed churn). |
| Dormant 3m Rate | `0.0%` | Share with no active month Aug-Oct 2026, customers registered by Jul-2026 (churn proxy). |
| Cohort Retention | `0.0%` | Share active - use in the cohort matrix (rows RegMonthDate, columns MonthsSinceRegistration). |
| Cohort Size | `#,0` | Customers in the registration cohort. |
| M1 Retention | `0.00%` | Active the calendar month after registration (pooled). |
| M3 Retention | `0.00%` | Active 3 calendar months after the registration month (pooled). |
| M6 Retention | `0.00%` | Active 6 calendar months after the registration month (pooled). |
| Inactivity Share (Eligible) | `0.0%` | Share of 30-day-eligible customers (tenure of at least 31 days) per days-since-last-activity bucket; same base as the Phase 3 inactivity distribution. |
| Trading Users | `#,0` | Customer-months with at least one trade (monthly trading users when sliced by month). |
| Trades | `#,0` | Number of trades. |
| Trading Value INR mn | `#,0.00` | Trading value in INR millions. |
| Deposits INR mn | `#,0.00` | Deposits in INR millions. |
| Withdrawals INR mn | `#,0.00` | Withdrawals in INR millions. |
| Net Flow INR mn | `#,0.00` | Deposits minus withdrawals (INR millions). |
| Withdrawal to Deposit Ratio | `0.0%` | Withdrawals as a share of deposits. |
| Trades per Trading User | `#,0.0` | Average trades per trading customer-month. |
| Avg Trade Value INR | `#,0` | Average value per trade. |
| Ever-Traders (Repeat Base) | `#,0` | Customers with enough history that traded in at least one month. |
| Repeat Traders | `#,0` | Customers who traded in 2+ calendar months. |
| Repeat Trader Share | `0.0%` | Repeat traders / ever-traders. |
| Segment Share | `0.0%` | Share of selected customers per segment. |
| Avg 6m Trading Value INR | `#,0` | Mean trading value over the last six months. |

### Customers To Date

```dax
Customers To Date =
VAR d = MAX(DimDate[Date])
RETURN
    CALCULATE([Registered Customers], FILTER(ALL(DimDate), DimDate[Date] <= d))
```

### MAU

```dax
MAU =
VAR mth = MAX(FactActivity[ActivityMonthDate])
RETURN
    CALCULATE(SUM(FactActivity[ActiveInMonth]), FactActivity[ActivityMonthDate] = mth)
```

### MAU Share of Customers

```dax
MAU Share of Customers =
VAR mth = MAX(FactActivity[ActivityMonthDate])
RETURN
    DIVIDE(
        [MAU],
        CALCULATE(
            [Registered Customers],
            FILTER(ALL(DimDate), DimDate[Date] <= EOMONTH(mth, 0))
        )
    )
```

### 30-Day Retention

```dax
30-Day Retention =
CALCULATE(AVERAGE(FactCustomer[Active30d]), FactCustomer[Eligible30d] = 1)
```

### Inactive 90d Rate

```dax
Inactive 90d Rate =
CALCULATE(AVERAGE(FactCustomer[Inactive90d]), FactCustomer[Eligible90d] = 1)
```

### Dormant 3m Rate

```dax
Dormant 3m Rate =
AVERAGE(FactCustomer[Dormant3m])
```

### Cohort Retention

```dax
Cohort Retention =
AVERAGE(FactActivity[ActiveInMonth])
```

### Cohort Size

```dax
Cohort Size =
CALCULATE(DISTINCTCOUNT(FactActivity[CustomerID]), FactActivity[MonthsSinceRegistration] = 0)
```

### M1 Retention

```dax
M1 Retention =
CALCULATE(AVERAGE(FactActivity[ActiveInMonth]), FactActivity[MonthsSinceRegistration] = 1)
```

### M3 Retention

```dax
M3 Retention =
CALCULATE(AVERAGE(FactActivity[ActiveInMonth]), FactActivity[MonthsSinceRegistration] = 3)
```

### M6 Retention

```dax
M6 Retention =
CALCULATE(AVERAGE(FactActivity[ActiveInMonth]), FactActivity[MonthsSinceRegistration] = 6)
```

### Inactivity Share (Eligible)

```dax
Inactivity Share (Eligible) =
DIVIDE(
    CALCULATE(COUNTROWS(FactCustomer), FactCustomer[Eligible30d] = 1),
    CALCULATE(
        COUNTROWS(FactCustomer),
        FactCustomer[Eligible30d] = 1,
        REMOVEFILTERS(FactCustomer[InactivityBucket])
    )
)
```

### Trading Users

```dax
Trading Users =
SUM(FactActivity[TradedInMonth])
```

### Trades

```dax
Trades =
SUM(FactActivity[TradeCount])
```

### Trading Value INR mn

```dax
Trading Value INR mn =
DIVIDE(SUM(FactActivity[TradingValueINR]), 1000000)
```

### Deposits INR mn

```dax
Deposits INR mn =
DIVIDE(SUM(FactActivity[DepositValueINR]), 1000000)
```

### Withdrawals INR mn

```dax
Withdrawals INR mn =
DIVIDE(SUM(FactActivity[WithdrawalValueINR]), 1000000)
```

### Net Flow INR mn

```dax
Net Flow INR mn =
DIVIDE(SUM(FactActivity[NetFlowINR]), 1000000)
```

### Withdrawal to Deposit Ratio

```dax
Withdrawal to Deposit Ratio =
DIVIDE(SUM(FactActivity[WithdrawalValueINR]), SUM(FactActivity[DepositValueINR]))
```

### Trades per Trading User

```dax
Trades per Trading User =
DIVIDE([Trades], [Trading Users])
```

### Avg Trade Value INR

```dax
Avg Trade Value INR =
DIVIDE(SUM(FactActivity[TradingValueINR]), [Trades])
```

### Ever-Traders (Repeat Base)

```dax
Ever-Traders (Repeat Base) =
CALCULATE(
    COUNTROWS(FactCustomer),
    FactCustomer[MonthsObserved] >= [Repeat Base Months],
    FactCustomer[TradeMonths] >= 1
)
```

### Repeat Traders

```dax
Repeat Traders =
CALCULATE(
    COUNTROWS(FactCustomer),
    FactCustomer[MonthsObserved] >= [Repeat Base Months],
    FactCustomer[TradeMonths] >= [Repeat Trader Min Months]
)
```

### Repeat Trader Share

```dax
Repeat Trader Share =
DIVIDE([Repeat Traders], [Ever-Traders (Repeat Base)])
```

### Segment Share

```dax
Segment Share =
DIVIDE([Registered Customers], CALCULATE([Registered Customers], ALLSELECTED(DimSegment)))
```

### Avg 6m Trading Value INR

```dax
Avg 6m Trading Value INR =
AVERAGE(FactCustomer[TradingValue6mINR])
```

## 04 Time Intelligence (10)

| Measure | Format | Purpose |
|---|---|---|
| Registered Customers PM | `#,0` | Registrations in the previous month. |
| Registrations MoM % | `0.0%` | Month-over-month change in registrations (single month in context). |
| Registrations 3M Avg | `#,0.0` | Rolling 3-month average of monthly registrations (fewer months at the start). |
| Registered YTD | `#,0` | Calendar year-to-date registrations (data cover Nov-2025 to Oct-2026, so 2025 YTD = Nov-Dec). |
| MAU PM | `#,0` | MAU of the previous month. |
| MAU MoM % | `0.0%` | Month-over-month change in MAU. |
| Tickets PM | `#,0` | Tickets raised in the previous month. |
| Tickets MoM % | `0.0%` | Month-over-month change in ticket volume. |
| Trading Value INR mn PM | `#,0.00` | Trading value of the previous month. |
| Trading Value MoM % | `0.0%` | Month-over-month change in trading value. |

### Registered Customers PM

```dax
Registered Customers PM =
CALCULATE([Registered Customers], DATEADD(DimDate[Date], -1, MONTH))
```

### Registrations MoM %

```dax
Registrations MoM % =
IF(HASONEVALUE(DimDate[MonthLabel]),
VAR pm = [Registered Customers PM]
RETURN
    IF(ISBLANK(pm), BLANK(), DIVIDE([Registered Customers] - pm, pm)), BLANK())
```

### Registrations 3M Avg

```dax
Registrations 3M Avg =
VAR d = MAX(DimDate[Date])
VAR win = DATESINPERIOD(DimDate[Date], d, -3, MONTH)
RETURN
    DIVIDE(
        CALCULATE([Registered Customers], win),
        CALCULATE(DISTINCTCOUNT(DimDate[MonthStart]), win)
    )
```

### Registered YTD

```dax
Registered YTD =
CALCULATE([Registered Customers], DATESYTD(DimDate[Date]))
```

### MAU PM

```dax
MAU PM =
CALCULATE([MAU], DATEADD(DimDate[Date], -1, MONTH))
```

### MAU MoM %

```dax
MAU MoM % =
IF(HASONEVALUE(DimDate[MonthLabel]),
VAR pm = [MAU PM]
RETURN
    IF(ISBLANK(pm), BLANK(), DIVIDE([MAU] - pm, pm)), BLANK())
```

### Tickets PM

```dax
Tickets PM =
CALCULATE([Tickets], DATEADD(DimDate[Date], -1, MONTH))
```

### Tickets MoM %

```dax
Tickets MoM % =
IF(HASONEVALUE(DimDate[MonthLabel]),
VAR pm = [Tickets PM]
RETURN
    IF(ISBLANK(pm), BLANK(), DIVIDE([Tickets] - pm, pm)), BLANK())
```

### Trading Value INR mn PM

```dax
Trading Value INR mn PM =
CALCULATE([Trading Value INR mn], DATEADD(DimDate[Date], -1, MONTH))
```

### Trading Value MoM %

```dax
Trading Value MoM % =
IF(HASONEVALUE(DimDate[MonthLabel]),
VAR pm = [Trading Value INR mn PM]
RETURN
    IF(ISBLANK(pm), BLANK(), DIVIDE([Trading Value INR mn] - pm, pm)), BLANK())
```

## 05 Customer Operations (22)

| Measure | Format | Purpose |
|---|---|---|
| Tickets | `#,0` | Support tickets. |
| Tickets per 1000 Customers | `#,0` | Tickets per 1,000 customers registered to date (whole period = Phase 3 definition). |
| Resolved Tickets | `#,0` | Tickets with a resolution. |
| Unresolved Tickets | `#,0` | Open plus escalated tickets (backlog). |
| Open Tickets | `#,0` | Tickets with status Open. |
| Escalated Tickets | `#,0` | Tickets with status Escalated. |
| Resolved Rate | `0.0%` | Resolved / all tickets. |
| Escalation Rate | `0.00%` | Escalated / all tickets. |
| Avg Resolution Hours | `#,0.0` | Mean hours to resolve (resolved tickets). |
| Median Resolution Hours | `#,0.0` | Median hours to resolve (typical customer wait). |
| P90 Resolution Hours | `#,0.0` | 90th percentile of resolution hours. |
| Within SLA Rate | `0.0%` | Resolved within the illustrative SLA hours. |
| CSAT | `#,0.00` | Mean customer satisfaction (1-5), rated tickets only. |
| CSAT Top-Box | `0.0%` | Share of ratings 4-5. |
| CSAT Bottom-Box | `0.0%` | Share of ratings 1-2. |
| Backlog over 90 Days | `#,0` | Unresolved tickets older than 90 days. |
| Category Share | `0.0%` | Share of tickets per category. |
| Priority Share | `0.0%` | Share of tickets per priority. |
| High Priority Share | `0.0%` | High-priority tickets / all tickets. |
| Onboarding Tickets | `#,0` | Tickets tied to an onboarding stage (KYC, bank, deposit, trade). |
| Tickets While Stage Pending | `#,0` | Onboarding tickets raised while the related stage was still pending. |
| Pending Stage Ticket Share | `0.0%` | Share of onboarding tickets raised while the stage was pending. |

### Tickets

```dax
Tickets =
COUNTROWS(FactTicket)
```

### Tickets per 1000 Customers

```dax
Tickets per 1000 Customers =
DIVIDE([Tickets], [Customers To Date]) * 1000
```

### Resolved Tickets

```dax
Resolved Tickets =
SUM(FactTicket[IsResolved])
```

### Unresolved Tickets

```dax
Unresolved Tickets =
SUM(FactTicket[IsUnresolved])
```

### Open Tickets

```dax
Open Tickets =
CALCULATE(COUNTROWS(FactTicket), FactTicket[Status] = "Open")
```

### Escalated Tickets

```dax
Escalated Tickets =
SUM(FactTicket[IsEscalated])
```

### Resolved Rate

```dax
Resolved Rate =
DIVIDE([Resolved Tickets], [Tickets])
```

### Escalation Rate

```dax
Escalation Rate =
DIVIDE([Escalated Tickets], [Tickets])
```

### Avg Resolution Hours

```dax
Avg Resolution Hours =
AVERAGE(FactTicket[ResolutionHours])
```

### Median Resolution Hours

```dax
Median Resolution Hours =
MEDIAN(FactTicket[ResolutionHours])
```

### P90 Resolution Hours

```dax
P90 Resolution Hours =
PERCENTILE.INC(FactTicket[ResolutionHours], 0.9)
```

### Within SLA Rate

```dax
Within SLA Rate =
DIVIDE(
    CALCULATE(
        COUNTROWS(FactTicket),
        FactTicket[IsResolved] = 1,
        FactTicket[ResolutionHours] <= [SLA Hours]
    ),
    [Resolved Tickets]
)
```

### CSAT

```dax
CSAT =
AVERAGE(FactTicket[CSAT])
```

### CSAT Top-Box

```dax
CSAT Top-Box =
DIVIDE(CALCULATE(COUNTROWS(FactTicket), FactTicket[CSAT] >= 4), COUNT(FactTicket[CSAT]))
```

### CSAT Bottom-Box

```dax
CSAT Bottom-Box =
DIVIDE(CALCULATE(COUNTROWS(FactTicket), FactTicket[CSAT] <= 2), COUNT(FactTicket[CSAT]))
```

### Backlog over 90 Days

```dax
Backlog over 90 Days =
CALCULATE(COUNTROWS(FactTicket), FactTicket[IsUnresolved] = 1, FactTicket[TicketAgeDays] > 90)
```

### Category Share

```dax
Category Share =
DIVIDE([Tickets], CALCULATE([Tickets], REMOVEFILTERS(FactTicket[Category])))
```

### Priority Share

```dax
Priority Share =
DIVIDE([Tickets], CALCULATE([Tickets], REMOVEFILTERS(FactTicket[Priority])))
```

### High Priority Share

```dax
High Priority Share =
DIVIDE(CALCULATE(COUNTROWS(FactTicket), FactTicket[Priority] = "High"), [Tickets])
```

### Onboarding Tickets

```dax
Onboarding Tickets =
CALCULATE(COUNTROWS(FactTicket), FactTicket[RelatedFunnelStage] <> "none")
```

### Tickets While Stage Pending

```dax
Tickets While Stage Pending =
CALCULATE(COUNTROWS(FactTicket), FactTicket[StagePendingAtTicket] = 1)
```

### Pending Stage Ticket Share

```dax
Pending Stage Ticket Share =
DIVIDE([Tickets While Stage Pending], [Onboarding Tickets])
```

## 06 Labels and Notes (3)

| Measure | Format | Purpose |
|---|---|---|
| Mature Cohort Note | `` | Footnote for funnel visuals. |
| Data Disclaimer | `` | Footer on every page. |
| Proxy Note | `` | Footnote for retention visuals. |

### Mature Cohort Note

```dax
Mature Cohort Note =
"Funnel rates use the mature cohort (registered before Oct-2026): n = " & FORMAT(
    [Mature Customers],
    "#,0"
)
```

### Data Disclaimer

```dax
Data Disclaimer =
"Synthetic data - fictional Indian retail brokerage; not real customer data."
```

### Proxy Note

```dax
Proxy Note =
"Inactive 90d and Dormant 3m are churn proxies, not confirmed churn."
```
