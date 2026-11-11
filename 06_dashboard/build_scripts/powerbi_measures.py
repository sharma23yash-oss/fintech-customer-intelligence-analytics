"""Single source of truth for the Power BI measure library (SYNTHETIC-data project).
Imported by 21_emit_powerbi_artifacts.py (-> .dax, .md, TMDL) and verify_phase5.py (-> pandas oracle).
Each entry: (folder, name, dax, format, description)."""
N0, P1, P2, D1, D2, TXT, INR = "#,0", "0.0%", "0.00%", "#,0.0", "#,0.00", "", "#,0"
M = []
def m(folder, name, dax, fmt, desc): M.append((folder, name, " ".join(dax.split()), fmt, desc))

# ---------------------------------------------------------------- 00 Parameters
f = "00 Parameters"
m(f, "Snapshot Date", "DATE(2026, 10, 31)", "yyyy-mm-dd", "Data cut-off; all *_asof columns count events on or before this date.")
m(f, "SLA Hours", "24", N0, "Illustrative internal resolution SLA (hours). Not a regulatory figure.")
m(f, "Efficient Index Threshold", "1.15", D2, "Cost Efficiency Index at or above this = efficient vs paid peers.")
m(f, "Costly Index Threshold", "0.85", D2, "Cost Efficiency Index at or below this = costly vs paid peers.")
m(f, "Repeat Base Months", "4", N0, "Customers need this many observed months to be judged on repeat trading.")
m(f, "Repeat Trader Min Months", "2", N0, "Trading in at least this many calendar months = repeat trader.")

