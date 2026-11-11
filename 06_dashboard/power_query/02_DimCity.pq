// DimCity - SYNTHETIC data. One query per CSV; load enabled. Requires the DataFolder parameter (see 00_DataFolder.pq).
let
    Source   = Csv.Document(File.Contents(DataFolder & "\DimCity.csv"), [Delimiter = ",", Columns = 2, Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed    = Table.TransformColumnTypes(Promoted, {{"CityKey", type text}, {"CitySort", Int64.Type}}, "en-US")
in
    Typed
