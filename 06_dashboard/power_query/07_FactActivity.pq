// FactActivity - SYNTHETIC data. One query per CSV; load enabled. Requires the DataFolder parameter (see 00_DataFolder.pq).
let
    Source   = Csv.Document(File.Contents(DataFolder & "\FactActivity.csv"), [Delimiter = ",", Columns = 17, Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed    = Table.TransformColumnTypes(Promoted, {{"CustomerID", type text}, {"ActivityMonthDate", type date}, {"RegMonthDate", type date}, {"MonthsSinceRegistration", Int64.Type}, {"CampaignKey", type text}, {"CityKey", type text}, {"DeviceKey", type text}, {"SegmentKey", Int64.Type}, {"ActiveInMonth", Int64.Type}, {"TradedInMonth", Int64.Type}, {"DepositedInMonth", Int64.Type}, {"WithdrewInMonth", Int64.Type}, {"TradeCount", Int64.Type}, {"TradingValueINR", type number}, {"DepositValueINR", type number}, {"WithdrawalValueINR", type number}, {"NetFlowINR", type number}}, "en-US")
in
    Typed