# ---------------------------------------------------------------- 01 Customers & funnel
f = "01 Customers and Funnel"
m(f, "Registered Customers", "COUNTROWS(FactCustomer)", N0, "Customers registered (all cohorts).")
m(f, "Mature Customers", "CALCULATE(COUNTROWS(FactCustomer), FactCustomer[FunnelMature] = 1)", N0, "Customers registered before Oct-2026; denominator for funnel rates.")
m(f, "Mature KYC Users", "CALCULATE(SUM(FactCustomer[KYCDone]), FactCustomer[FunnelMature] = 1)", N0, "Mature customers with KYC completed (as of snapshot).")
m(f, "Mature Bank Linked Users", "CALCULATE(SUM(FactCustomer[BankLinked]), FactCustomer[FunnelMature] = 1)", N0, "Mature customers with a bank account linked.")
m(f, "Mature Funded Users", "CALCULATE(SUM(FactCustomer[Deposited]), FactCustomer[FunnelMature] = 1)", N0, "Mature customers who made a first deposit.")
m(f, "Mature First Traders", "CALCULATE(SUM(FactCustomer[Traded]), FactCustomer[FunnelMature] = 1)", N0, "Mature customers who placed a first trade.")
m(f, "Mature Active 30d Traders", "CALCULATE(COUNTROWS(FactCustomer), FactCustomer[FunnelMature] = 1, FactCustomer[Traded] = 1, FactCustomer[Active30d] = 1)", N0, "Mature first traders active in the last 30 days (funnel stage 6).")
m(f, "KYC Completion Rate", "DIVIDE([Mature KYC Users], [Mature Customers])", P1, "KYC completed / mature registered.")
m(f, "Bank Link Conversion", "DIVIDE([Mature Bank Linked Users], [Mature KYC Users])", P1, "Bank linked / KYC completed.")
m(f, "First Deposit Conversion", "DIVIDE([Mature Funded Users], [Mature Bank Linked Users])", P1, "Funded / bank linked.")
m(f, "First Trade Conversion", "DIVIDE([Mature First Traders], [Mature Funded Users])", P1, "First traders / funded (activation of funded customers).")
m(f, "First Trade Activation Rate", "DIVIDE([Mature First Traders], [Mature Customers])", P1, "End-to-end: mature registered -> first trade.")
m(f, "Active 30d Share of First Traders", "DIVIDE([Mature Active 30d Traders], [Mature First Traders])", P1, "Funnel stage 6 conversion.")
m(f, "Funnel Users", 'SWITCH(SELECTEDVALUE(DimStage[StageName]), "Registered", [Mature Customers], "KYC Completed", [Mature KYC Users], "Bank Linked", [Mature Bank Linked Users], "First Deposit", [Mature Funded Users], "First Trade", [Mature First Traders], "Active (30d)", [Mature Active 30d Traders], BLANK())', N0, "Users reached at the stage on the DimStage axis (disconnected table).")
m(f, "Funnel Previous Stage Users", 'SWITCH(SELECTEDVALUE(DimStage[StageName]), "KYC Completed", [Mature Customers], "Bank Linked", [Mature KYC Users], "First Deposit", [Mature Bank Linked Users], "First Trade", [Mature Funded Users], "Active (30d)", [Mature First Traders], BLANK())', N0, "Users who reached the stage before the one on the axis.")
m(f, "Funnel % of Registered", "DIVIDE([Funnel Users], [Mature Customers])", P1, "Stage users as a share of mature registered.")
m(f, "Funnel Step Conversion", "DIVIDE([Funnel Users], [Funnel Previous Stage Users])", P1, "Stage users / previous-stage users.")
m(f, "Funnel Users Lost", "IF(ISBLANK([Funnel Previous Stage Users]), BLANK(), [Funnel Previous Stage Users] - [Funnel Users])", N0, "Users lost between the previous stage and this one.")
m(f, "Funnel Drop-off Rate", "DIVIDE([Funnel Users Lost], [Funnel Previous Stage Users])", P1, "Share of previous-stage users lost at this step.")
m(f, "Total Funnel Loss", "[Mature Customers] - [Mature Active 30d Traders]", N0, "All users lost between registration and active-30d trader.")
m(f, "Share of Funnel Losses", "DIVIDE([Funnel Users Lost], [Total Funnel Loss])", P1, "Bottleneck share: this step's losses / all losses.")
m(f, "Median Days in Stage", 'CALCULATE(SWITCH(SELECTEDVALUE(DimStage[StageName]), "KYC Completed", MEDIAN(FactCustomer[DaysRegToKYC]), "Bank Linked", MEDIAN(FactCustomer[DaysKYCToBank]), "First Deposit", MEDIAN(FactCustomer[DaysBankToDeposit]), "First Trade", MEDIAN(FactCustomer[DaysDepositToTrade]), BLANK()), FactCustomer[FunnelMature] = 1)', D1, "Median days from the previous stage (mature customers who reached the stage).")
m(f, "Median Days Registration to First Trade", "CALCULATE(MEDIAN(FactCustomer[DaysRegToTrade]), FactCustomer[FunnelMature] = 1)", D1, "Median end-to-end time to first trade.")
m(f, "Funded Never Traded", "CALCULATE(COUNTROWS(FactCustomer), FactCustomer[Deposited] = 1, FactCustomer[Traded] = 0)", N0, "High-potential activation pool: funded, no trade yet.")
m(f, "Funded Never Traded Deposits INR", "CALCULATE(SUM(FactCustomer[FirstDepositAmountINR]), FactCustomer[Deposited] = 1, FactCustomer[Traded] = 0)", INR, "Sum of first deposits of funded-never-traded customers (balance sitting idle; not revenue).")
m(f, "Stalled Onboarding Customers", "CALCULATE(COUNTROWS(FactCustomer), DimSegment[SegmentKey] IN {2, 3, 4, 5})", N0, "Customers stalled beyond the historical maximum stage lag (segments 02-05).")

