# Power Query transformation instructions

Synthetic data. The 8 star-schema CSVs in `06_dashboard/data/` are already clean (produced and validated by `06_dashboard/build_scripts/19_build_powerbi_model_data.py`, 27 integrity checks). Power Query therefore only has to **load and type** them; no business logic lives in M. All business logic is in DAX so every figure stays traceable.

## Steps

1. **Home > Transform data > New Source > Blank Query**, open *Advanced Editor*, paste `00_DataFolder.pq`, set the path of your local `06_dashboard/data` folder, and name the query `DataFolder` (Home > Manage Parameters also works).
2. For each file `01_...` to `08_...` create a blank query, paste the M, and name the query exactly as the table (`DimCampaign`, `FactCustomer`, ...).
3. **Close & Apply.** `DimDate` and `_Measures` are *not* Power Query tables - they are DAX calculated tables (see `dax/`).

## What each query does

| Step | M function | Why |
|---|---|---|
| Source | `Csv.Document(File.Contents(DataFolder & "\\Table.csv"), [Encoding = 65001, QuoteStyle = QuoteStyle.Csv])` | UTF-8 CSV; quote-aware so text with commas is safe |
| Promoted | `Table.PromoteHeaders(..., [PromoteAllScalars = true])` | first row becomes column names |
| Typed | `Table.TransformColumnTypes(..., "en-US")` | explicit types; fixed culture so ISO dates (`yyyy-mm-dd`) and `.` decimals parse the same on any machine |

Blank cells in integer columns (e.g. `DaysRegToKYC` for customers who never completed KYC, `CSAT` for unrated tickets) stay `null` on purpose: DAX `AVERAGE`, `MEDIAN` and `PERCENTILE` ignore blanks, which is the intended behaviour.

## Column types per table

### DimCampaign (10 rows, 14 columns)

| Column | Type |
|---|---|
| CampaignKey | text |
| CampaignName | text |
| Channel | text |
| ChannelSort | int |
| SourcePlatform | text |
| ChannelGroup | text |
| AcquisitionType | text |
| IsPaid | int |
| CampaignSpendINR | int |
| SpendBasis | text |
| Phase3Tier | text |
| Phase3OverallScore | number |
| Phase3FirstTradeP_Holm | number |
| Phase3SignificantAt5pct | text |

### DimCity (11 rows, 2 columns)

| Column | Type |
|---|---|
| CityKey | text |
| CitySort | int |

### DimDevice (3 rows, 2 columns)

| Column | Type |
|---|---|
| DeviceKey | text |
| DeviceSort | int |

### DimSegment (10 rows, 4 columns)

| Column | Type |
|---|---|
| SegmentKey | int |
| SegmentName | text |
| SegmentGroup | text |
| RecommendedAction | text |

### DimStage (6 rows, 2 columns)

| Column | Type |
|---|---|
| StageOrder | int |
| StageName | text |

### FactCustomer (10,000 rows, 42 columns)

| Column | Type |
|---|---|
| CustomerID | text |
| RegistrationDate | date |
| CampaignKey | text |
| CityKey | text |
| DeviceKey | text |
| SegmentKey | int |
| AgeGroup | text |
| RiskProfile | text |
| FurthestStage | text |
| KYCDone | int |
| BankLinked | int |
| Deposited | int |
| Traded | int |
| KYCDate | date |
| BankDate | date |
| DepositDate | date |
| FirstTradeDate | date |
| FirstDepositAmountINR | number |
| FunnelMature | int |
| Eligible30d | int |
| Eligible90d | int |
| DaysRegToKYC | int |
| DaysKYCToBank | int |
| DaysBankToDeposit | int |
| DaysDepositToTrade | int |
| DaysRegToTrade | int |
| Active30d | int |
| Inactive90d | int |
| TenureDays | int |
| MonthsObserved | int |
| TradeMonths | int |
| TradeMonths6m | int |
| TradingValue6mINR | number |
| Dormant3m | int |
| M1Retained | int |
| M3Retained | int |
| M6Retained | int |
| TicketCount | int |
| UnresolvedTicketCount | int |
| DaysSinceLastActivity | int |
| InactivityBucket | text |
| InactivitySort | int |

### FactActivity (64,645 rows, 17 columns)

| Column | Type |
|---|---|
| CustomerID | text |
| ActivityMonthDate | date |
| RegMonthDate | date |
| MonthsSinceRegistration | int |
| CampaignKey | text |
| CityKey | text |
| DeviceKey | text |
| SegmentKey | int |
| ActiveInMonth | int |
| TradedInMonth | int |
| DepositedInMonth | int |
| WithdrewInMonth | int |
| TradeCount | int |
| TradingValueINR | number |
| DepositValueINR | number |
| WithdrawalValueINR | number |
| NetFlowINR | number |

### FactTicket (7,614 rows, 21 columns)

| Column | Type |
|---|---|
| TicketID | text |
| CustomerID | text |
| CreatedDate | date |
| CampaignKey | text |
| CityKey | text |
| DeviceKey | text |
| SegmentKey | int |
| Category | text |
| Priority | text |
| PrioritySort | int |
| Status | text |
| ResolutionHours | number |
| CSAT | int |
| IsResolved | int |
| IsUnresolved | int |
| IsEscalated | int |
| TicketAgeDays | int |
| BacklogAgeBucket | text |
| BacklogSort | int |
| RelatedFunnelStage | text |
| StagePendingAtTicket | int |

## Model-side settings after load (cannot be stored in M)

- Set *Sort by column* as listed in `docs/Data_Model.md` (Month label by MonthSort, Channel by ChannelSort, Priority by PrioritySort, ...).
- Set *Summarization = Don't summarize* on every numeric column (use measures, not implicit aggregation).
- Hide key and sort helper columns in the fact tables.
- Date columns: format `yyyy-mm-dd`.
