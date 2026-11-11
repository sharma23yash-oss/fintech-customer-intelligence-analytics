// FactTicket - SYNTHETIC data. One query per CSV; load enabled. Requires the DataFolder parameter (see 00_DataFolder.pq).
let
    Source   = Csv.Document(File.Contents(DataFolder & "\FactTicket.csv"), [Delimiter = ",", Columns = 21, Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed    = Table.TransformColumnTypes(Promoted, {{"TicketID", type text}, {"CustomerID", type text}, {"CreatedDate", type date}, {"CampaignKey", type text}, {"CityKey", type text}, {"DeviceKey", type text}, {"SegmentKey", Int64.Type}, {"Category", type text}, {"Priority", type text}, {"PrioritySort", Int64.Type}, {"Status", type text}, {"ResolutionHours", type number}, {"CSAT", Int64.Type}, {"IsResolved", Int64.Type}, {"IsUnresolved", Int64.Type}, {"IsEscalated", Int64.Type}, {"TicketAgeDays", Int64.Type}, {"BacklogAgeBucket", type text}, {"BacklogSort", Int64.Type}, {"RelatedFunnelStage", type text}, {"StagePendingAtTicket", Int64.Type}}, "en-US")
in
    Typed