# ---------------------------------------------------------------- 02 Acquisition & marketing
f = "02 Acquisition and Marketing"
m(f, "Total Campaign Spend", "SUM(DimCampaign[CampaignSpendINR])", INR, "Recorded campaign spend (INR). Spend is not dated, so it ignores month/city/device/segment filters by design.")
m(f, "Paid Spend", "CALCULATE([Total Campaign Spend], DimCampaign[IsPaid] = 1)", INR, "Spend of campaigns with recorded spend.")
m(f, "Registered Customers (Full Period)", "CALCULATE([Registered Customers], REMOVEFILTERS(DimDate), REMOVEFILTERS(DimCity), REMOVEFILTERS(DimDevice), REMOVEFILTERS(DimSegment))", N0, "Registrations over the whole period; only campaign/channel filters apply. Matches the undated spend.")
m(f, "Paid Registrations (Full Period)", "CALCULATE([Registered Customers (Full Period)], DimCampaign[IsPaid] = 1)", N0, "Registrations from campaigns with recorded spend.")
m(f, "CAC", "DIVIDE([Total Campaign Spend], [Paid Registrations (Full Period)])", D1, "Customer acquisition cost = recorded spend / registered customers of paid campaigns. Blank for organic (no spend recorded) - not zero.")
m(f, "KYC Rate (Paid, Full Period)", "CALCULATE([KYC Completion Rate], REMOVEFILTERS(DimDate), REMOVEFILTERS(DimCity), REMOVEFILTERS(DimDevice), REMOVEFILTERS(DimSegment), DimCampaign[IsPaid] = 1)", P1, "Mature KYC rate of the paid population in scope.")
m(f, "First Trade Rate (Paid, Full Period)", "CALCULATE([First Trade Activation Rate], REMOVEFILTERS(DimDate), REMOVEFILTERS(DimCity), REMOVEFILTERS(DimDevice), REMOVEFILTERS(DimSegment), DimCampaign[IsPaid] = 1)", P1, "Mature first-trade rate of the paid population in scope.")
m(f, "Cost per KYC", "DIVIDE([CAC], [KYC Rate (Paid, Full Period)])", INR, "CAC / mature KYC rate = cost per KYC-complete customer at maturity.")
m(f, "Cost per First Trade", "DIVIDE([CAC], [First Trade Rate (Paid, Full Period)])", INR, "CAC / mature first-trade rate = cost per first trader at maturity. No revenue or ROI is implied.")
m(f, "Paid Share of Registrations", "DIVIDE(CALCULATE([Registered Customers], DimCampaign[IsPaid] = 1), [Registered Customers])", P1, "Share of registrations from campaigns with recorded spend.")
m(f, "Registration Share", "DIVIDE([Registered Customers], CALCULATE([Registered Customers], ALLSELECTED(DimCampaign)))", P1, "Share of selected registrations (campaign axis).")
m(f, "Spend Share", "DIVIDE([Total Campaign Spend], CALCULATE([Total Campaign Spend], ALLSELECTED(DimCampaign)))", P1, "Share of selected spend.")
m(f, "City Share of Registrations", "DIVIDE([Registered Customers], CALCULATE([Registered Customers], ALLSELECTED(DimCity)))", P1, "City axis share.")
m(f, "Device Share of Registrations", "DIVIDE([Registered Customers], CALCULATE([Registered Customers], ALLSELECTED(DimDevice)))", P1, "Device axis share.")
m(f, "Rank Cost per First Trade (Paid)", "IF(ISBLANK([Cost per First Trade]), BLANK(), RANKX(FILTER(ALLSELECTED(DimCampaign[CampaignName]), NOT(ISBLANK([Cost per First Trade]))), [Cost per First Trade], , ASC, DENSE))", N0, "1 = lowest cost per first trader among selected paid campaigns.")
m(f, "Rank First Trade Rate", "RANKX(ALLSELECTED(DimCampaign[CampaignName]), [First Trade Activation Rate], , DESC, DENSE)", N0, "1 = highest mature first-trade rate among selected campaigns.")
m(f, "Median Paid Cost per First Trade", "MEDIANX(FILTER(ALLSELECTED(DimCampaign[CampaignName]), NOT(ISBLANK([Cost per First Trade]))), [Cost per First Trade])", INR, "Median across selected paid campaigns (peer benchmark).")
m(f, "Median Paid Cost per KYC", "MEDIANX(FILTER(ALLSELECTED(DimCampaign[CampaignName]), NOT(ISBLANK([Cost per KYC]))), [Cost per KYC])", INR, "Median across selected paid campaigns (peer benchmark for onboarding cost).")
m(f, "Cost Efficiency Index", "DIVIDE([Median Paid Cost per First Trade], [Cost per First Trade])", D2, "Peer median / own cost per first trade. Above 1 = cheaper than the median paid campaign.")
m(f, "Budget Signal", 'SWITCH(TRUE(), ISBLANK([Cost per First Trade]), "Organic - no spend to optimise", [Cost Efficiency Index] >= [Efficient Index Threshold], "Efficient vs peers - protect / test scaling", [Cost Efficiency Index] <= [Costly Index Threshold], "Costly vs peers - review / test cut-back", "In line with peers")', TXT, "Indicator only: ranks cost per first trader against peers. Not a recommendation without a test (no revenue data).")
m(f, "Evidence Strength", 'IF(SELECTEDVALUE(DimCampaign[Phase3SignificantAt5pct]) = "Yes", "First-trade rate differs significantly from other campaigns (Phase 3, Holm)", "Not significant at 5% - treat as indicative")', TXT, "Statistical caution carried over from Phase 3.")
m(f, "Phase 3 Scorecard Tier", 'SELECTEDVALUE(DimCampaign[Phase3Tier], "Multiple campaigns")', TXT, "Tier assigned by the Phase 3 scorecard (static input).")
m(f, "Phase 3 Overall Score", "SELECTEDVALUE(DimCampaign[Phase3OverallScore])", D1, "Phase 3 composite score (paid campaigns only).")
m(f, "CAC Scope Note", 'IF(ISFILTERED(DimDate) || ISFILTERED(DimCity) || ISFILTERED(DimDevice) || ISFILTERED(DimSegment), "Spend is not dated: CAC and cost per trade ignore month, city, device and segment filters.", "")', TXT, "Warning shown on cards when a filter the spend cannot follow is active.")

