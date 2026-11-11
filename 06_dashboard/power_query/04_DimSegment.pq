// DimSegment - SYNTHETIC data. One query per CSV; load enabled. Requires the DataFolder parameter (see 00_DataFolder.pq).
let
    Source   = Csv.Document(File.Contents(DataFolder & "\DimSegment.csv"), [Delimiter = ",", Columns = 4, Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed    = Table.TransformColumnTypes(Promoted, {{"SegmentKey", Int64.Type}, {"SegmentName", type text}, {"SegmentGroup", type text}, {"RecommendedAction", type text}}, "en-US")
in
    Typed
