// DimCampaign - SYNTHETIC data. One query per CSV; load enabled. Requires the DataFolder parameter (see 00_DataFolder.pq).
let
    Source   = Csv.Document(File.Contents(DataFolder & "\DimCampaign.csv"), [Delimiter = ",", Columns = 14, Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed    = Table.TransformColumnTypes(Promoted, {{"CampaignKey", type text}, {"CampaignName", type text}, {"Channel", type text}, {"ChannelSort", Int64.Type}, {"SourcePlatform", type text}, {"ChannelGroup", type text}, {"AcquisitionType", type text}, {"IsPaid", Int64.Type}, {"CampaignSpendINR", Int64.Type}, {"SpendBasis", type text}, {"Phase3Tier", type text}, {"Phase3OverallScore", type number}, {"Phase3FirstTradeP_Holm", type number}, {"Phase3SignificantAt5pct", type text}}, "en-US")
in
    Typed