# ---------------------------------------------------------------- 03 Retention & engagement
f = "03 Retention and Engagement"
m(f, "Customers To Date", "VAR d = MAX(DimDate[Date]) RETURN CALCULATE([Registered Customers], FILTER(ALL(DimDate), DimDate[Date] <= d))", N0, "Cumulative registrations up to the last selected date.")
m(f, "MAU", "VAR mth = MAX(FactActivity[ActivityMonthDate]) RETURN CALCULATE(SUM(FactActivity[ActiveInMonth]), FactActivity[ActivityMonthDate] = mth)", N0, "Monthly active users of the latest month in context (Oct-2026 when unfiltered).")
m(f, "MAU Share of Customers", "VAR mth = MAX(FactActivity[ActivityMonthDate]) RETURN DIVIDE([MAU], CALCULATE([Registered Customers], FILTER(ALL(DimDate), DimDate[Date] <= EOMONTH(mth, 0))))", P1, "MAU / customers registered by month end.")
m(f, "30-Day Retention", "CALCULATE(AVERAGE(FactCustomer[Active30d]), FactCustomer[Eligible30d] = 1)", P1, "Share active in the last 30 days among customers with tenure of at least 31 days.")
m(f, "Inactive 90d Rate", "CALCULATE(AVERAGE(FactCustomer[Inactive90d]), FactCustomer[Eligible90d] = 1)", P1, "Share inactive for more than 90 days (proxy for churn, not confirmed churn).")
m(f, "Dormant 3m Rate", "AVERAGE(FactCustomer[Dormant3m])", P1, "Share with no active month Aug-Oct 2026, customers registered by Jul-2026 (churn proxy).")
m(f, "Cohort Retention", "AVERAGE(FactActivity[ActiveInMonth])", P1, "Share active - use in the cohort matrix (rows RegMonthDate, columns MonthsSinceRegistration).")
m(f, "Cohort Size", "CALCULATE(DISTINCTCOUNT(FactActivity[CustomerID]), FactActivity[MonthsSinceRegistration] = 0)", N0, "Customers in the registration cohort.")
m(f, "M1 Retention", "CALCULATE(AVERAGE(FactActivity[ActiveInMonth]), FactActivity[MonthsSinceRegistration] = 1)", P2, "Active the calendar month after registration (pooled).")
m(f, "M3 Retention", "CALCULATE(AVERAGE(FactActivity[ActiveInMonth]), FactActivity[MonthsSinceRegistration] = 3)", P2, "Active 3 calendar months after the registration month (pooled).")
m(f, "M6 Retention", "CALCULATE(AVERAGE(FactActivity[ActiveInMonth]), FactActivity[MonthsSinceRegistration] = 6)", P2, "Active 6 calendar months after the registration month (pooled).")
m(f, "Inactivity Share (Eligible)", "DIVIDE(CALCULATE(COUNTROWS(FactCustomer), FactCustomer[Eligible30d] = 1), CALCULATE(COUNTROWS(FactCustomer), FactCustomer[Eligible30d] = 1, REMOVEFILTERS(FactCustomer[InactivityBucket])))", P1, "Share of 30-day-eligible customers (tenure of at least 31 days) per days-since-last-activity bucket; same base as the Phase 3 inactivity distribution.")
m(f, "Trading Users", "SUM(FactActivity[TradedInMonth])", N0, "Customer-months with at least one trade (monthly trading users when sliced by month).")
m(f, "Trades", "SUM(FactActivity[TradeCount])", N0, "Number of trades.")
m(f, "Trading Value INR mn", "DIVIDE(SUM(FactActivity[TradingValueINR]), 1000000)", D2, "Trading value in INR millions.")
m(f, "Deposits INR mn", "DIVIDE(SUM(FactActivity[DepositValueINR]), 1000000)", D2, "Deposits in INR millions.")
m(f, "Withdrawals INR mn", "DIVIDE(SUM(FactActivity[WithdrawalValueINR]), 1000000)", D2, "Withdrawals in INR millions.")
m(f, "Net Flow INR mn", "DIVIDE(SUM(FactActivity[NetFlowINR]), 1000000)", D2, "Deposits minus withdrawals (INR millions).")
m(f, "Withdrawal to Deposit Ratio", "DIVIDE(SUM(FactActivity[WithdrawalValueINR]), SUM(FactActivity[DepositValueINR]))", P1, "Withdrawals as a share of deposits.")
m(f, "Trades per Trading User", "DIVIDE([Trades], [Trading Users])", D1, "Average trades per trading customer-month.")
m(f, "Avg Trade Value INR", "DIVIDE(SUM(FactActivity[TradingValueINR]), [Trades])", INR, "Average value per trade.")
m(f, "Ever-Traders (Repeat Base)", "CALCULATE(COUNTROWS(FactCustomer), FactCustomer[MonthsObserved] >= [Repeat Base Months], FactCustomer[TradeMonths] >= 1)", N0, "Customers with enough history that traded in at least one month.")
m(f, "Repeat Traders", "CALCULATE(COUNTROWS(FactCustomer), FactCustomer[MonthsObserved] >= [Repeat Base Months], FactCustomer[TradeMonths] >= [Repeat Trader Min Months])", N0, "Customers who traded in 2+ calendar months.")
m(f, "Repeat Trader Share", "DIVIDE([Repeat Traders], [Ever-Traders (Repeat Base)])", P1, "Repeat traders / ever-traders.")
m(f, "Segment Share", "DIVIDE([Registered Customers], CALCULATE([Registered Customers], ALLSELECTED(DimSegment)))", P1, "Share of selected customers per segment.")
m(f, "Avg 6m Trading Value INR", "AVERAGE(FactCustomer[TradingValue6mINR])", INR, "Mean trading value over the last six months.")

# ---------------------------------------------------------------- 04 Time intelligence
f = "04 Time Intelligence"
m(f, "Registered Customers PM", "CALCULATE([Registered Customers], DATEADD(DimDate[Date], -1, MONTH))", N0, "Registrations in the previous month.")
m(f, "Registrations MoM %", "IF(HASONEVALUE(DimDate[MonthLabel]), VAR pm = [Registered Customers PM] RETURN IF(ISBLANK(pm), BLANK(), DIVIDE([Registered Customers] - pm, pm)), BLANK())", P1, "Month-over-month change in registrations (single month in context).")
m(f, "Registrations 3M Avg", "VAR d = MAX(DimDate[Date]) VAR win = DATESINPERIOD(DimDate[Date], d, -3, MONTH) RETURN DIVIDE(CALCULATE([Registered Customers], win), CALCULATE(DISTINCTCOUNT(DimDate[MonthStart]), win))", D1, "Rolling 3-month average of monthly registrations (fewer months at the start).")
m(f, "Registered YTD", "CALCULATE([Registered Customers], DATESYTD(DimDate[Date]))", N0, "Calendar year-to-date registrations (data cover Nov-2025 to Oct-2026, so 2025 YTD = Nov-Dec).")
m(f, "MAU PM", "CALCULATE([MAU], DATEADD(DimDate[Date], -1, MONTH))", N0, "MAU of the previous month.")
m(f, "MAU MoM %", "IF(HASONEVALUE(DimDate[MonthLabel]), VAR pm = [MAU PM] RETURN IF(ISBLANK(pm), BLANK(), DIVIDE([MAU] - pm, pm)), BLANK())", P1, "Month-over-month change in MAU.")
m(f, "Tickets PM", "CALCULATE([Tickets], DATEADD(DimDate[Date], -1, MONTH))", N0, "Tickets raised in the previous month.")
m(f, "Tickets MoM %", "IF(HASONEVALUE(DimDate[MonthLabel]), VAR pm = [Tickets PM] RETURN IF(ISBLANK(pm), BLANK(), DIVIDE([Tickets] - pm, pm)), BLANK())", P1, "Month-over-month change in ticket volume.")
m(f, "Trading Value INR mn PM", "CALCULATE([Trading Value INR mn], DATEADD(DimDate[Date], -1, MONTH))", D2, "Trading value of the previous month.")
m(f, "Trading Value MoM %", "IF(HASONEVALUE(DimDate[MonthLabel]), VAR pm = [Trading Value INR mn PM] RETURN IF(ISBLANK(pm), BLANK(), DIVIDE([Trading Value INR mn] - pm, pm)), BLANK())", P1, "Month-over-month change in trading value.")

# ---------------------------------------------------------------- 05 Customer operations
f = "05 Customer Operations"
m(f, "Tickets", "COUNTROWS(FactTicket)", N0, "Support tickets.")
m(f, "Tickets per 1000 Customers", "DIVIDE([Tickets], [Customers To Date]) * 1000", N0, "Tickets per 1,000 customers registered to date (whole period = Phase 3 definition).")
m(f, "Resolved Tickets", "SUM(FactTicket[IsResolved])", N0, "Tickets with a resolution.")
m(f, "Unresolved Tickets", "SUM(FactTicket[IsUnresolved])", N0, "Open plus escalated tickets (backlog).")
m(f, "Open Tickets", 'CALCULATE(COUNTROWS(FactTicket), FactTicket[Status] = "Open")', N0, "Tickets with status Open.")
m(f, "Escalated Tickets", "SUM(FactTicket[IsEscalated])", N0, "Tickets with status Escalated.")
m(f, "Resolved Rate", "DIVIDE([Resolved Tickets], [Tickets])", P1, "Resolved / all tickets.")
m(f, "Escalation Rate", "DIVIDE([Escalated Tickets], [Tickets])", P2, "Escalated / all tickets.")
m(f, "Avg Resolution Hours", "AVERAGE(FactTicket[ResolutionHours])", D1, "Mean hours to resolve (resolved tickets).")
m(f, "Median Resolution Hours", "MEDIAN(FactTicket[ResolutionHours])", D1, "Median hours to resolve (typical customer wait).")
m(f, "P90 Resolution Hours", "PERCENTILE.INC(FactTicket[ResolutionHours], 0.9)", D1, "90th percentile of resolution hours.")
m(f, "Within SLA Rate", "DIVIDE(CALCULATE(COUNTROWS(FactTicket), FactTicket[IsResolved] = 1, FactTicket[ResolutionHours] <= [SLA Hours]), [Resolved Tickets])", P1, "Resolved within the illustrative SLA hours.")
m(f, "CSAT", "AVERAGE(FactTicket[CSAT])", D2, "Mean customer satisfaction (1-5), rated tickets only.")
m(f, "CSAT Top-Box", "DIVIDE(CALCULATE(COUNTROWS(FactTicket), FactTicket[CSAT] >= 4), COUNT(FactTicket[CSAT]))", P1, "Share of ratings 4-5.")
m(f, "CSAT Bottom-Box", "DIVIDE(CALCULATE(COUNTROWS(FactTicket), FactTicket[CSAT] <= 2), COUNT(FactTicket[CSAT]))", P1, "Share of ratings 1-2.")
m(f, "Backlog over 90 Days", "CALCULATE(COUNTROWS(FactTicket), FactTicket[IsUnresolved] = 1, FactTicket[TicketAgeDays] > 90)", N0, "Unresolved tickets older than 90 days.")
m(f, "Category Share", "DIVIDE([Tickets], CALCULATE([Tickets], REMOVEFILTERS(FactTicket[Category])))", P1, "Share of tickets per category.")
m(f, "Priority Share", "DIVIDE([Tickets], CALCULATE([Tickets], REMOVEFILTERS(FactTicket[Priority])))", P1, "Share of tickets per priority.")
m(f, "High Priority Share", 'DIVIDE(CALCULATE(COUNTROWS(FactTicket), FactTicket[Priority] = "High"), [Tickets])', P1, "High-priority tickets / all tickets.")
m(f, "Onboarding Tickets", 'CALCULATE(COUNTROWS(FactTicket), FactTicket[RelatedFunnelStage] <> "none")', N0, "Tickets tied to an onboarding stage (KYC, bank, deposit, trade).")
m(f, "Tickets While Stage Pending", "CALCULATE(COUNTROWS(FactTicket), FactTicket[StagePendingAtTicket] = 1)", N0, "Onboarding tickets raised while the related stage was still pending.")
m(f, "Pending Stage Ticket Share", "DIVIDE([Tickets While Stage Pending], [Onboarding Tickets])", P1, "Share of onboarding tickets raised while the stage was pending.")

# ---------------------------------------------------------------- 06 Labels
f = "06 Labels and Notes"
m(f, "Mature Cohort Note", '"Funnel rates use the mature cohort (registered before Oct-2026): n = " & FORMAT([Mature Customers], "#,0")', TXT, "Footnote for funnel visuals.")
m(f, "Data Disclaimer", '"Synthetic data - fictional Indian retail brokerage; not real customer data."', TXT, "Footer on every page.")
m(f, "Proxy Note", '"Inactive 90d and Dormant 3m are churn proxies, not confirmed churn."', TXT, "Footnote for retention visuals.")

DIM_DATE_DAX = """DimDate =
VAR _start = DATE(2025, 11, 1)
VAR _end = DATE(2026, 10, 31)
RETURN
ADDCOLUMNS(
    CALENDAR(_start, _end),
    "Year", YEAR([Date]),
    "Quarter", "Q" & ROUNDUP(MONTH([Date]) / 3, 0),
    "MonthNumber", MONTH([Date]),
    "MonthStart", DATE(YEAR([Date]), MONTH([Date]), 1),
    "MonthLabel", FORMAT([Date], "mmm yy"),
    "MonthSort", YEAR([Date]) * 100 + MONTH([Date]),
    "WeekdayNumber", WEEKDAY([Date], 2),
    "WeekdayName", FORMAT([Date], "ddd"),
    "IsMonthStart", IF(DAY([Date]) = 1, 1, 0)
)"""
